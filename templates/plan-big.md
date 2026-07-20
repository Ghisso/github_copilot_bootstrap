---
name: <slug>
type: big-plan
status: planning
originating_branch: dev
implementation_branch: <slug>_implementation
started_at:
phases:
  - <small-plan-slug-1>
  - <small-plan-slug-2>
current_phase:
---

# Big Plan: <slug>

## Context

[Why this work exists]

## Goals

- [Goal]

## Design Overview

[High-level design]

## Phases

- [ ] `<small-plan-slug-1>`
- [ ] `<small-plan-slug-2>`

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```
