"""Focused regressions for bootstrap installation ownership boundaries."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from install_bootstrap import copy_generated_tree  # noqa: E402

INSTALLER = REPO_ROOT / "scripts" / "install_bootstrap.py"
GENERATED = REPO_ROOT / "dist" / "multi-agent"


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _actor_env() -> dict[str, str]:
    return {
        **os.environ,
        "GIT_AUTHOR_NAME": "Installer Test",
        "GIT_AUTHOR_EMAIL": "installer@example.com",
        "GIT_COMMITTER_NAME": "Installer Test",
        "GIT_COMMITTER_EMAIL": "installer@example.com",
    }


def _tree_snapshot(root: Path) -> dict[Path, bytes | None]:
    return {
        path.relative_to(root): path.read_bytes() if path.is_file() else None
        for path in root.rglob("*")
    }


@pytest.mark.parametrize("gitfile", (False, True), ids=("directory", "gitfile"))
def test_copy_preserves_nested_git_metadata(tmp_path: Path, gitfile: bool) -> None:
    """Obsolete-file pruning never treats nested Git metadata as bootstrap data."""
    source = tmp_path / "generated"
    target = tmp_path / "consumer"
    (source / ".claude").mkdir(parents=True)
    (source / ".claude" / "generated.md").write_text("fresh\n")
    nested_git = target / ".claude" / ".git"
    if gitfile:
        nested_git.parent.mkdir(parents=True)
        nested_git.write_text("gitdir: ../ai-state.git\n")
    else:
        nested_git.mkdir(parents=True)
        (nested_git / "HEAD").write_text("ref: refs/heads/ai-state\n")

    copy_generated_tree(source, target, dry_run=False)

    if gitfile:
        assert nested_git.read_text() == "gitdir: ../ai-state.git\n"
    else:
        assert (nested_git / "HEAD").read_text() == "ref: refs/heads/ai-state\n"
    assert (target / ".claude" / "generated.md").read_text() == "fresh\n"


def test_copy_preserves_genuine_tracked_copilot_authoring(tmp_path: Path) -> None:
    """Local-only mode preserves tracked Copilot files without prior bootstrap ownership."""
    source = tmp_path / "generated"
    target = tmp_path / "consumer"
    generated_agent = source / ".github" / "agents" / "reviewer.agent.md"
    generated_agent.parent.mkdir(parents=True)
    generated_agent.write_text("generated\n")
    authored_agent = target / ".github" / "agents" / "reviewer.agent.md"
    authored_agent.parent.mkdir(parents=True)
    authored_agent.write_text("project-authored\n")
    assert _git(target, "init", "-q").returncode == 0
    assert _git(target, "add", ".github/agents/reviewer.agent.md").returncode == 0

    copy_generated_tree(source, target, dry_run=False)

    assert authored_agent.read_text() == "project-authored\n"


@pytest.mark.parametrize(
    "relation", ("equal", "source-inside-target", "target-inside-source")
)
@pytest.mark.parametrize("dry_run", (False, True), ids=("write", "dry-run"))
def test_installer_rejects_overlapping_roots_before_writes(
    tmp_path: Path, relation: str, dry_run: bool
) -> None:
    """Every overlap direction fails before legacy migration or generated copying."""
    if relation == "equal":
        source = target = tmp_path / "same"
    elif relation == "source-inside-target":
        target = tmp_path / "consumer"
        source = target / "generated"
    else:
        source = tmp_path / "generated"
        target = source / "consumer"
    source.mkdir(parents=True)
    marker = target / ".claude" / "MEMORY.md"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("consumer state\n")
    before = _tree_snapshot(tmp_path)
    command = [sys.executable, str(INSTALLER), str(target), "--source", str(source)]
    if dry_run:
        command.append("--dry-run")

    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "must be separate, non-overlapping directories" in result.stderr
    assert _tree_snapshot(tmp_path) == before
    assert not (target / ".claude" / ".git").exists()


def test_committed_to_local_copilot_migration_refreshes_owned_files(
    tmp_path: Path,
) -> None:
    """Explicit local mode refreshes prior bootstrap-owned tracked Copilot bytes."""
    target = tmp_path / "consumer"
    target.mkdir()
    assert _git(target, "init", "-q").returncode == 0
    first = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            str(target),
            "--source",
            str(GENERATED),
            "--commit-copilot-surface",
            "--local-only",
        ],
        cwd=REPO_ROOT,
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert first.returncode == 0, first.stdout + first.stderr

    agent_relative = Path(".github/agents/orchestrator.agent.md")
    agent = target / agent_relative
    obsolete_relative = Path(".github/agents/removed.agent.md")
    obsolete = target / obsolete_relative
    assert agent.is_file()
    obsolete.write_text("obsolete bootstrap file\n")
    assert _git(target, "add", ".github").returncode == 0
    agent.write_text("stale tracked bootstrap file\n")

    migrated = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            str(target),
            "--source",
            str(GENERATED),
            "--no-commit-copilot-surface",
            "--local-only",
        ],
        cwd=REPO_ROOT,
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert migrated.returncode == 0, migrated.stdout + migrated.stderr
    expected = (GENERATED / agent_relative).read_bytes()
    assert agent.read_bytes() == expected
    assert (
        target / ".claude" / "bootstrap-root" / agent_relative
    ).read_bytes() == expected
    assert not obsolete.exists()
    assert not (target / ".claude" / "bootstrap-root" / obsolete_relative).exists()
    manifest = (target / ".claude" / "bootstrap-ownership.env").read_text()
    assert "BOOTSTRAP_COMMIT_COPILOT_SURFACE=0\n" in manifest
