---
name: 2026-11-12_phase-E-workflow-split
type: small-plan
parent_plan: skills-and-instructions-trim
phase_index: 5
# status must occur exactly once: planned | in-progress | paused | complete | cancelled
# New phase files default to planned (not yet started); the branch-creation
# and post-commit hooks flip the active phase to in-progress automatically.
status: planned
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

# Small Plan: 2026-11-12_phase-E-workflow-split

## Scope

Agents read all of `workflow.instructions.md` (40.8 KB) before every non-trivial task. This phase splits it:

| New location | Content |
|---|---|
| `closeout.instructions.md` | The CLOSEOUT sequence: 8 numbered steps, each with its reason, plus the two hard rules, the completion-commit gate, the standing final-phase audit, the closeout session-log rules, and how to recover from the two stale-receipt errors. Read only at the closeout step. A new validator pin protects it. |
| `plan-lifecycle.instructions.md` | Declaring future phases, pausing, cancelling, reopening, the conditional checkpoint branch, and the Knowledge-Refresh Final Phase rule. The core keeps one trigger line for each. |
| `knowledge-refresh` skill | The OpenWiki Refresh section. |
| Removed | The recovery checklist, the file-protection section, and the operator troubleshooting lines. |

Other changes:
- The Verification Evidence Contract is trimmed to what planners need. The checkers' own messages explain the rest.
- The MEMORY reading rule becomes a targeted search.
- The core reaches 16,000 bytes or less, and a validator budget keeps it there.

Covers REQ-007.

Risk notes:
- Phase E's own closeout already reads the new closeout file (installed by Step 7).
- Sidecar workflow units must not name the two new files; the sidecar rewrites only the workspace and workflow paths.
- Every pinned fragment stays in place (`TASK_LANE_REQUIRED_FRAGMENTS`; the workflow entries of `EXECUTION_DEFAULTS_POLICY_FRAGMENTS`).

## Steps

- [ ] **1. Add the pins and tests first.**
  - Owner: `coder`. Files (modify): `scripts/validate_targets.py`, `tests/test_validate_targets.py`, `tests/test_validate_plan_frontmatter.py` (only where a test reads moved text). Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/testing-patterns/SKILL.md`.
  - Add `closeout_procedure_errors(text: str) -> list[str]`, run on the generated `.claude/instructions/closeout.instructions.md`. It requires:
    - exactly one procedure heading;
    - numbered steps 1 to 8 in order;
    - a `*Why` in every step;
    - both hard-rule fragments ("Never put `git commit` in the same Bash command", "Never checkpoint, publish, or push nested state between step 6 and step 7");
    - both stale-receipt messages, verbatim.
  - Add both new files to the required generated runtime files list (about line 8783).
  - Pointer pins:
    - the workflow core, the orchestrator prompt, the `commit` skill, and the plan-small template each name `closeout.instructions.md`;
    - none of them still says "CLOSEOUT sequence below" or "CLOSEOUT sequence in `.claude/instructions/workflow.instructions.md`".
  - Add `POLICY_BYTE_BUDGETS = {"workflow.instructions.md": 16 * 1024}`, checked on `shared/policies/`.
  - Tests carry `closeout_procedure` in their names: one positive case on generated text, and one negative case per rule.
  - Update the `_planning_source_texts` rows that read moved text.

- [ ] **2. Create the closeout file.**
  - Owner: `coder`. File (create): `shared/policies/closeout.instructions.md`, with `applicability: always` and a description that says to read it at the CLOSEOUT step. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/humanize/SKILL.md` (`edit` mode).
  - Move steps 1 to 8 from `workflow.instructions.md` 185-207. Add the missing reasons for steps 2, 6, 7, and 8.
  - Add the completion-commit gate paragraph (workflow line 181).
  - From Session Logging, add the standing final-phase audit, the closeout log fields (`**Status:** COMPLETED`, `**Plan:**`, LEARN or the no-lessons marker), and the Immutability and errata rule.
  - From the contract, add the session-log `## Verification` grammar (`- optional <n>: PASS|FAIL|NOT RUN — <detail>`).
  - Add a recovery section for the two stale-receipt messages: what changed and which steps to repeat. Base it on `shared/scripts/verify.py` 2141-2175 and the tests in `tests/test_verify.py` that produce these messages.

- [ ] **3. Create the plan-lifecycle file.**
  - Owner: `coder`. File (create): `shared/policies/plan-lifecycle.instructions.md`, with `applicability: always`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Move, with only cross-reference edits: "Declaring future phases", "Pausing a phase for a checkpoint", "Cancelling a plan or phase", "Reopening a completed big plan", the conditional checkpoint branch (workflow line 175), and "Knowledge-Refresh Final Phase".

- [ ] **4. Trim the workflow core to 16,000 bytes or less.**
  - Owner: `coder`. Files (modify): `shared/policies/workflow.instructions.md`, `shared/skills/knowledge-refresh/SKILL.md`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/humanize/SKILL.md` (`edit` mode).
  - Keep Task Lanes verbatim, Plan-First, Branch Lifecycle, the Canonical Orchestrator Loop (step 5 points to the closeout file), Bypass Policy, Reporting, and Context Management.
  - Add one trigger line each for the moved plan-lifecycle topics.
  - Trim the Verification Evidence Contract:
    - keep the required-block definition, the optional section, and the rule never to list `verify.py closeout`;
    - make the hedge rule one paragraph that names `HEDGED_VERIFICATION_PATTERNS` in `.claude/scripts/validate_plan_frontmatter.py`;
    - replace the enforcement table with one sentence: `validate_plan_frontmatter.py` (L1-L4) and `verify.py gate` (G1-G4) name the broken rule in their messages.
  - Trim Session Logging and Automatic Reminders. Drop the state-sync and Codex hook-trust operator details; README already covers them, so confirm each removed fact there.
  - Delete Recovery Checklist and File Protection Rules.
  - Move any fact the OpenWiki Refresh section has and the knowledge-refresh skill lacks into the skill, then delete the section.

- [ ] **5. Change the MEMORY reading rule.**
  - Owner: `coder`. Files (modify): `shared/policies/workflow.instructions.md` (Plan-First step 1 and Context Management), `scripts/generate_targets.py` (line 1370), and the authoring `CLAUDE.md` (line 30). Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - New text: "Search `.claude/MEMORY.md` for the task's area tags (for example `[LEARN:installer]`) and keywords, and read the matching entries. Read the whole file only for a memory audit."
  - Keep the `.claude/MEMORY.md` fragment.

- [ ] **6. Point every reference at the new files.**
  - Owner: `coder`. Files (modify):
    - `shared/agents/orchestrator/prompt.md` (step 7 and the KR pointer);
    - `shared/skills/commit/SKILL.md` (lines 46 and 57);
    - `shared/skills/code-review/SKILL.md` (lines 26 and 38);
    - `shared/skills/plan-decomposition/SKILL.md` (line 136, KR; line 115 stays on the contract);
    - `shared/agents/planner/prompt.md` (line 101, KR);
    - `shared/templates/plan-small.md` (checklist pointer), `shared/templates/plan-big.md` (line 77), `shared/templates/session-log.md` (line 40, grammar);
    - `scripts/validate_plan_frontmatter.py` (comment at lines 50-51);
    - `shared/policies/workspace.instructions.md` (Instructions table rows);
    - `README.md` (lines 326 and 358, plus the "Most Important Instructions" list);
    - `docs/architecture.md` (line 382).
  - Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - No sidecar workflow unit may name either new file.

- [ ] **7. Regenerate and refresh this repository.**
  - Owner: orchestrator. Run `uv run python scripts/generate_targets.py --all`, then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`. Read the installed closeout file before this phase's own closeout.

- [ ] **8. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`.
  - Focus:
    - nothing was lost in the move (diff the moved text);
    - each step's reason is true;
    - the stale-receipt recovery matches `verify.py`;
    - the trigger lines send every lifecycle case to the right file;
    - no pin was removed.

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
uv run pytest tests/test_validate_targets.py tests/test_validate_plan_frontmatter.py tests/test_verify.py -q --tb=short
uv run pytest tests/test_validate_targets.py -q --tb=short -k closeout_procedure
wc -c shared/policies/workflow.instructions.md shared/policies/closeout.instructions.md shared/policies/plan-lifecycle.instructions.md
test "$(wc -c < shared/policies/workflow.instructions.md)" -le 16000
test -f dist/multi-agent/.claude/instructions/closeout.instructions.md
test -f dist/multi-agent/.claude/instructions/plan-lifecycle.instructions.md
test "$(grep -c -F '### CLOSEOUT sequence' shared/policies/workflow.instructions.md)" = "0"
test "$(grep -c -F '## Recovery Checklist' shared/policies/workflow.instructions.md)" = "0"
test "$(grep -c -F '## File Protection Rules' shared/policies/workflow.instructions.md)" = "0"
grep -q -F 'closeout.instructions.md' shared/agents/orchestrator/prompt.md
grep -q -F 'closeout.instructions.md' shared/skills/commit/SKILL.md
grep -q -F 'closeout.instructions.md' shared/templates/plan-small.md
grep -q -F 'closeout receipt final tracked state is stale' shared/policies/closeout.instructions.md
grep -q -F 'closeout receipt governing control-plane provenance is stale' shared/policies/closeout.instructions.md
grep -q -F 'plan-lifecycle.instructions.md' shared/agents/planner/prompt.md
test "$(grep -c -F 'read `.claude/MEMORY.md`' dist/multi-agent/CLAUDE.md)" = "0"
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

- Walk this phase's own closeout using only `.claude/instructions/closeout.instructions.md`. Record any step that needed text from another file.

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
