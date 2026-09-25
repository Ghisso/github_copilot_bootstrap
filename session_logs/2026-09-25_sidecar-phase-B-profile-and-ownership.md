# Session: Sidecar Phase B — profile and ownership

**Date:** 2026-09-25
**Plan:** `.claude/plans/2026-09-24_phase-B-sidecar-profile-and-ownership.md`
**Status:** IN-PROGRESS

## Goal

Generate `dist/sidecar/` with license notices, validate that it is
self-contained, and build the pure reconciliation planner with its tests.
No consumer repository and no installer CLI change in this phase.

## Work Log

- Phase B activated by the Phase A completion commit `0f490a9` (pushed to
  `origin/consumer-sidecar-bootstrap-overlay_implementation`).
- Material-impact check: the Phase A outcome (two bridges, no Antigravity
  bridge) is already noted in this plan's step 2; no planner revision.
- Conflict found and resolved by the orchestrator: Decision 3 puts the
  sidecar constants in `scripts/runtime_ownership.py`, but the generator
  copies that file byte-for-byte to
  `dist/multi-agent/.claude/scripts/runtime_ownership.py`
  (`scripts/generate_targets.py:305`), and step 2 says `dist/multi-agent/`
  must not change. Resolution: that copied module is the one allowed
  difference (data-only constants); every rendered file stays identical.
  This keeps Decision 3's single ownership contract.
- `dist/` is not tracked by Git (0 tracked files), so generated output is
  never part of a commit.
- Step 1 done by the orchestrator so that steps 2-4 and 5-6 could run in
  parallel without a race: `FULL_INSTALL_ROOT_PATHS`, `SIDECAR_SKILLS`,
  `SIDECAR_SKILL_WRITE_ROOTS`, `SIDECAR_SKILL_READ_ROOTS`, `SIDECAR_BRIDGES`
  (path -> frontmatter; two entries), `SIDECAR_MANIFEST_NAME`,
  `SIDECAR_STAGING_NAME`, `SIDECAR_EXCLUDE_BEGIN`, `SIDECAR_EXCLUDE_END`.
  Values come from the contract's Step 4 frozen lists. Ruff check and
  format pass.
- Steps 2-4 (generator target, bridge body, validator) delegated to one
  `coder`; steps 5-6 (pure planner and tests) delegated to a second
  `coder`, with disjoint file ownership.
- Steps 2-4 result: `TARGETS = ("multi-agent", "sidecar")`,
  `render_sidecar()`, `SIDECAR_TEXT_REPLACEMENTS` (three rewrites) and
  `SIDECAR_HUMANIZE_CREDIT` in `scripts/generate_targets.py`;
  `shared/sidecar/bridge.md`; sidecar and `FULL_INSTALL_ROOT_PATHS`
  coverage checks with `*_cases` self-tests in `scripts/validate_targets.py`
  (each of 10 rules proven by stubbing it). `dist/sidecar/` has exactly 14
  files. `diff -r` of `dist/multi-agent/` before and after the generator
  change: identical. Every real `dist/multi-agent/` path is covered by
  `FULL_INSTALL_ROOT_PATHS`. `validate_targets.py` keeps its own
  `TARGETS = ("multi-agent",)` on purpose, because its support-file checks
  assume the full-install shape.
- Steps 5-6 result: `scripts/sidecar_overlay.py` (pure planner, desired-unit
  reader) and `tests/test_sidecar_overlay.py` (45 tests, including a real
  `git check-ignore --stdin -z` check of escaping). Interpretation calls
  sent to review: team takeover reuses the team-owned remedy; bridge
  takeover wording; idempotency means no action besides `unchanged`;
  `next_manifest` is the post-apply manifest.
- Orchestrator verification on the combined tree: generate PASS; validate
  PASS; `test_sidecar_overlay.py` + `test_validate_targets.py` 205 passed;
  `test_install_bootstrap.py` 52 passed; `verify.py fast` PASS.
- Review started with `code`, `architecture`, `security`, `tests`,
  `ponytail`.
- Full `verify.py phase` (not persisted) on the pre-review tree: PASS
  (ruff 0, mypy 0, pytest 1804 passed, generated runtime matches source).
- Review round 1: gate FAIL, 0 critical, 2 major, 2 minor. The reviewer
  accepted interpretation calls 1, 3, and 4 and turned call 2 into a minor.
  - MAJOR: a skill taken only in a read-only folder is skipped with no
    report (Decision 8 says "skipped and reported").
  - MAJOR: the anti-shadow `update` -> `remove` conversion has no test.
  - MINOR: the bridge wording of the team-owned remedy has no test.
  - MINOR (ponytail): `retained` stores hashes that no decision reads.
  All four sent back to the planner coder to fix.

## [LEARN] Entries

- [LEARN:architecture] `scripts/runtime_ownership.py` is copied
  byte-for-byte to `dist/multi-agent/.claude/scripts/runtime_ownership.py`,
  so every constant added there ships to every full consumer. A check that
  `dist/multi-agent/` is unchanged must allow that one file.
- [LEARN:workflow] Two coders can work in parallel in one worktree when the
  orchestrator first lands the shared constants they both import, gives
  each coder disjoint files, and tells each to run `ruff format` only on
  its own files.
- [LEARN:testing] Assert on the report output, not only on the actions. A
  skill skipped because of a folder that no unit snapshot covers produced
  the right actions and no report; only a `result.reports` assertion
  catches that.

## Verification

Pending.

## Open Questions / Next Steps

- Integrate both coders' results, run the Phase B verification block, then
  review with `code`, `architecture`, `security`, `tests`, `ponytail`.
