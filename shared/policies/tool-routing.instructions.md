---
description: Load when choosing between Semble, context-mode, grep, and direct file reads.
applicability: always
---

# Tool Routing

This file is the authoritative routing policy for retrieval helpers in this bootstrap. Semble is the optional semantic retrieval helper. Context Mode is available only as a filtered Model Context Protocol (MCP) server, with no hooks; the MCP surface exposes exactly three guarded tools: `ctx_index`, `ctx_search`, and `ctx_stats`. Neither replaces the pre-flight, branch, plan, verify, review, document, learn, session-log, commit workflow, hook guardrails, or project-specific instructions.

## Routing Contract

- Use direct file reads when the path is known or the user named a specific file.
- Use `rg` or equivalent exact search for literals, symbols, error text, config keys, and filenames.
- Use Semble for semantic repository discovery: behavior ownership, related-code lookup, architectural neighbors, and "where is this implemented?" questions.
- Use the exposed Context Mode MCP tools (`ctx_index`, `ctx_search`, `ctx_stats`) when a local guarded cache of indexed content is useful. Guarded `ctx_index` accepts content or one contained regular file. Folders and URLs are not accepted, so discovery stays with direct reads, `rg`, and Semble. Index one large file or text that will be searched more than once, then use focused `ctx_search` instead of reading the content again. Indexing is nonblocking and its content is never repository truth. Every other Context Mode tool — including `ctx_execute`, `ctx_batch`, `ctx_resume`, `ctx_upgrade`, `ctx_purge`, and `ctx_doctor` — is filtered out of `tools/list` and rejected locally before it reaches the upstream server; never call or recommend them.
- Agents use only tools their own runtime actually exposes as callable. Prompt text, memory, or other inherited context that names a filtered or unavailable Context Mode operation does not make that operation callable; this policy does not claim precedence over host-injected system or developer context, it only restates this repository's own guarded surface.
- Direct reads, `rg`, and Semble remain normal routes and fallbacks: use them when Context Mode is unavailable, unsafe, capped, or not needed, and do not treat Context Mode as a replacement for them. Git and filesystem state are authoritative over cached content; read files normally before editing.
- Where OpenWiki is enabled and its Claude Code or Codex integration is installed, the session also has OpenWiki's read-only `openwiki_search` and `openwiki_read` tools, plus its workspace-listing tools. Use them only for just-in-time descriptive context, never at task start. Their results, including linked wikis of other repositories, are derived context under the Knowledge Ownership contract in `workspace.instructions.md`; verify any consequential detail against source.
- Protected-path deny rules remain defense in depth for hooks and other readers: `.env`, `.env.*`, `secrets/**`, `config/credentials.json`, and every repository deny still win.
- Use context7 for current external library API documentation (fast-moving stacks like Haystack, BentoML, Hydra, Gradio go stale in training data quickly); it is not a substitute for Semble (repo code) or `rg` (literals).

## Fallback Order

1. Prefer the narrowest reliable source: known file, exact search, or local config.
2. Use Semble when semantic relationships matter more than exact text.
3. Use Semble for broader semantic discovery only when direct reads and exact search leave a concrete gap.
4. If Semble is unavailable, continue with direct reads and `rg`; missing optional binaries are warnings, not blockers.

The Context Mode MCP server runs through `.claude/hooks/scripts/context-mode-dispatch.sh` (`server` mode starts the guarded MCP filter), which is Context Mode's only route: no client runs a Context Mode hook. A hook call from stale wiring in a committed adapter reads its input, prints nothing, and exits 0. The root adapters (`.mcp.json`, `.vscode/mcp.json`, and `.codex/config.toml`) start the server only through this guarded dispatcher, and the bootstrap's `validate_targets.py` checks each adapter's `context-mode` entry. Antigravity has no Context Mode entry because its bridge denies every MCP call. By default the dispatcher exports the canonical absolute project-local cache root `<repo>/.claude/.cache/context-mode`. It refuses every override outside that subtree: an override that resolves anywhere else, inside or outside the repository, is ignored with a warning and the project-local cache is used. The cache is derived local state: never commit, sync, restore, or cite it as lifecycle evidence. Context Mode is pinned to exactly `2.1.8` and needs Node.js 24.15.0 or newer. Every client uses one server identity (`context-mode server --agent codex`), started from the outer repository root. The dispatcher exports `CONTEXT_MODE_DATA_DIR` as the guarded cache root, which is where everything the 2.x server writes goes; 2.x ignores `CONTEXT_MODE_DIR`. A cache from the previous pin is moved aside, never migrated or deleted. When Context Mode is unavailable, its version does not match, or Node.js is too old, the server warns clearly and exits nonzero, falling back to direct reads, `rg`, and Semble.

## Do Not Use Optional Retrieval For

- Simple edits in already-open files.
- Validation commands, formatting, or test execution.
- Secrets, credentials, or protected files.
- Replacing project instructions, skills, hooks, or review gates.
