# Session: Closeout, guidance, and validator fixes (skills-and-instructions-trim, Phase E)

**Date:** 2026-11-14
**Plan:** `.claude/plans/2026-11-14_phase-E-closeout-and-guidance-fixes.md`
**Status:** IN-PROGRESS

## Goal

Fix review findings R1 to R12 (`.claude/quality_reports/merges/2026-11-14_skills-and-instructions-trim-review-claude.md`): the closeout recovery for a late documentation change, the errata and coverage wording, the session-log update lines, the MEMORY literal-search rule, the Codex routes to two policies and the regression-test rule, the YAML-form and budget gaps in the validator, lost trigger phrases, and outdated docs (REQ-011).

## Work Log

- Reopen: on 2026-11-14 a consolidated review (four Claude phase reviewers, two Codex reports, and the main agent's own runs) held the PR. Findings R1 to R23 are recorded in the quality report above. The big plan was reopened per `.claude/instructions/plan-lifecycle.instructions.md` with Phases E, F, and G (`planned`), `status: in-progress`, and `current_phase` set to Phase E. `validate_plan_frontmatter.py` exit 0.
- Approval: the user asked for the fix plan ("ok do it"), then, before going to sleep, put the main agent in charge of implementing it to the end of the full big plan. That approves Phases E to G as written. Decisions 8 to 12 were taken with their recommended options while the user was away and are recorded in the big plan for the user to confirm or overturn.
- Material-impact check: the review findings are this phase's scope; no planner run (the main agent drafted the plans from the verified findings).
- Devil's advocate (separate read-only Opus subagent, `xhigh`, with `.claude/skills/devils-advocate/SKILL.md`): two HIGH, six MEDIUM, seven LOW, verdict "go ahead after changing the plans". Folded in before implementation. Phase E: Phase B size targets kept, with `wc -c` checks and named cuts in the core; the existing budget pin test and docstring added to Step 1; the R6 fixture keeps all three messages outside the section; the docs-only recovery no longer reruns the dry run, and an unintended edit is undone instead of staged; a `docs_only_recovery` test in `tests/test_verify.py` replaces the unrunnable optional check; the bug-fix trigger joins the existing tests-read entry; R11 lengths and grep lines added. Phase F: the symlink preflight covers every writer, runs after `commit_copilot_surface` and before `migrate_pre_existing_state`, and skips (does not refuse) a README under a symlinked consumer-state folder; no copy-time guard; R17 lists live folders only; a validator check for R14's assumption; real-consumer shapes on scratch clones. Phase G: exact-phrase checks. Big plan: Decisions 8, 9, and 12 updated.
- Phase E set to `in-progress` (reopen step 7); `validate_plan_frontmatter.py` exit 0.

## [LEARN] Entries

## Verification

## Open Questions / Next Steps
