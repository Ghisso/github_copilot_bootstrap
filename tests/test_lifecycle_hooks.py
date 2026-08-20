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
    validate_claude_lifecycle_hooks,
)

CODEX_STOP_SOURCE = REPO_ROOT / "shared" / "hooks" / "scripts" / "codex-stop.sh"
CLAUDE_STOP_SOURCE = REPO_ROOT / "shared" / "hooks" / "scripts" / "claude-stop.sh"
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
    assert len(prompt[0]["hooks"]) == 1
    assert "state-sync.sh push" in prompt[0]["hooks"][0]["command"]
    assert prompt[0]["hooks"][0]["timeout"] == 60

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
    assert len(prompt[0]["hooks"]) == 1
    assert "state-sync.sh push" in prompt[0]["hooks"][0]["command"]
    assert prompt[0]["hooks"][0]["timeout"] == 60

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

    assert errors == ["Claude UserPromptSubmit handler must be a command"]
