"""Regression coverage for branch-creation phase activation."""

from __future__ import annotations

import json
import os
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


# --------------------------------------------------------------------------
# GR-009: creating an implementation branch runs the plan checks on the big
# plan and the phase files it lists, and denies on any error.
# --------------------------------------------------------------------------

GATE_CLIENTS = (
    pytest.param("claude-code", id="claude-code-guard-chain"),
    pytest.param("openai-codex", id="codex-guard-chain"),
    pytest.param("github-copilot", id="copilot-direct-hook"),
    pytest.param("google-antigravity", id="antigravity-bridge"),
)
BRANCH_COMMAND = "git checkout -b foo_implementation"
VALID_BIG_PLAN = (
    "---\nname: foo\ntype: big-plan\nstatus: planning\n"
    "originating_branch: dev\nimplementation_branch: foo_implementation\n"
    "phases:\n  - phase-one\n---\n\n# Foo\n"
)
SMALL_PLAN_HEAD = (
    "---\nname: phase-one\ntype: small-plan\nparent_plan: foo\n"
    "phase_index: 1\nstatus: planned\n---\n\n# Phase one\n"
)
VALID_SMALL_PLAN = SMALL_PLAN_HEAD + "\n## Verification\n\n```bash\ntrue\n```\n"


def plan_gate_repo(tmp_path: Path) -> Path:
    """A clean `dev` checkout with the shipped hooks and plan validator."""
    root = tmp_path / "consumer"
    root.mkdir()
    run_git(root, "init", "-q", "-b", "dev")
    (root / ".gitignore").write_text(".claude/\n", encoding="utf-8")
    run_git(root, "add", ".gitignore")
    run_git(root, "commit", "-qm", "base")
    hooks = root / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "scripts").symlink_to(HOOKS_SOURCE / "scripts", target_is_directory=True)
    (root / ".claude" / "session_logs").mkdir()
    scripts = root / ".claude" / "scripts"
    scripts.mkdir()
    shutil.copy2(
        REPO_ROOT / "scripts" / "validate_plan_frontmatter.py",
        scripts / "validate_plan_frontmatter.py",
    )
    plans = root / ".claude" / "plans"
    plans.mkdir()
    (plans / "foo.md").write_text(VALID_BIG_PLAN, encoding="utf-8")
    (plans / "phase-one.md").write_text(VALID_SMALL_PLAN, encoding="utf-8")
    return root


def branch_gate_decision(
    root: Path,
    client: str,
    command: str = BRANCH_COMMAND,
    tool_name: str = "Bash",
) -> str:
    """Run the branch-creation gate the way `client` reaches it, returning
    `allow`, `ask`, or `deny` plus the reason text."""
    scripts = root / ".claude" / "hooks" / "scripts"
    env = {**os.environ, "REPO_ROOT": str(root)}
    payload: dict[str, object]
    if client == "google-antigravity":
        payload = {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": command, "Cwd": str(root)},
            }
        }
        argv = ["python3", str(scripts / "antigravity-pretool.py")]
    else:
        payload = {"tool_name": tool_name, "tool_input": {"command": command}}
        guard = (
            "enforce-branch-state.sh"
            if client == "github-copilot"
            else "pretool-bash-guard.sh"
        )
        argv = ["bash", str(scripts / guard), client]
    result = subprocess.run(
        argv,
        cwd=root,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    output = result.stdout.strip()
    if not output:
        return "allow"
    response = json.loads(output)
    if client == "google-antigravity":
        return f"{response['decision']} {response.get('reason', '')}".strip()
    specific = response["hookSpecificOutput"]
    return f"{specific['permissionDecision']} {specific['permissionDecisionReason']}"


@pytest.mark.parametrize("client", GATE_CLIENTS)
def test_branch_creation_allows_a_valid_plan(tmp_path: Path, client: str) -> None:
    root = plan_gate_repo(tmp_path)

    assert branch_gate_decision(root, client) == "allow"


@pytest.mark.parametrize("client", GATE_CLIENTS)
def test_branch_creation_denies_a_small_plan_without_a_verification_block(
    tmp_path: Path, client: str
) -> None:
    root = plan_gate_repo(tmp_path)
    (root / ".claude" / "plans" / "phase-one.md").write_text(
        SMALL_PLAN_HEAD, encoding="utf-8"
    )

    decision = branch_gate_decision(root, client)

    assert decision.startswith("deny "), decision
    assert "L1 verification-block-missing" in decision
    assert "phase-one.md" in decision


@pytest.mark.parametrize("client", GATE_CLIENTS)
def test_branch_creation_ignores_an_unrelated_invalid_draft(
    tmp_path: Path, client: str
) -> None:
    """The validator is given only this plan's files, so a broken draft that
    is not listed in `phases` cannot block the branch."""
    root = plan_gate_repo(tmp_path)
    draft = root / ".claude" / "plans" / "unrelated-draft.md"
    draft.write_text("---\ntype: small-plan\n---\n\n# Draft\n", encoding="utf-8")
    validator = root / ".claude" / "scripts" / "validate_plan_frontmatter.py"
    whole_directory = subprocess.run(
        ["python3", str(validator)],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )
    assert whole_directory.returncode != 0, "the draft must be invalid on its own"

    assert branch_gate_decision(root, client) == "allow"


def test_branch_creation_names_only_the_first_errors(tmp_path: Path) -> None:
    root = plan_gate_repo(tmp_path)
    plans = root / ".claude" / "plans"
    (plans / "foo.md").write_text(
        VALID_BIG_PLAN.replace(
            "phases:\n  - phase-one", "phases:\n  - a\n  - b\n  - c\n  - d"
        ),
        encoding="utf-8",
    )
    for phase in ("a", "b", "c", "d"):
        (plans / f"{phase}.md").write_text(
            SMALL_PLAN_HEAD.replace("phase-one", phase), encoding="utf-8"
        )

    decision = branch_gate_decision(root, "github-copilot")

    assert decision.count("L1 verification-block-missing") == 3
    assert "(and 1 more)" in decision


def test_branch_creation_denies_an_invalid_big_plan(tmp_path: Path) -> None:
    root = plan_gate_repo(tmp_path)
    (root / ".claude" / "plans" / "foo.md").write_text(
        VALID_BIG_PLAN.replace("originating_branch: dev\n", ""), encoding="utf-8"
    )

    decision = branch_gate_decision(root, "github-copilot")

    assert decision.startswith("deny "), decision
    assert "missing required field: originating_branch" in decision


@pytest.mark.parametrize("client", ("claude-code", "github-copilot"))
def test_branch_creation_denies_when_the_validator_is_missing(
    tmp_path: Path, client: str
) -> None:
    root = plan_gate_repo(tmp_path)
    (root / ".claude" / "scripts" / "validate_plan_frontmatter.py").unlink()

    decision = branch_gate_decision(root, client)

    assert decision.startswith("deny "), decision
    assert "missing plan-frontmatter validator" in decision


def test_branch_creation_denies_a_phase_name_that_is_not_a_safe_slug(
    tmp_path: Path,
) -> None:
    root = plan_gate_repo(tmp_path)
    (root / ".claude" / "plans" / "foo.md").write_text(
        VALID_BIG_PLAN.replace("  - phase-one", "  - ../../evil"), encoding="utf-8"
    )

    decision = branch_gate_decision(root, "github-copilot")

    assert decision.startswith("deny "), decision
    assert "not a safe plan name" in decision


def test_branch_creation_skips_a_listed_phase_whose_plan_does_not_exist_yet(
    tmp_path: Path,
) -> None:
    """Same tolerance as the commit gate: a missing phase file has nothing to
    validate, and the commit gate requires the current phase's file."""
    root = plan_gate_repo(tmp_path)
    (root / ".claude" / "plans" / "phase-one.md").unlink()

    assert branch_gate_decision(root, "github-copilot") == "allow"


@pytest.mark.parametrize("tool_name", ("run_in_terminal", "send_to_terminal"))
def test_branch_creation_gate_applies_to_vs_code_copilot_terminal_tools(
    tmp_path: Path, tool_name: str
) -> None:
    """VS Code's Local harness names its terminal tools `run_in_terminal` and
    `send_to_terminal`; the command is `tool_input.command`."""
    root = plan_gate_repo(tmp_path)
    assert branch_gate_decision(root, "github-copilot", tool_name=tool_name) == "allow"
    (root / ".claude" / "plans" / "phase-one.md").write_text(
        SMALL_PLAN_HEAD, encoding="utf-8"
    )

    decision = branch_gate_decision(root, "github-copilot", tool_name=tool_name)

    assert decision.startswith("deny "), decision
    assert "L1 verification-block-missing" in decision


def test_branch_creation_gate_ignores_a_tool_that_is_not_a_shell(
    tmp_path: Path,
) -> None:
    """A tool whose name is neither a shell nor a known terminal tool is not
    judged as a command, even when its input has a `command` key."""
    root = plan_gate_repo(tmp_path)
    (root / ".claude" / "plans" / "phase-one.md").write_text(
        SMALL_PLAN_HEAD, encoding="utf-8"
    )

    decision = branch_gate_decision(
        root, "github-copilot", tool_name="manage_todo_list"
    )

    assert decision == "allow"
