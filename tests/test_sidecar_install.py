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

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import sidecar_overlay as sidecar_overlay_module  # noqa: E402
from runtime_ownership import SIDECAR_MANIFEST_NAME  # noqa: E402
from sidecar_overlay import escape_exact_path, git_path, install_sidecar  # noqa: E402

INSTALLER = REPO_ROOT / "scripts" / "install_bootstrap.py"
SOURCE = REPO_ROOT / "dist" / "sidecar"
BAD_SOURCE = REPO_ROOT / "dist" / "multi-agent"


# --------------------------------------------------------------------------
# Git helpers
# --------------------------------------------------------------------------


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _commit_staged(root: Path, message: str) -> None:
    commit = _git(
        root,
        "-c",
        "user.name=sidecar-test",
        "-c",
        "user.email=sidecar-test@example.invalid",
        "commit",
        "-q",
        "-m",
        message,
    )
    assert commit.returncode == 0, commit.stderr


def _commit(root: Path, message: str, *paths: str) -> None:
    """Stage ``paths`` (or everything, on a fresh fixture with nothing else
    untracked) and commit. Never use bare ``-A`` once a sidecar file might be
    visible: that would sweep it into tracking instead of leaving it as the
    "still untracked" state a given scenario needs."""
    add = _git(root, "add", "--", *paths) if paths else _git(root, "add", "-A")
    assert add.returncode == 0, add.stderr
    _commit_staged(root, message)


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    result = _git(root, "init", "-q")
    assert result.returncode == 0, result.stderr


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _status(root: Path) -> str:
    result = _git(root, "status", "--porcelain", "--untracked-files=all")
    assert result.returncode == 0, result.stderr
    return result.stdout


def _is_ignored(root: Path, relative_path: str) -> bool:
    return _git(root, "check-ignore", "-q", "--", relative_path).returncode == 0


def _exclude_path(root: Path) -> Path:
    return git_path(root, "info/exclude")


def _manifest_path(root: Path) -> Path:
    return git_path(root, SIDECAR_MANIFEST_NAME)


def _read_manifest(root: Path) -> dict:
    return json.loads(_manifest_path(root).read_text(encoding="utf-8"))


def _raise_at(name: str):
    def _fault_point(point: str) -> None:
        if point == name:
            raise RuntimeError(f"injected fault at {point}")

    return _fault_point


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
    _commit(team_repo, "team owns ponytail", ".claude/skills/ponytail")

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
    assert "delete or restore" in out


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
