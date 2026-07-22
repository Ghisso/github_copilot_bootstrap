---
name: 2026-07-22_phase-1-state-sync-failure-propagation
type: small-plan
parent_plan: state-sync-durability
phase_index: 1
status: complete
closeout_session_log: .claude/session_logs/2026-07-22_state-sync-durability-sp1.md
---

# Small Plan: 2026-07-22_phase-1-state-sync-failure-propagation

## Scope

Correct failure propagation in `shared/hooks/scripts/state-sync.sh` and add the
deterministic multi-writer conflict policy. Add bash-driven regression tests.
Source-only edits; both consumer copies regenerate from the single `shared/`
source, so byte-identity is preserved structurally.

## Steps

- [ ] `cmd_pull`: on the rebase-conflict path, `return 1` instead of `return 0`.
      Keep the no-op returns (local-only, no remote, no remote branch yet) at `0`.
- [ ] `cmd_push`: after `commit_local_state`, guard the push:
      `if ! cmd_pull; then warn "...reconciliation required..."; return 1; fi`.
      No push attempt when reconciliation failed.
- [ ] Preserve every guarantee: commit-before-remote, clean `rebase --abort`,
      no discarded commits, no force-push, nested repo left outside an active
      rebase/merge, clear conflicting-filenames + recovery message.
- [ ] Add nested `.gitattributes` (written at repo init) giving append-only
      logs `merge=union`; `plans/**` and `MEMORY.md` keep default conflict.
- [ ] Add `tests/test_state_sync.py`: pull returns non-zero after a rebase
      conflict (local state intact, no rebase/merge active, both commits
      reachable); push does not push after failed reconciliation; a later
      reconcile pushes cleanly; two writers on separate files reconcile and
      push; union-merge auto-resolves an append-only log conflict.

## Verification

```bash
uv run pytest tests/ -q --tb=short
uv run ruff check tests/
uv run python scripts/validate_targets.py
```

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved (incl. ponytail)
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
