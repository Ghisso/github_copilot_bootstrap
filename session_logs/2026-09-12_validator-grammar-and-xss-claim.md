# Validator grammar and XSS claim

**Status:** IN PROGRESS

**Plan:** `.claude/plans/2026-09-12_phase-A-validator-grammar-and-xss-claim.md`

## Goal

Correct the skill-frontmatter grammar, placeholder recognition, stale security
claim, and related documentation, with regression coverage.

## Approach

Use the approved one-phase plan. Keep the validator's intentionally small
frontmatter parser, normalize the supported scalar forms once, update the
claim and documentation, then run the required verification and review gates.

## Initial state

- Implementation branch: `2026-09-12_validator-grammar-and-xss-claim_implementation`
- Base branch: `dev`
- Working tree: clean before branch creation
