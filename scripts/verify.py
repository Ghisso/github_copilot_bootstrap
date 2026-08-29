#!/usr/bin/env python3
"""Fail-closed deterministic verification receipts.

The deterministic command owns verification evidence while quality-score,
findings, and legacy hook gates remain authoritative. ``fast`` is focused feedback, ``phase``
persists reusable evidence, and ``closeout`` proves that phase evidence remains
fresh before emitting a final state-bound receipt.

Usage:
    uv run python .claude/scripts/verify.py fast --format json
    uv run python .claude/scripts/verify.py phase --format json --persist
    uv run python .claude/scripts/verify.py closeout --format json --persist
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.dont_write_bytecode = True
import quality_score  # noqa: E402  # must follow the bytecode-cache guard


SCHEMA_VERSION = 2
CHECK_STATES = frozenset({"PASS", "FAIL", "UNVERIFIED", "NOT_APPLICABLE"})
MODES = frozenset({"fast", "phase", "closeout"})
CHECK_IDS = (
    "VFY-STATUS-001",
    "VFY-STATUS-002",
    "VFY-RUFF-001",
    "VFY-MYPY-001",
    "VFY-PYTEST-001",
    "VFY-FRESH-001",
    "VFY-FRESH-002",
    "VFY-CONTROL-001",
    "VFY-GEN-001",
    "VFY-DETERMINISM-001",
    "VFY-RECEIPT-001",
)
COMMAND_TIMEOUT_SECONDS = 180
PHASE_RECEIPT = Path(".claude/quality_reports/verification-phase.json")
CLOSEOUT_RECEIPT = Path(".claude/quality_reports/verification-closeout.json")
ARTIFACT_KEYS = ("phase_receipt", "score", "findings", "closeout_log")
AUTHORITATIVE_RECEIPT_FIELDS = {
    "schema_version",
    "mode",
    "status",
    "checks",
    "metadata",
    "artifacts",
}
RECEIPT_EXTENSIONS_FIELD = "extensions"
CONTROL_PLANE_PREFIXES = (
    ".claude/",
    ".codex/",
    ".agents/",
    ".github/",
    ".devcontainer/",
)
CONTROL_PLANE_FILES = {"AGENTS.md", "CLAUDE.md", ".mcp.json"}
CONFIG_SUFFIXES = {".cfg", ".ini", ".json", ".toml", ".yaml", ".yml"}
DEPENDENCY_FILES = {
    "Cargo.lock",
    "Cargo.toml",
    "Pipfile",
    "Pipfile.lock",
    "go.mod",
    "go.sum",
    "package-lock.json",
    "package.json",
    "pnpm-lock.yaml",
    "poetry.lock",
    "uv.lock",
    "yarn.lock",
}


def run_process(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run one bounded local tool invocation."""
    return subprocess.run(
        args,
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        timeout=COMMAND_TIMEOUT_SECONDS,
    )


def check(
    check_id: str, status: str, summary: str, applicable: bool = True
) -> dict[str, object]:
    """Build a strict check record from deterministic applicability."""
    if check_id not in CHECK_IDS:
        raise ValueError(f"unknown check ID: {check_id}")
    if status not in CHECK_STATES:
        raise ValueError(f"unknown check status: {status}")
    if not applicable and status != "NOT_APPLICABLE":
        raise ValueError("inapplicable checks must use NOT_APPLICABLE")
    if applicable and status == "NOT_APPLICABLE":
        raise ValueError("NOT_APPLICABLE requires deterministic inapplicability")
    return {
        "id": check_id,
        "status": status,
        "summary": summary,
        "applicable": applicable,
    }


def aggregate_status(checks: list[dict[str, object]]) -> str:
    """Return the fail-closed aggregate state for check records."""
    statuses = {str(item["status"]) for item in checks}
    if "FAIL" in statuses:
        return "FAIL"
    if "UNVERIFIED" in statuses:
        return "UNVERIFIED"
    if "PASS" in statuses:
        return "PASS"
    return "NOT_APPLICABLE"


def validate_receipt(receipt: object) -> dict[str, object]:
    """Validate the versioned receipt contract and return its typed mapping."""
    if not isinstance(receipt, dict):
        raise ValueError("receipt must be an object")
    required = {"schema_version", "mode", "status", "checks", "metadata"}
    missing = sorted(required - receipt.keys())
    if missing:
        raise ValueError(f"receipt missing required fields: {', '.join(missing)}")
    if receipt["schema_version"] != SCHEMA_VERSION:
        raise ValueError("receipt has an unsupported schema_version")
    if receipt["mode"] not in MODES:
        raise ValueError("receipt has an unknown mode")
    if receipt["status"] not in CHECK_STATES:
        raise ValueError("receipt has an unknown status")
    unknown = set(receipt) - AUTHORITATIVE_RECEIPT_FIELDS - {RECEIPT_EXTENSIONS_FIELD}
    if unknown:
        raise ValueError("receipt has unknown authoritative fields")
    if RECEIPT_EXTENSIONS_FIELD in receipt and not isinstance(
        receipt[RECEIPT_EXTENSIONS_FIELD], dict
    ):
        raise ValueError("receipt extensions must be an object")
    checks = receipt["checks"]
    if not isinstance(checks, list) or len(checks) != len(CHECK_IDS):
        raise ValueError("receipt must contain every required check exactly once")
    found_ids: set[str] = set()
    typed_checks: list[dict[str, object]] = []
    for item in checks:
        if not isinstance(item, dict):
            raise ValueError("receipt check must be an object")
        if set(item) != {"id", "status", "summary", "applicable"}:
            raise ValueError("receipt check has malformed fields")
        check_id = item["id"]
        status = item["status"]
        applicable = item["applicable"]
        if not isinstance(check_id, str) or check_id not in CHECK_IDS:
            raise ValueError("receipt check has an unknown ID")
        if check_id in found_ids:
            raise ValueError("receipt has duplicate check IDs")
        if status not in CHECK_STATES:
            raise ValueError("receipt check has an unknown status")
        if not isinstance(item["summary"], str) or not isinstance(applicable, bool):
            raise ValueError("receipt check has invalid field types")
        if (status == "NOT_APPLICABLE") != (not applicable):
            raise ValueError("NOT_APPLICABLE must come from applicability logic")
        found_ids.add(check_id)
        typed_checks.append(item)
    if found_ids != set(CHECK_IDS):
        raise ValueError("receipt is missing a required check")
    if receipt["status"] != aggregate_status(typed_checks):
        raise ValueError("receipt aggregate status does not match checks")
    metadata = receipt["metadata"]
    if not isinstance(metadata, dict):
        raise ValueError("receipt metadata must be an object")
    for field in (
        "generated_at",
        "base_ref",
        "branch",
        "head_sha",
        "merge_base_sha",
        "tree_sha",
        "phase",
        "content_hash",
        "tracked_state_hash",
    ):
        if not isinstance(metadata.get(field), str):
            raise ValueError(f"receipt metadata is missing {field}")
    for field in ("changed_paths", "relevant_paths"):
        if not isinstance(metadata.get(field), list) or not all(
            isinstance(path, str) for path in metadata[field]
        ):
            raise ValueError(f"receipt metadata is missing {field}")
    if not isinstance(metadata.get("path_discovery_ok"), bool):
        raise ValueError("receipt metadata is missing path_discovery_ok")
    artifacts = receipt.get("artifacts")
    if receipt["mode"] == "closeout":
        validate_artifact_references(artifacts)
    elif artifacts is not None:
        raise ValueError("only closeout receipts may contain artifacts")
    validate_mode_applicability(receipt["mode"], typed_checks, metadata)
    return receipt


def validate_artifact_references(artifacts: object) -> None:
    """Reject ambiguous or unsafe closeout artifact references."""
    if not isinstance(artifacts, dict) or set(artifacts) != set(ARTIFACT_KEYS):
        raise ValueError("closeout receipt must contain every artifact reference")
    for key in ARTIFACT_KEYS:
        artifact = artifacts[key]
        if not isinstance(artifact, dict) or set(artifact) != {"path", "sha256"}:
            raise ValueError(f"closeout artifact {key} is malformed")
        path, digest = artifact["path"], artifact["sha256"]
        if (
            not isinstance(path, str)
            or not is_safe_relative_path(path)
            or not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            raise ValueError(f"closeout artifact {key} is invalid")


def is_safe_relative_path(value: str) -> bool:
    """Return whether a receipt reference stays inside the repository root."""
    path = Path(value)
    return bool(value and not path.is_absolute() and ".." not in path.parts)


def validate_mode_applicability(
    mode: object, checks: list[dict[str, object]], metadata: dict[str, object]
) -> None:
    """Reject caller-selected N/A states using fixed mode applicability."""
    inapplicable = {
        "fast": {
            "VFY-MYPY-001",
            "VFY-PYTEST-001",
            "VFY-FRESH-001",
            "VFY-FRESH-002",
            "VFY-GEN-001",
            "VFY-RECEIPT-001",
        },
        "phase": {"VFY-RECEIPT-001"},
        "closeout": {
            "VFY-RUFF-001",
            "VFY-MYPY-001",
            "VFY-PYTEST-001",
            "VFY-GEN-001",
        },
    }[str(mode)]
    if mode == "fast" and not any(
        Path(path).suffix == ".py"
        for path in metadata_paths(metadata, "relevant_paths")
    ):
        inapplicable.add("VFY-RUFF-001")
    for item in checks:
        if item["applicable"] is not (item["id"] not in inapplicable):
            raise ValueError(f"{item['id']} has invalid applicability for {mode} mode")


def git_output(args: list[str], root: Path) -> str:
    """Return Git output or an empty string when the repository is unavailable."""
    try:
        result = run_process(["git", *args], root)
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def git_paths(root: Path, base_ref: str) -> list[str]:
    """Return tracked changed paths relative to the branch base and worktree."""
    merge_base = git_output(["merge-base", base_ref, "HEAD"], root)
    paths: set[str] = set()
    for args in (
        ["diff", "--name-only", "-z", f"{base_ref}...HEAD"],
        ["diff", "--name-only", "-z"],
        ["diff", "--cached", "--name-only", "-z"],
        ["ls-files", "--others", "--exclude-standard", "-z"],
    ):
        if not merge_base and base_ref in args[-1]:
            continue
        try:
            result = run_process(["git", *args], root)
        except (OSError, subprocess.SubprocessError) as error:
            raise ValueError(f"Git path discovery failed: {error}") from error
        if result.returncode != 0:
            raise ValueError(f"Git path discovery exited {result.returncode}")
        paths.update(path for path in result.stdout.split("\0") if path)
    return sorted(paths)


def classify_path(path: str) -> str:
    """Classify the small, canonical freshness scope for one tracked path."""
    if path in CONTROL_PLANE_FILES or path.startswith(CONTROL_PLANE_PREFIXES):
        return "control-plane"
    if path.startswith(("scripts/", "shared/scripts/")):
        return "generator"
    if path.startswith("shared/"):
        return "control-plane"
    name = Path(path).name
    if (
        name in DEPENDENCY_FILES
        or name.startswith("requirements")
        or name.startswith("Dockerfile")
    ):
        return "config"
    suffix = Path(path).suffix.lower()
    if suffix in CONFIG_SUFFIXES:
        return "config"
    if path.startswith("tests/"):
        return "test"
    if suffix == ".py":
        return "code"
    if path.startswith("docs/") or suffix in {".md", ".rst"}:
        return "documentation-only"
    return "code"


def scoped_paths(paths: list[str]) -> list[str]:
    """Select evidence-relevant paths; ordinary documentation stays reusable."""
    return [path for path in paths if classify_path(path) != "documentation-only"]


def hash_paths(root: Path, paths: list[str]) -> str:
    """Hash current path names and bytes, including deletions and untracked files."""
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.encode("utf-8") + b"\0")
        candidate = root / path
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            digest.update(b"<deleted>")
        else:
            digest.update(
                f"{stat.S_IFMT(info.st_mode):o}:{stat.S_IMODE(info.st_mode):o}".encode()
            )
            if stat.S_ISLNK(info.st_mode):
                digest.update(b":link:" + os.readlink(candidate).encode("utf-8"))
            elif stat.S_ISREG(info.st_mode):
                digest.update(b":file:" + candidate.read_bytes())
            else:
                digest.update(b":other")
        digest.update(b"\0")
    return digest.hexdigest()


def current_phase(root: Path, branch: str) -> str:
    """Read the active phase for an implementation branch without YAML parsing."""
    if not branch.endswith("_implementation"):
        return ""
    plan = root / ".claude/plans" / f"{branch.removesuffix('_implementation')}.md"
    try:
        text = plan.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(r"^current_phase:[ \t]*([^\s#]+)[ \t]*$", text, re.MULTILINE)
    return match.group(1) if match else ""


def state_metadata(root: Path, base_ref: str, phase: str = "") -> dict[str, object]:
    """Capture Git metadata and whole/scoped content bindings."""
    merge_base = git_output(["merge-base", base_ref, "HEAD"], root)
    try:
        paths = git_paths(root, base_ref)
    except ValueError:
        paths = []
        path_discovery_ok = False
    else:
        path_discovery_ok = True
    relevant = scoped_paths(paths)
    branch = git_output(["rev-parse", "--abbrev-ref", "HEAD"], root)
    return {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "base_ref": base_ref,
        "branch": branch,
        "phase": phase or current_phase(root, branch),
        "head_sha": git_output(["rev-parse", "HEAD"], root),
        "merge_base_sha": merge_base,
        "tree_sha": git_output(["write-tree"], root),
        "content_hash": hash_paths(root, relevant),
        "tracked_state_hash": hash_paths(root, paths),
        "changed_paths": paths,
        "relevant_paths": relevant,
        "path_discovery_ok": path_discovery_ok,
    }


def gate_receipt_errors(
    root: Path,
    *,
    branch: str,
    phase: str,
    head: str,
    head_relation: str,
    require_major: bool,
    require_ponytail: bool,
    enforce_final_state: bool,
) -> list[str]:
    """Validate completed closeout evidence for every native hook adapter."""
    errors: list[str] = []
    if not branch or not phase or not head:
        return ["closeout receipt gate needs branch, phase, and head"]
    try:
        receipt = load_receipt(root / CLOSEOUT_RECEIPT)
    except ValueError as error:
        return [str(error)]
    if receipt["mode"] != "closeout" or receipt["status"] != "PASS":
        return ["closeout receipt must be a passing closeout receipt"]
    metadata = receipt["metadata"]
    if not isinstance(metadata, dict):
        return ["closeout receipt metadata is malformed"]
    for field, expected in (("base_ref", "dev"), ("branch", branch), ("phase", phase)):
        if metadata.get(field) != expected:
            errors.append(f"closeout receipt {field} does not match {expected}")
    receipt_head = metadata.get("head_sha")
    if not isinstance(receipt_head, str) or not receipt_head:
        errors.append("closeout receipt is missing head_sha")
    elif head_relation == "exact" and receipt_head != head:
        errors.append("closeout receipt head_sha is stale")
    elif head_relation == "ancestor" and not git_is_ancestor(root, receipt_head, head):
        errors.append("closeout receipt head_sha is not an ancestor of the pushed ref")
    expected_base = git_output(["merge-base", "dev", head], root)
    if not expected_base or metadata.get("merge_base_sha") != expected_base:
        errors.append("closeout receipt merge_base_sha is stale")
    if metadata.get("path_discovery_ok") is not True:
        errors.append("closeout receipt path discovery was not verified")
    if enforce_final_state:
        expected_tree = (
            git_output(["write-tree"], root)
            if head_relation == "exact"
            else git_output(["rev-parse", f"{head}^{{tree}}"], root)
        )
        if not expected_tree or metadata.get("tree_sha") != expected_tree:
            errors.append("closeout receipt final tracked state is stale")

    artifacts = receipt.get("artifacts")
    if not isinstance(artifacts, dict):
        return errors + ["closeout receipt artifacts are malformed"]
    expected_paths = {
        "phase_receipt": PHASE_RECEIPT.as_posix(),
        "score": ".claude/quality_reports/",
        "findings": ".claude/quality_reports/",
    }
    loaded: dict[str, object] = {}
    for key in ARTIFACT_KEYS:
        artifact = artifacts.get(key)
        if not isinstance(artifact, dict):
            errors.append(f"closeout receipt artifact {key} is missing")
            continue
        path_value = artifact.get("path")
        if not isinstance(path_value, str) or not is_safe_relative_path(path_value):
            errors.append(f"closeout receipt artifact {key} has an unsafe path")
            continue
        if key == "phase_receipt" and path_value != expected_paths[key]:
            errors.append("closeout receipt phase receipt path is invalid")
            continue
        if key in {"score", "findings"} and not path_value.startswith(
            expected_paths[key]
        ):
            errors.append(f"closeout receipt {key} path is outside quality reports")
            continue
        path = root / path_value
        try:
            actual_digest = file_digest(path)
        except ValueError:
            errors.append(f"closeout receipt artifact {key} is missing or unsafe")
            continue
        if artifact.get("sha256") != actual_digest:
            errors.append(f"closeout receipt artifact {key} was tampered with")
            continue
        loaded[key] = path

    phase_path = loaded.get("phase_receipt")
    if isinstance(phase_path, Path):
        try:
            phase_receipt = load_receipt(phase_path)
        except ValueError as error:
            errors.append(f"phase receipt is invalid: {error}")
        else:
            if phase_receipt["mode"] != "phase" or phase_receipt["status"] != "PASS":
                errors.append("phase receipt must be passing phase evidence")
    score_path = loaded.get("score")
    if isinstance(score_path, Path):
        errors.extend(
            report_errors(
                score_path,
                kind="score",
                branch=branch,
                phase=phase,
                head=head,
                head_relation=head_relation,
                expected_base=expected_base,
                root=root,
                require_major=False,
                require_ponytail=False,
                verify_current_content=enforce_final_state,
            )
        )
    findings_path = loaded.get("findings")
    if isinstance(findings_path, Path):
        errors.extend(
            report_errors(
                findings_path,
                kind="findings",
                branch=branch,
                phase=phase,
                head=head,
                head_relation=head_relation,
                expected_base=expected_base,
                root=root,
                require_major=require_major,
                require_ponytail=require_ponytail,
                verify_current_content=enforce_final_state,
            )
        )
    log_path = loaded.get("closeout_log")
    if isinstance(log_path, Path):
        errors.extend(closeout_log_errors(root, phase, log_path))
    return errors


def git_is_ancestor(root: Path, ancestor: str, descendant: str) -> bool:
    """Return whether a report parent is safely reachable from a target ref."""
    try:
        return (
            run_process(
                ["git", "merge-base", "--is-ancestor", ancestor, descendant], root
            ).returncode
            == 0
        )
    except (OSError, subprocess.SubprocessError):
        return False


def report_errors(
    path: Path,
    *,
    kind: str,
    branch: str,
    phase: str,
    head: str,
    head_relation: str,
    expected_base: str,
    root: Path,
    require_major: bool,
    require_ponytail: bool,
    verify_current_content: bool,
) -> list[str]:
    """Validate one exact child report without provider-specific policy."""
    label = f"{kind} report"
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [f"{label} is malformed"]
    if not isinstance(report, dict):
        return [f"{label} must be an object"]
    errors: list[str] = []
    for field, expected in (("branch", branch), ("phase", phase), ("base_ref", "dev")):
        if report.get(field) != expected:
            errors.append(f"{label} {field} does not match closeout receipt")
    report_head = report.get("head_sha")
    if not isinstance(report_head, str) or not report_head:
        errors.append(f"{label} is missing head_sha")
    elif head_relation == "exact" and report_head != head:
        errors.append(f"{label} head_sha is stale")
    elif head_relation == "ancestor" and not git_is_ancestor(root, report_head, head):
        errors.append(f"{label} head_sha is not an ancestor of the pushed ref")
    if report.get("merge_base_sha") != expected_base:
        errors.append(f"{label} merge_base_sha is stale")
    if report.get("dirty") is not False:
        errors.append(f"{label} must record dirty: false")
    if not isinstance(report.get("generated_at"), str):
        errors.append(f"{label} is missing generated_at")
    if not isinstance(report.get("target"), str):
        errors.append(f"{label} is missing target")
    if not isinstance(report.get("changed_files"), list):
        errors.append(f"{label} is missing changed_files")
    if verify_current_content:
        current_hash = content_hash_for(
            root, expected_base, head if head_relation == "ancestor" else ""
        )
        if not current_hash or report.get("content_hash") != current_hash:
            errors.append(f"{label} content_hash is stale")
    if kind == "score":
        score = report.get("score")
        if type(score) is not int or score < 90:
            errors.append("quality score must be >= 90")
        if (
            report.get("tests_passed") is not True
            or report.get("tests_skipped") is True
        ):
            errors.append("quality report test evidence is invalid")
    else:
        counts = report.get("counts")
        if not isinstance(counts, dict) or any(
            type(counts.get(name)) is not int or counts[name] < 0
            for name in ("critical", "major", "minor")
        ):
            errors.append("findings report severity counts are invalid")
        else:
            if counts["critical"] != 0:
                errors.append("findings report has CRITICAL findings")
            if require_major and counts["major"] != 0:
                errors.append("findings report has MAJOR findings")
        if require_ponytail and report.get("ponytail_reviewed") is not True:
            errors.append("this high-risk diff requires a fresh Ponytail review")
    return errors


def content_hash_for(root: Path, merge_base: str, ref: str) -> str:
    """Compute the existing report freshness hash for worktree or pushed ref."""
    try:
        diff = run_process(
            [
                "git",
                "diff",
                "--no-color",
                "--no-ext-diff",
                merge_base,
                *([ref] if ref else []),
            ],
            root,
        )
        if diff.returncode != 0:
            return ""
        hashed = subprocess.run(
            ["git", "hash-object", "--stdin"],
            cwd=root,
            input=diff.stdout,
            text=True,
            capture_output=True,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return hashed.stdout.strip() if hashed.returncode == 0 else ""


def closeout_log_errors(root: Path, phase: str, path: Path) -> list[str]:
    """Keep completed-log and LEARN authority bound to the receipt path."""
    expected = closeout_log_path(root, phase)
    if path.resolve() != expected.resolve():
        return ["closeout receipt log does not match phase frontmatter"]
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ["closeout session log is unreadable"]
    if not re.search(r"^\*\*Status:\*\*[ \t]+COMPLETED\b", text, re.MULTILINE):
        return ["closeout session log is not completed"]
    if "[LEARN] none - no new lessons this session" in text:
        return []
    memory = root / ".claude/MEMORY.md"
    plan = root / ".claude/plans" / f"{phase}.md"
    if (
        memory.is_file()
        and plan.is_file()
        and memory.stat().st_mtime >= plan.stat().st_mtime
    ):
        return []
    return ["LEARN evidence is missing"]


def measure_ruff(root: Path, targets: list[str]) -> dict[str, object]:
    """Adapt the scorer's strict Ruff measurement into a receipt check."""
    measurement = quality_score.measure_ruff(targets, cwd=str(root))
    return check(
        "VFY-RUFF-001",
        measurement.status,
        measurement.detail,
    )


def measure_mypy(root: Path, targets: list[str]) -> dict[str, object]:
    """Adapt the scorer's strict mypy measurement into a receipt check."""
    measurement = quality_score.measure_mypy(targets, cwd=str(root))
    return check("VFY-MYPY-001", measurement.status, measurement.detail)


def measure_pytest(root: Path) -> dict[str, object]:
    """Adapt the scorer's strict pytest measurement into a receipt check."""
    measurement = quality_score.measure_pytest(cwd=str(root))
    return check("VFY-PYTEST-001", measurement.status, measurement.detail)


def generation_check(root: Path) -> dict[str, object]:
    """Require the generated verifier and its measurement module to match source."""
    pairs = [
        (root / f"shared/scripts/{name}", root / f".claude/scripts/{name}")
        for name in ("verify.py", "quality_score.py")
    ]
    if pairs[0][0].is_file():
        if any(
            not source.is_file() or not generated.is_file()
            for source, generated in pairs
        ):
            return check(
                "VFY-GEN-001", "UNVERIFIED", "generated verifier runtime is missing"
            )
        status = (
            "PASS"
            if all(
                source.read_bytes() == generated.read_bytes()
                for source, generated in pairs
            )
            else "FAIL"
        )
        return check(
            "VFY-GEN-001",
            status,
            "generated verifier runtime matches source"
            if status == "PASS"
            else "generated verifier runtime drifted from source",
        )
    return check(
        "VFY-GEN-001",
        "PASS" if Path(__file__).is_file() else "UNVERIFIED",
        "consumer verifier is installed",
    )


def canonical_json(value: object) -> str:
    """Serialize verification evidence with stable key and item ordering."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def file_digest(path: Path) -> str:
    """Return the SHA-256 digest for one regular closeout artifact."""
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"artifact is not a regular file: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_artifact(root: Path, path: Path) -> dict[str, str]:
    """Bind one existing artifact by safe repository-relative path and bytes."""
    try:
        relative = path.resolve(strict=True).relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as error:
        raise ValueError(f"artifact is outside repository: {path}") from error
    return {"path": relative.as_posix(), "sha256": file_digest(path)}


def latest_report(root: Path, pattern: str, branch: str, phase: str) -> Path:
    """Choose a report once at receipt creation; gates never rediscover it."""
    candidates: list[tuple[str, Path]] = []
    for candidate in (root / ".claude/quality_reports").glob(pattern):
        try:
            report = json.loads(candidate.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(report, dict):
            continue
        generated_at = report.get("generated_at")
        if (
            report.get("branch") == branch
            and report.get("phase") == phase
            and isinstance(generated_at, str)
        ):
            candidates.append((generated_at, candidate))
    if not candidates:
        raise ValueError(f"no matching {pattern} report for phase {phase}")
    return max(candidates, key=lambda item: item[0])[1]


def closeout_log_path(root: Path, phase: str) -> Path:
    """Return the exact closeout log selected by current phase frontmatter."""
    plan = root / ".claude/plans" / f"{phase}.md"
    try:
        text = plan.read_text(encoding="utf-8")
    except OSError as error:
        raise ValueError(f"missing phase plan: {plan}") from error
    match = re.search(
        r"^closeout_session_log:[ \t]*([^\s#]+)[ \t]*$", text, re.MULTILINE
    )
    if not match or not is_safe_relative_path(match.group(1)):
        raise ValueError("phase plan has no safe closeout_session_log")
    return root / match.group(1)


def closeout_artifacts(root: Path, metadata: dict[str, object]) -> dict[str, object]:
    """Capture the precise evidence set a completed-phase gate consumes."""
    branch = metadata.get("branch")
    phase = metadata.get("phase")
    if (
        not isinstance(branch, str)
        or not branch
        or not isinstance(phase, str)
        or not phase
    ):
        raise ValueError("closeout receipt needs branch and phase metadata")
    return {
        "phase_receipt": relative_artifact(root, root / PHASE_RECEIPT),
        "score": relative_artifact(
            root, latest_report(root, "score-*.json", branch, phase)
        ),
        "findings": relative_artifact(
            root, latest_report(root, "findings-*.json", branch, phase)
        ),
        "closeout_log": relative_artifact(root, closeout_log_path(root, phase)),
    }


def build_receipt(
    mode: str,
    checks: list[dict[str, object]],
    metadata: dict[str, object],
    artifacts: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build and validate one complete receipt."""
    receipt = {
        "schema_version": SCHEMA_VERSION,
        "mode": mode,
        "status": aggregate_status(checks),
        "checks": checks,
        "metadata": metadata,
    }
    if mode == "closeout":
        receipt["artifacts"] = artifacts if artifacts is not None else {}
    validate_receipt(receipt)
    return receipt


def load_receipt(path: Path) -> dict[str, object]:
    """Read a strictly validated persisted receipt."""
    try:
        return validate_receipt(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(f"invalid receipt {path}: {error}") from error


def not_applicable(check_id: str, reason: str) -> dict[str, object]:
    """Record a mode-defined, rather than agent-selected, inapplicable check."""
    return check(check_id, "NOT_APPLICABLE", reason, applicable=False)


def metadata_paths(metadata: dict[str, object], field: str) -> list[str]:
    """Return one validated path list stored in local receipt metadata."""
    value = metadata.get(field)
    if not isinstance(value, list) or not all(isinstance(path, str) for path in value):
        raise ValueError(f"metadata field {field} must be a list of paths")
    return value


def metadata_is_bound(metadata: dict[str, object]) -> bool:
    """Return whether Git supplied the commit/base pair freshness requires."""
    return bool(
        metadata.get("head_sha")
        and metadata.get("merge_base_sha")
        and metadata.get("path_discovery_ok") is True
    )


def phase_checks(root: Path, metadata: dict[str, object]) -> list[dict[str, object]]:
    """Run the complete Phase-A measurement group."""
    categories = sorted(
        {classify_path(path) for path in metadata_paths(metadata, "changed_paths")}
    )
    freshness_status = "PASS" if metadata_is_bound(metadata) else "UNVERIFIED"
    checks = [
        check("VFY-STATUS-001", "PASS", "receipt schema is versioned and strict"),
        check("VFY-STATUS-002", "PASS", "phase check applicability is deterministic"),
        measure_ruff(root, ["shared", "scripts", "tests"]),
        measure_mypy(root, ["shared", "scripts", "tests"]),
        measure_pytest(root),
        check(
            "VFY-FRESH-001",
            freshness_status,
            "phase evidence captured relevant state"
            if freshness_status == "PASS"
            else "Git base state was unavailable",
        ),
        check(
            "VFY-FRESH-002",
            freshness_status,
            "phase evidence captured whole tracked state"
            if freshness_status == "PASS"
            else "Git base state was unavailable",
        ),
        check(
            "VFY-CONTROL-001",
            "PASS",
            f"classified paths: {', '.join(categories) or 'none'}",
        ),
        generation_check(root),
        check("VFY-DETERMINISM-001", "PASS", "receipt serialization is canonical"),
        not_applicable(
            "VFY-RECEIPT-001", "phase creates evidence; it does not reuse it"
        ),
    ]
    return checks


def fast_checks(root: Path, metadata: dict[str, object]) -> list[dict[str, object]]:
    """Run cheap changed-Python feedback without establishing authority."""
    python_paths = [
        path
        for path in metadata_paths(metadata, "relevant_paths")
        if Path(path).suffix == ".py"
    ]
    ruff = (
        measure_ruff(root, python_paths)
        if python_paths
        else not_applicable("VFY-RUFF-001", "no changed Python paths")
    )
    categories = sorted(
        {classify_path(path) for path in metadata_paths(metadata, "changed_paths")}
    )
    return [
        check("VFY-STATUS-001", "PASS", "receipt schema is versioned and strict"),
        check("VFY-STATUS-002", "PASS", "fast mode has fixed applicability"),
        ruff,
        not_applicable("VFY-MYPY-001", "fast mode does not run global typing"),
        not_applicable("VFY-PYTEST-001", "fast mode does not run the full test suite"),
        not_applicable(
            "VFY-FRESH-001", "fast mode never establishes reusable evidence"
        ),
        not_applicable(
            "VFY-FRESH-002", "fast mode never establishes closeout authority"
        ),
        check(
            "VFY-CONTROL-001",
            "PASS",
            f"classified paths: {', '.join(categories) or 'none'}",
        ),
        not_applicable(
            "VFY-GEN-001", "fast mode does not validate generated ownership"
        ),
        check("VFY-DETERMINISM-001", "PASS", "receipt serialization is canonical"),
        not_applicable("VFY-RECEIPT-001", "fast mode does not consume evidence"),
    ]


def closeout_checks(root: Path, metadata: dict[str, object]) -> list[dict[str, object]]:
    """Reuse validated phase evidence and bind a final full-state receipt."""
    phase_path = root / PHASE_RECEIPT
    try:
        phase = load_receipt(phase_path)
    except ValueError as error:
        receipt_check = check("VFY-RECEIPT-001", "FAIL", str(error))
        phase_metadata: dict[str, object] = {}
    else:
        phase_metadata = phase["metadata"]  # type: ignore[assignment]
        status = (
            "PASS" if phase["mode"] == "phase" and phase["status"] == "PASS" else "FAIL"
        )
        receipt_check = check(
            "VFY-RECEIPT-001",
            status,
            "reused successful phase receipt"
            if status == "PASS"
            else "phase receipt was not successful",
        )
    if not metadata_is_bound(metadata) or not metadata_is_bound(phase_metadata):
        fresh_status = "UNVERIFIED"
    elif (
        all(
            phase_metadata.get(field) == metadata.get(field)
            for field in ("base_ref", "branch", "head_sha", "merge_base_sha")
        )
        and phase_metadata.get("content_hash") == metadata["content_hash"]
    ):
        fresh_status = "PASS"
    else:
        fresh_status = "FAIL"
    return [
        check("VFY-STATUS-001", "PASS", "receipt schema is versioned and strict"),
        check(
            "VFY-STATUS-002", "PASS", "closeout check applicability is deterministic"
        ),
        not_applicable("VFY-RUFF-001", "closeout reuses phase Ruff evidence"),
        not_applicable("VFY-MYPY-001", "closeout reuses phase mypy evidence"),
        not_applicable("VFY-PYTEST-001", "closeout reuses phase pytest evidence"),
        check(
            "VFY-FRESH-001",
            fresh_status,
            "phase evidence matches relevant state"
            if fresh_status == "PASS"
            else (
                "relevant code evidence is stale"
                if fresh_status == "FAIL"
                else "Git base state was unavailable"
            ),
        ),
        check(
            "VFY-FRESH-002",
            "PASS" if metadata_is_bound(metadata) else "UNVERIFIED",
            "closeout receipt binds whole tracked state"
            if metadata_is_bound(metadata)
            else "Git base state was unavailable",
        ),
        check("VFY-CONTROL-001", "PASS", "control-plane paths are evidence-relevant"),
        not_applicable("VFY-GEN-001", "closeout reuses phase generation evidence"),
        check("VFY-DETERMINISM-001", "PASS", "receipt serialization is canonical"),
        receipt_check,
    ]


def receipt_path(root: Path, mode: str) -> Path:
    """Return the only deterministic persistence location for a receipt mode."""
    return root / (PHASE_RECEIPT if mode == "phase" else CLOSEOUT_RECEIPT)


def parse_args() -> argparse.Namespace:
    """Parse the intentionally small public verifier interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=sorted(MODES | {"gate"}))
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument("--persist", action="store_true")
    parser.add_argument("--base-ref", default="dev")
    parser.add_argument("--phase", default="")
    parser.add_argument("--branch", default="")
    parser.add_argument("--head", default="")
    parser.add_argument(
        "--head-relation", choices=("exact", "ancestor"), default="exact"
    )
    parser.add_argument("--require-major", action="store_true")
    parser.add_argument("--require-ponytail", action="store_true")
    parser.add_argument("--enforce-final-state", action="store_true")
    return parser.parse_args()


def main() -> int:
    """Run one verifier mode and optionally persist its non-authoritative receipt."""
    args = parse_args()
    root = Path.cwd()
    if args.mode == "gate":
        errors = gate_receipt_errors(
            root,
            branch=args.branch,
            phase=args.phase,
            head=args.head,
            head_relation=args.head_relation,
            require_major=args.require_major,
            require_ponytail=args.require_ponytail,
            enforce_final_state=args.enforce_final_state,
        )
        print(json.dumps({"errors": errors}, separators=(",", ":")))
        return 0 if not errors else 1
    metadata = state_metadata(root, args.base_ref, args.phase)
    if args.mode == "fast":
        checks = fast_checks(root, metadata)
    elif args.mode == "phase":
        checks = phase_checks(root, metadata)
    else:
        checks = closeout_checks(root, metadata)
    artifacts = closeout_artifacts(root, metadata) if args.mode == "closeout" else None
    receipt = build_receipt(args.mode, checks, metadata, artifacts)
    if args.persist:
        if args.mode == "fast":
            print("fast mode never persists evidence", file=sys.stderr)
            return 2
        path = receipt_path(root, args.mode)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(canonical_json(receipt) + "\n", encoding="utf-8")
    if args.format == "json":
        print(canonical_json(receipt))
    else:
        print(f"{args.mode}: {receipt['status']}")
        for item in checks:
            print(f"{item['id']}: {item['status']} - {item['summary']}")
    return 0 if receipt["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
