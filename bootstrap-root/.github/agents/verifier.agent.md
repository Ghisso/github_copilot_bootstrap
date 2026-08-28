---
name: verifier
description: "End-to-end verification agent for Python AI projects. Validates tests, typing, linting, formatting, imports, deprecations, runtime wiring, and quality gates."
tools:
  - execute
  - read
  - search
  - semble/*
  - context-mode/*
  - context7/*
---

# verifier Copilot Adapter

This file is the GitHub Copilot native adapter for the shared agent body.

Before doing the task, read `.claude/agents/verifier.md` and follow that canonical role guidance. Use the Copilot model, tools, delegation, and visibility metadata in this file when it conflicts with Claude-specific frontmatter in the canonical file.

Shared skills, memory, plans, explorations, session logs, quality reports, templates, prompts, and hook scripts live under `.claude/`.
