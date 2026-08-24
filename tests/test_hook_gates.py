"""Regression coverage for shared hook gate helpers."""

from __future__ import annotations

import json
import os
import runpy
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_SRC = REPO_ROOT / "shared" / "hooks" / "scripts"
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from generate_targets import ANTIGRAVITY_TOOL_MAP  # noqa: E402


def _run_antigravity_pretool(payload: dict) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["python3", str(SCRIPT_SRC / "antigravity-pretool.py")],
        cwd=REPO_ROOT,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "REPO_ROOT": str(REPO_ROOT)},
    )


def _run_native_protect_files(
    payload: dict, repo_root: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "python3",
            str(SCRIPT_SRC / "protect-files.py"),
            "google-antigravity",
            str(repo_root),
        ],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )


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


def _write_paused_plan(
    root: Path,
    *,
    missing_field: str = "",
    paused_at: str = "2026-08-11T07:00:00Z",
    reason: str = "The user requested an overnight checkpoint",
    log: str = "pause.md",
) -> Path:
    fields = {
        "paused_at": paused_at,
        "paused_reason": reason,
        "pause_session_log": log,
    }
    fields.pop(missing_field, None)
    plan = root / "phase-paused.md"
    plan.write_text(
        "---\n"
        "name: phase-paused\n"
        "type: small-plan\n"
        "parent_plan: example\n"
        "phase_index: 2\n"
        "status: paused\n"
        + "".join(f"{key}: {value}\n" for key, value in fields.items())
        + "---\n",
        encoding="utf-8",
    )
    return plan


def _pause_failures(root: Path, plan: Path, *, probe_override: str = "") -> list[str]:
    expression = (
        f"repo_root={shlex.quote(str(root))}; {probe_override} failures=(); "
        f"assert_pause_evidence {shlex.quote(str(plan))} phase-paused; "
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


def test_pause_evidence_accepts_paused_session_log(tmp_path: Path) -> None:
    plan = _write_paused_plan(tmp_path)
    (tmp_path / "pause.md").write_text("**Status:** PAUSED\n", encoding="utf-8")

    assert _pause_failures(tmp_path, plan) == []


@pytest.mark.parametrize(
    "missing_field", ("paused_at", "paused_reason", "pause_session_log")
)
def test_pause_evidence_names_each_missing_field(
    tmp_path: Path, missing_field: str
) -> None:
    plan = _write_paused_plan(tmp_path, missing_field=missing_field)
    if missing_field != "pause_session_log":
        (tmp_path / "pause.md").write_text("**Status:** PAUSED\n", encoding="utf-8")

    assert _pause_failures(tmp_path, plan) == [
        f"phase-paused paused plan must set {missing_field}"
    ]


def test_pause_evidence_rejects_markerless_session_log(tmp_path: Path) -> None:
    plan = _write_paused_plan(tmp_path)
    (tmp_path / "pause.md").write_text("**Status:** IN-PROGRESS\n", encoding="utf-8")

    assert _pause_failures(tmp_path, plan) == [
        "phase-paused pause session log must contain exact same-line prefix: "
        "**Status:** PAUSED"
    ]


@pytest.mark.parametrize("reason", ('"   "', "|- # folded", "[not, prose]"))
def test_pause_evidence_rejects_yaml_like_reason(tmp_path: Path, reason: str) -> None:
    plan = _write_paused_plan(tmp_path, reason=reason)
    (tmp_path / "pause.md").write_text("**Status:** PAUSED\n", encoding="utf-8")

    assert any(
        "single-line scalar prose" in failure
        for failure in _pause_failures(tmp_path, plan)
    )


@pytest.mark.parametrize(
    ("log", "expected"),
    (
        ("/tmp/outside.md", "repository-relative"),
        ("nested/../pause.md", "must not contain .. traversal"),
    ),
)
def test_pause_evidence_rejects_unsafe_paths(
    tmp_path: Path, log: str, expected: str
) -> None:
    plan = _write_paused_plan(tmp_path, log=log)

    assert any(expected in failure for failure in _pause_failures(tmp_path, plan))


def test_pause_evidence_rejects_missing_nonregular_and_invalid_utf8_logs(
    tmp_path: Path,
) -> None:
    missing = _write_paused_plan(tmp_path, log="missing.md")
    assert any(
        "log file is missing" in failure
        for failure in _pause_failures(tmp_path, missing)
    )

    (tmp_path / "directory").mkdir()
    directory = _write_paused_plan(tmp_path, log="directory")
    assert any(
        "regular file" in failure for failure in _pause_failures(tmp_path, directory)
    )

    (tmp_path / "invalid.md").write_bytes(b"\xff\xfe")
    invalid = _write_paused_plan(tmp_path, log="invalid.md")
    assert any(
        "valid UTF-8" in failure for failure in _pause_failures(tmp_path, invalid)
    )


def test_pause_evidence_rejects_outside_symlink_and_probe_failures(
    tmp_path: Path,
) -> None:
    outside = tmp_path.parent / f"{tmp_path.name}-outside.md"
    outside.write_text("**Status:** PAUSED\n", encoding="utf-8")
    (tmp_path / "pause.md").symlink_to(outside)
    plan = _write_paused_plan(tmp_path)
    assert any("stay inside" in failure for failure in _pause_failures(tmp_path, plan))
    assert any(
        "probe raised an exception" in failure
        for failure in _pause_failures(
            tmp_path,
            plan,
            probe_override="pause_validation_probe() { printf PROBE_EXCEPTION; };",
        )
    )


def test_pause_evidence_rejects_unreadable_log_and_missing_python(
    tmp_path: Path,
) -> None:
    log = tmp_path / "pause.md"
    log.write_text("**Status:** PAUSED\n", encoding="utf-8")
    log.chmod(0)
    plan = _write_paused_plan(tmp_path)
    assert any(
        "must be readable" in failure for failure in _pause_failures(tmp_path, plan)
    )

    empty_path = tmp_path / "empty-path"
    empty_path.mkdir()
    assert _pause_failures(
        tmp_path,
        plan,
        probe_override=f"PATH={shlex.quote(str(empty_path))};",
    ) == ["phase-paused pause validation requires python3"]


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
        "git -C . diff uv.lock",
        "git -C . status",
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
        "git diff --output=.env",
        "git diff --output .env",
        "git show --output=.env HEAD",
        "git log --output=.env -1",
        "git -C . rm .env",
        "git --work-tree=. checkout -- .env",
    ),
)
def test_protect_files_blocks_mutation_targets(command: str) -> None:
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


@pytest.mark.parametrize(
    "command",
    (
        "git mv terraform/secrets.tf terraform/aws/secrets.tf",
        'git commit -m "fix: Needs AWS credentials for deploy"',
        "grep -n closeout .claude/hooks/scripts/enforce-commit-gate.sh",
        "python3 - <<'PY'\ndef secret(self, ref: str):\n    return ref\nPY",
        'python3 -c \'open("db_secret_backup.txt", "w")\'',
    ),
)
def test_protect_files_allows_non_path_secret_words(command: str) -> None:
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout == "", f"unexpected stdout: {process.stdout!r}"


def test_protect_files_expands_mutating_glob_before_classification(
    tmp_path: Path,
) -> None:
    source = tmp_path / "terraform"
    destination = tmp_path / "aws"
    source.mkdir()
    destination.mkdir()
    (source / "normal.tf").write_text("", encoding="utf-8")
    (source / "credentials-prod.json").write_text("", encoding="utf-8")

    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": f"mv {source}/* {destination}/"},
        }
    )

    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert "credentials-prod.json" in process.stdout


def test_protect_files_allows_mutating_glob_with_only_normal_sources(
    tmp_path: Path,
) -> None:
    source = tmp_path / "terraform"
    destination = tmp_path / "aws"
    source.mkdir()
    destination.mkdir()
    (source / "main.tf").write_text("", encoding="utf-8")
    (source / "secrets.tf").write_text("", encoding="utf-8")

    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": f"mv {source}/* {destination}/"},
        }
    )

    assert process.returncode == 0, process.stderr
    assert process.stdout == "", f"unexpected stdout: {process.stdout!r}"


def test_protect_files_tracks_cd_before_expanding_mutating_glob(tmp_path: Path) -> None:
    source = tmp_path / "terraform"
    destination = source / "aws"
    source.mkdir()
    destination.mkdir()
    (source / "credentials-prod.json").write_text("", encoding="utf-8")

    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": f"cd {source} && mv * aws/"},
        }
    )

    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert "credentials-prod.json" in process.stdout


def test_protect_files_does_not_expand_quoted_glob(tmp_path: Path) -> None:
    source = tmp_path / "terraform"
    destination = tmp_path / "aws"
    source.mkdir()
    destination.mkdir()
    (source / "credentials-prod.json").write_text("", encoding="utf-8")

    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": f"mv '{source}/*' {destination}/"},
        }
    )

    assert process.returncode == 0, process.stderr
    assert process.stdout == "", f"unexpected stdout: {process.stdout!r}"


@pytest.mark.parametrize(
    "command",
    (
        "cd missing || mv * /tmp/out",
        "cd /tmp | mv * /tmp/out",
    ),
)
def test_protect_files_checks_original_cwd_when_cd_is_not_provable(
    tmp_path: Path, command: str
) -> None:
    (tmp_path / "credentials-prod.json").write_text("", encoding="utf-8")
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": f"cd {tmp_path} && {command}"},
        }
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


def test_protect_files_blocks_wildcard_move_destination() -> None:
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": "mv README.md .claude/h?oks/scripts/protect-files.py"
            },
        }
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


def test_protect_files_keeps_protected_paths_inside_quoted_interpreter_text() -> None:
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "bash -c 'printf x > .env; echo *'"},
        }
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


def test_protect_files_expands_quoted_assignment_at_unquoted_use(
    tmp_path: Path,
) -> None:
    (tmp_path / "credentials-prod.json").write_text("", encoding="utf-8")
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": f"cd {tmp_path} && PATTERN='*'; mv $PATTERN /tmp/out"
            },
        }
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


def test_protect_files_does_not_expand_variable_at_quoted_use(tmp_path: Path) -> None:
    (tmp_path / "credentials-prod.json").write_text("", encoding="utf-8")
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": f"cd {tmp_path} && PATTERN='*'; mv \"$PATTERN\" /tmp/out"
            },
        }
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout == "", f"unexpected stdout: {process.stdout!r}"


@pytest.mark.parametrize(
    "command",
    ('X=.env; touch "${X}.local"', "X=.env; touch ${X}.local"),
)
def test_protect_files_substitutes_variable_with_suffix(command: str) -> None:
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


def test_protect_files_does_not_expand_quoted_braces(tmp_path: Path) -> None:
    (tmp_path / "credentials-prod.json").write_text("", encoding="utf-8")
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": f"cd {tmp_path} && mv '{{credentials-prod.json,main.tf}}' /tmp/out"
            },
        }
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout == "", f"unexpected stdout: {process.stdout!r}"


def test_protect_files_expands_simple_brace_operand() -> None:
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "mv {.env,README.md} /tmp/out"},
        }
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


@pytest.mark.parametrize(
    "command",
    ("mv .e\\\nnv /tmp/out", "printf x > .e\\\nnv"),
)
def test_protect_files_applies_shell_line_continuation(command: str) -> None:
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


def test_protect_files_blocks_git_mv_of_protected_source() -> None:
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "git mv .env examples/environment"},
        }
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


def test_protect_files_applies_git_c_before_resolving_mv_source() -> None:
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": "git -C .claude mv hooks/scripts/guard.sh archive/guard.sh"
            },
        }
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert ".claude/hooks/scripts/guard.sh" in process.stdout


@pytest.mark.parametrize(
    "command",
    (
        "cd .claude && git mv hooks/scripts/protect-files.py archive/protect-files.py",
        "git --git-dir=.claude/.git --work-tree=.claude mv hooks/scripts/protect-files.py archive/protect-files.py",
    ),
)
def test_protect_files_blocks_git_mv_from_effective_worktree(command: str) -> None:
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


def test_protect_files_blocks_git_archive_output() -> None:
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "git archive --output=.env HEAD"},
        }
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


def test_protect_files_resolves_git_output_from_git_c() -> None:
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "git -C .claude diff --output=hooks/new.patch"},
        }
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert ".claude/hooks/new.patch" in process.stdout


def test_protect_files_blocks_mutation_through_symlinked_protected_source(
    tmp_path: Path,
) -> None:
    protected_source = tmp_path / "credentials-prod.json"
    protected_source.write_text("", encoding="utf-8")
    alias = tmp_path / "ordinary.json"
    alias.symlink_to(protected_source)

    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": f"cp {alias} {tmp_path / 'copy.json'}"},
        }
    )

    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert "credentials-prod.json" in process.stdout


def test_protect_files_blocks_write_through_symlinked_directory(tmp_path: Path) -> None:
    protected_dir = tmp_path / ".claude" / "hooks"
    protected_dir.mkdir(parents=True)
    alias = tmp_path / "ordinary"
    alias.symlink_to(protected_dir, target_is_directory=True)

    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": f"printf x > {alias / 'new.sh'}"},
        }
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert ".claude/hooks/new.sh" in process.stdout


def test_protect_files_blocks_exact_credentials_path_in_interpreter() -> None:
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": 'python3 -c \'open("credentials", "w")\''},
        }
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


def test_protect_files_blocks_pathlib_write_to_exact_credentials() -> None:
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": 'python3 -c \'Path("credentials").write_text("x")\''
            },
        }
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


def test_protect_files_blocks_pathlib_open_write_to_exact_credentials() -> None:
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": 'python3 -c \'Path("credentials").open("w").write("x")\''
            },
        }
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


def test_protect_files_blocks_pathlib_open_update_to_exact_credentials() -> None:
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": 'python3 -c \'Path("credentials").open("r+").write("x")\''
            },
        }
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


@pytest.mark.parametrize(
    "command",
    (
        'python3 -c \'open("credentials", mode="w")\'',
        'python3 -c \'Path("credentials").open(mode="w").write("x")\'',
    ),
)
def test_protect_files_blocks_keyword_open_write_mode(command: str) -> None:
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


@pytest.mark.parametrize(
    "command",
    (
        'python3 -c \'open(file="credentials", mode="w")\'',
        'python3 -c \'Path("credentials").open(encoding="utf-8", mode="w").write("x")\'',
    ),
)
def test_protect_files_blocks_reordered_keyword_open_write(command: str) -> None:
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


def test_protect_files_allows_pathlib_open_read_of_exact_credentials() -> None:
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {
                "command": 'python3 -c \'Path("credentials").open("r").read()\''
            },
        }
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout == "", f"unexpected stdout: {process.stdout!r}"


def test_protect_files_allows_builtin_open_read_of_exact_credentials() -> None:
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": 'python3 -c \'open("credentials", "r")\''},
        }
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout == "", f"unexpected stdout: {process.stdout!r}"


def test_protect_files_allows_credentials_as_interpreter_prose() -> None:
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": "python3 -c 'print(\"credentials\")'"},
        }
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout == "", f"unexpected stdout: {process.stdout!r}"


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


def test_antigravity_pretool_allows_safe_command_with_json_only_stdout() -> None:
    """The bridge preserves a clean protocol response for allowed commands."""
    process = _run_antigravity_pretool(
        {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git status", "Cwd": str(REPO_ROOT)},
            },
        }
    )

    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout) == {"decision": "allow"}
    assert process.stderr == ""


@pytest.mark.parametrize(
    "tool_name",
    sorted(
        {
            tool
            for capability in ("read", "search", "delegate", "web")
            for tool in ANTIGRAVITY_TOOL_MAP[capability]
        }
    ),
)
def test_antigravity_pretool_allows_known_non_mutating_tools(tool_name: str) -> None:
    """The wildcard bridge admits every generated non-mutating tool."""
    process = _run_antigravity_pretool({"toolCall": {"name": tool_name, "args": {}}})

    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout) == {"decision": "allow"}


def test_antigravity_pretool_non_mutating_allowlist_matches_generator() -> None:
    """The bridge adds only its documented native coordination exceptions."""
    bridge = runpy.run_path(str(SCRIPT_SRC / "antigravity-pretool.py"))
    expected = {
        tool
        for capability in ("read", "search", "delegate", "web")
        for tool in ANTIGRAVITY_TOOL_MAP[capability]
    }

    assert not {"manage_task", "schedule"} & expected
    assert bridge["NON_MUTATING_TOOLS"] == expected | {"manage_task", "schedule"}


@pytest.mark.parametrize("tool_name", ("manage_task", "schedule"))
def test_antigravity_pretool_allows_native_coordination_only_in_the_bridge(
    tool_name: str,
) -> None:
    """Native coordination is safe but never becomes a custom-agent tool."""
    process = _run_antigravity_pretool({"toolCall": {"name": tool_name, "args": {}}})

    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout) == {"decision": "allow"}
    assert tool_name not in {
        tool for tools in ANTIGRAVITY_TOOL_MAP.values() for tool in tools
    }


def test_antigravity_pretool_is_python_3_9_compatible() -> None:
    """The standalone bridge stays parseable by the hook runtime baseline."""
    process = subprocess.run(
        ["python3", "-m", "py_compile", str(SCRIPT_SRC / "antigravity-pretool.py")],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert process.returncode == 0, process.stderr


@pytest.mark.parametrize(
    "tool_name",
    ("write_to_file", "replace_file_content", "multi_replace_file_content"),
)
def test_antigravity_pretool_denies_protected_file_mutations(tool_name: str) -> None:
    """Each documented native mutation tool reaches canonical file policy."""
    process = _run_antigravity_pretool(
        {
            "toolCall": {"name": tool_name, "args": {"TargetFile": ".env"}},
        }
    )

    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)["decision"] == "deny"


def test_antigravity_pretool_allows_normal_file_mutation() -> None:
    """The bridge does not turn ordinary file writes into blanket denials."""
    process = _run_antigravity_pretool(
        {
            "toolCall": {
                "name": "write_to_file",
                "args": {"TargetFile": "notes/release.md"},
            },
        }
    )

    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout) == {"decision": "allow"}


def test_antigravity_pretool_denies_dangerous_git_command() -> None:
    """Command normalization retains the canonical dangerous-Git guard."""
    process = _run_antigravity_pretool(
        {
            "toolCall": {
                "name": "run_command",
                "args": {"CommandLine": "git reset --hard", "Cwd": str(REPO_ROOT)},
            },
        }
    )

    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)["decision"] == "deny"


def test_antigravity_pretool_uses_cwd_for_relative_protected_command() -> None:
    """The documented Cwd field scopes a relative command before classification."""
    process = _run_antigravity_pretool(
        {
            "toolCall": {
                "name": "run_command",
                "args": {
                    "CommandLine": "touch hooks/guard.sh",
                    "Cwd": str(REPO_ROOT / ".claude"),
                },
            }
        }
    )

    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout)["decision"] == "deny"


def test_antigravity_pretool_quotes_metacharacter_bearing_cwd() -> None:
    """Cwd stays one operand and cannot manufacture a second shell command."""
    process = _run_antigravity_pretool(
        {
            "toolCall": {
                "name": "run_command",
                "args": {
                    "CommandLine": "git status",
                    "Cwd": str(REPO_ROOT) + "; touch .env",
                },
            }
        }
    )

    assert process.returncode == 0, process.stderr
    assert json.loads(process.stdout) == {"decision": "allow"}


@pytest.mark.parametrize("kind", ("file", "directory"))
def test_protect_files_resolves_native_target_symlink_aliases(
    tmp_path: Path, kind: str
) -> None:
    """Native TargetFile checks include real paths for symlinked targets."""
    if kind == "file":
        protected_target = tmp_path / ".env"
        protected_target.write_text("", encoding="utf-8")
        alias = tmp_path / "alias"
        alias.symlink_to(protected_target)
        target = alias
    else:
        protected_directory = tmp_path / ".claude" / "hooks"
        protected_directory.mkdir(parents=True)
        alias = tmp_path / "alias"
        alias.symlink_to(protected_directory, target_is_directory=True)
        target = alias / "new-guard.sh"

    process = _run_native_protect_files(
        {"tool_name": "Write", "tool_input": {"path": str(target)}}, tmp_path
    )

    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


@pytest.mark.parametrize(
    "payload",
    (
        {},
        {"toolCall": {}},
        {
            "toolCall": {"name": "write_to_file", "args": {}},
        },
        {
            "toolCall": {"name": "unverified_write", "args": {}},
        },
    ),
)
def test_antigravity_pretool_fails_closed_for_invalid_payloads(payload: dict) -> None:
    """Malformed or unsupported requests never fall through to an allow."""
    process = _run_antigravity_pretool(payload)

    assert process.returncode == 0
    assert json.loads(process.stdout)["decision"] == "deny"
    assert "WARN antigravity-pretool:" in process.stderr


def test_antigravity_pretool_fails_closed_for_raw_malformed_json() -> None:
    """Raw malformed hook stdin receives a protocol deny, not a crash."""
    process = subprocess.run(
        ["python3", str(SCRIPT_SRC / "antigravity-pretool.py")],
        cwd=REPO_ROOT,
        input="{malformed",
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "REPO_ROOT": str(REPO_ROOT)},
    )

    assert process.returncode == 0
    assert json.loads(process.stdout)["decision"] == "deny"
    assert "WARN antigravity-pretool:" in process.stderr


if __name__ == "__main__":
    test_git_targets_nested_claude_detects_nested_claude_paths()
    test_git_targets_nested_claude_does_not_exempt_mixed_compound_commands()
    test_protect_files_python_pass_ignores_slashy_free_text()
    test_protect_files_allows_read_only_or_non_targeted_protected_paths(
        "cat .codex/config.toml"
    )
    test_protect_files_blocks_mutation_targets("printf x > .env")
