# Session: Sidecar workflow repair (Phase B)

**Date:** 2026-10-02
**Plan:** .claude/plans/2026-10-02_phase-B-sidecar-workflow-repair.md
**Status:** IN-PROGRESS

## Goal

Fix findings 1-7 of `.claude/explorations/2026-10-02_sidecar-workflow-profile-hands-on-review.md`
plus finding 8 from Phase A (planner and reviewer prompts ask for saves their
tools cannot make), relocate sidecar state to `.ai-bootstrap/`, and migrate
owned legacy state safely.

## Work Log

- **07:25** - Phase A committed (`e8297f8`) and pushed; Phase B activated.
  Material-impact check: Phase A added finding 8 and the user-run native
  rerun constraint. One planner revised Phase B only (+24 lines: step 5 now
  covers findings 5-8 with the caller-saves decision; step 6 native rerun is
  prepared and verified by the orchestrator and run by the user, fresh
  install only). Big plan goal, phase line, and done criteria now say
  findings 1-8.
- **07:50** - Step 1 (finding 2) by coder. `_full_install_evidence` adds a
  legacy signal only when no modern marker fired: a real, untracked
  `.claude/` (same tracked-path guard) plus either (a) tracked
  `.devcontainer/hf-ai-sync.py` or `.devcontainer/state-sync.sh`, or (b) a
  local `.claude/scripts/verify.py`, each corroborated by at least 2 of the
  bootstrap hook scripts `run-hook.sh`, `protect-files.sh`, `session-log.sh`,
  `context-mode-dispatch.sh`, `git-protection.sh`. Evidence: read-only
  inspection of `img-classification` (has six such hook scripts, tracked
  `hf-ai-sync.py`, no `verify.py`) and this repository's history
  (`dd1ee06` retired `hf-ai-sync.py`; `3de8385` added `state-sync.sh`).
  Rejected: an arbitrary hooks folder, a single hook name, a tracked team
  `.claude/` with the same names. Mixed evidence now advises backup and
  inspected cleanup; the ambiguous plain refusal stops steering toward
  sidecar when a per-clone `.claude/` exists. Focused tests: 228 passed;
  ruff, format, and mypy clean on touched files.
- **08:15** - Step 2 (finding 4) by coder. `backup_sidecar_state` now runs
  the shared target preflight, takes `_acquire_run_lock` only for a real
  backup with state present, and copies through the new
  `_copy_state_into_preserved(source, preserved_root)` helper: copy into a
  `mkdtemp` sibling, then `os.rename` to the collision-free name; on
  `OSError` it removes only its own staging copy (or names it as incomplete)
  and prints the existing `ABORT: filesystem error at <path>: <reason>`.
  Behavior change to document: a symlinked state root or preserved folder
  now refuses instead of being skipped. `_run_backup_state` lost its dead
  `CalledProcessError` wrapper. Full suite: 2289 passed.

## [LEARN] Entries

Pending.

## Verification

Pending.
