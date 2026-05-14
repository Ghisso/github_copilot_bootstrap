#!/usr/bin/env python3
"""Generate target-native bootstrap files from shared source files."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "dist"
TARGETS = ("multi-agent",)
OBSOLETE_TARGETS = ("github-copilot", "claude-code", "openai-codex")
COPY_IGNORE_PARTS = {".git", "__pycache__"}
COPY_IGNORE_SUFFIXES = {".pyc"}
SHARED_BASIS_NAMESPACE = ".claude"

CLAUDE_TOOL_MAP = {
    "read": ["Read"],
    "search": ["Grep", "Glob"],
    "edit": ["Edit", "MultiEdit", "Write"],
    "execute": ["Bash"],
    "delegate": ["Task"],
    "todo": ["TodoWrite"],
    "web": ["WebFetch", "WebSearch"],
}
COPILOT_TOOL_MAP = {
    "read": ["read"],
    "search": ["search"],
    "edit": ["edit"],
    "execute": ["execute"],
    "delegate": ["agent"],
    "todo": ["todo", "todos"],
    "web": ["web"],
    "vscode": ["vscode"],
}
TARGET_PATH_REPLACEMENTS = {
    "claude-code": (
        (".github/copilot-instructions.md", "CLAUDE.md"),
        ('normalized.endswith("/.github/copilot-instructions.md")', 'normalized.endswith("/CLAUDE.md")'),
        (".github/hooks/hooks.json", ".claude/settings.json"),
        (".github/hooks", ".claude/hooks"),
        ("git add .github/", "git add .claude/"),
        ("copilot-instructions.md", "CLAUDE.md"),
    ),
    "openai-codex": (
        (".github/copilot-instructions.md", "AGENTS.md"),
        ('normalized.endswith("/.github/copilot-instructions.md")', 'normalized.endswith("/AGENTS.md")'),
        (".github/hooks/hooks.json", ".codex/hooks.json"),
        (".github/hooks", ".codex/hooks"),
        ("git add .github/", "git add .claude/"),
        ("copilot-instructions.md", "AGENTS.md"),
    ),
}


def load_json_yaml(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, indent=2, sort_keys=False) + "\n")


def copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, ignore=copy_ignore)


def copy_ignore(directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        path = Path(directory) / name
        if name in COPY_IGNORE_PARTS or path.suffix in COPY_IGNORE_SUFFIXES:
            ignored.add(name)
    return ignored


def copy_skills(source: Path, destination: Path, target: str) -> None:
    copy_tree(source, destination)
    if target == "github-copilot":
        return
    for path in destination.rglob("*"):
        if path.suffix not in {".md", ".py", ".sh"}:
            continue
        text = path.read_text(encoding="utf-8")
        path.write_text(transform_target_paths(text, target), encoding="utf-8")


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def copy_text_transformed(source: Path, destination: Path, target: str) -> None:
    write_text(destination, transform_target_paths(source.read_text(encoding="utf-8"), target))


def copy_tree_transformed(source: Path, destination: Path, target: str) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for path in sorted(source.rglob("*")):
        if any(part in COPY_IGNORE_PARTS for part in path.parts) or path.suffix in COPY_IGNORE_SUFFIXES:
            continue
        relative = path.relative_to(source)
        target_path = destination / relative
        if path.is_dir():
            target_path.mkdir(parents=True, exist_ok=True)
        elif path.suffix in {".md", ".py", ".sh", ".json"}:
            copy_text_transformed(path, target_path, target)
            shutil.copymode(path, target_path)
        else:
            copy_file(path, target_path)


def render_shared_basis(target_root: Path, target: str) -> None:
    support_root = target_root / SHARED_BASIS_NAMESPACE
    target_label = {
        "github-copilot": "GitHub Copilot",
        "claude-code": "Claude Code",
        "openai-codex": "OpenAI Codex",
        "multi-agent": "multi-agent",
    }[target]

    copy_text_transformed(REPO_ROOT / "shared" / "MEMORY.md", support_root / "MEMORY.md", "claude-code")
    copy_tree_transformed(REPO_ROOT / "shared" / "templates", support_root / "templates", "claude-code")
    copy_text_transformed(
        REPO_ROOT / "shared" / "scripts" / "quality_score.py",
        support_root / "scripts" / "quality_score.py",
        "claude-code",
    )

    for name in ("plans", "quality_reports", "session_logs"):
        source = REPO_ROOT / "shared" / name / "README.md"
        copy_text_transformed(source, support_root / name / "README.md", "claude-code")

    write_text(
        support_root / "explorations" / "README.md",
        f"# Explorations\n\n"
        f"This directory stores exploratory or proof-of-concept plans created during {target_label} sessions.\n\n"
        "Use implementation plans for ready-to-execute work, and explorations when the work still needs "
        "research, feasibility checks, or throwaway prototypes.\n",
    )

    instructions_root = support_root / "instructions"
    instructions_root.mkdir(parents=True, exist_ok=True)
    for source in sorted((REPO_ROOT / "shared" / "policies").glob("*.instructions.md")):
        copy_text_transformed(source, instructions_root / source.name, "claude-code")
    write_text(
        instructions_root / "workspace.md",
        transform_agent_text(
            (REPO_ROOT / "shared" / "policies" / "workspace.instructions.md").read_text(
                encoding="utf-8"
            ),
            "claude-code",
        ),
    )

    copy_skills(REPO_ROOT / "shared" / "skills", support_root / "skills", "claude-code")
    copy_tree_transformed(REPO_ROOT / "shared" / "review-profiles", support_root / "review-profiles", "claude-code")
    copy_tree(REPO_ROOT / "shared" / "hooks" / "scripts", support_root / "hooks" / "scripts")
    copy_tree(REPO_ROOT / "shared" / "prompts", support_root / "prompts")
    render_claude_agents(target_root)


def reset_target(output_root: Path, target: str) -> Path:
    target_root = output_root / target
    if target_root.exists():
        shutil.rmtree(target_root)
    target_root.mkdir(parents=True)
    return target_root


def remove_obsolete_targets(output_root: Path) -> None:
    for target in OBSOLETE_TARGETS:
        target_root = output_root / target
        if target_root.exists():
            shutil.rmtree(target_root)


def shared_agents() -> list[tuple[dict[str, Any], Path]]:
    agents_root = REPO_ROOT / "shared" / "agents"
    agents: list[tuple[dict[str, Any], Path]] = []
    for metadata_path in sorted(agents_root.glob("*/agent.yaml")):
        agents.append((load_json_yaml(metadata_path), metadata_path.parent))
    return agents


def mapped_agent_name(agent_id: str, target: str) -> str:
    return agent_id


def transform_agent_text(text: str, target: str) -> str:
    transformed = text
    if target == "claude-code":
        transformed = transformed.replace("GPT-5.4", "Claude target-native primary review")
        transformed = transformed.replace("Claude Sonnet 4.6", "Claude target-native adversarial review")
        transformed = transformed.replace("Claude Opus 4.6 (copilot)", "Claude Code default model")
        transformed = transformed.replace("Claude Opus 4.6", "Claude Code default model")
        transformed = transformed.replace("Claude Sonnet 4.6 (copilot)", "Claude Code default model")
        transformed = transformed.replace("(copilot)", "")
    elif target == "openai-codex":
        transformed = transformed.replace("GPT-5.4", "Codex target-native primary review")
        transformed = transformed.replace("Claude Sonnet 4.6", "Codex target-native adversarial review")
        transformed = transformed.replace("Claude Opus 4.6 (copilot)", "Codex default model")
        transformed = transformed.replace("Claude Opus 4.6", "Codex default model")
        transformed = transformed.replace("Claude Sonnet 4.6 (copilot)", "Codex default model")
        transformed = transformed.replace("(copilot)", "")
    return transform_target_paths(transformed, target)


def transform_target_paths(text: str, target: str) -> str:
    transformed = text
    for old, new in TARGET_PATH_REPLACEMENTS.get(target, ()):
        transformed = transformed.replace(old, new)
    return transformed


def render_claude_tools(capabilities: list[str]) -> str:
    tools: list[str] = []
    for capability in capabilities:
        for tool_name in CLAUDE_TOOL_MAP.get(capability, []):
            if tool_name not in tools:
                tools.append(tool_name)
    return ", ".join(tools)


def render_copilot_tools(capabilities: list[str]) -> list[str]:
    tools: list[str] = []
    for capability in capabilities:
        for tool_name in COPILOT_TOOL_MAP.get(capability, []):
            if tool_name not in tools:
                tools.append(tool_name)
    return tools


def toml_string(value: str) -> str:
    return json.dumps(value)


def toml_multiline_literal(value: str) -> str:
    if "'''" in value:
        raise ValueError("Codex agent developer_instructions cannot contain triple single quotes")
    return "'''\n" + value.strip() + "\n'''"


def codex_sandbox_mode(capabilities: list[str]) -> str | None:
    if not capabilities:
        return None
    if "edit" not in capabilities and "execute" not in capabilities:
        return "read-only"
    return None


def shared_mcp_servers() -> dict[str, Any]:
    data = load_json_yaml(REPO_ROOT / "shared" / "mcp" / "servers.yaml")
    return data["servers"]


def shared_skill_names() -> list[str]:
    return sorted(path.parent.name for path in (REPO_ROOT / "shared" / "skills").glob("*/SKILL.md"))


def render_vscode_mcp_json(path: Path) -> None:
    write_json(path, {"servers": shared_mcp_servers()})


def render_claude_mcp_json(path: Path) -> None:
    write_json(path, {"mcpServers": shared_mcp_servers()})


def render_codex_config(path: Path) -> None:
    lines = [
        "# Generated from shared/mcp/servers.yaml.",
        "# Skills are sourced from the shared .claude basis; project trust is required.",
        "# Semble and context-mode are optional; missing binaries should warn, not block.",
        "",
        "[features]",
        "codex_hooks = true",
        "",
        "[agents]",
        "max_threads = 6",
        "max_depth = 1",
        "",
    ]
    for name, server in shared_mcp_servers().items():
        lines.append(f"[mcp_servers.{name}]")
        lines.append(f'command = "{server["command"]}"')
        if "args" in server:
            args = ", ".join(json.dumps(arg) for arg in server["args"])
            lines.append(f"args = [{args}]")
        lines.append("")
    for skill_name in shared_skill_names():
        lines.append("[[skills.config]]")
        lines.append(f"path = {toml_string(f'../.claude/skills/{skill_name}')}")
        lines.append("enabled = true")
        lines.append("")
    write_text(path, "\n".join(lines))


def render_claude_settings(path: Path) -> None:
    settings = {
        "permissions": {
            "deny": [
                "Read(./.env)",
                "Read(./.env.*)",
                "Read(./secrets/**)",
                "Read(./config/credentials.json)",
            ]
        },
        "hooks": {
            "SessionStart": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/scripts/session-log.sh claude-code",
                            "timeout": 10,
                        },
                        {
                            "type": "command",
                            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/scripts/context-mode-dispatch.sh claude-code sessionstart",
                            "timeout": 10,
                        },
                    ]
                }
            ],
            "PreToolUse": [
                {
                    "matcher": "Edit|MultiEdit|Write|Bash",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/scripts/protect-files.sh claude-code",
                            "timeout": 10,
                        },
                        {
                            "type": "command",
                            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/scripts/git-protection.sh",
                            "timeout": 10,
                        },
                        {
                            "type": "command",
                            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/scripts/context-mode-dispatch.sh claude-code pretooluse",
                            "timeout": 10,
                        },
                    ],
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/scripts/context-mode-dispatch.sh claude-code posttooluse",
                            "timeout": 10,
                        }
                    ],
                }
            ],
            "PreCompact": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/scripts/context-mode-dispatch.sh claude-code precompact",
                            "timeout": 10,
                        }
                    ]
                }
            ],
            "Stop": [
                {
                    "hooks": [
                        {
                            "type": "command",
                            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/scripts/session-log.sh claude-code",
                            "timeout": 10,
                        }
                    ]
                }
            ],
        },
    }
    write_json(path, settings)


def render_codex_hooks(path: Path) -> None:
    def command(script: str, *args: str) -> str:
        suffix = " ".join(args)
        executable = f'"$(git rev-parse --show-toplevel)/.claude/hooks/scripts/{script}"'
        return f"{executable} {suffix}".rstrip()

    hooks = {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "startup|resume|clear",
                    "hooks": [
                        {"type": "command", "command": command("session-log.sh", "openai-codex"), "timeout": 10},
                        {
                            "type": "command",
                            "command": command("context-mode-dispatch.sh", "openai-codex", "sessionstart"),
                            "timeout": 10,
                        },
                    ],
                }
            ],
            "PreToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {"type": "command", "command": command("protect-files.sh", "openai-codex"), "timeout": 10},
                        {"type": "command", "command": command("git-protection.sh"), "timeout": 10},
                        {
                            "type": "command",
                            "command": command("context-mode-dispatch.sh", "openai-codex", "pretooluse"),
                            "timeout": 10,
                        },
                    ],
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        {
                            "type": "command",
                            "command": command("context-mode-dispatch.sh", "openai-codex", "posttooluse"),
                            "timeout": 10,
                        }
                    ],
                }
            ],
            "Stop": [
                {
                    "hooks": [
                        {"type": "command", "command": command("session-log.sh", "openai-codex"), "timeout": 10}
                    ]
                }
            ],
        },
    }
    write_json(path, hooks)


def render_root_guidance(target: str) -> str:
    workspace = (REPO_ROOT / "shared" / "policies" / "workspace.instructions.md").read_text(
        encoding="utf-8"
    )
    routing = (REPO_ROOT / "shared" / "policies" / "tool-routing.instructions.md").read_text(
        encoding="utf-8"
    )
    workflow = (REPO_ROOT / "shared" / "policies" / "workflow.instructions.md").read_text(
        encoding="utf-8"
    )
    quality = (
        REPO_ROOT / "shared" / "policies" / "quality-and-testing.instructions.md"
    ).read_text(encoding="utf-8")
    if target == "claude-code":
        title = "Claude Code Bootstrap Guidance"
        agent_note = (
            "`.claude/` is the canonical shared project space. Custom agents are rendered as "
            "Claude Code project subagents in `.claude/agents/`; skills, plans, session logs, "
            "quality reports, memory, templates, and hook scripts also live under `.claude/`."
        )
    else:
        title = "OpenAI Codex Bootstrap Guidance"
        agent_note = (
            "`.claude/` is the canonical shared project space for skills, plans, session logs, "
            "quality reports, memory, templates, and hook scripts. Codex discovers those skills "
            "through `.codex/config.toml`, so trust this project before expecting project skill "
            "wiring and hooks to load. Custom agents stay as thin Codex adapters in "
            "`.codex/agents/*.toml` and point back to `.claude/agents/`."
        )
    return (
        f"# {title}\n\n"
        "This target is generated from `shared/`. Do not edit generated files manually.\n\n"
        "Preserve the plan -> implement -> verify -> review -> score workflow and hook guardrails.\n\n"
        f"{agent_note}\n\n"
        "## Workspace\n\n"
        f"{transform_target_paths(section_body(workspace), target)}\n\n"
        "## Tool Routing\n\n"
        f"{transform_target_paths(section_body(routing), target)}\n\n"
        "## Workflow\n\n"
        f"{transform_target_paths(section_body(workflow), target)}\n\n"
        "## Quality And Testing\n\n"
        f"{transform_target_paths(section_body(quality), target)}\n"
    )


def strip_frontmatter(text: str) -> str:
    if text.startswith("---\n"):
        parts = text.split("---\n", 2)
        if len(parts) == 3:
            return parts[2].lstrip()
    return text


def section_body(text: str) -> str:
    body = strip_frontmatter(text).lstrip()
    lines = body.splitlines()
    if lines and lines[0].startswith("# "):
        return "\n".join(lines[1:]).lstrip()
    return body


def split_frontmatter(text: str) -> tuple[str | None, str]:
    if not text.startswith("---\n"):
        return None, text
    parts = text.split("---\n", 2)
    if len(parts) != 3:
        return None, text
    return parts[1].strip(), parts[2].lstrip()


def canonical_agent_name(agent_id: str) -> str:
    return mapped_agent_name(agent_id, "claude-code")


def canonical_agent_path(agent_id: str) -> str:
    return f".claude/agents/{canonical_agent_name(agent_id)}.md"


def render_copilot_instructions() -> str:
    return """# GitHub Copilot Workspace Adapter

This target is generated from `shared/`. Do not edit generated files manually.

`.claude/` is the canonical shared project space for all AI systems in this repo. Use it for skills, plans, explorations, session logs, quality reports, memory, templates, prompts, shared agent bodies, and hook scripts.

Native Copilot files under `.github/` are adapters:

- `.github/instructions/*.instructions.md` preserves Copilot discovery and points to `.claude/instructions/`.
- `.github/agents/*.agent.md` preserves Copilot agent metadata and points to `.claude/agents/`.
- `.github/hooks/hooks.json` invokes shared hook scripts in `.claude/hooks/scripts/`.

Before planning or implementation, load the relevant canonical instruction files from `.claude/instructions/`, especially `workflow.instructions.md`, `quality-and-testing.instructions.md`, and `tool-routing.instructions.md`.

Preserve the plan -> implement -> verify -> review -> score workflow. Write all plans, session logs, exploration notes, memory updates, and quality reports under `.claude/`, not target-local `.github/` or `.codex/` state directories.
"""


def render_github_instruction_adapter(source: Path) -> str:
    frontmatter, body = split_frontmatter(source.read_text(encoding="utf-8"))
    title = source.stem.replace(".instructions", "").replace("-", " ").title()
    for line in body.splitlines():
        if line.startswith("# "):
            title = line[2:].strip()
            break
    adapter = (
        f"# {title} Adapter\n\n"
        f"This Copilot instruction file is a native discovery adapter. "
        f"Read and follow the canonical shared instruction at `.claude/instructions/{source.name}`.\n\n"
        "Critical shared-state rule: plans, explorations, session logs, memory, and quality reports "
        "belong under `.claude/` for every AI target.\n"
    )
    if frontmatter:
        return f"---\n{frontmatter}\n---\n\n{adapter}"
    return adapter


def render_github_agent_adapter(agent: dict[str, Any]) -> str:
    frontmatter_lines = [
        "---",
        f"name: {agent['id']}",
        f"description: {json.dumps(agent['description'])}",
    ]
    github_model = agent.get("model_intent", {}).get("github-copilot")
    if github_model and github_model != "target-default":
        frontmatter_lines.append(f"model: {github_model}")
    tools = render_copilot_tools(agent.get("capabilities", []))
    if tools:
        frontmatter_lines.append("tools:")
        frontmatter_lines.extend(f"  - {tool}" for tool in tools)
    delegates = agent.get("delegates", [])
    if delegates:
        frontmatter_lines.append("agents:")
        frontmatter_lines.extend(f"  - {delegate}" for delegate in delegates)
    if agent.get("visibility") == "hidden":
        frontmatter_lines.append("user-invocable: false")
    frontmatter_lines.append("---")
    canonical_path = canonical_agent_path(agent["id"])
    body = (
        f"# {agent['id']} Copilot Adapter\n\n"
        "This file is the GitHub Copilot native adapter for the shared agent body.\n\n"
        f"Before doing the task, read `{canonical_path}` and follow that canonical role guidance. "
        "Use the Copilot model, tools, delegation, and visibility metadata in this file when it "
        "conflicts with Claude-specific frontmatter in the canonical file.\n\n"
        "Shared skills, memory, plans, explorations, session logs, quality reports, templates, "
        "prompts, and hook scripts live under `.claude/`.\n"
    )
    return "\n".join(frontmatter_lines) + "\n\n" + body


def render_claude_agents(target_root: Path) -> None:
    for agent, agent_dir in shared_agents():
        target_name = canonical_agent_name(agent["id"])
        body = (agent_dir / "prompt.md").read_text(encoding="utf-8")
        body = transform_agent_text(body, "claude-code")
        tools = render_claude_tools(agent.get("capabilities", []))
        frontmatter = [
            "---",
            f"name: {target_name}",
            f"description: {json.dumps(transform_agent_text(agent['description'], 'claude-code'))}",
        ]
        if tools:
            frontmatter.append(f"tools: {tools}")
        frontmatter.append("---")
        write_text(
            target_root / ".claude" / "agents" / f"{target_name}.md",
            "\n".join(frontmatter) + "\n\n" + body.strip() + "\n",
        )


def render_codex_agent_adapter(agent: dict[str, Any]) -> str:
    codex_name = mapped_agent_name(agent["id"], "openai-codex")
    canonical_path = canonical_agent_path(agent["id"])
    capabilities = agent.get("capabilities", [])
    instructions = (
        "This is an OpenAI Codex custom-agent adapter over the shared `.claude` basis.\n\n"
        f"Before doing the task, read `{canonical_path}` and follow that canonical role guidance. "
        "Use the Codex TOML name, description, sandbox, and runtime behavior from this adapter "
        "when they conflict with Claude-specific frontmatter in the canonical file.\n\n"
        "Shared skills live in `.claude/skills/` and are enabled from `.codex/config.toml` when "
        "the project is trusted. Shared memory, plans, explorations, session logs, quality reports, "
        "templates, prompts, and hook scripts also live under `.claude/`.\n\n"
        f"Role type: {agent.get('role_type', 'unspecified')}\n"
        f"Visibility: {agent.get('visibility', 'public')}\n"
        f"Capability intents: {', '.join(capabilities) or 'target default'}"
    )
    agent_lines = [
        f"name = {toml_string(codex_name)}",
        f"description = {toml_string(transform_agent_text(agent['description'], 'openai-codex'))}",
    ]
    sandbox_mode = codex_sandbox_mode(capabilities)
    if sandbox_mode:
        agent_lines.append(f"sandbox_mode = {toml_string(sandbox_mode)}")
    agent_lines.append(f"developer_instructions = {toml_multiline_literal(instructions)}")
    return "\n".join(agent_lines) + "\n"


def render_github(target_root: Path) -> None:
    write_text(target_root / ".github" / "copilot-instructions.md", render_copilot_instructions())
    instructions_root = target_root / ".github" / "instructions"
    instructions_root.mkdir(parents=True, exist_ok=True)
    for source in sorted((REPO_ROOT / "shared" / "policies").glob("*.instructions.md")):
        write_text(instructions_root / source.name, render_github_instruction_adapter(source))

    copy_file(REPO_ROOT / "shared" / "hooks" / "hooks.json", target_root / ".github" / "hooks" / "hooks.json")
    render_vscode_mcp_json(target_root / ".vscode" / "mcp.json")

    for agent, _agent_dir in shared_agents():
        write_text(
            target_root / ".github" / "agents" / f"{agent['id']}.agent.md",
            render_github_agent_adapter(agent),
        )


def render_claude(target_root: Path) -> None:
    write_text(target_root / "CLAUDE.md", render_root_guidance("claude-code"))
    render_claude_mcp_json(target_root / ".mcp.json")
    render_claude_settings(target_root / ".claude" / "settings.json")


def render_codex(target_root: Path) -> None:
    write_text(target_root / "AGENTS.md", render_root_guidance("openai-codex"))
    render_codex_config(target_root / ".codex" / "config.toml")
    render_codex_hooks(target_root / ".codex" / "hooks.json")

    for agent, _agent_dir in shared_agents():
        target_name = mapped_agent_name(agent["id"], "openai-codex")
        write_text(
            target_root / ".codex" / "agents" / f"{target_name}.toml",
            render_codex_agent_adapter(agent),
        )


def render_multi_agent(target_root: Path) -> None:
    render_shared_basis(target_root, "multi-agent")
    render_github(target_root)
    render_claude(target_root)
    render_codex(target_root)


def generate(targets: list[str], output_root: Path) -> None:
    if "multi-agent" in targets:
        remove_obsolete_targets(output_root)
    for target in targets:
        target_root = reset_target(output_root, target)
        if target == "multi-agent":
            render_multi_agent(target_root)
        else:
            raise ValueError(f"unknown target: {target}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Generate the installable target.")
    parser.add_argument("--target", action="append", choices=TARGETS, help="Target to generate.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_ROOT, help="Output root.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    targets = list(TARGETS) if args.all or not args.target else args.target
    generate(targets, args.output)
    for target in targets:
        print(f"generated {target} -> {args.output / target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
