# Session: state-sync-durability SP1 — failure propagation + conflict policy

**Date:** 2026-07-22
**Plan:** [.claude/plans/2026-07-22_phase-1-state-sync-failure-propagation.md](../plans/2026-07-22_phase-1-state-sync-failure-propagation.md)
**Status:** COMPLETED

## Goal

Fix the two confirmed AI-state-sync defects reported from a consumer's Codex
session, in the `shared/` source: (1) `cmd_pull` returned success after
aborting a rebase conflict, so `cmd_push` attempted a doomed non-fast-forward
push; (2) no deterministic multi-writer conflict policy. SP1 covers the
`state-sync.sh` correctness + conflict policy + regression tests. The durable
commit-time checkpoint and the Stop/tab-closure documentation are SP2.

## Work Log

- Verified the report against the real code (context-mode + Semble + direct
  reads): confirmed the `cmd_pull` `return 0`-on-conflict and the unconditional
  `cmd_push` push. Corrected two report details — a VS Code "AI state: push"
  task already exists, and there is no `tests/tooling/test_state_sync.py` in
  the bootstrap (that is a consumer path; the durable home is `tests/`).
- `cmd_pull`: rebase-conflict path now `return 1`; legitimate no-op returns
  (local-only, no remote, no remote branch yet) stay `0`.
- `cmd_push`: guards the push behind `if ! cmd_pull; then warn; return 1; fi`.
  Top-level dispatch still converts a non-zero return into a non-blocking
  warning + `exit 0`, so hooks never block Codex shutdown.
- Added `write_nested_gitattributes()` (called from `init_nested_repo`):
  `session_logs/*.log` gets `merge=union`; `plans/**` and `MEMORY.md` keep the
  default conflict-and-abort path for manual semantic merge.
- Added `tests/test_state_sync.py`: 4 tests driving the real script against
  throwaway local repos (doomed-push averted, separate-file reconcile+push,
  post-conflict reconcile pushes, union-merge of append-only logs).
- Regenerated `dist/` so both consumer copies stay byte-identical.
- Review (reviewer agent, profiles code/security/tests/ponytail): PASS with one
  MINOR (test env did not pin `AI_STATE_LOCAL_ONLY`) — fixed. Documented the
  push-contract + conflict-policy changes; deferred `cmd_migrate`'s identical
  doomed-push shape to a follow-up (harmless today: git rejects the non-ff push).

## [LEARN] Entries

- [LEARN:quality] The commit gate's `content_hash` is `git hash-object` of
  `git diff <base>`, which excludes untracked files. Stage every file destined
  for the commit BEFORE running `quality_score.py`/`record_findings.py`, or the
  report's hash and `changed_files` won't match what the gate recomputes at
  commit time (and `dirty` will be `true`, which the gate rejects).
- [LEARN:domain] `cmd_migrate` in `state-sync.sh` has the same reconcile-then-
  unconditional-push shape SP1 fixed in `cmd_push`; harmless today only because
  a bare `git push` is rejected non-fast-forward. Left out of SP1's scope on
  purpose; candidate follow-up.

## Verification Results

```bash
uv run pytest tests/ -q            # 5 passed
uv run ruff check tests/           # All checks passed
uv run python scripts/validate_targets.py   # PASS (dist regenerated)
# score-20260722T083410Z.json: score 100, dirty false, tests_passed true
# findings-20260722T083359Z.json: 0 critical/major/minor, ponytail_reviewed true, ponytail_findings 0
```

## Score: 100/100

## Open Questions / Next Steps

- SP2: `post-commit` durable checkpoint hook, generator/validate wiring, VS
  Code task clarification, and the Stop/tab-closure documentation corrections.
- Follow-up candidate: apply the same push-guard to `cmd_migrate`.
