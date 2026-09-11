# Session: Outer-repository automatic push

**Date:** 2026-09-11
**Plan:** `.claude/plans/2026-09-11_phase-A-outer-repo-auto-push.md`
**Status:** IN-PROGRESS

## Goal

Make the orchestrator publish successful outer-repository commits by default
when a normal remote push is available, without changing nested `.claude`
`ai-state` publication or automatic PR/merge behavior.

## Work Log

- Plan approved and implementation branch created.
- Confirmed that completed-phase receipts must become historical records after
  the post-commit transition; later phases must not stale their certified state.
- Added the `PUSH` lifecycle stage to shared orchestrator and workflow
  guidance, generated root guidance, and consumer-target validation. The
  intended command is a normal non-force outer-repository push using the
  branch upstream or `origin`, with `GIT_TERMINAL_PROMPT=0`.
- Added the completed-phase publication path. It permits only the exact,
  non-merge completion commit directly certified by the prior phase's receipt
  and findings after `post-commit` advances to the next in-progress phase.
  Paused checkpoints, terminal closeout, nested `.claude` state sync, PRs,
  and merges retain their separate behavior.
- Added local-bare-remote coverage for Phase A publication, agent-facing
  `HEAD` resolution, receipt/artifact tampering, bypass acknowledgement,
  arbitrary Phase B work, stale completion evidence, and Phase B final push.
- Updated README and architecture, runtime-check, and smoke-test docs to
  distinguish outer code publication from nested `ai-state` publication.
- Regenerated targets and completed local-only self-install. The nested state
  repository is locally ahead; no outer or nested remote push was attempted.

## [LEARN] Entries

- [LEARN:workflow] A post-commit phase transition means an intermediate push
  must validate the prior receipt against the exact completion commit, not the
  newly current plan state. The `HEAD` form used by PreToolUse must be resolved
  to a commit SHA before direct-parent validation.

## Verification Results

```bash
uv run python scripts/validate_plan_frontmatter.py \
  .claude/plans/2026-09-11_outer-repo-auto-push.md \
  .claude/plans/2026-09-11_phase-A-outer-repo-auto-push.md
```

Plan frontmatter passed before branch creation.

The following passed before the final review correction:

```text
generate_targets.py --all
install_bootstrap.py . --allow-self --local-only
verify.py fast
check_runtime.py
bash -n shared/hooks/scripts/_lib-frontmatter.sh
ruff check / ruff format --check / git diff --check
focused pytest (3 tests)
local-bare-remote lifecycle validators
```

`uv run python scripts/validate_targets.py` exposed one remaining dispatch
regression: `assert_push_invariants` sends every in-progress big plan to the
new intermediate route. It must select that route only when the current small
plan is in progress *and* has a completed predecessor; first-phase and
current-complete in-progress fixtures must retain strict closeout behavior.
The initial full pytest run similarly reported 399 passed and 1 failed from
that validator assertion. Do not mark this phase complete until the dispatch
is narrowed, the full validators pass, and the required final review and
receipt ceremony are complete.

## Open Questions / Next Steps

1. Narrow `assert_push_invariants` dispatch as described above, then rerun the
   local-bare-remote lifecycle validator and `uv run python scripts/validate_targets.py`.
2. Rerun the focused three-file pytest suite and `verify.py fast` after the
   correction.
3. Complete code/architecture/security/tests/Ponytail/documentation review,
   address findings, then perform normal closeout and commit ceremony.
