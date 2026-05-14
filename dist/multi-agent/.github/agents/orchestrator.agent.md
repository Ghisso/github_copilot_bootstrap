---
name: orchestrator
description: "Workflow orchestrator for complex implementation tasks. Delegates planning, coding, design, and review work to specialist agents, prefers parallel execution when file ownership does not overlap, and enforces quality gates before completion. Use for multi-step features, refactors, and cross-file changes."
model: Claude Opus 4.6
tools:
  - agent
  - read
  - search
  - todo
agents:
  - "*"
---

# orchestrator Copilot Adapter

This file is the GitHub Copilot native adapter for the shared agent body.

Before doing the task, read `.claude/agents/orchestrator.md` and follow that canonical role guidance. Use the Copilot model, tools, delegation, and visibility metadata in this file when it conflicts with Claude-specific frontmatter in the canonical file.

Shared skills, memory, plans, explorations, session logs, quality reports, templates, prompts, and hook scripts live under `.claude/`.
