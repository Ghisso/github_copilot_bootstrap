---
name: 2026-11-14_phase-E-closeout-and-guidance-fixes
type: small-plan
parent_plan: skills-and-instructions-trim
phase_index: 5
# status must occur exactly once: planned | in-progress | paused | complete | cancelled
# New phase files default to planned (not yet started); the branch-creation
# and post-commit hooks flip the active phase to in-progress automatically.
status: in-progress
closeout_session_log:
# Pause fields (required only when status is paused):
# paused_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# paused_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# pause_session_log: <repository-relative readable UTF-8 PAUSED session log>
# Cancellation fields (required only when status is cancelled):
# cancelled_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# cancelled_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# cancelled_evidence: <repository-relative readable UTF-8 CANCELLED artifact>
---

# Small Plan: 2026-11-14_phase-E-closeout-and-guidance-fixes

## Scope

The 2026-11-14 review found that the closeout file's recovery for a late documentation change leads to a refused commit, and that several guidance, validator, and documentation statements are wrong or weak. This phase fixes findings R1 to R12 of `.claude/quality_reports/merges/2026-11-14_skills-and-instructions-trim-review-claude.md`:
- the closeout procedure's recovery, errata, coverage, and wording problems (R1 to R6);
- the MEMORY search rule's example, which is a regular-expression trap when pasted into `grep` or `rg` (R7);
- the weak Codex routes to the config-first-design and code-standards policies, and the hard-to-reach regression-test rule (R8);
- the description cap's blind spots for some YAML forms, and missing byte budgets (R9, R10);
- trigger phrases the skill trim dropped (R11);
- outdated documentation outside the installer area (R12).

It runs before the installer phase so that Phases F and G close out with the corrected procedure. Covers REQ-011 in the big plan. The phase owns the files its steps list; a file may be revisited after a failing-first test or a review finding.

Review acceptance bar (the user's rule for guard and checker work): block only on a decision looser than before, a hole this change introduces, or a false or missing statement about what is checked. List any other pre-existing gap as a follow-up in `docs/target-mapping.md` instead of chasing it.

Risk notes:
- Size targets from Phase B stay the acceptance line, and the verification block checks them with `wc -c`. Room left today:
  - workflow core: 45 bytes under 16,000 (its validator limit is 16 KiB);
  - generated `AGENTS.md`: 35 bytes under 4,800 (limit 5 KiB);
  - generated `CLAUDE.md`: 66 bytes under 4,500 (limit 5 KiB);
  - workspace policy: 34 bytes under 7,500.
- Every addition must be paid for by removals in the same file. The planned cuts in the core are: one full MEMORY rule instead of two copies, and one session-log reminder line instead of three (Session Logging "Frequency", Context Management, Manual reminders), carrying the R4 exception.
- Validator pins guard the closeout steps, the hard rules, the stale-receipt messages, and "CLOSEOUT sequence" pointers. Change pinned text only together with its pin and test.
- R2 (errata) is decided by evidence. If a script or hook reads `*.errata.md` files to decide a gate, stop and report instead of choosing a rule. The check in `scripts/validate_targets.py` (about lines 7152-7488) that writes an errata file to show the push gate ignores it is not such a reader.

## Steps

- [ ] **1. Write the failing tests first.**
  - Owner: `coder`. Files (modify): `tests/test_validate_targets.py`, `tests/test_verify.py`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/testing-patterns/SKILL.md`.
  - Every new test name contains one of `closeout_procedure`, `codex_fallback`, `frontmatter_yaml`, `policy_budget`, `root_guidance`, or `docs_only_recovery`.
  - `closeout_procedure` (R6, R1): build a fixture that keeps all three stale-receipt messages outside the recovery section (for example in step 6 and in a hard rule), then remove the whole "Recovering from a stale receipt" section. Validation must fail, so only the new section scoping can catch it. The section must also name `findings report content_hash is stale`. The real file passes.
  - `docs_only_recovery` (R1), in `tests/test_verify.py`: a documentation-only edit changes `content_hash_for` (the findings hash) but leaves the phase receipt's scoped content hash unchanged. This pins the fact the corrected recovery relies on.
  - Update the existing budget pins that R10 makes false: `test_root_guidance_budget_limits_are_pinned` (it asserts the workflow core is the only budgeted policy) and the docstring of `test_root_guidance_budget_workflow_policy_stays_within_16_kib` ("Other policies have no byte budget").
  - `codex_fallback`: for each entry of `CODEX_POLICY_SKILL_FALLBACKS`, a fixture skill whose `SKILL.md` does not name its mapped policy file fails; the five real skills pass (R8). `bentoml-service` must name both `api-service-standards.instructions.md` and `deployment.instructions.md`.
  - `frontmatter_yaml`: each of these `description` forms is rejected with `SKILL_FRONTMATTER_INVALID`, or measured at its true length and failing the cap: `|+`, `>2`, `| # comment`, a plain value continued on indented lines, and a double-quoted value continued on the next line (R9). Each case's text is over 300 characters. The 37 real skills still pass.
  - `policy_budget`: each new `POLICY_BYTE_BUDGETS` entry fails one byte over its limit and passes at it (R10).
  - `root_guidance`: the generated `CLAUDE.md` and `AGENTS.md` MEMORY sentence contains `rg -F` (R7).
  - Record each new test's first failing run in the session log. For the closeout and fallback checks, mutate the source to remove the guarded text and confirm the test fails, then restore it byte-identical.

- [ ] **2. Correct the closeout procedure.**
  - Owner: `coder`. Files (modify): `shared/policies/closeout.instructions.md`, `scripts/validate_targets.py` (`CLOSEOUT_STALE_RECEIPT_MESSAGES` and `closeout_procedure_errors`). Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/documentation/SKILL.md`.
  - R1, the documentation-only branch of "`closeout receipt final tracked state is stale`":
    - the phase receipt stays valid, because its content hash skips ordinary documentation;
    - the findings report does not: its `content_hash` covers every tracked change from the merge base, documentation and unstaged edits included, and the commit gate recomputes it;
    - so: stage, re-record findings with the step 4 recorder command, repeat step 5 only if the session log changed, then repeat step 6. Do not rerun the closeout dry run: the gate never compares the log's summary lines, and step 6 runs every required item again.
    - Fix the sentence saying an unstaged edit "alone does not" stale anything: it does not stale the closeout receipt's tree, but it does stale the findings hash.
  - Add a third recovery entry for `findings report content_hash is stale`. Cause: a tracked change after the findings were recorded. Repair: inspect `git diff`. An unintended edit is undone (for example `git restore <path>`) and nothing needs redoing. An intended one follows the documentation-only or the code branch above. Add the message to `CLOSEOUT_STALE_RECEIPT_MESSAGES`.
  - R6: `closeout_procedure_errors` checks the three messages inside the "Recovering from a stale receipt" section only, not anywhere in the file.
  - R2: first run `rg -n -F 'errata' shared/scripts shared/hooks scripts`. If nothing reads errata files to decide a gate (see the risk note), make the standing audit passage say a sibling `<log-name>.errata.md` is allowed for any closed log, bound by a receipt or not, when an entry would actively mislead a reader; the closed log itself never changes. This matches the Immutability paragraph. The core's copy is fixed in Step 3.
  - R3: the provenance coverage list names the big plan and every small plan listed in its `phases:`, and says to revise a future phase's plan before step 3 or after the commit.
  - R5:
    - the completion-commit list says it holds the review conditions, and names the other gate checks in one sentence (small plan complete with `closeout_session_log`, the log's status and LEARN section, the final-phase audit section, plan frontmatter checks, and optional-item outcomes);
    - the recovery section opens with one sentence: these recoveries are the exception to the FIX LOOP rule when only receipt state went stale and no code changed;
    - step 3's reason says `verify closeout` refuses to produce a passing receipt, not that it "refuses to run at all";
    - step 6's reason no longer says "last";
    - the opening paragraph names the small-plan and session-log templates, not "the plan templates".
  - Standing audit surface list: add `.claude/instructions/project-context.instructions.md`, `.github/`, and `openwiki/` (generated pages are fixed only through OpenWiki's tools). This turns the Phase D lesson into procedure.

- [ ] **3. Correct the workflow core and the root-guidance MEMORY sentence.**
  - Owner: `coder`. Files (modify): `shared/policies/workflow.instructions.md`, `scripts/generate_targets.py` (root guidance text), `CLAUDE.md` (authoring, hand-maintained). Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - R7: the MEMORY rule says to search with a literal match (`rg -F` or `grep -F`) for area tags such as `[LEARN:installer]` and for keywords, and gives the one command that lists the tags in use, for example `grep -oE '\[LEARN:[a-z-]+\]' .claude/MEMORY.md | sort | uniq -c`. Keep one full copy in the core (Plan-First step 1); the Context Management list points to it.
  - R4: replace the three session-log update reminders (Session Logging "Frequency", Context Management "update the session log", and Manual reminders) with one line that also excludes a log a closeout receipt already binds; such work goes in a new log.
  - R2: the Session Logging errata sentence matches Step 2.
  - Workflow line 84 (FIX LOOP) names the closeout file's stale-receipt recoveries as its exception.
  - Point the plan-validator references at `.claude/scripts/validate_plan_frontmatter.py`, the path that exists in consumers; fix the claim that the session-log template and the orchestrator link to the Verification Evidence Contract; replace "(see root guidance)" in Automatic Reminders with the file that actually describes the guarded paths.
  - The generated `CLAUDE.md` and `AGENTS.md` MEMORY sentence gains `rg -F`. Keep `AGENTS.md` at or under 4,800 bytes and `CLAUDE.md` at or under 4,500; keep the core at or under 16,000 bytes (budget 16 KiB).
  - The authoring `CLAUDE.md`: the same MEMORY wording, and the `verify.py phase` line no longer says "before REVIEW" (the core runs focused and fast checks before review and the persisted phase check at CLOSEOUT step 4).

- [ ] **4. Restore reliable Codex routes and the regression-test rule.**
  - Owner: `coder`. Files (modify): `shared/skills/hydra-config/SKILL.md`, `shared/agents/coder/prompt.md`, `shared/agents/coder/workflow-prompt.md` (only where it has the same tier), `scripts/validate_targets.py`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - R8:
    - `hydra-config` names `.claude/instructions/config-first-design.instructions.md` and says to read it, including its rule for projects without Hydra;
    - the coder prompt adds one conditional read: when the task edits Python source, read `.claude/instructions/code-standards.instructions.md` (Claude Code loads it through `.claude/rules/`);
    - the existing tests-policy entry also triggers on a bug fix, because a bug fix needs a regression test: "when the task adds or changes a test file, or fixes a bug, ...". Keep it one entry: `test_loading_rules_coder_tier_one_is_ponytail_and_a_conditional_tests_read` requires exactly one entry naming `tests.instructions.md`;
    - the always-load tier stays Ponytail only, so the Phase C `loading_rules` tests keep passing;
    - the validator requires each fallback skill's `SKILL.md` to name its mapped policy file.

- [ ] **5. Close the validator gaps.**
  - Owner: `coder`. Files (modify): `scripts/validate_targets.py`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - R9: `skill_frontmatter_yaml_errors` rejects, for `description` and `when_to_use`, a block header other than `|`, `>`, `|-`, or `>-`; a header followed by a comment; and a plain or quoted value continued on following lines. Prefer rejecting these forms over adding a YAML parser. The error names the key and the form.
  - R10: add to `POLICY_BYTE_BUDGETS` the values in big plan Decision 12: `workspace.instructions.md` 7.5 KiB (7,680 bytes), `quality-and-testing.instructions.md` 3 KiB, `tool-routing.instructions.md` 3 KiB, `closeout.instructions.md` 16 KiB, `plan-lifecycle.instructions.md` 11 KiB. Update the comment above it, which says the budgets cover policies read before real work.
  - Fix the comment at `SKILL_DESCRIPTION_CAP_EXEMPT`: the two skills are exempt because their text is hash-pinned, not because both are always on.

- [ ] **6. Restore lost trigger phrases and correct the remaining docs.**
  - Owner: `documenter`. Files (modify): `shared/skills/code-review/SKILL.md`, `shared/skills/rag-auditor/SKILL.md`, `shared/skills/research-critique/SKILL.md`, `shared/skills/data-and-graph-pitfalls/SKILL.md` (descriptions only), `README.md`, `docs/smoke-tests.md`, `docs/target-mapping.md`, `docs/runtime-checks.md`, `shared/policies/workspace.instructions.md`, `shared/agents/orchestrator/prompt.md`, `.claude/instructions/project-context.instructions.md`, `tests/test_validate_targets.py` (one stale comment). Required Skills: `.claude/skills/documentation/SKILL.md`.
  - R11, each description at most 300 characters (now: `code-review` 153, `rag-auditor` 288, `research-critique` 299, `data-and-graph-pitfalls` 250). Where a phrase does not fit, drop a near-duplicate trigger already in the same description; keep the most specific ones.
    - `code-review` gains "review an API or endpoint";
    - `rag-auditor` gains "RAG evaluation" and "retrieval quality";
    - `research-critique` gains "review this research";
    - `data-and-graph-pitfalls` gains "integration tests for a classifier, router, or SQL generator".
  - R12:
    - `README.md:304`: the "step 1 below" list no longer exists; point to CLOSEOUT step 4 in the closeout file.
    - `README.md:1533`: drop "compression" (that tool was `caveman-compress`).
    - `README.md:1254-1256` and `docs/smoke-tests.md:149-151`: Codex reads the `.agents/skills/` copy of the fallback skill.
    - `docs/target-mapping.md:176-177`: the sidecar denylist is `shared/sidecar/workflow/skills.txt`; `runtime_ownership.py` holds the allowlist.
    - `docs/target-mapping.md` "Recorded follow-ups": add the follow-ups listed at the end of the review report.
    - Note in `docs/runtime-checks.md` or `docs/smoke-tests.md` that no native Antigravity run has yet observed the agent following the one-line pointer in `AGENTS.md`.
    - `workspace.instructions.md`: line 44's description of the plan-lifecycle file includes the knowledge-refresh final-phase rule; line 57 says the commit gate also treats `shared/` as control plane.
    - Orchestrator prompt: replace the "file protection rules" reference with the section that now holds them.
    - Project context: correct the current-status lines (35-37, 207-220): PR #55 is merged and `dev` pins Context Mode `2.1.8`. Keep dated history as history.
    - `tests/test_validate_targets.py:3736-3741`: remove "(noted below)", whose note was deleted with the `run-tests` test.

- [ ] **7. Regenerate and refresh this repository.**
  - Owner: orchestrator. Run `uv run python scripts/generate_targets.py --all`, then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`.

- [ ] **8. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`. State the acceptance bar from the Scope in the first-round prompt.
  - Focus:
    - the R1 recovery matches `record_findings.py`, `verify.py`, and the commit hook;
    - every pin still guards its own section, and no check got looser;
    - the byte budgets hold;
    - the Codex routes and the coder's conditional reads;
    - the generated and installed copies match `shared/`.

## Verification

<!-- Every non-comment line in a `bash`/`sh` block below is a required item:
     a shell command `verify closeout` runs itself, from the repository
     root, and that must exit 0. Never list `verify.py closeout` itself.
     Anything a script cannot run — an interactive probe, a host session, a
     manual inspection — belongs under `## Optional Verification` instead.
     See the Verification Evidence Contract in
     `.claude/instructions/workflow.instructions.md`. -->

```bash
uv run python scripts/generate_targets.py --all
uv run pytest tests/test_validate_targets.py -q --tb=short -k "closeout_procedure or codex_fallback or frontmatter_yaml or policy_budget or root_guidance or loading_rules or description_cap"
uv run pytest tests/test_verify.py -q --tb=short -k docs_only_recovery
uv run pytest tests/test_validate_targets.py tests/test_validate_plan_frontmatter.py tests/test_verify.py -q --tb=short
test "$(grep -c -F 'repeat step 6 only' shared/policies/closeout.instructions.md)" = "0"
grep -q -F 'findings report content_hash is stale' shared/policies/closeout.instructions.md
grep -q -F 'rg -F' dist/multi-agent/CLAUDE.md
grep -q -F 'rg -F' dist/multi-agent/AGENTS.md
grep -q -F 'config-first-design.instructions.md' dist/multi-agent/.claude/skills/hydra-config/SKILL.md
grep -q -F 'code-standards.instructions.md' dist/multi-agent/.codex/agents/coder.toml
grep -q -F 'review an API or endpoint' shared/skills/code-review/SKILL.md
grep -q -F 'RAG evaluation' shared/skills/rag-auditor/SKILL.md
grep -q -F 'review this research' shared/skills/research-critique/SKILL.md
grep -q -F 'SQL generator' shared/skills/data-and-graph-pitfalls/SKILL.md
test "$(wc -c < shared/policies/workflow.instructions.md)" -le 16000
test "$(wc -c < shared/policies/workspace.instructions.md)" -le 7500
test "$(wc -c < dist/multi-agent/CLAUDE.md)" -le 4500
test "$(wc -c < dist/multi-agent/AGENTS.md)" -le 4800
test "$(grep -c -F 'before REVIEW' CLAUDE.md)" = "0"
test "$(grep -c -F 'Once the 2.x migration merges' .claude/instructions/project-context.instructions.md)" = "0"
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

<!-- The only place a check may be conditional or non-executable. One `- `
     bullet per item, numbered in the order it appears. -->

- Walk this phase's own CLOSEOUT with the corrected `closeout.instructions.md` alone, and record any step whose action or order had to come from elsewhere.

## Closeout Checklist

Run the numbered CLOSEOUT sequence in `.claude/instructions/closeout.instructions.md` in order. Tick both boxes at its step 2. Later steps bind this file's bytes, so do not edit this file after step 2.

- [ ] Step 1: documentation updated, or skipped as pure-internal with a reason
- [ ] Step 2: this plan set to `status: complete` with `closeout_session_log`, every step ticked, and LEARN entries or the no-lessons marker recorded

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.
Set `status: paused`, record the three pause fields, and create a session log
with `**Status:** PAUSED`. A checkpoint commit preserves incomplete work; it
does not require final findings, LEARN, DOCUMENT, or a completed closeout.
After the checkpoint commit, it may be pushed as a durable remote backup when
paused-publication invariants pass. It remains unfinished and blocks PR creation
and final closeout.
Keep the big plan `in-progress` with the same `current_phase`. On resume, read
the pause log and Git state, restore this plan to `in-progress`, and continue
this same phase without creating another small plan.
