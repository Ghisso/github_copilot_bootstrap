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
- Phase E set to `in-progress` (reopen step 7); `validate_plan_frontmatter.py` exit 0. Nested checkpoint `653df9d` (reopen step 8).
- Delegation by file ownership: `coder` took Steps 1-5 (tests, closeout procedure, validators, workflow core, root-guidance MEMORY sentence, authoring `CLAUDE.md`, `hydra-config` pointer, coder prompt) plus the stale test comment; `documenter` took Step 6 (four descriptions, README, docs, workspace policy, orchestrator prompt, project context). Neither ran the generator or the validators.
- Documenter: the four descriptions now carry the restored triggers (listing lengths 197, 287, 295, 293); `rag-auditor` dropped "retrieval precision" and "chunk quality", `research-critique` dropped "strengths and weaknesses". Workspace 7,474 bytes after cutting "(coder discipline, not a lifecycle phase)" (no reference anywhere). Project context: `dev` is 18 commits ahead of `main` at `cfde280` (PR #55 merge), pins Context Mode `2.1.8`; the one unmerged branch is this one.
- Coder: every new test failed first for the right reason (section-scoping, third message, fallback naming, the seven YAML forms for both keys, five budgets, `rg -F` in root guidance, the bug-fix and code-standards reads); `docs_only_recovery` pins existing behavior, so it passed first and fails when `scoped_paths` is mutated to keep docs. Mutations (recovery section removed, third message removed, `hydra-config` policy mention removed) each failed a test and were restored byte-identical. R2: no reader of errata files in `shared`, `scripts`, or the hooks; the rule is now "a sibling errata file is allowed for any closed log, bound or not; the log never changes".
- Scope changes decided during implementation: (1) the workflow sidecar ships `hydra-config` but has no `.claude/instructions/`, so a new `SIDECAR_WORKFLOW_PATH_REPLACEMENTS` entry deletes the pointer sentence in that build (denylisting the skill was rejected as a behavior change); 16 sidecar tests had failed before it. (2) `plan-lifecycle.instructions.md` lines 137 and 148 now name `.claude/scripts/validate_plan_frontmatter.py`. (3) The Verification Evidence Contract sentence names exactly its four linking surfaces (the `plan-decomposition` link wraps across lines, so `grep -F` first missed it).
- Integration: `generate_targets.py --all` exit 0; `install_bootstrap.py . --allow-self --local-only` exit 0, no refusal; `validate_targets.py` PASS; `check_runtime.py` exit 0; `validate_plan_frontmatter.py` exit 0; every quick Verification item PASS (workflow core 15,971; workspace 7,474; closeout 16,185 of its 16,384 budget; plan-lifecycle 10,073); `verify.py phase --format text` PASS (Ruff 0, mypy 0, pytest 5151 passed, 1 skipped).

## [LEARN] Entries

## Verification

## Open Questions / Next Steps
