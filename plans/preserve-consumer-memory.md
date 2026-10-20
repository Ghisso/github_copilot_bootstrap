---
name: preserve-consumer-memory
type: big-plan
status: complete
originating_branch: dev
implementation_branch: preserve-consumer-memory_implementation
started_at: 2026-07-18T05:45:00Z
phases:
  - 2026-07-18_phase-A-preserve-consumer-memory
current_phase:
---

# Big Plan: Preserve Consumer Memory

## Context

The generated bundle contains a blank `.claude/MEMORY.md` seed. The installer
currently merges that bundle over a consumer before state migration or sync,
so refreshes replace accumulated consumer memory with the seed.

## Goals

- Seed `MEMORY.md` on fresh installs.
- Preserve an existing consumer `MEMORY.md` byte-for-byte on every refresh.
- Cover legacy pre-git migration and git-backed reinstall paths.
- Keep all other bootstrap-controlled files refreshable.

## Phases

- [x] `2026-07-18_phase-A-preserve-consumer-memory` — merged into `dev` as PR #8 (`ab87dd7`) on 2026-07-18.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run ruff check scripts/install_bootstrap.py scripts/validate_targets.py
uv run mypy scripts --ignore-missing-imports --explicit-package-bases
```
