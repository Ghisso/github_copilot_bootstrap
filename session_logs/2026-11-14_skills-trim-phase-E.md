# Session: Closeout, guidance, and validator fixes (skills-and-instructions-trim, Phase E)

**Date:** 2026-11-14
**Plan:** `.claude/plans/2026-11-14_phase-E-closeout-and-guidance-fixes.md`
**Status:** COMPLETED

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
- Review round 1 (`reviewer`, six profiles, the user's acceptance bar stated up front): gate PASS, no CRITICAL or MAJOR, no open request, three MINOR documentation findings: (1) the core's CLOSEOUT step still said "the plan templates point at that file" (only the small-plan and session-log templates do); (2) the core's errata trigger "into reintroducing a defect" was narrower than the closeout file's "actively mislead a reader"; (3) `docs/smoke-tests.md` named only the 16 KiB workflow budget. The reviewer traced the corrected recovery through `record_findings.py`, `verify.py` (`content_hash_for`, `scoped_paths`, `gate_receipt_errors`, `verification_items_errors`), and the commit hook, and confirmed every instruction is true and sufficient; it confirmed no pin got looser and every new test fails without its change.
- Fixes (by the orchestrator, text only): the two core sentences and the smoke-test budget sentence (it now names all six `POLICY_BYTE_BUDGETS` entries). Core 15,965 bytes. After: regenerate + self-refresh exit 0; `validate_targets.py` PASS; `check_runtime.py` exit 0.
- Review round 2 (same reviewer): gate PASS, findings `[]`, no open request; the three edits checked against the files and the generated and installed copies.
- CLOSEOUT step 1: documentation was updated within the phase (README, `docs/smoke-tests.md`, `docs/target-mapping.md`, the authoring `CLAUDE.md`, the project context); this is not the big plan's last phase, so no standing audit here.
- CLOSEOUT step 2: read `.claude/skills/learn/SKILL.md`. Three lessons went to `.claude/MEMORY.md` (below); none needed a skill. The Phase D lesson about auditing the project context was corrected in place: the closeout file's audit list now names it. Small plan set to `status: complete` with every step ticked; Phase E ticked in the big plan.

## [LEARN] Entries

- [LEARN:testing] A whole-file string pin cannot catch the deletion of the section it guards when the guarded string also appears elsewhere; scope the pin to its section and test it with a fixture that keeps the strings outside the section. Saved to `.claude/MEMORY.md`.
- [LEARN:tooling] `grep -F` with a multi-word phrase misses Markdown text wrapped across lines; search with a multi-line pattern before stating a surface does not mention something. Saved to `.claude/MEMORY.md`.
- [LEARN:architecture] A policy pointer added to a skill the workflow sidecar ships verbatim needs a `SIDECAR_WORKFLOW_PATH_REPLACEMENTS` entry, because the sidecar has no `.claude/instructions/`. Saved to `.claude/MEMORY.md`.

## Verification

```text
PASS        0.2s  uv run python scripts/generate_targets.py --all
PASS        3.1s  uv run pytest tests/test_validate_targets.py -q --tb=short -k "closeout_procedure or codex_fallback or frontmatter_yaml or policy_budget or root_guidance or loading_rules or description_cap"
PASS        3.1s  uv run pytest tests/test_verify.py -q --tb=short -k docs_only_recovery
PASS       86.9s  uv run pytest tests/test_validate_targets.py tests/test_validate_plan_frontmatter.py tests/test_verify.py -q --tb=short
PASS        0.0s  test "$(grep -c -F 'repeat step 6 only' shared/policies/closeout.instructions.md)" = "0"
PASS        0.0s  grep -q -F 'findings report content_hash is stale' shared/policies/closeout.instructions.md
PASS        0.0s  grep -q -F 'rg -F' dist/multi-agent/CLAUDE.md
PASS        0.0s  grep -q -F 'rg -F' dist/multi-agent/AGENTS.md
PASS        0.0s  grep -q -F 'config-first-design.instructions.md' dist/multi-agent/.claude/skills/hydra-config/SKILL.md
PASS        0.0s  grep -q -F 'code-standards.instructions.md' dist/multi-agent/.codex/agents/coder.toml
PASS        0.0s  grep -q -F 'review an API or endpoint' shared/skills/code-review/SKILL.md
PASS        0.0s  grep -q -F 'RAG evaluation' shared/skills/rag-auditor/SKILL.md
PASS        0.0s  grep -q -F 'review this research' shared/skills/research-critique/SKILL.md
PASS        0.0s  grep -q -F 'SQL generator' shared/skills/data-and-graph-pitfalls/SKILL.md
PASS        0.0s  test "$(wc -c < shared/policies/workflow.instructions.md)" -le 16000
PASS        0.0s  test "$(wc -c < shared/policies/workspace.instructions.md)" -le 7500
PASS        0.0s  test "$(wc -c < dist/multi-agent/CLAUDE.md)" -le 4500
PASS        0.0s  test "$(wc -c < dist/multi-agent/AGENTS.md)" -le 4800
PASS        0.0s  test "$(grep -c -F 'before REVIEW' CLAUDE.md)" = "0"
PASS        0.0s  test "$(grep -c -F 'Once the 2.x migration merges' .claude/instructions/project-context.instructions.md)" = "0"
PASS       45.0s  uv run python scripts/validate_targets.py
PASS        0.7s  uv run python scripts/check_runtime.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS      327.6s  uv run python .claude/scripts/verify.py phase --format text
```

- Findings: `.claude/quality_reports/findings-2026-11-14_phase-E-closeout-and-guidance-fixes.json` (0 findings after review round 2; gate PASS; six profiles; round 1 had three MINORs, all fixed before round 2).
- Phase receipt: `verify.py phase --persist` PASS (Ruff, mypy, pytest, freshness, provenance, generation); the two earlier full runs reported pytest 5151 passed, 1 skipped.
- optional 1: PASS — this phase's CLOSEOUT steps 1 to 4 were taken from the corrected `.claude/instructions/closeout.instructions.md` alone, in its order; nothing about their action or order had to come from elsewhere. Steps 5 to 8 follow the same file after this log is final.

## Open Questions / Next Steps

- Phase F (`2026-11-14_phase-F-installer-safety`) is next; the post-commit hook sets it `in-progress`.
- The user has not yet confirmed Decisions 8 to 12 in the big plan.
