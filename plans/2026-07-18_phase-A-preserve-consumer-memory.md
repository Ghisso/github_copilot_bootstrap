---
name: 2026-07-18_phase-A-preserve-consumer-memory
type: small-plan
parent_plan: preserve-consumer-memory
phase_index: 1
status: in-progress
closeout_session_log: .claude/session_logs/2026-07-18_preserve-consumer-memory.md
---

# Small Plan: Preserve Consumer Memory

## Scope

Correct the installer copy boundary so an existing `.claude/MEMORY.md` remains
consumer-owned state while fresh installs still receive the generated seed.

## Steps

- [x] Reproduce git-backed reinstall data loss.
- [x] Reproduce legacy pre-git migration data loss.
- [x] Skip only an existing consumer `.claude/MEMORY.md` during generated copy.
- [x] Add regression coverage for both refresh paths.
- [x] Document fresh-seed and refresh-preservation behavior.
- [x] Complete verification, review, and score.

## Closeout Checklist

- [x] Verification passed
- [x] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [x] Documentation updated
- [x] LEARN entries saved
- [ ] Closeout session log has `**Status:** COMPLETED`
