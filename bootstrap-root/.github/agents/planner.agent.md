---
name: planner
description: "Planning specialist for implementation work. Produces phased plans with ownership, risks, verification commands, required skills, and review profiles."
tools:
  - agent
  - execute
  - read
  - search
  - semble/*
  - context-mode/*
  - context7/*
  - todo
  - todos
  - vscode
  - web
agents: []
---

# planner Copilot Adapter

This file is the GitHub Copilot native adapter for the shared agent body.

Before doing the task, read `.claude/agents/planner.md` and follow that canonical role guidance. Use the Copilot model, tools, delegation, and visibility metadata in this file when it conflicts with Claude-specific frontmatter in the canonical file.

Shared skills, memory, plans, explorations, session logs, quality reports, templates, prompts, and hook scripts live under `.claude/`.
