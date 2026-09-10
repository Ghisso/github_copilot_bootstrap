# Phase A Commit Closeout Reliability Review

**Profiles:** code, architecture, security, tests, ponytail, documentation  
**Gate:** commit  
**Result:** FAIL

## Critical

- `[high] [documentation] docs/architecture.md:297` — Live guidance still
  describes the deleted PostToolUse command-parser path and the superseded
  receipt order. `shared/policies/workspace.instructions.md:70`,
  `README.md:242`, and `docs/runtime-checks.md:348` also place `verify phase`
  before review, documentation, and findings. Update every live guide to the
  native hook and one canonical final ordering.

## Major

- `[high] [code] shared/hooks/scripts/record-commit-closeout.sh:69` — Candidate
  phases accept every unique status except `cancelled`. Missing, invalid,
  paused, and already-complete statuses can become `current_phase`; repeated
  invocation for one `HEAD` can advance another phase. Require the exact
  eligible state and add a regression test.
- `[high] [code] shared/hooks/git-hooks/post-commit:26` — Closeout failures are
  masked before state synchronization, malformed-state branches can exit
  silently, and the terminal transition uses two writes that can publish
  partial state. Make the transition atomic and emit a durable actionable
  warning before synchronization.
- `[high] [code] shared/scripts/verify.py:2685` — Complete-plan recovery can
  recommend the wrong phase because later missing, unreadable, or malformed
  phase metadata is skipped. Validate the declared sequence and return the
  specific fault before selecting the last completed non-cancelled phase.
- `[high] [tests] tests/test_commit_closeout.py:87` — Native-hook coverage lacks
  failed-commit, non-implementation, merge, repeated-invocation,
  editor-produced commit, and runtime-order cases. Make the sync stub record
  the plan state it observes.

## Minor

- `[medium] [security] shared/scripts/record_findings.py:92` — Untracked-path
  warnings follow symlinks and render control characters without escaping.
  Use lexical containment, keep target-root confinement, escape display names,
  and test symlink and newline filenames.

## Required remediation

All findings must be fixed and the same profile set must pass a fresh
two-pass review before Phase A closeout.
