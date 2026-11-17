---
name: 2026-11-17_phase-D-copilot-tool-inputs
type: small-plan
parent_plan: copilot-harness-migration
phase_index: 4
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

# Small Plan: 2026-11-17_phase-D-copilot-tool-inputs

## Scope

The file guard (`shared/hooks/scripts/protect-files.py`) misreads four kinds
of Copilot-harness tool input (REQ-004, REQ-005):

1. The patch tool used by six Codex-family models sends its patch as text.
   The guard crashes, so every edit is denied (F6).
2. The shell helper tools `read_bash`, `list_bash`, and `stop_bash` carry no
   command. The guard crashes, so they are always denied (P3).
3. The read tool arrives as `Read`, which the guard does not treat as
   read-only. So a read of a hook or agent file asks (Source).
4. The search tools name files in a `paths` list, which the guard does not
   read. So a secret-shaped file can be searched (F7).

The changes follow rows L1, L2, L3, and T1 of the big plan's decision-change
table. No other decision may change. Step 5 implements the user's answer to
the search-tools question. If the answer was no, the orchestrator removed
step 5 and its tests before branch creation.

## Steps

- [ ] **1. Write the failing tests first: a decision battery.**
  Owner: coder. Files: `tests/test_protect_files_scoping.py`, or a new
  `tests/test_protect_files_copilot_harness.py`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/testing-patterns/SKILL.md`.
  Build a table of tool name, input, target, and client mapped to the
  expected decision. Write the expected values from the decision-change
  table and `docs/target-mapping.md`.
  - Tool names: `Read`, `view`, `read_file`, `Grep`, `Glob`, `grep`, `rg`,
    `glob`, `Write`, `Edit` (object input), `Edit` (patch text input),
    `read_bash`, `list_bash`, `stop_bash`, `write_bash`, `bash_shutdown`,
    `Bash`.
  - Targets: a plain file; `.env`; `.github/hooks/hooks.json`;
    `.claude/agents/coder.md`; `.claude/agents/.env`.
  - Clients: `github-copilot`, `claude-code`, `openai-codex`,
    `google-antigravity`.
  - Copy the five patch payloads from the evidence file
    `raw/hook-inputs-patch-tool.txt` into the test, replacing `<project>`
    with the temporary path. Their expected decisions:
    - `probe-patch.txt` added: allowed;
    - `.env` added: deny;
    - `.github/hooks/evil.json` added: ask on Copilot and Claude, deny on
      Codex and Antigravity;
    - `.mcp.json` updated: same as the hook file;
    - `.claude/agents/coder.md` deleted: same as the hook file.
  - Patch text without `*** End Patch`: fail closed (exit 2).
  - A string that is neither JSON nor patch text: fail closed.
  - Patch text sent to a read-only tool or a shell tool: fail closed.
  - `read_bash` with `{"shellId": "0", "delay": 1}`: no decision.
    `read_bash` with a `command` that names `.env`: deny.
    `write_bash` with no `command`: fail closed.
  - First, a test that pins today's `ask` for `Read` on
    `.claude/agents/coder.md`. Record it in the session log, then flip it
    to no decision in step 4. This proves DA7.
  Acceptance: the battery fails only on the planned rows before steps 2 to
  5.

- [ ] **2. Read patch text.**
  Owner: coder. Files: `shared/hooks/scripts/protect-files.py` (`main`).
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/code-style/SKILL.md`.
  For a string `tool_input`:
  - When `json.loads` succeeds, keep today's path: the result must be an
    object.
  - Else, when the text after leading blanks starts with
    `*** Begin Patch`, and the tool name is non-empty, not a shell tool,
    and not in `READ_ONLY_TOOLS`: collect the targets with the existing
    `add_patch_paths`, then `emit`.
  - Else: raise `AmbiguousCommand`.
  No second parser. Standard library only; compiles on Python 3.9.

- [ ] **3. Handle the shell helper tools.**
  Owner: coder. Files: `shared/hooks/scripts/protect-files.py`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full).
  - Add `SHELL_HELPER_TOOLS = {"read_bash", "list_bash", "stop_bash"}`,
    with a comment that cites P3 and the runtime's tool list.
  - When the name is in that set and the input has no `command` key, check
    the input with `native_targets` like a native tool. This is not an
    early return: any path key in the input is still judged.
  - With a `command` key, use today's shell path.
  - `write_bash` and every other name ending in `bash` keep today's shell
    path.

- [ ] **4. Treat `Read` as read-only.**
  Owner: coder. Files: `shared/hooks/scripts/protect-files.py`
  (`READ_ONLY_TOOLS`).
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full).
  - Add `"read"` to the set. The comment says it is the Copilot harness's
    PascalCase name for `view`.
  - Secret-shaped files stay denied for it.

- [ ] **5. Read the search tools' `paths` list (user answer: yes).**
  Owner: coder. Files: `shared/hooks/scripts/protect-files.py`
  (`PATH_KEYS`).
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full).
  - Add `"paths"`. The read-only search tools then deny a secret-shaped
    entry and give no decision for a config entry.
  - A search over a folder, and a `glob` filter such as `.env*`, are not
    judged, like shell reads. The docs say so.

- [ ] **6. Add the probe checks.**
  Owner: coder. Files: `scripts/check_copilot_runtime.py`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/integration-gate-spike/SKILL.md`.
  - Session `codex-patch`, model `gpt-5.2-codex`, both hook sources, the
    five patch steps of the evidence scenario `sc5_codex_patch.json`.
    Checks:
    - `patch-plain-allowed`: success;
    - `patch-secret-denied`: reason has
      `Protected file blocked by policy: .env`;
    - `patch-hook-ask`, `patch-server-ask`, `patch-agent-ask`: exactly one
      question of kind `hook` each.
  - Session `main` adds these checks:
    - `helper-tools` (bash in `async` mode, then `read_bash`, `list_bash`,
      `stop_bash`): no result says `Denied by preToolUse hook`;
    - `read-agent-file` (view `.claude/agents/coder.md`): success, no
      question of kind `hook`;
    - `search-secret-denied` (grep with `paths: [".env"]`): denied;
    - `search-glob-not-judged` (glob `.env*`): not denied by a hook.

- [ ] **7. Update the docs.**
  Owner: coder. Files: `docs/target-mapping.md` (the parity tables' GitHub
  Copilot column and the agent-definition row), `docs/runtime-checks.md`
  (the list of forms the guard does not check).
  Required Skills: `.claude/skills/documentation/SKILL.md`.
  Content:
  - the Copilot-harness tool names the guards see (`Bash`, `Read`,
    `Write`, `Edit`, `Grep`, `Glob`, `Agent`, the shell helpers, the patch
    tool);
  - the decision-change rows L1, L2, L3, and T1, as "a deny or ask became
    allow, on purpose, because ...";
  - folder-wide search and glob filters are not judged.

- [ ] **8. Run the differential battery and record it.**
  Owner: coder.
  - Put a scratch script in the session's scratch folder; do not commit it.
  - It runs the `dev` copy (`git show dev:shared/hooks/scripts/protect-files.py`
    into the scratch folder) and the working copy over the full step-1
    matrix, plus the command shapes of the earlier batteries: redirects,
    heredocs, interpreters, `git -C`, `cd`, `&&`.
  - Write the table of every difference into the phase session log. Every
    row must match L1, L2, L3, or T1.

- [ ] **9. Regenerate and refresh this repository's own install.**
  Owner: coder.
  Commands:
  - `uv run python scripts/generate_targets.py --all`;
  - `uv run python scripts/install_bootstrap.py . --allow-self --local-only`;
  - `uv run python scripts/validate_targets.py`;
  - `uv run python scripts/check_runtime.py`.

- [ ] **10. Review.**
  Owner: reviewer.
  Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`,
  `documentation`.
  Focus:
  - only the planned decisions changed (the step 8 table);
  - no early return skips a later check;
  - fail-closed paths still exit 2;
  - Python 3.9 syntax.

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
uv run pytest tests/test_hook_gates.py tests/test_protect_files_scoping.py tests/test_protect_files_substitutions.py tests/test_check_copilot_runtime.py -q --tb=short
uv run python scripts/check_copilot_runtime.py --require --format text
python3 -c 'import ast, sys; ast.parse(open(sys.argv[1], encoding="utf-8").read(), feature_version=(3, 9))' shared/hooks/scripts/protect-files.py
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

<!-- The only place a check may be conditional or non-executable. One `- `
     bullet per item, numbered in the order it appears. -->

- The step 8 differential table is in the phase session log, and every row matches a decision-change row of the big plan.
- In a Copilot-harness chat in VS Code, start the `coder` sub-agent and record that reading `.claude/agents/coder.md` asks no question.

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
