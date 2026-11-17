---
name: 2026-11-17_phase-B-copilot-tool-inputs
type: small-plan
parent_plan: copilot-harness-migration
phase_index: 2
# status must occur exactly once: planned | in-progress | paused | complete | cancelled
# New phase files default to planned (not yet started); the branch-creation
# and post-commit hooks flip the active phase to in-progress automatically.
status: complete
closeout_session_log: .claude/session_logs/2026-11-17_copilot-harness-phase-B.md
# Pause fields (required only when status is paused):
# paused_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# paused_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# pause_session_log: <repository-relative readable UTF-8 PAUSED session log>
# Cancellation fields (required only when status is cancelled):
# cancelled_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# cancelled_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# cancelled_evidence: <repository-relative readable UTF-8 CANCELLED artifact>
---

# Small Plan: 2026-11-17_phase-B-copilot-tool-inputs

## Scope

This is the most urgent fix (REQ-002, REQ-005). In the real VS Code, file
creation and editing fail whenever the chosen model uses the patch tool,
because the file guard (`shared/hooks/scripts/protect-files.py`) crashes on
the patch text (A4, F6). The phase fixes the four kinds of Copilot-harness
tool input the guard misreads:

- patch text (row L3);
- the shell helpers `read_bash`, `list_bash`, `stop_bash` (L2);
- the read tool's PascalCase name `Read` (L1);
- the search tools' `paths` list (T1).

It also makes patch headers with blanks or another letter case give a target
(T2). And it gives every runtime tool in the Phase A inventory a recorded
handling (T4, only for a tool that runs commands outside the hooks). No
other decision may change.

The rows named here are in the big plan's decision-change table. Step 5 and
its parts implement user choice 1. If the user answered no, the orchestrator
removed step 5, its battery rows, the probe check `search-secret-denied`,
and the T1 text in step 8 before branch creation.

## Steps

- [x] **1. Write the failing tests first: a decision battery.**
  Owner: coder. Files: create `tests/test_protect_files_copilot_harness.py`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/testing-patterns/SKILL.md`.
  Build a table of tool name, input, target, and client mapped to the
  expected decision and exit code. Write the expected values from the
  decision-change table and `docs/target-mapping.md`. Compare the parsed
  `permissionDecision` and the exit code, not bytes, so that Phase C's
  output change does not break the table.
  - Tool names: `Read`, `view`, `read_file`, `Grep`, `Glob`, `grep`, `rg`,
    `glob`, `Write`, `Edit` (object input), `Edit` (patch text),
    `read_bash`, `list_bash`, `stop_bash`, `write_bash`, `bash_shutdown`,
    `Bash`.
  - Targets: a plain file; `.env`; `.github/hooks/hooks.json`;
    `.claude/agents/coder.md`; `.claude/agents/.env`.
  - Clients: `github-copilot`, `claude-code`, `openai-codex`,
    `google-antigravity`. Include `claude-code`, because on the Copilot
    harness the Claude-settings copy also receives `Edit` with patch text.
  - The five patch payloads from the evidence file
    `raw/hook-inputs-patch-tool.txt`, copied into the test with `<project>`
    replaced. Expected decisions:
    - `probe-patch.txt` added: allowed;
    - `.env` added: deny;
    - `.github/hooks/evil.json` added: ask on Copilot and Claude, deny on
      Codex and Antigravity;
    - `.mcp.json` updated: same as the hook file;
    - `.claude/agents/coder.md` deleted: same as the hook file.
  - Header shapes, each targeting `.github/hooks/evil.json` and each giving
    the hook-file decision: `  *** Add File: …` (indented),
    `*** add file: …` (lowercase), `***  Add  File:  …` (extra blanks).
    Use patch text, object input (`{"input": "<patch>"}`), and a shell
    `apply_patch` heredoc.
  - Fail closed (exit 2):
    - patch text without `*** End Patch`;
    - a string that is neither JSON nor patch text;
    - patch text sent to a read-only tool or a shell tool;
    - `write_bash` with no `command`.
  - `read_bash` with `{"shellId": "0", "delay": 1}`: no decision.
    `read_bash` with `{"command": "rm -f .env"}`: deny.
  - First, pin today's `ask` for `Read` on `.claude/agents/coder.md`, then
    flip it to no decision in step 4 (DA7).
  Acceptance: the battery fails only on the planned rows before steps 2 to
  6.

- [x] **2. Read patch text.**
  Owner: coder. Files: `shared/hooks/scripts/protect-files.py` (`main`).
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/code-style/SKILL.md`.
  For a string `tool_input`:
  - When `json.loads` succeeds, keep today's path: the result must be an
    object.
  - Else, when the text after leading blanks starts with
    `*** Begin Patch`, and the tool name is non-empty, not a shell tool,
    and not in `READ_ONLY_TOOLS`: collect targets with `add_patch_paths`,
    then `emit`.
  - Else: raise `AmbiguousCommand`.
  Standard library only; compiles on Python 3.9.

- [x] **3. Match patch headers tolerantly.**
  Owner: coder. Files: `shared/hooks/scripts/protect-files.py`
  (`add_patch_paths`).
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full).
  - Match each line case-insensitively against
    `^\s*\*\*\*\s*(add|update|delete)\s+file\s*:(.*)$` and
    `^\s*\*\*\*\s*move\s+to\s*:(.*)$`. Take the stripped remainder as the
    target. An empty target raises `AmbiguousCommand`, as today.
  - This only adds targets, so it only tightens, for every input kind.
  - Do not fail closed on other `*** ` lines. An update hunk's context line
    is the file's own text after one space (Markdown ` *** bold ***`), and
    a deny there would block ordinary edits. The comment says so.

- [x] **4. Shell helpers and the `Read` name.**
  Owner: coder. Files: `shared/hooks/scripts/protect-files.py`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full).
  - Add `SHELL_HELPER_TOOLS = {"read_bash", "list_bash", "stop_bash"}`,
    with a comment citing P3. When the name is in the set and the input has
    no `command` key, judge the input with `native_targets`. This is not an
    early return.
  - With a `command` key, use today's shell path. `write_bash` and every
    other name ending in `bash` keep today's shell path.
  - Add `"read"` to `READ_ONLY_TOOLS`, commented as the Copilot harness's
    PascalCase name for `view`. Secret-shaped files stay denied.

- [x] **5. Read the search tools' `paths` list (user choice 1: yes).**
  Owner: coder. Files: `shared/hooks/scripts/protect-files.py`
  (`PATH_KEYS`).
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full).
  - Add `"paths"`. A search over a folder, and a `glob` filter such as
    `.env*`, are not judged, like shell reads.

- [x] **6. Give every inventory tool a recorded handling.**
  Owner: coder. Files: `docs/target-mapping.md` (a new table, "Copilot
  harness tools and guard handling"), and `shared/hooks/scripts/protect-files.py`
  only when a row needs a guard change.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/integration-gate-spike/SKILL.md`.
  - Start from the Phase A tool inventory plus the names seen in VS Code
    (A4): `AskUserQuestion`/`ask_user`, `skill`, `tool_search_tool`. Cover
    at least `run_dynamic_workflow`, `dynamic_workflows_manage`, `sql`,
    `session_store_sql`, `semantic_code_search`, `write_agent`,
    `read_agent`, `list_agents`, `task`/`Agent`, `web_fetch`,
    `fetch_copilot_cli_documentation`, `update_todo`, and `rg`.
  - For each tool, record its hook name, its input keys, and one of three
    handlings:
    1. no command, path, or code to run: no decision needed;
    2. a path or file-content key: judged by `PATH_KEYS`, with a key added
       if needed (stricter);
    3. runs commands or code: add a probe step that shows whether its inner
       steps pass through the pre-tool hooks. If they do, record that. If
       they do not, or it cannot be shown, deny the tool by name on
       `github-copilot` (row T4), with a battery row and a docs line.

- [x] **7. Add the probe checks.**
  Owner: coder. Files: `scripts/check_copilot_runtime.py`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/integration-gate-spike/SKILL.md`.
  - Session `codex-patch`, model `gpt-5.2-codex` (offline, only
    Codex-family ids get `apply_patch`), both hook sources. It runs the
    five steps of the evidence scenario `sc5_codex_patch.json`, plus an
    indented header.
  - Checks for that session:
    - `patch-plain-allowed`: success;
    - `patch-secret-denied`: reason has
      `Protected file blocked by policy: .env`;
    - `patch-hook-ask`, `patch-server-ask`, `patch-agent-ask`,
      `patch-indented-hook-ask`: at least one question of kind `hook`
      each, and no denial.
  - Session `main` adds these checks:
    - `helper-tools` (bash in `async` mode, then `read_bash`, `list_bash`,
      `stop_bash`): no result says `Denied by preToolUse hook`. A run with
      no pre-tool hook event is not judged;
    - `read-agent-file` (view `.claude/agents/coder.md`): success, no
      question of kind `hook`;
    - `search-secret-denied` (grep with `paths: [".env"]`): denied;
    - `search-glob-not-judged` (glob `.env*`): no hook denial;
    - any probe step that step 6 adds.

- [x] **8. Update the docs.**
  Owner: coder. Files: `docs/target-mapping.md` (the GitHub Copilot column
  of the parity tables and the agent-definition row),
  `docs/runtime-checks.md` (forms the guard does not check).
  Required Skills: `.claude/skills/documentation/SKILL.md`.
  Content:
  - the Copilot-harness tool names the guards see;
  - rows L1, L2, L3, T1, T2, and T4, written as "a deny or ask became
    allow, on purpose, because …" or "now denied because …";
  - folder-wide search and glob filters are not judged;
  - reads in VS Code are approved by VS Code itself (`host_policy`, A4);
  - VS Code can give a model the patch tool even when the runtime's own
    list does not (A4).

- [x] **9. Run the differential battery and record it.**
  Owner: coder.
  - A scratch script in the session's scratch folder, not committed.
  - It runs `git show dev:shared/hooks/scripts/protect-files.py`, copied
    into the scratch folder, and the working copy over the full step-1
    matrix, plus the command shapes of the earlier batteries: redirects,
    heredocs, interpreters, `git -C`, `cd`, `&&`.
  - It compares the parsed `permissionDecision` and the exit code.
  - Write the table of every difference into the phase session log. Every
    row must match L1, L2, L3, T1, T2, or T4.

- [x] **10. Regenerate and refresh this repository's own install.**
  Owner: coder.
  Commands:
  - `uv run python scripts/generate_targets.py --all`;
  - `uv run python scripts/install_bootstrap.py . --allow-self --local-only`;
  - `uv run python scripts/validate_targets.py`;
  - `uv run python scripts/check_runtime.py`.

  Scope-change record (approved by the orchestrator on 2026-11-17; each
  item serves this phase's stated intent and changes no other decision):
  - Step 1, header shapes inside a shell `apply_patch` heredoc: the
    expected value is deny on all four clients, not the hook-file decision.
    That is today's behavior and it does not change: a shell command that
    starts an unknown program and names a protected file is an uncertain
    hit (`docs/target-mapping.md`), and `add_patch_paths` is not called for
    shell commands.
  - Step 6 found two tools for row T4: `run_dynamic_workflow` and
    `dynamic_workflows_manage`. Both are denied by name on `github-copilot`
    only. Offline the workflow tools answer "extensions are not configured",
    so no run could show their code passing through a hook. The user is
    told and can lift or narrow the deny.
  - Step 7 gains the probe steps that step 6 calls for:
    `deny-workflow-run`, `deny-workflow-manage`, `sql-no-file-write`,
    `subagent-deny-git-reset`, `subagent-store-sql-refused`, and the
    runner's scripted sub-agent steps.
  - `protect-files.py` gets one output function, `print_decision`, shared by
    `emit` and the T4 deny, and the constants `PATCH_BEGIN` and `PATCH_END`.
    No output byte changes.
  - The probe section of `docs/runtime-checks.md` is updated for the new
    counts (31 result lines, two sessions).

- [x] **11. Review.**
  Owner: reviewer.
  Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`,
  `documentation`.
  Focus:
  - only the planned decisions changed (the step 9 table);
  - no early return skips a later check;
  - fail-closed paths still exit 2;
  - the header pattern cannot drop a target;
  - Python 3.9 syntax;
  - every inventory tool has a row.

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
uv run pytest tests/test_protect_files_copilot_harness.py tests/test_hook_gates.py tests/test_protect_files_scoping.py tests/test_protect_files_substitutions.py tests/test_check_copilot_runtime.py -q --tb=short
uv run python scripts/check_copilot_runtime.py --require
python3 -c 'import ast, sys; ast.parse(open(sys.argv[1], encoding="utf-8").read(), feature_version=(3, 9))' shared/hooks/scripts/protect-files.py
grep -q -F 'Copilot harness tools and guard handling' docs/target-mapping.md
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

<!-- The only place a check may be conditional or non-executable. One `- `
     bullet per item, numbered in the order it appears. -->

- The step 9 differential table is in the phase session log, and every row matches a decision-change row of the big plan.
- In a Copilot-harness chat in VS Code where Auto picks a model that uses `apply_patch`, ask for a new plain file and record that it is created.

## Closeout Checklist

Run the numbered CLOSEOUT sequence in `.claude/instructions/closeout.instructions.md` in order. Tick both boxes at its step 2. Later steps bind this file's bytes, so do not edit this file after step 2.

- [x] Step 1: documentation updated, or skipped as pure-internal with a reason
- [x] Step 2: this plan set to `status: complete` with `closeout_session_log`, every step ticked, and LEARN entries or the no-lessons marker recorded

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
