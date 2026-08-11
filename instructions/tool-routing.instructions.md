---
description: Load when choosing between Semble, context-mode, grep, and direct file reads.
applicability: always
---

# Tool Routing

This file is the authoritative routing policy for retrieval helpers in this bootstrap. Semble is the optional semantic retrieval helper. Context Mode is hook-only; it does not expose MCP tools. Neither replaces the pre-flight, branch, plan, verify, review, score, document, learn, session-log, commit workflow, hook guardrails, or project-specific instructions.

## Routing Contract

- Use direct file reads when the path is known or the user named a specific file.
- Use `rg` or equivalent exact search for literals, symbols, error text, config keys, and filenames.
- Use Semble for semantic repository discovery: behavior ownership, related-code lookup, architectural neighbors, and "where is this implemented?" questions.
- Context Mode MCP routing and path-backed `ctx_index` are disabled because request-boundary project containment is not proved. Do not call or claim availability of `ctx_index` or `ctx_fetch_and_index`.
- Protected-path deny rules remain defense in depth for hooks and other readers: `.env`, `.env.*`, `secrets/**`, `config/credentials.json`, and every repository deny still win.
- Use context7 for current external library API documentation (fast-moving stacks like Haystack, BentoML, Hydra, Gradio go stale in training data quickly); it is not a substitute for Semble (repo code) or `rg` (literals).

## Fallback Order

1. Prefer the narrowest reliable source: known file, exact search, or local config.
2. Use Semble when semantic relationships matter more than exact text.
3. Use Semble for broader semantic discovery only when direct reads and exact search leave a concrete gap.
4. If Semble is unavailable, continue with direct reads and `rg`; missing optional binaries are warnings, not blockers.

Context Mode lifecycle hooks use `.claude/hooks/scripts/context-mode-dispatch.sh`. By default it exports the canonical absolute project-local cache root `<repo>/.claude/.cache/context-mode`. Inside the repository, overrides are accepted only within that subtree; canonical external absolute overrides remain supported. The cache is derived local state: never commit, sync, restore, or cite it as lifecycle evidence.

## Do Not Use Optional Retrieval For

- Simple edits in already-open files.
- Validation commands, formatting, or test execution.
- Secrets, credentials, or protected files.
- Replacing project instructions, skills, hooks, or review gates.
