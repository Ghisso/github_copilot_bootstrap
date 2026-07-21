---
name: 2026-07-21_phase-1-state-sync-local-only-regression
type: small-plan
parent_plan: state-sync-local-only-regression
phase_index: 1
status: complete
closeout_session_log: .claude/session_logs/2026-07-21_state-sync-local-only-regression.md
---

# Small Plan: 2026-07-21_phase-1-state-sync-local-only-regression

## Scope

Correct the shared state-sync control flow so a direct local-only pull still
initializes the nested `.claude` Git repository, and so an invalid explicit
repository root degrades to the existing path-resolution behavior. Extend the
authoring repository's Python validator with real subprocess checks; no new
shell test framework is required.

## Steps

- [x] Modify `shared/hooks/scripts/state-sync.sh` so `cmd_pull` calls
  `cmd_setup` before evaluating local-only mode, and make an unusable
  `AI_STATE_REPO_ROOT` warn then fall back to the current script-relative
  resolution cases.
- [x] Modify `scripts/validate_targets.py` to assert that a fresh direct
  `pull --local-only` creates a nested `ai-state` repository without remote
  I/O, and that an invalid root override warns but exits successfully through
  fallback resolution.
- [x] Run syntax, target-generation, target-validation, runtime, pytest,
  typing, linting, and focused manual smoke checks; review the control-plane
  diff with `code`, `architecture`, `security`, `tests`, and `ponytail`.

## Verification

```bash
bash -n shared/hooks/scripts/state-sync.sh
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run mypy scripts/ --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run python .claude/scripts/quality_score.py scripts/ --phase 2026-07-21_phase-1-state-sync-local-only-regression --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
```

## Closeout Checklist

- [x] Verification passed
- [x] Review findings resolved
- [x] Score >= 90 persisted with branch/phase metadata
- [x] Documentation skipped: pure internal regression repair
- [x] LEARN entries saved
- [x] Closeout session log has `**Status:** COMPLETED`
