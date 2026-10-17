---
name: 2026-10-17_phase-D-guard-coverage
type: small-plan
parent_plan: gate-repair
phase_index: 4
status: planned
closeout_session_log:
---

# Small Plan: Guard Coverage

## Scope

Close the remaining guard gaps from the audit and the devil's advocate
review. Protect every client's in-repository hook- and server-launching
config the same way, and stop the nested ai-state repository from tracking
`settings.local.json` (GR-008). Run the plan checks when an implementation
branch is created, as the policy already claims (GR-009). Make shipped
commands keep test failures visible (GR-010). Remove a stale, unused schema
(GR-011). Every guard here is shared, so one change reaches Claude Code and
Codex (through `pretool-bash-guard.sh`), GitHub Copilot (hooks listed
directly), and Antigravity (through `antigravity-pretool.py`; `protect-files`
itself denies for `google-antigravity`). Copilot workspace settings change
only on documentation evidence. Phase C has already updated the root
`.mcp.json` and `.vscode/mcp.json` that this phase protects.

## Steps

- [ ] **1. Protect hook- and server-launching configs (GR-008).**
  **Owner:** coder.
  **Files:** modify `shared/hooks/scripts/protect-files.py` (`HOOK_CONFIGS`,
  lines 15–20, and the `PROTECTED_PATH_LITERAL` capture of those names);
  modify `tests/test_hook_gates.py` and `tests/test_protect_files_scoping.py`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  Add `.claude/settings.local.json` (Claude local settings can add hooks or
  turn them off), `.agents/hooks.json` (Antigravity's only hook config),
  and the MCP configs that launch server commands: `.mcp.json`,
  `.vscode/mcp.json`, `.agents/mcp_config.json`. The existing decision rule
  stays: Codex and Antigravity deny; Claude and Copilot ask.
  **Tests:** for client ids `claude-code`, `openai-codex`, `github-copilot`,
  and the Antigravity bridge, an Edit or Write and a Bash redirect into each
  new path get the expected decision. `cat` and Read of them stay allowed.
  The same name outside this repository's root stays unprotected (existing
  scoping rule). The self-install command, which writes these files from
  Python without naming them, still passes the Bash guard.

- [ ] **2. Stop syncing `settings.local.json` through ai-state (GR-008).**
  **Owner:** coder.
  **Files:** modify `shared/hooks/scripts/state-sync.sh` (add an untrack
  helper beside `untrack_nested_cache` and `untrack_error_log`, called from
  `commit_local_state`); modify `tests/test_state_sync.py`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  Remove only the index entry (`git rm --cached --ignore-unmatch`), never the
  file. `.claude/.gitignore` already lists it. MEMORY `[LEARN:security]`
  records that losing this file was unrecoverable data loss before, so a
  second clone that pulls the untrack commit must keep its own
  `settings.local.json` bytes; preserve and restore the file around the
  pull when needed.
  **Tests:** after a checkpoint, the nested index no longer contains
  `settings.local.json` and the local file is unchanged; a second clone that
  pulls the untrack commit keeps its local file byte for byte.

- [ ] **3. Settle Copilot workspace hook settings from documentation (GR-008, Copilot).**
  **Owner:** coder.
  **Files:** modify `docs/target-mapping.md`; modify
  `shared/hooks/scripts/protect-files.py` and its tests only for a
  documented setting.
  **Required Skills:** `shared/skills/integration-gate-spike/SKILL.md`,
  `shared/skills/ponytail/SKILL.md` (full).
  Use the official VS Code documentation (`microsoft/vscode-docs`) with the
  big plan's lookup fallback order. Questions: does VS Code agent mode read
  hooks from other files, such as `.claude/settings*.json`? Can a workspace
  setting in `.vscode/settings.json` relocate or turn off agent hooks? For
  each documented answer, protect that file by the same rule and test it.
  Otherwise change no code and record "not documented" with the link, or
  "unverified".

- [ ] **4. Run plan checks at branch creation (GR-009).**
  **Owner:** coder.
  **Files:** modify `shared/hooks/scripts/enforce-branch-state.sh` and
  `shared/policies/workflow.instructions.md` (the "Plan approval" rows of
  the Enforcement table, lines 395–398, become "Branch creation and
  commit"); modify `tests/test_branch_state.py` or `tests/test_hook_gates.py`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  After the existing type and status checks, run
  `.claude/scripts/validate_plan_frontmatter.py` on the big plan and the
  small-plan files its `phases:` list names, passed as explicit paths, so an
  unrelated draft elsewhere cannot block the branch. Deny with the
  validator's first error lines. A missing validator or `python3` denies,
  the same as the commit gate.
  **Tests:** a plan whose small plan has no Verification block is denied
  with an `L1` message; a valid plan is allowed while an unrelated invalid
  draft exists in the same directory. Run both through the Claude/Codex
  guard chain and the Copilot direct hook; one case through the Antigravity
  bridge.

- [ ] **5. Keep test failures visible in shipped commands (GR-010).**
  **Owner:** coder.
  **Files:** modify `shared/skills/run-tests/SKILL.md` (Step 5, line 66) and
  `shared/skills/add-dependency/SKILL.md` (line 47); modify
  `scripts/validate_targets.py`; modify `tests/test_validate_targets.py`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  Rewrite both deprecation checks so they print the deprecation lines (or
  "No deprecation warnings") and still exit with pytest's own status. Add
  one narrow validator check over fenced `bash` and `sh` blocks in
  `shared/skills/`, `shared/policies/`, `shared/agents/`, `shared/templates/`,
  and `shared/sidecar/`: a line that runs `pytest`, `mypy`, `ruff`, or
  `verify.py` fails when it ends in `|| true`, `|| :`, or `|| echo ...`.
  Report file and line. Do not change plan rule L3 or its mirrored copies.
  **Tests:** extend
  `test_run_tests_e2e_step_propagates_failure_instead_of_masking_it` (or add
  a sibling) for Step 5; one positive and one negative validator case.

- [ ] **6. Remove the stale agent schema (GR-011).**
  **Owner:** coder.
  **Files:** delete `shared/schemas/agent.schema.json`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full).
  Nothing reads it and it is not shipped. Leave the dated reference in
  `plans/plan-agent-model-effort-tiers.md` unchanged.

- [ ] **7. Regenerate, refresh, document, review, close out.**
  **Owner:** orchestrator; fresh reviewer; documenter after review.
  Untrack `settings.local.json` in this repository's nested ai-state through
  the new state-sync path (a checkpoint), not by hand. Run
  `uv run python scripts/generate_targets.py --all` and
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
  before verification. Update `docs/smoke-tests.md` (protected configs;
  branch guard runs the plan validator) and the parity rows in
  `docs/target-mapping.md`.
  **Required Skills:** `shared/skills/documentation/SKILL.md`,
  `shared/skills/code-review/SKILL.md`.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run pytest tests/test_hook_gates.py tests/test_protect_files_scoping.py tests/test_branch_state.py tests/test_state_sync.py tests/test_lifecycle_hooks.py tests/test_validate_targets.py -q
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Claude Code: in this repository, ask the agent to add a key to
  `.claude/settings.local.json` and record the approval prompt. Then approve
  one ordinary permission with "don't ask again" and record that Claude Code
  still saves it.
- Codex: record that an edit to `.codex/hooks.json` is denied natively.
- Antigravity: in a disposable install, record whether a write to
  `.agents/hooks.json` is denied natively.

## Review Profiles

Use `.claude/review-profiles/code.md`, `.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`. Give the reviewer the audit
(§5 D3, D7, D8, D9), GR-008 to GR-011, the Copilot documentation evidence,
and the final diff.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT); the order below mirrors it
rather than restating it.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
