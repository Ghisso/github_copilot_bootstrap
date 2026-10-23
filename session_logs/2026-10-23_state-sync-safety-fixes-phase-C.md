# Session: Restorer symlink checks and devcontainer mount folders

**Date:** 2026-10-23
**Plan:** `.claude/plans/2026-10-23_phase-C-restorer-and-devcontainer-hardening.md`
**Status:** IN-PROGRESS

## Goal

Make `restore-root-adapters.sh` refuse a symlinked `.claude` or `.claude/bootstrap-root` (defense in depth), and have the generated `devcontainer.json` create both bind-mount source folders on the host before the container starts.

## Work Log

- Phase B committed as `cedb3b0` and pushed; the post-commit hook advanced `current_phase` to this phase.
- This repository's own `.devcontainer/` is untracked (`.git/info/exclude`) and byte-identical to the generated copy, so the overlay refresh updates it without touching the outer diff.
- Coder implemented steps 1-3 with no deviations: two one-line symlink refusals after `fail()` (the early `exit 0` stays first), the list-form `initializeCommand`, one inline validator check, and three tests plus a `_restore_from_devcontainer` helper. Negative controls: on the `HEAD` restorer both rejection tests failed (exit 0 instead of 1) and a scratch reproduction showed the old script copying an outside `CLAUDE.md` into the root; removing `initializeCommand` failed `validate_targets.py`. Coder checks: 367 passed across the three test files; `validate_targets.py` PASS; ruff clean.
- I wrote the step 4 docs myself (three small edits): the README devcontainer bullet no longer asks for a hand-made `~/.openwiki`; `docs/runtime-checks.md` describes the `initializeCommand` and the restorer's symlink refusal; `docs/smoke-tests.md` gained one Expected bullet.
- Regenerated and refreshed the overlay; the full required check set and the review are running.

## [LEARN] Entries

## Verification

## Open Questions / Next Steps

- Implement steps 1-3 (coder), then documentation (documenter), then review.
