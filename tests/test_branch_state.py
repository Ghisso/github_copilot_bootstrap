"""Regression coverage for branch-creation phase activation."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS_SOURCE = REPO_ROOT / "shared" / "hooks"


def run_git(root: Path, *args: str) -> None:
    """Run Git with a deterministic identity in a disposable repository."""
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Branch Test",
            "-c",
            "user.email=branch@example.com",
            *args,
        ],
        cwd=root,
        text=True,
        check=True,
    )


def write_big_plan(root: Path, phases: list[str]) -> Path:
    """Write the smallest big-plan frontmatter the branch-state hook reads."""
    plans = root / ".claude" / "plans"
    plans.mkdir(parents=True, exist_ok=True)
    phase_lines = "\n".join(f"  - {phase}" for phase in phases)
    plan = plans / "foo.md"
    plan.write_text(
        f"---\nname: foo\ntype: big-plan\nstatus: planning\nphases:\n{phase_lines}\n---\n",
        encoding="utf-8",
    )
    return plan


def write_small_plan(root: Path, phase: str, status: str) -> Path:
    """Write the smallest small-plan frontmatter carrying only ``status``."""
    plan = root / ".claude" / "plans" / f"{phase}.md"
    plan.write_text(f"---\nstatus: {status}\n---\n", encoding="utf-8")
    return plan


def branch_state_repo(tmp_path: Path) -> Path:
    """Create an outer repository with the shipped record-branch-state.sh."""
    root = tmp_path / "consumer"
    root.mkdir()
    run_git(root, "init", "-q")
    (root / ".gitignore").write_text(".claude/\n", encoding="utf-8")
    (root / "tracked.txt").write_text("base\n", encoding="utf-8")
    run_git(root, "add", ".gitignore", "tracked.txt")
    run_git(root, "commit", "-qm", "base")

    scripts = root / ".claude" / "hooks" / "scripts"
    scripts.mkdir(parents=True)
    for name in ("_lib-frontmatter.sh", "record-branch-state.sh"):
        shutil.copy2(HOOKS_SOURCE / "scripts" / name, scripts / name)
        (scripts / name).chmod(0o755)
    return root


def run_record_branch_state(
    root: Path, branch: str
) -> subprocess.CompletedProcess[str]:
    """Invoke the hook with the PostToolUse payload for a branch-create command."""
    payload = json.dumps(
        {"tool_name": "Bash", "tool_input": {"command": f"git checkout -b {branch}"}}
    )
    return subprocess.run(
        [
            "bash",
            str(root / ".claude" / "hooks" / "scripts" / "record-branch-state.sh"),
        ],
        cwd=root,
        input=payload,
        text=True,
        capture_output=True,
        check=False,
    )


def test_branch_creation_activates_a_planned_first_phase(tmp_path: Path) -> None:
    """Creating the implementation branch flips the first phase to in-progress."""
    root = branch_state_repo(tmp_path)
    plan = write_big_plan(root, ["phase-one", "phase-two"])
    write_small_plan(root, "phase-one", "planned")
    write_small_plan(root, "phase-two", "planned")
    run_git(root, "checkout", "-qb", "foo_implementation")

    result = run_record_branch_state(root, "foo_implementation")

    assert result.returncode == 0, result.stderr
    assert "status: in-progress" in (
        root / ".claude" / "plans" / "phase-one.md"
    ).read_text(encoding="utf-8")
    assert "status: planned" in (root / ".claude" / "plans" / "phase-two.md").read_text(
        encoding="utf-8"
    )
    assert "current_phase: phase-one" in plan.read_text(encoding="utf-8")
    assert "status: in-progress" in plan.read_text(encoding="utf-8")


def test_branch_creation_preserves_a_legacy_in_progress_first_phase(
    tmp_path: Path,
) -> None:
    """A pre-existing `in-progress` first phase activates without being rewritten."""
    root = branch_state_repo(tmp_path)
    write_big_plan(root, ["phase-one"])
    first_plan = write_small_plan(root, "phase-one", "in-progress")
    original_text = first_plan.read_text(encoding="utf-8")
    run_git(root, "checkout", "-qb", "foo_implementation")

    result = run_record_branch_state(root, "foo_implementation")

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert first_plan.read_text(encoding="utf-8") == original_text


@pytest.mark.parametrize("status", ("complete", "cancelled", "paused"))
def test_branch_creation_warns_instead_of_overwriting_an_unexpected_first_phase(
    tmp_path: Path, status: str
) -> None:
    """An already-terminal or paused first phase is reported, not clobbered."""
    root = branch_state_repo(tmp_path)
    write_big_plan(root, ["phase-one"])
    first_plan = write_small_plan(root, "phase-one", status)
    run_git(root, "checkout", "-qb", "foo_implementation")

    result = run_record_branch_state(root, "foo_implementation")

    assert result.returncode == 0, result.stderr
    assert f"status: {status}" in first_plan.read_text(encoding="utf-8")
    payload = json.loads(result.stdout)
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert "was not activated" in context
    assert status in context


def test_branch_creation_warns_about_a_duplicate_first_phase_status(
    tmp_path: Path,
) -> None:
    """A duplicate `status:` key reports plainly, never leaking the internal sentinel."""
    root = branch_state_repo(tmp_path)
    write_big_plan(root, ["phase-one"])
    first_plan = root / ".claude" / "plans" / "phase-one.md"
    original_text = "---\nstatus: planned\nstatus: in-progress\n---\n"
    first_plan.write_text(original_text, encoding="utf-8")
    run_git(root, "checkout", "-qb", "foo_implementation")

    result = run_record_branch_state(root, "foo_implementation")

    assert result.returncode == 0, result.stderr
    assert first_plan.read_text(encoding="utf-8") == original_text
    payload = json.loads(result.stdout)
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert "duplicate status metadata" in context
    assert "__DUPLICATE_FRONTMATTER_STATUS__" not in context


def test_branch_creation_rejects_a_traversal_shaped_first_phase(tmp_path: Path) -> None:
    """An unsafe phase slug can never be turned into a path and written to."""
    root = branch_state_repo(tmp_path)
    victim = root / "evil.md"
    # `status: planned` is deliberate: it is the one status that drives the
    # vulnerable `fm_write` call, so this fixture makes the byte-identity
    # assertion below load-bearing proof the write never fires, not merely a
    # coincidence of an unrelated status short-circuiting first.
    victim_text = "---\nstatus: planned\n---\n"
    victim.write_text(victim_text, encoding="utf-8")
    plan = write_big_plan(root, ["../../evil"])
    run_git(root, "checkout", "-qb", "foo_implementation")

    result = run_record_branch_state(root, "foo_implementation")

    assert result.returncode == 0, result.stderr
    assert victim.read_text(encoding="utf-8") == victim_text
    assert "current_phase:" not in plan.read_text(encoding="utf-8")
    payload = json.loads(result.stdout)
    context = payload["hookSpecificOutput"]["additionalContext"]
    assert "not a safe slug" in context


def test_branch_creation_skips_activation_when_first_phase_plan_is_missing(
    tmp_path: Path,
) -> None:
    """A declared phase with no plan file yet cannot crash branch-state recording."""
    root = branch_state_repo(tmp_path)
    plan = write_big_plan(root, ["phase-one"])
    run_git(root, "checkout", "-qb", "foo_implementation")

    result = run_record_branch_state(root, "foo_implementation")

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert "current_phase: phase-one" in plan.read_text(encoding="utf-8")
