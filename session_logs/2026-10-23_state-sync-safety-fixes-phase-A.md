# Session: Never commit over an unfinished rebase or merge

**Date:** 2026-10-23
**Plan:** `.claude/plans/2026-10-23_phase-A-unfinished-git-operations.md`
**Status:** COMPLETED

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
- Review round 1 (`code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`): gate PASS with three MINORs, all fixed rather than accepted: (1) a failed `merge --abort` was reported as "merge left in place" even when `git merge` had failed before creating `MERGE_HEAD`; the coder added `clear_current_merge_state`, guarded the branch with `nested_merge_in_progress`, and added `test_failed_unrelated_merge_without_merge_state_restores_settings` (it failed on the pre-fix script with `['merge -q', 'merge --abort'] == ['merge -q']`); (2) the new `docs/runtime-checks.md` paragraph split "`settings.local.json` is handled the same way" from the paragraph it refers to, so I moved it below the settings paragraphs; (3) that paragraph said every rebase in progress is left alone, so I named the orphaned-autostash exception.
- Review round 2 on the changed hunks: gate PASS, no findings, no open requests.
- Regenerated, refreshed the overlay again, and reran every required check: state-sync tests 93 passed; validator and installer tests 387 passed; `validate_targets.py`, `check_runtime.py`, plan lint exit 0; `verify.py phase` PASS (4967 passed, 1 skipped).
- Reran the three consumer-report probes against the new script: the manual merge keeps `MERGE_HEAD` with no merge commit; the failed-abort pull leaves the rebase in place, the next checkpoint commits nothing, `ai-state` does not move, and the remote keeps `from-A`; the failed setup merge stays at the init commit with `MERGE_HEAD` on disk. No commit holds conflict markers.

## [LEARN] Entries

- [LEARN:security] Forcing a Git operation out (`rebase --quit` after a failed `--abort`) turns a protected state into a silent corrupt one: a detached HEAD with an unmerged index that the next `git add -A` commits. Leave it for a person and guard automatic commits with the operation markers plus `git ls-files -u`.
- [LEARN:review] A consumer's bug report can describe its own hand-patched copy; two items of this report came from the consumer agent's own `rm -f` patch. Diff installed bytes against the shipped version first.
- [LEARN:tooling] A check runner that feeds commands on stdin must run each with `</dev/null`, or a child's stdin drain swallows the remaining commands.
- [LEARN:domain] Updated the `cmd_setup` entry in `.claude/MEMORY.md`: it now returns 1 before restoring adapters or committing while a rebase or merge is left unfinished.

## Verification

```text
PASS        0.3s  uv run python scripts/generate_targets.py --all
PASS       26.2s  uv run pytest tests/test_state_sync.py -q --tb=short
PASS      117.7s  uv run pytest tests/test_validate_targets.py tests/test_install_bootstrap.py -q --tb=short
PASS       49.4s  uv run python scripts/validate_targets.py
PASS        0.9s  uv run python scripts/check_runtime.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS      310.7s  uv run python .claude/scripts/verify.py phase --format text
```

- Findings: `.claude/quality_reports/findings-2026-10-23_phase-A-unfinished-git-operations.json` (0 findings, gate PASS, six profiles).
- optional 1: PASS — reran the three consumer-report scenarios (`probe_state_sync.py` in the session scratchpad) against the regenerated script; each ended with no new commit, and no commit holds conflict markers.

## Open Questions / Next Steps

- Phase B next: the sync lock, the network stall limit, and the exit trap.
