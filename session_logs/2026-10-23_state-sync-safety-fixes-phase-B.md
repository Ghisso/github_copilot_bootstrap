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
- Review round 1 (six profiles): gate WARN with one open request (the full verification results, answered with the run above) and five MINORs, all fixed: (1) a dead "status kept the lock" check after `status` had exited, removed, plus an uninitialized-`status` lock case and a 20 s timeout so a waiting `status` fails; (2) the `migrate-from-hf` wait and the exact `-w 60 9` / `-n 9` arguments were untested, now covered by a recording fake `flock` (mutations `-w 61`, a pattern typo, and a removed `lock:` line each failed a test); (3) the SIGINT/SIGHUP trap cases failed under a launcher that ignores those signals, fixed with `preexec_fn` resetting them (proved under `SIG_IGN`: 4 passed with the fix, INT and HUP failed without); (4) `docs/runtime-checks.md` overclaimed that only `SIGKILL` leaves the copy; (5) `docs/smoke-tests.md` lacked an Expected bullet for the phase. After the fixes: `tests/test_state_sync.py` 111 passed twice; ruff and mypy clean; the script itself was unchanged.

## [LEARN] Entries

- [LEARN:testing] A test that signals a child must reset the child's SIGINT, SIGHUP, and SIGTERM to `SIG_DFL` before exec; a launcher that ignores them makes Bash unable to trap them.
- [LEARN:testing] An assertion made after the process under test has exited cannot observe what it held; observe the resource while it runs, or drop the claim.
- [LEARN:tooling] A directory-descriptor `flock` needs no lock file and is released by the kernel, but every inherited descriptor (a detached grandchild, a hung network call) keeps it; make the lock state visible (`status` prints `lock: held`).

## Verification

- optional 1: NOT RUN — host and devcontainer lock sharing needs a running devcontainer on this checkout, which this session does not have; behavior without shared exclusion is the same as before this phase.
- optional 2: NOT RUN — no macOS host without `flock` is available; `test_sync_lock_runs_unlocked_without_flock` covers the same path by removing `flock` from `PATH`.

## Open Questions / Next Steps

- Phase C next: the restorer symlink checks and the devcontainer bind-mount folders.
