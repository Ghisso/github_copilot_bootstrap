# Agent Guidance

This repository is a reusable multi-agent bootstrap. Preserve the pre-flight -> branch -> plan when needed -> implement -> verify -> review -> closeout -> commit workflow and keep hook guardrails intact.

Use `shared/policies/workspace.instructions.md` for the main workspace guidance. When choosing retrieval tools, treat `shared/policies/tool-routing.instructions.md` as the single source of truth.

The source of truth lives in `shared/`; generated installable output lives in `dist/multi-agent/` (gitignored — run `uv run python scripts/generate_targets.py --all` before installing). Do not hand-edit generated files.

Semble and context-mode are optional helpers:

- Use Semble for semantic repository discovery and related-code lookup.
- Use context-mode for large outputs, logs, long markdown, and compaction-safe session continuity.
- Use `rg` for exact literals and direct file reads for known paths.

For every user-facing message, use clear, direct language with short sentences
and common precise words. Avoid unnecessary jargon, buzzwords, and idioms.
Define uncommon terms when needed, retain precise technical terms, and do not
use `caveman full` with the user. Compact internal agent handoffs may still use
`caveman full`. See
`.claude/instructions/agent-reporting.instructions.md` for the complete policy.

When MCP tools are unavailable, Semble can still be invoked from a shell-capable environment with `uvx --from "semble[mcp]" semble` where appropriate. Missing Semble or context-mode binaries should produce warnings or fallback behavior, not hard failures.
