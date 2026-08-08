---
name: installer-self-target-refresh
type: big-plan
status: in-progress
originating_branch: dev
implementation_branch: installer-self-target-refresh_implementation
started_at: 2026-08-09T00:00:00Z
phases:
  - 2026-08-09_phase-1-installer-allow-self
  - 2026-08-09_phase-2-promote-orphan-skill
current_phase: 2026-08-09_phase-2-promote-orphan-skill
---

# Big Plan: installer-self-target-refresh

## Context

This repository's own dogfood overlay (`.claude/`, `.codex/`, `.github/`
adapters) has drifted from `shared/` and **cannot be refreshed**. Both entry
points refuse to run:

- `install_bootstrap.py <this repo>` — `validate_install_roots` rejects
  overlapping source and target, because the generated source
  (`dist/multi-agent`) lives inside the target.
- `update_consumers.py <this repo>` — a thin wrapper that shells out to the
  installer, so it fails identically and surfaces a raw traceback.

`check_runtime.py` correctly reports the drift and prints
`install_bootstrap.py <consumer-repo>` as the repair — a command that cannot
work here. The drift therefore persisted through all fourteen phases of the
`bootstrap-guidance-runtime-modernization` plan, and is the root cause of the
Codex `PreToolUse` hook failures observed on 2026-08-09 (absent
`protect-files.py` and `pretool-bash-guard.sh`, differing `protect-files.sh`
and `.codex/hooks.json`, all six `.codex/agents/*.toml` stale).

## Goals

- Give the bootstrap repository a supported way to refresh its own overlay.
- Keep the overlap guard fail-closed by default; require explicit opt-in.
- Keep the guard's genuinely dangerous cases rejected even with the opt-in.
- Make `check_runtime.py` print a repair command that actually works here.
- Refresh this repository's overlay and verify the drift is resolved.

## Design Overview

`validate_install_roots` rejects three distinct situations. Only one of them is
the legitimate dogfood case:

| Situation | Meaning | With `--allow-self` |
| --- | --- | --- |
| `source == target` | installing dist over itself | still rejected |
| `target.is_relative_to(source)` | target inside `dist/` | still rejected |
| `source.is_relative_to(target)` | dist inside the bootstrap repo | **permitted** |

The permitted case is additionally required to be the bootstrap repository
itself, not any parent directory that happens to contain the source.

Removal scope is already safe for this: `owned_files()` walks only
`target/.claude` plus `RESTORABLE_ROOT_PATHS`, so `dist/` is never a removal
candidate and the source cannot delete itself mid-run.

## Non-Goals

- Changing what the installer preserves. `.claude/settings.local.json` is not
  in `CONSUMER_STATE_PATHS` and is therefore removed as an obsolete owned file.
  That is pre-existing behavior affecting every consumer, not something this
  plan introduces; it is recorded as a follow-up.
- Refreshing consumer repositories.
- Re-testing the Codex hooks natively (needs quota; resets 2026-08-15).

## Phases

- [x] `2026-08-09_phase-1-installer-allow-self`
- [ ] `2026-08-09_phase-2-promote-orphan-skill`

## Verification

```bash
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```
