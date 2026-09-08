"""Behavioral contracts for Codex and Claude sequential Stop wrappers."""

from __future__ import annotations

import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from generate_targets import (  # noqa: E402
    render_antigravity_hooks,
    render_claude_settings,
    render_codex_hooks,
)
from validate_targets import (  # noqa: E402
    antigravity_hook_errors,
    reporting_reminder_hook_errors,
    reporting_reminder_script_errors,
    validate_claude_lifecycle_hooks,
)

CODEX_STOP_SOURCE = REPO_ROOT / "shared" / "hooks" / "scripts" / "codex-stop.sh"
CLAUDE_STOP_SOURCE = REPO_ROOT / "shared" / "hooks" / "scripts" / "claude-stop.sh"
REPORTING_REMINDER_SOURCE = (
    REPO_ROOT / "shared" / "hooks" / "scripts" / "reporting-reminder.sh"
)
HOOK_SCRIPTS_SOURCE = REPO_ROOT / "shared" / "hooks" / "scripts"
STOP_CHILD_FIXTURE = """#!/usr/bin/env bash
set -euo pipefail
name="$(basename "$0")"
cat > "$CALL_LOG.$name.${1:-no-argument}"
printf '%s\\t%s\\n' "$name" "$*" >> "$CALL_LOG"
printf 'child stdout: %s\\n' "$(basename "$0")"
printf 'child stderr: %s\\n' "$(basename "$0")" >&2
if [[ "${FAIL_STEP:-}" == "$(basename "$0")" ]]; then
  exit 17
fi
"""


def copy_stop_wrapper(tmp_path: Path, source: Path) -> tuple[Path, Path]:
    """Copy one Stop wrapper beside deterministic child-hook fixtures."""
    hooks_dir = tmp_path / ".claude" / "hooks" / "scripts"
    hooks_dir.mkdir(parents=True)
    wrapper = hooks_dir / source.name
    shutil.copy(source, wrapper)
    wrapper.chmod(wrapper.stat().st_mode | stat.S_IXUSR)

    for name in ("session-log.sh", "stop-session-log-check.sh", "state-sync.sh"):
        script = hooks_dir / name
        script.write_text(STOP_CHILD_FIXTURE, encoding="utf-8")
        script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return wrapper, tmp_path / "calls.log"


@pytest.fixture
def codex_stop(tmp_path: Path) -> tuple[Path, Path]:
    """Copy the wrapper beside deterministic child-hook fixtures."""
    return copy_stop_wrapper(tmp_path, CODEX_STOP_SOURCE)


@pytest.fixture
def claude_stop(tmp_path: Path) -> tuple[Path, Path]:
    """Copy the Claude wrapper beside deterministic child-hook fixtures."""
    return copy_stop_wrapper(tmp_path, CLAUDE_STOP_SOURCE)


def run_stop_wrapper(
    wrapper: Path, call_log: Path, payload: str, *, fail_step: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run one copied Stop wrapper while recording every child invocation."""
    env = {**os.environ, "CALL_LOG": str(call_log)}
    if fail_step:
        env["FAIL_STEP"] = fail_step
    return subprocess.run(
        ["bash", str(wrapper)],
        input=payload,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def child_calls(call_log: Path) -> list[tuple[str, str]]:
    """Read child names and arguments in call order."""
    calls: list[tuple[str, str]] = []
    for line in call_log.read_text(encoding="utf-8").splitlines():
        name, args = line.split("\t", maxsplit=1)
        calls.append((name, args))
    return calls


def replayed_payload(call_log: Path, name: str, argument: str) -> str:
    """Read the exact payload received by one deterministic child fixture."""
    return (call_log.parent / f"{call_log.name}.{name}.{argument}").read_text(
        encoding="utf-8"
    )


def copy_real_lifecycle_hooks(root: Path) -> Path:
    """Install the real child hooks in a disposable AI-state workspace."""
    hooks_dir = root / ".claude" / "hooks" / "scripts"
    hooks_dir.mkdir(parents=True)
    for name in (
        "_lib-frontmatter.sh",
        "codex-stop.sh",
        "run-hook.sh",
        "session-log.sh",
        "state-sync.sh",
        "stop-session-log-check.sh",
    ):
        script = hooks_dir / name
        shutil.copy(HOOK_SCRIPTS_SOURCE / name, script)
        script.chmod(script.stat().st_mode | stat.S_IXUSR)
    return hooks_dir


def run_real_hook(
    script: Path, payload: dict[str, str], root: Path, env: dict[str, str], *args: str
) -> subprocess.CompletedProcess[str]:
    """Run one generated-hook command with a closed JSON stdin payload."""
    return subprocess.run(
        ["bash", str(script), *args],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        cwd=root,
        env=env,
    )


def test_codex_stop_replays_payload_sequentially_and_returns_only_json(
    codex_stop: tuple[Path, Path],
) -> None:
    """Stop has one payload-safe, best-effort sequence and clean stdout."""
    wrapper, call_log = codex_stop
    payload = '{"hook_event_name":"Stop","session_id":"turn-123"}\n'

    result = run_stop_wrapper(wrapper, call_log, payload)

    assert result.returncode == 0
    assert child_calls(call_log) == [
        ("session-log.sh", "openai-codex"),
        ("stop-session-log-check.sh", "openai-codex"),
        ("state-sync.sh", "checkpoint"),
        ("state-sync.sh", "publish"),
    ]
    assert replayed_payload(call_log, "session-log.sh", "openai-codex") == payload
    assert (
        replayed_payload(call_log, "stop-session-log-check.sh", "openai-codex")
        == payload
    )
    assert replayed_payload(call_log, "state-sync.sh", "checkpoint") == payload
    assert replayed_payload(call_log, "state-sync.sh", "publish") == payload
    assert json.loads(result.stdout) == {"continue": True}
    assert result.stdout == '{"continue":true}\n'
    assert "child stdout" not in result.stdout
    assert "child stderr" in result.stderr


def test_codex_stop_continues_after_child_failure(
    codex_stop: tuple[Path, Path],
) -> None:
    """A failed child warns but cannot prevent later durability boundaries."""
    wrapper, call_log = codex_stop
    payload = '{"hook_event_name":"Stop","session_id":"turn-456"}'

    result = run_stop_wrapper(
        wrapper, call_log, payload, fail_step="stop-session-log-check.sh"
    )

    assert result.returncode == 0
    assert [name for name, _args in child_calls(call_log)] == [
        "session-log.sh",
        "stop-session-log-check.sh",
        "state-sync.sh",
        "state-sync.sh",
    ]
    assert replayed_payload(call_log, "session-log.sh", "openai-codex") == payload
    assert (
        replayed_payload(call_log, "stop-session-log-check.sh", "openai-codex")
        == payload
    )
    assert replayed_payload(call_log, "state-sync.sh", "checkpoint") == payload
    assert replayed_payload(call_log, "state-sync.sh", "publish") == payload
    assert json.loads(result.stdout) == {"continue": True}
    assert "WARN codex-stop: stop-session-log-check.sh failed" in result.stderr


def test_claude_stop_replays_payload_sequentially_without_stdout(
    claude_stop: tuple[Path, Path],
) -> None:
    """Claude Stop serializes local durability and publication without response text."""
    wrapper, call_log = claude_stop
    payload = '{"hook_event_name":"Stop","session_id":"claude-turn-123"}\n'

    result = run_stop_wrapper(wrapper, call_log, payload)

    assert result.returncode == 0
    assert child_calls(call_log) == [
        ("session-log.sh", "claude-code"),
        ("stop-session-log-check.sh", "claude-code"),
        ("state-sync.sh", "checkpoint"),
        ("state-sync.sh", "publish"),
    ]
    assert replayed_payload(call_log, "session-log.sh", "claude-code") == payload
    assert (
        replayed_payload(call_log, "stop-session-log-check.sh", "claude-code")
        == payload
    )
    assert replayed_payload(call_log, "state-sync.sh", "checkpoint") == payload
    assert replayed_payload(call_log, "state-sync.sh", "publish") == payload
    assert result.stdout == ""
    assert "child stdout" not in result.stdout
    assert "child stdout" in result.stderr
    assert "child stderr" in result.stderr


def test_claude_stop_continues_after_child_failure(
    claude_stop: tuple[Path, Path],
) -> None:
    """A failed Claude Stop child cannot prevent checkpoint or publication."""
    wrapper, call_log = claude_stop
    payload = '{"hook_event_name":"Stop","session_id":"claude-turn-456"}'

    result = run_stop_wrapper(
        wrapper, call_log, payload, fail_step="stop-session-log-check.sh"
    )

    assert result.returncode == 0
    assert [name for name, _args in child_calls(call_log)] == [
        "session-log.sh",
        "stop-session-log-check.sh",
        "state-sync.sh",
        "state-sync.sh",
    ]
    assert replayed_payload(call_log, "session-log.sh", "claude-code") == payload
    assert (
        replayed_payload(call_log, "stop-session-log-check.sh", "claude-code")
        == payload
    )
    assert replayed_payload(call_log, "state-sync.sh", "checkpoint") == payload
    assert replayed_payload(call_log, "state-sync.sh", "publish") == payload
    assert result.stdout == ""
    assert "WARN claude-stop: stop-session-log-check.sh failed" in result.stderr


def test_online_prompt_pushes_offline_stop_plan_and_diagnostic(tmp_path: Path) -> None:
    """A later prompt checkpoints Stop's offline diagnostics before retrying push."""
    root = tmp_path / "workspace"
    root.mkdir()
    hooks_dir = copy_real_lifecycle_hooks(root)
    plan = root / ".claude" / "plans" / "offline-stop.md"
    plan.parent.mkdir()
    plan.write_text("offline plan\n", encoding="utf-8")
    remote = tmp_path / "state.git"
    env = {
        **os.environ,
        "AI_STATE_REPO_ROOT": str(root),
        "AI_STATE_REMOTE": str(remote),
        "AI_STATE_BRANCH": "ai-state",
        "GIT_AUTHOR_NAME": "Lifecycle Test",
        "GIT_AUTHOR_EMAIL": "lifecycle@example.com",
        "GIT_COMMITTER_NAME": "Lifecycle Test",
        "GIT_COMMITTER_EMAIL": "lifecycle@example.com",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
        "UV_CACHE_DIR": "/tmp/uv-cache",
    }

    offline_stop = run_real_hook(
        hooks_dir / "codex-stop.sh",
        {"hook_event_name": "Stop", "session_id": "offline-stop"},
        root,
        env,
    )

    assert offline_stop.returncode == 0
    assert json.loads(offline_stop.stdout) == {"continue": True}
    errors = root / ".claude" / "session_logs" / "hooks-errors.log"
    assert "fetch from origin/ai-state failed" in errors.read_text(encoding="utf-8")

    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    online_prompt = run_real_hook(
        hooks_dir / "run-hook.sh",
        {"hook_event_name": "UserPromptSubmit", "session_id": "online-prompt"},
        root,
        env,
        "state-sync.sh",
        "push",
    )

    assert online_prompt.returncode == 0, online_prompt.stderr
    assert (
        subprocess.run(
            ["git", "-C", str(remote), "show", "ai-state:plans/offline-stop.md"],
            text=True,
            capture_output=True,
            check=False,
        ).stdout
        == "offline plan\n"
    )
    remote_errors = subprocess.run(
        ["git", "-C", str(remote), "show", "ai-state:session_logs/hooks-errors.log"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert "fetch from origin/ai-state failed" in remote_errors.stdout


def test_rendered_codex_lifecycle_uses_single_stop_wrapper(tmp_path: Path) -> None:
    """Generated Codex lifecycle hooks use the planned local/network boundaries."""
    hooks_path = tmp_path / "hooks.json"

    render_codex_hooks(hooks_path)

    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))["hooks"]
    stop = hooks["Stop"]
    assert len(stop) == 1
    assert len(stop[0]["hooks"]) == 1
    assert "codex-stop.sh" in stop[0]["hooks"][0]["command"]
    assert "state-sync.sh" not in stop[0]["hooks"][0]["command"]

    prompt = hooks["UserPromptSubmit"]
    assert len(prompt) == 1
    assert len(prompt[0]["hooks"]) == 2
    assert "state-sync.sh push" in prompt[0]["hooks"][0]["command"]
    assert prompt[0]["hooks"][0]["timeout"] == 60
    assert (
        "reporting-reminder.sh prompt openai-codex" in prompt[0]["hooks"][1]["command"]
    )

    posttool = hooks["PostToolUse"]
    assert len(posttool) == 1
    assert [
        "record-branch-state.sh" in handler["command"]
        or "record-commit-closeout.sh" in handler["command"]
        or "context-mode-dispatch.sh" in handler["command"]
        or "reporting-reminder.sh late-report openai-codex" in handler["command"]
        for handler in posttool[0]["hooks"]
    ] == [True, True, True, True]
    assert reporting_reminder_hook_errors(hooks, "openai-codex") == []
    prompt[0]["hooks"][1]["timeout"] = 99
    assert reporting_reminder_hook_errors(hooks, "openai-codex") == [
        "openai-codex UserPromptSubmit must exactly retain state sync and add one reminder"
    ]

    session_end = hooks["SessionEnd"]
    assert len(session_end) == 1
    assert len(session_end[0]["hooks"]) == 1
    session_end_handler = session_end[0]["hooks"][0]
    assert "state-sync.sh checkpoint" in session_end_handler["command"]
    assert "publish" not in session_end_handler["command"]
    assert "push" not in session_end_handler["command"]
    assert session_end_handler["timeout"] == 3


def test_rendered_antigravity_hook_uses_only_proven_pretool_safety(
    tmp_path: Path,
) -> None:
    """Generated catch-all dispatch sends unknown tools to the denying bridge."""
    hooks_path = tmp_path / "hooks.json"

    render_antigravity_hooks(hooks_path)

    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))
    assert antigravity_hook_errors(hooks) == []
    assert set(hooks) == {"bootstrap-safety"}
    assert set(hooks["bootstrap-safety"]) == {"PreToolUse"}
    handler = hooks["bootstrap-safety"]["PreToolUse"][0]
    assert handler["matcher"] == "*"

    result = subprocess.run(
        ["bash", "-c", handler["hooks"][0]["command"]],
        cwd=REPO_ROOT,
        input=json.dumps({"toolCall": {"name": "unverified_write", "args": {}}}),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["decision"] == "deny"


def test_rendered_claude_lifecycle_uses_serialized_durability_boundaries(
    tmp_path: Path,
) -> None:
    """Generated Claude settings keep lifecycle boundaries single and ordered."""
    settings_path = tmp_path / "settings.json"

    render_claude_settings(settings_path)

    hooks = json.loads(settings_path.read_text(encoding="utf-8"))["hooks"]
    stop = hooks["Stop"]
    assert len(stop) == 1
    assert len(stop[0]["hooks"]) == 1
    assert "claude-stop.sh" in stop[0]["hooks"][0]["command"]
    assert "state-sync.sh" not in stop[0]["hooks"][0]["command"]
    assert stop[0]["hooks"][0]["timeout"] == 180

    prompt = hooks["UserPromptSubmit"]
    assert len(prompt) == 1
    assert len(prompt[0]["hooks"]) == 2
    assert "state-sync.sh push" in prompt[0]["hooks"][0]["command"]
    assert prompt[0]["hooks"][0]["timeout"] == 60
    assert (
        "reporting-reminder.sh prompt claude-code" in prompt[0]["hooks"][1]["command"]
    )

    posttool = hooks["PostToolUse"]
    assert len(posttool) == 1
    assert [
        "record-branch-state.sh" in handler["command"]
        or "record-commit-closeout.sh" in handler["command"]
        or "context-mode-dispatch.sh" in handler["command"]
        or "reporting-reminder.sh late-report claude-code" in handler["command"]
        for handler in posttool[0]["hooks"]
    ] == [True, True, True, True]

    stop_failure = hooks["StopFailure"]
    assert len(stop_failure) == 1
    assert len(stop_failure[0]["hooks"]) == 1
    stop_failure_handler = stop_failure[0]["hooks"][0]
    assert "state-sync.sh checkpoint" in stop_failure_handler["command"]
    assert "publish" not in stop_failure_handler["command"]
    assert "push" not in stop_failure_handler["command"]
    assert stop_failure_handler["timeout"] == 10

    session_end = hooks["SessionEnd"]
    assert len(session_end) == 1
    assert len(session_end[0]["hooks"]) == 1
    session_end_handler = session_end[0]["hooks"][0]
    assert "state-sync.sh push" in session_end_handler["command"]
    assert session_end_handler["timeout"] == 60


def test_claude_lifecycle_validation_rejects_non_command_prompt_handler(
    tmp_path: Path,
) -> None:
    """Claude prompt publication must retain a command-handler schema."""
    settings_path = tmp_path / "settings.json"
    render_claude_settings(settings_path)
    hooks = json.loads(settings_path.read_text(encoding="utf-8"))["hooks"]

    errors: list[str] = []
    validate_claude_lifecycle_hooks(hooks, errors)
    assert not errors

    hooks["UserPromptSubmit"][0]["hooks"][0]["type"] = "prompt"
    validate_claude_lifecycle_hooks(hooks, errors)

    assert errors == [
        "claude-code UserPromptSubmit must exactly retain state sync and add one reminder"
    ]


def run_reporting_reminder(
    mode: str, provider: str, payload: str, script: Path = REPORTING_REMINDER_SOURCE
) -> subprocess.CompletedProcess[str]:
    """Run the canonical reminder hook with controlled input."""
    return subprocess.run(
        ["bash", str(script), mode, provider],
        input=payload,
        text=True,
        capture_output=True,
        check=False,
        cwd=REPO_ROOT,
    )


def test_reporting_reminder_prompt_is_one_bounded_context_object() -> None:
    """Prompt mode emits only its fixed UserPromptSubmit context object."""
    result = run_reporting_reminder(
        "prompt", "claude-code", '{"hook_event_name":"UserPromptSubmit"}'
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert result.stdout.count("\n") == 1
    output = json.loads(result.stdout)
    context = output["hookSpecificOutput"]
    assert context["hookEventName"] == "UserPromptSubmit"
    assert context["additionalContext"] == (
        "For user-facing updates, use direct language; explain internal labels and "
        "uncommon abbreviations, and avoid idioms. State what options mean in "
        "practice. Preserve exact technical text."
    )
    assert len(context["additionalContext"].encode()) <= 200
    assert set(context) == {"hookEventName", "additionalContext"}
    assert (
        reporting_reminder_script_errors(
            REPORTING_REMINDER_SOURCE.read_text(encoding="utf-8")
        )
        == []
    )


@pytest.mark.parametrize(
    "command",
    (
        "uv run python .claude/scripts/verify.py closeout --format json --persist",
        "uv run python .claude/scripts/record_findings.py shared --out findings.json",
    ),
)
def test_reporting_reminder_emits_once_at_selected_late_boundaries(
    command: str,
) -> None:
    """Late mode only injects after one recognized closeout command."""
    payload = json.dumps(
        {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "tool_response": {},
        }
    )
    result = run_reporting_reminder("late-report", "openai-codex", payload)

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert result.stdout.count("\n") == 1
    assert (
        json.loads(result.stdout)["hookSpecificOutput"]["hookEventName"]
        == "PostToolUse"
    )


def copy_reporting_reminder(root: Path, library_text: str | None = None) -> Path:
    """Copy the reminder and helper into a disposable generated-hook root."""
    hooks_dir = root / ".claude" / "hooks" / "scripts"
    hooks_dir.mkdir(parents=True)
    script = hooks_dir / "reporting-reminder.sh"
    shutil.copy(REPORTING_REMINDER_SOURCE, script)
    script.chmod(0o755)
    library = hooks_dir / "_lib-frontmatter.sh"
    if library_text is None:
        shutil.copy(HOOK_SCRIPTS_SOURCE / "_lib-frontmatter.sh", library)
    else:
        library.write_text(library_text, encoding="utf-8")
    library.chmod(0o755)
    return script


def reminder_payload(command: str) -> str:
    """Return one representative completed Bash PostToolUse payload."""
    return json.dumps(
        {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "tool_response": {},
        }
    )


def run_git(args: list[str], cwd: Path) -> None:
    """Run one git command with a hermetic identity, matching the shipped hook."""
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Lifecycle Test",
            "-c",
            "user.email=lifecycle@example.com",
            *args,
        ],
        cwd=cwd,
        check=True,
    )


def phase_completion_reminder_script(tmp_path: Path, status: str = "complete") -> Path:
    """Create the minimum implementation-plan state for a completion commit.

    Mirrors the shipped topology (docs/architecture.md): the outer repository
    gitignores `.claude/`, and a separate nested Git repository rooted at
    `.claude/` holds the committed plan files that `head_frontmatter_value`
    reads from its own HEAD. A flat single repository tracking
    `.claude/plans/*.md` directly (the previous shape of this fixture) hides
    the defect it is meant to catch, because that shape never exists outside
    tests.
    """
    script = copy_reporting_reminder(tmp_path)
    run_git(["init", "-q"], tmp_path)
    (tmp_path / ".gitignore").write_text(".claude/\n", encoding="utf-8")
    (tmp_path / "seed.txt").write_text("seed\n", encoding="utf-8")
    run_git(["add", "seed.txt", ".gitignore"], tmp_path)
    run_git(["commit", "-q", "-m", "seed"], tmp_path)
    subprocess.run(
        ["git", "checkout", "-q", "-b", "phase_implementation"],
        cwd=tmp_path,
        check=True,
    )
    plans = tmp_path / ".claude" / "plans"
    plans.mkdir()
    (plans / "phase.md").write_text(
        "---\nstatus: in-progress\ncurrent_phase: phase-one\n---\n",
        encoding="utf-8",
    )
    (plans / "phase-one.md").write_text(
        f"---\nstatus: {status}\n---\n", encoding="utf-8"
    )
    nested = tmp_path / ".claude"
    run_git(["init", "-q"], nested)
    run_git(["add", "plans"], nested)
    run_git(["commit", "-q", "-m", "phase state"], nested)
    return script


@pytest.mark.parametrize(
    "command",
    (
        'git -C . commit -m "phase complete"',
        'git --git-dir .git --work-tree . commit -m "phase complete"',
    ),
)
def test_reporting_reminder_emits_after_a_phase_completion_commit(
    tmp_path: Path, command: str
) -> None:
    """A completed current phase permits direct commits targeting this repository."""
    script = phase_completion_reminder_script(tmp_path)
    result = run_reporting_reminder(
        "late-report",
        "claude-code",
        reminder_payload(command),
        script,
    )

    assert result.returncode == 0, result.stderr
    assert (
        json.loads(result.stdout)["hookSpecificOutput"]["hookEventName"]
        == "PostToolUse"
    )


def test_reporting_reminder_survives_post_closeout_phase_advance(
    tmp_path: Path,
) -> None:
    """Late classification reads the commit, not mutable post-closeout state."""
    script = phase_completion_reminder_script(tmp_path)
    plan = tmp_path / ".claude" / "plans" / "phase.md"
    plan.write_text("---\nstatus: complete\ncurrent_phase: \n---\n", encoding="utf-8")
    result = run_reporting_reminder(
        "late-report",
        "claude-code",
        reminder_payload('git commit -m "phase complete"'),
        script,
    )

    assert result.returncode == 0, result.stderr
    assert (
        json.loads(result.stdout)["hookSpecificOutput"]["hookEventName"]
        == "PostToolUse"
    )


def test_reporting_reminder_excludes_uncommitted_status_advance(
    tmp_path: Path,
) -> None:
    """An uncommitted working-tree edit cannot manufacture a false reminder."""
    script = phase_completion_reminder_script(tmp_path, status="in-progress")
    plan = tmp_path / ".claude" / "plans" / "phase-one.md"
    plan.write_text("---\nstatus: complete\n---\n", encoding="utf-8")
    result = run_reporting_reminder(
        "late-report",
        "claude-code",
        reminder_payload('git commit -m "phase complete"'),
        script,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""


def test_reporting_reminder_rejects_external_git_repositories(tmp_path: Path) -> None:
    """Global Git repository options must resolve back to the hook repository."""
    script = phase_completion_reminder_script(tmp_path)
    external = tmp_path.parent / "external-repository"
    external.mkdir()
    run_git(["init", "-q"], external)
    (external / "seed.txt").write_text("seed\n", encoding="utf-8")
    run_git(["add", "seed.txt"], external)
    run_git(["commit", "-q", "-m", "seed"], external)

    for command in (
        f'git -C "{external}" commit -m "phase complete"',
        f'git --git-dir "{external / ".git"}" --work-tree "{external}" commit -m "phase complete"',
    ):
        result = run_reporting_reminder(
            "late-report", "openai-codex", reminder_payload(command), script
        )
        assert result.returncode == 0, result.stderr
        assert result.stdout == ""


@pytest.mark.parametrize(
    "command",
    (
        "uv run python .claude/scripts/verify.py phase --format json --persist",
        "git status",
        "printf 'uv run python .claude/scripts/verify.py closeout'",
        "uv run python .claude/scripts/verify.py closeout || true",
        "uv run python .claude/scripts/record_findings.py shared ; printf -- --out",
    ),
)
def test_reporting_reminder_ignores_non_boundary_bash_commands(command: str) -> None:
    """Normal Bash commands leave standard output empty."""
    payload = json.dumps(
        {
            "hook_event_name": "PostToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": command},
            "tool_response": {},
        }
    )
    result = run_reporting_reminder("late-report", "claude-code", payload)

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert result.stderr == ""


@pytest.mark.parametrize(
    ("command", "status"),
    (
        ('git -C .claude commit -m "phase complete"', "complete"),
        ('git commit -m "fixup! phase complete"', "complete"),
        ('git commit -m "checkpoint work"', "paused"),
        ('git commit -m "ordinary work"', "in-progress"),
    ),
)
def test_reporting_reminder_excludes_non_phase_commits(
    tmp_path: Path, command: str, status: str
) -> None:
    """Nested, bypass, paused, and ordinary commits do not inject a reminder."""
    script = phase_completion_reminder_script(tmp_path, status)
    result = run_reporting_reminder(
        "late-report", "openai-codex", reminder_payload(command), script
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""


def test_reporting_reminder_fails_open_when_a_helper_fails(tmp_path: Path) -> None:
    """An unexpected helper failure emits no partial decision."""
    script = copy_reporting_reminder(
        tmp_path,
        'repo_root_from_script() { cd "$SCRIPT_DIR/../../.." && pwd; }\n'
        "payload_parseable() { return 0; }\n"
        "additional_context() { return 1; }\n",
    )
    result = run_reporting_reminder("prompt", "claude-code", "{}", script)

    assert result.returncode == 0
    assert result.stdout == ""
    assert "WARN reporting-reminder: internal error; skipping reminder" in result.stderr


@pytest.mark.parametrize(
    ("mode", "provider", "payload"),
    (
        ("late-report", "claude-code", "not json"),
        ("invalid", "claude-code", "{}"),
        ("prompt", "unsupported", "{}"),
    ),
)
def test_reporting_reminder_warns_and_never_blocks_invalid_inputs(
    mode: str, provider: str, payload: str
) -> None:
    """Malformed input and unsupported arguments fail open without JSON output."""
    result = run_reporting_reminder(mode, provider, payload)

    assert result.returncode == 0
    assert result.stdout == ""
    assert "WARN reporting-reminder:" in result.stderr
