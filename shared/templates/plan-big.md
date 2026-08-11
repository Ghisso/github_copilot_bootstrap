---
name: <slug>
type: big-plan
# status: planning | in-progress | complete | cancelled
status: planning
originating_branch: dev
implementation_branch: <slug>_implementation
started_at:
phases:
  - <small-plan-slug-1>
  - <small-plan-slug-2>
current_phase:
# Cancellation fields (required only when status is cancelled):
# cancelled_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# cancelled_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# cancelled_evidence: <repository-relative readable UTF-8 CANCELLED artifact>
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
