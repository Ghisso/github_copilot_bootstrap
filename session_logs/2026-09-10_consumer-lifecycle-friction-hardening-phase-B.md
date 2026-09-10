# Consumer Lifecycle Friction Hardening — Phase B

**Status:** PAUSED
**Plan:** `.claude/plans/2026-09-10_phase-B-root-adapter-recovery-diagnostics.md`
**Branch:** `consumer-lifecycle-friction-hardening_implementation`
**Started:** 2026-09-10T11:52:00Z

## Goal

Restore installer-owned ignored root adapters after every successful state
pull and make verifier provenance failures name the affected manifest-relative
path without exposing file contents.

## Starting state

- Phase A committed as `9838cc4` and native post-commit advancement selected
  Phase B.
- Outer and nested repositories were clean at Phase B start.
- The approved Phase B plan remains implementation-ready; Phase A introduced
  no material change to its assumptions.

## Completed work

- Phase A committed as `9838cc4`; native post-commit advancement selected
  Phase B.
- Baseline Phase B verification passed with 297 focused tests.
- The first implementation changed `shared/scripts/verify.py`,
  `shared/hooks/scripts/state-sync.sh`, `shared/devcontainer/post-start.sh`,
  `scripts/validate_targets.py`, `tests/test_state_sync.py`, and
  `tests/test_verify.py`.
- `cmd_pull` now follows local setup, one reconciliation or deliberate no-op,
  adapter restoration, and a final checkpoint. Failed reconciliation returns
  before restoration. The devcontainer no longer performs an unconditional
  restore after the fail-open pull wrapper.
- Verifier diagnostics preserve `bootstrap_root_fingerprint(root) -> str` and
  receipt schema v4 while collecting bounded manifest-relative `path`, `side`,
  and `category` details from the same filesystem walk.
- Initial implementation verification passed: 304 focused state-sync,
  verifier, and installer tests; Ruff lint and format; changed-scope Mypy;
  runtime checks; and `verify.py fast`.
- The first two-pass review found four blocking issues: over-broad recovery
  advice, missing conflicted-pull restoration coverage, missing initialized
  consumer branch-switch recovery coverage, and stale live documentation.
- Review remediation is present but not yet verified. It expands
  `tests/test_install_bootstrap.py`, conflict/state-sync tests, and verifier
  repairability tests. It also restores standalone `cmd_setup`'s existing-repo
  early return so installer changes remain a `bootstrap: update` commit.

## Verification state

- `git diff --check` passed at the checkpoint.
- Before the last remediation round, independent generated validation failed
  because `cmd_setup` absorbed installer changes into a generic `session:`
  commit. The current diff contains the identified early-return fix, but
  `scripts/validate_targets.py` has not been rerun after that fix.
- No focused or full verification has run against the final seven-file paused
  diff. No fresh re-review has run. Findings, phase receipt, and closeout
  receipt have not been persisted for Phase B.

## Remaining work

- Run focused tests for `tests/test_state_sync.py`, `tests/test_verify.py`, and
  `tests/test_install_bootstrap.py`; fix any deterministic failures.
- Regenerate targets, then run `scripts/validate_targets.py` and
  `scripts/check_runtime.py`. Confirm the legacy history is exactly
  `migrate: import pre-git state` followed by `bootstrap: update ...`.
- Confirm recovery advice is suppressed for symlink ancestry, tracked drift,
  unsupported or unreadable destinations, and extra live directory entries.
- Confirm a real pull conflict leaves the adapter absent, preserves nested
  state, and clears merge/rebase state.
- Confirm an already-initialized generated consumer restores an ignored
  `.github/**` adapter after an outer branch switch while preserving a tracked
  adapter and a valid, clean nested repository.
- Re-run the six-profile two-pass review. After code review converges, update
  live restoration and diagnostic guidance with the documenter, then review
  the final code and documentation again.
- Complete the ordinary Phase B closeout: final plan/log/LEARN state, explicit
  staging, clean findings, persisted phase and closeout receipts, and one
  completion commit.

## Exact resume point

1. Read this log and the paused Phase B plan. Set the same plan back to
   `in-progress` while preserving the pause metadata.
2. Inspect `git log --oneline -10`, `git status`, and the seven-file diff. Do
   not edit the completed Phase A log or receipt-bound Phase A plan evidence.
3. Resume the interrupted Phase B review remediation from the current working
   tree. Start with:

   ```bash
   uv run pytest tests/test_state_sync.py tests/test_verify.py tests/test_install_bootstrap.py -q
   uv run python scripts/generate_targets.py --all
   uv run python scripts/validate_targets.py
   uv run python scripts/check_runtime.py
   uv run python .claude/scripts/verify.py fast --format json
   ```

4. Route any failures back to the Phase B coder. Re-review only after every
   deterministic check above passes.
