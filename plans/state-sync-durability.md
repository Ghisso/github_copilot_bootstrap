---
name: state-sync-durability
type: big-plan
status: in-progress
originating_branch: dev
implementation_branch: state-sync-durability_implementation
started_at: 2026-07-22T08:07:34Z
phases:
  - 2026-07-22_phase-1-state-sync-failure-propagation
  - 2026-07-22_phase-2-durable-checkpoint-and-docs
  - 2026-07-22_phase-3-migrate-push-guard
current_phase: 2026-07-22_phase-3-migrate-push-guard
---

# Big Plan: state-sync-durability

## Context

A consumer repo running the Codex agent reported that AI state is not reliably
synchronized to `origin/ai-state`. Two root causes were confirmed against the
bootstrap source:

1. **Doomed push after aborted rebase.** `cmd_pull` in
   `shared/hooks/scripts/state-sync.sh` returns `0` even after it aborts a
   rebase on conflict. `cmd_push` calls `cmd_pull`, ignores its result, and
   attempts a push that is then rejected non-fast-forward.
2. **Tab closure is not a durability boundary.** The Codex `Stop` hook is the
   only automatic `push`. Closing a browser/editor tab does not guarantee a
   `Stop` event, so state can silently fail to publish. There is no
   commit-time checkpoint.

Documentation additionally overstates `Stop` as a guaranteed push.

Durable changes must be made in `shared/` and regenerated; generated consumer
files are never patched directly.

## Goals

- A failed pull reconciliation never leads to a doomed push attempt.
- No local or remote state is ever lost; no force operations; the nested repo
  is never left mid-rebase/merge.
- A reliable commit-time checkpoint replaces reliance on tab closure.
- An explicit sync command remains available.
- Same-file multi-writer conflicts have a documented, deterministic policy.
- Docs and tests no longer treat tab closure / `Stop` as guaranteed sync.
- Generated targets and both installed `state-sync.sh` copies stay consistent.

## Design Overview

- **Failure propagation:** `cmd_pull` returns non-zero only on the
  rebase-conflict path (legitimate no-op returns stay `0`). `cmd_push` guards
  the push behind a successful `cmd_pull`. Top-level dispatch keeps converting
  a non-zero return into a non-blocking warning + `exit 0`, so hook execution
  never blocks Codex shutdown or destroys state.
- **Durable checkpoint:** a new `shared/hooks/git-hooks/post-commit` runs
  `state-sync.sh push` best-effort after every successful outer commit
  (non-blocking; the commit has already landed). Auto-installed via the
  existing `core.hooksPath` glob. `Stop` remains a best-effort checkpoint.
  The existing VS Code "AI state: push" task remains the explicit command.
- **Multi-writer policy:** a nested `.gitattributes` gives append-only logs
  `merge=union` (git built-in, auto-reconciles during rebase); `plans/**` and
  `MEMORY.md` keep the default conflict -> abort -> warn path for manual
  semantic reconciliation. Never global ours/theirs.
- **Docs:** correct every "Stop always pushes" claim to "Stop is best-effort;
  tab closure is not guaranteed; post-commit checkpoint + explicit task are
  the durable paths."

## Phases

- [x] `2026-07-22_phase-1-state-sync-failure-propagation`
- [x] `2026-07-22_phase-2-durable-checkpoint-and-docs`
- [ ] `2026-07-22_phase-3-migrate-push-guard`

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```
