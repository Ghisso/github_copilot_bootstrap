---
description: Load when an agent reports results back to the orchestrator or user.
applicability: always
---

# Agent Reporting Convention

This is the single home for how agents phrase their reports. Agents reference it
rather than restating it.

## Default: caveman full

- Default to `caveman full` style for narrative/prose sections of a report.
- Preserve tables, code blocks, commands, file paths, identifiers, and
  structured findings (severity labels, scores) **literally** — terseness never
  drops structured or safety-critical detail.
- Load `.claude/skills/caveman/SKILL.md` if you need a refresher on the style.
- Drop terse mode for safety warnings, destructive actions, and ordered
  procedures where extra clarity matters.

## Exception: user-facing documentation

The `documenter` writes user-facing documentation in **normal prose**, not
caveman. Caveman is for orchestrator-facing status, never for the docs a reader
will see.
