#!/usr/bin/env python3
"""Validate optional agent runtime wiring for this bootstrap."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_FILES = (
    ".vscode/mcp.json",
    ".github/hooks/hooks.json",
    ".github/hooks/scripts/context-mode-dispatch.sh",
    ".github/instructions/tool-routing.instructions.md",
    ".github/copilot-instructions.md",
    "AGENTS.md",
    ".github/skills/retrieval-routing/SKILL.md",
    "README.md",
)

REQUIRED_CONTEXT_HOOK_EVENTS = (
    "SessionStart",
    "PreToolUse",
    "PostToolUse",
    "PreCompact",
)


def load_json(relative_path: str) -> dict[str, Any]:
    path = REPO_ROOT / relative_path
    with path.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"{relative_path} must contain a JSON object")
    return data


def command_values(entries: object) -> list[str]:
    if not isinstance(entries, list):
        return []
    values: list[str] = []
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("command"), str):
            values.append(entry["command"])
    return values


def check_required_files() -> list[str]:
    errors: list[str] = []
    for relative_path in REQUIRED_FILES:
        if not (REPO_ROOT / relative_path).exists():
            errors.append(f"missing required file: {relative_path}")
    return errors


def check_mcp() -> list[str]:
    errors: list[str] = []
    data = load_json(".vscode/mcp.json")
    servers = data.get("servers")
    if not isinstance(servers, dict):
        return [".vscode/mcp.json must define a servers object"]

    for server_name in ("semble", "context-mode"):
        server = servers.get(server_name)
        if not isinstance(server, dict):
            errors.append(f"missing MCP server: {server_name}")
        elif not isinstance(server.get("command"), str) or not server["command"]:
            errors.append(f"MCP server {server_name} must define a command")
    return errors


def check_hooks() -> list[str]:
    errors: list[str] = []
    data = load_json(".github/hooks/hooks.json")
    hooks = data.get("hooks")
    if not isinstance(hooks, dict):
        return [".github/hooks/hooks.json must define a hooks object"]

    pre_tool_commands = command_values(hooks.get("PreToolUse"))
    for required in (
        ".github/hooks/scripts/protect-files.sh",
        ".github/hooks/scripts/git-protection.sh",
    ):
        if required not in pre_tool_commands:
            errors.append(f"PreToolUse missing existing guardrail: {required}")

    for event_name in REQUIRED_CONTEXT_HOOK_EVENTS:
        commands = command_values(hooks.get(event_name))
        if ".github/hooks/scripts/context-mode-dispatch.sh" not in commands:
            errors.append(f"{event_name} missing context-mode wrapper hook")

    stop_commands = command_values(hooks.get("Stop"))
    if ".github/hooks/scripts/session-log.sh" not in stop_commands:
        errors.append("Stop missing existing session-log hook")
    return errors


def check_text_references() -> list[str]:
    errors: list[str] = []
    expected_references = {
        ".github/copilot-instructions.md": "tool-routing.instructions.md",
        "AGENTS.md": "tool-routing.instructions.md",
        ".github/skills/retrieval-routing/SKILL.md": "tool-routing.instructions.md",
        "README.md": ".vscode/mcp.json",
    }
    for relative_path, needle in expected_references.items():
        text = (REPO_ROOT / relative_path).read_text(encoding="utf-8")
        if needle not in text:
            errors.append(f"{relative_path} missing reference to {needle}")
    return errors


def report_optional_binaries() -> None:
    optional_commands = ("context-mode", "npx", "uvx")
    for command in optional_commands:
        path = shutil.which(command)
        if path:
            print(f"PASS optional binary available: {command} -> {path}")
        else:
            print(f"WARN optional binary missing: {command}")


def main() -> int:
    errors: list[str] = []
    errors.extend(check_required_files())
    errors.extend(check_mcp())
    errors.extend(check_hooks())
    errors.extend(check_text_references())

    report_optional_binaries()

    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1

    print("PASS agent runtime wiring is structurally valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
