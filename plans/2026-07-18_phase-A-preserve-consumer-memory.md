---
name: 2026-07-18_phase-A-preserve-consumer-memory
type: small-plan
parent_plan: preserve-consumer-memory
phase_index: 1
status: complete
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

## Resolution

Recorded 2026-10-20 by `backlog-followups` Phase A. The work was committed
as `18e0a08` and merged into `dev` as PR #8 (`ab87dd7`) on 2026-07-18. The
linked session log still says BLOCKED because the score gate of that time
(score 85, below the required 90) stopped the agent's own commit. That score
gate was removed on 2026-09-02 (`2af3df7`), when `verify.py` became the only
deterministic authority. The unticked closeout items above are left as they
were: they were never met.
