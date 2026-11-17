---
name: 2026-11-17_phase-A-copilot-runtime-probe
type: small-plan
parent_plan: copilot-harness-migration
phase_index: 1
# status must occur exactly once: planned | in-progress | paused | complete | cancelled
# New phase files default to planned (not yet started); the branch-creation
# and post-commit hooks flip the active phase to in-progress automatically.
status: complete
closeout_session_log: .claude/session_logs/2026-11-17_copilot-harness-phase-A.md
# Pause fields (required only when status is paused):
# paused_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# paused_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# pause_session_log: <repository-relative readable UTF-8 PAUSED session log>
# Cancellation fields (required only when status is cancelled):
# cancelled_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# cancelled_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# cancelled_evidence: <repository-relative readable UTF-8 CANCELLED artifact>
---

# Small Plan: 2026-11-17_phase-A-copilot-runtime-probe

## Scope

This phase adds an opt-in, offline check of the real Copilot runtime that
ships inside VS Code (REQ-001). It runs the runtime through its own SDK with
a private data folder, no login, and a small local server that plays the
model and returns scripted tool calls. So it makes no model call and needs
no account. It installs a fresh copy of this bootstrap into a temporary
folder and removes that folder's `.mcp.json`, so no MCP server starts and
nothing reaches the network. It then checks the guard results that are
correct today. Later phases add the checks for their own fixes, and list
this command in their required verification.

The method is the evidence harness in
`.claude/explorations/2026-11-17_copilot-harness-migration-evidence/scripts/`
(`step2_discover.mjs`, `step3_session.mjs`, `show_outcomes.py`,
`sc2_guards.json`), observed there and in planning probes P1 to P4 (big
plan). It does not exercise VS Code's own layer: approval dialogs, "Allow
all", or the tool set VS Code gives each model. VS Code gave `gpt-6-luna`
the patch tool, which the runtime's own list does not (A4).

## Steps

- [x] **1. Write the failing tests first.**
  Owner: coder. Files: create `tests/test_check_copilot_runtime.py`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/testing-patterns/SKILL.md`.
  Cases. None of them starts Node or the runtime:
  - Runtime discovery picks, among fake `~/.vscode-server/bin/*/` folders
    that have both `node` and
    `node_modules/@github/copilot-sdk/dist/index.js`, the one with the
    newest folder modification time. It skips folders that lack either.
    `--vscode-bin DIR` overrides discovery.
  - With no runtime found, `--require` exits 1 with a FAIL line. Without
    `--require` the probe exits 0 with a WARN line.
  - The runtime environment builder removes every variable whose name
    starts with `CLAUDE`, `ANTHROPIC`, or `CLAUDECODE`, and keeps `PATH` and
    `HOME`.
  - `evaluate` on a small synthetic event list gives the right PASS and
    FAIL results. Use the event names `show_outcomes.py` reads. Cases: a
    denial; a hook question; a plain success; and a tool run with no
    pre-tool hook event, which is not judged (the runtime's own read of a
    finished shell, P3).
  - The temporary project builder leaves no `.mcp.json` in the project.
  - `scripts/copilot_runtime_probe.mjs` is a regular file that the Python
    script names.
  Acceptance: the tests fail before step 2 and pass after it.

- [x] **2. Add the probe.**
  Owner: coder. Files: create `scripts/check_copilot_runtime.py` and
  `scripts/copilot_runtime_probe.mjs`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/integration-gate-spike/SKILL.md`,
  `.claude/skills/code-style/SKILL.md`.
  Contracts (adapt bodies to the codebase):
  - `find_runtime(vscode_bin: Path | None) -> RuntimeInfo | None`, with
    `node`, `sdk_root`, `sdk_version` (from the SDK's `package.json`), and
    `vscode_commit` (the folder name).
  - `prepare_project(parent: Path) -> Path`: `git init -b dev`, then
    `scripts/install_bootstrap.py <dir> --mode full --local-only`, then
    delete `<dir>/.mcp.json`. No commit.
  - `run_session(runtime: RuntimeInfo, project: Path, scenario: dict[str, object], home: Path) -> SessionRecord`.
  - `evaluate(record: SessionRecord, checks: Sequence[Check]) -> list[CheckResult]`.
  - `main(argv: Sequence[str] | None = None) -> int`, with these options:
    `--require`, `--vscode-bin DIR`, `--keep`, and `--discover DIR`
    (prints what the runtime discovers in DIR: hooks, MCP servers,
    instructions, skills, agents; no session).

  The Node runner is adapted from `step3_session.mjs` and
  `step2_discover.mjs`, without the probe-hook reply files:
  - `CopilotClient` with `baseDirectory` in the temporary folder,
    `useLoggedInUser: false`, and the stripped environment;
  - the session `provider` pointed at its own 127.0.0.1 server;
  - folder trust through the session's `folderTrust.addTrusted`;
  - every session event recorded, plus the first request of each
    sub-agent;
  - the `firstRequestTools` list recorded per session.

  Text output:
  - the VS Code commit, the SDK version, and the runtime version from
    `client.getStatus()`;
  - one line per check;
  - a tool inventory per session: each offered tool's name and input keys.

  Limits: each session stops after 150 seconds and the whole run after 480
  seconds, as FAIL. Temporary folders are removed unless `--keep` is given.

  Must not:
  - write to `~/.copilot`, VS Code settings, or this repository;
  - log in;
  - contact any host other than 127.0.0.1;
  - be called by `verify.py` or by pytest;
  - take a `--format` option.

  Acceptance: step 1 passes. Mypy and ruff are clean.

  Scope-change record (approved by the orchestrator on 2026-11-17; each
  item serves this phase's stated intent and adds no feature):
  - `prepare_project` removes three things, not one: `<dir>/.mcp.json`, the
    mirror copy `.claude/bootstrap-root/.mcp.json`, and the line
    `BOOTSTRAP_ROOT_PATH=.mcp.json` in `.claude/bootstrap-ownership.env`.
    Reason, seen with `strace` in a loopback-only namespace: the
    `SessionStart` hook calls `state-sync.sh pull`, which calls
    `restore-root-adapters.sh`, and that script copies `.mcp.json` back from
    the mirror. A manifest line with no mirror copy makes that script exit 1.
  - `prepare_project` writes a one-line `README.md`, because a fresh
    install ships none and the plain-read step views it.
  - The runtime environment also drops `GH_TOKEN`, `GITHUB_TOKEN`, and
    `COPILOT_GITHUB_TOKEN`.
  - An extra result line, `session-main`, reports FAIL for a session that
    timed out, crashed, or logged a runtime error.
  - `--discover DIR` adds no folder trust, so it lists 0 hooks and 0 MCP
    servers and says so. Instructions, skills, and agents are listed.
  - `mcp-none` also fails for a temporary project that holds `.mcp.json`
    after the last session. Reason: with only the project file deleted, the
    file was back in 4 of 4 control runs, yet the event-based conditions
    reported FAIL in only 1 of 4.
  - `prepare_project` gives git and the installer a fixed author identity,
    no standard input, and the time left of the 480-second limit.

- [x] **3. Add the baseline checks.**
  Owner: coder. Files: `scripts/check_copilot_runtime.py`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/integration-gate-spike/SKILL.md`.
  - Session `main` uses both hook sources (the real full install), model
    `probe-model`, and the steps ported from `sc2_guards.json`, without its
    MCP step.
  - Expected values come from `docs/target-mapping.md`, the F3 table, and
    P4.

  | Check | Tool call or action | Expected |
  | --- | --- | --- |
  | `hooks-untrusted` | discovery before trust | 0 hooks |
  | `hooks-sources` | discovery after trust | hooks listed from `.github/hooks/hooks.json` and from `.claude/settings.json` |
  | `hooks-subfolder` | discovery from `<project>/docs/deeper` after trust | the same two sources listed (P4) |
  | `mcp-none` | MCP discovery and session events | 0 MCP servers |
  | `deny-git-reset` | bash `git reset --hard HEAD` | denied; reason has `Blocked dangerous git operation` |
  | `deny-force-push` | bash `git push --force origin dev` | denied; same reason |
  | `deny-secret-rm` | bash `rm -f .env` | denied; reason has `Protected file blocked by policy: .env` |
  | `deny-secret-view` | view `.env` | denied; same reason |
  | `ask-vscode-settings` | create `.vscode/settings.json` | at least one question of kind `hook`; not denied |
  | `ask-agent-wrapper` | edit `.github/agents/coder.agent.md` | at least one question of kind `hook` |
  | `deny-branch` | bash `git checkout -b probe_implementation` | denied by the branch guard |
  | `deny-commit` | bash `git commit -m probe` | denied; reason has `commit gate failed for github-copilot` |
  | `deny-pr` | bash `gh pr create --base dev --title probe --body probe` | denied by the PR gate |
  | `allow-plain` | bash `echo probe`; view `README.md`; create `probe-plain.txt`; edit it | success; no question of kind `hook` |

  Acceptance: `uv run python scripts/check_copilot_runtime.py --require`
  prints PASS for every check, the three version lines, and the tool
  inventory.

- [x] **4. Document the probe.**
  Owner: coder. Files: `docs/runtime-checks.md`, under "VS Code Copilot
  evidence boundary". Add a subsection, "Copilot runtime probe".
  Required Skills: `.claude/skills/documentation/SKILL.md`,
  `.claude/skills/ponytail/SKILL.md` (full).
  Content:
  - what it proves, and what it does not (VS Code's own layer);
  - the command;
  - how the runtime is found: the newest `~/.vscode-server/bin/*` folder
    by modification time, or `--vscode-bin`. Only a VS Code server folder
    is known to ship a separate `node`; a desktop install needs
    `--vscode-bin` to a folder with both;
  - no model call, no account, no MCP server, no network beyond 127.0.0.1;
  - opt-in, not part of `verify.py`;
  - the integration-gate-spike evidence table (unknown, result, evidence),
    citing the evidence folder and P1 to P4;
  - the sentence "VS Code can give a model a different tool set than the
    runtime's own list for that model.", citing A4;
  - that the probe starts the runtime through the SDK, not through VS
    Code's agent host, so the `/run/user/<uid>` socket fault (A1) does not
    stop it.

  Say that VS Code hooks are "in preview".

- [x] **5. Review.**
  Owner: reviewer.
  Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`,
  `documentation`.
  Focus:
  - no user-config writes;
  - no network;
  - the time limits;
  - each check fails on a wrong result, not only on a crash;
  - the docs claim nothing beyond the run.

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
uv run pytest tests/test_check_copilot_runtime.py -q --tb=short
uv run python scripts/check_copilot_runtime.py --require
grep -q -F 'Copilot runtime probe' docs/runtime-checks.md
grep -q -F 'VS Code can give a model a different tool set than the runtime' docs/runtime-checks.md
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

<!-- The only place a check may be conditional or non-executable. One `- `
     bullet per item, numbered in the order it appears. -->

- Run the probe a second time and record that every check gives the same result (no flaky check).
- Record the printed VS Code commit, SDK version, runtime version, and tool inventory in the closeout session log.

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
