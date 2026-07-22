# Session: state-sync-durability SP3 — cmd_migrate push guard

**Date:** 2026-07-22
**Plan:** [.claude/plans/2026-07-22_phase-3-migrate-push-guard.md](../plans/2026-07-22_phase-3-migrate-push-guard.md)
**Status:** COMPLETED

## Goal

Close the twin of the SP1 doomed-push bug in `cmd_migrate` (flagged by the SP1
review as out-of-scope-then). It reconciled via `commit_and_reconcile` and then
pushed unconditionally, so an aborted conflicting merge produced a doomed
non-fast-forward push with a misleading "network/auth" warning.

## Work Log

- `commit_and_reconcile`: `return 1` on the merge-abort path, explicit
  `return 0` on success/no-op paths. `cmd_setup` (never pushes) keeps ignoring
  the result and its restore-adapters tail keeps it returning 0 — behavior
  unchanged.
- `cmd_migrate`: guard the push behind `if ! commit_and_reconcile; then warn
  (conflict, not network); skip; elif <remote>; then push fi`. Preserves the
  original network-failure warning only on the push-attempted path.
- Added two tests: conflicting migrate commits locally but does not push;
  disjoint-file migrate reconciles and pushes.
- Review (reviewer, code/security/tests/ponytail): found a CRITICAL — the
  conflict test's assertions all held under the OLD unguarded code too (git's
  own non-ff rejection keeps the remote unchanged; "conflict" came from a
  pre-existing warn). Fixed by asserting text unique to the new guard
  (`"not pushing"`) and the absence of the old `"network"` warning; reviewer
  re-verified the test now fails against a reverted guard. Final review clean.
- Verified the new post-commit hook's benign side effect: `validate_targets.py`
  hook tests make real commits in isolated temp repos, so post-commit now runs
  state-sync push there — it warns (no origin) or pushes to a temp bare remote
  deleted with the tempdir; git ignores post-commit's exit status, so no test
  commit is affected. validate_targets PASSES.

## [LEARN] Entries

- [LEARN:testing] A regression test for a bug fix must FAIL if the fix is
  reverted. When the buggy code was "harmless" because a lower layer already
  blocked the bad outcome (here git rejects a non-fast-forward push either
  way), assert on a marker unique to the fixed path (a new warning string) and
  on the absence of the old path's marker — outcome-only assertions can pass
  under both old and new code and prove nothing.

## Verification Results

```bash
uv run pytest tests/ -q            # 7 passed
uv run ruff check scripts/ tests/  # All checks passed
uv run python scripts/validate_targets.py   # PASS
# score-20260722T092611Z.json: score 100, dirty false, tests_passed true
# findings-20260722T092611Z.json: 0 critical/major/minor, ponytail_reviewed true, ponytail_findings 0
```

## Score: 100/100

## Open Questions / Next Steps

- Big plan `state-sync-durability` complete after this commit (3 phases).
- Open a PR to `dev` only when the user asks.
