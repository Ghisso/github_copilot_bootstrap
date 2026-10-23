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
- Coder implemented steps 1-5 in `shared/hooks/scripts/state-sync.sh`, `scripts/validate_targets.py`, and the tests (two comment-only edits in `tests/test_install_bootstrap.py`). No deviations from the plan. Choices: the marker check short-circuits before `git ls-files -u`; the failed-abort pull path still prints the pull output. Negative control: with the `dev` script swapped in, the 20 new and changed state-sync tests all failed, each on its targeted marker; the new script was restored and its hash checked. The three consumer-report probes now end safely.
- Documenter updated `README.md`, `docs/runtime-checks.md`, and `docs/smoke-tests.md`; I re-wrapped one README line.
- Regenerated targets and refreshed this repository's installed overlay (`install_bootstrap.py . --allow-self --local-only`, nested commit `dd9af16`).
- Required checks before review: state-sync tests 92 passed; validator and installer tests 387 passed; `validate_targets.py`, `check_runtime.py`, and `validate_plan_frontmatter.py` exit 0; `verify.py phase` PASS (4966 passed, 1 skipped). My first check runner fed commands on stdin and lost the last three to a child's stdin drain; rerunning with `</dev/null` fixed it.

## [LEARN] Entries

## Verification

## Open Questions / Next Steps

- Implement steps 1-5 (coder), then documentation (documenter), then review.
