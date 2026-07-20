---
name: coder
description: "Implementation specialist for Python AI engineering tasks. Applies standards, executes focused edits, simplifies changed code, and verifies with tests, types, and linting."
model: GPT-5.4
tools:
  - edit
  - execute
  - read
  - search
  - todo
  - todos
  - vscode
  - web
user-invocable: false
---

# coder Copilot Adapter

This file is the GitHub Copilot native adapter for the shared agent body.

Before doing the task, read `.claude/agents/coder.md` and follow that canonical role guidance. Use the Copilot model, tools, delegation, and visibility metadata in this file when it conflicts with Claude-specific frontmatter in the canonical file.

Shared skills, memory, plans, explorations, session logs, quality reports, templates, prompts, and hook scripts live under `.claude/`.
