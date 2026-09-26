"""The sidecar upgrade regression suite (Phase D of the big plan
`.claude/plans/consumer-sidecar-bootstrap-overlay.md`).

Two groups of tests:

* Reconciliation across bootstrap versions: each test builds two small,
  synthetic "bootstrap versions" as fixture sidecar sources (only
  ``SIDECAR_SKILLS`` names are valid, per ``_sidecar_source_violations``),
  installs the first with ``install_sidecar`` directly, then updates to the
  second, and checks the reconciliation rule under test. These do not go
  through ``update_consumers.py``: the planner they exercise
  (``plan_sidecar_reconciliation``) is the same code path for install, rerun,
  and update (one reconciliation code path, per the big plan's Goals), so a
  fixture source is the fastest and most precise way to control exactly what
  changed between "versions".
* Batch behavior through ``update_consumers.py``: ``update_consumers.py``
  never accepts a ``--source`` override (it always lets
  ``install_bootstrap.py`` pick ``dist/multi-agent`` or ``dist/sidecar`` by
  detected mode), so these tests run it against the real generated trees
  instead of a fixture (``uv run python scripts/generate_targets.py --all``
  regenerates them; see this file's own verification command). Full-mode
  fixtures always pass ``--local-only`` so no test touches a network remote
  (see ``safe-consumer-bootstrap-refresh``).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import sidecar_overlay as sidecar_overlay_module  # noqa: E402
from runtime_ownership import SIDECAR_MANIFEST_NAME  # noqa: E402
from sidecar_overlay import git_path, install_sidecar  # noqa: E402
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
    install_sidecar_with_profile,
)

UPDATER = REPO_ROOT / "scripts" / "update_consumers.py"
INSTALLER = REPO_ROOT / "scripts" / "install_bootstrap.py"
SIDECAR_SOURCE = REPO_ROOT / "dist" / "sidecar"


# --------------------------------------------------------------------------
# Helpers local to this file (the shared git/file helpers live in
# tests/sidecar_test_helpers.py)
# --------------------------------------------------------------------------


def _tree_snapshot(root: Path) -> dict[Path, bytes | None]:
    return {
        path.relative_to(root): path.read_bytes() if path.is_file() else None
        for path in root.rglob("*")
    }


def _tree_state(root: Path) -> dict[Path, tuple[bytes, int] | None]:
    """Like ``_tree_snapshot``, plus each file's mtime, for idempotency
    checks that must rule out a needless rewrite, not just a byte change."""
    return {
        path.relative_to(root): (
            (path.read_bytes(), path.stat().st_mtime_ns) if path.is_file() else None
        )
        for path in root.rglob("*")
    }


def _file_state(path: Path) -> tuple[bytes, int] | None:
    if not path.is_file():
        return None
    return path.read_bytes(), path.stat().st_mtime_ns


def _sidecar_tree_state(repo: Path) -> dict[Path, tuple[bytes, int] | None]:
    """Combined ``_tree_state`` of both sidecar write roots. Safe to merge:
    ``.claude`` and ``.agents`` never share a relative sub-path."""
    return {**_tree_state(repo / ".claude"), **_tree_state(repo / ".agents")}


_DEFAULT_BRIDGES = {
    ".claude/rules/ai-bootstrap-sidecar.md": "default bridge body\n",
    ".github/instructions/ai-bootstrap-sidecar.instructions.md": (
        '---\napplyTo: "**"\n---\ndefault bridge body\n'
    ),
}


def _write_sidecar_source(
    root: Path,
    skills: dict[str, str],
    bridges: dict[str, str] | None = None,
) -> None:
    """Build a complete, valid sidecar tree for exactly ``skills`` (Decision
    31; Phase H2 hardening): each name at both write roots (``.claude/skills``,
    ``.agents/skills``), a ``LICENSE`` alongside any ``ponytail``/
    ``ponytail-review`` entry (the exact-source contract always requires
    it for those two names), and every bridge in ``SIDECAR_BRIDGES`` --
    ``bridges`` only overrides specific bridge bodies, it never drops one.
    A caller must pair this with ``install_sidecar_with_profile`` (or
    ``patch_sidecar_skills(monkeypatch, tuple(skills))``), which patches
    ``SIDECAR_SKILLS`` to exactly this call's names, so the tree this
    builds -- not the real, unrelated profile -- is what the completeness
    check compares against. Only real ``SIDECAR_SKILLS`` names (any name is
    fine once patched) and ``SIDECAR_BRIDGES`` paths are valid sidecar-unit
    shapes; anything else would make ``install_sidecar`` reject the whole
    source as not a sidecar tree (``_sidecar_source_violations``).
    """
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    for skill, content in skills.items():
        for write_root in (".claude/skills", ".agents/skills"):
            skill_file = root / write_root / skill / "SKILL.md"
            skill_file.parent.mkdir(parents=True, exist_ok=True)
            skill_file.write_text(content, encoding="utf-8")
            if skill in ("ponytail", "ponytail-review"):
                (skill_file.parent / "LICENSE").write_text(
                    "MIT placeholder license\n", encoding="utf-8"
                )
    for bridge_path, content in {**_DEFAULT_BRIDGES, **(bridges or {})}.items():
        file_path = root / bridge_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")


def _fabricate_sidecar_manifest(target: Path) -> None:
    """Write sidecar evidence directly (no real sidecar install), so a
    target can carry both full-install and sidecar evidence at once."""
    git_path(target, SIDECAR_MANIFEST_NAME).write_text("{}", encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    _init_repo(root)
    return root


# --------------------------------------------------------------------------
# 1-10, 15: reconciliation across bootstrap versions (install_sidecar)
# --------------------------------------------------------------------------


def test_skill_content_change_updates_both_write_roots(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    v1 = tmp_path / "v1"
    v2 = tmp_path / "v2"
    _write_sidecar_source(v1, {"ponytail": "ponytail v1\n"})
    _write_sidecar_source(v2, {"ponytail": "ponytail v2\n"})

    assert install_sidecar_with_profile(repo, v1, monkeypatch) == 0
    assert install_sidecar_with_profile(repo, v2, monkeypatch) == 0

    for write_root in (".claude/skills", ".agents/skills"):
        content = (repo / write_root / "ponytail" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        assert content == "ponytail v2\n"


def test_skill_added_in_new_version_is_installed(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    v1 = tmp_path / "v1"
    v2 = tmp_path / "v2"
    _write_sidecar_source(v1, {"ponytail": "content\n"})
    _write_sidecar_source(v2, {"ponytail": "content\n", "humanize": "humanize v1\n"})

    assert install_sidecar_with_profile(repo, v1, monkeypatch) == 0
    assert not (repo / ".claude" / "skills" / "humanize").exists()

    assert install_sidecar_with_profile(repo, v2, monkeypatch) == 0
    for write_root in (".claude/skills", ".agents/skills"):
        assert (repo / write_root / "humanize" / "SKILL.md").read_text(
            encoding="utf-8"
        ) == "humanize v1\n"


def test_skill_removed_deletes_unmodified_copy_but_keeps_modified_one(
    repo: Path, tmp_path: Path, monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    v1 = tmp_path / "v1"
    v2 = tmp_path / "v2"
    _write_sidecar_source(v1, {"debug-investigator": "debug v1\n"})
    # debug-investigator is gone in the new version; humanize keeps shipping
    # unchanged so v2 is not an empty source (Decision 31, S13: an empty or
    # partial source is refused, not silently treated as "remove everything").
    _write_sidecar_source(v2, {"humanize": "humanize v1\n"})

    assert install_sidecar_with_profile(repo, v1, monkeypatch) == 0
    modified = repo / ".claude" / "skills" / "debug-investigator" / "SKILL.md"
    modified.write_text("debug v1\nEDITED BY A PERSON\n", encoding="utf-8")
    edited_bytes = modified.read_bytes()

    exit_code = install_sidecar_with_profile(repo, v2, monkeypatch)

    assert exit_code == 0
    # Unmodified at .agents/skills: the desired content is gone and the unit
    # still matches its record, so it is removed.
    assert not (repo / ".agents" / "skills" / "debug-investigator").exists()
    # Modified at .claude/skills: kept, and reported, regardless of the
    # skill's removal upstream.
    assert modified.read_bytes() == edited_bytes
    out = capsys.readouterr().out
    assert "has local edits" in out
    assert "copy your edits elsewhere" in out


def test_bridge_text_change_updates_bridge_files(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    v1 = tmp_path / "v1"
    v2 = tmp_path / "v2"
    claude_bridge = ".claude/rules/ai-bootstrap-sidecar.md"
    copilot_bridge = ".github/instructions/ai-bootstrap-sidecar.instructions.md"
    _write_sidecar_source(
        v1,
        {"ponytail": "content\n"},
        {
            claude_bridge: "bridge v1\n",
            copilot_bridge: '---\napplyTo: "**"\n---\nbridge v1\n',
        },
    )
    _write_sidecar_source(
        v2,
        {"ponytail": "content\n"},
        {
            claude_bridge: "bridge v2\n",
            copilot_bridge: '---\napplyTo: "**"\n---\nbridge v2\n',
        },
    )

    assert install_sidecar_with_profile(repo, v1, monkeypatch) == 0
    assert install_sidecar_with_profile(repo, v2, monkeypatch) == 0

    assert (repo / claude_bridge).read_text(encoding="utf-8") == "bridge v2\n"
    assert (repo / copilot_bridge).read_text(encoding="utf-8") == (
        '---\napplyTo: "**"\n---\nbridge v2\n'
    )


def test_user_modified_projection_is_kept_and_reported_every_run(
    repo: Path, tmp_path: Path, monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    v1 = tmp_path / "v1"
    _write_sidecar_source(v1, {"ponytail": "content v1\n"})
    assert install_sidecar_with_profile(repo, v1, monkeypatch) == 0
    capsys.readouterr()

    skill_md = repo / ".claude" / "skills" / "ponytail" / "SKILL.md"
    skill_md.write_text("content v1\nEDITED\n", encoding="utf-8")
    edited_bytes = skill_md.read_bytes()

    exit_code_1 = install_sidecar_with_profile(repo, v1, monkeypatch)
    out_1 = capsys.readouterr().out
    exit_code_2 = install_sidecar_with_profile(repo, v1, monkeypatch)
    out_2 = capsys.readouterr().out

    assert exit_code_1 == 0
    assert exit_code_2 == 0
    assert skill_md.read_bytes() == edited_bytes
    assert "has local edits" in out_1
    assert "has local edits" in out_2


def test_projection_replaced_by_tracked_team_file_drops_record_and_line(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    v1 = tmp_path / "v1"
    _write_sidecar_source(v1, {"ponytail": "content v1\n"})
    assert install_sidecar_with_profile(repo, v1, monkeypatch) == 0

    skill_md = repo / ".claude" / "skills" / "ponytail" / "SKILL.md"
    force_add = _git(repo, "add", "-f", "--", ".claude/skills/ponytail/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(repo, "team takes ponytail SKILL.md")
    tracked_bytes = skill_md.read_bytes()

    exit_code = install_sidecar_with_profile(repo, v1, monkeypatch)

    assert exit_code == 0
    assert skill_md.read_bytes() == tracked_bytes  # file untouched
    manifest = _read_manifest(repo)
    assert ".claude/skills/ponytail" not in manifest["units"]
    exclude_text = _exclude_path(repo).read_text(encoding="utf-8")
    assert "/.claude/skills/ponytail\n" not in exclude_text


def test_unrelated_tracked_team_config_added_after_install_is_untouched(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    v1 = tmp_path / "v1"
    _write_sidecar_source(v1, {"ponytail": "content v1\n"})
    assert install_sidecar_with_profile(repo, v1, monkeypatch) == 0

    team_file = repo / "CLAUDE.md"
    team_file.write_text("# team\nTEAM-MARKER\n", encoding="utf-8")
    _commit(repo, "team adds CLAUDE.md", "CLAUDE.md")
    before = team_file.read_bytes()

    exit_code = install_sidecar_with_profile(repo, v1, monkeypatch)

    assert exit_code == 0
    assert team_file.read_bytes() == before


def test_exclude_block_deleted_by_user_is_restored(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    v1 = tmp_path / "v1"
    _write_sidecar_source(v1, {"ponytail": "content v1\n"})
    assert install_sidecar_with_profile(repo, v1, monkeypatch) == 0

    exclude_path = _exclude_path(repo)
    exclude_path.write_text("", encoding="utf-8")

    exit_code = install_sidecar_with_profile(repo, v1, monkeypatch)

    assert exit_code == 0
    exclude_text = exclude_path.read_text(encoding="utf-8")
    assert "/.claude/skills/ponytail\n" in exclude_text
    ignored = _git(repo, "check-ignore", "-q", "--", ".claude/skills/ponytail/SKILL.md")
    assert ignored.returncode == 0


def test_owned_projection_deleted_by_user_is_reinstalled(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    v1 = tmp_path / "v1"
    _write_sidecar_source(v1, {"ponytail": "content v1\n"})
    assert install_sidecar_with_profile(repo, v1, monkeypatch) == 0

    shutil.rmtree(repo / ".claude" / "skills" / "ponytail")

    exit_code = install_sidecar_with_profile(repo, v1, monkeypatch)

    assert exit_code == 0
    assert (repo / ".claude" / "skills" / "ponytail" / "SKILL.md").read_text(
        encoding="utf-8"
    ) == "content v1\n"


def test_manifest_corrupted_aborts_then_remedy_rerun_adopts_matching_units(
    repo: Path, tmp_path: Path, monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    v1 = tmp_path / "v1"
    _write_sidecar_source(v1, {"ponytail": "content v1\n", "humanize": "humanize v1\n"})
    assert install_sidecar_with_profile(repo, v1, monkeypatch) == 0
    manifest_path = _manifest_path(repo)
    manifest_path.write_text("{not valid json", encoding="utf-8")

    exit_code = install_sidecar_with_profile(repo, v1, monkeypatch)
    err = capsys.readouterr().err

    assert exit_code != 0
    assert "aside and rerun with --mode sidecar" in err
    assert "adopted" in err

    manifest_path.rename(manifest_path.with_name(manifest_path.name + ".bak"))
    exit_code = install_sidecar_with_profile(repo, v1, monkeypatch)

    assert exit_code == 0
    manifest = _read_manifest(repo)
    assert set(manifest["units"]) == {
        ".claude/skills/ponytail",
        ".agents/skills/ponytail",
        ".claude/skills/humanize",
        ".agents/skills/humanize",
        *_DEFAULT_BRIDGES,
    }


def test_install_then_two_updates_the_second_update_changes_no_file(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    v1 = tmp_path / "v1"
    v2 = tmp_path / "v2"
    _write_sidecar_source(v1, {"ponytail": "content v1\n"})
    _write_sidecar_source(v2, {"ponytail": "content v2\n"})

    assert install_sidecar_with_profile(repo, v1, monkeypatch) == 0
    assert (
        install_sidecar_with_profile(repo, v2, monkeypatch) == 0
    )  # first update: a real content change

    before = _sidecar_tree_state(repo)
    before_exclude = _file_state(_exclude_path(repo))
    before_manifest = _file_state(_manifest_path(repo))

    exit_code = install_sidecar_with_profile(
        repo, v2, monkeypatch
    )  # second update: no upstream change

    assert exit_code == 0
    assert _sidecar_tree_state(repo) == before
    assert _file_state(_exclude_path(repo)) == before_exclude
    assert _file_state(_manifest_path(repo)) == before_manifest


def test_dry_run_update_makes_no_changes(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    v1 = tmp_path / "v1"
    _write_sidecar_source(v1, {"ponytail": "content v1\n", "humanize": "humanize v1\n"})
    assert install_sidecar_with_profile(repo, v1, monkeypatch) == 0
    before = _sidecar_tree_state(repo)
    before_exclude = _file_state(_exclude_path(repo))
    before_manifest = _file_state(_manifest_path(repo))
    status_before = _status(repo)

    exit_code = install_sidecar_with_profile(repo, v1, monkeypatch, dry_run=True)

    assert exit_code == 0
    assert _status(repo) == status_before
    assert _sidecar_tree_state(repo) == before
    assert _file_state(_exclude_path(repo)) == before_exclude
    assert _file_state(_manifest_path(repo)) == before_manifest


# --------------------------------------------------------------------------
# 11-14: batch behavior through update_consumers.py
# --------------------------------------------------------------------------


def test_batch_target_with_both_evidence_kinds_is_refused_others_continue(
    tmp_path: Path,
) -> None:
    good = tmp_path / "good"
    _init_repo(good)

    bad = tmp_path / "bad"
    _init_repo(bad)
    setup = subprocess.run(
        [sys.executable, str(INSTALLER), str(bad), "--mode", "full", "--local-only"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert setup.returncode == 0, setup.stdout + setup.stderr
    _fabricate_sidecar_manifest(bad)
    before_bad = _tree_snapshot(bad)

    result = subprocess.run(
        [
            sys.executable,
            str(UPDATER),
            "--skip-regen",
            "--local-only",
            str(bad),
            str(good),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert f"FAILED: {bad} (exit 1)" in result.stdout
    assert "Refusing to auto-detect an install mode" in result.stderr
    assert "=== Done: good ===" in result.stdout
    assert "All projects updated." not in result.stdout
    assert _tree_snapshot(bad) == before_bad  # refused before any write


def test_batch_target_refused_by_agents_takeover_others_continue(
    tmp_path: Path,
) -> None:
    good = tmp_path / "good"
    _init_repo(good)

    bad = tmp_path / "bad"
    _init_repo(bad)
    private = bad / ".agents" / "skills" / "company-private" / "SKILL.md"
    private.parent.mkdir(parents=True)
    private.write_text("company-owned\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(UPDATER),
            "--skip-regen",
            "--local-only",
            str(bad),
            str(good),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert f"FAILED: {bad} (exit 1)" in result.stdout
    assert "Refusing .agents takeover" in result.stderr
    assert "=== Done: good ===" in result.stdout
    assert "All projects updated." not in result.stdout
    assert not (bad / ".claude").exists()


def test_mixed_batch_updates_full_and_sidecar_targets(tmp_path: Path) -> None:
    full_target = tmp_path / "full-consumer"
    _init_repo(full_target)
    sidecar_target = tmp_path / "sidecar-consumer"
    _init_repo(sidecar_target)
    assert install_sidecar(sidecar_target, SIDECAR_SOURCE) == 0

    result = subprocess.run(
        [
            sys.executable,
            str(UPDATER),
            "--skip-regen",
            "--local-only",
            str(full_target),
            str(sidecar_target),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "All projects updated." in result.stdout
    assert "=== Done: full-consumer ===" in result.stdout
    assert "=== Done: sidecar-consumer ===" in result.stdout
    assert (full_target / ".claude" / ".git").is_dir()
    assert (sidecar_target / ".claude" / "skills").is_dir()
    assert not (sidecar_target / ".claude" / ".git").exists()


def test_batch_reports_not_a_directory_targets_and_continues(tmp_path: Path) -> None:
    """Cheap coverage of the exact summary contract, without a real install:
    a missing target is recorded like any other failure and does not stop
    the batch."""
    missing = (tmp_path / "does-not-exist").resolve()
    good = tmp_path / "good"
    _init_repo(good)

    result = subprocess.run(
        [
            sys.executable,
            str(UPDATER),
            "--skip-regen",
            "--local-only",
            str(missing),
            str(good),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert f"FAILED: {missing} (exit 1)" in result.stdout
    assert "=== Done: good ===" in result.stdout
    assert "All projects updated." not in result.stdout


# --------------------------------------------------------------------------
# Option forwarding in mixed batches (Decision 13)
# --------------------------------------------------------------------------


def test_full_only_options_forwarded_to_full_and_warned_once_on_sidecar(
    tmp_path: Path,
) -> None:
    full_target = tmp_path / "full-consumer"
    _init_repo(full_target)
    sidecar_target = tmp_path / "sidecar-consumer"
    _init_repo(sidecar_target)
    assert install_sidecar(sidecar_target, SIDECAR_SOURCE) == 0

    result = subprocess.run(
        [
            sys.executable,
            str(UPDATER),
            "--skip-regen",
            "--local-only",
            "--commit-copilot-surface",
            str(full_target),
            str(sidecar_target),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "All projects updated." in result.stdout

    # --local-only is a silent no-op on a sidecar target: not named.
    # --commit-copilot-surface is full-only: named once and ignored.
    warning = (
        "WARNING install-bootstrap: sidecar install ignores full-only "
        "option(s): --commit-copilot-surface"
    )
    assert warning in result.stderr
    assert "--local-only" not in result.stderr
    assert (sidecar_target / ".claude" / "skills").is_dir()

    # The full target actually used the option: its ignore block does not
    # hide the Copilot surface it would hide by default.
    gitignore_text = (full_target / ".gitignore").read_text(encoding="utf-8")
    assert ".github/agents/" not in gitignore_text


# --------------------------------------------------------------------------
# Phase G step 2: R1, recovery obeys team precedence too
# --------------------------------------------------------------------------


def test_manifest_lost_then_team_collision_removes_all_copies_and_reports_correctly(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # R1 (round-1 review, finding 1): the collision rule must apply to every
    # recovery outcome, including "adopt" -- the supported path for a lost
    # manifest -- not just unchanged/update/install.
    assert install_sidecar(repo, SIDECAR_SOURCE) == 0
    manifest_path = _manifest_path(repo)
    manifest_path.rename(manifest_path.with_name(manifest_path.name + ".bak"))

    team_skill = repo / ".github" / "skills" / "ponytail" / "SKILL.md"
    team_skill.parent.mkdir(parents=True, exist_ok=True)
    team_skill.write_text("---\nname: ponytail\n---\nTEAM-OWNED\n", encoding="utf-8")
    _commit(repo, "team tracks ponytail in .github/skills", ".github/skills/ponytail")
    status_before = _status(repo)

    exit_code = install_sidecar(repo, SIDECAR_SOURCE)

    assert exit_code == 0
    assert not (repo / ".claude" / "skills" / "ponytail").exists()
    assert not (repo / ".agents" / "skills" / "ponytail").exists()
    manifest = _read_manifest(repo)
    assert ".claude/skills/ponytail" not in manifest["units"]
    assert ".agents/skills/ponytail" not in manifest["units"]
    exclude_text = _exclude_path(repo).read_text(encoding="utf-8")
    assert "/.claude/skills/ponytail\n" not in exclude_text
    assert "/.agents/skills/ponytail\n" not in exclude_text
    out = capsys.readouterr().out
    assert "SKIPPED .github/skills/ponytail" in out
    assert _status(repo) == status_before

    # Second run and dry run stay stable.
    status_before_2 = _status(repo)
    assert install_sidecar(repo, SIDECAR_SOURCE) == 0
    assert _status(repo) == status_before_2
    assert install_sidecar(repo, SIDECAR_SOURCE, dry_run=True) == 0
    assert _status(repo) == status_before_2


# --------------------------------------------------------------------------
# Phase G step 3: ownership proof by record or exclude line (S3)
# --------------------------------------------------------------------------


def test_crash_before_manifest_write_then_new_content_stays_hidden_as_unfinished(
    repo: Path, tmp_path: Path, monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # S3: a crash during a fresh install, then new content before the
    # rerun. The unit must stay hidden and reported as unfinished, not
    # become "foreign" and lose its line.
    v1 = tmp_path / "v1"
    v2 = tmp_path / "v2"
    _write_sidecar_source(v1, {"ponytail": "content v1\n"})
    _write_sidecar_source(v2, {"ponytail": "content v2 -- different\n"})

    monkeypatch.setattr(
        sidecar_overlay_module, "_fault_point", _raise_at("before_manifest_write")
    )
    with pytest.raises(RuntimeError, match="before_manifest_write"):
        install_sidecar_with_profile(repo, v1, monkeypatch)
    capsys.readouterr()
    monkeypatch.setattr(sidecar_overlay_module, "_fault_point", lambda name: None)

    # Pre-rerun state: the unit is fully installed with v1's bytes, listed
    # in the exclude block, but has no manifest record yet.
    skill_md = repo / ".claude" / "skills" / "ponytail" / "SKILL.md"
    assert skill_md.read_text(encoding="utf-8") == "content v1\n"
    assert not _manifest_path(repo).exists()

    exit_code = install_sidecar_with_profile(repo, v2, monkeypatch)

    assert exit_code == 0
    # Content differs from the new desired bytes and there is no record: it
    # must stay exactly as it is, hidden, and reported -- never silently
    # exposed and never silently replaced with v2's bytes either.
    assert skill_md.read_text(encoding="utf-8") == "content v1\n"
    status = _status(repo)
    assert ".claude/skills/ponytail" not in status
    out = capsys.readouterr().out
    assert "unfinished" in out


def test_crash_or_manifest_moved_aside_then_skill_stops_shipping_stays_hidden(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    # S3: the unit must still be classified (required_snapshot_units), even
    # though the manifest is gone and the skill is no longer desired, so its
    # line is never silently dropped.
    v1 = tmp_path / "v1"
    v2 = tmp_path / "v2"
    _write_sidecar_source(v1, {"ponytail": "content v1\n", "humanize": "humanize v1\n"})
    _write_sidecar_source(v2, {"humanize": "humanize v1\n"})  # ponytail no longer ships
    assert install_sidecar_with_profile(repo, v1, monkeypatch) == 0

    manifest_path = _manifest_path(repo)
    manifest_path.rename(manifest_path.with_name(manifest_path.name + ".bak"))

    exit_code = install_sidecar_with_profile(repo, v2, monkeypatch)

    assert exit_code == 0
    skill_md = repo / ".claude" / "skills" / "ponytail" / "SKILL.md"
    assert skill_md.read_text(encoding="utf-8") == "content v1\n"
    status = _status(repo)
    assert ".claude/skills/ponytail" not in status
    exclude_text = _exclude_path(repo).read_text(encoding="utf-8")
    assert "/.claude/skills/ponytail\n" in exclude_text


def test_stale_record_matching_new_content_after_crashed_update_is_adopted(
    repo: Path, tmp_path: Path, monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # S3: a crash during an update, then the block deleted: equal content
    # must be adopted, never reported as locally modified.
    v1 = tmp_path / "v1"
    v2 = tmp_path / "v2"
    _write_sidecar_source(v1, {"ponytail": "content v1\n"})
    _write_sidecar_source(v2, {"ponytail": "content v2\n"})
    assert install_sidecar_with_profile(repo, v1, monkeypatch) == 0

    # Simulate a completed swap whose manifest write never landed, by
    # writing v2's bytes directly and deleting the exclude block (both
    # crash symptoms in the same recovery run).
    skill_md = repo / ".claude" / "skills" / "ponytail" / "SKILL.md"
    skill_md.write_text("content v2\n", encoding="utf-8")
    agents_skill_md = repo / ".agents" / "skills" / "ponytail" / "SKILL.md"
    agents_skill_md.write_text("content v2\n", encoding="utf-8")
    _exclude_path(repo).write_text("", encoding="utf-8")

    exit_code = install_sidecar_with_profile(repo, v2, monkeypatch)

    assert exit_code == 0
    assert skill_md.read_text(encoding="utf-8") == "content v2\n"
    out = capsys.readouterr().out
    assert "has local edits" not in out
    assert "unfinished" not in out
    manifest = _read_manifest(repo)
    assert manifest["units"][".claude/skills/ponytail"]["files"]["SKILL.md"] == (
        sidecar_overlay_module.compute_file_hash(b"content v2\n")
    )


def test_invalid_manifest_recovery_run_does_not_unhide_other_files(
    repo: Path, tmp_path: Path, monkeypatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # S3: the invalid-manifest recovery run must not un-hide a unit whose
    # content does not match desired just because the manifest is gone.
    v1 = tmp_path / "v1"
    _write_sidecar_source(v1, {"ponytail": "content v1\n"})
    assert install_sidecar_with_profile(repo, v1, monkeypatch) == 0
    skill_md = repo / ".claude" / "skills" / "ponytail" / "SKILL.md"
    skill_md.write_text("content v1\nEDITED BY A PERSON\n", encoding="utf-8")
    edited_bytes = skill_md.read_bytes()

    manifest_path = _manifest_path(repo)
    manifest_path.write_text("{not valid json", encoding="utf-8")
    exit_code = install_sidecar_with_profile(repo, v1, monkeypatch)
    assert exit_code != 0
    capsys.readouterr()

    manifest_path.rename(manifest_path.with_name(manifest_path.name + ".bak"))
    status_before = _status(repo)

    exit_code = install_sidecar_with_profile(repo, v1, monkeypatch)

    assert exit_code == 0
    assert skill_md.read_bytes() == edited_bytes
    assert _status(repo) == status_before
    out = capsys.readouterr().out
    assert "unfinished" in out or "has local edits" in out


# --------------------------------------------------------------------------
# Phase G step 5: an empty leftover unit folder counts as absent (S9)
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# Phase G step 7: stable manifest namespace (Decision 32, L1, L4)
# --------------------------------------------------------------------------


def test_retired_bridge_manifest_entry_is_valid_and_goes_through_remove(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    v1 = tmp_path / "v1"
    _write_sidecar_source(v1, {"ponytail": "content v1\n"})
    assert install_sidecar_with_profile(repo, v1, monkeypatch) == 0

    retired_bridge = ".claude/rules/old-bridge.md"
    monkeypatch.setattr(
        sidecar_overlay_module,
        "_ALL_BRIDGES",
        sidecar_overlay_module._ALL_BRIDGES | {retired_bridge},
    )

    # Hand-craft a retired-bridge unit and file, as an earlier bootstrap
    # version would have left them (Decision 32 must accept this path on
    # manifest read instead of aborting the whole run on schema validation).
    bridge_path = repo / retired_bridge
    bridge_path.parent.mkdir(parents=True, exist_ok=True)
    bridge_path.write_text("an old bridge\n", encoding="utf-8")
    file_hash = sidecar_overlay_module.compute_file_hash(bridge_path.read_bytes())
    manifest = _read_manifest(repo)
    manifest["units"][retired_bridge] = {
        "files": {"old-bridge.md": file_hash},
        "hash": sidecar_overlay_module.compute_unit_hash({"old-bridge.md": file_hash}),
    }
    _manifest_path(repo).write_text(json.dumps(manifest), encoding="utf-8")
    exclude_path = _exclude_path(repo)
    exclude_text = exclude_path.read_text(encoding="utf-8")
    line = sidecar_overlay_module.unit_exclude_line(retired_bridge)
    exclude_path.write_text(
        exclude_text.replace(
            "# END ai-bootstrap sidecar", f"{line}\n# END ai-bootstrap sidecar"
        ),
        encoding="utf-8",
    )

    exit_code = install_sidecar_with_profile(repo, v1, monkeypatch)

    assert exit_code == 0
    assert not bridge_path.exists()
    manifest_after = _read_manifest(repo)
    assert retired_bridge not in manifest_after["units"]
    assert _status(repo) == ""


def test_manifest_unit_path_with_backslash_is_invalid(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    v1 = tmp_path / "v1"
    _write_sidecar_source(v1, {"ponytail": "content v1\n"})
    assert install_sidecar_with_profile(repo, v1, monkeypatch) == 0

    # The backslash sits inside an otherwise valid unit-path shape, so a
    # check that only rejects the wrong overall shape would miss it (L4).
    manifest = _read_manifest(repo)
    manifest["units"][".claude/skills/pony\\tail"] = manifest["units"][
        ".claude/skills/ponytail"
    ]
    _manifest_path(repo).write_text(json.dumps(manifest), encoding="utf-8")

    exit_code = install_sidecar_with_profile(repo, v1, monkeypatch)

    assert exit_code != 0


# --------------------------------------------------------------------------
# Phase H step 8: remove bootstrap_commit (Decision 33; R6)
# --------------------------------------------------------------------------


def test_new_manifest_has_no_bootstrap_commit_key(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    v1 = tmp_path / "v1"
    _write_sidecar_source(v1, {"ponytail": "content v1\n"})
    assert install_sidecar_with_profile(repo, v1, monkeypatch) == 0
    manifest = _read_manifest(repo)
    assert "bootstrap_commit" not in manifest


def test_old_manifest_with_bootstrap_commit_key_still_parses_then_stabilizes(
    repo: Path, tmp_path: Path, monkeypatch
) -> None:
    v1 = tmp_path / "v1"
    _write_sidecar_source(v1, {"ponytail": "content v1\n"})
    assert install_sidecar_with_profile(repo, v1, monkeypatch) == 0

    manifest_path = _manifest_path(repo)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["bootstrap_commit"] = "deadbeef"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    # First rerun after the legacy key appears: parses fine and rewrites the
    # manifest once, since the freshly serialized bytes drop the key.
    exit_code_1 = install_sidecar_with_profile(repo, v1, monkeypatch)
    assert exit_code_1 == 0
    rewritten = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "bootstrap_commit" not in rewritten
    stable_bytes = manifest_path.read_bytes()
    stable_mtime = manifest_path.stat().st_mtime_ns

    # Second run: no further change at all.
    exit_code_2 = install_sidecar_with_profile(repo, v1, monkeypatch)
    assert exit_code_2 == 0
    assert manifest_path.read_bytes() == stable_bytes
    assert manifest_path.stat().st_mtime_ns == stable_mtime
