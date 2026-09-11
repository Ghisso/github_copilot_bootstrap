---
name: 2026-09-11_phase-E-hook-log-hygiene
type: small-plan
parent_plan: 2026-09-11_consumer-ceremony-friction
phase_index: 5
status: planned
closeout_session_log:
---

# Small Plan: Keep the hook error log local and keep tests out of it

## Scope

Stop tracking `session_logs/hooks-errors.log` in the nested `ai-state`
repository, make every test that runs a hook script write only under its
`tmp_path`, and add a guard that fails the suite if any test appends to the
live log. This is the final phase, so it also carries the plan-wide
documentation, memory, and LEARN audit.

## Findings This Plan Is Built On

- `git -C .claude ls-files session_logs/hooks-errors.log` shows the log is
  tracked. It has no size cap. In this repository it holds 3513 lines dated
  from 2026-07-20 to 2026-09-11.
- Counting by message: 1302 `unparseable tool payload`, 846
  `protect-files.sh exited with status 2`, 1067 `protected-file classifier
  exited with status 2`. Their timestamps match pytest and `verify phase`
  runs, and their error texts (`heredoc delimiter 'EOF' is never terminated`,
  `unbalanced process substitution`) are the adversarial payloads in
  `tests/test_hook_gates.py`. That file runs `protect-files.sh` and
  `antigravity-pretool.py` with `cwd=REPO_ROOT` and
  `env REPO_ROOT=<live checkout>` (`:26-31`, `:909-916`), so `fail_closed`
  appends to the live `.claude/session_logs/hooks-errors.log`.
- Real consumer entries are the remaining few hundred: `stop-session-log-check`
  warnings on every turn with a dirty tree and no dated log, and state-sync
  warnings from offline or conflicting syncs.
- `session_logs/hooks-bypass.log` is also tracked and is read by
  `assert_bypass_acknowledgement`; it must stay tracked.
- `.claude/.gitattributes` gives `session_logs/*.log` the `merge=union`
  driver specifically so two machines appending to these logs do not
  conflict. Untracking the error log removes that need for it.

## Decisions

- Add `session_logs/hooks-errors.log` to the nested `.gitignore` written by
  `write_nested_gitignore()` in `state-sync.sh`, following the existing
  `.cache/` upgrade pattern (append when absent), and untrack it with
  `git rm --cached --quiet` when it is currently tracked, following
  `untrack_nested_cache()`. The local file is never deleted.
- Keep `hooks-bypass.log` tracked.
- Test isolation: change every helper in `tests/test_hook_gates.py` (and any
  other test found by `grep -rn 'REPO_ROOT' tests/ | grep env`) that passes
  the live checkout as `REPO_ROOT` to pass a `tmp_path` that contains an empty
  `.claude/session_logs/` directory. The scripts still run from
  `shared/hooks/scripts`; only the repository root they log into moves.
- Leak guard: a session-scoped autouse fixture in `tests/conftest.py` records
  the live log's size and mtime at session start and asserts both are
  unchanged at session end, with a message naming the log path and the rule.
- Do not add rotation or truncation to the local file. It is untracked and
  local; the user can delete it. Record in the closeout log if review wants
  a cap.

## Steps

- [ ] `shared/hooks/scripts/state-sync.sh`: extend `write_nested_gitignore`
  and add the untrack step; run it where `untrack_nested_cache` runs.
- [ ] `tests/test_state_sync.py`: a checkpoint on a nested repository that
  tracks `session_logs/hooks-errors.log` untracks it, keeps the file on disk,
  and the next `status --porcelain` is clean; a fresh setup never tracks it.
  Update existing tests around `:1681-1752` that seed the remote with that
  file and assert on its tracked content.
- [ ] `tests/test_hook_gates.py` and any other offender: route `REPO_ROOT` to
  `tmp_path`. Run the full suite and confirm the live log's line count is
  unchanged before and after.
- [ ] `tests/conftest.py`: add the leak guard fixture.
- [ ] `scripts/validate_targets.py:3771` already asserts a hook root has no
  error log in one scenario; extend it to assert the generated nested
  `.gitignore` seed lists the error log.
- [ ] Documentation: `docs/architecture.md` state-sync section notes the error
  log is local-only and why; `docs/runtime-checks.md` where the log is
  described.
- [ ] Final-phase audit. Sweep `README.md`, `docs/`, root guidance, shared
  policies, agent prompts, and skills for claims invalidated by Phases A
  through E (prerequisites, hooks path ownership, prompt-time publication,
  remediation commands, tracked error log). Record each surface and outcome
  under `## Stale-claims surfaces checked` in this phase's closeout session
  log. Record reusable lessons in `.claude/MEMORY.md`.
- [ ] Regenerate and install locally.

## Review Profiles

Hook script, tests, and validator: `code`, `architecture`, `security`,
`tests`, and `ponytail`. Load the Ponytail skill in `full` mode.

## Verification

```bash
wc -l .claude/session_logs/hooks-errors.log   # before
uv run pytest tests/ -q
wc -l .claude/session_logs/hooks-errors.log   # after: identical
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests && uv run ruff format --check shared scripts tests
uv run python scripts/generate_targets.py --all && uv run python scripts/install_bootstrap.py . --allow-self --local-only
uv run python scripts/validate_targets.py && uv run python scripts/check_runtime.py
git -C .claude ls-files session_logs/hooks-errors.log   # prints nothing after the first checkpoint
```

## Risks And Fallback Paths

- `cmd_status` reports the last state-sync error from the log; it reads the
  local file, so untracking changes nothing for it.
- A consumer wanted the error history on other machines. The bypass ledger and
  session logs remain tracked; only operational warnings become local.
- The leak guard fails on a machine where a hook fires during the test run
  for an unrelated reason. The fixture message names the path so the cause is
  visible; skip the guard when the live log does not exist.

## Done Criteria

- The error log is untracked in `ai-state` after one checkpoint, and fresh
  installs never track it.
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
