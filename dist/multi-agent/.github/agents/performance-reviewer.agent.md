---
name: performance-reviewer
description: "Reviews code for performance issues including async patterns, memory usage, N+1 queries, unnecessary copies, caching opportunities, and batch processing. Especially relevant for ML inference paths and data pipelines. Use for I/O-heavy or ML-heavy code."
tools:
  - agent
  - read
  - search
agents:
  - review-pass-codex
  - review-pass-sonnet
---

# performance-reviewer Copilot Adapter

This file is the GitHub Copilot native adapter for the shared agent body.

Before doing the task, read `.claude/agents/performance-reviewer.md` and follow that canonical role guidance. Use the Copilot model, tools, delegation, and visibility metadata in this file when it conflicts with Claude-specific frontmatter in the canonical file.

Shared skills, memory, plans, explorations, session logs, quality reports, templates, prompts, and hook scripts live under `.claude/`.
