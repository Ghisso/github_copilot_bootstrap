---
name: state-sync-local-only-regression
type: big-plan
status: complete
originating_branch: dev
implementation_branch: state-sync-local-only-regression_implementation
started_at: 2026-07-21T00:00:00Z
phases:
  - 2026-07-21_phase-1-state-sync-local-only-regression
current_phase:
---

# Big Plan: State-Sync Local-Only Regression

## Context

The local-only refresh update introduced two regressions in the canonical
state-sync script: a fresh local-only pull bypasses nested-state setup, and an
invalid explicit repository-root override exits under `set -e` instead of
falling back to script-relative resolution.

## Goals

- Initialize nested AI state before a local-only pull returns.
- Treat an invalid `AI_STATE_REPO_ROOT` as a warning and use the established
  script-relative resolution path.
- Add direct validator coverage for both regressions.

## Design Overview

Keep the single canonical `shared/hooks/scripts/state-sync.sh` source.  The
generator already renders it into both consumer locations, so one focused fix
and two direct adversarial checks prevent both generated copies from drifting.

## Phases

- [x] `2026-07-21_phase-1-state-sync-local-only-regression`

## Verification

```bash
bash -n shared/hooks/scripts/state-sync.sh
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run mypy scripts/ --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
```
