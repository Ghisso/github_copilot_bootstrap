---
name: architecture-reviewer
description: "Reviews code architecture for separation of concerns, dependency direction, coupling analysis, and design pattern usage. Ensures the codebase remains maintainable as it grows. Use when adding new modules or refactoring."
tools:
  - agent
  - read
  - search
agents:
  - review-pass-codex
  - review-pass-sonnet
---

# architecture-reviewer Copilot Adapter

This file is the GitHub Copilot native adapter for the shared agent body.

Before doing the task, read `.claude/agents/architecture-reviewer.md` and follow that canonical role guidance. Use the Copilot model, tools, delegation, and visibility metadata in this file when it conflicts with Claude-specific frontmatter in the canonical file.

Shared skills, memory, plans, explorations, session logs, quality reports, templates, prompts, and hook scripts live under `.claude/`.
