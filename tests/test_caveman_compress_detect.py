"""Regression coverage for the caveman-compress protected-path detector."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

# Never write a __pycache__ into the canonical shared/skills/ source tree:
# a stray .pyc there would make it look like an authoring-source file that
# generate_targets.py never copied, tripping unrelated target-parity checks.
sys.dont_write_bytecode = True
sys.path.insert(
    0, str(REPO_ROOT / "shared" / "skills" / "caveman-compress" / "scripts")
)
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import detect  # noqa: E402
from runtime_ownership import CONSUMER_STATE_PATHS  # noqa: E402


def _write_skill(root: Path, relative_dir: str) -> Path:
    """Write a minimal SKILL.md at `<root>/<relative_dir>/SKILL.md`."""
    skill_dir = root / relative_dir
    skill_dir.mkdir(parents=True, exist_ok=True)
    path = skill_dir / "SKILL.md"
    path.write_text("---\nname: example-skill\n---\n\nBody.\n", encoding="utf-8")
    return path


def test_canonical_shared_skill_source_is_protected(tmp_path: Path) -> None:
    """A canonical `shared/skills/**/SKILL.md` authoring source must be
    refused, matching the protection already given to its generated
    `.claude/skills/**/SKILL.md` copy (evidence row 9)."""
    target = _write_skill(tmp_path, "shared/skills/example-skill")

    result = detect.inspect_path(target)

    assert result.compressible is False
    assert (
        result.reason == "Skill files must keep exact frontmatter and trigger phrases."
    )


def test_generated_claude_skill_copy_stays_protected(tmp_path: Path) -> None:
    """Regression guard: the pre-existing `.claude/skills` protection is
    unchanged by adding the canonical `shared/skills` protection."""
    target = _write_skill(tmp_path, ".claude/skills/example-skill")

    assert detect.should_compress(target) is False


def test_non_skill_markdown_under_shared_skills_stays_compressible(
    tmp_path: Path,
) -> None:
    """Only `SKILL.md` and `references/` content are protected; other sibling
    prose docs such as a skill's README remain compressible, matching the
    existing `.claude/skills` suffix-scoped pattern."""
    skill_dir = tmp_path / "shared" / "skills" / "example-skill"
    skill_dir.mkdir(parents=True)
    readme = skill_dir / "README.md"
    readme.write_text("Some notes about this skill.\n", encoding="utf-8")

    assert detect.should_compress(readme) is True


@pytest.mark.parametrize("root", ["shared/skills", ".claude/skills"])
def test_skill_reference_files_are_protected(tmp_path: Path, root: str) -> None:
    """Progressive disclosure moved normative skill content out of skill roots
    and into `references/` files, so those carry the same verbatim content the
    root used to and must not be compressed."""
    references_dir = tmp_path / root / "example-skill" / "references"
    references_dir.mkdir(parents=True)
    reference = references_dir / "xml-recipes.md"
    reference.write_text(
        "Exact XML recipes that must stay verbatim.\n", encoding="utf-8"
    )

    assert detect.should_compress(reference) is False


def _make_note(root: Path, relative: str) -> Path:
    """Write a one-line prose note at `<root>/<relative>` and return it."""
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("Some notes about the project.\n", encoding="utf-8")
    return path


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        (
            ".claude/MEMORY.md",
            ".claude/explorations/caveman-compress-backups/MEMORY.original.md",
        ),
        (
            ".claude/instructions/project-context.instructions.md",
            ".claude/explorations/caveman-compress-backups/instructions/"
            "project-context.instructions.original.md",
        ),
    ],
    ids=["top-level-file", "nested-file-keeps-relative-folders"],
)
def test_backup_moves_where_a_bootstrap_refresh_keeps_it(
    tmp_path: Path, target: str, expected: str
) -> None:
    """A refresh deletes unknown files under `.claude` outside the consumer
    state folders, so a backup of such a target goes into a preserved one."""
    (tmp_path / ".claude" / "explorations").mkdir(parents=True)
    note = _make_note(tmp_path, target)

    assert detect.backup_path(note) == tmp_path / expected


@pytest.mark.parametrize(
    "target",
    [
        ".claude/plans/2026-10-20_plan.md",
        ".claude/plans/nested/deeper.md",
        ".claude/explorations/finding.md",
        ".claude/session_logs/2026-10-20_log.md",
        ".claude/quality_reports/report.md",
        "docs/notes.md",
        ".ai-bootstrap/MEMORY.md",
    ],
    ids=[
        "plans",
        "plans-nested",
        "explorations",
        "session-logs",
        "quality-reports",
        "outside-claude",
        "sidecar-state-root",
    ],
)
def test_backup_stays_beside_targets_that_are_already_safe(
    tmp_path: Path, target: str
) -> None:
    """Targets in a preserved folder, outside `.claude`, or in a sidecar state
    root are never deleted by a refresh, so the sibling backup stays."""
    (tmp_path / ".claude" / "explorations").mkdir(parents=True)
    note = _make_note(tmp_path, target)

    assert detect.backup_path(note) == note.with_name(f"{note.stem}.original.md")


def test_backup_stays_beside_target_when_claude_has_no_explorations_folder(
    tmp_path: Path,
) -> None:
    """A team-owned `.claude` beside a sidecar install (or the user-level one)
    has no preserved explorations folder to hold a backup."""
    note = _make_note(tmp_path, ".claude/MEMORY.md")

    assert detect.backup_path(note) == tmp_path / ".claude" / "MEMORY.original.md"


def test_backup_uses_the_nearest_claude_folder(tmp_path: Path) -> None:
    """An inner `.claude` without explorations wins over an outer one that has
    them, because the nearest ancestor is the one a refresh would clean."""
    (tmp_path / ".claude" / "explorations").mkdir(parents=True)
    note = _make_note(tmp_path, "project/.claude/notes.md")

    assert detect.backup_path(note) == tmp_path / "project/.claude/notes.original.md"


def test_cli_prints_the_backup_path_for_a_compressible_target(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".claude" / "explorations").mkdir(parents=True)
    note = _make_note(tmp_path, ".claude/MEMORY.md")
    expected = (
        tmp_path / ".claude/explorations/caveman-compress-backups/MEMORY.original.md"
    )

    assert detect.main(["detect.py", str(note)]) == 0

    assert f"Backup: {expected}" in capsys.readouterr().out


def test_json_output_carries_the_backup_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / ".claude" / "explorations").mkdir(parents=True)
    note = _make_note(tmp_path, ".claude/MEMORY.md")
    expected = (
        tmp_path / ".claude/explorations/caveman-compress-backups/MEMORY.original.md"
    )

    assert detect.main(["detect.py", str(note), "--json"]) == 0

    assert json.loads(capsys.readouterr().out)["backup_path"] == str(expected)


def test_backup_file_target_is_still_refused_with_no_backup_path(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The new backup folder holds `*.original.md` files; compressing one of
    them would destroy the safety copy, so it stays hard-blocked."""
    (tmp_path / ".claude" / "explorations").mkdir(parents=True)
    backup = _make_note(
        tmp_path, ".claude/explorations/caveman-compress-backups/MEMORY.original.md"
    )

    result = detect.inspect_path(backup)

    assert result.compressible is False
    assert result.reason == "Backup files are never compressed."
    assert result.backup_path == ""
    assert detect.main(["detect.py", str(backup)]) == 2
    assert "Backup:" not in capsys.readouterr().out


def test_preserved_folders_match_the_consumer_state_folders() -> None:
    """The detector may only move a backup into a folder the installer keeps.
    A future ownership change must fail here before a backup is lost."""
    state_folders = {path for path in CONSUMER_STATE_PATHS if "." not in path}

    assert set(detect.PRESERVED_STATE_DIRS) == state_folders
