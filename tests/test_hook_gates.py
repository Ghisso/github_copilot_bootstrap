"""Regression coverage for shared hook gate helpers."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
from pathlib import Path

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
    assert _git_targets_nested_claude("git --git-dir .claude/.git commit -m hi", "commit") == 0
    assert _git_targets_nested_claude("git --work-tree .claude commit -m hi", "commit") == 0
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
    bypass_commit_reversed = 'git commit -m "sneaky outer commit" ; git -C .claude status'
    assert _git_targets_nested_claude(bypass_commit_reversed, "commit") == 1

    # Two genuinely nested invocations chained together should still exempt.
    both_nested = "git -C .claude add -A && git -C .claude commit -m hi"
    assert _git_targets_nested_claude(both_nested, "commit") == 0


def _run_protect_files(payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT_SRC / "protect-files.sh")],
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


def test_protect_files_still_catches_relative_secret_paths() -> None:
    """The coarse bash scan only recognizes explicit path prefixes/extensions,
    so a relative `cp app/secrets/db_secret.txt app/backup/copy.txt` produces
    zero bash-side candidates. An earlier fix short-circuited the Python
    precision pass whenever the bash pass found no candidates, which silently
    let this kind of secret-file copy through — the Python pass is the only
    layer that flags a relative path by basename (e.g. "secret" in the
    name), so it must still run even when the bash pass finds nothing."""
    payload = {
        "tool_name": "Bash",
        "tool_input": {
            "command": "cp app/secrets/db_secret.txt app/backup/db_secret_copy.txt"
        },
    }
    process = _run_protect_files(payload)
    assert process.returncode == 0, process.stderr
    assert "deny" in process.stdout, f"expected a deny decision, got: {process.stdout!r}"
    assert "db_secret" in process.stdout


if __name__ == "__main__":
    test_git_targets_nested_claude_detects_nested_claude_paths()
    test_git_targets_nested_claude_does_not_exempt_mixed_compound_commands()
    test_protect_files_python_pass_ignores_slashy_free_text()
    test_protect_files_still_catches_relative_secret_paths()
