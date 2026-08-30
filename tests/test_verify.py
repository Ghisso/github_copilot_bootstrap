"""Falsifier regressions for the deterministic verification receipt."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "shared" / "scripts"))

import quality_score  # noqa: E402
import verify  # noqa: E402


def test_verifier_disables_runtime_bytecode_cache() -> None:
    """Running the managed verifier must not create unmanaged runtime files."""
    source = (REPO_ROOT / "shared/scripts/verify.py").read_text(encoding="utf-8")
    assert "sys.dont_write_bytecode = True\nimport quality_score" in source


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
            "score": {
                "path": ".claude/quality_reports/score-test.json",
                "sha256": digest,
            },
            "findings": {
                "path": ".claude/quality_reports/findings-test.json",
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


def _findings_errors(tmp_path: Path, report: dict[str, object]) -> list[str]:
    """Persist and validate one focused findings fixture."""
    path = tmp_path / "findings.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return verify.report_errors(
        path,
        kind="findings",
        branch="verification-test",
        phase="phase-one",
        head="head",
        head_relation="exact",
        expected_base="base",
        root=tmp_path,
        require_major=False,
        require_ponytail=False,
        verify_current_content=False,
    )


def test_findings_rejects_nonstring_changed_file(tmp_path: Path) -> None:
    """Changed-file evidence cannot contain untyped JSON values."""
    errors = _findings_errors(tmp_path, _findings_report(changed_files=[1]))
    assert "findings report changed_files must be a list of strings" in errors


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
    artifacts["score"] = {"path": "../score.json", "sha256": "a" * 64}
    with pytest.raises(ValueError, match="artifact score is invalid"):
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
        quality_score, "_run", lambda *_args, **_kwargs: (returncode, stdout, "")
    )
    result = verify.measure_ruff(REPO_ROOT, ["shared"])
    assert result["status"] == expected


def test_ruff_missing_executable_is_unverified(monkeypatch: pytest.MonkeyPatch) -> None:
    """A missing verification tool is unverified rather than clean."""
    monkeypatch.setattr(
        quality_score,
        "_run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FileNotFoundError("uv")),
    )
    assert verify.measure_ruff(REPO_ROOT, ["shared"])["status"] == "UNVERIFIED"


def test_timeout_is_unverified(monkeypatch: pytest.MonkeyPatch) -> None:
    """A timed out command cannot be accepted as a passing check."""
    monkeypatch.setattr(
        quality_score,
        "_run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            subprocess.TimeoutExpired(["uv"], 1)
        ),
    )
    assert verify.measure_ruff(REPO_ROOT, ["shared"])["status"] == "UNVERIFIED"


def test_mypy_abnormal_exit_is_unverified(monkeypatch: pytest.MonkeyPatch) -> None:
    """mypy operational failures remain distinct from type errors."""
    monkeypatch.setattr(
        quality_score,
        "_run",
        lambda *_args, **_kwargs: (2, "", "internal error"),
    )
    assert verify.measure_mypy(REPO_ROOT, ["shared"])["status"] == "UNVERIFIED"


def test_pytest_infrastructure_exit_is_unverified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """pytest collection/tool errors are not represented as ordinary failures."""
    monkeypatch.setattr(
        quality_score,
        "_run",
        lambda *_args, **_kwargs: (2, "", "collection error"),
    )
    assert verify.measure_pytest(REPO_ROOT)["status"] == "UNVERIFIED"


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
    (tmp_path / "shared/scripts/quality_score.py").write_text(
        "same\n", encoding="utf-8"
    )
    (tmp_path / ".claude/scripts/quality_score.py").write_text(
        "same\n", encoding="utf-8"
    )
    assert verify.generation_check(tmp_path)["status"] == "FAIL"


def test_generation_check_detects_measurement_module_drift(tmp_path: Path) -> None:
    """The verifier cannot pass with stale generated measurement semantics."""
    source_dir = tmp_path / "shared/scripts"
    generated_dir = tmp_path / ".claude/scripts"
    source_dir.mkdir(parents=True)
    generated_dir.mkdir(parents=True)
    (source_dir / "verify.py").write_text("same\n", encoding="utf-8")
    (generated_dir / "verify.py").write_text("same\n", encoding="utf-8")
    (source_dir / "quality_score.py").write_text("new\n", encoding="utf-8")
    (generated_dir / "quality_score.py").write_text("old\n", encoding="utf-8")
    assert verify.generation_check(tmp_path)["status"] == "FAIL"


def test_generation_check_requires_generated_measurement_module(tmp_path: Path) -> None:
    """A missing generated measurement dependency remains unverified."""
    source_dir = tmp_path / "shared/scripts"
    generated_dir = tmp_path / ".claude/scripts"
    source_dir.mkdir(parents=True)
    generated_dir.mkdir(parents=True)
    (source_dir / "verify.py").write_text("same\n", encoding="utf-8")
    (generated_dir / "verify.py").write_text("same\n", encoding="utf-8")
    (source_dir / "quality_score.py").write_text("required\n", encoding="utf-8")
    assert verify.generation_check(tmp_path)["status"] == "UNVERIFIED"


def test_canonical_serialization_is_stable() -> None:
    """Receipt output has stable object-key ordering for machine consumers."""
    assert verify.canonical_json({"b": 1, "a": 2}) == '{"a":2,"b":1}'


@pytest.mark.parametrize(
    ("runner", "result", "status"),
    (
        (quality_score.measure_ruff, (1, "", ""), "UNVERIFIED"),
        (quality_score.measure_ruff, (1, "{", ""), "UNVERIFIED"),
        (quality_score.measure_ruff, (1, "[]", ""), "UNVERIFIED"),
        (quality_score.measure_mypy, (2, "", "internal error"), "UNVERIFIED"),
    ),
    ids=(
        "quality-ruff-empty",
        "quality-ruff-malformed",
        "quality-ruff-empty-failure",
        "quality-mypy-abnormal",
    ),
)
def test_quality_score_does_not_report_failed_measurement_clean(
    monkeypatch: pytest.MonkeyPatch,
    runner: object,
    result: tuple[int, str, str],
    status: str,
) -> None:
    """Legacy scoring fences its former fail-open paths with measurement state."""
    monkeypatch.setattr(quality_score, "_run", lambda *_args, **_kwargs: result)
    measurement = runner("shared")  # type: ignore[operator]
    assert measurement.status == status


def test_consumer_ruff_scope_extends_exclusions_without_replacing_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Consumer linting adds the runtime exclusion without bypassing Ruff config."""
    captured: list[str] = []

    def fake_run(args: list[str], cwd: str = ".") -> tuple[int, str, str]:
        captured.extend(args)
        assert cwd == "consumer"
        return 0, "[]", ""

    monkeypatch.setattr(quality_score, "_run", fake_run)
    measurement = quality_score.measure_ruff(
        ["."], cwd="consumer", extend_exclude=[".claude"]
    )

    assert measurement.status == "PASS"
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
