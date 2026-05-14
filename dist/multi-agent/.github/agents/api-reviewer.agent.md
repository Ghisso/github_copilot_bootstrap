---
name: api-reviewer
description: "Reviews API design, endpoint patterns, Pydantic validation, error responses, health checks, and service configuration. Ensures APIs are production-ready with proper lifecycle management, CORS, timeouts, and structured errors. Use when adding or changing API endpoints."
tools:
  - agent
  - read
  - search
agents:
  - review-pass-codex
  - review-pass-sonnet
---

# api-reviewer Copilot Adapter

This file is the GitHub Copilot native adapter for the shared agent body.

Before doing the task, read `.claude/agents/api-reviewer.md` and follow that canonical role guidance. Use the Copilot model, tools, delegation, and visibility metadata in this file when it conflicts with Claude-specific frontmatter in the canonical file.

Shared skills, memory, plans, explorations, session logs, quality reports, templates, prompts, and hook scripts live under `.claude/`.
