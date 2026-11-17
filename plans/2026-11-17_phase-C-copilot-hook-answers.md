---
name: 2026-11-17_phase-C-copilot-hook-answers
type: small-plan
parent_plan: copilot-harness-migration
phase_index: 3
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

# Small Plan: 2026-11-17_phase-C-copilot-hook-answers

## Scope

Today the guards answer only inside `hookSpecificOutput`. The Copilot
harness honors that only under PascalCase event names, through an
undocumented rule (F4). This phase makes the guards print the decision both
at the top level, the documented Copilot shape, and nested, but only for the
`github-copilot` client (REQ-003). Claude Code, Codex, and Antigravity keep
their exact bytes. The Local harness reads only the nested object (Source:
Copilot extension 0.74.0).

The combined answer looks like this:
`{"permissionDecision":"deny","permissionDecisionReason":"R","hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"R"}}`.
It has no top-level `hookEventName`, because the Local harness drops a
result whose top-level `hookEventName` names another event.

The phase also stops a reason with a control character from producing
invalid JSON (row T3). A new probe session renames the events to camelCase
in a temporary copy. It shows that every gate's deny no longer depends on
the PascalCase rule, which removes the output blocker for a later rename.

## Steps

- [ ] **1. Write the failing tests first.**
  Owner: coder. Files: `tests/test_hook_gates.py`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/testing-patterns/SKILL.md`.
  Cases:
  - For `github-copilot`: `git-protection.sh`, `enforce-branch-state.sh`,
    `enforce-commit-gate.sh`, `enforce-pr-gate.sh`, `protect-files.sh`
    (deny and ask), and each `fail_closed` path print one JSON object. Its
    top-level `permissionDecision` and `permissionDecisionReason` equal the
    nested ones. It has no top-level `hookEventName`. The exit codes are
    unchanged.
  - `additional_context` for `github-copilot` (`session-start-state.sh`,
    `record-branch-state.sh`) prints top-level `additionalContext` equal to
    the nested one.
  - For `claude-code`, `openai-codex`, and `google-antigravity`, the same
    calls print exactly today's bytes (literal expected strings).
  - With an exported `TARGET_ID=github-copilot`, `openwiki-guard.sh` and
    `reporting-reminder.sh prompt claude-code` still print today's bytes.
  - A deny reason holding a tab and a newline gives valid JSON with spaces
    in their place.
  - `pretool-bash-guard.sh github-copilot` with `git reset --hard HEAD`
    passes the combined deny through and exits 0.
  - The `antigravity-pretool.py` output for a denied write is unchanged.
  Acceptance: the new cases fail before steps 2 to 4.

- [ ] **2. Print the combined answer and escape safely in the library.**
  Owner: coder. Files: `shared/hooks/scripts/_lib-frontmatter.sh`
  (`json_escape`, `deny_pretool`, `ask_pretool`, `additional_context`).
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full).
  - When `${TARGET_ID:-}` is `github-copilot`, print the combined
    single-line object; otherwise today's line.
  - `json_escape` turns characters `\001` to `\037` into spaces (with `tr`)
    before escaping backslash and quote. It stays free of `python3`,
    because `fail_closed` runs when `python3` is missing.
  - Must not: change any other client's bytes for text with no control
    character, or add a top-level `hookEventName`.

- [ ] **3. Print the combined answer in the file guard.**
  Owner: coder. Files: `shared/hooks/scripts/protect-files.py` (`emit`).
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/code-style/SKILL.md`.
  - For `target_id == "github-copilot"`, add the top-level
    `permissionDecision` and `permissionDecisionReason` beside the nested
    object.
  - Standard library only; compiles on Python 3.9.

- [ ] **4. Every printing script names its client.**
  Owner: coder.
  Files:
  - `shared/hooks/scripts/enforce-pr-gate.sh`,
    `shared/hooks/scripts/session-start-state.sh`,
    `shared/hooks/scripts/record-branch-state.sh`: set
    `TARGET_ID="${1:-unknown-target}"`;
  - `shared/hooks/scripts/reporting-reminder.sh`: set
    `TARGET_ID="$PROVIDER"`;
  - `shared/hooks/scripts/openwiki-guard.sh`: set `TARGET_ID=""`;
  - `shared/hooks/hooks.json`: the `git-protection.sh` entry gains
    `github-copilot` in `bash`, `linux`, and `osx`;
  - `scripts/validate_targets.py`: a check that every guard under
    `PreToolUse` in the Copilot hook file passes `github-copilot`.

  Required Skills: `.claude/skills/ponytail/SKILL.md` (full).
  Must not rename any event in `shared/hooks/hooks.json`.

- [ ] **5. Check the readers of the nested answer.**
  Owner: coder. Files: none beyond the step 1 tests.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full).
  `pretool-bash-guard.sh:27` and `antigravity-pretool.py` `guard_decision`
  read only the nested object, which stays. No change; the step 1 tests pin
  it.

- [ ] **6. Add the camelCase probe session.**
  Owner: coder. Files: `scripts/check_copilot_runtime.py`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/integration-gate-spike/SKILL.md`.
  Session `camel-rename`:
  - In a copy of the probe project, rename the event keys of
    `.github/hooks/hooks.json`: `SessionStart` to `sessionStart`,
    `PreToolUse` to `preToolUse`, `PostToolUse` to `postToolUse`, and
    `Stop` to `agentStop`.
  - Rename `.claude/settings.json` to `.claude/settings.json.off` in that
    copy only.
  - Checks, each with the same expected value as its Phase A twin:
    `camel-deny-git-reset`, `camel-deny-secret-rm`, `camel-deny-commit`,
    `camel-deny-branch`, `camel-deny-pr`, `camel-ask-vscode-settings`,
    `camel-ask-agent-wrapper`, `camel-allow-plain`.
  - Before this phase, the `camel-deny-*` checks fail (F4). After it, they
    pass.

- [ ] **7. Update the docs.**
  Owner: coder. Files: `docs/target-mapping.md`.
  Required Skills: `.claude/skills/documentation/SKILL.md`.
  - Native Adapters, GitHub Copilot: for the Copilot client, the guards
    print the documented top-level answer and the nested one. The Local
    harness reads the nested one. Events stay PascalCase until the Local
    removal.
  - The context text from `session-start-state.sh` and
    `record-branch-state.sh` now reaches the Copilot model.
  - Recorded follow-ups: "Phase C removed the output blocker for a
    camelCase rename; recheck the input side before renaming."

- [ ] **8. Regenerate and refresh this repository's own install.**
  Owner: coder.
  Commands:
  - `uv run python scripts/generate_targets.py --all`;
  - `uv run python scripts/install_bootstrap.py . --allow-self --local-only`;
  - `uv run python scripts/validate_targets.py`;
  - `uv run python scripts/check_runtime.py`.

  Scope-change record (approved by the orchestrator on 2026-11-17; each
  item serves this phase's stated intent and changes no decision):
  - Step 3: the combined answer is printed by `print_decision`, the one
    output function Phase B added, and not only by `emit`. The deny of the
    two workflow tools is a `github-copilot` answer and gets the top-level
    fields too.
  - Step 2: one helper, `pretool_decision`, carries both shapes for
    `deny_pretool` and `ask_pretool`. In `json_escape`, the second `tr`
    set is exactly 31 spaces (built with the bash builtin `printf -v`), one
    for each character of `\001-\037`, so the mapping depends on no padding
    rule. The first form, `[ *]`, gave `]` on BusyBox `tr`. Run on GNU and
    BusyBox `tr`; a run on macOS or BSD `tr` is an unverified limitation.
  - Row T3 holds for every client, as the big plan's table says: each
    character 1 to 31 in a reason or context text becomes one space. A text
    that ends in a newline now ends in a space. Kept: no caller passes such
    a text (the byte-identity battery shows no difference), and removing it
    would add code for no caller.
  - Step 4: tests for the new validator check go into
    `tests/test_validate_targets.py`.
  - Step 1, after review round 1: the suite covers the `fail_closed` paths
    of every guard for the Copilot shape (42 more cases), not only
    `git-protection.sh` and the library function.
  - Step 6 also changes `tests/test_check_copilot_runtime.py` and the probe
    section of `docs/runtime-checks.md`. Three setup checks are added to
    the eight planned ones: `camel-hooks-source`, `camel-events-renamed`,
    and `camel-mcp-none`. A run prints 43 lines. The rename is applied to
    `.github/hooks/hooks.json` and to its restore copy under
    `.claude/bootstrap-root/`, because the `SessionStart` hook puts the
    restore copy back over the live file. The copy is made once, before
    any session runs.
  - Step 7 also adds a T3 row and an "Answer shape" paragraph to
    `docs/target-mapping.md`, and records one new finding: under camelCase
    event names the nested `ask` raised no question before this phase (F4
    had left that case untested).

- [ ] **9. Review.**
  Owner: reviewer.
  Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`,
  `documentation`.
  Focus:
  - no byte change for the other three clients;
  - no loosened decision;
  - `TARGET_ID` cannot leak in;
  - the camelCase session disables the Claude settings source.

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
uv run pytest tests/test_hook_gates.py tests/test_protect_files_copilot_harness.py tests/test_protect_files_scoping.py tests/test_protect_files_substitutions.py tests/test_validate_targets.py tests/test_check_copilot_runtime.py -q --tb=short
uv run python scripts/check_copilot_runtime.py --require
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
