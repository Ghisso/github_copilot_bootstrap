---
name: documenter
description: "Documentation update agent. Reads git diff, identifies changed public interfaces and flows, then updates README.md and docs/ with accurate prose and Mermaid diagrams."
tools:
  - edit
  - execute
  - read
  - search
user-invocable: false
---

# documenter Copilot Adapter

This file is the GitHub Copilot native adapter for the shared agent body.

Before doing the task, read `.claude/agents/documenter.md` and follow that canonical role guidance. Use the Copilot model, tools, delegation, and visibility metadata in this file when it conflicts with Claude-specific frontmatter in the canonical file.

Shared skills, memory, plans, explorations, session logs, quality reports, templates, prompts, and hook scripts live under `.claude/`.
