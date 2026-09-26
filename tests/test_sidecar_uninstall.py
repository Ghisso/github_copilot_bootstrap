"""Failing-first coverage for ``--uninstall`` (Decision 34; the small plan's
Phase H step 9, ``.claude/plans/2026-09-25_phase-H-sidecar-preflight-robustness-and-uninstall.md``).

``dist/sidecar`` is used as the source throughout, exactly like
``tests/test_sidecar_install.py``: it is small, real, and self-contained.
Every test that needs a real Git commit runs it in-process through
pytest/subprocess, which the repository's own commit-gate hook does not
intercept (see ``docs/sidecar-provider-contract.md``).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import sidecar_overlay as sidecar_overlay_module  # noqa: E402
from sidecar_overlay import (  # noqa: E402
    compute_file_hash,
    compute_unit_hash,
    install_sidecar,
    preserved_unit_slug,
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
)

INSTALLER = REPO_ROOT / "scripts" / "install_bootstrap.py"
UPDATER = REPO_ROOT / "scripts" / "update_consumers.py"
SOURCE = REPO_ROOT / "dist" / "sidecar"


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _is_ignored(root: Path, relative_path: str) -> bool:
    return _git(root, "check-ignore", "-q", "--", relative_path).returncode == 0


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    _init_repo(root)
    _write(root / "README.md", "# repo\n")
    _commit(root, "init")
    return root


def _staging_path(repo: Path) -> Path:
    return _absolute_git_dir(repo) / "ai-bootstrap-sidecar-staging"


def _preserved_root(repo: Path) -> Path:
    return _absolute_git_dir(repo) / "ai-bootstrap-sidecar-preserved"


def _sidecar_files(repo: Path) -> list[str]:
    return sorted(
        p.relative_to(repo).as_posix()
        for p in repo.rglob("*")
        if p.is_file() and ".git" not in p.parts
    )


# --------------------------------------------------------------------------
# Clean install then uninstall
# --------------------------------------------------------------------------


def test_clean_install_then_uninstall_restores_status_and_removes_everything(
    repo: Path,
) -> None:
    status_before = _status(repo)

    assert install_sidecar(repo, SOURCE) == 0
    assert install_sidecar is not None  # sanity: real install happened
    assert _sidecar_files(repo) != ["README.md"]

    exit_code = uninstall_sidecar(repo)

    assert exit_code == 0
    assert _status(repo) == status_before
    assert _sidecar_files(repo) == ["README.md"]
    assert not _manifest_path(repo).is_file()
    assert not _staging_path(repo).exists()
    exclude_text = _exclude_path(repo).read_text(encoding="utf-8")
    assert "ai-bootstrap sidecar" not in exclude_text


def test_uninstall_before_any_sidecar_install_says_nothing_to_do(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exit_code = uninstall_sidecar(repo)

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "no sidecar found; nothing to do" in out


def test_second_uninstall_prints_nothing_to_do(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(repo, SOURCE) == 0
    assert uninstall_sidecar(repo) == 0
    capsys.readouterr()

    exit_code = uninstall_sidecar(repo)

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "no sidecar found; nothing to do" in out


# --------------------------------------------------------------------------
# Preservation, retained files, team/foreign content, unrecognized lines
# --------------------------------------------------------------------------


def test_edited_copy_is_preserved_on_uninstall(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(repo, SOURCE) == 0
    edited = repo / ".claude" / "skills" / "ponytail" / "SKILL.md"
    edited.write_text(
        edited.read_text(encoding="utf-8") + "\nEDITED\n", encoding="utf-8"
    )
    edited_bytes = edited.read_bytes()

    exit_code = uninstall_sidecar(repo)

    assert exit_code == 0
    assert not edited.exists()
    preserved_entries = list(_preserved_root(repo).iterdir())
    assert len(preserved_entries) == 1
    assert preserved_entries[0].name.startswith(".claude__skills__ponytail--")
    assert (preserved_entries[0] / "SKILL.md").read_bytes() == edited_bytes
    out = capsys.readouterr().out
    assert f"PRESERVED .claude/skills/ponytail -> {preserved_entries[0]}" in out
    assert "uninstalled" in out


def test_edited_bridge_is_preserved_as_a_file_on_uninstall(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(repo, SOURCE) == 0
    bridge = repo / ".claude" / "rules" / "ai-bootstrap-sidecar.md"
    bridge.write_text(
        bridge.read_text(encoding="utf-8") + "\nEDITED BRIDGE\n", encoding="utf-8"
    )
    bridge_bytes = bridge.read_bytes()

    exit_code = uninstall_sidecar(repo)

    assert exit_code == 0
    assert not bridge.exists()
    preserved_entries = [
        p
        for p in _preserved_root(repo).iterdir()
        if p.name.startswith(".claude__rules__")
    ]
    assert len(preserved_entries) == 1
    assert preserved_entries[0].is_file()
    assert preserved_entries[0].read_bytes() == bridge_bytes


def test_listed_copy_with_no_record_is_preserved_on_uninstall(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(repo, SOURCE) == 0
    manifest_path = _manifest_path(repo)
    manifest_path.rename(manifest_path.with_name(manifest_path.name + ".bak"))

    exit_code = uninstall_sidecar(repo)

    assert exit_code == 0
    out = capsys.readouterr().out
    # Every unit was still listed by the exclude block (no record, since the
    # manifest is gone): an "unfinished sidecar copy" that uninstall must
    # preserve, not silently remove.
    preserved_entries = list(_preserved_root(repo).iterdir())
    assert len(preserved_entries) == 10
    assert out.count("PRESERVED") == 20  # one action line + one report line each


def test_retained_file_becomes_visible_and_reported_on_uninstall(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(repo, SOURCE) == 0
    user_file = repo / ".claude" / "skills" / "ponytail" / "user-notes.txt"
    user_file.write_bytes(b"kept by a person\n")
    force_add = _git(repo, "add", "-f", "--", ".claude/skills/ponytail/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(repo, "team takes ponytail SKILL.md")
    assert install_sidecar(repo, SOURCE) == 0  # records user-notes.txt retained
    manifest = _read_manifest(repo)
    assert manifest["retained"] == [".claude/skills/ponytail/user-notes.txt"]
    capsys.readouterr()

    exit_code = uninstall_sidecar(repo)

    assert exit_code == 0
    assert user_file.exists()
    assert not _is_ignored(repo, ".claude/skills/ponytail/user-notes.txt")
    status = _status(repo)
    assert "?? .claude/skills/ponytail/user-notes.txt" in status
    out = capsys.readouterr().out
    assert "user-notes.txt" in out
    assert "now visible to `git add -A`" in out


def test_team_and_foreign_content_untouched_on_uninstall(repo: Path) -> None:
    assert install_sidecar(repo, SOURCE) == 0

    team_content = "---\nname: humanize\n---\nTEAM-OWNED-HUMANIZE\n"
    _write(repo / ".claude" / "skills" / "humanize" / "SKILL.md", team_content)
    force_add = _git(repo, "add", "-f", "--", ".claude/skills/humanize")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(repo, "team owns humanize")

    foreign = repo / ".claude" / "skills" / "not-a-sidecar-skill" / "SKILL.md"
    _write(foreign, "unrelated content\n")
    foreign_bytes = foreign.read_bytes()

    exit_code = uninstall_sidecar(repo)

    assert exit_code == 0
    assert (repo / ".claude" / "skills" / "humanize" / "SKILL.md").read_text(
        encoding="utf-8"
    ) == team_content
    assert not (repo / ".agents" / "skills" / "humanize").exists()
    assert foreign.read_bytes() == foreign_bytes


def test_unrecognized_block_line_survives_as_a_plain_line_on_uninstall(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(repo, SOURCE) == 0
    exclude_path = _exclude_path(repo)
    text = exclude_path.read_text(encoding="utf-8")
    exclude_path.write_text(
        text.replace(
            "# END ai-bootstrap sidecar", "my-own-rule.txt\n# END ai-bootstrap sidecar"
        ),
        encoding="utf-8",
    )

    exit_code = uninstall_sidecar(repo)

    assert exit_code == 0
    final_text = exclude_path.read_text(encoding="utf-8")
    assert "ai-bootstrap sidecar" not in final_text
    assert "my-own-rule.txt" in final_text
    out = capsys.readouterr().out
    assert "my-own-rule.txt" in out


# --------------------------------------------------------------------------
# Preserve-destination conflict: the one exception to Decision 9
# --------------------------------------------------------------------------


def test_preserve_conflict_keeps_unit_and_block_rewrites_manifest_exits_1(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(repo, SOURCE) == 0
    edited = repo / ".claude" / "skills" / "ponytail" / "SKILL.md"
    edited.write_text(
        edited.read_text(encoding="utf-8") + "\nEDITED\n", encoding="utf-8"
    )
    edited_bytes = edited.read_bytes()

    unit_dir = edited.parent
    file_hashes = {
        p.relative_to(unit_dir).as_posix(): compute_file_hash(p.read_bytes())
        for p in sorted(unit_dir.rglob("*"))
        if p.is_file()
    }
    content_hash = compute_unit_hash(file_hashes)
    slug = preserved_unit_slug(".claude/skills/ponytail", content_hash)
    conflicting = _preserved_root(repo) / slug
    conflicting.mkdir(parents=True)
    (conflicting / "sentinel.txt").write_text("already here\n", encoding="utf-8")

    exit_code = uninstall_sidecar(repo)

    assert exit_code == 1
    assert edited.read_bytes() == edited_bytes  # kept in place, not preserved
    assert (conflicting / "sentinel.txt").is_file()  # conflict destination untouched
    manifest = _read_manifest(repo)
    assert list(manifest["units"]) == [".claude/skills/ponytail"]
    exclude_text = _exclude_path(repo).read_text(encoding="utf-8")
    assert "ai-bootstrap sidecar" in exclude_text  # the block survives
    assert "/.claude/skills/ponytail\n" in exclude_text
    # Every other unit still finished uninstalling.
    assert not (repo / ".agents" / "skills" / "ponytail").exists()
    assert not (repo / ".claude" / "skills" / "humanize").exists()
    out = capsys.readouterr().out
    assert "resolve" in out.lower()

    # Rerun after resolving the conflict by hand: finishes the uninstall.
    conflicting.rename(conflicting.with_name(conflicting.name + ".resolved"))
    exit_code_2 = uninstall_sidecar(repo)
    assert exit_code_2 == 0
    assert not _manifest_path(repo).is_file()
    assert "ai-bootstrap sidecar" not in _exclude_path(repo).read_text(encoding="utf-8")


def test_preserve_conflict_with_a_negation_aborts_before_any_write(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Review fix 1 (CRITICAL): a preserve conflict must re-prove the kept
    # unit is still actually ignored before keeping it in place -- a
    # person's own negation of exactly that path must abort the whole run,
    # not report the unit as safely kept while it is visible in git status.
    assert install_sidecar(repo, SOURCE) == 0
    edited = repo / ".claude" / "skills" / "ponytail" / "SKILL.md"
    edited.write_text(
        edited.read_text(encoding="utf-8") + "\nEDITED\n", encoding="utf-8"
    )
    edited_bytes = edited.read_bytes()

    unit_dir = edited.parent
    file_hashes = {
        p.relative_to(unit_dir).as_posix(): compute_file_hash(p.read_bytes())
        for p in sorted(unit_dir.rglob("*"))
        if p.is_file()
    }
    content_hash = compute_unit_hash(file_hashes)
    slug = preserved_unit_slug(".claude/skills/ponytail", content_hash)
    conflicting = _preserved_root(repo) / slug
    conflicting.mkdir(parents=True)
    (conflicting / "sentinel.txt").write_text("already here\n", encoding="utf-8")

    exclude_path = _exclude_path(repo)
    exclude_text = exclude_path.read_text(encoding="utf-8")
    exclude_path.write_text(
        exclude_text + "!/.claude/skills/ponytail/\n", encoding="utf-8"
    )
    exclude_before = exclude_path.read_bytes()
    manifest_before = _manifest_path(repo).read_bytes()
    status_before = _status(repo)

    dry_exit = uninstall_sidecar(repo, dry_run=True)
    dry_err = capsys.readouterr().err

    assert dry_exit == 1
    assert ".claude/skills/ponytail" in dry_err
    assert _exclude_path(repo).read_bytes() == exclude_before
    assert _manifest_path(repo).read_bytes() == manifest_before
    assert _status(repo) == status_before
    assert edited.read_bytes() == edited_bytes
    assert (unit_dir / "LICENSE").exists()
    assert (repo / ".agents" / "skills" / "humanize").exists()  # nothing removed

    exit_code = uninstall_sidecar(repo)
    err = capsys.readouterr().err

    assert exit_code == 1
    assert ".claude/skills/ponytail" in err
    assert exclude_path.read_bytes() == exclude_before
    assert _manifest_path(repo).read_bytes() == manifest_before
    assert _status(repo) == status_before
    assert edited.read_bytes() == edited_bytes
    assert (unit_dir / "LICENSE").exists()
    assert (repo / ".agents" / "skills" / "humanize").exists()
    assert (conflicting / "sentinel.txt").is_file()


def test_unfinished_conflict_with_a_negation_aborts_before_any_write(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Review fix 1 round 2 (CRITICAL): an unfinished (unrecorded) conflicting
    # unit has no manifest record and no action, so a gate built only from
    # _write_raw_paths()/next_manifest.units misses it entirely. The exact
    # coordinator reproduction: lose the manifest, pre-create the preserve
    # destination from the unit's current content, add a negation.
    assert install_sidecar(repo, SOURCE) == 0
    unit_dir = repo / ".claude" / "skills" / "ponytail"
    _manifest_path(repo).unlink()

    file_hashes = {
        p.relative_to(unit_dir).as_posix(): compute_file_hash(p.read_bytes())
        for p in sorted(unit_dir.rglob("*"))
        if p.is_file()
    }
    content_hash = compute_unit_hash(file_hashes)
    slug = preserved_unit_slug(".claude/skills/ponytail", content_hash)
    conflicting = _preserved_root(repo) / slug
    conflicting.mkdir(parents=True)
    (conflicting / "sentinel.txt").write_text("already here\n", encoding="utf-8")

    exclude_path = _exclude_path(repo)
    exclude_text = exclude_path.read_text(encoding="utf-8")
    exclude_path.write_text(
        exclude_text + "!/.claude/skills/ponytail/\n", encoding="utf-8"
    )
    exclude_before = exclude_path.read_bytes()
    skill_bytes = (unit_dir / "SKILL.md").read_bytes()
    license_bytes = (unit_dir / "LICENSE").read_bytes()
    status_before = _status(repo)

    dry_exit = uninstall_sidecar(repo, dry_run=True)
    dry_err = capsys.readouterr().err

    assert dry_exit == 1
    assert ".claude/skills/ponytail" in dry_err
    assert exclude_path.read_bytes() == exclude_before
    assert _status(repo) == status_before
    assert (unit_dir / "SKILL.md").read_bytes() == skill_bytes
    assert (unit_dir / "LICENSE").read_bytes() == license_bytes
    assert (repo / ".agents" / "skills" / "humanize").exists()  # nothing removed

    exit_code = uninstall_sidecar(repo)
    err = capsys.readouterr().err

    assert exit_code == 1
    assert ".claude/skills/ponytail" in err
    assert exclude_path.read_bytes() == exclude_before
    assert _status(repo) == status_before
    assert (unit_dir / "SKILL.md").read_bytes() == skill_bytes
    assert (unit_dir / "LICENSE").read_bytes() == license_bytes
    assert (repo / ".agents" / "skills" / "humanize").exists()
    assert (conflicting / "sentinel.txt").is_file()


def test_unfinished_conflict_with_no_negation_keeps_unit_hidden(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # Same setup, but without any drift: the gate must pass and the
    # unfinished unit stays in place, still hidden by its own block line,
    # with no manifest record (Decision 23) -- the SKIPPED report says so.
    assert install_sidecar(repo, SOURCE) == 0
    unit_dir = repo / ".claude" / "skills" / "ponytail"
    _manifest_path(repo).unlink()

    file_hashes = {
        p.relative_to(unit_dir).as_posix(): compute_file_hash(p.read_bytes())
        for p in sorted(unit_dir.rglob("*"))
        if p.is_file()
    }
    content_hash = compute_unit_hash(file_hashes)
    slug = preserved_unit_slug(".claude/skills/ponytail", content_hash)
    conflicting = _preserved_root(repo) / slug
    conflicting.mkdir(parents=True)
    (conflicting / "sentinel.txt").write_text("already here\n", encoding="utf-8")
    skill_bytes = (unit_dir / "SKILL.md").read_bytes()

    exit_code = uninstall_sidecar(repo)
    out = capsys.readouterr().out

    assert exit_code == 1
    assert (unit_dir / "SKILL.md").read_bytes() == skill_bytes
    assert (unit_dir / "LICENSE").exists()
    exclude_text = _exclude_path(repo).read_text(encoding="utf-8")
    assert "/.claude/skills/ponytail\n" in exclude_text
    assert _is_ignored(repo, ".claude/skills/ponytail/SKILL.md")
    assert "unfinished sidecar copy" in out
    assert "no manifest record" in out
    # Every other unit still finished uninstalling.
    assert not (repo / ".agents" / "skills" / "ponytail").exists()
    assert not (repo / ".claude" / "skills" / "humanize").exists()


def test_bridge_preserve_conflict_is_checked_by_the_gate(repo: Path) -> None:
    # A bridge can reach the same conflict path as a skill (Decision 24: a
    # bridge preserves as a file); the gate must cover it exactly the same
    # way.
    assert install_sidecar(repo, SOURCE) == 0
    bridge = repo / ".claude" / "rules" / "ai-bootstrap-sidecar.md"
    bridge.write_text(
        bridge.read_text(encoding="utf-8") + "\nEDITED BRIDGE\n", encoding="utf-8"
    )
    bridge_bytes = bridge.read_bytes()

    content_hash = compute_unit_hash(
        {"ai-bootstrap-sidecar.md": compute_file_hash(bridge_bytes)}
    )
    slug = preserved_unit_slug(".claude/rules/ai-bootstrap-sidecar.md", content_hash)
    conflicting = _preserved_root(repo) / slug
    conflicting.parent.mkdir(parents=True, exist_ok=True)
    conflicting.write_text("already here\n", encoding="utf-8")

    exit_code = uninstall_sidecar(repo)

    assert exit_code == 1
    assert bridge.read_bytes() == bridge_bytes
    exclude_text = _exclude_path(repo).read_text(encoding="utf-8")
    assert "ai-bootstrap-sidecar.md\n" in exclude_text
    assert _is_ignored(repo, ".claude/rules/ai-bootstrap-sidecar.md")


# --------------------------------------------------------------------------
# Dry run and fault-point convergence
# --------------------------------------------------------------------------


def test_uninstall_dry_run_writes_nothing_and_predicts_the_real_run(
    repo: Path,
) -> None:
    assert install_sidecar(repo, SOURCE) == 0
    status_before = _status(repo)
    exclude_before = _exclude_path(repo).read_bytes()
    manifest_before = _manifest_path(repo).read_bytes()
    staging_before = sorted(_staging_path(repo).iterdir())

    dry_exit = uninstall_sidecar(repo, dry_run=True)

    assert dry_exit == 0
    assert _status(repo) == status_before
    assert _exclude_path(repo).read_bytes() == exclude_before
    assert _manifest_path(repo).read_bytes() == manifest_before
    assert sorted(_staging_path(repo).iterdir()) == staging_before

    real_exit = uninstall_sidecar(repo)
    assert real_exit == dry_exit
    assert not _manifest_path(repo).is_file()
    assert not _staging_path(repo).exists()


def test_uninstall_dry_run_predicts_a_preserve_conflict(repo: Path) -> None:
    assert install_sidecar(repo, SOURCE) == 0
    edited = repo / ".claude" / "skills" / "ponytail" / "SKILL.md"
    edited.write_text(
        edited.read_text(encoding="utf-8") + "\nEDITED\n", encoding="utf-8"
    )
    unit_dir = edited.parent
    file_hashes = {
        p.relative_to(unit_dir).as_posix(): compute_file_hash(p.read_bytes())
        for p in sorted(unit_dir.rglob("*"))
        if p.is_file()
    }
    content_hash = compute_unit_hash(file_hashes)
    slug = preserved_unit_slug(".claude/skills/ponytail", content_hash)
    conflicting = _preserved_root(repo) / slug
    conflicting.mkdir(parents=True)

    dry_exit = uninstall_sidecar(repo, dry_run=True)

    assert dry_exit == 1
    assert edited.exists()  # dry run wrote nothing
    assert _manifest_path(repo).is_file()


def test_fault_after_units_removed_rerun_converges(
    repo: Path, monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(repo, SOURCE) == 0
    monkeypatch.setattr(
        sidecar_overlay_module, "_fault_point", _raise_at("after_units_removed")
    )
    with pytest.raises(RuntimeError, match="after_units_removed"):
        uninstall_sidecar(repo)
    capsys.readouterr()

    # Pre-rerun state: every unit already moved out; the block and manifest
    # still hold their pre-uninstall bytes.
    assert not (repo / ".claude" / "skills" / "ponytail").exists()
    assert _manifest_path(repo).is_file()
    exclude_text = _exclude_path(repo).read_text(encoding="utf-8")
    assert "ai-bootstrap sidecar" in exclude_text

    monkeypatch.setattr(sidecar_overlay_module, "_fault_point", lambda name: None)
    exit_code = uninstall_sidecar(repo)

    assert exit_code == 0
    assert not _manifest_path(repo).is_file()
    assert "ai-bootstrap sidecar" not in _exclude_path(repo).read_text(encoding="utf-8")


def test_fault_before_manifest_write_rerun_converges(
    repo: Path, monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(repo, SOURCE) == 0
    monkeypatch.setattr(
        sidecar_overlay_module, "_fault_point", _raise_at("before_manifest_write")
    )
    with pytest.raises(RuntimeError, match="before_manifest_write"):
        uninstall_sidecar(repo)
    capsys.readouterr()

    # Pre-rerun state: the block is already gone, but the manifest was not
    # deleted yet.
    assert "ai-bootstrap sidecar" not in _exclude_path(repo).read_text(encoding="utf-8")
    assert _manifest_path(repo).is_file()

    monkeypatch.setattr(sidecar_overlay_module, "_fault_point", lambda name: None)
    exit_code = uninstall_sidecar(repo)

    assert exit_code == 0
    assert not _manifest_path(repo).is_file()


# --------------------------------------------------------------------------
# CLI: mode refusals and detection wiring
# --------------------------------------------------------------------------


def test_full_evidence_refuses_uninstall(tmp_path: Path) -> None:
    target = tmp_path / "full-consumer"
    _init_repo(target)
    result = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            str(target),
            "--mode",
            "full",
            "--local-only",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    refused = subprocess.run(
        [sys.executable, str(INSTALLER), str(target), "--uninstall"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert refused.returncode != 0
    assert "full-install evidence" in refused.stderr
    assert (target / ".claude" / ".git").exists()


def test_mode_full_uninstall_is_refused(repo: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(INSTALLER), str(repo), "--mode", "full", "--uninstall"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert "--mode full" in result.stderr


def test_uninstall_with_no_mode_works_when_sidecar_evidence_present(
    repo: Path,
) -> None:
    assert install_sidecar(repo, SOURCE) == 0

    result = subprocess.run(
        [sys.executable, str(INSTALLER), str(repo), "--uninstall"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert not (repo / ".claude" / "skills" / "ponytail").exists()


def test_uninstall_skips_the_team_config_refusal(repo: Path) -> None:
    assert install_sidecar(repo, SOURCE) == 0
    # Team config content that would otherwise make a plain (no --mode)
    # install refuse with "tracks bootstrap-owned paths" -- --uninstall must
    # never even reach that check.
    _write(repo / ".devcontainer" / "devcontainer.json", "{}\n")
    _commit(repo, "team adds devcontainer", ".devcontainer/devcontainer.json")

    result = subprocess.run(
        [sys.executable, str(INSTALLER), str(repo), "--uninstall"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "tracks bootstrap-owned paths" not in result.stderr
    assert not (repo / ".claude" / "skills" / "ponytail").exists()
    assert (repo / ".devcontainer" / "devcontainer.json").is_file()


def test_uninstall_dry_run_cli_flag(repo: Path) -> None:
    assert install_sidecar(repo, SOURCE) == 0
    result = subprocess.run(
        [sys.executable, str(INSTALLER), str(repo), "--uninstall", "--dry-run"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repo / ".claude" / "skills" / "ponytail").is_dir()


# --------------------------------------------------------------------------
# update_consumers.py never forwards --uninstall
# --------------------------------------------------------------------------


def test_update_consumers_never_forwards_uninstall_source_has_no_flag() -> None:
    source_text = (REPO_ROOT / "scripts" / "update_consumers.py").read_text(
        encoding="utf-8"
    )
    assert "--uninstall" not in source_text


def test_update_consumers_batch_leaves_sidecar_installed(tmp_path: Path) -> None:
    sidecar_target = tmp_path / "sidecar-consumer"
    _init_repo(sidecar_target)
    assert install_sidecar(sidecar_target, SOURCE) == 0

    result = subprocess.run(
        [
            sys.executable,
            str(UPDATER),
            "--skip-regen",
            "--local-only",
            str(sidecar_target),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert (sidecar_target / ".claude" / "skills" / "ponytail").is_dir()


# --------------------------------------------------------------------------
# Review fix 1 (CRITICAL): "nothing to do" must not ignore a block that
# holds only unrecognized lines, or an empty balanced block
# --------------------------------------------------------------------------


def _write_raw_exclude(repo: Path, text: str) -> None:
    exclude_path = _absolute_git_dir(repo) / "info" / "exclude"
    exclude_path.parent.mkdir(parents=True, exist_ok=True)
    exclude_path.write_text(text, encoding="utf-8")


def test_lost_manifest_with_only_an_unrecognized_line_is_not_nothing_to_do(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(repo, SOURCE) == 0
    _manifest_path(repo).unlink()
    _write_raw_exclude(
        repo,
        "# BEGIN ai-bootstrap sidecar\nmy-own-rule.txt\n# END ai-bootstrap sidecar\n",
    )
    capsys.readouterr()

    exit_code = uninstall_sidecar(repo)

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "no sidecar found; nothing to do" not in out
    exclude_text = _exclude_path(repo).read_text(encoding="utf-8")
    assert "ai-bootstrap sidecar" not in exclude_text
    assert "my-own-rule.txt" in exclude_text
    assert "my-own-rule.txt" in out

    capsys.readouterr()
    second_exit = uninstall_sidecar(repo)
    assert second_exit == 0
    assert "no sidecar found; nothing to do" in capsys.readouterr().out


def test_lost_manifest_with_an_empty_block_is_not_nothing_to_do(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(repo, SOURCE) == 0
    _manifest_path(repo).unlink()
    _write_raw_exclude(
        repo, "# BEGIN ai-bootstrap sidecar\n# END ai-bootstrap sidecar\n"
    )
    capsys.readouterr()

    exit_code = uninstall_sidecar(repo)

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "no sidecar found; nothing to do" not in out
    exclude_text = _exclude_path(repo).read_text(encoding="utf-8")
    assert "ai-bootstrap sidecar" not in exclude_text


# --------------------------------------------------------------------------
# Review fix 2 (MAJOR): a first-time team takeover during uninstall makes a
# retained file visible, not "stays hidden"
# --------------------------------------------------------------------------


def test_first_time_team_takeover_during_uninstall_makes_retained_file_visible(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(repo, SOURCE) == 0
    unit_dir = repo / ".claude" / "skills" / "ponytail"
    personal_file = unit_dir / "my-notes.txt"
    personal_file.write_bytes(b"kept by a person\n")
    assert _is_ignored(repo, ".claude/skills/ponytail/my-notes.txt")

    force_add = _git(repo, "add", "-f", "--", ".claude/skills/ponytail/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(repo, "team takes ponytail SKILL.md")
    team_bytes = (unit_dir / "SKILL.md").read_bytes()
    capsys.readouterr()

    exit_code = uninstall_sidecar(repo)

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "my-notes.txt" in out
    assert "now visible to `git add -A`" in out
    assert "stays hidden" not in out
    assert not _is_ignored(repo, ".claude/skills/ponytail/my-notes.txt")
    assert personal_file.exists()
    # The team's own file is untouched, and the sidecar's other matching
    # files in the same unit are gone (deleted as sidecar bytes).
    assert (unit_dir / "SKILL.md").read_bytes() == team_bytes
    assert not (unit_dir / "LICENSE").exists()
