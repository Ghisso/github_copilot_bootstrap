---
name: 2026-08-30_phase-C-terminal-push-provenance
type: small-plan
parent_plan: consumer-verification-provenance-hardening
phase_index: 2
status: complete
closeout_session_log: .claude/session_logs/2026-08-30_terminal-push-provenance.md
---
# Small Plan: 2026-08-30_phase-C-terminal-push-provenance

## Scope

Fix the normal final-commit transition so pre-push provenance accepts only the
validated automatic big-plan transition from the recorded active final phase to
the current completed plan. Preserve staleness for every other plan/runtime
change.

## Steps

- [x] Add a narrow terminal-transition provenance validator.
- [x] Add positive installed pre-push coverage after the final commit.
- [x] Add negative plan-content and non-terminal transition coverage.
- [x] Run full verification, review, closeout, and commit.

## Acceptance Criteria

- [x] The completed branch pushes through the native pre-push gate.
- [x] Only the expected status/current-phase transition is exempted.
- [x] Runtime, active-plan content, receipt, and unrelated nested mutations remain stale.

## Closeout Checklist

- [x] Verification passed
- [x] Review findings resolved
- [x] Score >= 90 persisted
- [x] Documentation updated or explicitly skipped
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log is COMPLETED
