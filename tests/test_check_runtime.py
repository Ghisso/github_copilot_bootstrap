"""Regression coverage for check_runtime.py's hard consumer-facing checks."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_runtime  # noqa: E402


def _write_plan(root: Path, frontmatter: str) -> None:
    plans = root / ".claude" / "plans"
    plans.mkdir(parents=True, exist_ok=True)
    (plans / "example.md").write_text(
        f"---\n{frontmatter.strip()}\n---\n\n# Example\n", encoding="utf-8"
    )


def test_plan_frontmatter_errors_reports_invalid_metadata_as_fail(
    tmp_path: Path,
) -> None:
    """R-LIFECYCLE-04: check_runtime.py now surfaces invalid plan frontmatter
    as a hard FAIL, not the earlier advisory WARN."""
    (tmp_path / "scripts").mkdir()
    shutil.copy2(
        REPO_ROOT / "scripts" / "validate_plan_frontmatter.py",
        tmp_path / "scripts" / "validate_plan_frontmatter.py",
    )
    _write_plan(
        tmp_path,
        "type: big-plan\nstatus: planning\noriginating_branch: dev\n"
        "implementation_branch: example_implementation\nphases:\n  - phase-one",
    )
    errors = check_runtime.plan_frontmatter_errors(tmp_path)
    assert len(errors) == 1
    assert "plan frontmatter validation reported issues" in errors[0]
    assert "missing required field: name" in errors[0]


def test_plan_frontmatter_errors_passes_for_valid_metadata(tmp_path: Path) -> None:
    (tmp_path / "scripts").mkdir()
    shutil.copy2(
        REPO_ROOT / "scripts" / "validate_plan_frontmatter.py",
        tmp_path / "scripts" / "validate_plan_frontmatter.py",
    )
    _write_plan(
        tmp_path,
        "name: example\ntype: big-plan\nstatus: planning\noriginating_branch: dev\n"
        "implementation_branch: example_implementation\nphases:\n  - phase-one",
    )
    assert check_runtime.plan_frontmatter_errors(tmp_path) == []


def test_plan_frontmatter_errors_skips_when_validator_is_absent(
    tmp_path: Path,
) -> None:
    """A missing validator is the generated-target-parity checks' job to
    catch, not a duplicate failure reason here."""
    assert check_runtime.plan_frontmatter_errors(tmp_path) == []
