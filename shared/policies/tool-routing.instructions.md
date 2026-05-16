---
description: Load when choosing between Semble, context-mode, grep, and direct file reads.
---

# Tool Routing

This file is the authoritative routing policy for retrieval helpers in this bootstrap. Semble and context-mode are retrieval helpers; they do not replace the plan, verify, review, score, document workflow, hook guardrails, or project-specific instructions.

## Routing Contract

- Use direct file reads when the path is known or the user named a specific file.
- Use `rg` or equivalent exact search for literals, symbols, error text, config keys, and filenames.
- Use Semble for semantic repository discovery: behavior ownership, related-code lookup, architectural neighbors, and "where is this implemented?" questions.
- Use context-mode for large outputs, logs, generated prose, long markdown artifacts, session continuity, and compaction-safe retrieval.
- Avoid running broad Semble and context-mode retrieval for the same question unless the first pass leaves a concrete gap.

## Fallback Order

1. Prefer the narrowest reliable source: known file, exact search, or local config.
2. Use Semble when semantic relationships matter more than exact text.
3. Use context-mode when the task depends on large artifacts, conversational continuity, or content likely to be lost during compaction.
4. Inside the generated devcontainer, Semble and context-mode are installed as required tools. Outside that managed environment, if retrieval helpers are unavailable, continue with direct reads and `rg`; missing optional binaries are warnings, not blockers.

## Do Not Use Optional Retrieval For

- Simple edits in already-open files.
- Validation commands, formatting, or test execution.
- Secrets, credentials, or protected files.
- Replacing project instructions, skills, hooks, or review gates.
