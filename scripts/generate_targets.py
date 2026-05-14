#!/usr/bin/env python3
"""Generate target-native bootstrap files from shared source files."""

from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "dist"
TARGETS = ("github-copilot", "claude-code", "openai-codex")
COPY_IGNORE_PARTS = {".git", "__pycache__"}
COPY_IGNORE_SUFFIXES = {".pyc"}

CLAUDE_REVIEW_NAME_MAP = {
    "review-pass-codex": "review-pass-claude-primary",
    "review-pass-sonnet": "review-pass-claude-adversarial",
}
CODEX_REVIEW_NAME_MAP = {
    "review-pass-codex": "review-pass-codex-primary",
    "review-pass-sonnet": "review-pass-codex-adversarial",
}
CLAUDE_TOOL_MAP = {
    "read": ["Read"],
    "search": ["Grep", "Glob"],
    "edit": ["Edit", "MultiEdit", "Write"],
    "execute": ["Bash"],
    "delegate": ["Task"],
    "todo": ["TodoWrite"],
    "web": ["WebFetch", "WebSearch"],
}
TARGET_PATH_REPLACEMENTS = {
    "claude-code": (
        (
            "under `.github/agents/`, `.github/instructions/`, `.github/hooks/`, or is `copilot-instructions.md`",
            "under `.claude/agents/`, `.claude/skills/`, `.claude/hooks/`, or is `CLAUDE.md` or `.claude/settings.json`",
        ),
        (
            "(`.github/agents/**`, `.github/instructions/**`, `.github/hooks/**`, `copilot-instructions.md`)",
            "(`.claude/agents/**`, `.claude/skills/**`, `.claude/hooks/**`, `.claude/settings.json`, `CLAUDE.md`)",
        ),
        ("Copy `copilot-instructions.md` to new project's `.github/`", "Copy `CLAUDE.md` to the new project's root"),
        ("See `quality-and-testing.instructions.md` rubric.", "See the Quality Gates & Testing Protocol section below."),
        ("quality-and-testing.instructions.md", "Quality Gates & Testing Protocol"),
        ("See `tests.instructions.md` for detailed mocking rules.", "Follow the testing guidance in this file for detailed mocking rules."),
        (
            "Load `.github/instructions/tool-routing.instructions.md` before choosing a retrieval helper. That instruction file is the authority; this skill is only a short trigger and reminder.",
            "Use the Tool Routing section in `CLAUDE.md` before choosing a retrieval helper. That section is the authority; this skill is only a short trigger and reminder.",
        ),
        ("Apply `quality-and-testing.instructions.md` rubric.", "Apply the Quality Gates & Testing Protocol rubric."),
        (".github/copilot-instructions.md", "CLAUDE.md"),
        (".github/instructions/quality-and-testing.instructions.md", "CLAUDE.md"),
        (".github/instructions/tool-routing.instructions.md", "CLAUDE.md"),
        (".github/instructions/**", "CLAUDE.md"),
        (".github/agents/**/*.agent.md", ".claude/agents/**/*.md"),
        ('normalized.endswith("/.github/copilot-instructions.md")', 'normalized.endswith("/CLAUDE.md")'),
        ('"/.github/instructions/" in normalized and normalized.endswith(".md")', 'normalized.endswith("/CLAUDE.md")'),
        ('"/.github/skills/" in normalized', '"/.claude/skills/" in normalized'),
        ('"/.github/agents/" in normalized and normalized.endswith(".agent.md")', '"/.claude/agents/" in normalized and normalized.endswith(".md")'),
        (".github/hooks/hooks.json", ".claude/settings.json"),
        (".github/session_logs", ".claude/session_logs"),
        (".github/quality_reports", ".claude/quality_reports"),
        (".github/explorations", ".claude/explorations"),
        (".github/plans", ".claude/plans"),
        (".github/skills", ".claude/skills"),
        (".github/scripts", ".claude/scripts"),
        (".github/templates", ".claude/templates"),
        (".github/agents", ".claude/agents"),
        (".github/hooks", ".claude/hooks"),
        (".github/instructions/", "CLAUDE.md"),
        (".github/instructions", "CLAUDE.md"),
        (".github/MEMORY.md", ".claude/MEMORY.md"),
        ("Copy `.github/` directory", "Copy `.claude/` directory"),
        ("git add .github/", "git add .claude/"),
        ("copilot-instructions.md", "CLAUDE.md"),
    ),
    "openai-codex": (
        (
            "under `.github/agents/`, `.github/instructions/`, `.github/hooks/`, or is `copilot-instructions.md`",
            "under `.codex/agents/`, `.agents/skills/`, `.codex/hooks/`, or is `AGENTS.md`, `.codex/config.toml`, or `.codex/hooks.json`",
        ),
        (
            "(`.github/agents/**`, `.github/instructions/**`, `.github/hooks/**`, `copilot-instructions.md`)",
            "(`.codex/agents/**`, `.agents/skills/**`, `.codex/hooks/**`, `.codex/config.toml`, `.codex/hooks.json`, `AGENTS.md`)",
        ),
        ("Copy `copilot-instructions.md` to new project's `.github/`", "Copy `AGENTS.md` to the new project's root"),
        ("See `quality-and-testing.instructions.md` rubric.", "See the Quality Gates & Testing Protocol section below."),
        ("quality-and-testing.instructions.md", "Quality Gates & Testing Protocol"),
        ("See `tests.instructions.md` for detailed mocking rules.", "Follow the testing guidance in this file for detailed mocking rules."),
        (
            "Load `.github/instructions/tool-routing.instructions.md` before choosing a retrieval helper. That instruction file is the authority; this skill is only a short trigger and reminder.",
            "Use the Tool Routing section in `AGENTS.md` before choosing a retrieval helper. That section is the authority; this skill is only a short trigger and reminder.",
        ),
        ("Apply `quality-and-testing.instructions.md` rubric.", "Apply the Quality Gates & Testing Protocol rubric."),
        (".github/copilot-instructions.md", "AGENTS.md"),
        (".github/instructions/quality-and-testing.instructions.md", "AGENTS.md"),
        (".github/instructions/tool-routing.instructions.md", "AGENTS.md"),
        (".github/instructions/**", "AGENTS.md"),
        (".github/agents/**/*.agent.md", ".codex/agents/**/*.toml"),
        ('normalized.endswith("/.github/copilot-instructions.md")', 'normalized.endswith("/AGENTS.md")'),
        ('"/.github/instructions/" in normalized and normalized.endswith(".md")', 'normalized.endswith("/AGENTS.md")'),
        ('"/.github/skills/" in normalized', '"/.agents/skills/" in normalized'),
        ('"/.github/agents/" in normalized and normalized.endswith(".agent.md")', '"/.codex/agents/" in normalized and normalized.endswith(".toml")'),
        (".github/hooks/hooks.json", ".codex/hooks.json"),
        (".github/session_logs", ".codex/session_logs"),
        (".github/quality_reports", ".codex/quality_reports"),
        (".github/explorations", ".codex/explorations"),
        (".github/plans", ".codex/plans"),
        (".github/skills", ".agents/skills"),
        (".github/scripts", ".codex/scripts"),
        (".github/templates", ".codex/templates"),
        (".github/agents", ".codex/agents"),
        (".github/hooks", ".codex/hooks"),
        (".github/instructions/", "AGENTS.md"),
        (".github/instructions", "AGENTS.md"),
        (".github/MEMORY.md", ".codex/MEMORY.md"),
        ("Copy `.github/` directory", "Copy `.codex/` directory"),
        ("git add .github/", "git add .codex/"),
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


def support_namespace(target: str) -> str:
    if target == "github-copilot":
        return ".github"
    if target == "claude-code":
        return ".claude"
    if target == "openai-codex":
        return ".codex"
    raise ValueError(f"unknown target: {target}")


def render_support_files(target_root: Path, target: str) -> None:
    namespace = support_namespace(target)
    support_root = target_root / namespace
    target_label = {
        "github-copilot": "GitHub Copilot",
        "claude-code": "Claude Code",
        "openai-codex": "OpenAI Codex",
    }[target]

    copy_text_transformed(REPO_ROOT / ".github" / "MEMORY.md", support_root / "MEMORY.md", target)
    copy_tree_transformed(REPO_ROOT / ".github" / "templates", support_root / "templates", target)
    copy_text_transformed(
        REPO_ROOT / ".github" / "scripts" / "quality_score.py",
        support_root / "scripts" / "quality_score.py",
        target,
    )

    for name in ("plans", "quality_reports", "session_logs"):
        source = REPO_ROOT / ".github" / name / "README.md"
        copy_text_transformed(source, support_root / name / "README.md", target)

    write_text(
        support_root / "explorations" / "README.md",
        f"# Explorations\n\n"
        f"This directory stores exploratory or proof-of-concept plans created during {target_label} sessions.\n\n"
        "Use implementation plans for ready-to-execute work, and explorations when the work still needs "
        "research, feasibility checks, or throwaway prototypes.\n",
    )


def reset_target(output_root: Path, target: str) -> Path:
    target_root = output_root / target
    if target_root.exists():
        shutil.rmtree(target_root)
    target_root.mkdir(parents=True)
    return target_root


def shared_agents() -> list[tuple[dict[str, Any], Path]]:
    agents_root = REPO_ROOT / "shared" / "agents"
    agents: list[tuple[dict[str, Any], Path]] = []
    for metadata_path in sorted(agents_root.glob("*/agent.yaml")):
        agents.append((load_json_yaml(metadata_path), metadata_path.parent))
    return agents


def mapped_agent_name(agent_id: str, target: str) -> str:
    if target == "claude-code":
        return CLAUDE_REVIEW_NAME_MAP.get(agent_id, agent_id)
    if target == "openai-codex":
        return CODEX_REVIEW_NAME_MAP.get(agent_id, agent_id)
    return agent_id


def transform_agent_text(text: str, target: str) -> str:
    replacements = {
        "review-pass-codex": mapped_agent_name("review-pass-codex", target),
        "review-pass-sonnet": mapped_agent_name("review-pass-sonnet", target),
    }
    transformed = text
    for old, new in replacements.items():
        transformed = re.sub(rf"(?<![\w-]){re.escape(old)}(?![\w-])", new, transformed)

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


def render_vscode_mcp_json(path: Path) -> None:
    write_json(path, {"servers": shared_mcp_servers()})


def render_claude_mcp_json(path: Path) -> None:
    write_json(path, {"mcpServers": shared_mcp_servers()})


def render_codex_config(path: Path) -> None:
    lines = [
        "# Generated from shared/mcp/servers.yaml.",
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
                            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/scripts/session-log.sh",
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
                            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/scripts/protect-files.sh",
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
                            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/scripts/session-log.sh",
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
        executable = f'"$(git rev-parse --show-toplevel)/.codex/hooks/scripts/{script}"'
        return f"{executable} {suffix}".rstrip()

    hooks = {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "startup|resume|clear",
                    "hooks": [
                        {"type": "command", "command": command("session-log.sh"), "timeout": 10},
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
                        {"type": "command", "command": command("protect-files.sh"), "timeout": 10},
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
                        {"type": "command", "command": command("session-log.sh"), "timeout": 10}
                    ]
                }
            ],
        },
    }
    write_json(path, hooks)


def render_root_guidance(target: str) -> str:
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
            "Custom agents are rendered as Claude Code project subagents in `.claude/agents/`. "
            "Copilot model pins are intentionally omitted; review helpers use Claude-native "
            "primary/adversarial passes."
        )
    else:
        title = "OpenAI Codex Bootstrap Guidance"
        agent_note = (
            "Custom agents are rendered as Codex project custom agents in `.codex/agents/*.toml`. "
            "Copilot and Claude model pins are intentionally omitted; review helpers use "
            "Codex-native primary/adversarial agents."
        )
    return (
        f"# {title}\n\n"
        "This target is generated from `shared/`. Do not edit generated files manually.\n\n"
        "Preserve the plan -> implement -> verify -> review -> score workflow and hook guardrails.\n\n"
        f"{agent_note}\n\n"
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


def render_github(target_root: Path) -> None:
    render_support_files(target_root, "github-copilot")
    copy_file(
        REPO_ROOT / "shared" / "policies" / "copilot-instructions.md",
        target_root / ".github" / "copilot-instructions.md",
    )
    instructions_root = target_root / ".github" / "instructions"
    instructions_root.mkdir(parents=True, exist_ok=True)
    for source in sorted((REPO_ROOT / "shared" / "policies").glob("*.instructions.md")):
        copy_file(source, instructions_root / source.name)

    copy_skills(REPO_ROOT / "shared" / "skills", target_root / ".github" / "skills", "github-copilot")
    copy_file(REPO_ROOT / "shared" / "hooks" / "hooks.json", target_root / ".github" / "hooks" / "hooks.json")
    copy_tree(REPO_ROOT / "shared" / "hooks" / "scripts", target_root / ".github" / "hooks" / "scripts")
    render_vscode_mcp_json(target_root / ".vscode" / "mcp.json")

    prompts_root = target_root / ".github" / "prompts"
    copy_tree(REPO_ROOT / "shared" / "prompts", prompts_root)

    for agent, agent_dir in shared_agents():
        source = agent_dir / "targets" / "github-copilot.md"
        copy_file(source, target_root / ".github" / "agents" / f"{agent['id']}.agent.md")


def render_claude(target_root: Path) -> None:
    render_support_files(target_root, "claude-code")
    write_text(target_root / "CLAUDE.md", render_root_guidance("claude-code"))
    render_claude_mcp_json(target_root / ".mcp.json")
    render_claude_settings(target_root / ".claude" / "settings.json")
    copy_skills(REPO_ROOT / "shared" / "skills", target_root / ".claude" / "skills", "claude-code")
    copy_tree(REPO_ROOT / "shared" / "hooks" / "scripts", target_root / ".claude" / "hooks" / "scripts")

    for agent, agent_dir in shared_agents():
        target_name = mapped_agent_name(agent["id"], "claude-code")
        body = (agent_dir / "targets" / "claude-code.md").read_text(encoding="utf-8")
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


def render_codex(target_root: Path) -> None:
    render_support_files(target_root, "openai-codex")
    write_text(target_root / "AGENTS.md", render_root_guidance("openai-codex"))
    render_codex_config(target_root / ".codex" / "config.toml")
    render_codex_hooks(target_root / ".codex" / "hooks.json")
    copy_skills(REPO_ROOT / "shared" / "skills", target_root / ".agents" / "skills", "openai-codex")
    copy_tree(REPO_ROOT / "shared" / "hooks" / "scripts", target_root / ".codex" / "hooks" / "scripts")

    for agent, agent_dir in shared_agents():
        target_name = mapped_agent_name(agent["id"], "openai-codex")
        body = (agent_dir / agent["targets"]["openai-codex"]).read_text(encoding="utf-8")
        body = transform_agent_text(body, "openai-codex")
        capabilities = agent.get("capabilities", [])
        instructions = (
            "This project custom agent was generated from shared agent metadata.\n\n"
            f"Role type: {agent.get('role_type', 'unspecified')}\n"
            f"Visibility: {agent.get('visibility', 'public')}\n"
            f"Capability intents: {', '.join(capabilities) or 'target default'}\n\n"
            f"{body.strip()}"
        )
        agent_lines = [
            f"name = {toml_string(target_name)}",
            f"description = {toml_string(transform_agent_text(agent['description'], 'openai-codex'))}",
        ]
        sandbox_mode = codex_sandbox_mode(capabilities)
        if sandbox_mode:
            agent_lines.append(f"sandbox_mode = {toml_string(sandbox_mode)}")
        agent_lines.append(f"developer_instructions = {toml_multiline_literal(instructions)}")
        write_text(
            target_root / ".codex" / "agents" / f"{target_name}.toml",
            "\n".join(agent_lines) + "\n",
        )


def generate(targets: list[str], output_root: Path) -> None:
    for target in targets:
        target_root = reset_target(output_root, target)
        if target == "github-copilot":
            render_github(target_root)
        elif target == "claude-code":
            render_claude(target_root)
        elif target == "openai-codex":
            render_codex(target_root)
        else:
            raise ValueError(f"unknown target: {target}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true", help="Generate all targets.")
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
