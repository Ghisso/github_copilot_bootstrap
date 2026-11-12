---
name: 2026-11-12_phase-F-guidance-trims
type: small-plan
parent_plan: skills-and-instructions-trim
phase_index: 6
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

# Small Plan: 2026-11-12_phase-F-guidance-trims

## Scope

This phase trims the guidance that loads on every turn or every task:

| Surface | Change | Target |
|---|---|---|
| Generated `CLAUDE.md` | Trim | ≤ 4,500 B (about 4.3 KB) |
| Generated `AGENTS.md` | Trim; the 2,786-byte Antigravity supplement becomes a one-line pointer to `.agents/agents/orchestrator/agent.md`, which already carries it | ≤ 4,800 B |
| `workspace` policy | Trim; the hooks runtime contract moves to this repository's project context | ≤ 7,500 B |
| `quality-and-testing` policy | Trim; the path-to-review-profile rule moves to the workspace routing table; the `record_findings.py` command is fixed | ≤ 3,000 B |
| `tool-routing` policy | Trim | ≤ 3,000 B |
| `config-first-design` policy | Drop the repeated Hydra text | none |
| Orchestrator prompt | Trim | ≤ 12,500 B |
| Documenter prompt | Trim | ≤ 6,500 B |

The root-guidance validator gets stricter byte budgets and is never loosened. Covers REQ-008.

Risk notes:
- These must stay:
  - every `required_fragments` item and the 7 headers in `root_guidance_errors`;
  - `ROOT_GUIDANCE_USER_FACING_FRAGMENTS`;
  - exactly one `.github/hooks/` in `CLAUDE.md`, `AGENTS.md`, and workspace;
  - the `**Project:**` placeholder and the `**Python:**`/`**Stack:**` lines that the installer substitutes (`PROJECT_NAME_FILES`, `PYTHON_FACT_FILES`).
- Antigravity following the pointer is not observed (DA-7).

## Steps

- [ ] **1. Tighten the pins first.**
  - Owner: `coder`. Files (modify): `scripts/validate_targets.py`, `tests/test_validate_targets.py`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/testing-patterns/SKILL.md`.
  - `ROOT_GUIDANCE_BUDGETS` becomes `("bytes", 5 * 1024)` for both files.
  - `antigravity_default_agent_contract_errors` checks the new pointer. A new check requires the generated `.agents/agents/orchestrator/agent.md` to hold the orchestrator's Antigravity supplement delimiter.
  - Update tests 460-462, and add a test that the multi-agent `AGENTS.md` no longer holds the supplement text.

- [ ] **2. Trim the root guidance.**
  - Owner: `coder`. Files (modify): `scripts/generate_targets.py` (`render_root_guidance`, `render_antigravity_default_agent_contract`), and the authoring `CLAUDE.md` where it shares the text (keep its authoring phrases and the `check_runtime.py` fragment "review -> closeout"). Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/humanize/SKILL.md` (`edit` mode).
  - Shorten the retrieval sentence to a pointer to the tool-routing policy.
  - Shorten the Task Lanes bullets to the pinned pointer plus one line per lane, and shorten the push bullet and the Map.
  - The Antigravity section becomes its heading plus one sentence: the native default agent is the main-thread orchestrator; before complex work, read and follow `.agents/agents/orchestrator/agent.md` and delegate only to the custom specialists in `.agents/agents/`.

- [ ] **3. Trim the workspace policy.**
  - Owner: `coder`. Files (modify): `shared/policies/workspace.instructions.md`, `.claude/instructions/project-context.instructions.md` (this repository's AI state, checkpointed in the nested repository). Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Merge the three `uv` sections into one.
  - Cut the Workflow restatement down to its pinned fragments and the control-plane inventory.
  - Receive the path-to-profile rule from quality-and-testing.
  - Make Verification a pointer.
  - Move "Bootstrap Hooks Runtime Contract" to the project context.
  - Keep the Knowledge Ownership and Review Profiles tables.

- [ ] **4. Trim the quality-and-testing policy.**
  - Owner: `coder`. Files (modify): `shared/policies/quality-and-testing.instructions.md`, `shared/policies/tests.instructions.md`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Keep the verification commands, the consumer scope, the Verification Detail table, the severity tiering, and the metadata-matrix sentence.
  - Keep one `record_findings.py . --findings-json - --phase ... --out ...` command, matching the closeout file.
  - Delete the parts the tests policy repeats. First move the coverage target and the "every bug fix needs a regression test" rule into the tests policy if it lacks them.
  - Keep the R-AGENTS-08 comment in `validate_targets.py` true.

- [ ] **5. Trim the tool-routing policy.**
  - Owner: `coder`. Files (modify): `shared/policies/tool-routing.instructions.md`, `docs/runtime-checks.md`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Move the Context Mode server paragraph (line 29) to `docs/runtime-checks.md`. Before moving it, grep the validators and tests for its sentences (for example `2.1.8`, `CONTEXT_MODE_DATA_DIR`, `--agent codex`) and keep any pinned sentence in the policy.

- [ ] **6. Trim config-first-design and the two prompts.**
  - Owner: `coder`. Files (modify): `shared/policies/config-first-design.instructions.md`, `shared/agents/orchestrator/prompt.md`, `shared/agents/documenter/prompt.md`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/humanize/SKILL.md` (`edit` mode).
  - config-first-design: remove the code examples that `hydra-config` repeats, and keep the rules.
  - Orchestrator: remove the text that tool-routing and the closeout file already hold, and the duplicate Quality Gates section. Keep the pinned fragments (the `_planning_source_texts` rows) and the orchestrator-only `record_findings.py ... --out` rule.
  - Documenter: remove the text that the documentation skill and the closeout file repeat.

- [ ] **7. Check the sizes.**
  - Owner: `coder`. No file changes. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Run the Verification byte checks and record the before and after numbers in the session log.

- [ ] **8. Regenerate and refresh this repository.**
  - Owner: orchestrator. Run `uv run python scripts/generate_targets.py --all`, then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`.

- [ ] **9. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`.
  - Focus:
    - no safety rule was lost (the protected files, the destructive Git commands, the control-plane lane);
    - the moved texts land where agents will read them;
    - the validator change only tightens.

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
uv run pytest tests/test_validate_targets.py tests/test_install_bootstrap.py -q --tb=short
wc -c dist/multi-agent/CLAUDE.md dist/multi-agent/AGENTS.md shared/policies/workspace.instructions.md shared/policies/quality-and-testing.instructions.md shared/policies/tool-routing.instructions.md shared/agents/orchestrator/prompt.md shared/agents/documenter/prompt.md
test "$(wc -c < dist/multi-agent/CLAUDE.md)" -le 4500
test "$(wc -c < dist/multi-agent/AGENTS.md)" -le 4800
test "$(wc -c < shared/policies/workspace.instructions.md)" -le 7500
test "$(wc -c < shared/policies/quality-and-testing.instructions.md)" -le 3000
test "$(wc -c < shared/policies/tool-routing.instructions.md)" -le 3000
test "$(wc -c < shared/agents/orchestrator/prompt.md)" -le 12500
test "$(wc -c < shared/agents/documenter/prompt.md)" -le 6500
grep -q -F '.agents/agents/orchestrator/agent.md' dist/multi-agent/AGENTS.md
test "$(grep -c -F 'record_findings.py src/' shared/policies/quality-and-testing.instructions.md)" = "0"
test "$(grep -c -F 'Bootstrap Hooks Runtime Contract' shared/policies/workspace.instructions.md)" = "0"
grep -q -F 'Minimum Python version' .claude/instructions/project-context.instructions.md
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

- In a fresh Codex session in this repository, ask for the control-plane list and the closeout file path. Record whether the answers match the trimmed `AGENTS.md`.

## Closeout Checklist

(The same text as Phase E.)

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
