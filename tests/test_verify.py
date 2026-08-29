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


def _metadata(content_hash: str = "relevant") -> dict[str, object]:
    """Return the minimum strict receipt metadata."""
    return {
        "base_ref": "dev",
        "branch": "verification-test",
        "head_sha": "head",
        "merge_base_sha": "base",
        "content_hash": content_hash,
        "tracked_state_hash": "whole-state",
        "generated_at": "2026-08-29T00:00:00Z",
        "changed_paths": [],
        "relevant_paths": [],
        "path_discovery_ok": True,
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
    phase_path = tmp_path / verify.PHASE_RECEIPT
    phase_path.parent.mkdir(parents=True)
    phase_path.write_text(json.dumps(_receipt(content_hash="old")), encoding="utf-8")
    checks = verify.closeout_checks(tmp_path, _metadata(content_hash="new"))
    fresh = next(item for item in checks if item["id"] == "VFY-FRESH-001")
    assert fresh["status"] == "FAIL"


def test_closeout_rejects_tampered_phase_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Tampered referenced evidence cannot produce a closeout PASS."""
    phase_path = tmp_path / verify.PHASE_RECEIPT
    phase_path.parent.mkdir(parents=True)
    receipt = _receipt()
    receipt["checks"][0]["summary"] = "edited after measurement"  # type: ignore[index]
    phase_path.write_text(json.dumps(receipt), encoding="utf-8")
    monkeypatch.setattr(verify, "phase_checks", lambda *_args: _receipt()["checks"])
    checks = verify.closeout_checks(tmp_path, _metadata())
    reused = next(item for item in checks if item["id"] == "VFY-RECEIPT-001")
    assert reused["status"] == "FAIL"


def test_closeout_rejects_rewritten_receipt_after_remeasurement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A locally rewritten PASS receipt cannot replace current measurement."""
    phase_path = tmp_path / verify.PHASE_RECEIPT
    phase_path.parent.mkdir(parents=True)
    phase_path.write_text(json.dumps(_receipt()), encoding="utf-8")
    current = _receipt()["checks"]
    assert isinstance(current, list) and isinstance(current[0], dict)
    current[0] = {**current[0], "status": "FAIL", "summary": "current failure"}
    monkeypatch.setattr(verify, "phase_checks", lambda *_args: current)
    checks = verify.closeout_checks(tmp_path, _metadata())
    reused = next(item for item in checks if item["id"] == "VFY-RECEIPT-001")
    assert reused["status"] == "FAIL"


def test_closeout_rejects_different_git_binding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Equal diff hashes do not cross branch/base/head freshness boundaries."""
    phase_path = tmp_path / verify.PHASE_RECEIPT
    phase_path.parent.mkdir(parents=True)
    phase = _receipt()
    phase_path.write_text(json.dumps(phase), encoding="utf-8")
    monkeypatch.setattr(verify, "phase_checks", lambda *_args: phase["checks"])
    current = _metadata()
    current["merge_base_sha"] = "different-base"
    checks = verify.closeout_checks(tmp_path, current)
    fresh = next(item for item in checks if item["id"] == "VFY-FRESH-001")
    assert fresh["status"] == "FAIL"


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
