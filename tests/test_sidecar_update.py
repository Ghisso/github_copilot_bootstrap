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

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from runtime_ownership import SIDECAR_MANIFEST_NAME  # noqa: E402
from sidecar_overlay import git_path, install_sidecar  # noqa: E402
from sidecar_test_helpers import (  # noqa: E402
    _commit,
    _commit_staged,
    _exclude_path,
    _git,
    _init_repo,
    _manifest_path,
    _read_manifest,
    _status,
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


def _write_sidecar_source(
    root: Path,
    skills: dict[str, str],
    bridges: dict[str, str] | None = None,
) -> None:
    """Build a minimal, valid sidecar tree: each of ``skills`` at both write
    roots (``.claude/skills``, ``.agents/skills``), plus any ``bridges`` at
    their fixed path. Only ``SIDECAR_SKILLS`` names and ``SIDECAR_BRIDGES``
    paths are valid sidecar-unit shapes; anything else would make
    ``install_sidecar`` reject the whole source as not a sidecar tree
    (``_sidecar_source_violations``), which is exactly how a test would fail
    if it typoed a skill name.
    """
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    for skill, content in skills.items():
        for write_root in (".claude/skills", ".agents/skills"):
            skill_file = root / write_root / skill / "SKILL.md"
            skill_file.parent.mkdir(parents=True, exist_ok=True)
            skill_file.write_text(content, encoding="utf-8")
    for bridge_path, content in (bridges or {}).items():
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
    repo: Path, tmp_path: Path
) -> None:
    v1 = tmp_path / "v1"
    v2 = tmp_path / "v2"
    _write_sidecar_source(v1, {"ponytail": "ponytail v1\n"})
    _write_sidecar_source(v2, {"ponytail": "ponytail v2\n"})

    assert install_sidecar(repo, v1) == 0
    assert install_sidecar(repo, v2) == 0

    for write_root in (".claude/skills", ".agents/skills"):
        content = (repo / write_root / "ponytail" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        assert content == "ponytail v2\n"


def test_skill_added_in_new_version_is_installed(repo: Path, tmp_path: Path) -> None:
    v1 = tmp_path / "v1"
    v2 = tmp_path / "v2"
    _write_sidecar_source(v1, {"ponytail": "content\n"})
    _write_sidecar_source(v2, {"ponytail": "content\n", "humanize": "humanize v1\n"})

    assert install_sidecar(repo, v1) == 0
    assert not (repo / ".claude" / "skills" / "humanize").exists()

    assert install_sidecar(repo, v2) == 0
    for write_root in (".claude/skills", ".agents/skills"):
        assert (repo / write_root / "humanize" / "SKILL.md").read_text(
            encoding="utf-8"
        ) == "humanize v1\n"


def test_skill_removed_deletes_unmodified_copy_but_keeps_modified_one(
    repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    v1 = tmp_path / "v1"
    v2 = tmp_path / "v2"
    _write_sidecar_source(v1, {"debug-investigator": "debug v1\n"})
    _write_sidecar_source(v2, {})  # the skill is gone in the new version

    assert install_sidecar(repo, v1) == 0
    modified = repo / ".claude" / "skills" / "debug-investigator" / "SKILL.md"
    modified.write_text("debug v1\nEDITED BY A PERSON\n", encoding="utf-8")
    edited_bytes = modified.read_bytes()

    exit_code = install_sidecar(repo, v2)

    assert exit_code == 0
    # Unmodified at .agents/skills: the desired content is gone and the unit
    # still matches its record, so it is removed.
    assert not (repo / ".agents" / "skills" / "debug-investigator").exists()
    # Modified at .claude/skills: kept, and reported, regardless of the
    # skill's removal upstream.
    assert modified.read_bytes() == edited_bytes
    out = capsys.readouterr().out
    assert "delete or restore" in out


def test_bridge_text_change_updates_bridge_files(repo: Path, tmp_path: Path) -> None:
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

    assert install_sidecar(repo, v1) == 0
    assert install_sidecar(repo, v2) == 0

    assert (repo / claude_bridge).read_text(encoding="utf-8") == "bridge v2\n"
    assert (repo / copilot_bridge).read_text(encoding="utf-8") == (
        '---\napplyTo: "**"\n---\nbridge v2\n'
    )


def test_user_modified_projection_is_kept_and_reported_every_run(
    repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    v1 = tmp_path / "v1"
    _write_sidecar_source(v1, {"ponytail": "content v1\n"})
    assert install_sidecar(repo, v1) == 0
    capsys.readouterr()

    skill_md = repo / ".claude" / "skills" / "ponytail" / "SKILL.md"
    skill_md.write_text("content v1\nEDITED\n", encoding="utf-8")
    edited_bytes = skill_md.read_bytes()

    exit_code_1 = install_sidecar(repo, v1)
    out_1 = capsys.readouterr().out
    exit_code_2 = install_sidecar(repo, v1)
    out_2 = capsys.readouterr().out

    assert exit_code_1 == 0
    assert exit_code_2 == 0
    assert skill_md.read_bytes() == edited_bytes
    assert "delete or restore" in out_1
    assert "delete or restore" in out_2


def test_projection_replaced_by_tracked_team_file_drops_record_and_line(
    repo: Path, tmp_path: Path
) -> None:
    v1 = tmp_path / "v1"
    _write_sidecar_source(v1, {"ponytail": "content v1\n"})
    assert install_sidecar(repo, v1) == 0

    skill_md = repo / ".claude" / "skills" / "ponytail" / "SKILL.md"
    force_add = _git(repo, "add", "-f", "--", ".claude/skills/ponytail/SKILL.md")
    assert force_add.returncode == 0, force_add.stderr
    _commit_staged(repo, "team takes ponytail SKILL.md")
    tracked_bytes = skill_md.read_bytes()

    exit_code = install_sidecar(repo, v1)

    assert exit_code == 0
    assert skill_md.read_bytes() == tracked_bytes  # file untouched
    manifest = _read_manifest(repo)
    assert ".claude/skills/ponytail" not in manifest["units"]
    exclude_text = _exclude_path(repo).read_text(encoding="utf-8")
    assert "/.claude/skills/ponytail\n" not in exclude_text


def test_unrelated_tracked_team_config_added_after_install_is_untouched(
    repo: Path, tmp_path: Path
) -> None:
    v1 = tmp_path / "v1"
    _write_sidecar_source(v1, {"ponytail": "content v1\n"})
    assert install_sidecar(repo, v1) == 0

    team_file = repo / "CLAUDE.md"
    team_file.write_text("# team\nTEAM-MARKER\n", encoding="utf-8")
    _commit(repo, "team adds CLAUDE.md", "CLAUDE.md")
    before = team_file.read_bytes()

    exit_code = install_sidecar(repo, v1)

    assert exit_code == 0
    assert team_file.read_bytes() == before


def test_exclude_block_deleted_by_user_is_restored(repo: Path, tmp_path: Path) -> None:
    v1 = tmp_path / "v1"
    _write_sidecar_source(v1, {"ponytail": "content v1\n"})
    assert install_sidecar(repo, v1) == 0

    exclude_path = _exclude_path(repo)
    exclude_path.write_text("", encoding="utf-8")

    exit_code = install_sidecar(repo, v1)

    assert exit_code == 0
    exclude_text = exclude_path.read_text(encoding="utf-8")
    assert "/.claude/skills/ponytail\n" in exclude_text
    ignored = _git(repo, "check-ignore", "-q", "--", ".claude/skills/ponytail/SKILL.md")
    assert ignored.returncode == 0


def test_owned_projection_deleted_by_user_is_reinstalled(
    repo: Path, tmp_path: Path
) -> None:
    v1 = tmp_path / "v1"
    _write_sidecar_source(v1, {"ponytail": "content v1\n"})
    assert install_sidecar(repo, v1) == 0

    shutil.rmtree(repo / ".claude" / "skills" / "ponytail")

    exit_code = install_sidecar(repo, v1)

    assert exit_code == 0
    assert (repo / ".claude" / "skills" / "ponytail" / "SKILL.md").read_text(
        encoding="utf-8"
    ) == "content v1\n"


def test_manifest_corrupted_aborts_then_remedy_rerun_adopts_matching_units(
    repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    v1 = tmp_path / "v1"
    _write_sidecar_source(v1, {"ponytail": "content v1\n", "humanize": "humanize v1\n"})
    assert install_sidecar(repo, v1) == 0
    manifest_path = _manifest_path(repo)
    manifest_path.write_text("{not valid json", encoding="utf-8")

    exit_code = install_sidecar(repo, v1)
    err = capsys.readouterr().err

    assert exit_code != 0
    assert "move the manifest aside" in err
    assert "adopted" in err

    manifest_path.rename(manifest_path.with_name(manifest_path.name + ".bak"))
    exit_code = install_sidecar(repo, v1)

    assert exit_code == 0
    manifest = _read_manifest(repo)
    assert set(manifest["units"]) == {
        ".claude/skills/ponytail",
        ".agents/skills/ponytail",
        ".claude/skills/humanize",
        ".agents/skills/humanize",
    }


def test_install_then_two_updates_the_second_update_changes_no_file(
    repo: Path, tmp_path: Path
) -> None:
    v1 = tmp_path / "v1"
    v2 = tmp_path / "v2"
    _write_sidecar_source(v1, {"ponytail": "content v1\n"})
    _write_sidecar_source(v2, {"ponytail": "content v2\n"})

    assert install_sidecar(repo, v1) == 0
    assert install_sidecar(repo, v2) == 0  # first update: a real content change

    before = _sidecar_tree_state(repo)
    before_exclude = _file_state(_exclude_path(repo))
    before_manifest = _file_state(_manifest_path(repo))

    exit_code = install_sidecar(repo, v2)  # second update: no upstream change

    assert exit_code == 0
    assert _sidecar_tree_state(repo) == before
    assert _file_state(_exclude_path(repo)) == before_exclude
    assert _file_state(_manifest_path(repo)) == before_manifest


def test_dry_run_update_makes_no_changes(repo: Path, tmp_path: Path) -> None:
    v1 = tmp_path / "v1"
    _write_sidecar_source(v1, {"ponytail": "content v1\n", "humanize": "humanize v1\n"})
    assert install_sidecar(repo, v1) == 0
    before = _sidecar_tree_state(repo)
    before_exclude = _file_state(_exclude_path(repo))
    before_manifest = _file_state(_manifest_path(repo))
    status_before = _status(repo)

    exit_code = install_sidecar(repo, v1, dry_run=True)

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
