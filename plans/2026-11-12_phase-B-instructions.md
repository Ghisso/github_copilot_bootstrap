---
name: 2026-11-12_phase-B-instructions
type: small-plan
parent_plan: skills-and-instructions-trim
phase_index: 2
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

# Small Plan: 2026-11-12_phase-B-instructions

## Scope

Before real work, agents read the workflow policy (40.8 KB), root guidance, and several policies and prompts. This phase changes three things.

**It fixes exploration section 7 defects 2 to 6:**
- The plan-small Closeout Checklist sets the session log to COMPLETED early, and its boxes get ticked before the steps they name happen.
- The orchestrator's Completion Protocol says to write the session log after the receipt has locked it, and its numbered workflow is broken by two subsections.
- Four control-plane lists disagree with each other.
- Two files say MEMORY is "loaded into every session".
- The Copilot root file has an outdated lifecycle and no plain-language rule.

**It splits the workflow policy:**

| New location | Content |
|---|---|
| `closeout.instructions.md` | The CLOSEOUT sequence: 8 numbered steps, each with its reason, plus the two hard rules, the completion-commit gate, the standing final-phase audit, the closeout session-log rules, and how to recover from the two stale-receipt errors. Read only at the closeout step. A validator pin protects it. |
| `plan-lifecycle.instructions.md` | Declaring future phases, pausing, cancelling, reopening, the conditional checkpoint branch, and the Knowledge-Refresh Final Phase rule. The core keeps one trigger line for each. |
| `knowledge-refresh` skill | The OpenWiki Refresh section. |
| Removed | The recovery checklist, the file-protection section, and the operator troubleshooting lines. |

Also in the split:
- The Verification Evidence Contract is trimmed to what planners need.
- The MEMORY reading rule becomes a targeted search.
- The core reaches 16,000 bytes or less, and a validator budget keeps it there.

**It trims the rest:**

| Surface | Change | Target |
|---|---|---|
| Generated `CLAUDE.md` | Trim | ≤ 4,500 B |
| Generated `AGENTS.md` | Trim; the 2,786-byte Antigravity supplement becomes a one-line pointer to `.agents/agents/orchestrator/agent.md`, which already carries it | ≤ 4,800 B |
| `workspace` policy | Trim; the hooks runtime contract moves to this repository's project context | ≤ 7,500 B |
| `quality-and-testing` policy | Trim; the path-to-review-profile rule moves to workspace; the `record_findings.py` command is fixed | ≤ 3,000 B |
| `tool-routing` policy | Trim | ≤ 3,000 B |
| `config-first-design` policy | Drop the repeated Hydra text | none |
| Orchestrator prompt | Trim | ≤ 12,500 B |
| Documenter prompt | Trim | ≤ 6,500 B |

The root-guidance validator budgets only tighten. Covers REQ-002, REQ-007, and REQ-008. This phase's own closeout already reads the new closeout file, installed in Step 8.

Risk notes:
- These must stay:
  - `TASK_LANE_REQUIRED_FRAGMENTS`;
  - the workflow entries of `EXECUTION_DEFAULTS_POLICY_FRAGMENTS`;
  - every `required_fragments` item and the 7 headers in `root_guidance_errors`;
  - `ROOT_GUIDANCE_USER_FACING_FRAGMENTS`;
  - exactly one `.github/hooks/` in `CLAUDE.md`, `AGENTS.md`, and workspace (`scripts/validate_targets.py` 711-720 and 8199-8211);
  - the `**Project:**` placeholder and the `**Python:**`/`**Stack:**` lines that the installer substitutes.
- The commit gate's wider list (`CONTROL_PLANE_PREFIXES`, `shared/scripts/verify.py:99-106`) is not copied into the lane lists. Copying it would make every MEMORY or plan edit high-risk.
- No sidecar workflow unit may name either new file; the sidecar rewrites only the workspace and workflow paths.
- Antigravity following the pointer is not observed (DA-7).
- This is the largest phase. The big plan names the B1/B2 split fallback.

## Steps

- [ ] **1. Add the validator pins and tests first.**
  - Owner: `coder`. Files (modify): `scripts/validate_targets.py`, `tests/test_validate_targets.py`, `tests/test_validate_plan_frontmatter.py` (only where a test reads moved text). Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/testing-patterns/SKILL.md`.
  - Copilot guidance check, next to the Ponytail check (about line 8217):
    - require `REPORTING_POLICY_POINTER`;
    - require exactly one canonical lifecycle equal to `ROOT_GUIDANCE_WORKFLOW` (reuse `ROOT_LIFECYCLE_PATTERN`);
    - reject "especially `workflow.instructions.md`, `quality-and-testing.instructions.md`, and `tool-routing.instructions.md`".
  - Template test: the `## Closeout Checklist` of `shared/templates/plan-small.md` has exactly two `- [ ]` boxes, names `closeout.instructions.md`, and contains neither "mirrors it" nor "`**Status:** COMPLETED`".
  - Orchestrator tests:
    - replace the `## Completion Protocol (Mandatory)` row (about line 4343) with a `## Phase-Boundary Summary` row that still requires `agent-reporting.instructions.md`;
    - add a test that the `## Core Workflow` numbered items run from 1 to the last number with no heading between them.
  - Control-plane checks:
    - all three `render_root_guidance` targets and the generated workspace policy contain the new generator constant `CONTROL_PLANE_INVENTORY`;
    - add `.agents/` and `.vscode/mcp.json` to `TASK_LANE_CONTROL_PLANE_PATHS`;
    - a test checks that `TASK_LANE_CONTROL_PLANE_PATHS` and `TASK_LANE_CONTROL_PLANE_FILES` name the backticked paths of the constant.
  - Closeout pin: `closeout_procedure_errors(text: str) -> list[str]`, run on the generated `.claude/instructions/closeout.instructions.md`. It requires:
    - exactly one procedure heading;
    - numbered steps 1 to 8 in order;
    - a `*Why` in every step;
    - both hard-rule fragments ("Never put `git commit` in the same Bash command", "Never checkpoint, publish, or push nested state between step 6 and step 7");
    - both stale-receipt messages, verbatim.
  - Add both new files to the required generated runtime files list (about line 8783).
  - Pointer pins:
    - the workflow core, the orchestrator prompt, the `commit` skill, and the plan-small template name `closeout.instructions.md`;
    - none still says "CLOSEOUT sequence below" or "CLOSEOUT sequence in `.claude/instructions/workflow.instructions.md`".
  - Budgets:
    - `POLICY_BYTE_BUDGETS = {"workflow.instructions.md": 16 * 1024}`, checked on `shared/policies/`;
    - `ROOT_GUIDANCE_BUDGETS` becomes `("bytes", 5 * 1024)` for both root files.
  - Antigravity:
    - `antigravity_default_agent_contract_errors` checks the new pointer;
    - a new check requires the generated `.agents/agents/orchestrator/agent.md` to hold the orchestrator's Antigravity supplement delimiter;
    - update tests 460-462, and add a test that the multi-agent `AGENTS.md` lacks the supplement text.
  - Update the `_planning_source_texts` rows that read moved text. Keep the R-AGENTS-08 comment true for the shorter quality-and-testing command.
  - Tests for the closeout pin carry `closeout_procedure` in their names: one positive case, and one negative case per rule.
  - Acceptance: the new tests fail before Step 2.

- [ ] **2. Split the workflow policy.**
  - Owner: `coder`. Files: create `shared/policies/closeout.instructions.md` and `shared/policies/plan-lifecycle.instructions.md` (both `applicability: always`); modify `shared/policies/workflow.instructions.md` and `shared/skills/knowledge-refresh/SKILL.md`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/humanize/SKILL.md` (`edit` mode).
  - Closeout file:
    - steps 1 to 8 from workflow 185-207, adding the missing reasons for steps 2, 6, 7, and 8;
    - the completion-commit gate paragraph (line 181);
    - from Session Logging: the standing final-phase audit, the closeout log fields (`**Status:** COMPLETED`, `**Plan:**`, LEARN or the no-lessons marker), and the Immutability and errata rule;
    - from the contract: the `- optional <n>: PASS|FAIL|NOT RUN — <detail>` grammar;
    - a recovery section for both stale-receipt messages: what changed and which steps to repeat. Base it on `shared/scripts/verify.py` 2141-2175 and the tests in `tests/test_verify.py` that produce these messages.
  - Plan-lifecycle file: move "Declaring future phases", "Pausing a phase for a checkpoint", "Cancelling a plan or phase", "Reopening a completed big plan", the conditional checkpoint branch (line 175), and "Knowledge-Refresh Final Phase". Only cross-references change.
  - Workflow core (16,000 bytes or less):
    - keep Task Lanes verbatim, Plan-First, Branch Lifecycle with one trigger line per moved topic, the Canonical Orchestrator Loop (step 5 points to the closeout file), Bypass Policy, Reporting, and Context Management;
    - trim the Verification Evidence Contract: keep the required-block definition, the optional section, and the rule never to list `verify.py closeout`; make the hedge rule one paragraph naming `HEDGED_VERIFICATION_PATTERNS` in `.claude/scripts/validate_plan_frontmatter.py`; replace the enforcement table with one sentence: L1-L4 and G1-G4 name the broken rule in their messages;
    - Plan-First step 1 and Context Management: "Search `.claude/MEMORY.md` for the task's area tags (for example `[LEARN:installer]`) and keywords, and read the matching entries. Read the whole file only for a memory audit.";
    - Session Logging: write "`.claude/MEMORY.md` is live advice that agents act on, not a dated record" (defect 5);
    - trim Automatic Reminders and drop the state-sync and Codex hook-trust operator details, after confirming README holds each removed fact;
    - delete Recovery Checklist and File Protection Rules.
  - knowledge-refresh skill: add any OpenWiki Refresh fact the skill lacks, then delete that section from the workflow. Point its line 175 reference at the right file.

- [ ] **3. Change the root guidance and the Copilot file.**
  - Owner: `coder`. Files (modify): `scripts/generate_targets.py`, and the authoring `CLAUDE.md`. In `CLAUDE.md`, change line 30 (MEMORY), line 67 (control plane), and the trims to text it shares with the generated file; keep its authoring phrases and the `check_runtime.py` fragment "review -> closeout". Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/humanize/SKILL.md` (`edit` mode).
  - `CONTROL_PLANE_INVENTORY` = "root guidance (`CLAUDE.md`, `AGENTS.md`), `.claude/hooks/`, `.claude/settings.json`, `.github/hooks/`, `.codex/`, `.agents/`, `.mcp.json`, `.vscode/mcp.json`, and `.devcontainer/`". Use it in all three root-guidance targets.
  - `render_root_guidance`:
    - the MEMORY line uses the targeted-search wording and keeps `.claude/MEMORY.md`;
    - the retrieval sentence becomes a pointer to the tool-routing policy;
    - shorten the Task Lanes bullets, the push bullet, and the Map.
  - `render_antigravity_default_agent_contract`: the heading plus one sentence: the native default agent is the main-thread orchestrator; before complex work, read and follow `.agents/agents/orchestrator/agent.md` and delegate only to the custom specialists in `.agents/agents/`.
  - `render_copilot_instructions` (lines 1517-1519). Replace them with:
    - classify each request with the Task Lanes table in `.claude/instructions/workflow.instructions.md`, and read other files only when the task needs them;
    - keep the Ponytail line;
    - the `ROOT_GUIDANCE_WORKFLOW` lifecycle;
    - "follow `.claude/instructions/closeout.instructions.md` before commit";
    - keep the `.claude/` state sentence;
    - the reporting pointer, with the root guidance's plain-language sentence.

- [ ] **4. Trim the workspace policy and move the hooks contract.**
  - Owner: `coder`. Files (modify): `shared/policies/workspace.instructions.md`, and `.claude/instructions/project-context.instructions.md` (this repository's AI state, checkpointed in the nested repository). Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Control plane: the inventory text, plus "The commit gate is wider: it treats every tracked path under `.claude/`, `.codex/`, `.agents/`, `.github/`, and `.devcontainer/` as control plane."
  - Merge the three `uv` sections into one. Cut the Workflow restatement to its pinned fragments.
  - Add rows for the two new files to the Instructions table.
  - Receive the path-to-review-profile rule from quality-and-testing.
  - Rewrite the Skills section: drop the repeated "High-leverage public skills" list; say that both visibility values are listed to the model with their descriptions, and that `visibility` marks only the intended use.
  - Make Verification a pointer.
  - Move "Bootstrap Hooks Runtime Contract" to the project context.
  - Keep the Knowledge Ownership and Review Profiles tables.

- [ ] **5. Trim the other policies.**
  - Owner: `coder`. Files (modify): `shared/policies/quality-and-testing.instructions.md`, `shared/policies/tests.instructions.md`, `shared/policies/tool-routing.instructions.md`, `docs/runtime-checks.md`, `shared/policies/config-first-design.instructions.md`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - quality-and-testing:
    - keep the commands, the consumer scope, the Verification Detail table, the severity tiering, and the metadata-matrix sentence;
    - keep one `record_findings.py . --findings-json - --phase ... --out ...` command, matching the closeout file;
    - delete the text the tests policy repeats. First move the coverage target and the regression-test rule into the tests policy if it lacks them.
  - tool-routing: move the Context Mode server paragraph (line 29) to `docs/runtime-checks.md`. Before moving it, grep the validators and tests for its sentences (for example `2.1.8`, `CONTEXT_MODE_DATA_DIR`, `--agent codex`) and keep any pinned sentence in the policy.
  - config-first-design: remove the code examples that `hydra-config` repeats, and keep the rules.

- [ ] **6. Fix and trim the agent prompts.**
  - Owner: `coder`. Files (modify): `shared/agents/orchestrator/prompt.md`, `shared/agents/coder/prompt.md`, `shared/agents/documenter/prompt.md`, `shared/agents/planner/prompt.md`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/humanize/SKILL.md` (`edit` mode).
  - Orchestrator:
    - line 3: "the memory/session-log writes in the Completion Protocol" becomes "the CLOSEOUT steps";
    - delete `## Completion Protocol (Mandatory)`;
    - add `## Phase-Boundary Summary`: after PUSH, give the summary that `.claude/instructions/agent-reporting.instructions.md` defines; LEARN, MEMORY, and the session log belong to CLOSEOUT step 2; a log bound by a receipt is never edited, and corrections go to `<log-name>.errata.md`;
    - replace the two `###` subsections inside the numbered list with one pointer each: in step 4 to the KR rule in `plan-lifecycle.instructions.md`; in step 7 to `closeout.instructions.md`, which holds the standing audit;
    - step 7 follows the closeout file;
    - remove text the tool-routing policy and the closeout file already hold, and the duplicate Quality Gates section;
    - keep the pinned fragments and the orchestrator-only `record_findings.py ... --out` rule.
  - Coder: replace the line-23 inline list with a pointer to the workspace control-plane list. Tier 1 is unchanged here; Phase C changes it.
  - Documenter:
    - line 98: "live advice that agents act on";
    - remove text the documentation skill and the closeout file repeat;
    - keep the domain routing lines, because Phase C repoints the pipeline one.
  - Planner: line 101 points the KR rule at `plan-lifecycle.instructions.md`. Line 121 (the contract) stays.

- [ ] **7. Point skills, templates, and docs at the new files.**
  - Owner: `coder` (`documenter` for `README.md` and `docs/`). Files (modify):
    - `shared/templates/plan-small.md`, `shared/templates/plan-big.md` (line 77), `shared/templates/session-log.md` (line 40);
    - `shared/skills/plan-decomposition/SKILL.md`, `shared/skills/commit/SKILL.md` (lines 46 and 57), `shared/skills/code-review/SKILL.md` (lines 26 and 38);
    - `scripts/validate_plan_frontmatter.py` (comment at lines 50-51);
    - `README.md`, `docs/architecture.md` (line 382).
  - Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/documentation/SKILL.md`.
  - plan-small: replace the Closeout Checklist body with the text this plan's own checklist uses (two boxes; points to `closeout.instructions.md`).
  - plan-decomposition:
    - lines 117-119: keep the template's two boxes and tick them at CLOSEOUT step 2; the CLOSEOUT sequence, not this checklist, gates the normal completion commit. Keep the phrase "normal completion commit";
    - line 136: the KR rule is in `plan-lifecycle.instructions.md`.
  - README: lines 326 and 358, plus the two new files in "Most Important Instructions".

- [ ] **8. Regenerate and refresh this repository.**
  - Owner: orchestrator. Run `uv run python scripts/generate_targets.py --all`, then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`. Read the installed closeout file before this phase's closeout, and record the before and after sizes in the session log.

- [ ] **9. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`.
  - Focus:
    - no moved text was lost (diff the old sections against the new files);
    - each step's reason is true;
    - the stale-receipt recovery matches `verify.py`;
    - the checklist cannot claim a later step early;
    - nothing tells the orchestrator to write state after the receipts;
    - the unified control-plane list leaves no surface narrower than before;
    - no safety rule was lost (protected files, destructive Git commands, the control-plane lane);
    - the validator changes only tighten.

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
uv run pytest tests/test_validate_targets.py tests/test_validate_plan_frontmatter.py tests/test_verify.py tests/test_install_bootstrap.py -q --tb=short
uv run pytest tests/test_validate_targets.py -q --tb=short -k closeout_procedure
wc -c dist/multi-agent/CLAUDE.md dist/multi-agent/AGENTS.md shared/policies/workflow.instructions.md shared/policies/closeout.instructions.md shared/policies/plan-lifecycle.instructions.md shared/policies/workspace.instructions.md shared/policies/quality-and-testing.instructions.md shared/policies/tool-routing.instructions.md shared/agents/orchestrator/prompt.md shared/agents/documenter/prompt.md
test "$(wc -c < dist/multi-agent/CLAUDE.md)" -le 4500
test "$(wc -c < dist/multi-agent/AGENTS.md)" -le 4800
test "$(wc -c < shared/policies/workflow.instructions.md)" -le 16000
test "$(wc -c < shared/policies/workspace.instructions.md)" -le 7500
test "$(wc -c < shared/policies/quality-and-testing.instructions.md)" -le 3000
test "$(wc -c < shared/policies/tool-routing.instructions.md)" -le 3000
test "$(wc -c < shared/agents/orchestrator/prompt.md)" -le 12500
test "$(wc -c < shared/agents/documenter/prompt.md)" -le 6500
test -f dist/multi-agent/.claude/instructions/closeout.instructions.md
test -f dist/multi-agent/.claude/instructions/plan-lifecycle.instructions.md
test "$(grep -c -F '### CLOSEOUT sequence' shared/policies/workflow.instructions.md)" = "0"
test "$(grep -c -F '## Recovery Checklist' shared/policies/workflow.instructions.md)" = "0"
test "$(grep -c -F '## File Protection Rules' shared/policies/workflow.instructions.md)" = "0"
grep -q -F 'closeout receipt final tracked state is stale' shared/policies/closeout.instructions.md
grep -q -F 'closeout receipt governing control-plane provenance is stale' shared/policies/closeout.instructions.md
grep -q -F 'closeout.instructions.md' shared/agents/orchestrator/prompt.md
grep -q -F 'closeout.instructions.md' shared/skills/commit/SKILL.md
grep -q -F 'closeout.instructions.md' shared/templates/plan-small.md
grep -q -F 'plan-lifecycle.instructions.md' shared/agents/planner/prompt.md
test "$(grep -c -F 'Completion Protocol' shared/agents/orchestrator/prompt.md)" = "0"
test "$(grep -c -F 'mirrors it' shared/templates/plan-small.md)" = "0"
test "$(grep -r -l -F 'loaded into every session' shared | wc -l)" = "0"
test "$(grep -r -l -F 'hidden helpers' shared | wc -l)" = "0"
test "$(grep -c -F 'read `.claude/MEMORY.md`' dist/multi-agent/CLAUDE.md)" = "0"
grep -q -F '`.agents/`' dist/multi-agent/CLAUDE.md
grep -q -F '`.claude/settings.json`' dist/multi-agent/AGENTS.md
grep -q -F '.agents/agents/orchestrator/agent.md' dist/multi-agent/AGENTS.md
grep -q -F '.claude/instructions/agent-reporting.instructions.md' dist/multi-agent/.github/copilot-instructions.md
grep -q -F 'PRE-FLIGHT -> BRANCH -> PLAN WHEN NEEDED -> IMPLEMENT -> VERIFY -> REVIEW -> CLOSEOUT -> COMMIT -> PUSH' dist/multi-agent/.github/copilot-instructions.md
test "$(grep -c -F 'especially `workflow.instructions.md`' dist/multi-agent/.github/copilot-instructions.md)" = "0"
test "$(grep -c -F 'record_findings.py src/' shared/policies/quality-and-testing.instructions.md)" = "0"
test "$(grep -c -F 'Bootstrap Hooks Runtime Contract' shared/policies/workspace.instructions.md)" = "0"
grep -q -F 'Minimum Python version' .claude/instructions/project-context.instructions.md
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

- Walk this phase's own closeout using only `.claude/instructions/closeout.instructions.md`. Record any step that needed text from another file.
- In VS Code Copilot Chat, check that the reporting rule from the generated `.github/copilot-instructions.md` is listed under the loaded instructions.
- In a fresh Codex session in this repository, ask for the control-plane list and the closeout file path. Record whether the answers match the trimmed `AGENTS.md`.

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
