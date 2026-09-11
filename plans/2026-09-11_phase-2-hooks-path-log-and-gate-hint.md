---
name: 2026-09-11_phase-2-hooks-path-log-and-gate-hint
type: small-plan
parent_plan: 2026-09-11_consumer-ceremony-friction
phase_index: 2
status: in-progress
closeout_session_log:
---

# Small Plan: Hook scripts activate Git hooks, keep the error log local, and explain the push refusal

## Scope

Four changes to the hook-script family, plus the plan-wide final audit:

1. `state-sync.sh` sets `core.hooksPath` on the outer repository whenever it
   restores the `.claude` checkout, and `session-start-state.sh` warns when
   hooks are inactive.
2. `state-sync.sh` stops tracking `session_logs/hooks-errors.log` in
   `ai-state`.
3. `enforce-pr-gate.sh` explains why a chained commit-and-push is refused;
   the commit skill documents the rule.
4. Hook tests write only under `tmp_path`, with a leak guard.

## Findings This Plan Is Built On

Hooks path:

- `core.hooksPath .claude/hooks/git-hooks` is set in exactly two places:
  `scripts/install_bootstrap.py:796` and
  `shared/devcontainer/post-start.sh:40`. Nothing under `shared/hooks/`
  sets it, and the generated `.vscode/tasks.json` folder-open task runs only
  `state-sync.sh setup && state-sync.sh pull`.
- `README.md` "Changing dev machines without a devcontainer" says those two
  commands, or the folder-open task, are enough. Without the post-commit hook,
  `record-commit-closeout.sh` never advances `current_phase`, and the next
  agent push is refused for stale plan state with no message about hooks.
- `restore_root_adapters()` in `state-sync.sh` is the one function every
  restoring path shares: a fresh `setup`, `pull` through `finish_pull`, and a
  fresh `checkpoint`. It already treats failure as a warning.
- `session-start-state.sh` already emits one `additional_context` line at
  SessionStart describing branch and phase state.

Error log:

- `git -C .claude ls-files session_logs/hooks-errors.log` shows the log is
  tracked, with no size cap. In this repository it holds 3513 lines dated
  from 2026-07-20 to 2026-09-11. Counting by message: 1302
  `unparseable tool payload`, 846 `protect-files.sh exited with status 2`,
  1067 `protected-file classifier exited with status 2`. Their timestamps
  match pytest and `verify phase` runs and their error texts
  (`heredoc delimiter 'EOF' is never terminated`, `unbalanced process
  substitution`) are the adversarial payloads in `tests/test_hook_gates.py`,
  which runs `protect-files.sh` and `antigravity-pretool.py` with
  `cwd=REPO_ROOT` and `env REPO_ROOT=<live checkout>` (`:26-31`, `:909-916`).
- `session_logs/hooks-bypass.log` is also tracked and is read by
  `assert_bypass_acknowledgement`; it must stay tracked.
- `.claude/.gitattributes` gives `session_logs/*.log` the `merge=union`
  driver so two machines appending to these logs do not conflict. Untracking
  the error log removes that need for it.

Push gate:

- `enforce-pr-gate.sh` evaluates `assert_push_invariants … "HEAD"` when a
  Bash command contains `git push`. A command that also contains the
  `git commit` that would create the certified HEAD is evaluated against the
  pre-commit HEAD and denied with
  `implementation branch must have at least one commit per completed small plan before PR/push`
  plus stale-receipt errors. No skill, policy, or doc mentions it.

## Decisions

- Set the hooks path inside `restore_root_adapters()`, after the adapter
  restore, only when `$REPO_ROOT/.git` exists and
  `$CLAUDE_DIR/hooks/git-hooks` exists. Compare the current value first and
  skip the write when it already matches; overwrite a different value with a
  warning naming the old one. A failure is a `warn`, never a hard exit.
- Delete the duplicate `core.hooksPath` block from
  `shared/devcontainer/post-start.sh` and reword its comment. One place owns
  the behaviour. Leave `install_bootstrap.py` alone.
- `session-start-state.sh` appends one sentence when
  `git config core.hooksPath` is not `.claude/hooks/git-hooks` while
  `.claude/hooks/git-hooks` exists:
  `Git hooks are not active (core.hooksPath unset); run bash .devcontainer/state-sync.sh setup`.
- Add `session_logs/hooks-errors.log` to the nested `.gitignore` written by
  `write_nested_gitignore()`, following the existing `.cache/` append-if-absent
  pattern, and untrack it with `git rm --cached --quiet` when currently
  tracked, following `untrack_nested_cache()`. Never delete the local file.
  No rotation or cap; the file is local. Keep `hooks-bypass.log` tracked.
- In `enforce-pr-gate.sh`, when the denied command also satisfies
  `is_git_commit_command`, prefix the reason with
  `commit and push must be separate Bash commands: the push gate evaluates the current HEAD before this command's commit exists; run the commit first, then push`.
  Do not change what is evaluated.
- Test isolation: every helper in `tests/test_hook_gates.py` (and any other
  test found by `grep -rn 'REPO_ROOT' tests/ | grep env`) that passes the
  live checkout as `REPO_ROOT` passes a `tmp_path` holding an empty
  `.claude/session_logs/` instead. Scripts still run from
  `shared/hooks/scripts`; only the root they log into moves.
- Leak guard: a session-scoped autouse fixture in `tests/conftest.py`
  records the live log's size and mtime at session start and asserts both are
  unchanged at session end, naming the path and the rule in its message;
  skip when the live log does not exist.

## Steps

- [ ] `shared/hooks/scripts/state-sync.sh`: add `configure_outer_hooks_path()`
  and call it at the end of `restore_root_adapters()`; extend
  `write_nested_gitignore()` and add the error-log untrack step where
  `untrack_nested_cache` runs.
- [ ] `shared/devcontainer/post-start.sh`: remove the `core.hooksPath` block
  and update the comment above `setup`.
- [ ] `shared/hooks/scripts/session-start-state.sh`: append the warning
  sentence under the stated condition.
- [ ] `shared/hooks/scripts/enforce-pr-gate.sh`: add the prefixed reason under
  the stated condition.
- [ ] `shared/skills/commit/SKILL.md` Phase 5 and `docs/runtime-checks.md`
  push-gate description: one sentence each on the separate-commands rule.
- [ ] Tests, `tests/test_state_sync.py`: a fresh `setup` on an outer Git
  repository containing `.claude/hooks/git-hooks` sets `core.hooksPath`; a
  repeated `setup` does not rewrite it; `pull` sets it on a writer whose
  checkout arrived from the remote; an outer directory that is not a Git
  repository warns and exits 0; a checkpoint on a nested repository that
  tracks `session_logs/hooks-errors.log` untracks it, keeps the file on disk,
  and the next `status --porcelain` is clean; a fresh setup never tracks it.
  Update the existing tests around `:1681-1752` that seed the remote with
  that file and assert on its tracked content.
- [ ] Tests, `tests/test_hook_gates.py`: a payload `git commit -m x && git push`
  on an implementation branch yields a denial containing
  `separate Bash commands`; a plain `git push` denial does not. Route every
  live-checkout `REPO_ROOT` to `tmp_path`. In the file that already covers
  `session-start-state.sh`, assert the hooks warning appears when the path is
  unset and is absent when set.
- [ ] `tests/conftest.py`: add the leak guard fixture. Run the full suite and
  confirm the live log's line count is unchanged before and after.
- [ ] `scripts/validate_targets.py`: assert both generated `state-sync.sh`
  copies contain the `core.hooksPath` configuration and the error-log
  gitignore seed, and that generated `post-start.sh` no longer sets the hooks
  path.
- [ ] Documentation: `README.md` "Changing dev machines" states that `setup`
  also activates the Git hooks; `docs/runtime-checks.md` hooks section and
  `docs/architecture.md` state-sync `setup` bullet mention it; the state-sync
  section notes the error log is local-only and why.
- [ ] Final-phase audit. Sweep `README.md`, `docs/`, root guidance, shared
  policies, agent prompts, and skills for claims invalidated by Phases 1 and
  2 (prerequisites, `UNVERIFIED` semantics, hooks-path ownership, remediation
  commands, tracked error log, chained push). Record each surface and outcome
  under `## Stale-claims surfaces checked` in this phase's closeout session
  log. Record reusable lessons in `.claude/MEMORY.md`.
- [ ] Regenerate and install locally.

## Review Profiles

Hook scripts, devcontainer, validator, and tests are control-plane: `code`,
`architecture`, `security`, `tests`, and `ponytail`. Load the Ponytail skill
in `full` mode before every coding step.

## Verification

```bash
wc -l .claude/session_logs/hooks-errors.log   # before
uv run pytest tests/test_state_sync.py tests/test_hook_gates.py tests/test_lifecycle_hooks.py -q --tb=short
uv run pytest tests/ -q
wc -l .claude/session_logs/hooks-errors.log   # after: identical
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests && uv run ruff format --check shared scripts tests
uv run python scripts/generate_targets.py --all && uv run python scripts/install_bootstrap.py . --allow-self --local-only
uv run python scripts/validate_targets.py && uv run python scripts/check_runtime.py
git -C .claude ls-files session_logs/hooks-errors.log   # prints nothing after the first checkpoint
```

Phase-specific proof: clone a scratch consumer to a second directory with no
`.claude`, run `bash .devcontainer/state-sync.sh setup` and `pull`, and show
`git config core.hooksPath` prints `.claude/hooks/git-hooks`. Run the
generated guard against `git commit -m x && git push` and show the new
explanation.

## Risks And Fallback Paths

- A consumer deliberately uses a different hooks path. The overwrite warns
  with the old value. If review considers that too aggressive, skip when any
  value is set and let the session-start warning report it.
- `restore_root_adapters()` runs inside hooks that must stay fast. One
  `git config --get` and at most one write add milliseconds.
- `cmd_status` reports the last state-sync error from the local file, so
  untracking changes nothing for it.
- The leak guard fails on a machine where a hook fires during the test run
  for an unrelated reason. The message names the path so the cause is
  visible.

## Done Criteria

- `setup`, `pull`, and a fresh `checkpoint` all leave `core.hooksPath` set on
  a Git outer repository, and a session that starts without it is told.
- `post-start.sh` no longer carries its own copy.
- The error log is untracked in `ai-state` after one checkpoint, and fresh
  installs never track it.
- A chained commit-and-push denial explains the rule; the commit skill and
  runtime docs state it.
- The full test suite leaves the live log byte-identical.
- The final-phase audit is recorded under the exact heading.

## Closeout Checklist

- [ ] All steps implemented and verified
- [ ] `uv run pytest tests/ -q` passes
- [ ] mypy, ruff check, and ruff format pass
- [ ] `validate_targets.py` and `check_runtime.py` pass
- [ ] Targets regenerated and installed locally
- [ ] Code, architecture, security, tests, and Ponytail reviews complete
- [ ] Critical and major findings at zero
- [ ] Documentation updated
- [ ] `.claude/MEMORY.md` records the reusable lessons
- [ ] Closeout session log complete, including `## Stale-claims surfaces checked`
- [ ] Nested state checkpointed before persisting the closeout receipt
- [ ] Verification passed (`verify phase` then `verify closeout` PASS)
