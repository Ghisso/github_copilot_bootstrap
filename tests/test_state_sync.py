"""Regression coverage for git-backed AI state sync (``state-sync.sh``).

Exercises the real shared script against throwaway local git repositories so
the failure-propagation and multi-writer conflict guarantees are verified
end-to-end rather than mocked. A bare repo stands in for ``origin`` and every
git operation is local, so the suite needs no network.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_SRC = REPO_ROOT / "shared" / "hooks" / "scripts" / "state-sync.sh"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run ``git -C root <args>`` and capture output without raising."""
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _sync(
    script: Path, root: Path, remote: Path, mode: str, *args: str
) -> subprocess.CompletedProcess[str]:
    """Invoke the copied ``state-sync.sh`` for one writer against ``remote``."""
    env = {
        **os.environ,
        "AI_STATE_REPO_ROOT": str(root),
        "AI_STATE_REMOTE": str(remote),
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
