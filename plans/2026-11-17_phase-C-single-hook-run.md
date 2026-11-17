---
name: 2026-11-17_phase-C-single-hook-run
type: small-plan
parent_plan: copilot-harness-migration
phase_index: 3
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

# Small Plan: 2026-11-17_phase-C-single-hook-run

## Scope

The Copilot harness loads both `.github/hooks/hooks.json` and
`.claude/settings.json`. So every hook runs twice: two approval questions,
one session logged as two, and state sync twice (F2; the real VS Code, A3).
This phase makes a hook that was reached through the Claude settings stand
down on the Copilot harness. "Stand down" means: read and discard the input,
print nothing, and exit 0 (REQ-003). The copy in `.github/hooks/hooks.json`
still runs the same guards with the `github-copilot` client.

A hook stands down only when all five conditions in step 2 hold. Two cases
never stand down:

- A real Claude Code session: it lacks `COPILOT_HOOK_DEPTH`, which the
  runtime sets only for its own hook processes (P1, A3).
- The Local harness with `chat.useClaudeHooks: true`: its hooks lack
  `COPILOT_CLI=1` (A2). Its double run stays, and is documented with the
  advice to turn that setting off. Local's hook sources follow user
  settings, so a hook there cannot tell whether the other source also runs.

## Steps

- [ ] **1. Write the failing tests first.**
  Owner: coder. Files: `tests/test_hook_gates.py`,
  `tests/test_validate_targets.py`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/testing-patterns/SKILL.md`.
  Run `run-hook.sh git-protection.sh github-copilot` on
  `git reset --hard HEAD`, in a temporary repository with a generated
  Copilot hook file, under these environments:
  - All five conditions hold: exit 0, empty stdout, input consumed.
  - Each condition removed in turn (no marker; `COPILOT_CLI` unset;
    `COPILOT_HOOK_DEPTH` unset; `CLAUDECODE=1`; Copilot hook file missing,
    a link, or missing one guard): the deny is printed, as today.
  - The environment of this planning session (Claude Code):
    `COPILOT_CLI_ENABLED_FEATURE_FLAGS`, `COPILOT_OTEL_FILE_EXPORTER_PATH`,
    `CLAUDECODE=1`, and the marker. The deny is printed.
  - Claude Code started from a Copilot shell (P1 variables):
    `COPILOT_CLI=1`, `COPILOT_AGENT_SESSION_ID`, `COPILOT_HOME`, and the
    marker, with no `COPILOT_HOOK_DEPTH`. The deny is printed.
  - A Local-harness hook with `chat.useClaudeHooks` on (A2 variables), with
    the marker. The deny is printed.
  - Old install, new launcher: no marker, Copilot hook variables set. The
    deny is printed.
  - The generated Claude settings carry the marker in every hook command.
    The Codex, Copilot, and Antigravity hook files never carry it.
  Acceptance: the new cases fail before steps 2 and 3.

- [ ] **2. Add the stand-down rule to the launcher.**
  Owner: coder. Files: `shared/hooks/scripts/run-hook.sh`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full).
  Stand down only when all of these hold:
  1. `BOOTSTRAP_HOOK_SOURCE` is `claude-settings`;
  2. `COPILOT_CLI` is `1`;
  3. `COPILOT_HOOK_DEPTH` is non-empty;
  4. `CLAUDECODE` is empty;
  5. `$REPO_ROOT/.github/hooks/hooks.json` is a regular file and not a
     link, and contains each of these fixed strings:
     `protect-files.sh github-copilot`, `git-protection.sh github-copilot`,
     `enforce-branch-state.sh github-copilot`,
     `enforce-commit-gate.sh github-copilot`,
     `enforce-pr-gate.sh github-copilot`.

  Behavior:
  - Then: `cat >/dev/null`, `exit 0`. Otherwise: today's `exec`, unchanged.
  - A short comment names the reason and the evidence: F2, A2, A3, P1.

  Must not:
  - exit non-zero on the stand-down path, which would deny every Copilot
    tool call;
  - key on any `CLAUDE_CODE_*` variable, because VS Code's agent host sets
    one (A3);
  - read the payload.

- [ ] **3. Mark the Claude settings commands.**
  Owner: coder.
  Files:
  - `scripts/generate_targets.py` (`_claude_hook_cmd`): emit
    `REPO_ROOT="..."; BOOTSTRAP_HOOK_SOURCE=claude-settings "$REPO_ROOT/.claude/hooks/scripts/run-hook.sh" <script> <args>`;
  - `scripts/validate_targets.py`: require the marker in every Claude
    settings hook command, and refuse it in the other three hook files;
  - `tests/test_validate_targets.py`.

  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/code-style/SKILL.md`.
  Older installs stay safe either way:
  - new launcher with old settings: no marker, so no stand-down;
  - old launcher with new settings: the prefix is ignored, so no
    stand-down.

- [ ] **4. Add the single-run probe checks.**
  Owner: coder. Files: `scripts/check_copilot_runtime.py`.
  Required Skills: `.claude/skills/ponytail/SKILL.md` (full),
  `.claude/skills/integration-gate-spike/SKILL.md`.
  - `ask-vscode-settings` and `ask-agent-wrapper` now require exactly one
    question of kind `hook`.
  - New check `single-session-log`: in the probe project's
    `.claude/session_logs/hooks-sessions.log`, the session has at least one
    `target=github-copilot` line and no `target=claude-code` line.
  - The probe still removes `CLAUDE*` variables from the runtime
    environment (Phase A), so condition 4 holds in the probe as it does in
    VS Code.

- [ ] **5. Update the docs.**
  Owner: coder. Files: `README.md` (Hooks section), `docs/target-mapping.md`
  (Native Adapters, GitHub Copilot).
  Required Skills: `.claude/skills/documentation/SKILL.md`.
  In plain words:
  - On the Copilot harness, the hooks from `.claude/settings.json` stand
    down, and `.github/hooks/hooks.json` runs them once.
  - On the Local harness, `chat.useClaudeHooks: true` makes every hook run
    twice: two questions and two session entries. Turn it off for this
    bootstrap.
  - Name the five conditions.

- [ ] **6. Regenerate and refresh this repository's own install.**
  Owner: coder.
  Commands:
  - `uv run python scripts/generate_targets.py --all`;
  - `uv run python scripts/install_bootstrap.py . --allow-self --local-only`;
  - `uv run python scripts/validate_targets.py`;
  - `uv run python scripts/check_runtime.py`.

- [ ] **7. Review.**
  Owner: reviewer.
  Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`,
  `documentation`.
  Focus:
  - no environment of a real Claude Code session can stand down;
  - the stand-down path never denies;
  - mixed old and new files stay safe;
  - the docs do not overclaim the Local case.

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
uv run python scripts/check_copilot_runtime.py --require --format text
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

- In a Copilot-harness chat in VS Code, ask the agent to create `.vscode/settings.json` and record that exactly one approval question appears, and that `hooks-sessions.log` has no `target=claude-code` line for that session.

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
