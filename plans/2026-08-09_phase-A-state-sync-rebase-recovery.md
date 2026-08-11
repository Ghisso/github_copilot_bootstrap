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
state is reported as a distinct latched condition and surfaced in
`state-sync.sh status` so the failure is visible instead of silent. The
warn-never-fail contract does not change.

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
      pre-existing state (create): `.git/rebase-merge/autostash` exists while
      `.git/rebase-merge/head-name` does not. Treat every other pre-existing
      `rebase-merge` or `rebase-apply` shape as valid or unknown; do not infer
      that state belongs to state sync.
- [ ] Add `clear_current_pull_rebase_state()` (create). This helper is only for
      a rebase known to have been started by the current pull. Contract: run
      `git -C "$CLAUDE_DIR" rebase --abort` capturing combined output; if that
      exits non-zero, run `git -C "$CLAUDE_DIR" rebase --quit` capturing
      combined output. Return 0 when either succeeded, non-zero when both
      failed, after passing both captured outputs to `append_error_output`.
      Must not use `|| true`. Must not use `2>/dev/null` to hide the failure.
- [ ] In `reconcile_committed_state` (modify), before the remote-ref check: when
      `nested_rebase_in_progress` is true, branch on ownership. For the exact
      orphaned-autostash shape, `warn` that leftover state was detected and run
      `git -C "$CLAUDE_DIR" rebase --quit` directly, capturing and logging any
      failure; never run `--abort` on this pre-existing path. For a structurally
      valid or unknown pre-existing rebase, run neither `--abort` nor `--quit`:
      warn that state sync will not alter an ambiguous rebase, give explicit
      commands to inspect and resolve or quit it, and `return 1`. Both warnings
      must be distinct from the existing conflict warning so the conditions are
      separable by grep in `.claude/session_logs/hooks-errors.log`. The valid or
      unknown path must leave `HEAD`, the logical index, the worktree, and the
      rebase metadata unchanged.
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
      create `.git/rebase-merge/` containing only an `autostash` file and no
      `head-name`, run `pull`. Assert exit code 0; assert the latched-state
      warning and the `--quit`-only marker appear; assert no `--abort` marker
      appears; assert `.git/rebase-merge` no longer exists; assert a following
      `pull` succeeds.
- [ ] `test_rebase_abort_alone_cannot_clear_half_initialized_state`: assert
      directly that `git rebase --abort` fails on that fixture. This validates
      the fixture against git itself and makes the suite fail if the `--quit`
      fallback is reverted.
- [ ] `test_pull_preserves_valid_preexisting_rebase`: create a real, valid
      in-progress rebase before invoking `pull`. Snapshot `HEAD`, the logical
      index (including unmerged stages), worktree contents/status, and rebase
      metadata. Assert the command remains warn-never-fail, gives explicit
      operator guidance, invokes neither `--abort` nor `--quit`, does not start
      reconciliation, and leaves every snapshot byte-for-byte or logically
      identical as appropriate.
- [ ] `test_current_pull_recovery_reports_distinct_abort_and_quit_failures`:
      exercise the failed-pull path after proving no rebase existed before that
      pull, force `--abort` to emit a unique abort-failure marker and `--quit`
      to emit a different quit-failure marker, and make both fail. Assert both
      markers independently in `hooks-errors.log`, assert the warning names the
      manual `git -C <dir> rebase --quit` command, and assert the public command
      still exits 0. A shared failure string is forbidden because it cannot
      prove that both recovery commands ran and both outputs were retained.
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
  behind. Mitigation: the fixture creates only `autostash`, which is exactly the
  observed state, and one test asserts that real `git rebase --abort` fails on
  it, so git validates the fixture instead of an assumption.
- The warning strings become an interface the tests depend on. Accepted
  deliberately: marker-based assertions are the only way to prove the fixed path
  ran, per the recorded lesson about outcome-only tests.
- This phase edits a script the live session executes. Mitigation: warn-never-fail
  keeps any defect from blocking a session, the dogfood refresh runs only after
  verification passes, and `state-sync.sh status` runs immediately after it.
- A pre-existing rebase may represent active operator work rather than failed
  state sync. Mitigation: only the observed orphaned-autostash shape is cleaned
  automatically, with `--quit` only. Valid or unknown pre-existing state is
  preserved, and a real-rebase fixture asserts that `HEAD`, index, worktree,
  and rebase metadata are unchanged.

## Acceptance Criteria

- [ ] A half-initialized `.git/rebase-merge` matching the observed
      orphaned-autostash shape is cleared automatically with `--quit` only, and
      the next sync succeeds.
- [ ] A structurally valid or unknown pre-existing rebase is not aborted or
      quit automatically. State sync gives explicit operator guidance and
      preserves `HEAD`, the logical index, the worktree, and rebase metadata.
- [ ] A rebase known to have been created by the current pull uses `--abort`,
      then `--quit` only as fallback.
- [ ] Recovery failure is warned and logged, never swallowed by `|| true`.
- [ ] When current-pull abort and quit recovery both fail, their distinct
      outputs are both retained and asserted independently.
- [ ] Pre-existing rebase state produces a warning distinct from an ordinary
      conflict warning.
- [ ] `state-sync.sh status` reports `rebase: in-progress` or `rebase: none`.
- [ ] Every state-sync entry point still exits 0 on failure; no sync problem
      blocks a session.
- [ ] Regeneration is deterministic and both installed `state-sync.sh` copies
      stay byte-identical.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
