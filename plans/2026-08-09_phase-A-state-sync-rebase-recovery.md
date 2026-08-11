---
name: 2026-08-09_phase-A-state-sync-rebase-recovery
type: small-plan
parent_plan: state-sync-recovery-and-plan-cancellation
phase_index: 1
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-08-09_phase-A-state-sync-rebase-recovery

## Scope

Make AI state sync recover from a partially-initialized rebase instead of
latching into a permanent failure. Today `reconcile_committed_state` recovers
with `git rebase --abort 2>/dev/null || true`. When git left a
`.git/rebase-merge/` directory containing only `autostash` and no `head-name`,
`--abort` cannot succeed, `|| true` throws the failure away, and every later
sync fails with `fatal: It seems that there is already a rebase-merge
directory`. This phase adds ownership-aware recovery. A pre-existing
half-initialized state matching the observed orphaned-autostash shape is cleared
with `--quit` only; a structurally valid or unknown pre-existing rebase is left
intact with explicit operator guidance. A rebase known to have been created by
the current pull may use `--abort`, then `--quit` as fallback. Pre-existing
state is classified by one common preflight before every potentially mutating
entry point, including the modes used by Stop and post-commit hooks, and is
surfaced in `state-sync.sh status` so the failure is visible instead of silent.
The warn-never-fail contract does not change.

## Ownership

- `coder`: `shared/hooks/scripts/state-sync.sh`, `tests/test_state_sync.py`,
  `scripts/validate_targets.py`.
- `verifier`: full verification plus target generation, determinism, and the
  `state-sync.sh status` health probe.
- `reviewer`: the profiles listed below.
- `documenter`: skip for this phase; documentation lands in Phase E, which is
  the single home for the state-sync incident record.

## Required Skills

- `.claude/skills/ponytail/SKILL.md` in `full` mode.
- `.claude/skills/code-style/SKILL.md` and
  `.claude/skills/testing-patterns/SKILL.md`.
- `.claude/skills/run-tests/SKILL.md` for the verifier.
- `.claude/skills/learn/SKILL.md` and `.claude/skills/commit/SKILL.md` at
  closeout.

## Review Profiles

- `.claude/review-profiles/code.md`
- `.claude/review-profiles/architecture.md`
- `.claude/review-profiles/security.md`
- `.claude/review-profiles/tests.md`
- `.claude/review-profiles/ponytail.md`

Review is mandatory here because this phase changes control-plane/high-risk
lifecycle code. This use of the Ponytail profile follows the current calibrated
review policy; it is not a return to universal Ponytail review for every diff.

## Steps

- [ ] Add `nested_rebase_in_progress()` to
      `shared/hooks/scripts/state-sync.sh` (modify). Returns 0 when
      `$CLAUDE_DIR/.git/rebase-merge` or `$CLAUDE_DIR/.git/rebase-apply` exists,
      1 otherwise. Must use a plain directory test and run no git subprocess:
      the check has to work in exactly the state where git itself refuses to
      operate.
- [ ] Add the narrow classifier needed to recognize the observed orphaned
      pre-existing state (create). It matches only when `rebase-apply` is
      absent and `.git/rebase-merge/` contains exactly one directory entry: a
      non-symlink regular file named `autostash`. Any extra entry, missing or
      non-regular `autostash`, symlink, subdirectory, or simultaneous
      `rebase-apply` state is valid or unknown and must be preserved; do not
      infer that it belongs to state sync.
- [ ] Add one common mutating-entrypoint preflight (create) and route `setup`,
      `pull`, `checkpoint`, `publish`, `push`, and `migrate-from-hf` through it
      before their command functions run. `status` is read-only and must only
      report rebase state, never clean it. With no rebase, proceed normally.
      For the exact orphaned-autostash shape, warn and run `rebase --quit` only;
      on cleanup failure, keep the existing logged/manual-guidance behavior and
      skip the command. For valid or unknown state, write one guidance message
      directly to stderr: do not call `warn`, `append_error_output`, or
      `prepare_error_log`, do not run a git subprocess, and do not dispatch the
      requested command. Preserve a distinct internal protected-state outcome
      so nested callers can propagate it without adding a warning.
- [ ] Update top-level dispatch (modify) to consume that protected-state outcome
      without its usual `cmd_x || warn ...` fallback. The exact public contract
      for valid or unknown pre-existing state is: exit 0, write no stdout, emit
      stderr-only operator guidance, and perform no checkpoint, reconciliation,
      publication, persistent log write, or other nested-repository mutation.
      This same behavior applies when `checkpoint`/`publish` are invoked by
      automatic Stop hooks and when `push` is invoked by post-commit.
- [ ] Add `clear_current_pull_rebase_state()` (create). This helper is only for
      a rebase known to have been started by the current pull. Contract: run
      `git -C "$CLAUDE_DIR" rebase --abort` capturing combined output; if that
      exits non-zero, run `git -C "$CLAUDE_DIR" rebase --quit` capturing
      combined output. Return 0 when either succeeded, non-zero when both
      failed, after passing both captured outputs to `append_error_output`.
      Must not use `|| true`. Must not use `2>/dev/null` to hide the failure.
- [ ] Remove pull-only ownership classification from
      `reconcile_committed_state` (modify); the common preflight owns
      pre-existing-state classification for every mutating mode. Keep its
      orphan warning distinct from the existing pull-conflict warning. The
      current-pull cleanup below remains local to reconciliation because only
      that path owns rebase state created after preflight.
- [ ] Replace the recovery on the failed-pull path (currently line ~248) with
      `clear_current_pull_rebase_state` (modify). This path runs only after the
      pre-existing-state check proved no rebase was already active, so the
      failed pull owns any new rebase metadata. When cleanup returns non-zero,
      emit a second distinct warning naming the leftover state and the manual
      command, then keep the existing `return 1`. Preserve the existing
      conflict warning text and its manual resolution instructions unchanged.
- [ ] Add a `rebase:` line to `cmd_status` output (modify), value `in-progress`
      or `none`, printed with the other repository fields and before
      `error-log:`. This makes a latched failure visible from a single
      read-only command.
- [ ] Add regression tests to `tests/test_state_sync.py` (modify), listed under
      Test Scenarios below.
- [ ] Add structural assertions to `scripts/validate_targets.py` (modify): the
      generated `state-sync.sh` must contain the literal `rebase --quit`
      invocation and must not contain `rebase --abort 2>/dev/null || true`.
      Assert the literal invocation, not loose independent substrings.
- [ ] Regenerate targets and refresh the dogfood install, then confirm the
      health probe.

## Test Scenarios

Each test asserts a marker unique to the fixed path and the absence of the old
path's marker. Outcome-only assertions can pass under both old and new code.

- [ ] `test_pull_clears_half_initialized_rebase_state`: build a nested repo,
      create `.git/rebase-merge/` containing exactly one non-symlink regular
      file named `autostash`, and run `pull`. Make fake Git append every rebase
      invocation to a side-channel file. Assert exit code 0; assert the
      latched-state warning appears; assert the side channel contains exactly
      one `rebase --quit` and no `rebase --abort`; assert `.git/rebase-merge`
      no longer exists; assert a following `pull` succeeds.
- [ ] `test_rebase_abort_alone_cannot_clear_half_initialized_state`: assert
      directly that `git rebase --abort` fails on that fixture. This validates
      the fixture against git itself and makes the suite fail if the `--quit`
      fallback is reverted.
- [ ] `test_mutating_entrypoints_preserve_valid_preexisting_rebase`: parameterize
      over `setup`, `pull`, `checkpoint`, `publish`, `push`, and
      `migrate-from-hf`. Create a real, valid in-progress rebase before each
      invocation. Snapshot `HEAD`, the logical index (including unmerged
      stages), worktree contents/status, rebase metadata, remote state, and the
      existing error-log contents or absence. Assert exact public behavior:
      exit 0, empty stdout, and stderr-only operator guidance. Use Git tracing
      or a fake-Git invocation side channel to prove no add, commit, fetch,
      pull, rebase, or push ran; assert every snapshot and the persistent error
      log remain unchanged. This covers direct commands plus the
      `checkpoint`/`publish` modes used by Stop and the `push` mode used by
      post-commit.
- [ ] `test_extra_or_nonfile_rebase_metadata_is_preserved`: parameterize the
      orphan fixture with an extra regular metadata file, a subdirectory, a
      symlink/non-regular `autostash`, and simultaneous `rebase-apply` state.
      Assert every shape takes the valid/unknown stderr-only path, stays intact,
      and records no rebase command in the invocation side channel.
- [ ] `test_current_pull_recovery_reports_distinct_abort_and_quit_failures`:
      exercise the failed-pull path after proving no rebase existed before that
      pull, force `--abort` to emit a unique abort-failure marker and `--quit`
      to emit a different quit-failure marker, and make both fail. Record the
      actual fake-Git invocations in a side-channel file and assert the exact
      ordered recovery sequence is `rebase --abort`, then `rebase --quit`, with
      no extra rebase command. Assert both output markers independently in
      `hooks-errors.log`, assert the warning names the manual
      `git -C <dir> rebase --quit` command, and assert the public command still
      exits 0. A shared failure string is forbidden because it cannot prove
      that both recovery commands ran and both outputs were retained.
- [ ] `test_status_reports_rebase_state`: assert `status` prints
      `rebase: in-progress` with the fixture present and `rebase: none` without
      it.
- [ ] Regression: `test_push_after_rebase_conflict_does_not_push`,
      `test_reconciliation_after_conflict_can_push`, and
      `test_publish_refuses_dirty_state_without_committing_or_publishing` must
      pass unchanged.

## Verification

```bash
uv sync
uv run pytest tests/test_state_sync.py -q --tb=short
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/install_bootstrap.py . --allow-self --local-only
bash .claude/hooks/scripts/state-sync.sh status
uv run python .claude/scripts/quality_score.py scripts/ --phase 2026-08-09_phase-A-state-sync-rebase-recovery --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
```

Generator determinism, after all edits settle:

```bash
uv run python scripts/generate_targets.py --all
cp -a dist /tmp/dist-gen-a
uv run python scripts/generate_targets.py --all
diff -r /tmp/dist-gen-a dist
rm -rf /tmp/dist-gen-a
```

## Risks

- The hand-built `.git/rebase-merge` fixture must match what git actually left
  behind. Mitigation: the fixture contains exactly one non-symlink regular file,
  `autostash`, which is the observed directory shape, and one test asserts that
  real `git rebase --abort` fails on it. Extra-entry and non-file fixtures prove
  the classifier fails safe instead of broadening from that evidence.
- The warning strings become an interface the tests depend on. Accepted
  deliberately: marker-based assertions are the only way to prove the fixed path
  ran, per the recorded lesson about outcome-only tests.
- This phase edits a script the live session executes. Mitigation: warn-never-fail
  keeps any defect from blocking a session, the dogfood refresh runs only after
  verification passes, and `state-sync.sh status` runs immediately after it.
- A pre-existing rebase may represent active operator work rather than failed
  state sync. Mitigation: only the observed orphaned-autostash shape is cleaned
  automatically, with `--quit` only. Valid or unknown pre-existing state is
  intercepted before dispatch with stderr-only guidance. A parameterized
  real-rebase fixture asserts that every mutating mode preserves `HEAD`, index,
  worktree, rebase metadata, remote state, and the persistent error log.

## Acceptance Criteria

- [ ] A half-initialized `.git/rebase-merge` matching the observed
      orphaned-autostash shape—exactly one non-symlink regular `autostash` file
      and no `rebase-apply` state—is cleared automatically with `--quit` only,
      and the next sync succeeds. Any extra or non-file entry is preserved as
      valid or unknown state.
- [ ] A structurally valid or unknown pre-existing rebase is not aborted or
      quit automatically. Every mutating entry point exits 0 with empty stdout
      and stderr-only operator guidance, bypasses checkpointing/reconciliation/
      publication, makes no persistent log write, and preserves `HEAD`, the
      logical index, the worktree, rebase metadata, and remote state.
- [ ] A rebase known to have been created by the current pull uses `--abort`,
      then `--quit` only as fallback.
- [ ] Recovery failure is warned and logged, never swallowed by `|| true`.
- [ ] When current-pull abort and quit recovery both fail, their distinct
      outputs are both retained and asserted independently, and the recorded
      Git invocation sequence is exactly abort then quit.
- [ ] The orphan warning and the valid/unknown stderr-only guidance are each
      distinct from an ordinary conflict warning.
- [ ] `state-sync.sh status` reports `rebase: in-progress` or `rebase: none`.
- [ ] Every state-sync entry point still exits 0 at the script boundary; no sync
      problem blocks a session. `status` remains read-only and never performs
      cleanup.
- [ ] Regeneration is deterministic and both installed `state-sync.sh` copies
      stay byte-identical.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
