---
name: 2026-09-11_phase-B-hooks-path-from-state-sync
type: small-plan
parent_plan: 2026-09-11_consumer-ceremony-friction
phase_index: 2
status: planned
closeout_session_log:
---

# Small Plan: Configure the Git hooks path wherever the checkout is restored

## Scope

Make `shared/hooks/scripts/state-sync.sh` set `core.hooksPath` on the outer
repository whenever it restores the `.claude` checkout, so every documented
first-machine path activates the commit-msg, post-commit, and pre-push hooks.
Warn at session start when the hooks path is missing. Remove the now-duplicate
block from the devcontainer script.

## Findings This Plan Is Built On

- `core.hooksPath .claude/hooks/git-hooks` is set in exactly two places:
  `scripts/install_bootstrap.py:796` and
  `shared/devcontainer/post-start.sh:40`. Nothing under `shared/hooks/`
  sets it, and the generated `.vscode/tasks.json` folder-open task runs only
  `state-sync.sh setup && state-sync.sh pull`.
- `README.md` "Changing dev machines without a devcontainer" tells the user
  those two commands, or the folder-open task, are enough. They are not: the
  Git hooks never run on that machine.
- Without the post-commit hook, `record-commit-closeout.sh` never advances
  `current_phase` and never completes the big plan, and `state-sync.sh push`
  never runs after commits. The next agent push is refused for stale plan
  state, and no message mentions the hooks path.
- `restore_root_adapters()` in `state-sync.sh` is the one function every
  restoring path shares: a fresh `setup`, `pull` through `finish_pull`, and a
  fresh `checkpoint`. It already treats failure as a warning.
- `session-start-state.sh` already emits one `additional_context` line at
  SessionStart describing branch and phase state.

## Decisions

- Set the hooks path inside `restore_root_adapters()`, after the adapter
  restore, only when `$REPO_ROOT/.git` exists and
  `$CLAUDE_DIR/hooks/git-hooks` exists. Compare the current value first and
  skip the write when it already matches, so repeated runs stay quiet. A
  failure is a `warn`, never a hard exit, matching the script's contract.
- Delete the duplicate block from `shared/devcontainer/post-start.sh` and
  reword its comment to say `setup` now configures the hooks path. One place
  owns the behaviour.
- Add one sentence to `session-start-state.sh`'s message when
  `git config core.hooksPath` is not `.claude/hooks/git-hooks` while
  `.claude/hooks/git-hooks` exists:
  `Git hooks are not active (core.hooksPath unset); run bash .devcontainer/state-sync.sh setup`.
  This is a context line, not a denial.
- Do not touch `install_bootstrap.py`; its own configuration remains correct
  and covers the install path before any state-sync restore has run.

## Steps

- [ ] In `shared/hooks/scripts/state-sync.sh`, add `configure_outer_hooks_path()`
  as described and call it at the end of `restore_root_adapters()`.
- [ ] In `shared/devcontainer/post-start.sh`, remove the `core.hooksPath`
  block and update the comment above `setup`.
- [ ] In `shared/hooks/scripts/session-start-state.sh`, append the warning
  sentence to `message` under the stated condition.
- [ ] Tests in `tests/test_state_sync.py`: a fresh `setup` on an outer
  repository containing `.claude/hooks/git-hooks` sets `core.hooksPath`; a
  repeated `setup` does not rewrite it; `pull` sets it on a writer whose
  checkout arrived from the remote; an outer directory that is not a Git
  repository produces a warning and exit 0. In `tests/test_lifecycle_hooks.py`
  or the file that already covers `session-start-state.sh`, assert the
  warning sentence appears when the hooks path is unset and is absent when
  set.
- [ ] In `scripts/validate_targets.py`, assert both generated `state-sync.sh`
  copies contain the `core.hooksPath` configuration and that the generated
  `post-start.sh` no longer does.
- [ ] Documentation: `README.md` "Changing dev machines" paragraph states that
  `setup` also activates the Git hooks; `docs/runtime-checks.md` hooks section
  and `docs/architecture.md` state-sync `setup` bullet mention it.
- [ ] Regenerate and install locally.

## Review Profiles

Hook scripts and the devcontainer are control-plane: `code`, `architecture`,
`security`, `tests`, and `ponytail`. Load the Ponytail skill in `full` mode.

## Verification

```bash
uv run pytest tests/test_state_sync.py tests/test_lifecycle_hooks.py -q --tb=short
uv run pytest tests/ -q
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests && uv run ruff format --check shared scripts tests
uv run python scripts/generate_targets.py --all && uv run python scripts/install_bootstrap.py . --allow-self --local-only
uv run python scripts/validate_targets.py && uv run python scripts/check_runtime.py
```

Phase-specific proof: clone a scratch consumer to a second directory with no
`.claude`, run `bash .devcontainer/state-sync.sh setup` and `pull`, and show
`git config core.hooksPath` prints `.claude/hooks/git-hooks`.

## Risks And Fallback Paths

- A consumer deliberately uses a different hooks path. The write is skipped
  only when the value already matches; a different value is overwritten with a
  warning naming the old value. If review considers that too aggressive, skip
  when any value is set and let the session-start warning report it.
- `restore_root_adapters()` runs during hooks that must stay fast. One
  `git config --get` and at most one `git config` write add milliseconds.

## Done Criteria

- `setup`, `pull`, and a fresh `checkpoint` all leave `core.hooksPath` set on
  a Git outer repository.
- A session that starts without it is told in the SessionStart context.
- `post-start.sh` no longer carries its own copy.
- Docs describe the behaviour; generated copies regenerated.

## Closeout Checklist

- [ ] All steps implemented and verified
- [ ] `uv run pytest tests/ -q` passes
- [ ] mypy, ruff check, and ruff format pass
- [ ] `validate_targets.py` and `check_runtime.py` pass
- [ ] Targets regenerated and installed locally
- [ ] Code, architecture, security, tests, and Ponytail reviews complete
- [ ] Critical and major findings at zero
- [ ] Documentation updated
- [ ] `.claude/MEMORY.md` records the reusable lessons or the no-lessons marker
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested state checkpointed before persisting the closeout receipt
- [ ] Verification passed (`verify phase` then `verify closeout` PASS)
