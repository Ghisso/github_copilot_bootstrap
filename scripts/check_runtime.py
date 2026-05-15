#!/usr/bin/env python3
"""Check runtime wiring for the generated bootstrap target."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_ROOT = REPO_ROOT / "dist"
OPTIONAL_BINARIES = ("context-mode", "npx", "uv", "uvx", "hf")
REQUIRED_FILES = (
    "dist/multi-agent/.devcontainer/devcontainer.json",
    "dist/multi-agent/.devcontainer/Dockerfile",
    "dist/multi-agent/.devcontainer/post-start.sh",
    "dist/multi-agent/.devcontainer/hf-ai-sync.py",
    "dist/multi-agent/.claude/hooks/scripts/hf-ai-sync.sh",
    "dist/multi-agent/.vscode/mcp.json",
    "dist/multi-agent/.github/hooks/hooks.json",
    "dist/multi-agent/.mcp.json",
    "dist/multi-agent/.claude/settings.json",
    "dist/multi-agent/.codex/config.toml",
    "dist/multi-agent/.codex/hooks.json",
)
REQUIRED_DIRS = (
    "dist/multi-agent/.codex/agents",
    "dist/multi-agent/.github/agents",
    "dist/multi-agent/.claude/agents",
    "dist/multi-agent/.claude/skills",
    "dist/multi-agent/.claude/review-profiles",
    "dist/multi-agent/.claude/hooks/scripts",
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
