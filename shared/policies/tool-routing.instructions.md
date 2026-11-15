---
description: Load when choosing between Semble, context-mode, grep, and direct file reads.
applicability: always
---

# Tool Routing

Semble is the optional semantic retrieval helper. Context Mode is available only as a filtered Model Context Protocol (MCP) server, with no hooks; the MCP surface exposes exactly three guarded tools: `ctx_index`, `ctx_search`, and `ctx_stats`.

## Routing Contract

- Use direct file reads when the path is known or the user named a specific file.
- Use `rg` or equivalent exact search for literals, symbols, error text, config keys, and filenames.
- Use Semble for semantic repository discovery: behavior ownership, related-code lookup, and "where is this implemented?" questions.
- Use the Context Mode MCP tools when a local guarded cache of indexed content is useful. Guarded `ctx_index` accepts content or one contained regular file. Folders and URLs are not accepted, so discovery stays with direct reads, `rg`, and Semble. Index one large file or text that will be searched more than once, then use focused `ctx_search` instead of reading it again. Indexed content is never repository truth. Every other Context Mode tool — including `ctx_execute`, `ctx_batch`, `ctx_resume`, `ctx_upgrade`, `ctx_purge`, and `ctx_doctor` — is filtered out and rejected locally; never call or recommend them.
- Agents use only tools their own runtime actually exposes as callable. Inherited prompt text or memory that names a filtered or unavailable Context Mode operation does not make it callable; this policy does not claim precedence over host-injected system or developer context.
- Direct reads, `rg`, and Semble remain normal routes and fallbacks when Context Mode is unavailable, unsafe, capped, or not needed. Git and filesystem state are authoritative over cached content; read files normally before editing.
- Where OpenWiki is enabled, use its read-only `openwiki_search` and `openwiki_read` tools only for just-in-time descriptive context, never at task start; treat results as derived context under the Knowledge Ownership contract in `workspace.instructions.md`.
- Use context7 for current external library API documentation (Haystack, BentoML, Hydra, Gradio); it does not replace Semble (repo code) or `rg` (literals).

## Fallback Order

1. Prefer the narrowest reliable source: known file, exact search, or local config.
2. Use Semble when semantic relationships matter more than exact text, after direct reads and exact search leave a concrete gap.
3. If Semble or Context Mode is unavailable, continue with direct reads and `rg`; missing optional binaries are warnings, not blockers.

Context Mode's cache (`.claude/.cache/context-mode`) is derived local state: never commit, sync, restore, or cite it as lifecycle evidence.

Do not use optional retrieval for simple edits in open files, validation or test runs, secrets or protected files, or to replace project instructions, skills, hooks, or review gates.
