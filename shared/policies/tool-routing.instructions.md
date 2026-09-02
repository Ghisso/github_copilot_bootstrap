---
description: Load when choosing between Semble, context-mode, grep, and direct file reads.
applicability: always
---

# Tool Routing

This file is the authoritative routing policy for retrieval helpers in this bootstrap. Semble is the optional semantic retrieval helper. Context Mode is available as both lifecycle hooks and a filtered Model Context Protocol (MCP) server; the MCP surface exposes exactly four guarded tools: `ctx_index`, `ctx_search`, `ctx_stats`, and `ctx_doctor`. Neither replaces the pre-flight, branch, plan, verify, review, document, learn, session-log, commit workflow, hook guardrails, or project-specific instructions.

## Routing Contract

- Use direct file reads when the path is known or the user named a specific file.
- Use `rg` or equivalent exact search for literals, symbols, error text, config keys, and filenames.
- Use Semble for semantic repository discovery: behavior ownership, related-code lookup, architectural neighbors, and "where is this implemented?" questions.
- Use the exposed Context Mode MCP tools (`ctx_index`, `ctx_search`, `ctx_stats`, `ctx_doctor`) when a local guarded cache of project content is useful. Guarded `ctx_index` accepts content, a contained regular file, or a contained real directory. For broader repository discovery, the orchestrator may issue one bounded directory index after direct pre-flight reads, using the absolute repository root and stable source `project:<repository-name>` with no directory-policy override arguments; use focused `ctx_search` only when useful. The filter fixes upstream directory defaults, including `maxDepth: 5`, `maxFiles: 200`, `respectGitignore: true`, and `followSymlinks: false`; do not pass `include`, `exclude`, `maxDepth`, `maxFiles`, `extensions`, `respectGitignore`, or `followSymlinks`. This optional index is nonblocking, never repository truth, and never a reason to raise caps automatically. Every other Context Mode tool — including `ctx_execute`, `ctx_execute_file`, `ctx_batch_execute`, `ctx_fetch_and_index`, `ctx_upgrade`, `ctx_purge`, and `ctx_insight` — is filtered out of `tools/list` and rejected locally before it reaches the upstream server; never call or recommend them.
- Direct reads, `rg`, and Semble remain normal routes and fallbacks: use them when Context Mode is unavailable, unsafe, capped, or not needed, and do not treat Context Mode as a replacement for them. Git and filesystem state are authoritative over cached content; read files normally before editing.
- Protected-path deny rules remain defense in depth for hooks and other readers: `.env`, `.env.*`, `secrets/**`, `config/credentials.json`, and every repository deny still win.
- Use context7 for current external library API documentation (fast-moving stacks like Haystack, BentoML, Hydra, Gradio go stale in training data quickly); it is not a substitute for Semble (repo code) or `rg` (literals).

## Fallback Order

1. Prefer the narrowest reliable source: known file, exact search, or local config.
2. Use Semble when semantic relationships matter more than exact text.
3. Use Semble for broader semantic discovery only when direct reads and exact search leave a concrete gap.
4. If Semble is unavailable, continue with direct reads and `rg`; missing optional binaries are warnings, not blockers.

Context Mode lifecycle hooks and its MCP server both run through `.claude/hooks/scripts/context-mode-dispatch.sh` (`server` mode starts the guarded MCP filter). By default it exports the canonical absolute project-local cache root `<repo>/.claude/.cache/context-mode`. Inside the repository, overrides are accepted only within that subtree; canonical external absolute overrides remain supported. The cache is derived local state: never commit, sync, restore, or cite it as lifecycle evidence. Context Mode is pinned to exactly `1.0.169`; when it is unavailable or its version does not match, hooks warn and fail open and the MCP server warns clearly and exits nonzero, falling back to direct reads, `rg`, and Semble.

## Do Not Use Optional Retrieval For

- Simple edits in already-open files.
- Validation commands, formatting, or test execution.
- Secrets, credentials, or protected files.
- Replacing project instructions, skills, hooks, or review gates.
