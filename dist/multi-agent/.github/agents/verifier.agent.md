---
name: verifier
description: "End-to-end verification agent for Python AI projects. Validates that code compiles, tests pass, types check, linting is clean, configs load, and services start. Use as the final gate before any commit or PR."
tools:
    - execute
    - read
    - search
---

# verifier Copilot Adapter

This file is the GitHub Copilot native adapter for the shared agent body.

Before doing the task, read `.claude/agents/verifier.md` and follow that canonical role guidance. Use the Copilot model, tools, delegation, and visibility metadata in this file when it conflicts with Claude-specific frontmatter in the canonical file.

Shared skills, memory, plans, explorations, session logs, quality reports, templates, prompts, and hook scripts live under `.claude/`.
