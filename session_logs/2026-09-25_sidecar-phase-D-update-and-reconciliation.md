# Session: Sidecar Phase D — update and reconciliation

**Date:** 2026-09-25
**Plan:** `.claude/plans/2026-09-24_phase-D-sidecar-update-and-reconciliation.md`
**Status:** COMPLETED

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
- Fixes: the SKIPPED row is split into three rows with a Cause column,
  each remedy matching its function in `scripts/sidecar_overlay.py`;
  manual removal is a numbered list; two long sentences are split; the
  eight shared helpers live in `tests/sidecar_test_helpers.py`, imported by
  both sidecar test files. 176 tests pass; validator PASS.
- Review round 2 (fix delta): all three resolved, no new finding, gate
  PASS. The findings report lists surviving findings only, so it is
  empty; the three fixed findings are recorded here.

## [LEARN] Entries

- [LEARN:workflow] A coder and a documenter can run the same phase in
  parallel when the plan fixes the behavior exactly. Tell the documenter to
  describe the coder's behavior without quoting output strings that do not
  exist yet, and to take exact strings only from committed code.

## Verification

Required items (`verify closeout --format text` summary lines):

```text
PASS        0.5s  uv run python scripts/generate_targets.py --all
PASS       54.9s  uv run python scripts/validate_targets.py
PASS       47.4s  uv run pytest tests/test_sidecar_overlay.py tests/test_sidecar_install.py tests/test_sidecar_update.py tests/test_install_bootstrap.py -q --tb=short
PASS        0.3s  uv run python .claude/scripts/verify.py fast --format json
```

`verify.py phase --format json --persist`: PASS (full suite 1883 passed in
the run just before). Findings report:
`.claude/quality_reports/findings-2026-09-24_phase-D-sidecar-update-and-reconciliation.json`
(surviving findings only: 0 critical, 0 major, 0 minor;
`ponytail_reviewed=true`).

- optional 1: NOT RUN — no clone of a real team repository with configuration for all four clients is available in this session. Partial substitute by the orchestrator, 2026-09-25: `update_consumers.py --skip-regen` on the Phase C sidecar clone (tracked `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`, team skills in three folders) detected sidecar mode, reported `unchanged 10` and `All projects updated.`; `git status --porcelain --untracked-files=all` empty before and after; `info/exclude` and manifest SHA-256 identical before and after. The four-client batch behavior is covered by `tests/test_sidecar_update.py`.

## Documentation

Updated in this phase: `README.md` (four install and update parts, the
team-repository use case, the takeover description, behavior changes,
limits, client support, SKIPPED/RETAINED remedies, manual removal),
`docs/target-mapping.md` (Sidecar Overlay projection table),
`docs/architecture.md` (`dist/sidecar/`, sidecar Ponytail license).

## Open Questions / Next Steps

- Next: Phase E (`2026-09-24_phase-E-sidecar-knowledge-refresh`): OpenWiki
  refresh through its MCP tools, then the final stale-claims audit.
