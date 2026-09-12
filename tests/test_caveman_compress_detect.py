"""Regression coverage for the caveman-compress protected-path detector."""

from __future__ import annotations

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

import detect  # noqa: E402


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
