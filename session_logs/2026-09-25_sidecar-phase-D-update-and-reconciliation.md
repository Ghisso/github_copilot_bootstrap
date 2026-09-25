# Session: Sidecar Phase D — update and reconciliation

**Date:** 2026-09-25
**Plan:** `.claude/plans/2026-09-24_phase-D-sidecar-update-and-reconciliation.md`
**Status:** IN-PROGRESS

## Goal

Make batch updates skip and report a failed target (Decision 20), prove
sidecar updates across bootstrap versions and in mixed batches, and
document full and sidecar installation.

## Work Log

- Phase D activated by the Phase C completion commit `4ad6b9c` (pushed).
- Material-impact check: Phase C kept one reconciliation path for install
  and update, as this phase assumes; the fresh-clone refusal found in
  Phase C is already noted in step 4. No planner revision.
- Steps 1-3 (updater skip-and-report, option forwarding, upgrade suite)
  delegated to `coder`; step 4 (README, `docs/target-mapping.md`,
  `docs/architecture.md`) delegated to `documenter` in parallel, with
  disjoint files.
- Documenter result: README split into Full Install, Personal Sidecar
  Install, "What a full install changes in a team repository", "Behavior
  changes you should know about", Updating Existing Repos (batch
  skip-and-report), Updating Full Consumers, Updating Sidecar Consumers;
  `docs/target-mapping.md` gains the Sidecar Overlay projection table and a
  contract link; `docs/architecture.md` describes `dist/sidecar/` and the
  sidecar's Ponytail skills with their license. Corrected the stale "What
  Is Included" bullet that named only `dist/multi-agent/`.
  `validate_targets.py` PASS.
- Coder result: `update_consumers.py` keeps `run()` (generator, still
  stops the batch) and adds `run_target()`; failures are collected and
  printed as `FAILED: <path> (exit <code>)`, then exit 1; the final
  "All projects updated." / "Preview complete; no projects were updated."
  banner prints only when every target succeeded. `tests/test_sidecar_update.py`:
  the 15 cases, option forwarding, and a not-a-directory case (17 tests);
  batch tests run `update_consumers.py --skip-regen` against real `dist/`
  output. No change to `sidecar_overlay.py` or `validate_targets.py` was
  needed. Coder-reported: 176 tests pass across the four sidecar/installer
  test files.
- Review started with `code`, `architecture`, `security`, `tests`,
  `ponytail`, `documentation`, while the full phase verifier runs.
- Full `verify.py phase` before review fixes: PASS (pytest 1883 passed;
  ruff 0; mypy 0); `validate_targets.py` PASS; Phase D block 176 passed.
- Review round 1: gate PASS, 0 critical, 0 major, 3 minor. The reviewer
  confirmed the updater's batch handling, the 15 cases plus option
  forwarding, and every documented claim against the code.
  - MINOR (documentation): the README's SKIPPED remedy did not cover a
    skill name taken in a read-only folder.
  - MINOR (documentation): the manual-removal procedure and two other
    README sentences were long run-on sentences.
  - MINOR (ponytail): `tests/test_sidecar_update.py` copied eight helpers
    from `tests/test_sidecar_install.py`.
  All three are being fixed: the documenter takes the two README items,
  and the coder moves the shared helpers into one test helper module.

## [LEARN] Entries

Pending.

## Verification

Pending.

## Open Questions / Next Steps

- Integrate, verify, and review with `code`, `architecture`, `security`,
  `tests`, `ponytail`, `documentation`.
