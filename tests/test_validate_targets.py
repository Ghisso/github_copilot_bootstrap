"""Integration coverage for the generated-target control-plane validator."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from generate_targets import render_root_guidance  # noqa: E402
from validate_targets import root_guidance_errors  # noqa: E402


def test_root_guidance_budgets_and_structural_invariants() -> None:
    """Concise root templates retain their unique sections and lifecycle."""
    claude = render_root_guidance("claude-code")
    codex = render_root_guidance("openai-codex")

    assert root_guidance_errors("CLAUDE.md", claude) == []
    assert root_guidance_errors("AGENTS.md", codex) == []
    assert len(claude.splitlines()) <= 200
    assert len(codex.encode()) <= 16 * 1024


def test_root_guidance_rejects_duplicate_sections_and_stale_lifecycle_order() -> None:
    """Structural validation rejects regressions hidden by broad substring checks."""
    guidance = render_root_guidance("claude-code")
    mutated = guidance.replace("## Map\n", "## Map\n\n## Map\n", 1).replace(
        "PRE-FLIGHT -> BRANCH -> PLAN -> PONYTAIL -> IMPLEMENT -> VERIFY -> REVIEW -> "
        "DOCUMENT -> SCORE -> LEARN -> SESSION LOG -> COMMIT",
        "PRE-FLIGHT -> PLAN -> BRANCH -> PONYTAIL -> IMPLEMENT -> VERIFY -> REVIEW -> "
        "DOCUMENT -> SCORE -> LEARN -> SESSION LOG -> COMMIT",
        1,
    )

    errors = root_guidance_errors("CLAUDE.md", mutated)

    assert any("exactly one '## Map' section" in error for error in errors)
    assert any("canonical lifecycle" in error for error in errors)


def test_validate_targets() -> None:
    """The real generated-target validator accepts the current repository."""
    result = subprocess.run(
        [sys.executable, "scripts/validate_targets.py"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS generated target is structurally valid" in result.stdout
