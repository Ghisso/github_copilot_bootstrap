---
name: 2026-08-12_phase-G-cancellation-contract-drift-guard
type: small-plan
parent_plan: state-sync-recovery-and-plan-cancellation
phase_index: 7
status: complete
closeout_session_log: .claude/session_logs/2026-08-12_big-plan-closeout-state-sync-recovery-and-plan-cancellation.md
---

# Small Plan: 2026-08-12_phase-G-cancellation-contract-drift-guard

## Scope

Resolve the single minor finding from the big-plan closeout review of
`dev...HEAD`. The cancellation-evidence contract introduced across Phases C and
D is implemented twice with nothing recording the split and nothing forcing the
copies to agree:

- `validate_cancellation` in `scripts/validate_plan_frontmatter.py` is
  authoring-repo-only tooling that never ships.
- `cancellation_validation_probe` in `shared/hooks/scripts/_lib-frontmatter.sh`
  ships into consumer `.claude/hooks/scripts/` and enforces the same contract at
  push time, so it must run on a stock `python3` with no imports.

The duplication is justified by that dependency constraint, so this phase
documents it and guards it rather than collapsing it. Tightening the timestamp,
block-scalar, or evidence-status rule in one copy must no longer leave the other
permissive.

This phase changes no runtime behaviour. It adds comments and tests only. It
does not reopen Graphify and does not touch the Context Mode boundary.

## Steps

- [x] Record the rationale for the deliberate duplication at both definitions,
      naming the other copy and the reason it cannot be shared.
- [x] Pin the shared timestamp, block-scalar, and evidence-status patterns plus
      the required cancellation field names across both copies in
      `tests/test_validate_plan_frontmatter.py`.
- [x] Prove the guard is load-bearing by perturbing the shipped pattern and
      observing a drift failure, then restoring it.
- [x] Regenerate targets and refresh the dogfood install.

## Verification

```bash
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
bash -n shared/hooks/scripts/_lib-frontmatter.sh
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/check_runtime.py
```

## Review Profiles

- `.claude/review-profiles/code.md`
- `.claude/review-profiles/tests.md`
- `.claude/review-profiles/ponytail.md`
- `.claude/review-profiles/documentation.md`

## Results

- `uv run pytest tests/ -q` — 801 passed.
- `uv run mypy .` — no issues in 22 source files.
- Ruff check and `format --check` — clean.
- `bash -n` on the changed shell library — OK.
- Generation, target validation, plan frontmatter, and runtime checks — pass,
  zero runtime failures.
- Load-bearing proof: perturbing the shipped `TIMESTAMP` pattern fails
  `test_shipped_probe_shares_the_cancellation_rules` with an explicit drift
  message; restored afterwards.
- Score 100/100 (EXCELLENCE); findings 0 critical, 0 major, 0 minor.

## Done Criteria

- [x] The duplication rationale is recorded at both definitions.
- [x] A load-bearing test pins the shared rules and field names.
- [x] Full verification, score, and findings gates pass.
- [x] No runtime behaviour changed.

## Closeout Checklist

- [x] Verification passed
- [x] Review findings resolved
- [x] Score >= 90 persisted with branch/phase metadata
- [x] Documentation updated
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
