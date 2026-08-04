# Agent Guidance

This repository is a reusable multi-agent bootstrap. Preserve the pre-flight -> branch -> plan -> implement -> verify -> review -> document -> score -> learn -> session-log -> commit workflow and keep hook guardrails intact.

Use `shared/policies/workspace.instructions.md` for the main workspace guidance. When choosing retrieval tools, treat `shared/policies/tool-routing.instructions.md` as the single source of truth.

The source of truth lives in `shared/`; generated installable output lives in `dist/multi-agent/` (gitignored — run `uv run python scripts/generate_targets.py --all` before installing). Do not hand-edit generated files.

Semble and context-mode are optional helpers:

- Use Semble for semantic repository discovery and related-code lookup.
- Use context-mode for large outputs, logs, long markdown, and compaction-safe session continuity.
- Use `rg` for exact literals and direct file reads for known paths.

When MCP tools are unavailable, Semble can still be invoked from a shell-capable environment with `uvx --from "semble[mcp]" semble` where appropriate. Missing Semble or context-mode binaries should produce warnings or fallback behavior, not hard failures.
