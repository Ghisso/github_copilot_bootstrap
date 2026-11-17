---
name: 2026-11-17_phase-D-lifecycle-hook-stand-down
type: small-plan
parent_plan: copilot-harness-migration
phase_index: 4
# status must occur exactly once: planned | in-progress | paused | complete | cancelled
# New phase files default to planned (not yet started); the branch-creation
# and post-commit hooks flip the active phase to in-progress automatically.
status: complete
closeout_session_log: .claude/session_logs/2026-11-18_copilot-harness-phase-D.md
# Pause fields (required only when status is paused):
# paused_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# paused_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# pause_session_log: <repository-relative readable UTF-8 PAUSED session log>
# Cancellation fields (required only when status is cancelled):
# cancelled_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# cancelled_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# cancelled_evidence: <repository-relative readable UTF-8 CANCELLED artifact>
---

# Small Plan: 2026-11-17_phase-D-lifecycle-hook-stand-down

## Scope

The Copilot harness loads both `.github/hooks/hooks.json` and
`.claude/settings.json`. So every hook runs twice: one session logged as
two, state sync twice, and two questions for a protected edit (F2; the real
VS Code, A3). This phase implements **option B** of the big plan (REQ-004).
"Stand down" means: read and discard the input, print nothing, and exit 0.

- **Standing down:** only the lifecycle hooks reached through the Claude
  settings: `state-sync.sh`, `session-log.sh`, `session-start-state.sh`,
  `claude-stop.sh`, `reporting-reminder.sh`. The `.github/hooks` copy runs
  its own lifecycle hooks once.
- **Never standing down:** guard scripts. On the Copilot harness, a deny
  happens twice (harmless: a deny wins), and a protected-config edit asks
  twice.
- **What a wrong stand-down costs:** when a lifecycle hook stands down while
  the `.github/hooks` copy does not run, that session loses its session-log
  entries, session-start context, AI-state pull and push, and the reminder.
  No guard.
- **Never standing down:** a real Claude Code session and the Local harness
  with `chat.useClaudeHooks: true` (A2). The docs advise turning that
  setting off.
- **If the user chose option A or C at approval,** the orchestrator replaced
  steps 1, 2, and 4 with that option's row of the big plan before branch
  creation.

## Steps

- [x] **1. Write the failing tests first.**
  Owner: coder. Files: `tests/test_hook_gates.py`,
  `tests/test_validate_targets.py`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/testing-patterns/SKILL.md`.
  In a temporary repository with a generated Copilot hook file, run
  `run-hook.sh` for `session-log.sh claude-code` (lifecycle) and for
  `git-protection.sh github-copilot` with `git reset --hard HEAD` (guard),
  under these environments:
  - All seven conditions of step 2 hold: the lifecycle hook prints nothing,
    exits 0, consumes its input, and writes no session-log line. The guard
    still prints its deny.
  - Each condition broken in turn: the lifecycle hook runs as today. The
    broken conditions are:
    - no marker;
    - `COPILOT_CLI` unset;
    - `COPILOT_HOOK_DEPTH` unset;
    - `COPILOT_HOOK_DIR` set;
    - `CLAUDECODE=1`;
    - the Copilot hook file missing, a link, holding `disableAllHooks`, or
      missing `session-log.sh github-copilot`.
  - The environment of this planning session (Claude Code):
    `COPILOT_CLI_ENABLED_FEATURE_FLAGS`, `COPILOT_OTEL_FILE_EXPORTER_PATH`,
    `CLAUDECODE=1`, and the marker. The lifecycle hook runs.
  - Claude Code started from a Copilot shell (P1 variables):
    `COPILOT_CLI=1`, `COPILOT_AGENT_SESSION_ID`, `COPILOT_HOME`, and the
    marker, with no `COPILOT_HOOK_DEPTH`. The lifecycle hook runs.
  - A Local-harness hook with `chat.useClaudeHooks` on (A2 variables), with
    the marker. The lifecycle hook runs.
  - For every guard script name (`protect-files.sh`,
    `pretool-bash-guard.sh`, `git-protection.sh`, `enforce-branch-state.sh`,
    `enforce-commit-gate.sh`, `enforce-pr-gate.sh`, `openwiki-guard.sh`,
    `record-branch-state.sh`): no stand-down, with all conditions holding.
  - The generated Claude settings carry the marker in every hook command.
    The Codex, Copilot, and Antigravity hook files never carry it.
  Acceptance: the new cases fail before steps 2 and 3.

- [x] **2. Add the stand-down rule to the launcher.**
  Owner: coder. Files: `shared/hooks/scripts/run-hook.sh`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full).
  Stand down only when all of these hold:
  1. the script name is one of `state-sync.sh`, `session-log.sh`,
     `session-start-state.sh`, `claude-stop.sh`, `reporting-reminder.sh`;
  2. `BOOTSTRAP_HOOK_SOURCE` is `claude-settings`;
  3. `COPILOT_CLI` is `1`;
  4. `COPILOT_HOOK_DEPTH` is non-empty;
  5. `COPILOT_HOOK_DIR` is empty;
  6. `CLAUDECODE` is empty;
  7. `$REPO_ROOT/.github/hooks/hooks.json` is a regular file and not a
     link, does not contain `disableAllHooks`, and contains the fixed
     strings `session-log.sh github-copilot` and `state-sync.sh push`.

  Behavior:
  - Then: `cat >/dev/null`, `exit 0`. Otherwise: today's `exec`, unchanged.
  - A short comment names the evidence: F2, A2, A3, P1, P4.

  Must not:
  - stand down any other script;
  - exit non-zero on the stand-down path;
  - key on a `CLAUDE_CODE_*` variable (A3);
  - read the payload.

- [x] **3. Mark the Claude settings commands.**
  Owner: coder.
  Files:
  - `scripts/generate_targets.py` (`_claude_hook_cmd`): emit
    `REPO_ROOT="..."; BOOTSTRAP_HOOK_SOURCE=claude-settings "$REPO_ROOT/.claude/hooks/scripts/run-hook.sh" <script> <args>`;
  - `scripts/validate_targets.py`: require the marker in every Claude
    settings hook command, and refuse it in the other three hook files;
  - `tests/test_validate_targets.py`.

  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/code-style/SKILL.md`.
  Older installs stay safe: a new launcher with old settings has no marker,
  and an old launcher ignores the prefix. Neither stands down.

- [x] **4. Add the probe checks.**
  Owner: coder. Files: `scripts/check_copilot_runtime.py`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/integration-gate-spike/SKILL.md`.
  - `single-session-log`: the probe project's
    `.claude/session_logs/hooks-sessions.log` has, for the session, at
    least one `target=github-copilot` line and no `target=claude-code`
    line.
  - `state-sync-once`: the probe project's
    `.claude/session_logs/hooks-errors.log` has exactly one state-sync
    pull line for the session. Take the exact text from `state-sync.sh`;
    the probe project has no state remote.
  - `guards-both-sources`: creating `.vscode/settings.json` gives exactly
    two questions of kind `hook`, one per source. This pins option B.
  - The probe keeps removing `CLAUDE*` variables from the runtime
    environment (Phase A), so condition 6 holds in the probe as it does in
    VS Code.

- [x] **5. Update the docs.**
  Owner: coder. Files: `README.md` (Hooks section), `docs/target-mapping.md`
  (Native Adapters, GitHub Copilot).
  Required Skills: `.claude/skills/documentation/SKILL.md`.
  In plain words:
  - On the Copilot harness, the lifecycle hooks from `.claude/settings.json`
    stand down. The guards run from both files, so a deny shows twice and a
    protected edit asks twice.
  - Name the seven conditions, and what a wrong stand-down costs.
  - The Copilot harness no longer gets the Claude-settings state push at
    `UserPromptSubmit` and `SessionEnd`; the Copilot file still pushes at
    every `Stop`.
  - On the Local harness, `chat.useClaudeHooks: true` makes every hook run
    twice. Turn it off for this bootstrap.

- [x] **6. Regenerate and refresh this repository's own install.**
  Owner: coder.
  Commands:
  - `uv run python scripts/generate_targets.py --all`;
  - `uv run python scripts/install_bootstrap.py . --allow-self --local-only`;
  - `uv run python scripts/validate_targets.py`;
  - `uv run python scripts/check_runtime.py`.

  Scope-change record (approved by the orchestrator on 2026-11-18; each
  item serves this phase's stated intent, and no guard can stand down):
  - Step 2: the stand-down path runs `cat >/dev/null 2>&1 || true` and not
    the bare `cat >/dev/null`. Under `set -e`, a failing `cat` on a closed
    standard input would exit non-zero, and this path must never do that.
  - Step 2: `reporting-reminder.sh` and `claude-stop.sh` stand down
    although the Copilot hook file has no entry for them. Nothing is lost:
    the Copilot file's `Stop` entries cover the session log, the stop
    check, and the state push, and the runtime ignored the reminder's
    nested `claude-code` answer (F13). `README.md` says so.
  - Step 3: the independent copy of the command builder in
    `scripts/validate_targets.py` emits the marker too.
  - Step 4 also changes `tests/test_check_copilot_runtime.py` and the probe
    section of `docs/runtime-checks.md`. A run prints 46 lines. The session
    script `scripts/copilot_runtime_probe.mjs` is unchanged.
  - Step 4, `state-sync-once`: the errors log has no session id, so the
    check counts the pull lines of the whole log and relies on `main`
    being the first session in the project.
  - Step 4, `guards-both-sources`: it passes before and after this phase,
    because the guards do not change. It is a pin: it fails when a guard
    stands down or a hook source stops running.
  - Step 4, added from the Phase C review (old gap): the probe removes
    every `GIT_*` and `GH_*` variable from the environment it gives the
    runtime, and from the environment of `git init` and the installer in
    `prepare_project`, which then adds its own identity values. A
    to-be-denied command that runs because of a broken guard can then not
    act on another repository.
  - Step 1: the tests of the probe checks were written after the probe
    code. Mutation runs and a run against the earlier probe show that they
    can fail. The launcher, marker, and validator tests were written first.
  - Step 1: four calls are added to the script form of
    `tests/test_hook_gates.py`, which the CI workflow runs on macOS.
  - Step 5, after review round 1: the docs do not repeat this plan's
    wording that a deny "happens twice" and a protected edit "asks twice".
    The recorded runs show one deny reason per denied call. For a
    protected edit the runtime raises two hook questions, and in the one
    real VS Code run VS Code answered the second one itself, so one
    question was seen (A6). The docs say that.
  - After review round 1: `stands_down()` silences `grep` errors for an
    unreadable Copilot hook file; the probe also removes `AI_STATE_*`
    variables from the runtime environment; `docs/architecture.md` gets one
    sentence on the stand-down rule.

- [x] **7. Review.**
  Owner: reviewer.
  Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`,
  `documentation`.
  Focus:
  - no guard script can stand down;
  - no environment of a real Claude Code session or Local session can stand
    down;
  - the stand-down path never denies;
  - mixed old and new files stay safe.

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
uv run pytest tests/test_hook_gates.py tests/test_validate_targets.py tests/test_check_copilot_runtime.py -q --tb=short
uv run python scripts/check_copilot_runtime.py --require
grep -q -F 'BOOTSTRAP_HOOK_SOURCE=claude-settings' dist/multi-agent/.claude/settings.json
test "$(grep -c -F 'BOOTSTRAP_HOOK_SOURCE' dist/multi-agent/.github/hooks/hooks.json)" = "0"
grep -q -F 'chat.useClaudeHooks' README.md
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

<!-- The only place a check may be conditional or non-executable. One `- `
     bullet per item, numbered in the order it appears. -->

- In a Copilot-harness chat in VS Code, record that `hooks-sessions.log` has no `target=claude-code` line for that session, and that `git reset --hard HEAD` is still denied.

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
