---
name: code-reviewer
description: "Reviews Python source code for quality, patterns, and maintainability. Checks SOLID principles, DRY, readability, function length, Pythonic patterns, type hints, docstrings, import organization, and error handling. Use after implementing new features or before PRs."
tools:
  - agent
  - read
  - search
agents:
  - review-pass-codex
  - review-pass-sonnet
---

# code-reviewer Copilot Adapter

This file is the GitHub Copilot native adapter for the shared agent body.

Before doing the task, read `.claude/agents/code-reviewer.md` and follow that canonical role guidance. Use the Copilot model, tools, delegation, and visibility metadata in this file when it conflicts with Claude-specific frontmatter in the canonical file.

Shared skills, memory, plans, explorations, session logs, quality reports, templates, prompts, and hook scripts live under `.claude/`.
