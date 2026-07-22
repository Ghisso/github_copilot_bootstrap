---
name: 2026-07-22_phase-3-migrate-push-guard
type: small-plan
parent_plan: state-sync-durability
phase_index: 3
status: complete
closeout_session_log: .claude/session_logs/2026-07-22_state-sync-durability-sp3.md
---

# Small Plan: 2026-07-22_phase-3-migrate-push-guard

## Scope

Close the twin of the SP1 doomed-push bug in `cmd_migrate`: it calls
`commit_and_reconcile` (which aborts a conflicting merge but returned success)
and then pushes unconditionally, so an aborted reconciliation produced a
doomed non-fast-forward push with a misleading "network/auth" warning. Apply
the same guard SP1 applied to `cmd_push`.

## Steps

- [ ] `commit_and_reconcile`: return non-zero when it aborts a conflicting
      merge; return 0 on all success/no-op paths. `cmd_setup` (which does not
      push) keeps ignoring the result, so its behavior is unchanged.
- [ ] `cmd_migrate`: guard the push on `commit_and_reconcile` succeeding; on
      failure, warn clearly (conflict, not network) and skip the push. Preserve
      the existing network-failure warning for the push-attempted path.
- [ ] Extend `tests/test_state_sync.py`: a conflicting migrate commits locally
      but does not push (remote unchanged, no active merge, local reachable);
      a non-conflicting migrate (separate files) reconciles and pushes.
- [ ] DOCUMENT (deferred): correct the `migrate` bullet in `docs/architecture.md`
      ("commits everything ... and pushes") to note the push is skipped when
      reconciliation conflicts.

## Verification

```bash
uv run pytest tests/ -q --tb=short
uv run ruff check tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
```

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved (incl. ponytail)
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
