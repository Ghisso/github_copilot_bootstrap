#!/usr/bin/env python3
"""Generate target-native bootstrap files from shared source files."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "dist"
TARGETS = ("multi-agent",)
COPY_IGNORE_PARTS = {".git", "__pycache__"}
COPY_IGNORE_SUFFIXES = {".pyc"}
SHARED_BASIS_NAMESPACE = ".claude"
# Codex has no stable model aliases (unlike Claude's opus/sonnet/haiku), so the
# session model is pinned to one concrete string here and inherited by every
# Codex agent. This is the single place to bump when gpt-5.6 ships. Per-agent
# reasoning-effort tiers live in each agent.yaml model_intent.openai-codex.
CODEX_SESSION_MODEL = "gpt-5.5"

CLAUDE_TOOL_MAP = {
    "read": ["Read"],
    "search": ["Grep", "Glob"],
    "edit": ["Edit", "MultiEdit", "Write"],
    "execute": ["Bash"],
    "delegate": ["Task"],
    "todo": ["TodoWrite"],
    "web": ["WebFetch", "WebSearch"],
}
# The "vscode" capability is intentionally Copilot-only: it maps to a Copilot
# tool and has no equivalent in Claude/Codex, so it is (correctly) omitted from
# their tool lists rather than silently mishandled.
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


def strip_quarantine(path: Path) -> None:
    """shared/ can carry macOS's com.apple.quarantine xattr (e.g. if this repo
    was ever extracted from a downloaded archive), and shutil.copy2/copytree
    preserve xattrs. Left alone that flag rides into dist/ and then into every
    consumer repo via install_bootstrap.py, where it makes git refuse to exec
    hook scripts (EPERM). Strip it from each generated target tree."""
    if sys.platform != "darwin":
        return
    subprocess.run(["xattr", "-rc", str(path)], check=False, capture_output=True)


def load_json(path: Path) -> dict[str, Any]:
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
    for path in destination.rglob("*"):
        if path.suffix not in {".md", ".py", ".sh"}:
            continue
        text = path.read_text(encoding="utf-8")
        path.write_text(transform_target_paths(text, target), encoding="utf-8")


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def ensure_executable(path: Path) -> None:
    path.chmod(path.stat().st_mode | 0o111)


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
    target_label = {"multi-agent": "multi-agent"}[target]

    copy_text_transformed(REPO_ROOT / "shared" / "MEMORY.md", support_root / "MEMORY.md", "claude-code")
    copy_tree_transformed(REPO_ROOT / "shared" / "templates", support_root / "templates", "claude-code")
    copy_text_transformed(
        REPO_ROOT / "shared" / "scripts" / "quality_score.py",
        support_root / "scripts" / "quality_score.py",
        "claude-code",
    )
    copy_text_transformed(
        REPO_ROOT / "shared" / "scripts" / "record_findings.py",
        support_root / "scripts" / "record_findings.py",
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
    copy_tree_transformed(
        REPO_ROOT / "shared" / "third_party",
        support_root / "third_party",
        "claude-code",
    )
    copy_tree_transformed(REPO_ROOT / "shared" / "review-profiles", support_root / "review-profiles", "claude-code")
    copy_tree(REPO_ROOT / "shared" / "hooks" / "scripts", support_root / "hooks" / "scripts")
    # Every hook script must be executable: the runtime wrapper execs them, and
    # validate_targets.py invokes them by path. The shared sources are tracked
    # 0644 (git core.fileMode aside), so make them +x here rather than relying on
    # the checked-out mode.
    for script in sorted((support_root / "hooks" / "scripts").glob("*.sh")):
        ensure_executable(script)
    copy_tree(REPO_ROOT / "shared" / "hooks" / "git-hooks", support_root / "hooks" / "git-hooks")
    # git invokes these directly by exact filename (commit-msg, not *.sh), so
    # they need the same executable-bit treatment as hooks/scripts/*.sh above.
    for script in sorted((support_root / "hooks" / "git-hooks").glob("*")):
        ensure_executable(script)
    copy_tree(REPO_ROOT / "shared" / "prompts", support_root / "prompts")
    render_claude_agents(target_root)


def render_devcontainer(target_root: Path) -> None:
    copy_tree(REPO_ROOT / "shared" / "devcontainer", target_root / ".devcontainer")
    # A second rendered copy of the two state-sync scripts, reachable BEFORE
    # .claude/ exists at all: .claude/ is gitignored in consumers, so a fresh
    # clone has none of it until post-start.sh's own bootstrap run of these
    # scripts creates it (see the REPO_ROOT-resolution comment at the top of
    # state-sync.sh). Both copies come from the same shared/ source and are
    # regenerated together, so they cannot drift.
    for name in ("state-sync.sh", "restore-root-adapters.sh"):
        source = REPO_ROOT / "shared" / "hooks" / "scripts" / name
        destination = target_root / ".devcontainer" / name
        copy_file(source, destination)
        ensure_executable(destination)


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
        agents.append((load_json(metadata_path), metadata_path.parent))
    return agents


def transform_agent_text(text: str, target: str) -> str:
    # Model names live only in agent.yaml model_intent (consumed directly when
    # rendering the GitHub adapter), never in prompt bodies or descriptions, so
    # there are no model-name substitutions to apply here — only path rewrites.
    return transform_target_paths(text, target)


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
    data = load_json(REPO_ROOT / "shared" / "mcp" / "servers.json")
    return data["servers"]


def shared_skill_names() -> list[str]:
    return sorted(path.parent.name for path in (REPO_ROOT / "shared" / "skills").glob("*/SKILL.md"))


def render_vscode_mcp_json(path: Path) -> None:
    write_json(path, {"servers": shared_mcp_servers()})


def render_vscode_tasks_json(path: Path) -> None:
    src = REPO_ROOT / "shared" / "vscode" / "tasks.json"
    write_json(path, json.loads(src.read_text()))


def render_claude_mcp_json(path: Path) -> None:
    write_json(path, {"mcpServers": shared_mcp_servers()})


def render_codex_config(path: Path) -> None:
    lines = [
        "# Generated from shared/mcp/servers.json.",
        "# Skills are sourced from the shared .claude basis; project trust is required.",
        "# Semble and context-mode are optional; missing binaries should warn, not block.",
        "# Hooks are enabled by default in current Codex, so no features block is emitted.",
        "# Codex resolves a non-absolute skill `path` relative to config.toml; the generated",
        "# bundle cannot know the consumer's absolute path, so each skill points at",
        "# ../.claude/skills/<name>/SKILL.md relative to this config. This relative form is",
        "# the tested contract: validate_targets.py asserts it structurally in two places -",
        "# validate_mcp_and_hooks (\"../.claude/skills/\" in config) and validate_skills_and_paths",
        "# (the enabled-skill path set must equal the shared/skills SKILL.md set exactly).",
        "# Runtime resolution follows Codex's documented relative-path handling (docs accessed",
        "# 2026-07-03); see architecture-review-2026-07.md appendix B for the epistemic status.",
        "#",
        "# Session model is pinned here (Codex has no stable model aliases). Every agent",
        "# inherits it unless it overrides model itself; per-agent reasoning-effort tiers",
        "# are emitted on the individual .codex/agents/*.toml files.",
        "",
        f"model = {toml_string(CODEX_SESSION_MODEL)}",
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
        lines.append(f"path = {toml_string(f'../.claude/skills/{skill_name}/SKILL.md')}")
        lines.append("enabled = true")
        lines.append("")
    write_text(path, "\n".join(lines))


def _claude_hook_cmd(script: str, *args: str) -> str:
    root_expr = '${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}'
    parts = [f'REPO_ROOT="{root_expr}"', '"$REPO_ROOT/.claude/hooks/scripts/run-hook.sh"', script, *args]
    return "; ".join(parts[:2]) + " " + " ".join(parts[2:])


def render_claude_settings(path: Path) -> None:
    def cmd(script: str, *args: str, timeout: int = 10) -> dict[str, Any]:
        return {"type": "command", "command": _claude_hook_cmd(script, *args), "timeout": timeout}

    def cmd_stop(script: str, *args: str) -> dict[str, Any]:
        return {"type": "command", "command": _claude_hook_cmd(script, *args), "timeout": 180}

    settings: dict[str, Any] = {
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
                        cmd("state-sync.sh", "pull", timeout=60),
                        cmd("session-log.sh", "claude-code"),
                        cmd("session-start-state.sh", "claude-code"),
                        cmd("context-mode-dispatch.sh", "claude-code", "sessionstart"),
                    ]
                }
            ],
            "PreToolUse": [
                {
                    "matcher": "Edit|MultiEdit|Write|Bash",
                    "hooks": [
                        cmd("protect-files.sh", "claude-code"),
                        cmd("git-protection.sh"),
                        cmd("enforce-branch-state.sh", "claude-code"),
                        cmd("enforce-commit-gate.sh", "claude-code"),
                        cmd("enforce-pr-gate.sh", "claude-code"),
                        cmd("context-mode-dispatch.sh", "claude-code", "pretooluse"),
                    ],
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        cmd("record-branch-state.sh", "claude-code"),
                        cmd("record-commit-closeout.sh", "claude-code"),
                        cmd("context-mode-dispatch.sh", "claude-code", "posttooluse"),
                    ],
                }
            ],
            "PreCompact": [
                {"hooks": [cmd("context-mode-dispatch.sh", "claude-code", "precompact")]}
            ],
            "Stop": [
                {
                    "hooks": [
                        cmd("session-log.sh", "claude-code"),
                        cmd("stop-session-log-check.sh", "claude-code"),
                        cmd_stop("state-sync.sh", "push"),
                    ]
                }
            ],
        },
    }
    write_json(path, settings)


def render_codex_hooks(path: Path) -> None:
    def command(script: str, *args: str) -> str:
        root_expr = "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
        parts = [f'REPO_ROOT="{root_expr}"', '"$REPO_ROOT/.claude/hooks/scripts/run-hook.sh"', script, *args]
        return "; ".join(parts[:2]) + " " + " ".join(parts[2:])

    def cmd(script: str, *args: str, timeout: int = 10) -> dict[str, Any]:
        return {"type": "command", "command": command(script, *args), "timeout": timeout}

    hooks: dict[str, Any] = {
        "hooks": {
            "SessionStart": [
                {
                    "matcher": "startup|resume|clear",
                    "hooks": [
                        cmd("state-sync.sh", "pull", timeout=60),
                        cmd("session-log.sh", "openai-codex"),
                        cmd("session-start-state.sh", "openai-codex"),
                        cmd("context-mode-dispatch.sh", "openai-codex", "sessionstart"),
                    ],
                }
            ],
            "PreToolUse": [
                {
                    "matcher": "*",
                    "hooks": [
                        cmd("protect-files.sh", "openai-codex"),
                        cmd("git-protection.sh"),
                        cmd("enforce-branch-state.sh", "openai-codex"),
                        cmd("enforce-commit-gate.sh", "openai-codex"),
                        cmd("enforce-pr-gate.sh", "openai-codex"),
                        cmd("context-mode-dispatch.sh", "openai-codex", "pretooluse"),
                    ],
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "Bash",
                    "hooks": [
                        cmd("record-branch-state.sh", "openai-codex"),
                        cmd("record-commit-closeout.sh", "openai-codex"),
                        cmd("context-mode-dispatch.sh", "openai-codex", "posttooluse"),
                    ],
                }
            ],
            "PreCompact": [
                {"hooks": [cmd("context-mode-dispatch.sh", "openai-codex", "precompact")]}
            ],
            "Stop": [
                {
                    "hooks": [
                        cmd("session-log.sh", "openai-codex"),
                        cmd("stop-session-log-check.sh", "openai-codex"),
                        cmd("state-sync.sh", "push", timeout=180),
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
        "Preserve the pre-flight -> branch -> plan -> implement -> verify -> review -> score -> document -> learn -> session-log -> commit workflow and hook guardrails. "
        "Score >= 90 plus required documentation updates are mandatory before commit or PR closeout.\n\n"
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
    # Agent names are identical across every target; there is no per-target
    # renaming (the earlier mapped_agent_name was an identity function).
    return agent_id


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

Before planning or implementation, load the relevant canonical instruction files from `.claude/instructions/`, especially `workflow.instructions.md`, `quality-and-testing.instructions.md`, and `tool-routing.instructions.md`. Before every coding action, load `.claude/skills/ponytail/SKILL.md` in `full` mode.

Preserve the pre-flight -> branch -> plan -> implement -> verify -> review -> score -> document -> learn -> session-log -> commit workflow. Score >= 90 plus required documentation updates are mandatory before commit or PR closeout. Write all plans, session logs, exploration notes, memory updates, and quality reports under `.claude/`, not target-local `.github/` or `.codex/` state directories.
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
        # Per-agent model/effort tiering lives in agent.yaml model_intent under the
        # "claude-code" key as an object; a legacy "target-native" string emits
        # nothing (inherit). "inherit" values are omitted so the agent follows the
        # session. Haiku agents must not carry effort (Haiku has no effort level).
        intent = agent.get("model_intent", {}).get("claude-code")
        if isinstance(intent, dict):
            model = intent.get("model")
            effort = intent.get("effort")
            if model and model != "inherit":
                frontmatter.append(f"model: {model}")
            if effort and effort != "inherit":
                frontmatter.append(f"effort: {effort}")
        frontmatter.append("---")
        write_text(
            target_root / ".claude" / "agents" / f"{target_name}.md",
            "\n".join(frontmatter) + "\n\n" + body.strip() + "\n",
        )


def render_codex_agent_adapter(agent: dict[str, Any]) -> str:
    codex_name = agent["id"]
    canonical_path = canonical_agent_path(agent["id"])
    capabilities = agent.get("capabilities", [])
    instructions = (
        "This is an OpenAI Codex custom-agent adapter over the shared `.claude` basis.\n\n"
        f"Before doing the task, read `{canonical_path}` and follow that canonical role guidance. "
        "Use the Codex TOML name, description, model, reasoning effort, sandbox, and runtime "
        "behavior from this adapter when they conflict with Claude-specific frontmatter in the "
        "canonical file.\n\n"
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
    # Per-agent model/effort tiering. model_intent.openai-codex is an object
    # carrying an optional per-agent model override and a reasoning-effort tier;
    # a legacy "target-native" string or an omitted/"inherit" value emits nothing,
    # so the agent inherits the session model/effort. Model is normally pinned
    # once globally (config.toml), so agents usually set only effort here.
    codex_intent = agent.get("model_intent", {}).get("openai-codex")
    if isinstance(codex_intent, dict):
        model = codex_intent.get("model")
        effort = codex_intent.get("effort")
        if model and model != "inherit":
            agent_lines.append(f"model = {toml_string(model)}")
        if effort and effort != "inherit":
            agent_lines.append(f"model_reasoning_effort = {toml_string(effort)}")
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
    render_vscode_tasks_json(target_root / ".vscode" / "tasks.json")

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
        target_name = agent["id"]
        write_text(
            target_root / ".codex" / "agents" / f"{target_name}.toml",
            render_codex_agent_adapter(agent),
        )


def render_multi_agent(target_root: Path) -> None:
    render_devcontainer(target_root)
    render_shared_basis(target_root, "multi-agent")
    render_github(target_root)
    render_claude(target_root)
    render_codex(target_root)


def generate(targets: list[str], output_root: Path) -> None:
    for target in targets:
        target_root = reset_target(output_root, target)
        if target == "multi-agent":
            render_multi_agent(target_root)
        else:
            raise ValueError(f"unknown target: {target}")
        strip_quarantine(target_root)


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
