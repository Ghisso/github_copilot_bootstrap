---
name: review-pass-sonnet
description: "Hidden helper agent that runs an independent review pass using Claude Sonnet 4.6 and returns findings in a normalized structure for downstream synthesis."
model: Claude Sonnet 4.6
tools:
  - read
  - search
user-invocable: false
---

# review-pass-sonnet Copilot Adapter

This file is the GitHub Copilot native adapter for the shared agent body.

Before doing the task, read `.claude/agents/review-pass-claude-adversarial.md` and follow that canonical role guidance. Use the Copilot model, tools, delegation, and visibility metadata in this file when it conflicts with Claude-specific frontmatter in the canonical file.

Shared skills, memory, plans, explorations, session logs, quality reports, templates, prompts, and hook scripts live under `.claude/`.
