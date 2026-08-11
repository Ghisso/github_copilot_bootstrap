"""Regression coverage for git-backed AI state sync (``state-sync.sh``).

Exercises the real shared script against throwaway local git repositories so
the failure-propagation and multi-writer conflict guarantees are verified
end-to-end rather than mocked. A bare repo stands in for ``origin`` and every
git operation is local, so the suite needs no network.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from runtime_ownership import render_restore_script  # noqa: E402

SCRIPT_SRC = REPO_ROOT / "shared" / "hooks" / "scripts" / "state-sync.sh"
RESTORE_SRC = REPO_ROOT / "shared" / "hooks" / "scripts" / "restore-root-adapters.sh"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run ``git -C root <args>`` and capture output without raising."""
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _sync(
    script: Path,
    root: Path,
    remote: Path | None,
    mode: str,
    *args: str,
    trace_path: Path | None = None,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Invoke the copied ``state-sync.sh`` for one writer against ``remote``."""
    env = {
        **os.environ,
        "AI_STATE_REPO_ROOT": str(root),
        "AI_STATE_BRANCH": "ai-state",
        # Pin off so an ambient AI_STATE_LOCAL_ONLY in the dev shell can't
        # silently divert these tests into local-only mode (no remote ops).
        "AI_STATE_LOCAL_ONLY": "0",
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
    }
    if remote is not None:
        env["AI_STATE_REMOTE"] = str(remote)
    if trace_path is not None:
        env["GIT_TRACE2_EVENT"] = str(trace_path)
    if extra_env is not None:
        env.update(extra_env)
    return subprocess.run(
        ["bash", str(script), mode, *args],
        text=True,
        capture_output=True,
        check=False,
        # stdin closed so the script's 2s stdin-drain returns immediately.
        stdin=subprocess.DEVNULL,
        env=env,
    )


@pytest.fixture
def script(tmp_path: Path) -> Path:
    """Copy the script alone into a temp dir.

    With no sibling ``restore-root-adapters.sh``, ``cmd_setup`` skips the
    root-adapter restore, keeping each test hermetic.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    dst = bin_dir / "state-sync.sh"
    shutil.copy(SCRIPT_SRC, dst)
    return dst


def _bare_remote(tmp_path: Path) -> Path:
    """Create an empty bare repo to act as ``origin``."""
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    return remote


def _new_writer(script: Path, tmp_path: Path, remote: Path, name: str) -> Path:
    """Create a repo root with a fresh ``.claude`` and run ``setup``.

    ``setup`` reconciles with ``origin/ai-state`` when it already exists, so a
    second writer starts from the published state.
    """
    root = tmp_path / name
    (root / ".claude").mkdir(parents=True)
    result = _sync(script, root, remote, "setup")
    assert result.returncode == 0, result.stderr
    return root


def _write(root: Path, relpath: str, content: str) -> None:
    """Write ``content`` to ``.claude/<relpath>`` under a writer root."""
    path = root / ".claude" / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _restore(root: Path) -> subprocess.CompletedProcess[str]:
    """Run the real root-adapter restorer from its installed location."""
    script = root / ".claude" / "hooks" / "scripts" / "restore-root-adapters.sh"
    script.parent.mkdir(parents=True, exist_ok=True)
    script.write_text(render_restore_script(RESTORE_SRC.read_text(encoding="utf-8")))
    return subprocess.run(
        ["bash", str(script)], text=True, capture_output=True, check=False
    )


def _write_restore_manifest(root: Path, *paths: str) -> None:
    """Write the inert manifest format emitted by runtime_ownership.py."""
    manifest = root / ".claude" / "bootstrap-ownership.env"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        "# Generated from scripts/runtime_ownership.py.\n"
        + "".join(f"BOOTSTRAP_ROOT_PATH={path}\n" for path in paths)
    )


def _local_show(root: Path, relpath: str) -> str:
    """Content of ``relpath`` at the writer's local ``HEAD``."""
    return _git(root / ".claude", "show", f"HEAD:{relpath}").stdout


def _remote_show(remote: Path, relpath: str) -> str:
    """Content of ``relpath`` on ``origin/ai-state`` (empty if absent)."""
    return subprocess.run(
        ["git", "-C", str(remote), "show", f"ai-state:{relpath}"],
        text=True,
        capture_output=True,
        check=False,
    ).stdout


def _no_active_rebase_or_merge(root: Path) -> bool:
    """True when the nested repo is left outside any rebase/merge state."""
    git_dir = root / ".claude" / ".git"
    if (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists():
        return False
    if (git_dir / "MERGE_HEAD").exists():
        return False
    unmerged = _git(root / ".claude", "diff", "--name-only", "--diff-filter=U").stdout
    return unmerged.strip() == ""


_REMOTE_GIT_COMMANDS = {"fetch", "ls-remote", "pull", "merge", "push"}


def _traced_remote_commands(trace_path: Path) -> list[str]:
    """Return remote-facing Git commands found in a Trace2 event log."""
    assert trace_path.is_file(), "Git Trace2 event log was not created"
    commands: list[str] = []
    start_events = 0
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("event") != "start":
            continue
        start_events += 1
        argv = event.get("argv", [])
        if isinstance(argv, list):
            commands.extend(
                command for command in argv if command in _REMOTE_GIT_COMMANDS
            )
    assert start_events, "Git Trace2 event log contained no Git start events"
    return commands


def _local_head(root: Path) -> str:
    """Return the nested repository's current commit ID."""
    return _git(root / ".claude", "rev-parse", "HEAD").stdout.strip()


def _local_commit_count(root: Path) -> int:
    """Return the number of commits reachable from the nested HEAD."""
    return int(_git(root / ".claude", "rev-list", "--count", "HEAD").stdout)


def _half_initialized_rebase(root: Path) -> Path:
    """Create the incomplete rebase state Git can only clear with ``--quit``."""
    rebase_dir = root / ".claude" / ".git" / "rebase-merge"
    rebase_dir.mkdir()
    (rebase_dir / "autostash").write_text("deadbeef\n")
    return rebase_dir


def _rebase_metadata(root: Path) -> dict[str, bytes]:
    """Return the active rebase metadata as byte snapshots by relative path."""
    git_dir = root / ".claude" / ".git"
    snapshot: dict[str, bytes] = {}
    for rebase_dir in (git_dir / "rebase-merge", git_dir / "rebase-apply"):
        if not rebase_dir.is_dir():
            continue
        for path in sorted(rebase_dir.rglob("*")):
            key = path.relative_to(git_dir).as_posix()
            if path.is_symlink():
                snapshot[key] = b"symlink:" + os.readlink(path).encode()
            elif path.is_dir():
                snapshot[key] = b"directory"
            else:
                snapshot[key] = b"file:" + path.read_bytes()
    return snapshot


def _worktree_snapshot(root: Path) -> dict[str, bytes]:
    """Return every non-Git worktree file as a byte snapshot."""
    worktree = root / ".claude"
    return {
        path.relative_to(worktree).as_posix(): path.read_bytes()
        for path in sorted(worktree.rglob("*"))
        if path.is_file() and ".git" not in path.relative_to(worktree).parts
    }


def _valid_preexisting_rebase(
    script: Path, tmp_path: Path, remote: Path, name: str
) -> tuple[Path, str]:
    """Create a real conflicted rebase that represents active operator work."""
    writer = _new_writer(script, tmp_path, remote, name)
    rebase_file = "plans/operator-rebase.md"
    assert _git(writer / ".claude", "config", "user.name", "Test").returncode == 0
    assert (
        _git(writer / ".claude", "config", "user.email", "test@example.com").returncode
        == 0
    )
    _write(writer, rebase_file, "base\n")
    assert _sync(script, writer, remote, "push").returncode == 0
    assert _git(writer / ".claude", "checkout", "-qb", "operator-work").returncode == 0
    _write(writer, rebase_file, "operator\n")
    assert _git(writer / ".claude", "add", "-A").returncode == 0
    assert _git(writer / ".claude", "commit", "-qm", "operator").returncode == 0
    assert _git(writer / ".claude", "checkout", "-q", "ai-state").returncode == 0
    _write(writer, rebase_file, "sync\n")
    assert _git(writer / ".claude", "add", "-A").returncode == 0
    assert _git(writer / ".claude", "commit", "-qm", "sync").returncode == 0
    assert _git(writer / ".claude", "checkout", "-q", "operator-work").returncode == 0
    assert _git(writer / ".claude", "rebase", "ai-state").returncode != 0
    return writer, rebase_file


def test_checkpoint_commits_locally_without_remote_io(
    script: Path, tmp_path: Path
) -> None:
    """Checkpoint is a network-free local commit boundary."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "checkpoint")
    _write(writer, "plans/checkpoint.md", "checkpointed\n")
    trace_path = tmp_path / "checkpoint-trace.json"

    result = _sync(script, writer, remote, "checkpoint", trace_path=trace_path)

    assert result.returncode == 0
    assert result.stdout == ""
    assert _local_show(writer, "plans/checkpoint.md") == "checkpointed\n"
    assert not _remote_show(remote, "plans/checkpoint.md")
    assert _traced_remote_commands(trace_path) == []


def test_publish_sends_checkpoint_without_another_commit_and_is_idempotent(
    script: Path, tmp_path: Path
) -> None:
    """Publish sends an existing checkpoint without creating a new commit."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "publish")
    _write(writer, "plans/publish.md", "ready\n")
    assert _sync(script, writer, remote, "checkpoint").returncode == 0
    before_head = _local_head(writer)
    before_count = _local_commit_count(writer)

    first = _sync(script, writer, remote, "publish")
    first_remote_head = _git(remote, "rev-parse", "ai-state").stdout.strip()
    second = _sync(script, writer, remote, "publish")

    assert first.returncode == 0
    assert second.returncode == 0
    assert first.stdout == second.stdout == ""
    assert _remote_show(remote, "plans/publish.md") == "ready\n"
    assert _local_head(writer) == before_head == first_remote_head
    assert _local_commit_count(writer) == before_count
    assert _git(remote, "rev-parse", "ai-state").stdout.strip() == first_remote_head


def test_publish_refuses_dirty_state_without_committing_or_publishing(
    script: Path, tmp_path: Path
) -> None:
    """Publish preserves uncheckpointed files for a later checkpoint."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "dirty-publish")
    _write(writer, "plans/published.md", "published\n")
    assert _sync(script, writer, remote, "checkpoint").returncode == 0
    assert _sync(script, writer, remote, "publish").returncode == 0
    remote_head = _git(remote, "rev-parse", "ai-state").stdout.strip()
    local_head = _local_head(writer)
    _write(writer, "plans/uncheckpointed.md", "keep-local\n")

    result = _sync(script, writer, remote, "publish")

    assert result.returncode == 0
    assert result.stdout == ""
    assert "dirty" in result.stderr.lower()
    assert _local_head(writer) == local_head
    assert (
        "?? plans/uncheckpointed.md"
        in _git(writer / ".claude", "status", "--porcelain").stdout
    )
    assert not _remote_show(remote, "plans/uncheckpointed.md")
    assert _git(remote, "rev-parse", "ai-state").stdout.strip() == remote_head


def test_push_remains_checkpoint_then_publish_compatible(
    script: Path, tmp_path: Path
) -> None:
    """The legacy push command still checkpoints and publishes in one call."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "push-compatible")
    _write(writer, "plans/push.md", "legacy\n")

    result = _sync(script, writer, remote, "push")

    assert result.returncode == 0
    assert result.stdout == ""
    assert _local_show(writer, "plans/push.md") == "legacy\n"
    assert _remote_show(remote, "plans/push.md") == "legacy\n"


def test_status_is_local_only_credential_safe_and_reports_cached_state(
    script: Path, tmp_path: Path
) -> None:
    """Status reports local state without contacting or printing the remote."""
    remote = _bare_remote(tmp_path)
    uninitialized = tmp_path / "uninitialized"
    uninitialized.mkdir()
    remote_url = f"https://token@example.invalid/{remote.name}"

    initial = _sync(script, uninitialized, None, "status")

    assert initial.returncode == 0
    assert "repository: uninitialized" in initial.stdout
    assert "error-log:" in initial.stdout
    assert remote_url not in initial.stdout

    writer = _new_writer(script, tmp_path, remote, "status")
    clean_trace = tmp_path / "clean-status-trace.json"
    clean = _sync(script, writer, remote, "status", trace_path=clean_trace)
    assert "repository: initialized" in clean.stdout
    assert "worktree: clean" in clean.stdout
    assert "remote: configured" in clean.stdout
    assert "tracking: unavailable" in clean.stdout
    assert "rebase: none" in clean.stdout
    assert _traced_remote_commands(clean_trace) == []

    _write(writer, "plans/dirty.md", "dirty\n")
    dirty = _sync(script, writer, remote, "status")
    assert "worktree: dirty" in dirty.stdout

    assert _sync(script, writer, remote, "checkpoint").returncode == 0
    assert _sync(script, writer, remote, "publish").returncode == 0
    _write(writer, "plans/ahead.md", "ahead\n")
    assert _sync(script, writer, remote, "checkpoint").returncode == 0
    ahead = _sync(script, writer, remote, "status")
    assert "tracking: ahead=1 behind=0" in ahead.stdout


def test_pull_clears_half_initialized_rebase_state(
    script: Path, tmp_path: Path
) -> None:
    """Pull clears leftover rebase metadata before starting remote reconciliation."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "half-initialized")
    assert _sync(script, writer, remote, "checkpoint").returncode == 0
    rebase_dir = _half_initialized_rebase(writer)
    actual_git = shutil.which("git")
    assert actual_git is not None
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    invocations = tmp_path / "git-invocations.log"
    fake_git.write_text(
        "#!/usr/bin/env bash\n"
        'printf "%s %s\\n" "${3:-}" "${4:-}" >> "$GIT_INVOCATIONS"\n'
        'if [[ "$3" == "rebase" && "$4" == "--quit" ]]; then\n'
        "  printf 'orphaned-autostash-quit-invoked\\n' >&2\n"
        "fi\n"
        f'exec "{actual_git}" "$@"\n'
    )
    fake_git.chmod(0o755)

    recovered = _sync(
        script,
        writer,
        remote,
        "pull",
        extra_env={
            "GIT_INVOCATIONS": str(invocations),
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
        },
    )
    error_log = writer / ".claude" / "session_logs" / "hooks-errors.log"

    assert recovered.returncode == 0
    assert (
        "orphaned autostash rebase state from a previous sync detected"
        in recovered.stderr
    )
    assert "reconciliation with origin/ai-state failed" not in recovered.stderr
    assert not rebase_dir.exists()
    assert "orphaned-autostash-quit-invoked" in error_log.read_text()
    rebase_invocations = [
        line
        for line in invocations.read_text().splitlines()
        if line.startswith("rebase ")
    ]
    assert rebase_invocations == ["rebase --quit"]

    following_pull = _sync(script, writer, remote, "pull")

    assert following_pull.returncode == 0
    assert "leftover rebase state from a previous sync" not in following_pull.stderr


def test_rebase_abort_alone_cannot_clear_half_initialized_state(
    script: Path, tmp_path: Path
) -> None:
    """The fixture matches the Git state that requires ``rebase --quit``."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "abort-only")
    rebase_dir = _half_initialized_rebase(writer)

    result = _git(writer / ".claude", "rebase", "--abort")

    assert result.returncode != 0
    assert rebase_dir.exists()


@pytest.mark.parametrize(
    "shape", ("extra-file", "subdirectory", "symlink", "rebase-apply")
)
def test_extra_or_nonfile_rebase_metadata_is_preserved(
    script: Path, tmp_path: Path, shape: str
) -> None:
    """Only the observed one-file orphan shape is safe to clear automatically."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, shape)
    rebase_dir = _half_initialized_rebase(writer)
    if shape == "extra-file":
        (rebase_dir / "extra").write_text("metadata\n")
    elif shape == "subdirectory":
        (rebase_dir / "metadata").mkdir()
    elif shape == "symlink":
        target = tmp_path / "autostash-target"
        target.write_text("metadata\n")
        (rebase_dir / "autostash").unlink()
        (rebase_dir / "autostash").symlink_to(target)
    else:
        (writer / ".claude" / ".git" / "rebase-apply").mkdir()
    before_metadata = _rebase_metadata(writer)
    actual_git = shutil.which("git")
    assert actual_git is not None
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    invocations = tmp_path / "git-invocations.log"
    fake_git.write_text(
        "#!/usr/bin/env bash\n"
        'printf "%s %s\\n" "${3:-}" "${4:-}" >> "$GIT_INVOCATIONS"\n'
        f'exec "{actual_git}" "$@"\n'
    )
    fake_git.chmod(0o755)

    result = _sync(
        script,
        writer,
        remote,
        "pull",
        extra_env={
            "GIT_INVOCATIONS": str(invocations),
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
        },
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert "pre-existing rebase state is ambiguous" in result.stderr
    assert not invocations.exists()
    assert _rebase_metadata(writer) == before_metadata


@pytest.mark.parametrize(
    "mode",
    ("setup", "pull", "checkpoint", "publish", "push", "migrate-from-hf"),
)
def test_mutating_entrypoints_preserve_valid_preexisting_rebase(
    script: Path, tmp_path: Path, mode: str
) -> None:
    """Every mutating entry point leaves an active operator rebase untouched."""
    remote = _bare_remote(tmp_path)
    writer, rebase_file = _valid_preexisting_rebase(script, tmp_path, remote, mode)

    before_head = _local_head(writer)
    before_index = _git(writer / ".claude", "ls-files", "--stage").stdout
    before_status = _git(writer / ".claude", "status", "--porcelain=v1", "-z").stdout
    before_content = (writer / ".claude" / rebase_file).read_bytes()
    before_worktree = _worktree_snapshot(writer)
    before_metadata = _rebase_metadata(writer)
    before_remote = _git(remote, "rev-parse", "ai-state").stdout
    error_log = writer / ".claude" / "session_logs" / "hooks-errors.log"
    before_error_log = error_log.read_bytes() if error_log.exists() else None
    actual_git = shutil.which("git")
    assert actual_git is not None
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    invocations = tmp_path / "git-invocations.log"
    fake_git.write_text(
        "#!/usr/bin/env bash\n"
        'printf "%s %s\\n" "${3:-}" "${4:-}" >> "$GIT_INVOCATIONS"\n'
        f'exec "{actual_git}" "$@"\n'
    )
    fake_git.chmod(0o755)

    result = _sync(
        script,
        writer,
        remote,
        mode,
        extra_env={
            "GIT_INVOCATIONS": str(invocations),
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
        },
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert "pre-existing rebase state is ambiguous" in result.stderr
    assert not invocations.exists()
    assert _local_head(writer) == before_head
    assert _git(writer / ".claude", "ls-files", "--stage").stdout == before_index
    assert (
        _git(writer / ".claude", "status", "--porcelain=v1", "-z").stdout
        == before_status
    )
    assert (writer / ".claude" / rebase_file).read_bytes() == before_content
    assert _worktree_snapshot(writer) == before_worktree
    assert _rebase_metadata(writer) == before_metadata
    assert _git(remote, "rev-parse", "ai-state").stdout == before_remote
    if before_error_log is None:
        assert not error_log.exists()
    else:
        assert error_log.read_bytes() == before_error_log


def test_current_pull_recovery_reports_distinct_abort_and_quit_failures(
    script: Path, tmp_path: Path
) -> None:
    """Current-pull recovery preserves both abort and quit diagnostics."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "recovery-failure")
    _write(writer, "plans/published.md", "published\n")
    assert _sync(script, writer, remote, "push").returncode == 0
    assert not (writer / ".claude" / ".git" / "rebase-merge").exists()
    assert not (writer / ".claude" / ".git" / "rebase-apply").exists()
    actual_git = shutil.which("git")
    assert actual_git is not None
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    invocations = tmp_path / "git-invocations.log"
    fake_git.write_text(
        "#!/usr/bin/env bash\n"
        'printf "%s %s\\n" "${3:-}" "${4:-}" >> "$GIT_INVOCATIONS"\n'
        'if [[ "$3" == "pull" ]]; then\n'
        '  mkdir -p "$2/.git/rebase-merge"\n'
        '  printf "current-pull\\n" > "$2/.git/rebase-merge/head-name"\n'
        "  printf 'forced current pull failure\\n' >&2\n"
        "  exit 1\n"
        "fi\n"
        'if [[ "$3" == "rebase" && "$4" == "--abort" ]]; then\n'
        "  printf 'forced abort recovery failure\\n' >&2\n"
        "  exit 1\n"
        "fi\n"
        'if [[ "$3" == "rebase" && "$4" == "--quit" ]]; then\n'
        "  printf 'forced quit recovery failure\\n' >&2\n"
        "  exit 1\n"
        "fi\n"
        f'exec "{actual_git}" "$@"\n'
    )
    fake_git.chmod(0o755)

    result = _sync(
        script,
        writer,
        remote,
        "pull",
        extra_env={
            "GIT_INVOCATIONS": str(invocations),
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
        },
    )
    error_log = writer / ".claude" / "session_logs" / "hooks-errors.log"

    assert result.returncode == 0
    assert (
        "leftover rebase state from a failed reconciliation could not be cleared"
        in result.stderr
    )
    assert f"git -C {writer / '.claude'} rebase --quit" in result.stderr
    assert "pull: up to date" not in result.stderr
    assert error_log.exists()
    assert "forced abort recovery failure" in error_log.read_text()
    assert "forced quit recovery failure" in error_log.read_text()
    rebase_invocations = [
        line
        for line in invocations.read_text().splitlines()
        if line.startswith("rebase ")
    ]
    assert rebase_invocations == ["rebase --abort", "rebase --quit"]


def test_failed_pull_without_rebase_does_not_attempt_recovery(
    script: Path, tmp_path: Path
) -> None:
    """An ordinary failed pull does not report or log nonexistent rebase recovery."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "ordinary-pull-failure")
    _write(writer, "plans/published.md", "published\n")
    assert _sync(script, writer, remote, "push").returncode == 0
    actual_git = shutil.which("git")
    assert actual_git is not None
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    fake_git.write_text(
        "#!/usr/bin/env bash\n"
        'if [[ "$3" == "pull" ]]; then\n'
        "  printf 'forced ordinary pull failure\\n' >&2\n"
        "  exit 1\n"
        "fi\n"
        f'exec "{actual_git}" "$@"\n'
    )
    fake_git.chmod(0o755)

    result = _sync(
        script,
        writer,
        remote,
        "pull",
        extra_env={"PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )
    error_log = writer / ".claude" / "session_logs" / "hooks-errors.log"

    assert result.returncode == 0
    assert "reconciliation with origin/ai-state failed" in result.stderr
    assert "leftover rebase state" not in result.stderr
    assert "forced ordinary pull failure" in error_log.read_text()
    assert "No rebase in progress" not in error_log.read_text()


def test_status_reports_rebase_state(script: Path, tmp_path: Path) -> None:
    """Status exposes leftover rebase state without invoking Git recovery."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "status-rebase")
    rebase_dir = _half_initialized_rebase(writer)

    in_progress = _sync(script, writer, remote, "status")
    shutil.rmtree(rebase_dir)
    clear = _sync(script, writer, remote, "status")

    assert "rebase: in-progress" in in_progress.stdout
    assert "rebase: none" in clear.stdout


def test_restore_root_adapters_parses_inert_paths_and_preserves_tracked_files(
    tmp_path: Path,
) -> None:
    """Tracked adapters survive while generated siblings are refreshed."""
    root = tmp_path / "consumer"
    source = root / ".claude" / "bootstrap-root"
    _write_restore_manifest(root, "CLAUDE.md", ".codex")
    source.mkdir(parents=True)
    (source / "CLAUDE.md").write_text("generated guidance\n")
    (source / ".codex").mkdir()
    (source / ".codex" / "config.toml").write_text("generated config\n")
    (source / ".codex" / "agents").mkdir(parents=True)
    (source / ".codex" / "agents" / "coder.toml").write_text("new agent\n")
    (root / ".codex" / "agents").mkdir(parents=True)
    (root / ".codex" / "config.toml").write_text("tracked config\n")
    (root / ".codex" / "agents" / "coder.toml").write_text("stale agent\n")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", ".codex/config.toml"], check=True)

    result = _restore(root)

    assert result.returncode == 0, result.stderr
    assert (root / "CLAUDE.md").read_text() == "generated guidance\n"
    assert (root / ".codex" / "config.toml").read_text() == "tracked config\n"
    assert (root / ".codex" / "agents" / "coder.toml").read_text() == "new agent\n"


def test_restore_root_adapters_preserves_tracked_root_guidance(
    tmp_path: Path,
) -> None:
    """Tracked authoring guidance wins over differing restored root copies."""
    root = tmp_path / "bootstrap-authoring"
    source = root / ".claude" / "bootstrap-root"
    _write_restore_manifest(root, "AGENTS.md", "CLAUDE.md")
    source.mkdir(parents=True)
    for name in ("AGENTS.md", "CLAUDE.md"):
        (root / name).write_text(f"authoring {name}\n")
        (source / name).write_text(f"generated {name}\n")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(
        ["git", "-C", str(root), "add", "AGENTS.md", "CLAUDE.md"], check=True
    )

    result = _restore(root)

    assert result.returncode == 0, result.stderr
    for name in ("AGENTS.md", "CLAUDE.md"):
        assert (root / name).read_text() == f"authoring {name}\n"


@pytest.mark.parametrize(
    "record",
    (
        "BOOTSTRAP_ROOT_PATH=$(touch should-not-run)",
        "BOOTSTRAP_ROOT_PATH=../../outside",
        "BOOTSTRAP_ROOT_PATH=/tmp/outside",
    ),
)
def test_restore_root_adapters_rejects_untrusted_manifest_records(
    tmp_path: Path, record: str
) -> None:
    """Manifest data cannot execute shell or escape its two expected roots."""
    root = tmp_path / "consumer"
    source = root / ".claude" / "bootstrap-root"
    source.mkdir(parents=True)
    marker = tmp_path / "should-not-run"
    rendered_record = record.replace("should-not-run", str(marker))
    (root / ".claude" / "bootstrap-ownership.env").write_text(f"{rendered_record}\n")

    result = _restore(root)

    assert result.returncode == 1
    assert "invalid manifest path" in result.stderr
    assert not marker.exists()
    assert not (tmp_path / "outside").exists()


def test_restore_root_adapters_rejects_allowed_source_symlink_escape(
    tmp_path: Path,
) -> None:
    """An allowlisted adapter cannot redirect restoration outside bootstrap-root."""
    root = tmp_path / "consumer"
    source = root / ".claude" / "bootstrap-root"
    outside = tmp_path / "outside"
    source.mkdir(parents=True)
    outside.mkdir()
    (outside / "config.toml").write_text("escaped\n")
    (source / ".codex").symlink_to(outside, target_is_directory=True)
    _write_restore_manifest(root, ".codex")

    result = _restore(root)

    assert result.returncode == 1
    assert "missing or unsafe source path: .codex" in result.stderr
    assert not (root / ".codex").exists()


def test_push_after_rebase_conflict_does_not_push(script: Path, tmp_path: Path) -> None:
    """A same-file conflict must abort cleanly and skip the doomed push.

    ``plans/`` is narrative state, so the conflict is left for manual merge
    rather than auto-resolved. The push must not run (it would be rejected
    non-fast-forward), and no local or remote commit may be lost.
    """
    remote = _bare_remote(tmp_path)
    a = _new_writer(script, tmp_path, remote, "A")
    _write(a, "plans/x.md", "base\n")
    assert _sync(script, a, remote, "push").returncode == 0
    assert _remote_show(remote, "plans/x.md") == "base\n"

    b = _new_writer(script, tmp_path, remote, "B")
    _write(b, "plans/x.md", "from-B\n")
    assert _sync(script, b, remote, "push").returncode == 0
    assert _remote_show(remote, "plans/x.md") == "from-B\n"

    # A diverges on the same line without having seen B's change.
    _write(a, "plans/x.md", "from-A\n")
    result = _sync(script, a, remote, "push")

    # Top-level dispatch always exits 0 so a hook never blocks Codex shutdown,
    # but the push itself must not have happened: the remote still holds B.
    assert result.returncode == 0
    assert _remote_show(remote, "plans/x.md") == "from-B\n"
    # A's own commit is intact and reachable.
    assert _local_show(a, "plans/x.md") == "from-A\n"
    # The remote commit is still reachable locally too.
    assert _git(a / ".claude", "cat-file", "-e", "origin/ai-state").returncode == 0
    assert _no_active_rebase_or_merge(a)
    assert "reconciliation" in result.stderr.lower()


def test_two_writers_separate_files_reconcile_and_push(
    script: Path, tmp_path: Path
) -> None:
    """Writers touching different files reconcile via rebase and push."""
    remote = _bare_remote(tmp_path)
    a = _new_writer(script, tmp_path, remote, "A")
    _write(a, "seed.md", "seed\n")
    assert _sync(script, a, remote, "push").returncode == 0

    b = _new_writer(script, tmp_path, remote, "B")
    _write(b, "plans/b.md", "B\n")
    assert _sync(script, b, remote, "push").returncode == 0

    _write(a, "plans/a.md", "A\n")
    result = _sync(script, a, remote, "push")

    assert result.returncode == 0
    assert _remote_show(remote, "plans/a.md") == "A\n"
    assert _remote_show(remote, "plans/b.md") == "B\n"


def test_reconciliation_after_conflict_can_push(script: Path, tmp_path: Path) -> None:
    """After a conflict aborts, a manual reconciliation still pushes cleanly."""
    remote = _bare_remote(tmp_path)
    a = _new_writer(script, tmp_path, remote, "A")
    _write(a, "plans/x.md", "base\n")
    assert _sync(script, a, remote, "push").returncode == 0

    b = _new_writer(script, tmp_path, remote, "B")
    _write(b, "plans/x.md", "from-B\n")
    assert _sync(script, b, remote, "push").returncode == 0

    _write(a, "plans/x.md", "from-A\n")
    assert _sync(script, a, remote, "push").returncode == 0  # conflict, no push
    assert _remote_show(remote, "plans/x.md") == "from-B\n"

    # Human resolves by taking the remote and re-applying their intent.
    assert _git(a / ".claude", "reset", "--hard", "origin/ai-state").returncode == 0
    _write(a, "plans/x.md", "resolved\n")
    result = _sync(script, a, remote, "push")

    assert result.returncode == 0
    assert _remote_show(remote, "plans/x.md") == "resolved\n"


def test_append_only_log_union_merges(script: Path, tmp_path: Path) -> None:
    """Concurrent appends to a ``session_logs/*.log`` file auto-union-merge.

    The nested ``.gitattributes`` gives these append-only logs git's built-in
    ``merge=union`` driver, so two writers adding different lines reconcile
    during rebase instead of conflicting.
    """
    log = "session_logs/hooks-sessions.log"
    remote = _bare_remote(tmp_path)
    a = _new_writer(script, tmp_path, remote, "A")
    _write(a, log, "L1\n")
    assert _sync(script, a, remote, "push").returncode == 0

    b = _new_writer(script, tmp_path, remote, "B")
    _write(b, log, "L1\nfrom-B\n")
    assert _sync(script, b, remote, "push").returncode == 0

    # A appends a different line to the same region without seeing B.
    _write(a, log, "L1\nfrom-A\n")
    result = _sync(script, a, remote, "push")

    assert result.returncode == 0
    merged = _remote_show(remote, log)
    assert "from-A" in merged
    assert "from-B" in merged


def _seed_remote(
    script: Path, tmp_path: Path, remote: Path, relpath: str, content: str
) -> None:
    """Publish one file to origin/ai-state via a throwaway writer."""
    seeder = _new_writer(script, tmp_path, remote, f"seed-{relpath.replace('/', '-')}")
    _write(seeder, relpath, content)
    assert _sync(script, seeder, remote, "push").returncode == 0


def test_setup_merges_remote_error_log_without_creating_a_local_blocker(
    script: Path, tmp_path: Path
) -> None:
    """Fresh setup must not create the error log before an unrelated merge."""
    remote = _bare_remote(tmp_path)
    _seed_remote(script, tmp_path, remote, "session_logs/hooks-errors.log", "remote\n")
    writer = tmp_path / "fresh-setup"
    (writer / ".claude").mkdir(parents=True)

    result = _sync(script, writer, remote, "setup")

    assert result.returncode == 0
    assert _local_show(writer, "session_logs/hooks-errors.log") == "remote\n"
    assert _no_active_rebase_or_merge(writer)
    assert "could not be merged automatically" not in result.stderr


def test_setup_checkpoints_error_log_when_remote_is_unavailable(
    script: Path, tmp_path: Path
) -> None:
    """Offline setup leaves durable state clean after recording its warning."""
    writer = tmp_path / "offline-setup"
    (writer / ".claude").mkdir(parents=True)
    unavailable_remote = tmp_path / "missing.git"

    result = _sync(script, writer, unavailable_remote, "setup")

    assert result.returncode == 0
    assert _local_head(writer)
    assert _git(writer / ".claude", "status", "--porcelain").stdout == ""
    assert "fetch from origin/ai-state failed" in result.stderr
    assert "fetch from origin/ai-state failed" in _local_show(
        writer, "session_logs/hooks-errors.log"
    )


def test_migrate_conflict_commits_locally_but_does_not_push(
    script: Path, tmp_path: Path
) -> None:
    """A migrate whose reconciliation conflicts must not attempt a push.

    ``migrate-from-hf`` imports pre-git ``.claude/`` content, then reconciles
    with an existing remote. A genuine conflict aborts the merge; the migrated
    state stays committed locally, but the push is skipped (it would be
    non-fast-forward) — the twin of the cmd_push doomed-push fix.
    """
    remote = _bare_remote(tmp_path)
    _seed_remote(script, tmp_path, remote, "plans/x.md", "from-remote\n")

    # A pre-git root: .claude/ has content but no nested .git yet.
    m = tmp_path / "M"
    (m / ".claude").mkdir(parents=True)
    _write(m, "plans/x.md", "from-local\n")
    result = _sync(script, m, remote, "migrate-from-hf")

    assert result.returncode == 0
    # Remote is untouched — no push happened.
    assert _remote_show(remote, "plans/x.md") == "from-remote\n"
    # The migrated state is committed locally and reachable.
    assert (m / ".claude" / ".git").is_dir()
    assert _local_show(m, "plans/x.md") == "from-local\n"
    assert _no_active_rebase_or_merge(m)
    # Discriminate the new guard from the old unguarded code: "not pushing"
    # appears only in the new cmd_migrate guard message, and the old code's
    # misleading "network/auth" push-failure warning must be absent because no
    # push was attempted. Both assertions fail against a reverted push-guard.
    assert "not pushing" in result.stderr.lower()
    assert "network" not in result.stderr.lower()


def test_migrate_without_conflict_reconciles_and_pushes(
    script: Path, tmp_path: Path
) -> None:
    """A migrate touching files disjoint from the remote reconciles and pushes."""
    remote = _bare_remote(tmp_path)
    _seed_remote(script, tmp_path, remote, "plans/x.md", "from-remote\n")
    _seed_remote(script, tmp_path, remote, "session_logs/hooks-errors.log", "remote\n")

    n = tmp_path / "N"
    (n / ".claude").mkdir(parents=True)
    _write(n, "plans/n.md", "from-migrate\n")
    result = _sync(script, n, remote, "migrate-from-hf")

    assert result.returncode == 0
    assert _remote_show(remote, "plans/n.md") == "from-migrate\n"
    assert _remote_show(remote, "plans/x.md") == "from-remote\n"
