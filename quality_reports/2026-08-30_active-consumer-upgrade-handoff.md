# Active Consumer Upgrade Safety Handoff

## Decision

Do not deploy commit `1fce3fe` broadly yet.

A direct old-to-new consumer simulation showed that the installer preserves an
active plan and dirty nested state. The audit still found three MAJOR gaps that
must be resolved before broad rollout.

## Verified Behavior

The audit refreshed a temporary consumer from the bootstrap at `ca51bbc` to the
current branch at `1fce3fe` while an implementation plan was active.

The refresh preserved these bytes exactly:

- active big plan;
- active small plan;
- schema-v2 receipt;
- session log;
- `.claude/MEMORY.md`.

A dirty active-small-plan edit was checkpointed before generated runtime files
were replaced. The nested `.claude` repository ended with a valid HEAD and a
clean worktree. The installed verifier reported schema v3.

After the refresh:

- report, log, and memory checkpoints did not stale control-plane provenance;
- active-plan mutations did stale provenance;
- arbitrary in-progress big-plan changes did not qualify for the terminal
  transition exception;
- schema-v3 phase verification, closeout, and the native commit gate passed
  after nested state was checkpointed before `verify phase`;
- schema-v2 receipts remained on disk but failed closed under schema v3.

Local-only installer coverage also confirms that no `fetch`, `ls-remote`,
`pull`, `merge`, or `push` command runs during `--local-only` refreshes.

## MAJOR 1: Live Root Adapters Are Not Bound to Provenance

### Location

- `shared/scripts/verify.py`, near `control_plane_provenance()`
- `shared/scripts/verify.py`, near `nested_runtime_paths()`
- installer ownership/runtime manifest helpers under `scripts/`

### Root cause

`control_plane_provenance()` hashes governing files below `.claude`, including
the `.claude/bootstrap-root` mirror. It does not hash or compare the live root
adapters that consumers actually use.

Affected live surfaces include at least:

- `.codex/hooks.json`;
- `.agents/`;
- `.mcp.json`;
- `.vscode/mcp.json`;
- `AGENTS.md`;
- `CLAUDE.md`;
- other root adapters restored from `.claude/bootstrap-root` according to the
  existing ownership manifest.

Many generated consumer adapters are ignored by the outer Git repository.
Therefore, the outer `content_hash` does not reliably bind them either.

### Reproduction

1. Install the generated bootstrap into a consumer.
2. Record `control_plane_provenance()`.
3. Modify live `.codex/hooks.json` without changing
   `.claude/bootstrap-root/.codex/hooks.json`.
4. Recompute provenance.

Observed result:

- outer `content_hash` is unchanged;
- `control_plane_provenance_matches()` returns `True`;
- the live runtime differs from the bound mirror.

### Risk

A consumer can execute different hook, agent, MCP, or instruction bytes from
the bytes certified by the receipt. This is a provenance gap, even if the
installer normally keeps both copies aligned.

### Required fix

Reuse the existing runtime ownership manifest. Do not create a second adapter
inventory.

Choose the smallest fail-closed design that binds every live generated adapter:

1. Resolve the existing owned live adapter paths from the manifest.
2. For each adapter, verify file type, mode, symlink identity, path, and bytes.
3. Either hash the live adapter directly or verify it equals its
   `.claude/bootstrap-root` mirror and bind that equality into the canonical
   runtime fingerprint.
4. Treat missing, unreadable, mismatched, or partially discovered required
   adapters as unavailable provenance, never PASS.
5. Preserve consumer-owned mutable state and intentionally retained authoring
   adapters according to the existing ownership rules.
6. Keep the push hook bounded; use the manifest rather than recursive root
   discovery.

### Required tests

- Every owned live adapter matches its mirror in a clean generated consumer.
- Mutating each adapter family stales provenance:
  `.codex/hooks.json`, `.agents/`, `.mcp.json`, `.vscode/mcp.json`, `AGENTS.md`,
  and `CLAUDE.md` where installed.
- A missing required live adapter fails closed.
- A live/mirror file-type or symlink mismatch fails closed.
- Consumer-owned mutable state does not enter this fingerprint.
- Generated-source, installed-runtime, and ownership-manifest parity remains
  validated.

### Acceptance criteria

- No live generated adapter can differ from the bound runtime while
  `control_plane_provenance_matches()` returns `True`.
- The implementation uses the existing ownership manifest as the source of
  truth.
- Hook cost remains bounded by the finite manifest.

## MAJOR 2: Terminal Exception Accepts an In-Progress Small Plan

### Location

- `shared/scripts/verify.py`, near
  `terminal_control_plane_provenance_matches()`
- `has_only_terminal_big_plan_change()`
- `has_only_checkpointed_terminal_big_plan_change()`

### Root cause

The terminal exception validates the exact big-plan byte transition from:

```text
status: in-progress
current_phase: <phase>
```

to:

```text
status: complete
current_phase:
```

It also checks later phases are cancelled. It does not independently require
the receipt's current small plan to be `complete`.

The Bash commit and push lifecycle checks currently reject an in-progress
small plan, so this is not a demonstrated hook bypass. The provider-neutral
Python provenance exception is still semantically incomplete and unsafe to
reuse on its own.

### Reproduction

1. Create a recorded big plan with one current phase.
2. Leave that small plan at `status: in-progress`.
3. Apply only the accepted terminal big-plan transition.
4. Call `terminal_control_plane_provenance_matches()`.

Observed result: the terminal exception returns `True`.

### Required fix

Add one shared small-plan terminal validator and use it in both terminal paths.

The exception must require:

- the current phase exists in the recorded big plan's `phases:` list;
- the current small-plan bytes at the receipt's recorded nested HEAD are
  `status: complete`;
- the current indexed/worktree small-plan bytes remain identical to the
  recorded authoritative bytes, apart from evidence roots already excluded by
  design;
- every later phase is fully evidenced as `cancelled`;
- the big-plan change is still exactly the automatic status/current-phase
  transition;
- no other relevant nested dirty/index or checkpointed change exists.

Do not rely only on the surrounding Bash gate. The Python exception must be
correct in isolation.

### Required tests

Cover both the unstaged and clean-checkpoint terminal paths:

- current small plan `complete` -> terminal transition allowed;
- current small plan `in-progress` -> denied;
- current small plan `paused` -> denied;
- current small plan `cancelled` -> denied as the committing current phase;
- current small plan missing/unreadable/malformed -> denied;
- small-plan index-only mutation -> denied;
- small-plan worktree mutation -> denied;
- checkpointed small-plan mutation after the receipt -> denied;
- exact terminal big-plan transition with completed current phase and only
  cancelled later phases -> allowed.

### Acceptance criteria

- The terminal exception cannot return `True` unless the recorded current small
  plan is complete and unchanged.
- Both terminal paths enforce the same small-plan semantics.
- Existing arbitrary-plan, runtime, index-only, and dirty-state negatives stay
  green.

## MAJOR 3: Missing Old-to-New Active-Plan Upgrade Regression

### Location

- `tests/test_install_bootstrap.py`
- optionally shared fixture helpers used by `scripts/validate_targets.py`

### Root cause

Existing tests prove these behaviors separately:

- generated consumer lifecycle from a fresh install;
- preservation of consumer-state directories during refresh;
- schema-v3 provenance and tamper rejection;
- local-only state-sync postconditions.

No committed test combines them into the upgrade path users will run: an older
consumer with an active plan and schema-v2 evidence refreshed to the schema-v3
runtime.

The temporary audit simulation passed, but it is not durable regression
coverage.

### Required integration test

Use one deterministic consumer. Do not add a layout matrix.

1. Generate or install the old bootstrap from commit `ca51bbc`, or use a
   checked-in minimal legacy fixture containing the exact schema-v2 runtime
   contract needed by the test.
2. Create an outer Git repository on `<plan>_implementation` with application
   changes in progress.
3. Create nested `.claude` Git state containing:
   - an `in-progress` big plan;
   - an active small plan;
   - a dirty small-plan edit not yet checkpointed;
   - session log and memory;
   - schema-v2 phase/closeout evidence.
4. Run the supported generated installer/update path with `--local-only`.
5. Assert before/after bytes for big plan, small plan, dirty edit, log, memory,
   and old receipts.
6. Assert the nested repository has a valid HEAD and clean worktree after the
   installer checkpoints state.
7. Assert the installed verifier is schema v3 and generated-runtime validation
   passes.
8. Assert old schema-v2 receipts are preserved but rejected fail closed.
9. Checkpoint any active-plan state before authoritative verification.
10. Run installed `verify fast` and `verify phase --persist`.
11. Create deterministic score/findings/documentation/LEARN/session evidence
    through repository-supported formats.
12. Run installed `verify closeout --persist`.
13. Exercise the native commit gate.
14. Complete the plan through the real post-commit transition.
15. Exercise the native pre-push gate in both supported states:
    - immediate terminal worktree transition;
    - clean nested checkpoint after the terminal transition.
16. Assert arbitrary live-adapter, plan, runtime, receipt, index-only, and dirty
    mutations remain denied.

Avoid network dependence by generating both source versions locally. If the
test must use historical bytes, bind the fixture to an explicit version/hash so
it cannot silently drift.

### Acceptance criteria

- The committed test fails against the pre-fix upgrade behavior where relevant.
- An active consumer loses no plan or evidence bytes during refresh.
- Schema-v2 evidence is preserved but cannot authorize schema-v3 gates.
- Regenerated schema-v3 evidence reaches native commit and pre-push allow.
- Local-only refresh performs no remote Git command.

## Compatibility Contract for Consumers Already Mid-Plan

The update procedure must state this explicitly:

1. Do not reuse schema-v2 phase or closeout receipts after upgrading.
2. Run the supported installer/update path with `--local-only` for the local
   refresh.
3. Confirm nested state is durable before verification:

   ```bash
   git -C .claude status --short --branch
   ```

   It must have a valid HEAD and a clean worktree. If it is not clean, stop and
   diagnose the installer/state-sync result; do not continue to verification.

4. Regenerate evidence with the installed schema-v3 verifier:

   ```bash
   uv run python .claude/scripts/verify.py fast --format json
   uv run python .claude/scripts/verify.py phase --format json --persist
   ```

5. Regenerate score, findings, documentation applicability, LEARN, and completed
   session evidence through the normal lifecycle.
6. Run:

   ```bash
   uv run python .claude/scripts/verify.py closeout --format json --persist
   ```

7. Commit and push only after the native gates pass.

If nested state changes after `verify phase` for any governing runtime or active
plan reason, rerun phase verification. Evidence-only report/log/memory
checkpoints should not stale the receipt.

## Verification Gate Before Broad Deployment

Run at minimum:

```bash
uv run pytest tests/ -q --tb=short
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```

Then run the committed old-to-new active-plan integration test independently.

Deployment gate:

- zero CRITICAL findings;
- zero MAJOR findings;
- full generated/install/runtime validation passes;
- active-plan upgrade integration passes without network;
- native commit and pre-push allow/deny cases pass through installed artifacts.

## Agent Implementation Order

1. Bind live root adapters using the existing ownership manifest.
2. Make the terminal exception require a complete, unchanged current small plan.
3. Add the old-to-new active-plan upgrade integration test.
4. Regenerate installed targets.
5. Run full verification and two-pass security/architecture/tests/Ponytail review.
6. Do not publish or recommend broad consumer rollout until all MAJOR findings
   are closed.
