#!/usr/bin/env python3
"""Check runtime wiring for generated bootstrap targets."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_ROOT = REPO_ROOT / "dist"
OPTIONAL_BINARIES = ("context-mode", "npx", "uvx")
REQUIRED_FILES = (
    "dist/github-copilot/.vscode/mcp.json",
    "dist/github-copilot/.github/hooks/hooks.json",
    "dist/claude-code/.mcp.json",
    "dist/claude-code/.claude/settings.json",
    "dist/openai-codex/.codex/config.toml",
    "dist/openai-codex/.codex/hooks.json",
)
REQUIRED_DIRS = (
    "dist/openai-codex/.codex/agents",
    "dist/openai-codex/.agents/skills",
)


def main() -> int:
    errors: list[str] = []
    for relative_path in REQUIRED_FILES:
        if not (REPO_ROOT / relative_path).exists():
            errors.append(f"missing runtime file: {relative_path}")
    for relative_path in REQUIRED_DIRS:
        if not (REPO_ROOT / relative_path).is_dir():
            errors.append(f"missing runtime directory: {relative_path}")

    for command in OPTIONAL_BINARIES:
        path = shutil.which(command)
        if path:
            print(f"PASS optional binary available: {command} -> {path}")
        else:
            print(f"WARN optional binary missing: {command}")

    if shutil.which("uvx"):
        print("PASS Semble can be launched through uvx when requested")
    else:
        print("WARN Semble MCP launcher uvx is missing; Semble is optional")

    if errors:
        for error in errors:
            print(f"FAIL {error}", file=sys.stderr)
        return 1

    print("PASS generated runtime wiring is present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
