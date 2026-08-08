"""Regression coverage for shared hook gate helpers."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_SRC = REPO_ROOT / "shared" / "hooks" / "scripts"


def _bash_source(script: Path, expression: str) -> subprocess.CompletedProcess[str]:
    command = [
        "bash",
        "-lc",
        f". {shlex.quote(str(script))}; {expression}",
    ]
    return subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def _git_targets_nested_claude(command: str, subcommand: str) -> int:
    result = _bash_source(
        SCRIPT_SRC / "_lib-frontmatter.sh",
        f"git_targets_nested_claude {shlex.quote(command)} {shlex.quote(subcommand)}; printf '%s' $?",
    )
    assert result.returncode == 0, result.stderr
    return int(result.stdout.strip())


def test_git_targets_nested_claude_detects_nested_claude_paths() -> None:
    assert _git_targets_nested_claude("git -C .claude commit -m hi", "commit") == 0
    assert (
        _git_targets_nested_claude("git --git-dir .claude/.git commit -m hi", "commit")
        == 0
    )
    assert (
        _git_targets_nested_claude("git --work-tree .claude commit -m hi", "commit")
        == 0
    )
    assert _git_targets_nested_claude("git commit -m hi", "commit") == 1


def test_git_targets_nested_claude_does_not_exempt_mixed_compound_commands() -> None:
    """A nested-.claude git call earlier in a compound command must not exempt
    an unrelated outer-repo commit/push later in the same command — the
    original fix checked "does ANY git call in the string touch .claude"
    instead of "does THIS subcommand's own invocation touch .claude", which
    let `git -C .claude status && git commit -m ...` skip the ceremony gate
    entirely for the outer commit."""
    bypass_commit = 'git -C .claude status && git commit -m "sneaky outer commit"'
    assert _git_targets_nested_claude(bypass_commit, "commit") == 1

    bypass_push = "git -C .claude fetch origin && git push origin main"
    assert _git_targets_nested_claude(bypass_push, "push") == 1

    # The inverse (nested call after the outer one) must also stay gated.
    bypass_commit_reversed = (
        'git commit -m "sneaky outer commit" ; git -C .claude status'
    )
    assert _git_targets_nested_claude(bypass_commit_reversed, "commit") == 1

    # Two genuinely nested invocations chained together should still exempt.
    both_nested = "git -C .claude add -A && git -C .claude commit -m hi"
    assert _git_targets_nested_claude(both_nested, "commit") == 0


def _run_protect_files(payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_SRC / "protect-files.sh"), "openai-codex"],
        cwd=REPO_ROOT,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env={
            **os.environ,
            "REPO_ROOT": str(REPO_ROOT),
            "TARGET_ID": "openai-codex",
            "UV_CACHE_DIR": os.environ.get("UV_CACHE_DIR", "/tmp/uv-cache"),
        },
    )


def test_protect_files_python_pass_ignores_slashy_free_text() -> None:
    payload = {
        "tool_name": "edit",
        "tool_input": {
            "comment": "Please update the docs/section or call out /not-a-path in the note."
        },
    }
    process = _run_protect_files(payload)
    assert process.returncode == 0, process.stderr
    assert process.stdout.strip() == "", f"unexpected stdout: {process.stdout!r}"
    assert process.stderr.strip() == "", f"unexpected stderr: {process.stderr!r}"


@pytest.mark.parametrize(
    "command",
    (
        "rg codex .codex/config.toml 2>/dev/null",
        "wc -l .codex/config.toml 2>/dev/null",
        "cat .codex/config.toml 2>/dev/null",
        "sed -n '1,10p' .codex/config.toml 2>/dev/null",
    ),
)
def test_protect_files_allows_read_only_or_non_targeted_protected_paths(
    command: str,
) -> None:
    """Only mutation targets, not incidental read operands, are protected."""
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": command},
    }
    process = _run_protect_files(payload)
    assert process.returncode == 0, process.stderr
    assert process.stdout == ""


@pytest.mark.parametrize(
    "command",
    (
        "printf x > .env",
        "printf x | tee .env",
        "sed -i 's/x/y/' .codex/config.toml",
        "perl -i -pe 's/x/y/' .codex/config.toml",
        "touch .env && cat README.md",
        "mv README.md .env",
        "chmod 600 .env",
        "chown root .env",
        "sed -ni 's/x/y/' .codex/config.toml",
        "perl -pi -e 's/x/y/' .codex/config.toml",
        "sudo touch .env",
        "env FOO=1 touch .env",
        "command touch .env",
        "ln -s README.md .env",
        "dd if=README.md of=.env",
        'python3 -c \'open(".env", "w")\'',
        "bash -c 'cat credentials-prod.json > /tmp/out'",
        'python3 -c \'open("deploy.key", "w")\'',
        "bash -c 'cat uv.lock > /tmp/out'",
        'python3 -c \'open("db_secret_backup.txt", "w")\'',
        "bash -c 'cat service.pem > /tmp/out'",
        'python3 -c \'open(".claude/hooks/guard.sh", "w")\'',
        "bash -c 'cat .codex/hooks.json > /tmp/out'",
        "cp .env public-example.env",
        "touch nested/../.claude/settings.json",
        "cat README.md\ntouch .env",
    ),
)
def test_protect_files_blocks_mutation_targets(command: str) -> None:
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


@pytest.mark.parametrize(
    "payload",
    (
        {"tool_name": "Write", "tool_input": {"path": ".env"}},
        {
            "tool_name": "apply_patch",
            "tool_input": {
                "command": "*** Begin Patch\n*** Update File: .codex/config.toml\n*** End Patch\n"
            },
        },
    ),
)
def test_protect_files_blocks_native_edits(payload: dict) -> None:
    process = _run_protect_files(payload)
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


def test_protect_files_fails_closed_for_malformed_command_and_without_uv() -> None:
    malformed = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": "sed -i 'unterminated .env"}}
    )
    assert malformed.returncode == 2
    assert '"permissionDecision":"deny"' in malformed.stdout

    env = {
        **os.environ,
        "PATH": os.pathsep.join(
            part
            for part in os.environ["PATH"].split(os.pathsep)
            if not (Path(part) / "uv").exists()
        ),
    }
    process = subprocess.run(
        ["bash", str(SCRIPT_SRC / "protect-files.sh")],
        cwd=REPO_ROOT,
        input=json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "sed -i 's/x/y/' .env"}}
        ),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


def test_bash_safety_wrapper_short_circuits_first_decision_and_fails_closed() -> None:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "touch .env"}})
    result = subprocess.run(
        ["bash", str(SCRIPT_SRC / "pretool-bash-guard.sh"), "openai-codex"],
        cwd=REPO_ROOT,
        input=payload,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert '"permissionDecision":"deny"' in result.stdout

    malformed = subprocess.run(
        ["bash", str(SCRIPT_SRC / "pretool-bash-guard.sh"), "openai-codex"],
        cwd=REPO_ROOT,
        input="{bad",
        text=True,
        capture_output=True,
        check=False,
    )
    assert malformed.returncode == 2
    assert '"permissionDecision":"deny"' in malformed.stdout


def test_bash_safety_wrapper_uses_ordered_isolated_children(tmp_path: Path) -> None:
    """Fixture guards prove order, first decision, and malformed fail-closed."""
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("pretool-bash-guard.sh", "_lib-frontmatter.sh"):
        shutil.copy2(SCRIPT_SRC / name, scripts / name)
    guards = (
        "protect-files.sh",
        "git-protection.sh",
        "enforce-branch-state.sh",
        "enforce-commit-gate.sh",
        "enforce-pr-gate.sh",
    )
    for index, name in enumerate(guards):
        outcome = (
            "exit 0\n"
            if index == 0
            else (
                'printf \'{"hookSpecificOutput":{"permissionDecision":"deny"}}\\n\'\n'
                if index == 1
                else "exit 0\n"
            )
        )
        (scripts / name).write_text(
            '#!/usr/bin/env bash\ncat >/dev/null\nprintf \'%s\\n\' "$0" >> "$CALLS"\n'
            'if [[ "${MODE:-deny}" == malformed && "$(basename "$0")" == protect-files.sh ]]; then\n'
            "  printf 'not-json'\nelse\n"
            f"  {outcome}fi\n",
            encoding="utf-8",
        )
    calls = tmp_path / "calls"
    result = subprocess.run(
        ["bash", str(scripts / "pretool-bash-guard.sh"), "openai-codex"],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "true"}}),
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "CALLS": str(calls)},
    )
    assert result.returncode == 0
    assert [Path(line).name for line in calls.read_text().splitlines()] == list(
        guards[:2]
    )
    malformed = subprocess.run(
        ["bash", str(scripts / "pretool-bash-guard.sh"), "openai-codex"],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": "true"}}),
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "CALLS": str(calls), "MODE": "malformed"},
    )
    assert malformed.returncode == 2


if __name__ == "__main__":
    test_git_targets_nested_claude_detects_nested_claude_paths()
    test_git_targets_nested_claude_does_not_exempt_mixed_compound_commands()
    test_protect_files_python_pass_ignores_slashy_free_text()
    test_protect_files_allows_read_only_or_non_targeted_protected_paths(
        "cat .codex/config.toml"
    )
    test_protect_files_blocks_mutation_targets("printf x > .env")
