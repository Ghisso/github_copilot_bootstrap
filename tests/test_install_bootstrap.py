"""Focused regressions for bootstrap installation ownership boundaries."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from install_bootstrap import (  # noqa: E402
    copy_generated_tree,
    substitute_project_name,
    substitute_python_version,
    validate_install_roots,
)

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


def test_substitutions_update_root_guidance_and_workspace_facts(tmp_path: Path) -> None:
    """Installer reconciles project and Python facts across generated guidance."""
    target = tmp_path / "example-consumer"
    project_fact = "**Project:** [TODO: project name and one-liner description]\n"
    python_facts = (
        "**Python:** 3.12+ | **Package Manager:** uv\n**Stack:** Python 3.12+ with uv\n"
    )
    for relative in (
        Path("CLAUDE.md"),
        Path("AGENTS.md"),
        Path(".claude/instructions/workspace.instructions.md"),
        Path(".claude/instructions/workspace.md"),
    ):
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(project_fact + python_facts)
    (target / "pyproject.toml").write_text('[project]\nrequires-python = ">=3.13"\n')

    substitute_project_name(target, dry_run=False)
    substitute_python_version(target, dry_run=False)

    for relative in (
        Path("CLAUDE.md"),
        Path("AGENTS.md"),
        Path(".claude/instructions/workspace.instructions.md"),
        Path(".claude/instructions/workspace.md"),
    ):
        text = (target / relative).read_text()
        assert "[TODO: project name" not in text
        assert "**Project:** example-consumer" in text
        assert "**Python:** 3.13+" in text
        assert "**Stack:** Python 3.13+ with uv" in text


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


def test_copy_preserves_tracked_authoring_root_adapters(tmp_path: Path) -> None:
    """Dogfood refreshes never overwrite either tracked root adapter."""
    source = tmp_path / "generated"
    target = tmp_path / "bootstrap-authoring"
    target.mkdir()
    assert _git(target, "init", "-q").returncode == 0
    for name in ("AGENTS.md", "CLAUDE.md"):
        (source / name).parent.mkdir(parents=True, exist_ok=True)
        (source / name).write_text(f"generated {name}\n")
        (target / name).write_text(f"authoring {name}\n")
        assert _git(target, "add", name).returncode == 0

    copy_generated_tree(source, target, dry_run=False)

    for name in ("AGENTS.md", "CLAUDE.md"):
        assert (target / name).read_text() == f"authoring {name}\n"


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


def test_installer_preserves_consumer_memory_bytes_on_refresh_and_migration(
    tmp_path: Path,
) -> None:
    """Consumer-owned MEMORY.md survives both supported installation paths."""
    memory = b"# Consumer memory\r\n\r\n- preserve \xff\x00 exact bytes\r\n"

    refreshed = tmp_path / "refreshed-consumer"
    refreshed.mkdir()
    assert _git(refreshed, "init", "-q").returncode == 0
    first_install = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            str(refreshed),
            "--source",
            str(GENERATED),
            "--local-only",
        ],
        cwd=REPO_ROOT,
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert first_install.returncode == 0, first_install.stdout + first_install.stderr
    refreshed_memory = refreshed / ".claude" / "MEMORY.md"
    refreshed_memory.write_bytes(memory)
    assert _git(refreshed / ".claude", "add", "MEMORY.md").returncode == 0
    assert (
        _git(
            refreshed / ".claude", "commit", "-q", "-m", "session: consumer memory"
        ).returncode
        == 0
    )

    update = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            str(refreshed),
            "--source",
            str(GENERATED),
            "--local-only",
        ],
        cwd=REPO_ROOT,
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert update.returncode == 0, update.stdout + update.stderr
    assert refreshed_memory.read_bytes() == memory
    refreshed_state = subprocess.run(
        ["git", "-C", str(refreshed / ".claude"), "show", "HEAD:MEMORY.md"],
        capture_output=True,
        check=False,
    )
    assert refreshed_state.returncode == 0
    assert refreshed_state.stdout == memory

    legacy = tmp_path / "legacy-consumer"
    legacy.mkdir()
    assert _git(legacy, "init", "-q").returncode == 0
    legacy_memory = legacy / ".claude" / "MEMORY.md"
    legacy_memory.parent.mkdir(parents=True)
    legacy_memory.write_bytes(memory)

    migration = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            str(legacy),
            "--source",
            str(GENERATED),
            "--local-only",
        ],
        cwd=REPO_ROOT,
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert migration.returncode == 0, migration.stdout + migration.stderr
    assert legacy_memory.read_bytes() == memory
    legacy_state = subprocess.run(
        ["git", "-C", str(legacy / ".claude"), "show", "HEAD:MEMORY.md"],
        capture_output=True,
        check=False,
    )
    assert legacy_state.returncode == 0
    assert legacy_state.stdout == memory


# --- --allow-self: the bootstrap repo refreshing its own dogfood overlay ----


def test_overlapping_roots_rejected_without_allow_self(tmp_path: Path) -> None:
    """Default stays fail-closed for every overlapping-root shape."""
    target = tmp_path / "repo"
    inside = target / "dist" / "multi-agent"
    for source in (target, inside):
        with pytest.raises(SystemExit) as excinfo:
            validate_install_roots(source, target)
        assert "non-overlapping" in str(excinfo.value)
    with pytest.raises(SystemExit) as excinfo:
        validate_install_roots(target, inside)
    assert "non-overlapping" in str(excinfo.value)


def test_rejection_without_the_flag_names_the_opt_in(tmp_path: Path) -> None:
    """A blocked dogfood refresh should say how to proceed deliberately."""
    target = tmp_path / "repo"
    with pytest.raises(SystemExit) as excinfo:
        validate_install_roots(target / "dist" / "multi-agent", target)
    assert "--allow-self" in str(excinfo.value)


def test_allow_self_permits_only_the_bootstrap_repo(tmp_path: Path) -> None:
    """Source inside target is permitted for this repo, refused elsewhere."""
    validate_install_roots(GENERATED, REPO_ROOT, allow_self=True)

    other = tmp_path / "someone-elses-repo"
    with pytest.raises(SystemExit) as excinfo:
        validate_install_roots(other / "dist" / "multi-agent", other, allow_self=True)
    assert "--allow-self only refreshes" in str(excinfo.value)


def test_allow_self_still_rejects_the_dangerous_overlaps() -> None:
    """The flag must not unlock installing a tree over or under itself."""
    with pytest.raises(SystemExit):
        validate_install_roots(REPO_ROOT, REPO_ROOT, allow_self=True)
    with pytest.raises(SystemExit):
        validate_install_roots(GENERATED, GENERATED / "nested", allow_self=True)


def test_separate_roots_are_unaffected_by_the_flag(tmp_path: Path) -> None:
    """Ordinary consumer installs behave identically with or without it."""
    consumer = tmp_path / "consumer"
    validate_install_roots(GENERATED, consumer)
    validate_install_roots(GENERATED, consumer, allow_self=True)


def test_local_client_settings_are_consumer_state() -> None:
    """`settings.local.json` is machine-local; a refresh must not delete it."""
    from runtime_ownership import is_consumer_state_path

    assert is_consumer_state_path("settings.local.json")
    assert is_consumer_state_path(".cache/context-mode/sessions/local.db")


def test_refresh_preserves_local_context_mode_cache_bytes(tmp_path: Path) -> None:
    source = tmp_path / "generated"
    target = tmp_path / "consumer"
    (source / ".claude/hooks").mkdir(parents=True)
    (source / ".claude/hooks/generated.txt").write_text("generated\n")
    cache = target / ".claude/.cache/context-mode/sessions/local.db"
    cache.parent.mkdir(parents=True)
    cache.write_bytes(b"local-cache\x00bytes")

    copy_generated_tree(source, target, dry_run=False)

    assert cache.read_bytes() == b"local-cache\x00bytes"


def test_fresh_install_gitignore_excludes_provenance_secret(tmp_path: Path) -> None:
    """context-mode-dispatch.sh creates its anti-forgery provenance secret
    (`.context-mode-provenance.secret`) at the consumer repository root,
    outside `.claude/`. A freshly-installed `.gitignore` must exclude it, or
    a routine `git add -A` at the consumer root commits the secret into the
    consumer's main history (MAJOR finding)."""
    target = tmp_path / "consumer"
    target.mkdir()
    assert _git(target, "init", "-q").returncode == 0

    result = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            str(target),
            "--source",
            str(GENERATED),
            "--local-only",
        ],
        cwd=REPO_ROOT,
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    gitignore = (target / ".gitignore").read_text(encoding="utf-8")
    assert ".context-mode-provenance.secret" in gitignore
