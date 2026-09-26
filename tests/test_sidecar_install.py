"""Failing-first coverage for the sidecar apply step (``install_sidecar``).

Every test here uses a real, temporary Git repository. ``git commit`` runs
in-process through pytest/subprocess, which the repository's own commit-gate
hook does not intercept (see ``docs/sidecar-provider-contract.md``). Tests
that simulate "the team commits a file inside a sidecar-owned unit" stage
that one path explicitly (never ``git add -A``) so the commit does not
accidentally sweep up a sidecar-owned file that a ``.gitignore`` change made
visible in the same step; that would silently turn a "team re-includes a
retained file" scenario into "team tracks the file", a different case.

``dist/sidecar`` is used as the source throughout: it is small (four
skills, two write roots, two bridges), real, and already self-contained
(``uv run python scripts/generate_targets.py --all`` regenerates it).
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import install_bootstrap  # noqa: E402
import sidecar_overlay as sidecar_overlay_module  # noqa: E402
from sidecar_overlay import (  # noqa: E402
    GitCheckIgnoreError,
    escape_exact_path,
    git_path,
    install_sidecar,
    uninstall_sidecar,
)
from sidecar_test_helpers import (  # noqa: E402
    _absolute_git_dir,
    _commit,
    _commit_staged,
    _exclude_path,
    _git,
    _init_repo,
    _manifest_path,
    _raise_at,
    _read_manifest,
    _status,
    patch_sidecar_skills,
)

INSTALLER = REPO_ROOT / "scripts" / "install_bootstrap.py"
SOURCE = REPO_ROOT / "dist" / "sidecar"
BAD_SOURCE = REPO_ROOT / "dist" / "multi-agent"


# --------------------------------------------------------------------------
# Helpers local to this file (the shared git/file helpers live in
# tests/sidecar_test_helpers.py)
# --------------------------------------------------------------------------


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _is_ignored(root: Path, relative_path: str) -> bool:
    return _git(root, "check-ignore", "-q", "--", relative_path).returncode == 0


def _insert_block_line(root: Path, line: str) -> None:
    """Hand-insert a raw line inside the sidecar's own BEGIN/END block, as a
    person or an older/newer bootstrap version might leave behind."""
    exclude_path = _exclude_path(root)
    marker = "# END ai-bootstrap sidecar"
    text = exclude_path.read_text(encoding="utf-8")
    assert marker in text
    exclude_path.write_text(text.replace(marker, f"{line}\n{marker}"), encoding="utf-8")


# --------------------------------------------------------------------------
# The team fixture: tracked config for all four clients
# --------------------------------------------------------------------------


def _build_team_repo(root: Path) -> None:
    _init_repo(root)
    _write(root / "CLAUDE.md", "# Team CLAUDE.md\nTEAM-CLAUDE-MARKER\n")
    _write(root / "AGENTS.md", "# Team AGENTS.md\nTEAM-AGENTS-MARKER\n")
    _write(root / "GEMINI.md", "# Team GEMINI.md\nTEAM-GEMINI-MARKER\n")
    _write(
        root / ".github" / "copilot-instructions.md",
        "TEAM-COPILOT-INSTRUCTIONS-MARKER\n",
    )
    _write(
        root / ".github" / "instructions" / "team.instructions.md",
        '---\napplyTo: "**"\n---\nTEAM-INSTRUCTIONS-MARKER\n',
    )
    _write(root / ".claude" / "settings.json", '{"team": true}\n')
    _write(
        root / ".claude" / "skills" / "team-claude-skill" / "SKILL.md",
        "---\nname: team-claude-skill\n---\nTEAM-CLAUDE-SKILL\n",
    )
    _write(
        root / ".agents" / "skills" / "team-agents-skill" / "SKILL.md",
        "---\nname: team-agents-skill\n---\nTEAM-AGENTS-SKILL\n",
    )
    _write(
        root / ".github" / "skills" / "team-github-skill" / "SKILL.md",
        "---\nname: team-github-skill\n---\nTEAM-GITHUB-SKILL\n",
    )
    _write(root / ".codex" / "config.toml", "# team codex config\n")
    _write(root / ".devcontainer" / "devcontainer.json", '{"name": "team"}\n')
    _write(root / ".gitignore", "*.log\n")
    _commit(root, "team fixture")


TEAM_TRACKED_PATHS = (
    "CLAUDE.md",
    "AGENTS.md",
    "GEMINI.md",
    ".github/copilot-instructions.md",
    ".github/instructions/team.instructions.md",
    ".claude/settings.json",
    ".claude/skills/team-claude-skill/SKILL.md",
    ".agents/skills/team-agents-skill/SKILL.md",
    ".github/skills/team-github-skill/SKILL.md",
    ".codex/config.toml",
    ".devcontainer/devcontainer.json",
    ".gitignore",
)


@pytest.fixture
def team_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    _build_team_repo(root)
    return root


# --------------------------------------------------------------------------
# Preflight aborts, before any write
# --------------------------------------------------------------------------


def test_missing_source_aborts_before_any_write(team_repo: Path) -> None:
    status_before = _status(team_repo)
    exit_code = install_sidecar(team_repo, team_repo / "does-not-exist")
    assert exit_code != 0
    assert _status(team_repo) == status_before


def test_source_not_a_sidecar_tree_aborts_before_any_write(team_repo: Path) -> None:
    status_before = _status(team_repo)
    exit_code = install_sidecar(team_repo, BAD_SOURCE)
    assert exit_code != 0
    assert _status(team_repo) == status_before
    assert not _manifest_path(team_repo).exists()
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()


def test_git_older_than_2_31_aborts(team_repo: Path, monkeypatch) -> None:
    monkeypatch.setattr(sidecar_overlay_module, "_git_version", lambda: (2, 30, 0))
    exit_code = install_sidecar(team_repo, SOURCE)
    assert exit_code != 0
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()


def test_target_not_top_level_of_worktree_aborts(team_repo: Path) -> None:
    exit_code = install_sidecar(team_repo / ".claude", SOURCE)
    assert exit_code != 0
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()


def test_linked_worktree_aborts(team_repo: Path, tmp_path: Path) -> None:
    linked = tmp_path / "linked-worktree"
    result = _git(
        team_repo, "worktree", "add", "-q", str(linked), "-b", "linked-branch"
    )
    assert result.returncode == 0, result.stderr
    exit_code = install_sidecar(linked, SOURCE)
    assert exit_code != 0
    assert not (linked / ".claude" / "skills" / "ponytail").exists()


def test_git_directory_on_another_filesystem_aborts(
    team_repo: Path, monkeypatch
) -> None:
    real_device_id = sidecar_overlay_module._device_id
    git_dir = (team_repo / ".git").resolve()

    def fake_device_id(path: Path) -> int:
        if Path(path).resolve() == git_dir:
            return real_device_id(path) + 1
        return real_device_id(path)

    monkeypatch.setattr(sidecar_overlay_module, "_device_id", fake_device_id)
    exit_code = install_sidecar(team_repo, SOURCE)
    assert exit_code != 0
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()


def test_invalid_manifest_aborts_with_remedy(team_repo: Path, capsys) -> None:
    _manifest_path(team_repo).write_text("{not valid json", encoding="utf-8")
    exit_code = install_sidecar(team_repo, SOURCE)
    assert exit_code != 0
    err = capsys.readouterr().err
    assert "aside and rerun with --mode sidecar" in err
    assert "adopted" in err


def test_symlinked_info_exclude_aborts(team_repo: Path, tmp_path: Path) -> None:
    exclude_path = team_repo / ".git" / "info" / "exclude"
    exclude_path.parent.mkdir(parents=True, exist_ok=True)
    elsewhere = tmp_path / "elsewhere-exclude"
    elsewhere.write_text("", encoding="utf-8")
    if exclude_path.exists() or exclude_path.is_symlink():
        exclude_path.unlink()
    exclude_path.symlink_to(elsewhere)
    exit_code = install_sidecar(team_repo, SOURCE)
    assert exit_code != 0
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()


def test_agents_skills_symlinked_to_claude_skills_aborts(team_repo: Path) -> None:
    shutil.rmtree(team_repo / ".agents" / "skills")
    (team_repo / ".agents" / "skills").symlink_to(
        team_repo / ".claude" / "skills", target_is_directory=True
    )
    exit_code = install_sidecar(team_repo, SOURCE)
    assert exit_code != 0
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()


# --------------------------------------------------------------------------
# Core invariants: pre-existing team content is never touched
# --------------------------------------------------------------------------


def test_tracked_team_config_for_all_four_clients_is_byte_identical_after_install(
    team_repo: Path,
) -> None:
    before = {path: (team_repo / path).read_bytes() for path in TEAM_TRACKED_PATHS}
    assert install_sidecar(team_repo, SOURCE) == 0
    after = {path: (team_repo / path).read_bytes() for path in TEAM_TRACKED_PATHS}
    assert after == before


def test_git_status_unchanged_by_sidecar_install(team_repo: Path) -> None:
    status_before = _status(team_repo)
    assert install_sidecar(team_repo, SOURCE) == 0
    assert _status(team_repo) == status_before


def test_gitignore_hooks_path_and_hook_files_unchanged(team_repo: Path) -> None:
    gitignore_before = (team_repo / ".gitignore").read_bytes()
    hooks_path_before = _git(team_repo, "config", "--get", "core.hooksPath")
    hooks_dir = team_repo / ".git" / "hooks"
    hook_files_before = (
        sorted(p.name for p in hooks_dir.glob("*")) if hooks_dir.is_dir() else []
    )

    assert install_sidecar(team_repo, SOURCE) == 0

    assert (team_repo / ".gitignore").read_bytes() == gitignore_before
    hooks_path_after = _git(team_repo, "config", "--get", "core.hooksPath")
    assert hooks_path_after.returncode == hooks_path_before.returncode
    assert hooks_path_after.stdout == hooks_path_before.stdout
    hook_files_after = (
        sorted(p.name for p in hooks_dir.glob("*")) if hooks_dir.is_dir() else []
    )
    assert hook_files_after == hook_files_before


def test_no_nested_git_repo_or_legacy_ai_bootstrap_folder_created(
    team_repo: Path,
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    assert not (team_repo / ".claude" / ".git").exists()
    assert not (team_repo / "ai-bootstrap").exists()


def test_ponytail_license_present_and_byte_equal_at_both_write_roots(
    team_repo: Path,
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    for write_root in (".claude/skills", ".agents/skills"):
        for skill in ("ponytail", "ponytail-review"):
            installed = team_repo / write_root / skill / "LICENSE"
            source_license = SOURCE / write_root / skill / "LICENSE"
            assert installed.is_file(), installed
            assert installed.read_bytes() == source_license.read_bytes()


def test_skill_taken_by_tracked_team_skill_is_skipped_at_both_roots_and_reported(
    team_repo: Path, capsys
) -> None:
    team_content = "---\nname: ponytail\n---\nTEAM-OWNED-PONYTAIL\n"
    _write(team_repo / ".claude" / "skills" / "ponytail" / "SKILL.md", team_content)
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team owns ponytail")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not (team_repo / ".agents" / "skills" / "ponytail").exists()
    team_file = team_repo / ".claude" / "skills" / "ponytail" / "SKILL.md"
    assert team_file.read_text(encoding="utf-8") == team_content
    out = capsys.readouterr().out
    assert "SKIPPED .claude/skills/ponytail" in out


def test_skill_taken_only_in_github_skills_is_skipped_at_both_write_roots(
    team_repo: Path, capsys
) -> None:
    _write(
        team_repo / ".github" / "skills" / "humanize" / "SKILL.md",
        "---\nname: humanize\n---\nTEAM-OWNED-IN-GITHUB\n",
    )
    _commit(
        team_repo, "team owns humanize in .github/skills", ".github/skills/humanize"
    )

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not (team_repo / ".claude" / "skills" / "humanize").exists()
    assert not (team_repo / ".agents" / "skills" / "humanize").exists()
    out = capsys.readouterr().out
    assert "SKIPPED .github/skills/humanize" in out


def test_team_tracked_skill_with_no_manifest_record_gets_no_exclude_line(
    team_repo: Path,
) -> None:
    _write(
        team_repo / ".claude" / "skills" / "ponytail" / "SKILL.md",
        "team-owned, first run, never recorded\n",
    )
    _commit(team_repo, "team owns ponytail", ".claude/skills/ponytail")

    assert install_sidecar(team_repo, SOURCE) == 0

    exclude_text = _exclude_path(team_repo).read_text(encoding="utf-8")
    assert "/.claude/skills/ponytail\n" not in exclude_text


def test_foreign_untracked_skill_directory_is_left_alone(team_repo: Path) -> None:
    foreign = team_repo / ".claude" / "skills" / "not-a-sidecar-skill" / "SKILL.md"
    _write(foreign, "unrelated content\n")
    before = foreign.read_bytes()

    assert install_sidecar(team_repo, SOURCE) == 0

    assert foreign.read_bytes() == before
    assert ".claude/skills/not-a-sidecar-skill/" in _status(team_repo)


def test_visible_untracked_copy_identical_to_sidecar_is_foreign_not_adopted(
    team_repo: Path, capsys
) -> None:
    skill_md = (SOURCE / ".claude" / "skills" / "humanize" / "SKILL.md").read_bytes()
    destination = team_repo / ".claude" / "skills" / "humanize" / "SKILL.md"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(skill_md)

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    # Foreign at one write root taken the skill name everywhere (Decision 8),
    # so the sibling copy at the other write root is not installed either.
    assert not (team_repo / ".agents" / "skills" / "humanize").exists()
    assert destination.read_bytes() == skill_md
    assert ".claude/skills/humanize/" in _status(team_repo)
    out = capsys.readouterr().out
    assert "will not replace" in out
    exclude_text = _exclude_path(team_repo).read_text(encoding="utf-8")
    assert "/.claude/skills/humanize\n" not in exclude_text


def test_bridge_path_already_occupied_is_skipped_and_reported(
    team_repo: Path, capsys
) -> None:
    bridge_path = team_repo / ".claude" / "rules" / "ai-bootstrap-sidecar.md"
    _write(bridge_path, "someone else's rule file\n")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert bridge_path.read_text(encoding="utf-8") == "someone else's rule file\n"
    out = capsys.readouterr().out
    assert "SKIPPED .claude/rules/ai-bootstrap-sidecar.md" in out


# --------------------------------------------------------------------------
# The ignore gate (Decision 17)
# --------------------------------------------------------------------------


def test_team_gitignore_negation_of_sidecar_skills_aborts_and_restores_exclude(
    team_repo: Path, capsys
) -> None:
    gitignore = team_repo / ".gitignore"
    _write(gitignore, gitignore.read_text(encoding="utf-8") + "!.claude/skills/**\n")
    _commit(team_repo, "team un-ignores .claude/skills", ".gitignore")
    status_before = _status(team_repo)
    exclude_before = (
        _exclude_path(team_repo).read_bytes()
        if _exclude_path(team_repo).is_file()
        else None
    )

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code != 0
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()
    assert not _manifest_path(team_repo).exists()
    exclude_after = (
        _exclude_path(team_repo).read_bytes()
        if _exclude_path(team_repo).is_file()
        else None
    )
    assert exclude_after == exclude_before
    assert _status(team_repo) == status_before
    assert "ABORT" in capsys.readouterr().err


def test_team_gitignore_negation_aborts_the_same_way_with_dry_run(
    team_repo: Path,
) -> None:
    gitignore = team_repo / ".gitignore"
    _write(gitignore, gitignore.read_text(encoding="utf-8") + "!.claude/skills/**\n")
    _commit(team_repo, "team un-ignores .claude/skills", ".gitignore")
    status_before = _status(team_repo)

    exit_code = install_sidecar(team_repo, SOURCE, dry_run=True)

    assert exit_code != 0
    assert _status(team_repo) == status_before
    assert not _manifest_path(team_repo).exists()
    assert not git_path(team_repo, "ai-bootstrap-sidecar-staging").exists()


def test_partial_ignore_negation_is_caught_despite_stdin_exit_zero_trap(
    team_repo: Path,
) -> None:
    # A plain `git check-ignore --stdin` (no full-set comparison) exits 0 as
    # soon as ANY one of the piped paths is ignored; ponytail's own line
    # still matches here, so that trap would report success. The gate must
    # still fail because humanize does not match its own line any more.
    gitignore = team_repo / ".gitignore"
    _write(
        gitignore,
        gitignore.read_text(encoding="utf-8") + "!/.claude/skills/humanize\n",
    )
    _commit(team_repo, "team un-ignores only humanize", ".gitignore")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code != 0
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()
    assert not (team_repo / ".claude" / "skills" / "humanize").exists()


NAMES_NEEDING_ESCAPE = [
    "glob[1].txt",
    "wild*card.txt",
    "ques?tion.txt",
    "!bang.txt",
    "#hash.txt",
    "trailing space.txt ",
    "héllo.txt",
    "back\\slash.txt",
]


def test_retained_names_with_special_characters_are_each_hidden_exactly(
    team_repo: Path,
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    unit_dir = team_repo / ".claude" / "skills" / "humanize"
    for name in NAMES_NEEDING_ESCAPE:
        (unit_dir / name).write_bytes(b"extra\n")
    decoy = team_repo / "decoy-outside-unit.txt"
    decoy.write_bytes(b"must never be hidden\n")

    # SKILL.md is still hidden by the unit's own directory-level exclude
    # line at this point, so tracking it needs a forced add (real teams do
    # this via checkout/merge; `-f` reproduces "now tracked" directly).
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/humanize/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team takes humanize SKILL.md")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    manifest = _read_manifest(team_repo)
    expected = {f".claude/skills/humanize/{name}" for name in NAMES_NEEDING_ESCAPE}
    assert set(manifest["retained"]) == expected
    for name in NAMES_NEEDING_ESCAPE:
        assert _is_ignored(team_repo, f".claude/skills/humanize/{name}")
    assert not _is_ignored(team_repo, "decoy-outside-unit.txt")
    status = _status(team_repo)
    assert status == "?? decoy-outside-unit.txt\n"


def test_team_gitignore_re_including_a_retained_file_aborts_before_any_unit_write(
    team_repo: Path,
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    scratch = team_repo / ".claude" / "skills" / "humanize" / "scratch.txt"
    scratch.write_bytes(b"kept by a person\n")
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/humanize/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit(team_repo, "team takes humanize SKILL.md")
    assert install_sidecar(team_repo, SOURCE) == 0

    manifest_before = _read_manifest(team_repo)
    assert manifest_before["retained"] == [".claude/skills/humanize/scratch.txt"]
    exclude_before = _exclude_path(team_repo).read_bytes()

    gitignore = team_repo / ".gitignore"
    _write(
        gitignore,
        gitignore.read_text(encoding="utf-8")
        + "!/.claude/skills/humanize/scratch.txt\n",
    )
    # Stage only .gitignore: the negation genuinely un-ignores scratch.txt,
    # and "git add -A" would sweep it into tracking too, which would turn
    # this into "the team commits the retained file" instead of the
    # "re-included but still untracked" case this test targets.
    _commit(team_repo, "team un-ignores the retained file", ".gitignore")

    status_before = _status(team_repo)
    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code != 0
    assert _exclude_path(team_repo).read_bytes() == exclude_before
    assert _status(team_repo) == status_before
    assert _read_manifest(team_repo) == manifest_before


# --------------------------------------------------------------------------
# Team takeover and rerun mechanics
# --------------------------------------------------------------------------


def test_team_checkout_tracks_one_file_keeps_git_status_unchanged(
    team_repo: Path,
) -> None:
    # ponytail has two files (SKILL.md, LICENSE), so tracking only SKILL.md
    # leaves LICENSE untracked and still hash-matching the record: this is
    # the one scenario that actually exercises team_takeover_delete.
    assert install_sidecar(team_repo, SOURCE) == 0
    status_before_takeover = _status(team_repo)
    unit_dir = team_repo / ".claude" / "skills" / "ponytail"
    license_path = unit_dir / "LICENSE"
    user_file = unit_dir / "user-notes.txt"
    # Untracked, hidden by the unit's own directory-level exclude line, and
    # does not match any recorded file: retained, not deleted.
    user_file.write_bytes(b"kept by a person\n")

    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team checkout tracks ponytail/SKILL.md")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not license_path.exists()
    assert user_file.exists()
    assert _is_ignored(team_repo, ".claude/skills/ponytail/user-notes.txt")
    skill_md = unit_dir / "SKILL.md"
    assert (
        skill_md.read_bytes()
        == (SOURCE / ".claude" / "skills" / "ponytail" / "SKILL.md").read_bytes()
    )
    assert not (team_repo / ".agents" / "skills" / "ponytail").exists()

    manifest = _read_manifest(team_repo)
    assert ".claude/skills/ponytail" not in manifest["units"]
    assert manifest["retained"] == [".claude/skills/ponytail/user-notes.txt"]

    exclude_text = _exclude_path(team_repo).read_text(encoding="utf-8")
    assert "/.claude/skills/ponytail\n" not in exclude_text
    assert "/.claude/skills/ponytail/LICENSE" not in exclude_text
    assert (
        escape_exact_path(".claude/skills/ponytail/user-notes.txt") + "\n"
        in exclude_text
    )

    assert _status(team_repo) == status_before_takeover


def test_manifest_moved_aside_after_good_install_then_rerun_adopts_units(
    team_repo: Path,
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    before_manifest = _read_manifest(team_repo)
    before_tree = {
        path.relative_to(team_repo): path.read_bytes()
        for path in (team_repo / ".claude").rglob("*")
        if path.is_file()
    }
    manifest_path = _manifest_path(team_repo)
    manifest_path.rename(manifest_path.with_name(manifest_path.name + ".bak"))

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    after_manifest = _read_manifest(team_repo)
    assert after_manifest["units"] == before_manifest["units"]
    after_tree = {
        path.relative_to(team_repo): path.read_bytes()
        for path in (team_repo / ".claude").rglob("*")
        if path.is_file()
    }
    assert after_tree == before_tree


def test_one_file_changed_after_good_install_then_rerun_reports_locally_modified(
    team_repo: Path, capsys
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    skill_md = team_repo / ".claude" / "skills" / "humanize" / "SKILL.md"
    skill_md.write_text(
        skill_md.read_text(encoding="utf-8") + "\nEDITED BY A PERSON\n",
        encoding="utf-8",
    )
    edited_bytes = skill_md.read_bytes()

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert skill_md.read_bytes() == edited_bytes
    manifest = _read_manifest(team_repo)
    assert ".claude/skills/humanize" in manifest["units"]
    out = capsys.readouterr().out
    assert "has local edits" in out
    assert "copy your edits elsewhere" in out


def test_rerun_with_no_upstream_change_writes_nothing(team_repo: Path) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    exclude_path = _exclude_path(team_repo)
    manifest_path = _manifest_path(team_repo)
    before = {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in (exclude_path, manifest_path)
    }

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    for path, (data, mtime) in before.items():
        assert path.read_bytes() == data
        assert path.stat().st_mtime_ns == mtime, f"{path} was rewritten unnecessarily"


# --------------------------------------------------------------------------
# Dry-run
# --------------------------------------------------------------------------


def test_dry_run_leaves_worktree_exclude_manifest_and_staging_unchanged(
    team_repo: Path,
) -> None:
    status_before = _status(team_repo)
    exclude_path = _exclude_path(team_repo)
    exclude_before = exclude_path.read_bytes() if exclude_path.is_file() else None

    exit_code = install_sidecar(team_repo, SOURCE, dry_run=True)

    assert exit_code == 0
    assert _status(team_repo) == status_before
    exclude_after = exclude_path.read_bytes() if exclude_path.is_file() else None
    assert exclude_after == exclude_before
    assert not _manifest_path(team_repo).exists()
    assert not git_path(team_repo, "ai-bootstrap-sidecar-staging").exists()
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()


# --------------------------------------------------------------------------
# Fault injection: the three named checkpoints, each proving rerun recovery
# --------------------------------------------------------------------------


def test_fault_before_manifest_write_rerun_adopts_the_unit(
    team_repo: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        sidecar_overlay_module, "_fault_point", _raise_at("before_manifest_write")
    )
    with pytest.raises(RuntimeError, match="before_manifest_write"):
        install_sidecar(team_repo, SOURCE)
    capsys.readouterr()

    # Pre-rerun state: units already fully written, exclude block already
    # final, but the manifest never landed.
    assert (team_repo / ".claude" / "skills" / "ponytail").is_dir()
    assert not _manifest_path(team_repo).exists()
    exclude_text = _exclude_path(team_repo).read_text(encoding="utf-8")
    assert "/.claude/skills/ponytail\n" in exclude_text

    monkeypatch.setattr(sidecar_overlay_module, "_fault_point", lambda name: None)
    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "SKIPPED" not in out
    assert "adopted 10" in out
    manifest = _read_manifest(team_repo)
    assert len(manifest["units"]) == 10


def test_fault_mid_unit_swap_rerun_installs_the_unit(
    team_repo: Path, tmp_path: Path, monkeypatch
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    mutated_source = tmp_path / "mutated-source"
    shutil.copytree(SOURCE, mutated_source)
    mutated_file = mutated_source / ".claude" / "skills" / "humanize" / "SKILL.md"
    mutated_file.write_text(
        mutated_file.read_text(encoding="utf-8") + "\nmutated upstream\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sidecar_overlay_module, "_fault_point", _raise_at("mid_unit_swap")
    )
    with pytest.raises(RuntimeError, match="mid_unit_swap"):
        install_sidecar(team_repo, mutated_source)

    # Pre-rerun state: the old copy was moved out before the crash, so the
    # unit is absent from the worktree (both the old and the built new copy
    # sit in staging).
    assert not (team_repo / ".claude" / "skills" / "humanize").exists()
    staging = git_path(team_repo, "ai-bootstrap-sidecar-staging")
    assert any(staging.iterdir())

    monkeypatch.setattr(sidecar_overlay_module, "_fault_point", lambda name: None)
    exit_code = install_sidecar(team_repo, mutated_source)

    assert exit_code == 0
    content = (team_repo / ".claude" / "skills" / "humanize" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "mutated upstream" in content
    assert not any(staging.iterdir())


def test_fault_after_takeover_exclude_write_rerun_deletes_matching_files_keeps_retained(
    team_repo: Path, monkeypatch, capsys
) -> None:
    # ponytail has two files (SKILL.md, LICENSE): tracking SKILL.md leaves
    # LICENSE untracked and hash-matching, which is what team_takeover_delete
    # actually deletes; a one-file unit never exercises that code path.
    assert install_sidecar(team_repo, SOURCE) == 0
    unit_dir = team_repo / ".claude" / "skills" / "ponytail"
    license_path = unit_dir / "LICENSE"
    user_file = unit_dir / "user-notes.txt"
    user_file.write_bytes(b"kept by a person\n")

    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team takes ponytail SKILL.md")

    monkeypatch.setattr(
        sidecar_overlay_module, "_fault_point", _raise_at("after_exclude_write")
    )
    with pytest.raises(RuntimeError, match="after_exclude_write"):
        install_sidecar(team_repo, SOURCE)
    capsys.readouterr()

    # Pre-rerun state: the takeover exclude write already ran (both files
    # already have their own lines), but neither was deleted yet.
    assert license_path.exists()
    assert user_file.exists()
    assert _is_ignored(team_repo, ".claude/skills/ponytail/LICENSE")
    assert _is_ignored(team_repo, ".claude/skills/ponytail/user-notes.txt")

    monkeypatch.setattr(sidecar_overlay_module, "_fault_point", lambda name: None)
    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not license_path.exists()
    assert user_file.exists()
    assert _is_ignored(team_repo, ".claude/skills/ponytail/user-notes.txt")
    manifest = _read_manifest(team_repo)
    assert manifest["retained"] == [".claude/skills/ponytail/user-notes.txt"]


# --------------------------------------------------------------------------
# End-to-end through the installer CLI (mode detection + dispatch)
# --------------------------------------------------------------------------


def test_cli_invalid_manifest_with_no_mode_aborts_with_remedy(team_repo: Path) -> None:
    _manifest_path(team_repo).write_text("{not valid json", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(INSTALLER), str(team_repo)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "aside and rerun with --mode sidecar" in result.stderr


def test_cli_sidecar_evidence_with_no_mode_takes_sidecar_path(team_repo: Path) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0

    result = subprocess.run(
        [sys.executable, str(INSTALLER), str(team_repo)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "sidecar-install:" in result.stdout
    assert "install-bootstrap:" not in result.stdout
    assert not (team_repo / ".claude" / ".git").exists()


def test_cli_mode_sidecar_with_multi_agent_source_aborts_before_any_write(
    team_repo: Path,
) -> None:
    status_before = _status(team_repo)

    result = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            str(team_repo),
            "--mode",
            "sidecar",
            "--source",
            str(BAD_SOURCE),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert _status(team_repo) == status_before
    assert not _manifest_path(team_repo).exists()


# --------------------------------------------------------------------------
# Phase G step 1: ownership from the Git index (Decision 25; R4)
# --------------------------------------------------------------------------


def _second_run_and_dry_run_are_stable(team_repo: Path) -> None:
    """Shared post-condition: a second run changes nothing, and a dry run
    predicts the same result as the run that already happened."""
    status_before = _status(team_repo)
    exclude_before = _exclude_path(team_repo).read_bytes()
    manifest_before = (
        _manifest_path(team_repo).read_bytes()
        if _manifest_path(team_repo).is_file()
        else None
    )
    assert install_sidecar(team_repo, SOURCE) == 0
    assert _status(team_repo) == status_before
    assert _exclude_path(team_repo).read_bytes() == exclude_before
    manifest_after = (
        _manifest_path(team_repo).read_bytes()
        if _manifest_path(team_repo).is_file()
        else None
    )
    assert manifest_after == manifest_before
    assert install_sidecar(team_repo, SOURCE, dry_run=True) == 0
    assert _status(team_repo) == status_before


def test_tracked_skill_folder_deleted_from_disk_stays_team_owned(
    team_repo: Path, capsys
) -> None:
    team_content = "---\nname: ponytail\n---\nTEAM-OWNED-PONYTAIL\n"
    _write(team_repo / ".claude" / "skills" / "ponytail" / "SKILL.md", team_content)
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team owns ponytail")
    shutil.rmtree(team_repo / ".claude" / "skills" / "ponytail")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    # The local deletion stays: nothing is written into or checked out at
    # the tracked path, and nothing is installed there or at the sibling
    # write root (Decision 25: ownership comes from the index, not disk).
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()
    assert not (team_repo / ".agents" / "skills" / "ponytail").exists()
    status = _git(team_repo, "status", "--short", "--", ".claude/skills/ponytail")
    assert " D .claude/skills/ponytail/SKILL.md" in status.stdout
    out = capsys.readouterr().out
    assert "the repository tracks" in out
    assert "ponytail" in out
    _second_run_and_dry_run_are_stable(team_repo)


def test_only_one_tracked_file_deleted_leaves_empty_folder_still_team_owned(
    team_repo: Path, capsys
) -> None:
    team_content = "---\nname: ponytail\n---\nTEAM-OWNED-PONYTAIL-ONE-FILE\n"
    skill_md = team_repo / ".claude" / "skills" / "ponytail" / "SKILL.md"
    _write(skill_md, team_content)
    _commit(team_repo, "team owns ponytail SKILL.md only", ".claude/skills/ponytail")
    skill_md.unlink()  # empty folder left behind, SKILL.md stays in the index

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not skill_md.exists()
    assert not any((team_repo / ".claude" / "skills" / "ponytail").iterdir())
    assert not (team_repo / ".agents" / "skills" / "ponytail").exists()
    out = capsys.readouterr().out
    assert "the repository tracks" in out
    _second_run_and_dry_run_are_stable(team_repo)


def test_gitlink_at_skill_path_with_no_folder_is_team_owned(
    team_repo: Path, capsys
) -> None:
    """Decision 37: a gitlink unit is team-owned, but the report must say
    the sidecar never touches files inside a submodule, not the ordinary
    team-owned wording (which implies the sidecar inspected the content)."""
    fake_commit = "a" * 40
    cacheinfo = _git(
        team_repo,
        "update-index",
        "--add",
        "--cacheinfo",
        f"160000,{fake_commit},.claude/skills/ponytail",
    )
    assert cacheinfo.returncode == 0, cacheinfo.stderr
    _commit_staged(team_repo, "team embeds ponytail as a gitlink")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()
    assert not (team_repo / ".agents" / "skills" / "ponytail").exists()
    out = capsys.readouterr().out
    assert "is a submodule; the sidecar never touches files inside a submodule" in out
    _second_run_and_dry_run_are_stable(team_repo)


def test_tracked_symlink_at_skill_path_is_team_owned_not_aborted(
    team_repo: Path, capsys
) -> None:
    unit_dir = team_repo / ".claude" / "skills" / "ponytail"
    unit_dir.parent.mkdir(parents=True, exist_ok=True)
    elsewhere = team_repo / "team-owned-elsewhere"
    elsewhere.mkdir()
    (elsewhere / "SKILL.md").write_text("team symlinked skill\n", encoding="utf-8")
    unit_dir.symlink_to(elsewhere, target_is_directory=True)
    _commit(team_repo, "team tracks a symlinked skill", ".claude/skills/ponytail")

    exit_code = install_sidecar(team_repo, SOURCE)

    # A tracked symlink at a unit path is team-owned, not an abort
    # (Decision 25): the run must still finish and install every other unit.
    assert exit_code == 0
    assert unit_dir.is_symlink()
    assert not (team_repo / ".agents" / "skills" / "ponytail").exists()
    assert (team_repo / ".claude" / "skills" / "humanize").is_dir()
    out = capsys.readouterr().out
    assert "the repository tracks" in out


def test_untracked_symlink_at_skill_path_is_foreign_not_aborted(
    team_repo: Path, capsys
) -> None:
    unit_dir = team_repo / ".claude" / "skills" / "ponytail"
    unit_dir.parent.mkdir(parents=True, exist_ok=True)
    elsewhere = team_repo / "personal-elsewhere"
    elsewhere.mkdir()
    (elsewhere / "SKILL.md").write_text("a personal symlinked copy\n", encoding="utf-8")
    unit_dir.symlink_to(elsewhere, target_is_directory=True)

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert unit_dir.is_symlink()
    assert unit_dir.resolve() == elsewhere.resolve()
    assert not (team_repo / ".agents" / "skills" / "ponytail").exists()
    assert (team_repo / ".claude" / "skills" / "humanize").is_dir()
    out = capsys.readouterr().out
    assert "will not replace" in out


def test_tracked_github_skills_entry_deleted_from_disk_still_taken(
    team_repo: Path, capsys
) -> None:
    github_skill = team_repo / ".github" / "skills" / "humanize" / "SKILL.md"
    _write(github_skill, "---\nname: humanize\n---\nTEAM-OWNED-IN-GITHUB\n")
    _commit(
        team_repo, "team owns humanize in .github/skills", ".github/skills/humanize"
    )
    shutil.rmtree(team_repo / ".github" / "skills" / "humanize")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not (team_repo / ".claude" / "skills" / "humanize").exists()
    assert not (team_repo / ".agents" / "skills" / "humanize").exists()
    out = capsys.readouterr().out
    assert "SKIPPED .github/skills/humanize" in out


# --------------------------------------------------------------------------
# Phase G step 2 follow-up: R1 siblings as real-git scenarios
# --------------------------------------------------------------------------


def test_r1_sibling_fault_before_manifest_write_then_team_collision_committed(
    team_repo: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        sidecar_overlay_module, "_fault_point", _raise_at("before_manifest_write")
    )
    with pytest.raises(RuntimeError, match="before_manifest_write"):
        install_sidecar(team_repo, SOURCE)
    capsys.readouterr()
    monkeypatch.setattr(sidecar_overlay_module, "_fault_point", lambda name: None)

    # Pre-rerun state: units are fully written and listed, but no manifest.
    assert (team_repo / ".claude" / "skills" / "ponytail").is_dir()
    assert not _manifest_path(team_repo).exists()

    team_skill = team_repo / ".github" / "skills" / "ponytail" / "SKILL.md"
    team_skill.parent.mkdir(parents=True, exist_ok=True)
    team_skill.write_text("---\nname: ponytail\n---\nTEAM-OWNED\n", encoding="utf-8")
    _commit(
        team_repo, "team tracks ponytail in .github/skills", ".github/skills/ponytail"
    )

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()
    assert not (team_repo / ".agents" / "skills" / "ponytail").exists()
    manifest = _read_manifest(team_repo)
    assert ".claude/skills/ponytail" not in manifest["units"]
    assert ".agents/skills/ponytail" not in manifest["units"]
    exclude_text = _exclude_path(team_repo).read_text(encoding="utf-8")
    assert "/.claude/skills/ponytail\n" not in exclude_text
    assert "/.agents/skills/ponytail\n" not in exclude_text
    out = capsys.readouterr().out
    assert "SKIPPED .github/skills/ponytail" in out

    status_before = _status(team_repo)
    assert install_sidecar(team_repo, SOURCE) == 0
    assert _status(team_repo) == status_before


def test_r1_sibling_adoptable_copy_at_one_root_foreign_copy_at_other(
    team_repo: Path, capsys
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    manifest_path = _manifest_path(team_repo)
    manifest_path.rename(manifest_path.with_name(manifest_path.name + ".bak"))

    # Strip .agents/skills/ponytail's own line from the exclude block (a
    # partially corrupted block, on top of the lost manifest) and edit its
    # content so it also no longer matches the desired bytes: genuinely
    # foreign there, never merely "unfinished". .claude/skills/ponytail
    # keeps its line and matches the desired content: adoptable.
    exclude_path = _exclude_path(team_repo)
    agents_line = escape_exact_path(".agents/skills/ponytail")
    exclude_text = exclude_path.read_text(encoding="utf-8")
    assert f"{agents_line}\n" in exclude_text
    exclude_path.write_text(
        exclude_text.replace(f"{agents_line}\n", ""), encoding="utf-8"
    )

    agents_skill_md = team_repo / ".agents" / "skills" / "ponytail" / "SKILL.md"
    agents_skill_md.write_text(
        agents_skill_md.read_text(encoding="utf-8") + "\nEDITED-BY-A-PERSON\n",
        encoding="utf-8",
    )
    edited_bytes = agents_skill_md.read_bytes()

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    # The adoptable copy is removed once the skill is taken by the foreign
    # collision at the other root (R1: the old collision loop missed
    # "adopt", so it stayed installed while the report claimed a skip).
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()
    assert agents_skill_md.read_bytes() == edited_bytes  # foreign: left alone
    manifest = _read_manifest(team_repo)
    assert ".claude/skills/ponytail" not in manifest["units"]
    assert ".agents/skills/ponytail" not in manifest["units"]
    out = capsys.readouterr().out
    assert "will not replace" in out

    status_before = _status(team_repo)
    assert install_sidecar(team_repo, SOURCE) == 0
    assert _status(team_repo) == status_before


def test_r1_sibling_adoptable_copy_at_one_root_team_tracked_copy_at_other(
    team_repo: Path, capsys
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    manifest_path = _manifest_path(team_repo)
    manifest_path.rename(manifest_path.with_name(manifest_path.name + ".bak"))

    force_add = _git(team_repo, "add", "-f", "--", ".agents/skills/ponytail/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team takes over .agents/skills/ponytail")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()
    assert (team_repo / ".agents" / "skills" / "ponytail" / "SKILL.md").is_file()
    manifest = _read_manifest(team_repo)
    assert ".claude/skills/ponytail" not in manifest["units"]
    assert ".agents/skills/ponytail" not in manifest["units"]
    out = capsys.readouterr().out
    assert "the repository tracks" in out

    status_before = _status(team_repo)
    assert install_sidecar(team_repo, SOURCE) == 0
    assert _status(team_repo) == status_before


# --------------------------------------------------------------------------
# Phase G step 1 follow-up: more index-ownership real-git scenarios
# --------------------------------------------------------------------------


def test_sparse_checkout_without_the_team_skill_is_still_team_owned(
    tmp_path: Path, capsys
) -> None:
    root = tmp_path / "sparse-repo"
    _init_repo(root)
    team_content = "---\nname: ponytail\n---\nTEAM-OWNED-PONYTAIL\n"
    _write(root / ".claude" / "skills" / "ponytail" / "SKILL.md", team_content)
    _write(root / "README.md", "# repo\n")
    _commit(root, "team owns ponytail")

    init_sparse = _git(root, "sparse-checkout", "init", "--cone")
    assert init_sparse.returncode == 0, init_sparse.stderr
    set_sparse = _git(root, "sparse-checkout", "set")  # cone: root files only
    assert set_sparse.returncode == 0, set_sparse.stderr
    assert not (root / ".claude" / "skills" / "ponytail").exists()
    ls = _git(root, "ls-files", "--", ".claude/skills/ponytail/SKILL.md")
    assert ls.stdout.strip() == ".claude/skills/ponytail/SKILL.md"

    exit_code = install_sidecar(root, SOURCE)

    assert exit_code == 0
    assert not (root / ".claude" / "skills" / "ponytail").exists()
    assert not (root / ".agents" / "skills" / "ponytail").exists()
    assert (root / ".claude" / "skills" / "humanize").is_dir()
    out = capsys.readouterr().out
    assert "the repository tracks" in out


def test_skip_worktree_entry_is_still_team_owned(team_repo: Path, capsys) -> None:
    team_content = "---\nname: ponytail\n---\nTEAM-OWNED-PONYTAIL\n"
    _write(team_repo / ".claude" / "skills" / "ponytail" / "SKILL.md", team_content)
    _commit(team_repo, "team owns ponytail", ".claude/skills/ponytail")
    skip = _git(
        team_repo,
        "update-index",
        "--skip-worktree",
        ".claude/skills/ponytail/SKILL.md",
    )
    assert skip.returncode == 0, skip.stderr
    shutil.rmtree(team_repo / ".claude" / "skills" / "ponytail")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()
    assert not (team_repo / ".agents" / "skills" / "ponytail").exists()
    out = capsys.readouterr().out
    assert "the repository tracks" in out
    ls = _git(team_repo, "ls-files", "-v", "--", ".claude/skills/ponytail/SKILL.md")
    assert ls.stdout.startswith("S ")  # skip-worktree bit preserved


def test_team_takeover_then_person_deletes_the_tracked_file_stays_team_owned(
    team_repo: Path, capsys
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team takes over ponytail")
    assert install_sidecar(team_repo, SOURCE) == 0  # the takeover reconciliation run
    assert not (team_repo / ".claude" / "skills" / "ponytail" / "LICENSE").exists()
    capsys.readouterr()  # discard earlier runs' output, so `out` below is only this run

    (team_repo / ".claude" / "skills" / "ponytail" / "SKILL.md").unlink()
    status_before = _status(team_repo)

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not (team_repo / ".claude" / "skills" / "ponytail" / "SKILL.md").exists()
    assert not (team_repo / ".agents" / "skills" / "ponytail").exists()
    out = capsys.readouterr().out
    assert "the repository tracks" in out
    assert _status(team_repo) == status_before


def test_tracked_bridge_deleted_locally_stays_team_owned(
    team_repo: Path, capsys
) -> None:
    bridge_path = team_repo / ".claude" / "rules" / "ai-bootstrap-sidecar.md"
    _write(bridge_path, "team owns this bridge path\n")
    _commit(
        team_repo,
        "team tracks the claude bridge path",
        ".claude/rules/ai-bootstrap-sidecar.md",
    )
    bridge_path.unlink()

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not bridge_path.exists()
    out = capsys.readouterr().out
    assert "SKIPPED .claude/rules/ai-bootstrap-sidecar.md" in out
    status = _git(
        team_repo, "status", "--short", "--", ".claude/rules/ai-bootstrap-sidecar.md"
    )
    assert " D .claude/rules/ai-bootstrap-sidecar.md" in status.stdout


# --------------------------------------------------------------------------
# Phase G step 3 follow-up: more S3 real-git scenarios
# --------------------------------------------------------------------------


def test_crash_during_fresh_install_then_team_tracks_a_file_keeps_others_hidden(
    team_repo: Path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(
        sidecar_overlay_module, "_fault_point", _raise_at("before_manifest_write")
    )
    with pytest.raises(RuntimeError, match="before_manifest_write"):
        install_sidecar(team_repo, SOURCE)
    capsys.readouterr()
    monkeypatch.setattr(sidecar_overlay_module, "_fault_point", lambda name: None)

    assert (team_repo / ".claude" / "skills" / "ponytail" / "LICENSE").is_file()
    assert not _manifest_path(team_repo).exists()

    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team tracks ponytail SKILL.md")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    # LICENSE matches the desired reference (no manifest record yet) and
    # must be deleted, not left visible in git status.
    assert not (team_repo / ".claude" / "skills" / "ponytail" / "LICENSE").exists()
    status = _status(team_repo)
    assert ".claude/skills/ponytail" not in status


def test_retained_file_survives_a_lost_manifest_and_stays_hidden(
    team_repo: Path, capsys
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    unit_dir = team_repo / ".claude" / "skills" / "ponytail"
    user_file = unit_dir / "user-notes.txt"
    user_file.write_bytes(b"kept by a person\n")
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team takes ponytail SKILL.md")
    assert install_sidecar(team_repo, SOURCE) == 0  # records user-notes.txt retained
    manifest_before = _read_manifest(team_repo)
    assert manifest_before["retained"] == [".claude/skills/ponytail/user-notes.txt"]

    manifest_path = _manifest_path(team_repo)
    manifest_path.rename(manifest_path.with_name(manifest_path.name + ".bak"))
    status_before = _status(team_repo)

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert user_file.exists()
    assert _is_ignored(team_repo, ".claude/skills/ponytail/user-notes.txt")
    assert _status(team_repo) == status_before
    out = capsys.readouterr().out
    assert "RETAINED .claude/skills/ponytail/user-notes.txt" in out


# --------------------------------------------------------------------------
# Phase G step 2 follow-up: L3, a named pipe is never opened
# --------------------------------------------------------------------------


def test_named_pipe_named_skill_md_is_never_opened(team_repo: Path) -> None:
    pipe_dir = team_repo / ".github" / "skills" / "team-pipe-skill"
    pipe_dir.mkdir(parents=True, exist_ok=True)
    pipe_path = pipe_dir / "SKILL.md"
    os.mkfifo(pipe_path)

    # If frontmatter scanning ever opened the pipe for reading, this would
    # hang forever with no writer on the other end; enforce a hard deadline
    # instead of letting a hung test block the whole suite.
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(install_sidecar, team_repo, SOURCE)
        exit_code = future.result(timeout=15)

    assert exit_code == 0


# --------------------------------------------------------------------------
# Phase G review follow-up: the sidecar's own entry must not hide a team
# frontmatter-name collision under a different folder name
# --------------------------------------------------------------------------


def test_frontmatter_collision_at_read_only_folder_takes_the_skill_and_removes_copies(
    team_repo: Path, capsys
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    team_skill = team_repo / ".github" / "skills" / "team-humanize" / "SKILL.md"
    team_skill.parent.mkdir(parents=True, exist_ok=True)
    team_skill.write_text("---\nname: humanize\n---\nTEAM-HUMANIZE\n", encoding="utf-8")
    _commit(
        team_repo,
        "team declares humanize under a different folder name",
        ".github/skills/team-humanize",
    )
    status_before = _status(team_repo)

    dry_run_exit = install_sidecar(team_repo, SOURCE, dry_run=True)
    assert dry_run_exit == 0
    assert _status(team_repo) == status_before
    dry_out = capsys.readouterr().out
    assert "would remove .claude/skills/humanize" in dry_out
    assert "would remove .agents/skills/humanize" in dry_out
    assert (team_repo / ".claude" / "skills" / "humanize").exists()  # dry-run only

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not (team_repo / ".claude" / "skills" / "humanize").exists()
    assert not (team_repo / ".agents" / "skills" / "humanize").exists()
    manifest = _read_manifest(team_repo)
    assert ".claude/skills/humanize" not in manifest["units"]
    assert ".agents/skills/humanize" not in manifest["units"]
    exclude_text = _exclude_path(team_repo).read_text(encoding="utf-8")
    assert "/.claude/skills/humanize\n" not in exclude_text
    assert "/.agents/skills/humanize\n" not in exclude_text
    out = capsys.readouterr().out
    assert "SKIPPED .github/skills/team-humanize" in out
    assert _status(team_repo) == status_before

    status_before_2 = _status(team_repo)
    assert install_sidecar(team_repo, SOURCE) == 0
    assert _status(team_repo) == status_before_2


def test_frontmatter_collision_at_write_root_different_name_takes_the_skill(
    team_repo: Path, capsys
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    team_skill = team_repo / ".claude" / "skills" / "team-humanize" / "SKILL.md"
    team_skill.parent.mkdir(parents=True, exist_ok=True)
    team_skill.write_text("---\nname: humanize\n---\nTEAM-HUMANIZE\n", encoding="utf-8")
    _commit(
        team_repo,
        "team declares humanize under a write-root folder with a different name",
        ".claude/skills/team-humanize",
    )
    status_before = _status(team_repo)

    dry_run_exit = install_sidecar(team_repo, SOURCE, dry_run=True)
    assert dry_run_exit == 0
    assert _status(team_repo) == status_before

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not (team_repo / ".claude" / "skills" / "humanize").exists()
    assert not (team_repo / ".agents" / "skills" / "humanize").exists()
    assert (
        team_skill.read_text(encoding="utf-8")
        == "---\nname: humanize\n---\nTEAM-HUMANIZE\n"
    )
    manifest = _read_manifest(team_repo)
    assert ".claude/skills/humanize" not in manifest["units"]
    assert ".agents/skills/humanize" not in manifest["units"]
    out = capsys.readouterr().out
    assert "SKIPPED .claude/skills/team-humanize" in out
    assert _status(team_repo) == status_before

    status_before_2 = _status(team_repo)
    assert install_sidecar(team_repo, SOURCE) == 0
    assert _status(team_repo) == status_before_2


def test_own_installed_copies_never_take_their_own_skill(
    team_repo: Path, capsys
) -> None:
    # Guard: after a normal install with no team content, a rerun reports
    # nothing taken -- the sidecar's own write-root copies, which also
    # declare their own frontmatter name, must never take their own skill.
    assert install_sidecar(team_repo, SOURCE) == 0
    capsys.readouterr()

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "SKIPPED" not in out
    assert (team_repo / ".claude" / "skills" / "humanize").is_dir()
    assert (team_repo / ".agents" / "skills" / "humanize").is_dir()


def test_edited_copy_declaring_another_sidecar_skills_name_only_costs_that_skill(
    team_repo: Path, capsys
) -> None:
    # Decision 22 (round-3 review, MINOR): a false frontmatter match costs
    # a sidecar skill, never a team file. Editing humanize's .claude copy
    # to declare "ponytail" must take ponytail (removing its two unmodified
    # copies) while leaving humanize itself merely locally modified, since
    # nothing else declares "humanize" and its .agents copy is untouched.
    assert install_sidecar(team_repo, SOURCE) == 0
    before = {path: (team_repo / path).read_bytes() for path in TEAM_TRACKED_PATHS}
    humanize_skill_md = team_repo / ".claude" / "skills" / "humanize" / "SKILL.md"
    humanize_skill_md.write_text(
        "---\nname: ponytail\n---\nEDITED-TO-DECLARE-PONYTAIL\n", encoding="utf-8"
    )
    edited_bytes = humanize_skill_md.read_bytes()

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()
    assert not (team_repo / ".agents" / "skills" / "ponytail").exists()
    assert humanize_skill_md.read_bytes() == edited_bytes  # kept, never overwritten
    assert (team_repo / ".agents" / "skills" / "humanize" / "SKILL.md").is_file()
    manifest = _read_manifest(team_repo)
    assert ".claude/skills/ponytail" not in manifest["units"]
    assert ".agents/skills/ponytail" not in manifest["units"]
    assert ".claude/skills/humanize" in manifest["units"]  # record kept, unmodified
    after = {path: (team_repo / path).read_bytes() for path in TEAM_TRACKED_PATHS}
    assert after == before  # no team file is touched
    out = capsys.readouterr().out
    assert "SKIPPED .claude/skills/humanize" in out
    assert "has local edits" in out
    assert "ponytail" in out

    status_before = _status(team_repo)
    assert install_sidecar(team_repo, SOURCE) == 0
    assert _status(team_repo) == status_before


# --------------------------------------------------------------------------
# Phase G review round 3: MAJOR, _ignorecase() against the real git binary
# --------------------------------------------------------------------------


def test_ignorecase_reads_core_ignorecase_config(team_repo: Path) -> None:
    assert sidecar_overlay_module._ignorecase(team_repo) is False  # unset by default
    config = _git(team_repo, "config", "core.ignorecase", "true")
    assert config.returncode == 0, config.stderr
    assert sidecar_overlay_module._ignorecase(team_repo) is True


def test_ignorecase_true_with_real_case_variant_folder_takes_ponytail_end_to_end(
    team_repo: Path, capsys
) -> None:
    config = _git(team_repo, "config", "core.ignorecase", "true")
    assert config.returncode == 0, config.stderr
    variant_dir = team_repo / ".github" / "skills" / "Ponytail"
    variant_dir.mkdir(parents=True, exist_ok=True)
    (variant_dir / "SKILL.md").write_text(
        "a personal case-variant folder\n", encoding="utf-8"
    )

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()
    assert not (team_repo / ".agents" / "skills" / "ponytail").exists()
    out = capsys.readouterr().out
    assert "SKIPPED .github/skills/Ponytail" in out
    # The person's own case-variant folder is never hidden or written to.
    exclude_text = _exclude_path(team_repo).read_text(encoding="utf-8")
    assert "Ponytail" not in exclude_text
    assert "?? .github/skills/Ponytail/" in _status(team_repo)
    assert (variant_dir / "SKILL.md").read_text(encoding="utf-8") == (
        "a personal case-variant folder\n"
    )


# --------------------------------------------------------------------------
# Phase G step 8 follow-up: S15, exact per-path lines in a real run
# --------------------------------------------------------------------------


def test_real_run_prints_exact_lines_for_remove_delete_and_preserve(
    team_repo: Path, tmp_path: Path, monkeypatch, capsys
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0

    # team_takeover_delete: force-track ponytail's SKILL.md, leaving its
    # untracked LICENSE matching the record -> deleted.
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team takes ponytail SKILL.md")

    # preserve: edit humanize's .agents copy, then have the team take
    # humanize's .claude copy (so the skill is taken and the edited copy
    # must move out, not stay installed).
    edited = team_repo / ".agents" / "skills" / "humanize" / "SKILL.md"
    edited.write_text(
        edited.read_text(encoding="utf-8") + "\nEDITED\n", encoding="utf-8"
    )
    team_content = "---\nname: humanize\n---\nTEAM-OWNED-HUMANIZE\n"
    _write(team_repo / ".claude" / "skills" / "humanize" / "SKILL.md", team_content)
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/humanize")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team owns humanize")

    # remove: build a reduced source that no longer ships debug-investigator.
    # Decision 31's exact-source check now compares against the current
    # SIDECAR_SKILLS constant, so a source that intentionally drops a skill
    # needs that constant patched to match (patch_sidecar_skills), not a
    # weaker check.
    reduced_source = tmp_path / "reduced-source"
    shutil.copytree(SOURCE, reduced_source)
    for write_root in (".claude/skills", ".agents/skills"):
        shutil.rmtree(reduced_source / write_root / "debug-investigator")
    patch_sidecar_skills(monkeypatch, ("humanize", "ponytail", "ponytail-review"))

    exit_code = install_sidecar(team_repo, reduced_source)

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "removed .claude/skills/debug-investigator" in out
    assert "removed .agents/skills/debug-investigator" in out
    assert "deleted .claude/skills/ponytail/LICENSE" in out
    preserved_root = git_path(team_repo, "ai-bootstrap-sidecar-preserved")
    preserved_entries = list(preserved_root.iterdir())
    assert len(preserved_entries) == 1
    assert f"PRESERVED .agents/skills/humanize -> {preserved_entries[0]}" in out


# --------------------------------------------------------------------------
# Phase G step 2: R2, symlinked read roots and skill entries
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "read_only_root", [".github/skills", ".agent/skills", ".codex/skills"]
)
def test_symlinked_read_only_root_is_scanned_through_the_link(
    team_repo: Path, tmp_path: Path, read_only_root: str, capsys
) -> None:
    elsewhere = tmp_path / "team-skills-elsewhere"
    (elsewhere / "ponytail").mkdir(parents=True)
    (elsewhere / "ponytail" / "SKILL.md").write_text(
        "---\nname: ponytail\n---\nTEAM-VIA-SYMLINKED-ROOT\n", encoding="utf-8"
    )
    root_path = team_repo / PurePosixPath(read_only_root)
    root_path.parent.mkdir(parents=True, exist_ok=True)
    if root_path.exists() or root_path.is_symlink():
        shutil.rmtree(root_path)
    root_path.symlink_to(elsewhere, target_is_directory=True)

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()
    assert not (team_repo / ".agents" / "skills" / "ponytail").exists()
    out = capsys.readouterr().out
    assert f"{read_only_root}/ponytail" in out


def test_symlinked_skill_folder_inside_a_read_only_root_is_a_collision(
    team_repo: Path, tmp_path: Path, capsys
) -> None:
    elsewhere = tmp_path / "team-ponytail-elsewhere"
    elsewhere.mkdir()
    (elsewhere / "SKILL.md").write_text(
        "---\nname: ponytail\n---\nTEAM-VIA-SYMLINKED-SKILL\n", encoding="utf-8"
    )
    link = team_repo / ".github" / "skills" / "ponytail"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(elsewhere, target_is_directory=True)

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()
    assert not (team_repo / ".agents" / "skills" / "ponytail").exists()
    out = capsys.readouterr().out
    assert ".github/skills/ponytail" in out


def test_broken_symlink_entry_in_a_read_only_root_is_a_collision(
    team_repo: Path, capsys
) -> None:
    link = team_repo / ".github" / "skills" / "ponytail"
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(team_repo / "does-not-exist")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()
    assert not (team_repo / ".agents" / "skills" / "ponytail").exists()
    out = capsys.readouterr().out
    assert ".github/skills/ponytail" in out


def test_github_skills_symlinked_to_claude_skills_never_alternates_over_three_runs(
    team_repo: Path,
) -> None:
    shutil.rmtree(team_repo / ".github" / "skills", ignore_errors=True)
    (team_repo / ".github" / "skills").symlink_to(
        team_repo / ".claude" / "skills", target_is_directory=True
    )

    for _ in range(3):
        exit_code = install_sidecar(team_repo, SOURCE)
        assert exit_code == 0
        assert (team_repo / ".claude" / "skills" / "ponytail").is_dir()
        assert (team_repo / ".agents" / "skills" / "ponytail").is_dir()


# --------------------------------------------------------------------------
# Phase J step 8: one path-identity rule for collision sources (Decision 41;
# R3, O6, O7, O8)
# --------------------------------------------------------------------------


def test_r3_case1_symlinked_root_frontmatter_declares_a_different_folder_name(
    team_repo: Path, tmp_path: Path
) -> None:
    """R3 case 1: the frontmatter scan used to skip every symlinked read
    root outright, missing a collision behind one entirely, unlike the
    folder-name scan (which already follows it). Fails on 010f08c."""
    elsewhere = tmp_path / "team-skills-elsewhere"
    (elsewhere / "team-humanize").mkdir(parents=True)
    (elsewhere / "team-humanize" / "SKILL.md").write_text(
        "---\nname: humanize\n---\nTEAM-VIA-SYMLINKED-ROOT\n", encoding="utf-8"
    )
    root_path = team_repo / ".github" / "skills"
    root_path.parent.mkdir(parents=True, exist_ok=True)
    if root_path.exists() or root_path.is_symlink():
        shutil.rmtree(root_path)
    root_path.symlink_to(elsewhere, target_is_directory=True)

    for _ in range(3):
        exit_code = install_sidecar(team_repo, SOURCE)
        assert exit_code == 0
        assert not (team_repo / ".claude" / "skills" / "humanize").exists()
        assert not (team_repo / ".agents" / "skills" / "humanize").exists()
        assert (team_repo / ".claude" / "skills" / "ponytail").is_dir()


def test_r3_case2_o7_per_entry_symlink_into_a_write_root_never_takes_its_own_skill(
    team_repo: Path,
) -> None:
    """R3 case 2 / O7: a per-entry symlink inside a read-only root that
    resolves into the sidecar's own write root used to be followed by the
    frontmatter scan (declaring the skill's own name) without the folder-
    name scan's alias exclusion, alternately removing and reinstalling both
    real copies every run. Fails on 010f08c."""
    assert install_sidecar(team_repo, SOURCE) == 0
    alias = team_repo / ".github" / "skills" / "ponytail"
    alias.parent.mkdir(parents=True, exist_ok=True)
    alias.symlink_to(
        Path("..") / ".." / ".claude" / "skills" / "ponytail", target_is_directory=True
    )

    for _ in range(3):
        exit_code = install_sidecar(team_repo, SOURCE)
        assert exit_code == 0
        assert (team_repo / ".claude" / "skills" / "ponytail").is_dir()
        assert (team_repo / ".agents" / "skills" / "ponytail").is_dir()
        assert alias.is_symlink()


def test_write_root_alias_to_another_write_root_never_dangles(
    team_repo: Path,
) -> None:
    """Decision 41: a symlink entry inside a write root itself that resolves
    into another write root is an alias too, not only one inside a
    read-only root. Fails on 010f08c."""
    assert install_sidecar(team_repo, SOURCE) == 0
    alias = team_repo / ".claude" / "skills" / "pt"
    alias.symlink_to(
        Path("..") / ".." / ".agents" / "skills" / "ponytail", target_is_directory=True
    )

    for _ in range(3):
        exit_code = install_sidecar(team_repo, SOURCE)
        assert exit_code == 0
        assert (team_repo / ".claude" / "skills" / "ponytail").is_dir()
        assert (team_repo / ".agents" / "skills" / "ponytail").is_dir()
        assert alias.is_symlink()


def test_o8_symlinked_read_only_root_frontmatter_declares_a_different_folder_name(
    team_repo: Path, tmp_path: Path
) -> None:
    """O8: a symlinked read-only root's frontmatter declaration under a
    differently named folder must still take the skill. Fails on 010f08c."""
    elsewhere = tmp_path / "shared-skills"
    (elsewhere / "team-review").mkdir(parents=True)
    (elsewhere / "team-review" / "SKILL.md").write_text(
        "---\nname: ponytail-review\n---\nTEAM-VIA-SYMLINKED-ROOT\n", encoding="utf-8"
    )
    root_path = team_repo / ".codex" / "skills"
    root_path.parent.mkdir(parents=True, exist_ok=True)
    if root_path.exists() or root_path.is_symlink():
        shutil.rmtree(root_path)
    root_path.symlink_to(elsewhere, target_is_directory=True)

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not (team_repo / ".claude" / "skills" / "ponytail-review").exists()
    assert not (team_repo / ".agents" / "skills" / "ponytail-review").exists()
    assert (team_repo / ".claude" / "skills" / "ponytail").is_dir()


def test_o6_ignorecase_case_variant_folder_at_a_write_root_takes_the_skill(
    team_repo: Path, capsys
) -> None:
    """O6: ``_reflects_a_write_root`` was true for any ordinary entry
    physically inside a write root (a write root is always its own
    ancestor), so disk names at write roots were always empty; a personal
    case-variant folder there was never seen. Fails on 010f08c."""
    config = _git(team_repo, "config", "core.ignorecase", "true")
    assert config.returncode == 0, config.stderr
    variant_dir = team_repo / ".claude" / "skills" / "Ponytail"
    variant_dir.mkdir(parents=True, exist_ok=True)
    (variant_dir / "SKILL.md").write_text(
        "a personal case-variant folder\n", encoding="utf-8"
    )

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()
    assert not (team_repo / ".agents" / "skills" / "ponytail").exists()
    out = capsys.readouterr().out
    assert "SKIPPED .claude/skills/Ponytail" in out
    exclude_text = _exclude_path(team_repo).read_text(encoding="utf-8")
    assert "Ponytail" not in exclude_text
    assert "?? .claude/skills/Ponytail/" in _status(team_repo)
    assert (variant_dir / "SKILL.md").read_text(encoding="utf-8") == (
        "a personal case-variant folder\n"
    )


# --------------------------------------------------------------------------
# Phase G step 5: an empty leftover unit folder counts as absent (S9)
# --------------------------------------------------------------------------


def test_empty_leftover_folder_after_untrack_and_cleanup_reinstalls_the_skill(
    team_repo: Path,
) -> None:
    # The product's own path: team takeover retains a personal file
    # alongside the tracked one; the team later stops tracking the skill;
    # the person deletes the retained file exactly as the report told them
    # to. The now-empty folder must be reinstalled, not blocked forever.
    assert install_sidecar(team_repo, SOURCE) == 0
    unit_dir = team_repo / ".claude" / "skills" / "ponytail"
    user_file = unit_dir / "user-notes.txt"
    user_file.write_bytes(b"kept by a person\n")

    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team takes over ponytail")
    assert install_sidecar(team_repo, SOURCE) == 0
    # LICENSE matched the record and was deleted; user-notes.txt is retained.
    assert not (unit_dir / "LICENSE").exists()
    assert user_file.exists()

    rm = _git(team_repo, "rm", "-q", "--", ".claude/skills/ponytail/SKILL.md")
    assert rm.returncode == 0, rm.stderr
    _commit_staged(team_repo, "team stops tracking ponytail")
    assert unit_dir.is_dir()  # user-notes.txt keeps it non-empty
    user_file.unlink()  # the person deletes the retained file as told
    assert unit_dir.is_dir()
    assert not any(unit_dir.iterdir())

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert (unit_dir / "SKILL.md").is_file()
    assert (unit_dir / "LICENSE").is_file()
    assert (team_repo / ".agents" / "skills" / "ponytail").is_dir()


# --------------------------------------------------------------------------
# Phase G step 6: gate skill folders with a trailing slash (S4)
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "gitignore_rule",
    [
        "!.claude/skills/*/\n",
        ".claude/skills/*\n!.claude/skills/*/\n",
        "!.agents/skills/**/\n",
        "!**/ponytail/\n",
        "!.claude/skills/ponytail/\n",
    ],
)
def test_directory_only_team_rule_fails_the_gate_before_any_write(
    team_repo: Path, gitignore_rule: str
) -> None:
    gitignore = team_repo / ".gitignore"
    _write(gitignore, gitignore.read_text(encoding="utf-8") + gitignore_rule)
    _commit(
        team_repo,
        "team un-ignores a sidecar folder with a trailing slash rule",
        ".gitignore",
    )
    status_before = _status(team_repo)
    exclude_before = (
        _exclude_path(team_repo).read_bytes()
        if _exclude_path(team_repo).is_file()
        else None
    )

    dry_run_exit = install_sidecar(team_repo, SOURCE, dry_run=True)
    assert dry_run_exit != 0
    assert _status(team_repo) == status_before

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code != 0
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()
    assert not _manifest_path(team_repo).exists()
    exclude_after = (
        _exclude_path(team_repo).read_bytes()
        if _exclude_path(team_repo).is_file()
        else None
    )
    assert exclude_after == exclude_before
    assert _status(team_repo) == status_before


def test_claude_star_plus_negated_skills_dir_still_passes_the_gate(
    team_repo: Path,
) -> None:
    gitignore = team_repo / ".gitignore"
    _write(
        gitignore,
        gitignore.read_text(encoding="utf-8") + ".claude/*\n!.claude/skills/\n",
    )
    _commit(team_repo, "team keeps .claude/skills visible in listings", ".gitignore")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert (team_repo / ".claude" / "skills" / "ponytail").is_dir()


# --------------------------------------------------------------------------
# Phase G step 4: preserving edited copies of a taken skill (Decision 24)
# --------------------------------------------------------------------------


def test_taken_skill_with_edited_copy_is_preserved_into_the_git_directory(
    team_repo: Path, capsys
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    edited = team_repo / ".agents" / "skills" / "ponytail" / "SKILL.md"
    edited.write_text(
        edited.read_text(encoding="utf-8") + "\nEDITED\n", encoding="utf-8"
    )
    edited_bytes = edited.read_bytes()
    license_bytes = (
        team_repo / ".agents" / "skills" / "ponytail" / "LICENSE"
    ).read_bytes()

    team_content = "---\nname: ponytail\n---\nTEAM-OWNED-PONYTAIL\n"
    _write(team_repo / ".claude" / "skills" / "ponytail" / "SKILL.md", team_content)
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team owns ponytail")
    status_before = _status(team_repo)

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not (team_repo / ".agents" / "skills" / "ponytail").exists()
    preserved_root = git_path(team_repo, "ai-bootstrap-sidecar-preserved")
    entries = list(preserved_root.iterdir())
    assert len(entries) == 1
    preserved_dir = entries[0]
    assert preserved_dir.name.startswith(".agents__skills__ponytail--")
    assert (preserved_dir / "SKILL.md").read_bytes() == edited_bytes
    assert (preserved_dir / "LICENSE").read_bytes() == license_bytes
    manifest = _read_manifest(team_repo)
    assert ".agents/skills/ponytail" not in manifest["units"]
    exclude_text = _exclude_path(team_repo).read_text(encoding="utf-8")
    assert "/.agents/skills/ponytail\n" not in exclude_text
    out = capsys.readouterr().out
    assert f"PRESERVED .agents/skills/ponytail -> {preserved_dir}" in out
    assert _status(team_repo) == status_before

    # A rerun changes nothing further.
    status_before_2 = _status(team_repo)
    assert install_sidecar(team_repo, SOURCE) == 0
    assert _status(team_repo) == status_before_2
    assert list(preserved_root.iterdir()) == entries


def test_preserve_destination_conflict_keeps_the_unit_in_place(
    team_repo: Path, capsys
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    edited = team_repo / ".agents" / "skills" / "ponytail" / "SKILL.md"
    edited.write_text(
        edited.read_text(encoding="utf-8") + "\nEDITED\n", encoding="utf-8"
    )
    edited_bytes = edited.read_bytes()

    # Pre-create the exact destination the preserve move would use, so the
    # run must report a conflict and leave the unit alone (Decision 24).
    unit_dir = team_repo / ".agents" / "skills" / "ponytail"
    file_hashes = {
        p.relative_to(unit_dir).as_posix(): sidecar_overlay_module.compute_file_hash(
            p.read_bytes()
        )
        for p in sorted(unit_dir.rglob("*"))
        if p.is_file()
    }
    content_hash = sidecar_overlay_module.compute_unit_hash(file_hashes)
    slug = sidecar_overlay_module.preserved_unit_slug(
        ".agents/skills/ponytail", content_hash
    )
    preserved_root = git_path(team_repo, "ai-bootstrap-sidecar-preserved")
    conflicting = preserved_root / slug
    conflicting.mkdir(parents=True)
    (conflicting / "sentinel.txt").write_text("already here\n", encoding="utf-8")

    team_content = "---\nname: ponytail\n---\nTEAM-OWNED-PONYTAIL\n"
    _write(team_repo / ".claude" / "skills" / "ponytail" / "SKILL.md", team_content)
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team owns ponytail")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert edited.read_bytes() == edited_bytes
    assert (conflicting / "sentinel.txt").is_file()
    manifest = _read_manifest(team_repo)
    assert ".agents/skills/ponytail" in manifest["units"]
    out = capsys.readouterr().out
    assert str(conflicting) in out


def test_preserve_dry_run_predicts_the_same_result_as_the_real_run(
    team_repo: Path,
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    edited = team_repo / ".agents" / "skills" / "ponytail" / "SKILL.md"
    edited.write_text(
        edited.read_text(encoding="utf-8") + "\nEDITED\n", encoding="utf-8"
    )

    team_content = "---\nname: ponytail\n---\nTEAM-OWNED-PONYTAIL\n"
    _write(team_repo / ".claude" / "skills" / "ponytail" / "SKILL.md", team_content)
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team owns ponytail")

    status_before = _status(team_repo)
    dry_run_exit = install_sidecar(team_repo, SOURCE, dry_run=True)
    assert dry_run_exit == 0
    assert _status(team_repo) == status_before
    assert (team_repo / ".agents" / "skills" / "ponytail").exists()

    exit_code = install_sidecar(team_repo, SOURCE)
    assert exit_code == 0
    assert not (team_repo / ".agents" / "skills" / "ponytail").exists()


def test_fault_before_manifest_write_after_preserve_rerun_converges(
    team_repo: Path, monkeypatch, capsys
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    edited = team_repo / ".agents" / "skills" / "ponytail" / "SKILL.md"
    edited.write_text(
        edited.read_text(encoding="utf-8") + "\nEDITED\n", encoding="utf-8"
    )
    edited_bytes = edited.read_bytes()

    team_content = "---\nname: ponytail\n---\nTEAM-OWNED-PONYTAIL\n"
    _write(team_repo / ".claude" / "skills" / "ponytail" / "SKILL.md", team_content)
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team owns ponytail")

    monkeypatch.setattr(
        sidecar_overlay_module, "_fault_point", _raise_at("before_manifest_write")
    )
    with pytest.raises(RuntimeError, match="before_manifest_write"):
        install_sidecar(team_repo, SOURCE)
    capsys.readouterr()

    # Pre-rerun state: the unit has already moved into the preserved folder.
    assert not (team_repo / ".agents" / "skills" / "ponytail").exists()
    preserved_root = git_path(team_repo, "ai-bootstrap-sidecar-preserved")
    entries = list(preserved_root.iterdir())
    assert len(entries) == 1
    assert (entries[0] / "SKILL.md").read_bytes() == edited_bytes
    manifest_before = _manifest_path(team_repo)
    assert manifest_before.is_file()  # from the first, successful install

    monkeypatch.setattr(sidecar_overlay_module, "_fault_point", lambda name: None)
    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    manifest = _read_manifest(team_repo)
    assert ".agents/skills/ponytail" not in manifest["units"]
    assert list(preserved_root.iterdir()) == entries  # unchanged, not moved again


# --------------------------------------------------------------------------
# Phase G review round 3: CRITICAL, unrecognized exclude-block lines
# --------------------------------------------------------------------------


def test_unrecognized_line_hiding_a_personal_file_survives_and_stays_hidden(
    team_repo: Path, capsys
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    personal_file = team_repo / ".claude" / "skills" / "humanize" / "notes.txt"
    personal_file.write_text(
        "kept by a person, hidden by a hand-written rule\n", encoding="utf-8"
    )
    _insert_block_line(team_repo, "notes.txt")
    assert _is_ignored(team_repo, ".claude/skills/humanize/notes.txt")
    status_before = _status(team_repo)

    dry_run_exit = install_sidecar(team_repo, SOURCE, dry_run=True)
    assert dry_run_exit == 0
    assert _status(team_repo) == status_before
    dry_out = capsys.readouterr().out
    assert "notes.txt" in dry_out

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert personal_file.exists()
    assert _is_ignored(team_repo, ".claude/skills/humanize/notes.txt")
    assert _status(team_repo) == status_before
    exclude_after_first_run = _exclude_path(team_repo).read_bytes()
    assert b"notes.txt" in exclude_after_first_run
    out = capsys.readouterr().out
    assert "notes.txt" in out
    assert "RETAINED" in out

    exit_code_2 = install_sidecar(team_repo, SOURCE)

    assert exit_code_2 == 0
    assert _exclude_path(team_repo).read_bytes() == exclude_after_first_run
    assert _status(team_repo) == status_before
    assert personal_file.exists()


def test_unrecognized_garbage_line_survives_and_is_reported(
    team_repo: Path, capsys
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    garbage_line = "not-a-recognized-sidecar-line-just-garbage-text"
    _insert_block_line(team_repo, garbage_line)
    status_before = _status(team_repo)

    dry_run_exit = install_sidecar(team_repo, SOURCE, dry_run=True)
    assert dry_run_exit == 0
    assert _status(team_repo) == status_before

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert _status(team_repo) == status_before
    exclude_after_first_run = _exclude_path(team_repo).read_bytes()
    assert garbage_line.encode("utf-8") in exclude_after_first_run
    out = capsys.readouterr().out
    assert garbage_line in out
    assert "RETAINED" in out

    exit_code_2 = install_sidecar(team_repo, SOURCE)

    assert exit_code_2 == 0
    assert _exclude_path(team_repo).read_bytes() == exclude_after_first_run
    assert _status(team_repo) == status_before


# --------------------------------------------------------------------------
# Phase H step 1: drop inherited Git repository-local environment variables
# --------------------------------------------------------------------------


def _build_other_repo(root: Path) -> Path:
    other = root / "other-repo"
    _init_repo(other)
    _write(other / "README.md", "other repo\n")
    _commit(other, "init other repo")
    return other


def test_exported_git_dir_pointing_elsewhere_is_scrubbed(
    team_repo: Path, tmp_path: Path
) -> None:
    other = _build_other_repo(tmp_path)
    other_status_before = _status(other)

    env = os.environ.copy()
    env["GIT_DIR"] = str(other / ".git")

    result = subprocess.run(
        [sys.executable, str(INSTALLER), str(team_repo), "--mode", "sidecar"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert _manifest_path(team_repo).is_file()
    assert "/.claude/skills/ponytail\n" in _exclude_path(team_repo).read_text(
        encoding="utf-8"
    )
    assert not _manifest_path(other).exists()
    other_exclude = other / ".git" / "info" / "exclude"
    other_exclude_text = (
        other_exclude.read_text(encoding="utf-8") if other_exclude.is_file() else ""
    )
    assert "ai-bootstrap sidecar" not in other_exclude_text
    assert _status(other) == other_status_before


def test_exported_git_index_file_is_scrubbed(team_repo: Path, tmp_path: Path) -> None:
    # A stray GIT_INDEX_FILE, left unscrubbed, makes every ls-files query see
    # an empty index: the team's tracked ponytail is then misread as
    # untracked "foreign" content instead of "team_owned" -- both skip
    # installing it, but only the correct read names it as tracked.
    team_content = "---\nname: ponytail\n---\nTEAM-OWNED-PONYTAIL\n"
    _write(team_repo / ".claude" / "skills" / "ponytail" / "SKILL.md", team_content)
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team owns ponytail")

    stray_index = tmp_path / "stray-index"
    env = os.environ.copy()
    env["GIT_INDEX_FILE"] = str(stray_index)

    result = subprocess.run(
        [sys.executable, str(INSTALLER), str(team_repo), "--mode", "sidecar"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (team_repo / ".claude" / "skills" / "ponytail" / "SKILL.md").read_text(
        encoding="utf-8"
    ) == team_content
    assert "the repository tracks" in result.stdout
    assert "will not replace" not in result.stdout
    assert not stray_index.exists()


# --------------------------------------------------------------------------
# Phase H step 3: validate Git-directory metadata before any write
# --------------------------------------------------------------------------


# Reuse the shared Git-dir path builder (sidecar_test_helpers._absolute_git_dir),
# the same one install_sidecar itself uses, so a symlink test never gets
# fooled by a resolved path.
_git_dir_path = _absolute_git_dir


def _run_capturing_stderr(
    team_repo: Path, dry_run: bool = False, source: Path = SOURCE
) -> tuple[int, str]:
    import contextlib
    import io

    buffer = io.StringIO()
    with contextlib.redirect_stderr(buffer):
        exit_code = install_sidecar(team_repo, source, dry_run=dry_run)
    return exit_code, buffer.getvalue()


@pytest.mark.parametrize("dry_run", [False, True])
def test_manifest_as_a_folder_aborts_before_any_write(
    team_repo: Path, dry_run: bool
) -> None:
    git_dir = _git_dir_path(team_repo)
    manifest_path = git_dir / "ai-bootstrap-sidecar.json"
    manifest_path.mkdir()
    staging = git_dir / "ai-bootstrap-sidecar-staging"
    status_before = _status(team_repo)

    exit_code, err = _run_capturing_stderr(team_repo, dry_run=dry_run)

    assert exit_code != 0
    assert str(manifest_path) in err
    assert _status(team_repo) == status_before
    assert not staging.exists()
    assert manifest_path.is_dir()
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()


@pytest.mark.parametrize("dry_run", [False, True])
def test_manifest_as_dangling_symlink_aborts_before_any_write(
    team_repo: Path, tmp_path: Path, dry_run: bool
) -> None:
    git_dir = _git_dir_path(team_repo)
    manifest_path = git_dir / "ai-bootstrap-sidecar.json"
    manifest_path.symlink_to(tmp_path / "does-not-exist-target")
    status_before = _status(team_repo)

    exit_code, err = _run_capturing_stderr(team_repo, dry_run=dry_run)

    assert exit_code != 0
    assert str(manifest_path) in err
    assert "regular file" in err
    assert _status(team_repo) == status_before
    assert manifest_path.is_symlink()
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()


@pytest.mark.parametrize("dry_run", [False, True])
def test_manifest_as_symlink_to_a_file_aborts_before_any_write(
    team_repo: Path, tmp_path: Path, dry_run: bool
) -> None:
    real_file = tmp_path / "elsewhere.json"
    real_file.write_text("{}", encoding="utf-8")
    git_dir = _git_dir_path(team_repo)
    manifest_path = git_dir / "ai-bootstrap-sidecar.json"
    manifest_path.symlink_to(real_file)

    exit_code, err = _run_capturing_stderr(team_repo, dry_run=dry_run)

    assert exit_code != 0
    assert str(manifest_path) in err
    assert real_file.read_text(encoding="utf-8") == "{}"
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()


@pytest.mark.parametrize("dry_run", [False, True])
def test_manifest_as_named_pipe_aborts_before_any_write(
    team_repo: Path, dry_run: bool
) -> None:
    git_dir = _git_dir_path(team_repo)
    manifest_path = git_dir / "ai-bootstrap-sidecar.json"
    os.mkfifo(manifest_path)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(install_sidecar, team_repo, SOURCE, dry_run=dry_run)
        exit_code = future.result(timeout=15)

    assert exit_code != 0
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()


@pytest.mark.parametrize("dry_run", [False, True])
def test_staging_as_a_regular_file_aborts_before_any_write(
    team_repo: Path, dry_run: bool
) -> None:
    git_dir = _git_dir_path(team_repo)
    staging = git_dir / "ai-bootstrap-sidecar-staging"
    staging.write_text("not a folder\n", encoding="utf-8")
    before_bytes = staging.read_bytes()

    exit_code, err = _run_capturing_stderr(team_repo, dry_run=dry_run)

    assert exit_code != 0
    assert str(staging) in err
    assert staging.read_bytes() == before_bytes
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()


@pytest.mark.parametrize("dry_run", [False, True])
def test_staging_as_symlink_to_a_folder_holding_a_tracked_file_aborts(
    team_repo: Path, tmp_path: Path, dry_run: bool
) -> None:
    linked_folder = tmp_path / "shared-elsewhere"
    linked_folder.mkdir()
    tracked_sentinel = linked_folder / "important.txt"
    tracked_sentinel.write_text("do not touch\n", encoding="utf-8")
    git_dir = _git_dir_path(team_repo)
    staging = git_dir / "ai-bootstrap-sidecar-staging"
    staging.symlink_to(linked_folder, target_is_directory=True)

    exit_code, err = _run_capturing_stderr(team_repo, dry_run=dry_run)

    assert exit_code != 0
    assert str(staging) in err
    assert tracked_sentinel.read_text(encoding="utf-8") == "do not touch\n"
    assert sorted(p.name for p in linked_folder.iterdir()) == ["important.txt"]
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()


@pytest.mark.parametrize("dry_run", [False, True])
def test_info_as_a_symlink_to_a_shared_folder_aborts(
    team_repo: Path, tmp_path: Path, dry_run: bool
) -> None:
    shared_info = tmp_path / "shared-info"
    shared_info.mkdir()
    (shared_info / "exclude").write_text("*.log\n", encoding="utf-8")
    git_dir = _git_dir_path(team_repo)
    info_dir = git_dir / "info"
    shutil.rmtree(info_dir)
    info_dir.symlink_to(shared_info, target_is_directory=True)

    exit_code, err = _run_capturing_stderr(team_repo, dry_run=dry_run)

    assert exit_code != 0
    assert str(info_dir) in err
    assert (shared_info / "exclude").read_text(encoding="utf-8") == "*.log\n"
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()


@pytest.mark.parametrize("dry_run", [False, True])
def test_info_exclude_as_a_folder_aborts_before_any_write(
    team_repo: Path, dry_run: bool
) -> None:
    git_dir = _git_dir_path(team_repo)
    exclude_path = git_dir / "info" / "exclude"
    if exclude_path.is_file():
        exclude_path.unlink()
    exclude_path.mkdir()

    exit_code, err = _run_capturing_stderr(team_repo, dry_run=dry_run)

    assert exit_code != 0
    assert str(exclude_path) in err
    assert exclude_path.is_dir()
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()


@pytest.mark.parametrize("dry_run", [False, True])
def test_info_exclude_as_a_named_pipe_aborts_before_any_write(
    team_repo: Path, dry_run: bool
) -> None:
    git_dir = _git_dir_path(team_repo)
    exclude_path = git_dir / "info" / "exclude"
    if exclude_path.is_file():
        exclude_path.unlink()
    os.mkfifo(exclude_path)

    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(install_sidecar, team_repo, SOURCE, dry_run=dry_run)
        exit_code = future.result(timeout=15)

    assert exit_code != 0
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()


def test_linked_worktree_of_a_sidecar_main_worktree_still_refused(
    team_repo: Path, tmp_path: Path
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    linked = tmp_path / "linked-worktree"
    added = _git(team_repo, "worktree", "add", "-q", str(linked), "-b", "linked-branch")
    assert added.returncode == 0, added.stderr

    # With no --mode, the shared exclude block is detected as sidecar
    # evidence from the linked worktree too (Decision 15), so detection
    # picks "sidecar" without aborting; install_sidecar's own existing
    # linked-worktree preflight is what refuses it.
    result_plain = subprocess.run(
        [sys.executable, str(INSTALLER), str(linked)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result_plain.returncode != 0
    assert "linked worktree" in result_plain.stderr

    result_full = subprocess.run(
        [sys.executable, str(INSTALLER), str(linked), "--mode", "full"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result_full.returncode != 0
    assert "sidecar evidence" in result_full.stderr
    assert not (linked / ".claude" / ".git").exists()


# --------------------------------------------------------------------------
# Phase H step 4: require balanced exclude markers (Decision 26; S7)
# --------------------------------------------------------------------------

BEGIN_MARKER = "# BEGIN ai-bootstrap sidecar"
END_MARKER = "# END ai-bootstrap sidecar"


def _write_raw_exclude(team_repo: Path, text: str) -> None:
    exclude_path = _git_dir_path(team_repo) / "info" / "exclude"
    exclude_path.parent.mkdir(parents=True, exist_ok=True)
    exclude_path.write_text(text, encoding="utf-8")


@pytest.mark.parametrize(
    "broken_text",
    [
        f"{BEGIN_MARKER}\n.env.other\n",
        f"{END_MARKER}\n{BEGIN_MARKER}\n.env.other\n",
        f"{BEGIN_MARKER}\nx\n{END_MARKER}\n{BEGIN_MARKER}\ny\n{END_MARKER}\n",
        f"{BEGIN_MARKER}\n{BEGIN_MARKER}\nx\n{END_MARKER}\n",
    ],
    ids=("orphan-begin", "end-before-begin", "two-blocks", "repeated-begin"),
)
def test_unbalanced_exclude_markers_abort_before_any_write(
    team_repo: Path, broken_text: str
) -> None:
    personal_line = ".env.personal\n"
    text = personal_line + broken_text
    _write_raw_exclude(team_repo, text)
    exclude_path = _git_dir_path(team_repo) / "info" / "exclude"
    before_bytes = exclude_path.read_bytes()
    status_before = _status(team_repo)

    dry_exit, _ = _run_capturing_stderr(team_repo, dry_run=True)
    assert dry_exit != 0
    assert exclude_path.read_bytes() == before_bytes
    assert _status(team_repo) == status_before

    exit_code, err = _run_capturing_stderr(team_repo)
    assert exit_code != 0
    assert "line" in err
    assert exclude_path.read_bytes() == before_bytes
    assert _status(team_repo) == status_before
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()
    # The person's own line, byte-identical, no matter which shape broke.
    assert exclude_path.read_bytes().startswith(personal_line.encode("utf-8"))


def test_unbalanced_exclude_markers_also_abort_mode_detection(team_repo: Path) -> None:
    _write_raw_exclude(team_repo, f"{BEGIN_MARKER}\n.env.other\n")
    status_before = _status(team_repo)

    result = subprocess.run(
        [sys.executable, str(INSTALLER), str(team_repo)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "unbalanced" in result.stderr
    assert _status(team_repo) == status_before
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()


def test_normal_block_with_crlf_line_endings_still_works(team_repo: Path) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    exclude_path = _exclude_path(team_repo)
    text = exclude_path.read_text(encoding="utf-8")
    crlf_text = text.replace("\n", "\r\n")
    exclude_path.write_bytes(crlf_text.encode("utf-8"))

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert (team_repo / ".claude" / "skills" / "ponytail").is_dir()


# --------------------------------------------------------------------------
# Phase H step 5: bytes-safe paths (Decision 29; R5, S15)
# --------------------------------------------------------------------------

# os.fsdecode/os.fsencode round-trip: this str holds a surrogate-escaped
# byte 0xff, an illegal standalone UTF-8 byte on a POSIX filesystem.
BAD_BYTE_NAME = os.fsdecode(b"bad-\xff.txt")


def test_unrelated_staged_non_utf8_filename_installs_fine(team_repo: Path) -> None:
    bad_path = team_repo / BAD_BYTE_NAME
    bad_path.write_bytes(b"not utf-8 on purpose\n")
    add = _git(team_repo, "add", "-A")
    assert add.returncode == 0, add.stderr
    status_before = _status(team_repo)

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert (team_repo / ".claude" / "skills" / "ponytail").is_dir()
    assert _status(team_repo) == status_before
    assert bad_path.read_bytes() == b"not utf-8 on purpose\n"


def test_non_utf8_file_inside_owned_unit_is_kept_hidden_and_stable(
    team_repo: Path,
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    unit_dir = team_repo / ".claude" / "skills" / "ponytail"
    weird_file = unit_dir / BAD_BYTE_NAME
    weird_file.write_bytes(b"personal notes\n")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert weird_file.read_bytes() == b"personal notes\n"
    status = _status(team_repo)
    assert ".claude/skills/ponytail" not in status

    # Stable rerun: no oscillation, no crash.
    status_before_2 = _status(team_repo)
    assert install_sidecar(team_repo, SOURCE) == 0
    assert weird_file.read_bytes() == b"personal notes\n"
    assert _status(team_repo) == status_before_2


def test_retained_non_utf8_file_after_takeover_gets_a_raw_bytes_line(
    team_repo: Path,
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    unit_dir = team_repo / ".claude" / "skills" / "ponytail"
    weird_file = unit_dir / BAD_BYTE_NAME
    weird_file.write_bytes(b"kept by a person\n")
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team takes ponytail SKILL.md")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert weird_file.read_bytes() == b"kept by a person\n"
    exclude_bytes = _exclude_path(team_repo).read_bytes()
    assert b"bad-\xff.txt" in exclude_bytes
    manifest = _read_manifest(team_repo)
    expected_retained = f".claude/skills/ponytail/{BAD_BYTE_NAME}"
    assert any(
        os.fsencode(path) == os.fsencode(expected_retained)
        for path in manifest["retained"]
    )
    assert _is_ignored(team_repo, f".claude/skills/ponytail/{BAD_BYTE_NAME}")


def test_latin1_personal_exclude_line_preserved_byte_for_byte(team_repo: Path) -> None:
    exclude_path = _git_dir_path(team_repo) / "info" / "exclude"
    exclude_path.parent.mkdir(parents=True, exist_ok=True)
    latin1_line = "café-notes.txt".encode("latin-1")
    before = exclude_path.read_bytes() if exclude_path.is_file() else b""
    separator = b"" if not before or before.endswith(b"\n") else b"\n"
    exclude_path.write_bytes(before + separator + latin1_line + b"\n")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert latin1_line in _exclude_path(team_repo).read_bytes()


def test_retained_name_with_embedded_newline_never_gets_a_raw_pattern_line(
    team_repo: Path, capsys
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    unit_dir = team_repo / ".claude" / "skills" / "ponytail"
    weird_name = "weird\nname.txt"
    (unit_dir / weird_name).write_bytes(b"kept\n")
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team takes ponytail SKILL.md")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    exclude_text = _exclude_path(team_repo).read_text(encoding="utf-8")
    assert "weird" not in exclude_text
    out = capsys.readouterr().out
    assert "cannot be hidden" in out


def test_retained_name_with_trailing_cr_never_gets_a_raw_pattern_line(
    team_repo: Path, capsys
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    unit_dir = team_repo / ".claude" / "skills" / "ponytail"
    weird_name = "trailing-cr.txt\r"
    (unit_dir / weird_name).write_bytes(b"kept\n")
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team takes ponytail SKILL.md")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    exclude_text = _exclude_path(team_repo).read_text(encoding="utf-8")
    assert "trailing-cr" not in exclude_text
    out = capsys.readouterr().out
    assert "cannot be hidden" in out


@pytest.mark.parametrize(
    "control_char",
    ["\f", "\v", " "],
    ids=("form-feed", "vertical-tab", "line-separator"),
)
def test_retained_name_with_a_git_ignored_line_boundary_stays_one_line(
    team_repo: Path, control_char: str
) -> None:
    """O5/Decision 42: str.splitlines() also breaks on \\f, \\v, and U+2028,
    none of which Git treats as a line boundary in info/exclude. Splitting a
    retained file's escaped exclude line on one of those turns it into two
    lines; the second, unanchored fragment then hides an unrelated untracked
    file anywhere in the repository. Fails on 010f08c."""
    assert install_sidecar(team_repo, SOURCE) == 0
    unit_dir = team_repo / ".claude" / "skills" / "ponytail"
    weird_name = f"weird{control_char}name.txt"
    (unit_dir / weird_name).write_bytes(b"kept by a person\n")
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team takes ponytail SKILL.md")

    assert install_sidecar(team_repo, SOURCE) == 0
    decoy = team_repo / "name.txt"
    decoy.write_bytes(b"unrelated team file\n")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert "name.txt" in _status(team_repo)
    manifest = _read_manifest(team_repo)
    weird_path = f".claude/skills/ponytail/{weird_name}"
    assert weird_path in manifest["retained"]
    assert _is_ignored(team_repo, weird_path)
    exclude_text = _exclude_path(team_repo).read_text(encoding="utf-8")
    assert exclude_text.count(escape_exact_path(weird_path)) == 1

    status_before = _status(team_repo)
    assert install_sidecar(team_repo, SOURCE, dry_run=True) == 0
    assert _status(team_repo) == status_before
    assert install_sidecar(team_repo, SOURCE) == 0
    assert _status(team_repo) == status_before


def test_unexpressible_name_gate_catches_a_forced_raw_pattern_line(
    team_repo: Path, monkeypatch
) -> None:
    """Defense in depth (S15): even if a future bug bypassed the guard and
    forced a raw pattern line for an unexpressible name, the write-time
    ignore gate still refuses rather than silently mis-hiding it."""
    monkeypatch.setattr(
        sidecar_overlay_module, "_can_express_in_gitignore", lambda _: True
    )
    unit_dir = team_repo / ".claude" / "skills" / "ponytail"
    weird_name = "weird\nname.txt"

    assert install_sidecar(team_repo, SOURCE) == 0
    (unit_dir / weird_name).write_bytes(b"kept\n")
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team takes ponytail SKILL.md")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code != 0


def test_fixed_fixture_unit_hash_equals_pre_change_value():
    # Pinned before this phase's os.fsencode change (Decision 29): for any
    # legal name, os.fsencode is byte-identical to str.encode("utf-8"), so a
    # unit hash computed the old way (plain .encode("utf-8")) must still
    # match compute_unit_hash's new result for a fixed, real fixture.
    file_hash = sidecar_overlay_module.compute_file_hash(b"hello\n")
    files = {"SKILL.md": file_hash}
    old_algorithm = hashlib.sha256(
        "SKILL.md".encode("utf-8") + b"\0" + file_hash.encode("ascii") + b"\n"
    ).hexdigest()
    assert sidecar_overlay_module.compute_unit_hash(files) == old_algorithm


# --------------------------------------------------------------------------
# Phase H step 6: repository boundaries and filesystem shape (Decision 28)
# --------------------------------------------------------------------------


def _nested_clone(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _init_repo(path)
    _write(path / "README.md", "nested clone\n")
    _commit(path, "nested clone content")


@pytest.fixture
def bare_repo(tmp_path: Path) -> Path:
    root = tmp_path / "bare-repo"
    _init_repo(root)
    return root


def test_nested_clone_at_claude_skills_is_refused(bare_repo: Path) -> None:
    nested = bare_repo / ".claude" / "skills"
    _nested_clone(nested)
    status_before = _status(nested)

    exit_code, err = _run_capturing_stderr(bare_repo)

    assert exit_code != 0
    assert "nested repository or submodule" in err
    assert "nothing was written" in err
    assert _status(nested) == status_before
    assert not _manifest_path(bare_repo).exists()


def test_nested_clone_at_agents_with_no_skills_yet_is_refused(bare_repo: Path) -> None:
    nested = bare_repo / ".agents"
    _nested_clone(nested)
    status_before = _status(nested)

    exit_code, err = _run_capturing_stderr(bare_repo)

    assert exit_code != 0
    assert "nested repository or submodule" in err
    assert _status(nested) == status_before
    assert not _manifest_path(bare_repo).exists()


def _add_submodule(target: Path, relative: str, tmp_path: Path) -> Path:
    source = tmp_path / f"{relative.replace('/', '_')}-submodule-source"
    _init_repo(source)
    _write(source / "settings.json", '{"team": true}\n')
    _commit(source, "submodule content")
    add = _git(
        target,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        "-f",
        "-q",
        str(source),
        relative,
    )
    assert add.returncode == 0, add.stderr
    _commit(target, f"add {relative} submodule")
    return source


def test_submodule_at_a_write_root_is_refused(bare_repo: Path, tmp_path: Path) -> None:
    _add_submodule(bare_repo, ".claude/skills", tmp_path)
    status_before = _status(bare_repo / ".claude" / "skills")

    exit_code, err = _run_capturing_stderr(bare_repo)

    assert exit_code != 0
    assert "nested repository or submodule" in err
    assert _status(bare_repo / ".claude" / "skills") == status_before
    assert not _manifest_path(bare_repo).exists()


def test_submodule_at_claude_with_no_skills_inside_is_refused(
    bare_repo: Path, tmp_path: Path
) -> None:
    _add_submodule(bare_repo, ".claude", tmp_path)
    status_before = _status(bare_repo / ".claude")

    exit_code, err = _run_capturing_stderr(bare_repo)

    assert exit_code != 0
    assert "nested repository or submodule" in err
    assert "sidecar mode does not support" in err
    # Not the .gitignore remedy (S5): a submodule needs the new message, not
    # a suggestion to change a team ignore rule.
    assert ".gitignore" not in err
    assert _status(bare_repo / ".claude") == status_before
    assert not _manifest_path(bare_repo).exists()


def test_regular_file_at_agents_is_refused(bare_repo: Path) -> None:
    (bare_repo / ".agents").write_text("not a folder\n", encoding="utf-8")
    before_bytes = (bare_repo / ".agents").read_bytes()

    exit_code, err = _run_capturing_stderr(bare_repo)

    assert exit_code != 0
    assert (bare_repo / ".agents").read_bytes() == before_bytes
    assert not _manifest_path(bare_repo).exists()


def test_read_only_unit_folder_during_an_update_is_refused(team_repo: Path) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    unit_dir = team_repo / ".claude" / "skills" / "humanize"
    mutated_source = team_repo.parent / "mutated-source"
    shutil.copytree(SOURCE, mutated_source)
    mutated_file = mutated_source / ".claude" / "skills" / "humanize" / "SKILL.md"
    mutated_file.write_text(
        mutated_file.read_text(encoding="utf-8") + "\nmutated\n", encoding="utf-8"
    )
    mode_before = unit_dir.stat().st_mode
    unit_dir.chmod(0o555)
    try:
        exit_code, err = _run_capturing_stderr(team_repo, source=mutated_source)
        assert exit_code != 0
        assert "not writable" in err
        assert (
            not (unit_dir / "SKILL.md")
            .read_text(encoding="utf-8")
            .endswith("mutated\n")
        )
    finally:
        unit_dir.chmod(mode_before)
        shutil.rmtree(mutated_source)


def test_unit_with_a_read_only_subfolder_during_a_remove_is_refused(
    team_repo: Path, monkeypatch
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    reduced_source = team_repo.parent / "reduced-source"
    shutil.copytree(SOURCE, reduced_source)
    for write_root in (".claude/skills", ".agents/skills"):
        shutil.rmtree(reduced_source / write_root / "debug-investigator")
    patch_sidecar_skills(monkeypatch, ("humanize", "ponytail", "ponytail-review"))
    unit_dir = team_repo / ".claude" / "skills" / "debug-investigator"
    subfolder = unit_dir / "sub"
    subfolder.mkdir()
    (subfolder / "note.txt").write_text("x\n", encoding="utf-8")

    # Hand-craft the manifest record to match this exact on-disk content
    # (Decision 32: a recorded unit outside the current desired shape still
    # goes through the normal remove row), so the "remove" row -- not
    # "locally modified" -- is what plans to sweep the read-only subfolder.
    file_hashes = {
        p.relative_to(unit_dir).as_posix(): sidecar_overlay_module.compute_file_hash(
            p.read_bytes()
        )
        for p in sorted(unit_dir.rglob("*"))
        if p.is_file()
    }
    unit_hash = sidecar_overlay_module.compute_unit_hash(file_hashes)
    manifest = _read_manifest(team_repo)
    manifest["units"][".claude/skills/debug-investigator"] = {
        "files": file_hashes,
        "hash": unit_hash,
    }
    _manifest_path(team_repo).write_text(json.dumps(manifest), encoding="utf-8")

    mode_before = subfolder.stat().st_mode
    subfolder.chmod(0o555)
    try:
        exit_code, err = _run_capturing_stderr(team_repo, source=reduced_source)
        assert exit_code != 0
        assert "not writable" in err
        assert (unit_dir / "SKILL.md").exists()
    finally:
        subfolder.chmod(mode_before)
        shutil.rmtree(reduced_source)


def test_different_st_dev_via_monkeypatched_lstat_is_refused(
    team_repo: Path, monkeypatch
) -> None:
    real_lstat = os.lstat
    # Resolved once, with the real lstat, before patching: the fake must
    # never call anything that could recurse back into itself.
    write_root_str = str((team_repo / ".claude" / "skills").resolve())

    def fake_lstat(path, *args, **kwargs):
        result = real_lstat(path, *args, **kwargs)
        if os.fspath(path) == write_root_str:
            fields = list(result)
            fields[stat.ST_DEV] = result.st_dev + 1
            return os.stat_result(fields)
        return result

    monkeypatch.setattr(os, "lstat", fake_lstat)

    exit_code, err = _run_capturing_stderr(team_repo)

    assert exit_code != 0
    assert "different filesystem" in err
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()


# --------------------------------------------------------------------------
# Phase J step 2: unit-level repository boundaries (Decision 37; R1, O1)
# --------------------------------------------------------------------------


def _run_uninstall_capturing_stderr(
    team_repo: Path, dry_run: bool = False
) -> tuple[int, str]:
    import contextlib
    import io

    buffer = io.StringIO()
    with contextlib.redirect_stderr(buffer):
        exit_code = uninstall_sidecar(team_repo, dry_run=dry_run)
    return exit_code, buffer.getvalue()


def test_previously_owned_unit_turned_gitlink_is_never_touched(
    team_repo: Path,
) -> None:
    """R1/O1: uninstall used to delete a team submodule's tracked files
    (LICENSE) after a previously sidecar-owned unit became a gitlink, and
    reported it as an ordinary team-owned skip. Fails on 010f08c."""
    assert install_sidecar(team_repo, SOURCE) == 0
    unit_dir = team_repo / ".claude" / "skills" / "ponytail"
    _init_repo(unit_dir)
    _commit(unit_dir, "nested repository content")
    nested_status_before = _status(unit_dir)
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team embeds ponytail as a gitlink")

    assert install_sidecar(team_repo, SOURCE) == 0
    assert _status(unit_dir) == nested_status_before
    assert install_sidecar(team_repo, SOURCE) == 0  # update rerun
    assert _status(unit_dir) == nested_status_before
    assert install_sidecar(team_repo, SOURCE, dry_run=True) == 0
    assert _status(unit_dir) == nested_status_before

    assert uninstall_sidecar(team_repo, dry_run=True) == 0
    assert _status(unit_dir) == nested_status_before
    exit_code = uninstall_sidecar(team_repo)

    assert exit_code == 0
    assert (unit_dir / "SKILL.md").is_file()
    assert (unit_dir / "LICENSE").is_file()
    assert _status(unit_dir) == nested_status_before


def test_disk_only_nested_repo_at_recorded_unit_aborts_every_mode(
    team_repo: Path,
) -> None:
    """R1/O1: a disk-only nested repository at a unit the sidecar already
    owns must abort before any write in every mode, not be silently moved
    into the preserved folder. Fails on 010f08c."""
    assert install_sidecar(team_repo, SOURCE) == 0
    unit_dir = team_repo / ".claude" / "skills" / "ponytail"
    _init_repo(unit_dir)
    _commit(unit_dir, "nested repository content")
    nested_status_before = _status(unit_dir)
    outer_status_before = _status(team_repo)
    manifest_before = _read_manifest(team_repo)

    for dry_run in (True, False):
        exit_code, err = _run_capturing_stderr(team_repo, dry_run=dry_run)
        assert exit_code != 0
        assert "nested repository or submodule" in err
        assert "nothing was written" in err
        assert _status(unit_dir) == nested_status_before
        assert _status(team_repo) == outer_status_before
        assert _read_manifest(team_repo) == manifest_before

    for dry_run in (True, False):
        exit_code, err = _run_uninstall_capturing_stderr(team_repo, dry_run=dry_run)
        assert exit_code != 0
        assert "nested repository or submodule" in err
        assert "nothing was written" in err
        assert _status(unit_dir) == nested_status_before
        assert _status(team_repo) == outer_status_before
        assert _read_manifest(team_repo) == manifest_before


def test_personal_clone_never_owned_is_skipped_as_foreign(team_repo: Path) -> None:
    """Guard: a personal nested clone at a unit the sidecar never recorded
    or listed is foreign; its skill is skipped everywhere, the other units
    still install, and nothing inside the clone changes. A second run and a
    dry run must both agree that nothing changes further."""
    unit_dir = team_repo / ".claude" / "skills" / "ponytail"
    _nested_clone(unit_dir)
    clone_status_before = _status(unit_dir)

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert not (team_repo / ".agents" / "skills" / "ponytail").exists()
    assert _status(unit_dir) == clone_status_before
    assert (team_repo / ".claude" / "skills" / "humanize").is_dir()
    manifest = _read_manifest(team_repo)
    assert ".claude/skills/ponytail" not in manifest["units"]

    status_before = _status(team_repo)
    exclude_before = _exclude_path(team_repo).read_bytes()
    assert install_sidecar(team_repo, SOURCE, dry_run=True) == 0
    assert _status(team_repo) == status_before
    assert _exclude_path(team_repo).read_bytes() == exclude_before
    assert _read_manifest(team_repo) == manifest
    assert _status(unit_dir) == clone_status_before

    assert install_sidecar(team_repo, SOURCE) == 0
    assert _status(team_repo) == status_before
    assert _exclude_path(team_repo).read_bytes() == exclude_before
    assert _read_manifest(team_repo) == manifest
    assert _status(unit_dir) == clone_status_before


def test_real_submodule_at_recorded_unit_installs_and_uninstalls_cleanly(
    team_repo: Path, tmp_path: Path
) -> None:
    """Guard: a real `git submodule add` at a previously owned unit must not
    produce a false ignore-gate failure, and uninstall must delete nothing
    inside it. Already passes on 010f08c (a fatal check-ignore error inside
    the submodule is silently swallowed there rather than raised, which
    happens to leave this specific scenario's exit codes and files
    unaffected); `test_fatal_check_ignore_error_aborts_naming_gits_message`
    is the real regression test for that swallowed error."""
    assert install_sidecar(team_repo, SOURCE) == 0
    unit_dir = team_repo / ".claude" / "skills" / "ponytail"
    shutil.rmtree(unit_dir)
    _add_submodule(team_repo, ".claude/skills/ponytail", tmp_path)
    nested_status_before = _status(unit_dir)

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert _status(unit_dir) == nested_status_before
    assert install_sidecar(team_repo, SOURCE, dry_run=True) == 0
    assert _status(unit_dir) == nested_status_before

    exit_code = uninstall_sidecar(team_repo)

    assert exit_code == 0
    assert (unit_dir / "settings.json").is_file()
    assert _status(unit_dir) == nested_status_before


def test_team_skill_with_its_own_submodule_one_level_down(
    team_repo: Path, tmp_path: Path
) -> None:
    """Guard: a tracked team skill folder that holds its own submodule must
    not abort and must never gain a bogus exclude line for a path inside the
    submodule. Already passes on 010f08c for this specific layout (Git's own
    check-ignore fatal error for a submodule path is silently swallowed
    there, and happens to leave this outcome unaffected); this guards the
    structural fix (Decision 37) against regressing it."""
    team_content = "---\nname: ponytail\n---\nTEAM-OWNED-PONYTAIL\n"
    _write(team_repo / ".claude" / "skills" / "ponytail" / "SKILL.md", team_content)
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team owns ponytail")
    _add_submodule(team_repo, ".claude/skills/ponytail/vendor", tmp_path)
    vendor_dir = team_repo / ".claude" / "skills" / "ponytail" / "vendor"
    vendor_status_before = _status(vendor_dir)

    for dry_run in (True, False):
        assert install_sidecar(team_repo, SOURCE, dry_run=dry_run) == 0
        assert _status(vendor_dir) == vendor_status_before
    exclude_text = _exclude_path(team_repo).read_text(encoding="utf-8")
    assert "vendor" not in exclude_text

    for dry_run in (True, False):
        assert uninstall_sidecar(team_repo, dry_run=dry_run) == 0
        assert _status(vendor_dir) == vendor_status_before
    assert (vendor_dir / "settings.json").is_file()
    assert (
        team_repo.joinpath(".claude", "skills", "ponytail", "SKILL.md").read_text(
            encoding="utf-8"
        )
        == team_content
    )


def test_gitlink_below_a_unit_drops_a_stale_retained_line_and_reports_it(
    team_repo: Path, tmp_path: Path, capsys
) -> None:
    """Decision 37: nothing at or under any gitlink index entry keeps a file
    line, including a gitlink nested inside a unit -- not only when the
    whole unit is one. A stale retained line that now falls under it must
    be dropped and reported, never sent to check-ignore (which exits 128 for
    a path inside a submodule)."""
    assert install_sidecar(team_repo, SOURCE) == 0
    unit_dir = team_repo / ".claude" / "skills" / "ponytail"
    vendor_dir = unit_dir / "vendor"
    vendor_dir.mkdir()
    (vendor_dir / "notes.txt").write_bytes(b"kept by a person\n")
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team takes ponytail SKILL.md")

    assert install_sidecar(team_repo, SOURCE) == 0
    manifest = _read_manifest(team_repo)
    assert manifest["retained"] == [".claude/skills/ponytail/vendor/notes.txt"]
    assert _is_ignored(team_repo, ".claude/skills/ponytail/vendor/notes.txt")

    # vendor becomes a real submodule whose own tracked content happens to
    # collide in name with the stale retained file; a bug that tries to
    # re-hide "notes.txt" would send a path inside the submodule to
    # check-ignore, which exits 128 ("is in submodule").
    shutil.rmtree(vendor_dir)
    submodule_source = tmp_path / "vendor-submodule-source"
    _init_repo(submodule_source)
    _write(submodule_source / "notes.txt", "submodule content, different bytes\n")
    _commit(submodule_source, "submodule content")
    add = _git(
        team_repo,
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "add",
        "-f",
        "-q",
        str(submodule_source),
        ".claude/skills/ponytail/vendor",
    )
    assert add.returncode == 0, add.stderr
    _commit(team_repo, "add vendor submodule")
    vendor_status_before = _status(vendor_dir)

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    manifest_after = _read_manifest(team_repo)
    assert manifest_after["retained"] == []
    exclude_text = _exclude_path(team_repo).read_text(encoding="utf-8")
    assert "notes.txt" not in exclude_text
    out = capsys.readouterr().out
    assert "RETAINED .claude/skills/ponytail/vendor/notes.txt" in out
    assert "now visible" in out
    assert (vendor_dir / "notes.txt").read_text(
        encoding="utf-8"
    ) == "submodule content, different bytes\n"
    assert _status(vendor_dir) == vendor_status_before

    status_before = _status(team_repo)
    assert install_sidecar(team_repo, SOURCE) == 0
    assert _status(team_repo) == status_before


def test_fatal_check_ignore_error_aborts_naming_gits_message(
    team_repo: Path, monkeypatch
) -> None:
    """A `check-ignore` exit other than 0 or 1 (for example 128) must abort
    naming Git's message, never be treated as a partial ignore set. Uses a
    rerun of an already-installed unit so gathering has real untracked-file
    candidates to check (a fresh install has none yet)."""
    assert install_sidecar(team_repo, SOURCE) == 0
    manifest_before = _read_manifest(team_repo)
    status_before = _status(team_repo)
    real_run = subprocess.run

    def fake_run(args, *a, **kw):
        if len(args) >= 3 and args[0] == "git" and "check-ignore" in args:
            return subprocess.CompletedProcess(
                args, 128, stdout=b"", stderr=b"fatal: injected check-ignore failure\n"
            )
        return real_run(args, *a, **kw)

    monkeypatch.setattr(sidecar_overlay_module.subprocess, "run", fake_run)

    exit_code, err = _run_capturing_stderr(team_repo)

    assert exit_code != 0
    assert "injected check-ignore failure" in err
    assert _status(team_repo) == status_before
    assert _read_manifest(team_repo) == manifest_before


def test_check_ignore_raises_on_fatal_exit_code(monkeypatch) -> None:
    """Guard/unit-level: ``_check_ignore`` itself raises ``GitCheckIgnoreError``
    on a Git exit code other than 0 or 1, instead of returning a partial set."""

    def fake_run(args, *a, **kw):
        return subprocess.CompletedProcess(args, 128, stdout=b"", stderr=b"fatal: x\n")

    monkeypatch.setattr(sidecar_overlay_module.subprocess, "run", fake_run)

    with pytest.raises(GitCheckIgnoreError, match="fatal: x"):
        sidecar_overlay_module._check_ignore(Path("."), ["a"])


# --------------------------------------------------------------------------
# Phase J step 3: complete snapshots (Decision 38; R4, O9, O17 special-file)
# --------------------------------------------------------------------------


def test_named_pipe_in_installed_unit_uninstall_preserves_it_intact(
    team_repo: Path,
) -> None:
    """R4/O17: a personal FIFO inside an otherwise-matching installed unit
    used to be silently deleted along with the rest of the unit on
    uninstall. Fails on 010f08c. Runs the CLI in a subprocess with a
    timeout so the test process never opens the pipe."""
    assert install_sidecar(team_repo, SOURCE) == 0
    pipe_path = team_repo / ".claude" / "skills" / "ponytail" / "personal-channel"
    os.mkfifo(pipe_path)
    preserved_root = git_path(team_repo, "ai-bootstrap-sidecar-preserved")

    result = subprocess.run(
        [sys.executable, str(INSTALLER), str(team_repo), "--uninstall"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()
    entries = list(preserved_root.iterdir())
    assert len(entries) == 1
    preserved_dir = entries[0]
    assert stat.S_ISFIFO((preserved_dir / "personal-channel").stat().st_mode)
    assert (preserved_dir / "SKILL.md").is_file()
    assert (preserved_dir / "LICENSE").is_file()


def test_named_pipe_in_installed_unit_then_update_keeps_it_locally_modified(
    team_repo: Path, tmp_path: Path
) -> None:
    """R4/O17 variant: a personal FIFO must also block a plain hash-match
    update from silently replacing the unit; it stays locally modified
    instead. Fails on 010f08c. Runs the CLI in a subprocess with a timeout
    so the test process never opens the pipe."""
    assert install_sidecar(team_repo, SOURCE) == 0
    pipe_path = team_repo / ".claude" / "skills" / "ponytail" / "personal-channel"
    os.mkfifo(pipe_path)
    mutated_source = tmp_path / "mutated-source"
    shutil.copytree(SOURCE, mutated_source)
    mutated_file = mutated_source / ".claude" / "skills" / "ponytail" / "SKILL.md"
    mutated_file.write_text(
        mutated_file.read_text(encoding="utf-8") + "\nmutated upstream\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            str(team_repo),
            "--mode",
            "sidecar",
            "--source",
            str(mutated_source),
        ],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "has local edits" in result.stdout
    assert stat.S_ISFIFO(pipe_path.stat().st_mode)
    content = (team_repo / ".claude" / "skills" / "ponytail" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "mutated upstream" not in content


def test_unix_socket_in_installed_unit_uninstall_preserves_it_intact(
    team_repo: Path,
) -> None:
    """R4/O17: a Unix socket behaves the same as a named pipe. Fails on
    010f08c. Runs the CLI in a subprocess with a timeout; the socket is
    only bound (never connected or accepted), which never blocks."""
    assert install_sidecar(team_repo, SOURCE) == 0
    socket_path = team_repo / ".claude" / "skills" / "ponytail" / "personal.sock"
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        sock.bind(str(socket_path))
    finally:
        sock.close()
    preserved_root = git_path(team_repo, "ai-bootstrap-sidecar-preserved")

    result = subprocess.run(
        [sys.executable, str(INSTALLER), str(team_repo), "--uninstall"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()
    entries = list(preserved_root.iterdir())
    assert len(entries) == 1
    preserved_dir = entries[0]
    assert stat.S_ISSOCK((preserved_dir / "personal.sock").stat().st_mode)


def test_empty_subfolder_added_to_installed_unit_is_locally_modified(
    team_repo: Path, capsys
) -> None:
    """Decision 38: an empty subfolder makes an otherwise-matching unit
    locally modified rather than staying "unchanged". Fails on 010f08c."""
    assert install_sidecar(team_repo, SOURCE) == 0
    empty_dir = team_repo / ".claude" / "skills" / "ponytail" / "empty"
    empty_dir.mkdir()

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert empty_dir.is_dir()
    manifest = _read_manifest(team_repo)
    assert ".claude/skills/ponytail" in manifest["units"]
    out = capsys.readouterr().out
    assert "has local edits" in out


def test_team_tracked_skill_with_a_symlink_is_team_owned_others_install(
    team_repo: Path,
) -> None:
    """O9: Decision 25 says a tracked unit is team-owned before any symlink
    check; a symlink inside it must never abort the whole run. Fails on
    010f08c (the old inner-symlink abort ran first)."""
    unit_dir = team_repo / ".claude" / "skills" / "ponytail"
    unit_dir.mkdir(parents=True)
    _write(unit_dir / "SKILL.md", "---\nname: ponytail\n---\nTEAM\n")
    (unit_dir / "mylink").symlink_to("SKILL.md")
    _commit(team_repo, "team owns ponytail with a symlink", ".claude/skills/ponytail")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert (team_repo / ".claude" / "skills" / "humanize").is_dir()
    assert (unit_dir / "mylink").is_symlink()


def test_untracked_owned_unit_with_inner_symlink_is_locally_modified_no_abort(
    team_repo: Path, capsys
) -> None:
    """Decision 38: an inner symlink inside a unit must never abort the
    whole run; only a symlinked ancestor still does. Fails on 010f08c."""
    assert install_sidecar(team_repo, SOURCE) == 0
    (team_repo / ".claude" / "skills" / "ponytail" / "mylink").symlink_to("SKILL.md")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    assert (team_repo / ".claude" / "skills" / "ponytail" / "mylink").is_symlink()
    out = capsys.readouterr().out
    assert "has local edits" in out
    manifest = _read_manifest(team_repo)
    assert ".claude/skills/ponytail" in manifest["units"]


def test_symlink_persists_through_team_takeover_then_uninstall_reports_it_visible(
    team_repo: Path, capsys
) -> None:
    """Decision 38: an untracked symlink inside a taken-over unit is
    retained with its own line while it exists, stable over a second run,
    and reported as now visible on uninstall. Fails on 010f08c."""
    assert install_sidecar(team_repo, SOURCE) == 0
    unit_dir = team_repo / ".claude" / "skills" / "ponytail"
    (unit_dir / "mylink").symlink_to("SKILL.md")
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/ponytail/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team takes ponytail SKILL.md")

    exit_code = install_sidecar(team_repo, SOURCE)
    assert exit_code == 0
    assert (unit_dir / "mylink").is_symlink()
    assert _is_ignored(team_repo, ".claude/skills/ponytail/mylink")
    out = capsys.readouterr().out
    assert "RETAINED .claude/skills/ponytail/mylink" in out

    status_before = _status(team_repo)
    assert install_sidecar(team_repo, SOURCE) == 0
    assert _status(team_repo) == status_before
    assert (unit_dir / "mylink").is_symlink()

    uninstall_exit = uninstall_sidecar(team_repo)

    assert uninstall_exit == 0
    assert (unit_dir / "mylink").is_symlink()
    assert not _is_ignored(team_repo, ".claude/skills/ponytail/mylink")
    assert ".claude/skills/ponytail/mylink" in _status(team_repo)


# --------------------------------------------------------------------------
# Phase J step 4: retained files of dropped skills (Decision 43; O4)
# --------------------------------------------------------------------------


def test_retained_file_of_a_later_dropped_skill_stays_hidden_after_lost_manifest(
    team_repo: Path, tmp_path: Path, monkeypatch, capsys
) -> None:
    """O4: a listed retained file of a skill the sidecar later stops
    shipping used to be silently un-hidden once its manifest record (and
    then the whole manifest) was gone, because ``required_snapshot_units``
    never snapshotted its owning unit. Fails on 010f08c."""
    assert install_sidecar(team_repo, SOURCE) == 0
    notes = team_repo / ".claude" / "skills" / "humanize" / "notes.md"
    notes.write_bytes(b"kept by a person\n")
    force_add = _git(team_repo, "add", "-f", "--", ".claude/skills/humanize/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(team_repo, "team takes humanize SKILL.md")
    assert install_sidecar(team_repo, SOURCE) == 0
    manifest = _read_manifest(team_repo)
    assert manifest["retained"] == [".claude/skills/humanize/notes.md"]
    assert _is_ignored(team_repo, ".claude/skills/humanize/notes.md")

    # Version 2 drops humanize from the profile.
    reduced_source = tmp_path / "reduced-source"
    shutil.copytree(SOURCE, reduced_source)
    for write_root in (".claude/skills", ".agents/skills"):
        shutil.rmtree(reduced_source / write_root / "humanize")
    patch_sidecar_skills(
        monkeypatch, ("debug-investigator", "ponytail", "ponytail-review")
    )

    # The invalid-manifest remedy: move the manifest aside and rerun.
    manifest_path = _manifest_path(team_repo)
    manifest_path.rename(manifest_path.with_name(manifest_path.name + ".bak"))

    exit_code = install_sidecar(team_repo, reduced_source)

    assert exit_code == 0
    assert notes.is_file()
    assert _is_ignored(team_repo, ".claude/skills/humanize/notes.md")
    assert ".claude/skills/humanize/notes.md" not in _status(team_repo)
    out = capsys.readouterr().out
    assert "RETAINED .claude/skills/humanize/notes.md" in out

    uninstall_exit = uninstall_sidecar(team_repo)

    assert uninstall_exit == 0
    assert notes.is_file()
    assert not _is_ignored(team_repo, ".claude/skills/humanize/notes.md")
    assert ".claude/skills/humanize/notes.md" in _status(team_repo)
    uninstall_out = capsys.readouterr().out
    assert "RETAINED .claude/skills/humanize/notes.md" in uninstall_out
    assert "now visible" in uninstall_out


# --------------------------------------------------------------------------
# Phase J step 5: planner gate paths (Decision 40; O10, O11)
# --------------------------------------------------------------------------


def test_team_negation_exposes_an_unfinished_unit_aborts_and_restores(
    team_repo: Path,
) -> None:
    """O11: the gate used to build its path set only from manifest records
    and actions, so an unfinished unit (listed, no record, content not
    matching desired) was never checked -- a team negation could expose it
    while the run still reported "stays hidden". Fails on 010f08c."""
    assert install_sidecar(team_repo, SOURCE) == 0
    skill_md = team_repo / ".claude" / "skills" / "ponytail" / "SKILL.md"
    skill_md.write_text(
        skill_md.read_text(encoding="utf-8") + "\nEDIT\n", encoding="utf-8"
    )
    _manifest_path(team_repo).unlink()

    gitignore = team_repo / ".gitignore"
    _write(
        gitignore, gitignore.read_text(encoding="utf-8") + "!/.claude/skills/ponytail\n"
    )
    _commit(team_repo, "team un-ignores ponytail", ".gitignore")
    status_before = _status(team_repo)
    exclude_before = _exclude_path(team_repo).read_bytes()

    exit_code, err = _run_capturing_stderr(team_repo)

    assert exit_code != 0
    assert "ABORT" in err
    assert not _manifest_path(team_repo).exists()
    assert _exclude_path(team_repo).read_bytes() == exclude_before
    assert _status(team_repo) == status_before


def test_team_negation_of_one_skill_names_only_that_path_in_the_failure(
    team_repo: Path,
) -> None:
    """O10: ``run_ignore_gate`` used to pass the whole expected set to the
    verbose explainer, so a single team negation produced a failure message
    naming every correctly ignored sidecar path too, not just the exposed
    one. Fails on 010f08c."""
    gitignore = team_repo / ".gitignore"
    _write(
        gitignore, gitignore.read_text(encoding="utf-8") + "!/.claude/skills/humanize\n"
    )
    _commit(team_repo, "team un-ignores only humanize", ".gitignore")

    exit_code, err = _run_capturing_stderr(team_repo)

    assert exit_code != 0
    assert ".claude/skills/humanize/" in err
    for other in ("ponytail", "ponytail-review", "debug-investigator"):
        assert f"{other}/" not in err
    assert ".agents/skills/humanize/" not in err


def test_installed_unit_replaced_by_a_symlink_installs_clean_no_gate_failure(
    team_repo: Path, tmp_path: Path
) -> None:
    """A symlink unit gated with a trailing slash makes Git exit 128
    ("beyond a symbolic link"), which used to fail the gate outright.
    Decision 40: a non-folder unit is gated without the trailing slash.
    Fails on 010f08c."""
    assert install_sidecar(team_repo, SOURCE) == 0
    unit_dir = team_repo / ".claude" / "skills" / "ponytail"
    shutil.rmtree(unit_dir)
    personal_folder = tmp_path / "personal-ponytail"
    personal_folder.mkdir()
    (personal_folder / "SKILL.md").write_text("personal\n", encoding="utf-8")
    unit_dir.symlink_to(personal_folder, target_is_directory=True)

    exit_code, err = _run_capturing_stderr(team_repo)

    assert exit_code == 0
    assert err == ""
    assert unit_dir.is_symlink()
    assert _is_ignored(team_repo, ".claude/skills/ponytail")


def test_installed_unit_replaced_by_a_plain_file_is_locally_modified_and_preserved(
    team_repo: Path, capsys
) -> None:
    """Guard: a plain regular file at an installed unit path is already
    kept as locally modified on install, preserved intact on uninstall, and
    skipped as foreign before any install -- confirmed on 010f08c. Guards
    the MINOR fix that gates such a unit as `<unit>`, never `<unit>/`
    (Decision 40): a plain file is neither a real folder nor absent."""
    assert install_sidecar(team_repo, SOURCE) == 0
    unit_dir = team_repo / ".claude" / "skills" / "humanize"
    shutil.rmtree(unit_dir)
    content = b"a personal file where a folder used to be\n"
    unit_dir.write_bytes(content)

    exit_code, err = _run_capturing_stderr(team_repo)

    assert exit_code == 0
    assert err == ""
    assert unit_dir.is_file()
    assert unit_dir.read_bytes() == content
    assert _is_ignored(team_repo, ".claude/skills/humanize")
    out = capsys.readouterr().out
    assert "has local edits" in out

    status_before = _status(team_repo)
    assert install_sidecar(team_repo, SOURCE, dry_run=True) == 0
    assert _status(team_repo) == status_before
    assert install_sidecar(team_repo, SOURCE) == 0
    assert _status(team_repo) == status_before
    assert unit_dir.read_bytes() == content

    exit_code = uninstall_sidecar(team_repo)

    assert exit_code == 0
    preserved_root = git_path(team_repo, "ai-bootstrap-sidecar-preserved")
    entries = list(preserved_root.iterdir())
    assert len(entries) == 1
    assert entries[0].read_bytes() == content
    assert not unit_dir.exists()
    assert ".claude/skills/humanize" not in _status(team_repo)


# --------------------------------------------------------------------------
# Phase J step 7: accurate reports and the NITs (Decisions 44, 46; O12,
# O15, O16, O17)
# --------------------------------------------------------------------------


def test_taken_skill_with_a_conflict_copy_reports_kept_not_skipped(
    team_repo: Path, capsys
) -> None:
    """O12: while a conflict copy remains, a taken skill's other taking
    paths must report it as kept until the conflict is resolved, never as
    skipped at every root -- the edited copy the conflict kept is still
    there. Fails on 010f08c."""
    assert install_sidecar(team_repo, SOURCE) == 0
    edited = team_repo / ".claude" / "skills" / "ponytail" / "SKILL.md"
    edited.write_text(
        edited.read_text(encoding="utf-8") + "\nEDITED\n", encoding="utf-8"
    )

    unit_dir = edited.parent
    file_hashes = {
        p.relative_to(unit_dir).as_posix(): sidecar_overlay_module.compute_file_hash(
            p.read_bytes()
        )
        for p in sorted(unit_dir.rglob("*"))
        if p.is_file()
    }
    content_hash = sidecar_overlay_module.compute_unit_hash(file_hashes)
    slug = sidecar_overlay_module.preserved_unit_slug(
        ".claude/skills/ponytail", content_hash
    )
    conflicting = git_path(team_repo, "ai-bootstrap-sidecar-preserved") / slug
    conflicting.mkdir(parents=True)

    _write(
        team_repo / ".github" / "skills" / "ponytail" / "SKILL.md", "team elsewhere\n"
    )

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "kept in place until its edited-copy conflict is resolved" in out
    assert "skips `ponytail` at every root" not in out
    assert edited.exists()


def test_uninstall_nothing_to_do_prints_preserved_folder_path(
    team_repo: Path, capsys
) -> None:
    """O16: uninstall's own "no sidecar found; nothing to do" path must
    still print the preserved-copy folder's path whenever it holds
    anything. Fails on 010f08c."""
    assert install_sidecar(team_repo, SOURCE) == 0
    exit_code_1 = uninstall_sidecar(team_repo)
    assert exit_code_1 == 0
    preserved_root = git_path(team_repo, "ai-bootstrap-sidecar-preserved")
    # This fixture's install/uninstall never has a conflict, so make a
    # leftover preserved entry by hand to prove the "nothing to do" path
    # still reports it.
    leftover = preserved_root / "leftover-from-an-earlier-run"
    leftover.mkdir(parents=True)
    (leftover / "notes.txt").write_text("kept\n", encoding="utf-8")
    capsys.readouterr()

    exit_code_2 = uninstall_sidecar(team_repo)

    assert exit_code_2 == 0
    out = capsys.readouterr().out
    assert "no sidecar found; nothing to do" in out
    assert str(preserved_root) in out


def test_cli_uninstall_nothing_to_do_prints_preserved_folder_path(
    team_repo: Path,
) -> None:
    """O16: the CLI's own "no sidecar found; nothing to do" path
    (install_bootstrap.py) must also print the preserved-copy folder's path
    whenever it holds anything. Fails on 010f08c."""
    assert install_sidecar(team_repo, SOURCE) == 0
    assert uninstall_sidecar(team_repo) == 0
    preserved_root = git_path(team_repo, "ai-bootstrap-sidecar-preserved")
    leftover = preserved_root / "leftover-from-an-earlier-run"
    leftover.mkdir(parents=True)
    (leftover / "notes.txt").write_text("kept\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(INSTALLER), str(team_repo), "--uninstall"],
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "no sidecar found; nothing to do" in result.stdout
    assert str(preserved_root) in result.stdout


# --------------------------------------------------------------------------
# Phase H step 7: require complete, exact sources (Decision 31; S13, S14, L2)
# --------------------------------------------------------------------------


def test_empty_source_is_refused_and_removes_nothing(
    team_repo: Path, tmp_path: Path
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    status_before = _status(team_repo)
    empty_source = tmp_path / "empty-source"
    empty_source.mkdir()

    exit_code, err = _run_capturing_stderr(team_repo, source=empty_source)

    assert exit_code != 0
    assert "missing" in err
    assert _status(team_repo) == status_before
    assert (team_repo / ".claude" / "skills" / "ponytail").is_dir()


def test_source_with_only_claude_folder_is_refused(
    team_repo: Path, tmp_path: Path
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    status_before = _status(team_repo)
    partial_source = tmp_path / "partial-source"
    shutil.copytree(SOURCE / ".claude", partial_source / ".claude")

    exit_code, err = _run_capturing_stderr(team_repo, source=partial_source)

    assert exit_code != 0
    assert "missing" in err or "incomplete" in err
    assert _status(team_repo) == status_before
    assert (team_repo / ".claude" / "skills" / "ponytail").is_dir()
    assert (team_repo / ".agents" / "skills" / "ponytail").is_dir()


def test_source_with_an_extra_file_is_refused(team_repo: Path, tmp_path: Path) -> None:
    crafted = tmp_path / "crafted-source"
    shutil.copytree(SOURCE, crafted)
    (crafted / ".claude" / "skills" / "ponytail" / "extra.md").write_text(
        "stray\n", encoding="utf-8"
    )

    exit_code, err = _run_capturing_stderr(team_repo, source=crafted)

    assert exit_code != 0
    assert "extra.md" in err or "unexpected" in err
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()


def test_crafted_tree_gets_the_same_verdict_from_validator_and_installer(
    tmp_path: Path,
) -> None:
    import validate_targets

    crafted = tmp_path / "crafted-source"
    shutil.copytree(SOURCE, crafted)
    shutil.rmtree(crafted / ".agents" / "skills" / "ponytail")

    installer_violations = sidecar_overlay_module._sidecar_source_violations(crafted)
    validator_errors = validate_targets.sidecar_target_errors(crafted)

    assert installer_violations
    assert any("incomplete" in error for error in validator_errors)
    # Both flag the exact same missing skill, not merely "something is wrong".
    assert any("ponytail" in violation for violation in installer_violations)
    assert any("ponytail" in error for error in validator_errors)


def test_source_with_only_two_of_four_skills_is_refused_and_removes_nothing(
    team_repo: Path, tmp_path: Path
) -> None:
    # Decision 31, full enforcement: a source that is internally symmetric
    # (both write roots agree) but simply thinner than the real profile must
    # still be refused -- not silently accepted as "a smaller profile".
    assert install_sidecar(team_repo, SOURCE) == 0
    status_before = _status(team_repo)
    reduced = tmp_path / "reduced-two-of-four"
    shutil.copytree(SOURCE, reduced)
    for write_root in (".claude/skills", ".agents/skills"):
        shutil.rmtree(reduced / write_root / "debug-investigator")
        shutil.rmtree(reduced / write_root / "humanize")

    exit_code, err = _run_capturing_stderr(team_repo, source=reduced)

    assert exit_code != 0
    assert "missing" in err
    assert _status(team_repo) == status_before
    assert (team_repo / ".claude" / "skills" / "ponytail").is_dir()
    assert (team_repo / ".claude" / "skills" / "humanize").is_dir()
    assert (team_repo / ".claude" / "skills" / "debug-investigator").is_dir()


def test_source_missing_a_bridge_is_refused(team_repo: Path, tmp_path: Path) -> None:
    crafted = tmp_path / "missing-bridge-source"
    shutil.copytree(SOURCE, crafted)
    (
        crafted / ".github" / "instructions" / "ai-bootstrap-sidecar.instructions.md"
    ).unlink()

    exit_code, err = _run_capturing_stderr(team_repo, source=crafted)

    assert exit_code != 0
    assert "missing" in err
    assert "ai-bootstrap-sidecar.instructions.md" in err
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()


def test_source_missing_a_ponytail_license_is_refused(
    team_repo: Path, tmp_path: Path
) -> None:
    crafted = tmp_path / "missing-license-source"
    shutil.copytree(SOURCE, crafted)
    (crafted / ".agents" / "skills" / "ponytail-review" / "LICENSE").unlink()

    exit_code, err = _run_capturing_stderr(team_repo, source=crafted)

    assert exit_code != 0
    assert "missing" in err
    assert ".agents/skills/ponytail-review/LICENSE" in err
    assert not (team_repo / ".claude" / "skills" / "ponytail").exists()


# --------------------------------------------------------------------------
# Phase H step 10: correct preflight and installer messages (Decision 36)
# --------------------------------------------------------------------------


def test_directory_only_negation_names_the_explanation_not_a_blank_rule(
    team_repo: Path, capsys
) -> None:
    gitignore = team_repo / ".gitignore"
    _write(gitignore, gitignore.read_text(encoding="utf-8") + "!.claude/skills/*/\n")
    _commit(team_repo, "team un-ignores sidecar skill folders", ".gitignore")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code != 0
    err = capsys.readouterr().err
    assert "directory-only" in err or "un-ignoring the folder" in err
    assert "does not exist yet" in err


def test_ignore_gate_remedy_never_tells_person_to_edit_team_gitignore(
    team_repo: Path, capsys
) -> None:
    gitignore = team_repo / ".gitignore"
    _write(gitignore, gitignore.read_text(encoding="utf-8") + "!.claude/skills/**\n")
    _commit(team_repo, "team un-ignores .claude/skills", ".gitignore")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code != 0
    err = capsys.readouterr().err
    assert "ask the team to change" in err
    assert "remove your own negation from info/exclude" in err
    assert "fix the team .gitignore" not in err


def test_invalid_manifest_remedy_matches_the_big_plans_text(
    team_repo: Path, capsys
) -> None:
    _manifest_path(team_repo).write_text("{not valid json", encoding="utf-8")

    exit_code = install_sidecar(team_repo, SOURCE)

    assert exit_code != 0
    err = capsys.readouterr().err
    assert "any other listed unit is kept hidden and reported" in err
    assert "reported as foreign" not in err


def test_sidecar_source_overlap_error_never_suggests_allow_self(
    tmp_path: Path,
) -> None:
    target = tmp_path / "nested"
    target.mkdir(parents=True)
    _init_repo(target)
    source_inside_target = target / "dist" / "sidecar"
    shutil.copytree(SOURCE, source_inside_target)

    with pytest.raises(SystemExit) as error:
        install_bootstrap.validate_install_roots(
            source_inside_target, target, allow_self=False, suggest_allow_self=False
        )
    assert "--allow-self" not in str(error.value)


def test_linked_worktree_full_mode_message_names_evidence_not_a_manual_fix(
    team_repo: Path, tmp_path: Path
) -> None:
    assert install_sidecar(team_repo, SOURCE) == 0
    linked = tmp_path / "linked-worktree"
    added = _git(team_repo, "worktree", "add", "-q", str(linked), "-b", "linked-branch")
    assert added.returncode == 0, added.stderr

    result_full = subprocess.run(
        [sys.executable, str(INSTALLER), str(linked), "--mode", "full"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result_full.returncode != 0
    assert "sidecar evidence" in result_full.stderr
    assert "shared by every worktree" in result_full.stderr
    assert "Remove that sidecar evidence manually" not in result_full.stderr


def test_missing_explicit_source_names_that_path(team_repo: Path) -> None:
    missing = team_repo / "does-not-exist-source"
    result = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            str(team_repo),
            "--mode",
            "sidecar",
            "--source",
            str(missing),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert str(missing) in result.stderr
    assert "generate_targets.py --all" not in result.stderr


def test_missing_default_source_says_to_run_generate_targets(tmp_path: Path) -> None:
    fake_default = tmp_path / "does-not-exist-default-sidecar-source"

    with pytest.raises(SystemExit) as error:
        install_bootstrap.require_source_exists(fake_default, explicit=False)
    message = str(error.value)
    assert str(fake_default) in message
    assert "generate_targets.py --all" in message

    with pytest.raises(SystemExit) as error_explicit:
        install_bootstrap.require_source_exists(fake_default, explicit=True)
    assert "generate_targets.py --all" not in str(error_explicit.value)


def test_symlinked_ancestor_abort_says_sidecar_mode_does_not_support_it(
    team_repo: Path,
) -> None:
    shutil.rmtree(team_repo / ".agents" / "skills")
    (team_repo / ".agents" / "skills").symlink_to(
        team_repo / ".claude" / "skills", target_is_directory=True
    )

    exit_code, err = _run_capturing_stderr(team_repo)

    assert exit_code != 0
    assert "sidecar mode does not support" in err
    assert "nothing was written" in err
    assert "replace tracked team content" not in err
