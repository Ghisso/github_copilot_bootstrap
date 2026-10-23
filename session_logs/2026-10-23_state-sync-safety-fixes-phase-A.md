# Session: Never commit over an unfinished rebase or merge

**Date:** 2026-10-23
**Plan:** `.claude/plans/2026-10-23_phase-A-unfinished-git-operations.md`
**Status:** IN-PROGRESS

## Goal

Stop state sync from committing conflict markers: refuse to commit while a rebase or merge is unfinished or unmerged paths exist, protect a merge found in place, drop the `rebase --quit` fallback for the current pull, keep and name the settings copy when an operation is left unfinished, stop `setup` in that case, commit before the unrelated-history merge, report merges in `status`, and remove two duplications.

## Work Log

- Plan approved by the user on 2026-10-23 after a planner draft, a separate devil's-advocate review (8 changes applied), and three user decisions: keep the `git ls-files -u` refusal, let `setup` and `migrate-from-hf` wait up to 60 s for the lock (phase B), and add a network stall limit (phase B).
- Pre-flight: `dev` at `a0c6003`, clean, level with `origin/dev`; all five plan files pass `validate_plan_frontmatter.py`.
- Created `state-sync-safety-fixes_implementation`; the branch hook set the big plan `in-progress` (`started_at: 2026-10-23T04:06:37Z`) and activated this phase.

## [LEARN] Entries

## Verification

## Open Questions / Next Steps

- Implement steps 1-5 (coder), then documentation (documenter), then review.
