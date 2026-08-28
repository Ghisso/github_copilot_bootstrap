---
name: reviewer
description: "Unified review agent for code, architecture, security, tests, APIs, configs, performance, documentation, and domain checks. Selects one or more review profiles and runs two sequential passes itself."
tools:
  - read
  - search
  - semble/*
  - context-mode/*
  - context7/*
---

# reviewer Copilot Adapter

This file is the GitHub Copilot native adapter for the shared agent body.

Before doing the task, read `.claude/agents/reviewer.md` and follow that canonical role guidance. Use the Copilot model, tools, delegation, and visibility metadata in this file when it conflicts with Claude-specific frontmatter in the canonical file.

Shared skills, memory, plans, explorations, session logs, quality reports, templates, prompts, and hook scripts live under `.claude/`.
