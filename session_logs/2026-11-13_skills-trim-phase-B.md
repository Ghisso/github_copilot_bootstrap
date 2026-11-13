# Session: Instructions split and trims (skills-and-instructions-trim, Phase B)

**Date:** 2026-11-13
**Plan:** `.claude/plans/2026-11-12_phase-B-instructions.md`
**Status:** COMPLETED

## Goal

Fix exploration section 7 defects 2 to 6, move CLOSEOUT into `closeout.instructions.md` and the plan-lifecycle rules into `plan-lifecycle.instructions.md`, replace the competing closeout procedures with pointers, switch the MEMORY rule to a targeted search, and trim root guidance, policies, and prompts to their budgets (REQ-002, REQ-007, REQ-008).

## Work Log

- Phase A committed as `ba629ba` and pushed; the post-commit hook set Phase B `in-progress`. Material-impact check: Phase A's only design change (the mirror keeps the marker) does not touch Phase B, C, or D; no planner run.
- Sidecar check: the sidecar ships its own workflow rule (`shared/sidecar/workflow/rules/workflow.md`), templates, and agent `workflow-prompt.md` files, and denies the `commit`, `plan-decomposition`, `code-review`, and `knowledge-refresh` skills (`shared/sidecar/workflow/skills.txt`). Phase B leaves `shared/sidecar/**` and every `workflow-prompt.md` unchanged, so no sidecar unit names the two new files.
- Delegation (one phase, split by file ownership instead of the B1/B2 fallback): coder alpha Step 1 (validator pins and tests, failing first); coder beta-1 Step 2 (workflow split, closeout and plan-lifecycle files, knowledge-refresh skill); coder beta-2 Steps 6 and 7 (agent prompts, templates, commit/plan-decomposition/code-review skills, plan-frontmatter comment); coder gamma Steps 3 to 5 (generator root guidance, authoring `CLAUDE.md`, workspace and other policies, project context, `docs/runtime-checks.md`); documenter Step 7 (README, `docs/architecture.md`). No content agent runs the generator or validators; alpha integrates after all edits settle.
- Alpha (Step 1) failing-first, measured in a `git archive HEAD` scratch copy so live files stayed untouched: run A (HEAD validator + new tests) 59 failed, 12 passed (missing validator names plus content); run B (new validator + new tests, HEAD content) 25 failed, 46 passed, all real content gaps (budgets: `CLAUDE.md` 6,507 B, `AGENTS.md` 9,467 B, workflow 40,797 B; missing `CONTROL_PLANE_INVENTORY`; closeout pointers; Copilot adapter; plan-small checklist; orchestrator numbering; Antigravity pointer and supplement; the Phase-Boundary Summary row). On the wave-1 tree the plan's `-k "closeout_procedure or root_guidance_budget"` selected 34 tests, all passing. Validator changes only add checks or lower limits; `CONTROL_PLANE_PREFIXES` was not copied into the lane lists.
- Beta-1 (Step 2): workflow 40,797 -> 15,955 B; new `closeout.instructions.md` 13,912 B (`## CLOSEOUT procedure`, 8 steps each with `*Why`, step 2 reads the learn skill and routes lessons, both hard rules, completion-commit gate, push and PR gates, closeout log rules and errata, the `## Stale-claims surfaces checked` audit, stale-receipt recovery derived from `verify.py` ~2147 and `test_staged_documentation_change_after_closeout_makes_final_state_stale` / `test_control_plane_provenance_binds_runtime_and_active_plans`); new `plan-lifecycle.instructions.md` 10,057 B (only cross-references changed, checked with a word diff). OpenWiki Refresh deleted after adding three missing facts to the knowledge-refresh skill. State-sync operator details README lacks stay in `docs/runtime-checks.md` 497-582; the kept operator facts are one Automatic Reminders bullet. Dropped with no home: the Recovery Checklist line "Mermaid diagrams render without errors".
- Beta-2 (Steps 6-7): orchestrator 16,178 -> 11,856 B (Completion Protocol removed; `## Phase-Boundary Summary` added; Core Workflow 1-10 with no heading between items; Quality Gates removed); documenter 7,626 -> 6,344 B; coder points at the workspace control-plane list; planner points the KR rule at `plan-lifecycle.instructions.md`; plan-small checklist byte-identical to this phase's own; commit skill pointer keeps "run `git commit` in its own Bash command" and the staging rules; "Never checkpoint after the receipts are persisted" deleted. Pins checked read-only with an `ast` reader.
- Gamma (Steps 3-5): generated `CLAUDE.md` 6,507 B/64 lines -> 4,434 B/55 lines; `AGENTS.md` 9,467 -> 4,765 B; Codex root 6,682 -> 4,623 B; Copilot file 1,393 -> 1,676 B (Task Lanes, Ponytail, lifecycle, closeout pointer, state sentence, reporting pointer with the plain-language rule); authoring `CLAUDE.md` 7,181 -> 5,975 B; workspace 11,707 -> 7,466 B (adds a protected-files and destructive-Git line with "stop and explain", requested by the orchestrator after beta-1 deleted File Protection Rules); quality-and-testing 10,287 -> 2,973 B; tool-routing 5,545 -> 2,960 B; config-first-design 5,331 -> 3,556 B; hooks runtime contract moved to `.claude/instructions/project-context.instructions.md`. Dropped unpinned root sentences (listed for review): the Task Lanes category list (the workflow table holds it), "run focused and fast checks ...", the commit bullet's profile/lessons/Ponytail clauses (closeout file and commit gate cover them), the OpenWiki enabling clause, and the Context Mode tool-detail sentence.
- Alpha integration: `generate_targets.py --all`; `validate_targets.py` had one FAIL (the ignored live `.github/instructions` overlay lacked the two new files, fixed by the self-refresh); three test files 1321 passed, 1 failed (the same overlay check). Added the `PLAIN_LANGUAGE_RULE` pin to `copilot_guidance_errors` (negative cases `plain-language-missing` and `plain-language-weakened`), rewrote the stale R-BYPASS-02 comment, and confirmed the Antigravity pointer and supplement tests. Ruff, format, mypy clean.
- Orchestrator: `docs/smoke-tests.md` now states the 5 KiB `AGENTS.md` and `CLAUDE.md` limits and the 16 KiB workflow limit.
- Step 8: `generate_targets.py --all` exit 0; `install_bootstrap.py . --allow-self --local-only` exit 0. Installed sizes: `.claude/instructions/workflow.instructions.md` 40,797 -> 15,955 B; new `closeout.instructions.md` 13,912 B and `plan-lifecycle.instructions.md` 10,057 B. The orchestrator read the installed closeout file in full before this phase's closeout.
- Required Verification block, orchestrator scratch runner: 50 items, 0 failed (`verify.py phase` PASS, 319.7 s).
- The harness flagged gamma's report as "instruction-shaped" (`settings-json`); the match was the factual `.claude/settings.json` path in the control-plane inventory, not a directive.
- Review round 1 (six profiles): gate FAIL on one MAJOR and two MINORs. MAJOR: closeout step 8's reason said receipts and findings "cannot exist before step 7", but they are made at steps 4 and 6 and the push gate requires the receipt's `head_sha` to be the pushed commit's direct parent (`verify.py` `gate_receipt_errors`, `git_is_direct_child`). MINORs: the standing audit's surface list was shorter than the list removed from the orchestrator prompt, with a second, longer list left in `plan-decomposition`; `docs/runtime-checks.md` ~603 still restated the checkpoint order with "never checkpoint after the receipts". The reviewer confirmed the stale-receipt recovery against `verify.py` and `tests/test_verify.py` (provenance ignores `nested_head`; `session_logs/`, `MEMORY.md`, `explorations/`, `quality_reports/`, `settings.local.json`, and project context are uncovered), that no moved text was lost, that no surface's control-plane list got narrower, and that every validator change only adds a check or lowers a limit (the one relaxation, `AGENTS.md` no longer carrying the Antigravity supplement, is plan-authorized and replaced by the pointer plus the adapter-delimiter check). It judged gamma's dropped root sentences acceptable (each is held in the Task Lanes table, closeout file, tool-routing, or a skill).
- Fixes (orchestrator, text only): step 8's reason rewritten; the closeout audit now lists root guidance, active plans, undated `docs/`, the canonical policy/skill/template/agent/review-profile source, state READMEs, and MEMORY, plus the errata rule, and `plan-decomposition` cites it instead of a second list; `docs/runtime-checks.md` points at CLOSEOUT steps 3-6, names both checkpoints, and limits the ban to "between step 6 and step 7". Also from the reviewer's notes: step 2's reason names the step-4 `**Status:**` edit, and the stale-tree recovery says only an index change (not an unstaged edit) stales the receipt. After: regenerate + self-refresh 0; `-k "closeout_procedure or root_guidance_budget or stale_skill or planning"` 53 passed; `validate_targets.py` PASS; `check_runtime.py` 0.
- Review round 2 (same reviewer): gate PASS, 0 findings, no open requests. Standing non-blocking notes, not changed: no remedy text for a push-time stale receipt; the older "~30 responses" session-log reminder; consumers lost the hooks contract's `python3` 3.9 floor statement (moved to this repository's project context, as planned); README 1268 "hidden helpers" (Phase C owns it); the pre-2026-08-29 exception appears in both the quality table and the closeout file.
- CLOSEOUT step 1: README (closeout pointer, Most Important Instructions rows), `docs/architecture.md`, `docs/runtime-checks.md`, `docs/smoke-tests.md`. Not the last phase, so no standing audit.
- CLOSEOUT step 2: read the learn skill and routed three lessons (below): one MEMORY entry updated in place, two kept in this log only. Small plan `status: complete`, 12 boxes ticked; Phase B ticked in the big plan; `validate_plan_frontmatter.py` exit 0.

## [LEARN] Entries

- [LEARN:workflow] A large guidance phase can be split by file ownership across parallel agents when no content agent runs the generator or validators, each greps `scripts/validate_targets.py` and `tests/` before cutting a sentence, and one validator owner integrates after edits settle. Five agents, one overlay failure (fixed by the self-refresh), no lost pin. Saved by extending the existing parallel-coders entry in `.claude/MEMORY.md`.
- [LEARN:documentation] A procedure's `*Why` reasons need a code check, not only a presence pin: the closeout pin required a reason in every step, and the reviewer still found step 8's reason false against `verify.py`. Kept in this log; the review step already asks for it.
- [LEARN:workflow] A Stop-hook nested checkpoint during closeout does not stale the receipts, because provenance ignores the nested HEAD and the session-log and MEMORY paths. The closeout file now states this, so no MEMORY entry.

## Verification

```text
PASS        0.2s  uv run python scripts/generate_targets.py --all
PASS      246.5s  uv run pytest tests/test_validate_targets.py tests/test_validate_plan_frontmatter.py tests/test_verify.py tests/test_install_bootstrap.py -q --tb=short
PASS        0.2s  uv run pytest tests/test_validate_targets.py -q --tb=short -k "closeout_procedure or root_guidance_budget"
PASS        0.0s  wc -c dist/multi-agent/CLAUDE.md dist/multi-agent/AGENTS.md shared/policies/workflow.instructions.md shared/policies/closeout.instructions.md shared/policies/plan-lifecycle.instructions.md shared/policies/workspace.instructions.md shared/policies/quality-and-testing.instructions.md shared/policies/tool-routing.instructions.md shared/agents/orchestrator/prompt.md shared/agents/documenter/prompt.md
PASS        0.0s  test "$(wc -c < dist/multi-agent/CLAUDE.md)" -le 4500
PASS        0.0s  test "$(wc -c < dist/multi-agent/AGENTS.md)" -le 4800
PASS        0.0s  test "$(wc -c < shared/policies/workflow.instructions.md)" -le 16000
PASS        0.0s  test "$(wc -c < shared/policies/workspace.instructions.md)" -le 7500
PASS        0.0s  test "$(wc -c < shared/policies/quality-and-testing.instructions.md)" -le 3000
PASS        0.0s  test "$(wc -c < shared/policies/tool-routing.instructions.md)" -le 3000
PASS        0.0s  test "$(wc -c < shared/agents/orchestrator/prompt.md)" -le 12500
PASS        0.0s  test "$(wc -c < shared/agents/documenter/prompt.md)" -le 6500
PASS        0.0s  test -f dist/multi-agent/.claude/instructions/closeout.instructions.md
PASS        0.0s  test -f dist/multi-agent/.claude/instructions/plan-lifecycle.instructions.md
PASS        0.0s  test "$(grep -c -F '### CLOSEOUT sequence' shared/policies/workflow.instructions.md)" = "0"
PASS        0.0s  test "$(grep -c -F '## Recovery Checklist' shared/policies/workflow.instructions.md)" = "0"
PASS        0.0s  test "$(grep -c -F '## File Protection Rules' shared/policies/workflow.instructions.md)" = "0"
PASS        0.0s  grep -q -F 'closeout receipt final tracked state is stale' shared/policies/closeout.instructions.md
PASS        0.0s  grep -q -F 'closeout receipt governing control-plane provenance is stale' shared/policies/closeout.instructions.md
PASS        0.0s  grep -q -F '.claude/skills/learn/SKILL.md' shared/policies/closeout.instructions.md
PASS        0.0s  grep -q -F 'closeout.instructions.md' shared/agents/orchestrator/prompt.md
PASS        0.0s  grep -q -F 'closeout.instructions.md' shared/skills/commit/SKILL.md
PASS        0.0s  grep -q -F 'closeout.instructions.md' shared/templates/plan-small.md
PASS        0.0s  grep -q -F 'closeout.instructions.md' dist/multi-agent/CLAUDE.md
PASS        0.0s  grep -q -F 'closeout.instructions.md' dist/multi-agent/AGENTS.md
PASS        0.0s  grep -q -F 'closeout.instructions.md' dist/multi-agent/.github/copilot-instructions.md
PASS        0.0s  grep -q -F 'closeout.instructions.md' CLAUDE.md
PASS        0.0s  grep -q -F 'closeout.instructions.md' README.md
PASS        0.0s  grep -q -F 'plan-lifecycle.instructions.md' shared/agents/planner/prompt.md
PASS        0.0s  test "$(grep -c -F 'Completion Protocol' shared/agents/orchestrator/prompt.md)" = "0"
PASS        0.0s  test "$(grep -c -F 'mirrors it' shared/templates/plan-small.md)" = "0"
PASS        0.0s  test "$(grep -c -F 'Never checkpoint after step 5' README.md)" = "0"
PASS        0.0s  test "$(grep -c -F 'Never checkpoint after the receipts are persisted' shared/skills/commit/SKILL.md)" = "0"
PASS        0.0s  test "$(grep -c -F 'persists findings, records learning' CLAUDE.md)" = "0"
PASS        0.0s  test "$(grep -c -F 'read `.claude/MEMORY.md`' dist/multi-agent/CLAUDE.md)" = "0"
PASS        0.0s  test "$(grep -c -F 'read `.claude/MEMORY.md`' CLAUDE.md)" = "0"
PASS        0.0s  uv run python -I -c 'import pathlib, re, sys; pat = re.compile(sys.argv[1].encode()); roots = [pathlib.Path(a) for a in sys.argv[2:]]; bad = [str(r) for r in roots if not r.exists()] + [str(p) for r in roots if r.exists() for p in ([r] if r.is_file() else sorted(r.rglob("*"))) if p.is_file() and "__pycache__" not in p.parts and pat.search(p.read_bytes())]; sys.exit("missing or matching: " + ", ".join(bad) if bad else 0)' 'loaded into every session|hidden helpers' shared
PASS        0.0s  grep -q -F '`.agents/`' dist/multi-agent/CLAUDE.md
PASS        0.0s  grep -q -F '`.claude/settings.json`' dist/multi-agent/AGENTS.md
PASS        0.0s  grep -q -F '.agents/agents/orchestrator/agent.md' dist/multi-agent/AGENTS.md
PASS        0.0s  grep -q -F '.claude/instructions/agent-reporting.instructions.md' dist/multi-agent/.github/copilot-instructions.md
PASS        0.0s  grep -q -F 'PRE-FLIGHT -> BRANCH -> PLAN WHEN NEEDED -> IMPLEMENT -> VERIFY -> REVIEW -> CLOSEOUT -> COMMIT -> PUSH' dist/multi-agent/.github/copilot-instructions.md
PASS        0.0s  test "$(grep -c -F 'especially `workflow.instructions.md`' dist/multi-agent/.github/copilot-instructions.md)" = "0"
PASS        0.0s  test "$(grep -c -F 'record_findings.py src/' shared/policies/quality-and-testing.instructions.md)" = "0"
PASS        0.0s  test "$(grep -c -F 'Bootstrap Hooks Runtime Contract' shared/policies/workspace.instructions.md)" = "0"
PASS        0.0s  grep -q -F 'Minimum Python version' .claude/instructions/project-context.instructions.md
PASS       48.0s  uv run python scripts/validate_targets.py
PASS        0.8s  uv run python scripts/check_runtime.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS      319.8s  uv run python .claude/scripts/verify.py phase --format text
```

- Findings: `.claude/quality_reports/findings-2026-11-12_phase-B-instructions.json` (0 findings after review round 2; gate PASS; six profiles; round 1 had one MAJOR and two MINORs, all fixed before round 2).
- Phase receipt: `verify.py phase --persist` PASS (pytest completed (5092 passed, 1 skipped in 321.77s (0:05:21)); mypy 0 errors; Ruff 0 violations).
- optional 1: PASS — this phase's closeout was walked with `.claude/instructions/closeout.instructions.md` alone. Every step's action and order came from that file. Two details came from elsewhere: the script path and runner for the findings recorder (the file names `record_findings.py`; the real call is `uv run python .claude/scripts/record_findings.py`), and the checkpoint/commit facts were confirmed against `verify.py` by the reviewer. Recorded for the Phase D audit.
- optional 2: NOT RUN — needs an interactive VS Code Copilot Chat session to view its loaded-instructions list; this agent cannot drive that UI. The generated `.github/copilot-instructions.md` carries the reporting pointer and the plain-language rule (required items and the new `copilot_guidance_errors` pin).
- optional 3: NOT RUN — a fresh interactive Codex chat in this repository was not started (it would run this repository's trusted Codex hooks, including nested state sync, mid-closeout). Substitute check: `codex debug prompt-input` with an isolated, untrusted Codex home (no hooks) showed that this authoring repository loads its own hand-maintained 2,099-byte `AGENTS.md`, not the generated one, and it names neither the control-plane list nor the closeout file; it routes Codex to the workspace policy, which carries both. Unchanged by this phase; listed for the Phase D audit.

## Open Questions / Next Steps

- Next: Phase C (skill set 55 to 37, description cap).
- Phase D audit items: the closeout file's `record_findings.py` mention lacks the `uv run python .claude/scripts/` prefix; the authoring `AGENTS.md` has no closeout pointer.
