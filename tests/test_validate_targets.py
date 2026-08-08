"""Integration coverage for the generated-target control-plane validator."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from generate_targets import (  # noqa: E402
    parse_policy,
    render_claude_rule_adapter,
    render_github_instruction_adapter,
    render_root_guidance,
    shared_policies,
)
from validate_targets import (  # noqa: E402
    POLICY_SCOPE_FIXTURES,
    claude_rule_paths,
    copilot_instruction_paths,
    root_guidance_errors,
    scope_matches,
)


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


def test_policy_adapters_share_one_validated_target_neutral_scope() -> None:
    """Claude and Copilot derive equivalent conditional scopes from policies."""
    policies = shared_policies()

    assert {policy.source.name for policy in policies if policy.paths} == set(
        POLICY_SCOPE_FIXTURES
    )
    for policy in policies:
        github = render_github_instruction_adapter(policy)
        assert "applicability:" not in github
        if not policy.paths:
            assert copilot_instruction_paths(github) == ()
            continue

        claude = render_claude_rule_adapter(policy)
        assert copilot_instruction_paths(github) == policy.paths
        assert claude_rule_paths(claude) == policy.paths
        assert "applicability:" not in claude
        for path, expected_match in POLICY_SCOPE_FIXTURES[policy.source.name]:
            assert scope_matches(path, policy.paths) is expected_match
            assert (
                scope_matches(path, copilot_instruction_paths(github)) is expected_match
            )
            assert scope_matches(path, claude_rule_paths(claude)) is expected_match


def test_policy_schema_rejects_copilot_native_or_ambiguous_scope(
    tmp_path: Path,
) -> None:
    """Canonical applicability accepts only explicit always-on or path lists."""
    policy = tmp_path / "legacy.instructions.md"
    policy.write_text('---\napplyTo: "src/**/*.py"\n---\n\n# Legacy\n')

    with pytest.raises(ValueError, match="unsupported policy frontmatter field"):
        parse_policy(policy)

    policy.write_text('---\napplicability: "src/**/*.py"\n---\n\n# Ambiguous\n')

    with pytest.raises(ValueError, match="must be 'always' or a YAML list"):
        parse_policy(policy)


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
