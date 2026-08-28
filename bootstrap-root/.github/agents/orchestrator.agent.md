---
name: orchestrator
description: "Main-thread workflow orchestrator for complex implementation tasks. Delegates planning, coding, review, and verification to specialists, and owns the lifecycle ceremony (branch, commit, PR, memory, and session-log writes) itself. Not itself a delegatable subagent."
tools:
  - agent
  - edit
  - execute
  - read
  - search
  - semble/*
  - context-mode/*
  - context7/*
  - todo
  - todos
agents:
  - planner
  - coder
  - reviewer
  - verifier
  - documenter
disable-model-invocation: true
---

# orchestrator Copilot Adapter

This file is the GitHub Copilot native adapter for the shared agent body.

Before doing the task, read `.claude/agents/orchestrator.md` and follow that canonical role guidance. Use the Copilot model, tools, delegation, and visibility metadata in this file when it conflicts with Claude-specific frontmatter in the canonical file.

Shared skills, memory, plans, explorations, session logs, quality reports, templates, prompts, and hook scripts live under `.claude/`.
