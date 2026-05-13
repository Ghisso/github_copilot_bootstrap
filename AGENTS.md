# Agent Guidance

This repository is a reusable GitHub Copilot bootstrap. Preserve the plan -> implement -> verify -> review -> score workflow and keep hook guardrails intact.

Use `.github/copilot-instructions.md` for the main workspace guidance. When choosing between retrieval tools, treat `.github/instructions/tool-routing.instructions.md` as the single source of truth.

Semble and context-mode are optional helpers:

- Use Semble for semantic repository discovery and related-code lookup.
- Use context-mode for large outputs, logs, long markdown, and compaction-safe session continuity.
- Use `rg` for exact literals and direct file reads for known paths.

When MCP tools are unavailable, Semble can still be invoked from a shell-capable environment with `uvx --from "semble[mcp]" semble` where appropriate. Missing Semble or context-mode binaries should produce warnings or fallback behavior, not hard failures.
