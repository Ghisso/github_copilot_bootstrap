# Session: Bootstrap efficiency fixes (identifiably broken issues)

**Date:** 2026-07-22
**Plan:** .claude/plans/bootstrap-efficiency-fixes.md
**Status:** COMPLETED

## Goal

Fix only the identifiably broken control-plane issues from the
`industrial-inspection` efficiency investigation, defer the speculative
batching/policy work, then roll the fixes out to that consumer. Normal
branch/score/findings lifecycle intentionally skipped (the change edits that
lifecycle).

## Work Log

- Reviewed the consumer findings and the earlier speculative `improvement_plan`;
  critiqued the plan and separated provably-broken defects from unverifiable /
  efficiency-policy items. Confirmed with code/docs grounding.
- Established that MCP parity was NOT a bootstrap defect (identical servers
  generated for all targets; consumer hand-edit caused the drift), and that the
  largest usage driver (coder/reviewer thread growth) is out of scope here.
- **B2:** installer derives Python version from consumer `requires-python`
  across 4 surfaces; fresh/compound specs keep the `3.12+` baseline;
  `check_runtime` warns on baseline drift.
- **B3:** reordered lifecycle to `REVIEW -> DOCUMENT -> SCORE` everywhere so
  documenter edits stop staling the whole-tree `content_hash`-bound reports.
  Decision: doc-only changes are NOT re-reviewed (user directive).
- **B4:** `UV_CACHE_DIR` -> `${containerWorkspaceFolder}/.uv-cache`; added
  `.uv-cache/` to ignore block and repo `.gitignore`.
- **B5:** documented the typed-role fresh-spawn rule in the orchestrator prompt.
- Regenerated `dist/`, re-synced the ignored root overlay (`.github/instructions`,
  `CLAUDE.md`), ran the full validator + tests.
- Second commit: `merge_gitignore` now refreshes an existing ignore block in
  place so `.uv-cache/` reaches consumers that already had the block.
- Rolled out to `industrial-inspection` (full update + `ai-state` push);
  verified all four fixes live plus `.uv-cache/` now ignored.
- Agent commits are blocked on `dev` by `enforce-commit-gate.sh` (PreToolUse,
  not bypassable with `--no-verify`); the user ran both commits as a human.

## [LEARN] Entries

- [LEARN:hooks] `enforce-commit-gate.sh` (PreToolUse) denies agent `git commit`
  on any branch that is not `<plan>_implementation`, including `dev`.
  `--no-verify` does not help (it skips git's own hooks, not PreToolUse). A
  human commit bypasses it; the `commit-msg` git hook passes through on `dev`.
- [LEARN:generator] The bootstrap self-installs its own output; regenerating
  `dist/` staled the gitignored root overlay (`.github/instructions`, root
  `CLAUDE.md`), which `validate_targets.py` rejects until re-synced from `dist/`.
- [LEARN:installer] `merge_gitignore` only *appended* its block when absent, so
  ignore-pattern changes never reached existing consumers until it was changed
  to refresh the block in place.
- [LEARN:score] `content_hash` binds score/findings to the whole-tree diff, so
  any post-SCORE tracked edit (e.g. DOCUMENT) stales both reports.

## Verification Results

```bash
uv run python scripts/generate_targets.py --all   # generated multi-agent
uv run python scripts/validate_targets.py          # PASS generated target is structurally valid
uv run python scripts/check_runtime.py             # PASS (incl. baseline check)
uv run pytest tests/ -q                            # 1 passed
uv run mypy scripts/install_bootstrap.py scripts/check_runtime.py --ignore-missing-imports  # Success
uv run ruff check scripts/install_bootstrap.py scripts/check_runtime.py                     # All checks passed
```

## Score: N/A

Score/findings ceremony intentionally skipped this session (lifecycle change).

## Open Questions / Next Steps

- Deferred: measure real (uncached) token cost before attempting the batching /
  turn-budget policy work.
- Existing consumers other than `industrial-inspection` not yet refreshed.
- Root `focused-fixes-plan.md` superseded by this plan and removed.
