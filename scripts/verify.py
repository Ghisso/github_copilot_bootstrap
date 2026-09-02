#!/usr/bin/env python3
"""Fail-closed deterministic verification evidence and gate receipts.

The deterministic command owns verification evidence and emits the authoritative
per-phase closeout receipt consumed by lifecycle gates. ``fast`` is focused
feedback, ``phase`` persists reusable evidence, and ``closeout`` proves that
phase evidence remains fresh before binding the final state and child artifacts.

Usage:
    uv run python .claude/scripts/verify.py fast --format json
    uv run python .claude/scripts/verify.py phase --format json --persist
    uv run python .claude/scripts/verify.py closeout --format json --persist
"""

from __future__ import annotations

import argparse
import configparser
import hashlib
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True

_VERIFIER_PATH = Path(__file__).resolve()
_AUTHORING_VERIFIER_PATH = (
    _VERIFIER_PATH.parents[2] / "shared" / "scripts" / "verify.py"
)
_OWNERSHIP_PATH = (
    _VERIFIER_PATH.parents[2] / "scripts" / "runtime_ownership.py"
    if _VERIFIER_PATH == _AUTHORING_VERIFIER_PATH
    else _VERIFIER_PATH.with_name("runtime_ownership.py")
)
_ownership_spec = importlib.util.spec_from_file_location(
    "runtime_ownership", _OWNERSHIP_PATH
)
if _ownership_spec is None or _ownership_spec.loader is None:
    raise ImportError(f"missing runtime ownership authority: {_OWNERSHIP_PATH}")
_ownership = importlib.util.module_from_spec(_ownership_spec)
_ownership_spec.loader.exec_module(_ownership)
owned_bootstrap_root_paths = _ownership.bootstrap_root_paths
install_mode_from_manifest = _ownership.install_mode_from_manifest


SCHEMA_VERSION = 4
CHECK_STATES = frozenset({"PASS", "FAIL", "UNVERIFIED", "NOT_APPLICABLE"})
MODES = frozenset({"fast", "phase", "closeout"})
CHECK_IDS = (
    "VFY-RUFF-001",
    "VFY-MYPY-001",
    "VFY-PYTEST-001",
    "VFY-FRESH-001",
    "VFY-FRESH-002",
    "VFY-GEN-001",
    "VFY-RECEIPT-001",
)
COMMAND_TIMEOUT_SECONDS = 180
PHASE_RECEIPT = Path(".claude/quality_reports/verification-phase-{phase}.json")
CLOSEOUT_RECEIPT = Path(".claude/quality_reports/verification-closeout-{phase}.json")
ARTIFACT_KEYS = (
    "phase_receipt",
    "findings",
    "closeout_log",
    "documentation",
)
AUTHORITATIVE_RECEIPT_FIELDS = {
    "schema_version",
    "mode",
    "status",
    "checks",
    "metadata",
    "artifacts",
}
RECEIPT_EXTENSIONS_FIELD = "extensions"
PHASE_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
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
AUTHORING_RUNTIME_MARKERS = (
    "shared/scripts/verify.py",
    "shared/policies/workspace.instructions.md",
    "scripts/generate_targets.py",
    "scripts/runtime_ownership.py",
)
MYPY_CONFIG_FILES = ("mypy.ini", ".mypy.ini", "pyproject.toml", "setup.cfg")
MYPY_SCOPE_OPTIONS = ("files", "packages", "modules")
CONTROL_PLANE_PROVENANCE_SCHEMA_VERSION = 1
CONTROL_PLANE_PROVENANCE_FIELDS = {
    "schema_version",
    "nested_head",
    "runtime_fingerprint",
    "tracked_state_fingerprint",
    "big_plan_digest",
    "small_plan_digest",
}
NESTED_MUTABLE_STATE_ROOTS = frozenset(
    {
        "MEMORY.md",
        "plans",
        "explorations",
        "session_logs",
        "quality_reports",
        ".cache",
        "settings.local.json",
    }
)
NESTED_MUTABLE_STATE_PATHS = frozenset({"instructions/project-context.instructions.md"})


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
    metadata_fields = {
        "generated_at",
        "base_ref",
        "branch",
        "head_sha",
        "merge_base_sha",
        "tree_sha",
        "phase",
        "content_hash",
        "tracked_state_hash",
        "changed_paths",
        "relevant_paths",
        "path_discovery_ok",
        "control_plane_provenance",
    }
    if set(metadata) != metadata_fields:
        raise ValueError("receipt metadata has unknown or missing authoritative fields")
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
    if not has_control_plane_provenance(metadata):
        raise ValueError("receipt metadata control-plane provenance is invalid")
    if not is_utc_timestamp(metadata["generated_at"]):
        raise ValueError("receipt metadata generated_at must be a UTC timestamp")
    if receipt["mode"] in {"phase", "closeout"}:
        for field in (
            "generated_at",
            "branch",
            "head_sha",
            "merge_base_sha",
            "tree_sha",
            "phase",
            "content_hash",
            "tracked_state_hash",
        ):
            if not metadata[field]:
                raise ValueError(f"receipt metadata {field} must be non-empty")
        if metadata["base_ref"] != "dev" or not PHASE_SLUG.fullmatch(metadata["phase"]):
            raise ValueError("receipt metadata base_ref or phase is invalid")
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
        if key == "documentation":
            validate_documentation_evidence(artifact)
            continue
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


def validate_documentation_evidence(evidence: object) -> None:
    """Validate the compact canonical documentation disposition."""
    if not isinstance(evidence, dict) or set(evidence) not in (
        {"status", "reason"},
        {"status", "paths"},
    ):
        raise ValueError("closeout documentation evidence is malformed")
    status = evidence.get("status")
    if status == "NOT_APPLICABLE":
        if (
            not isinstance(evidence.get("reason"), str)
            or not evidence["reason"].strip()
        ):
            raise ValueError("closeout documentation N/A needs a reason")
    elif status == "UPDATED":
        paths = evidence.get("paths")
        if (
            not isinstance(paths, list)
            or not paths
            or not all(
                isinstance(path, str) and is_safe_relative_path(path) for path in paths
            )
        ):
            raise ValueError("closeout documentation update paths are invalid")
    else:
        raise ValueError("closeout documentation status is unknown")


def is_utc_timestamp(value: object) -> bool:
    """Return whether a value is a real canonical UTC second timestamp."""
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value
    ):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return False
    return True


def is_safe_relative_path(value: str) -> bool:
    """Return whether a receipt reference stays inside the repository root."""
    path = Path(value)
    return bool(value and not path.is_absolute() and ".." not in path.parts)


def confined_path(root: Path, value: str, *, regular: bool = False) -> Path:
    """Resolve an existing repo path while rejecting symlink traversal."""
    root = root.resolve(strict=True)
    raw = Path(value)
    candidate = raw if raw.is_absolute() else root / raw
    try:
        relative = candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("path is outside repository") from error
    if ".." in relative.parts:
        raise ValueError("path traversal is not allowed")
    current = root
    for part in relative.parts:
        current /= part
        if current.is_symlink():
            raise ValueError("symlink path components are not allowed")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (OSError, ValueError) as error:
        raise ValueError("path is missing or outside repository") from error
    if regular and (not resolved.is_file() or resolved.is_symlink()):
        raise ValueError("path is not a regular file")
    return resolved


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


def nested_runtime_paths(root: Path) -> list[str] | None:
    """Return static nested runtime paths, excluding mutable consumer evidence."""
    nested = root / ".claude"
    if not nested.is_dir() or nested.is_symlink():
        return None
    paths: list[str] = []
    try:
        for path in nested.rglob("*"):
            relative = path.relative_to(nested)
            if not is_relevant_nested_path(relative.as_posix()):
                continue
            if path.is_file() or path.is_symlink():
                paths.append(relative.as_posix())
    except OSError:
        return None
    return sorted(paths)


def manifest_bootstrap_root_paths(root: Path) -> tuple[str, ...] | None:
    """Return the finite installer-owned root adapters from its manifest."""
    manifest = root / ".claude" / "bootstrap-ownership.env"
    try:
        info = manifest.lstat()
        if not stat.S_ISREG(info.st_mode) or manifest.is_symlink():
            return None
        text = manifest.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None

    mode = install_mode_from_manifest(text)
    return owned_bootstrap_root_paths(mode) if mode is not None else None


def confined_adapter_path(root: Path, relative: str) -> Path | None:
    """Return one adapter path only when every component is a non-symlink."""
    if not is_safe_relative_path(relative):
        return None
    candidate = root
    try:
        for component in Path(relative).parts:
            candidate /= component
            if candidate.is_symlink():
                return None
            candidate.lstat()
    except OSError:
        return None
    return candidate


def regular_tree_fingerprint(path: Path) -> bytes | None:
    """Fingerprint a regular root adapter tree while rejecting links and special files."""
    try:
        info = path.lstat()
        if path.is_symlink():
            return None
        digest = hashlib.sha256()
        if stat.S_ISREG(info.st_mode):
            return b"file\0" + hashlib.sha256(path.read_bytes()).digest()
        if not stat.S_ISDIR(info.st_mode):
            return None
        digest.update(b"directory\0")
        for descendant in sorted(path.rglob("*")):
            relative = descendant.relative_to(path).as_posix().encode("utf-8")
            child_info = descendant.lstat()
            if descendant.is_symlink():
                return None
            if stat.S_ISDIR(child_info.st_mode):
                digest.update(b"directory\0" + relative + b"\0")
            elif stat.S_ISREG(child_info.st_mode):
                digest.update(
                    b"file\0"
                    + relative
                    + b"\0"
                    + hashlib.sha256(descendant.read_bytes()).digest()
                )
            else:
                return None
        return b"directory\0" + digest.digest()
    except OSError:
        return None


def bootstrap_root_fingerprint(root: Path) -> str:
    """Bind each installer-owned live adapter to its canonical nested mirror."""
    paths = manifest_bootstrap_root_paths(root)
    if paths is None:
        return ""
    digest = hashlib.sha256()
    for relative in paths:
        live_path = confined_adapter_path(root, relative)
        mirror_path = confined_adapter_path(root, f".claude/bootstrap-root/{relative}")
        if live_path is None or mirror_path is None:
            return ""
        live = regular_tree_fingerprint(live_path)
        mirror = regular_tree_fingerprint(mirror_path)
        if live is None or mirror is None or live != mirror:
            return ""
        digest.update(relative.encode("utf-8") + b"\0" + live + b"\0")
    return digest.hexdigest()


def is_relevant_nested_path(
    path: str, active_plan_paths: frozenset[str] = frozenset()
) -> bool:
    """Return whether one nested path governs runtime behavior rather than evidence."""
    relative = Path(path)
    return bool(
        relative.parts
        and ".git" not in relative.parts
        and (
            relative.as_posix() in active_plan_paths
            or (
                relative.parts[0] not in NESTED_MUTABLE_STATE_ROOTS
                and relative.as_posix() not in NESTED_MUTABLE_STATE_PATHS
            )
        )
    )


def nested_git_head(root: Path) -> str:
    """Return the nested AI-state HEAD only when it is available."""
    nested = root / ".claude"
    if not nested.is_dir() or nested.is_symlink():
        return ""
    return git_output(["-C", str(nested), "rev-parse", "--verify", "HEAD"], root)


def nested_tracked_state_fingerprint(
    root: Path, active_plan_paths: frozenset[str]
) -> str:
    """Hash relevant nested Git index and dirty state without mutable evidence."""
    nested = root / ".claude"
    if not nested.is_dir() or nested.is_symlink():
        return ""
    try:
        index = run_process(["git", "ls-files", "--stage", "-z"], nested)
        status = run_process(
            ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            nested,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    if index.returncode != 0 or status.returncode != 0:
        return ""
    digest = hashlib.sha256()
    for record in index.stdout.split("\0"):
        _, separator, path = record.partition("\t")
        if separator and is_relevant_nested_path(path, active_plan_paths):
            digest.update(b"index\0" + record.encode("utf-8") + b"\0")
    records = status.stdout.split("\0")
    position = 0
    while position < len(records):
        record = records[position]
        position += 1
        if not record:
            continue
        state, separator, path = record[:2], record[2:3], record[3:]
        paths = [path] if separator == " " else []
        if "R" in state or "C" in state:
            if position >= len(records):
                return ""
            paths.append(records[position])
            position += 1
        if any(
            is_relevant_nested_path(candidate, active_plan_paths) for candidate in paths
        ):
            digest.update(b"status\0" + record.encode("utf-8") + b"\0")
            for candidate in paths[1:]:
                digest.update(candidate.encode("utf-8") + b"\0")
    return digest.hexdigest()


def digest_file(path: Path) -> str:
    """Return a SHA-256 file digest, or an empty value when it is unreadable."""
    try:
        if not path.is_file() or path.is_symlink():
            return ""
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""


def active_big_plan_path(root: Path, branch: str) -> Path | None:
    """Return the active implementation plan path when the branch names one."""
    if not branch.endswith("_implementation"):
        return None
    slug = branch.removesuffix("_implementation")
    if not PHASE_SLUG.fullmatch(slug):
        return None
    return root / ".claude/plans" / f"{slug}.md"


def active_plan_paths(root: Path, branch: str, phase: str) -> frozenset[str]:
    """Return every declared active-plan path, including future phase plans."""
    big_plan = active_big_plan_path(root, branch)
    if big_plan is None:
        return frozenset()
    paths = {big_plan.relative_to(root / ".claude").as_posix()}
    if PHASE_SLUG.fullmatch(phase):
        paths.add(f"plans/{phase}.md")
    try:
        match = re.match(
            r"\A---\n(?P<body>.*?)\n---",
            big_plan.read_text(encoding="utf-8"),
            re.DOTALL,
        )
    except OSError:
        return frozenset(paths)
    if match is None:
        return frozenset(paths)
    phases = frontmatter_phases(match.group("body"))
    if phases is not None:
        paths.update(f"plans/{item}.md" for item in phases)
    return frozenset(paths)


def control_plane_provenance(root: Path, branch: str, phase: str) -> dict[str, object]:
    """Bind the nested runtime and active plans without hashing mutable evidence."""
    active_paths = active_plan_paths(root, branch, phase)
    runtime_paths = nested_runtime_paths(root)
    nested_fingerprint = (
        hash_paths(root / ".claude", runtime_paths) if runtime_paths is not None else ""
    )
    root_fingerprint = bootstrap_root_fingerprint(root)
    runtime_fingerprint = (
        hashlib.sha256(
            b"nested\0"
            + nested_fingerprint.encode("ascii")
            + b"\0root\0"
            + root_fingerprint.encode("ascii")
        ).hexdigest()
        if nested_fingerprint and root_fingerprint
        else ""
    )
    nested_head = nested_git_head(root)
    big_plan = active_big_plan_path(root, branch)
    small_plan = (
        root / ".claude/plans" / f"{phase}.md"
        if big_plan is not None and PHASE_SLUG.fullmatch(phase)
        else None
    )
    tracked_state_fingerprint = nested_tracked_state_fingerprint(root, active_paths)
    return {
        "schema_version": CONTROL_PLANE_PROVENANCE_SCHEMA_VERSION,
        "nested_head": nested_head,
        "runtime_fingerprint": runtime_fingerprint,
        "tracked_state_fingerprint": tracked_state_fingerprint,
        "big_plan_digest": digest_file(big_plan) if big_plan is not None else "",
        "small_plan_digest": digest_file(small_plan) if small_plan is not None else "",
    }


def has_control_plane_provenance(metadata: dict[str, object]) -> bool:
    """Return whether required nested state was recorded for this branch."""
    provenance = metadata.get("control_plane_provenance")
    if (
        not isinstance(provenance, dict)
        or set(provenance) != CONTROL_PLANE_PROVENANCE_FIELDS
    ):
        return False
    if provenance.get("schema_version") != CONTROL_PLANE_PROVENANCE_SCHEMA_VERSION:
        return False
    nested_head = provenance.get("nested_head")
    if not isinstance(nested_head, str) or not re.fullmatch(
        r"[0-9a-f]{40,64}", nested_head
    ):
        return False
    for field in ("runtime_fingerprint", "tracked_state_fingerprint"):
        if not isinstance(provenance.get(field), str) or not re.fullmatch(
            r"[0-9a-f]{64}", str(provenance[field])
        ):
            return False
    branch = metadata.get("branch")
    if isinstance(branch, str) and branch.endswith("_implementation"):
        return all(
            isinstance(provenance.get(field), str)
            and re.fullmatch(r"[0-9a-f]{64}", str(provenance[field]))
            for field in ("big_plan_digest", "small_plan_digest")
        )
    return all(
        isinstance(provenance.get(field), str)
        for field in ("big_plan_digest", "small_plan_digest")
    )


def control_plane_provenance_matches(
    recorded: dict[str, object], current: dict[str, object]
) -> bool:
    """Compare governing bytes while allowing evidence-only nested HEAD advances."""
    if not has_control_plane_provenance(recorded) or not has_control_plane_provenance(
        current
    ):
        return False
    recorded_provenance = recorded["control_plane_provenance"]
    current_provenance = current["control_plane_provenance"]
    assert isinstance(recorded_provenance, dict) and isinstance(
        current_provenance, dict
    )
    return all(
        recorded_provenance.get(field) == current_provenance.get(field)
        for field in CONTROL_PLANE_PROVENANCE_FIELDS - {"nested_head"}
    )


def indexed_nested_file(root: Path, relative: str) -> bytes | None:
    """Read one tracked nested-state file from the Git index."""
    nested = root / ".claude"
    if (
        not nested.is_dir()
        or nested.is_symlink()
        or not is_safe_relative_path(relative)
    ):
        return None
    try:
        result = subprocess.run(
            ["git", "show", f":{relative}"],
            cwd=nested,
            capture_output=True,
            check=False,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def nested_revision_file(root: Path, revision: str, relative: str) -> bytes | None:
    """Read one nested-state file from a recorded immutable Git revision."""
    nested = root / ".claude"
    if (
        not nested.is_dir()
        or nested.is_symlink()
        or not re.fullmatch(r"[0-9a-f]{40,64}", revision)
        or not is_safe_relative_path(relative)
    ):
        return None
    try:
        result = subprocess.run(
            ["git", "show", f"{revision}:{relative}"],
            cwd=nested,
            capture_output=True,
            check=False,
            timeout=COMMAND_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def relevant_nested_status_changes(
    root: Path, active_plan_paths: frozenset[str]
) -> list[tuple[str, list[str]]] | None:
    """Return only dirty nested state that contributes to provenance."""
    nested = root / ".claude"
    try:
        status = run_process(
            ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
            nested,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if status.returncode != 0:
        return None
    changes: list[tuple[str, list[str]]] = []
    records = status.stdout.split("\0")
    position = 0
    while position < len(records):
        record = records[position]
        position += 1
        if not record:
            continue
        state, separator, path = record[:2], record[2:3], record[3:]
        paths = [path] if separator == " " else []
        if "R" in state or "C" in state:
            if position >= len(records):
                return None
            paths.append(records[position])
            position += 1
        relevant = [
            candidate
            for candidate in paths
            if is_relevant_nested_path(candidate, active_plan_paths)
        ]
        if relevant:
            changes.append((state, relevant))
    return changes


def terminal_big_plan_bytes(indexed: bytes, phase: str) -> bytes | None:
    """Return the sole final-plan mutation the post-commit hook may make."""
    try:
        text = indexed.decode("utf-8")
    except UnicodeDecodeError:
        return None
    frontmatter = re.match(r"\A---\n(?P<body>.*?)\n---", text, re.DOTALL)
    if frontmatter is None:
        return None
    body = frontmatter.group("body")

    def replace_scalar(key: str, expected: str, replacement: str) -> str | None:
        pattern = re.compile(
            rf"^{key}:[ \t]*(?P<value>[^\r\n#]*?)[ \t]*$", re.MULTILINE
        )
        matches = list(pattern.finditer(body))
        if len(matches) != 1 or matches[0].group("value").strip() != expected:
            return None
        match = matches[0]
        return body[: match.start()] + f"{key}: {replacement}" + body[match.end() :]

    completed = replace_scalar("status", "in-progress", "complete")
    if completed is None:
        return None
    original_body = body
    body = completed
    current_pattern = re.compile(
        r"^current_phase:[ \t]*(?P<value>[^\r\n#]*?)[ \t]*$", re.MULTILINE
    )
    matches = list(current_pattern.finditer(body))
    if len(matches) != 1 or matches[0].group("value").strip() != phase:
        return None
    match = matches[0]
    body = body[: match.start()] + "current_phase: " + body[match.end() :]
    phases = frontmatter_phases(original_body)
    if phases is None or phase not in phases:
        return None
    return ("---\n" + body + "\n---" + text[frontmatter.end() :]).encode("utf-8")


def frontmatter_phases(frontmatter: str) -> list[str] | None:
    """Read one complete, unambiguous ``phases:`` list from frontmatter."""
    phases: list[str] = []
    capture = False
    found = False
    for line in frontmatter.splitlines():
        if re.fullmatch(r"phases:[ \t]*", line):
            if found:
                return None
            found = True
            capture = True
            continue
        if not capture:
            continue
        item = re.fullmatch(r"[ \t]*-[ \t]*([^\s#]+)[ \t]*", line)
        if item is not None:
            candidate = item.group(1)
            if not PHASE_SLUG.fullmatch(candidate) or candidate in phases:
                return None
            phases.append(candidate)
            continue
        if re.fullmatch(r"[ \t]*(?:#.*)?", line):
            continue
        if re.fullmatch(r"[A-Za-z0-9_.-]+[ \t]*:.*", line):
            break
        return None
    return phases if found and phases else None


def terminal_plan_paths(source: bytes, relative: str) -> frozenset[str] | None:
    """Return the complete active plan set only for valid terminal frontmatter."""
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError:
        return None
    frontmatter = re.match(r"\A---\n(?P<body>.*?)\n---", text, re.DOTALL)
    if frontmatter is None:
        return None
    phases = frontmatter_phases(frontmatter.group("body"))
    if phases is None:
        return None
    return frozenset({relative, *(f"plans/{item}.md" for item in phases)})


def terminal_later_phases(source: bytes, phase: str) -> list[str] | None:
    """Return only cancelled phases a terminal hook may skip after ``phase``."""
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError:
        return None
    frontmatter = re.match(r"\A---\n(?P<body>.*?)\n---", text, re.DOTALL)
    if frontmatter is None:
        return None
    phases = frontmatter_phases(frontmatter.group("body"))
    return (
        phases[phases.index(phase) + 1 :]
        if phases is not None and phase in phases
        else None
    )


def small_plan_frontmatter(source: bytes) -> dict[str, str] | None:
    """Parse a small plan's scalar frontmatter without permissive YAML coercion."""
    try:
        text = source.decode("utf-8")
    except UnicodeDecodeError:
        return None
    frontmatter = re.match(r"\A---\n(?P<body>.*?)\n---", text, re.DOTALL)
    if frontmatter is None:
        return None
    values: dict[str, str] = {}
    for line in frontmatter.group("body").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        match = re.fullmatch(r"([A-Za-z_]+):[ \t]*([^\r\n#]*?)[ \t]*", line)
        if match is None:
            return None
        key, value = match.groups()
        if key in values:
            return None
        values[key] = value.strip()
    return values


def is_cancelled_small_plan(
    root: Path, source: bytes, phase: str, parent_plan: str
) -> bool:
    """Return whether an identified later small plan is terminally cancelled."""
    values = small_plan_frontmatter(source)
    if not (
        values
        and values.get("name") == phase
        and values.get("type") == "small-plan"
        and values.get("parent_plan") == parent_plan
        and values.get("status") == "cancelled"
        and re.fullmatch(r"[0-9]+", values.get("phase_index", ""))
        and is_utc_timestamp(values.get("cancelled_at"))
    ):
        return False
    reason = values.get("cancelled_reason", "").strip()
    evidence = values.get("cancelled_evidence", "")
    if (
        not reason
        or reason in {"''", '""'}
        or reason.startswith(("[", "{", "- ", "#"))
        or not is_safe_relative_path(evidence)
    ):
        return False
    try:
        return bool(
            re.search(
                r"^\*\*Status:\*\*[ \t]+CANCELLED\b",
                confined_path(root, evidence, regular=True).read_text(encoding="utf-8"),
                re.MULTILINE,
            )
        )
    except (OSError, UnicodeError, ValueError):
        return False


def is_complete_small_plan(source: bytes, phase: str, parent_plan: str) -> bool:
    """Return whether the authoritative current small plan is complete and valid."""
    values = small_plan_frontmatter(source)
    return (
        values is not None
        and values.get("name") == phase
        and values.get("type") == "small-plan"
        and values.get("parent_plan") == parent_plan
        and values.get("status") == "complete"
        and bool(re.fullmatch(r"[0-9]+", values.get("phase_index", "")))
        and bool(values.get("closeout_session_log"))
        and is_safe_relative_path(values["closeout_session_log"])
    )


def terminal_current_small_plan_matches(
    root: Path, phase: str, parent_plan: str, recorded: dict[str, object], source: bytes
) -> bool:
    """Require the current completed small plan to be unchanged after receipt authority."""
    relative = f"plans/{phase}.md"
    if hashlib.sha256(source).hexdigest() != recorded.get(
        "small_plan_digest"
    ) or not is_complete_small_plan(source, phase, parent_plan):
        return False
    indexed = indexed_nested_file(root, relative)
    plan = root / ".claude" / relative
    return indexed == source and bool(digest_file(plan)) and plan.read_bytes() == source


def has_only_terminal_big_plan_change(
    root: Path, branch: str, phase: str, metadata: dict[str, object]
) -> bool:
    """Accept the exact unstaged final-plan mutation made by closeout hooks."""
    recorded = metadata.get("control_plane_provenance")
    if not isinstance(recorded, dict) or not branch.endswith("_implementation"):
        return False
    slug = branch.removesuffix("_implementation")
    relative = f"plans/{slug}.md"
    indexed = indexed_nested_file(root, relative)
    plan = root / ".claude" / relative
    if indexed is None or digest_file(plan) == "":
        return False
    if hashlib.sha256(indexed).hexdigest() != recorded.get("big_plan_digest"):
        return False
    expected = terminal_big_plan_bytes(indexed, phase)
    if expected is None or plan.read_bytes() != expected:
        return False
    source_small = indexed_nested_file(root, f"plans/{phase}.md")
    if source_small is None or not terminal_current_small_plan_matches(
        root, phase, slug, recorded, source_small
    ):
        return False
    later_phases = terminal_later_phases(indexed, phase)
    if later_phases is None:
        return False
    for later_phase in later_phases:
        later = indexed_nested_file(root, f"plans/{later_phase}.md")
        if later is None or not is_cancelled_small_plan(root, later, later_phase, slug):
            return False

    plan_paths = terminal_plan_paths(indexed, relative)
    if plan_paths is None:
        return False
    changes = relevant_nested_status_changes(root, plan_paths)
    return changes == [(" M", [relative])]


def has_only_checkpointed_terminal_big_plan_change(
    root: Path, branch: str, phase: str, metadata: dict[str, object]
) -> bool:
    """Accept a receipt-bound completed small-plan checkpoint and exact terminal big-plan transition."""
    recorded = metadata.get("control_plane_provenance")
    if not isinstance(recorded, dict) or not branch.endswith("_implementation"):
        return False
    slug = branch.removesuffix("_implementation")
    relative = f"plans/{slug}.md"
    recorded_head = recorded.get("nested_head")
    if not isinstance(recorded_head, str):
        return False
    source = nested_revision_file(root, recorded_head, relative)
    indexed = indexed_nested_file(root, relative)
    plan = root / ".claude" / relative
    if source is None or indexed is None or digest_file(plan) == "":
        return False
    if hashlib.sha256(source).hexdigest() != recorded.get("big_plan_digest"):
        return False
    expected = terminal_big_plan_bytes(source, phase)
    if expected is None or indexed != expected or plan.read_bytes() != expected:
        return False
    source_small = indexed_nested_file(root, f"plans/{phase}.md")
    if source_small is None or not terminal_current_small_plan_matches(
        root, phase, slug, recorded, source_small
    ):
        return False
    later_phases = terminal_later_phases(source, phase)
    if later_phases is None:
        return False
    for later_phase in later_phases:
        later = nested_revision_file(root, recorded_head, f"plans/{later_phase}.md")
        if later is None or not is_cancelled_small_plan(root, later, later_phase, slug):
            return False
    active_plan_paths = terminal_plan_paths(source, relative)
    if active_plan_paths is None:
        return False
    if relevant_nested_status_changes(root, active_plan_paths) != []:
        return False
    current_head = nested_git_head(root)
    if not current_head:
        return False
    try:
        diff = run_process(
            ["git", "diff", "--name-only", "-z", recorded_head, current_head],
            root / ".claude",
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if diff.returncode != 0:
        return False
    changed = [path for path in diff.stdout.split("\0") if path]
    allowed_checkpoint_paths = {relative, f"plans/{phase}.md"}
    return all(
        not is_relevant_nested_path(path, active_plan_paths)
        or path in allowed_checkpoint_paths
        for path in changed
    )


def terminal_control_plane_provenance_matches(
    root: Path,
    branch: str,
    phase: str,
    recorded_metadata: dict[str, object],
    current_metadata: dict[str, object],
) -> bool:
    """Allow only the terminal big-plan change made after a successful commit."""
    if not has_control_plane_provenance(
        recorded_metadata
    ) or not has_control_plane_provenance(current_metadata):
        return False
    recorded = recorded_metadata["control_plane_provenance"]
    current = current_metadata["control_plane_provenance"]
    assert isinstance(recorded, dict) and isinstance(current, dict)
    unchanged = CONTROL_PLANE_PROVENANCE_FIELDS - {
        "nested_head",
        "tracked_state_fingerprint",
        "big_plan_digest",
    }
    return all(recorded.get(field) == current.get(field) for field in unchanged) and (
        has_only_terminal_big_plan_change(root, branch, phase, recorded_metadata)
        or has_only_checkpointed_terminal_big_plan_change(
            root, branch, phase, recorded_metadata
        )
    )


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
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
        "control_plane_provenance": control_plane_provenance(
            root, branch, phase or current_phase(root, branch)
        ),
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
        closeout_path = receipt_path(root, "closeout", phase)
        safe_closeout_path = confined_path(
            root, closeout_path.relative_to(root).as_posix(), regular=True
        )
        receipt = load_receipt(safe_closeout_path)
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
        current_provenance = control_plane_provenance(root, branch, phase)
        if not has_control_plane_provenance(
            {**metadata, "control_plane_provenance": current_provenance}
        ):
            errors.append(
                "closeout receipt governing control-plane provenance is unavailable"
            )
        elif not control_plane_provenance_matches(
            metadata, {**metadata, "control_plane_provenance": current_provenance}
        ) and not terminal_control_plane_provenance_matches(
            root,
            branch,
            phase,
            metadata,
            {**metadata, "control_plane_provenance": current_provenance},
        ):
            errors.append(
                "closeout receipt governing control-plane provenance is stale"
            )

    artifacts = receipt.get("artifacts")
    if not isinstance(artifacts, dict):
        return errors + ["closeout receipt artifacts are malformed"]
    expected_paths = {
        "phase_receipt": receipt_path(root, "phase", phase)
        .relative_to(root)
        .as_posix(),
        "findings": f".claude/quality_reports/findings-{phase}.json",
    }
    loaded: dict[str, object] = {}
    for key in ARTIFACT_KEYS:
        artifact = artifacts.get(key)
        if key == "documentation":
            try:
                validate_documentation_evidence(artifact)
            except ValueError as error:
                errors.append(str(error))
            continue
        if not isinstance(artifact, dict):
            errors.append(f"closeout receipt artifact {key} is missing")
            continue
        path_value = artifact.get("path")
        if not isinstance(path_value, str) or not is_safe_relative_path(path_value):
            errors.append(f"closeout receipt artifact {key} has an unsafe path")
            continue
        if key in {"phase_receipt", "findings"} and path_value != expected_paths[key]:
            errors.append(f"closeout receipt {key} path is invalid")
            continue
        try:
            path = confined_path(root, path_value, regular=True)
            actual_digest = file_digest(path)
        except ValueError:
            errors.append(f"closeout receipt artifact {key} is missing or unsafe")
            continue
        if artifact.get("sha256") != actual_digest:
            errors.append(f"closeout receipt artifact {key} was tampered with")
            continue
        loaded[key] = path

    documentation = artifacts.get("documentation")
    if isinstance(documentation, dict):
        changed_docs = [
            path
            for path in metadata.get("changed_paths", [])
            if isinstance(path, str) and classify_path(path) == "documentation-only"
        ]
        if changed_docs and documentation.get("status") != "UPDATED":
            errors.append("closeout receipt must record updated documentation")
        if (
            documentation.get("status") == "UPDATED"
            and documentation.get("paths") != changed_docs
        ):
            errors.append("closeout receipt documentation paths are stale")

    phase_path = loaded.get("phase_receipt")
    if isinstance(phase_path, Path):
        try:
            phase_receipt = load_receipt(phase_path)
        except ValueError as error:
            errors.append(f"phase receipt is invalid: {error}")
        else:
            if phase_receipt["mode"] != "phase" or phase_receipt["status"] != "PASS":
                errors.append("phase receipt must be passing phase evidence")
            phase_metadata = phase_receipt.get("metadata")
            if (
                not isinstance(phase_metadata, dict)
                or any(
                    phase_metadata.get(field) != metadata.get(field)
                    for field in (
                        "phase",
                        "branch",
                        "base_ref",
                        "head_sha",
                        "merge_base_sha",
                        "content_hash",
                    )
                )
                or not control_plane_provenance_matches(phase_metadata, metadata)
            ):
                errors.append("phase receipt does not correlate with closeout evidence")
    findings_path = loaded.get("findings")
    if isinstance(findings_path, Path):
        errors.extend(
            report_errors(
                findings_path,
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
    """Validate the findings report without provider-specific policy."""
    label = "findings report"
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
    if not is_utc_timestamp(report.get("generated_at")):
        errors.append(f"{label} generated_at must be a UTC timestamp")
    target = report.get("target")
    if not isinstance(target, str):
        errors.append(f"{label} is missing target")
    else:
        try:
            confined_path(root, target)
        except ValueError:
            errors.append(
                f"{label} target is missing, unsafe, or outside the repository"
            )
    changed_files = report.get("changed_files")
    if not isinstance(changed_files, list) or not all(
        isinstance(item, str) for item in changed_files
    ):
        errors.append(f"{label} changed_files must be a list of strings")
    if verify_current_content:
        current_hash = content_hash_for(
            root, expected_base, head if head_relation == "ancestor" else ""
        )
        if not current_hash or report.get("content_hash") != current_hash:
            errors.append(f"{label} content_hash is stale")
    findings = report.get("findings")
    profiles = report.get("profiles_reviewed")
    if (
        not isinstance(findings, list)
        or not isinstance(profiles, list)
        or not profiles
        or not all(isinstance(profile, str) and profile for profile in profiles)
        or len(set(profiles)) != len(profiles)
    ):
        errors.append("findings report schema or reviewed profiles are invalid")
        findings = []
        profiles = []
    observed = {"critical": 0, "major": 0, "minor": 0}
    for finding in findings:
        if not isinstance(finding, dict):
            errors.append("findings report contains a malformed finding")
            continue
        severity = finding.get("severity")
        profile = finding.get("profile")
        title = finding.get("title")
        if (
            severity not in {"CRITICAL", "MAJOR", "MINOR"}
            or not isinstance(profile, str)
            or profile not in profiles
            or not isinstance(title, str)
            or not title.strip()
        ):
            errors.append(
                "findings report finding is invalid"
                + (f": {title}" if isinstance(title, str) and title else "")
            )
            continue
        observed[str(severity).lower()] += 1
    counts = report.get("counts")
    if not isinstance(counts, dict) or any(
        type(counts.get(name)) is not int or counts[name] < 0
        for name in ("critical", "major", "minor")
    ):
        errors.append("findings report severity counts are invalid")
    else:
        if counts != observed:
            errors.append("findings report counts do not match findings")
        if counts["critical"] != 0:
            titles = ", ".join(
                str(item.get("title"))
                for item in findings
                if isinstance(item, dict) and item.get("severity") == "CRITICAL"
            )
            errors.append(
                "findings report has CRITICAL findings"
                + (f": {titles}" if titles else "")
            )
        if require_major and counts["major"] != 0:
            titles = ", ".join(
                str(item.get("title"))
                for item in findings
                if isinstance(item, dict) and item.get("severity") == "MAJOR"
            )
            errors.append(
                "findings report has MAJOR findings" + (f": {titles}" if titles else "")
            )
    ponytail_reviewed = report.get("ponytail_reviewed")
    ponytail_findings = report.get("ponytail_findings")
    ponytail_selected = "ponytail" in profiles
    observed_ponytail = sum(
        1
        for finding in findings
        if isinstance(finding, dict) and finding.get("profile") == "ponytail"
    )
    if ponytail_selected:
        if ponytail_reviewed is not True:
            errors.append("Ponytail review metadata contradicts reviewed profiles")
        if type(ponytail_findings) is not int or ponytail_findings != observed_ponytail:
            errors.append("Ponytail finding count does not match findings")
    elif ponytail_reviewed is not None or ponytail_findings is not None:
        errors.append("unselected Ponytail review must omit Ponytail metadata")
    if require_ponytail and not ponytail_selected:
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


def _run(args: list[str], cwd: str = ".") -> tuple[int, str, str]:
    """Run one external verification tool, returning its raw result."""
    result = subprocess.run(
        args,
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=COMMAND_TIMEOUT_SECONDS,
    )
    return result.returncode, result.stdout, result.stderr


def _ruff_measurement(
    targets: list[str], cwd: str = ".", *, extend_exclude: list[str] | None = None
) -> tuple[str, str]:
    """Measure Ruff without treating failed measurement as a clean result."""
    try:
        args = ["uv", "run", "ruff", "check", *targets, "--output-format=json"]
        for pattern in extend_exclude or []:
            args.extend(("--extend-exclude", pattern))
        rc, stdout, stderr = _run(args, cwd=cwd)
    except (OSError, subprocess.SubprocessError) as error:
        return "UNVERIFIED", f"Ruff did not run: {error}"
    if rc not in {0, 1}:
        return (
            "UNVERIFIED",
            f"Ruff exited abnormally ({rc}): {(stderr or stdout).strip()}",
        )
    if not stdout.strip():
        return "UNVERIFIED", "Ruff produced no JSON output"
    try:
        violations = json.loads(stdout)
    except json.JSONDecodeError as error:
        return "UNVERIFIED", f"Ruff produced invalid JSON: {error}"
    if not isinstance(violations, list) or not all(
        isinstance(item, dict) for item in violations
    ):
        return "UNVERIFIED", "Ruff JSON was not a violation list"
    if rc == 0 and violations:
        return "UNVERIFIED", "Ruff reported violations with a successful exit status"
    if rc == 1 and not violations:
        return "UNVERIFIED", "Ruff failed without reporting any violations"
    if rc == 0:
        return "PASS", "Ruff completed with 0 violations"
    return "FAIL", f"Ruff reported {len(violations)} violation(s)"


def _mypy_measurement(targets: list[str] | None, cwd: str = ".") -> tuple[str, str]:
    """Measure mypy while distinguishing type failures from tool failures."""
    try:
        rc, stdout, stderr = _run(
            [
                "uv",
                "run",
                "mypy",
                *(targets or []),
                "--ignore-missing-imports",
                "--explicit-package-bases",
            ],
            cwd=cwd,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return "UNVERIFIED", f"mypy did not run: {error}"
    output = stdout + stderr
    error_count = sum(1 for line in output.splitlines() if ": error:" in line)
    if rc == 0:
        if error_count:
            return "UNVERIFIED", "mypy reported errors with a successful exit status"
        return "PASS", "mypy completed with 0 errors"
    if rc == 1 and error_count:
        return "FAIL", f"mypy reported {error_count} type error(s)"
    return (
        "UNVERIFIED",
        f"mypy exited abnormally ({rc}): {output.strip() or 'no output'}",
    )


def _pytest_measurement(
    cwd: str = ".", targets: list[str] | None = None
) -> tuple[str, str]:
    """Measure pytest, separating test failures from infrastructure failures."""
    try:
        rc, stdout, stderr = _run(
            [
                "uv",
                "run",
                "pytest",
                *(targets if targets is not None else ["tests/"]),
                "-q",
                "--tb=no",
            ],
            cwd=cwd,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return "UNVERIFIED", f"pytest did not run: {error}"
    if rc == 0:
        return "PASS", "pytest completed"
    if rc == 1:
        return "FAIL", "pytest reported test failures"
    return (
        "UNVERIFIED",
        f"pytest infrastructure exit ({rc}): {(stderr or stdout).strip() or 'no output'}",
    )


def measure_ruff(
    root: Path, targets: list[str], *, extend_exclude: list[str] | None = None
) -> dict[str, object]:
    """Adapt the strict Ruff measurement into a receipt check."""
    status, detail = _ruff_measurement(
        targets, cwd=str(root), extend_exclude=extend_exclude
    )
    return check("VFY-RUFF-001", status, detail)


def measure_mypy(root: Path, targets: list[str] | None) -> dict[str, object]:
    """Adapt the strict mypy measurement into a receipt check."""
    status, detail = _mypy_measurement(targets, cwd=str(root))
    return check("VFY-MYPY-001", status, detail)


def measure_pytest(root: Path, targets: list[str] | None = None) -> dict[str, object]:
    """Adapt the strict pytest measurement into a receipt check."""
    status, detail = _pytest_measurement(cwd=str(root), targets=targets)
    return check("VFY-PYTEST-001", status, detail)


def is_bootstrap_authoring_repository(root: Path) -> bool:
    """Return whether the repository contains the bootstrap source ownership markers."""
    return all((root / marker).is_file() for marker in AUTHORING_RUNTIME_MARKERS)


def is_configured_mypy_scope(value: object) -> bool:
    """Return whether one parsed Mypy target setting has usable values."""
    if isinstance(value, str):
        return bool(value.strip())
    return bool(
        isinstance(value, list)
        and value
        and all(isinstance(item, str) and item.strip() for item in value)
    )


def mypy_configured_scope(root: Path) -> bool | None:
    """Read the selected native Mypy config or report an unsafe parse as unknown."""
    for relative in MYPY_CONFIG_FILES:
        config = root / relative
        if not config.exists():
            continue
        if config.name == "pyproject.toml":
            try:
                import tomllib
            except ModuleNotFoundError:  # Python 3.9-3.10 cannot inspect TOML safely.
                return None
            try:
                parsed = tomllib.loads(config.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
                return None
            tool = parsed.get("tool")
            section = tool.get("mypy") if isinstance(tool, dict) else None
            if not isinstance(section, dict):
                continue
            return any(
                is_configured_mypy_scope(section.get(option))
                for option in MYPY_SCOPE_OPTIONS
            )
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read(config, encoding="utf-8")
        except (OSError, UnicodeDecodeError, configparser.Error):
            return None
        if not parser.has_section("mypy"):
            continue
        return any(
            is_configured_mypy_scope(parser.get("mypy", option, fallback=""))
            for option in MYPY_SCOPE_OPTIONS
        )
    return False


def consumer_mypy_targets(root: Path) -> list[str] | None:
    """Resolve only native configured scope or the conventional ``src`` root."""
    configured_scope = mypy_configured_scope(root)
    if configured_scope is True:
        return []
    if configured_scope is None:
        return None
    return ["src"] if (root / "src").is_dir() else None


def generation_check(root: Path) -> dict[str, object]:
    """Require the generated verifier to match its canonical source."""
    source = root / "shared/scripts/verify.py"
    generated = root / ".claude/scripts/verify.py"
    if source.is_file():
        if not generated.is_file():
            return check(
                "VFY-GEN-001", "UNVERIFIED", "generated verifier runtime is missing"
            )
        status = "PASS" if source.read_bytes() == generated.read_bytes() else "FAIL"
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
        relative = path.relative_to(root)
        resolved = confined_path(root, relative.as_posix(), regular=True)
    except ValueError as error:
        raise ValueError(f"artifact is outside repository: {path}") from error
    return {"path": relative.as_posix(), "sha256": file_digest(resolved)}


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
    return confined_path(root, match.group(1), regular=True)


def closeout_artifacts(
    root: Path, metadata: dict[str, object], documentation_na: str = ""
) -> dict[str, object]:
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
    documentation_paths = [
        path
        for path in metadata_paths(metadata, "changed_paths")
        if classify_path(path) == "documentation-only"
    ]
    if not documentation_paths and not documentation_na.strip():
        raise ValueError(
            "closeout needs --documentation-na REASON when documentation was not updated"
        )
    return {
        "phase_receipt": relative_artifact(root, receipt_path(root, "phase", phase)),
        "findings": relative_artifact(
            root, root / ".claude/quality_reports" / f"findings-{phase}.json"
        ),
        "closeout_log": relative_artifact(root, closeout_log_path(root, phase)),
        "documentation": (
            {"status": "UPDATED", "paths": documentation_paths}
            if documentation_paths
            else {
                "status": "NOT_APPLICABLE",
                "reason": documentation_na.strip(),
            }
        ),
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
    """Return whether Git and governing nested provenance are trustworthy."""
    return bool(
        metadata.get("head_sha")
        and metadata.get("merge_base_sha")
        and metadata.get("path_discovery_ok") is True
        and has_control_plane_provenance(metadata)
    )


def metadata_has_outer_binding(metadata: dict[str, object]) -> bool:
    """Return whether Git supplied the outer commit/base pair freshness needs."""
    return bool(
        metadata.get("head_sha")
        and metadata.get("merge_base_sha")
        and metadata.get("path_discovery_ok") is True
    )


def phase_checks(root: Path, metadata: dict[str, object]) -> list[dict[str, object]]:
    """Run the complete Phase-A measurement group."""
    outer_freshness_status = (
        "PASS" if metadata_has_outer_binding(metadata) else "UNVERIFIED"
    )
    provenance_status = "PASS" if metadata_is_bound(metadata) else "UNVERIFIED"
    if is_bootstrap_authoring_repository(root):
        ruff = measure_ruff(root, ["shared", "scripts", "tests"])
        mypy = measure_mypy(root, ["shared", "scripts", "tests"])
        pytest = measure_pytest(root, ["tests/"])
    else:
        ruff = measure_ruff(root, ["."], extend_exclude=[".claude"])
        mypy_targets = consumer_mypy_targets(root)
        mypy = (
            measure_mypy(root, mypy_targets)
            if mypy_targets is not None
            else check(
                "VFY-MYPY-001",
                "UNVERIFIED",
                "Mypy has no configured scope or conventional src root",
            )
        )
        pytest = measure_pytest(root, [])
    checks = [
        ruff,
        mypy,
        pytest,
        check(
            "VFY-FRESH-001",
            outer_freshness_status,
            "phase evidence captured relevant state"
            if outer_freshness_status == "PASS"
            else "Git base state was unavailable",
        ),
        check(
            "VFY-FRESH-002",
            provenance_status,
            "phase evidence captured governing control-plane provenance"
            if provenance_status == "PASS"
            else "governing control-plane provenance was unavailable",
        ),
        generation_check(root),
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
    return [
        ruff,
        not_applicable("VFY-MYPY-001", "fast mode does not run global typing"),
        not_applicable("VFY-PYTEST-001", "fast mode does not run the full test suite"),
        not_applicable(
            "VFY-FRESH-001", "fast mode never establishes reusable evidence"
        ),
        not_applicable(
            "VFY-FRESH-002", "fast mode never establishes closeout authority"
        ),
        not_applicable(
            "VFY-GEN-001", "fast mode does not validate generated ownership"
        ),
        not_applicable("VFY-RECEIPT-001", "fast mode does not consume evidence"),
    ]


def closeout_checks(root: Path, metadata: dict[str, object]) -> list[dict[str, object]]:
    """Reuse validated phase evidence and bind a final full-state receipt."""
    phase = metadata.get("phase")
    phase_path = receipt_path(root, "phase", phase) if isinstance(phase, str) else root
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
    if not metadata_has_outer_binding(metadata) or not metadata_has_outer_binding(
        phase_metadata
    ):
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
    if not metadata_is_bound(metadata) or not metadata_is_bound(phase_metadata):
        provenance_status = "UNVERIFIED"
    elif control_plane_provenance_matches(phase_metadata, metadata):
        provenance_status = "PASS"
    else:
        provenance_status = "FAIL"
    return [
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
            provenance_status,
            "phase evidence matches governing control-plane provenance"
            if provenance_status == "PASS"
            else (
                "governing control-plane provenance is stale"
                if provenance_status == "FAIL"
                else "governing control-plane provenance was unavailable"
            ),
        ),
        not_applicable("VFY-GEN-001", "closeout reuses phase generation evidence"),
        receipt_check,
    ]


def receipt_path(root: Path, mode: str, phase: str) -> Path:
    """Return one immutable receipt path for the named implementation phase."""
    if mode not in {"phase", "closeout"} or not PHASE_SLUG.fullmatch(phase):
        raise ValueError("receipt persistence needs a safe phase slug")
    pattern = PHASE_RECEIPT if mode == "phase" else CLOSEOUT_RECEIPT
    return root / Path(str(pattern).format(phase=phase))


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
    parser.add_argument(
        "--documentation-na",
        default="",
        metavar="REASON",
        help="explain why a closeout does not require documentation changes",
    )
    return parser.parse_args()


def main() -> int:
    """Run one verifier mode and optionally persist its authoritative receipt."""
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
    artifacts = (
        closeout_artifacts(root, metadata, args.documentation_na)
        if args.mode == "closeout"
        else None
    )
    receipt = build_receipt(args.mode, checks, metadata, artifacts)
    if args.persist:
        if args.mode == "fast":
            print("fast mode never persists evidence", file=sys.stderr)
            return 2
        phase = metadata.get("phase")
        if not isinstance(phase, str):
            print("receipt persistence needs phase metadata", file=sys.stderr)
            return 2
        path = receipt_path(root, args.mode, phase)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(canonical_json(receipt) + "\n", encoding="utf-8")
    if args.format == "json":
        print(canonical_json(receipt))
    else:
        print(f"{args.mode}: {receipt['status']}")
        for item in checks:
            print(f"{item['id']}: {item['status']} - {item['summary']}")
    return 0 if receipt["status"] in {"PASS", "NOT_APPLICABLE"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
