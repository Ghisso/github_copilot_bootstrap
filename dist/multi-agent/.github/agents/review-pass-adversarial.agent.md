---
name: review-pass-adversarial
description: "Hidden helper agent that runs an adversarial independent review pass and returns normalized findings for reviewer synthesis."
model: Claude Sonnet 4.6
tools:
  - read
  - search
user-invocable: false
---

# review-pass-adversarial Copilot Adapter

This file is the GitHub Copilot native adapter for the shared agent body.

Before doing the task, read `.claude/agents/review-pass-adversarial.md` and follow that canonical role guidance. Use the Copilot model, tools, delegation, and visibility metadata in this file when it conflicts with Claude-specific frontmatter in the canonical file.

Shared skills, memory, plans, explorations, session logs, quality reports, templates, prompts, and hook scripts live under `.claude/`.
