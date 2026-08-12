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


def _write_cancelled_plan(
    root: Path,
    *,
    missing_field: str = "",
    cancelled_at: str = "2026-08-11T07:00:00Z",
    reason: str = "The phase is no longer authorized",
    evidence: str = "evidence.md",
) -> Path:
    fields = {
        "cancelled_at": cancelled_at,
        "cancelled_reason": reason,
        "cancelled_evidence": evidence,
    }
    fields.pop(missing_field, None)
    plan = root / "phase-cancelled.md"
    plan.write_text(
        "---\n"
        "name: phase-cancelled\n"
        "type: small-plan\n"
        "parent_plan: example\n"
        "phase_index: 2\n"
        "status: cancelled\n"
        + "".join(f"{key}: {value}\n" for key, value in fields.items())
        + "---\n",
        encoding="utf-8",
    )
    return plan


def _cancellation_failures(
    root: Path, plan: Path, *, probe_override: str = ""
) -> list[str]:
    expression = (
        f"repo_root={shlex.quote(str(root))}; {probe_override} failures=(); "
        f"assert_cancellation_evidence {shlex.quote(str(plan))} phase-cancelled; "
        'if [[ "${#failures[@]}" -gt 0 ]]; then printf \'%s\\n\' "${failures[@]}"; fi'
    )
    result = _bash_source(SCRIPT_SRC / "_lib-frontmatter.sh", expression)
    assert result.returncode == 0, result.stderr
    return result.stdout.splitlines()


@pytest.mark.parametrize(
    "statuses",
    [
        ("cancelled", "complete"),
        ("complete", "cancelled"),
        ("complete", "complete"),
    ],
)
def test_unique_status_reader_rejects_duplicate_keys(
    tmp_path: Path, statuses: tuple[str, str]
) -> None:
    plan = tmp_path / "plan.md"
    plan.write_text(
        f"---\nstatus: {statuses[0]}\nstatus: {statuses[1]}\n---\n",
        encoding="utf-8",
    )

    result = _bash_source(
        SCRIPT_SRC / "_lib-frontmatter.sh",
        f"fm_read_unique_status {shlex.quote(str(plan))}",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "__DUPLICATE_FRONTMATTER_STATUS__"


def test_unique_status_reader_preserves_single_status(tmp_path: Path) -> None:
    plan = tmp_path / "plan.md"
    plan.write_text("---\nstatus: complete\n---\n", encoding="utf-8")

    result = _bash_source(
        SCRIPT_SRC / "_lib-frontmatter.sh",
        f"fm_read_unique_status {shlex.quote(str(plan))}",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "complete"


def test_cancellation_evidence_accepts_complete_artifact(tmp_path: Path) -> None:
    plan = _write_cancelled_plan(tmp_path)
    (tmp_path / "evidence.md").write_text(
        "# Decision\n\n**Status:** CANCELLED\n", encoding="utf-8"
    )

    assert _cancellation_failures(tmp_path, plan) == []


@pytest.mark.parametrize(
    "missing_field", ("cancelled_at", "cancelled_reason", "cancelled_evidence")
)
def test_cancellation_evidence_names_each_missing_field(
    tmp_path: Path, missing_field: str
) -> None:
    plan = _write_cancelled_plan(tmp_path, missing_field=missing_field)
    if missing_field != "cancelled_evidence":
        (tmp_path / "evidence.md").write_text(
            "**Status:** CANCELLED\n", encoding="utf-8"
        )

    assert _cancellation_failures(tmp_path, plan) == [
        f"phase-cancelled cancelled plan must set {missing_field}"
    ]


def test_cancellation_evidence_names_missing_file(tmp_path: Path) -> None:
    plan = _write_cancelled_plan(tmp_path, evidence="unique-missing-evidence.md")

    failures = _cancellation_failures(tmp_path, plan)

    assert failures == ["phase-cancelled cancelled evidence file is missing"]


def test_cancellation_evidence_rejects_markerless_file(tmp_path: Path) -> None:
    plan = _write_cancelled_plan(tmp_path)
    (tmp_path / "evidence.md").write_text(
        "# Decision\n\n**Status:** IN-PROGRESS\n", encoding="utf-8"
    )

    assert _cancellation_failures(tmp_path, plan) == [
        "phase-cancelled cancelled evidence must contain exact same-line prefix: "
        "**Status:** CANCELLED"
    ]


@pytest.mark.parametrize(
    "cancelled_at", ("2026-08-11T07:00:00", "2026-02-30T07:00:00Z")
)
def test_cancellation_evidence_rejects_invalid_timestamp(
    tmp_path: Path, cancelled_at: str
) -> None:
    plan = _write_cancelled_plan(tmp_path, cancelled_at=cancelled_at)
    (tmp_path / "evidence.md").write_text("**Status:** CANCELLED\n", encoding="utf-8")

    assert _cancellation_failures(tmp_path, plan) == [
        "phase-cancelled cancelled_at must be a real UTC timestamp in "
        "YYYY-MM-DDTHH:MM:SSZ format"
    ]


@pytest.mark.parametrize(
    "reason",
    (
        '"   "',
        "|- # folded",
        "[not, prose]",
        "{decision: cancelled}",
        "- list item",
        "First line\n  continued line",
    ),
)
def test_cancellation_evidence_rejects_yaml_like_reason(
    tmp_path: Path, reason: str
) -> None:
    plan = _write_cancelled_plan(tmp_path, reason=reason)
    (tmp_path / "evidence.md").write_text("**Status:** CANCELLED\n", encoding="utf-8")

    assert _cancellation_failures(tmp_path, plan) == [
        "phase-cancelled cancelled_reason must be meaningful plain single-line "
        "scalar prose"
    ]


@pytest.mark.parametrize("reason", ("| useful reason", ">+9 prose"))
def test_cancellation_evidence_accepts_block_header_lookalike_prose(
    tmp_path: Path, reason: str
) -> None:
    plan = _write_cancelled_plan(tmp_path, reason=reason)
    (tmp_path / "evidence.md").write_text("**Status:**\tCANCELLED\n", encoding="utf-8")

    assert _cancellation_failures(tmp_path, plan) == []


@pytest.mark.parametrize(
    ("evidence", "expected"),
    (
        ("/tmp/outside.md", "must be repository-relative"),
        ("nested/../evidence.md", "must not contain .. traversal"),
    ),
)
def test_cancellation_evidence_rejects_absolute_and_traversal_paths(
    tmp_path: Path, evidence: str, expected: str
) -> None:
    plan = _write_cancelled_plan(tmp_path, evidence=evidence)

    assert any(
        expected in failure for failure in _cancellation_failures(tmp_path, plan)
    )


def test_cancellation_evidence_rejects_outside_symlink(tmp_path: Path) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.md"
    outside.write_text("**Status:** CANCELLED\n", encoding="utf-8")
    (tmp_path / "evidence.md").symlink_to(outside)
    plan = _write_cancelled_plan(tmp_path)

    assert _cancellation_failures(tmp_path, plan) == [
        "phase-cancelled cancelled evidence must stay inside the repository"
    ]


def test_cancellation_evidence_rejects_symlink_loop(tmp_path: Path) -> None:
    (tmp_path / "evidence.md").symlink_to("evidence.md")
    plan = _write_cancelled_plan(tmp_path)

    assert _cancellation_failures(tmp_path, plan) == [
        "phase-cancelled cancelled evidence path could not be resolved safely"
    ]


def test_cancellation_evidence_rejects_directory(tmp_path: Path) -> None:
    (tmp_path / "evidence").mkdir()
    plan = _write_cancelled_plan(tmp_path, evidence="evidence")

    assert _cancellation_failures(tmp_path, plan) == [
        "phase-cancelled cancelled evidence must be a regular file"
    ]


def test_cancellation_evidence_rejects_unreadable_file(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence.md"
    evidence.write_text("**Status:** CANCELLED\n", encoding="utf-8")
    evidence.chmod(0)
    plan = _write_cancelled_plan(tmp_path)

    assert _cancellation_failures(tmp_path, plan) == [
        "phase-cancelled cancelled evidence must be readable"
    ]


def test_cancellation_evidence_rejects_invalid_utf8(tmp_path: Path) -> None:
    (tmp_path / "evidence.md").write_bytes(b"\xff\xfe")
    plan = _write_cancelled_plan(tmp_path)

    assert _cancellation_failures(tmp_path, plan) == [
        "phase-cancelled cancelled evidence must be valid UTF-8 text"
    ]


@pytest.mark.parametrize(
    "marker", ("**Status:**\nCANCELLED\n", "**Status:**\vCANCELLED\n")
)
def test_cancellation_evidence_rejects_split_or_vertical_marker(
    tmp_path: Path, marker: str
) -> None:
    (tmp_path / "evidence.md").write_text(marker, encoding="utf-8")
    plan = _write_cancelled_plan(tmp_path)

    assert _cancellation_failures(tmp_path, plan) == [
        "phase-cancelled cancelled evidence must contain exact same-line prefix: "
        "**Status:** CANCELLED"
    ]


@pytest.mark.parametrize(
    ("probe_override", "expected"),
    (
        (
            "cancellation_validation_probe() { printf PROBE_EXCEPTION; };",
            "probe raised an exception",
        ),
        (
            "cancellation_validation_probe() { printf UNEXPECTED; };",
            "probe returned malformed output",
        ),
    ),
)
def test_cancellation_evidence_probe_failures_block(
    tmp_path: Path, probe_override: str, expected: str
) -> None:
    plan = _write_cancelled_plan(tmp_path)

    assert any(
        expected in failure
        for failure in _cancellation_failures(
            tmp_path, plan, probe_override=probe_override
        )
    )


def test_cancellation_evidence_missing_python_blocks(tmp_path: Path) -> None:
    plan = _write_cancelled_plan(tmp_path)
    empty_path = tmp_path / "empty-path"
    empty_path.mkdir()

    assert _cancellation_failures(
        tmp_path,
        plan,
        probe_override=f"PATH={shlex.quote(str(empty_path))};",
    ) == ["phase-cancelled cancellation validation requires python3"]


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
        "stat uv.lock",
        "git diff uv.lock",
        "git show HEAD:uv.lock",
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
        "git rm .env",
        "git restore .env",
        "git checkout -- .env",
        'TARGET=.env rm "$TARGET"',
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


@pytest.mark.parametrize(
    "command",
    (
        "FOO=bar\nrg something .",
        "FOO=bar\nBAR=baz\nrg something .",
        'ROOT="$(pwd)"\nrg something "$ROOT"',
        "some-valid-but-unsupported-shell-syntax",
        "rg something .;",
        "chmod 600",
    ),
)
def test_protect_files_allows_valid_syntax_the_classifier_cannot_fully_model(
    command: str,
) -> None:
    """Assignment-only segments, trailing separators, and other syntax our
    lightweight parser cannot fully model must not become a blanket denial
    when no protected resource is involved."""
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout == "", f"unexpected stdout: {process.stdout!r}"


def test_protect_files_resolves_tracked_variable_before_blocking_mutation() -> None:
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": 'TARGET=.env\nrm "$TARGET"'}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


def test_protect_files_resolves_tracked_variable_before_allowing_normal_target() -> (
    None
):
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": 'TARGET=normal.txt\nrm "$TARGET"'},
        }
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout == "", f"unexpected stdout: {process.stdout!r}"


def test_protect_files_denies_ambiguous_protected_reference_without_infra_failure() -> (
    None
):
    """An unsupported command touching a protected literal (via a tracked
    variable) must become a normal, reasoned safety denial - not the
    'protect-files.sh exited with status 2' infrastructure-failure path."""
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": 'TARGET=".env"\nsome-unsupported-command "$TARGET"'
            },
        }
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert "could not determine whether the command may" in process.stdout
    assert "exited with status" not in process.stdout


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


def test_protect_files_python_3_9_compatibility() -> None:
    """Regression test for Python 3.9 compatibility.

    Verifies that protect-files.py:
    - Imports successfully without type-annotation syntax errors
    - Classifies harmless commands normally
    - Denies protected-file mutations
    - Fails closed on malformed input
    """
    # Test 1: protect-files.py imports successfully (compile check)
    result = subprocess.run(
        [
            "python3",
            "-m",
            "py_compile",
            str(SCRIPT_SRC / "protect-files.py"),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, f"Compilation failed: {result.stderr}"

    # Test 2: Harmless Bash command should pass classifier
    harmless = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": "ls -la /tmp"}}
    )
    assert harmless.returncode == 0, harmless.stderr
    assert harmless.stdout.strip() == "", "Harmless command should produce no output"

    # Test 3: Protected file mutation should be denied
    protected = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": "touch .env"}}
    )
    assert protected.returncode == 0, protected.stderr
    assert '"permissionDecision":"deny"' in protected.stdout

    # Test 4: Malformed payload should fail closed
    malformed = subprocess.run(
        ["bash", str(SCRIPT_SRC / "protect-files.sh"), "openai-codex"],
        cwd=REPO_ROOT,
        input="{bad json",
        text=True,
        capture_output=True,
        check=False,
    )
    assert malformed.returncode == 2, "Malformed payload should fail closed"
    assert '"permissionDecision":"deny"' in malformed.stdout


if __name__ == "__main__":
    test_git_targets_nested_claude_detects_nested_claude_paths()
    test_git_targets_nested_claude_does_not_exempt_mixed_compound_commands()
    test_protect_files_python_pass_ignores_slashy_free_text()
    test_protect_files_allows_read_only_or_non_targeted_protected_paths(
        "cat .codex/config.toml"
    )
    test_protect_files_blocks_mutation_targets("printf x > .env")
