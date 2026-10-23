# Session: One state sync at a time, a network stall limit, and an exit trap

**Date:** 2026-10-23
**Plan:** `.claude/plans/2026-10-23_phase-B-sync-lock-and-exit-trap.md`
**Status:** IN-PROGRESS

## Goal

Let only one mutating state-sync run work on a checkout at a time (a `flock` lock on the repository root folder; busy runs skip, `setup` and `migrate-from-hf` wait up to 60 seconds), report the lock in `status`, bound state sync's HTTPS Git calls with a stall limit and no typed password prompts, and add an exit trap that puts the settings copy back after a signal unless a rebase or merge is unfinished.

## Work Log

- Phase A committed as `d68387f` and pushed; the post-commit hook advanced `current_phase` to this phase and set it `in-progress`.
- Coder implemented steps 1-4 in `shared/hooks/scripts/state-sync.sh` and `tests/test_state_sync.py` (17 new test cases for the plan's 12 tests). No behavior deviations; test-helper refactor only (`_sync_env` split out of `_sync`, a module-scoped `path_without_flock` fixture). Spike evidence per `integration-gate-spike`: `flock -w 2` on a held lock exited 1 after 2.003 s; `flock -n` exited 1 held and 0 free; a silent local HTTP server ended `pull` in about 2.2 s with `GIT_HTTP_LOW_SPEED_TIME=2` through the existing fetch-failure path (the Phase A script hit the test's 20 s limit); TERM, INT, and HUP to the process group exited 143, 130, and 129 through the EXIT trap.
- Negative control against the Phase A script: 15 of 17 new tests failed on their targeted markers; tests 4 and 5 passed as designed (contract guards). Full `tests/test_state_sync.py` ran 110 passed twice (about 31 s each), and the timing-sensitive subset passed five times in a row.
- Documenter updated `docs/runtime-checks.md`, `shared/policies/workflow.instructions.md` (the session-start AI-state bullet), `README.md`, and `docs/smoke-tests.md`; `validate_targets.py` passed after the policy edit. I moved the two new runtime-checks paragraphs below the settings-file paragraphs (the same "handled the same way" placement problem Phase A's review caught) and re-wrapped one line. The README pointer to "the recovery after a killed sync" stays accurate: `SIGKILL` can still leave the copy.
- Regenerated, refreshed the overlay, and ran every required check: targeted lock/trap/stall tests 17 passed; state-sync and installer tests 257 passed; `validate_targets.py`, `check_runtime.py`, and plan lint exit 0; `verify.py phase` PASS (4984 passed, 1 skipped).

## [LEARN] Entries

## Verification

## Open Questions / Next Steps

- Implement steps 1-4 (coder), then documentation (documenter), then review.
