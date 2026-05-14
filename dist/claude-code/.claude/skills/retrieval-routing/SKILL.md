---
name: retrieval-routing
description: Use when deciding between direct reads, ripgrep, Semble, and context-mode retrieval.
---

# Retrieval Routing

Use the Tool Routing section in `CLAUDE.md` before choosing a retrieval helper. That section is the authority; this skill is only a short trigger and reminder.

Quick dispatch:

- Known path: read the file directly.
- Exact text, symbol, filename, or error: use `rg`.
- Semantic ownership or related-code discovery: use Semble.
- Large logs, long markdown/prose artifacts, session continuity, or compaction-safe recall: use context-mode.

Do not duplicate broad retrieval across Semble and context-mode unless the first pass leaves a specific unanswered question.
