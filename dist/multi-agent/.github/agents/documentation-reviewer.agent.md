---
name: documentation-reviewer
description: "Reviews documentation quality including Google-style docstrings, README completeness, docs/ organization, and documentation-code synchronization. Use after implementation changes to ensure docs are accurate and helpful for users and developers."
tools:
  - agent
  - read
  - search
agents:
  - review-pass-codex
  - review-pass-sonnet
---

# documentation-reviewer Copilot Adapter

This file is the GitHub Copilot native adapter for the shared agent body.

Before doing the task, read `.claude/agents/documentation-reviewer.md` and follow that canonical role guidance. Use the Copilot model, tools, delegation, and visibility metadata in this file when it conflicts with Claude-specific frontmatter in the canonical file.

Shared skills, memory, plans, explorations, session logs, quality reports, templates, prompts, and hook scripts live under `.claude/`.
