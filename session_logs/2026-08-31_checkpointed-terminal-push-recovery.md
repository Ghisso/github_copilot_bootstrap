# Checkpointed Terminal Push Recovery

**Status:** COMPLETED
**Plan:** .claude/plans/2026-08-31_phase-B-checkpointed-terminal-push-recovery.md

## Symptom

The native pre-push gate rejected the completed implementation branch because
the closeout receipt's nested HEAD predated the checkpoint containing the
receipt-bound completed small plan and terminal big-plan transition.

## Root Cause

The clean-checkpoint validator read the current small plan from the receipt's
older nested HEAD instead of validating checkpointed bytes against the receipt
digest and strict completed-plan identity.

## Outcome

- The clean-checkpoint path validates the indexed completed small plan against
  the receipt digest and strict identity.
- Only that receipt-bound small plan and the exact terminal big-plan transition
  may differ across the checkpoint range; governing mutations remain denied.
- The regression models separate closeout-evidence and terminal checkpoints.

## Verification and Review

- Full suite: 1,135 passed.
- Quality score: 100/100.
- Review profiles: code, security, tests, ponytail.
- Surviving findings: none.

## [LEARN] Entries

- [LEARN:verification] A clean terminal checkpoint must validate receipt-bound
  worktree bytes that were dirty when evidence was recorded; reading those files
  from the older recorded HEAD reconstructs the wrong authority state.

## Score: 100/100
