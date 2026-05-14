---
name: iterative-plan-review
visibility: background
description: |
  Plan review loop using the unified reviewer. Use when reviewing implementation
  plans before coding begins or when a plan needs architecture/security critique.
user-invocable: false
---

# Iterative Plan Review

This workflow is now part of `plan-decomposition`; keep this skill as a background trigger for older prompts.

## Workflow

1. Draft or update the plan using `plan-decomposition/SKILL.md`.
2. Run `reviewer` on the plan with profiles:
   - `architecture` for module boundaries and dependency direction.
   - `security` if the plan changes auth, secrets, subprocesses, SQL, file paths, or external input handling.
   - `tests` for test strategy completeness.
   - `documentation` if user-facing docs or generated bootstrap docs change.
3. Fix findings in severity order.
4. Re-run review until no critical or major findings remain, or document the accepted risk.

