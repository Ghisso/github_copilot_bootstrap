"""Integration coverage for the generated-target control-plane validator."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tomllib
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import generate_targets as target_generator  # noqa: E402

from generate_targets import (  # noqa: E402
    CODEX_AGENT_INSTRUCTIONS_DELIMITER,
    load_shared_agents,
    parse_policy,
    render_claude_rule_adapter,
    render_github_agent_adapter,
    codex_agent_metadata_header,
    render_codex_agent_adapter,
    render_github_instruction_adapter,
    render_root_guidance,
    shared_agents,
    shared_policies,
    transform_agent_text,
    transform_target_paths,
)
from validate_targets import (  # noqa: E402
    CODEX_CODER_ESCALATION,
    CODEX_ESCALATION_CHAIN,
    CODEX_AGENT_MODEL_INTENTS,
    CODEX_ROLE_MODEL_INTENTS,
    CONTEXT_MODE_ALLOWED_TOOLS,
    CONTEXT_MODE_BLOCKED_TOOLS,
    CONTEXT_MODE_PINNED_VERSION,
    POLICY_SCOPE_FIXTURES,
    codex_agent_instruction_errors,
    canonical_agent_contract_errors,
    codex_orchestrator_attribution_errors,
    codex_orchestrator_escalation_errors,
    codex_orchestrator_routing_errors,
    claude_rule_paths,
    codex_config_contract_errors,
    copilot_instruction_paths,
    github_agent_model_errors,
    agent_membership_errors,
    mcp_server_parity_errors,
    memory_security_authority_errors,
    pretool_routing_errors,
    root_guidance_errors,
    planner_supervision_contract_errors,
    reporting_policy_errors,
    reporting_prompt_errors,
    scope_matches,
    task_lane_contract_errors,
    task_lane_for,
    TaskLaneInputs,
    workflow_reporting_errors,
    workspace_guidance_errors,
)

import validate_targets as target_validator  # noqa: E402


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
    assert CODEX_CODER_ESCALATION == "sol_coder"
    assert CODEX_ESCALATION_CHAIN == {
        "luna_coder": "coder",
        "coder": "sol_coder",
    }
    assert CODEX_AGENT_MODEL_INTENTS["luna_coder"] == ("gpt-5.6-luna", "xhigh")
    assert CODEX_AGENT_MODEL_INTENTS["sol_coder"] == ("gpt-5.6-sol", "xhigh")

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
    missing_reporting_pointer = claude.replace(
        ".claude/instructions/agent-reporting.instructions.md", "reporting.md", 1
    )
    assert any(
        "agent-reporting.instructions.md" in error
        for error in root_guidance_errors("CLAUDE.md", missing_reporting_pointer)
    )


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
        "PRE-FLIGHT -> BRANCH -> PLAN -> IMPLEMENT -> VERIFY -> REVIEW -> "
        "DOCUMENT -> SCORE -> LEARN -> SESSION LOG -> COMMIT",
        "PRE-FLIGHT -> PLAN -> BRANCH -> IMPLEMENT -> VERIFY -> REVIEW -> "
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

    assert workflow_reporting_errors(workflow) == []
    legacy_reporting = workflow.replace(
        ".claude/instructions/agent-reporting.instructions.md",
        ".claude/instructions/agent-reporting.instructions.md\n\n"
        "Subagents reporting back to the orchestrator should use `caveman` `full`.\n"
        "Preserve tables, code blocks, commands, and paths literally.",
        1,
    )
    assert workflow_reporting_errors(legacy_reporting)


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


def test_reporting_policy_and_agent_prompts_preserve_the_audience_boundary() -> None:
    """The shared policy owns prose rules while each agent retains only a pointer."""
    policy = (
        REPO_ROOT / "shared" / "policies" / "agent-reporting.instructions.md"
    ).read_text(encoding="utf-8")

    assert reporting_policy_errors(policy) == []
    reflowed_policy = policy.replace(
        "does not claim\nformal ASD-STE100 compliance",
        "does not claim formal ASD-STE100 compliance",
        1,
    ).replace(
        "identifiers, API\nnames, commands",
        "identifiers, API names, commands",
        1,
    )
    assert reporting_policy_errors(reflowed_policy) == []
    assert reporting_policy_errors(
        policy.replace(
            "does not claim\nformal ASD-STE100 compliance", "is compliant", 1
        )
    )
    assert reporting_policy_errors(
        policy.replace(
            "Technical precision has priority", "Simple vocabulary has priority", 1
        )
    )
    assert reporting_policy_errors(
        f"{policy}\nDefault to `caveman full` style for user communication.\n"
    )
    assert reporting_policy_errors(
        f"{policy}\nCaveman is the default for user-facing communication.\n"
    )
    assert reporting_policy_errors(
        f"{policy}\nCaveman full is the default for user communication.\n"
    )
    assert reporting_policy_errors(
        f"{policy}\nCaveman full should be the default for human-facing reports.\n"
    )
    assert reporting_policy_errors(
        f"{policy}\nUse caveman full for user-facing communication.\n"
    )
    assert (
        reporting_policy_errors(
            f"{policy}\nDo not use caveman full for user-facing communication.\n"
        )
        == []
    )
    assert (
        reporting_policy_errors(
            f"{policy}\nDo not default to caveman full for human communication.\n"
        )
        == []
    )
    assert reporting_policy_errors(
        f"{policy}\nCaveman is for orchestrator-facing status.\n"
    )

    for prompt_path in sorted((REPO_ROOT / "shared" / "agents").glob("*/prompt.md")):
        prompt = prompt_path.read_text(encoding="utf-8")
        assert reporting_prompt_errors(prompt_path.parent.name, prompt) == []
        assert reporting_prompt_errors(
            prompt_path.parent.name,
            prompt.replace("agent-reporting.instructions.md", "reporting.md", 1),
        )

    coder_prompt = (REPO_ROOT / "shared" / "agents" / "coder" / "prompt.md").read_text(
        encoding="utf-8"
    )
    assert reporting_prompt_errors(
        "coder", f"{coder_prompt}\nDefault to `caveman full`.\n"
    )
    assert reporting_prompt_errors(
        "coder", f"{coder_prompt}\nPreserve tables, code blocks, commands literally.\n"
    )
    assert reporting_prompt_errors(
        "coder", f"{coder_prompt}\nUse active voice where practical.\n"
    )


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


def write_scoped_agent(
    agents_root: Path,
    targets: list[str] | None,
    model_intent: dict[str, object],
    agent_id: str = "codex-only",
    include_delegates: bool = True,
) -> Path:
    """Create minimal canonical metadata for target-scoping tests."""
    agent_dir = agents_root / agent_id
    agent_dir.mkdir(parents=True)
    metadata: dict[str, object] = {
        "id": agent_id,
        "description": "Synthetic target-scoping fixture.",
        "role_type": "fixture",
        "visibility": "hidden",
        "capabilities": ["read"],
        "model_intent": model_intent,
    }
    if include_delegates:
        metadata["delegates"] = []
    if targets is not None:
        metadata["targets"] = targets
    (agent_dir / "agent.yaml").write_text(json.dumps(metadata), encoding="utf-8")
    (agent_dir / "prompt.md").write_text("Synthetic prompt.\n", encoding="utf-8")
    return agent_dir


def test_omitted_agent_targets_resolve_to_all_supported_targets() -> None:
    """Universal agents stay universal while Codex gains two scoped specialists."""
    agents = shared_agents()

    universal_agents = {
        "coder",
        "documenter",
        "orchestrator",
        "planner",
        "reviewer",
        "verifier",
    }
    assert len(agents) == 8
    assert {agent["id"] for agent, _agent_dir in agents} == {
        *universal_agents,
        "luna_coder",
        "sol_coder",
    }
    assert {
        agent["id"] for agent, _agent_dir in shared_agents("github-copilot")
    } == universal_agents
    assert {
        agent["id"] for agent, _agent_dir in shared_agents("claude-code")
    } == universal_agents
    assert {agent["id"] for agent, _agent_dir in shared_agents("openai-codex")} == {
        *universal_agents,
        "luna_coder",
        "sol_coder",
    }


def test_codex_coder_specialist_metadata_and_supplements_are_exact() -> None:
    """Luna and Sol remain constrained Codex-only derivatives of coder."""
    agents_by_id = {
        agent["id"]: (agent, agent_dir) for agent, agent_dir in shared_agents()
    }
    expected_capabilities = [
        "edit",
        "execute",
        "read",
        "search",
        "todo",
        "vscode",
        "web",
    ]
    coder, _coder_dir = agents_by_id["coder"]
    assert coder["capabilities"] == expected_capabilities
    assert coder["model_intent"]["openai-codex"] == {
        "model": "gpt-5.6-terra",
        "effort": "high",
        "escalate_to": "sol_coder",
    }

    luna, luna_dir = agents_by_id["luna_coder"]
    sol, sol_dir = agents_by_id["sol_coder"]
    expected_metadata_fields = {
        "id",
        "description",
        "role_type",
        "visibility",
        "capabilities",
        "delegates",
        "targets",
        "prompt_base",
        "model_intent",
    }
    for specialist in (luna, sol):
        assert set(specialist) == expected_metadata_fields
        assert specialist["role_type"] == "coder"
        assert specialist["visibility"] == "hidden"
        assert specialist["capabilities"] == expected_capabilities
        assert specialist["delegates"] == []
        assert specialist["prompt_base"] == "coder"
        assert specialist["targets"] == ("openai-codex",)

    assert luna["id"] == "luna_coder"
    assert luna["description"] == (
        "Bounded implementation specialist for deterministic Codex orchestration. "
        "Hidden is an internal orchestration convention and does not claim native "
        "Codex UI invisibility."
    )
    assert luna["model_intent"] == {
        "openai-codex": {
            "model": "gpt-5.6-luna",
            "effort": "xhigh",
            "escalate_to": "coder",
        }
    }
    assert sol["id"] == "sol_coder"
    assert sol["description"] == (
        "Final recovery implementation specialist for deterministic Codex "
        "orchestration. Hidden is an internal orchestration convention and does "
        "not claim native Codex UI invisibility."
    )
    assert sol["model_intent"] == {
        "openai-codex": {"model": "gpt-5.6-sol", "effort": "xhigh"}
    }

    luna_supplement = (luna_dir / "prompt.openai-codex.md").read_text(encoding="utf-8")
    normalized_luna_supplement = " ".join(luna_supplement.split())
    for clause in (
        "Before editing, validate the supplied implementation packet where possible.",
        "a clear outcome and plan-step identity;",
        "relevant files, symbols, entry points, patterns, or failing checks;",
        "approved constraints and must-not-change behavior;",
        "rejected approaches when relevant; required skills;",
        "objective acceptance criteria and verification commands;",
        "freedom to choose the smallest maintainable local implementation body, decomposition, and algorithm.",
        "Do not invent missing architecture, interfaces, root cause, migrations, security decisions, ownership, or unrelated refactors.",
        "If the packet is unsafe or insufficient to implement, return only this escalation object:",
        "`workspace_changed` must accurately report whether this agent changed the workspace.",
        "`evidence` and `needed` must be concrete lists.",
        "This is a prompt-enforced handoff object, not a native typed protocol.",
    ):
        assert clause in normalized_luna_supplement
    escalation_match = re.search(
        r"```json\n(?P<object>.*?)\n```", luna_supplement, flags=re.DOTALL
    )
    assert escalation_match is not None
    assert json.loads(escalation_match["object"]) == {
        "status": "escalate",
        "reason": "unknown-root-cause",
        "workspace_changed": False,
        "evidence": ["concrete evidence"],
        "needed": ["needed decision or evidence"],
    }
    reason_section = luna_supplement.split("`reason` must be one of ", 1)[1].split(
        "`workspace_changed`", 1
    )[0]
    assert set(re.findall(r"`([^`]+)`", reason_section)) == {
        "unresolved-design-decision",
        "unknown-root-cause",
        "scope-not-bounded",
        "missing-interface-contract",
        "security-or-migration-decision",
        "ownership-unclear",
    }

    sol_supplement = (sol_dir / "prompt.openai-codex.md").read_text(encoding="utf-8")
    normalized_sol_supplement = " ".join(sol_supplement.split())
    for clause in (
        "Inspect the existing diff and prior verifier or reviewer failure evidence before editing.",
        "Recover with the smallest safe change that addresses that evidence;",
        "do not restart the phase or broaden scope.",
        "Preserve any useful prior work and adapt it only when the evidence requires it.",
        "stop recovery and return control to the orchestrator with the failure evidence and current diff state.",
        "Do not loop, delegate further, or choose another successor.",
    ):
        assert clause in normalized_sol_supplement


def test_codex_orchestrator_routing_is_self_contained_and_target_isolated(
    tmp_path: Path,
) -> None:
    """The named recovery route exists only in Codex's composed orchestrator prompt."""
    agents_by_id = {
        agent["id"]: (agent, agent_dir) for agent, agent_dir in shared_agents()
    }
    orchestrator, orchestrator_dir = agents_by_id["orchestrator"]
    supplement = (orchestrator_dir / "prompt.openai-codex.md").read_text(
        encoding="utf-8"
    )
    rendered_codex = tomllib.loads(render_codex_agent_adapter(orchestrator))[
        "developer_instructions"
    ]

    assert "--- Codex role supplement: orchestrator ---" in rendered_codex
    assert rendered_codex.count("--- Codex role supplement: orchestrator ---") == 1
    assert supplement.strip() in rendered_codex
    assert codex_orchestrator_routing_errors(rendered_codex) == []
    assert codex_orchestrator_escalation_errors(rendered_codex) == []
    normalized_codex = " ".join(rendered_codex.split())
    for clause in (
        "Before editing where possible, `luna_coder` validates the packet.",
        "it returns only this prompt-enforced escalation object; this is not a native typed protocol:",
    ):
        assert clause in normalized_codex
    escalation_match = re.search(
        r"```json\n(?P<object>.*?)\n```", rendered_codex, flags=re.DOTALL
    )
    assert escalation_match is not None
    assert json.loads(escalation_match["object"]) == {
        "status": "escalate",
        "reason": "unknown-root-cause",
        "workspace_changed": False,
        "evidence": ["..."],
        "needed": ["..."],
    }
    reason_section = rendered_codex.split("`reason` is exactly one of ", 1)[1].split(
        "`workspace_changed`", 1
    )[0]
    assert set(re.findall(r"`([^`]+)`", reason_section)) == {
        "unresolved-design-decision",
        "unknown-root-cause",
        "scope-not-bounded",
        "missing-interface-contract",
        "security-or-migration-decision",
        "ownership-unclear",
    }
    invalid_reason_values = ('"other"', "[]", "{}", "7", "null")
    for mutated in (
        rendered_codex.replace("Before editing where possible", "Before editing", 1),
        *(
            rendered_codex.replace(
                '"reason": "unknown-root-cause"', f'"reason": {value}', 1
            )
            for value in invalid_reason_values
        ),
        rendered_codex.replace(
            "`ownership-unclear`.", "`ownership-unclear`, or `other`.", 1
        ),
    ):
        assert codex_orchestrator_escalation_errors(mutated)
    assert any(
        "missing Codex orchestrator routing fragment" in error
        for error in codex_orchestrator_routing_errors(
            rendered_codex.replace(
                "`luna_coder` for that step", "`bounded_coder` for that step", 1
            )
        )
    )
    for prohibited in (
        "model_reasoning_effort",
        "spawn override",
        "spawn-time model override",
        "spawn-time effort override",
        "per-call model override",
        "per-call Luna-specific override",
        "Luna/model-specific override",
    ):
        assert any(
            "obsolete Codex" in error and "override" in error
            for error in codex_orchestrator_routing_errors(
                f"{rendered_codex}\n{prohibited}"
            )
        )

    target_generator.render_claude_agents(tmp_path)
    claude = (tmp_path / ".claude" / "agents" / "orchestrator.md").read_text(
        encoding="utf-8"
    )
    copilot = render_github_agent_adapter(orchestrator, orchestrator_dir)
    for instructions in (claude, copilot):
        assert "luna_coder" not in instructions
        assert "sol_coder" not in instructions
        assert "Codex Coder Routing Supplement" not in instructions


def test_codex_orchestrator_attribution_contract_fails_closed() -> None:
    """Only evidence-backed implementation failures can spend the next tier."""
    orchestrator = next(
        agent for agent, _agent_dir in shared_agents() if agent["id"] == "orchestrator"
    )
    rendered_codex = tomllib.loads(render_codex_agent_adapter(orchestrator))[
        "developer_instructions"
    ]

    assert codex_orchestrator_attribution_errors(rendered_codex) == []
    normalized_codex = " ".join(rendered_codex.split())
    for clause in (
        "`implementation`: the current implementation caused the failure; advance exactly one tier automatically.",
        "`environment`: a missing dependency, service, credential, sandbox restriction, unavailable tool, or other execution-environment blocker; stop model escalation and report it.",
        "`baseline`: evidence shows the failure existed on the originating branch or outside the changed scope; stop model escalation and report it.",
        "`indeterminate`: the evidence cannot reliably attribute the failure; return to orchestrator judgment with no automatic escalation.",
        "A verifier failure alone is not sufficient for `implementation`.",
        "A reviewer CRITICAL or MAJOR finding advances a tier only when it applies to the current implementation diff.",
        "Infrastructure errors, flaky or unreproduced failures, and unrelated baseline findings must not spend a stronger model automatically.",
        "The orchestrator may request focused evidence using existing agents or tools; it must not invent attribution.",
        "Only `implementation` routes once to `sol_coder` with all prior evidence and the current diff, after an attributable Terra-produced failure.",
    ):
        assert clause in normalized_codex

    for removed_clause in (
        "A verifier failure alone is not sufficient for `implementation`.",
        "only when it applies to the current\nimplementation diff.",
        "must not spend a stronger model automatically.",
        "it must not invent attribution.",
        "Only `implementation` routes once to\n`sol_coder` with all prior evidence and the current diff, after an attributable\nTerra-produced failure.",
    ):
        assert codex_orchestrator_attribution_errors(
            rendered_codex.replace(removed_clause, "", 1)
        )

    category_mutations = (
        (
            "extra category",
            "\n\nA verifier failure alone is not sufficient for `implementation`.",
            "\n- `fifth`: spend a stronger model automatically.\n\nA verifier failure alone is not sufficient for `implementation`.",
            "categories must be exactly",
        ),
        (
            "missing indeterminate category",
            "- `indeterminate`: the evidence cannot reliably attribute the failure; return\n  to orchestrator judgment with no automatic escalation.\n",
            "",
            "indeterminate category",
        ),
        (
            "environment stop drift",
            "or other execution-environment blocker; stop\n  model escalation and report it.",
            "or other execution-environment blocker; advance a tier automatically.",
            "environment category",
        ),
        (
            "baseline stop drift",
            "outside the changed scope; stop model escalation and report it.",
            "outside the changed scope; advance a tier automatically.",
            "baseline category",
        ),
    )
    for _name, source, replacement, expected_error in category_mutations:
        mutated = rendered_codex.replace(source, replacement, 1)
        assert mutated != rendered_codex, _name
        assert any(
            expected_error in error
            for error in codex_orchestrator_attribution_errors(mutated)
        )

    unmatched_category_mutations = (
        (
            "alternate asterisk bullet",
            "\n\nA verifier failure alone is not sufficient for `implementation`.",
            "\n* `fifth`: spend a stronger model automatically.\n\nA verifier failure alone is not sufficient for `implementation`.",
        ),
        (
            "alternate plus bullet",
            "\n\nA verifier failure alone is not sufficient for `implementation`.",
            "\n+ `fifth`: spend a stronger model automatically.\n\nA verifier failure alone is not sufficient for `implementation`.",
        ),
        (
            "numbered category bullet",
            "\n\nA verifier failure alone is not sufficient for `implementation`.",
            "\n1. `fifth`: spend a stronger model automatically.\n\nA verifier failure alone is not sufficient for `implementation`.",
        ),
        (
            "stray prose before categories",
            "as exactly one of:\n\n- `implementation`",
            "as exactly one of:\n\nStray category prose.\n\n- `implementation`",
        ),
        (
            "stray prose between categories",
            "automatically.\n- `environment`",
            "automatically.\nStray category prose.\n- `environment`",
        ),
        (
            "stray prose after categories",
            "\n\nA verifier failure alone is not sufficient for `implementation`.",
            "\nStray category prose.\n\nA verifier failure alone is not sufficient for `implementation`.",
        ),
    )
    for name, source, replacement in unmatched_category_mutations:
        mutated = rendered_codex.replace(source, replacement, 1)
        assert mutated != rendered_codex, name
        assert any(
            "category list must contain only canonical bullets" in error
            for error in codex_orchestrator_attribution_errors(mutated)
        )


def test_canonical_coder_routing_contract_rejects_roster_tier_and_graph_drift() -> None:
    """The universal-six/Codex-eight roster and named recovery chain are closed."""
    canonical_agents = shared_agents()
    assert canonical_agent_contract_errors(canonical_agents) == []

    def changed_agents() -> list[tuple[dict[str, object], Path]]:
        return [(deepcopy(agent), agent_dir) for agent, agent_dir in canonical_agents]

    def agent_by_id(
        agents: list[tuple[dict[str, object], Path]], agent_id: str
    ) -> dict[str, object]:
        return next(agent for agent, _agent_dir in agents if agent["id"] == agent_id)

    for agent_id, model, effort in (
        ("luna_coder", "gpt-5.6-luna", "max"),
        ("coder", "gpt-5.6-sol", "high"),
        ("sol_coder", "gpt-5.6-sol", "high"),
    ):
        drifted_agents = changed_agents()
        intent = agent_by_id(drifted_agents, agent_id)["model_intent"]
        assert isinstance(intent, dict)
        codex_intent = intent["openai-codex"]
        assert isinstance(codex_intent, dict)
        codex_intent.update(model=model, effort=effort)
        assert any(
            "model/effort mappings drifted" in error
            for error in canonical_agent_contract_errors(drifted_agents)
        )

    for source, successor in (
        ("luna_coder", "sol_coder"),
        ("coder", "coder"),
        ("coder", None),
    ):
        drifted_agents = changed_agents()
        intent = agent_by_id(drifted_agents, source)["model_intent"]
        assert isinstance(intent, dict)
        codex_intent = intent["openai-codex"]
        assert isinstance(codex_intent, dict)
        if successor is None:
            codex_intent.pop("escalate_to")
        else:
            codex_intent["escalate_to"] = successor
        assert any(
            "escalation contract" in error
            for error in canonical_agent_contract_errors(drifted_agents)
        )

    for target in ("github-copilot", "claude-code"):
        drifted_agents = changed_agents()
        luna = agent_by_id(drifted_agents, "luna_coder")
        luna_targets = luna["targets"]
        assert isinstance(luna_targets, tuple)
        luna["targets"] = (*luna_targets, target)
        assert any(
            f"canonical {target} agents" in error
            for error in canonical_agent_contract_errors(drifted_agents)
        )
    drifted_agents = changed_agents()
    luna = agent_by_id(drifted_agents, "luna_coder")
    luna["targets"] = ()
    assert any(
        "canonical openai-codex agents" in error
        for error in canonical_agent_contract_errors(drifted_agents)
    )


@pytest.mark.parametrize(
    ("targets", "model_intent", "field"),
    (
        ([], {}, "targets must not be empty"),
        (["openai-codex", "openai-codex"], {}, "targets must not contain duplicates"),
        (["not-a-target"], {}, "targets contains unsupported target IDs"),
        (["openai-codex"], {}, "model_intent is missing eligible targets"),
        (
            ["openai-codex"],
            {"github-copilot": "target-default", "openai-codex": {}},
            "model_intent declares ineligible targets",
        ),
        (["github-copilot"], {"github-copilot": 42}, "model_intent.github-copilot"),
        (["claude-code"], {"claude-code": {}}, "model_intent.claude-code.model"),
        (
            ["openai-codex"],
            {"openai-codex": {"model": "gpt-5.6-luna"}},
            "model_intent.openai-codex.effort",
        ),
        (
            ["claude-code"],
            {"claude-code": {"model": "sonnet", "tier": "high"}},
            "model_intent.claude-code has unsupported fields",
        ),
    ),
)
def test_agent_target_metadata_rejects_invalid_scope(
    tmp_path: Path,
    targets: list[str],
    model_intent: dict[str, object],
    field: str,
) -> None:
    """Invalid eligibility metadata names both its file and bad field."""
    agents_root = tmp_path / "agents"
    write_scoped_agent(agents_root, targets, model_intent)

    with pytest.raises(ValueError, match=rf"agent\.yaml: {re.escape(field)}"):
        load_shared_agents(agents_root)


def test_codex_only_agent_renders_only_to_codex(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A scoped agent is emitted only by its eligible target renderer."""
    agents_root = tmp_path / "shared" / "agents"
    write_scoped_agent(
        agents_root,
        ["openai-codex"],
        {"openai-codex": {"model": "gpt-5.6-luna", "effort": "low"}},
    )
    monkeypatch.setattr(target_generator, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(target_generator, "render_root_guidance", lambda _target: "")
    monkeypatch.setattr(target_generator, "render_codex_config", lambda _path: None)
    monkeypatch.setattr(target_generator, "render_codex_hooks", lambda _path: None)
    monkeypatch.setattr(target_generator, "render_copilot_instructions", lambda: "")
    monkeypatch.setattr(target_generator, "shared_policies", lambda: [])
    monkeypatch.setattr(
        target_generator, "copy_file", lambda _source, _destination: None
    )
    monkeypatch.setattr(target_generator, "render_vscode_mcp_json", lambda _path: None)
    monkeypatch.setattr(
        target_generator, "render_vscode_tasks_json", lambda _path: None
    )

    target_generator.render_claude_agents(tmp_path)
    target_generator.render_github(tmp_path)
    target_generator.render_codex(tmp_path)

    assert not (tmp_path / ".claude" / "agents" / "codex-only.md").exists()
    assert not (tmp_path / ".github" / "agents" / "codex-only.agent.md").exists()
    assert (tmp_path / ".codex" / "agents" / "codex-only.toml").exists()


def test_github_only_agent_embeds_its_prompt_without_claude_reference(
    tmp_path: Path,
) -> None:
    """A GitHub-only eligible agent cannot reference an absent Claude adapter."""
    agents_root = tmp_path / "agents"
    agent_dir = write_scoped_agent(
        agents_root,
        ["github-copilot"],
        {"github-copilot": "target-default"},
    )
    agent = load_shared_agents(agents_root)[0][0]

    rendered = render_github_agent_adapter(agent, agent_dir)

    assert ".claude/agents/" not in rendered
    assert "This file is self-contained" in rendered
    assert "Synthetic prompt." in rendered


def test_omitted_delegates_normalizes_to_an_empty_rendered_list(tmp_path: Path) -> None:
    """Historical agent metadata may omit delegates without changing rendering."""
    agents_root = tmp_path / "agents"
    agent_dir = write_scoped_agent(
        agents_root,
        ["github-copilot"],
        {"github-copilot": "target-default"},
        include_delegates=False,
    )
    agent = load_shared_agents(agents_root)[0][0]

    assert agent["delegates"] == []
    assert "agents:" not in render_github_agent_adapter(agent, agent_dir)


def test_agent_loader_preserves_malformed_json_cause(tmp_path: Path) -> None:
    """Malformed agent metadata names its file and preserves loader safety."""
    metadata_path = tmp_path / "agents" / "broken" / "agent.yaml"
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_text("{", encoding="utf-8")

    with pytest.raises(
        ValueError, match=r"agent\.yaml: invalid JSON metadata"
    ) as error:
        load_shared_agents(tmp_path / "agents")

    assert isinstance(error.value.__cause__, json.JSONDecodeError)


def test_agent_loader_rejects_non_object_metadata(tmp_path: Path) -> None:
    """Canonical agent metadata must be a JSON object."""
    metadata_path = tmp_path / "agents" / "broken" / "agent.yaml"
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match=r"agent\.yaml: metadata must be an object"):
        load_shared_agents(tmp_path / "agents")


def test_agent_loader_accepts_approved_underscore_stable_ids(tmp_path: Path) -> None:
    """Stable agent IDs allow the approved underscore routing names."""
    agents_root = tmp_path / "agents"
    write_scoped_agent(
        agents_root,
        ["openai-codex"],
        {"openai-codex": {"model": "gpt-5.6-luna", "effort": "low"}},
        agent_id="luna_coder",
    )

    assert load_shared_agents(agents_root)[0][0]["id"] == "luna_coder"


@pytest.mark.parametrize(
    ("prompt_base", "base_prompt_base", "include_supplement", "expected"),
    (
        ("missing", None, True, "prompt_base references missing agent"),
        ("derived", None, True, "prompt_base must not self-reference"),
        ("base", "root", True, "prompt_base must not create multi-level inheritance"),
        ("base", None, False, "derived Codex agents require prompt.openai-codex.md"),
    ),
)
def test_agent_loader_rejects_invalid_one_level_prompt_composition(
    tmp_path: Path,
    prompt_base: str,
    base_prompt_base: str | None,
    include_supplement: bool,
    expected: str,
) -> None:
    """Derived Codex prompts must have one real base and one supplement."""
    agents_root = tmp_path / "agents"
    base = write_scoped_agent(
        agents_root,
        ["openai-codex"],
        {"openai-codex": {"model": "gpt-5.6-terra", "effort": "high"}},
        agent_id="base",
    )
    if base_prompt_base is not None:
        root = write_scoped_agent(
            agents_root,
            ["openai-codex"],
            {"openai-codex": {"model": "gpt-5.6-terra", "effort": "high"}},
            agent_id="root",
        )
        metadata = json.loads((base / "agent.yaml").read_text(encoding="utf-8"))
        metadata["prompt_base"] = base_prompt_base
        (base / "agent.yaml").write_text(json.dumps(metadata), encoding="utf-8")
        (root / "prompt.md").write_text("Root prompt.\n", encoding="utf-8")

    derived = agents_root / "derived"
    derived.mkdir()
    derived_metadata = {
        "id": "derived",
        "description": "Derived fixture.",
        "role_type": "coder",
        "visibility": "hidden",
        "capabilities": ["read"],
        "delegates": [],
        "targets": ["openai-codex"],
        "prompt_base": prompt_base,
        "model_intent": {"openai-codex": {"model": "gpt-5.6-luna", "effort": "xhigh"}},
    }
    (derived / "agent.yaml").write_text(json.dumps(derived_metadata), encoding="utf-8")
    if include_supplement:
        (derived / "prompt.openai-codex.md").write_text(
            "Derived supplement.\n", encoding="utf-8"
        )

    with pytest.raises(ValueError, match=re.escape(expected)):
        load_shared_agents(agents_root)


def test_agent_loader_rejects_named_escalation_cycles(tmp_path: Path) -> None:
    """Named Codex escalation targets cannot create a recovery loop."""
    agents_root = tmp_path / "agents"
    for agent_id, target_id in (("first", "second"), ("second", "first")):
        agent_dir = write_scoped_agent(
            agents_root,
            ["openai-codex"],
            {
                "openai-codex": {
                    "model": "gpt-5.6-terra",
                    "effort": "high",
                    "escalate_to": target_id,
                }
            },
            agent_id=agent_id,
        )
        (agent_dir / "prompt.md").write_text("Prompt.\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Codex escalation cycle detected"):
        load_shared_agents(agents_root)


def test_agent_loader_rejects_prompt_base_cycles(tmp_path: Path) -> None:
    """Prompt composition cycles fail before any generated prompt is read."""
    agents_root = tmp_path / "agents"
    for agent_id, base_id in (("first", "second"), ("second", "first")):
        agent_dir = agents_root / agent_id
        agent_dir.mkdir(parents=True)
        metadata = {
            "id": agent_id,
            "description": "Derived fixture.",
            "role_type": "coder",
            "visibility": "hidden",
            "capabilities": ["read"],
            "delegates": [],
            "targets": ["openai-codex"],
            "prompt_base": base_id,
            "model_intent": {
                "openai-codex": {"model": "gpt-5.6-luna", "effort": "xhigh"}
            },
        }
        (agent_dir / "agent.yaml").write_text(json.dumps(metadata), encoding="utf-8")
        (agent_dir / "prompt.openai-codex.md").write_text(
            "Derived supplement.\n", encoding="utf-8"
        )

    with pytest.raises(ValueError, match="prompt_base cycle detected"):
        load_shared_agents(agents_root)


@pytest.mark.parametrize(
    "supplement",
    (
        "# Header\n\nUse AGENTS.md and keep implementation focused.\n",
        "# Header\n\nUse   AGENTS.md\n\n and\tkeep implementation\nfocused.\n",
    ),
    ids=("transformed-copy", "whitespace-normalized-copy"),
)
def test_agent_loader_rejects_transformed_or_whitespace_copied_base_prompt(
    tmp_path: Path, supplement: str
) -> None:
    """A supplement cannot conceal a complete base copy behind target rewrites."""
    agents_root = tmp_path / "agents"
    base = write_scoped_agent(
        agents_root,
        ["openai-codex"],
        {"openai-codex": {"model": "gpt-5.6-terra", "effort": "high"}},
        agent_id="base",
    )
    (base / "prompt.md").write_text(
        "# Header\n\nUse .github/copilot-instructions.md and keep implementation focused.\n",
        encoding="utf-8",
    )
    derived = agents_root / "derived"
    derived.mkdir()
    metadata = {
        "id": "derived",
        "description": "Derived fixture.",
        "role_type": "coder",
        "visibility": "hidden",
        "capabilities": ["read"],
        "delegates": [],
        "targets": ["openai-codex"],
        "prompt_base": "base",
        "model_intent": {"openai-codex": {"model": "gpt-5.6-luna", "effort": "xhigh"}},
    }
    (derived / "agent.yaml").write_text(json.dumps(metadata), encoding="utf-8")
    (derived / "prompt.openai-codex.md").write_text(supplement, encoding="utf-8")

    with pytest.raises(ValueError, match="must not copy its full base prompt"):
        load_shared_agents(agents_root)


def test_agent_loader_allows_only_codex_normal_agent_supplements(
    tmp_path: Path,
) -> None:
    """A normal prompt can add Codex-only guidance without leaking to other targets."""
    agents_root = tmp_path / "agents"
    agent_dir = write_scoped_agent(
        agents_root,
        ["openai-codex"],
        {"openai-codex": {"model": "gpt-5.6-sol", "effort": "xhigh"}},
    )
    supplement = agent_dir / "prompt.openai-codex.md"
    supplement.write_text("Codex-only supplement.\n", encoding="utf-8")
    assert load_shared_agents(agents_root)[0][0]["id"] == "codex-only"

    metadata = json.loads((agent_dir / "agent.yaml").read_text(encoding="utf-8"))
    metadata["targets"] = ["claude-code"]
    metadata["model_intent"] = {"claude-code": {"model": "sonnet"}}
    (agent_dir / "agent.yaml").write_text(json.dumps(metadata), encoding="utf-8")
    with pytest.raises(ValueError, match="requires Codex eligibility"):
        load_shared_agents(agents_root)


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    (
        ("description", None, "description must be a non-empty string"),
        ("role_type", 7, "role_type must be a non-empty string"),
        ("visibility", "internal", "visibility must be one of"),
        ("capabilities", ["read", "read"], "capabilities must not contain duplicates"),
        ("capabilities", ["invent"], "capabilities contains unsupported values"),
        (
            "delegates",
            ["luna_coder", "luna_coder"],
            "delegates must not contain duplicates",
        ),
        ("delegates", ["not valid"], "delegates must contain stable agent IDs"),
        (
            "model_intent",
            {"claude-code": {"model": "sonnet", "effort": 7}},
            "model_intent.claude-code.effort must be a non-empty string",
        ),
        (
            "model_intent",
            {
                "claude-code": {"model": "sonnet"},
                "openai-codex": {
                    "model": "gpt-5.6-luna",
                    "effort": "low",
                    "escalate_to": {"agent": "sol_coder"},
                },
            },
            "model_intent.openai-codex.escalate_to must be a non-empty string",
        ),
    ),
)
def test_agent_loader_validates_renderer_consumed_metadata(
    tmp_path: Path, field: str, value: object, expected: str
) -> None:
    """All metadata a renderer reads is validated before generation starts."""
    agents_root = tmp_path / "agents"
    agent_dir = write_scoped_agent(
        agents_root,
        ["claude-code"],
        {"claude-code": {"model": "sonnet"}},
    )
    metadata_path = agent_dir / "agent.yaml"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if value is None:
        del metadata[field]
    else:
        metadata[field] = value
    if "openai-codex" in metadata["model_intent"]:
        metadata["targets"].append("openai-codex")
    metadata_path.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ValueError, match=rf"agent\.yaml: {re.escape(expected)}"):
        load_shared_agents(agents_root)


def test_agent_membership_errors_reject_target_omission_and_leakage() -> None:
    """Target validation independently reports both eligibility failure modes."""
    errors = agent_membership_errors("openai-codex", {"codex-only"}, {"github-only"})

    assert "openai-codex missing eligible agents: ['codex-only']" in errors
    assert "openai-codex contains ineligible agents: ['github-only']" in errors


@pytest.mark.parametrize(
    ("relative_path", "contents", "expected"),
    (
        (
            ".github/agents/planner.agent.md",
            None,
            "github-copilot missing eligible agents: ['planner']",
        ),
        (
            ".github/agents/leaked.agent.md",
            ".github/agents/coder.agent.md",
            "github-copilot contains ineligible agents: ['leaked']",
        ),
        (
            ".github/agents/luna_coder.agent.md",
            ".github/agents/coder.agent.md",
            "github-copilot contains ineligible agents: ['luna_coder']",
        ),
        (
            ".claude/agents/luna_coder.md",
            ".claude/agents/coder.md",
            "claude-code contains ineligible agents: ['luna_coder']",
        ),
        (
            ".codex/agents/luna_coder.toml",
            None,
            "openai-codex missing eligible agents: ['luna_coder']",
        ),
        (
            ".codex/agents/sol_coder.toml",
            None,
            "openai-codex missing eligible agents: ['sol_coder']",
        ),
    ),
)
def test_validate_agents_rejects_generated_target_omission_and_leakage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative_path: str,
    contents: str | None,
    expected: str,
) -> None:
    """The full agent validator detects generated target membership drift."""
    target_root = tmp_path / "multi-agent"
    shutil.copytree(REPO_ROOT / "dist" / "multi-agent", target_root)
    path = target_root / relative_path
    if contents is None:
        path.unlink()
    else:
        path.write_text(
            (target_root / contents).read_text(encoding="utf-8"), encoding="utf-8"
        )
    monkeypatch.setattr(target_validator, "TARGET_ROOT", target_root)

    errors: list[str] = []
    target_validator.validate_agents(errors)

    assert expected in errors


@pytest.mark.parametrize("field", ("skills", "mcp_servers"))
def test_validate_agents_rejects_codex_agent_local_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    """Codex agents inherit skills and MCP configuration instead of overriding it."""
    target_root = tmp_path / "multi-agent"
    shutil.copytree(REPO_ROOT / "dist" / "multi-agent", target_root)
    agent_path = target_root / ".codex" / "agents" / "coder.toml"
    agent_path.write_text(
        f"{agent_path.read_text(encoding='utf-8')}\n{field} = []\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(target_validator, "TARGET_ROOT", target_root)

    errors: list[str] = []
    target_validator.validate_agents(errors)

    assert any(
        "must not define per-agent overrides" in error and field in error
        for error in errors
    )


@pytest.mark.parametrize(
    ("metadata", "expected"),
    (
        ("{", "invalid JSON metadata"),
        (
            json.dumps(
                {
                    "id": "github_only",
                    "description": "Malformed model-intent fixture.",
                    "role_type": "fixture",
                    "visibility": "hidden",
                    "capabilities": ["read"],
                    "delegates": [],
                    "targets": ["github-copilot"],
                    "model_intent": {"github-copilot": 42},
                }
            ),
            "model_intent.github-copilot must be a non-empty string",
        ),
    ),
)
def test_validate_agents_reports_canonical_loader_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    metadata: str,
    expected: str,
) -> None:
    """The full validator reports malformed canonical metadata without crashing."""
    metadata_path = tmp_path / "shared" / "agents" / "broken" / "agent.yaml"
    metadata_path.parent.mkdir(parents=True)
    metadata_path.write_text(metadata, encoding="utf-8")
    monkeypatch.setattr(target_generator, "REPO_ROOT", tmp_path)

    errors: list[str] = []
    target_validator.validate_agents(errors)

    assert errors == [f"{metadata_path}: {expected}"]


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


def test_mcp_server_parity_errors_fail_independently() -> None:
    """A single drifted/missing server must fail on its own, never bundled
    with, or masked by, an unrelated server's result."""
    shared_mcp = {
        "semble": {"command": "uvx", "args": ["semble"]},
        "context7": {"command": "npx", "args": ["context7"]},
        "context-mode": {"command": "bash", "args": ["dispatch.sh", "server"]},
    }

    only_semble_drifted = dict(shared_mcp, semble={"command": "uvx", "args": ["WRONG"]})
    assert mcp_server_parity_errors(only_semble_drifted, shared_mcp, "target") == [
        "target MCP server drifted from shared source: semble"
    ]

    only_context7_missing = {
        key: value for key, value in shared_mcp.items() if key != "context7"
    }
    assert mcp_server_parity_errors(only_context7_missing, shared_mcp, "target") == [
        "target missing MCP server: context7"
    ]

    only_context_mode_drifted = dict(
        shared_mcp, **{"context-mode": {"command": "node", "args": []}}
    )
    assert mcp_server_parity_errors(
        only_context_mode_drifted, shared_mcp, "target"
    ) == ["target MCP server drifted from shared source: context-mode"]

    assert mcp_server_parity_errors(shared_mcp, shared_mcp, "target") == []


def test_context_mode_tool_surface_is_exactly_four_tools_everywhere() -> None:
    """The approved allowlist is exact and closed: exactly four tools, pinned
    to 1.0.169, and no blocked tool name reaches any generated routing or
    permission surface (agent tool grants, MCP server configs, hook
    scripts)."""
    assert CONTEXT_MODE_ALLOWED_TOOLS == (
        "ctx_index",
        "ctx_search",
        "ctx_stats",
        "ctx_doctor",
    )
    assert CONTEXT_MODE_PINNED_VERSION == "1.0.169"

    target_root = REPO_ROOT / "dist" / "multi-agent"
    surfaces = [
        *sorted((target_root / ".claude" / "agents").glob("*.md")),
        *sorted((target_root / ".codex" / "agents").glob("*.toml")),
        *sorted((target_root / ".github" / "agents").glob("*.agent.md")),
        target_root / ".mcp.json",
        target_root / ".vscode" / "mcp.json",
        target_root / ".codex" / "config.toml",
        target_root / ".claude" / "hooks" / "scripts" / "context-mode-dispatch.sh",
        target_root / ".claude" / "hooks" / "scripts" / "context-mode-mcp-filter.mjs",
    ]
    for path in surfaces:
        text = path.read_text()
        for blocked in CONTEXT_MODE_BLOCKED_TOOLS:
            assert blocked not in text, (
                f"{path} names blocked Context Mode tool {blocked}"
            )

    filter_text = (
        REPO_ROOT / "shared/hooks/scripts/context-mode-mcp-filter.mjs"
    ).read_text()
    allowed = ", ".join(f'"{tool}"' for tool in CONTEXT_MODE_ALLOWED_TOOLS)
    assert f"new Set([{allowed}])" in filter_text


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
    for agent, agent_dir in shared_agents("openai-codex"):
        rendered = render_codex_agent_adapter(agent)
        instructions = tomllib.loads(rendered)["developer_instructions"]
        prompt_base = agent.get("prompt_base")
        supplement_path = agent_dir / "prompt.openai-codex.md"
        if isinstance(prompt_base, str) or supplement_path.exists():
            base_prompt = transform_agent_text(
                (
                    REPO_ROOT / "shared" / "agents" / prompt_base / "prompt.md"
                    if isinstance(prompt_base, str)
                    else agent_dir / "prompt.md"
                ).read_text(encoding="utf-8"),
                "openai-codex",
            ).strip()
            supplement = transform_agent_text(
                supplement_path.read_text(encoding="utf-8"),
                "openai-codex",
            ).strip()
            role_delimiter = {
                "luna_coder": "--- Codex role supplement: luna_coder ---",
                "sol_coder": "--- Codex role supplement: sol_coder ---",
                "orchestrator": "--- Codex role supplement: orchestrator ---",
            }[agent["id"]]
            expected_body = f"{base_prompt}\n\n{role_delimiter}\n\n{supplement}"
        else:
            expected_body = transform_agent_text(
                (agent_dir / "prompt.md").read_text(encoding="utf-8"),
                "openai-codex",
            ).strip()

        assert instructions.count(CODEX_AGENT_INSTRUCTIONS_DELIMITER) == 1
        assert (
            instructions.split(CODEX_AGENT_INSTRUCTIONS_DELIMITER, 1)[1].strip()
            == expected_body
        )
        assert "Before doing the task, read `.claude/agents/" not in instructions
        assert "[mcp_servers." not in rendered
        assert codex_agent_instruction_errors(agent, instructions) == []
        if isinstance(prompt_base, str) or supplement_path.exists():
            assert instructions.count(role_delimiter) == 1
        else:
            assert "--- Codex role supplement:" not in instructions

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
