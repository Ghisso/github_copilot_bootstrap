# Session: state-sync-durability SP2 — durable checkpoint + docs

**Date:** 2026-07-22
**Plan:** [.claude/plans/2026-07-22_phase-2-durable-checkpoint-and-docs.md](../plans/2026-07-22_phase-2-durable-checkpoint-and-docs.md)
**Status:** COMPLETED

## Goal

Make AI-state durability independent of the Codex/Claude `Stop` event (tab
closure does not guarantee Stop), and correct the docs that overstate `Stop`.

## Work Log

- Added `shared/hooks/git-hooks/post-commit`: best-effort `state-sync.sh push`
  after every successful outer commit; stdin from `/dev/null`; never fails a
  commit (git ignores the hook's exit status; state-sync is warn-never-fail).
  Auto-installed via the existing `copy_tree` + `chmod` + `core.hooksPath`
  wiring — no `install_bootstrap.py` change.
- `scripts/validate_targets.py`: added `post-commit` to `REQUIRED_GIT_HOOKS`; a
  content check that the generated hook pushes via `state-sync.sh`; and a check
  that the two generated `state-sync.sh` copies are byte-identical.
- Review (reviewer agent, code/architecture/security/tests/ponytail): confirmed
  the no-recursion reasoning and non-blocking design, then found 2 MAJOR issues
  in the validator additions — an unguarded `read()` that would crash on a
  missing hook, and a falsely-passable substring check (`"push"` also occurs in
  the `cmd_push` comment). Both fixed (guard the read; assert the literal
  `'"$STATE_SYNC" push'` invocation) and re-verified clean by the reviewer.
- Documented the checkpoint + Stop-is-best-effort / tab-closure caveat in
  `shared/policies/workflow.instructions.md`, `README.md`, `docs/architecture.md`,
  and `docs/smoke-tests.md`. Regenerated `dist/`; full validator + suite green.

## [LEARN] Entries

- [LEARN:quality] Validator/structural checks over generated text must assert
  the literal invocation form (e.g. `'"$STATE_SYNC" push'`), not loose
  independent substrings — a stray word in a comment (`cmd_push`) can otherwise
  satisfy the check and hide a real regression. Guard any unconditional
  `read()` of a required-but-possibly-missing file so a missing file yields a
  clean accumulated failure instead of an uncaught exception that aborts the
  rest of the suite.

## Verification Results

```bash
uv run python scripts/generate_targets.py --all
uv run pytest tests/ -q            # 5 passed
uv run ruff check scripts/ tests/  # All checks passed
uv run python scripts/validate_targets.py   # PASS (post-commit + byte-identical checks)
# score-20260722T085358Z.json: score 100, dirty false, tests_passed true
# findings-20260722T085358Z.json: 0 critical/major/minor, ponytail_reviewed true, ponytail_findings 0
```

## Score: 100/100

## Open Questions / Next Steps

- Big plan `state-sync-durability` complete after this commit. Open a PR to
  `dev` only when the user asks.
- Follow-up candidate (unchanged from SP1): apply the same push-guard to
  `cmd_migrate`; refresh the repo-root self-install `.devcontainer/state-sync.sh`
  dogfood copy at the next self-install cadence.
