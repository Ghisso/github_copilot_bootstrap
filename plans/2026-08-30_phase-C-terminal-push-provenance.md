---
name: 2026-08-30_phase-C-terminal-push-provenance
type: small-plan
parent_plan: consumer-verification-provenance-hardening
phase_index: 2
status: in-progress
closeout_session_log:
---
# Small Plan: 2026-08-30_phase-C-terminal-push-provenance

## Scope

Fix the normal final-commit transition so pre-push provenance accepts only the
validated automatic big-plan transition from the recorded active final phase to
the current completed plan. Preserve staleness for every other plan/runtime
change.

## Steps

- [ ] Add a narrow terminal-transition provenance validator.
- [ ] Add positive installed pre-push coverage after the final commit.
- [ ] Add negative plan-content and non-terminal transition coverage.
- [ ] Run full verification, review, closeout, and commit.

## Acceptance Criteria

- [ ] The completed branch pushes through the native pre-push gate.
- [ ] Only the expected status/current-phase transition is exempted.
- [ ] Runtime, active-plan content, receipt, and unrelated nested mutations remain stale.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted
- [ ] Documentation updated or explicitly skipped
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log is COMPLETED
