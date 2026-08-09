"""Integration coverage for the generated-target control-plane validator."""

from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from typing import Any
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from generate_targets import (  # noqa: E402
    CODEX_AGENT_INSTRUCTIONS_DELIMITER,
    parse_policy,
    render_claude_rule_adapter,
    codex_agent_metadata_header,
    render_codex_agent_adapter,
    render_github_instruction_adapter,
    render_root_guidance,
    shared_agents,
    shared_policies,
    transform_target_paths,
    transform_agent_text,
)
from validate_targets import (  # noqa: E402
    CODEX_CODER_ESCALATION,
    CODEX_ROLE_MODEL_INTENTS,
    POLICY_SCOPE_FIXTURES,
    codex_agent_instruction_errors,
    claude_rule_paths,
    codex_config_contract_errors,
    copilot_instruction_paths,
    github_agent_model_errors,
    memory_security_authority_errors,
    pretool_routing_errors,
    root_guidance_errors,
    planner_supervision_contract_errors,
    scope_matches,
    task_lane_contract_errors,
    task_lane_for,
    TaskLaneInputs,
    workspace_guidance_errors,
)


def test_pretool_routing_rejects_wildcard_safety_and_lifecycle_drift() -> None:
    """Safety handlers are scoped while the wildcard remains observer-only."""
    hooks: dict[str, Any] = {
        "PreToolUse": [
            {"matcher": "Edit|Write", "hooks": [{"command": "protect-files.sh"}]},
            {"matcher": "Bash", "hooks": [{"command": "pretool-bash-guard.sh"}]},
            {"matcher": "*", "hooks": [{"command": "context-mode-dispatch.sh"}]},
        ]
    }
    assert pretool_routing_errors(hooks, "openai-codex") == []

    hooks["PreToolUse"][2]["hooks"].append({"command": "git-protection.sh"})
    errors = pretool_routing_errors(hooks, "openai-codex")
    assert any("wildcard" in error for error in errors)
    assert any("must contain only" in error for error in errors)


def test_codex_routing_contract_rejects_aliases_and_root_pins() -> None:
    """The generated config uses documented concurrency without root model pins."""
    agents = {"max_concurrent_threads_per_session": 6, "max_depth": 1}
    config: dict[str, object] = {
        "agents": agents,
        "features": {
            "multi_agent_v2": {
                "hide_spawn_agent_metadata": False,
                "tool_namespace": "agents",
            }
        },
    }

    assert codex_config_contract_errors(config, "fixture") == []
    assert CODEX_ROLE_MODEL_INTENTS == {
        "orchestrator": ("gpt-5.6-sol", "xhigh"),
        "planner": ("gpt-5.6-sol", "xhigh"),
        "coder": ("gpt-5.6-terra", "high"),
        "reviewer": ("gpt-5.6-sol", "high"),
        "documenter": ("gpt-5.6-luna", "medium"),
        "verifier": ("gpt-5.6-luna", "low"),
    }
    assert CODEX_CODER_ESCALATION == ("gpt-5.6-sol", "xhigh")

    for key, value, expected_error in (
        ("max_threads", 6, "legacy agents.max_threads"),
        ("enabled", True, "agents.enabled"),
    ):
        invalid = {**config, "agents": {**agents, key: value}}
        assert any(
            expected_error in error
            for error in codex_config_contract_errors(invalid, "fixture")
        )
    for key in ("model", "model_reasoning_effort"):
        invalid = {**config, key: "gpt-5.6-sol"}
        assert any(
            key in error for error in codex_config_contract_errors(invalid, "fixture")
        )


def test_planner_supervision_contract_requires_bounded_evidence_and_waits() -> None:
    """Planner prompts retain the calibrated discovery and supervision contract."""
    planner = (REPO_ROOT / "shared" / "agents" / "planner" / "prompt.md").read_text(
        encoding="utf-8"
    )
    orchestrator = (
        REPO_ROOT / "shared" / "agents" / "orchestrator" / "prompt.md"
    ).read_text(encoding="utf-8")

    assert planner_supervision_contract_errors(planner, orchestrator) == []

    missing_packet = planner.replace("orchestrator's evidence packet", "handoff", 1)
    errors = planner_supervision_contract_errors(missing_packet, orchestrator)
    assert any("bounded-discovery" in error for error in errors)

    missing_wait = orchestrator.replace(
        "A pending wait means no mailbox event arrived during that polling window",
        "A completed wait means success",
        1,
    )
    errors = planner_supervision_contract_errors(planner, missing_wait)
    assert any("planner-supervision" in error for error in errors)

    stale_mandates = (
        f"{planner}\nUses a PRD-style interview to surface unknowns before drafting.\n"
        "Show the user the sketch and ask for confirmation before proceeding.\n"
        "Iterate at least once based on user responses.\n"
    )
    errors = planner_supervision_contract_errors(stale_mandates, orchestrator)
    assert any("stale unconditional mandate" in error for error in errors)


def test_github_agent_model_contract_uses_frontmatter_not_body_substrings() -> None:
    """GitHub model parity uses parsed frontmatter and rejects malformed inputs."""
    path = Path(".github/agents/planner.agent.md")
    valid = "---\nname: planner\nmodel: Claude Opus 4.6\n---\n\nmodel: wrong\n"

    assert github_agent_model_errors(valid, "Claude Opus 4.6", path) == []
    assert any(
        "drifted" in error
        for error in github_agent_model_errors(
            valid.replace("Claude Opus 4.6", "GPT-5.4", 1),
            "Claude Opus 4.6",
            path,
        )
    )
    assert any(
        "missing frontmatter" in error
        for error in github_agent_model_errors(
            "model: Claude Opus 4.6\n", "Claude Opus 4.6", path
        )
    )


def test_planner_model_intent_preserves_native_models_and_copilot_choice() -> None:
    """Only planner effort changes; native models and Copilot intent stay fixed."""
    planner = json.loads(
        (REPO_ROOT / "shared" / "agents" / "planner" / "agent.yaml").read_text(
            encoding="utf-8"
        )
    )
    intent = planner["model_intent"]

    assert intent["github-copilot"] == "Claude Opus 4.6"
    assert intent["claude-code"] == {"model": "opus", "effort": "xhigh"}
    assert intent["openai-codex"] == {
        "model": "gpt-5.6-sol",
        "effort": "xhigh",
    }


def test_root_guidance_budgets_and_structural_invariants() -> None:
    """Concise root templates retain their unique sections and lifecycle."""
    claude = render_root_guidance("claude-code")
    codex = render_root_guidance("openai-codex")

    assert root_guidance_errors("CLAUDE.md", claude) == []
    assert root_guidance_errors("AGENTS.md", codex) == []
    assert "`.claude/hooks/`" in claude
    assert "`.github/hooks/`" in claude
    assert "`.codex/`" in codex
    assert "`.github/hooks/`" in codex
    assert len(claude.splitlines()) <= 200
    assert len(codex.encode()) <= 16 * 1024


@pytest.mark.parametrize(
    "target,name",
    (("claude-code", "CLAUDE.md"), ("openai-codex", "AGENTS.md")),
)
@pytest.mark.parametrize(
    "authoring_phrase",
    (
        "Bootstrap Guidance",
        "reusable multi-agent bootstrap",
        "In an installed project",
        "Bootstrap maintainers own authoring and regeneration",
    ),
)
def test_root_guidance_rejects_authoring_specific_phrases(
    target: str, name: str, authoring_phrase: str
) -> None:
    """Generated root guidance stays neutral to the bootstrap authoring repo."""
    guidance = render_root_guidance(target)

    assert authoring_phrase not in guidance
    errors = root_guidance_errors(name, f"{guidance}\n{authoring_phrase}\n")

    assert any(authoring_phrase in error for error in errors)


def test_root_guidance_allows_bootstrap_when_it_is_not_an_authoring_phrase() -> None:
    """The regression guard rejects exact phrases, not the general word."""
    guidance = render_root_guidance("claude-code")

    assert root_guidance_errors("CLAUDE.md", f"{guidance}\nbootstrap\n") == []


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

    missing_inventory = guidance.replace("`.github/hooks/`, ", "", 1)
    assert any(
        "`.github/hooks/`" in error
        for error in root_guidance_errors("CLAUDE.md", missing_inventory)
    )

    codex_missing_inventory = render_root_guidance("openai-codex").replace(
        "`.github/hooks/`, ", "", 1
    )
    assert any(
        "`.github/hooks/`" in error
        for error in root_guidance_errors("AGENTS.md", codex_missing_inventory)
    )


def test_workspace_guidance_preserves_shared_git_hook_inventory() -> None:
    """Target path rewrites retain the shared Git-hook control-plane surface."""
    workspace = (
        REPO_ROOT / "shared" / "policies" / "workspace.instructions.md"
    ).read_text(encoding="utf-8")
    for target in ("claude-code", "openai-codex"):
        rendered = transform_target_paths(
            workspace, target, preserve_shared_git_hooks=True
        )
        assert workspace_guidance_errors(rendered) == []

    missing_inventory = workspace.replace("`.github/hooks/`, ", "", 1)
    assert any(
        "`.github/hooks/`" in error
        for error in workspace_guidance_errors(missing_inventory)
    )


@pytest.mark.parametrize(
    ("case", "inputs", "expected"),
    (
        (
            "reporting request",
            {"change_requested": False},
            "read-only/reporting",
        ),
        (
            "explicit docs typo",
            {
                "change_requested": True,
                "explicit": True,
                "affected_paths": ("README.md",),
                "low_risk": True,
            },
            "lightweight edit",
        ),
        (
            "single-file behavior edit",
            {
                "change_requested": True,
                "explicit": True,
                "affected_paths": ("src/formatter.py",),
                "low_risk": True,
            },
            "lightweight edit",
        ),
        (
            "dependency change",
            {
                "change_requested": True,
                "explicit": True,
                "affected_paths": ("pyproject.toml",),
                "dependency_or_lockfile_impact": True,
            },
            "control-plane/high-risk",
        ),
        (
            "hook change",
            {
                "change_requested": True,
                "explicit": True,
                "affected_paths": (".claude/hooks/scripts/guard.sh",),
            },
            "control-plane/high-risk",
        ),
        (
            "runtime config change",
            {
                "change_requested": True,
                "explicit": True,
                "affected_paths": (".codex/config.toml",),
            },
            "control-plane/high-risk",
        ),
        (
            "commit request",
            {
                "change_requested": True,
                "explicit": True,
                "affected_paths": ("docs/guide.md",),
                "low_risk": True,
                "commit_or_pr_requested": True,
            },
            "standard implementation",
        ),
        (
            "multi-file implementation",
            {
                "change_requested": True,
                "explicit": True,
                "affected_paths": ("src/a.py", "tests/test_a.py"),
            },
            "control-plane/high-risk",
        ),
    ),
    ids=lambda case: case,
)
def test_task_lane_fixtures(case: str, inputs: TaskLaneInputs, expected: str) -> None:
    """The decision-table fixtures cover positive and safety-boundary cases."""
    assert task_lane_for(**inputs) == expected


def test_task_lane_contract_rejects_missing_requirement_and_stale_drift() -> None:
    """Structural validation catches omissions and prior blanket-path wording."""
    workflow = (
        REPO_ROOT / "shared" / "policies" / "workflow.instructions.md"
    ).read_text(encoding="utf-8")
    assert task_lane_contract_errors(workflow) == []

    missing = workflow.replace("No lifecycle artifacts.", "No records.", 1)
    assert any(
        "No lifecycle artifacts." in error
        for error in task_lane_contract_errors(missing)
    )

    drift = workflow.replace(
        "Do not use time or line-count thresholds to classify a lane.",
        "Do not use time or line-count thresholds to classify a lane.\n"
        "Skip planning only for: one-file work.",
        1,
    )
    assert any(
        "Skip planning only for:" in error for error in task_lane_contract_errors(drift)
    )


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


def test_memory_security_authority_contract_requires_headings_and_links() -> None:
    """The threat model stays discoverable without pinning native-memory settings."""
    security = (REPO_ROOT / "SECURITY.md").read_text(encoding="utf-8")
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    architecture = (REPO_ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    target_mapping = (REPO_ROOT / "docs" / "target-mapping.md").read_text(
        encoding="utf-8"
    )

    assert (
        memory_security_authority_errors(security, readme, architecture, target_mapping)
        == []
    )

    missing_heading = security.replace("## Credential Handling", "## Credentials", 1)
    assert any(
        "Credential Handling" in error
        for error in memory_security_authority_errors(
            missing_heading, readme, architecture, target_mapping
        )
    )

    missing_link = readme.replace("[SECURITY.md](SECURITY.md)", "SECURITY.md", 1)
    assert any(
        "README.md" in error and "SECURITY.md" in error
        for error in memory_security_authority_errors(
            security, missing_link, architecture, target_mapping
        )
    )


def test_codex_agents_embed_transformed_shared_prompts_and_reject_legacy_reads() -> (
    None
):
    """Codex agents are self-contained while inheriting project MCP configuration."""
    for agent, agent_dir in shared_agents():
        rendered = render_codex_agent_adapter(agent)
        instructions = tomllib.loads(rendered)["developer_instructions"]
        expected_body = transform_agent_text(
            (agent_dir / "prompt.md").read_text(encoding="utf-8"), "openai-codex"
        ).strip()

        assert instructions.count(CODEX_AGENT_INSTRUCTIONS_DELIMITER) == 1
        assert (
            instructions.split(CODEX_AGENT_INSTRUCTIONS_DELIMITER, 1)[1].strip()
            == expected_body
        )
        assert "Before doing the task, read `.claude/agents/" not in instructions
        assert "[mcp_servers." not in rendered
        assert codex_agent_instruction_errors(agent, instructions) == []

        legacy = (
            "This is an OpenAI Codex custom-agent adapter over the shared `.claude` basis.\n\n"
            f"Before doing the task, read `.claude/agents/{agent['id']}.md`.\n"
        )
        assert any(
            "legacy Claude-native runtime read" in error
            for error in codex_agent_instruction_errors(agent, legacy)
        )

        mutated_body = instructions.replace(
            expected_body, f"{expected_body}\nchanged", 1
        )
        assert any(
            "exactly match" in error
            for error in codex_agent_instruction_errors(agent, mutated_body)
        )

        assert instructions.startswith(codex_agent_metadata_header(agent))
