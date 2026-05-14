---
name: review-pass-codex
description: "Hidden helper agent that runs a strict review pass using GPT-5.4 and returns findings in a normalized structure for downstream synthesis."
model: GPT-5.4
tools:
  - read
  - search
user-invocable: false
---

# review-pass-codex Copilot Adapter

This file is the GitHub Copilot native adapter for the shared agent body.

Before doing the task, read `.claude/agents/review-pass-claude-primary.md` and follow that canonical role guidance. Use the Copilot model, tools, delegation, and visibility metadata in this file when it conflicts with Claude-specific frontmatter in the canonical file.

Shared skills, memory, plans, explorations, session logs, quality reports, templates, prompts, and hook scripts live under `.claude/`.
