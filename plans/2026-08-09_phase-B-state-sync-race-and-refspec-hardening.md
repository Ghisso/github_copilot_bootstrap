---
name: 2026-08-09_phase-B-state-sync-race-and-refspec-hardening
type: small-plan
parent_plan: state-sync-recovery-and-plan-cancellation
phase_index: 2
status: complete
closeout_session_log: .claude/session_logs/2026-08-11_state-sync-race-refspec-phase-B.md
---

# Small Plan: 2026-08-09_phase-B-state-sync-race-and-refspec-hardening

## Scope

Stop the self-write race from creating orphan rebase state in the first place.
The logging hooks append to `session_logs/hooks-*.log` inside the repository
being synced, so the working tree can be re-dirtied between the caller's commit
and the start of the rebase. `--autostash` reacts to that by creating the
autostash commit and the `rebase-merge` directory before discovering the tree is
dirty again, which is what turns a transient failure into a latched one. This
phase re-runs Phase A's common active-rebase preflight immediately before it
commits local churn, then removes `--autostash` so any residual dirty-tree race
fails cleanly with no rebase directory created. It also idempotently re-pins
the nested remote's fetch and push refspecs. No pre-rebase checkpoint may stage
or commit an active operator rebase.

## Ownership

- `coder`: `shared/hooks/scripts/state-sync.sh`, `tests/test_state_sync.py`,
  `scripts/validate_targets.py`.
- `verifier`: full verification plus target generation, determinism, and the
  `state-sync.sh status` health probe.
- `reviewer`: the profiles listed below.
- `documenter`: skip for this phase; documentation lands in Phase E.

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

- [ ] In `reconcile_committed_state` in
      `shared/hooks/scripts/state-sync.sh` (modify), re-run Phase A's common
      mutating-entrypoint preflight immediately before `commit_local_state`,
      then call `commit_local_state` immediately before the pull. The second
      preflight is mandatory because active rebase state can appear after the
      entrypoint-level check. If it reports valid or unknown state, propagate
      the protected-state outcome through `reconcile_committed_state`, its
      caller, and top-level dispatch without `warn`, checkpointing, pull, push,
      or any persistent log write. Otherwise, `commit_local_state` remains
      idempotent: on a clean tree with an existing `HEAD` it commits nothing.
      This absorbs log churn written between the caller's own commit and the
      rebase without staging an active operator rebase.
- [ ] Remove `--autostash` from the pull invocation (modify), leaving
      `git -C "$CLAUDE_DIR" pull --rebase origin "$BRANCH"`. Add a comment
      recording why: `--autostash` writes the autostash commit and the
      `rebase-merge` directory before it discovers the tree is dirty again, so
      it converts a transient dirty-tree failure into a latched one; without it
      the same race fails cleanly with no rebase directory created and retries
      on the next sync.
- [ ] Add `ensure_pinned_refspecs()` (create). Idempotently sets
      `remote.origin.fetch` to `+refs/heads/$BRANCH:refs/remotes/origin/$BRANCH`
      and `remote.origin.push` to `refs/heads/$BRANCH:refs/heads/$BRANCH`, the
      same values `init_nested_repo` already writes. Call it from
      `reconcile_committed_state` before the fetch, and only when an `origin`
      remote exists.
- [ ] Comment `ensure_pinned_refspecs` with its real justification: a nested
      repository initialized before refspec pinning existed still carries the
      wildcard `+refs/heads/*:refs/remotes/origin/*`. Mark the link to the
      historical `Cannot rebase onto multiple branches` failures as an
      unverified assumption using an inline
      `# ASSUMPTION: ... needs empirical verification` comment. That error could
      not be reproduced; this re-pin is correct regardless of its cause.
- [ ] Must not change `cmd_publish`'s refusal to publish a dirty worktree. That
      check runs before `reconcile_committed_state` and keeps its current
      behavior, message, and return value. The new `commit_local_state` inside
      reconcile must not become a back door that publishes a dirty tree.
- [ ] Preserve Phase A's top-level dispatch contract. In particular, do not
      restore an unconditional `cmd_x || warn ...` for the protected-state
      outcome. Every public mode still exits 0, while valid or unknown active
      rebase state produces stderr-only guidance and no persistent warning.
- [ ] Add regression tests to `tests/test_state_sync.py` (modify), listed under
      Test Scenarios below.
- [ ] Add structural assertions to `scripts/validate_targets.py` (modify): the
      generated `state-sync.sh` must not contain `--autostash`, and its pull
      invocation must be the exact `pull --rebase origin` form. Assert the
      literal invocation, not loose substrings.
- [ ] Regenerate targets and refresh the dogfood install, then confirm the
      health probe.

## Test Scenarios

- [ ] `test_pull_absorbs_log_churn_without_creating_rebase_state`: after setup,
      append to `session_logs/hooks-errors.log` inside the nested repo to
      simulate a concurrent hook write, then run `pull`. Assert the pull
      succeeds, the churn is committed rather than stashed, and
      `.git/rebase-merge` does not exist at any point afterwards.
- [ ] `test_reconcile_repins_wildcard_fetch_refspec`: set `remote.origin.fetch`
      to `+refs/heads/*:refs/remotes/origin/*`, run `pull`, assert the refspec
      is restored to the single pinned form and `remote.origin.push` is intact.
- [ ] `test_dirty_tree_race_fails_without_leaving_rebase_state`: force the tree
      dirty at the moment of the rebase, assert the failure is warned, assert
      exit code 0, and assert no `.git/rebase-merge` directory was created.
- [ ] `test_pre_rebase_checkpoint_rechecks_active_rebase`: begin with no active
      rebase so the entrypoint preflight passes, then introduce a valid rebase
      before the new pre-rebase checkpoint boundary. Assert the second common
      preflight catches it; the public command exits 0 with empty stdout and
      stderr-only guidance; Git trace or an invocation side channel records no
      subsequent add, commit, pull, or push; and `HEAD`, index, worktree,
      rebase metadata, remote state, and persistent error log are unchanged.
- [ ] Regression, must pass unchanged:
      `test_publish_refuses_dirty_state_without_committing_or_publishing`,
      `test_push_after_rebase_conflict_does_not_push`,
      `test_reconciliation_after_conflict_can_push`,
      `test_two_writers_separate_files_reconcile_and_push`,
      `test_append_only_log_union_merges`,
      `test_checkpoint_commits_locally_without_remote_io`.

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
uv run python .claude/scripts/quality_score.py scripts/ --phase 2026-08-09_phase-B-state-sync-race-and-refspec-hardening --base-ref dev --json --out .claude/quality_reports/score-<timestamp>.json
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

- A residual race window still exists between the new `commit_local_state` and
  the rebase. Accepted and documented: without `--autostash` the residual case
  fails cleanly and transiently and retries on the next sync, instead of
  latching. Phase A's detection and recovery cover the case where it somehow
  still latches.
- An operator rebase can start after Phase A's entrypoint preflight but before
  Phase B's new `commit_local_state`. Mitigation: re-run the same common
  preflight immediately before staging and propagate its protected-state
  outcome without warnings or publication.
- Removing `--autostash` could regress a caller that depended on it. All three
  callers already guarantee a clean tree, and the existing publish-dirty test is
  listed as a required regression precisely to catch this.
- Re-pinning refspecs could fight a deliberate operator override.
  `AI_STATE_BRANCH` still parameterizes the branch, and the pin writes the same
  values `init_nested_repo` already writes, so it only repairs drift.
- The causal link between wildcard refspecs and the historical
  `Cannot rebase onto multiple branches` failures is unverified and is marked as
  an assumption in the code and here.

## Acceptance Criteria

- [ ] Concurrent log writes during a pull are committed, not stashed, and leave
      no rebase directory behind.
- [ ] The pre-rebase checkpoint runs only after the common preflight confirms
      no valid or unknown active rebase. A protected rebase is not staged,
      committed, reconciled, published, or persistently logged.
- [ ] `--autostash` no longer appears in either installed `state-sync.sh` copy.
- [ ] A wildcard fetch refspec is repaired to the single pinned refspec on the
      next sync.
- [ ] `cmd_publish` still refuses a dirty worktree with its existing behavior and
      message.
- [ ] Every state-sync entry point still exits 0 at the public script boundary;
      protected-state propagation never triggers a persistent fallback warning.
- [ ] Regeneration is deterministic and both installed copies stay
      byte-identical.

## Closeout Checklist

- [x] Verification passed
- [x] Review findings resolved
- [x] Score >= 90 persisted with branch/phase metadata
- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
