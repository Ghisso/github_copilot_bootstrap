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


def _run_antigravity_pretool(
    payload: dict, repo_root: Path | None = None
) -> subprocess.CompletedProcess[str]:
    root = repo_root if repo_root is not None else REPO_ROOT
    return subprocess.run(
        ["python3", str(SCRIPT_SRC / "antigravity-pretool.py")],
        cwd=root,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "REPO_ROOT": str(root)},
    )


def _isolated_hook_scripts_dir(repo_root: Path) -> Path:
    """Return a `shared/hooks/scripts`-shaped path under `repo_root` whose
    scripts still run the real `SCRIPT_SRC` bytes via a symlink.

    `repo_root_from_script` (`_lib-frontmatter.sh`) derives REPO_ROOT from the
    invoking script's own physical location, three directories up from
    wherever `$0`/`BASH_SOURCE` says it lives. Bash's `cd`/`pwd` track that
    location logically (through symlinks) rather than resolving it, so
    invoking the scripts through this symlink keeps every `fail_closed`/`warn`
    write scoped to `repo_root` instead of the live checkout, without copying
    or editing the scripts themselves.
    """
    scripts_dir = repo_root / "shared" / "hooks" / "scripts"
    if not scripts_dir.exists():
        scripts_dir.parent.mkdir(parents=True, exist_ok=True)
        scripts_dir.symlink_to(SCRIPT_SRC, target_is_directory=True)
    (repo_root / ".claude" / "session_logs").mkdir(parents=True, exist_ok=True)
    return scripts_dir


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


def test_certified_receipt_relation_accepts_only_the_direct_completion_commit(
    tmp_path: Path,
) -> None:
    """Completed-phase publication cannot authorize a later WIP commit."""
    for args in (
        ("git", "init", "-q", "-b", "dev"),
        ("git", "config", "user.email", "agent@example.com"),
        ("git", "config", "user.name", "Agent"),
    ):
        subprocess.run(args, cwd=tmp_path, check=True)
    (tmp_path / "work.txt").write_text("base\n", encoding="utf-8")
    subprocess.run(("git", "add", "work.txt"), cwd=tmp_path, check=True)
    subprocess.run(("git", "commit", "-qm", "base"), cwd=tmp_path, check=True)
    receipt_head = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()

    (tmp_path / "work.txt").write_text("completed\n", encoding="utf-8")
    subprocess.run(("git", "commit", "-am", "complete"), cwd=tmp_path, check=True)
    completion = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()
    verifier = runpy.run_path(str(REPO_ROOT / "shared" / "scripts" / "verify.py"))
    is_direct_child = verifier["git_is_direct_child"]
    assert is_direct_child(tmp_path, receipt_head, completion)
    assert is_direct_child(tmp_path, receipt_head, "HEAD")
    (tmp_path / "work.txt").write_text("unreviewed\n", encoding="utf-8")
    subprocess.run(("git", "commit", "-am", "wip"), cwd=tmp_path, check=True)
    later_commit = subprocess.run(
        ("git", "rev-parse", "HEAD"),
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=True,
    ).stdout.strip()

    assert not is_direct_child(tmp_path, receipt_head, later_commit)


def test_certified_receipt_relation_rejects_a_merge_and_accepts_short_shas(
    tmp_path: Path,
) -> None:
    """A merge commit never certifies; an abbreviated SHA still resolves.

    The whole contract of ``git_is_direct_child`` is that exactly one
    non-merge child qualifies, so loosening the parent count would admit a
    merge that carries unreviewed work in from a second parent.
    """
    for args in (
        ("git", "init", "-q", "-b", "dev"),
        ("git", "config", "user.email", "agent@example.com"),
        ("git", "config", "user.name", "Agent"),
    ):
        subprocess.run(args, cwd=tmp_path, check=True)

    def run(*args: str) -> str:
        return subprocess.run(
            args,
            cwd=tmp_path,
            text=True,
            capture_output=True,
            check=True,
        ).stdout.strip()

    (tmp_path / "work.txt").write_text("base\n", encoding="utf-8")
    run("git", "add", "work.txt")
    run("git", "commit", "-qm", "base")
    receipt_head = run("git", "rev-parse", "HEAD")

    (tmp_path / "work.txt").write_text("completed\n", encoding="utf-8")
    run("git", "commit", "-qam", "complete")
    completion = run("git", "rev-parse", "HEAD")

    verifier = runpy.run_path(str(REPO_ROOT / "shared" / "scripts" / "verify.py"))
    is_direct_child = verifier["git_is_direct_child"]

    # An abbreviated receipt SHA and an abbreviated pushed SHA both resolve to
    # the same canonical commits, so neither form may deny a valid push.
    short_receipt = run("git", "rev-parse", "--short", receipt_head)
    short_completion = run("git", "rev-parse", "--short", completion)
    assert short_receipt != receipt_head
    assert is_direct_child(tmp_path, short_receipt, completion)
    assert is_direct_child(tmp_path, receipt_head, short_completion)
    assert is_direct_child(tmp_path, short_receipt, short_completion)

    # A merge whose first parent is the certified commit still has two
    # parents, so it brings in work the receipt never certified.
    run("git", "checkout", "-q", "-b", "side", receipt_head)
    (tmp_path / "side.txt").write_text("uncertified\n", encoding="utf-8")
    run("git", "add", "side.txt")
    run("git", "commit", "-qm", "side work")
    run("git", "checkout", "-q", "dev")
    run("git", "merge", "-q", "--no-ff", "-m", "merge side", "side")
    merge_commit = run("git", "rev-parse", "HEAD")
    assert (
        len(run("git", "rev-list", "--parents", "-n", "1", merge_commit).split()) == 3
    )
    assert not is_direct_child(tmp_path, completion, merge_commit)
    assert not is_direct_child(tmp_path, completion, "HEAD")

    # An unknown parent revision cannot resolve, so it cannot certify either.
    assert not is_direct_child(tmp_path, "does-not-exist", completion)


def _assert_plan_frontmatter_failures(tmp_path: Path) -> list[str]:
    """Invoke the shipped ``assert_plan_frontmatter`` gate against a fixture
    repo root, returning its accumulated failures (empty when valid)."""
    scripts_dir = tmp_path / ".claude" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        REPO_ROOT / "scripts" / "validate_plan_frontmatter.py",
        scripts_dir / "validate_plan_frontmatter.py",
    )
    expression = f"""
failures=()
assert_plan_frontmatter {shlex.quote(str(tmp_path))}
printf '%s\\n' "${{failures[@]}}"
"""
    result = _bash_source(SCRIPT_SRC / "_lib-frontmatter.sh", expression)
    assert result.returncode == 0, result.stderr
    return [line for line in result.stdout.splitlines() if line]


def test_assert_plan_frontmatter_blocks_missing_required_field(
    tmp_path: Path,
) -> None:
    """R-LIFECYCLE-04: consumers now receive a hard plan-frontmatter gate, not
    only the authoring repo's own tooling."""
    plans = tmp_path / ".claude" / "plans"
    plans.mkdir(parents=True)
    (plans / "example.md").write_text(
        "---\n"
        "type: big-plan\n"
        "status: planning\n"
        "originating_branch: dev\n"
        "implementation_branch: example_implementation\n"
        "phases:\n  - phase-one\n"
        "---\n\n# Example\n",
        encoding="utf-8",
    )
    failures = _assert_plan_frontmatter_failures(tmp_path)
    assert any("missing required field: name" in failure for failure in failures)


def test_assert_plan_frontmatter_blocks_small_plan_missing_phase_index(
    tmp_path: Path,
) -> None:
    plans = tmp_path / ".claude" / "plans"
    plans.mkdir(parents=True)
    (plans / "phase-one.md").write_text(
        "---\n"
        "name: phase-one\n"
        "type: small-plan\n"
        "parent_plan: example\n"
        "status: in-progress\n"
        "---\n\n# Phase\n",
        encoding="utf-8",
    )
    failures = _assert_plan_frontmatter_failures(tmp_path)
    assert any("missing required field: phase_index" in failure for failure in failures)


def test_assert_plan_frontmatter_blocks_invalid_body_phase_inventory(
    tmp_path: Path,
) -> None:
    plans = tmp_path / ".claude" / "plans"
    plans.mkdir(parents=True)
    (plans / "example.md").write_text(
        "---\n"
        "name: example\n"
        "type: big-plan\n"
        "status: planning\n"
        "originating_branch: dev\n"
        "implementation_branch: example_implementation\n"
        "phases:\n  - phase-one\n"
        "---\n\n## Phase\n\n- `phase-two`\n",
        encoding="utf-8",
    )
    failures = _assert_plan_frontmatter_failures(tmp_path)
    assert any(
        "body phase inventory must match frontmatter phases" in failure
        for failure in failures
    )


def test_assert_plan_frontmatter_accepts_valid_plans(tmp_path: Path) -> None:
    plans = tmp_path / ".claude" / "plans"
    plans.mkdir(parents=True)
    (plans / "example.md").write_text(
        "---\n"
        "name: example\n"
        "type: big-plan\n"
        "status: planning\n"
        "originating_branch: dev\n"
        "implementation_branch: example_implementation\n"
        "phases:\n  - phase-one\n"
        "---\n\n# Example\n",
        encoding="utf-8",
    )
    (plans / "phase-one.md").write_text(
        "---\n"
        "name: phase-one\n"
        "type: small-plan\n"
        "parent_plan: example\n"
        "phase_index: 1\n"
        "status: in-progress\n"
        "---\n\n# Phase\n",
        encoding="utf-8",
    )
    assert _assert_plan_frontmatter_failures(tmp_path) == []


def test_assert_plan_frontmatter_missing_validator_fails_closed(
    tmp_path: Path,
) -> None:
    """No shipped validator on disk is a hard failure, not a silent skip."""
    (tmp_path / ".claude" / "plans").mkdir(parents=True)
    expression = f"""
failures=()
assert_plan_frontmatter {shlex.quote(str(tmp_path))}
printf '%s\\n' "${{failures[@]}}"
"""
    result = _bash_source(SCRIPT_SRC / "_lib-frontmatter.sh", expression)
    assert result.returncode == 0, result.stderr
    assert "missing plan-frontmatter validator" in result.stdout


def test_confirmed_reachable_sites_use_the_guarded_array_expansion_idiom() -> None:
    """Phase B2 (2026-09-11_phase-B2-hook-empty-array-safety): each of the
    seven Confirmed Reachable Instances, plus the ``expected`` site in
    ``reporting-reminder.sh`` found while widening the regression scanner to
    the ``[*]``/indices shapes, must use the repository's
    ``${arr[@]+"${arr[@]}"}`` guard, not a bare ``${arr[@]}``/``${arr[*]}``/
    ``${!arr[@]}`` form. Bash 3.2 (the declared consumer orchestration
    baseline) aborts on every one of those bare forms with 'unbound
    variable' under `set -u` when the array is empty. This host's newer
    Bash cannot reproduce that abort, so the fix is pinned at the source
    level instead of behaviorally."""
    frontmatter_text = (SCRIPT_SRC / "_lib-frontmatter.sh").read_text(encoding="utf-8")
    git_protection_text = (SCRIPT_SRC / "git-protection.sh").read_text(encoding="utf-8")
    reporting_reminder_text = (SCRIPT_SRC / "reporting-reminder.sh").read_text(
        encoding="utf-8"
    )
    expectations = (
        (
            frontmatter_text,
            "_lib-frontmatter.sh",
            "all_phases",
            'for other_phase in ${all_phases[@]+"${all_phases[@]}"}; do',
            1,
        ),
        (
            frontmatter_text,
            "_lib-frontmatter.sh",
            "paths",
            'for path in ${paths[@]+"${paths[@]}"}; do',
            1,
        ),
        (
            frontmatter_text,
            "_lib-frontmatter.sh",
            "_TOKENS",
            'tokens=(${_TOKENS[@]+"${_TOKENS[@]}"})',
            3,
        ),
        (
            frontmatter_text,
            "_lib-frontmatter.sh",
            "tokens",
            '_git_invocation_targets_nested_claude ${tokens[@]+"${tokens[@]}"} || return 1',
            1,
        ),
        (
            git_protection_text,
            "git-protection.sh",
            "tokens",
            'if reason="$(_git_danger_from_tokens ${tokens[@]+"${tokens[@]}"})"; then',
            1,
        ),
        (
            reporting_reminder_text,
            "reporting-reminder.sh",
            "expected",
            'for index in ${expected[@]+"${!expected[@]}"}; do',
            1,
        ),
    )
    for text, filename, variable, snippet, expected_count in expectations:
        assert text.count(snippet) == expected_count, (
            f"{filename}: expected {expected_count} guarded expansion(s) of "
            f"{variable!r} via {snippet!r}; source drifted from the Phase B2 fix"
        )


def test_assert_commit_invariants_reports_missing_current_phase_without_aborting(
    tmp_path: Path,
) -> None:
    """An empty ``current_phase`` must surface as its own gate failure, and
    the cancellation sweep immediately below it must run zero iterations
    over the still-empty ``all_phases`` rather than partially executing. On
    Bash 3.2 an unguarded ``"${all_phases[@]}"`` there aborts with an
    unbound-variable error before this message is ever printed; this host's
    newer Bash cannot reproduce that abort, so this test pins the intended
    message and confirms the sibling sweep never runs (no cancellation-
    evidence failure for the sibling plan below, even though it is
    cancelled and missing its evidence fields)."""
    plans = tmp_path / ".claude" / "plans"
    plans.mkdir(parents=True)
    (plans / "example.md").write_text(
        "---\nname: example\nstatus: in-progress\ncurrent_phase:\n---\n\n# Example\n",
        encoding="utf-8",
    )
    # A sibling plan that looks cancelled-and-incomplete: if the sweep ever
    # ran despite the empty current_phase, assert_cancellation_evidence
    # would append failures for it.
    (plans / "sibling.md").write_text(
        "---\nname: sibling\nstatus: cancelled\n---\n\n# Sibling\n",
        encoding="utf-8",
    )
    expression = f"""
assert_plan_frontmatter() {{ :; }}
assert_completed_receipt() {{ :; }}
failures=()
assert_commit_invariants {shlex.quote(str(tmp_path))} example_implementation
printf '%s\\n' "${{failures[@]}}"
"""
    result = _bash_source(SCRIPT_SRC / "_lib-frontmatter.sh", expression)
    assert result.returncode == 0, result.stderr
    failures = result.stdout.splitlines()
    assert "big plan has no current_phase" in failures
    assert not any("evidence" in failure for failure in failures), failures


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


def _run_protect_files(
    payload: dict, repo_root: Path | None = None
) -> subprocess.CompletedProcess[str]:
    root = repo_root if repo_root is not None else REPO_ROOT
    scripts_dir = (
        _isolated_hook_scripts_dir(root) if repo_root is not None else SCRIPT_SRC
    )
    return subprocess.run(
        ["bash", str(scripts_dir / "protect-files.sh"), "openai-codex"],
        cwd=root,
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        env={
            **os.environ,
            "REPO_ROOT": str(root),
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


@pytest.mark.parametrize(
    "command",
    (
        # `diff`/`cat` never write through their own arguments (READ_ONLY);
        # reading a protected-looking path through a nested, read-only
        # process substitution must not become a mutation denial merely
        # because the classifier cannot yet model <( ).
        "diff <(cat .env) <(cat CLAUDE.md)",
        "diff <(cat credentials-prod.json) <(echo ok)",
    ),
)
def test_protect_files_allows_read_only_process_substitution(command: str) -> None:
    """Regression test for the reported false positive: a read-only process
    substitution must be allowed, not denied merely because its inner
    command happens to reference a protected-looking path for reading."""
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout == "", f"unexpected stdout: {process.stdout!r}"


def test_protect_files_allows_data_heredoc_with_unmatched_apostrophe() -> None:
    """A heredoc body is prose/data, not shell syntax: an unmatched
    apostrophe or shell metacharacters inside it must not corrupt outer
    tokenization."""
    command = "cat <<'EOF'\nFix: don't break ${arr[@]} or \"${arr[@]}\" handling\nEOF"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout == "", f"unexpected stdout: {process.stdout!r}"


def test_protect_files_allows_git_commit_file_dash_heredoc_reproduction() -> None:
    """Firsthand reproduction: `git commit -F - <<'EOF' ... EOF` was denied
    with "protect-files.sh exited with status 2" because the commit
    message's `${arr[@]}` and `"${arr[@]}"` broke outer shell tokenization,
    even though the body is pure data fed to git's own -F - stdin convention
    and can never become a filesystem write target."""
    command = (
        "git commit -F - <<'EOF'\n"
        'Fix: don\'t break ${arr[@]} or "${arr[@]}" handling\n'
        "EOF"
    )
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout == "", f"unexpected stdout: {process.stdout!r}"


def test_protect_files_allows_read_only_command_heredoc_with_harmless_data() -> None:
    """A READ_ONLY command's heredoc is stdin data, exactly like its own
    command-line arguments already are; harmless prose must not be denied."""
    command = "wc -l <<'EOF'\njust some ordinary text\nEOF"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout == "", f"unexpected stdout: {process.stdout!r}"


def test_protect_files_denies_read_only_command_heredoc_mentioning_protected_path() -> (
    None
):
    """CRITICAL security-review fix: a READ_ONLY consumer's heredoc body is
    never fully skipped - only its own command-line arguments are known
    never to write. sed's own script sub-language supports `w file` and `e`
    without `-i` (see the dedicated sed test below), so every READ_ONLY
    command's heredoc gets the same conservative literal-scan floor an
    unmodeled command's own arguments already get."""
    command = "wc -l <<'EOF'\nreferences .env in prose\nEOF"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert "could not determine whether the command may" in process.stdout


def test_protect_files_denies_sed_heredoc_write_command() -> None:
    """CRITICAL security-review fix: sed is READ_ONLY for its own arguments,
    but its own scripting language can write an arbitrary file via `w file`/
    `s///w file`, or execute a shell command via `e`, without ever using
    `-i`. The dedicated sed/perl `-i` branch does not fire here, so the
    heredoc-body literal-scan floor is what must catch this."""
    command = "sed -n -f - CLAUDE.md <<'EOF'\ns/.*/&/w .env\nEOF"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


def test_protect_files_denies_unquoted_heredoc_command_substitution() -> None:
    """CRITICAL security-review fix: an *unquoted* heredoc delimiter's body
    is expanded by the shell - including $( ) command substitution - before
    any consuming command ever runs, so `cat <<EOF` with `$(touch .env)` in
    the body must deny even though `cat` never interprets its own stdin."""
    command = "cat <<EOF\n$(touch .env)\nEOF"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert "Protected file blocked by policy: .env" in process.stdout


@pytest.mark.parametrize(
    "command",
    (
        "cat <<EOF\n'literal $(touch .env) more'\nEOF",
        'cat <<EOF\n"literal $(touch .env) more"\nEOF',
    ),
)
def test_protect_files_denies_quote_wrapped_command_substitution_in_unquoted_heredoc(
    command: str,
) -> None:
    """A heredoc body is not re-tokenized with normal shell quoting rules:
    only a backslash escaping $, a backtick, or itself is special, so a
    single or double quote around $( ) is plain literal text and does not
    suppress it (verified empirically in a real bash). Wrapping the exploit
    in quotes must not smuggle it past the scanner."""
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert "Protected file blocked by policy: .env" in process.stdout


def test_protect_files_allows_backslash_escaped_dollar_in_unquoted_heredoc() -> None:
    """A backslash immediately before `$` suppresses command-substitution
    expansion even in an unquoted heredoc, so this must not be recursively
    classified as executable code - it is still denied by the always-on
    literal-scan floor for the literal ".env" text, but only with the
    softer "could not determine" wording, not the confirmed one a genuinely
    executed mutator would produce."""
    command = "cat <<EOF\nescaped: \\$(touch .env)\nEOF"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert "could not determine whether the command may" in process.stdout
    assert "Protected file blocked by policy" not in process.stdout


def test_protect_files_resolves_tracked_variable_inside_unquoted_heredoc_command_substitution() -> (
    None
):
    """The $( ) inside an unquoted heredoc runs in a subshell of the
    *current* shell (like a process substitution), so it inherits already-
    tracked variables. The body text itself never contains the literal
    ".env" substring - only the recursive classification proves this."""
    command = "TARGET=.env\ncat <<EOF\n$(touch $TARGET)\nEOF"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert "Protected file blocked by policy: .env" in process.stdout


@pytest.mark.parametrize(
    "command",
    (
        "TARGET=.env bash <<'EOF'\ntouch $TARGET\nEOF",
        "env TARGET=.env bash <<'EOF'\ntouch $TARGET\nEOF",
    ),
)
def test_protect_files_resolves_prefix_assignment_inside_quoted_bare_shell_heredoc(
    command: str,
) -> None:
    """CRITICAL security-review fix: a *quoted* heredoc delimiter's body
    passes through to the child `bash` process literally; the child's own
    environment does contain this command's own prefix assignment (`VAR=v
    cmd` and `env VAR=value cmd` both export it to the child), so `touch
    $TARGET` must resolve and deny. Verified in real bash first (throwaway
    temp dir, harmless marker file): both forms write the marker."""
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert "Protected file blocked by policy: .env" in process.stdout


def test_protect_files_allows_prefix_assignment_inside_unquoted_bare_shell_heredoc() -> (
    None
):
    """Must-not-regress control: with an *unquoted* delimiter, the *parent*
    shell expands the body before the child ever runs, using the parent's
    own scope - and a prefix assignment is not part of that scope (it is
    exported only to the child about to exec). Real bash expands `$TARGET`
    to empty here and `touch` errors with no write (verified empirically).
    "Fixing" this to resolve would be a new false positive, not a fix."""
    command = "TARGET=.env bash <<EOF\ntouch $TARGET\nEOF"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout == "", f"unexpected stdout: {process.stdout!r}"


def test_protect_files_resolves_persistent_assignment_inside_unquoted_bare_shell_heredoc() -> (
    None
):
    """MAJOR test-gap fix: the fourth quoted/prefix combination. A bare
    assignment on its own, separate segment (`TARGET=.env` then `bash ...`
    later) *is* already in `outer_variables`, because it was recorded
    before this segment ever ran; with an *unquoted* delimiter the parent
    shell expands the body using exactly that scope before the child runs
    (verified empirically: `touch` succeeds and writes the marker here,
    unlike the quoted-delimiter sibling test above). This is the one case
    that actually distinguishes "outer_variables correctly threads
    cross-segment scope" from "outer_variables is empty and broken exactly
    like the old unconditional {}" - every sibling test in this batch
    expects "stays unresolved", so a regression back to always-empty would
    pass them all untouched."""
    command = "TARGET=.env\nbash <<EOF\ntouch $TARGET\nEOF"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert "Protected file blocked by policy: .env" in process.stdout


def test_protect_files_does_not_resolve_persistent_assignment_inside_quoted_bare_shell_heredoc() -> (
    None
):
    """Must-not-regress control: a bare assignment on its own, separate
    segment (`TARGET=.env` then `bash ...` later) is never exported to a
    child process - only a same-command prefix assignment is. Real bash
    leaves `$TARGET` empty in the child too here (verified empirically:
    `touch` errors with "missing file operand", no write), distinguishing
    this from the prefix-assignment case above."""
    command = "TARGET=.env\nbash <<'EOF'\ntouch $TARGET\nEOF"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout == "", f"unexpected stdout: {process.stdout!r}"


def test_protect_files_process_substitution_still_resolves_persistent_assignment() -> (
    None
):
    """Control: the process-substitution path is untouched by this fix and
    must keep resolving a persistent, separate-segment assignment exactly
    as before - a subshell fork inherits the parent's entire variable
    scope, exported or not."""
    command = "TARGET=.env\ndiff <(touch $TARGET) <(echo x)"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert "Protected file blocked by policy: .env" in process.stdout


@pytest.mark.parametrize(
    "command",
    (
        # env -u NAME takes a separate value token; the old loop skipped
        # only the flag, leaving the value token ("VAR") to be misread as
        # the command name, so `bash` and its heredoc were never reached.
        # Indirect construction (TARGET=env, then ".$TARGET") means the
        # literal ".env" text never appears anywhere - only correct
        # resolution can catch this, not the generic literal-scan floor.
        "env -u VAR TARGET=env bash <<'EOF'\ntouch \".$TARGET\"\nEOF",
        # env -C dir (chdir) - another separate-value flag.
        "env -C /tmp TARGET=env bash <<'EOF'\ntouch \".$TARGET\"\nEOF",
        # env -S "" (split-string) - another separate-value flag.
        'env -S "" TARGET=env bash <<\'EOF\'\ntouch ".$TARGET"\nEOF',
        # sudo shares the same wrapper-skip loop and has its own
        # separate-value flags (-u USER, -g GROUP).
        "sudo -u nobody TARGET=env bash <<'EOF'\ntouch \".$TARGET\"\nEOF",
    ),
)
def test_protect_files_resolves_prefix_assignment_past_wrapper_value_flag(
    command: str,
) -> None:
    """CRITICAL security-review fix: command_name()'s sudo/env/command
    wrapper-flag loop now skips a value-taking flag's separate value token
    too, so the real command and its own prefix assignment are still found
    and resolved. Verified in real bash first (throwaway temp dir, harmless
    marker file): `env -u SOME_VAR TARGET=marker bash <<'EOF'` does write
    the marker."""
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert "Protected file blocked by policy: .env" in process.stdout


def test_protect_files_allows_legitimate_env_value_flag_with_harmless_body() -> None:
    """Must-not-regress control: `env -u FOO` followed by a genuinely
    harmless heredoc body must not become a new false positive merely
    because the wrapper now understands -u takes a value."""
    command = "env -u FOO bash <<'EOF'\necho hello\nEOF"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout == "", f"unexpected stdout: {process.stdout!r}"


def test_protect_files_fails_closed_for_unrecognized_wrapper_flag() -> None:
    """CRITICAL security-review fix, backstop 2: a future/unmodeled env
    flag must not be silently assumed to take no value (that assumption is
    exactly how -u's value was mistaken for the command name before this
    fix) - the segment becomes ambiguous instead, and the conservative
    fallback still examines the heredoc body directly rather than treating
    it as invisible."""
    command = "env --future-flag=value bash <<'EOF'\ntouch .env\nEOF"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


def test_protect_files_allows_quoted_heredoc_command_substitution_syntax_as_data() -> (
    None
):
    """A *quoted* heredoc delimiter suppresses shell expansion entirely, so
    `$(...)`-shaped text in the body is inert prose, not a command
    substitution - the quoted/unquoted distinction the CRITICAL fix relies
    on. (The commit-message reproduction test above already proves the
    apostrophe/brace case; this proves the $( ) case specifically stays
    inert when quoted, with body text that has no protected-looking literal
    for the always-on scan floor to catch instead.)"""
    command = "cat <<'EOF'\n$(some_command some_argument)\nEOF"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout == "", f"unexpected stdout: {process.stdout!r}"


def test_protect_files_allows_heredoc_nested_inside_process_substitution() -> None:
    """Nesting must compose: a heredoc inside a process substitution, both
    read-only, must be allowed."""
    command = "diff <(cat <<'A'\nfoo\nA\n) <(cat <<'B'\nbar\nB\n)"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout == "", f"unexpected stdout: {process.stdout!r}"


@pytest.mark.parametrize(
    "command",
    (
        "diff <(touch .env) <(cat CLAUDE.md)",
        "diff <(cat <(touch .env)) <(echo x)",
        "tee >(cat > .env)",
        # CRITICAL security-review fix: a *mutating heredoc* nested inside
        # <( ) / >( ), not merely a mutating plain command - the recursive
        # call for the process substitution's inner text must still be able
        # to resolve a heredoc placeholder the outer extraction pass lifted
        # out first.
        "diff <(bash <<'A'\ntouch .env\nA\n) <(cat <<'B'\nbar\nB\n)",
        "tee >(bash <<'A'\ntouch .env\nA\n)",
        # A process substitution nested inside a bare shell heredoc's own
        # body, itself containing another nested heredoc.
        "bash <<'EOF'\ndiff <(bash <<'X'\ntouch .env\nX\n) <(cat CLAUDE.md)\nEOF",
    ),
)
def test_protect_files_confirms_mutation_inside_process_substitution(
    command: str,
) -> None:
    """Negative control: a real mutator inside <( ) or >( ), including a
    nested substitution and a mutating heredoc nested inside one, must still
    be a *confirmed* denial - not merely the softer "could not determine"
    uncertain wording a naive token leak could produce by accident, and
    never a silent allow from an unresolved, orphaned heredoc placeholder."""
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert "Protected file blocked by policy: .env" in process.stdout
    assert "could not determine" not in process.stdout


@pytest.mark.parametrize(
    "command",
    (
        "echo $((1 << 2))",
        "echo $((\n1 << 2\n))",
    ),
)
def test_protect_files_allows_arithmetic_left_shift(command: str) -> None:
    """MAJOR security-review fix: `<<` inside `$(( ))`/`(( ))` is bash's
    arithmetic left-shift operator, not a heredoc redirect. The paren-blind
    scanner used to find `<<` there, misread the next token as a heredoc
    delimiter word, and failed closed with no body/no terminator - a false
    fail for a common idiom, on both a single line and split across lines."""
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout == "", f"unexpected stdout: {process.stdout!r}"


@pytest.mark.parametrize(
    "command",
    (
        "bash <<'EOF'\ntouch .env\nEOF",
        "bash <<'EOF'\ntouch .claude/hooks/scripts/new.sh\nEOF",
    ),
)
def test_protect_files_confirms_shell_heredoc_protected_write(command: str) -> None:
    """Negative control: a bare shell interpreter executes its heredoc body
    as real code, so a protected-file mutation or hook-file edit inside it
    must still be denied."""
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


@pytest.mark.parametrize(
    "command",
    (
        'python3 <<\'PY\'\nopen(".env", "w").write("x")\nPY',
        'python3 <<\'PY\'\nPath(".env").write_text("x")\nPY',
    ),
)
def test_protect_files_denies_interpreter_heredoc_protected_write(
    command: str,
) -> None:
    """Negative control: an interpreter heredoc that opaquely writes a
    protected file must be denied, the same as the equivalent `-c` form
    already is."""
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


def test_protect_files_confirms_heredoc_redirected_to_protected_target() -> None:
    """Negative control: the heredoc's own outer redirect target is still
    classified regardless of the body content."""
    command = "cat <<'EOF' > .claude/hooks/scripts/new.sh\necho hi\nEOF"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert ".claude/hooks/scripts/new.sh" in process.stdout


def test_protect_files_denies_unknown_consumer_heredoc_with_protected_evidence() -> (
    None
):
    """An unmodeled command's heredoc stays conservative: a protected-looking
    literal in the body is still enough for a reasoned (not infra-failed)
    denial."""
    command = "some-unsupported-command <<'EOF'\nplease touch .env for me\nEOF"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert "could not determine whether the command may" in process.stdout


@pytest.mark.parametrize(
    "command",
    (
        "cat <<'EOF'\nhello",
        "printf x <<\n",
    ),
)
def test_protect_files_fails_closed_for_malformed_heredoc(
    command: str, tmp_path: Path
) -> None:
    """A heredoc with no delimiter word, or whose body never reaches its
    terminator line, is genuinely malformed shell syntax - the
    infrastructure fail-closed path (exit 2), distinguishable from an
    ordinary reasoned policy denial such as the one asserted in
    ``test_protect_files_denies_ambiguous_protected_reference_without_infra_failure``.
    This genuinely trips the shared library's fail-closed write, so it runs
    against an isolated `tmp_path` root rather than the live checkout."""
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}, repo_root=tmp_path
    )
    assert process.returncode == 2
    assert '"permissionDecision":"deny"' in process.stdout
    assert "hook could not evaluate the request safely, denying" in process.stdout


def test_protect_files_fails_closed_for_unbalanced_process_substitution(
    tmp_path: Path,
) -> None:
    """An unbalanced <( construct is genuinely malformed shell syntax - the
    infrastructure fail-closed path, not an ordinary reasoned denial. This
    genuinely trips the shared library's fail-closed write, so it runs
    against an isolated `tmp_path` root rather than the live checkout."""
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": "diff <(cat README.md"}},
        repo_root=tmp_path,
    )
    assert process.returncode == 2
    assert '"permissionDecision":"deny"' in process.stdout
    assert "hook could not evaluate the request safely, denying" in process.stdout


# CRITICAL security-review fix: `<`, `<<`, `<(`, and `>(` are shell
# metacharacters that terminate the preceding word even with no leading
# space (`bash<<'EOF'` and `cat<(...)` are both valid, executing bash), but
# the entire corpus above always wrote a leading space before these
# operators - the same convention the round-1 review itself used, which is
# exactly why nobody exercised the glued form. Every test below repeats an
# existing corpus command with that space removed, sweeping allow and deny
# cases across every distinct mechanism: command-name gluing for both `<<`
# and `<(`/`>(` (which defeats classification entirely, not merely one
# protected-path category), the exact/suffix/prefix protected-path
# categories, the outer redirect target, the READ_ONLY/sed/unquoted
# command-substitution/unknown-consumer heredoc floors, mutation nested
# inside a glued process substitution, and the hook-file and interpreter
# heredoc paths.
@pytest.mark.parametrize(
    "command",
    (
        "diff<(cat .env)<(cat CLAUDE.md)",
        "cat<<'EOF'\nFix: don't break ${arr[@]} or \"${arr[@]}\" handling\nEOF",
        (
            "git commit -F -<<'EOF'\n"
            'Fix: don\'t break ${arr[@]} or "${arr[@]}" handling\nEOF'
        ),
        "cat<<'EOF'\n$(some_command some_argument)\nEOF",
        "diff<(cat<<'A'\nfoo\nA\n)<(cat<<'B'\nbar\nB\n)",
    ),
)
def test_protect_files_allows_glued_operator_safe_commands(command: str) -> None:
    """Sweep: every safe positive case above must stay allowed when written
    with no space before <<, <(, or >( - including full-glue nesting."""
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert process.stdout == "", f"unexpected stdout: {process.stdout!r}"


@pytest.mark.parametrize(
    "command",
    (
        # Command-name gluing (minimum required coverage): defeats
        # classification entirely, for both operator families.
        "bash<<'EOF'\ntouch .env\nEOF",
        "cat<(touch .env)",
    ),
)
def test_protect_files_denies_glued_command_name_mutation(command: str) -> None:
    """Sweep: command-name gluing must not silently defeat classification -
    a real mutator must still be a *confirmed* denial."""
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert "Protected file blocked by policy: .env" in process.stdout


@pytest.mark.parametrize(
    ("command", "expected_reason_fragment"),
    (
        # Exact-match category (minimum required coverage).
        ("touch .env<<EOF\nx\nEOF", "Protected file blocked by policy: .env"),
        # Suffix-matched category (minimum required coverage).
        (
            "touch service.pem<<EOF\nx\nEOF",
            "Protected file blocked by policy: service.pem",
        ),
        # Prefix-matched controls (minimum required coverage): `startswith`
        # only inspects leading characters, so these were never at risk from
        # trailing glued garbage - confirm that stays true, with a clean
        # (non-garbled) path in the reason now that gluing is fixed.
        (
            "touch .env.local<<EOF\nx\nEOF",
            "Protected file blocked by policy: .env.local",
        ),
        (
            "touch .claude/hooks/scripts/new.sh<<EOF\nx\nEOF",
            "Editing hook files is blocked because PreToolUse cannot request "
            "approval: .claude/hooks/scripts/new.sh",
        ),
        # Redirect-target gluing: `cat > .env<<'EOF'` is valid bash where
        # ".env" is `>`'s target and `<<'EOF'` is a separate stdin redirect.
        ("cat > .env<<'EOF'\nx\nEOF", "Protected file blocked by policy: .env"),
    ),
)
def test_protect_files_denies_glued_operand_by_protected_category(
    command: str, expected_reason_fragment: str
) -> None:
    """Sweep: every protected-path category still resolves to a clean,
    exact operand/redirect-target once the trailing garbage from a glued
    placeholder is gone, not merely "still denied for the wrong reason"."""
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert expected_reason_fragment in process.stdout
    assert "HEREDOC" not in process.stdout, (
        "a leftover placeholder fragment in the reason means gluing is "
        f"still corrupting the operand: {process.stdout!r}"
    )


@pytest.mark.parametrize(
    "command",
    (
        "wc -l<<'EOF'\nreferences .env in prose\nEOF",
        "sed -n -f - CLAUDE.md<<'EOF'\ns/.*/&/w .env\nEOF",
        "cat<<EOF\n$(touch .env)\nEOF",
        "TARGET=.env\ncat<<EOF\n$(touch $TARGET)\nEOF",
        "some-unsupported-command<<'EOF'\nplease touch .env for me\nEOF",
    ),
)
def test_protect_files_denies_glued_heredoc_floor_cases(command: str) -> None:
    """Sweep: the READ_ONLY literal-scan floor, sed's own write sub-language,
    unquoted command-substitution execution (plain and variable-resolved),
    and the unknown-consumer conservative floor must all still fire when
    the heredoc operator has no leading space."""
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


@pytest.mark.parametrize(
    "command",
    (
        "diff<(touch .env) <(cat CLAUDE.md)",
        "diff <(bash<<'A'\ntouch .env\nA\n)<(cat <<'B'\nbar\nB\n)",
    ),
)
def test_protect_files_confirms_glued_mutation_inside_process_substitution(
    command: str,
) -> None:
    """Sweep: a mutator inside a glued process substitution, including a
    glued mutating heredoc nested inside one, must still be a *confirmed*
    denial."""
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert "Protected file blocked by policy: .env" in process.stdout


def test_protect_files_confirms_glued_shell_heredoc_hookfile_write() -> None:
    """Sweep: the hook-file branch (a different emit() bucket than a plain
    protected file) must still fire for a glued bare-shell heredoc."""
    command = "bash<<'EOF'\ntouch .claude/hooks/scripts/new.sh\nEOF"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert ".claude/hooks/scripts/new.sh" in process.stdout


@pytest.mark.parametrize(
    "command",
    (
        'python3<<\'PY\'\nopen(".env", "w").write("x")\nPY',
        'python3<<\'PY\'\nPath(".env").write_text("x")\nPY',
    ),
)
def test_protect_files_denies_glued_interpreter_heredoc_protected_write(
    command: str,
) -> None:
    """Sweep: an interpreter heredoc's opaque-write floor must still fire
    when the interpreter name has no space before <<."""
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


def test_protect_files_confirms_glued_heredoc_redirected_to_protected_target() -> None:
    """Sweep: the outer redirect target is still classified when the
    heredoc operator is glued to the preceding command name."""
    command = "cat<<'EOF' > .env\necho hi\nEOF"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert process.returncode == 0, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout
    assert "Protected file blocked by policy: .env" in process.stdout


def test_protect_files_fails_closed_for_malformed_command_and_without_uv(
    tmp_path: Path,
) -> None:
    malformed = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": "sed -i 'unterminated .env"}},
        repo_root=tmp_path,
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


def test_bash_safety_wrapper_short_circuits_first_decision_and_fails_closed(
    tmp_path: Path,
) -> None:
    """The malformed payload trips both `protect-files.sh`'s and this
    wrapper's own fail-closed writes, so this runs against an isolated
    `tmp_path` root rather than the live checkout."""
    scripts_dir = _isolated_hook_scripts_dir(tmp_path)
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": "touch .env"}})
    result = subprocess.run(
        ["bash", str(scripts_dir / "pretool-bash-guard.sh"), "openai-codex"],
        cwd=tmp_path,
        input=payload,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert '"permissionDecision":"deny"' in result.stdout

    malformed = subprocess.run(
        ["bash", str(scripts_dir / "pretool-bash-guard.sh"), "openai-codex"],
        cwd=tmp_path,
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


def test_protect_files_python_3_9_compatibility(tmp_path: Path) -> None:
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

    # Test 4: Malformed payload should fail closed. This genuinely trips the
    # shared library's fail-closed write, so it runs against an isolated
    # tmp_path root rather than the live checkout.
    scripts_dir = _isolated_hook_scripts_dir(tmp_path)
    malformed = subprocess.run(
        ["bash", str(scripts_dir / "protect-files.sh"), "openai-codex"],
        cwd=tmp_path,
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


def test_antigravity_pretool_fails_closed_for_raw_malformed_json(
    tmp_path: Path,
) -> None:
    """Raw malformed hook stdin receives a protocol deny, not a crash."""
    process = subprocess.run(
        ["python3", str(SCRIPT_SRC / "antigravity-pretool.py")],
        cwd=tmp_path,
        input="{malformed",
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "REPO_ROOT": str(tmp_path)},
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
