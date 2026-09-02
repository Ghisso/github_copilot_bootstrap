"""Falsifier regressions for the deterministic verification receipt."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "shared" / "scripts"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import verify  # noqa: E402
from runtime_ownership import (  # type: ignore[import-not-found]  # noqa: E402
    bootstrap_root_paths,
    restore_manifest,
)


HISTORICAL_SCHEMA_V2_SOURCE_COMMIT = "e2753a9f2fd24dd2fc952e20929a9c7bbb1eeb37"
HISTORICAL_SCHEMA_V2_RUNTIME_SHA256 = (
    "9abc7edbd1d31ab89c232ad451583867b5943ad42af7eee45d58ff60fbe35fad"
)
HISTORICAL_SCHEMA_V2_RECEIPTS = {
    "schema-v2-receipt.json": "15c78e5320e23b1bb59c6751d165a87d2e74d146b431fd7320639bafd87e5c76",
    "schema-v2-closeout-receipt.json": "5cf5c3477016200a817e0fa0de4db13aef06a84c64b791d3a90f51f90cb72f15",
}
HISTORICAL_SCHEMA_V2_RUNTIME = (
    REPO_ROOT / "tests" / "fixtures" / "schema-v2-verify.py.txt"
)
HISTORICAL_SCHEMA_V2_SOURCE = REPO_ROOT / "tests" / "fixtures" / "schema-v2-source.json"

HISTORICAL_SCHEMA_V3_SOURCE_COMMIT = "b9a235f7d13b0d45a4383ee908ff2f18eb732692"
HISTORICAL_SCHEMA_V3_RUNTIME_SHA256 = (
    "c1ee21871bd2ee3956bf8ec277f3042a315e23cf3cba7ea1a90de7bf8c89f595"
)
HISTORICAL_SCHEMA_V3_RECEIPTS = {
    "schema-v3-receipt.json": "262805a16d2f98eef94bd28408c5ec12f12c7e9534278f68ea05bd1f79512c71",
    "schema-v3-closeout-receipt.json": "19acbf5f5181c19c865a9b3a1b00c6e23f3f62c902abbd6bc654142c3ee7e82b",
}
HISTORICAL_SCHEMA_V3_RUNTIME = (
    REPO_ROOT / "tests" / "fixtures" / "schema-v3-verify.py.txt"
)
HISTORICAL_SCHEMA_V3_SOURCE = REPO_ROOT / "tests" / "fixtures" / "schema-v3-source.json"


def test_verifier_disables_runtime_bytecode_cache() -> None:
    """Running the managed verifier must not create unmanaged runtime files."""
    source = (REPO_ROOT / "shared/scripts/verify.py").read_text(encoding="utf-8")
    assert "sys.dont_write_bytecode = True" in source
    assert "import quality_score" not in source


def test_quality_score_module_is_deleted_everywhere() -> None:
    """The deleted score-era measurement module must not be reintroduced in
    canonical source or in the generated consumer runtime."""
    assert not (REPO_ROOT / "shared" / "scripts" / "quality_score.py").exists()
    generated = REPO_ROOT / "dist" / "multi-agent" / ".claude" / "scripts"
    if generated.is_dir():
        assert not (generated / "quality_score.py").exists()


def test_phase_text_format_reports_deterministic_per_check_detail() -> None:
    """`verify.py phase --format text` stays a compact human-readable
    PASS/FAIL summary: one line per deterministic check plus an overall
    result line, with no numeric score anywhere in that output shape."""
    source = (REPO_ROOT / "shared/scripts/verify.py").read_text(encoding="utf-8")
    assert "print(f\"{args.mode}: {receipt['status']}\")" in source
    assert "print(f\"{item['id']}: {item['status']} - {item['summary']}\")" in source


def test_verifier_uses_python39_compatible_utc_clock() -> None:
    """Hook-side receipt reading imports without Python 3.11's datetime.UTC."""
    source = (REPO_ROOT / "shared/scripts/verify.py").read_text(encoding="utf-8")
    assert "from datetime import UTC" not in source
    assert "timezone.utc" in source


def test_completed_receipts_are_immutable_per_phase(tmp_path: Path) -> None:
    """Later phases cannot overwrite earlier completed receipt locations."""
    assert verify.receipt_path(
        tmp_path, "closeout", "phase-one"
    ) != verify.receipt_path(tmp_path, "closeout", "phase-two")


def _metadata(content_hash: str = "relevant") -> dict[str, object]:
    """Return the minimum strict receipt metadata."""
    return {
        "base_ref": "dev",
        "branch": "verification-test",
        "head_sha": "head",
        "merge_base_sha": "base",
        "tree_sha": "tree",
        "phase": "phase-one",
        "content_hash": content_hash,
        "tracked_state_hash": "whole-state",
        "generated_at": "2026-08-29T00:00:00Z",
        "changed_paths": [],
        "relevant_paths": [],
        "path_discovery_ok": True,
        "control_plane_provenance": {
            "schema_version": verify.CONTROL_PLANE_PROVENANCE_SCHEMA_VERSION,
            "nested_head": "a" * 40,
            "runtime_fingerprint": "b" * 64,
            "tracked_state_fingerprint": "c" * 64,
            "big_plan_digest": "",
            "small_plan_digest": "",
        },
    }


def _receipt(status: str = "PASS", content_hash: str = "relevant") -> dict[str, object]:
    """Build a complete receipt with controllable aggregate status."""
    checks = [
        verify.not_applicable(check_id, "phase does not consume evidence")
        if check_id == "VFY-RECEIPT-001"
        else verify.check(check_id, status, "measured")
        for check_id in verify.CHECK_IDS
    ]
    return verify.build_receipt("phase", checks, _metadata(content_hash))


def _exec_historical_verify(
    monkeypatch: pytest.MonkeyPatch, source: bytes, path: Path
) -> types.ModuleType:
    """Execute a byte-pinned historical verify.py that still imports the
    deleted sibling measurement module; only schema/receipt validation is
    exercised below, so a harmless stand-in module satisfies that legacy
    import without needing the deleted file's bytes."""
    monkeypatch.setitem(sys.modules, "quality_score", types.ModuleType("quality_score"))
    historical = types.ModuleType("historical_verify")
    historical.__file__ = str(path)
    exec(compile(source, historical.__file__, "exec"), historical.__dict__)
    return historical


def test_historical_schema_v2_receipts_are_rejected_before_v3_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pinned local v2 receipts are valid there, never current authority."""
    source = HISTORICAL_SCHEMA_V2_RUNTIME.read_bytes()
    source_metadata = json.loads(HISTORICAL_SCHEMA_V2_SOURCE.read_text())
    assert source_metadata == {
        "source_commit": HISTORICAL_SCHEMA_V2_SOURCE_COMMIT,
        "runtime_sha256": HISTORICAL_SCHEMA_V2_RUNTIME_SHA256,
    }
    assert hashlib.sha256(source).hexdigest() == HISTORICAL_SCHEMA_V2_RUNTIME_SHA256
    historical = _exec_historical_verify(
        monkeypatch, source, REPO_ROOT / "shared" / "scripts" / "verify.py"
    )
    assert historical.SCHEMA_VERSION == 2
    for fixture, digest in HISTORICAL_SCHEMA_V2_RECEIPTS.items():
        raw = (REPO_ROOT / "tests" / "fixtures" / fixture).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == digest
        receipt = json.loads(raw)
        assert historical.validate_receipt(receipt) == receipt
        with pytest.raises(
            ValueError, match=r"^receipt has an unsupported schema_version$"
        ):
            verify.validate_receipt(receipt)


def test_historical_schema_v3_receipts_are_rejected_before_v4_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pinned local v3 receipts are valid there, never current (v4) authority."""
    source = HISTORICAL_SCHEMA_V3_RUNTIME.read_bytes()
    source_metadata = json.loads(HISTORICAL_SCHEMA_V3_SOURCE.read_text())
    assert source_metadata == {
        "source_commit": HISTORICAL_SCHEMA_V3_SOURCE_COMMIT,
        "runtime_sha256": HISTORICAL_SCHEMA_V3_RUNTIME_SHA256,
    }
    assert hashlib.sha256(source).hexdigest() == HISTORICAL_SCHEMA_V3_RUNTIME_SHA256
    historical = _exec_historical_verify(
        monkeypatch, source, REPO_ROOT / "shared" / "scripts" / "verify.py"
    )
    assert historical.SCHEMA_VERSION == 3
    for fixture, digest in HISTORICAL_SCHEMA_V3_RECEIPTS.items():
        raw = (REPO_ROOT / "tests" / "fixtures" / fixture).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == digest
        receipt = json.loads(raw)
        assert historical.validate_receipt(receipt) == receipt
        with pytest.raises(
            ValueError, match=r"^receipt has an unsupported schema_version$"
        ):
            verify.validate_receipt(receipt)


def test_mid_plan_schema_refresh_fails_closed_then_recovers(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A stale pre-refresh phase receipt fails closed; re-running `phase`
    under the current runtime recovers without any manual receipt edit or
    bypass - the only supported v3 -> v4 mid-plan upgrade path."""
    source = HISTORICAL_SCHEMA_V3_RUNTIME.read_bytes()
    historical = _exec_historical_verify(
        monkeypatch, source, REPO_ROOT / "shared" / "scripts" / "verify.py"
    )
    stale_metadata = _metadata()
    stale_checks = [
        historical.not_applicable(check_id, "phase does not consume evidence")
        if check_id == "VFY-RECEIPT-001"
        else historical.check(check_id, "PASS", "legacy measured")
        for check_id in historical.CHECK_IDS
    ]
    stale_receipt = historical.build_receipt("phase", stale_checks, stale_metadata)
    phase_path = verify.receipt_path(tmp_path, "phase", "phase-one")
    phase_path.parent.mkdir(parents=True)
    phase_path.write_text(json.dumps(stale_receipt), encoding="utf-8")

    # Fail closed: the current (v4) runtime refuses the stale v3 receipt with
    # a clear, diagnosable message rather than crashing or accepting it.
    stale_checks_result = verify.closeout_checks(tmp_path, _metadata())
    stale_reused = next(
        item for item in stale_checks_result if item["id"] == "VFY-RECEIPT-001"
    )
    assert stale_reused["status"] == "FAIL"
    assert "schema_version" in stale_reused["summary"]

    # Recover: re-running `phase --persist` under the current runtime (no
    # manual receipt edit, no bypass) regenerates a valid current-schema
    # receipt at the same deterministic path.
    fresh_receipt = _receipt()
    phase_path.write_text(json.dumps(fresh_receipt), encoding="utf-8")
    recovered_checks = verify.closeout_checks(tmp_path, _metadata())
    recovered_reused = next(
        item for item in recovered_checks if item["id"] == "VFY-RECEIPT-001"
    )
    assert recovered_reused["status"] == "PASS"


def test_gate_rejects_a_schema_v3_closeout_receipt_at_the_fixed_path(
    tmp_path: Path,
) -> None:
    """The literal git-hook scenario: a consumer completed a v3 closeout,
    refreshed the runtime, and now attempts the checkpoint transition commit.
    `gate_receipt_errors` is the function the real commit-msg/pre-push git
    hooks call (via `verify.py gate`); it must fail closed on the pinned v3
    closeout receipt rather than accepting or crashing on it."""
    raw = (
        REPO_ROOT / "tests" / "fixtures" / "schema-v3-closeout-receipt.json"
    ).read_bytes()
    receipt = json.loads(raw)
    branch = receipt["metadata"]["branch"]
    phase = receipt["metadata"]["phase"]
    closeout_path = verify.receipt_path(tmp_path, "closeout", phase)
    closeout_path.parent.mkdir(parents=True)
    closeout_path.write_bytes(raw)

    errors = verify.gate_receipt_errors(
        tmp_path,
        branch=branch,
        phase=phase,
        head="0" * 40,
        head_relation="exact",
        require_major=False,
        require_ponytail=False,
        enforce_final_state=True,
    )
    assert len(errors) == 1
    assert "schema_version" in errors[0]


def _write_root_adapter_pairs(root: Path, mode: bool = True) -> None:
    """Write one complete mode-specific ownership inventory and its mirrors."""
    for relative in bootstrap_root_paths(mode):
        for base in (root, root / ".claude" / "bootstrap-root"):
            path = base / relative
            if Path(relative).suffix:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("adapter\n", encoding="utf-8")
            else:
                (path / "fixture.txt").parent.mkdir(parents=True, exist_ok=True)
                (path / "fixture.txt").write_text("adapter\n", encoding="utf-8")
    manifest = root / ".claude" / "bootstrap-ownership.env"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(restore_manifest(mode), encoding="utf-8")


def _closeout_receipt() -> dict[str, object]:
    """Build minimal syntactically valid completed evidence references."""
    checks = [
        verify.not_applicable(check_id, "closeout reuses phase evidence")
        if check_id in {"VFY-RUFF-001", "VFY-MYPY-001", "VFY-PYTEST-001", "VFY-GEN-001"}
        else verify.check(check_id, "PASS", "measured")
        for check_id in verify.CHECK_IDS
    ]
    digest = "a" * 64
    return verify.build_receipt(
        "closeout",
        checks,
        _metadata(),
        {
            "phase_receipt": {
                "path": ".claude/quality_reports/verification-phase-phase-one.json",
                "sha256": digest,
            },
            "findings": {
                "path": ".claude/quality_reports/findings-phase-one.json",
                "sha256": digest,
            },
            "closeout_log": {
                "path": ".claude/session_logs/phase-one-closeout.md",
                "sha256": digest,
            },
            "documentation": {
                "status": "NOT_APPLICABLE",
                "reason": "no documentation paths changed",
            },
        },
    )


def test_confined_path_rejects_symlink_components(tmp_path: Path) -> None:
    """Receipt children cannot escape through an otherwise in-repo symlink."""
    outside = tmp_path.parent / "outside-evidence.json"
    outside.write_text("{}", encoding="utf-8")
    (tmp_path / "reports").symlink_to(tmp_path.parent, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        verify.confined_path(tmp_path, "reports/outside-evidence.json", regular=True)


@pytest.mark.parametrize("symlink_parent", (False, True), ids=("receipt", "parent"))
def test_gate_rejects_symlinked_closeout_receipt(
    tmp_path: Path, symlink_parent: bool
) -> None:
    """The authoritative receipt and each parent directory must be real paths."""
    outside = tmp_path / "outside"
    outside.mkdir()
    receipt_name = "verification-closeout-phase-one.json"
    (outside / receipt_name).write_text(
        json.dumps(_closeout_receipt()), encoding="utf-8"
    )
    reports = tmp_path / ".claude/quality_reports"
    if symlink_parent:
        reports.parent.mkdir(parents=True)
        reports.symlink_to(outside, target_is_directory=True)
    else:
        reports.mkdir(parents=True)
        (reports / receipt_name).symlink_to(outside / receipt_name)
    errors = verify.gate_receipt_errors(
        tmp_path,
        branch="verification-test",
        phase="phase-one",
        head="head",
        head_relation="exact",
        require_major=False,
        require_ponytail=False,
        enforce_final_state=False,
    )
    assert errors and "symlink" in errors[0]


@pytest.mark.parametrize(
    "timestamp",
    ("2026-02-30T00:00:00Z", "2026-08-29T00:00:00+00:00", "later"),
)
def test_receipt_rejects_noncanonical_or_impossible_timestamp(timestamp: str) -> None:
    """Receipt timestamps use one parseable UTC-second representation."""
    receipt = _receipt()
    receipt["metadata"]["generated_at"] = timestamp  # type: ignore[index]
    with pytest.raises(ValueError, match="UTC timestamp"):
        verify.validate_receipt(receipt)


def test_closeout_requires_explicit_documentation_na(tmp_path: Path) -> None:
    """No documentation diff is not evidence that documentation is unnecessary."""
    with pytest.raises(ValueError, match="--documentation-na"):
        verify.closeout_artifacts(tmp_path, _metadata())


def _findings_report(**updates: object) -> dict[str, object]:
    """Return a findings report suitable for focused schema checks."""
    report: dict[str, object] = {
        "branch": "verification-test",
        "phase": "phase-one",
        "base_ref": "dev",
        "head_sha": "head",
        "merge_base_sha": "base",
        "dirty": False,
        "generated_at": "2026-08-29T00:00:00Z",
        "target": ".",
        "changed_files": [],
        "content_hash": "hash",
        "profiles_reviewed": ["code"],
        "findings": [],
        "counts": {"critical": 0, "major": 0, "minor": 0},
    }
    report.update(updates)
    return report


def _findings_errors(
    tmp_path: Path, report: dict[str, object], *, require_major: bool = False
) -> list[str]:
    """Persist and validate one focused findings fixture."""
    path = tmp_path / "findings.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return verify.report_errors(
        path,
        branch="verification-test",
        phase="phase-one",
        head="head",
        head_relation="exact",
        expected_base="base",
        root=tmp_path,
        require_major=require_major,
        require_ponytail=False,
        verify_current_content=False,
    )


def test_findings_rejects_nonstring_changed_file(tmp_path: Path) -> None:
    """Changed-file evidence cannot contain untyped JSON values."""
    errors = _findings_errors(tmp_path, _findings_report(changed_files=[1]))
    assert "findings report changed_files must be a list of strings" in errors


def _major_finding() -> dict[str, object]:
    return {
        "severity": "MAJOR",
        "profile": "code",
        "title": "unresolved MAJOR finding",
    }


def test_open_major_blocks_only_when_phase_completion_is_required(
    tmp_path: Path,
) -> None:
    """An open MAJOR finding blocks phase-completion (require_major=True) but
    is not, by itself, a blocking reason for a non-completion validation pass
    (require_major=False) - the distinction Phase 2 must draw correctly."""
    report = _findings_report(
        findings=[_major_finding()], counts={"critical": 0, "major": 1, "minor": 0}
    )
    completion_errors = _findings_errors(tmp_path, report, require_major=True)
    assert any("MAJOR findings" in error for error in completion_errors)

    intermediate_errors = _findings_errors(tmp_path, report, require_major=False)
    assert not any("MAJOR findings" in error for error in intermediate_errors)


def _minor_finding(**updates: object) -> dict[str, object]:
    finding: dict[str, object] = {
        "severity": "MINOR",
        "profile": "code",
        "title": "advisory MINOR finding",
    }
    finding.update(updates)
    return finding


def test_minor_finding_without_disposition_blocks_completion(tmp_path: Path) -> None:
    """A surviving MINOR finding with no disposition fails phase completion."""
    report = _findings_report(
        findings=[_minor_finding()], counts={"critical": 0, "major": 0, "minor": 1}
    )
    errors = _findings_errors(tmp_path, report, require_major=True)
    assert any("explicit disposition and reason" in error for error in errors)


def test_minor_finding_with_empty_reason_blocks_completion(tmp_path: Path) -> None:
    """A disposition without meaningful reason text still fails completion."""
    report = _findings_report(
        findings=[_minor_finding(disposition="accepted", reason="   ")],
        counts={"critical": 0, "major": 0, "minor": 1},
    )
    errors = _findings_errors(tmp_path, report, require_major=True)
    assert any("explicit disposition and reason" in error for error in errors)


def test_minor_finding_with_disposition_and_reason_passes(tmp_path: Path) -> None:
    """An explicit disposition and non-empty reason satisfies the contract."""
    report = _findings_report(
        findings=[
            _minor_finding(disposition="accepted", reason="tracked for a later phase")
        ],
        counts={"critical": 0, "major": 0, "minor": 1},
    )
    errors = _findings_errors(tmp_path, report, require_major=True)
    assert not any("disposition" in error for error in errors)


def test_minor_disposition_is_not_required_outside_phase_completion(
    tmp_path: Path,
) -> None:
    """Non-completion validation (require_major=False) does not demand a
    MINOR disposition; that contract is phase-completion-specific."""
    report = _findings_report(
        findings=[_minor_finding()], counts={"critical": 0, "major": 0, "minor": 1}
    )
    errors = _findings_errors(tmp_path, report, require_major=False)
    assert not any("disposition" in error for error in errors)


def test_forged_counts_inconsistent_with_findings_are_rejected(tmp_path: Path) -> None:
    """An independently asserted count must match the derived finding list."""
    report = _findings_report(
        findings=[_minor_finding(disposition="accepted", reason="tracked")],
        counts={"critical": 0, "major": 0, "minor": 0},
    )
    errors = _findings_errors(tmp_path, report, require_major=True)
    assert "findings report counts do not match findings" in errors


def _git(args: list[str], cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def _init_repo(root: Path) -> None:
    _git(["init", "-q"], root)
    _git(["config", "user.email", "test@example.com"], root)
    _git(["config", "user.name", "Test"], root)


def _commit_all(root: Path, message: str) -> str:
    """Commit the current working tree (or an empty commit) and return its sha."""
    _git(["add", "-A"], root)
    _git(["commit", "-q", "--allow-empty", "-m", message], root)
    return _git(["rev-parse", "HEAD"], root)


def _write_big_plan(root: Path, *, slug: str, phases: list[str]) -> None:
    plans = root / ".claude" / "plans"
    plans.mkdir(parents=True, exist_ok=True)
    phase_lines = "\n".join(f"  - {phase}" for phase in phases)
    (plans / f"{slug}.md").write_text(
        "---\n"
        f"name: {slug}\n"
        "type: big-plan\n"
        "status: in-progress\n"
        "originating_branch: dev\n"
        f"implementation_branch: {slug}_implementation\n"
        "phases:\n"
        f"{phase_lines}\n"
        f"current_phase: {phases[-1]}\n"
        "---\n\n# Big Plan\n",
        encoding="utf-8",
    )


def _historical_metadata(
    *, branch: str, phase: str, head_sha: str, tree_sha: str
) -> dict[str, object]:
    metadata = _metadata()
    metadata.update(
        {"branch": branch, "phase": phase, "head_sha": head_sha, "tree_sha": tree_sha}
    )
    metadata["control_plane_provenance"] = {
        "schema_version": verify.CONTROL_PLANE_PROVENANCE_SCHEMA_VERSION,
        "nested_head": "a" * 40,
        "runtime_fingerprint": "b" * 64,
        "tracked_state_fingerprint": "c" * 64,
        "big_plan_digest": "d" * 64,
        "small_plan_digest": "e" * 64,
    }
    return metadata


def _write_historical_phase(
    root: Path,
    *,
    branch: str,
    phase: str,
    parent_plan: str,
    head_sha: str,
    tree_sha: str,
) -> None:
    """Write one complete, hash-consistent historical completed-phase fixture."""
    plans = root / ".claude" / "plans"
    reports = root / ".claude" / "quality_reports"
    logs = root / ".claude" / "session_logs"
    for directory in (plans, reports, logs):
        directory.mkdir(parents=True, exist_ok=True)

    (plans / f"{phase}.md").write_text(
        "---\n"
        f"name: {phase}\n"
        "type: small-plan\n"
        f"parent_plan: {parent_plan}\n"
        "phase_index: 1\n"
        "status: complete\n"
        f"closeout_session_log: .claude/session_logs/{phase}-closeout.md\n"
        "---\n\n# Phase\n",
        encoding="utf-8",
    )
    phase_receipt_bytes = f"phase-receipt-for-{phase}\n".encode()
    findings_bytes = json.dumps(
        {"findings": [], "counts": {"critical": 0, "major": 0, "minor": 0}}
    ).encode()
    log_bytes = b"**Status:** COMPLETED\n"
    (reports / f"verification-phase-{phase}.json").write_bytes(phase_receipt_bytes)
    (reports / f"findings-{phase}.json").write_bytes(findings_bytes)
    (logs / f"{phase}-closeout.md").write_bytes(log_bytes)

    checks = [
        verify.not_applicable(check_id, "closeout reuses phase evidence")
        if check_id in {"VFY-RUFF-001", "VFY-MYPY-001", "VFY-PYTEST-001", "VFY-GEN-001"}
        else verify.check(check_id, "PASS", "measured")
        for check_id in verify.CHECK_IDS
    ]
    receipt = verify.build_receipt(
        "closeout",
        checks,
        _historical_metadata(
            branch=branch, phase=phase, head_sha=head_sha, tree_sha=tree_sha
        ),
        {
            "phase_receipt": {
                "path": f".claude/quality_reports/verification-phase-{phase}.json",
                "sha256": hashlib.sha256(phase_receipt_bytes).hexdigest(),
            },
            "findings": {
                "path": f".claude/quality_reports/findings-{phase}.json",
                "sha256": hashlib.sha256(findings_bytes).hexdigest(),
            },
            "closeout_log": {
                "path": f".claude/session_logs/{phase}-closeout.md",
                "sha256": hashlib.sha256(log_bytes).hexdigest(),
            },
            "documentation": {"status": "NOT_APPLICABLE", "reason": "no docs changed"},
        },
    )
    (reports / f"verification-closeout-{phase}.json").write_text(
        json.dumps(receipt), encoding="utf-8"
    )


def _historical_chain_fixture(tmp_path: Path) -> tuple[str, str]:
    """Build one valid two-phase historical chain; return (parent_sha, sha_b).

    Mirrors the real closeout lifecycle: a phase's closeout receipt is
    generated before its completion commit (stage everything, generate
    reports and receipts, then commit), so the receipt's ``head_sha`` is the
    *parent* commit and ``tree_sha`` is the tree of the commit that phase's
    completion commit actually introduced - never the same commit's own
    tree. Real file changes are committed at each step so the parent,
    phase-one, and phase-two trees are genuinely distinct.
    """
    _init_repo(tmp_path)
    parent_sha = _commit_all(tmp_path, "base commit")
    (tmp_path / "phase-one.txt").write_text("phase one content\n", encoding="utf-8")
    sha_a = _commit_all(tmp_path, "phase one commit")
    (tmp_path / "phase-two.txt").write_text("phase two content\n", encoding="utf-8")
    sha_b = _commit_all(tmp_path, "phase two commit")
    _write_big_plan(tmp_path, slug="big", phases=["phase-one", "phase-two"])
    _write_historical_phase(
        tmp_path,
        branch="big_implementation",
        phase="phase-one",
        parent_plan="big",
        head_sha=parent_sha,
        tree_sha=_git(["rev-parse", f"{sha_a}^{{tree}}"], tmp_path),
    )
    return parent_sha, sha_b


def test_historical_chain_accepts_ordered_completed_phase(tmp_path: Path) -> None:
    """A single earlier completed phase, built the way the real lifecycle
    produces it - head_sha is the phase's parent commit, tree_sha is the
    tree its own completion commit introduced, not head_sha's own tree -
    produces no historical chain errors."""
    _, sha_b = _historical_chain_fixture(tmp_path)
    errors = verify.historical_chain_errors(
        tmp_path, branch="big_implementation", phase="phase-two", receipt_head=sha_b
    )
    assert errors == []


def test_historical_chain_rejects_missing_receipt_head(tmp_path: Path) -> None:
    """A historical receipt whose head_sha does not resolve to a commit fails."""
    _, sha_b = _historical_chain_fixture(tmp_path)
    receipt_path = (
        tmp_path / ".claude/quality_reports/verification-closeout-phase-one.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["metadata"]["head_sha"] = "0" * 40
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    errors = verify.historical_chain_errors(
        tmp_path, branch="big_implementation", phase="phase-two", receipt_head=sha_b
    )
    assert any("does not resolve to a commit" in error for error in errors)


def test_historical_chain_rejects_missing_receipt_file(tmp_path: Path) -> None:
    """A completed historical phase with no closeout receipt at all must fail
    closed. This is the legacy/migration boundary: a phase predating receipts
    gets no implicit pass from the terminal receipt covering it."""
    _, sha_b = _historical_chain_fixture(tmp_path)
    receipt_path = (
        tmp_path / ".claude/quality_reports/verification-closeout-phase-one.json"
    )
    receipt_path.unlink()
    errors = verify.historical_chain_errors(
        tmp_path, branch="big_implementation", phase="phase-two", receipt_head=sha_b
    )
    assert any("phase-one receipt is invalid" in error for error in errors)


def test_historical_chain_rejects_tree_sha_mismatch(tmp_path: Path) -> None:
    """A historical receipt whose tree_sha matches nothing real must fail."""
    _, sha_b = _historical_chain_fixture(tmp_path)
    receipt_path = (
        tmp_path / ".claude/quality_reports/verification-closeout-phase-one.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["metadata"]["tree_sha"] = "f" * 40
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    errors = verify.historical_chain_errors(
        tmp_path, branch="big_implementation", phase="phase-two", receipt_head=sha_b
    )
    assert any(
        "tree_sha does not match the tree introduced by its certified completion "
        "commit" in error
        for error in errors
    )


def test_historical_chain_rejects_certified_commit_tree_mismatch(
    tmp_path: Path,
) -> None:
    """A historical receipt's tree_sha must match the tree its certified
    completion commit introduced, not the tree of head_sha itself. head_sha
    is the *parent* of the commit the receipt certifies (receipts are
    generated before their completion commit), so a receipt that instead
    claims head_sha's own tree - the old, wrong assumption this check used
    to make - is rejected."""
    parent_sha, sha_b = _historical_chain_fixture(tmp_path)
    receipt_path = (
        tmp_path / ".claude/quality_reports/verification-closeout-phase-one.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["metadata"]["tree_sha"] = _git(
        ["rev-parse", f"{parent_sha}^{{tree}}"], tmp_path
    )
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    errors = verify.historical_chain_errors(
        tmp_path, branch="big_implementation", phase="phase-two", receipt_head=sha_b
    )
    assert any(
        "tree_sha does not match the tree introduced by its certified completion "
        "commit" in error
        for error in errors
    )


def test_historical_chain_accepts_real_lifecycle_receipt(tmp_path: Path) -> None:
    """Reproduces the exact real-lifecycle window: stage a phase's changes,
    capture tree_sha via ``git write-tree`` against that dirty index while
    head_sha is still the parent commit (as closeout does, since receipts
    are generated before the completion commit), then commit. The resulting
    receipt must be accepted once its staged tree becomes a real commit."""
    _init_repo(tmp_path)
    parent_sha = _commit_all(tmp_path, "base commit")
    (tmp_path / "phase-one.txt").write_text("phase one content\n", encoding="utf-8")
    _git(["add", "-A"], tmp_path)
    staged_tree = _git(["write-tree"], tmp_path)
    _write_big_plan(tmp_path, slug="big", phases=["phase-one", "phase-two"])
    _write_historical_phase(
        tmp_path,
        branch="big_implementation",
        phase="phase-one",
        parent_plan="big",
        head_sha=parent_sha,
        tree_sha=staged_tree,
    )
    _git(["commit", "-q", "-m", "phase one commit"], tmp_path)
    sha_a = _git(["rev-parse", "HEAD"], tmp_path)
    assert _git(["rev-parse", f"{sha_a}^{{tree}}"], tmp_path) == staged_tree
    (tmp_path / "phase-two.txt").write_text("phase two content\n", encoding="utf-8")
    sha_b = _commit_all(tmp_path, "phase two commit")
    errors = verify.historical_chain_errors(
        tmp_path, branch="big_implementation", phase="phase-two", receipt_head=sha_b
    )
    assert errors == []


def test_historical_chain_rejects_tampered_artifact_bytes(tmp_path: Path) -> None:
    """Changed findings bytes since the historical receipt was bound must fail."""
    _, sha_b = _historical_chain_fixture(tmp_path)
    findings_path = tmp_path / ".claude/quality_reports/findings-phase-one.json"
    findings_path.write_text('{"tampered": true}', encoding="utf-8")
    errors = verify.historical_chain_errors(
        tmp_path, branch="big_implementation", phase="phase-two", receipt_head=sha_b
    )
    assert any("was tampered with" in error for error in errors)


def test_historical_chain_rejects_reversed_phase_order(tmp_path: Path) -> None:
    """Two earlier completed phases whose actual commit order contradicts the
    big plan's declared phase order fail the chain, even though each
    individual receipt is otherwise well-formed on its own."""
    _init_repo(tmp_path)
    sha_two = _commit_all(tmp_path, "phase two commit")  # completed first in history
    sha_one = _commit_all(
        tmp_path, "phase one commit"
    )  # declared first, completed second
    sha_three = _commit_all(tmp_path, "phase three commit")
    _write_big_plan(
        tmp_path, slug="big", phases=["phase-one", "phase-two", "phase-three"]
    )
    _write_historical_phase(
        tmp_path,
        branch="big_implementation",
        phase="phase-one",
        parent_plan="big",
        head_sha=sha_one,
        tree_sha=_git(["rev-parse", f"{sha_one}^{{tree}}"], tmp_path),
    )
    _write_historical_phase(
        tmp_path,
        branch="big_implementation",
        phase="phase-two",
        parent_plan="big",
        head_sha=sha_two,
        tree_sha=_git(["rev-parse", f"{sha_two}^{{tree}}"], tmp_path),
    )
    errors = verify.historical_chain_errors(
        tmp_path,
        branch="big_implementation",
        phase="phase-three",
        receipt_head=sha_three,
    )
    assert any("is not an ancestor of" in error for error in errors)


def test_gate_receipt_errors_wires_in_historical_chain_validation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The public gate entrypoint - not just the internal helper - calls the
    historical chain validator once a terminal receipt head is known."""
    receipt = _closeout_receipt()
    metadata = receipt["metadata"]
    assert isinstance(metadata, dict)
    branch, phase, head = metadata["branch"], metadata["phase"], metadata["head_sha"]
    assert isinstance(branch, str) and isinstance(phase, str) and isinstance(head, str)
    closeout_path = verify.receipt_path(tmp_path, "closeout", phase)
    closeout_path.parent.mkdir(parents=True)
    closeout_path.write_text(json.dumps(receipt), encoding="utf-8")

    monkeypatch.setattr(
        verify, "historical_chain_errors", lambda *a, **k: ["SENTINEL-HISTORICAL-ERROR"]
    )
    errors = verify.gate_receipt_errors(
        tmp_path,
        branch=branch,
        phase=phase,
        head=head,
        head_relation="exact",
        require_major=False,
        require_ponytail=False,
        enforce_final_state=False,
    )
    assert "SENTINEL-HISTORICAL-ERROR" in errors


def test_historical_chain_rejects_ancestor_failure(tmp_path: Path) -> None:
    """A historical receipt head that is not an ancestor of the next
    completed phase's head fails the chain."""
    _init_repo(tmp_path)
    sha_a = _commit_all(tmp_path, "phase one commit")
    # sha_b is a sibling branch commit, not a descendant of sha_a.
    _git(["checkout", "-q", "--orphan", "sibling"], tmp_path)
    sha_b = _commit_all(tmp_path, "unrelated sibling commit")
    _write_big_plan(tmp_path, slug="big", phases=["phase-one", "phase-two"])
    _write_historical_phase(
        tmp_path,
        branch="big_implementation",
        phase="phase-one",
        parent_plan="big",
        head_sha=sha_a,
        # Deliberately never read: the ancestor check runs before the tree
        # check, so this value must not matter. A sentinel makes that explicit
        # and fails loudly if the check order ever changes, rather than quietly
        # depending on the old tree_sha == head_sha^{tree} assumption.
        tree_sha="0" * 40,
    )
    errors = verify.historical_chain_errors(
        tmp_path, branch="big_implementation", phase="phase-two", receipt_head=sha_b
    )
    assert any("is not an ancestor of" in error for error in errors)


@pytest.mark.parametrize(
    "updates",
    (
        {"ponytail_reviewed": True, "ponytail_findings": 0},
        {"profiles_reviewed": ["code", "ponytail"]},
        {
            "profiles_reviewed": ["code", "ponytail"],
            "ponytail_reviewed": True,
            "ponytail_findings": 1,
        },
    ),
    ids=("profile-missing", "authority-missing", "count-mismatch"),
)
def test_findings_rejects_contradictory_ponytail_metadata(
    tmp_path: Path, updates: dict[str, object]
) -> None:
    """Ponytail authority must agree with selected profiles and findings."""
    errors = _findings_errors(tmp_path, _findings_report(**updates))
    assert any("Ponytail" in error for error in errors)


@pytest.mark.parametrize(
    "mutate",
    (
        lambda receipt: receipt.pop("metadata"),
        lambda receipt: receipt["checks"].pop(),
        lambda receipt: receipt["checks"].__setitem__(
            0, {**receipt["checks"][0], "status": "MAYBE"}
        ),
        lambda receipt: receipt["checks"].__setitem__(
            0, {**receipt["checks"][0], "status": "NOT_APPLICABLE"}
        ),
    ),
    ids=("missing-field", "missing-check", "unknown-status", "freeform-na"),
)
def test_receipt_validation_rejects_malformed_required_contract(
    mutate: object,
) -> None:
    """Strict receipts reject omitted checks, unknown states, and free-form N/A."""
    receipt = _receipt()
    mutate(receipt)  # type: ignore[operator]
    with pytest.raises(ValueError):
        verify.validate_receipt(receipt)


def test_closeout_receipt_rejects_missing_or_unsafe_artifact_references() -> None:
    """Completed evidence has exact, safe references instead of report discovery."""
    receipt = _closeout_receipt()
    artifacts = receipt["artifacts"]
    assert isinstance(artifacts, dict)
    artifacts["findings"] = {"path": "../findings.json", "sha256": "a" * 64}
    with pytest.raises(ValueError, match="artifact findings is invalid"):
        verify.validate_receipt(receipt)


@pytest.mark.parametrize(
    ("stdout", "returncode", "expected"),
    (
        ("", 1, "UNVERIFIED"),
        ("not json", 1, "UNVERIFIED"),
        ("[]", 0, "PASS"),
        ("[]", 1, "UNVERIFIED"),
    ),
    ids=("empty-nonzero", "malformed-json", "clean-json", "empty-failure"),
)
def test_ruff_measurement_is_fail_closed(
    monkeypatch: pytest.MonkeyPatch, stdout: str, returncode: int, expected: str
) -> None:
    """Ruff cannot turn a failed or malformed measurement into PASS."""
    monkeypatch.setattr(
        verify, "_run", lambda *_args, **_kwargs: (returncode, stdout, "")
    )
    result = verify.measure_ruff(REPO_ROOT, ["shared"])
    assert result["status"] == expected


def test_ruff_missing_executable_is_unverified(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing verification tool is unverified rather than clean."""
    monkeypatch.setattr(
        verify,
        "_run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileNotFoundError("uv")),
    )
    assert verify.measure_ruff(REPO_ROOT, ["shared"])["status"] == "UNVERIFIED"


def test_timeout_is_unverified(monkeypatch: pytest.MonkeyPatch) -> None:
    """A timed out command cannot be accepted as a passing check."""
    monkeypatch.setattr(
        verify,
        "_run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            subprocess.TimeoutExpired(["uv"], 1)
        ),
    )
    assert verify.measure_ruff(REPO_ROOT, ["shared"])["status"] == "UNVERIFIED"


def test_mypy_abnormal_exit_is_unverified(monkeypatch: pytest.MonkeyPatch) -> None:
    """mypy operational failures remain distinct from type errors."""
    monkeypatch.setattr(
        verify,
        "_run",
        lambda *_args, **_kwargs: (2, "", "internal error"),
    )
    assert verify.measure_mypy(REPO_ROOT, ["shared"])["status"] == "UNVERIFIED"


def test_pytest_infrastructure_exit_is_unverified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """pytest collection/tool errors are not represented as ordinary failures."""
    monkeypatch.setattr(
        verify,
        "_run",
        lambda *_args, **_kwargs: (2, "", "collection error"),
    )
    assert verify.measure_pytest(REPO_ROOT)["status"] == "UNVERIFIED"


@pytest.mark.parametrize(
    ("stdout", "expected"),
    (
        ("12 passed in 0.34s", "12 passed in 0.34s"),
        ("===== 3 failed, 9 passed in 1.02s =====", "3 failed, 9 passed in 1.02s"),
        ("5 passed, 1 skipped in 0.12s", "5 passed, 1 skipped in 0.12s"),
        ("no summary line here", ""),
    ),
    ids=("passed", "failed-and-passed", "skipped", "no-match"),
)
def test_pytest_result_summary_extracts_trailing_counts(
    stdout: str, expected: str
) -> None:
    """The pytest detail line carries a test count, matching ruff/mypy."""
    assert verify._pytest_result_summary(stdout) == expected


def test_pytest_measurement_includes_test_count_in_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A passing pytest measurement reports its count, like ruff/mypy do."""
    monkeypatch.setattr(
        verify, "_run", lambda *_args, **_kwargs: (0, "12 passed in 0.34s\n", "")
    )
    status, detail = verify._pytest_measurement(cwd=".")
    assert status == "PASS"
    assert detail == "pytest completed (12 passed in 0.34s)"


def test_closeout_rejects_stale_relevant_evidence(tmp_path: Path) -> None:
    """Code/config/control evidence is stale when its scoped fingerprint changes."""
    phase_path = verify.receipt_path(tmp_path, "phase", "phase-one")
    phase_path.parent.mkdir(parents=True)
    phase_path.write_text(json.dumps(_receipt(content_hash="old")), encoding="utf-8")
    checks = verify.closeout_checks(tmp_path, _metadata(content_hash="new"))
    fresh = next(item for item in checks if item["id"] == "VFY-FRESH-001")
    assert fresh["status"] == "FAIL"


def test_closeout_rejects_tampered_phase_receipt(tmp_path: Path) -> None:
    """Malformed referenced evidence cannot produce a closeout PASS."""
    phase_path = verify.receipt_path(tmp_path, "phase", "phase-one")
    phase_path.parent.mkdir(parents=True)
    receipt = _receipt()
    receipt["checks"][0]["unexpected"] = "edited after measurement"  # type: ignore[index]
    phase_path.write_text(json.dumps(receipt), encoding="utf-8")
    checks = verify.closeout_checks(tmp_path, _metadata())
    reused = next(item for item in checks if item["id"] == "VFY-RECEIPT-001")
    assert reused["status"] == "FAIL"


def test_closeout_rejects_non_passing_phase_receipt(tmp_path: Path) -> None:
    """A closeout receipt cannot reuse phase evidence that recorded a failure."""
    phase_path = verify.receipt_path(tmp_path, "phase", "phase-one")
    phase_path.parent.mkdir(parents=True)
    phase = _receipt()
    checks = phase["checks"]
    assert isinstance(checks, list) and isinstance(checks[0], dict)
    checks[0] = {**checks[0], "status": "FAIL", "summary": "measurement failed"}
    phase["status"] = "FAIL"
    phase_path.write_text(json.dumps(phase), encoding="utf-8")
    checks = verify.closeout_checks(tmp_path, _metadata())
    reused = next(item for item in checks if item["id"] == "VFY-RECEIPT-001")
    assert reused["status"] == "FAIL"


def test_closeout_rejects_different_git_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Equal diff hashes do not cross branch/base/head freshness boundaries."""
    phase_path = verify.receipt_path(tmp_path, "phase", "phase-one")
    phase_path.parent.mkdir(parents=True)
    phase = _receipt()
    phase_path.write_text(json.dumps(phase), encoding="utf-8")
    monkeypatch.setattr(verify, "phase_checks", lambda *_args: phase["checks"])
    current = _metadata()
    current["merge_base_sha"] = "different-base"
    checks = verify.closeout_checks(tmp_path, current)
    fresh = next(item for item in checks if item["id"] == "VFY-FRESH-001")
    assert fresh["status"] == "FAIL"


def test_closeout_rejects_stale_control_plane_provenance(tmp_path: Path) -> None:
    """Changing a governing runtime or plan fingerprint stales phase evidence."""
    phase_path = verify.receipt_path(tmp_path, "phase", "phase-one")
    phase_path.parent.mkdir(parents=True)
    phase_path.write_text(json.dumps(_receipt()), encoding="utf-8")
    current = _metadata()
    provenance = current["control_plane_provenance"]
    assert isinstance(provenance, dict)
    current["control_plane_provenance"] = {
        **provenance,
        "runtime_fingerprint": "d" * 64,
    }

    checks = verify.closeout_checks(tmp_path, current)

    fresh = next(item for item in checks if item["id"] == "VFY-FRESH-002")
    assert fresh["status"] == "FAIL"


def test_control_plane_provenance_binds_runtime_and_active_plans(
    tmp_path: Path,
) -> None:
    """Nested runtime and active plan changes invalidate only governing evidence."""
    nested = tmp_path / ".claude"
    plans = nested / "plans"
    (nested / "scripts").mkdir(parents=True)
    plans.mkdir()
    _write_root_adapter_pairs(tmp_path)
    (nested / "scripts" / "verify.py").write_text("runtime = 1\n", encoding="utf-8")
    big_plan = plans / "consumer-proof.md"
    small_plan = plans / "phase-one.md"
    big_plan.write_text(
        "status: in-progress\ncurrent_phase: phase-one\n", encoding="utf-8"
    )
    small_plan.write_text("status: in-progress\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=nested, check=True)
    subprocess.run(["git", "add", "."], cwd=nested, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Verifier",
            "-c",
            "user.email=verifier@example.com",
            "commit",
            "-qm",
            "runtime",
        ],
        cwd=nested,
        check=True,
    )

    before = verify.control_plane_provenance(
        tmp_path, "consumer-proof_implementation", "phase-one"
    )
    assert verify.has_control_plane_provenance(
        {"branch": "consumer-proof_implementation", "control_plane_provenance": before}
    )

    (nested / "quality_reports").mkdir()
    (nested / "quality_reports" / "score.json").write_text(
        "mutable\n", encoding="utf-8"
    )
    subprocess.run(["git", "add", "quality_reports/score.json"], cwd=nested, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "evidence"],
        cwd=nested,
        check=True,
    )
    after_evidence = verify.control_plane_provenance(
        tmp_path, "consumer-proof_implementation", "phase-one"
    )
    assert after_evidence["nested_head"] != before["nested_head"]
    assert verify.control_plane_provenance_matches(
        {"branch": "consumer-proof_implementation", "control_plane_provenance": before},
        {
            "branch": "consumer-proof_implementation",
            "control_plane_provenance": after_evidence,
        },
    )

    runtime_file = nested / "scripts" / "verify.py"
    runtime_file.write_text("runtime = staged\n", encoding="utf-8")
    subprocess.run(["git", "add", "scripts/verify.py"], cwd=nested, check=True)
    runtime_file.write_text("runtime = 1\n", encoding="utf-8")
    index_only = verify.control_plane_provenance(
        tmp_path, "consumer-proof_implementation", "phase-one"
    )
    assert index_only["runtime_fingerprint"] == before["runtime_fingerprint"]
    assert (
        index_only["tracked_state_fingerprint"] != before["tracked_state_fingerprint"]
    )
    subprocess.run(["git", "add", "scripts/verify.py"], cwd=nested, check=True)

    original_small_plan = small_plan.read_text(encoding="utf-8")
    small_plan.write_text("status: staged\n", encoding="utf-8")
    subprocess.run(["git", "add", "plans/phase-one.md"], cwd=nested, check=True)
    small_plan.write_text(original_small_plan, encoding="utf-8")
    staged_plan = verify.control_plane_provenance(
        tmp_path, "consumer-proof_implementation", "phase-one"
    )
    assert staged_plan["small_plan_digest"] == before["small_plan_digest"]
    assert (
        staged_plan["tracked_state_fingerprint"] != before["tracked_state_fingerprint"]
    )
    subprocess.run(["git", "add", "plans/phase-one.md"], cwd=nested, check=True)

    small_plan.write_text("status: complete\n", encoding="utf-8")
    plan_changed = verify.control_plane_provenance(
        tmp_path, "consumer-proof_implementation", "phase-one"
    )
    assert plan_changed["small_plan_digest"] != before["small_plan_digest"]
    assert plan_changed["runtime_fingerprint"] == before["runtime_fingerprint"]

    runtime_file.write_text("runtime = 2\n", encoding="utf-8")
    runtime_changed = verify.control_plane_provenance(
        tmp_path, "consumer-proof_implementation", "phase-one"
    )
    assert runtime_changed["runtime_fingerprint"] != before["runtime_fingerprint"]
    assert (
        runtime_changed["tracked_state_fingerprint"]
        != before["tracked_state_fingerprint"]
    )


def test_control_plane_provenance_binds_owned_live_root_adapters(
    tmp_path: Path,
) -> None:
    """Every manifest-owned live root adapter must equal its nested mirror."""
    nested = tmp_path / ".claude"
    plans = nested / "plans"
    plans.mkdir(parents=True)
    (nested / "scripts").mkdir()
    (nested / "scripts" / "verify.py").write_text("runtime = 1\n", encoding="utf-8")
    (plans / "consumer-proof.md").write_text("big plan\n", encoding="utf-8")
    (plans / "phase-one.md").write_text("small plan\n", encoding="utf-8")
    adapters = {
        "CLAUDE.md": "claude\n",
        "AGENTS.md": "agents\n",
        ".mcp.json": "{}\n",
        ".codex/hooks.json": "{}\n",
        ".agents/agents/coder.md": "coder\n",
        ".vscode/mcp.json": "{}\n",
        ".github/hooks/hooks.json": "{}\n",
    }
    _write_root_adapter_pairs(tmp_path, mode=False)
    for relative, content in adapters.items():
        for base in (tmp_path, nested / "bootstrap-root"):
            path = base / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=nested, check=True)
    subprocess.run(["git", "add", "."], cwd=nested, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Verifier",
            "-c",
            "user.email=verifier@example.com",
            "commit",
            "-qm",
            "runtime",
        ],
        cwd=nested,
        check=True,
    )

    before = verify.control_plane_provenance(
        tmp_path, "consumer-proof_implementation", "phase-one"
    )
    metadata: dict[str, object] = {
        "branch": "consumer-proof_implementation",
        "control_plane_provenance": before,
    }
    assert verify.has_control_plane_provenance(metadata)

    for relative, content in adapters.items():
        live = tmp_path / relative
        live.write_text(content + "drift\n", encoding="utf-8")
        after = verify.control_plane_provenance(
            tmp_path, "consumer-proof_implementation", "phase-one"
        )
        assert not verify.control_plane_provenance_matches(
            metadata, {**metadata, "control_plane_provenance": after}
        )
        live.write_text(content, encoding="utf-8")

    (tmp_path / ".mcp.json").unlink()
    assert not verify.has_control_plane_provenance(
        {
            **metadata,
            "control_plane_provenance": verify.control_plane_provenance(
                tmp_path, "consumer-proof_implementation", "phase-one"
            ),
        }
    )
    (tmp_path / ".mcp.json").mkdir()
    assert not verify.has_control_plane_provenance(
        {
            **metadata,
            "control_plane_provenance": verify.control_plane_provenance(
                tmp_path, "consumer-proof_implementation", "phase-one"
            ),
        }
    )
    (tmp_path / ".mcp.json").rmdir()
    (tmp_path / ".mcp.json").symlink_to(nested / "bootstrap-root" / ".mcp.json")
    assert not verify.has_control_plane_provenance(
        {
            **metadata,
            "control_plane_provenance": verify.control_plane_provenance(
                tmp_path, "consumer-proof_implementation", "phase-one"
            ),
        }
    )


@pytest.mark.parametrize(
    ("mode", "manifest"),
    (
        (True, "BOOTSTRAP_COMMIT_COPILOT_SURFACE=1\nBOOTSTRAP_ROOT_PATH=.mcp.json\n"),
        (
            False,
            "BOOTSTRAP_COMMIT_COPILOT_SURFACE=0\n"
            "BOOTSTRAP_ROOT_PATH=.mcp.json\nBOOTSTRAP_ROOT_PATH=foreign\n",
        ),
    ),
)
def test_root_adapter_manifest_requires_complete_mode_inventory(
    tmp_path: Path, mode: bool, manifest: str
) -> None:
    """Incomplete or foreign root ownership records cannot establish provenance."""
    _write_root_adapter_pairs(tmp_path, mode)
    (tmp_path / ".claude" / "bootstrap-ownership.env").write_text(
        manifest, encoding="utf-8"
    )

    assert verify.manifest_bootstrap_root_paths(tmp_path) is None


@pytest.mark.parametrize("mirror", (False, True))
def test_root_adapter_rejects_ancestor_symlink_escape(
    tmp_path: Path, mirror: bool
) -> None:
    """A link in either adapter ancestry cannot redirect hashing outside the repo."""
    _write_root_adapter_pairs(tmp_path)
    ancestor = (
        tmp_path / ".claude" / "bootstrap-root" / ".codex"
        if mirror
        else tmp_path / ".codex"
    )
    outside = tmp_path / "outside"
    outside.mkdir()
    shutil.rmtree(ancestor)
    ancestor.symlink_to(outside, target_is_directory=True)

    assert verify.bootstrap_root_fingerprint(tmp_path) == ""


@pytest.mark.parametrize(
    "replacement",
    (
        "name: wrong-phase",
        "parent_plan: another-plan",
        "phase_index: not-a-number",
        "status: in-progress",
        "closeout_session_log:",
        "closeout_session_log: ../escape.md",
        "type:\n  - small-plan",
    ),
)
def test_terminal_small_plan_requires_complete_well_formed_identity(
    replacement: str,
) -> None:
    """Terminal exceptions accept only the receipt's complete current plan."""
    source = (
        "---\nname: phase-one\ntype: small-plan\nparent_plan: consumer-proof\n"
        "phase_index: 1\nstatus: complete\n"
        "closeout_session_log: .claude/session_logs/phase-one.md\n---\n"
    )
    key = replacement.partition(":")[0]
    original = next(line for line in source.splitlines() if line.startswith(f"{key}:"))
    assert not verify.is_complete_small_plan(
        source.replace(original, replacement).encode(), "phase-one", "consumer-proof"
    )


def test_terminal_plan_transition_provenance(
    tmp_path: Path,
) -> None:
    """Only the hook's unstaged final-plan transition may follow closeout."""
    nested = tmp_path / ".claude"
    plans = nested / "plans"
    (nested / "scripts").mkdir(parents=True)
    plans.mkdir()
    _write_root_adapter_pairs(tmp_path)
    (nested / "scripts" / "verify.py").write_text("runtime = 1\n", encoding="utf-8")
    big_plan = plans / "consumer-proof.md"
    big_plan.write_text(
        """---
name: consumer-proof
type: big-plan
status: in-progress
current_phase: phase-one
phases:
  - phase-one
review_profiles:
  - code
  - security
---
""",
        encoding="utf-8",
    )
    (plans / "phase-one.md").write_text(
        "---\nname: phase-one\ntype: small-plan\nparent_plan: consumer-proof\n"
        "phase_index: 1\nstatus: complete\n"
        "closeout_session_log: .claude/session_logs/phase-one.md\n---\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=nested, check=True)
    subprocess.run(["git", "add", "."], cwd=nested, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Verifier",
            "-c",
            "user.email=verifier@example.com",
            "commit",
            "-qm",
            "closeout state",
        ],
        cwd=nested,
        check=True,
    )

    before = verify.control_plane_provenance(
        tmp_path, "consumer-proof_implementation", "phase-one"
    )
    metadata: dict[str, object] = {
        "branch": "consumer-proof_implementation",
        "control_plane_provenance": before,
    }
    big_plan.write_text(
        big_plan.read_text(encoding="utf-8")
        .replace("status: in-progress", "status: complete")
        .replace("current_phase: phase-one", "current_phase: "),
        encoding="utf-8",
    )
    terminal = verify.control_plane_provenance(
        tmp_path, "consumer-proof_implementation", "phase-one"
    )
    assert verify.has_only_terminal_big_plan_change(
        tmp_path, "consumer-proof_implementation", "phase-one", metadata
    )
    assert verify.terminal_control_plane_provenance_matches(
        tmp_path,
        "consumer-proof_implementation",
        "phase-one",
        metadata,
        {**metadata, "control_plane_provenance": terminal},
    )

    big_plan.write_text(big_plan.read_text(encoding="utf-8") + "# changed\n")
    assert not verify.terminal_control_plane_provenance_matches(
        tmp_path,
        "consumer-proof_implementation",
        "phase-one",
        metadata,
        {
            **metadata,
            "control_plane_provenance": verify.control_plane_provenance(
                tmp_path, "consumer-proof_implementation", "phase-one"
            ),
        },
    )

    subprocess.run(["git", "checkout", "--", "plans"], cwd=nested, check=True)
    phase_one = plans / "phase-one.md"
    phase_one.write_text(
        "---\nname: phase-one\ntype: small-plan\nparent_plan: consumer-proof\n"
        "phase_index: 1\nstatus: in-progress\n---\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "plans/phase-one.md"], cwd=nested, check=True)
    subprocess.run(["git", "commit", "-qm", "unfinished phase"], cwd=nested, check=True)
    unfinished_metadata: dict[str, object] = {
        "branch": "consumer-proof_implementation",
        "control_plane_provenance": verify.control_plane_provenance(
            tmp_path, "consumer-proof_implementation", "phase-one"
        ),
    }
    big_plan.write_text(
        big_plan.read_text(encoding="utf-8")
        .replace("status: in-progress", "status: complete")
        .replace("current_phase: phase-one", "current_phase: "),
        encoding="utf-8",
    )
    assert not verify.terminal_control_plane_provenance_matches(
        tmp_path,
        "consumer-proof_implementation",
        "phase-one",
        unfinished_metadata,
        {
            **unfinished_metadata,
            "control_plane_provenance": verify.control_plane_provenance(
                tmp_path, "consumer-proof_implementation", "phase-one"
            ),
        },
    )

    subprocess.run(["git", "checkout", "--", "plans"], cwd=nested, check=True)
    big_plan.write_text(
        big_plan.read_text(encoding="utf-8").replace(
            "  - phase-one", "  - phase-one\n  - phase-two"
        ),
        encoding="utf-8",
    )
    phase_one.write_text(
        "---\nname: phase-one\ntype: small-plan\nparent_plan: consumer-proof\n"
        "phase_index: 1\nstatus: complete\n"
        "closeout_session_log: .claude/session_logs/phase-one.md\n---\n",
        encoding="utf-8",
    )
    phase_two = plans / "phase-two.md"
    cancelled_evidence = nested / "session_logs" / "phase-two-cancelled.md"
    cancelled_evidence.parent.mkdir(exist_ok=True)
    cancelled_evidence.write_text("**Status:** CANCELLED\n", encoding="utf-8")
    phase_two.write_text(
        "---\nname: phase-two\ntype: small-plan\nparent_plan: consumer-proof\n"
        "phase_index: 2\nstatus: cancelled\n"
        "cancelled_at: 2026-08-31T00:00:00Z\n"
        "cancelled_reason: Later work is no longer needed\n"
        "cancelled_evidence: .claude/session_logs/phase-two-cancelled.md\n---\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "plans"], cwd=nested, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "terminal precondition"], cwd=nested, check=True
    )
    later_metadata: dict[str, object] = {
        "branch": "consumer-proof_implementation",
        "control_plane_provenance": verify.control_plane_provenance(
            tmp_path, "consumer-proof_implementation", "phase-one"
        ),
    }
    big_plan.write_text(
        big_plan.read_text(encoding="utf-8")
        .replace("status: in-progress", "status: complete")
        .replace("current_phase: phase-one", "current_phase: "),
        encoding="utf-8",
    )
    assert verify.has_only_terminal_big_plan_change(
        tmp_path, "consumer-proof_implementation", "phase-one", later_metadata
    )
    phase_two.write_text(phase_two.read_text(encoding="utf-8") + "# dirty\n")
    assert not verify.has_only_terminal_big_plan_change(
        tmp_path, "consumer-proof_implementation", "phase-one", later_metadata
    )
    subprocess.run(["git", "reset", "--", "plans/phase-two.md"], cwd=nested, check=True)
    subprocess.run(["git", "checkout", "--", "plans"], cwd=nested, check=True)
    big_plan.write_text(
        big_plan.read_text(encoding="utf-8")
        .replace("status: in-progress", "status: complete")
        .replace("current_phase: phase-one", "current_phase: "),
        encoding="utf-8",
    )
    phase_two.write_text(phase_two.read_text(encoding="utf-8") + "# staged\n")
    subprocess.run(["git", "add", "plans/phase-two.md"], cwd=nested, check=True)
    assert not verify.has_only_terminal_big_plan_change(
        tmp_path, "consumer-proof_implementation", "phase-one", later_metadata
    )
    subprocess.run(["git", "reset", "--", "plans/phase-two.md"], cwd=nested, check=True)
    subprocess.run(["git", "checkout", "--", "plans"], cwd=nested, check=True)
    big_plan.write_text(
        big_plan.read_text(encoding="utf-8")
        .replace("status: in-progress", "status: complete")
        .replace("current_phase: phase-one", "current_phase: "),
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "plans/consumer-proof.md"], cwd=nested, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "terminal transition"], cwd=nested, check=True
    )
    assert verify.has_only_checkpointed_terminal_big_plan_change(
        tmp_path, "consumer-proof_implementation", "phase-one", later_metadata
    )
    phase_two.write_text(phase_two.read_text(encoding="utf-8") + "# checkpoint dirty\n")
    subprocess.run(["git", "add", "plans/phase-two.md"], cwd=nested, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "later phase mutation"], cwd=nested, check=True
    )
    assert not verify.has_only_checkpointed_terminal_big_plan_change(
        tmp_path, "consumer-proof_implementation", "phase-one", later_metadata
    )


@pytest.mark.parametrize(
    ("replacement", "evidence"),
    (
        ("cancelled_at:", "**Status:** CANCELLED\n"),
        ("cancelled_at: invalid", "**Status:** CANCELLED\n"),
        ("cancelled_reason: [not prose]", "**Status:** CANCELLED\n"),
        ("cancelled_evidence: ../escape.md", "**Status:** CANCELLED\n"),
        ("cancelled_evidence: .claude/session_logs/cancelled.md", "not cancelled\n"),
    ),
)
def test_terminal_paths_require_valid_cancelled_evidence(
    tmp_path: Path, replacement: str, evidence: str
) -> None:
    """Both terminal paths require the full audited cancellation contract."""
    nested = tmp_path / ".claude"
    plans = nested / "plans"
    plans.mkdir(parents=True)
    (nested / "scripts").mkdir()
    (nested / "scripts" / "verify.py").write_text("runtime = 1\n", encoding="utf-8")
    _write_root_adapter_pairs(tmp_path)
    (plans / "consumer-proof.md").write_text(
        "---\nname: consumer-proof\ntype: big-plan\nstatus: in-progress\n"
        "current_phase: phase-one\nphases:\n  - phase-one\n  - phase-two\n---\n",
        encoding="utf-8",
    )
    (plans / "phase-one.md").write_text(
        "---\nname: phase-one\ntype: small-plan\nparent_plan: consumer-proof\n"
        "phase_index: 1\nstatus: complete\n"
        "closeout_session_log: .claude/session_logs/phase-one.md\n---\n",
        encoding="utf-8",
    )
    base_cancelled = (
        "---\nname: phase-two\ntype: small-plan\nparent_plan: consumer-proof\n"
        "phase_index: 2\nstatus: cancelled\ncancelled_at: 2026-08-31T00:00:00Z\n"
        "cancelled_reason: Later work is unnecessary\n"
        "cancelled_evidence: .claude/session_logs/cancelled.md\n---\n"
    )
    key = replacement.partition(":")[0]
    original = next(
        line for line in base_cancelled.splitlines() if line.startswith(f"{key}:")
    )
    (plans / "phase-two.md").write_text(
        base_cancelled.replace(original, replacement), encoding="utf-8"
    )
    cancelled_log = nested / "session_logs" / "cancelled.md"
    cancelled_log.parent.mkdir()
    cancelled_log.write_text(evidence, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=nested, check=True)
    subprocess.run(["git", "add", "."], cwd=nested, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Verifier",
            "-c",
            "user.email=verifier@example.com",
            "commit",
            "-qm",
            "base",
        ],
        cwd=nested,
        check=True,
    )
    metadata: dict[str, object] = {
        "branch": "consumer-proof_implementation",
        "control_plane_provenance": verify.control_plane_provenance(
            tmp_path, "consumer-proof_implementation", "phase-one"
        ),
    }
    big_plan = plans / "consumer-proof.md"
    big_plan.write_text(
        big_plan.read_text(encoding="utf-8")
        .replace("status: in-progress", "status: complete")
        .replace("current_phase: phase-one", "current_phase: "),
        encoding="utf-8",
    )
    assert not verify.has_only_terminal_big_plan_change(
        tmp_path, "consumer-proof_implementation", "phase-one", metadata
    )
    subprocess.run(["git", "add", "plans/consumer-proof.md"], cwd=nested, check=True)
    subprocess.run(["git", "commit", "-qm", "terminal"], cwd=nested, check=True)
    assert not verify.has_only_checkpointed_terminal_big_plan_change(
        tmp_path, "consumer-proof_implementation", "phase-one", metadata
    )


def test_checkpointed_terminal_accepts_receipt_bound_dirty_closeout_state(
    tmp_path: Path,
) -> None:
    """A receipt may precede one checkpoint that persists its completed plan."""
    nested = tmp_path / ".claude"
    plans = nested / "plans"
    plans.mkdir(parents=True)
    (nested / "scripts").mkdir()
    (nested / "scripts" / "verify.py").write_text("runtime = 1\n", encoding="utf-8")
    _write_root_adapter_pairs(tmp_path)
    big_plan = plans / "consumer-proof.md"
    big_plan.write_text(
        "---\nname: consumer-proof\ntype: big-plan\nstatus: in-progress\n"
        "current_phase: phase-one\nphases:\n  - phase-one\n---\n",
        encoding="utf-8",
    )
    small_plan = plans / "phase-one.md"
    small_plan.write_text(
        "---\nname: phase-one\ntype: small-plan\nparent_plan: consumer-proof\n"
        "phase_index: 1\nstatus: in-progress\n---\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q"], cwd=nested, check=True)
    subprocess.run(["git", "config", "user.name", "Verifier"], cwd=nested, check=True)
    subprocess.run(
        ["git", "config", "user.email", "verifier@example.com"],
        cwd=nested,
        check=True,
    )
    subprocess.run(["git", "add", "."], cwd=nested, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Verifier",
            "-c",
            "user.email=verifier@example.com",
            "commit",
            "-qm",
            "base",
        ],
        cwd=nested,
        check=True,
    )
    small_plan.write_text(
        "---\nname: phase-one\ntype: small-plan\nparent_plan: consumer-proof\n"
        "phase_index: 1\nstatus: complete\n"
        "closeout_session_log: .claude/session_logs/phase-one.md\n---\n",
        encoding="utf-8",
    )
    evidence = nested / "quality_reports" / "verification-phase-phase-one.json"
    evidence.parent.mkdir()
    evidence.write_text("receipt\n", encoding="utf-8")
    metadata: dict[str, object] = {
        "branch": "consumer-proof_implementation",
        "control_plane_provenance": verify.control_plane_provenance(
            tmp_path, "consumer-proof_implementation", "phase-one"
        ),
    }
    subprocess.run(
        ["git", "add", "plans/phase-one.md", "quality_reports"], cwd=nested, check=True
    )
    subprocess.run(
        ["git", "commit", "-qm", "closeout evidence checkpoint"],
        cwd=nested,
        check=True,
    )
    big_plan.write_text(
        big_plan.read_text(encoding="utf-8")
        .replace("status: in-progress", "status: complete")
        .replace("current_phase: phase-one", "current_phase: "),
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "plans/consumer-proof.md"], cwd=nested, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "closeout checkpoint"], cwd=nested, check=True
    )

    assert verify.has_only_checkpointed_terminal_big_plan_change(
        tmp_path, "consumer-proof_implementation", "phase-one", metadata
    )
    small_plan.write_text(small_plan.read_text(encoding="utf-8") + "# mutated\n")
    subprocess.run(["git", "add", "plans/phase-one.md"], cwd=nested, check=True)
    subprocess.run(
        ["git", "commit", "-qm", "post-receipt mutation"], cwd=nested, check=True
    )
    assert not verify.has_only_checkpointed_terminal_big_plan_change(
        tmp_path, "consumer-proof_implementation", "phase-one", metadata
    )


def test_receipt_rejects_missing_control_plane_provenance() -> None:
    """Schema validation cannot silently accept receipts without nested evidence."""
    receipt = _receipt()
    metadata = receipt["metadata"]
    assert isinstance(metadata, dict)
    metadata.pop("control_plane_provenance")

    with pytest.raises(ValueError, match="authoritative fields"):
        verify.validate_receipt(receipt)


def test_docs_only_scope_preserves_code_evidence_but_control_markdown_does_not() -> (
    None
):
    """Only ordinary documentation is excluded from the scoped freshness hash."""
    assert verify.scoped_paths(["docs/guide.md"]) == []
    assert (
        verify.classify_path(".claude/instructions/workflow.instructions.md")
        == "control-plane"
    )
    assert verify.scoped_paths([".claude/instructions/workflow.instructions.md"])


@pytest.mark.parametrize(
    "path",
    (
        "shared/policies/workflow.instructions.md",
        "shared/hooks/scripts/enforce-commit-gate.sh",
        "shared/agents/orchestrator/AGENT.md",
        "shared/skills/ponytail/SKILL.md",
        "shared/review-profiles/security.md",
    ),
)
def test_canonical_shared_sources_are_control_plane(path: str) -> None:
    """Generated canonical sources always invalidate relevant evidence."""
    assert verify.classify_path(path) == "control-plane"


@pytest.mark.parametrize(
    "path",
    (
        "service/uv.lock",
        "requirements-dev.txt",
        "frontend/package.json",
        "deployment/Dockerfile",
        "rust/Cargo.lock",
        "go/go.mod",
    ),
)
def test_dependency_and_build_inputs_are_config(path: str) -> None:
    """Dependency, lock, and build inputs always stale relevant evidence."""
    assert verify.classify_path(path) == "config"


@pytest.mark.parametrize(
    "path",
    (".gitignore", "Makefile", "src/app.ts", "db/schema.sql", "bin/deploy.sh"),
)
def test_unknown_source_and_build_paths_fail_closed(path: str) -> None:
    """Unknown non-document paths remain evidence-relevant by default."""
    assert verify.classify_path(path) != "documentation-only"


def test_ordinary_documentation_remains_reusable() -> None:
    """Only narrow ordinary documentation paths are excluded from code evidence."""
    assert verify.classify_path("docs/guide.md") == "documentation-only"


def test_phase_receipt_rejects_required_check_marked_not_applicable() -> None:
    """Changing both status and applicability cannot bypass a phase check."""
    receipt = _receipt()
    checks = receipt["checks"]
    assert isinstance(checks, list)
    ruff = next(item for item in checks if item["id"] == "VFY-RUFF-001")
    ruff.update(status="NOT_APPLICABLE", applicable=False)
    with pytest.raises(ValueError, match="invalid applicability"):
        verify.validate_receipt(receipt)


def test_missing_git_binding_is_not_fresh_evidence() -> None:
    """Freshness cannot pass when Git did not supply a head/base binding."""
    metadata = _metadata()
    metadata["head_sha"] = ""
    assert not verify.metadata_is_bound(metadata)


def test_git_paths_and_hash_include_untracked_files(tmp_path: Path) -> None:
    """New source files participate in changed-path and freshness evidence."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-qm", "base"], cwd=tmp_path, check=True)
    subprocess.run(["git", "branch", "dev"], cwd=tmp_path, check=True)
    untracked = tmp_path / "new.py"
    untracked.write_text("VALUE = 1\n", encoding="utf-8")
    paths = verify.git_paths(tmp_path, "dev")
    assert paths == ["new.py"]
    before = verify.hash_paths(tmp_path, paths)
    untracked.write_text("VALUE = 2\n", encoding="utf-8")
    assert verify.hash_paths(tmp_path, paths) != before


def test_failed_git_path_discovery_clears_freshness_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A partial or failed Git inventory cannot produce fresh evidence."""
    monkeypatch.setattr(
        verify,
        "run_process",
        lambda args, _root: subprocess.CompletedProcess(
            args,
            0
            if args[1:3] in (["merge-base", "dev"], ["rev-parse", "--abbrev-ref"])
            or args[1:2] == ["rev-parse"]
            else 2,
            "head\n",
            "",
        ),
    )
    metadata = verify.state_metadata(tmp_path, "dev")
    assert metadata["path_discovery_ok"] is False
    assert not verify.metadata_is_bound(metadata)


def test_git_paths_preserve_newline_filename(tmp_path: Path) -> None:
    """NUL-delimited Git output preserves quoted and newline path identity."""
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    unusual = tmp_path / "odd\nname.py"
    unusual.write_text("VALUE = 1\n", encoding="utf-8")
    paths = verify.git_paths(tmp_path, "dev")
    assert paths == ["odd\nname.py"]
    before = verify.hash_paths(tmp_path, paths)
    unusual.write_text("VALUE = 2\n", encoding="utf-8")
    assert verify.hash_paths(tmp_path, paths) != before


def test_existing_paths_filters_only_deleted_entries(tmp_path: Path) -> None:
    """existing_paths keeps files still on disk and drops the rest, nothing
    more - it is the sole gate between a changed-path list and a tool that
    must open each target."""
    (tmp_path / "present.py").write_text("VALUE = 1\n", encoding="utf-8")
    assert verify.existing_paths(tmp_path, ["present.py", "gone.py"]) == ["present.py"]


def test_fast_checks_skips_ruff_when_all_python_paths_are_deleted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reproduces the real defect: a tracked Python file deleted since the
    base ref (as Phase 1 deleted shared/scripts/quality_score.py) is a
    legitimate changed path, so VFY-RUFF-001 stays applicable, but it must
    never be handed to Ruff as an open target - and with no surviving
    Python path, Ruff must not run at all (an empty target list would
    silently widen its scope to the whole tree)."""
    _init_repo(tmp_path)
    (tmp_path / "mod.py").write_text("VALUE = 1\n", encoding="utf-8")
    _commit_all(tmp_path, "add module")
    _git(["branch", "dev"], tmp_path)
    (tmp_path / "mod.py").unlink()
    _commit_all(tmp_path, "delete module")
    metadata = verify.state_metadata(tmp_path, "dev")
    assert metadata["relevant_paths"] == ["mod.py"]

    def fail_if_called(*_args: object, **_kwargs: object) -> tuple[int, str, str]:
        raise AssertionError("Ruff must not run with no surviving targets")

    monkeypatch.setattr(verify, "_run", fail_if_called)
    checks = verify.fast_checks(tmp_path, metadata)
    ruff = next(item for item in checks if item["id"] == "VFY-RUFF-001")
    assert ruff["applicable"] is True
    assert ruff["status"] == "PASS"


def test_fast_checks_excludes_deleted_paths_from_ruff_target_list(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A deleted Python path must be dropped from the actual Ruff
    invocation while a surviving changed Python path is still measured."""
    _init_repo(tmp_path)
    (tmp_path / "mod.py").write_text("VALUE = 1\n", encoding="utf-8")
    _commit_all(tmp_path, "add module")
    _git(["branch", "dev"], tmp_path)
    (tmp_path / "mod.py").unlink()
    (tmp_path / "kept.py").write_text("VALUE = 2\n", encoding="utf-8")
    _commit_all(tmp_path, "delete mod.py, add kept.py")
    metadata = verify.state_metadata(tmp_path, "dev")
    assert set(metadata["relevant_paths"]) == {"mod.py", "kept.py"}

    seen_targets: list[str] = []

    def fake_run(args: list[str], cwd: str = ".") -> tuple[int, str, str]:
        seen_targets.extend(arg for arg in args if arg.endswith(".py"))
        return 0, "[]", ""

    monkeypatch.setattr(verify, "_run", fake_run)
    checks = verify.fast_checks(tmp_path, metadata)
    ruff = next(item for item in checks if item["id"] == "VFY-RUFF-001")
    assert ruff["applicable"] is True
    assert ruff["status"] == "PASS"
    assert seen_targets == ["kept.py"]


def test_fast_checks_still_fails_a_real_violation_beside_a_deletion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Filtering a deleted path out of Ruff's target list must not weaken a
    genuine violation reported for a file that still exists."""
    _init_repo(tmp_path)
    (tmp_path / "mod.py").write_text("VALUE = 1\n", encoding="utf-8")
    _commit_all(tmp_path, "add module")
    _git(["branch", "dev"], tmp_path)
    (tmp_path / "mod.py").unlink()
    (tmp_path / "bad.py").write_text("import os\n", encoding="utf-8")
    _commit_all(tmp_path, "delete mod.py, add bad.py")
    metadata = verify.state_metadata(tmp_path, "dev")
    assert set(metadata["relevant_paths"]) == {"mod.py", "bad.py"}
    violation = [
        {
            "cell": None,
            "code": "F401",
            "end_location": {"column": 1, "row": 1},
            "filename": str(tmp_path / "bad.py"),
            "fix": None,
            "location": {"column": 1, "row": 1},
            "message": "`os` imported but unused",
            "noqa_row": 1,
            "severity": "error",
            "url": "https://docs.astral.sh/ruff/rules/unused-import",
        }
    ]
    monkeypatch.setattr(
        verify, "_run", lambda *_a, **_k: (1, json.dumps(violation), "")
    )
    checks = verify.fast_checks(tmp_path, metadata)
    ruff = next(item for item in checks if item["id"] == "VFY-RUFF-001")
    assert ruff["status"] == "FAIL"


def test_hash_paths_includes_mode_and_symlink_identity(tmp_path: Path) -> None:
    """Executable bits and link targets participate in freshness evidence."""
    script = tmp_path / "mode.sh"
    script.write_text("exit 0\n", encoding="utf-8")
    script.chmod(0o644)
    before_mode = verify.hash_paths(tmp_path, ["mode.sh"])
    script.chmod(0o755)
    assert verify.hash_paths(tmp_path, ["mode.sh"]) != before_mode

    first = tmp_path / "first"
    second = tmp_path / "second"
    first.write_text("same\n", encoding="utf-8")
    second.write_text("same\n", encoding="utf-8")
    link = tmp_path / "current"
    link.symlink_to("first")
    before_link = verify.hash_paths(tmp_path, ["current"])
    link.unlink()
    link.symlink_to("second")
    assert verify.hash_paths(tmp_path, ["current"]) != before_link


def test_generation_check_detects_drift(tmp_path: Path) -> None:
    """Source/generated verifier byte drift is a failing ownership check."""
    source = tmp_path / "shared/scripts/verify.py"
    generated = tmp_path / ".claude/scripts/verify.py"
    source.parent.mkdir(parents=True)
    generated.parent.mkdir(parents=True)
    source.write_text("source\n", encoding="utf-8")
    generated.write_text("generated\n", encoding="utf-8")
    assert verify.generation_check(tmp_path)["status"] == "FAIL"


def test_generation_check_requires_generated_verifier(tmp_path: Path) -> None:
    """A missing generated verifier file remains unverified."""
    source = tmp_path / "shared/scripts/verify.py"
    source.parent.mkdir(parents=True)
    source.write_text("same\n", encoding="utf-8")
    assert verify.generation_check(tmp_path)["status"] == "UNVERIFIED"


def test_canonical_serialization_is_stable() -> None:
    """Receipt output has stable object-key ordering for machine consumers."""
    assert verify.canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'


@pytest.mark.parametrize(
    ("runner", "result", "status"),
    (
        (verify._ruff_measurement, (1, "", ""), "UNVERIFIED"),
        (verify._ruff_measurement, (1, "{", ""), "UNVERIFIED"),
        (verify._ruff_measurement, (1, "[]", ""), "UNVERIFIED"),
        (verify._mypy_measurement, (2, "", "internal error"), "UNVERIFIED"),
    ),
    ids=(
        "quality-ruff-empty",
        "quality-ruff-malformed",
        "quality-ruff-empty-failure",
        "quality-mypy-abnormal",
    ),
)
def test_measurement_does_not_report_failed_measurement_clean(
    monkeypatch: pytest.MonkeyPatch,
    runner: object,
    result: tuple[int, str, str],
    status: str,
) -> None:
    """Fail-open tool exits never resolve to a clean measurement state."""
    monkeypatch.setattr(verify, "_run", lambda *_args, **_kwargs: result)
    measured_status, _detail = runner("shared")  # type: ignore[operator]
    assert measured_status == status


def test_consumer_ruff_scope_extends_exclusions_without_replacing_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Consumer linting adds the runtime exclusion without bypassing Ruff config."""
    captured: list[str] = []

    def fake_run(args: list[str], cwd: str = ".") -> tuple[int, str, str]:
        captured.extend(args)
        assert cwd == "consumer"
        return 0, "[]", ""

    monkeypatch.setattr(verify, "_run", fake_run)
    status, _detail = verify._ruff_measurement(
        ["."], cwd="consumer", extend_exclude=[".claude"]
    )

    assert status == "PASS"
    assert captured == [
        "uv",
        "run",
        "ruff",
        "check",
        ".",
        "--output-format=json",
        "--extend-exclude",
        ".claude",
    ]


@pytest.mark.parametrize(
    ("filename", "contents"),
    (
        ("mypy.ini", "[mypy]\nfiles = src\n"),
        (".mypy.ini", "[mypy]\npackages = example_consumer\n"),
        ("pyproject.toml", '[tool.mypy]\nfiles = ["lib", "tests"]\n'),
        ("setup.cfg", "[mypy]\nmodules = example_consumer.cli\n"),
    ),
    ids=("mypy-ini", "dot-mypy-ini", "pyproject", "setup-cfg"),
)
def test_consumer_mypy_scope_prefers_valid_native_configuration(
    tmp_path: Path, filename: str, contents: str
) -> None:
    """Valid native Mypy syntax delegates scope to Mypy's own config parser."""
    (tmp_path / filename).write_text(contents, encoding="utf-8")

    assert verify.consumer_mypy_targets(tmp_path) == []


def test_consumer_mypy_scope_respects_mypy_config_precedence(tmp_path: Path) -> None:
    """A higher-precedence config without scope suppresses lower config targets."""
    (tmp_path / "mypy.ini").write_text("[mypy]\nwarn_unused_configs = True\n")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.mypy]\nfiles = ["lib"]\n', encoding="utf-8"
    )

    assert verify.consumer_mypy_targets(tmp_path) is None


def test_consumer_mypy_scope_skips_non_mypy_config_files(tmp_path: Path) -> None:
    """Mypy discovery continues after a valid config that has no Mypy section."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "example-consumer"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    (tmp_path / "setup.cfg").write_text("[mypy]\nfiles = src\n", encoding="utf-8")

    assert verify.consumer_mypy_targets(tmp_path) == []


def test_consumer_mypy_scope_rejects_invalid_selected_config(tmp_path: Path) -> None:
    """Malformed selected config cannot fall through to a lower-precedence file."""
    (tmp_path / "mypy.ini").write_text("[mypy\nfiles = src\n")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.mypy]\nfiles = ["lib"]\n', encoding="utf-8"
    )
    (tmp_path / "src").mkdir()

    assert verify.consumer_mypy_targets(tmp_path) is None


def test_consumer_mypy_scope_does_not_parse_toml_text_as_config(tmp_path: Path) -> None:
    """Valid TOML strings cannot masquerade as Mypy configuration sections."""
    (tmp_path / "pyproject.toml").write_text(
        '[tool.example]\nnote = "[tool.mypy] files = [\\"src\\"]"\n',
        encoding="utf-8",
    )

    assert verify.consumer_mypy_targets(tmp_path) is None


def test_consumer_mypy_scope_falls_back_only_to_src(tmp_path: Path) -> None:
    """Without native Mypy targets, only the conventional source root is trusted."""
    assert verify.consumer_mypy_targets(tmp_path) is None
    (tmp_path / "src").mkdir()
    assert verify.consumer_mypy_targets(tmp_path) == ["src"]


def test_consumer_phase_checks_exclude_bootstrap_runtime_and_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Consumers use native project targets and never guess a Mypy scope."""
    ruff_calls: list[tuple[list[str], list[str] | None]] = []
    mypy_calls: list[list[str] | None] = []
    pytest_calls: list[list[str] | None] = []

    def fake_ruff(
        _root: Path, targets: list[str], *, extend_exclude: list[str] | None = None
    ) -> dict[str, object]:
        ruff_calls.append((targets, extend_exclude))
        return verify.check("VFY-RUFF-001", "PASS", "ruff completed")

    def fake_mypy(_root: Path, targets: list[str] | None) -> dict[str, object]:
        mypy_calls.append(targets)
        return verify.check("VFY-MYPY-001", "PASS", "mypy completed")

    def fake_pytest(_root: Path, targets: list[str] | None = None) -> dict[str, object]:
        pytest_calls.append(targets)
        return verify.check("VFY-PYTEST-001", "PASS", "pytest completed")

    monkeypatch.setattr(verify, "measure_ruff", fake_ruff)
    monkeypatch.setattr(verify, "measure_mypy", fake_mypy)
    monkeypatch.setattr(verify, "measure_pytest", fake_pytest)
    monkeypatch.setattr(
        verify,
        "generation_check",
        lambda _root: verify.check("VFY-GEN-001", "PASS", "installed"),
    )
    metadata = _metadata()
    checks = verify.phase_checks(tmp_path, metadata)

    assert ruff_calls == [(["."], [".claude"])]
    assert mypy_calls == []
    assert pytest_calls == [[]]
    assert next(
        item for item in checks if item["id"] == "VFY-MYPY-001"
    ) == verify.check(
        "VFY-MYPY-001",
        "UNVERIFIED",
        "Mypy has no configured scope or conventional src root",
    )


def test_bootstrap_phase_checks_keep_explicit_authoring_targets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The authoring checkout retains its existing fixed verification groups."""
    ruff_calls: list[tuple[list[str], list[str] | None]] = []
    mypy_calls: list[list[str] | None] = []
    pytest_calls: list[list[str] | None] = []

    def fake_ruff(
        _root: Path, targets: list[str], *, extend_exclude: list[str] | None = None
    ) -> dict[str, object]:
        ruff_calls.append((targets, extend_exclude))
        return verify.check("VFY-RUFF-001", "PASS", "ruff completed")

    def fake_mypy(_root: Path, targets: list[str] | None) -> dict[str, object]:
        mypy_calls.append(targets)
        return verify.check("VFY-MYPY-001", "PASS", "mypy completed")

    def fake_pytest(_root: Path, targets: list[str] | None = None) -> dict[str, object]:
        pytest_calls.append(targets)
        return verify.check("VFY-PYTEST-001", "PASS", "pytest completed")

    monkeypatch.setattr(verify, "measure_ruff", fake_ruff)
    monkeypatch.setattr(verify, "measure_mypy", fake_mypy)
    monkeypatch.setattr(verify, "measure_pytest", fake_pytest)
    monkeypatch.setattr(
        verify,
        "generation_check",
        lambda _root: verify.check("VFY-GEN-001", "PASS", "generated"),
    )

    verify.phase_checks(REPO_ROOT, _metadata())

    assert ruff_calls == [(["shared", "scripts", "tests"], None)]
    assert mypy_calls == [["shared", "scripts", "tests"]]
    assert pytest_calls == [["tests/"]]
