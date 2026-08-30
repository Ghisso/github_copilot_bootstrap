# Terminal Push Provenance Recovery

**Status:** COMPLETED
**Plan:** .claude/plans/2026-08-30_phase-C-terminal-push-provenance.md

## Root Cause

Phase B closeout bound the big plan while it was `in-progress`. The successful
final commit then changed the big plan to `complete` and cleared
`current_phase`, so pre-push rejected the otherwise valid receipt as stale.

## Result

- Pre-push accepts only the exact automatic terminal big-plan transition.
- Both an unstaged transition and a supported clean nested checkpoint are covered.
- Runtime, plan-content, index/dirty, and receipt mutations remain stale.
- Python bytecode caches remain provenance-bound.
- Full suite: 1107 passed.
- Review: no surviving findings.

[LEARN] Saved the terminal-plan provenance lesson to `.claude/MEMORY.md`.
