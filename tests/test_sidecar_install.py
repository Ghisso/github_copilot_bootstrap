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

import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import sidecar_overlay as sidecar_overlay_module  # noqa: E402
from sidecar_overlay import escape_exact_path, git_path, install_sidecar  # noqa: E402
from sidecar_test_helpers import (  # noqa: E402
    _commit,
    _commit_staged,
    _exclude_path,
    _git,
    _init_repo,
    _manifest_path,
    _raise_at,
    _read_manifest,
    _status,
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
    assert "move the manifest aside" in err
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
    assert "move the manifest aside" in result.stderr


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
    assert "the repository tracks" in out
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
    team_repo: Path, tmp_path: Path, capsys
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
    reduced_source = tmp_path / "reduced-source"
    shutil.copytree(SOURCE, reduced_source)
    for write_root in (".claude/skills", ".agents/skills"):
        shutil.rmtree(reduced_source / write_root / "debug-investigator")

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
