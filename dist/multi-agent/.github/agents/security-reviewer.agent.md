---
name: security-reviewer
description: "Reviews code for security vulnerabilities. Checks OWASP Top 10 adapted for Python AI projects: hardcoded secrets, injection risks, unsafe deserialization, SQL injection, path traversal, and dependency security. Use before any PR or deployment."
tools:
  - agent
  - read
  - search
agents:
  - review-pass-codex
  - review-pass-sonnet
---

# security-reviewer Copilot Adapter

This file is the GitHub Copilot native adapter for the shared agent body.

Before doing the task, read `.claude/agents/security-reviewer.md` and follow that canonical role guidance. Use the Copilot model, tools, delegation, and visibility metadata in this file when it conflicts with Claude-specific frontmatter in the canonical file.

Shared skills, memory, plans, explorations, session logs, quality reports, templates, prompts, and hook scripts live under `.claude/`.
