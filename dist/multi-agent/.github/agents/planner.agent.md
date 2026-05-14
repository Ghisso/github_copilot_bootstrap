---
name: planner
description: "Planning specialist for implementation work. Produces phased plans with file ownership, risk analysis, verification commands, and required skills per step. Use before coding on non-trivial tasks."
model: Claude Opus 4.6
tools:
	- agent
	- execute
	- read
	- search
	- todo
	- todos
	- vscode
	- web
---

# planner Copilot Adapter

This file is the GitHub Copilot native adapter for the shared agent body.

Before doing the task, read `.claude/agents/planner.md` and follow that canonical role guidance. Use the Copilot model, tools, delegation, and visibility metadata in this file when it conflicts with Claude-specific frontmatter in the canonical file.

Shared skills, memory, plans, explorations, session logs, quality reports, templates, prompts, and hook scripts live under `.claude/`.
