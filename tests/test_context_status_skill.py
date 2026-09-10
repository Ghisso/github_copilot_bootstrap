"""Regression coverage for the context-status skill's embedded plan report."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL = REPO_ROOT / "shared" / "skills" / "context-status" / "SKILL.md"

# Matches the "### 1. Active Plan" fenced bash block's embedded Python heredoc,
# the same script a consumer session actually runs to list plan status.
_ACTIVE_PLAN_SCRIPT_PATTERN = re.compile(
    r"```bash\nuv run python - <<'PY'\n(?P<script>.*?)\nPY\n```", re.DOTALL
)


def _embedded_active_plan_script() -> str:
    """Extract the Active Plan check's Python heredoc from the skill doc."""
    match = _ACTIVE_PLAN_SCRIPT_PATTERN.search(SKILL.read_text(encoding="utf-8"))
    assert match is not None, "context-status SKILL.md active-plan script not found"
    return match.group("script")


def _write_plan(root: Path, name: str, plan_type: str, status: str) -> None:
    """Write the smallest frontmatter the embedded report script parses."""
    plans = root / ".claude" / "plans"
    plans.mkdir(parents=True, exist_ok=True)
    (plans / f"{name}.md").write_text(
        f"---\nname: {name}\ntype: {plan_type}\nstatus: {status}\n---\n\n# {name}\n",
        encoding="utf-8",
    )


def _run_active_plan_report(root: Path) -> list[str]:
    """Run the exact embedded script against a fixture plan directory."""
    result = subprocess.run(
        [sys.executable, "-c", _embedded_active_plan_script()],
        cwd=root,
        text=True,
        capture_output=True,
        check=True,
    )
    return result.stdout.splitlines()


def test_reports_multiple_planned_phases_alongside_one_current_phase(
    tmp_path: Path,
) -> None:
    """Several `planned` future phases and one `in-progress` phase all surface."""
    _write_plan(tmp_path, "example", "big-plan", "in-progress")
    _write_plan(tmp_path, "phase-one", "small-plan", "complete")
    _write_plan(tmp_path, "phase-two", "small-plan", "in-progress")
    _write_plan(tmp_path, "phase-three", "small-plan", "planned")
    _write_plan(tmp_path, "phase-four", "small-plan", "planned")

    lines = _run_active_plan_report(tmp_path)

    assert "small-plan\tin-progress\tphase-two.md" in lines
    assert "small-plan\tplanned\tphase-three.md" in lines
    assert "small-plan\tplanned\tphase-four.md" in lines
    active = [line for line in lines if line == "small-plan\tin-progress\tphase-two.md"]
    assert len(active) == 1, "exactly one small plan may report the active status"
    planned = [line for line in lines if "\tplanned\t" in line]
    assert len(planned) == 2, "every declared planned phase must still be listed"


def test_report_format_never_lists_planned_as_an_active_small_plan_status() -> None:
    """The active-status vocabulary line excludes `planned` by construction."""
    text = SKILL.read_text(encoding="utf-8")

    assert "in-progress/paused/complete/cancelled" in text
    assert "planned/in-progress/paused/complete/cancelled" not in text
