# Session: Instructions split and trims (skills-and-instructions-trim, Phase B)

**Date:** 2026-11-13
**Plan:** `.claude/plans/2026-11-12_phase-B-instructions.md`
**Status:** IN-PROGRESS

## Goal

Fix exploration section 7 defects 2 to 6, move CLOSEOUT into `closeout.instructions.md` and the plan-lifecycle rules into `plan-lifecycle.instructions.md`, replace the competing closeout procedures with pointers, switch the MEMORY rule to a targeted search, and trim root guidance, policies, and prompts to their budgets (REQ-002, REQ-007, REQ-008).

## Work Log

- Phase A committed as `ba629ba` and pushed; the post-commit hook set Phase B `in-progress`. Material-impact check: Phase A's only design change (the mirror keeps the marker) does not touch Phase B, C, or D; no planner run.
- Sidecar check: the sidecar ships its own workflow rule (`shared/sidecar/workflow/rules/workflow.md`), templates, and agent `workflow-prompt.md` files, and denies the `commit`, `plan-decomposition`, `code-review`, and `knowledge-refresh` skills (`shared/sidecar/workflow/skills.txt`). Phase B leaves `shared/sidecar/**` and every `workflow-prompt.md` unchanged, so no sidecar unit names the two new files.
- Delegation (one phase, split by file ownership instead of the B1/B2 fallback): coder alpha Step 1 (validator pins and tests, failing first); coder beta-1 Step 2 (workflow split, closeout and plan-lifecycle files, knowledge-refresh skill); coder beta-2 Steps 6 and 7 (agent prompts, templates, commit/plan-decomposition/code-review skills, plan-frontmatter comment); coder gamma Steps 3 to 5 (generator root guidance, authoring `CLAUDE.md`, workspace and other policies, project context, `docs/runtime-checks.md`); documenter Step 7 (README, `docs/architecture.md`). No content agent runs the generator or validators; alpha integrates after all edits settle.

## [LEARN] Entries

## Verification

## Open Questions / Next Steps
