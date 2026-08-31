# Checkpointed Terminal Push Recovery

**Status:** IN PROGRESS
**Plan:** .claude/plans/2026-08-31_phase-B-checkpointed-terminal-push-recovery.md

## Symptom

The native pre-push gate rejected the completed implementation branch because
the closeout receipt's nested HEAD predated the checkpoint containing the
receipt-bound completed small plan and terminal big-plan transition.

## Root Cause

The clean-checkpoint validator read the current small plan from the receipt's
older nested HEAD instead of validating checkpointed bytes against the receipt
digest and strict completed-plan identity.
