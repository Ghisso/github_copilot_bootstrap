---
name: 2026-11-17_phase-B-copilot-hook-answers
type: small-plan
parent_plan: copilot-harness-migration
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

# Small Plan: 2026-11-17_phase-B-copilot-hook-answers

## Scope

Today the guards answer only inside `hookSpecificOutput`. The Copilot
harness honors that only under PascalCase event names, through an
undocumented rule (F4). This phase makes the guards print the decision both
at the top level, the documented Copilot shape, and nested, but only for the
`github-copilot` client (REQ-002). Claude Code, Codex, and Antigravity keep
their exact bytes. The Local harness reads only the nested object (Source:
Copilot extension 0.74.0), so it is unaffected. A new probe session renames
the events to camelCase in a temporary copy, to prove that denies no longer
depend on the PascalCase rule.

The combined answer looks like this:
`{"permissionDecision":"deny","permissionDecisionReason":"R","hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"R"}}`.
It has no top-level `hookEventName`, because the Local harness drops a
result whose top-level `hookEventName` names another event.

## Steps

- [ ] **1. Write the failing tests first.**
  Owner: coder. Files: `tests/test_hook_gates.py`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/testing-patterns/SKILL.md`.
  Cases:
  - For `github-copilot`: `git-protection.sh`, `enforce-branch-state.sh`,
    `enforce-commit-gate.sh`, `enforce-pr-gate.sh`, `protect-files.sh`
    (deny and ask), and each `fail_closed` path print one JSON object.
    Its top-level `permissionDecision` and `permissionDecisionReason` equal
    the nested ones. It has no top-level `hookEventName`. The exit codes are
    unchanged (0 for a decision, 2 for `fail_closed`).
  - `additional_context` for `github-copilot` (`session-start-state.sh`,
    `record-branch-state.sh`) prints top-level `additionalContext` equal to
    the nested one.
  - For `claude-code`, `openai-codex`, and `google-antigravity`, the same
    calls print exactly today's bytes. Compare with literal expected
    strings.
  - `pretool-bash-guard.sh github-copilot` with `git reset --hard HEAD`
    passes the combined deny through and exits 0, because its reader at
    line 27 still finds the nested decision.
  - The `antigravity-pretool.py` output for a denied write is unchanged.
  Acceptance: the new cases fail before steps 2 to 4.

- [ ] **2. Print the combined answer in the shared library.**
  Owner: coder. Files: `shared/hooks/scripts/_lib-frontmatter.sh`
  (`deny_pretool`, `ask_pretool`, `additional_context`).
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full).
  - When `${TARGET_ID:-}` is `github-copilot`, print the combined
    single-line object. Otherwise print today's line unchanged.
  - Keep `json_escape` and the one-line `printf` form.
  - Must not: change any other client's bytes, or add a top-level
    `hookEventName`.

- [ ] **3. Print the combined answer in the file guard.**
  Owner: coder. Files: `shared/hooks/scripts/protect-files.py` (`emit`).
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/code-style/SKILL.md`.
  - For `target_id == "github-copilot"`, add the top-level
    `permissionDecision` and `permissionDecisionReason` beside the nested
    object, with the same `json.dumps` separators.
  - Standard library only; compiles on Python 3.9.

- [ ] **4. Give every printing script its client name.**
  Owner: coder.
  Files:
  - `shared/hooks/scripts/enforce-pr-gate.sh`,
    `shared/hooks/scripts/session-start-state.sh`,
    `shared/hooks/scripts/record-branch-state.sh`: set
    `TARGET_ID="${1:-unknown-target}"` before any output;
  - `shared/hooks/hooks.json`: the `git-protection.sh` entry gains the
    `github-copilot` argument in `bash`, `linux`, and `osx`;
  - `scripts/validate_targets.py`: a new check that every guard entry under
    `PreToolUse` in the Copilot hook file passes `github-copilot`.

  Required Skills: `.claude/skills/ponytail/SKILL.md` (full).
  Must not rename any event in `shared/hooks/hooks.json`.

- [ ] **5. Add the camelCase probe session.**
  Owner: coder. Files: `scripts/check_copilot_runtime.py`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/integration-gate-spike/SKILL.md`.
  Session `camel-rename`:
  - In a copy of the probe project, rename the event keys of
    `.github/hooks/hooks.json`: `SessionStart` to `sessionStart`,
    `PreToolUse` to `preToolUse`, `PostToolUse` to `postToolUse`, and
    `Stop` to `agentStop`.
  - Rename `.claude/settings.json` to `.claude/settings.json.off` in that
    copy only, so the Copilot file is the only source.
  - New checks: `camel-deny-git-reset`, `camel-deny-secret-rm`,
    `camel-ask-vscode-settings` (at least one question of kind `hook`), and
    `camel-allow-plain`, with the same expected values as the Phase A
    checks.
  - Before this phase's changes, `camel-deny-*` fails, because the nested
    answer is ignored under camelCase (F4). After them, it passes.

- [ ] **6. Update the docs.**
  Owner: coder. Files: `docs/target-mapping.md`.
  Required Skills: `.claude/skills/documentation/SKILL.md`.
  - Native Adapters, GitHub Copilot: one short paragraph. For the Copilot
    client, the guards print the documented top-level answer and the nested
    one. The Local harness reads the nested one. The event names stay
    PascalCase until the Local removal.
  - Recorded follow-ups: rename to camelCase after the Local removal.

- [ ] **7. Regenerate and refresh this repository's own install.**
  Owner: coder.
  Commands:
  - `uv run python scripts/generate_targets.py --all`;
  - `uv run python scripts/install_bootstrap.py . --allow-self --local-only`;
  - `uv run python scripts/validate_targets.py`;
  - `uv run python scripts/check_runtime.py`.

- [ ] **8. Review.**
  Owner: reviewer.
  Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`,
  `documentation`.
  Focus:
  - no byte change for the other three clients;
  - no loosened decision;
  - the camelCase session really disables the Claude settings source.

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
uv run pytest tests/test_hook_gates.py tests/test_protect_files_scoping.py tests/test_protect_files_substitutions.py tests/test_validate_targets.py tests/test_check_copilot_runtime.py -q --tb=short
uv run python scripts/check_copilot_runtime.py --require --format text
grep -q -F 'git-protection.sh github-copilot' dist/multi-agent/.github/hooks/hooks.json
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

<!-- The only place a check may be conditional or non-executable. One `- `
     bullet per item, numbered in the order it appears. -->

- In a Local-harness chat in VS Code, ask the agent to run `git reset --hard HEAD` and record that it is still denied with the new output.

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
