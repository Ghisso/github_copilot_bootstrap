"""Regression coverage for git-backed AI state sync (``state-sync.sh``).

Exercises the real shared script against throwaway local git repositories so
the failure-propagation and multi-writer conflict guarantees are verified
end-to-end rather than mocked. A bare repo stands in for ``origin`` and every
git operation is local, so the suite needs no network.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from runtime_ownership import render_restore_script  # noqa: E402

SCRIPT_SRC = REPO_ROOT / "shared" / "hooks" / "scripts" / "state-sync.sh"
RESTORE_SRC = REPO_ROOT / "shared" / "hooks" / "scripts" / "restore-root-adapters.sh"
DISPATCH_SRC = REPO_ROOT / "shared" / "hooks" / "scripts" / "context-mode-dispatch.sh"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run ``git -C root <args>`` and capture output without raising."""
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _sync_env(
    root: Path,
    remote: Path | None,
    trace_path: Path | None = None,
    extra_env: dict[str, str] | None = None,
) -> dict[str, str]:
    """Return the environment for one writer's ``state-sync.sh`` run."""
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
    return env


def _sync(
    script: Path,
    root: Path,
    remote: Path | None,
    mode: str,
    *args: str,
    trace_path: Path | None = None,
    extra_env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    """Invoke the copied ``state-sync.sh`` for one writer against ``remote``."""
    return subprocess.run(
        ["bash", str(script), mode, *args],
        text=True,
        capture_output=True,
        check=False,
        # stdin closed so the script's 2s stdin-drain returns immediately.
        stdin=subprocess.DEVNULL,
        env=_sync_env(root, remote, trace_path, extra_env),
        timeout=timeout,
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


def _install_restorer(script: Path) -> None:
    """Install the rendered sibling restorer used by session-start pull."""
    script.with_name("restore-root-adapters.sh").write_text(
        render_restore_script(RESTORE_SRC.read_text(encoding="utf-8"))
    )


def _install_pull_runtime(root: Path) -> Path:
    """Install the state-sync pair at its real consumer path for restoration."""
    scripts = root / ".claude" / "hooks" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    state_sync = scripts / "state-sync.sh"
    shutil.copy(SCRIPT_SRC, state_sync)
    _install_restorer(state_sync)
    return state_sync


def _write_restore_manifest(root: Path, *paths: str) -> None:
    """Write the inert manifest format emitted by runtime_ownership.py."""
    manifest = root / ".claude" / "bootstrap-ownership.env"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        "# Generated from scripts/runtime_ownership.py.\n"
        + "".join(f"BOOTSTRAP_ROOT_PATH={path}\n" for path in paths)
    )


def _write_github_adapter_source(
    root: Path, content: str = "generated agent\n"
) -> Path:
    """Add one ignored directory adapter to the nested restoration mirror."""
    _write_restore_manifest(root, ".github/agents")
    agent = root / ".claude" / "bootstrap-root/.github/agents/coder.agent.md"
    agent.parent.mkdir(parents=True, exist_ok=True)
    agent.write_text(content, encoding="utf-8")
    return agent


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


ERROR_LOG_RELPATH = "session_logs/hooks-errors.log"


def _worktree_snapshot(root: Path) -> dict[str, bytes]:
    """Return every non-Git worktree file as a byte snapshot.

    The local error log is left out: a protected run appends one warning to it.
    """
    worktree = root / ".claude"
    return {
        path.relative_to(worktree).as_posix(): path.read_bytes()
        for path in sorted(worktree.rglob("*"))
        if path.is_file()
        and ".git" not in path.relative_to(worktree).parts
        and path.relative_to(worktree).as_posix() != ERROR_LOG_RELPATH
    }


def _error_log_lines(root: Path) -> list[str]:
    """Return the local error log's lines (empty when it does not exist)."""
    log = root / ".claude" / ERROR_LOG_RELPATH
    return log.read_text().splitlines() if log.exists() else []


def _appended_error_lines(root: Path, before: list[str]) -> list[str]:
    """Return the lines a run appended to the error log, never rewriting old ones."""
    after = _error_log_lines(root)
    assert after[: len(before)] == before
    return after[len(before) :]


def _recording_git(
    tmp_path: Path,
    *,
    fail: tuple[str, str] | None = None,
    delete_after_pull: Path | None = None,
) -> tuple[dict[str, str], Path]:
    """Return the environment for a fake ``git`` that logs each call, then runs real git.

    The log holds ``<subcommand> <first argument>`` per call and does not exist
    until a call is made. ``fail`` makes only that subcommand and first argument
    fail. ``delete_after_pull`` is removed right after a real ``git pull``, as Git
    removes the ignored local settings file while it replays commits around it.
    """
    real_git = shutil.which("git")
    assert real_git is not None
    fake_bin = tmp_path / "recording-bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    fake_git.write_text(
        r"""#!/usr/bin/env bash
printf "%s %s\n" "${3:-}" "${4:-}" >> "$GIT_INVOCATIONS"
if [[ "${3:-}" == "$FAIL_SUBCOMMAND" && "${4:-}" == "$FAIL_ARGUMENT" ]]; then
  printf 'forced %s %s failure\n' "$3" "$4" >&2
  exit 1
fi
"$REAL_GIT" "$@"
status=$?
if [[ "${3:-}" == "pull" && -n "$DELETE_AFTER_PULL" ]]; then
  rm -f "$DELETE_AFTER_PULL"
fi
exit "$status"
"""
    )
    fake_git.chmod(0o755)
    invocations = tmp_path / "recording-invocations.log"
    fail_subcommand, fail_argument = fail or ("-", "-")
    return {
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "REAL_GIT": real_git,
        "GIT_INVOCATIONS": str(invocations),
        "FAIL_SUBCOMMAND": fail_subcommand,
        "FAIL_ARGUMENT": fail_argument,
        "DELETE_AFTER_PULL": str(delete_after_pull or ""),
    }, invocations


def _logged_calls(invocations: Path, subcommand: str) -> list[str]:
    """Return the logged calls of one Git subcommand, in order."""
    return [
        line
        for line in invocations.read_text().splitlines()
        if line.startswith(f"{subcommand} ")
    ]


needs_flock = pytest.mark.skipif(
    shutil.which("flock") is None, reason="flock(1) is not installed"
)


@contextlib.contextmanager
def _sync_lock_held(root: Path) -> Iterator[Callable[[], None]]:
    """Hold the sync lock the way ``flock(1)`` takes it: ``flock(2)`` on a
    read-only descriptor of the repository root. Yields a function that
    releases it early; leaving the block releases it too."""
    fd = os.open(root, os.O_RDONLY)
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    released = False

    def release() -> None:
        nonlocal released
        if not released:
            released = True
            os.close(fd)

    try:
        yield release
    finally:
        release()


def _default_signal_handling() -> None:
    """Run in the child before exec: undo signals the launcher ignored (``nohup``,
    a backgrounded non-interactive shell). Bash cannot trap a signal that was
    ignored on entry, and an ignored disposition survives ``exec``."""
    for signum in (signal.SIGINT, signal.SIGHUP, signal.SIGTERM):
        signal.signal(signum, signal.SIG_DFL)


@contextlib.contextmanager
def _sync_process(
    script: Path,
    root: Path,
    remote: Path | None,
    mode: str,
    *args: str,
    extra_env: dict[str, str] | None = None,
) -> Iterator[subprocess.Popen[str]]:
    """Start one run in its own process group, as a hook runner would. Leaving
    the block kills the whole group if it is still running."""
    proc = subprocess.Popen(
        ["bash", str(script), mode, *args],
        text=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=_sync_env(root, remote, None, extra_env),
        start_new_session=True,
        preexec_fn=_default_signal_handling,
    )
    try:
        yield proc
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGKILL)
        proc.wait()
        for stream in (proc.stdout, proc.stderr):
            if stream is not None:
                stream.close()


def _wait_for_file(
    path: Path, proc: subprocess.Popen[str], limit: float = 30.0
) -> None:
    """Wait for ``path``, failing instead of hanging when the run ends first or
    ``limit`` seconds pass."""
    deadline = time.monotonic() + limit
    while not path.exists():
        assert proc.poll() is None, f"the run ended before {path.name} appeared"
        assert time.monotonic() < deadline, f"{path.name} not seen in {limit} s"
        time.sleep(0.05)


def _fake_git(tmp_path: Path, body: str) -> dict[str, str]:
    """Return the environment for a fake ``git`` that runs the bash ``body`` on
    every call and then real git (``$REAL_GIT``), unless ``body`` exits."""
    real_git = shutil.which("git")
    assert real_git is not None
    fake_bin = tmp_path / "fake-git-bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    fake_git.write_text(f'#!/usr/bin/env bash\n{body}\nexec "$REAL_GIT" "$@"\n')
    fake_git.chmod(0o755)
    return {"PATH": f"{fake_bin}:{os.environ['PATH']}", "REAL_GIT": real_git}


def _fake_flock(tmp_path: Path, body: str) -> dict[str, str]:
    """Return the environment for a fake ``flock`` that runs the bash ``body``."""
    fake_bin = tmp_path / "fake-flock-bin"
    fake_bin.mkdir()
    fake_flock = fake_bin / "flock"
    fake_flock.write_text(f"#!/usr/bin/env bash\n{body}\n")
    fake_flock.chmod(0o755)
    return {"PATH": f"{fake_bin}:{os.environ['PATH']}"}


@pytest.fixture(scope="module")
def path_without_flock(tmp_path_factory: pytest.TempPathFactory) -> dict[str, str]:
    """Return a ``PATH`` of symlinks to every program on the current ``PATH``
    except ``flock`` (built once: it links thousands of programs)."""
    bin_dir = tmp_path_factory.mktemp("no-flock-bin")
    for directory in os.environ["PATH"].split(os.pathsep):
        if not os.path.isdir(directory):
            continue
        for entry in os.scandir(directory):
            if (
                entry.name != "flock"
                and not entry.is_dir()
                and os.access(entry.path, os.X_OK)
                and not (bin_dir / entry.name).exists()
            ):
                (bin_dir / entry.name).symlink_to(entry.path)
    return {"PATH": str(bin_dir)}


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


def _diverged_branches(
    script: Path, tmp_path: Path, remote: Path, name: str
) -> tuple[Path, str]:
    """Create a writer whose ``ai-state`` and ``operator-work`` branches edit one
    file differently, with ``ai-state`` checked out and a clean tree."""
    writer = _new_writer(script, tmp_path, remote, name)
    nested = writer / ".claude"
    relpath = "plans/operator-merge.md"
    assert _git(nested, "config", "user.name", "Test").returncode == 0
    assert _git(nested, "config", "user.email", "test@example.com").returncode == 0
    _write(writer, relpath, "base\n")
    assert _sync(script, writer, remote, "push").returncode == 0
    assert _git(nested, "checkout", "-qb", "operator-work").returncode == 0
    _write(writer, relpath, "operator\n")
    assert _git(nested, "add", "-A").returncode == 0
    assert _git(nested, "commit", "-qm", "operator").returncode == 0
    assert _git(nested, "checkout", "-q", "ai-state").returncode == 0
    _write(writer, relpath, "sync\n")
    assert _git(nested, "add", "-A").returncode == 0
    assert _git(nested, "commit", "-qm", "sync").returncode == 0
    return writer, relpath


def _valid_preexisting_merge(
    script: Path, tmp_path: Path, remote: Path, name: str
) -> tuple[Path, str]:
    """Create a real conflicted merge that represents active operator work."""
    writer, relpath = _diverged_branches(script, tmp_path, remote, name)
    nested = writer / ".claude"
    assert _git(nested, "merge", "operator-work").returncode != 0
    assert (nested / ".git" / "MERGE_HEAD").is_file()
    stages = {
        line.split()[2] for line in _git(nested, "ls-files", "-u").stdout.splitlines()
    }
    assert stages == {"1", "2", "3"}
    return writer, relpath


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


def test_checkpoint_upgrades_gitignore_and_never_tracks_context_cache(
    script: Path, tmp_path: Path
) -> None:
    """Existing nested repos preserve user ignores and exclude derived cache."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "cache-ignore")
    gitignore = writer / ".claude/.gitignore"
    gitignore.write_text("user-sentinel/\n")
    cache_file = writer / ".claude/.cache/context-mode/content/index.db"
    cache_file.parent.mkdir(parents=True)
    cache_file.write_text("derived")
    _write(writer, "MEMORY.md", "tracked\n")

    result = _sync(script, writer, remote, "checkpoint")

    assert result.returncode == 0, result.stderr
    ignore_text = gitignore.read_text()
    assert "user-sentinel/" in ignore_text
    assert ignore_text.splitlines().count(".cache/") == 1
    assert _git(writer / ".claude", "ls-files", ".cache").stdout == ""

    second = _sync(script, writer, remote, "checkpoint")
    assert second.returncode == 0, second.stderr
    assert gitignore.read_text().splitlines().count(".cache/") == 1


def test_setup_upgrades_existing_nested_gitignore_without_overwriting_user_entries(
    script: Path, tmp_path: Path
) -> None:
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "setup-ignore")
    gitignore = writer / ".claude/.gitignore"
    gitignore.write_text("user-sentinel/\n")

    result = _sync(script, writer, remote, "setup")

    assert result.returncode == 0, result.stderr
    upgraded = gitignore.read_text()
    assert upgraded.splitlines() == [
        "user-sentinel/",
        "",
        "# Local client settings; never synced.",
        "settings.local.json",
        "",
        "# Derived local caches; never synced.",
        ".cache/",
        "",
        "# Local hook-runtime diagnostics only; never synced "
        "(session_logs/hooks-bypass.log stays tracked).",
        "session_logs/hooks-errors.log",
    ]

    second = _sync(script, writer, remote, "setup")
    assert second.returncode == 0, second.stderr
    assert gitignore.read_text() == upgraded


def test_setup_activates_the_outer_git_hooks_path(script: Path, tmp_path: Path) -> None:
    """A fresh setup activates the outer repository's checked-out Git hooks."""
    root = tmp_path / "hooks-path-consumer"
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / ".claude" / "hooks" / "git-hooks").mkdir(parents=True)

    result = _sync(script, root, None, "setup")

    assert result.returncode == 0, result.stderr
    assert _git(root, "config", "--get", "core.hooksPath").stdout.strip() == (
        ".claude/hooks/git-hooks"
    )


def test_repeated_setup_does_not_rewrite_a_matching_hooks_path(
    script: Path, tmp_path: Path
) -> None:
    """An already-active hooks path is left alone, without a spurious warning."""
    root = tmp_path / "hooks-path-repeat"
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / ".claude" / "hooks" / "git-hooks").mkdir(parents=True)
    assert _sync(script, root, None, "setup").returncode == 0

    result = _sync(script, root, None, "setup")

    assert result.returncode == 0, result.stderr
    assert "core.hooksPath was" not in result.stderr
    assert _git(root, "config", "--get", "core.hooksPath").stdout.strip() == (
        ".claude/hooks/git-hooks"
    )


def test_setup_overwrites_a_different_pre_existing_hooks_path_with_a_warning(
    script: Path, tmp_path: Path
) -> None:
    """A deliberately different pre-existing value is overwritten, and the
    warning names the old value so the override stays visible."""
    root = tmp_path / "hooks-path-override"
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / ".claude" / "hooks" / "git-hooks").mkdir(parents=True)
    assert _git(root, "config", "core.hooksPath", "some/other/hooks").returncode == 0

    result = _sync(script, root, None, "setup")

    assert result.returncode == 0, result.stderr
    assert (
        "core.hooksPath was some/other/hooks; replaced it with "
        ".claude/hooks/git-hooks" in result.stderr
    )
    assert _git(root, "config", "--get", "core.hooksPath").stdout.strip() == (
        ".claude/hooks/git-hooks"
    )


def test_pull_activates_the_outer_hooks_path_for_a_writer_arriving_from_remote(
    script: Path, tmp_path: Path
) -> None:
    """A writer whose ``.claude/`` arrives entirely from ``origin/ai-state``
    still gets the outer Git hooks path activated on its first pull."""
    remote = _bare_remote(tmp_path)
    publisher = _new_writer(script, tmp_path, remote, "hooks-path-publisher")
    hooks_dir = publisher / ".claude" / "hooks" / "git-hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "post-commit").write_text("#!/usr/bin/env bash\nexit 0\n")
    assert _sync(script, publisher, remote, "push").returncode == 0

    writer = tmp_path / "hooks-path-writer"
    subprocess.run(["git", "init", "-q", str(writer)], check=True)

    result = _sync(script, writer, remote, "pull")

    assert result.returncode == 0, result.stderr
    assert (writer / ".claude" / "hooks" / "git-hooks" / "post-commit").exists()
    assert _git(writer, "config", "--get", "core.hooksPath").stdout.strip() == (
        ".claude/hooks/git-hooks"
    )


def test_setup_skips_hooks_path_when_outer_root_is_not_a_git_repository(
    script: Path, tmp_path: Path
) -> None:
    """A consumer root with no outer ``.git`` is not a hard failure; the
    hooks-path step is silently skipped and the rest of setup still succeeds."""
    root = tmp_path / "not-a-repository"
    (root / ".claude" / "hooks" / "git-hooks").mkdir(parents=True)

    result = _sync(script, root, None, "setup")

    assert result.returncode == 0, result.stderr
    assert "no state remote configured" in result.stderr


def test_checkpoint_untracks_previously_committed_error_log_without_deleting_it(
    script: Path, tmp_path: Path
) -> None:
    """Upgrade removes the local-only error log from history while preserving
    it on disk; ``session_logs/hooks-bypass.log`` stays a separate, tracked
    file (unaffected by this)."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "tracked-error-log")
    error_log = writer / ".claude" / "session_logs" / "hooks-errors.log"
    error_log.parent.mkdir(parents=True, exist_ok=True)
    error_log.write_text("legacy tracked error\n")
    assert (
        _git(
            writer / ".claude", "add", "-f", "session_logs/hooks-errors.log"
        ).returncode
        == 0
    )
    assert (
        _git(writer / ".claude", "commit", "-qm", "legacy tracked error log").returncode
        == 0
    )
    assert _git(writer / ".claude", "push", "-q").returncode == 0
    assert (
        _remote_show(remote, "session_logs/hooks-errors.log")
        == "legacy tracked error\n"
    )

    result = _sync(script, writer, remote, "checkpoint")

    assert result.returncode == 0, result.stderr
    assert error_log.read_text() == "legacy tracked error\n"
    assert (
        _git(writer / ".claude", "ls-files", "session_logs/hooks-errors.log").stdout
        == ""
    )
    assert _git(writer / ".claude", "status", "--porcelain").stdout == ""
    assert _sync(script, writer, remote, "publish").returncode == 0
    assert _remote_show(remote, "session_logs/hooks-errors.log") == ""


def test_setup_never_tracks_the_error_log(script: Path, tmp_path: Path) -> None:
    """A brand-new nested repository never commits the local-only error log."""
    remote = _bare_remote(tmp_path)
    writer = tmp_path / "fresh-error-log"
    error_log = writer / ".claude" / "session_logs" / "hooks-errors.log"
    error_log.parent.mkdir(parents=True, exist_ok=True)
    error_log.write_text("local-only\n")

    result = _sync(script, writer, remote, "setup")

    assert result.returncode == 0, result.stderr
    assert error_log.read_text() == "local-only\n"
    assert (
        _git(writer / ".claude", "ls-files", "session_logs/hooks-errors.log").stdout
        == ""
    )


def test_checkpoint_untracks_previously_committed_cache_without_deleting_it(
    script: Path, tmp_path: Path
) -> None:
    """Upgrade removes cache from history while preserving local cache bytes."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "tracked-cache")
    cache_file = writer / ".claude/.cache/context-mode/content/index.db"
    cache_file.parent.mkdir(parents=True)
    cache_file.write_text("local-derived-data")
    assert (
        _git(
            writer / ".claude", "add", "-f", ".cache/context-mode/content/index.db"
        ).returncode
        == 0
    )
    assert (
        _git(writer / ".claude", "commit", "-qm", "legacy tracked cache").returncode
        == 0
    )
    assert _git(writer / ".claude", "push", "-q").returncode == 0
    assert (
        _remote_show(remote, ".cache/context-mode/content/index.db")
        == "local-derived-data"
    )

    result = _sync(script, writer, remote, "checkpoint")

    assert result.returncode == 0, result.stderr
    assert cache_file.read_text() == "local-derived-data"
    assert _git(writer / ".claude", "ls-files", ".cache").stdout == ""
    assert _sync(script, writer, remote, "publish").returncode == 0
    assert _remote_show(remote, ".cache/context-mode/content/index.db") == ""


@pytest.mark.parametrize("reconcile_shape", ["unrelated", "common-history"])
def test_remote_tracked_cache_is_untracked_after_every_successful_reconcile(
    script: Path, tmp_path: Path, reconcile_shape: str
) -> None:
    """A remote cache survives locally but cannot remain tracked or republish."""
    remote = _bare_remote(tmp_path)
    writer_a = _new_writer(script, tmp_path, remote, "remote-cache-a")
    writer_b = None
    if reconcile_shape == "common-history":
        writer_b = _new_writer(script, tmp_path, remote, "remote-cache-b")

    cache_rel = ".cache/context-mode/content/remote.db"
    cache_a = writer_a / ".claude" / cache_rel
    cache_a.parent.mkdir(parents=True)
    cache_a.write_text("remote-derived-data")
    assert _git(writer_a / ".claude", "add", "-f", cache_rel).returncode == 0
    assert (
        _git(writer_a / ".claude", "commit", "-qm", "hostile remote cache").returncode
        == 0
    )
    assert _git(writer_a / ".claude", "push", "-q").returncode == 0

    if writer_b is None:
        writer_b = _new_writer(script, tmp_path, remote, "remote-cache-b")
    else:
        result = _sync(script, writer_b, remote, "pull")
        assert result.returncode == 0, result.stderr

    cache_b = writer_b / ".claude" / cache_rel
    assert cache_b.read_text() == "remote-derived-data"
    assert _git(writer_b / ".claude", "ls-files", ".cache").stdout == ""
    assert _sync(script, writer_b, remote, "publish").returncode == 0
    assert _remote_show(remote, cache_rel) == ""


SETTINGS_LOCAL = "settings.local.json"


def _commit_tracked_settings(writer: Path, content: str, *, push: bool = False) -> None:
    """Track ``settings.local.json`` the way an install from before the
    untrack change did (a forced add: the nested ``.gitignore`` lists it)."""
    _write(writer, SETTINGS_LOCAL, content)
    nested = writer / ".claude"
    assert _git(nested, "add", "-f", SETTINGS_LOCAL).returncode == 0
    commit = _git(
        nested,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-qm",
        "legacy tracked local settings",
    )
    assert commit.returncode == 0, commit.stderr
    if push:
        assert _git(nested, "push", "-q").returncode == 0


def test_checkpoint_untracks_previously_committed_local_settings_without_deleting_it(
    script: Path, tmp_path: Path
) -> None:
    """GR-008: the nested index stops tracking ``settings.local.json`` while
    the local file keeps its exact bytes (including CRLF and non-ASCII). The
    nested ``.gitignore`` is also left byte for byte: the file is still tracked
    when the ignore rules are checked, and only ``--no-index`` makes git judge
    the rules instead of reporting a tracked path as not ignored."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "tracked-local-settings")
    nested = writer / ".claude"
    _commit_tracked_settings(writer, '{"committed": true}\n', push=True)
    assert _remote_show(remote, SETTINGS_LOCAL) == '{"committed": true}\n'
    local = nested / SETTINGS_LOCAL
    local.write_bytes('{"local": "edited é"}\r\n'.encode())
    before = local.read_bytes()
    gitignore_before = (nested / ".gitignore").read_bytes()

    result = _sync(script, writer, remote, "checkpoint")

    assert result.returncode == 0, result.stderr
    assert (nested / ".gitignore").read_bytes() == gitignore_before
    assert local.read_bytes() == before
    assert _git(nested, "ls-files", SETTINGS_LOCAL).stdout == ""
    assert _git(nested, "status", "--porcelain").stdout == ""
    assert _sync(script, writer, remote, "publish").returncode == 0
    assert _remote_show(remote, SETTINGS_LOCAL) == ""


@pytest.mark.parametrize(
    "user_text",
    ["user-sentinel/\n", "settings.local.json\n!settings.local.json\n"],
    ids=["line-missing", "line-negated"],
)
def test_checkpoint_keeps_local_settings_out_of_a_gitignore_that_stopped_ignoring_them(
    script: Path, tmp_path: Path, user_text: str
) -> None:
    """BF-B1: a refresh now keeps the nested ``.gitignore`` as the consumer left
    it, so state sync must not let ``git add -A`` commit local settings when
    that copy lacks the line or a later line negates it. User text is kept and
    a repeat run adds nothing."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "settings-unignored")
    nested = writer / ".claude"
    gitignore = nested / ".gitignore"
    gitignore.write_text(user_text)
    _write(writer, SETTINGS_LOCAL, '{"local": true}\n')

    result = _sync(script, writer, remote, "checkpoint")

    assert result.returncode == 0, result.stderr
    assert gitignore.read_text().startswith(user_text)
    ignored = _git(nested, "check-ignore", "-q", "--no-index", SETTINGS_LOCAL)
    assert ignored.returncode == 0
    assert _git(nested, "ls-files", SETTINGS_LOCAL).stdout == ""
    assert (nested / SETTINGS_LOCAL).read_text() == '{"local": true}\n'

    first = gitignore.read_text()
    assert _sync(script, writer, remote, "checkpoint").returncode == 0
    assert gitignore.read_text() == first


def test_setup_adds_nothing_to_gitignore_while_git_cannot_read_the_nested_repo(
    script: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``git check-ignore`` exits 128, not 1, when the nested repository is
    broken. That is a git failure, not "not ignored", so state sync must not
    append a ``settings.local.json`` block on every run while it lasts."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "broken-nested-repo")
    nested = writer / ".claude"
    gitignore = nested / ".gitignore"
    # Every other guard line is present, so only the settings line could change it.
    gitignore.write_text("user-sentinel/\n.cache/\nsession_logs/hooks-errors.log\n")
    (nested / ".git" / "HEAD").write_text("not a valid HEAD\n")
    # The ceiling keeps git from finding a repository above the temp folder.
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    broken = _git(nested, "check-ignore", "-q", "--no-index", SETTINGS_LOCAL)
    assert broken.returncode == 128

    for _ in range(2):
        _sync(script, writer, remote, "setup")
        assert gitignore.read_text() == (
            "user-sentinel/\n.cache/\nsession_logs/hooks-errors.log\n"
        )


UNION_RULE = "session_logs/*.log merge=union"


def _nested_without_gitattributes(script: Path, tmp_path: Path, name: str) -> Path:
    """Return a writer whose nested ``HEAD`` lacks ``.gitattributes``.

    That matches a nested repository created before the file was written for
    existing repositories too.
    """
    writer = _new_writer(script, tmp_path, _bare_remote(tmp_path), name)
    nested = writer / ".claude"
    assert _git(nested, "rm", "-q", ".gitattributes").returncode == 0
    commit = _git(
        nested,
        "-c",
        "user.name=Test",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-qm",
        "drop attributes",
    )
    assert commit.returncode == 0, commit.stderr
    assert not (nested / ".gitattributes").exists()
    return writer


@pytest.mark.parametrize("mode", ["setup", "checkpoint"])
def test_existing_nested_repo_without_gitattributes_gains_the_union_rule(
    script: Path, tmp_path: Path, mode: str
) -> None:
    """BF-B2: setup and checkpoint write the file once, and it ends up tracked."""
    writer = _nested_without_gitattributes(script, tmp_path, f"attrs-{mode}")
    nested = writer / ".claude"
    attributes = nested / ".gitattributes"

    result = _sync(script, writer, None, mode)

    assert result.returncode == 0, result.stderr
    assert attributes.read_text().splitlines().count(UNION_RULE) == 1

    # Setup is local-only and commits nothing; a checkpoint tracks the file.
    assert _sync(script, writer, None, "checkpoint").returncode == 0
    assert _git(nested, "ls-files", "--error-unmatch", ".gitattributes").returncode == 0
    assert attributes.read_text().splitlines().count(UNION_RULE) == 1
    assert _git(nested, "status", "--porcelain").stdout == ""


def test_existing_gitattributes_keeps_user_lines_and_gains_the_union_rule_once(
    script: Path, tmp_path: Path
) -> None:
    """BF-B2: a user line without a trailing newline survives the append, and
    repeat runs of every entry point change neither the file nor history."""
    writer = _nested_without_gitattributes(script, tmp_path, "attrs-user-line")
    nested = writer / ".claude"
    attributes = nested / ".gitattributes"
    attributes.write_text("*.md -diff")

    assert _sync(script, writer, None, "setup").returncode == 0

    lines = attributes.read_text().splitlines()
    assert lines[0] == "*.md -diff"
    assert lines.count(UNION_RULE) == 1

    assert _sync(script, writer, None, "checkpoint").returncode == 0
    settled = attributes.read_bytes()
    head = _local_head(writer)
    for mode in ("setup", "checkpoint", "setup"):
        assert _sync(script, writer, None, mode).returncode == 0
    assert attributes.read_bytes() == settled
    assert _local_head(writer) == head


def test_second_clone_keeps_its_local_settings_when_it_pulls_the_untrack_commit(
    script: Path, tmp_path: Path
) -> None:
    """GR-008 data-loss guard. Clone B has an unpushed commit that still
    tracks ``settings.local.json`` and a newer local edit; clone A publishes
    the untrack commit. Replaying B's commits through trees that track and
    then untrack the file makes git delete B's working copy. The control
    clone proves that, so the assertion below is not vacuous."""
    remote = _bare_remote(tmp_path)
    clone_a = _new_writer(script, tmp_path, remote, "settings-a")
    _commit_tracked_settings(clone_a, "from-A\n", push=True)
    clone_b = _new_writer(script, tmp_path, remote, "settings-b")
    nested_b = clone_b / ".claude"
    _commit_tracked_settings(clone_b, "B-committed\n")
    local_b = nested_b / SETTINGS_LOCAL
    local_b.write_bytes(b"B-local-final\r\n")
    assert _sync(script, clone_a, remote, "push").returncode == 0
    assert _remote_show(remote, SETTINGS_LOCAL) == ""

    # Control: the same git steps the script runs, minus the preserved copy.
    control = tmp_path / "settings-b-control"
    shutil.copytree(clone_b, control, symlinks=True)
    identity = ("-c", "user.name=Test", "-c", "user.email=test@example.com")
    nested_control = control / ".claude"
    assert (
        _git(
            nested_control, "rm", "-f", "-q", "--cached", "--", SETTINGS_LOCAL
        ).returncode
        == 0
    )
    assert _git(nested_control, *identity, "commit", "-qm", "untrack").returncode == 0
    _git(nested_control, *identity, "pull", "--rebase", "origin", "ai-state")
    assert not (nested_control / SETTINGS_LOCAL).exists(), (
        "fixture must reach git's deletion path"
    )

    result = _sync(script, clone_b, remote, "pull")

    assert local_b.read_bytes() == b"B-local-final\r\n", result.stderr
    assert "restored local settings.local.json" in result.stderr
    assert _git(nested_b, "ls-files", SETTINGS_LOCAL).stdout == ""
    assert _no_active_rebase_or_merge(clone_b)
    assert list((nested_b / ".git").glob("settings.local.json.*")) == []
    assert _sync(script, clone_b, remote, "publish").returncode == 0
    assert _remote_show(remote, SETTINGS_LOCAL) == ""


def test_conflicted_pull_keeps_the_local_settings_it_aborts_around(
    script: Path, tmp_path: Path
) -> None:
    """GR-008: when the pull aborts on a real conflict, the rebase has already
    replayed B's commit that tracked the file, so the abort must still leave
    B's own bytes in place."""
    remote = _bare_remote(tmp_path)
    clone_a = _new_writer(script, tmp_path, remote, "conflict-settings-a")
    _write(clone_a, "plans/x.md", "base\n")
    _commit_tracked_settings(clone_a, "from-A\n")
    assert _sync(script, clone_a, remote, "push").returncode == 0
    clone_b = _new_writer(script, tmp_path, remote, "conflict-settings-b")
    nested_b = clone_b / ".claude"
    _commit_tracked_settings(clone_b, "B-committed\n")
    _write(clone_b, "plans/x.md", "from-B\n")
    assert _git(nested_b, "add", "plans/x.md").returncode == 0
    assert (
        _git(
            nested_b,
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-qm",
            "B edits the plan",
        ).returncode
        == 0
    )
    local_b = nested_b / SETTINGS_LOCAL
    local_b.write_bytes(b"B-local-final\n")
    _write(clone_a, "plans/x.md", "from-A\n")
    assert _sync(script, clone_a, remote, "push").returncode == 0

    result = _sync(script, clone_b, remote, "pull")

    assert "reconciliation with origin/ai-state failed" in result.stderr
    assert local_b.read_bytes() == b"B-local-final\n"
    assert _no_active_rebase_or_merge(clone_b)
    assert list((nested_b / ".git").glob("settings.local.json.*")) == []


def test_conflicted_merge_keeps_the_local_settings_it_aborts_around(
    script: Path, tmp_path: Path
) -> None:
    """GR-008: an unrelated-history merge that conflicts is aborted. The merge
    had already written the remote's copy of the file, so the abort path must
    put B's own bytes back too."""
    remote = _bare_remote(tmp_path)
    clone_a = _new_writer(script, tmp_path, remote, "merge-conflict-a")
    _write(clone_a, "plans/x.md", "from-A\n")
    assert _git(clone_a / ".claude", "add", "plans/x.md").returncode == 0
    _commit_tracked_settings(clone_a, "from-A\n", push=True)
    clone_b = tmp_path / "merge-conflict-b"
    _write(clone_b, "plans/x.md", "from-B\n")
    local_b = clone_b / ".claude" / SETTINGS_LOCAL
    local_b.write_bytes(b"B-fresh\n")

    result = _sync(script, clone_b, remote, "setup")

    assert "could not be merged automatically" in result.stderr
    assert local_b.read_bytes() == b"B-fresh\n"
    assert _no_active_rebase_or_merge(clone_b)
    assert list((clone_b / ".claude" / ".git").glob("settings.local.json.*")) == []


def test_fresh_clone_keeps_its_local_settings_when_origin_still_tracks_them(
    script: Path, tmp_path: Path
) -> None:
    """GR-008 data-loss guard for the unrelated-history merge: origin's tip
    still tracks the file, and the merge would replace the fresh clone's own
    bytes with the remote's."""
    remote = _bare_remote(tmp_path)
    clone_a = _new_writer(script, tmp_path, remote, "fresh-settings-a")
    _commit_tracked_settings(clone_a, "from-A\n", push=True)
    assert _remote_show(remote, SETTINGS_LOCAL) == "from-A\n"
    clone_b = tmp_path / "fresh-settings-b"
    # A tracked file only B has keeps B's first commit different from A's, so
    # the histories stay unrelated and the merge path runs every time.
    _write(clone_b, "plans/b-only.md", "B\n")
    local_b = clone_b / ".claude" / SETTINGS_LOCAL
    local_b.write_bytes(b"B-fresh\r\n")

    result = _sync(script, clone_b, remote, "setup")

    assert result.returncode == 0, result.stderr
    assert local_b.read_bytes() == b"B-fresh\r\n"
    assert "restored local settings.local.json" in result.stderr
    assert _git(clone_b / ".claude", "ls-files", SETTINGS_LOCAL).stdout == ""
    assert list((clone_b / ".claude" / ".git").glob("settings.local.json.*")) == []


@pytest.mark.parametrize("shape", ["unrelated", "common-history"])
def test_reconciliation_is_skipped_when_local_settings_cannot_be_preserved(
    script: Path, tmp_path: Path, shape: str
) -> None:
    """If the byte copy cannot be made, git is not allowed to touch the tree:
    no merge or rebase runs, and the file keeps its bytes."""
    remote = _bare_remote(tmp_path)
    clone_a = _new_writer(script, tmp_path, remote, f"unsafe-a-{shape}")
    _write(clone_a, "plans/from-a.md", "A\n")
    assert _sync(script, clone_a, remote, "push").returncode == 0
    if shape == "common-history":
        clone_b = _new_writer(script, tmp_path, remote, f"unsafe-b-{shape}")
        _write(clone_a, "plans/second-from-a.md", "A2\n")
        assert _sync(script, clone_a, remote, "push").returncode == 0
        expected_missing = "plans/second-from-a.md"
    else:
        clone_b = tmp_path / f"unsafe-b-{shape}"
        _write(clone_b, "plans/b-only.md", "B\n")
        expected_missing = "plans/from-a.md"
    local_b = clone_b / ".claude" / SETTINGS_LOCAL
    local_b.write_bytes(b"B-only\n")
    fake_bin = tmp_path / f"failing-cp-{shape}"
    fake_bin.mkdir()
    (fake_bin / "cp").write_text("#!/usr/bin/env bash\nexit 1\n")
    (fake_bin / "cp").chmod(0o755)

    result = _sync(
        script,
        clone_b,
        remote,
        "setup" if shape == "unrelated" else "pull",
        extra_env={"PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )

    assert "could not keep a copy of local settings.local.json" in result.stderr
    assert local_b.read_bytes() == b"B-only\n"
    assert not (clone_b / ".claude" / expected_missing).exists()
    assert _no_active_rebase_or_merge(clone_b)


def _concurrent_settings_write(
    tmp_path: Path, git_command: str, target: Path, content: str
) -> dict[str, str]:
    """Environment whose `git` writes ``content`` to ``target`` right after the
    real ``git <git_command>`` finishes: a stand-in for Claude Code or another
    session saving ``settings.local.json`` while state sync is running."""
    real_git = shutil.which("git")
    assert real_git is not None
    fake_bin = tmp_path / f"concurrent-write-{git_command}-bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    fake_git.write_text(
        "#!/usr/bin/env bash\n"
        '"$REAL_GIT" "$@"\n'
        "status=$?\n"
        'if [[ "${3:-}" == "$CONCURRENT_AFTER" ]]; then\n'
        '  printf "%s" "$CONCURRENT_CONTENT" > "$CONCURRENT_TARGET"\n'
        "fi\n"
        'exit "$status"\n'
    )
    fake_git.chmod(0o755)
    return {
        "PATH": f"{fake_bin}:{os.environ['PATH']}",
        "REAL_GIT": real_git,
        "CONCURRENT_AFTER": git_command,
        "CONCURRENT_TARGET": str(target),
        "CONCURRENT_CONTENT": content,
    }


def test_pull_keeps_a_settings_write_made_while_it_ran(
    script: Path, tmp_path: Path
) -> None:
    """A write that lands after git deleted the file is newer than the byte
    copy, so it is kept and the copy stays for manual recovery."""
    remote = _bare_remote(tmp_path)
    clone_a = _new_writer(script, tmp_path, remote, "concurrent-pull-a")
    _commit_tracked_settings(clone_a, "from-A\n", push=True)
    clone_b = _new_writer(script, tmp_path, remote, "concurrent-pull-b")
    nested_b = clone_b / ".claude"
    _commit_tracked_settings(clone_b, "B-committed\n")
    local_b = nested_b / SETTINGS_LOCAL
    local_b.write_bytes(b"B-local-final\r\n")
    assert _sync(script, clone_a, remote, "push").returncode == 0

    result = _sync(
        script,
        clone_b,
        remote,
        "pull",
        extra_env=_concurrent_settings_write(
            tmp_path, "pull", local_b, '{"approved": "Bash(ls)"}\n'
        ),
    )

    assert local_b.read_bytes() == b'{"approved": "Bash(ls)"}\n', result.stderr
    backups = list((nested_b / ".git").glob("settings.local.json.*"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b"B-local-final\r\n"
    assert f"kept at {backups[0]}" in result.stderr
    assert "written while state sync ran" in result.stderr
    assert "restored local settings.local.json" not in result.stderr
    assert _git(nested_b, "ls-files", SETTINGS_LOCAL).stdout == ""
    assert _no_active_rebase_or_merge(clone_b)


def test_merge_keeps_a_settings_write_made_while_it_ran(
    script: Path, tmp_path: Path
) -> None:
    """Same rule for the unrelated-history merge: after git wrote origin's
    copy, newer bytes that are not that copy are kept, not reverted."""
    remote = _bare_remote(tmp_path)
    clone_a = _new_writer(script, tmp_path, remote, "concurrent-merge-a")
    _commit_tracked_settings(clone_a, "from-A\n", push=True)
    clone_b = tmp_path / "concurrent-merge-b"
    _write(clone_b, "plans/b-only.md", "B\n")
    nested_b = clone_b / ".claude"
    local_b = nested_b / SETTINGS_LOCAL
    local_b.write_bytes(b"B-fresh\r\n")

    result = _sync(
        script,
        clone_b,
        remote,
        "setup",
        extra_env=_concurrent_settings_write(
            tmp_path, "merge", local_b, '{"approved": "Bash(ls)"}\n'
        ),
    )

    assert local_b.read_bytes() == b'{"approved": "Bash(ls)"}\n', result.stderr
    backups = list((nested_b / ".git").glob("settings.local.json.*"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == b"B-fresh\r\n"
    assert "written while state sync ran" in result.stderr
    assert _git(nested_b, "ls-files", SETTINGS_LOCAL).stdout == ""


def test_pull_that_leaves_the_settings_file_alone_removes_its_byte_copy(
    script: Path, tmp_path: Path
) -> None:
    remote = _bare_remote(tmp_path)
    clone_a = _new_writer(script, tmp_path, remote, "untouched-a")
    clone_b = _new_writer(script, tmp_path, remote, "untouched-b")
    nested_b = clone_b / ".claude"
    local_b = nested_b / SETTINGS_LOCAL
    local_b.write_bytes(b"B-local\r\n")
    _write(clone_a, "plans/from-a.md", "A\n")
    assert _sync(script, clone_a, remote, "push").returncode == 0

    result = _sync(script, clone_b, remote, "pull")

    assert (nested_b / "plans" / "from-a.md").read_text() == "A\n"
    assert local_b.read_bytes() == b"B-local\r\n"
    assert list((nested_b / ".git").glob("settings.local.json.*")) == []
    assert "settings.local.json" not in result.stderr


def _install_dispatcher(root: Path) -> Path:
    """Copy the real context-mode dispatcher into a writer's ``.claude/``."""
    scripts = root / ".claude" / "hooks" / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    dispatcher = scripts / "context-mode-dispatch.sh"
    shutil.copy(DISPATCH_SRC, dispatcher)
    return dispatcher


def test_hostile_remote_cache_with_forged_marker_is_quarantined_not_trusted(
    script: Path, tmp_path: Path
) -> None:
    """A hostile/compromised ai-state remote can restore a poisoned cache
    directory together with a forged plaintext provenance marker (correct,
    guessable repository/version/filter fields), but it can never learn the
    local-only secret the dispatcher also requires. The restored cache must
    be quarantined, never trusted or searched live."""
    remote = _bare_remote(tmp_path)
    writer_a = _new_writer(script, tmp_path, remote, "hostile-cache-a")
    writer_b_root = tmp_path / "hostile-cache-b"

    cache_root_rel = ".cache/context-mode"
    poisoned_rel = f"{cache_root_rel}/content/remote.db"
    marker_rel = f"{cache_root_rel}/.bootstrap-provenance"

    poisoned = writer_a / ".claude" / poisoned_rel
    poisoned.parent.mkdir(parents=True)
    poisoned.write_text("poisoned-cache-bytes")
    marker = writer_a / ".claude" / marker_rel
    marker.write_text(
        f"repository={writer_b_root.resolve()}\n"
        "context-mode=1.0.169\n"
        "filter=ctx-index-file-content-v1\n"
        "secret=guessed-by-attacker\n"
    )
    assert (
        _git(writer_a / ".claude", "add", "-f", poisoned_rel, marker_rel).returncode
        == 0
    )
    assert (
        _git(
            writer_a / ".claude", "commit", "-qm", "hostile cache + forged marker"
        ).returncode
        == 0
    )
    assert _git(writer_a / ".claude", "push", "-q").returncode == 0

    writer_b = _new_writer(script, tmp_path, remote, "hostile-cache-b")
    cache_root = writer_b / ".claude" / cache_root_rel
    assert (cache_root / "content" / "remote.db").read_text() == "poisoned-cache-bytes"
    assert _git(writer_b / ".claude", "ls-files", ".cache").stdout == ""

    dispatcher = _install_dispatcher(writer_b)
    result = subprocess.run(
        ["bash", str(dispatcher), "claude-code", "sessionstart"],
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 0, result.stderr

    # The poisoned bytes must never become the live, searchable cache...
    assert not (cache_root / "content" / "remote.db").exists()
    # ...they must survive only inside a quarantined sibling directory...
    quarantines = list(
        (writer_b / ".claude" / ".cache").glob("context-mode.untrusted.*")
    )
    assert len(quarantines) == 1
    assert (
        quarantines[0] / "content" / "remote.db"
    ).read_text() == "poisoned-cache-bytes"
    # ...and the freshly (re)created marker must not carry the attacker's guess.
    fresh_marker = (cache_root / ".bootstrap-provenance").read_text()
    assert "secret=guessed-by-attacker" not in fresh_marker
    assert "secret=" in fresh_marker


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


def test_setup_existing_nested_repo_does_not_checkpoint_pending_state(
    script: Path, tmp_path: Path
) -> None:
    """Standalone setup leaves a caller's pending nested state for its own commit."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "existing-setup")
    before_head = _local_head(writer)
    _write(writer, "plans/pending-bootstrap.md", "await installer commit\n")

    result = _sync(script, writer, remote, "setup")

    assert result.returncode == 0, result.stderr
    assert _local_head(writer) == before_head
    assert "?? plans/" in _git(writer / ".claude", "status", "--porcelain").stdout


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


def test_pull_absorbs_log_churn_without_creating_rebase_state(
    script: Path, tmp_path: Path
) -> None:
    """Pull checkpoints log churn written after the former caller boundary."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "log-churn")
    assert _sync(script, writer, remote, "push").returncode == 0
    before_count = _local_commit_count(writer)
    actual_git = shutil.which("git")
    assert actual_git is not None
    fake_bin = tmp_path / "log-churn-bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    invocations = tmp_path / "log-churn-invocations.log"
    fake_git.write_text(
        "#!/usr/bin/env bash\n"
        'if [[ "${3:-}" == "merge-base" && ! -e "$LOG_CHURN_WRITTEN" ]]; then\n'
        '  : > "$LOG_CHURN_WRITTEN"\n'
        '  mkdir -p "$2/session_logs"\n'
        '  printf "post-old-checkpoint churn\\n" >> "$2/session_logs/phase-b-churn.log"\n'
        "  printf 'log-churn-written\\n' >> \"$GIT_INVOCATIONS\"\n"
        "fi\n"
        'if [[ "${3:-}" == "commit" ]]; then\n'
        "  printf 'phase-b-churn-checkpoint-commit\\n' >> \"$GIT_INVOCATIONS\"\n"
        "fi\n"
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
            "LOG_CHURN_WRITTEN": str(tmp_path / "log-churn-written"),
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
        },
    )

    invocation_lines = invocations.read_text().splitlines()
    churn_index = invocation_lines.index("log-churn-written")
    assert result.returncode == 0
    assert result.stdout == ""
    assert (
        _local_show(writer, "session_logs/phase-b-churn.log")
        == "post-old-checkpoint churn\n"
    )
    assert _local_commit_count(writer) == before_count + 1
    assert invocation_lines.index("phase-b-churn-checkpoint-commit") > churn_index
    assert not (writer / ".claude" / ".git" / "rebase-merge").exists()
    assert not (writer / ".claude" / ".git" / "rebase-apply").exists()


def test_reconcile_repins_wildcard_fetch_refspec(script: Path, tmp_path: Path) -> None:
    """Every reconciliation repairs a legacy wildcard fetch refspec."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "refspec-repair")
    assert _sync(script, writer, remote, "push").returncode == 0
    nested = writer / ".claude"
    assert (
        _git(
            nested,
            "config",
            "remote.origin.fetch",
            "+refs/heads/*:refs/remotes/origin/*",
        ).returncode
        == 0
    )

    result = _sync(script, writer, remote, "pull")

    assert result.returncode == 0
    assert _git(
        nested, "config", "--get-all", "remote.origin.fetch"
    ).stdout.splitlines() == ["+refs/heads/ai-state:refs/remotes/origin/ai-state"]
    assert _git(
        nested, "config", "--get-all", "remote.origin.push"
    ).stdout.splitlines() == ["refs/heads/ai-state:refs/heads/ai-state"]


@pytest.mark.parametrize("refspec", ("remote.origin.fetch", "remote.origin.push"))
def test_refspec_write_failure_skips_remote_reconciliation(
    script: Path, tmp_path: Path, refspec: str
) -> None:
    """A failed pin write warns publicly without attempting pull or push."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(
        script, tmp_path, remote, f"refspec-failure-{refspec.rsplit('.', 1)[1]}"
    )
    assert _sync(script, writer, remote, "push").returncode == 0
    actual_git = shutil.which("git")
    assert actual_git is not None
    fake_bin = tmp_path / "refspec-failure-bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    invocations = tmp_path / "refspec-failure-invocations.log"
    fake_git.write_text(
        "#!/usr/bin/env bash\n"
        'printf "%s %s %s\\n" "${3:-}" "${4:-}" "${5:-}" >> "$GIT_INVOCATIONS"\n'
        'if [[ "${3:-}" == "config" && "${4:-}" == "--replace-all" && "${5:-}" == "$FAIL_REFSPEC" ]]; then\n'
        '  printf "forced refspec write failure\\n" >&2\n'
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
            "FAIL_REFSPEC": refspec,
            "GIT_INVOCATIONS": str(invocations),
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
        },
    )

    commands = [
        line.split(maxsplit=1)[0] for line in invocations.read_text().splitlines()
    ]
    assert result.returncode == 0
    assert result.stdout == ""
    assert "configuring pinned origin refspecs failed" in result.stderr
    assert "pull: up to date" not in result.stderr
    assert "pull" not in commands
    assert "push" not in commands


@pytest.mark.parametrize("failed_command", ("add", "commit"))
def test_checkpoint_failure_skips_publication(
    script: Path, tmp_path: Path, failed_command: str
) -> None:
    """A failed local checkpoint warns publicly without remote publication."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(
        script, tmp_path, remote, f"checkpoint-failure-{failed_command}"
    )
    _write(writer, "session_logs/checkpoint-failure.log", "must stay local\n")
    actual_git = shutil.which("git")
    assert actual_git is not None
    fake_bin = tmp_path / "checkpoint-failure-bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    invocations = tmp_path / "checkpoint-failure-invocations.log"
    fake_git.write_text(
        "#!/usr/bin/env bash\n"
        'printf "%s %s\\n" "${3:-}" "${4:-}" >> "$GIT_INVOCATIONS"\n'
        'if [[ "${3:-}" == "$FAIL_COMMAND" ]]; then\n'
        '  printf "forced checkpoint failure\\n" >&2\n'
        "  exit 1\n"
        "fi\n"
        f'exec "{actual_git}" "$@"\n'
    )
    fake_git.chmod(0o755)

    result = _sync(
        script,
        writer,
        remote,
        "push",
        extra_env={
            "FAIL_COMMAND": failed_command,
            "GIT_INVOCATIONS": str(invocations),
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
        },
    )

    commands = [
        line.split(maxsplit=1)[0] for line in invocations.read_text().splitlines()
    ]
    assert result.returncode == 0
    assert result.stdout == ""
    assert "checkpoint failed" in result.stderr
    assert "push failed" in result.stderr
    assert "pull" not in commands
    assert "push" not in commands


@pytest.mark.parametrize("failed_command", ("add", "commit"))
def test_reconcile_checkpoint_failure_skips_pull(
    script: Path, tmp_path: Path, failed_command: str
) -> None:
    """An initialized pull stops at its post-fetch local checkpoint failure."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(
        script, tmp_path, remote, f"reconcile-checkpoint-failure-{failed_command}"
    )
    assert _sync(script, writer, remote, "push").returncode == 0
    _write(writer, "session_logs/reconcile-checkpoint-failure.log", "pending\n")
    actual_git = shutil.which("git")
    assert actual_git is not None
    fake_bin = tmp_path / "reconcile-checkpoint-failure-bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    invocations = tmp_path / "reconcile-checkpoint-failure-invocations.log"
    boundary = tmp_path / "reconcile-checkpoint-boundary"
    fake_git.write_text(
        "#!/usr/bin/env bash\n"
        'if [[ "${3:-}" == "merge-base" ]]; then\n'
        '  : > "$RECONCILE_CHECKPOINT_BOUNDARY"\n'
        "  printf 'reconcile-checkpoint-boundary\\n' >> \"$GIT_INVOCATIONS\"\n"
        "fi\n"
        'if [[ -e "$RECONCILE_CHECKPOINT_BOUNDARY" && "${3:-}" == "$FAIL_COMMAND" ]]; then\n'
        "  printf 'reconcile-checkpoint-failed\\n' >> \"$GIT_INVOCATIONS\"\n"
        '  printf "forced reconciliation checkpoint failure\\n" >&2\n'
        "  exit 1\n"
        "fi\n"
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
            "FAIL_COMMAND": failed_command,
            "GIT_INVOCATIONS": str(invocations),
            "RECONCILE_CHECKPOINT_BOUNDARY": str(boundary),
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
        },
    )

    invocation_lines = invocations.read_text().splitlines()
    boundary_index = invocation_lines.index("reconcile-checkpoint-boundary")
    failure_index = invocation_lines.index("reconcile-checkpoint-failed")
    commands_after_boundary = [
        line.split(maxsplit=1)[0] for line in invocation_lines[boundary_index + 1 :]
    ]
    assert result.returncode == 0
    assert result.stdout == ""
    assert "local state checkpoint failed" in result.stderr
    assert "pull failed" in result.stderr
    assert "pull: up to date" not in result.stderr
    assert any(line.startswith("fetch ") for line in invocation_lines[:boundary_index])
    assert failure_index > boundary_index
    assert "pull" not in commands_after_boundary
    assert "push" not in commands_after_boundary


def test_dirty_tree_race_fails_without_leaving_rebase_state(
    script: Path, tmp_path: Path
) -> None:
    """A write immediately before pull fails transiently without rebase state."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "dirty-race")
    assert _sync(script, writer, remote, "push").returncode == 0
    peer = _new_writer(script, tmp_path, remote, "dirty-race-peer")
    _write(peer, "session_logs/peer-update.log", "remote update\n")
    assert _sync(script, peer, remote, "push").returncode == 0
    _write(writer, "session_logs/local-update.log", "local update\n")
    actual_git = shutil.which("git")
    assert actual_git is not None
    fake_bin = tmp_path / "dirty-race-bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    fake_git.write_text(
        "#!/usr/bin/env bash\n"
        'if [[ "${3:-}" == "pull" ]]; then\n'
        '  printf "race write\\n" >> "$2/session_logs/local-update.log"\n'
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

    assert result.returncode == 0
    assert result.stdout == ""
    assert "reconciliation with origin/ai-state failed" in result.stderr
    assert (writer / ".claude" / "session_logs" / "local-update.log").read_text() == (
        "local update\nrace write\n"
    )
    assert not (writer / ".claude" / ".git" / "rebase-merge").exists()
    assert not (writer / ".claude" / ".git" / "rebase-apply").exists()


def test_pre_rebase_checkpoint_rechecks_active_rebase(
    script: Path, tmp_path: Path
) -> None:
    """The checkpoint guard protects a rebase started after dispatch begins."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "late-operator-rebase")
    rebase_file = "plans/late-operator-rebase.md"
    _write(writer, rebase_file, "base\n")
    assert _sync(script, writer, remote, "push").returncode == 0
    nested = writer / ".claude"
    assert _git(nested, "checkout", "-qb", "late-operator-work").returncode == 0
    _write(writer, rebase_file, "operator\n")
    assert _git(nested, "add", "-A").returncode == 0
    assert _git(nested, "commit", "-qm", "late operator").returncode == 0
    assert _git(nested, "checkout", "-q", "ai-state").returncode == 0
    _write(writer, rebase_file, "sync\n")
    assert _git(nested, "add", "-A").returncode == 0
    assert _git(nested, "commit", "-qm", "late sync").returncode == 0
    assert _git(nested, "checkout", "-q", "late-operator-work").returncode == 0
    before_remote = _git(remote, "rev-parse", "ai-state").stdout
    before_error_log = _error_log_lines(writer)
    actual_git = shutil.which("git")
    assert actual_git is not None
    fake_bin = tmp_path / "late-rebase-bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    invocations = tmp_path / "late-rebase-invocations.log"
    protected_head = tmp_path / "protected-head"
    protected_index = tmp_path / "protected-index"
    protected_worktree = tmp_path / "protected-worktree"
    protected_rebase = tmp_path / "protected-rebase"
    fake_git.write_text(
        "#!/usr/bin/env bash\n"
        'if [[ "${3:-}" == "merge-base" && ! -e "$LATE_REBASE_STARTED" ]]; then\n'
        '  : > "$LATE_REBASE_STARTED"\n'
        f'  "{actual_git}" -C "$2" rebase ai-state >/dev/null 2>&1 || true\n'
        f'  "{actual_git}" -C "$2" rev-parse HEAD > "$PROTECTED_HEAD"\n'
        f'  "{actual_git}" -C "$2" ls-files --stage > "$PROTECTED_INDEX"\n'
        f'  cp "$2/{rebase_file}" "$PROTECTED_WORKTREE"\n'
        '  cp -a "$2/.git/rebase-merge" "$PROTECTED_REBASE_DIR"\n'
        "  printf 'rebase-started\\n' >> \"$GIT_INVOCATIONS\"\n"
        "fi\n"
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
            "LATE_REBASE_STARTED": str(tmp_path / "late-rebase-started"),
            "PROTECTED_HEAD": str(protected_head),
            "PROTECTED_INDEX": str(protected_index),
            "PROTECTED_WORKTREE": str(protected_worktree),
            "PROTECTED_REBASE_DIR": str(protected_rebase),
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
        },
    )

    invocation_lines = invocations.read_text().splitlines()
    rebase_start = invocation_lines.index("rebase-started")
    assert result.returncode == 0
    assert result.stdout == ""
    assert "pre-existing rebase state is ambiguous" in result.stderr
    assert "rebase --quit" not in result.stderr
    assert not any(
        line.split(maxsplit=1)[0] in {"add", "commit", "pull", "push"}
        for line in invocation_lines[rebase_start + 1 :]
    )
    assert _local_head(writer) == protected_head.read_text().strip()
    assert _git(nested, "ls-files", "--stage").stdout == protected_index.read_text()
    assert (nested / rebase_file).read_bytes() == protected_worktree.read_bytes()
    actual_rebase = nested / ".git" / "rebase-merge"
    assert {path.relative_to(actual_rebase) for path in actual_rebase.rglob("*")} == {
        path.relative_to(protected_rebase) for path in protected_rebase.rglob("*")
    }
    for path in protected_rebase.rglob("*"):
        if path.is_file():
            assert (
                actual_rebase / path.relative_to(protected_rebase)
            ).read_bytes() == (path.read_bytes())
    assert _git(remote, "rev-parse", "ai-state").stdout == before_remote
    (logged,) = _appended_error_lines(writer, before_error_log)
    assert "pre-existing rebase state is ambiguous" in logged
    assert "rebase --abort" in logged


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
    before_error_log = _error_log_lines(writer)
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
    assert "rebase --quit" not in result.stderr
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
    (logged,) = _appended_error_lines(writer, before_error_log)
    assert "pre-existing rebase state is ambiguous" in logged
    assert "rebase --abort" in logged


@pytest.mark.parametrize(
    "mode",
    ("setup", "pull", "checkpoint", "publish", "push", "migrate-from-hf"),
)
def test_mutating_entrypoints_preserve_valid_preexisting_merge(
    script: Path, tmp_path: Path, mode: str
) -> None:
    """Every mutating entry point leaves an operator's conflicted merge untouched,
    runs no Git command, and logs one warning that advises ``--continue`` or ``--abort``."""
    remote = _bare_remote(tmp_path)
    writer, _ = _valid_preexisting_merge(script, tmp_path, remote, mode)
    nested = writer / ".claude"
    before_head = _local_head(writer)
    before_index = _git(nested, "ls-files", "--stage").stdout
    before_merge_head = (nested / ".git" / "MERGE_HEAD").read_bytes()
    before_status = _git(nested, "status", "--porcelain=v1", "-z").stdout
    before_worktree = _worktree_snapshot(writer)
    before_remote = _git(remote, "rev-parse", "ai-state").stdout
    before_error_log = _error_log_lines(writer)
    env, invocations = _recording_git(tmp_path)

    result = _sync(script, writer, remote, mode, extra_env=env)

    assert result.returncode == 0
    assert result.stdout == ""
    assert (
        "an unfinished merge is in progress; state sync will not alter it"
        in result.stderr
    )
    assert "merge --continue" in result.stderr
    assert "merge --abort" in result.stderr
    assert not invocations.exists()
    assert _local_head(writer) == before_head
    assert _git(nested, "ls-files", "--stage").stdout == before_index
    assert (nested / ".git" / "MERGE_HEAD").read_bytes() == before_merge_head
    assert _git(nested, "status", "--porcelain=v1", "-z").stdout == before_status
    assert _worktree_snapshot(writer) == before_worktree
    assert _git(remote, "rev-parse", "ai-state").stdout == before_remote
    assert _git(nested, "rev-list", "--merges", "HEAD").stdout == ""
    (logged,) = _appended_error_lines(writer, before_error_log)
    assert "an unfinished merge is in progress" in logged
    assert "merge --abort" in logged


def test_failed_pull_abort_leaves_rebase_and_keeps_settings_copy(
    script: Path, tmp_path: Path
) -> None:
    """A pull conflict whose ``rebase --abort`` fails is left for the operator: no
    ``rebase --quit`` fallback, no later commit over it, and the settings copy
    is kept and named instead of being written back into a tree Git still owns."""
    remote = _bare_remote(tmp_path)
    first = _new_writer(script, tmp_path, remote, "first")
    _write(first, "plans/x.md", "base\n")
    assert _sync(script, first, remote, "push").returncode == 0
    second = _new_writer(script, tmp_path, remote, "second")
    nested = second / ".claude"
    _write(second, "plans/x.md", "from-second\n")
    assert _sync(script, second, remote, "checkpoint").returncode == 0
    branch_before = _git(nested, "rev-parse", "ai-state").stdout.strip()
    _write(first, "plans/x.md", "from-first\n")
    assert _sync(script, first, remote, "push").returncode == 0
    settings = nested / SETTINGS_LOCAL
    settings.write_bytes(b"second-local\r\n")
    env, invocations = _recording_git(
        tmp_path, fail=("rebase", "--abort"), delete_after_pull=settings
    )

    result = _sync(script, second, remote, "pull", extra_env=env)

    assert result.returncode == 0
    assert _logged_calls(invocations, "rebase") == ["rebase --abort"]
    assert (nested / ".git" / "rebase-merge").is_dir()
    assert _git(nested, "rev-parse", "ai-state").stdout.strip() == branch_before
    copies = list((nested / ".git").glob("settings.local.json.*"))
    assert len(copies) == 1
    assert copies[0].read_bytes() == b"second-local\r\n"
    assert str(copies[0]) in result.stderr
    assert not settings.exists()
    assert "rebase --continue" in result.stderr
    assert "rebase --abort" in result.stderr
    assert "rebase --quit" not in result.stderr
    assert "forced rebase --abort failure" in "\n".join(_error_log_lines(second))
    before_head = _local_head(second)
    before_count = _git(nested, "rev-list", "--all", "--count").stdout
    before_remote = _git(remote, "rev-parse", "ai-state").stdout

    checkpoint = _sync(script, second, remote, "checkpoint")
    push = _sync(script, second, remote, "push")

    assert checkpoint.returncode == 0
    assert "pre-existing rebase state is ambiguous" in checkpoint.stderr
    assert _local_head(second) == before_head
    assert _git(nested, "rev-list", "--all", "--count").stdout == before_count
    assert _git(nested, "ls-files", "-u").stdout != ""
    assert push.returncode == 0
    assert _git(remote, "rev-parse", "ai-state").stdout == before_remote


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
    assert "merge: none" in in_progress.stdout
    assert "merge: none" in clear.stdout


def test_status_reports_merge_state(script: Path, tmp_path: Path) -> None:
    """Status exposes an unfinished merge on the line after ``rebase:``."""
    remote = _bare_remote(tmp_path)
    uninitialized = tmp_path / "uninitialized"
    uninitialized.mkdir()
    writer, _ = _valid_preexisting_merge(script, tmp_path, remote, "status-merge")

    fresh = _sync(script, uninitialized, None, "status")
    in_progress = _sync(script, writer, remote, "status")
    assert _git(writer / ".claude", "merge", "--abort").returncode == 0
    clear = _sync(script, writer, remote, "status")

    assert "rebase: none\nmerge: none\n" in fresh.stdout
    assert "rebase: none\nmerge: in-progress\n" in in_progress.stdout
    assert "rebase: none\nmerge: none\n" in clear.stdout


def test_fresh_setup_with_unabortable_merge_neither_commits_nor_restores(
    script: Path, tmp_path: Path
) -> None:
    """A fresh setup whose unrelated-history merge conflicts and cannot be aborted
    leaves the merge for the operator: no commit over the markers, no adapter
    restore, and the settings copy kept and named."""
    remote = _bare_remote(tmp_path)
    publisher = _new_writer(script, tmp_path, remote, "publisher")
    _write(publisher, "plans/x.md", "from-publisher\n")
    assert _sync(script, publisher, remote, "push").returncode == 0
    root = tmp_path / "fresh"
    consumer_script = _install_pull_runtime(root)
    adapter_source = _write_github_adapter_source(root)
    _write(root, "plans/x.md", "from-fresh\n")
    nested = root / ".claude"
    (nested / SETTINGS_LOCAL).write_bytes(b"fresh-local\r\n")
    env, invocations = _recording_git(tmp_path, fail=("merge", "--abort"))

    result = _sync(consumer_script, root, remote, "setup", extra_env=env)

    assert result.returncode == 0
    assert adapter_source.is_file()
    assert _logged_calls(invocations, "merge") == ["merge -q", "merge --abort"]
    assert (nested / ".git" / "MERGE_HEAD").is_file()
    assert _local_commit_count(root) == 1
    assert _git(nested, "log", "-1", "--format=%s").stdout.strip() == (
        "bootstrap: init ai-state"
    )
    assert _git(nested, "rev-list", "--merges", "HEAD").stdout == ""
    assert not (root / ".github").exists()
    copies = list((nested / ".git").glob("settings.local.json.*"))
    assert len(copies) == 1
    assert copies[0].read_bytes() == b"fresh-local\r\n"
    assert str(copies[0]) in result.stderr
    assert "merge --continue" in result.stderr
    assert "merge --abort" in result.stderr
    assert "setup failed; continuing." in result.stderr
    before_head = _local_head(root)

    checkpoint = _sync(consumer_script, root, remote, "checkpoint")

    assert checkpoint.returncode == 0
    assert "an unfinished merge is in progress" in checkpoint.stderr
    assert _local_head(root) == before_head
    assert _local_commit_count(root) == 1


def test_failed_unrelated_merge_without_merge_state_restores_settings(
    script: Path, tmp_path: Path
) -> None:
    """A merge that fails before it creates ``MERGE_HEAD`` has nothing to abort:
    no ``merge --abort`` runs, nothing is reported as left in place, and the
    settings file keeps its bytes with no copy left under ``.git``."""
    remote = _bare_remote(tmp_path)
    publisher = _new_writer(script, tmp_path, remote, "publisher")
    _write(publisher, "plans/x.md", "from-publisher\n")
    assert _sync(script, publisher, remote, "push").returncode == 0
    root = tmp_path / "fresh"
    _write(root, "plans/x.md", "from-fresh\n")
    nested = root / ".claude"
    settings = nested / SETTINGS_LOCAL
    settings.write_bytes(b"fresh-local\r\n")
    env, invocations = _recording_git(tmp_path, fail=("merge", "-q"))

    result = _sync(script, root, remote, "setup", extra_env=env)

    assert result.returncode == 0
    assert _logged_calls(invocations, "merge") == ["merge -q"]
    assert "could not be merged automatically" in result.stderr
    assert "left in place" not in result.stderr
    assert not (nested / ".git" / "MERGE_HEAD").exists()
    assert settings.read_bytes() == b"fresh-local\r\n"
    assert list((nested / ".git").glob("settings.local.json.*")) == []


def test_unrelated_history_merge_commits_local_changes_first(
    script: Path, tmp_path: Path
) -> None:
    """The unrelated-history merge starts from a committed tree: an uncommitted
    local file is in the merge commit's first parent, not added after the merge."""
    remote = _bare_remote(tmp_path)
    peer = _new_writer(script, tmp_path, remote, "peer")
    _write(peer, "plans/remote.md", "from-remote\n")
    assert _sync(script, peer, remote, "push").returncode == 0
    writer = tmp_path / "local-first"
    (writer / ".claude").mkdir(parents=True)
    _write(writer, "plans/base.md", "base\n")
    assert _sync(script, writer, None, "checkpoint").returncode == 0
    nested = writer / ".claude"
    assert _git(nested, "remote", "add", "origin", str(remote)).returncode == 0
    _write(writer, "plans/dirty.md", "written, not committed\n")

    result = _sync(script, writer, remote, "pull")

    assert result.returncode == 0, result.stderr
    _, *parents = _git(
        nested, "rev-list", "--parents", "-n", "1", "HEAD"
    ).stdout.split()
    assert len(parents) == 2, "HEAD must be the merge commit itself"
    first_parent, second_parent = parents
    assert (
        _git(nested, "show", f"{first_parent}:plans/dirty.md").stdout
        == "written, not committed\n"
    )
    assert _git(nested, "show", f"{second_parent}:plans/remote.md").returncode == 0
    assert _git(nested, "status", "--porcelain").stdout == ""
    assert (nested / "plans" / "remote.md").read_text() == "from-remote\n"
    assert (nested / "plans" / "dirty.md").read_text() == "written, not committed\n"


def test_commit_refuses_while_a_merge_is_unfinished(
    script: Path, tmp_path: Path
) -> None:
    """The backstop in ``commit_local_state``: a merge that starts after the entry
    guard ran (here inside the adapter restore before the post-pull checkpoint)
    is never committed over, and no staging or untrack call touches it."""
    remote = _bare_remote(tmp_path)
    writer, _ = _diverged_branches(script, tmp_path, remote, "late-merge")
    nested = writer / ".claude"
    script.with_name("restore-root-adapters.sh").write_text(
        "#!/usr/bin/env bash\n"
        f'git -C "{nested}" merge operator-work >/dev/null 2>&1 || true\n'
    )
    before_head = _local_head(writer)
    env, invocations = _recording_git(tmp_path)

    result = _sync(script, writer, remote, "pull", "--local-only", extra_env=env)

    calls = invocations.read_text().splitlines()
    assert result.returncode == 0
    assert "not committing over it" in result.stderr
    assert "post-pull checkpoint failed" in result.stderr
    assert (nested / ".git" / "MERGE_HEAD").is_file()
    assert _local_head(writer) == before_head
    assert _git(nested, "rev-list", "--merges", "HEAD").stdout == ""
    assert calls[-1] == "merge operator-work"


def test_checkpoint_refuses_unmerged_index_left_by_rebase_quit(
    script: Path, tmp_path: Path
) -> None:
    """``rebase --quit`` leaves a detached HEAD with an unmerged index and no
    rebase folder. No marker file shows it, so ``commit_local_state`` finds it
    through the index and refuses to commit the conflict markers."""
    remote = _bare_remote(tmp_path)
    writer, _ = _valid_preexisting_rebase(script, tmp_path, remote, "quit-leftover")
    nested = writer / ".claude"
    assert _git(nested, "rebase", "--quit").returncode == 0
    assert not (nested / ".git" / "rebase-merge").exists()
    assert _git(nested, "ls-files", "-u").stdout != ""
    before_head = _local_head(writer)
    before_count = _git(nested, "rev-list", "--all", "--count").stdout

    result = _sync(script, writer, remote, "checkpoint")

    assert result.returncode == 0
    assert "not committing over it" in result.stderr
    assert _local_head(writer) == before_head
    assert _git(nested, "rev-list", "--all", "--count").stdout == before_count
    assert _git(nested, "ls-files", "-u").stdout != ""


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


@pytest.mark.parametrize("local_only", (False, True), ids=("no-remote", "local-only"))
def test_pull_restores_ignored_github_directory_after_successful_local_setup(
    tmp_path: Path, local_only: bool
) -> None:
    """Successful no-remote and local-only pulls restore an ignored directory adapter."""
    root = tmp_path / ("local-only" if local_only else "no-remote")
    consumer_script = _install_pull_runtime(root)
    _write_github_adapter_source(root)

    result = _sync(
        consumer_script,
        root,
        None,
        "pull",
        extra_env={"AI_STATE_LOCAL_ONLY": "1" if local_only else "0"},
    )

    restored = root / ".github/agents/coder.agent.md"
    assert result.returncode == 0, result.stderr
    assert restored.read_text(encoding="utf-8") == "generated agent\n"
    assert _git(root / ".claude", "rev-parse", "--verify", "HEAD").returncode == 0
    assert _git(root / ".claude", "status", "--porcelain").stdout == ""


def test_pull_restores_after_successful_remote_reconciliation(tmp_path: Path) -> None:
    """A fresh consumer restores the pulled mirror only after remote reconciliation."""
    remote = _bare_remote(tmp_path)
    publisher = tmp_path / "publisher"
    publisher_script = _install_pull_runtime(publisher)
    _write_github_adapter_source(publisher, "published agent\n")
    assert _sync(publisher_script, publisher, remote, "setup").returncode == 0
    assert _sync(publisher_script, publisher, remote, "push").returncode == 0
    consumer = tmp_path / "consumer"
    consumer_script = _install_pull_runtime(consumer)

    result = _sync(consumer_script, consumer, remote, "pull")

    assert result.returncode == 0, result.stderr
    assert (consumer / ".github/agents/coder.agent.md").read_text() == (
        "published agent\n"
    )
    assert _git(consumer / ".claude", "rev-parse", "--verify", "HEAD").returncode == 0
    assert _git(consumer / ".claude", "status", "--porcelain").stdout == ""


def test_failed_pull_does_not_restore_root_adapters(tmp_path: Path) -> None:
    """A failed reconciliation leaves an absent ignored adapter absent."""
    remote = _bare_remote(tmp_path)
    publisher = tmp_path / "publisher"
    publisher_script = _install_pull_runtime(publisher)
    _write_github_adapter_source(publisher)
    assert _sync(publisher_script, publisher, remote, "setup").returncode == 0
    assert _sync(publisher_script, publisher, remote, "push").returncode == 0
    root = tmp_path / "failed-pull"
    consumer_script = _install_pull_runtime(root)
    _write_github_adapter_source(root)
    actual_git = shutil.which("git")
    assert actual_git is not None
    fake_bin = tmp_path / "failed-pull-bin"
    fake_bin.mkdir()
    fake_git = fake_bin / "git"
    fake_git.write_text(
        "#!/usr/bin/env bash\n"
        'if [[ "${3:-}" == "fetch" ]]; then\n'
        '  printf "forced fetch failure\\n" >&2\n'
        "  exit 1\n"
        "fi\n"
        f'exec "{actual_git}" "$@"\n'
    )
    fake_git.chmod(0o755)

    result = _sync(
        consumer_script,
        root,
        remote,
        "pull",
        extra_env={"PATH": f"{fake_bin}:{os.environ['PATH']}"},
    )

    assert result.returncode == 0
    assert "fetch from origin/ai-state failed" in result.stderr
    assert not (root / ".github/agents/coder.agent.md").exists()


def test_conflicted_pull_does_not_restore_root_adapters(
    script: Path, tmp_path: Path
) -> None:
    """A real rebase conflict preserves the local state and skips restoration."""
    remote = _bare_remote(tmp_path)
    publisher = tmp_path / "publisher"
    publisher_script = _install_pull_runtime(publisher)
    _write_github_adapter_source(publisher)
    assert _sync(publisher_script, publisher, remote, "setup").returncode == 0
    _write(publisher, "plans/conflict.md", "base\n")
    assert _sync(publisher_script, publisher, remote, "push").returncode == 0

    consumer = tmp_path / "consumer"
    consumer_script = _install_pull_runtime(consumer)
    assert _sync(consumer_script, consumer, remote, "pull").returncode == 0
    _write(consumer, "plans/conflict.md", "consumer\n")
    assert _sync(consumer_script, consumer, remote, "checkpoint").returncode == 0
    before_head = _local_head(consumer)
    shutil.rmtree(consumer / ".github")

    peer = _new_writer(script, tmp_path, remote, "peer")
    _write(peer, "plans/conflict.md", "peer\n")
    assert _sync(script, peer, remote, "push").returncode == 0

    result = _sync(consumer_script, consumer, remote, "pull")

    assert result.returncode == 0
    assert "reconciliation with origin/ai-state failed" in result.stderr
    assert _local_head(consumer) == before_head
    assert _local_show(consumer, "plans/conflict.md") == "consumer\n"
    assert not (consumer / ".github/agents/coder.agent.md").exists()
    assert _no_active_rebase_or_merge(consumer)


def test_setup_alone_restores_ignored_github_directory_on_fresh_repo(
    tmp_path: Path,
) -> None:
    """Standalone `setup` (no `pull`) restores installer-owned ignored root
    adapters too (D5 / F1 §9), matching the manual two-command bootstrap in
    README.md where a non-devcontainer machine may run only `setup`."""
    root = tmp_path / "standalone-setup"
    consumer_script = _install_pull_runtime(root)
    _write_github_adapter_source(root)

    result = _sync(consumer_script, root, None, "setup")

    restored = root / ".github/agents/coder.agent.md"
    assert result.returncode == 0, result.stderr
    assert restored.read_text(encoding="utf-8") == "generated agent\n"
    assert _git(root / ".claude", "rev-parse", "--verify", "HEAD").returncode == 0
    assert _git(root / ".claude", "status", "--porcelain").stdout == ""


def test_restore_root_adapters_restores_agents_directory(tmp_path: Path) -> None:
    """The ordinary root manifest restores the complete `.agents` adapter."""
    root = tmp_path / "consumer"
    source = root / ".claude" / "bootstrap-root"
    _write_restore_manifest(root, ".agents")
    agent = source / ".agents" / "agents" / "coder" / "agent.md"
    agent.parent.mkdir(parents=True)
    agent.write_text("generated agent\n")

    result = _restore(root)

    assert result.returncode == 0, result.stderr
    assert (root / ".agents" / "agents" / "coder" / "agent.md").read_text() == (
        "generated agent\n"
    )


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


def test_setup_merges_remote_tracked_log_without_creating_a_local_blocker(
    script: Path, tmp_path: Path
) -> None:
    """Fresh setup must not create a tracked ``session_logs/*.log`` file
    before an unrelated merge. Uses ``hooks-bypass.log`` (still a normal
    tracked, union-merged log) rather than the now local-only error log."""
    remote = _bare_remote(tmp_path)
    _seed_remote(script, tmp_path, remote, "session_logs/hooks-bypass.log", "remote\n")
    writer = tmp_path / "fresh-setup"
    (writer / ".claude").mkdir(parents=True)

    result = _sync(script, writer, remote, "setup")

    assert result.returncode == 0
    assert _local_show(writer, "session_logs/hooks-bypass.log") == "remote\n"
    assert _no_active_rebase_or_merge(writer)
    assert "could not be merged automatically" not in result.stderr


def test_setup_checkpoints_error_log_locally_when_remote_is_unavailable(
    script: Path, tmp_path: Path
) -> None:
    """Offline setup leaves durable state clean after recording its warning
    in the local-only error log (never committed, so read directly rather
    than through ``git show HEAD:...``)."""
    writer = tmp_path / "offline-setup"
    (writer / ".claude").mkdir(parents=True)
    unavailable_remote = tmp_path / "missing.git"

    result = _sync(script, writer, unavailable_remote, "setup")

    assert result.returncode == 0
    assert _local_head(writer)
    assert _git(writer / ".claude", "status", "--porcelain").stdout == ""
    assert "fetch from origin/ai-state failed" in result.stderr
    assert (
        "fetch from origin/ai-state failed"
        in (writer / ".claude" / "session_logs" / "hooks-errors.log").read_text()
    )
    assert (
        _git(writer / ".claude", "ls-files", "session_logs/hooks-errors.log").stdout
        == ""
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


# --- One sync at a time, the exit trap, and the network stall limit ---------

# Pauses a fake ``git`` at its first ``add``: writes READY_FILE, then waits up to
# 30 seconds for RELEASE_FILE so a broken run fails instead of hanging.
PAUSE_AT_ADD = r"""
if [[ "${3:-}" == "add" && ! -e "$READY_FILE" ]]; then
  : > "$READY_FILE"
  waited=0
  while [[ ! -e "$RELEASE_FILE" && $waited -lt 300 ]]; do
    sleep 0.1
    waited=$((waited + 1))
  done
fi
"""

# At ``pull``: optionally runs real git first (which may stop on a conflict),
# then deletes the live settings file, writes READY_FILE, and sleeps until a
# signal ends it (30 seconds at most).
STALL_AT_PULL = r"""
if [[ "${3:-}" == "pull" ]]; then
  if [[ -n "${REAL_PULL:-}" ]]; then
    "$REAL_GIT" "$@" || true
  fi
  rm -f "$SETTINGS"
  : > "$READY_FILE"
  sleep 30
  exit 1
fi
"""


@needs_flock
@pytest.mark.parametrize("mode", ("pull", "checkpoint", "publish", "push"))
def test_sync_lock_busy_run_skips_without_running_git(
    script: Path, tmp_path: Path, mode: str
) -> None:
    """A run that finds the lock held skips at once and touches nothing: no Git
    command, HEAD, remote ref, or dirty file changes. The next checkpoint, with
    the lock free, commits the file. (``setup`` and ``migrate-from-hf`` wait
    instead; see the ``setup`` lock tests.)"""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, mode)
    _write(writer, "plans/seed.md", "seed\n")
    assert _sync(script, writer, remote, "push").returncode == 0
    _write(writer, "plans/dirty.md", "waits for the next run\n")
    nested = writer / ".claude"
    before_head = _local_head(writer)
    before_remote = _git(remote, "rev-parse", "ai-state").stdout
    env, invocations = _recording_git(tmp_path)

    with _sync_lock_held(writer):
        result = _sync(script, writer, remote, mode, extra_env=env)

    assert result.returncode == 0
    assert result.stdout == ""
    assert "another state sync is running" in result.stderr
    assert not invocations.exists()
    assert _local_head(writer) == before_head
    assert _git(remote, "rev-parse", "ai-state").stdout == before_remote
    assert _git(nested, "status", "--porcelain").stdout == "?? plans/dirty.md\n"
    assert _sync(script, writer, remote, "checkpoint").returncode == 0
    assert _local_show(writer, "plans/dirty.md") == "waits for the next run\n"


@needs_flock
def test_sync_lock_is_shared_by_devcontainer_and_hooks_copies(tmp_path: Path) -> None:
    """Both installed copies resolve the same root from their own location (no
    ``AI_STATE_REPO_ROOT``), so a run of one excludes a run of the other."""
    root = tmp_path / "shared-root"
    hooks_copy = root / ".claude" / "hooks" / "scripts" / "state-sync.sh"
    devcontainer_copy = root / ".devcontainer" / "state-sync.sh"
    for copy in (hooks_copy, devcontainer_copy):
        copy.parent.mkdir(parents=True)
        shutil.copy(SCRIPT_SRC, copy)
    own_root = {"AI_STATE_REPO_ROOT": ""}
    assert (
        _sync(hooks_copy, root, None, "checkpoint", extra_env=own_root).returncode == 0
    )
    _write(root, "plans/dirty.md", "committed by run A\n")
    before_head = _local_head(root)
    ready, release = tmp_path / "ready", tmp_path / "release"
    env = {
        **own_root,
        **_fake_git(tmp_path, PAUSE_AT_ADD),
        "READY_FILE": str(ready),
        "RELEASE_FILE": str(release),
    }

    with _sync_process(hooks_copy, root, None, "checkpoint", extra_env=env) as run_a:
        _wait_for_file(ready, run_a)
        run_b = _sync(devcontainer_copy, root, None, "checkpoint", extra_env=own_root)
        head_while_a_waits = _local_head(root)
        release.touch()
        run_a.communicate(timeout=30)

    assert run_b.returncode == 0
    assert "another state sync is running" in run_b.stderr
    assert head_while_a_waits == before_head
    assert run_a.returncode == 0
    assert _local_show(root, "plans/dirty.md") == "committed by run A\n"


@needs_flock
def test_sync_lock_status_runs_while_lock_is_held(
    script: Path, tmp_path: Path, path_without_flock: dict[str, str]
) -> None:
    """``status`` never waits for the lock (it would hit the time limit here) and
    reports ``held``, ``free``, or ``unavailable`` (no ``flock``), in both the
    initialized and the uninitialized report."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "status-lock")
    uninitialized = tmp_path / "uninitialized"
    (uninitialized / ".claude").mkdir(parents=True)

    with _sync_lock_held(writer):
        held = _sync(script, writer, remote, "status", timeout=20)
    free = _sync(script, writer, remote, "status")
    unavailable = _sync(script, writer, remote, "status", extra_env=path_without_flock)
    with _sync_lock_held(uninitialized):
        fresh_held = _sync(script, uninitialized, None, "status", timeout=20)
    fresh_free = _sync(script, uninitialized, None, "status")

    assert held.returncode == 0
    assert "repository: initialized" in held.stdout
    assert "merge: none\nlock: held\n" in held.stdout
    assert "another state sync is running" not in held.stderr
    assert "merge: none\nlock: free\n" in free.stdout
    assert "merge: none\nlock: unavailable\n" in unavailable.stdout
    assert "repository: uninitialized" in fresh_held.stdout
    assert "merge: none\nlock: held\n" in fresh_held.stdout
    assert "merge: none\nlock: free\n" in fresh_free.stdout


def test_sync_lock_fresh_clone_leaves_no_lock_file(tmp_path: Path) -> None:
    """Contract guard that already passes without the lock: the lock is the root
    folder itself, so a fresh clone gains no lock file and no dirty nested tree."""
    root = tmp_path / "fresh-clone"
    root.mkdir()
    assert subprocess.run(["git", "init", "-q", str(root)], check=False).returncode == 0
    copy = root / ".devcontainer" / "state-sync.sh"
    copy.parent.mkdir()
    shutil.copy(SCRIPT_SRC, copy)

    result = _sync(copy, root, None, "setup", extra_env={"AI_STATE_REPO_ROOT": ""})

    assert result.returncode == 0, result.stderr
    assert {entry.name for entry in root.iterdir()} == {
        ".git",
        ".claude",
        ".devcontainer",
    }
    assert _git(root / ".claude", "status", "--porcelain").stdout == ""


def test_sync_lock_runs_unlocked_without_flock(
    script: Path, tmp_path: Path, path_without_flock: dict[str, str]
) -> None:
    """Contract guard that already passes without the lock: with no ``flock`` on
    ``PATH`` (stock macOS) a run goes on unlocked and silent, even while the
    lock is held."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "no-flock")
    _write(writer, "plans/unlocked.md", "committed anyway\n")

    with _sync_lock_held(writer):
        result = _sync(
            script, writer, remote, "checkpoint", extra_env=path_without_flock
        )

    assert result.returncode == 0
    assert "another state sync is running" not in result.stderr
    assert _local_show(writer, "plans/unlocked.md") == "committed anyway\n"


def test_sync_lock_failure_runs_unlocked_with_notice(
    script: Path, tmp_path: Path
) -> None:
    """A ``flock`` that fails for any reason but a busy lock (exit 65 here) does
    not stop sync: the run commits, tells stderr, and logs nothing."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "flock-fails")
    _write(writer, "plans/unlocked.md", "committed anyway\n")

    result = _sync(
        script,
        writer,
        remote,
        "checkpoint",
        extra_env=_fake_flock(tmp_path, "exit 65"),
    )

    assert result.returncode == 0
    assert "could not lock" in result.stderr
    assert "flock exit 65" in result.stderr
    assert not any("could not lock" in line for line in _error_log_lines(writer))
    assert _local_show(writer, "plans/unlocked.md") == "committed anyway\n"


@pytest.mark.parametrize(
    ("signum", "exit_code"),
    (
        pytest.param(signal.SIGTERM, 143, id="SIGTERM"),
        pytest.param(signal.SIGINT, 130, id="SIGINT"),
        pytest.param(signal.SIGHUP, 129, id="SIGHUP"),
    ),
)
def test_exit_trap_restores_settings_copy_after_signal(
    script: Path, tmp_path: Path, signum: signal.Signals, exit_code: int
) -> None:
    """A run stopped by a signal while Git has removed the live settings file puts
    its copy back and leaves none behind; the exit code is 128 plus the signal."""
    remote = _bare_remote(tmp_path)
    first = _new_writer(script, tmp_path, remote, "first")
    assert _sync(script, first, remote, "push").returncode == 0
    second = _new_writer(script, tmp_path, remote, "second")
    nested = second / ".claude"
    settings = nested / SETTINGS_LOCAL
    settings.write_bytes(b"second-local\r\n")
    ready = tmp_path / "ready"
    env = {
        **_fake_git(tmp_path, STALL_AT_PULL),
        "SETTINGS": str(settings),
        "READY_FILE": str(ready),
    }

    with _sync_process(script, second, remote, "pull", extra_env=env) as run:
        _wait_for_file(ready, run)
        assert not settings.exists()
        os.killpg(run.pid, signum)
        run.communicate(timeout=30)

    assert run.returncode == exit_code
    assert settings.read_bytes() == b"second-local\r\n"
    assert list((nested / ".git").glob("settings.local.json.*")) == []


def test_exit_trap_keeps_and_names_copy_during_unfinished_rebase(
    script: Path, tmp_path: Path
) -> None:
    """A run stopped while its pull's conflicted rebase is still in place keeps the
    settings copy and names it; writing it back would hand Git's tree a file Git
    may overwrite again."""
    remote = _bare_remote(tmp_path)
    first = _new_writer(script, tmp_path, remote, "first")
    _write(first, "plans/x.md", "base\n")
    assert _sync(script, first, remote, "push").returncode == 0
    second = _new_writer(script, tmp_path, remote, "second")
    nested = second / ".claude"
    _write(second, "plans/x.md", "from-second\n")
    assert _sync(script, second, remote, "checkpoint").returncode == 0
    _write(first, "plans/x.md", "from-first\n")
    assert _sync(script, first, remote, "push").returncode == 0
    settings = nested / SETTINGS_LOCAL
    settings.write_bytes(b"second-local\r\n")
    ready = tmp_path / "ready"
    env = {
        **_fake_git(tmp_path, STALL_AT_PULL),
        "REAL_PULL": "1",
        "SETTINGS": str(settings),
        "READY_FILE": str(ready),
    }

    with _sync_process(script, second, remote, "pull", extra_env=env) as run:
        _wait_for_file(ready, run)
        os.killpg(run.pid, signal.SIGTERM)
        _, stderr = run.communicate(timeout=30)

    copies = list((nested / ".git").glob("settings.local.json.*"))
    assert run.returncode == 143
    assert (nested / ".git" / "rebase-merge").is_dir()
    assert not settings.exists()
    assert len(copies) == 1
    assert copies[0].read_bytes() == b"second-local\r\n"
    marker = "state sync stopped while a rebase or merge was unfinished"
    assert marker in stderr
    assert str(copies[0]) in stderr.split(marker, 1)[1]


@contextlib.contextmanager
def _silent_http_server() -> Iterator[int]:
    """Serve a local port that accepts connections, reads each request, and never
    answers. Yields the port."""
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen()
    connections: list[socket.socket] = []

    def accept_forever() -> None:
        while True:
            try:
                connection, _ = server.accept()
            except OSError:
                return
            connections.append(connection)
            connection.settimeout(5)
            with contextlib.suppress(OSError):
                connection.recv(65536)

    thread = threading.Thread(target=accept_forever, daemon=True)
    thread.start()
    try:
        yield server.getsockname()[1]
    finally:
        with contextlib.suppress(OSError):
            server.shutdown(socket.SHUT_RDWR)
        server.close()
        for connection in connections:
            connection.close()
        thread.join(timeout=10)


@needs_flock
def test_network_limit_ends_a_stalled_fetch(script: Path, tmp_path: Path) -> None:
    """A server that accepts the request and never answers cannot hold a run for
    good: Git gives up at the stall limit (the caller's 2 seconds here win over
    the 60-second default), the run takes its fetch-failure path, and the lock is
    free afterwards. Without a default limit Git waits forever."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "stalled")
    env = {
        "GIT_HTTP_LOW_SPEED_TIME": "2",
        "NO_PROXY": "127.0.0.1",
        "no_proxy": "127.0.0.1",
    }

    with _silent_http_server() as port:
        url = f"http://127.0.0.1:{port}/x.git"
        assert (
            _git(writer / ".claude", "remote", "set-url", "origin", url).returncode == 0
        )
        started = time.monotonic()
        with _sync_process(script, writer, remote, "pull", extra_env=env) as run:
            _, stderr = run.communicate(timeout=20)
        elapsed = time.monotonic() - started

    assert run.returncode == 0
    assert elapsed < 20
    assert "fetch from origin/ai-state failed" in stderr
    assert "lock: free" in _sync(script, writer, remote, "status").stdout


def test_network_limit_sets_no_prompt_and_stall_defaults(
    script: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Every ``fetch`` and ``push`` runs with the password prompt off and the stall
    limit set: 1000 bytes per second for 60 seconds unless the caller chose its
    own values, and the prompt stays off even when the caller turned it on."""
    for name in (
        "GIT_TERMINAL_PROMPT",
        "GIT_HTTP_LOW_SPEED_LIMIT",
        "GIT_HTTP_LOW_SPEED_TIME",
    ):
        monkeypatch.delenv(name, raising=False)
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "limits")
    assert _sync(script, writer, remote, "push").returncode == 0
    record = r"""
if [[ "${3:-}" == "fetch" || "${3:-}" == "push" ]]; then
  printf '%s %s %s %s\n' "$3" "${GIT_TERMINAL_PROMPT-unset}" \
    "${GIT_HTTP_LOW_SPEED_LIMIT-unset}" "${GIT_HTTP_LOW_SPEED_TIME-unset}" >> "$ENV_LOG"
fi
"""
    fake = _fake_git(tmp_path, record)
    scenarios: tuple[tuple[dict[str, str], str], ...] = (
        ({}, "0 1000 60"),
        ({"GIT_HTTP_LOW_SPEED_TIME": "5"}, "0 1000 5"),
        ({"GIT_TERMINAL_PROMPT": "1"}, "0 1000 60"),
    )

    for index, (caller, expected) in enumerate(scenarios):
        log = tmp_path / f"env-{index}.log"
        _write(writer, f"plans/limits-{index}.md", "changed\n")
        result = _sync(
            script,
            writer,
            remote,
            "push",
            extra_env={**fake, **caller, "ENV_LOG": str(log)},
        )
        assert result.returncode == 0, result.stderr
        assert log.read_text().splitlines() == [f"fetch {expected}", f"push {expected}"]


@needs_flock
def test_sync_lock_setup_waits_for_a_busy_lock(script: Path, tmp_path: Path) -> None:
    """``setup`` waits for a busy lock instead of skipping, because the installer
    relies on it to keep ``settings.local.json`` ignored; a ``checkpoint`` under
    the same lock skips at once."""
    remote = _bare_remote(tmp_path)
    writer = _new_writer(script, tmp_path, remote, "waiting-setup")
    gitignore = writer / ".claude" / ".gitignore"
    gitignore.write_text("user-sentinel/\n")

    with _sync_lock_held(writer) as release:
        started = time.monotonic()
        skipped = _sync(script, writer, remote, "checkpoint")
        skipped_after = time.monotonic() - started
        with _sync_process(script, writer, remote, "setup") as run:
            time.sleep(2)
            still_waiting = run.poll() is None
            untouched = gitignore.read_text()
            release()
            _, stderr = run.communicate(timeout=30)

    assert "another state sync is running" in skipped.stderr
    assert skipped_after < 10
    assert still_waiting
    assert untouched == "user-sentinel/\n"
    assert run.returncode == 0
    assert "another state sync is running" not in stderr
    assert "settings.local.json" in gitignore.read_text().splitlines()


@pytest.mark.parametrize("mode", ("setup", "migrate-from-hf"))
def test_sync_lock_setup_warns_when_the_wait_ends(
    script: Path, tmp_path: Path, mode: str
) -> None:
    """The two patient modes call exactly ``flock -w 60 9``. When that wait ends
    with the lock still busy (a fake ``flock`` exits 1 for ``-w``) they log a
    warning and skip, changing nothing and making no commit. A ``checkpoint``
    under the same fake calls ``flock -n 9``."""
    remote = _bare_remote(tmp_path)
    if mode == "setup":
        root = _new_writer(script, tmp_path, remote, mode)
        (root / ".claude" / ".gitignore").write_text("user-sentinel/\n")
    else:
        root = tmp_path / mode
        _write(root, "plans/pre-git.md", "state from before git\n")
    nested = root / ".claude"
    had_repository = (nested / ".git").exists()
    before_head = _local_head(root) if had_repository else None
    before_worktree = _worktree_snapshot(root)
    flock_log = tmp_path / "flock-arguments.log"
    env = {
        **_fake_flock(
            tmp_path,
            'printf "%s\\n" "$*" >> "$FLOCK_LOG"\nif [[ "$1" == "-w" ]]; then exit 1; fi',
        ),
        "FLOCK_LOG": str(flock_log),
    }

    result = _sync(script, root, remote, mode, extra_env=env)

    assert result.returncode == 0
    assert flock_log.read_text().splitlines() == ["-w 60 9"]
    assert any(
        f"another state sync held the lock for 60 seconds; {mode} skipped" in line
        for line in _error_log_lines(root)
    )
    assert (nested / ".git").exists() == had_repository
    if had_repository:
        assert _local_head(root) == before_head
    assert _worktree_snapshot(root) == before_worktree

    checkpoint = _sync(script, root, remote, "checkpoint", extra_env=env)

    assert checkpoint.returncode == 0
    assert flock_log.read_text().splitlines() == ["-w 60 9", "-n 9"]
