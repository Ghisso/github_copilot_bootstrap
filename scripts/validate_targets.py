#!/usr/bin/env python3
"""Validate the generated bootstrap target."""

from __future__ import annotations

import filecmp
import hashlib
import json
import os
import py_compile
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import tomllib
from pathlib import Path
from typing import TypedDict, Unpack

from check_runtime import runtime_drift_errors
from generate_targets import (
    CODEX_AGENT_INSTRUCTIONS_DELIMITER,
    CODEX_ROLE_SUPPLEMENT_DELIMITER,
    ROOT_GUIDANCE_WORKFLOW,
    SUPPORTED_AGENT_TARGETS,
    codex_agent_metadata_header,
    codex_agent_prompt_body,
    shared_agents,
    shared_policies,
    transform_agent_text,
)
from install_bootstrap import copy_generated_tree
from runtime_ownership import CONSUMER_STATE_PATHS, render_restore_script

REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_ROOT = REPO_ROOT / "dist"
TARGETS = ("multi-agent",)
TARGET_ROOT = DIST_ROOT / "multi-agent"
COPILOT_MODEL_PINS = (
    "GPT-5.4",
    "Claude Opus 4.6",
    "Claude Sonnet 4.6",
    "(copilot)",
)
# Hand-maintained allow-list of Copilot picker model names. These were valid
# against the official GitHub Copilot supported-models reference as last checked
# 2026-07-03. This list rots silently as the picker changes — re-verify against
# the reference and update the date when you touch it.
GITHUB_ALLOWED_AGENT_MODELS = {
    "GPT-5.4",
    "Claude Opus 4.6",
    "Claude Sonnet 4.6",
}
# Claude subagent frontmatter allow-lists. Model aliases and effort levels are
# validated against the official Claude Code references as last checked
# 2026-07-09 (subagents.md supported frontmatter fields; model-config.md effort
# level table). Re-verify and update the date when you touch these.
CLAUDE_ALLOWED_AGENT_MODELS = {"opus", "sonnet", "haiku", "fable", "inherit"}
CLAUDE_ALLOWED_EFFORT = {"low", "medium", "high", "xhigh", "max"}
# Models that do NOT support the effort field: Haiku is absent from the
# model-config.md effort table, so any effort on a Haiku agent is invalid.
CLAUDE_NO_EFFORT_MODELS = {"haiku"}
# GPT-5.6 model and effort values (developers.openai.com/api/docs/guides/latest-model,
# checked 2026-07-18). Keep these strict so misspelled or retired values fail
# generation validation instead of reaching consumer sessions.
CODEX_ALLOWED_AGENT_MODELS = {"gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"}
CODEX_ALLOWED_EFFORT = {"none", "low", "medium", "high", "xhigh", "max"}
# Current declared routing contract. The 2026-07-18 runtime probe used
# documenter Terra/medium; that historical result must not overwrite the
# current Luna/medium declaration below.
CODEX_ROLE_MODEL_INTENTS = {
    "orchestrator": ("gpt-5.6-sol", "xhigh"),
    "planner": ("gpt-5.6-sol", "xhigh"),
    "coder": ("gpt-5.6-terra", "high"),
    "reviewer": ("gpt-5.6-sol", "high"),
    "documenter": ("gpt-5.6-luna", "medium"),
    "verifier": ("gpt-5.6-luna", "low"),
}
CODEX_SPECIALIST_MODEL_INTENTS = {
    "luna_coder": ("gpt-5.6-luna", "xhigh"),
    "sol_coder": ("gpt-5.6-sol", "xhigh"),
}
CODEX_AGENT_MODEL_INTENTS = {
    **CODEX_ROLE_MODEL_INTENTS,
    **CODEX_SPECIALIST_MODEL_INTENTS,
}
CODEX_CODER_ESCALATION = "sol_coder"
CODEX_ESCALATION_CHAIN = {"luna_coder": "coder", "coder": "sol_coder"}
PLANNER_PROMPT_REQUIRED_FRAGMENTS = (
    "orchestrator's evidence packet",
    "exact artifacts, supplied evidence, approved decisions, constraints",
    "genuinely unresolved questions",
    "do not repeat broad intake, discovery, or user interview questions that the user has already answered",
    "Bounded Discovery",
    "Do not repeat answered discovery during a bounded full-plan revision",
    "Do not require a fixed number of interview rounds",
    "When genuinely unresolved decisions remain, use a focused PRD-style interview before drafting",
    "Module Sketch (only when an unresolved interface decision needs it)",
    "Present the sketch for confirmation only when the decision requires user input",
    "Iterate only when a user response is needed to resolve that decision",
)
PLANNER_PROMPT_FORBIDDEN_FRAGMENTS = (
    "Uses a PRD-style interview to surface unknowns before drafting.",
    "Show the user the sketch and ask for confirmation before proceeding.",
    "Iterate at least once based on user responses.",
)
ORCHESTRATOR_PROMPT_REQUIRED_FRAGMENTS = (
    "prepare a compact evidence packet containing approved decisions, verified facts and measurements, exact artifacts and source locations, constraints, rejected approaches, and genuinely unresolved questions",
    "compact, minimally scoped task and evidence packet",
    "Keep one active planner",
    "A pending wait means no mailbox event arrived during that polling window",
    "does not establish success, failure, progress, or a transport outage",
    "runtime-native agent state, recent observable activity, and actual terminal, tool, or configuration errors",
    "Silence alone is not health evidence",
    "at least every five minutes",
    "30 minutes as a provisional floor before a planner health review",
    "not an automatic interruption timer",
    "Explicit user cancellation and an actual terminal error remain immediate exceptions",
    "Do not add a generic `max` retry or lower the default to `high`",
    "two matched `xhigh` runs reproduce a material checklist failure",
)
REQUIRED_HOOK_SCRIPTS = (
    "run-hook.sh",
    "protect-files.sh",
    "protect-files.py",
    "pretool-bash-guard.sh",
    "git-protection.sh",
    "context-mode-dispatch.sh",
    "session-log.sh",
    "state-sync.sh",
    "restore-root-adapters.sh",
    "enforce-branch-state.sh",
    "record-branch-state.sh",
    "enforce-commit-gate.sh",
    "record-commit-closeout.sh",
    "enforce-pr-gate.sh",
    "session-start-state.sh",
    "stop-session-log-check.sh",
    "claude-stop.sh",
    "codex-stop.sh",
)
# Approved Context Mode capability contract (Phase F). The allowlist is exact
# and closed; a new upstream tool needs a later approved plan before it can
# join CONTEXT_MODE_ALLOWED_TOOLS.
CONTEXT_MODE_PINNED_VERSION = "1.0.169"
CONTEXT_MODE_ALLOWED_TOOLS = ("ctx_index", "ctx_search", "ctx_stats", "ctx_doctor")
CONTEXT_MODE_BLOCKED_TOOLS = (
    "ctx_execute",
    "ctx_execute_file",
    "ctx_batch_execute",
    "ctx_fetch_and_index",
    "ctx_upgrade",
    "ctx_purge",
    "ctx_insight",
)
REQUIRED_HOOK_LIBRARIES = ("_lib-frontmatter.sh",)
REQUIRED_GIT_HOOKS = (
    "commit-msg",
    "pre-push",
    "post-commit",
)
NON_COPILOT_REVIEW_LABEL_LEAKS = (
    "Review Pass (Codex)",
    "Review Pass (Sonnet)",
    "Findings (Codex)",
    "Findings (Sonnet)",
)
NON_COPILOT_PATH_LEAKS = (
    ".github/session_logs",
    ".github/quality_reports",
    ".github/explorations",
    ".github/plans",
    ".github/skills",
    ".github/agents",
    ".github/hooks",
    ".github/instructions",
    ".github/MEMORY.md",
    ".github/scripts",
    ".codex/skills",
    ".github/AGENTS.md",
    ".github/CLAUDE.md",
    "copilot-instructions.md",
    "Copy `.github/` directory",
    "new project's `.github/`",
    "git add .github/",
    "AGENTS.md/",
    "CLAUDE.md/",
    "AGENTS.md**",
    "CLAUDE.md**",
    "AGENTS.mdtool",
    "CLAUDE.mdtool",
)
OBSOLETE_GENERATED_DIRS = (
    ".github/skills",
    ".github/scripts",
    ".github/templates",
    ".github/session_logs",
    ".github/quality_reports",
    ".github/explorations",
    ".github/plans",
    ".agents/skills",
    ".codex/skills",
    ".codex/scripts",
    ".codex/templates",
    ".codex/session_logs",
    ".codex/quality_reports",
    ".codex/explorations",
    ".codex/plans",
    ".codex/hooks/scripts",
)
OBSOLETE_ROOT_SOURCE_DIRS = (
    ".github/agents",
    ".github/instructions",
    ".github/skills",
    ".github/scripts",
    ".github/templates",
    ".github/plans",
    ".github/session_logs",
    ".github/quality_reports",
    ".github/hooks/scripts",
)
ROOT_GUIDANCE_HEADERS = (
    "## Source Of Truth",
    "## Task Lanes",
    "## Required Lifecycle",
    "## Exact Commands",
    "## Safety And Control Plane",
    "## Map",
    "## Target Runtime",
)
ROOT_GUIDANCE_BUDGETS = {
    "CLAUDE.md": ("lines", 200),
    "AGENTS.md": ("bytes", 16 * 1024),
}
ROOT_GUIDANCE_CONTROL_PLANE_FRAGMENTS = {
    "CLAUDE.md": ("`.claude/hooks/`", "`.github/hooks/`"),
    "AGENTS.md": ("`.codex/`", "`.github/hooks/`"),
}
ROOT_GUIDANCE_AUTHORING_PHRASES = (
    "Bootstrap Guidance",
    "reusable multi-agent bootstrap",
    "In an installed project",
    "Bootstrap maintainers own authoring and regeneration",
)
REPORTING_POLICY_POINTER = ".claude/instructions/agent-reporting.instructions.md"
REPORTING_POLICY_REQUIRED_FRAGMENTS = (
    "## Human-facing communication",
    "precise, clear, direct, natural prose",
    "inspired by ASD-STE100 principles",
    "does not claim formal ASD-STE100 compliance",
    "Apply these rules strongly",
    "Apply them lightly to commit messages",
    "Use common words when they are as precise",
    "Use one term consistently",
    "short, direct sentences",
    "active voice where practical",
    "Avoid idioms, buzzwords, marketing language, and unnecessary abbreviations",
    "Define an uncommon abbreviation or technical term",
    "Technical precision has priority over simpler vocabulary",
    "identifiers, API names, commands, paths, logs, errors, structured findings, quotations",
    "Do not lossily rewrite",
    "Do not make a rewrite stage mandatory",
    "## Agent-to-agent status and handoffs",
    "`caveman full` may be the default",
    "not the default for user communication",
)
REPORTING_POLICY_FORBIDDEN_FRAGMENTS = (
    "default to `caveman full` style",
    "caveman is for orchestrator-facing status",
    "caveman full for narrative/prose sections",
)
REPORTING_CAVEMAN_USER_DEFAULT_PATTERNS = (
    re.compile(
        r"(?:default to|use) [`']?caveman(?: full)?[`']?.{0,60}"
        r"(?:user(?:-facing)?|human(?:-facing)?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"caveman(?: full)? (?:is|as|should be|must be) (?:the )?default.{0,30}"
        r"(?:user(?:-facing)?|human(?:-facing)?)",
        re.IGNORECASE,
    ),
)
REPORTING_PROMPT_DUPLICATE_FRAGMENTS = (
    "default to `caveman full`",
    "preserve tables, code blocks, commands",
    "precise, clear, direct, natural prose",
    "inspired by ASD-STE100 principles",
    "use common words when",
    "use one term consistently",
    "short, direct sentences",
    "active voice where practical",
    "avoid idioms, buzzwords",
    "define an uncommon abbreviation",
    "keep established technical terms",
    "technical precision has priority",
    "do not make a rewrite stage mandatory",
    "do not lossily rewrite",
)
WORKFLOW_REPORTING_FORBIDDEN_FRAGMENTS = (
    "subagents reporting back to the orchestrator should use",
    "preserve tables, code blocks, commands",
    "the documenter writes normal user-facing prose",
    "`caveman` `full`",
)
SHARED_GITHUB_HOOK_INVENTORY_PATHS = {
    TARGET_ROOT / "CLAUDE.md",
    TARGET_ROOT / "AGENTS.md",
    TARGET_ROOT / ".claude" / "instructions" / "workspace.instructions.md",
    TARGET_ROOT / ".claude" / "instructions" / "workspace.md",
}
TASK_LANE_CONTROL_PLANE_PATHS = (
    ".claude/hooks/",
    ".claude/settings.json",
    ".github/hooks/",
    ".codex/",
    ".mcp.json",
    ".devcontainer/",
)
TASK_LANE_CONTROL_PLANE_FILES = {"CLAUDE.md", "AGENTS.md"}
TASK_LANE_REQUIRED_FRAGMENTS = (
    "This is the single normative\ntask-size decision table",
    "Do not use time or line-count thresholds to classify a lane.",
    "Read-only/reporting",
    "Main agent; inspect and provide evidence only.",
    "Lightweight edit",
    "The request is explicit, changes one non-control-plane file, is low risk",
    "no dependency/lockfile, migration, user-data, security, or control-plane impact",
    "requests no commit or PR",
    "Main agent; make the focused edit and run proportionate focused verification.",
    "No lifecycle artifacts.",
    "Standard implementation",
    "including all work with a requested commit or PR.",
    "Main-thread orchestrator; use a micro-plan or full-plan",
    "Control-plane/high-risk",
    "generator, or script change.",
    "Main-thread orchestrator; use a full plan",
    "`code`, `architecture`, `security`, `tests`, and `ponytail` review.",
    "already-explicit request or approved plan is sufficient authority",
    "audited recovery exceptions, never task-lane\nclassification",
)
TASK_LANE_FORBIDDEN_FRAGMENTS = (
    ">1 file or >30 min",
    "Skip planning only for:",
    "there is no trivial-task fast path",
    "Pause and ask the user to confirm the change before applying.",
)


class TaskLaneInputs(TypedDict, total=False):
    """Named inputs for the executable Task Lanes regression fixture."""

    change_requested: bool
    explicit: bool
    affected_paths: tuple[str, ...]
    low_risk: bool
    commit_or_pr_requested: bool
    security_impact: bool
    dependency_or_lockfile_impact: bool
    migration: bool
    user_data_impact: bool


ROOT_LIFECYCLE_PATTERN = re.compile(
    r"\b(?:PRE-FLIGHT|BRANCH|PLAN|IMPLEMENT|VERIFY|REVIEW|DOCUMENT|"
    r"SCORE|LEARN|SESSION LOG|COMMIT)(?:\s*->\s*(?:PRE-FLIGHT|BRANCH|PLAN|"
    r"IMPLEMENT|VERIFY|REVIEW|DOCUMENT|SCORE|LEARN|SESSION LOG|COMMIT))+\b",
    re.IGNORECASE,
)
POLICY_SCOPE_FIXTURES = {
    "api-service-standards.instructions.md": (
        ("service.py", True),
        ("src/api/routes/health.py", True),
        ("src/services/health.py", False),
    ),
    "code-standards.instructions.md": (
        ("src/pipeline.py", True),
        ("tests/unit/test_pipeline.py", True),
        ("docs/pipeline.py", False),
    ),
    "config-first-design.instructions.md": (
        ("src/configs/model.py", True),
        ("src/models/model.py", False),
    ),
    "deployment.instructions.md": (
        ("service.py", True),
        ("gradio_app/app.py", True),
        ("deployment/docker/Dockerfile", True),
        ("src/service.py", False),
    ),
    "tests.instructions.md": (
        ("tests/unit/test_routes.py", True),
        ("src/test_routes.py", False),
    ),
}
CODEX_POLICY_SKILL_FALLBACKS = {
    "api-service-standards.instructions.md": "bentoml-service",
    "code-standards.instructions.md": "code-style",
    "config-first-design.instructions.md": "hydra-config",
    "deployment.instructions.md": "deploy-service",
    "tests.instructions.md": "testing-patterns",
}


def text_files(root: Path) -> list[Path]:
    return [
        path
        for path in root.rglob("*")
        if path.is_file()
        and not any(part in {".git", "__pycache__"} for part in path.parts)
        and path.suffix not in {".pyc"}
    ]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def read_toml(path: Path) -> dict[str, object]:
    return tomllib.loads(read(path))


def check(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def root_guidance_errors(name: str, text: str) -> list[str]:
    """Return structural invariant failures for one generated root guidance file."""
    errors: list[str] = []
    budget_kind, budget = ROOT_GUIDANCE_BUDGETS[name]
    size = len(text.splitlines()) if budget_kind == "lines" else len(text.encode())
    if size > budget:
        errors.append(f"{name} exceeds its {budget_kind} budget of {budget}")
    for header in ROOT_GUIDANCE_HEADERS:
        if text.count(f"{header}\n") != 1:
            errors.append(f"{name} must contain exactly one {header!r} section")
    lifecycle_matches = [
        " ".join(match.group(0).upper().split())
        for match in ROOT_LIFECYCLE_PATTERN.finditer(text)
    ]
    if lifecycle_matches != [ROOT_GUIDANCE_WORKFLOW]:
        errors.append(
            f"{name} must contain exactly one canonical lifecycle in the required phase order"
        )
    required_fragments = (
        ".claude/MEMORY.md",
        "<plan_name>_implementation",
        ".claude/skills/ponytail/SKILL.md",
        "score is at least 90",
        "documentation before persisting findings and score",
        REPORTING_POLICY_POINTER,
        "Control-plane files include",
        "Keep hook guardrails enabled",
        "uv run pytest tests/ -q --tb=short",
        "sole normative classifier",
    )
    for fragment in required_fragments:
        if fragment not in text:
            errors.append(
                f"{name} is missing mandatory root-guidance invariant: {fragment}"
            )
    for fragment in ROOT_GUIDANCE_CONTROL_PLANE_FRAGMENTS[name]:
        if fragment not in text:
            errors.append(f"{name} is missing control-plane inventory path: {fragment}")
    for phrase in ROOT_GUIDANCE_AUTHORING_PHRASES:
        if phrase in text:
            errors.append(
                f"{name} contains authoring-specific root-guidance phrase: {phrase}"
            )
    return errors


def workspace_guidance_errors(text: str) -> list[str]:
    """Return failures for the shared Git-hook control-plane inventory."""
    errors: list[str] = []
    for fragment in ("`.claude/hooks/`", "`.github/hooks/`"):
        if text.count(fragment) != 1:
            errors.append(
                "workspace guidance must contain exactly one control-plane inventory path: "
                f"{fragment}"
            )
    return errors


def normalized_text(text: str) -> str:
    """Collapse Markdown layout into text suitable for semantic checks."""
    return " ".join(text.split())


def is_negated_caveman_match(text: str, match: re.Match[str]) -> bool:
    """Return whether a Caveman-default match is immediately negated."""
    prefix = text[max(0, match.start() - 24) : match.start()].lower()
    return bool(re.search(r"\b(?:do not|don't|never)\s+$", prefix))


def has_caveman_user_default(text: str) -> bool:
    """Detect an unnegated instruction to make Caveman user-facing default."""
    return any(
        not is_negated_caveman_match(text, match)
        for pattern in REPORTING_CAVEMAN_USER_DEFAULT_PATTERNS
        for match in pattern.finditer(text)
    )


def reporting_policy_errors(text: str) -> list[str]:
    """Return missing audience-boundary requirements from the canonical policy."""
    errors: list[str] = []
    if text.count("# Audience-Aware Reporting Policy\n") != 1:
        errors.append("reporting policy must contain exactly one canonical title")
    semantic_text = normalized_text(text)
    for fragment in REPORTING_POLICY_REQUIRED_FRAGMENTS:
        if normalized_text(fragment) not in semantic_text:
            errors.append(f"reporting policy is missing: {fragment}")
    lower_text = semantic_text.lower()
    for fragment in REPORTING_POLICY_FORBIDDEN_FRAGMENTS:
        if normalized_text(fragment).lower() in lower_text:
            errors.append(
                f"reporting policy contains legacy or contradictory language: {fragment}"
            )
    if has_caveman_user_default(semantic_text):
        errors.append("reporting policy makes Caveman the user-facing default")
    return errors


def reporting_prompt_errors(agent_id: str, text: str) -> list[str]:
    """Return missing reporting-policy pointers from one canonical agent prompt."""
    errors: list[str] = []
    if REPORTING_POLICY_POINTER not in text:
        errors.append(f"{agent_id} prompt must point to the canonical reporting policy")
    lower_text = normalized_text(text).lower()
    if "caveman" in lower_text:
        errors.append(f"{agent_id} prompt must not duplicate Caveman reporting rules")
    for fragment in REPORTING_PROMPT_DUPLICATE_FRAGMENTS:
        if fragment.lower() in lower_text:
            errors.append(
                f"{agent_id} prompt must not duplicate reporting rule: {fragment}"
            )
    if agent_id == "documenter" and "normal prose" not in text.lower():
        errors.append(
            "documenter prompt must keep user-facing documentation in normal prose"
        )
    return errors


def workflow_reporting_errors(text: str) -> list[str]:
    """Return duplicated reporting-policy rules from the workflow policy."""
    errors: list[str] = []
    semantic_text = normalized_text(text).lower()
    if REPORTING_POLICY_POINTER not in text:
        errors.append("workflow policy must point to the canonical reporting policy")
    for fragment in WORKFLOW_REPORTING_FORBIDDEN_FRAGMENTS:
        if fragment.lower() in semantic_text:
            errors.append(f"workflow policy duplicates reporting rules: {fragment}")
    return errors


def task_lane_contract_errors(text: str) -> list[str]:
    """Return failures for the sole normative Task Lanes policy table."""
    errors: list[str] = []
    if text.count("## Task Lanes\n") != 1:
        errors.append("workflow policy must contain exactly one Task Lanes section")
    for fragment in TASK_LANE_REQUIRED_FRAGMENTS:
        if fragment not in text:
            errors.append(f"workflow Task Lanes table is missing: {fragment}")
    for fragment in TASK_LANE_FORBIDDEN_FRAGMENTS:
        if fragment in text:
            errors.append(
                f"workflow Task Lanes table contains stale contradiction: {fragment}"
            )
    return errors


def planner_supervision_contract_errors(
    planner_prompt: str, orchestrator_prompt: str
) -> list[str]:
    """Return missing bounded-planning and single-planner supervision clauses."""
    errors: list[str] = []
    planner_text = " ".join(planner_prompt.split())
    orchestrator_text = " ".join(orchestrator_prompt.split())
    for fragment in PLANNER_PROMPT_REQUIRED_FRAGMENTS:
        if fragment not in planner_text:
            errors.append(
                f"planner prompt is missing bounded-discovery contract: {fragment}"
            )
    for fragment in PLANNER_PROMPT_FORBIDDEN_FRAGMENTS:
        if fragment in planner_text:
            errors.append(
                f"planner prompt contains stale unconditional mandate: {fragment}"
            )
    for fragment in ORCHESTRATOR_PROMPT_REQUIRED_FRAGMENTS:
        if fragment not in orchestrator_text:
            errors.append(
                f"orchestrator prompt is missing planner-supervision contract: {fragment}"
            )
    return errors


def task_lane_for(**inputs: Unpack[TaskLaneInputs]) -> str:
    """Classify a task according to the canonical Task Lanes table.

    This compact executable fixture mirrors the policy table for regression
    coverage; agents still apply the table to the actual user request.
    """
    if not inputs.get("change_requested", False):
        return "read-only/reporting"

    affected_paths = inputs.get("affected_paths", ())

    control_plane = any(
        path in TASK_LANE_CONTROL_PLANE_FILES
        or path.startswith(TASK_LANE_CONTROL_PLANE_PATHS)
        for path in affected_paths
    )
    generator_or_script = any(
        path.startswith("scripts/") or path.startswith("shared/scripts/")
        for path in affected_paths
    )
    high_risk = (
        control_plane
        or inputs.get("security_impact", False)
        or inputs.get("dependency_or_lockfile_impact", False)
        or inputs.get("migration", False)
        or inputs.get("user_data_impact", False)
        or generator_or_script
        or len(affected_paths) > 1
    )
    if high_risk:
        return "control-plane/high-risk"
    if (
        inputs.get("explicit", False)
        and len(affected_paths) == 1
        and inputs.get("low_risk", False)
        and not inputs.get("commit_or_pr_requested", False)
    ):
        return "lightweight edit"
    return "standard implementation"


def validate_task_lane_contract(errors: list[str]) -> None:
    """Validate the authoritative policy rather than duplicating it in adapters."""
    workflow = read(REPO_ROOT / "shared" / "policies" / "workflow.instructions.md")
    errors.extend(task_lane_contract_errors(workflow))
    errors.extend(workflow_reporting_errors(workflow))


def validate_root_guidance(errors: list[str]) -> None:
    """Validate generated root guidance budgets and structural invariants."""
    for name in ROOT_GUIDANCE_BUDGETS:
        path = TARGET_ROOT / name
        if not path.exists():
            errors.append(f"missing generated root guidance: {path}")
            continue
        errors.extend(root_guidance_errors(name, read(path)))
    for workspace_name in ("workspace.instructions.md", "workspace.md"):
        workspace_path = TARGET_ROOT / ".claude" / "instructions" / workspace_name
        if not workspace_path.exists():
            errors.append(f"missing generated workspace guidance: {workspace_path}")
        else:
            errors.extend(workspace_guidance_errors(read(workspace_path)))


def scope_matches(path: str, patterns: tuple[str, ...]) -> bool:
    """Match the narrow glob subset used by target-native policy adapters."""
    for pattern in patterns:
        regex = ""
        index = 0
        while index < len(pattern):
            if pattern.startswith("**/", index):
                regex += "(?:.*/)?"
                index += 3
            elif pattern.startswith("**", index):
                regex += ".*"
                index += 2
            elif pattern[index] == "*":
                regex += "[^/]*"
                index += 1
            elif pattern[index] == "?":
                regex += "[^/]"
                index += 1
            else:
                regex += re.escape(pattern[index])
                index += 1
        if re.fullmatch(regex, path):
            return True
    return False


def claude_rule_paths(text: str) -> tuple[str, ...]:
    """Read the generated Claude ``paths`` list without another YAML parser."""
    frontmatter = extract_frontmatter(text)
    lines = frontmatter.splitlines()
    try:
        index = lines.index("paths:") + 1
    except ValueError:
        return ()
    paths: list[str] = []
    while index < len(lines) and lines[index].startswith("  - "):
        paths.append(json.loads(lines[index][4:]))
        index += 1
    return tuple(paths)


def copilot_instruction_paths(text: str) -> tuple[str, ...]:
    """Read a generated Copilot ``applyTo`` value without parsing source YAML."""
    for line in extract_frontmatter(text).splitlines():
        if line.startswith("applyTo:"):
            return tuple(json.loads(line.split(":", 1)[1].strip()).split(","))
    return ()


def requires_codex_skill_fallback(patterns: tuple[str, ...]) -> bool:
    """Return whether directory-scoped AGENTS.md would widen this policy's scope."""
    return len(patterns) != 1 or not re.fullmatch(r"[^*?]+/\*\*", patterns[0])


def validate_policy_adapters(errors: list[str]) -> None:
    """Validate canonical policy schema and equivalent native scoped adapters."""
    try:
        policies = shared_policies()
    except ValueError as error:
        errors.append(f"invalid shared policy schema: {error}")
        return

    source_names = {policy.source.name for policy in policies}
    conditional = {policy.source.name for policy in policies if policy.paths}
    check(
        len(source_names) == len(policies),
        "shared policy filenames must be unique",
        errors,
    )
    check(
        conditional == set(POLICY_SCOPE_FIXTURES),
        "every conditional policy must have matching/nonmatching scope fixtures",
        errors,
    )
    check(
        conditional == set(CODEX_POLICY_SKILL_FALLBACKS),
        "every conditional policy must declare a Codex skill fallback decision",
        errors,
    )
    reporting_policy = next(
        (
            policy
            for policy in policies
            if policy.source.name == "agent-reporting.instructions.md"
        ),
        None,
    )
    check(reporting_policy is not None, "missing canonical reporting policy", errors)
    if reporting_policy is not None:
        errors.extend(reporting_policy_errors(reporting_policy.body))

    github_root = TARGET_ROOT / ".github" / "instructions"
    rules_root = TARGET_ROOT / ".claude" / "rules"
    check(
        {path.name for path in github_root.glob("*.instructions.md")} == source_names,
        "Copilot policy adapters must uniquely mirror shared policies",
        errors,
    )
    check(
        {path.name for path in rules_root.glob("*.instructions.md")} == conditional,
        "Claude rules must exist only for conditional shared policies",
        errors,
    )

    for policy in policies:
        source_text = read(policy.source)
        canonical_path = TARGET_ROOT / ".claude" / "instructions" / policy.source.name
        github_path = github_root / policy.source.name
        rule_path = rules_root / policy.source.name
        check(
            "applyTo:" not in source_text,
            f"shared policy must not retain Copilot-native applyTo metadata: {policy.source}",
            errors,
        )
        check(
            canonical_path.exists(),
            f"missing canonical shared policy in target: {canonical_path}",
            errors,
        )
        if (
            policy.source.name == "agent-reporting.instructions.md"
            and canonical_path.exists()
        ):
            errors.extend(reporting_policy_errors(read(canonical_path)))
        check(
            github_path.exists(),
            f"missing Copilot policy adapter: {github_path}",
            errors,
        )
        if not github_path.exists():
            continue
        github_text = read(github_path)
        check(
            "applicability:" not in github_text,
            f"target-neutral policy metadata leaked into Copilot adapter: {github_path}",
            errors,
        )
        check(
            f".claude/instructions/{policy.source.name}" in github_text,
            f"Copilot policy adapter must reference canonical policy: {github_path}",
            errors,
        )
        if not policy.paths:
            check(
                not copilot_instruction_paths(github_text),
                f"always-on Copilot adapter must not emit applyTo: {github_path}",
                errors,
            )
            check(
                not rule_path.exists(),
                f"always-on policy must not consume a Claude rule: {rule_path}",
                errors,
            )
            continue

        github_paths = copilot_instruction_paths(github_text)
        check(
            github_paths == policy.paths,
            f"Copilot applyTo must derive exactly from canonical scope: {github_path}",
            errors,
        )
        check(rule_path.exists(), f"missing Claude policy rule: {rule_path}", errors)
        if not rule_path.exists():
            continue
        rule_text = read(rule_path)
        rule_paths = claude_rule_paths(rule_text)
        check(
            "applicability:" not in rule_text,
            f"target-neutral policy metadata leaked into Claude rule: {rule_path}",
            errors,
        )
        check(
            f".claude/instructions/{policy.source.name}" in rule_text,
            f"Claude rule must reference canonical policy: {rule_path}",
            errors,
        )
        check(
            rule_paths == policy.paths,
            f"Claude paths must derive exactly from canonical scope: {rule_path}",
            errors,
        )
        for path, expected_match in POLICY_SCOPE_FIXTURES[policy.source.name]:
            check(
                scope_matches(path, policy.paths) == expected_match,
                f"canonical scope has wrong matching semantics for {policy.source}: {path}",
                errors,
            )
            check(
                scope_matches(path, github_paths) == expected_match,
                f"Copilot scope parity failed for {github_path}: {path}",
                errors,
            )
            check(
                scope_matches(path, rule_paths) == expected_match,
                f"Claude scope parity failed for {rule_path}: {path}",
                errors,
            )
        check(
            requires_codex_skill_fallback(policy.paths),
            f"Phase C Codex policy should not widen a mixed/glob scope with nested AGENTS.md: {policy.source}",
            errors,
        )
        skill_name = CODEX_POLICY_SKILL_FALLBACKS[policy.source.name]
        check(
            (TARGET_ROOT / ".claude" / "skills" / skill_name / "SKILL.md").exists(),
            f"Codex scoped-policy fallback skill is missing: {skill_name}",
            errors,
        )

    nested_agents = [
        path
        for path in TARGET_ROOT.rglob("AGENTS.md")
        if path != TARGET_ROOT / "AGENTS.md"
    ]
    check(
        not nested_agents,
        "Codex must not generate unsafe nested AGENTS.md for mixed/glob policy scopes",
        errors,
    )
    check(
        not (TARGET_ROOT / ".codex" / "rules").exists(),
        "Codex target must not generate .codex/rules for policy scopes",
        errors,
    )


def check_codex_hook_trust_notice(
    label: str,
    stdout: str,
    errors: list[str],
    *,
    dry_run: bool,
) -> None:
    """Validate the installer's non-authoritative Codex trust guidance."""
    expected_action = "would install or update" if dry_run else "installed or updated"
    for fragment in (
        expected_action,
        ".codex/hooks.json",
        "Codex for VS Code",
        "content/hash",
        "review/retrust",
        "reopen/reload",
        "review and approve the project hooks when prompted",
        "does not approve project hooks or change user trust settings",
    ):
        check(
            fragment in stdout,
            f"{label} trust notice must include {fragment!r}",
            errors,
        )
    if dry_run:
        check(
            "installed or updated .codex/hooks.json" not in stdout,
            f"{label} dry-run trust notice must not claim hook content changed",
            errors,
        )


def check_batch_dry_run_summary(stdout: str, errors: list[str]) -> None:
    """Validate that a batch dry run is explicitly non-mutating."""
    for fragment in (
        "=== Previewing ",
        "=== Preview complete:",
        "no files updated",
        "Preview complete; no projects were updated.",
    ):
        check(
            fragment in stdout,
            f"updater dry-run summary must include {fragment!r}",
            errors,
        )
    for forbidden in ("=== Updating ", "=== Done:", "All projects updated."):
        check(
            forbidden not in stdout,
            f"updater dry-run summary must not claim {forbidden!r}",
            errors,
        )


def codex_hook_command(script: str, *args: str) -> str:
    """Return the generated repo-rooted Codex hook command."""
    root_expr = "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
    parts = [
        f'REPO_ROOT="{root_expr}"',
        '"$REPO_ROOT/.claude/hooks/scripts/run-hook.sh"',
        script,
        *args,
    ]
    return "; ".join(parts[:2]) + " " + " ".join(parts[2:])


def claude_hook_command(script: str, *args: str) -> str:
    """Return the generated Claude repo-rooted hook command."""
    root_expr = (
        "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
    )
    parts = [
        f'REPO_ROOT="{root_expr}"',
        '"$REPO_ROOT/.claude/hooks/scripts/run-hook.sh"',
        script,
        *args,
    ]
    return "; ".join(parts[:2]) + " " + " ".join(parts[2:])


CLAUDE_EXPECTED_EVENTS = {
    "SessionStart",
    "PreToolUse",
    "PostToolUse",
    "PreCompact",
    "Stop",
    "UserPromptSubmit",
    "StopFailure",
    "SessionEnd",
}
CLAUDE_LIFECYCLE_HOOKS = {
    "Stop": ("claude-stop.sh", (), 180),
    "UserPromptSubmit": ("state-sync.sh", ("push",), 60),
    "StopFailure": ("state-sync.sh", ("checkpoint",), 10),
    "SessionEnd": ("state-sync.sh", ("push",), 60),
}


def pretool_routing_errors(hooks: object, target: str) -> list[str]:
    """Return errors for the deterministic mutation/observer hook split."""
    native_matcher = "Edit|MultiEdit|Write" if target == "claude-code" else "Edit|Write"
    errors: list[str] = []
    if not isinstance(hooks, dict) or not isinstance(hooks.get("PreToolUse"), list):
        return [f"{target} PreToolUse routing is missing"]
    groups = hooks["PreToolUse"]
    expected: dict[str, tuple[str, ...]] = {
        native_matcher: ("protect-files.sh",),
        "Bash": ("pretool-bash-guard.sh",),
        "*": ("context-mode-dispatch.sh",),
    }
    if len(groups) != len(expected):
        errors.append(f"{target} PreToolUse must have exactly three routing groups")
    found: dict[str, tuple[str, ...]] = {}
    for group in groups:
        if not isinstance(group, dict):
            errors.append(f"{target} PreToolUse group must be an object")
            continue
        matcher = group.get("matcher")
        handlers = group.get("hooks")
        if not isinstance(matcher, str) or not isinstance(handlers, list):
            errors.append(f"{target} PreToolUse group must have matcher and hooks")
            continue
        commands: tuple[str, ...] = tuple(
            next(
                (
                    script
                    for script in (
                        *expected[native_matcher],
                        "pretool-bash-guard.sh",
                        "context-mode-dispatch.sh",
                    )
                    if script in str(handler.get("command", ""))
                ),
                "",
            )
            for handler in handlers
            if isinstance(handler, dict)
        )
        found[matcher] = commands
    for matcher, scripts in expected.items():
        if found.get(matcher) != scripts:
            errors.append(
                f"{target} PreToolUse {matcher!r} must contain only {scripts}"
            )
    for matcher, scripts in found.items():
        if matcher == "*" and any(
            script != "context-mode-dispatch.sh" for script in scripts
        ):
            errors.append(
                f"{target} wildcard PreToolUse group must be observability only"
            )
        if matcher != "Bash" and "pretool-bash-guard.sh" in scripts:
            errors.append(f"{target} Bash safety wrapper must not run for {matcher!r}")
    return errors


def validate_claude_lifecycle_hooks(hooks: object, errors: list[str]) -> None:
    """Validate the generated Claude lifecycle command-handler contract."""
    check(isinstance(hooks, dict), "Claude settings hooks must be an object", errors)
    if not isinstance(hooks, dict):
        return
    check(
        set(hooks) == CLAUDE_EXPECTED_EVENTS,
        "Claude hooks must use only the supported generated lifecycle events",
        errors,
    )
    for event_name, (script, args, timeout) in CLAUDE_LIFECYCLE_HOOKS.items():
        groups = hooks.get(event_name)
        check(
            isinstance(groups, list) and len(groups) == 1,
            f"Claude {event_name} must have exactly one handler group",
            errors,
        )
        if (
            not isinstance(groups, list)
            or len(groups) != 1
            or not isinstance(groups[0], dict)
        ):
            continue
        group = groups[0]
        check(
            set(group) == {"hooks"},
            f"Claude {event_name} group must not use unsupported fields",
            errors,
        )
        handlers = group.get("hooks")
        check(
            isinstance(handlers, list) and len(handlers) == 1,
            f"Claude {event_name} must have exactly one command handler",
            errors,
        )
        if (
            not isinstance(handlers, list)
            or len(handlers) != 1
            or not isinstance(handlers[0], dict)
        ):
            continue
        handler = handlers[0]
        check(
            set(handler) == {"type", "command", "timeout"},
            f"Claude {event_name} handler must not use unsupported fields",
            errors,
        )
        check(
            handler.get("type") == "command",
            f"Claude {event_name} handler must be a command",
            errors,
        )
        check(
            handler.get("command") == claude_hook_command(script, *args),
            f"Claude {event_name} must invoke {script} with the expected operation",
            errors,
        )
        check(
            handler.get("timeout") == timeout,
            f"Claude {event_name} timeout must be exactly {timeout}",
            errors,
        )


def validate_codex_model_contract(
    label: str,
    model: object,
    effort: object,
    errors: list[str],
    *,
    expected_model: object | None = None,
    expected_effort: object | None = None,
) -> None:
    model_valid = isinstance(model, str) and bool(model)
    effort_valid = isinstance(effort, str) and bool(effort)
    check(model_valid, f"{label} must set an explicit Codex model", errors)
    check(effort_valid, f"{label} must set an explicit Codex reasoning effort", errors)
    if model_valid:
        check(
            model in CODEX_ALLOWED_AGENT_MODELS,
            f"{label} has unsupported Codex model '{model}'",
            errors,
        )
    if effort_valid:
        check(
            effort in CODEX_ALLOWED_EFFORT,
            f"{label} has unsupported Codex reasoning effort '{effort}'",
            errors,
        )
    if expected_model is not None:
        check(
            model == expected_model,
            f"{label} model drift: expected '{expected_model}', got '{model}'",
            errors,
        )
    if expected_effort is not None:
        check(
            effort == expected_effort,
            f"{label} effort drift: expected '{expected_effort}', got '{effort}'",
            errors,
        )


def validate_codex_model_contract_cases(errors: list[str]) -> None:
    valid_errors: list[str] = []
    validate_codex_model_contract(
        "valid fixture",
        "gpt-5.6-sol",
        "max",
        valid_errors,
        expected_model="gpt-5.6-sol",
        expected_effort="max",
    )
    check(
        not valid_errors,
        f"valid Codex model contract was rejected: {valid_errors}",
        errors,
    )

    invalid_cases = (
        ("unsupported model", "gpt-5.7-sol", "high", "gpt-5.7-sol", "high"),
        ("unsupported effort", "gpt-5.6-sol", "ultra", "gpt-5.6-sol", "ultra"),
        ("missing model", None, "high", None, "high"),
        ("missing effort", "gpt-5.6-sol", None, "gpt-5.6-sol", None),
        ("generated drift", "gpt-5.6-terra", "high", "gpt-5.6-sol", "high"),
    )
    for label, model, effort, expected_model, expected_effort in invalid_cases:
        case_errors: list[str] = []
        validate_codex_model_contract(
            label,
            model,
            effort,
            case_errors,
            expected_model=expected_model,
            expected_effort=expected_effort,
        )
        check(
            bool(case_errors),
            f"adversarial Codex model case was not rejected: {label}",
            errors,
        )


def codex_config_contract_errors(
    config: dict[str, object], label: str, *, require_agent_settings: bool = True
) -> list[str]:
    """Return structural errors for a Codex multi-agent configuration."""
    errors: list[str] = []
    agents = config.get("agents")
    if require_agent_settings:
        check(isinstance(agents, dict), f"{label} missing agents section", errors)
    if require_agent_settings and isinstance(agents, dict):
        check(
            "max_threads" not in agents,
            f"{label} must not use legacy agents.max_threads",
            errors,
        )
        check(
            agents.get("max_concurrent_threads_per_session") == 6,
            f"{label} must set agents.max_concurrent_threads_per_session = 6",
            errors,
        )
        check(
            agents.get("max_depth") == 1,
            f"{label} must retain agents.max_depth = 1 pending native routing probes",
            errors,
        )
        check(
            "enabled" not in agents,
            f"{label} must not restate agents.enabled = true (the documented default)",
            errors,
        )
    check(
        "model" not in config,
        f"{label} must not pin root model",
        errors,
    )
    check(
        "model_reasoning_effort" not in config,
        f"{label} must not pin root model_reasoning_effort",
        errors,
    )
    features = config.get("features")
    multi_agent_v2 = (
        features.get("multi_agent_v2") if isinstance(features, dict) else None
    )
    check(
        isinstance(multi_agent_v2, dict),
        f"{label} must define the MultiAgent V2 routing table",
        errors,
    )
    if isinstance(multi_agent_v2, dict):
        check(
            multi_agent_v2.get("hide_spawn_agent_metadata") is False,
            f"{label} must expose MultiAgent V2 spawn metadata",
            errors,
        )
        check(
            multi_agent_v2.get("tool_namespace") == "agents",
            f"{label} must route MultiAgent V2 tools through the agents namespace",
            errors,
        )
    return errors


def count_skills(root: Path) -> int:
    return len(list(root.glob("*/SKILL.md")))


def target_support_root(target: str) -> Path:
    if target not in TARGETS:
        raise ValueError(f"unknown target: {target}")
    return TARGET_ROOT / ".claude"


def compare_dirs(left: Path, right: Path, errors: list[str]) -> None:
    comparison = filecmp.dircmp(left, right)
    if comparison.left_only or comparison.right_only or comparison.funny_files:
        errors.append(
            "generated dist is not deterministic; rerun scripts/generate_targets.py --all"
        )
        return
    # Compare file contents (shallow=False), not just stat signatures, so a
    # byte-level nondeterminism is caught even when size/mtime happen to match.
    _, mismatch, errored = filecmp.cmpfiles(
        left, right, comparison.common_files, shallow=False
    )
    if mismatch or errored:
        errors.append(
            "generated dist is not deterministic; rerun scripts/generate_targets.py --all"
        )
        return
    for name in comparison.common_dirs:
        compare_dirs(left / name, right / name, errors)


def dirs_match(left: Path, right: Path) -> bool:
    """Return whether two directory trees contain the same files and bytes."""
    if not left.is_dir() or not right.is_dir():
        return False
    comparison = filecmp.dircmp(left, right)
    if comparison.left_only or comparison.right_only or comparison.funny_files:
        return False
    _, mismatch, errored = filecmp.cmpfiles(
        left, right, comparison.common_files, shallow=False
    )
    return (
        not mismatch
        and not errored
        and all(
            dirs_match(left / name, right / name) for name in comparison.common_dirs
        )
    )


def root_source_mirror_errors(repo_root: Path, target_root: Path) -> list[str]:
    """Reject legacy source mirrors while allowing exact ignored overlays."""
    errors: list[str] = []
    for relative_path in OBSOLETE_ROOT_SOURCE_DIRS:
        overlay = repo_root / relative_path
        if not overlay.exists():
            continue
        tracked = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "--", relative_path],
            text=True,
            capture_output=True,
            check=False,
        )
        if tracked.stdout.strip():
            errors.append(
                f"root .github must not keep tracked legacy source mirror: {relative_path}"
            )
            continue
        ignored = subprocess.run(
            ["git", "-C", str(repo_root), "check-ignore", "-q", "--", relative_path],
            check=False,
        )
        if ignored.returncode != 0:
            errors.append(
                f"root .github legacy source mirror must be ignored: {relative_path}"
            )
            continue
        if not dirs_match(overlay, target_root / relative_path):
            errors.append(
                f"root .github ignored self-install overlay is stale: {relative_path}"
            )
    return errors


def codex_agent_instruction_errors(
    agent: dict[str, object], instructions: str
) -> list[str]:
    """Return self-containment contract errors for one parsed Codex agent body."""
    expected_prefix = (
        f"{codex_agent_metadata_header(agent)}\n\n"
        f"{CODEX_AGENT_INSTRUCTIONS_DELIMITER}\n\n"
    )
    expected_prompt = codex_agent_prompt_body(agent)
    errors: list[str] = []
    if not instructions.startswith(expected_prefix):
        errors.append("must use the generated metadata header and stable delimiter")
    if instructions.count(CODEX_AGENT_INSTRUCTIONS_DELIMITER) != 1:
        errors.append("must contain exactly one stable prompt delimiter")
    prompt_base = agent.get("prompt_base")
    if isinstance(prompt_base, str):
        supplement_delimiter = CODEX_ROLE_SUPPLEMENT_DELIMITER.format(
            agent_id=agent["id"]
        )
        if instructions.count(supplement_delimiter) != 1:
            errors.append("must contain exactly one derived role-supplement delimiter")
    elif "--- Codex role supplement:" in instructions:
        errors.append("must not contain a derived role-supplement delimiter")
    if instructions.removeprefix(expected_prefix) != expected_prompt:
        errors.append("body must exactly match its transformed shared prompt")
    if "Before doing the task, read `.claude/agents/" in instructions:
        errors.append("must not retain the legacy Claude-native runtime read")
    return errors


def agent_membership_errors(
    target: str, expected_agent_ids: set[str], generated_agent_ids: set[str]
) -> list[str]:
    """Return target-scoped omissions and leaks in generated agent files."""
    missing = sorted(expected_agent_ids - generated_agent_ids)
    unexpected = sorted(generated_agent_ids - expected_agent_ids)
    errors: list[str] = []
    if missing:
        errors.append(f"{target} missing eligible agents: {missing}")
    if unexpected:
        errors.append(f"{target} contains ineligible agents: {unexpected}")
    return errors


def validate_agents(errors: list[str]) -> None:
    try:
        canonical_agents = shared_agents()
    except ValueError as error:
        errors.append(str(error))
        return
    planner_prompt = read(REPO_ROOT / "shared" / "agents" / "planner" / "prompt.md")
    errors.extend(
        planner_supervision_contract_errors(
            planner_prompt,
            read(REPO_ROOT / "shared" / "agents" / "orchestrator" / "prompt.md"),
        )
    )
    for prompt_path in sorted((REPO_ROOT / "shared" / "agents").glob("*/prompt.md")):
        errors.extend(
            reporting_prompt_errors(prompt_path.parent.name, read(prompt_path))
        )
    check(
        canonical_agents,
        "no shared agents found under shared/agents/",
        errors,
    )
    expected_codex_intents: dict[str, tuple[object, object]] = {}
    expected_claude_intents: dict[str, tuple[object, object]] = {}
    expected_github_models: dict[str, object] = {}
    codex_escalations: dict[str, object] = {}
    agents_by_id = {agent["id"]: agent for agent, _agent_dir in canonical_agents}
    agent_dirs_by_id = {agent["id"]: agent_dir for agent, agent_dir in canonical_agents}

    for data, agent_dir in canonical_agents:
        agent_id = data["id"]
        if "github-copilot" in data["targets"]:
            expected_github_models[agent_id] = data["model_intent"]["github-copilot"]
        claude_intent = data["model_intent"].get("claude-code")
        if isinstance(claude_intent, dict):
            expected_claude_intents[agent_id] = (
                claude_intent.get("model"),
                claude_intent.get("effort"),
            )
        codex_intent = data["model_intent"].get("openai-codex")
        if isinstance(codex_intent, dict):
            model = codex_intent.get("model")
            effort = codex_intent.get("effort")
            validate_codex_model_contract(
                f"canonical Codex agent {agent_id}", model, effort, errors
            )
            expected_codex_intents[agent_id] = (model, effort)
            escalate_to = codex_intent.get("escalate_to")
            if escalate_to is not None:
                check(
                    isinstance(escalate_to, str),
                    f"{agent_id} escalate_to must name an agent ID",
                    errors,
                )
                codex_escalations[agent_id] = escalate_to
        if "prompt_base" in data:
            check(
                not (agent_dir / "prompt.md").exists(),
                f"{agent_id} derived prompt must not copy canonical prompt.md",
                errors,
            )
            check(
                (agent_dir / "prompt.openai-codex.md").exists(),
                f"{agent_id} derived prompt missing Codex supplement",
                errors,
            )
        else:
            check(
                (agent_dir / "prompt.md").exists(),
                f"{agent_id} missing canonical prompt.md",
                errors,
            )
        check(
            not (agent_dir / "targets").exists(),
            f"{agent_id} must not keep target-specific prompt forks",
            errors,
        )
        capabilities = set(data.get("capabilities", []))
        if agent_id == "orchestrator":
            # R-AGENTS-01: the orchestrator's prompt mandates branch/commit/PR
            # and memory/session-log writes, so its toolset must actually grant
            # delegation, editing, and execution.
            missing = {"delegate", "edit", "execute"} - capabilities
            check(
                not missing,
                f"orchestrator capabilities must cover its prompt-declared actions; missing {sorted(missing)}",
                errors,
            )

    check(
        expected_codex_intents == CODEX_AGENT_MODEL_INTENTS,
        "canonical Codex model/effort mappings drifted from the eight-agent contract",
        errors,
    )
    check(
        codex_escalations == CODEX_ESCALATION_CHAIN,
        "canonical Codex escalation contract must be luna_coder -> coder -> sol_coder",
        errors,
    )
    expected_agent_ids = {
        target: {agent["id"] for agent, _agent_dir in shared_agents(target)}
        for target in SUPPORTED_AGENT_TARGETS
    }
    universal_agent_ids = set(CODEX_ROLE_MODEL_INTENTS)
    check(
        expected_agent_ids["github-copilot"] == universal_agent_ids,
        "GitHub Copilot must retain exactly the six universal agents",
        errors,
    )
    check(
        expected_agent_ids["claude-code"] == universal_agent_ids,
        "Claude Code must retain exactly the six universal agents",
        errors,
    )
    check(
        expected_agent_ids["openai-codex"] == set(CODEX_AGENT_MODEL_INTENTS),
        "Codex must contain exactly six universal agents plus luna_coder and sol_coder",
        errors,
    )

    generated_github_agents = sorted(
        (TARGET_ROOT / ".github" / "agents").glob("*.agent.md")
    )
    errors.extend(
        agent_membership_errors(
            "github-copilot",
            expected_agent_ids["github-copilot"],
            {path.name.removesuffix(".agent.md") for path in generated_github_agents},
        )
    )
    for agent_id in expected_agent_ids["github-copilot"]:
        generated = TARGET_ROOT / ".github" / "agents" / f"{agent_id}.agent.md"
        check(generated.exists(), f"missing generated GitHub agent: {agent_id}", errors)
        if generated.exists():
            text = read(generated)
            agent = agents_by_id[agent_id]
            if "claude-code" not in agent["targets"]:
                prompt = transform_agent_text(
                    read(agent_dirs_by_id[agent_id] / "prompt.md"), "github-copilot"
                ).strip()
                check(
                    ".claude/agents/" not in text
                    and "This file is self-contained" in text
                    and prompt in text,
                    f"GitHub-only agent must be self-contained: {generated}",
                    errors,
                )
            else:
                check(
                    ".claude/agents/" in text,
                    f"GitHub agent adapter must point at canonical .claude agent: {generated}",
                    errors,
                )
                for reference in re.findall(r"`(\.claude/agents/[^`]+\.md)`", text):
                    check(
                        (TARGET_ROOT / reference).exists(),
                        f"GitHub agent adapter points at missing canonical agent: {generated}: {reference}",
                        errors,
                    )
                check(
                    "This file is the GitHub Copilot native adapter" in text,
                    f"GitHub agent should be a thin native adapter: {generated}",
                    errors,
                )

    claude_agents = sorted((TARGET_ROOT / ".claude" / "agents").glob("*.md"))
    errors.extend(
        agent_membership_errors(
            "claude-code",
            expected_agent_ids["claude-code"],
            {path.stem for path in claude_agents},
        )
    )
    for path in claude_agents:
        text = read(path)
        check(
            text.startswith("---\n"),
            f"Claude agent missing frontmatter: {path}",
            errors,
        )
        check(
            "\nname: " in text and "\ndescription: " in text,
            f"Claude agent missing required fields: {path}",
            errors,
        )
        check(
            "tool-routing.instructions.md" in text,
            f"Claude agent must route retrieval through tool-routing instructions: {path}",
            errors,
        )
        # An agent told to route through tool-routing.instructions.md (which
        # names Semble and Context Mode) but whose own tools: allowlist
        # omits the matching mcp__ wildcard physically cannot follow that
        # instruction — tools: is an explicit allowlist, not additive to
        # defaults. Caught this exact bug once already (every generated
        # subagent had the instruction but not the tool); guard against it
        # regenerating.
        if "tool-routing.instructions.md" in text:
            tools_line = next(
                (line for line in text.splitlines() if line.startswith("tools:")), ""
            )
            check(
                "mcp__semble" in tools_line and "mcp__context-mode" in tools_line,
                f"Claude agent must allow both Semble and Context Mode MCP: {path}",
                errors,
            )
        # Per-agent model/effort tiering: validate any emitted frontmatter fields
        # against the allow-lists, and reject effort on models that lack it.
        frontmatter_block = text.split("---\n", 2)
        frontmatter_text = frontmatter_block[1] if len(frontmatter_block) >= 3 else ""
        model_value = effort_value = None
        for line in frontmatter_text.splitlines():
            if line.startswith("model:"):
                model_value = line.split(":", 1)[1].strip()
            elif line.startswith("effort:"):
                effort_value = line.split(":", 1)[1].strip()
        if model_value is not None:
            check(
                model_value in CLAUDE_ALLOWED_AGENT_MODELS,
                f"Claude agent has unsupported model '{model_value}': {path}",
                errors,
            )
        if effort_value is not None:
            check(
                effort_value in CLAUDE_ALLOWED_EFFORT,
                f"Claude agent has unsupported effort '{effort_value}': {path}",
                errors,
            )
            check(
                model_value not in CLAUDE_NO_EFFORT_MODELS,
                f"Claude agent model '{model_value}' does not support effort but sets '{effort_value}': {path}",
                errors,
            )
        expected_model, expected_effort = expected_claude_intents.get(
            path.stem, ("inherit", "inherit")
        )
        check(
            model_value == (None if expected_model == "inherit" else expected_model),
            f"generated Claude agent {path.stem} model drifted from canonical intent",
            errors,
        )
        check(
            effort_value == (None if expected_effort == "inherit" else expected_effort),
            f"generated Claude agent {path.stem} effort drifted from canonical intent",
            errors,
        )
        errors.extend(
            f"generated Claude {error}: {path}"
            for error in reporting_prompt_errors(path.stem, text)
        )

    codex_agents = sorted((TARGET_ROOT / ".codex" / "agents").glob("*.toml"))
    errors.extend(
        agent_membership_errors(
            "openai-codex",
            expected_agent_ids["openai-codex"],
            {path.stem for path in codex_agents},
        )
    )
    check(
        not (TARGET_ROOT / ".codex" / "rules").exists(),
        "Codex target must not generate deprecated .codex/rules output",
        errors,
    )

    expected_codex_names = expected_agent_ids["openai-codex"]
    check(
        {path.stem for path in codex_agents} == expected_codex_names,
        "Codex custom agent filenames must match mapped shared agent names",
        errors,
    )

    for path in codex_agents:
        text = read(path)
        try:
            data = read_toml(path)
        except tomllib.TOMLDecodeError as error:
            errors.append(f"invalid Codex custom agent TOML: {path}: {error}")
            continue
        for field in ("name", "description", "developer_instructions"):
            check(
                isinstance(data.get(field), str) and bool(data.get(field)),
                f"Codex agent missing required field {field}: {path}",
                errors,
            )
        check(
            data.get("name") == path.stem,
            f"Codex agent name must match filename stem: {path}",
            errors,
        )
        expected_model, expected_effort = expected_codex_intents.get(
            path.stem, (None, None)
        )
        validate_codex_model_contract(
            f"generated Codex agent {path.stem}",
            data.get("model"),
            data.get("model_reasoning_effort"),
            errors,
            expected_model=expected_model,
            expected_effort=expected_effort,
        )
        instructions = str(data.get("developer_instructions", ""))
        agent = agents_by_id.get(path.stem)
        if agent is None:
            continue
        errors.extend(
            f"Codex agent {error}: {path}"
            for error in codex_agent_instruction_errors(agent, instructions)
        )
        errors.extend(
            f"generated Codex {error}: {path}"
            for error in reporting_prompt_errors(path.stem, instructions)
        )
        if "tool-routing.instructions.md" in instructions:
            check(
                "[mcp_servers." not in text,
                f"Codex agent must inherit MCP servers from config, not duplicate them: {path}",
                errors,
            )
            codex_config = read_toml(TARGET_ROOT / ".codex" / "config.toml")
            mcp_servers = codex_config.get("mcp_servers", {})
            check(
                isinstance(mcp_servers, dict)
                and "semble" in mcp_servers
                and "context-mode" in mcp_servers,
                f"Codex agent requires both Semble and Context Mode MCP from inherited config: {path}",
                errors,
            )
    for root in (TARGET_ROOT / ".claude" / "agents", TARGET_ROOT / ".codex" / "agents"):
        for path in text_files(root):
            text = read(path)
            for label in NON_COPILOT_REVIEW_LABEL_LEAKS:
                check(
                    label not in text,
                    f"non-Copilot review helper label leaked into {path}: {label}",
                    errors,
                )

    claude_planner = read(TARGET_ROOT / ".claude" / "agents" / "planner.md")
    claude_orchestrator = read(TARGET_ROOT / ".claude" / "agents" / "orchestrator.md")
    errors.extend(
        f"generated Claude {error}"
        for error in planner_supervision_contract_errors(
            claude_planner, claude_orchestrator
        )
    )
    codex_planner = str(
        read_toml(TARGET_ROOT / ".codex" / "agents" / "planner.toml").get(
            "developer_instructions", ""
        )
    )
    codex_orchestrator = str(
        read_toml(TARGET_ROOT / ".codex" / "agents" / "orchestrator.toml").get(
            "developer_instructions", ""
        )
    )
    errors.extend(
        f"generated Codex {error}"
        for error in planner_supervision_contract_errors(
            codex_planner, codex_orchestrator
        )
    )

    # R-AGENTS-06: control-plane guards must use consumer paths; the authoring
    # repo's shared/ and dist/ must not leak into generated agent bodies.
    for path in sorted((TARGET_ROOT / ".claude" / "agents").glob("*.md")):
        text = read(path)
        for authoring_path in ("shared/", "dist/"):
            check(
                authoring_path not in text,
                f"generated agent must not reference authoring-repo path '{authoring_path}': {path}",
                errors,
            )
        # R-AGENTS-07: the documenter must diff against the plan's originating
        # branch (dev), never main.
        check(
            "main...HEAD" not in text,
            f"generated agent must not diff against main...HEAD (use originating_branch/dev): {path}",
            errors,
        )
        # R-AGENTS-08: the verifier is the single owner of the persisted score
        # report; only it writes the report (`--json --out`).
        if "--json --out" in text:
            check(
                path.stem == "verifier",
                f"only the verifier may write a persisted score report (--json --out): {path}",
                errors,
            )

    validate_github_agent_models(errors, expected_github_models)


def github_agent_model_errors(
    text: str, expected_model: object, path: Path
) -> list[str]:
    """Return GitHub custom-agent frontmatter model contract failures."""
    errors: list[str] = []
    if not text.startswith("---\n"):
        return [f"GitHub agent missing frontmatter: {path}"]
    parts = text.split("---\n", 2)
    if len(parts) != 3:
        return [f"GitHub agent frontmatter is malformed: {path}"]
    frontmatter_lines = parts[1].splitlines()
    model_lines = [
        line.split(":", 1)[1].strip()
        for line in frontmatter_lines
        if line.startswith("model:")
    ]
    for index, line in enumerate(frontmatter_lines):
        if not line.startswith("model:"):
            continue
        value = line.split(":", 1)[1].strip()
        if not value:
            errors.append(
                f"GitHub agent model must be a single string, not a YAML list: {path}"
            )
            continue
        if value not in GITHUB_ALLOWED_AGENT_MODELS:
            errors.append(
                f"GitHub agent model is not a current supported Copilot model string: {path}: {value}"
            )
        if "(copilot)" in value:
            errors.append(
                f"GitHub agent model must not include provider suffix: {path}"
            )
        if index + 1 < len(frontmatter_lines) and frontmatter_lines[
            index + 1
        ].lstrip().startswith("- "):
            errors.append(f"GitHub agent model must not be a YAML sequence: {path}")
    expected = expected_model if isinstance(expected_model, str) else "target-default"
    if expected == "target-default":
        if model_lines:
            errors.append(f"generated GitHub agent must inherit its model: {path}")
    elif model_lines != [expected]:
        errors.append(
            f"generated GitHub agent model drifted from canonical intent: {path}"
        )
    return errors


def validate_github_agent_models(
    errors: list[str], expected_models: dict[str, object]
) -> None:
    agent_root = TARGET_ROOT / ".github" / "agents"
    for path in sorted(agent_root.glob("*.agent.md")):
        text = read(path)
        errors.extend(
            github_agent_model_errors(
                text, expected_models.get(path.name.removesuffix(".agent.md")), path
            )
        )


def validate_model_leaks(errors: list[str]) -> None:
    non_github_roots = (
        TARGET_ROOT / "CLAUDE.md",
        TARGET_ROOT / "AGENTS.md",
        TARGET_ROOT / ".claude",
        TARGET_ROOT / ".codex",
    )
    for root in non_github_roots:
        paths = [root] if root.is_file() else text_files(root)
        for path in paths:
            text = read(path)
            for pin in COPILOT_MODEL_PINS:
                if pin in text:
                    errors.append(
                        f"Copilot model pin leaked into non-GitHub output: {path} contains {pin}"
                    )


# Every generated target must carry the identical Semble, Context7, and
# Context Mode MCP server entries from shared/mcp/servers.json. Iterating this
# tuple per server (rather than one combined boolean) is what lets a single
# server's drift or absence fail independently of the others.
MCP_PARITY_SERVERS = ("semble", "context7", "context-mode")


def mcp_server_parity_errors(
    servers: dict[str, object],
    shared_mcp: dict[str, object],
    label: str,
    server_names: tuple[str, ...] = MCP_PARITY_SERVERS,
) -> list[str]:
    """Return one failure per drifted/missing MCP server, never a combined check."""
    errors: list[str] = []
    for server in server_names:
        if server not in servers:
            errors.append(f"{label} missing MCP server: {server}")
            continue
        if servers.get(server) != shared_mcp.get(server):
            errors.append(f"{label} MCP server drifted from shared source: {server}")
    return errors


def validate_mcp_and_hooks(errors: list[str]) -> None:
    github_mcp = json.loads(read(TARGET_ROOT / ".vscode" / "mcp.json"))
    claude_mcp = json.loads(read(TARGET_ROOT / ".mcp.json"))
    shared_mcp = json.loads(read(REPO_ROOT / "shared" / "mcp" / "servers.json"))[
        "servers"
    ]
    check(
        shared_mcp.get("context-mode")
        == {
            "command": "bash",
            "args": [
                "-c",
                'REPO_ROOT="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"; exec "$REPO_ROOT/.claude/hooks/scripts/context-mode-dispatch.sh" server',
            ],
        },
        "shared Context Mode MCP server must route through an absolute-REPO_ROOT dispatcher server command, not a bare workspace-relative path",
        errors,
    )
    context_dispatcher = read(
        REPO_ROOT / "shared" / "hooks" / "scripts" / "context-mode-dispatch.sh"
    )
    check(
        'openai-codex) CONTEXT_MODE_TARGET="codex"' in context_dispatcher,
        "Context Mode dispatcher must map OpenAI Codex hooks to upstream target id 'codex'",
        errors,
    )
    check(
        f'PINNED_CONTEXT_MODE_VERSION="{CONTEXT_MODE_PINNED_VERSION}"'
        in context_dispatcher,
        f"Context Mode dispatcher must pin version {CONTEXT_MODE_PINNED_VERSION}",
        errors,
    )
    check(
        '"$MODE" == "server"' in context_dispatcher,
        "Context Mode dispatcher must support the MCP server route",
        errors,
    )
    for servers, label in (
        (github_mcp.get("servers", {}), "github"),
        (claude_mcp.get("mcpServers", {}), "claude"),
    ):
        errors.extend(mcp_server_parity_errors(servers, shared_mcp, label))
    check(
        "servers" not in claude_mcp,
        "Claude .mcp.json must use mcpServers, not servers",
        errors,
    )

    codex_config = read(TARGET_ROOT / ".codex" / "config.toml")
    codex_config_data: dict[str, object] = {}
    try:
        codex_config_data = read_toml(TARGET_ROOT / ".codex" / "config.toml")
    except tomllib.TOMLDecodeError as error:
        errors.append(f"invalid Codex config TOML: {error}")
    # R-CODEX-01: hooks are on by default in current Codex; the flat [features]
    # block is redundant. The nested MultiAgent V2 table is required because
    # Codex 0.144.x otherwise hides agent_type/model/effort routing metadata.
    check(
        "[features]" not in codex_config,
        "Codex config must not emit the redundant [features] block",
        errors,
    )
    check(
        "hooks = true" not in codex_config,
        "Codex config must not restate hooks = true (on by default)",
        errors,
    )
    check(
        "codex_hooks = true" not in codex_config,
        "Codex config must not use deprecated codex_hooks alias",
        errors,
    )
    errors.extend(codex_config_contract_errors(codex_config_data, "Codex config"))
    codex_servers = codex_config_data.get("mcp_servers", {})
    if isinstance(codex_servers, dict):
        errors.extend(mcp_server_parity_errors(codex_servers, shared_mcp, "codex"))
    else:
        errors.append("Codex config mcp_servers must be a table")
    authoring_config = read_toml(REPO_ROOT / ".codex" / "config.toml")
    errors.extend(
        codex_config_contract_errors(
            authoring_config,
            "authoring Codex config",
            require_agent_settings=False,
        )
    )
    check(
        "[mcp_servers.semble]" in codex_config,
        "Codex config missing Semble MCP server",
        errors,
    )
    check(
        "[mcp_servers.context-mode]" in codex_config,
        "Codex config missing context-mode MCP server",
        errors,
    )
    check(
        "[mcp_servers.context7]" in codex_config,
        "Codex config missing context7 MCP server",
        errors,
    )
    for deny_rule in (
        "Read(./.env)",
        "Read(./.env.*)",
        "Read(./secrets/**)",
        "Read(./config/credentials.json)",
    ):
        check(
            deny_rule in read(TARGET_ROOT / ".claude" / "settings.json"),
            f"protected Context Mode deny rule missing: {deny_rule}",
            errors,
        )
    check(
        "../.claude/skills/" in codex_config,
        "Codex config must point skills at .claude/skills",
        errors,
    )
    # R-CODEX-01: skill paths point at the SKILL.md file, not the directory.
    check(
        '/SKILL.md"' in codex_config,
        "Codex skill paths must point at the SKILL.md file",
        errors,
    )

    codex_hooks = json.loads(read(TARGET_ROOT / ".codex" / "hooks.json"))
    check(
        set(codex_hooks) == {"hooks"},
        "Codex hooks.json should only contain the top-level hooks object",
        errors,
    )
    expected_codex_events = {
        "SessionStart",
        "PreToolUse",
        "PostToolUse",
        "PreCompact",
        "Stop",
        "UserPromptSubmit",
        "SessionEnd",
    }
    hooks_by_event = codex_hooks.get("hooks", {})
    check(isinstance(hooks_by_event, dict), "Codex hooks must be an object", errors)
    if isinstance(hooks_by_event, dict):
        check(
            set(hooks_by_event) == expected_codex_events,
            "Codex hooks must use only the supported generated lifecycle events",
            errors,
        )
    # R-CODEX-01: PreCompact is a documented Codex event and must be wired.
    check(
        "PreCompact" in codex_hooks.get("hooks", {}),
        "Codex hooks must wire the documented PreCompact event",
        errors,
    )
    for event_name, groups in codex_hooks.get("hooks", {}).items():
        check(
            isinstance(groups, list),
            f"Codex hook event must be a list: {event_name}",
            errors,
        )
        for group in groups if isinstance(groups, list) else []:
            check(
                isinstance(group, dict),
                f"Codex hook group must be an object: {event_name}",
                errors,
            )
            check(
                "hooks" in group and isinstance(group.get("hooks"), list),
                f"Codex hook group missing nested hooks: {event_name}",
                errors,
            )
            for hook in group.get("hooks", []) if isinstance(group, dict) else []:
                command = hook.get("command", "") if isinstance(hook, dict) else ""
                check(
                    "git rev-parse --show-toplevel" in command,
                    f"Codex repo-local hook should resolve from git root: {event_name}",
                    errors,
                )
                check(
                    ".claude/hooks/scripts/" in command,
                    f"Codex hooks should invoke shared .claude hook scripts: {event_name}",
                    errors,
                )
                if (
                    "session-log.sh" in command
                    or "protect-files.sh" in command
                    or "enforce-" in command
                    or "record-" in command
                    or "session-start-state.sh" in command
                    or "stop-session-log-check.sh" in command
                ):
                    check(
                        "openai-codex" in command,
                        f"Codex hook command should pass target id: {event_name}",
                        errors,
                    )

    expected_lifecycle_hooks = {
        "Stop": ("codex-stop.sh", (), 180),
        "UserPromptSubmit": ("state-sync.sh", ("push",), 60),
        "SessionEnd": ("state-sync.sh", ("checkpoint",), 3),
    }
    if isinstance(hooks_by_event, dict):
        for event_name, (script, args, timeout) in expected_lifecycle_hooks.items():
            groups = hooks_by_event.get(event_name)
            check(
                isinstance(groups, list) and len(groups) == 1,
                f"Codex {event_name} must have exactly one handler group",
                errors,
            )
            if (
                not isinstance(groups, list)
                or len(groups) != 1
                or not isinstance(groups[0], dict)
            ):
                continue
            group = groups[0]
            handlers = group.get("hooks")
            check(
                set(group) == {"hooks"},
                f"Codex {event_name} group must not use unsupported fields",
                errors,
            )
            check(
                isinstance(handlers, list) and len(handlers) == 1,
                f"Codex {event_name} must have exactly one command handler",
                errors,
            )
            if (
                not isinstance(handlers, list)
                or len(handlers) != 1
                or not isinstance(handlers[0], dict)
            ):
                continue
            handler = handlers[0]
            check(
                set(handler) == {"type", "command", "timeout"},
                f"Codex {event_name} handler must not use unsupported fields",
                errors,
            )
            check(
                handler.get("type") == "command",
                f"Codex {event_name} handler must be a command",
                errors,
            )
            check(
                handler.get("command") == codex_hook_command(script, *args),
                f"Codex {event_name} must invoke {script} with the expected operation",
                errors,
            )
            check(
                handler.get("timeout") == timeout,
                f"Codex {event_name} timeout must be exactly {timeout}",
                errors,
            )
        session_end = json.dumps(hooks_by_event.get("SessionEnd", {}))
        check(
            "publish" not in session_end and "push" not in session_end,
            "Codex SessionEnd must not perform a network publication",
            errors,
        )

    hook_roots = (TARGET_ROOT / ".claude" / "hooks" / "scripts",)
    for hook_root in hook_roots:
        for script in REQUIRED_HOOK_SCRIPTS:
            path = hook_root / script
            check(path.exists(), f"missing hook script: {path}", errors)
            check(
                path.exists() and bool(path.stat().st_mode & 0o111),
                f"hook script is not executable: {path}",
                errors,
            )
        for script in REQUIRED_HOOK_LIBRARIES:
            path = hook_root / script
            check(path.exists(), f"missing hook library: {path}", errors)

    # R-HOOKS-07: the deterministic commit-msg git hook lives beside the
    # PreToolUse scripts but git invokes it directly, so it needs its own
    # presence/executability assertion (generate_targets.py's ensure_executable
    # loop is what should satisfy this).
    git_hook_root = TARGET_ROOT / ".claude" / "hooks" / "git-hooks"
    for script in REQUIRED_GIT_HOOKS:
        path = git_hook_root / script
        check(path.exists(), f"missing git hook: {path}", errors)
        check(
            path.exists() and bool(path.stat().st_mode & 0o111),
            f"git hook is not executable: {path}",
            errors,
        )

    # R-SYNC (durable checkpoint): the post-commit hook is the reliable
    # commit-time AI-state sync that does not depend on a Codex Stop event
    # (browser/editor tab closure never guarantees Stop). It best-effort pushes
    # via state-sync.sh after every successful commit. Presence/executability is
    # already asserted by the REQUIRED_GIT_HOOKS loop above; guard the read so a
    # missing file yields that clean failure instead of an uncaught exception.
    post_commit = git_hook_root / "post-commit"
    if post_commit.exists():
        post_commit_text = read(post_commit)
        check(
            '"$STATE_SYNC" push' in post_commit_text,
            "post-commit git hook must push AI state via state-sync.sh",
            errors,
        )

    # Both installed state-sync.sh copies come from one shared/ source and must
    # stay byte-identical: the .devcontainer/ copy bootstraps before .claude/
    # exists, and the .claude/hooks/scripts/ copy runs afterward.
    state_sync_claude = TARGET_ROOT / ".claude" / "hooks" / "scripts" / "state-sync.sh"
    state_sync_devcontainer = TARGET_ROOT / ".devcontainer" / "state-sync.sh"
    check(
        state_sync_claude.exists()
        and state_sync_devcontainer.exists()
        and state_sync_claude.read_bytes() == state_sync_devcontainer.read_bytes(),
        "the two installed state-sync.sh copies must be byte-identical",
        errors,
    )
    if state_sync_claude.exists():
        state_sync_text = read(state_sync_claude)
        check(
            'git -C "$CLAUDE_DIR" rebase --quit' in state_sync_text,
            "state-sync.sh must use the literal rebase --quit recovery invocation",
            errors,
        )
        check(
            "rebase --abort 2>/dev/null || true" not in state_sync_text,
            "state-sync.sh must not silently discard failed rebase aborts",
            errors,
        )
        check(
            "--autostash" not in state_sync_text,
            "state-sync.sh must not contain --autostash",
            errors,
        )
        check(
            'output="$(git -C "$CLAUDE_DIR" pull --rebase origin "$BRANCH" 2>&1)"'
            in state_sync_text,
            "state-sync.sh must use the exact rebase pull invocation",
            errors,
        )

    # Run generated Stop wrappers instead of relying on text searches: Codex
    # needs one JSON response, while Claude must leave stdout empty.
    with tempfile.TemporaryDirectory() as temp_dir:
        wrapper_root = Path(temp_dir)
        wrapper_scripts = wrapper_root / ".claude" / "hooks" / "scripts"
        shutil.copytree(TARGET_ROOT / ".claude" / "hooks" / "scripts", wrapper_scripts)
        payload = json.dumps({"hook_event_name": "Stop", "session_id": "validator"})
        codex_result = subprocess.run(
            [str(wrapper_scripts / "codex-stop.sh")],
            input=payload,
            text=True,
            capture_output=True,
            check=False,
            cwd=wrapper_root,
        )
        check(
            codex_result.returncode == 0,
            f"generated Codex Stop wrapper failed: {codex_result.stderr}",
            errors,
        )
        try:
            wrapper_output = json.loads(codex_result.stdout)
        except json.JSONDecodeError as error:
            errors.append(
                f"generated Codex Stop wrapper stdout must be one JSON object: {error}"
            )
        else:
            check(
                wrapper_output == {"continue": True},
                "generated Codex Stop wrapper must return the minimal continue JSON object",
                errors,
            )
        claude_result = subprocess.run(
            [str(wrapper_scripts / "claude-stop.sh")],
            input=payload,
            text=True,
            capture_output=True,
            check=False,
            cwd=wrapper_root,
        )
        check(
            claude_result.returncode == 0,
            f"generated Claude Stop wrapper failed: {claude_result.stderr}",
            errors,
        )
        check(
            claude_result.stdout == "",
            "generated Claude Stop wrapper must not write response text to stdout",
            errors,
        )

    github_hooks = json.loads(read(TARGET_ROOT / ".github" / "hooks" / "hooks.json"))
    github_hook_text = json.dumps(github_hooks)
    check(
        ".claude/hooks/scripts/" in github_hook_text,
        "GitHub hooks should invoke shared .claude hook scripts",
        errors,
    )
    check(
        "github-copilot" in github_hook_text,
        "GitHub hooks should pass target id",
        errors,
    )
    check(
        "state-sync.sh" in github_hook_text,
        "GitHub hooks should sync AI state via state-sync.sh",
        errors,
    )
    for event_name, hooks in github_hooks.get("hooks", {}).items():
        check(
            isinstance(hooks, list),
            f"GitHub hook event must be a list: {event_name}",
            errors,
        )
        for hook in hooks if isinstance(hooks, list) else []:
            if not isinstance(hook, dict):
                errors.append(f"GitHub hook must be an object: {event_name}")
                continue
            check(
                hook.get("type") == "command",
                f"GitHub hook must be command type: {event_name}",
                errors,
            )
            check(
                "args" not in hook,
                f"GitHub hooks must not use unsupported args field: {event_name}",
                errors,
            )
            check(
                "bash" in hook,
                f"GitHub hook must include bash field to avoid /bin/sh fallback: {event_name}",
                errors,
            )
            check(
                "timeout" in hook,
                f"GitHub hook missing VS Code timeout: {event_name}",
                errors,
            )
            check(
                "timeoutSec" in hook,
                f"GitHub hook missing Copilot CLI/cloud timeoutSec: {event_name}",
                errors,
            )
            for field in ("bash", "linux", "osx"):
                command = hook.get(field)
                if command is not None:
                    check(
                        ".claude/hooks/scripts/run-hook.sh" in str(command),
                        f"GitHub hook {field} should invoke shared dispatcher: {event_name}",
                        errors,
                    )
                    check(
                        "/bin/sh" not in str(command),
                        f"GitHub hook {field} must not depend on /bin/sh: {event_name}",
                        errors,
                    )

    claude_settings = json.loads(read(TARGET_ROOT / ".claude" / "settings.json"))
    claude_settings_text = json.dumps(claude_settings)
    check(
        ".claude/hooks/scripts/" in claude_settings_text,
        "Claude settings should invoke shared .claude hook scripts",
        errors,
    )
    check(
        "claude-code" in claude_settings_text,
        "Claude hooks should pass target id",
        errors,
    )
    check(
        "state-sync.sh" in claude_settings_text,
        "Claude settings should sync AI state via state-sync.sh",
        errors,
    )

    validate_claude_lifecycle_hooks(claude_settings.get("hooks"), errors)
    errors.extend(pretool_routing_errors(claude_settings.get("hooks"), "claude-code"))

    check(
        "state-sync.sh" in json.dumps(codex_hooks),
        "Codex hooks should sync AI state via state-sync.sh",
        errors,
    )
    errors.extend(pretool_routing_errors(hooks_by_event, "openai-codex"))

    check(
        "state-sync.sh pull" in claude_settings_text,
        "Claude SessionStart hook must pull AI state",
        errors,
    )
    check(
        "claude-stop.sh" in claude_settings_text,
        "Claude Stop hook must use claude-stop.sh",
        errors,
    )
    check(
        "upload-bootstrap" not in claude_settings_text,
        "Claude hooks must not re-mirror the bootstrap (upload-bootstrap)",
        errors,
    )
    check(
        "state-sync.sh pull" in github_hook_text,
        "GitHub hooks SessionStart hook must pull AI state",
        errors,
    )
    check(
        "state-sync.sh push" in github_hook_text,
        "GitHub hooks Stop hook must push AI state",
        errors,
    )
    check(
        "upload-bootstrap" not in github_hook_text,
        "GitHub hooks Stop hook must not re-mirror the bootstrap (upload-bootstrap)",
        errors,
    )
    codex_hooks_text = json.dumps(codex_hooks)
    check(
        "state-sync.sh pull" in codex_hooks_text,
        "Codex SessionStart hook must pull AI state",
        errors,
    )
    check(
        "codex-stop.sh" in codex_hooks_text,
        "Codex Stop hook must use codex-stop.sh",
        errors,
    )
    check(
        "upload-bootstrap" not in codex_hooks_text,
        "Codex hooks must not re-mirror the bootstrap (upload-bootstrap)",
        errors,
    )

    dispatcher = TARGET_ROOT / ".claude" / "hooks" / "scripts" / "run-hook.sh"
    check(
        dispatcher.exists() and bool(dispatcher.stat().st_mode & 0o111),
        "generated hook dispatcher run-hook.sh must be executable because Claude/Codex invoke it directly",
        errors,
    )
    bash_wrapper = (
        TARGET_ROOT / ".claude" / "hooks" / "scripts" / "pretool-bash-guard.sh"
    )
    wrapper_text = read(bash_wrapper) if bash_wrapper.exists() else ""
    expected_children = (
        "protect-files.sh",
        "git-protection.sh",
        "enforce-branch-state.sh",
        "enforce-commit-gate.sh",
        "enforce-pr-gate.sh",
    )
    child_loop = re.search(r"for guard in ([^;]+); do", wrapper_text)
    actual_children: tuple[str, ...] = (
        tuple(child_loop.group(1).split()) if child_loop else ()
    )
    check(
        actual_children == expected_children,
        "Bash safety wrapper must invoke exactly five ordered child guards",
        errors,
    )
    check(
        '[[ -z "$output" ]] && continue' in wrapper_text and "exit 0" in wrapper_text,
        "Bash safety wrapper must short-circuit after a child decision",
        errors,
    )

    validate_hook_guardrails(errors)
    validate_generated_scripts(errors)


# Every routing/permission surface that can actually advertise or grant an MCP
# tool. Narrative policy/doc prose (e.g. tool-routing.instructions.md) is
# reconciled by the documenter separately and is deliberately not a member of
# this list: it is guidance text, not a place a client discovers callable
# tools.
CONTEXT_MODE_ROUTING_SURFACE_FILES = (
    ".mcp.json",
    ".vscode/mcp.json",
    ".codex/config.toml",
    ".claude/hooks/scripts/context-mode-dispatch.sh",
    ".claude/hooks/scripts/context-mode-mcp-filter.mjs",
)


def validate_context_mode_tool_surface(errors: list[str]) -> None:
    """Assert the advertised Context Mode tool surface is exactly the approved
    four-tool allowlist and that no blocked tool name reaches any generated
    routing or permission surface (agent tool grants, MCP server configs,
    hook scripts)."""
    filter_text = read(
        REPO_ROOT / "shared" / "hooks" / "scripts" / "context-mode-mcp-filter.mjs"
    )
    allowed = ", ".join(f'"{tool}"' for tool in CONTEXT_MODE_ALLOWED_TOOLS)
    check(
        f"new Set([{allowed}])" in filter_text,
        "Context Mode MCP filter allowlist must be exactly the four approved tools",
        errors,
    )
    check(
        f'"{CONTEXT_MODE_PINNED_VERSION}"' in filter_text,
        f"Context Mode MCP filter must pin version {CONTEXT_MODE_PINNED_VERSION}",
        errors,
    )
    surfaces = [
        *sorted((TARGET_ROOT / ".claude" / "agents").glob("*.md")),
        *sorted((TARGET_ROOT / ".codex" / "agents").glob("*.toml")),
        *sorted((TARGET_ROOT / ".github" / "agents").glob("*.agent.md")),
        *(TARGET_ROOT / relative for relative in CONTEXT_MODE_ROUTING_SURFACE_FILES),
    ]
    for path in surfaces:
        text = read(path)
        for blocked in CONTEXT_MODE_BLOCKED_TOOLS:
            check(
                blocked not in text,
                f"generated Context Mode routing surface names blocked tool {blocked}: {path}",
                errors,
            )


def run_hook(
    script: Path,
    payload: dict[str, object],
    *args: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> tuple[int, str, str]:
    result = subprocess.run(
        [str(script), *args],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
        cwd=cwd,
        env=env,
    )
    return result.returncode, result.stdout, result.stderr


def run_hook_raw(
    script: Path,
    raw_input: str,
    *args: str,
    cwd: Path | None = None,
) -> tuple[int, str, str]:
    result = subprocess.run(
        [str(script), *args],
        input=raw_input,
        text=True,
        capture_output=True,
        check=False,
        cwd=cwd,
    )
    return result.returncode, result.stdout, result.stderr


def path_without_uv() -> dict[str, str]:
    """A copy of os.environ with any directory containing a `uv` binary removed
    from PATH, so tests can exercise the no-uv guardrail fallback."""
    env = dict(os.environ)
    kept = [
        part
        for part in env.get("PATH", "").split(os.pathsep)
        if part and not (Path(part) / "uv").exists()
    ]
    env["PATH"] = os.pathsep.join(kept)
    return env


def validate_hook_guardrails(errors: list[str]) -> None:
    hook_cases = (
        (
            TARGET_ROOT / ".claude" / "hooks" / "scripts" / "protect-files.sh",
            ".github/hooks/hooks.json",
            "ask",
            "github-copilot",
        ),
        (
            TARGET_ROOT / ".claude" / "hooks" / "scripts" / "protect-files.sh",
            ".claude/settings.json",
            "ask",
            "claude-code",
        ),
        (
            TARGET_ROOT / ".claude" / "hooks" / "scripts" / "protect-files.sh",
            ".codex/hooks.json",
            "deny",
            "openai-codex",
        ),
    )
    for script, protected_path, expected_decision, target_id in hook_cases:
        patch = f"*** Begin Patch\n*** Update File: {protected_path}\n@@\n x\n*** End Patch\n"
        returncode, stdout, stderr = run_hook(
            script,
            {"tool_name": "apply_patch", "tool_input": {"command": patch}},
            target_id,
        )
        check(
            returncode == 0, f"hook guardrail failed to run: {script}: {stderr}", errors
        )
        check(
            f'"permissionDecision":"{expected_decision}"' in stdout,
            f"hook guardrail did not protect {protected_path} with {expected_decision}: {script}",
            errors,
        )

    for target_id, hook_root in (
        ("github-copilot", TARGET_ROOT / ".claude" / "hooks" / "scripts"),
        ("claude-code", TARGET_ROOT / ".claude" / "hooks" / "scripts"),
        ("openai-codex", TARGET_ROOT / ".claude" / "hooks" / "scripts"),
    ):
        returncode, stdout, stderr = run_hook(
            hook_root / "protect-files.sh",
            {"tool_name": "Write", "tool_input": {"path": ".env"}},
            target_id,
        )
        check(
            returncode == 0,
            f"protected-file guardrail failed to run: {hook_root}: {stderr}",
            errors,
        )
        check(
            '"permissionDecision":"deny"' in stdout,
            f"protected-file guardrail did not deny .env: {hook_root}",
            errors,
        )

        returncode, stdout, stderr = run_hook(
            hook_root / "protect-files.sh",
            {"tool_name": "Bash", "tool_input": {"command": "touch .env"}},
            target_id,
        )
        check(
            returncode == 0,
            f"Bash protected-file guardrail failed to run: {hook_root}: {stderr}",
            errors,
        )
        check(
            '"permissionDecision":"deny"' in stdout,
            f"protected-file guardrail did not deny Bash write to .env: {hook_root}",
            errors,
        )

        returncode, stdout, stderr = run_hook(
            hook_root / "git-protection.sh",
            {"tool_name": "Bash", "tool_input": {"command": "git reset --hard HEAD"}},
        )
        check(
            returncode == 0,
            f"git guardrail failed to run: {hook_root}: {stderr}",
            errors,
        )
        check(
            '"permissionDecision":"deny"' in stdout,
            f"git guardrail did not deny git reset --hard: {hook_root}",
            errors,
        )

        # R-HOOKS-01/03: a quoted flag value with whitespace must not desync the
        # tokenizer and smuggle a destructive subcommand past the guard.
        returncode, stdout, stderr = run_hook(
            hook_root / "git-protection.sh",
            {
                "tool_name": "Bash",
                "tool_input": {"command": 'git -C "some dir" reset --hard'},
            },
        )
        check(
            returncode == 0,
            f"git guardrail (quoted flag) failed to run: {hook_root}: {stderr}",
            errors,
        )
        check(
            '"permissionDecision":"deny"' in stdout,
            f"git guardrail must deny reset --hard behind a quoted -C value: {hook_root}",
            errors,
        )

        # A chained command must not let a later, unrelated invocation's flags
        # bleed into an earlier git subcommand's own danger scan (the guard
        # tokenizes past shell operators, which _shell_tokenize drops as mere
        # separators, so "args" for one subcommand must be bounded to that
        # invocation's own clause). `git clean -f && ls -d /tmp` is a wholly
        # benign compound command; without the fix, ls's unrelated -d bled into
        # clean's own args and produced a false "git clean -fd" denial.
        returncode, stdout, stderr = run_hook(
            hook_root / "git-protection.sh",
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git clean -f && ls -d /tmp"},
            },
        )
        check(
            returncode == 0,
            f"git guardrail (chained clean) failed to run: {hook_root}: {stderr}",
            errors,
        )
        check(
            "permissionDecision" not in stdout,
            f"git guardrail must not treat a chained command's unrelated -d as completing 'git clean -fd': {hook_root}",
            errors,
        )

        returncode, stdout, stderr = run_hook(
            hook_root / "git-protection.sh",
            {
                "tool_name": "Bash",
                "tool_input": {
                    "command": "git push origin main && curl --force https://example.com"
                },
            },
        )
        check(
            returncode == 0,
            f"git guardrail (chained push) failed to run: {hook_root}: {stderr}",
            errors,
        )
        check(
            "permissionDecision" not in stdout,
            f"git guardrail must not attribute a chained command's --force to the preceding git push: {hook_root}",
            errors,
        )

        # The same bounding must not blind the guard to a REAL danger that
        # comes after a benign command in the same chain.
        returncode, stdout, stderr = run_hook(
            hook_root / "git-protection.sh",
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git status && git reset --hard"},
            },
        )
        check(
            returncode == 0,
            f"git guardrail (chained danger) failed to run: {hook_root}: {stderr}",
            errors,
        )
        check(
            '"permissionDecision":"deny"' in stdout,
            f"git guardrail must still deny a real reset --hard chained after a benign command: {hook_root}",
            errors,
        )

        # An empty payload carries nothing to inspect: both guards must allow it
        # silently (no spurious ask/deny, no error-log pollution of the repo).
        for guard in ("protect-files.sh", "git-protection.sh"):
            returncode, stdout, stderr = run_hook_raw(hook_root / guard, "", target_id)
            check(
                returncode == 0,
                f"{guard} must exit 0 on empty payload: {hook_root}: {stderr}",
                errors,
            )
            check(
                "permissionDecision" not in stdout,
                f"{guard} must not escalate on an empty payload: {hook_root}",
                errors,
            )
        check(
            not (hook_root.parents[1] / "session_logs" / "hooks-errors.log").exists(),
            f"empty payload must not write hooks-errors.log: {hook_root}",
            errors,
        )

        # R-HOOKS-03: the two safety-critical guards must survive without `uv`.
        no_uv = path_without_uv()
        returncode, stdout, stderr = run_hook(
            hook_root / "protect-files.sh",
            {"tool_name": "Write", "tool_input": {"path": ".env"}},
            target_id,
            env=no_uv,
        )
        check(
            returncode == 0,
            f"protect-files failed to run without uv: {hook_root}: {stderr}",
            errors,
        )
        check(
            '"permissionDecision":"deny"' in stdout,
            f"protect-files must deny .env write even without uv: {hook_root}",
            errors,
        )
        returncode, stdout, stderr = run_hook(
            hook_root / "git-protection.sh",
            {"tool_name": "Bash", "tool_input": {"command": "git -C . reset --hard"}},
            env=no_uv,
        )
        check(
            returncode == 0,
            f"git-protection failed to run without uv: {hook_root}: {stderr}",
            errors,
        )
        check(
            '"permissionDecision":"deny"' in stdout,
            f"git-protection must deny reset --hard even without uv (and past global flags): {hook_root}",
            errors,
        )

    bash_hook_cases = (
        (
            TARGET_ROOT / ".claude" / "hooks" / "scripts" / "protect-files.sh",
            "cat > .github/hooks/hooks.json",
            "ask",
            "github-copilot",
        ),
        (
            TARGET_ROOT / ".claude" / "hooks" / "scripts" / "protect-files.sh",
            "cat > .claude/settings.json",
            "ask",
            "claude-code",
        ),
        (
            TARGET_ROOT / ".claude" / "hooks" / "scripts" / "protect-files.sh",
            "cat > .codex/hooks.json",
            "deny",
            "openai-codex",
        ),
    )
    for script, command, expected_decision, target_id in bash_hook_cases:
        returncode, stdout, stderr = run_hook(
            script,
            {"tool_name": "Bash", "tool_input": {"command": command}},
            target_id,
        )
        check(
            returncode == 0,
            f"Bash hook-file guardrail failed to run: {script}: {stderr}",
            errors,
        )
        check(
            f'"permissionDecision":"{expected_decision}"' in stdout,
            f"hook guardrail did not protect Bash hook edit with {expected_decision}: {script}",
            errors,
        )

    validate_lifecycle_hook_guardrails(errors)
    validate_cancelled_phase_gate_cases(errors)
    validate_commit_msg_git_hook(errors)
    validate_pre_push_git_hook(errors)


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args], text=True, capture_output=True, check=False
    )


def git_actor_env(actor: str) -> dict[str, str]:
    """A hermetic git identity for temp-repo tests: real CI runners and stock
    machines are not guaranteed to have a global user.name/user.email set."""
    return {
        **os.environ,
        "GIT_AUTHOR_NAME": actor,
        "GIT_AUTHOR_EMAIL": f"{actor.lower()}@example.com",
        "GIT_COMMITTER_NAME": actor,
        "GIT_COMMITTER_EMAIL": f"{actor.lower()}@example.com",
    }


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def setup_hook_repo(temp_root: Path) -> Path:
    # Canonicalize the temp root before deriving any fixture paths. On macOS
    # tempfile hands back a /var/... path, but /var is a symlink to
    # /private/var, and both the hooks' repo_root_from_script (cd && pwd) and
    # `git rev-parse --show-toplevel` resolve it to /private/var. Report
    # `target` fields we write from `repo` must match that resolved form or the
    # gates' in-repo containment check spuriously reports "outside this repo".
    temp_root = temp_root.resolve()
    repo = temp_root / "repo"
    repo.mkdir()
    result = subprocess.run(
        ["git", "init", "-b", "dev"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        subprocess.run(
            ["git", "init"], cwd=repo, text=True, capture_output=True, check=False
        )
        git(repo, "checkout", "-b", "dev")
    git(repo, "config", "user.email", "agent@example.com")
    git(repo, "config", "user.name", "Agent")
    shutil.copytree(
        TARGET_ROOT / ".claude" / "hooks" / "scripts",
        repo / ".claude" / "hooks" / "scripts",
    )
    write(repo / ".gitignore", ".claude/\n")
    write(repo / ".claude" / "MEMORY.md", "# Memory\n")
    write(repo / "README.md", "# Scratch\n")
    git(repo, "add", ".")
    git(repo, "commit", "-m", "initial")
    return repo


def write_big_plan(
    repo: Path,
    status: str = "planning",
    phases: tuple[str, ...] = ("phase-one",),
    *,
    current_phase: str = "",
    duplicate_status: str = "",
) -> None:
    phase_lines = "\n".join(f"  - {phase}" for phase in phases)
    duplicate_status_line = f"status: {duplicate_status}\n" if duplicate_status else ""
    write(
        repo / ".claude" / "plans" / "foo.md",
        f"""---
name: foo
type: big-plan
status: {status}
{duplicate_status_line}originating_branch: dev
implementation_branch: foo_implementation
started_at:
phases:
{phase_lines}
current_phase: {current_phase}
---

# Foo
""",
    )


def write_small_plan(
    repo: Path,
    status: str = "in-progress",
    *,
    phase: str = "phase-one",
    missing_cancellation_field: str = "",
    cancelled_at: str = "2026-08-11T07:00:00Z",
    cancelled_reason: str = "The phase is no longer authorized",
    cancelled_evidence: str = "",
    evidence_exists: bool = True,
    evidence_marker: bool = True,
    duplicate_status: str = "",
) -> None:
    closeout = (
        ""
        if status == "cancelled"
        else f"closeout_session_log: .claude/session_logs/{phase}-closeout.md\n"
    )
    if not cancelled_evidence:
        cancelled_evidence = f".claude/session_logs/{phase}-cancelled.md"
    cancellation_values = {
        "cancelled_at": cancelled_at,
        "cancelled_reason": cancelled_reason,
        "cancelled_evidence": cancelled_evidence,
    }
    cancellation_values.pop(missing_cancellation_field, None)
    cancellation = ""
    if status == "cancelled":
        cancellation = "".join(
            f"{key}: {value}\n" for key, value in cancellation_values.items()
        )
    duplicate_status_line = f"status: {duplicate_status}\n" if duplicate_status else ""
    write(
        repo / ".claude" / "plans" / f"{phase}.md",
        f"""---
name: {phase}
type: small-plan
parent_plan: foo
phase_index: 1
status: {status}
{duplicate_status_line}{closeout}{cancellation}---

# {phase}
""",
    )
    if (
        status == "cancelled"
        and evidence_exists
        and "cancelled_evidence" in cancellation_values
    ):
        marker = "**Status:** CANCELLED\n" if evidence_marker else "Status: stopped\n"
        evidence_path = Path(cancellation_values["cancelled_evidence"])
        if not evidence_path.is_absolute():
            evidence_path = repo / evidence_path
        write(
            evidence_path,
            f"# Cancellation\n\n{marker}",
        )


def lifecycle_script(repo: Path, name: str) -> Path:
    return repo / ".claude" / "hooks" / "scripts" / name


def validate_lifecycle_hook_guardrails(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        repo = setup_hook_repo(Path(temp_dir))
        write_big_plan(repo)
        write_small_plan(repo)

        # R-HOOKS-04: a present-but-unparseable payload must fail closed
        # (non-zero exit + deny) instead of silently allowing the tool call.
        # Run against the temp repo so fail-closed logging stays isolated.
        for gate in (
            "protect-files.sh",
            "git-protection.sh",
            "enforce-commit-gate.sh",
            "enforce-pr-gate.sh",
        ):
            returncode, stdout, stderr = run_hook_raw(
                lifecycle_script(repo, gate),
                "this is not json",
                "github-copilot",
                cwd=repo,
            )
            check(
                returncode != 0,
                f"{gate} must exit non-zero on unparseable payload (got {returncode})",
                errors,
            )
            check(
                '"permissionDecision":"deny"' in stdout,
                f"{gate} must deny on unparseable payload",
                errors,
            )

        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-commit-gate.sh"),
            {"tool_name": "Bash", "tool_input": {"command": 'git commit -m "test"'}},
            "github-copilot",
            cwd=repo,
        )
        check(returncode == 0, f"commit gate on dev failed to run: {stderr}", errors)
        check(
            '"permissionDecision":"deny"' in stdout,
            "commit gate must deny commits on dev",
            errors,
        )

        # R-HOOKS-01: global git flags must not smuggle a commit past the classifier.
        # The quoted-whitespace forms guard the tokenizer against word-splitting a
        # quoted flag value (verified 2026-07-07 regression).
        for command in (
            "git -C . commit -m x",
            "git -c a=b commit -m x",
            "git --git-dir=.git commit -m x",
            'git -C "some dir" commit -m x',
            "git -c user.name='A B' commit -m x",
        ):
            returncode, stdout, stderr = run_hook(
                lifecycle_script(repo, "enforce-commit-gate.sh"),
                {"tool_name": "Bash", "tool_input": {"command": command}},
                "github-copilot",
                cwd=repo,
            )
            check(
                returncode == 0,
                f"commit gate flag-evasion case failed to run: {command}: {stderr}",
                errors,
            )
            check(
                '"permissionDecision":"deny"' in stdout,
                f"commit gate must deny flag-smuggled commit on dev: {command}",
                errors,
            )

        # R-HOOKS-02: bypass subjects still undergo branch-shape validation.
        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-commit-gate.sh"),
            {
                "tool_name": "Bash",
                "tool_input": {"command": 'git commit -m "chore(typo): x"'},
            },
            "github-copilot",
            cwd=repo,
        )
        check(
            returncode == 0,
            f"commit gate bypass-branch-shape case failed to run: {stderr}",
            errors,
        )
        check(
            '"permissionDecision":"deny"' in stdout,
            "commit gate must deny bypass-subject commits off an implementation branch",
            errors,
        )

        write(repo / "dirty.txt", "dirty\n")
        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-branch-state.sh"),
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git checkout -b foo_implementation"},
            },
            "github-copilot",
            cwd=repo,
        )
        check(
            returncode == 0,
            f"branch gate dirty-tree case failed to run: {stderr}",
            errors,
        )
        check(
            '"permissionDecision":"deny"' in stdout,
            "branch gate must deny dirty-tree branch creation",
            errors,
        )
        for command in (
            "git switch --create foo_implementation",
            "git checkout -B foo_implementation",
            "git -C . checkout -b foo_implementation",
        ):
            returncode, stdout, stderr = run_hook(
                lifecycle_script(repo, "enforce-branch-state.sh"),
                {"tool_name": "Bash", "tool_input": {"command": command}},
                "github-copilot",
                cwd=repo,
            )
            check(
                returncode == 0,
                f"branch gate alternate dirty-tree case failed to run: {stderr}",
                errors,
            )
            check(
                '"permissionDecision":"deny"' in stdout,
                f"branch gate must deny dirty-tree branch creation: {command}",
                errors,
            )
        (repo / "dirty.txt").unlink()

        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-branch-state.sh"),
            {
                "tool_name": "Bash",
                "tool_input": {"command": 'git checkout -b "bad:slug_implementation"'},
            },
            "github-copilot",
            cwd=repo,
        )
        check(
            returncode == 0,
            f"branch gate invalid-slug case failed to run: {stderr}",
            errors,
        )
        check(
            '"permissionDecision":"deny"' in stdout,
            "branch gate must deny invalid branch slugs",
            errors,
        )

        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-branch-state.sh"),
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git checkout -b foo_implementation"},
            },
            "github-copilot",
            cwd=repo,
        )
        check(
            returncode == 0,
            f"branch gate positive case failed to run: {stderr}",
            errors,
        )
        check(
            '"permissionDecision":"deny"' not in stdout,
            f"branch gate should allow valid branch: {stdout}",
            errors,
        )
        git(repo, "checkout", "-b", "foo_implementation")
        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "record-branch-state.sh"),
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git checkout -b foo_implementation"},
            },
            "github-copilot",
            cwd=repo,
        )
        check(returncode == 0, f"record branch state failed to run: {stderr}", errors)
        check(
            "current_phase: phase-one" in read(repo / ".claude" / "plans" / "foo.md"),
            "record branch state must set current_phase",
            errors,
        )

        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-commit-gate.sh"),
            {
                "tool_name": "Bash",
                "tool_input": {"command": 'git commit -m "fixup! whatever"'},
            },
            "github-copilot",
            cwd=repo,
        )
        check(returncode == 0, f"commit bypass case failed to run: {stderr}", errors)
        check(
            '"permissionDecision":"deny"' not in stdout,
            "commit gate must allow bypass prefixes",
            errors,
        )

        for command in (
            "git push -u origin foo_implementation",
            "git push origin HEAD",
            "git push origin foo_implementation",
        ):
            returncode, stdout, stderr = run_hook(
                lifecycle_script(repo, "enforce-pr-gate.sh"),
                {"tool_name": "Bash", "tool_input": {"command": command}},
                "github-copilot",
                cwd=repo,
            )
            check(
                returncode == 0,
                f"PR gate incomplete-push case failed to run: {stderr}",
                errors,
            )
            check(
                '"permissionDecision":"deny"' in stdout,
                f"PR gate must deny incomplete push command: {command}",
                errors,
            )

        write_small_plan(repo, status="complete")
        write(
            repo / ".claude" / "session_logs" / "phase-one-closeout.md",
            "# Session\n\n**Status:** COMPLETED\n\n## [LEARN] Entries\n\n- [LEARN] none - no new lessons this session\n",
        )
        write(repo / "work.txt", "work\n")
        git(repo, "add", "work.txt")
        write(
            repo / ".claude" / "quality_reports" / "score-test.json",
            json.dumps(
                {
                    "score": 95,
                    "branch": "foo_implementation",
                    "phase": "phase-one",
                    "generated_at": "2099-01-01T00:00:00Z",
                },
                indent=2,
            )
            + "\n",
        )
        os.utime(repo / ".claude" / "quality_reports" / "score-test.json", None)

        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-commit-gate.sh"),
            {
                "tool_name": "Bash",
                "tool_input": {"command": 'git commit -m "phase 1 closeout"'},
            },
            "github-copilot",
            cwd=repo,
        )
        check(
            returncode == 0,
            f"commit missing-metadata case failed to run: {stderr}",
            errors,
        )
        check(
            '"permissionDecision":"deny"' in stdout,
            "commit gate must reject score reports missing required metadata",
            errors,
        )

        head_sha = git(repo, "rev-parse", "HEAD").stdout.strip()
        merge_base = git(repo, "merge-base", "dev", "HEAD").stdout.strip()
        # Content signature the gate recomputes: git hash-object of git diff <merge-base>.
        diff_out = git(repo, "diff", "--no-color", "--no-ext-diff", merge_base).stdout
        content_hash = subprocess.run(
            ["git", "-C", str(repo), "hash-object", "--stdin"],
            input=diff_out,
            text=True,
            capture_output=True,
            check=False,
        ).stdout.strip()
        reports_dir = repo / ".claude" / "quality_reports"

        def score_report(**overrides: object) -> dict[str, object]:
            report: dict[str, object] = {
                "score": 95,
                "branch": "foo_implementation",
                "phase": "phase-one",
                "generated_at": "2099-01-01T00:00:00Z",
                "base_ref": "dev",
                "merge_base_sha": merge_base,
                "head_sha": head_sha,
                "target": str(repo / "work.txt"),
                "dirty": False,
                "tests_passed": True,
                "tests_skipped": False,
                "content_hash": content_hash,
                "changed_files": ["work.txt"],
            }
            report.update(overrides)
            return report

        def clear_reports() -> None:
            for stale in reports_dir.glob("score-*.json"):
                stale.unlink()

        def write_score(report: dict[str, object]) -> None:
            clear_reports()
            path = reports_dir / "score-test.json"
            write(path, json.dumps(report, indent=2) + "\n")
            os.utime(path, None)

        def findings_report(**overrides: object) -> dict[str, object]:
            report: dict[str, object] = {
                "findings": [],
                "counts": {"critical": 0, "major": 0, "minor": 0},
                "ponytail_reviewed": True,
                "ponytail_findings": 0,
                "profiles_reviewed": ["code", "ponytail"],
                "branch": "foo_implementation",
                "phase": "phase-one",
                "generated_at": "2099-01-01T00:00:00Z",
                "base_ref": "dev",
                "merge_base_sha": merge_base,
                "head_sha": head_sha,
                "target": str(repo / "work.txt"),
                "dirty": False,
                "content_hash": content_hash,
                "changed_files": ["work.txt"],
            }
            report.update(overrides)
            return report

        def clear_findings() -> None:
            for stale in reports_dir.glob("findings-*.json"):
                stale.unlink()

        def write_findings(report: dict[str, object]) -> None:
            clear_findings()
            path = reports_dir / "findings-test.json"
            write(path, json.dumps(report, indent=2) + "\n")
            os.utime(path, None)

        # A clean findings report stays valid for every score-axis probe below
        # (HEAD does not move until the real commit lands further down), so
        # each probe's denial is attributable to the score axis under test,
        # not to a findings report that happens to be missing too.
        write_findings(findings_report())

        # R-SCORE-01: tests_passed:false / missing, tests_skipped:true, or
        # dirty:true must all be denied even at a passing score.
        for label, report in (
            ("tests_passed:false", score_report(tests_passed=False)),
            (
                "tests_passed missing",
                {k: v for k, v in score_report().items() if k != "tests_passed"},
            ),
            ("tests_skipped:true", score_report(tests_skipped=True)),
            ("dirty:true", score_report(dirty=True)),
        ):
            write_score(report)
            returncode, stdout, stderr = run_hook(
                lifecycle_script(repo, "enforce-commit-gate.sh"),
                {
                    "tool_name": "Bash",
                    "tool_input": {"command": 'git commit -m "phase 1 closeout"'},
                },
                "github-copilot",
                cwd=repo,
            )
            check(
                returncode == 0, f"commit {label} case failed to run: {stderr}", errors
            )
            check(
                '"permissionDecision":"deny"' in stdout,
                f"commit gate must deny score report with {label} even at score 95",
                errors,
            )

        # R-SCORE-02: select the newest report by generated_at, not filename.
        # Older passing report has a lexically-later filename; newer failing
        # report has a lexically-earlier one. The gate must pick the newer.
        clear_reports()
        write(
            reports_dir / "score-zzz.json",
            json.dumps(score_report(generated_at="2099-01-01T00:00:00Z"), indent=2)
            + "\n",
        )
        write(
            reports_dir / "score-aaa.json",
            json.dumps(
                score_report(score=50, generated_at="2099-06-01T00:00:00Z"), indent=2
            )
            + "\n",
        )
        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-commit-gate.sh"),
            {
                "tool_name": "Bash",
                "tool_input": {"command": 'git commit -m "phase 1 closeout"'},
            },
            "github-copilot",
            cwd=repo,
        )
        check(
            returncode == 0,
            f"commit report-selection case failed to run: {stderr}",
            errors,
        )
        check(
            '"permissionDecision":"deny"' in stdout,
            "commit gate must select the newest report by generated_at",
            errors,
        )
        check(
            "found 50" in stdout,
            "commit gate must use the newer (failing) report, not the lexically-later passing one",
            errors,
        )

        # R-SCORE-02: an amended-HEAD / stale report yields a diagnosable message.
        write_score(score_report(head_sha="0" * 40))
        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-commit-gate.sh"),
            {
                "tool_name": "Bash",
                "tool_input": {"command": 'git commit -m "phase 1 closeout"'},
            },
            "github-copilot",
            cwd=repo,
        )
        check(
            '"permissionDecision":"deny"' in stdout,
            "commit gate must deny a stale-HEAD report",
            errors,
        )
        check(
            "re-run quality_score" in stdout,
            "stale-HEAD failure must tell the user to re-run quality_score",
            errors,
        )

        # R-SCORE-02: content edited since scoring is caught by the content hash.
        write_score(score_report(content_hash="deadbeef"))
        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-commit-gate.sh"),
            {
                "tool_name": "Bash",
                "tool_input": {"command": 'git commit -m "phase 1 closeout"'},
            },
            "github-copilot",
            cwd=repo,
        )
        check(
            '"permissionDecision":"deny"' in stdout,
            "commit gate must deny a content_hash mismatch",
            errors,
        )
        check(
            "re-run quality_score" in stdout,
            "content_hash mismatch failure must tell the user to re-run quality_score",
            errors,
        )

        write_score(score_report())
        # findings-test.json is still the clean baseline written before the
        # R-SCORE-01 loop above; only score-*.json has been swapped since.

        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-commit-gate.sh"),
            {
                "tool_name": "Bash",
                "tool_input": {"command": 'git commit -m "phase 1 closeout"'},
            },
            "github-copilot",
            cwd=repo,
        )
        check(returncode == 0, f"commit positive case failed to run: {stderr}", errors)
        check(
            '"permissionDecision":"deny"' not in stdout,
            f"commit gate should allow complete closeout: {stdout}",
            errors,
        )
        git(repo, "add", ".")
        git(repo, "commit", "-m", "phase 1 closeout")
        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "record-commit-closeout.sh"),
            {"tool_name": "Bash", "tool_input": {"command": "git commit"}},
            "github-copilot",
            cwd=repo,
        )
        check(
            returncode == 0,
            f"record commit no-subject case failed to run: {stderr}",
            errors,
        )
        check(
            "status: complete" not in read(repo / ".claude" / "plans" / "foo.md"),
            "record commit closeout must not complete big plan without commit correlation",
            errors,
        )
        # R-HOOKS-05: a whitespace-variant subject still correlates with HEAD.
        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "record-commit-closeout.sh"),
            {
                "tool_name": "Bash",
                "tool_input": {"command": 'git commit -m "phase 1   closeout"'},
            },
            "github-copilot",
            cwd=repo,
        )
        check(
            returncode == 0, f"record commit closeout failed to run: {stderr}", errors
        )
        check(
            "status: complete" in read(repo / ".claude" / "plans" / "foo.md"),
            "record commit closeout must complete final big plan via normalized subject match",
            errors,
        )

        write(
            repo / ".claude" / "session_logs" / "hooks-bypass.log",
            "2099-01-01T00:00:00Z, target=github-copilot, branch=foo_implementation, subject=fixup! bypass\n",
        )
        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-pr-gate.sh"),
            {"tool_name": "Bash", "tool_input": {"command": "gh pr create --base dev"}},
            "github-copilot",
            cwd=repo,
        )
        check(
            returncode == 0, f"PR gate bypass-log case failed to run: {stderr}", errors
        )
        check(
            '"permissionDecision":"deny"' in stdout,
            "PR gate must deny unacknowledged bypass logs",
            errors,
        )

        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-pr-gate.sh"),
            {
                "tool_name": "Bash",
                "tool_input": {"command": "gh pr create --base main"},
            },
            "github-copilot",
            cwd=repo,
        )
        check(
            returncode == 0, f"PR gate base-main case failed to run: {stderr}", errors
        )
        check(
            '"permissionDecision":"deny"' in stdout,
            "PR gate must deny --base main",
            errors,
        )


def validate_cancelled_phase_gate_cases(errors: list[str]) -> None:
    """Exercise the cancellation-specific lifecycle gate contract."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo = setup_hook_repo(Path(temp_dir))
        git(repo, "checkout", "-b", "foo_implementation")
        write(repo / "phase-work.txt", "certified work\n")
        git(repo, "add", "phase-work.txt")
        git(repo, "commit", "-m", "phase work")
        library = lifecycle_script(repo, "_lib-frontmatter.sh")
        trace = repo / ".claude" / "findings-phase.trace"
        dummy_report = repo / ".claude" / "quality_reports" / "findings.json"
        write(dummy_report, "{}\n")

        def push_failures(probe_override: str = "") -> list[str]:
            trace.unlink(missing_ok=True)
            local_sha = git(repo, "rev-parse", "HEAD").stdout.strip()
            expression = f"""
. {shlex.quote(str(library))}
{probe_override}
select_fresh_report() {{ printf '%s' "$4" > {shlex.quote(str(trace))}; printf '%s' {shlex.quote(str(dummy_report))}; }}
assert_report_freshness() {{ :; }}
json_file_number_value() {{ printf '0'; }}
assert_required_ponytail_review() {{ :; }}
failures=()
assert_push_invariants {shlex.quote(str(repo))} foo_implementation {shlex.quote(local_sha)}
if [[ "${{#failures[@]}}" -gt 0 ]]; then printf '%s\\n' "${{failures[@]}}"; fi
"""
            result = subprocess.run(
                ["bash", "-lc", expression],
                cwd=repo,
                text=True,
                capture_output=True,
                check=False,
            )
            check(
                result.returncode == 0,
                f"cancelled push invariant fixture failed: {result.stderr}",
                errors,
            )
            return result.stdout.splitlines()

        duplicate_status_pairs = (
            ("cancelled", "complete"),
            ("complete", "cancelled"),
            ("complete", "complete"),
        )
        write_big_plan(repo, status="in-progress", phases=("phase-duplicate",))
        for first_status, second_status in duplicate_status_pairs:
            write_small_plan(
                repo,
                status=first_status,
                phase="phase-duplicate",
                duplicate_status=second_status,
            )
            check(
                any(
                    "exactly one status field" in failure for failure in push_failures()
                ),
                f"push gate must reject duplicate status fields: {first_status}, {second_status}",
                errors,
            )

        phases = ("phase-complete",) + tuple(
            f"phase-cancelled-{index}" for index in range(1, 7)
        )
        write_big_plan(repo, status="in-progress", phases=phases)
        write_small_plan(repo, status="complete", phase="phase-complete")
        for phase in phases[1:]:
            write_small_plan(repo, status="cancelled", phase=phase)
        check(
            push_failures() == [],
            "push gate must accept one completed phase plus six evidenced cancelled phases with one commit",
            errors,
        )
        check(
            trace.exists() and read(trace) == "phase-complete",
            "push findings report must bind to the last completed phase, not a cancelled tail",
            errors,
        )

        write_big_plan(
            repo,
            status="in-progress",
            phases=("phase-complete", "phase-cancelled"),
        )
        write_small_plan(repo, status="complete", phase="phase-complete")
        for field in ("cancelled_at", "cancelled_reason", "cancelled_evidence"):
            write_small_plan(
                repo,
                status="cancelled",
                phase="phase-cancelled",
                missing_cancellation_field=field,
            )
            check(
                any(field in failure for failure in push_failures()),
                f"push gate must name missing cancellation field: {field}",
                errors,
            )

        evidence_path = (
            repo / ".claude" / "session_logs" / "phase-cancelled-cancelled.md"
        )
        write_small_plan(
            repo,
            status="cancelled",
            phase="phase-cancelled",
            evidence_exists=False,
        )
        evidence_path.unlink(missing_ok=True)
        check(
            any("evidence file is missing" in failure for failure in push_failures()),
            "push gate must reject a missing cancellation evidence file",
            errors,
        )
        write_small_plan(
            repo,
            status="cancelled",
            phase="phase-cancelled",
            evidence_marker=False,
        )
        check(
            any("same-line prefix" in failure for failure in push_failures()),
            "push gate must reject cancellation evidence without the CANCELLED marker",
            errors,
        )

        for cancelled_at in (
            "2026-08-11T07:00:00",
            "2026-02-30T07:00:00Z",
        ):
            write_small_plan(
                repo,
                status="cancelled",
                phase="phase-cancelled",
                cancelled_at=cancelled_at,
            )
            check(
                any("real UTC timestamp" in failure for failure in push_failures()),
                f"push gate must reject invalid cancelled_at: {cancelled_at}",
                errors,
            )

        for reason in (
            '"   "',
            "|- # folded",
            "[not, prose]",
            "First line\n  continued line",
        ):
            write_small_plan(
                repo,
                status="cancelled",
                phase="phase-cancelled",
                cancelled_reason=reason,
            )
            check(
                any(
                    "single-line scalar prose" in failure for failure in push_failures()
                ),
                f"push gate must reject invalid cancelled_reason: {reason!r}",
                errors,
            )

        for evidence, expected in (
            ("/tmp/phase-d-absolute-evidence.md", "repository-relative"),
            ("nested/../evidence.md", "must not contain .. traversal"),
        ):
            write_small_plan(
                repo,
                status="cancelled",
                phase="phase-cancelled",
                cancelled_evidence=evidence,
                evidence_exists=False,
            )
            check(
                any(expected in failure for failure in push_failures()),
                f"push gate must reject unsafe cancellation evidence path: {evidence}",
                errors,
            )

        outside = Path(temp_dir) / "outside-cancellation.md"
        write(outside, "**Status:** CANCELLED\n")
        outside_link = repo / ".claude" / "session_logs" / "outside-link.md"
        outside_link.unlink(missing_ok=True)
        outside_link.symlink_to(outside)
        write_small_plan(
            repo,
            status="cancelled",
            phase="phase-cancelled",
            cancelled_evidence=".claude/session_logs/outside-link.md",
            evidence_exists=False,
        )
        check(
            any("stay inside the repository" in failure for failure in push_failures()),
            "push gate must reject cancellation evidence symlinked outside the repo",
            errors,
        )

        loop_link = repo / ".claude" / "session_logs" / "loop.md"
        loop_link.unlink(missing_ok=True)
        loop_link.symlink_to("loop.md")
        write_small_plan(
            repo,
            status="cancelled",
            phase="phase-cancelled",
            cancelled_evidence=".claude/session_logs/loop.md",
            evidence_exists=False,
        )
        check(
            any("resolved safely" in failure for failure in push_failures()),
            "push gate must reject a cancellation evidence symlink loop",
            errors,
        )

        evidence_directory = repo / ".claude" / "session_logs" / "evidence-dir"
        evidence_directory.mkdir(exist_ok=True)
        write_small_plan(
            repo,
            status="cancelled",
            phase="phase-cancelled",
            cancelled_evidence=".claude/session_logs/evidence-dir",
            evidence_exists=False,
        )
        check(
            any("regular file" in failure for failure in push_failures()),
            "push gate must reject a directory as cancellation evidence",
            errors,
        )

        invalid_utf8 = repo / ".claude" / "session_logs" / "invalid-utf8.md"
        invalid_utf8.write_bytes(b"\xff\xfe")
        write_small_plan(
            repo,
            status="cancelled",
            phase="phase-cancelled",
            cancelled_evidence=".claude/session_logs/invalid-utf8.md",
            evidence_exists=False,
        )
        check(
            any("valid UTF-8" in failure for failure in push_failures()),
            "push gate must reject invalid-UTF-8 cancellation evidence",
            errors,
        )

        unreadable = repo / ".claude" / "session_logs" / "unreadable.md"
        write(unreadable, "**Status:** CANCELLED\n")
        unreadable.chmod(0)
        write_small_plan(
            repo,
            status="cancelled",
            phase="phase-cancelled",
            cancelled_evidence=".claude/session_logs/unreadable.md",
            evidence_exists=False,
        )
        check(
            any("must be readable" in failure for failure in push_failures()),
            "push gate must reject unreadable cancellation evidence",
            errors,
        )

        split_marker = repo / ".claude" / "session_logs" / "split-marker.md"
        write(split_marker, "**Status:**\nCANCELLED\n")
        write_small_plan(
            repo,
            status="cancelled",
            phase="phase-cancelled",
            cancelled_evidence=".claude/session_logs/split-marker.md",
            evidence_exists=False,
        )
        check(
            any("same-line prefix" in failure for failure in push_failures()),
            "push gate must reject a split-line cancellation marker",
            errors,
        )

        write_small_plan(repo, status="cancelled", phase="phase-cancelled")
        for probe_override, expected in (
            ("cancellation_validation_probe() { return 127; }", "requires python3"),
            (
                "cancellation_validation_probe() { printf PROBE_EXCEPTION; }",
                "probe raised an exception",
            ),
            (
                "cancellation_validation_probe() { printf UNEXPECTED; }",
                "probe returned malformed output",
            ),
        ):
            check(
                any(
                    expected in failure
                    for failure in push_failures(probe_override=probe_override)
                ),
                f"push gate must fail closed for probe condition: {expected}",
                errors,
            )

        write_big_plan(repo, status="in-progress", phases=("phase-cancelled",))
        write_small_plan(repo, status="cancelled", phase="phase-cancelled")
        all_cancelled_failures = push_failures()
        check(
            any(
                "certifies no completed work" in failure
                for failure in all_cancelled_failures
            ),
            "push gate must refuse a branch whose every phase is cancelled",
            errors,
        )
        check(
            not trace.exists(),
            "all-cancelled push must not look for a findings report",
            errors,
        )

        write_big_plan(
            repo,
            status="in-progress",
            phases=("phase-complete",),
        )
        write_small_plan(repo, status="complete", phase="phase-complete")
        check(
            push_failures() == [],
            "existing all-complete push scenario must still pass unchanged",
            errors,
        )

        write_big_plan(
            repo,
            status="in-progress",
            phases=("phase-cancelled",),
            current_phase="phase-cancelled",
        )
        write_small_plan(repo, status="cancelled", phase="phase-cancelled")
        commit_expression = f"""
. {shlex.quote(str(library))}
select_fresh_report() {{ :; }}
failures=()
assert_commit_invariants {shlex.quote(str(repo))} foo_implementation
printf '%s\\n' "${{failures[@]}}"
"""
        commit_result = subprocess.run(
            ["bash", "-lc", commit_expression],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            "cancelled phase never certifies a commit" in commit_result.stdout
            and "advance current_phase past it" in commit_result.stdout,
            "commit gate must emit the distinct cancelled stale-pointer message",
            errors,
        )
        for first_status, second_status in duplicate_status_pairs:
            write_small_plan(
                repo,
                status=first_status,
                phase="phase-cancelled",
                duplicate_status=second_status,
            )
            commit_result = subprocess.run(
                ["bash", "-lc", commit_expression],
                cwd=repo,
                text=True,
                capture_output=True,
                check=False,
            )
            check(
                "exactly one status field before commit" in commit_result.stdout,
                f"commit gate must reject duplicate status fields: {first_status}, {second_status}",
                errors,
            )

        def run_closeout() -> None:
            returncode, _, stderr = run_hook(
                lifecycle_script(repo, "record-commit-closeout.sh"),
                {
                    "tool_name": "Bash",
                    "tool_input": {"command": 'git commit -m "phase work"'},
                },
                "github-copilot",
                cwd=repo,
            )
            check(
                returncode == 0,
                f"cancelled closeout fixture failed: {stderr}",
                errors,
            )

        for first_status, second_status in duplicate_status_pairs:
            write_big_plan(
                repo,
                status="in-progress",
                phases=("phase-one", "phase-two"),
                current_phase="phase-one",
            )
            write_small_plan(repo, status="complete", phase="phase-one")
            write_small_plan(
                repo,
                status=first_status,
                phase="phase-two",
                duplicate_status=second_status,
            )
            run_closeout()
            check(
                "current_phase: phase-one"
                in read(repo / ".claude" / "plans" / "foo.md"),
                f"closeout must not advance past duplicate candidate status fields: {first_status}, {second_status}",
                errors,
            )

        for first_status, second_status in duplicate_status_pairs:
            write_big_plan(
                repo,
                status="in-progress",
                phases=("phase-one", "phase-two"),
                current_phase="phase-one",
            )
            write_small_plan(
                repo,
                status=first_status,
                phase="phase-one",
                duplicate_status=second_status,
            )
            write_small_plan(repo, status="in-progress", phase="phase-two")
            run_closeout()
            check(
                "current_phase: phase-one"
                in read(repo / ".claude" / "plans" / "foo.md"),
                f"closeout must not advance a duplicate current status: {first_status}, {second_status}",
                errors,
            )

        for first_status, second_status in duplicate_status_pairs:
            write_big_plan(
                repo,
                status=first_status,
                duplicate_status=second_status,
                phases=("phase-one", "phase-two"),
                current_phase="phase-one",
            )
            write_small_plan(repo, status="complete", phase="phase-one")
            write_small_plan(repo, status="in-progress", phase="phase-two")
            run_closeout()
            check(
                "current_phase: phase-one"
                in read(repo / ".claude" / "plans" / "foo.md"),
                f"closeout must not advance a duplicate big-plan status: {first_status}, {second_status}",
                errors,
            )

        closeout_phases = ("phase-one", "phase-two", "phase-three")
        write_big_plan(
            repo,
            status="in-progress",
            phases=closeout_phases,
            current_phase="phase-one",
        )
        write_small_plan(repo, status="complete", phase="phase-one")
        write_small_plan(repo, status="cancelled", phase="phase-two")
        write_small_plan(repo, status="in-progress", phase="phase-three")
        run_closeout()
        big_plan_text = read(repo / ".claude" / "plans" / "foo.md")
        check(
            "current_phase: phase-three" in big_plan_text,
            "closeout advance must skip a cancelled next phase",
            errors,
        )

        tail_phases = ("phase-one", "phase-two")
        write_big_plan(
            repo,
            status="in-progress",
            phases=tail_phases,
            current_phase="phase-one",
        )
        write_small_plan(repo, status="cancelled", phase="phase-two")
        run_closeout()
        big_plan_text = read(repo / ".claude" / "plans" / "foo.md")
        check(
            "current_phase: \n" in big_plan_text
            and "status: complete" in big_plan_text,
            "closeout advance past a cancelled tail must clear current_phase and complete the big plan",
            errors,
        )

        write_big_plan(
            repo,
            status="cancelled",
            phases=tail_phases,
            current_phase="phase-one",
        )
        run_closeout()
        big_plan_text = read(repo / ".claude" / "plans" / "foo.md")
        check(
            "current_phase: \n" in big_plan_text
            and "status: cancelled" in big_plan_text,
            "closeout advance must not overwrite an already-cancelled big plan",
            errors,
        )

        git(repo, "checkout", "dev")
        for first_status, second_status in duplicate_status_pairs:
            write_big_plan(repo, status=first_status, duplicate_status=second_status)
            returncode, stdout, stderr = run_hook(
                lifecycle_script(repo, "enforce-branch-state.sh"),
                {
                    "tool_name": "Bash",
                    "tool_input": {"command": "git checkout -b foo_implementation"},
                },
                "github-copilot",
                cwd=repo,
            )
            check(
                returncode == 0,
                f"duplicate-status branch fixture failed to run: {stderr}",
                errors,
            )
            check(
                '"permissionDecision":"deny"' in stdout
                and "exactly one status field" in stdout,
                f"branch gate must reject duplicate status fields: {first_status}, {second_status}",
                errors,
            )

        write_big_plan(repo, status="cancelled")
        returncode, stdout, stderr = run_hook(
            lifecycle_script(repo, "enforce-branch-state.sh"),
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git checkout -b foo_implementation"},
            },
            "github-copilot",
            cwd=repo,
        )
        check(
            returncode == 0,
            f"cancelled branch denial fixture failed: {stderr}",
            errors,
        )
        check(
            '"permissionDecision":"deny"' in stdout
            and "cancelled is terminal" in stdout,
            "branch creation must deny a cancelled big plan with the terminal-status message",
            errors,
        )


def install_git_hooks(repo: Path) -> None:
    git_hook_root = repo / ".claude" / "hooks" / "git-hooks"
    shutil.copytree(TARGET_ROOT / ".claude" / "hooks" / "git-hooks", git_hook_root)
    for hook in git_hook_root.glob("*"):
        hook.chmod(hook.stat().st_mode | 0o111)
    git(repo, "config", "core.hooksPath", ".claude/hooks/git-hooks")


def validate_commit_msg_git_hook(errors: list[str]) -> None:
    """R-HOOKS-07: the commit-msg git hook must mirror enforce-commit-gate.sh's
    ceremony contract for REAL git commits, including the git-alias and `-C`
    evasion paths this deterministic layer exists to close."""
    with tempfile.TemporaryDirectory() as temp_dir:
        repo = setup_hook_repo(Path(temp_dir))
        install_git_hooks(repo)
        write_big_plan(repo)
        git(repo, "checkout", "-b", "foo_implementation")
        run_hook(
            lifecycle_script(repo, "record-branch-state.sh"),
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git checkout -b foo_implementation"},
            },
            "github-copilot",
            cwd=repo,
        )
        write_small_plan(repo, status="complete")
        write(
            repo / ".claude" / "session_logs" / "phase-one-closeout.md",
            "# Session\n\n**Status:** COMPLETED\n\n## [LEARN] Entries\n\n- [LEARN] none - no new lessons this session\n",
        )
        # Pin MEMORY.md's mtime safely in the past so the mtime-based LEARN
        # fallback (memory_mtime >= plan_mtime) cannot flip true/false on
        # filesystem clock resolution during the "missing LEARN" case below.
        old = 1_000_000_000
        os.utime(repo / ".claude" / "MEMORY.md", (old, old))

        reports_dir = repo / ".claude" / "quality_reports"
        merge_base = git(repo, "merge-base", "dev", "HEAD").stdout.strip()

        def head_and_hash() -> tuple[str, str]:
            head = git(repo, "rev-parse", "HEAD").stdout.strip()
            diff_out = git(
                repo, "diff", "--no-color", "--no-ext-diff", merge_base
            ).stdout
            content_hash = subprocess.run(
                ["git", "-C", str(repo), "hash-object", "--stdin"],
                input=diff_out,
                text=True,
                capture_output=True,
                check=False,
            ).stdout.strip()
            return head, content_hash

        def score_report(
            head_sha: str, content_hash_value: str, **overrides: object
        ) -> dict[str, object]:
            report: dict[str, object] = {
                "score": 95,
                "branch": "foo_implementation",
                "phase": "phase-one",
                "generated_at": "2099-01-01T00:00:00Z",
                "base_ref": "dev",
                "merge_base_sha": merge_base,
                "head_sha": head_sha,
                "target": str(repo / "work.txt"),
                "dirty": False,
                "tests_passed": True,
                "tests_skipped": False,
                "content_hash": content_hash_value,
                "changed_files": ["work.txt"],
            }
            report.update(overrides)
            return report

        def clear_scores() -> None:
            for stale in reports_dir.glob("score-*.json"):
                stale.unlink()

        def write_score(report: dict[str, object]) -> None:
            clear_scores()
            path = reports_dir / "score-test.json"
            write(path, json.dumps(report, indent=2) + "\n")
            os.utime(path, None)

        def findings_report(
            head_sha: str, content_hash_value: str, **overrides: object
        ) -> dict[str, object]:
            report: dict[str, object] = {
                "findings": [],
                "counts": {"critical": 0, "major": 0, "minor": 0},
                "ponytail_reviewed": True,
                "ponytail_findings": 0,
                "profiles_reviewed": ["code", "ponytail"],
                "branch": "foo_implementation",
                "phase": "phase-one",
                "generated_at": "2099-01-01T00:00:00Z",
                "base_ref": "dev",
                "merge_base_sha": merge_base,
                "head_sha": head_sha,
                "target": str(repo / "work.txt"),
                "dirty": False,
                "content_hash": content_hash_value,
                "changed_files": ["work.txt"],
            }
            report.update(overrides)
            return report

        def clear_findings() -> None:
            for stale in reports_dir.glob("findings-*.json"):
                stale.unlink()

        def write_findings(report: dict[str, object]) -> None:
            clear_findings()
            path = reports_dir / "findings-test.json"
            write(path, json.dumps(report, indent=2) + "\n")
            os.utime(path, None)

        write(repo / "work.txt", "work\n")
        git(repo, "add", ".")

        # Invalid states, one axis at a time, each blocked by a real `git commit`.

        result = git(repo, "commit", "-m", "phase 1 closeout")
        check(
            result.returncode != 0,
            f"commit-msg hook must block a commit with no quality report: {result.stdout}{result.stderr}",
            errors,
        )

        head_sha, content_hash = head_and_hash()

        # A clean findings report stays valid for every score/plan/closeout/
        # LEARN probe below (HEAD does not move until the "fully valid"
        # commit lands further down), so each probe's denial is attributable
        # to the axis under test, not to a findings report missing too.
        write_findings(findings_report(head_sha, content_hash))

        write_score(score_report(head_sha, content_hash, score=50))
        result = git(repo, "commit", "-m", "phase 1 closeout")
        check(
            result.returncode != 0,
            "commit-msg hook must block a quality score below 90",
            errors,
        )

        write_score(score_report(head_sha, content_hash, content_hash="deadbeef"))
        result = git(repo, "commit", "-m", "phase 1 closeout")
        check(
            result.returncode != 0,
            "commit-msg hook must block a stale content_hash",
            errors,
        )

        # From here the score itself is valid; each remaining axis breaks
        # exactly one other input and restores it before the next.
        write_score(score_report(head_sha, content_hash))

        # R-SCORE-03e: findings-report axis probes, score held valid throughout.
        clear_findings()
        result = git(repo, "commit", "-m", "phase 1 closeout")
        check(
            result.returncode != 0,
            "commit-msg hook must block a commit with a valid score but no findings report",
            errors,
        )

        write_findings(
            findings_report(
                head_sha,
                content_hash,
                findings=[
                    {
                        "severity": "CRITICAL",
                        "title": "sql injection in query builder",
                        "file": "work.txt",
                    }
                ],
                counts={"critical": 1, "major": 0, "minor": 0},
            )
        )
        result = git(repo, "commit", "-m", "phase 1 closeout")
        check(
            result.returncode != 0,
            "commit-msg hook must block a findings report with a CRITICAL finding",
            errors,
        )
        check(
            "sql injection in query builder" in result.stderr,
            "commit-msg hook's CRITICAL-finding failure must name the finding",
            errors,
        )

        optional_report = findings_report(head_sha, content_hash)
        optional_report.pop("ponytail_reviewed")
        optional_report.pop("ponytail_findings")
        optional_report["profiles_reviewed"] = ["code"]
        write_findings(optional_report)
        result = git(repo, "commit", "-m", "phase 1 closeout")
        check(
            result.returncode == 0,
            "commit-msg hook must allow ordinary low-complexity work without Ponytail metadata",
            errors,
        )
        if result.returncode == 0:
            git(repo, "reset", "--soft", "HEAD~1")

        write_findings(
            findings_report(
                head_sha,
                content_hash,
                findings=[
                    {
                        "severity": "MINOR",
                        "title": "yagni: unused abstraction",
                        "file": "work.txt",
                        "profile": "ponytail",
                    }
                ],
                counts={"critical": 0, "major": 0, "minor": 1},
            )
        )
        result = git(repo, "commit", "-m", "phase 1 closeout")
        check(
            result.returncode == 0,
            "commit-msg hook must allow an advisory Ponytail MINOR finding",
            errors,
        )
        if result.returncode == 0:
            git(repo, "reset", "--soft", "HEAD~1")

        write(repo / ".codex" / "config.toml", "[features]\n")
        git(repo, "add", ".codex/config.toml")
        head_sha, content_hash = head_and_hash()
        write_score(score_report(head_sha, content_hash))
        required_report = findings_report(head_sha, content_hash)
        required_report.pop("ponytail_reviewed")
        required_report.pop("ponytail_findings")
        required_report["profiles_reviewed"] = ["code"]
        write_findings(required_report)
        result = git(repo, "commit", "-m", "phase 1 closeout")
        check(
            result.returncode != 0
            and "requires a fresh Ponytail review" in result.stderr,
            "commit-msg hook must require Ponytail metadata for control-plane work",
            errors,
        )

        write_findings(findings_report(head_sha, content_hash))

        write_findings(findings_report(head_sha, content_hash, content_hash="deadbeef"))
        result = git(repo, "commit", "-m", "phase 1 closeout")
        check(
            result.returncode != 0,
            "commit-msg hook must block a stale findings content_hash",
            errors,
        )

        # R-SCORE-03e: select the newest findings report by generated_at, not
        # filename order - mirrors the score report's R-SCORE-02 rule. The
        # older report has a lexically-LATER filename and is clean; the newer
        # one has a lexically-EARLIER filename and carries a CRITICAL finding.
        clear_findings()
        write(
            reports_dir / "findings-zzz.json",
            json.dumps(
                findings_report(
                    head_sha, content_hash, generated_at="2099-01-01T00:00:00Z"
                ),
                indent=2,
            )
            + "\n",
        )
        write(
            reports_dir / "findings-aaa.json",
            json.dumps(
                findings_report(
                    head_sha,
                    content_hash,
                    generated_at="2099-06-01T00:00:00Z",
                    findings=[
                        {
                            "severity": "CRITICAL",
                            "title": "newer critical wins",
                            "file": "work.txt",
                        }
                    ],
                    counts={"critical": 1, "major": 0, "minor": 0},
                ),
                indent=2,
            )
            + "\n",
        )
        result = git(repo, "commit", "-m", "phase 1 closeout")
        check(
            result.returncode != 0,
            "commit-msg hook must select the newest findings report by generated_at",
            errors,
        )
        check(
            "newer critical wins" in result.stderr,
            "commit-msg hook must use the newer (CRITICAL) findings report, not the lexically-later clean one",
            errors,
        )

        # Restore the clean baseline before the remaining axis probes below.
        write_findings(findings_report(head_sha, content_hash))

        write_small_plan(repo, status="in-progress")
        result = git(repo, "commit", "-m", "phase 1 closeout")
        check(
            result.returncode != 0,
            "commit-msg hook must block an incomplete small plan",
            errors,
        )
        write_small_plan(repo, status="complete")

        write(
            repo / ".claude" / "session_logs" / "phase-one-closeout.md",
            "# Session\n\nStatus: done\n",
        )
        result = git(repo, "commit", "-m", "phase 1 closeout")
        check(
            result.returncode != 0,
            "commit-msg hook must block a closeout log missing **Status:** COMPLETED",
            errors,
        )

        write(
            repo / ".claude" / "session_logs" / "phase-one-closeout.md",
            "# Session\n\n**Status:** COMPLETED\n",
        )
        result = git(repo, "commit", "-m", "phase 1 closeout")
        check(
            result.returncode != 0,
            "commit-msg hook must block missing LEARN evidence",
            errors,
        )

        # Fully valid state -> allowed; this actually lands the commit.
        write(
            repo / ".claude" / "session_logs" / "phase-one-closeout.md",
            "# Session\n\n**Status:** COMPLETED\n\n## [LEARN] Entries\n\n- [LEARN] none - no new lessons this session\n",
        )
        # findings-test.json is still the clean baseline written above.
        result = git(repo, "commit", "-m", "phase 1 closeout")
        check(
            result.returncode == 0,
            f"commit-msg hook must allow a fully valid commit: {result.stdout}{result.stderr}",
            errors,
        )

        # R-HOOKS-07: git-alias evasion (the one residual gap the PreToolUse
        # classifier could not close) must hit the same gate as `git commit`.
        write(repo / "more.txt", "more\n")
        git(repo, "add", ".")
        git(repo, "config", "alias.ci", "commit")
        clear_scores()
        alias_result = subprocess.run(
            ["git", "ci", "-m", "invalid via alias"],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            alias_result.returncode != 0,
            "commit-msg hook must block the git-alias evasion path (git ci)",
            errors,
        )

        # `git -C <path> commit`, invoked from entirely outside the repo: there
        # is no cwd-dependent classifier here for a global flag to evade.
        outside_result = subprocess.run(
            ["git", "-C", str(repo), "commit", "-m", "invalid via -C"],
            cwd=temp_dir,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            outside_result.returncode != 0,
            "commit-msg hook must block invalid commits invoked via git -C from outside the repo",
            errors,
        )

        # Fix the state; the same staged change now commits cleanly.
        head_sha, content_hash = head_and_hash()
        write_score(score_report(head_sha, content_hash))
        write_findings(findings_report(head_sha, content_hash))
        retry_result = git(repo, "commit", "-m", "phase 1 closeout take 2")
        check(
            retry_result.returncode == 0,
            f"commit-msg hook must allow the retried valid commit: {retry_result.stdout}{retry_result.stderr}",
            errors,
        )

        # D4-B: dev/main pass through regardless of ceremony state.
        clear_scores()
        git(repo, "checkout", "dev")
        write(repo / "dev-work.txt", "dev work\n")
        git(repo, "add", "dev-work.txt")
        dev_result = git(
            repo, "commit", "-m", "direct commit on dev with no ceremony at all"
        )
        check(
            dev_result.returncode == 0,
            f"commit-msg hook must pass through commits on dev regardless of state: {dev_result.stdout}{dev_result.stderr}",
            errors,
        )

        # `git commit --no-verify` remains the sanctioned manual escape.
        git(repo, "checkout", "foo_implementation")
        clear_scores()
        write(repo / "escape.txt", "escape\n")
        git(repo, "add", "escape.txt")
        escape_result = git(repo, "commit", "-m", "escape hatch", "--no-verify")
        check(
            escape_result.returncode == 0,
            f"git commit --no-verify must bypass the commit-msg gate: {escape_result.stdout}{escape_result.stderr}",
            errors,
        )

        # R-HOOKS-08: commit-msg also fires for git-merge (githooks(5)). A merge
        # commit from dev must pass through even with invalid ceremony state
        # (dev already diverged above via "direct commit on dev with no
        # ceremony at all"); the very next real commit is still gated normally.
        clear_scores()
        merge_result = git(
            repo,
            "merge",
            "--no-ff",
            "dev",
            "-m",
            "Merge branch 'dev' into foo_implementation",
        )
        check(
            merge_result.returncode == 0,
            f"commit-msg hook must allow a merge commit even with invalid ceremony state: {merge_result.stdout}{merge_result.stderr}",
            errors,
        )

        write(repo / "after-merge.txt", "after merge\n")
        git(repo, "add", "after-merge.txt")
        post_merge_result = git(repo, "commit", "-m", "phase 1 after merge")
        check(
            post_merge_result.returncode != 0,
            "commit-msg hook must still block a normal commit with invalid state right after a merge passthrough",
            errors,
        )


def validate_pre_push_git_hook(errors: list[str]) -> None:
    """R-HOOKS-09: the pre-push git hook must mirror enforce-pr-gate.sh's
    push-invariant contract (assert_push_invariants) for REAL git pushes to a
    bare remote, gating the ref/sha actually being pushed."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        remote = temp_root / "remote.git"
        subprocess.run(
            ["git", "init", "--bare", "-b", "dev", str(remote)],
            text=True,
            capture_output=True,
            check=False,
        )

        repo = setup_hook_repo(temp_root)
        install_git_hooks(repo)
        git(repo, "remote", "add", "origin", str(remote))
        initial_push = git(repo, "push", "origin", "dev")
        check(
            initial_push.returncode == 0,
            f"initial push to bare remote failed: {initial_push.stdout}{initial_push.stderr}",
            errors,
        )

        reports_dir = repo / ".claude" / "quality_reports"

        def content_hash_for(base: str) -> str:
            diff_out = git(repo, "diff", "--no-color", "--no-ext-diff", base).stdout
            return subprocess.run(
                ["git", "-C", str(repo), "hash-object", "--stdin"],
                input=diff_out,
                text=True,
                capture_output=True,
                check=False,
            ).stdout.strip()

        def write_score_report(**overrides: object) -> None:
            head_sha = git(repo, "rev-parse", "HEAD").stdout.strip()
            merge_base = git(repo, "merge-base", "dev", "HEAD").stdout.strip()
            report: dict[str, object] = {
                "score": 95,
                "branch": "foo_implementation",
                "phase": "phase-one",
                "generated_at": "2099-01-01T00:00:00Z",
                "base_ref": "dev",
                "merge_base_sha": merge_base,
                "head_sha": head_sha,
                "target": str(repo / "phase-work.txt"),
                "dirty": False,
                "tests_passed": True,
                "tests_skipped": False,
                "content_hash": content_hash_for(merge_base),
                "changed_files": ["phase-work.txt"],
            }
            report.update(overrides)
            for stale in reports_dir.glob("score-*.json"):
                stale.unlink()
            write(reports_dir / "score-test.json", json.dumps(report, indent=2) + "\n")

        def write_findings_report(**overrides: object) -> None:
            # Matches the real workflow: record_findings.py runs during
            # REVIEW, before the commit it certifies lands - so head_sha here
            # is that commit's PARENT, never the commit itself. This is why
            # assert_push_invariants checks head_sha as an ancestor of the
            # pushed sha, not an exact match (a report generated pre-commit
            # can never equal the branch tip once one or more commits land).
            head_sha = git(repo, "rev-parse", "HEAD").stdout.strip()
            merge_base = git(repo, "merge-base", "dev", "HEAD").stdout.strip()
            report: dict[str, object] = {
                "findings": [],
                "counts": {"critical": 0, "major": 0, "minor": 0},
                "ponytail_reviewed": True,
                "ponytail_findings": 0,
                "profiles_reviewed": ["code", "ponytail"],
                "branch": "foo_implementation",
                "phase": "phase-one",
                "generated_at": "2099-01-01T00:00:00Z",
                "base_ref": "dev",
                "merge_base_sha": merge_base,
                "head_sha": head_sha,
                "target": str(repo / "phase-work.txt"),
                "dirty": False,
                "content_hash": content_hash_for(merge_base),
                "changed_files": ["phase-work.txt"],
            }
            report.update(overrides)
            for stale in reports_dir.glob("findings-*.json"):
                stale.unlink()
            write(
                reports_dir / "findings-test.json", json.dumps(report, indent=2) + "\n"
            )

        write_big_plan(repo)
        git(repo, "add", ".")
        git(repo, "commit", "-m", "add big plan", "--no-verify")
        git(repo, "push", "origin", "dev")

        git(repo, "checkout", "-b", "foo_implementation")
        run_hook(
            lifecycle_script(repo, "record-branch-state.sh"),
            {
                "tool_name": "Bash",
                "tool_input": {"command": "git checkout -b foo_implementation"},
            },
            "github-copilot",
            cwd=repo,
        )
        write_small_plan(repo, status="in-progress")
        write(repo / "phase-work.txt", "phase work\n")
        git(repo, "add", ".")
        git(repo, "commit", "-m", "phase 1 work", "--no-verify")

        # Incomplete small plan -> push blocked, stderr names the phase.
        push_result = subprocess.run(
            ["git", "push", "origin", "foo_implementation"],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            push_result.returncode != 0,
            f"pre-push hook must block a push with an incomplete small plan: {push_result.stdout}{push_result.stderr}",
            errors,
        )
        check(
            "phase-one" in push_result.stderr,
            "pre-push hook failure must name the incomplete phase",
            errors,
        )

        # Complete the small plan/closeout/LEARN so the commit-count check
        # (>= one commit per phase) is also satisfied.
        write_small_plan(repo, status="complete")
        write(
            repo / ".claude" / "session_logs" / "phase-one-closeout.md",
            "# Session\n\n**Status:** COMPLETED\n\n## [LEARN] Entries\n\n- [LEARN] none - no new lessons this session\n",
        )
        git(repo, "add", ".")
        # Generated pre-commit (matching REVIEW-before-COMMIT in the real
        # workflow): head_sha here is the parent of the commit below, so this
        # exercises the ancestor relation, not a same-sha coincidence.
        write_findings_report()
        git(repo, "commit", "-m", "phase 1 closeout", "--no-verify")

        push_result = subprocess.run(
            ["git", "push", "origin", "foo_implementation"],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            push_result.returncode == 0,
            f"pre-push hook must allow a push once all phases are complete: {push_result.stdout}{push_result.stderr}",
            errors,
        )

        write(repo / "minor-work.txt", "minor work\n")
        git(repo, "add", "minor-work.txt")
        write_score_report()
        write_findings_report(
            counts={"critical": 0, "major": 0, "minor": 1},
            findings=[
                {
                    "severity": "MINOR",
                    "title": "yagni: optional simplification",
                    "file": "minor-work.txt",
                    "profile": "ponytail",
                }
            ],
        )
        minor_commit = git(repo, "commit", "-m", "phase 1 advisory minor")
        check(
            minor_commit.returncode == 0,
            "commit-msg hook must allow a Ponytail MINOR finding",
            errors,
        )
        minor_push = subprocess.run(
            ["git", "push", "origin", "foo_implementation"],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            minor_push.returncode == 0,
            "pre-push hook must allow an advisory Ponytail MINOR finding",
            errors,
        )

        write(repo / ".codex" / "config.toml", "[features]\n")
        git(repo, "add", ".codex/config.toml")
        write_score_report()
        # Build the ordinary report then remove optional metadata to exercise
        # the required-review push path without bypassing report freshness.
        write_findings_report()
        required_path = reports_dir / "findings-test.json"
        required_report = json.loads(read(required_path))
        required_report.pop("ponytail_reviewed")
        required_report.pop("ponytail_findings")
        required_report["profiles_reviewed"] = ["code"]
        write(required_path, json.dumps(required_report, indent=2) + "\n")
        git(repo, "commit", "-m", "phase 1 high-risk metadata", "--no-verify")
        missing_metadata_push = subprocess.run(
            ["git", "push", "origin", "foo_implementation"],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            missing_metadata_push.returncode != 0
            and "requires a fresh Ponytail review" in missing_metadata_push.stderr,
            "pre-push hook must require Ponytail metadata for high-risk diffs",
            errors,
        )

        # R-SCORE-03e: counts.critical == 0 but counts.major > 0 must still
        # allow the commit (the commit gate only checks critical) while
        # blocking the push (the push gate additionally checks major).
        write(repo / "major-work.txt", "major work\n")
        git(repo, "add", "major-work.txt")
        write_score_report()
        write_findings_report(
            counts={"critical": 0, "major": 2, "minor": 0},
            findings=[
                {
                    "severity": "MAJOR",
                    "title": "unbounded query",
                    "file": "major-work.txt",
                    "profile": "ponytail",
                },
                {
                    "severity": "MAJOR",
                    "title": "missing pagination",
                    "file": "major-work.txt",
                    "profile": "ponytail",
                },
            ],
        )
        commit_result = git(
            repo, "commit", "-m", "phase 1 followup with major findings"
        )
        check(
            commit_result.returncode == 0,
            f"commit-msg hook must allow a commit whose findings report has MAJOR findings but zero CRITICAL: {commit_result.stdout}{commit_result.stderr}",
            errors,
        )
        major_push = subprocess.run(
            ["git", "push", "origin", "foo_implementation"],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            major_push.returncode != 0,
            "pre-push hook must block a push whose findings report has MAJOR findings",
            errors,
        )
        check(
            "unbounded query" in major_push.stderr
            or "missing pagination" in major_push.stderr,
            "pre-push hook's MAJOR-finding failure must name at least one finding",
            errors,
        )

        # D4-B: dev passthrough regardless of ceremony state.
        git(repo, "checkout", "dev")
        write(repo / "dev-arbitrary.txt", "dev\n")
        git(repo, "add", "dev-arbitrary.txt")
        git(repo, "commit", "-m", "arbitrary dev commit", "--no-verify")
        dev_push = subprocess.run(
            ["git", "push", "origin", "dev"],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            dev_push.returncode == 0,
            f"pre-push hook must pass through pushes on dev regardless of ceremony state: {dev_push.stdout}{dev_push.stderr}",
            errors,
        )

        # Break the ceremony again, then use --no-verify as the sanctioned
        # manual escape from the pre-push gate.
        git(repo, "checkout", "foo_implementation")
        write_small_plan(repo, status="in-progress")
        write(repo / "break-ceremony.txt", "break\n")
        git(repo, "add", ".")
        git(repo, "commit", "-m", "break ceremony again", "--no-verify")
        blocked_push = subprocess.run(
            ["git", "push", "origin", "foo_implementation"],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            blocked_push.returncode != 0,
            "pre-push hook must still block a push with broken ceremony before the --no-verify case",
            errors,
        )
        escape_push = subprocess.run(
            ["git", "push", "--no-verify", "origin", "foo_implementation"],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            escape_push.returncode == 0,
            f"git push --no-verify must bypass the pre-push gate: {escape_push.stdout}{escape_push.stderr}",
            errors,
        )

        # Branch deletion passthrough: the ref already exists on the remote
        # from the successful pushes above.
        delete_push = subprocess.run(
            ["git", "push", "origin", "--delete", "foo_implementation"],
            cwd=repo,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            delete_push.returncode == 0,
            f"pre-push hook must allow branch deletion pushes: {delete_push.stdout}{delete_push.stderr}",
            errors,
        )


def validate_generated_scripts(errors: list[str]) -> None:
    python_scripts = sorted(DIST_ROOT.rglob("*.py"))
    with tempfile.TemporaryDirectory() as temp_dir:
        bytecode_root = Path(temp_dir)
        for index, script in enumerate(python_scripts):
            try:
                py_compile.compile(
                    str(script),
                    cfile=str(bytecode_root / f"{index}.pyc"),
                    doraise=True,
                )
            except py_compile.PyCompileError as error:
                errors.append(
                    f"generated Python script syntax failed: {script}: {error}"
                )

    # git-hooks/* files are named for git's hook-discovery convention (no .sh
    # suffix), so the glob above would silently skip them.
    shell_scripts = sorted(DIST_ROOT.rglob("*.sh")) + sorted(
        DIST_ROOT.rglob("git-hooks/*")
    )
    for script in shell_scripts:
        result = subprocess.run(
            ["bash", "-n", str(script)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            result.returncode == 0,
            f"generated shell script syntax failed: {script}: {result.stderr}",
            errors,
        )

    findings_script = TARGET_ROOT / ".claude" / "scripts" / "record_findings.py"
    with tempfile.TemporaryDirectory() as temp_dir:
        report_path = Path(temp_dir) / "findings.json"
        result = subprocess.run(
            [
                sys.executable,
                str(findings_script),
                "README.md",
                "--profile",
                "code",
                "--phase",
                "validator",
                "--base-ref",
                "dev",
                "--out",
                str(report_path),
            ],
            cwd=REPO_ROOT,
            input="[]",
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            result.returncode == 0,
            f"record_findings optional-metadata run failed: {result.stderr}",
            errors,
        )
        if report_path.exists():
            report = json.loads(read(report_path))
            check(
                "ponytail_reviewed" not in report,
                "record_findings must omit Ponytail metadata when the profile did not run",
                errors,
            )
            check(
                "ponytail_findings" not in report,
                "record_findings must omit Ponytail finding metadata when the profile did not run",
                errors,
            )
            check(
                report.get("profiles_reviewed") == ["code"],
                "record_findings must persist sorted reviewed profiles",
                errors,
            )

        legacy_path = Path(temp_dir) / "legacy-ponytail-findings.json"
        legacy = subprocess.run(
            [
                sys.executable,
                str(findings_script),
                "README.md",
                "--profile",
                "ponytail",
                "--phase",
                "validator",
                "--base-ref",
                "dev",
                "--out",
                str(legacy_path),
            ],
            cwd=REPO_ROOT,
            input="[]",
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            legacy.returncode == 0,
            f"record_findings Ponytail metadata run failed: {legacy.stderr}",
            errors,
        )
        if legacy_path.exists():
            report = json.loads(read(legacy_path))
            check(
                report.get("ponytail_reviewed") is True,
                "record_findings must preserve Ponytail metadata when the profile ran",
                errors,
            )
            check(
                report.get("ponytail_findings") == 0,
                "record_findings must preserve zero Ponytail findings",
                errors,
            )

        no_profile = subprocess.run(
            [
                sys.executable,
                str(findings_script),
                "README.md",
                "--phase",
                "validator",
                "--out",
                str(Path(temp_dir) / "no-profile.json"),
            ],
            cwd=REPO_ROOT,
            input="[]",
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            no_profile.returncode != 0
            and "at least one --profile" in no_profile.stderr,
            "record_findings must reject empty reviewed-profile lists for new reports",
            errors,
        )

        missing_finding_profile = subprocess.run(
            [
                sys.executable,
                str(findings_script),
                "README.md",
                "--profile",
                "code",
                "--phase",
                "validator",
                "--out",
                str(Path(temp_dir) / "missing-finding-profile.json"),
            ],
            cwd=REPO_ROOT,
            input='[{"severity": "MINOR", "title": "missing profile"}]',
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            missing_finding_profile.returncode != 0
            and "non-empty profile" in missing_finding_profile.stderr,
            "record_findings must reject findings without a reviewed profile",
            errors,
        )


def validate_skills_and_paths(errors: list[str]) -> None:
    shared_skill_count = count_skills(REPO_ROOT / "shared" / "skills")
    skill_root = TARGET_ROOT / ".claude" / "skills"
    count = count_skills(skill_root)
    check(
        count == shared_skill_count,
        f"multi-agent skill count mismatch: {count}",
        errors,
    )
    # Skill frontmatter integrity (visibility, description) is checked once,
    # in validate_docs_parity, alongside the other named-inventory checks.
    for skill_name in ("ponytail", "ponytail-review"):
        skill_path = skill_root / skill_name / "SKILL.md"
        check(
            skill_path.exists(),
            f"generated Ponytail skill missing: {skill_path}",
            errors,
        )
        if skill_path.exists():
            skill_text = read(skill_path)
            check(
                "visibility: public" in skill_text,
                f"{skill_name} must remain public",
                errors,
            )
            check(
                "license: MIT" in skill_text,
                f"{skill_name} must retain its MIT license metadata",
                errors,
            )

    ponytail_license = TARGET_ROOT / ".claude" / "third_party" / "ponytail" / "LICENSE"
    ponytail_upstream = (
        TARGET_ROOT / ".claude" / "third_party" / "ponytail" / "UPSTREAM.md"
    )
    check(
        ponytail_license.exists(),
        "generated target must include Ponytail's MIT license",
        errors,
    )
    check(
        ponytail_upstream.exists(),
        "generated target must include Ponytail provenance",
        errors,
    )
    if ponytail_upstream.exists():
        provenance = read(ponytail_upstream)
        check(
            "v4.8.4" in provenance,
            "Ponytail provenance must pin release v4.8.4",
            errors,
        )
        check(
            "canonical\nworkflow and review-routing policies decide lifecycle placement"
            in provenance,
            "Ponytail provenance must preserve canonical workflow authority",
            errors,
        )
        check(
            "conditional `ponytail` review profile runs" in provenance
            and "`ponytail-review` remains an\nimported skill" in provenance,
            "Ponytail provenance must distinguish the review profile from the imported skill",
            errors,
        )
        check(
            "bc9ee94" in provenance,
            "Ponytail provenance must pin commit bc9ee94",
            errors,
        )
        pinned_files = {
            REPO_ROOT
            / "shared"
            / "skills"
            / "ponytail"
            / "SKILL.md": "9e2611144a8da730f110af6f789fd4dc9f6574f7fbff1fd5be7220b0b30a6fc3",
            REPO_ROOT
            / "shared"
            / "skills"
            / "ponytail-review"
            / "SKILL.md": "bf0f50e5a406c8c1587ab4a69340369bf0293ef1022450cb9142468aa15f8656",
            REPO_ROOT
            / "shared"
            / "third_party"
            / "ponytail"
            / "LICENSE": "fc5bd8de55887831701aa9b9da85925fe0a581680187a5e23f2cf74235aadcd4",
        }
        for source, expected_hash in pinned_files.items():
            actual_hash = hashlib.sha256(source.read_bytes()).hexdigest()
            check(
                actual_hash == expected_hash
                and f"sha256:{expected_hash}" in provenance,
                f"Ponytail allowlist hash changed without a provenance update: {source}",
                errors,
            )

    # R-SKILLS-01: the commit skill must follow the enforced lifecycle, never
    # walking the agent into feature/* branches or agent-driven merges.
    commit_skill = skill_root / "commit" / "SKILL.md"
    if commit_skill.exists():
        commit_text = read(commit_skill)
        check(
            "feature/" not in commit_text,
            "commit skill must not use feature/* branches",
            errors,
        )
        check(
            "gh pr merge" not in commit_text,
            "commit skill must not run gh pr merge (human merges)",
            errors,
        )
        check(
            "_implementation" in commit_text,
            "commit skill must use <plan>_implementation branches",
            errors,
        )
        check(
            "--base dev" in commit_text,
            "commit skill must open PRs against dev",
            errors,
        )

    shared_prompts = sorted((REPO_ROOT / "shared" / "prompts").glob("*.prompt.md"))
    generated_prompts = sorted(
        (TARGET_ROOT / ".claude" / "prompts").glob("*.prompt.md")
    )
    check(
        [path.name for path in generated_prompts]
        == [path.name for path in shared_prompts],
        ".claude prompt output must mirror shared/prompts",
        errors,
    )
    for source in shared_prompts:
        generated = TARGET_ROOT / ".claude" / "prompts" / source.name
        check(
            generated.exists() and read(generated) == read(source),
            f"generated prompt differs from source: {source.name}",
            errors,
        )

    shared_profiles = sorted((REPO_ROOT / "shared" / "review-profiles").glob("*.md"))
    generated_profiles = sorted(
        (TARGET_ROOT / ".claude" / "review-profiles").glob("*.md")
    )
    check(
        [path.name for path in generated_profiles]
        == [path.name for path in shared_profiles],
        ".claude review profile output must mirror shared/review-profiles",
        errors,
    )

    codex_config = read_toml(TARGET_ROOT / ".codex" / "config.toml")
    skill_entries = codex_config.get("skills", {})
    if isinstance(skill_entries, dict):
        skill_config = skill_entries.get("config", [])
    else:
        skill_config = []
    configured_skill_paths = {
        entry.get("path")
        for entry in skill_config
        if isinstance(entry, dict) and entry.get("enabled") is True
    }
    expected_skill_paths = {
        f"../.claude/skills/{path.parent.name}/SKILL.md"
        for path in (REPO_ROOT / "shared" / "skills").glob("*/SKILL.md")
    }
    check(
        configured_skill_paths == expected_skill_paths,
        "Codex config must enable every shared .claude skill by relative SKILL.md path",
        errors,
    )

    forbidden_fragments = ("/home/ghisso", "/Users/", "BEGIN OPENSSH", "PRIVATE KEY")
    for relative_path in OBSOLETE_GENERATED_DIRS:
        check(
            not (TARGET_ROOT / relative_path).exists(),
            f"multi-agent must not generate obsolete target-local path: {relative_path}",
            errors,
        )
    errors.extend(root_source_mirror_errors(REPO_ROOT, TARGET_ROOT))
    for path in text_files(TARGET_ROOT):
        text = read(path)
        for fragment in forbidden_fragments:
            if fragment in text:
                errors.append(
                    f"forbidden fragment in generated file: {path} contains {fragment}"
                )

    for root in (
        TARGET_ROOT / "CLAUDE.md",
        TARGET_ROOT / "AGENTS.md",
        TARGET_ROOT / ".claude",
        TARGET_ROOT / ".codex",
    ):
        paths = [root] if root.is_file() else text_files(root)
        for path in paths:
            if (
                "hooks" in path.parts and "scripts" in path.parts
            ) or path.name == "bootstrap-ownership.env":
                continue
            text = read(path)
            for fragment in NON_COPILOT_PATH_LEAKS:
                # These exact canonical inventories name the shared Git-hook
                # surface. Every other generated non-Copilot file still rejects it.
                if (
                    fragment == ".github/hooks"
                    and path in SHARED_GITHUB_HOOK_INVENTORY_PATHS
                    and text.count(".github/hooks/") == 1
                ):
                    continue
                if fragment in text:
                    errors.append(
                        f"Copilot path leaked into non-GitHub output: {path} contains {fragment}"
                    )

    validate_root_guidance(errors)
    validate_policy_adapters(errors)

    copilot_guidance = read(TARGET_ROOT / ".github" / "copilot-instructions.md")
    check(
        ".claude/skills/ponytail/SKILL.md" in copilot_guidance,
        "Copilot guidance must activate the canonical Ponytail skill for coding",
        errors,
    )

    stale_workflow_fragments = (
        "After score >= 80",
        "After score ≥ 80",
        "Score >= 80",
        "plan -> implement -> verify -> review -> score workflow",
        "PLAN -> IMPLEMENT -> VERIFY -> REVIEW -> FIX -> SCORE\n",
        "plan, verify, review, score loop",
        "plan/verify/review/score loop",
        "Score ≥ 80 = commit",
        "Score ≥ 90 = PR-ready",
        "auto-commit if score ≥ 80",
        "auto-commit if score >= 80",
        "Just do it",
        "codex_hooks",
        "quality_reports/<timestamp>-<phase>.json",
    )
    for path in (
        TARGET_ROOT / "AGENTS.md",
        TARGET_ROOT / "CLAUDE.md",
        TARGET_ROOT / ".claude" / "instructions" / "workspace.instructions.md",
        TARGET_ROOT / ".claude" / "instructions" / "workflow.instructions.md",
        TARGET_ROOT / ".claude" / "instructions" / "tool-routing.instructions.md",
        TARGET_ROOT
        / ".claude"
        / "instructions"
        / "quality-and-testing.instructions.md",
        TARGET_ROOT / ".claude" / "agents" / "orchestrator.md",
        TARGET_ROOT / ".claude" / "agents" / "verifier.md",
    ):
        text = read(path)
        for fragment in stale_workflow_fragments:
            check(
                fragment not in text,
                f"{path} contains stale workflow/gate phrase: {fragment}",
                errors,
            )
    # docs/history/ holds archived completed plans; they legitimately contain
    # old path patterns and are not living documentation.
    source_paths = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
        *(
            p
            for p in text_files(REPO_ROOT / "docs")
            if "history" not in p.relative_to(REPO_ROOT / "docs").parts
        ),
        *text_files(REPO_ROOT / "shared"),
    ]
    for path in source_paths:
        text = read(path)
        check(
            "quality_reports/<timestamp>-<phase>.json" not in text,
            f"{path} contains stale quality report path pattern",
            errors,
        )
    # R-VALID-01: assert the concept structurally (the devcontainer-required vs
    # outside-fallback distinction is documented) rather than pinning one exact
    # English sentence that every wording change would have to chase.
    tool_routing_text = read(
        TARGET_ROOT / ".claude" / "instructions" / "tool-routing.instructions.md"
    ).lower()
    check(
        "semble" in tool_routing_text
        and "context mode" in tool_routing_text
        and all(tool in tool_routing_text for tool in CONTEXT_MODE_ALLOWED_TOOLS)
        and "hook-only" not in tool_routing_text
        and "does not expose mcp tools" not in tool_routing_text,
        "tool-routing instructions must name all four allowed Context Mode "
        "tools and must not claim Context Mode is hook-only or exposes no "
        "MCP tools",
        errors,
    )

    validate_support_files(errors)
    validate_generated_hygiene(errors)


MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def extract_markdown_links(text: str) -> list[str]:
    return MARKDOWN_LINK_PATTERN.findall(text)


def extract_frontmatter(text: str) -> str:
    parts = text.split("---\n", 2)
    return parts[1] if text.startswith("---\n") and len(parts) == 3 else ""


def extract_frontmatter_description(frontmatter: str) -> str:
    lines = frontmatter.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("description:"):
            continue
        rest = line[len("description:") :].strip()
        if rest in ("|", ">", "|-", ">-", ""):
            # A blank line does NOT end a YAML block scalar - only a
            # less-indented (or EOF) line does. Treating an empty `follow`
            # as "end of block" would silently truncate the description at
            # the first blank paragraph break.
            block_lines = []
            for follow in lines[index + 1 :]:
                if not follow.strip() or follow.startswith((" ", "\t")):
                    block_lines.append(follow.strip())
                else:
                    break
            return " ".join(block_lines).strip()
        return rest.strip("\"'")
    return ""


def validate_docs_parity(errors: list[str]) -> None:
    """R-VALID-02: mechanical drift-policing for authoring docs, mirroring
    upstream's check-surface-sync.py / check-skill-integrity.py after they
    were burned by repeated doc drift (architecture-review-2026-07.md §3.2).
    Structural assertions only (R-VALID-01 lesson) - no exact-sentence pins."""

    # 1. Link integrity: every relative markdown link in README.md, AGENTS.md,
    # and docs/*.md (excluding archived docs/history/) resolves to an
    # existing file or directory, relative to the linking file's own
    # directory (docs/*.md link with "../", matching how they render on
    # GitHub).
    docs_root = REPO_ROOT / "docs"
    doc_files = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
        *sorted(
            p
            for p in text_files(docs_root)
            if p.suffix == ".md" and "history" not in p.relative_to(docs_root).parts
        ),
    ]
    for doc in doc_files:
        if not doc.exists():
            continue
        for link in extract_markdown_links(read(doc)):
            if link.startswith(("http://", "https://", "mailto:")):
                continue
            target = link.split("#", 1)[0]
            if not target:
                continue
            resolved = (doc.parent / target).resolve()
            check(
                resolved.exists(),
                f"{doc.relative_to(REPO_ROOT)} has a broken relative link: '{link}' does not resolve to {resolved}",
                errors,
            )

    readme_text = read(REPO_ROOT / "README.md")

    # 2a. Skill names: README references are a SUBSET of shared/skills/*/ (it
    # lists "most important", not all) - the reverse is not required.
    referenced_skills = set(re.findall(r"shared/skills/([^/]+)/SKILL\.md", readme_text))
    disk_skills = {
        path.parent.name
        for path in (REPO_ROOT / "shared" / "skills").glob("*/SKILL.md")
    }
    missing_skills = referenced_skills - disk_skills
    check(
        not missing_skills,
        f"README references skills that do not exist on disk: {sorted(missing_skills)}",
        errors,
    )

    # 2b. Agent names: README's "Current agents" list is exact for universal
    # roles. Codex-only derived roles intentionally have no canonical prompt.md
    # and remain internal until their target-specific documentation phase.
    agents_match = re.search(r"Current agents:\n\n((?:- .+\n)+)", readme_text)
    check(agents_match is not None, "README must have a 'Current agents:' list", errors)
    if agents_match:
        readme_agents = {
            line[2:].strip()
            for line in agents_match.group(1).splitlines()
            if line.strip()
        }
        universal_agents = {
            path.parent.name
            for path in (REPO_ROOT / "shared" / "agents").glob("*/prompt.md")
        }
        check(
            readme_agents == universal_agents,
            f"README 'Current agents' list must exactly match universal shared agents: readme={sorted(readme_agents)} universal={sorted(universal_agents)}",
            errors,
        )

    # 2c. Hook script names: docs/runtime-checks.md's guardrail list is EXACT
    # against shared/hooks/scripts/*.sh, excluding _lib-frontmatter.sh (a
    # sourced library, not a hook entry point).
    runtime_checks_text = read(REPO_ROOT / "docs" / "runtime-checks.md")
    hooks_match = re.search(
        r"Guardrail scripts are generated under[^\n]*:\n\n((?:- [^\n]+\n)+)",
        runtime_checks_text,
    )
    check(
        hooks_match is not None,
        "docs/runtime-checks.md must list guardrail scripts",
        errors,
    )
    if hooks_match:
        doc_hook_scripts = set(re.findall(r"`([\w.-]+\.sh)`", hooks_match.group(1)))
        disk_hook_scripts = {
            path.name
            for path in (REPO_ROOT / "shared" / "hooks" / "scripts").glob("*.sh")
            if path.name != "_lib-frontmatter.sh"
        }
        check(
            doc_hook_scripts == disk_hook_scripts,
            "docs/runtime-checks.md guardrail script list must exactly match shared/hooks/scripts/*.sh "
            f"(excluding _lib-frontmatter.sh): doc={sorted(doc_hook_scripts)} disk={sorted(disk_hook_scripts)}",
            errors,
        )

    # 3. Skill frontmatter integrity: visibility + non-empty, non-duplicate
    # description (duplicate descriptions break description-match loading of
    # background skills).
    descriptions: dict[str, Path] = {}
    for skill_path in sorted((REPO_ROOT / "shared" / "skills").glob("*/SKILL.md")):
        frontmatter = extract_frontmatter(read(skill_path))
        check(
            "\nvisibility: public" in f"\n{frontmatter}"
            or "\nvisibility: background" in f"\n{frontmatter}",
            f"skill missing visibility metadata: {skill_path}",
            errors,
        )
        description = extract_frontmatter_description(frontmatter).strip()
        check(
            bool(description),
            f"skill missing non-empty description: {skill_path}",
            errors,
        )
        if not description:
            continue
        duplicate = descriptions.get(description)
        if duplicate is not None:
            errors.append(
                f"duplicate skill description breaks description-match loading: {duplicate} and {skill_path}"
            )
        else:
            descriptions[description] = skill_path


SECURITY_REQUIRED_HEADINGS = (
    "Assets",
    "Trust Boundaries",
    "Hostile Inputs",
    "Generated Hook Trust",
    "Command Parsing",
    "Protected Paths",
    "Credential Handling",
    "Nested Git State",
    "Accepted Escapes",
    "Reporting Criteria",
    "Exclusions",
)


def memory_security_authority_errors(
    security_text: str,
    readme_text: str,
    architecture_text: str,
    target_mapping_text: str,
) -> list[str]:
    """Return narrow drift errors for the shared-memory security contract."""
    errors: list[str] = []
    for heading in SECURITY_REQUIRED_HEADINGS:
        if not re.search(rf"^## {re.escape(heading)}$", security_text, re.MULTILINE):
            errors.append(
                f"SECURITY.md missing required threat-model heading: {heading}"
            )

    required_links = (
        (
            "README.md",
            readme_text,
            "docs/architecture.md#memory-authority-and-privacy",
        ),
        ("README.md", readme_text, "SECURITY.md"),
        (
            "docs/architecture.md",
            architecture_text,
            "../SECURITY.md",
        ),
        (
            "docs/target-mapping.md",
            target_mapping_text,
            "architecture.md#memory-authority-and-privacy",
        ),
    )
    for document, text, required_link in required_links:
        if required_link not in extract_markdown_links(text):
            errors.append(
                f"{document} missing required memory/security authority link: {required_link}"
            )
    return errors


def validate_memory_security_authority(errors: list[str]) -> None:
    """Require one discoverable security model without configuring native memory."""
    security = REPO_ROOT / "SECURITY.md"
    if not security.is_file():
        errors.append("missing root SECURITY.md threat model")
        return
    errors.extend(
        memory_security_authority_errors(
            read(security),
            read(REPO_ROOT / "README.md"),
            read(REPO_ROOT / "docs" / "architecture.md"),
            read(REPO_ROOT / "docs" / "target-mapping.md"),
        )
    )


def validate_support_files(errors: list[str]) -> None:
    required_files = (
        "MEMORY.md",
        "scripts/quality_score.py",
        "scripts/record_findings.py",
        "templates/session-log.md",
        "templates/plan-big.md",
        "templates/plan-small.md",
        "templates/quality-report.md",
        "templates/requirements-spec.md",
        "templates/skill-template.md",
        "plans/README.md",
        "quality_reports/README.md",
        "session_logs/README.md",
        "explorations/README.md",
        "instructions/workflow.instructions.md",
        "instructions/quality-and-testing.instructions.md",
        "instructions/tool-routing.instructions.md",
        "instructions/workspace.md",
        "prompts/README.prompt.md",
        "review-profiles/code.md",
        "review-profiles/ponytail.md",
        "review-profiles/security.md",
        "skills/ponytail/SKILL.md",
        "skills/ponytail-review/SKILL.md",
        "third_party/ponytail/LICENSE",
        "third_party/ponytail/UPSTREAM.md",
        "hooks/scripts/run-hook.sh",
        "hooks/scripts/protect-files.sh",
        "hooks/scripts/git-protection.sh",
        "hooks/scripts/context-mode-dispatch.sh",
        "hooks/scripts/session-log.sh",
        "hooks/scripts/state-sync.sh",
        "hooks/scripts/restore-root-adapters.sh",
        "hooks/scripts/_lib-frontmatter.sh",
        "hooks/scripts/enforce-branch-state.sh",
        "hooks/scripts/record-branch-state.sh",
        "hooks/scripts/enforce-commit-gate.sh",
        "hooks/scripts/record-commit-closeout.sh",
        "hooks/scripts/enforce-pr-gate.sh",
        "hooks/scripts/session-start-state.sh",
        "hooks/scripts/stop-session-log-check.sh",
    )
    for target in TARGETS:
        support_root = target_support_root(target)
        for relative_path in required_files:
            path = support_root / relative_path
            check(
                path.exists(),
                f"{target} missing generated support file: {path}",
                errors,
            )
            if (
                relative_path in {"templates/plan-big.md", "templates/plan-small.md"}
                and path.exists()
            ):
                check(
                    read(path).startswith("---\n"),
                    f"{target} plan template must start with frontmatter: {path}",
                    errors,
                )


def validate_generated_hygiene(errors: list[str]) -> None:
    for path in DIST_ROOT.rglob("*"):
        if path.name == "__pycache__" or path.suffix == ".pyc":
            errors.append(f"generated bytecode artifact must not be committed: {path}")


def validate_devcontainer_and_installer(errors: list[str]) -> None:
    devcontainer_root = TARGET_ROOT / ".devcontainer"
    required_files = (
        "devcontainer.json",
        "Dockerfile",
        "post-start.sh",
        "state-sync.sh",
        "restore-root-adapters.sh",
    )
    for relative_path in required_files:
        path = devcontainer_root / relative_path
        check(path.exists(), f"missing generated devcontainer file: {path}", errors)
    for relative_path in ("state-sync.sh", "restore-root-adapters.sh"):
        path = devcontainer_root / relative_path
        check(
            path.exists() and bool(path.stat().st_mode & 0o111),
            f"devcontainer AI-state script is not executable: {path}",
            errors,
        )

    restore_template = read(
        REPO_ROOT / "shared" / "hooks" / "scripts" / "restore-root-adapters.sh"
    )
    expected_restore_script = render_restore_script(restore_template)
    for generated_restore in (
        devcontainer_root / "restore-root-adapters.sh",
        TARGET_ROOT / ".claude" / "hooks" / "scripts" / "restore-root-adapters.sh",
    ):
        check(
            generated_restore.exists()
            and read(generated_restore) == expected_restore_script,
            f"generated restorer allowlist must derive from runtime ownership: {generated_restore}",
            errors,
        )

    if (devcontainer_root / "devcontainer.json").exists():
        data = json.loads(read(devcontainer_root / "devcontainer.json"))
        build = data.get("build", {})
        run_args = data.get("runArgs", [])
        container_env = data.get("containerEnv", {})
        settings = data.get("customizations", {}).get("vscode", {}).get("settings", {})
        post_create = data.get("postCreateCommand", "")
        check(
            build.get("context") == ".",
            "devcontainer build context must stay inside .devcontainer",
            errors,
        )
        check(
            data.get("postStartCommand") == "bash .devcontainer/post-start.sh",
            "devcontainer must run post-start sync script",
            errors,
        )
        check(
            "--gpus" in run_args and "all" in run_args,
            "devcontainer must default to GPU sandbox run args",
            errors,
        )
        check(
            "HF_HUB_ENABLE_HF_TRANSFER" not in container_env,
            "devcontainer must not use deprecated HF_HUB_ENABLE_HF_TRANSFER",
            errors,
        )
        check(
            container_env.get("HF_XET_HIGH_PERFORMANCE") == "1",
            "devcontainer must enable high-performance Hugging Face Xet transfers",
            errors,
        )
        check("HF_TOKEN" in container_env, "devcontainer must forward HF_TOKEN", errors)
        check(
            "HUGGING_FACE_HUB_TOKEN" in container_env,
            "devcontainer must forward HUGGING_FACE_HUB_TOKEN",
            errors,
        )
        check(
            container_env.get("UV_PROJECT_ENVIRONMENT") == "/home/vscode/.venv",
            "devcontainer must not reuse a host-mounted project .venv",
            errors,
        )
        check(
            container_env.get("UV_LINK_MODE") == "copy",
            "devcontainer must use uv copy link mode",
            errors,
        )
        check(
            settings.get("python.defaultInterpreterPath")
            == "/home/vscode/.venv/bin/python",
            "devcontainer VS Code Python path must use the container-local uv venv",
            errors,
        )
        check(
            "/home/vscode/.venv" in post_create,
            "devcontainer postCreateCommand must initialize the container-local uv venv",
            errors,
        )
        forbidden_run_args = ("/dev/fuse", "apparmor:unconfined")
        for fragment in forbidden_run_args:
            check(
                fragment not in json.dumps(run_args),
                f"devcontainer must not require hf-mount/FUSE privilege: {fragment}",
                errors,
            )

    if (devcontainer_root / "Dockerfile").exists():
        dockerfile = read(devcontainer_root / "Dockerfile")
        check(
            "cuda-dl-base" in dockerfile,
            "devcontainer Dockerfile must use the GPU base image",
            errors,
        )
        check(
            f"npm install -g context-mode@{CONTEXT_MODE_PINNED_VERSION}" in dockerfile,
            f"devcontainer Dockerfile must install context-mode pinned to {CONTEXT_MODE_PINNED_VERSION}",
            errors,
        )
        check(
            "command -v context-mode" in dockerfile,
            "devcontainer Dockerfile must verify context-mode is on PATH",
            errors,
        )
        check(
            "context-mode --help >/dev/null" in dockerfile,
            "devcontainer Dockerfile must verify context-mode CLI execution",
            errors,
        )
        check(
            "huggingface_hub" in dockerfile,
            "devcontainer Dockerfile must install Hugging Face tooling",
            errors,
        )
        check(
            "hf_transfer" not in dockerfile,
            "devcontainer Dockerfile must not install deprecated hf_transfer tooling",
            errors,
        )
        check(
            '"semble[mcp]"' in dockerfile,
            "devcontainer Dockerfile must install Semble MCP tooling",
            errors,
        )
        check(
            'python3 -c "import huggingface_hub, semble"' in dockerfile,
            "devcontainer Dockerfile must verify HF hub and Semble imports",
            errors,
        )
        check(
            "command -v hf" in dockerfile,
            "devcontainer Dockerfile must verify the HF CLI is on PATH",
            errors,
        )
        check(
            "command -v semble" in dockerfile,
            "devcontainer Dockerfile must verify the Semble CLI is on PATH",
            errors,
        )
        check(
            "optional " not in dockerfile.lower(),
            "devcontainer tool installs must be required, not optional fallbacks",
            errors,
        )
        check(
            'getent passwd "${USERNAME}"' in dockerfile,
            "devcontainer Dockerfile must verify the remote user passwd entry",
            errors,
        )
        check(
            'id -gn "${USERNAME}"' in dockerfile,
            "devcontainer Dockerfile must use the remote user's actual primary group",
            errors,
        )
        check(
            "USER ${USERNAME}" in dockerfile,
            "devcontainer Dockerfile must switch to the non-host user",
            errors,
        )

    post_start = devcontainer_root / "post-start.sh"
    if post_start.exists():
        post_start_text = read(post_start)
        check(
            "uv run python" not in post_start_text,
            "post-start must not invoke project uv for AI state sync",
            errors,
        )
        # R-SYNC-05: setup's checkout populates .claude/hooks/git-hooks/, so
        # core.hooksPath is configured immediately after it and before pull -
        # no window where a fresh container is ungated once setup completes.
        setup_index = post_start_text.find('"$STATE_SYNC" setup')
        hooks_path_index = post_start_text.find(
            'git -C "$REPO_ROOT" config core.hooksPath'
        )
        pull_index = post_start_text.find('"$STATE_SYNC" pull')
        restore_index = post_start_text.find('"$RESTORE_ROOT_ADAPTERS"')
        check(setup_index != -1, "post-start must run state-sync.sh setup", errors)
        check(
            hooks_path_index != -1, "post-start must configure core.hooksPath", errors
        )
        check(pull_index != -1, "post-start must run state-sync.sh pull", errors)
        check(
            restore_index != -1, "post-start must run restore-root-adapters.sh", errors
        )
        check(
            -1 not in (setup_index, hooks_path_index, pull_index, restore_index)
            and setup_index < hooks_path_index < pull_index < restore_index,
            "post-start must run: state-sync.sh setup, then set core.hooksPath, then state-sync.sh pull, then restore-root-adapters.sh, in that order",
            errors,
        )

    installer = REPO_ROOT / "scripts" / "install_bootstrap.py"
    updater = REPO_ROOT / "scripts" / "update_consumers.py"
    git_identity_env = git_actor_env("Validator")
    with tempfile.TemporaryDirectory() as temp_dir_name:
        trust_home = Path(temp_dir_name) / "user-home"
        trust_home.mkdir()
        install_env = {
            **git_identity_env,
            "HOME": str(trust_home),
            "XDG_CONFIG_HOME": str(trust_home / "xdg"),
            "CODEX_HOME": str(trust_home / "codex-home"),
        }
        temp_repo = Path(temp_dir_name) / "consumer"
        temp_repo.mkdir()
        init_result = subprocess.run(
            ["git", "init", str(temp_repo)],
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            init_result.returncode == 0,
            f"temporary git init failed: {init_result.stderr}",
            errors,
        )

        # R-SYNC-05: no bucket, no --state-remote — the installer must succeed
        # with no sync configuration at all (state stays local-only, per D4's
        # fail-toward-local contract; a bare origin is exercised separately in
        # the Phase 6 adversarial suite).
        install_result = subprocess.run(
            [sys.executable, str(installer), str(temp_repo)],
            cwd=REPO_ROOT,
            env=install_env,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            install_result.returncode == 0,
            f"installer temp run failed: {install_result.stderr}",
            errors,
        )
        check_codex_hook_trust_notice(
            "default installer", install_result.stdout, errors, dry_run=False
        )
        check(
            not any(trust_home.iterdir()),
            "installer must not write user-level trust state",
            errors,
        )
        check(
            (temp_repo / ".devcontainer" / "devcontainer.json").exists(),
            "installer must copy trackable devcontainer",
            errors,
        )
        check(
            (temp_repo / ".gitignore").exists(),
            "installer must create or update .gitignore",
            errors,
        )
        check(
            "AI_STATE_REMOTE"
            not in read(temp_repo / ".devcontainer" / "devcontainer.json"),
            "installer must not write AI_STATE_REMOTE without --state-remote",
            errors,
        )
        for relative_path in (
            ".claude/skills/ponytail/SKILL.md",
            ".claude/skills/ponytail-review/SKILL.md",
            ".claude/third_party/ponytail/LICENSE",
            ".claude/third_party/ponytail/UPSTREAM.md",
        ):
            check(
                (temp_repo / relative_path).exists(),
                f"installer must make Ponytail available downstream: {relative_path}",
                errors,
            )
        check(
            "v4.8.4"
            in read(temp_repo / ".claude" / "third_party" / "ponytail" / "UPSTREAM.md"),
            "installed Ponytail provenance must retain the pinned release",
            errors,
        )

        # R-SYNC-05: the installer creates the nested .claude/ AI-state repo
        # and makes its own bootstrap: install commit (distinct from the Stop
        # hook's session: commits).
        claude_git = temp_repo / ".claude" / ".git"
        check(
            claude_git.is_dir(),
            "installer must create the nested .claude/ AI-state repo",
            errors,
        )
        if claude_git.is_dir():
            claude_branch = subprocess.run(
                ["git", "-C", str(temp_repo / ".claude"), "branch", "--show-current"],
                text=True,
                capture_output=True,
                check=False,
            )
            check(
                claude_branch.stdout.strip() == "ai-state",
                "nested .claude/ repo must be on branch ai-state",
                errors,
            )
            claude_log = subprocess.run(
                ["git", "-C", str(temp_repo / ".claude"), "log", "--oneline"],
                text=True,
                capture_output=True,
                check=False,
            )
            check(
                "bootstrap:" in claude_log.stdout,
                "installer must make a bootstrap:-prefixed commit in .claude/",
                errors,
            )

        # Consumer MEMORY.md is mutable state, not bootstrap content. A repeat
        # install must preserve it even though dist/ carries the blank seed
        # template used for fresh consumers.
        consumer_memory = (
            "# Consumer memory\n\n- [LEARN:domain] preserve this exact content\n"
        )
        memory_path = temp_repo / ".claude" / "MEMORY.md"
        write(memory_path, consumer_memory)
        subprocess.run(
            ["git", "-C", str(temp_repo / ".claude"), "add", "MEMORY.md"], check=False
        )
        memory_commit = subprocess.run(
            [
                "git",
                "-C",
                str(temp_repo / ".claude"),
                "commit",
                "-q",
                "-m",
                "session: add consumer memory",
            ],
            env=install_env,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            memory_commit.returncode == 0,
            f"consumer memory fixture commit failed: {memory_commit.stderr}",
            errors,
        )
        reinstall_result = subprocess.run(
            [sys.executable, str(installer), str(temp_repo)],
            cwd=REPO_ROOT,
            env=install_env,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            reinstall_result.returncode == 0,
            f"installer repeat run failed: {reinstall_result.stderr}",
            errors,
        )
        check(
            memory_path.read_bytes() == consumer_memory.encode(),
            "installer repeat run must preserve git-backed consumer MEMORY.md byte-for-byte",
            errors,
        )

        consumer_state = {
            "MEMORY.md": b"# Consumer memory\n",
            "plans/consumer-plan.md": b"consumer plan\n",
            "explorations/consumer-note.md": b"consumer exploration\n",
            "session_logs/consumer.log": b"consumer log\n",
            "quality_reports/consumer.json": b'{"consumer": true}\n',
            "instructions/project-context.instructions.md": b"consumer project context\n",
            "settings.local.json": b'{"consumerLocal": true}\n',
        }
        check(
            tuple(CONSUMER_STATE_PATHS)
            == (
                "MEMORY.md",
                "plans",
                "explorations",
                "session_logs",
                "quality_reports",
                # Derived machine-local hook state. It is always untracked/ignored,
                # never git-committed like the other consumer-state roots above, so
                # it is exercised by the dedicated cache-preservation coverage in
                # validate_state_sync/validate_local_only_state_sync instead of the
                # git-add/commit fixture below.
                ".cache",
                "instructions/project-context.instructions.md",
                "settings.local.json",
            ),
            "consumer-state fixture must cover every ownership-contract root",
            errors,
        )
        for relative_path, content in consumer_state.items():
            state_path = temp_repo / ".claude" / relative_path
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_bytes(content)
        subprocess.run(
            ["git", "-C", str(temp_repo / ".claude"), "add", *consumer_state],
            check=False,
        )
        state_commit = subprocess.run(
            [
                "git",
                "-C",
                str(temp_repo / ".claude"),
                "commit",
                "-q",
                "-m",
                "session: add consumer state",
            ],
            env=install_env,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            state_commit.returncode == 0,
            f"consumer state fixture commit failed: {state_commit.stderr}",
            errors,
        )
        state_reinstall = subprocess.run(
            [sys.executable, str(installer), str(temp_repo)],
            cwd=REPO_ROOT,
            env=install_env,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            state_reinstall.returncode == 0,
            f"installer repeat state refresh failed: {state_reinstall.stderr}",
            errors,
        )
        for relative_path, content in consumer_state.items():
            check(
                (temp_repo / ".claude" / relative_path).read_bytes() == content,
                f"installer repeat run must preserve consumer state {relative_path} byte-for-byte",
                errors,
            )

        # A legacy consumer has mutable state but no nested .claude git repo.
        # Preservation must happen before migrate-from-hf snapshots that state.
        legacy_repo = Path(temp_dir_name) / "legacy-consumer"
        legacy_repo.mkdir()
        subprocess.run(
            ["git", "init", str(legacy_repo)],
            text=True,
            capture_output=True,
            check=False,
        )
        legacy_memory = (
            "# Legacy memory\n\n- [LEARN:domain] preserve before migration\n"
        )
        legacy_memory_path = legacy_repo / ".claude" / "MEMORY.md"
        write(legacy_memory_path, legacy_memory)
        legacy_state = {
            relative_path: content.replace(b"Consumer", b"Legacy")
            for relative_path, content in consumer_state.items()
        }
        legacy_state["MEMORY.md"] = legacy_memory.encode()
        for relative_path, content in legacy_state.items():
            state_path = legacy_repo / ".claude" / relative_path
            state_path.parent.mkdir(parents=True, exist_ok=True)
            state_path.write_bytes(content)
        legacy_install_result = subprocess.run(
            [sys.executable, str(installer), str(legacy_repo)],
            cwd=REPO_ROOT,
            env=install_env,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            legacy_install_result.returncode == 0,
            f"installer legacy refresh failed: {legacy_install_result.stderr}",
            errors,
        )
        check(
            legacy_memory_path.read_bytes() == legacy_memory.encode(),
            "installer legacy refresh must preserve pre-git consumer MEMORY.md byte-for-byte",
            errors,
        )
        migrated_memory = subprocess.run(
            ["git", "-C", str(legacy_repo / ".claude"), "show", "HEAD:MEMORY.md"],
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            migrated_memory.returncode == 0 and migrated_memory.stdout == legacy_memory,
            "legacy migration commit must contain the original consumer MEMORY.md",
            errors,
        )
        for relative_path, content in legacy_state.items():
            state_path = legacy_repo / ".claude" / relative_path
            check(
                state_path.read_bytes() == content,
                f"installer legacy refresh must preserve consumer state {relative_path} byte-for-byte",
                errors,
            )
            if relative_path == "settings.local.json":
                # Preserved on disk, but state-sync.sh gitignores it in the
                # nested repo ("local convenience only; never synced"), so it
                # is deliberately absent from migration history.
                continue
            migrated_state = subprocess.run(
                [
                    "git",
                    "-C",
                    str(legacy_repo / ".claude"),
                    "show",
                    f"HEAD~1:{relative_path}",
                ],
                text=False,
                capture_output=True,
                check=False,
            )
            check(
                migrated_state.returncode == 0 and migrated_state.stdout == content,
                f"legacy migration commit must contain original consumer state {relative_path}",
                errors,
            )

        # D3: --state-remote persists AI_STATE_REMOTE into the committed
        # devcontainer config, since a fresh container clone has no other way
        # to learn a non-default state remote (.claude/ itself is gitignored).
        remote_repo = temp_dir_name and Path(temp_dir_name) / "state-remote.git"
        subprocess.run(["git", "init", "-q", "--bare", str(remote_repo)], check=False)
        remote_temp_repo = Path(temp_dir_name) / "consumer-with-remote"
        remote_temp_repo.mkdir()
        subprocess.run(
            ["git", "init", str(remote_temp_repo)],
            text=True,
            capture_output=True,
            check=False,
        )
        remote_install_result = subprocess.run(
            [
                sys.executable,
                str(installer),
                str(remote_temp_repo),
                "--state-remote",
                str(remote_repo),
            ],
            cwd=REPO_ROOT,
            env=install_env,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            remote_install_result.returncode == 0,
            f"installer --state-remote run failed: {remote_install_result.stderr}",
            errors,
        )
        check(
            f'"AI_STATE_REMOTE": "{remote_repo}"'
            in read(remote_temp_repo / ".devcontainer" / "devcontainer.json"),
            "installer must persist --state-remote into the devcontainer config",
            errors,
        )
        remote_branches = subprocess.run(
            [
                "git",
                "--git-dir",
                str(remote_repo),
                "for-each-ref",
                "refs/heads/ai-state",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            "refs/heads/ai-state" in remote_branches.stdout,
            "installer with --state-remote must push ai-state to that remote, not origin",
            errors,
        )

        default_batch = subprocess.run(
            [sys.executable, str(updater), "--skip-regen", str(remote_temp_repo)],
            cwd=REPO_ROOT,
            env=install_env,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            default_batch.returncode == 0,
            f"default updater run failed: {default_batch.stderr}",
            errors,
        )
        check_codex_hook_trust_notice(
            "default updater", default_batch.stdout, errors, dry_run=False
        )
        check(
            not any(trust_home.iterdir()),
            "updater must not write user-level trust state",
            errors,
        )

        dry_repo = Path(temp_dir_name) / "dry-run-consumer"
        dry_repo.mkdir()
        subprocess.run(["git", "init", "-q", str(dry_repo)], check=False)
        direct_dry_run = subprocess.run(
            [sys.executable, str(installer), str(dry_repo), "--dry-run"],
            cwd=REPO_ROOT,
            env=install_env,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            direct_dry_run.returncode == 0,
            f"installer dry-run failed: {direct_dry_run.stderr}",
            errors,
        )
        check_codex_hook_trust_notice(
            "installer dry-run", direct_dry_run.stdout, errors, dry_run=True
        )
        check(
            not (dry_repo / ".codex" / "hooks.json").exists(),
            "installer dry-run must not write hooks.json",
            errors,
        )

        batch_dry_run = subprocess.run(
            [sys.executable, str(updater), "--skip-regen", "--dry-run", str(dry_repo)],
            cwd=REPO_ROOT,
            env=install_env,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            batch_dry_run.returncode == 0,
            f"updater dry-run failed: {batch_dry_run.stderr}",
            errors,
        )
        check_codex_hook_trust_notice(
            "updater dry-run", batch_dry_run.stdout, errors, dry_run=True
        )
        check_batch_dry_run_summary(batch_dry_run.stdout, errors)
        check(
            not (dry_repo / ".codex" / "hooks.json").exists(),
            "updater dry-run must not write hooks.json",
            errors,
        )
        check(
            not any(trust_home.iterdir()),
            "dry runs must not write user-level trust state",
            errors,
        )

        local_only_batch_dry_run = subprocess.run(
            [
                sys.executable,
                str(updater),
                "--skip-regen",
                "--dry-run",
                "--local-only",
                str(dry_repo),
            ],
            cwd=REPO_ROOT,
            env=install_env,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            local_only_batch_dry_run.returncode == 0,
            f"local-only updater dry-run failed: {local_only_batch_dry_run.stderr}",
            errors,
        )
        check_codex_hook_trust_notice(
            "local-only updater dry-run",
            local_only_batch_dry_run.stdout,
            errors,
            dry_run=True,
        )
        check_batch_dry_run_summary(local_only_batch_dry_run.stdout, errors)

        # R-POLICY-01: installer substitutes the workspace project-name placeholder.
        installed_workspace = read(
            temp_repo / ".claude" / "instructions" / "workspace.instructions.md"
        )
        check(
            "[TODO: project name" not in installed_workspace,
            "installer must fill the workspace project-name placeholder",
            errors,
        )
        check(
            "**Project:** consumer" in installed_workspace,
            "installer must substitute the target repo name into the workspace instructions",
            errors,
        )

        # R-HOOKS-07: install must wire the deterministic commit-msg git hook.
        hooks_path_result = subprocess.run(
            ["git", "-C", str(temp_repo), "config", "core.hooksPath"],
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            hooks_path_result.stdout.strip() == ".claude/hooks/git-hooks",
            f"installer must set core.hooksPath to .claude/hooks/git-hooks (got {hooks_path_result.stdout.strip()!r})",
            errors,
        )
        commit_msg_hook = temp_repo / ".claude" / "hooks" / "git-hooks" / "commit-msg"
        check(
            commit_msg_hook.exists(),
            "installer must copy the commit-msg git hook",
            errors,
        )
        check(
            commit_msg_hook.exists() and bool(commit_msg_hook.stat().st_mode & 0o111),
            "installer must leave the commit-msg git hook executable",
            errors,
        )

        ignored_result = subprocess.run(
            ["git", "-C", str(temp_repo), "check-ignore", ".claude/MEMORY.md"],
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            ignored_result.returncode == 0,
            "installer must ignore generated .claude content",
            errors,
        )

        devcontainer_ignore_result = subprocess.run(
            [
                "git",
                "-C",
                str(temp_repo),
                "check-ignore",
                ".devcontainer/devcontainer.json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            devcontainer_ignore_result.returncode != 0,
            "installer must leave .devcontainer trackable",
            errors,
        )

        # R-SYNC-03: default install keeps the Copilot cloud surface ignored
        # (local-IDE only).
        copilot_ignored = subprocess.run(
            [
                "git",
                "-C",
                str(temp_repo),
                "check-ignore",
                ".github/agents/orchestrator.agent.md",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            copilot_ignored.returncode == 0,
            "default install must ignore the Copilot cloud surface (.github/agents)",
            errors,
        )

        # D5: root adapter files are mirrored into .claude/bootstrap-root/ so
        # state-sync.sh's checkout of .claude/ alone still carries them.
        for relative in ("CLAUDE.md", "AGENTS.md", ".mcp.json"):
            check(
                (temp_repo / ".claude" / "bootstrap-root" / relative).exists(),
                f"installer must mirror {relative} into .claude/bootstrap-root/",
                errors,
            )
        check(
            (temp_repo / ".claude" / "bootstrap-root" / ".github" / "agents").exists(),
            "installer must mirror the gitignored Copilot surface into .claude/bootstrap-root/ by default",
            errors,
        )

    # R-SYNC-03: --commit-copilot-surface keeps the Copilot surface trackable.
    with tempfile.TemporaryDirectory() as flag_dir_name:
        flag_repo = Path(flag_dir_name) / "consumer"
        flag_repo.mkdir()
        subprocess.run(
            ["git", "init", str(flag_repo)], text=True, capture_output=True, check=False
        )
        default_install = subprocess.run(
            [sys.executable, str(installer), str(flag_repo)],
            cwd=REPO_ROOT,
            env=git_identity_env,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            default_install.returncode == 0,
            f"default installer run before mode migration failed: {default_install.stderr}",
            errors,
        )
        check(
            (flag_repo / ".claude" / "bootstrap-root" / ".github" / "agents").exists(),
            "default install must seed the Copilot surface before mode migration",
            errors,
        )
        flag_install = subprocess.run(
            [
                sys.executable,
                str(installer),
                str(flag_repo),
                "--commit-copilot-surface",
            ],
            cwd=REPO_ROOT,
            env=git_identity_env,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            flag_install.returncode == 0,
            f"installer --commit-copilot-surface run failed: {flag_install.stderr}",
            errors,
        )
        gitignore_text = (
            read(flag_repo / ".gitignore")
            if (flag_repo / ".gitignore").exists()
            else ""
        )
        check(
            ".github/agents/" not in gitignore_text,
            "--commit-copilot-surface must omit .github/agents from the ignore block",
            errors,
        )
        surface_trackable = subprocess.run(
            [
                "git",
                "-C",
                str(flag_repo),
                "check-ignore",
                ".github/agents/orchestrator.agent.md",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            surface_trackable.returncode != 0,
            "--commit-copilot-surface must leave .github/agents trackable",
            errors,
        )
        check(
            not (flag_repo / ".claude" / "bootstrap-root" / ".github").exists(),
            "migrating to --commit-copilot-surface must remove the Copilot surface from .claude/bootstrap-root/",
            errors,
        )
        ownership_manifest = read(flag_repo / ".claude" / "bootstrap-ownership.env")
        check(
            "BOOTSTRAP_ROOT_PATH=.github/" not in ownership_manifest,
            "migrating to --commit-copilot-surface must remove Copilot paths from the restoration manifest",
            errors,
        )
        check(
            "BOOTSTRAP_ROOT_PATH=.codex\n" in ownership_manifest,
            "mode migration must preserve non-Copilot restoration manifest paths",
            errors,
        )
        check(
            "BOOTSTRAP_COMMIT_COPILOT_SURFACE=1\n" in ownership_manifest,
            "committed Copilot mode must be persisted as inert manifest data",
            errors,
        )

        committed_agent = flag_repo / ".github" / "agents" / "orchestrator.agent.md"
        subprocess.run(["git", "-C", str(flag_repo), "add", ".github"], check=False)
        write(committed_agent, "stale committed agent\n")
        repeat_flag_install = subprocess.run(
            [
                sys.executable,
                str(installer),
                str(flag_repo),
                "--commit-copilot-surface",
            ],
            cwd=REPO_ROOT,
            env=git_identity_env,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            repeat_flag_install.returncode == 0,
            f"repeat committed-surface install failed: {repeat_flag_install.stderr}",
            errors,
        )
        check(
            read(committed_agent)
            == read(TARGET_ROOT / ".github" / "agents" / "orchestrator.agent.md"),
            "repeat committed-surface installs must refresh tracked generated Copilot files",
            errors,
        )

        local_repo = Path(flag_dir_name) / "local-consumer"
        local_repo.mkdir()
        subprocess.run(["git", "init", "-q", str(local_repo)], check=False)
        local_install = subprocess.run(
            [sys.executable, str(installer), str(local_repo)],
            cwd=REPO_ROOT,
            env=git_identity_env,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            local_install.returncode == 0,
            f"local-surface fixture install failed: {local_install.stderr}",
            errors,
        )
        retained_batch = subprocess.run(
            [
                sys.executable,
                str(updater),
                "--skip-regen",
                "--dry-run",
                str(flag_repo),
                str(local_repo),
            ],
            cwd=REPO_ROOT,
            env=git_identity_env,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            retained_batch.returncode == 0,
            f"mixed-mode updater dry run failed: {retained_batch.stderr}",
            errors,
        )
        check(
            retained_batch.stdout.count("Copilot surface mode: committed (retained)")
            == 1
            and retained_batch.stdout.count(
                "Copilot surface mode: local-only (retained)"
            )
            == 1,
            "batch updates must retain each consumer's persisted Copilot mode",
            errors,
        )
        selected_batch = subprocess.run(
            [
                sys.executable,
                str(updater),
                "--skip-regen",
                "--dry-run",
                "--commit-copilot-surface",
                str(flag_repo),
                str(local_repo),
            ],
            cwd=REPO_ROOT,
            env=git_identity_env,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            selected_batch.returncode == 0
            and selected_batch.stdout.count(
                "Copilot surface mode: committed (explicit)"
            )
            == 2,
            "batch updates must forward an explicit Copilot mode to every consumer",
            errors,
        )
        # State still stays ignored regardless of the flag.
        state_ignored = subprocess.run(
            ["git", "-C", str(flag_repo), "check-ignore", ".claude/MEMORY.md"],
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            state_ignored.returncode == 0,
            "--commit-copilot-surface must still ignore .claude state",
            errors,
        )


def state_sync_script(consumer: Path) -> Path:
    # Mirrors post-start.sh: before .claude/ exists at all (a fresh clone
    # that has never run `setup`), the only reachable copy is the one
    # rendered into the trackable .devcontainer/.
    claude_copy = consumer / ".claude" / "hooks" / "scripts" / "state-sync.sh"
    if claude_copy.is_file():
        return claude_copy
    return consumer / ".devcontainer" / "state-sync.sh"


def run_state_sync(
    consumer: Path, mode: str, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(state_sync_script(consumer)), mode],
        cwd=consumer,
        env=env,
        text=True,
        capture_output=True,
        check=False,
        stdin=subprocess.DEVNULL,
    )


def validate_state_sync(errors: list[str]) -> None:
    """R-SYNC-05f: adversarial end-to-end coverage of the git-backed state
    sync mechanism (state-sync.sh) across two simulated "machines" sharing a
    bare origin, mirroring the manual acceptance procedure in
    plans/plan-git-state-sync.md Phase 6."""
    installer = REPO_ROOT / "scripts" / "install_bootstrap.py"
    with tempfile.TemporaryDirectory() as temp_dir_name:
        temp_root = Path(temp_dir_name)
        bare_origin = temp_root / "origin.git"
        subprocess.run(["git", "init", "-q", "--bare", str(bare_origin)], check=False)
        subprocess.run(
            [
                "git",
                "--git-dir",
                str(bare_origin),
                "symbolic-ref",
                "HEAD",
                "refs/heads/main",
            ],
            check=False,
        )

        # 1. Install on machine A: ai-state exists on the remote; nested repo checked out.
        machine_a = temp_root / "machine-a"
        subprocess.run(
            ["git", "clone", "-q", str(bare_origin), str(machine_a)],
            text=True,
            capture_output=True,
            check=False,
        )
        env_a = git_actor_env("MachineA")
        install_a = subprocess.run(
            [sys.executable, str(installer), str(machine_a)],
            cwd=REPO_ROOT,
            env=env_a,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            install_a.returncode == 0,
            f"[state-sync] install on machine A failed: {install_a.stderr}",
            errors,
        )
        subprocess.run(
            ["git", "-C", str(machine_a), "add", ".devcontainer", ".gitignore"],
            check=False,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(machine_a),
                "commit",
                "-q",
                "-m",
                "chore: add AI devcontainer bootstrap",
            ],
            env=env_a,
            check=False,
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(machine_a),
                "push",
                "-q",
                "origin",
                "HEAD:refs/heads/main",
            ],
            check=False,
        )

        remote_refs = subprocess.run(
            [
                "git",
                "--git-dir",
                str(bare_origin),
                "for-each-ref",
                "refs/heads/ai-state",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            "refs/heads/ai-state" in remote_refs.stdout,
            "[state-sync] install must push ai-state to the bare origin",
            errors,
        )
        check(
            (machine_a / ".claude" / ".git").is_dir(),
            "[state-sync] install must check out a nested .claude/ repo",
            errors,
        )

        # Phase A: checkpoint is a local-only commit boundary, while publish
        # transmits only an existing checkpoint. Trace2 distinguishes this
        # from a failed remote push or a lower-level Git rejection.
        checkpoint_relpath = Path("plans") / "checkpoint-only.md"
        checkpoint_path = machine_a / ".claude" / checkpoint_relpath
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_text("checkpointed locally\n", encoding="utf-8")
        checkpoint_trace = temp_root / "checkpoint-trace.json"
        checkpoint = run_state_sync(
            machine_a,
            "checkpoint",
            {**env_a, "GIT_TRACE2_EVENT": str(checkpoint_trace)},
        )
        remote_before_checkpoint_publish = subprocess.run(
            ["git", "--git-dir", str(bare_origin), "rev-parse", "ai-state"],
            text=True,
            capture_output=True,
            check=False,
        ).stdout.strip()
        check(
            checkpoint.returncode == 0,
            f"[state-sync] checkpoint failed: {checkpoint.stderr}",
            errors,
        )
        check(
            checkpoint.stdout == "",
            "[state-sync] checkpoint must not write stdout",
            errors,
        )
        check(
            not traced_remote_git_commands(checkpoint_trace, "checkpoint", errors),
            "[state-sync] checkpoint must not run fetch, ls-remote, pull, merge, or push",
            errors,
        )
        checkpoint_remote_before_publish = subprocess.run(
            [
                "git",
                "--git-dir",
                str(bare_origin),
                "show",
                f"ai-state:{checkpoint_relpath.as_posix()}",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            checkpoint_remote_before_publish.returncode != 0,
            "[state-sync] checkpoint must not publish its local commit",
            errors,
        )
        checkpoint_head = subprocess.run(
            ["git", "-C", str(machine_a / ".claude"), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            check=False,
        ).stdout.strip()
        checkpoint_count = subprocess.run(
            ["git", "-C", str(machine_a / ".claude"), "rev-list", "--count", "HEAD"],
            text=True,
            capture_output=True,
            check=False,
        ).stdout.strip()
        first_publish = run_state_sync(machine_a, "publish", env_a)
        second_publish = run_state_sync(machine_a, "publish", env_a)
        remote_after_publish = subprocess.run(
            ["git", "--git-dir", str(bare_origin), "rev-parse", "ai-state"],
            text=True,
            capture_output=True,
            check=False,
        ).stdout.strip()
        checkpoint_head_after_publish = subprocess.run(
            ["git", "-C", str(machine_a / ".claude"), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            check=False,
        ).stdout.strip()
        checkpoint_count_after_publish = subprocess.run(
            ["git", "-C", str(machine_a / ".claude"), "rev-list", "--count", "HEAD"],
            text=True,
            capture_output=True,
            check=False,
        ).stdout.strip()
        check(
            first_publish.returncode == 0 and second_publish.returncode == 0,
            "[state-sync] publish must exit zero",
            errors,
        )
        check(
            first_publish.stdout == second_publish.stdout == "",
            "[state-sync] publish must not write stdout",
            errors,
        )
        check(
            remote_after_publish != remote_before_checkpoint_publish,
            "[state-sync] publish must advance the remote with the checkpoint",
            errors,
        )
        check(
            checkpoint_head == checkpoint_head_after_publish == remote_after_publish
            and checkpoint_count == checkpoint_count_after_publish,
            "[state-sync] publish must not create another local commit and must be idempotent",
            errors,
        )

        dirty_publish_path = machine_a / ".claude" / "plans" / "uncheckpointed.md"
        dirty_publish_path.write_text("preserve this locally\n", encoding="utf-8")
        dirty_head = checkpoint_head_after_publish
        dirty_publish = run_state_sync(machine_a, "publish", env_a)
        dirty_remote = subprocess.run(
            ["git", "--git-dir", str(bare_origin), "rev-parse", "ai-state"],
            text=True,
            capture_output=True,
            check=False,
        ).stdout.strip()
        dirty_head_after = subprocess.run(
            ["git", "-C", str(machine_a / ".claude"), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            check=False,
        ).stdout.strip()
        check(
            dirty_publish.returncode == 0,
            "[state-sync] dirty publish must remain non-blocking",
            errors,
        )
        check(
            dirty_publish.stdout == "",
            "[state-sync] dirty publish must not write stdout",
            errors,
        )
        check(
            "dirty" in dirty_publish.stderr.lower(),
            "[state-sync] dirty publish must explain the checkpoint boundary",
            errors,
        )
        check(
            dirty_publish_path.read_text(encoding="utf-8") == "preserve this locally\n"
            and dirty_head == dirty_head_after
            and dirty_remote == remote_after_publish,
            "[state-sync] dirty publish must preserve files, HEAD, and the remote",
            errors,
        )
        run_state_sync(machine_a, "checkpoint", env_a)
        run_state_sync(machine_a, "publish", env_a)

        status_trace = temp_root / "status-trace.json"
        status = run_state_sync(
            machine_a,
            "status",
            {**env_a, "GIT_TRACE2_EVENT": str(status_trace)},
        )
        check(
            status.returncode == 0,
            f"[state-sync] status failed: {status.stderr}",
            errors,
        )
        check(
            "repository: initialized" in status.stdout
            and "worktree: clean" in status.stdout
            and "remote: configured" in status.stdout
            and "tracking: ahead=0 behind=0" in status.stdout
            and "error-log:" in status.stdout,
            "[state-sync] status must report initialized clean cached state and the error log",
            errors,
        )
        check(
            str(bare_origin) not in status.stdout,
            "[state-sync] status must not print the remote URL",
            errors,
        )
        check(
            not traced_remote_git_commands(status_trace, "status", errors),
            "[state-sync] status must not run fetch, ls-remote, pull, merge, or push",
            errors,
        )

        # A shared plan file with frontmatter, common to both machines from
        # here on, so step 4 below can conflict on one of its lines.
        plan_relpath = Path("plans") / "state-sync-test.md"
        (machine_a / ".claude" / plan_relpath).write_text(
            "---\nstatus: in-progress\n---\n\nShared baseline plan.\n",
            encoding="utf-8",
        )
        baseline_push = run_state_sync(machine_a, "push", env_a)
        check(
            baseline_push.returncode == 0,
            f"[state-sync] machine A baseline push failed: {baseline_push.stderr}",
            errors,
        )

        # 2. Machine B: clone fresh, setup && pull -> state present, byte-identical.
        machine_b = temp_root / "machine-b"
        subprocess.run(
            ["git", "clone", "-q", str(bare_origin), str(machine_b)],
            text=True,
            capture_output=True,
            check=False,
        )
        env_b = git_actor_env("MachineB")
        run_state_sync(machine_b, "setup", env_b)
        # F1 (§9): setup on a fresh, non-devcontainer clone (no post-start.sh)
        # must restore the root adapters carried in bootstrap-root/, not just
        # check out .claude/. Without setup calling restore-root-adapters.sh,
        # CLAUDE.md would never appear at the repo root outside the devcontainer.
        check(
            (machine_b / "CLAUDE.md").is_file(),
            "[state-sync] setup must restore root adapters (CLAUDE.md) from bootstrap-root/ on a fresh clone",
            errors,
        )
        pull_b = run_state_sync(machine_b, "pull", env_b)
        check(
            pull_b.returncode == 0,
            f"[state-sync] machine B setup+pull failed: {pull_b.stderr}",
            errors,
        )

        a_plan = machine_a / ".claude" / plan_relpath
        b_plan = machine_b / ".claude" / plan_relpath
        check(
            b_plan.exists()
            and a_plan.exists()
            and a_plan.read_bytes() == b_plan.read_bytes(),
            "[state-sync] machine B pull must restore state byte-identical to machine A",
            errors,
        )

        # 3. Divergence: different new files on A and B; B's push auto-rebases.
        (machine_a / ".claude" / "session_logs" / "a-only.md").write_text(
            "from A\n", encoding="utf-8"
        )
        push_a_divergent = run_state_sync(machine_a, "push", env_a)
        check(
            push_a_divergent.returncode == 0,
            f"[state-sync] machine A divergent push failed: {push_a_divergent.stderr}",
            errors,
        )

        (machine_b / ".claude" / "session_logs" / "b-only.md").write_text(
            "from B\n", encoding="utf-8"
        )
        push_b_divergent = run_state_sync(machine_b, "push", env_b)
        check(
            push_b_divergent.returncode == 0,
            f"[state-sync] machine B push must succeed after auto-rebasing divergent state: {push_b_divergent.stderr}",
            errors,
        )
        check(
            "WARN" not in (push_b_divergent.stdout + push_b_divergent.stderr),
            "[state-sync] a clean divergence must rebase without warning",
            errors,
        )
        check(
            (machine_b / ".claude" / "session_logs" / "a-only.md").exists(),
            "[state-sync] machine B must see machine A's file after its own push rebases",
            errors,
        )

        pull_a_final = run_state_sync(machine_a, "pull", env_a)
        check(
            pull_a_final.returncode == 0,
            "[state-sync] machine A final pull failed",
            errors,
        )
        check(
            (machine_a / ".claude" / "session_logs" / "b-only.md").exists(),
            "[state-sync] machine A must see machine B's divergent file after pulling",
            errors,
        )

        # 4. Conflict: same line of the same plan frontmatter changed on both,
        # neither having pulled the other's change first.
        (machine_a / ".claude" / plan_relpath).write_text(
            "---\nstatus: in-progress\n---\n\nEdited by A.\n",
            encoding="utf-8",
        )
        conflict_push_a = run_state_sync(machine_a, "push", env_a)
        check(
            conflict_push_a.returncode == 0,
            f"[state-sync] machine A conflict-setup push failed: {conflict_push_a.stderr}",
            errors,
        )

        (machine_b / ".claude" / plan_relpath).write_text(
            "---\nstatus: in-progress\n---\n\nEdited by B.\n",
            encoding="utf-8",
        )
        conflict_push_b = run_state_sync(machine_b, "push", env_b)
        check(
            conflict_push_b.returncode == 0,
            "[state-sync] a same-line conflict must still exit 0 (warn, not fail the session)",
            errors,
        )
        check(
            "WARN" in (conflict_push_b.stdout + conflict_push_b.stderr),
            "[state-sync] a same-line conflict must print a WARN naming the conflicting file",
            errors,
        )
        check(
            b_plan.read_text(encoding="utf-8")
            == "---\nstatus: in-progress\n---\n\nEdited by B.\n",
            "[state-sync] machine B's local file must be untouched after a failed rebase",
            errors,
        )
        remote_conflict_content = subprocess.run(
            [
                "git",
                "--git-dir",
                str(bare_origin),
                "show",
                f"ai-state:{plan_relpath.as_posix()}",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            remote_conflict_content.stdout
            == "---\nstatus: in-progress\n---\n\nEdited by A.\n",
            "[state-sync] the remote must still have machine A's version after B's conflicting push fails; nothing lost on either side",
            errors,
        )

        # 5. Stop-hook contract: stdin held open (as VS Code / an AI Stop hook
        # never closes it) must not hang past the 2-second drain.
        started = time.monotonic()
        stop_hook_process = subprocess.Popen(
            ["bash", str(state_sync_script(machine_a)), "push"],
            cwd=machine_a,
            env=env_a,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            stop_hook_process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            stop_hook_process.kill()
            stop_hook_process.communicate()
            check(
                False,
                "[state-sync] push must return promptly even with stdin held open (Stop-hook contract)",
                errors,
            )
        else:
            elapsed = time.monotonic() - started
            check(
                elapsed < 10,
                f"[state-sync] push with stdin held open took too long ({elapsed:.1f}s)",
                errors,
            )

        # 6. --state-remote: a fresh install's state lands on that remote, not origin.
        state_remote = temp_root / "state-remote.git"
        subprocess.run(["git", "init", "-q", "--bare", str(state_remote)], check=False)
        machine_c = temp_root / "machine-c"
        subprocess.run(
            ["git", "clone", "-q", str(bare_origin), str(machine_c)],
            text=True,
            capture_output=True,
            check=False,
        )
        env_c = git_actor_env("MachineC")
        install_c = subprocess.run(
            [
                sys.executable,
                str(installer),
                str(machine_c),
                "--state-remote",
                str(state_remote),
            ],
            cwd=REPO_ROOT,
            env=env_c,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            install_c.returncode == 0,
            f"[state-sync] install --state-remote on machine C failed: {install_c.stderr}",
            errors,
        )

        state_remote_refs = subprocess.run(
            [
                "git",
                "--git-dir",
                str(state_remote),
                "for-each-ref",
                "refs/heads/ai-state",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            "refs/heads/ai-state" in state_remote_refs.stdout,
            "[state-sync] --state-remote must push ai-state to the configured remote",
            errors,
        )
        # bare_origin already legitimately has ai-state from machine A/B above,
        # so the meaningful assertion is which remote machine C's OWN nested
        # repo is configured against, not whether bare_origin lacks ai-state.
        nested_remote_url = subprocess.run(
            ["git", "-C", str(machine_c / ".claude"), "remote", "get-url", "origin"],
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            nested_remote_url.stdout.strip() == str(state_remote),
            "[state-sync] --state-remote must configure the nested repo's own remote to that URL, not the outer repo's origin",
            errors,
        )


FORBIDDEN_LOCAL_ONLY_GIT_COMMANDS = {"fetch", "ls-remote", "pull", "merge", "push"}


def traced_remote_git_commands(
    trace_path: Path, label: str, errors: list[str]
) -> list[str]:
    """Return forbidden Git subcommands recorded by Git's JSON trace."""
    if not trace_path.is_file():
        check(False, f"[state-sync] {label} must emit a Git trace", errors)
        return []
    commands: list[str] = []
    start_events = 0
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            check(
                False,
                f"[state-sync] {label} emitted an invalid Git trace event",
                errors,
            )
            continue
        if event.get("event") != "start":
            continue
        start_events += 1
        argv = event.get("argv", [])
        if isinstance(argv, list):
            commands.extend(
                arg for arg in argv if arg in FORBIDDEN_LOCAL_ONLY_GIT_COMMANDS
            )
    check(
        start_events > 0,
        f"[state-sync] {label} Git trace must contain start events",
        errors,
    )
    return commands


def check_local_only_git_trace(label: str, trace_path: Path, errors: list[str]) -> None:
    commands = traced_remote_git_commands(trace_path, label, errors)
    check(
        not commands,
        f"[local-only] {label} invoked forbidden remote Git command(s): {commands}",
        errors,
    )


def validate_installer_commit_failure(errors: list[str]) -> None:
    """A failed legacy migration must stop before generated files replace state."""
    installer = REPO_ROOT / "scripts" / "install_bootstrap.py"
    with tempfile.TemporaryDirectory() as temp_dir_name:
        consumer = Path(temp_dir_name) / "legacy-consumer"
        consumer.mkdir()
        subprocess.run(["git", "init", "-q", str(consumer)], check=False)
        write(consumer / ".claude" / "MEMORY.md", "# Legacy state\n")
        failure_env = {
            **os.environ,
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_AUTHOR_NAME": "",
            "GIT_AUTHOR_EMAIL": "",
            "GIT_COMMITTER_NAME": "",
            "GIT_COMMITTER_EMAIL": "",
        }
        result = subprocess.run(
            [sys.executable, str(installer), str(consumer), "--local-only"],
            cwd=REPO_ROOT,
            env=failure_env,
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            result.returncode != 0,
            "installer must fail when legacy migration cannot commit",
            errors,
        )
        check(
            not (consumer / ".claude" / "hooks" / "scripts" / "state-sync.sh").exists(),
            "failed legacy migration must not replace state with generated files",
            errors,
        )


def validate_local_only_state_sync(errors: list[str]) -> None:
    """Local-only refreshes commit durable state without touching the remote."""
    installer = REPO_ROOT / "scripts" / "install_bootstrap.py"
    updater = REPO_ROOT / "scripts" / "update_consumers.py"
    with tempfile.TemporaryDirectory() as temp_dir_name:
        # install_bootstrap.py resolves its target path (expanduser().resolve())
        # before printing anything derived from it. On macOS tempfile hands back
        # a /var/... path while /var is a symlink to /private/var, so the
        # installer's "Publish later: ..." line comes back /private/var/...  —
        # resolve here too (same fix as setup_hook_repo above) or the expected
        # string built from an unresolved consumer path never matches.
        temp_root = Path(temp_dir_name).resolve()
        state_remote = temp_root / "state-remote.git"
        subprocess.run(["git", "init", "-q", "--bare", str(state_remote)], check=False)

        direct_pull_consumer = temp_root / "direct local-only pull"
        direct_pull_consumer.mkdir()
        subprocess.run(["git", "init", "-q", str(direct_pull_consumer)], check=False)
        shutil.copytree(
            TARGET_ROOT / ".devcontainer", direct_pull_consumer / ".devcontainer"
        )
        local_env = git_actor_env("LocalOnly")
        direct_pull_trace = temp_root / "direct-pull-trace.json"
        direct_pull = subprocess.run(
            [
                "bash",
                str(state_sync_script(direct_pull_consumer)),
                "pull",
                "--local-only",
            ],
            cwd=direct_pull_consumer,
            env={**local_env, "GIT_TRACE2_EVENT": str(direct_pull_trace)},
            text=True,
            capture_output=True,
            check=False,
            stdin=subprocess.DEVNULL,
        )
        check(
            direct_pull.returncode == 0,
            f"[local-only] direct pull failed: {direct_pull.stderr}",
            errors,
        )
        check(
            (direct_pull_consumer / ".claude" / ".git").is_dir(),
            "[local-only] direct pull must bootstrap nested ai-state before skipping remote sync",
            errors,
        )
        check_local_only_git_trace("direct pull", direct_pull_trace, errors)

        invalid_root_consumer = temp_root / "invalid root pull"
        invalid_root_consumer.mkdir()
        subprocess.run(["git", "init", "-q", str(invalid_root_consumer)], check=False)
        shutil.copytree(
            TARGET_ROOT / ".devcontainer", invalid_root_consumer / ".devcontainer"
        )
        invalid_root = temp_root / "not-a-directory"
        invalid_root_pull = subprocess.run(
            [
                "bash",
                str(state_sync_script(invalid_root_consumer)),
                "pull",
                "--local-only",
            ],
            cwd=invalid_root_consumer,
            env={**local_env, "AI_STATE_REPO_ROOT": str(invalid_root)},
            text=True,
            capture_output=True,
            check=False,
            stdin=subprocess.DEVNULL,
        )
        check(
            invalid_root_pull.returncode == 0,
            f"[local-only] invalid AI_STATE_REPO_ROOT must fall back: {invalid_root_pull.stderr}",
            errors,
        )
        check(
            "AI_STATE_REPO_ROOT=" in invalid_root_pull.stderr
            and "falling back to script-relative resolution"
            in invalid_root_pull.stderr,
            "[local-only] invalid AI_STATE_REPO_ROOT must warn before falling back",
            errors,
        )
        check(
            (invalid_root_consumer / ".claude" / ".git").is_dir(),
            "[local-only] invalid AI_STATE_REPO_ROOT must fall back to the consumer root",
            errors,
        )
        consumer = temp_root / "local only consumer"
        consumer.mkdir()
        subprocess.run(["git", "init", "-q", str(consumer)], check=False)
        fresh_trace = temp_root / "fresh-trace.json"
        fresh_install = subprocess.run(
            [
                sys.executable,
                str(installer),
                str(consumer),
                "--state-remote",
                str(state_remote),
                "--local-only",
            ],
            cwd=REPO_ROOT,
            env={**local_env, "GIT_TRACE2_EVENT": str(fresh_trace)},
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            fresh_install.returncode == 0,
            f"[local-only] fresh install failed: {fresh_install.stderr}",
            errors,
        )
        check_codex_hook_trust_notice(
            "local-only installer", fresh_install.stdout, errors, dry_run=False
        )
        check_local_only_git_trace("fresh install", fresh_trace, errors)
        remote_refs = subprocess.run(
            [
                "git",
                "--git-dir",
                str(state_remote),
                "for-each-ref",
                "refs/heads/ai-state",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            not remote_refs.stdout.strip(),
            "[local-only] fresh install must not push ai-state",
            errors,
        )
        fresh_bootstrap_root = subprocess.run(
            [
                "git",
                "-C",
                str(consumer / ".claude"),
                "show",
                "HEAD:bootstrap-root/CLAUDE.md",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            fresh_bootstrap_root.returncode == 0,
            "[local-only] fresh bootstrap commit must include bootstrap-root content",
            errors,
        )
        expected_push = f"Publish later: bash {shlex.quote(str(consumer / '.claude' / 'hooks' / 'scripts' / 'state-sync.sh'))} push"
        check(
            expected_push in fresh_install.stdout,
            "[local-only] installer must print a shell-safe manual push command",
            errors,
        )

        existing_trace = temp_root / "existing-trace.json"
        existing_install = subprocess.run(
            [
                sys.executable,
                str(installer),
                str(consumer),
                "--state-remote",
                str(state_remote),
                "--local-only",
            ],
            cwd=REPO_ROOT,
            env={**local_env, "GIT_TRACE2_EVENT": str(existing_trace)},
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            existing_install.returncode == 0,
            f"[local-only] existing install failed: {existing_install.stderr}",
            errors,
        )
        check_local_only_git_trace("existing install", existing_trace, errors)

        legacy = temp_root / "legacy consumer"
        legacy.mkdir()
        subprocess.run(["git", "init", "-q", str(legacy)], check=False)
        legacy_memory = "# Legacy memory\n\n- preserve local state\n"
        write(legacy / ".claude" / "MEMORY.md", legacy_memory)
        legacy_trace = temp_root / "legacy-trace.json"
        legacy_install = subprocess.run(
            [
                sys.executable,
                str(installer),
                str(legacy),
                "--state-remote",
                str(state_remote),
                "--local-only",
            ],
            cwd=REPO_ROOT,
            env={**local_env, "GIT_TRACE2_EVENT": str(legacy_trace)},
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            legacy_install.returncode == 0,
            f"[local-only] legacy install failed: {legacy_install.stderr}",
            errors,
        )
        check_local_only_git_trace("legacy install", legacy_trace, errors)
        history = subprocess.run(
            ["git", "-C", str(legacy / ".claude"), "log", "--reverse", "--format=%s"],
            text=True,
            capture_output=True,
            check=False,
        )
        subjects = history.stdout.splitlines()
        check(
            len(subjects) >= 2
            and subjects[0] == "migrate: import pre-git state"
            and subjects[1].startswith("bootstrap: update"),
            "[local-only] legacy refresh must commit migrate before bootstrap update",
            errors,
        )
        legacy_snapshot = subprocess.run(
            ["git", "-C", str(legacy / ".claude"), "show", "HEAD~1:MEMORY.md"],
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            legacy_snapshot.stdout == legacy_memory,
            "[local-only] legacy migration must preserve state before generated files replace it",
            errors,
        )
        legacy_bootstrap_root = subprocess.run(
            [
                "git",
                "-C",
                str(legacy / ".claude"),
                "show",
                "HEAD:bootstrap-root/CLAUDE.md",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            legacy_bootstrap_root.returncode == 0,
            "[local-only] legacy bootstrap commit must include bootstrap-root content",
            errors,
        )
        unchanged_remote = subprocess.run(
            [
                "git",
                "--git-dir",
                str(state_remote),
                "for-each-ref",
                "refs/heads/ai-state",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            not unchanged_remote.stdout.strip(),
            "[local-only] legacy migration must not push ai-state",
            errors,
        )

        updater_remote = temp_root / "updater-remote.git"
        subprocess.run(
            ["git", "init", "-q", "--bare", str(updater_remote)], check=False
        )
        updater_consumer = temp_root / "updater consumer"
        updater_consumer.mkdir()
        subprocess.run(["git", "init", "-q", str(updater_consumer)], check=False)
        subprocess.run(
            [
                "git",
                "-C",
                str(updater_consumer),
                "remote",
                "add",
                "origin",
                str(updater_remote),
            ],
            check=False,
        )
        updater_trace = temp_root / "updater-trace.json"
        update = subprocess.run(
            [
                sys.executable,
                str(updater),
                "--skip-regen",
                "--local-only",
                str(updater_consumer),
            ],
            cwd=REPO_ROOT,
            env={**local_env, "GIT_TRACE2_EVENT": str(updater_trace)},
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            update.returncode == 0,
            f"[local-only] updater failed: {update.stderr}",
            errors,
        )
        check_codex_hook_trust_notice(
            "local-only updater", update.stdout, errors, dry_run=False
        )
        check_local_only_git_trace("updater", updater_trace, errors)
        updater_refs = subprocess.run(
            [
                "git",
                "--git-dir",
                str(updater_remote),
                "for-each-ref",
                "refs/heads/ai-state",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        check(
            not updater_refs.stdout.strip(),
            "[local-only] updater must forward the no-push boundary",
            errors,
        )


def validate_determinism(errors: list[str]) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        output = Path(temp_dir) / "dist"
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "generate_targets.py"),
                "--all",
                "--output",
                str(output),
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            errors.append(
                f"temporary generation failed: {result.stderr or result.stdout}"
            )
            return
        compare_dirs(DIST_ROOT, output, errors)


def validate_ponytail_diff_classifier(errors: list[str]) -> None:
    """Only deterministic high-risk paths require Ponytail metadata in hooks."""
    library = TARGET_ROOT / ".claude" / "hooks" / "scripts" / "_lib-frontmatter.sh"
    with tempfile.TemporaryDirectory() as temp_dir:
        repo = Path(temp_dir) / "repo"
        repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "dev", str(repo)], check=False)
        env = git_actor_env("PonytailClassifier")
        write(repo / "README.md", "# Fixture\n")
        write(repo / ".codex" / "root-adapter.md", "# Adapter\n")
        subprocess.run(["git", "add", "."], cwd=repo, env=env, check=False)
        subprocess.run(
            ["git", "commit", "-q", "-m", "base"], cwd=repo, env=env, check=False
        )
        subprocess.run(
            ["git", "switch", "-q", "-c", "fixture_implementation"],
            cwd=repo,
            env=env,
            check=False,
        )

        def classifier_status(*refs: str) -> int:
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    '. "$1"; diff_requires_ponytail "$2" "${3:-}"',
                    "_",
                    str(library),
                    str(repo),
                    *refs,
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            return result.returncode

        write(repo / "README.md", "# Fixture\n\nDocs only.\n")
        docs_only = classifier_status()
        check(
            docs_only != 0,
            "Ponytail diff classifier must exempt a single documentation-only diff",
            errors,
        )
        git(repo, "checkout", "--", "README.md")

        write(repo / "app.py", "print('fixture')\n")
        subprocess.run(["git", "add", "."], cwd=repo, env=env, check=False)
        ordinary = classifier_status()
        check(
            ordinary != 0,
            "Ponytail diff classifier must keep one ordinary code file optional",
            errors,
        )
        git(repo, "reset", "app.py")
        (repo / "app.py").unlink()

        write(repo / "scripts" / "generate.py", "print('fixture')\n")
        git(repo, "add", "scripts/generate.py")
        generator = classifier_status()
        check(
            generator == 0,
            "Ponytail diff classifier must require review for scripts and generators",
            errors,
        )
        git(repo, "reset", "scripts/generate.py")
        (repo / "scripts" / "generate.py").unlink()

        write(repo / "docs" / "guide.md", "# Guide\n")
        write(repo / "README.md", "# Fixture\n\nSecond docs file.\n")
        git(repo, "add", "README.md", "docs/guide.md")
        multi_docs = classifier_status()
        check(
            multi_docs == 0,
            "Ponytail diff classifier must treat a multi-file docs diff as high-risk",
            errors,
        )
        git(repo, "reset", "README.md", "docs/guide.md")
        git(repo, "checkout", "--", "README.md")
        (repo / "docs" / "guide.md").unlink()

        write(repo / "README.md", "# Fixture\n\nMixed docs.\n")
        write(repo / "app.py", "print('mixed')\n")
        git(repo, "add", "README.md", "app.py")
        mixed = classifier_status()
        check(
            mixed == 0,
            "Ponytail diff classifier must treat a mixed docs/code diff as high-risk",
            errors,
        )
        git(repo, "reset", "README.md", "app.py")
        git(repo, "checkout", "--", "README.md")
        (repo / "app.py").unlink()

        write(repo / "pyproject.toml", "[project]\nname = 'fixture'\n")
        git(repo, "add", "pyproject.toml")
        dependency = classifier_status()
        check(
            dependency == 0,
            "Ponytail diff classifier must require review for dependency manifests",
            errors,
        )
        git(repo, "reset", "pyproject.toml")
        (repo / "pyproject.toml").unlink()

        write(repo / "service" / "pyproject.toml", "[project]\nname = 'service'\n")
        git(repo, "add", "service/pyproject.toml")
        nested_dependency = classifier_status()
        check(
            nested_dependency == 0,
            "Ponytail diff classifier must require review for nested dependency manifests",
            errors,
        )
        git(repo, "reset", "service/pyproject.toml")
        (repo / "service" / "pyproject.toml").unlink()

        write(repo / "frontend" / "package.json", '{"name": "frontend"}\n')
        git(repo, "add", "frontend/package.json")
        nested_package = classifier_status()
        check(
            nested_package == 0,
            "Ponytail diff classifier must require review for nested package manifests",
            errors,
        )
        git(repo, "reset", "frontend/package.json")
        (repo / "frontend" / "package.json").unlink()

        write(repo / "service" / "uv.lock", "version = 1\n")
        git(repo, "add", "service/uv.lock")
        nested_lockfile = classifier_status()
        check(
            nested_lockfile == 0,
            "Ponytail diff classifier must require review for nested lockfiles",
            errors,
        )
        git(repo, "reset", "service/uv.lock")
        (repo / "service" / "uv.lock").unlink()

        write(repo / "AGENTS.md", "# Control plane\n")
        git(repo, "add", "AGENTS.md")
        control_plane_markdown = classifier_status()
        check(
            control_plane_markdown == 0,
            "Ponytail diff classifier must not exempt a control-plane Markdown file",
            errors,
        )
        git(repo, "add", "AGENTS.md")
        subprocess.run(
            [
                "git",
                "commit",
                "-q",
                "-m",
                "control plane fixture",
            ],
            cwd=repo,
            env=env,
            check=False,
        )
        check(
            classifier_status("HEAD") == 0,
            "Ponytail diff classifier must apply the same rule to a pushed diff_ref",
            errors,
        )

        git(repo, "reset", "--hard", "dev")
        git(repo, "mv", ".codex/root-adapter.md", "ordinary-adapter.md")
        check(
            classifier_status() == 0,
            "Ponytail diff classifier must inspect both paths of a live control-plane rename",
            errors,
        )
        git(repo, "reset", "--hard", "dev")
        git(repo, "mv", ".codex/root-adapter.md", "ordinary-adapter.md")
        git(repo, "commit", "-q", "-m", "rename control-plane adapter")
        check(
            classifier_status("HEAD") == 0,
            "Ponytail diff classifier must inspect both paths of a pushed control-plane rename",
            errors,
        )

        git(repo, "reset", "--hard", "dev")
        write(repo / "service" / "pyproject.toml", "[project]\nname = 'service'\n")
        git(repo, "add", "service/pyproject.toml")
        git(repo, "commit", "-q", "-m", "add nested manifest")
        check(
            classifier_status("HEAD") == 0,
            "Ponytail diff classifier must require a nested manifest in diff_ref mode",
            errors,
        )


def validate_json_report_readers(errors: list[str]) -> None:
    """Report readers must ignore nested reserved keys and key order."""
    library = TARGET_ROOT / ".claude" / "hooks" / "scripts" / "_lib-frontmatter.sh"
    with tempfile.TemporaryDirectory() as temp_dir:
        report = Path(temp_dir) / "report.json"

        def values(payload: dict[str, object]) -> list[str]:
            write(report, json.dumps(payload) + "\n")
            result = subprocess.run(
                [
                    "bash",
                    "-c",
                    '. "$1"; json_file_bool_value "$2" ponytail_reviewed; '
                    'json_file_number_value "$2" counts.critical',
                    "_",
                    str(library),
                    str(report),
                ],
                text=True,
                capture_output=True,
                check=False,
            )
            check(
                result.returncode == 0,
                f"JSON report reader failed: {result.stderr}",
                errors,
            )
            return result.stdout.splitlines()

        nested_first = {
            "findings": [{"ponytail_reviewed": True, "critical": 9}],
            "ponytail_reviewed": False,
            "counts": {"critical": 0, "major": 0, "minor": 0},
        }
        check(
            values(nested_first) == ["false", "0"],
            "nested reserved metadata must not precede top-level false/zero fields",
            errors,
        )
        top_level_first = {
            "ponytail_reviewed": True,
            "counts": {"critical": 1, "major": 0, "minor": 0},
            "findings": [{"ponytail_reviewed": False, "critical": 0}],
        }
        check(
            values(top_level_first) == ["true", "1"],
            "nested reserved metadata must not override top-level true/count fields",
            errors,
        )


def validate_routing_table_parity(errors: list[str]) -> None:
    """R-AGENTS-05: the profile-routing table must have exactly one home. Its
    distinctive row marker may appear in only one shared source file
    (workspace.instructions.md); everything else references it by path."""
    marker = "Domain-specific correctness"
    owner = REPO_ROOT / "shared" / "policies" / "workspace.instructions.md"
    holders = sorted(
        path
        for path in (REPO_ROOT / "shared").rglob("*.md")
        if "__pycache__" not in path.parts and marker in read(path)
    )
    check(
        holders == [owner],
        "profile-routing table must live only in shared/policies/workspace.instructions.md; "
        f"found the routing marker in: {[str(p.relative_to(REPO_ROOT)) for p in holders]}",
        errors,
    )


def validate_root_source_mirror_cases(errors: list[str]) -> None:
    """Ignored self-install output is valid only while it matches generation."""
    with tempfile.TemporaryDirectory() as temp_dir_name:
        repo = Path(temp_dir_name) / "repo"
        target = Path(temp_dir_name) / "target"
        subprocess.run(["git", "init", "-q", str(repo)], check=False)
        write(target / ".github" / "agents" / "coder.agent.md", "generated\n")
        write(repo / ".github" / "agents" / "coder.agent.md", "generated\n")

        unignored = root_source_mirror_errors(repo, target)
        check(
            any("must be ignored" in error for error in unignored),
            "unignored legacy source mirror must be rejected even when byte-identical",
            errors,
        )

        write(repo / ".gitignore", ".github/agents/\n")
        check(
            not root_source_mirror_errors(repo, target),
            "byte-identical ignored self-install overlay must be allowed",
            errors,
        )

        write(repo / ".github" / "agents" / "coder.agent.md", "stale\n")
        stale = root_source_mirror_errors(repo, target)
        check(
            any("is stale" in error for error in stale),
            "stale ignored self-install overlay must be rejected",
            errors,
        )

        subprocess.run(
            ["git", "-C", str(repo), "add", "-f", ".github/agents/coder.agent.md"],
            check=False,
        )
        tracked = root_source_mirror_errors(repo, target)
        check(
            any("tracked legacy" in error for error in tracked),
            "tracked legacy source mirror must be rejected",
            errors,
        )


def validate_runtime_drift_cases(errors: list[str]) -> None:
    """Cover runtime ownership without mutating a consumer's state."""
    with tempfile.TemporaryDirectory() as temp_dir_name:
        repo = Path(temp_dir_name) / "repo"
        target = Path(temp_dir_name) / "target"
        workflow = "PRE-FLIGHT -> REVIEW -> DOCUMENT -> SCORE\n"
        write(target / "CLAUDE.md", workflow)
        write(target / ".codex" / "config.toml", "generated config\n")
        write(target / ".codex" / "agents" / "coder.toml", "generated agent\n")
        write(target / ".codex" / "hooks.json", "generated hook\n")
        write(
            target / ".claude" / "instructions" / "workflow.instructions.md", workflow
        )
        write(
            target / ".claude" / "instructions" / "workspace.instructions.md",
            "**Project:** [TODO: project name and one-liner description]\n",
        )
        write(target / ".claude" / "agents" / "orchestrator.md", workflow)
        write(
            repo / "AGENTS.md",
            "The source of truth lives in `shared/`.\nREVIEW -> DOCUMENT -> SCORE\n",
        )
        write(repo / "CLAUDE.md", workflow)
        write(repo / ".codex" / "config.toml", "tracked authoring config\n")
        write(repo / ".codex" / "agents" / "coder.toml", "generated agent\n")
        write(repo / ".codex" / "hooks.json", "generated hook\n")
        write(repo / ".claude" / "instructions" / "workflow.instructions.md", workflow)
        write(
            repo / ".claude" / "instructions" / "workspace.instructions.md",
            "**Project:** repo\n",
        )
        write(repo / ".claude" / "agents" / "orchestrator.md", workflow)
        write(repo / ".claude" / "bootstrap-root" / "CLAUDE.md", workflow)
        write(
            repo / ".claude" / "bootstrap-root" / ".codex" / "agents" / "coder.toml",
            "generated agent\n",
        )
        write(
            repo / ".claude" / "bootstrap-root" / ".codex" / "hooks.json",
            "generated hook\n",
        )
        write(repo / ".claude" / "MEMORY.md", "consumer-owned\n")
        subprocess.run(["git", "init", "-q", str(repo)], check=False)
        subprocess.run(
            ["git", "-C", str(repo), "add", ".codex/config.toml"], check=False
        )

        before = {
            path.relative_to(repo): path.read_bytes()
            for path in repo.rglob("*")
            if path.is_file()
        }
        initial_runtime_errors = runtime_drift_errors(repo, target)
        check(
            not initial_runtime_errors,
            "runtime parity must allow documented project substitution and "
            f"consumer-owned state: {initial_runtime_errors}",
            errors,
        )
        after = {
            path.relative_to(repo): path.read_bytes()
            for path in repo.rglob("*")
            if path.is_file()
        }
        check(before == after, "runtime parity checks must be read-only", errors)

        write(repo / ".codex" / "agents" / "coder.toml", "stale agent\n")
        write(repo / ".codex" / "hooks.json", "stale hook\n")
        stale_generated = runtime_drift_errors(repo, target)
        check(
            any(".codex/agents/coder.toml" in error for error in stale_generated)
            and any(".codex/hooks.json" in error for error in stale_generated),
            "runtime parity must refresh generated siblings beside tracked authoring files",
            errors,
        )
        write(repo / ".codex" / "agents" / "coder.toml", "generated agent\n")
        write(repo / ".codex" / "hooks.json", "generated hook\n")

        write(repo / "CLAUDE.md", "stale overlay\n")
        stale_overlay = runtime_drift_errors(repo, target)
        check(
            any(
                "CLAUDE.md" in error
                and "authoritative source" in error
                and "install_bootstrap.py" in error
                for error in stale_overlay
            ),
            "stale ignored overlay diagnostics must name its path, source, and reinstall action",
            errors,
        )

        write(
            repo / "AGENTS.md",
            "The source of truth lives in `shared/`.\nREVIEW -> SCORE -> DOCUMENT\n",
        )
        authoring = runtime_drift_errors(repo, target)
        check(
            any(
                error.startswith("stale runtime path: AGENTS.md") for error in authoring
            ),
            "tracked authoring guidance must be checked by workflow invariants",
            errors,
        )

        write(repo / ".claude" / "instructions" / "removed.instructions.md", "old\n")
        write(repo / ".codex" / "agents" / "removed.toml", "old\n")
        write(
            repo / ".claude" / "bootstrap-root" / ".codex" / "agents" / "removed.toml",
            "old\n",
        )
        obsolete = runtime_drift_errors(repo, target)
        check(
            any(
                error.startswith(
                    "stale runtime path: .claude/instructions/removed.instructions.md"
                )
                for error in obsolete
            )
            and any(
                error.startswith("stale runtime path: .codex/agents/removed.toml")
                for error in obsolete
            )
            and any(
                error.startswith(
                    "stale runtime path: .claude/bootstrap-root/.codex/agents/removed.toml"
                )
                for error in obsolete
            ),
            "runtime parity must detect files removed from generated ownership-controlled trees",
            errors,
        )

        generated = Path(temp_dir_name) / "generated"
        install_target = Path(temp_dir_name) / "install-target"
        write(generated / "AGENTS.md", "generated adapter\n")
        write(generated / ".codex" / "config.toml", "generated config\n")
        write(generated / ".codex" / "agents" / "coder.toml", "generated agent\n")
        write(install_target / "AGENTS.md", "tracked authoring adapter\n")
        write(install_target / ".codex" / "config.toml", "tracked config\n")
        write(install_target / ".codex" / "agents" / "coder.toml", "stale agent\n")
        write(install_target / ".codex" / "agents" / "removed.toml", "obsolete\n")
        write(
            install_target / ".claude" / "instructions" / "removed.instructions.md",
            "obsolete\n",
        )
        write(install_target / ".claude" / "MEMORY.md", "consumer-owned\n")
        subprocess.run(["git", "init", "-q", str(install_target)], check=False)
        subprocess.run(
            [
                "git",
                "-C",
                str(install_target),
                "add",
                "AGENTS.md",
                ".codex/config.toml",
            ],
            check=False,
        )
        copy_generated_tree(generated, install_target, dry_run=False)
        check(
            read(install_target / "AGENTS.md") == "tracked authoring adapter\n",
            "installer must preserve a tracked source adapter during dogfood refresh",
            errors,
        )
        check(
            read(install_target / ".codex" / "config.toml") == "tracked config\n"
            and read(install_target / ".codex" / "agents" / "coder.toml")
            == "generated agent\n",
            "installer must preserve a tracked adapter file while refreshing generated siblings",
            errors,
        )
        check(
            not (install_target / ".codex" / "agents" / "removed.toml").exists()
            and not (
                install_target / ".claude" / "instructions" / "removed.instructions.md"
            ).exists(),
            "installer merges must remove obsolete ownership-controlled files",
            errors,
        )
        check(
            read(install_target / ".claude" / "MEMORY.md") == "consumer-owned\n",
            "obsolete-file cleanup must preserve consumer state",
            errors,
        )


def validate_hook_gate_regression_tests(errors: list[str]) -> None:
    """CI (.github/workflows/validate.yml) only runs this file, not `pytest` —
    pytest isn't even installed by this repo's own dependency set. Without
    this, tests/test_hook_gates.py (unit coverage for git_targets_nested_claude's
    per-invocation scoping and protect-files.sh's secret-basename check) would
    only ever run when someone remembers to invoke it by hand, silently
    losing its regression value the moment that's forgotten."""
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "tests" / "test_hook_gates.py")],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    check(
        result.returncode == 0,
        f"tests/test_hook_gates.py failed:\n{result.stdout}{result.stderr}",
        errors,
    )


def main() -> int:
    errors: list[str] = []
    for target in TARGETS:
        check(
            (DIST_ROOT / target).exists(), f"missing generated target: {target}", errors
        )

    if not errors:
        validate_task_lane_contract(errors)
        validate_codex_model_contract_cases(errors)
        validate_agents(errors)
        validate_model_leaks(errors)
        validate_mcp_and_hooks(errors)
        validate_context_mode_tool_surface(errors)
        validate_skills_and_paths(errors)
        validate_docs_parity(errors)
        validate_memory_security_authority(errors)
        validate_routing_table_parity(errors)
        validate_root_source_mirror_cases(errors)
        validate_runtime_drift_cases(errors)
        validate_ponytail_diff_classifier(errors)
        validate_json_report_readers(errors)
        validate_devcontainer_and_installer(errors)
        validate_state_sync(errors)
        validate_installer_commit_failure(errors)
        validate_local_only_state_sync(errors)
        validate_determinism(errors)
        validate_hook_gate_regression_tests(errors)

    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1

    print("PASS generated target is structurally valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
