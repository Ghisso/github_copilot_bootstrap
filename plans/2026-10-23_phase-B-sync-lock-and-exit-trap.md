---
name: 2026-10-23_phase-B-sync-lock-and-exit-trap
type: small-plan
parent_plan: state-sync-safety-fixes
phase_index: 2
status: planned
closeout_session_log:
---

# Small Plan: One State Sync at a Time, and an Exit Trap for the Settings Copy

## Scope

Several sessions, clients, the outer `post-commit` hook, a VS Code task, and the host plus its devcontainer share one checkout, so two state-sync runs can overlap on the same nested repository. This phase lets only one mutating run work at a time. A run that finds another one working skips at once, and the next run includes its changes. It also adds an exit trap. A run that ends early, normally or through `INT`, `TERM`, or `HUP` (for example a hook timeout), puts the settings copy back. A run that ends while a rebase or merge is unfinished keeps the copy and names it instead. Requirements: REQ-005 (exit-trap part), REQ-008, REQ-009.

`flock` (from util-linux) is new to this repository, so this phase follows `.claude/skills/integration-gate-spike/SKILL.md`. The planning probe on 2026-10-23 (util-linux 2.39.3, Bash 5.2.21, Linux 6.18 under WSL2) observed:

| Unknown | Result | Evidence |
| --- | --- | --- |
| Lock with no lock file | `exec 9<"$dir"` then `flock -n 9` takes an exclusive lock on the folder itself | Probe |
| Busy result | `flock -n` exits 1 while another process holds the lock | Probe |
| Other failure | Exits 65 (`EX_DATAERR`) on a bad descriptor | Probe |
| Release | Held until every process holding descriptor 9 has exited; a child of a holder killed with `SIGKILL` kept it until the child ended | Probe |
| `exec` failure under `set -e` | `exec 9<missing \|\| ...` prints an error and the script goes on, in Bash's default mode | Probe |
| Signal traps | `trap 'exit 143' TERM`, `trap 'exit 130' INT`, and `trap 'exit 129' HUP` run the `EXIT` trap; a process-group signal returns those codes | Probe |
| Host and devcontainer | Not observed; exclusion across that boundary needs both sides on one kernel | Optional Verification |

Decisions settled from this evidence:

- **Lock target:** the repository root folder itself, opened read-only on descriptor 9. There is no lock file, so `git add -A` cannot commit one, neither tree gets dirty, and nothing goes stale. It works on a fresh clone before `.claude/` exists. The host and the devcontainer see the same folder through the bind mount, and both installed copies of the script resolve the same root.
- **Busy run:** skip at once with `flock -n`, with no wait. Codex gives `checkpoint` 3 seconds, and the script's stdin drain alone can use 2 of them. The message goes to stderr through `info`, not to the error log: a busy lock is a normal outcome with several sessions, and logging it would fill the `last-error` line of `status`.
- **No `flock`** (stock macOS): the run proceeds unlocked and silent, as today. Any `flock` failure other than busy prints an `info` notice and proceeds unlocked, so a filesystem that refuses locks never stops sync for good.

## Steps

- [ ] **1. Add the lock.**
  - Owner: `coder`. File: `shared/hooks/scripts/state-sync.sh`.
  - Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/integration-gate-spike/SKILL.md`.
  - Add `acquire_sync_lock` and make it the first line of `dispatch_mutating`: `acquire_sync_lock || return 0`. `status` stays unlocked. Behavior, in order:
    1. `command -v flock` fails: return 0 with no message.
    2. `exec 9<"$REPO_ROOT"` fails: `info` that the lock could not be opened, then return 0. Never attach `2>/dev/null` to a bare `exec`: it would silence the script's stderr for the rest of the run.
    3. `flock -n 9` exits 0: return 0. Exit 1: `info "another state sync is running for $REPO_ROOT; $MODE skipped. The next sync will include these changes."` and return 1. Any other status: `info "could not lock $REPO_ROOT for state sync (flock exit <status>); continuing without the lock."`, close descriptor 9, and return 0.
  - Use the fixed descriptor 9, because Bash 3.2 has no `{fd}` allocation. Add no lock file, no stale-lock recovery, and no wait.
  - Leave a `ponytail:` comment that names the ceilings: no exclusion without `flock` or on a filesystem that refuses it; a detached child that inherits descriptor 9, for example `git maintenance` started by a commit, keeps the lock until it ends; exclusion between host and container needs one shared kernel. Upgrade path: a portable lock with owner recovery, only after a measured collision.
  - Acceptance: a busy run of any mutating mode exits 0 and runs no Git command.

- [ ] **2. Add the exit trap.**
  - Owner: `coder`. File: `shared/hooks/scripts/state-sync.sh`.
  - Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Add `settle_local_settings_on_exit`. Install it at top level, just before the `case "$MODE"` dispatch, with `trap settle_local_settings_on_exit EXIT`, `trap 'exit 129' HUP`, `trap 'exit 130' INT`, and `trap 'exit 143' TERM`. The signal traps must call `exit` so the script stops.
  - Behavior: with no settings copy held, do nothing. With a copy held while `nested_operation_in_progress` is true, `warn "state sync stopped while a rebase or merge was unfinished;"` followed by phase A's kept-settings sentence, then clear the variable. Otherwise call `restore_local_settings || true`. Write every command so `set -e` cannot end the trap early.
  - Keep copy-don't-move: `preserve_local_settings` still copies and never deletes the live file.
  - Acceptance: a signal during a pull leaves no settings copy behind, except while a rebase or merge is unfinished; then the copy is kept and named.

- [ ] **3. Tests.**
  - Owner: `coder`. File: `tests/test_state_sync.py`.
  - Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/testing-patterns/SKILL.md`, `.claude/skills/integration-gate-spike/SKILL.md`.
  - Put `sync_lock` in the name of every lock test and `exit_trap` in the name of every trap test, so the real-invocation command in `## Verification` selects them. Lock tests that need a real `flock` carry `pytest.mark.skipif(shutil.which("flock") is None, reason=...)`.
  - The test holds the lock with `fcntl.flock` on a read-only descriptor of the root folder; that is the same kernel lock `flock(1)` takes.
  - New tests:
    1. `test_sync_lock_busy_run_skips_without_running_git`, parametrized over the six mutating modes. A dirty file waits and the test holds the lock. Expect exit 0, empty stdout, `another state sync is running` on stderr, no fake-Git call log, unchanged HEAD and remote ref, and the dirty file still untracked. After release, `checkpoint` commits the file.
    2. `test_sync_lock_is_shared_by_devcontainer_and_hooks_copies`. Install the devcontainer copy and the hooks copy under one root, and run both without `AI_STATE_REPO_ROOT`, so each resolves the root from its own location (MEMORY: cover the generated devcontainer copy). Run A (hooks copy, `checkpoint`) uses a fake `git` that pauses at its first `add` until a release file appears, with a 30-second limit so a broken run fails instead of hanging. While A waits, run B (devcontainer copy, `checkpoint`) exits 0 with the busy message and makes no commit. After release, A exits 0 and its commit holds the dirty file.
    3. `test_sync_lock_status_runs_while_lock_is_held`. With the lock held, `status` exits 0 with its normal report and no busy message.
    4. `test_sync_lock_fresh_clone_leaves_no_lock_file`. An outer `git init` root with no `.claude` folder; the devcontainer copy runs `setup` with no remote. Afterward the root's top-level entries are exactly `.git`, `.claude`, and the devcontainer folder, and the nested `git status --porcelain` is empty.
    5. `test_sync_lock_runs_unlocked_without_flock`. `PATH` points at a folder of symlinks to every program on the current `PATH` except `flock`. With the lock held by the test, `checkpoint` still commits and prints no busy message.
    6. `test_sync_lock_failure_runs_unlocked_with_notice`. A fake `flock` exits 65. `checkpoint` commits; stderr holds `could not lock`; the error log does not.
    7. `test_exit_trap_restores_settings_copy_after_signal`, parametrized over `SIGTERM`, `SIGINT`, and `SIGHUP` with expected exit codes 143, 130, and 129 (128 plus the signal number). Start `pull` with `subprocess.Popen(..., start_new_session=True)`. At `pull`, the fake `git` deletes the live settings file, writes a ready file, and sleeps. The test waits for the ready file and signals the process group. Expect that exit code, the settings file back with its original bytes, and no settings copy left under `.claude/.git/`.
    8. `test_exit_trap_keeps_and_names_copy_during_unfinished_rebase`. The fake `git` passes `pull` to real Git, which stops on a real conflict, then writes `git-wrote\n` to the live settings file, writes the ready file, and sleeps. After `SIGTERM`: exit 143; the `rebase-merge` folder on disk; the live file still `git-wrote\n`; one copy with the original bytes; and its path on stderr after `state sync stopped while a rebase or merge was unfinished`.
  - All existing tests pass unchanged; each uses its own root, so none of them contends for a lock.

- [ ] **4. Update documentation.**
  - Owner: `documenter` (CLOSEOUT step 1). Files: `docs/runtime-checks.md` (the paragraph at line 502 and the hook paragraph at about lines 506-516), `shared/policies/workflow.instructions.md` (the session-start AI-state bullet at line 539), `README.md` (the "Both are safe to (re-)run anytime" paragraph near line 470), `docs/smoke-tests.md` (lines 279 and 335).
  - Required Skills: `.claude/skills/documentation/SKILL.md`.
  - State: one state sync runs at a time per checkout; a busy run skips and the next one catches up; `status` never waits.
  - State: a run stopped by `INT`, `TERM`, or `HUP` puts the settings copy back, unless a rebase or merge is unfinished, in which case it keeps the copy and names it. Only an untrappable kill (`SIGKILL`), or a signal that lands while the copy is being put back, can still leave the copy under `.claude/.git/`; keep the manual recovery sentence for that case.
  - State: the lock covers state-sync runs only. Direct `git -C .claude` commands by people or agents do not take it.

- [ ] **5. Orchestrator closeout items.**
  - Owner: orchestrator.
  - Before CLOSEOUT step 2, run `uv run python scripts/generate_targets.py --all` and then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`. From then on, this repository's own hooks take the lock.

- [ ] **6. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`.
  - Focus: a busy run never touches Git; no lock file or stale-lock path exists; the trap cannot write the copy back during an unfinished operation; the Bash 3.2 rules hold.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run pytest tests/test_state_sync.py -q --tb=short -k "sync_lock or exit_trap"
uv run pytest tests/test_state_sync.py tests/test_install_bootstrap.py -q --tb=short
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

- Host and devcontainer exclusion: inside a running devcontainer, hold the lock from the repository root with `flock "$PWD" sleep 60`. Meanwhile, on the host, run `bash .devcontainer/state-sync.sh checkpoint` in the same checkout and record whether it prints `another state sync is running`. A run that commits instead shows that this host and container do not share the lock.
- On a macOS host without `flock`, run `checkpoint` and record that it commits as before.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT); the order below mirrors it
rather than restating it.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
