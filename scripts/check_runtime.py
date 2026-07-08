#!/usr/bin/env python3
"""Check runtime wiring for the generated bootstrap target."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DIST_ROOT = REPO_ROOT / "dist"
OPTIONAL_BINARIES = ("context-mode", "npx", "uv", "uvx", "hf", "gh")
REQUIRED_FILES = (
    "dist/multi-agent/.devcontainer/devcontainer.json",
    "dist/multi-agent/.devcontainer/Dockerfile",
    "dist/multi-agent/.devcontainer/post-start.sh",
    "dist/multi-agent/.devcontainer/state-sync.sh",
    "dist/multi-agent/.devcontainer/restore-root-adapters.sh",
    "dist/multi-agent/.claude/hooks/scripts/state-sync.sh",
    "dist/multi-agent/.claude/hooks/scripts/restore-root-adapters.sh",
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
            if command == "gh":
                print(
                    "WARN optional binary missing: gh; enforce-pr-gate.sh still blocks common "
                    "implementation-branch git push paths, but GitHub web UI PR opening itself is not gated"
                )
            elif command == "uv":
                print(
                    "WARN optional binary missing: uv; the file-protection and git guardrails run "
                    "in pure bash without it, and quality_score.py is the only feature that needs it"
                )
            elif command == "context-mode":
                print(
                    "WARN optional binary missing: context-mode; retrieval falls back to direct reads "
                    "and rg (context-mode is a convenience, not a requirement)"
                )
            elif command == "npx":
                print(
                    "WARN optional binary missing: npx; the context7 MCP server (current external "
                    "library API docs) is unavailable, falling back to training-data knowledge, and "
                    "context-mode-dispatch.sh loses its npx fallback for launching context-mode"
                )
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

    validator = REPO_ROOT / "scripts" / "validate_plan_frontmatter.py"
    if validator.exists():
        result = subprocess.run(
            [sys.executable, str(validator)],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode == 0:
            print("PASS plan frontmatter validation")
        else:
            output = (result.stdout + result.stderr).strip()
            print(f"WARN plan frontmatter validation reported issues: {output}")

    print("PASS generated runtime wiring is present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
