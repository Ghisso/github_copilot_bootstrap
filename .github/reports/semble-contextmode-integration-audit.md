# Semble + context-mode Integration Audit

Date: 2026-05-13

## Current State

- `.vscode/mcp.json` already used VS Code MCP `servers` syntax and registered `semble` through `uvx --from "semble[mcp]" semble`.
- `.github/hooks/hooks.json` already defined `SessionStart`, `Stop`, and `PreToolUse` hooks.
- Existing hook guardrails were `.github/hooks/scripts/protect-files.sh`, `.github/hooks/scripts/git-protection.sh`, and `.github/hooks/scripts/session-log.sh`.
- `.github/copilot-instructions.md` is the main always-on workspace instruction file.
- Root `AGENTS.md` was absent before this integration.
- The README quick-copy flow copied only `.github/`, so `.vscode/mcp.json` and `AGENTS.md` needed explicit optional distribution guidance.
- There is no project test suite or `pyproject.toml`; validation must rely on JSON checks, shell syntax checks, Python compilation, the runtime checker, and smoke notes.

## Upstream Merge Targets

- Semble remains configured as an MCP server and as a shell-available helper through `uvx --from "semble[mcp]" semble`.
- context-mode is added as an MCP server and a hook runtime helper without making it mandatory for every target repo.
- VS Code MCP configuration stays minimal and portable through a `servers` object with command entries and no user-specific paths.

## Routing Contract

- Semble is for semantic repository discovery, behavior ownership, architectural neighbors, and related-code lookup.
- context-mode is for large outputs, logs, prose and markdown artifacts, session continuity, and compaction-safe retrieval.
- `rg` is for exact literals, symbols, config keys, filenames, and error text.
- Direct file reads are preferred for known paths and user-named files.
- Broad retrieval should not be duplicated across Semble and context-mode unless the first pass leaves a concrete gap.

## Distribution Contract

`.github/` remains the main scaffold. `.vscode/mcp.json` and `AGENTS.md` are optional but recommended root surfaces for repositories that want VS Code MCP integration and CLI/sub-agent compatibility. Target repositories can skip these files and still keep the core bootstrap workflow functional.
