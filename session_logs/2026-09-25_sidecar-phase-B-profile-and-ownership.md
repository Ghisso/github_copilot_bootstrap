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
- Fixes (only `scripts/sidecar_overlay.py` and `tests/test_sidecar_overlay.py`
  changed): a second anti-shadow pass emits one SKIPPED report
  ("the repository has `<folder>/<skill>`; the sidecar skips `<skill>` at
  every root") for a skill taken only in a read-only folder, with no
  duplicate when a write-root unit already reports; new tests for the
  `update` -> `remove` conversion, the no-duplicate case, and the bridge
  remedy; `Manifest.retained` is now a set of paths (sorted JSON list).
  48 planner tests pass; the coder proved three new tests fail when their
  rules are broken.
- Review round 2 (same reviewer, fix delta only): gate PASS; all four
  findings resolved; no new findings. All four recorded with disposition
  `fixed`.

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

Required items (`verify closeout --format text` summary lines):

```text
PENDING
```

Full `verify.py phase` on the final tree (before persisting): PASS (ruff 0,
mypy 0, pytest 1807 passed, generated runtime matches source).

- optional 1: PASS — `dev` exported with `git archive` and generated into the scratch folder; `diff -r` of its `dist/multi-agent/` against this branch's shows exactly one differing file, `.claude/scripts/runtime_ownership.py`, the approved data-only copy of the ownership module (see Work Log); every rendered file is identical.

## Documentation

Not applicable for this phase: it adds an internal generator target, a
validator, and a pure planner, with no user-facing command until Phase C.
Phase D owns the README and `docs/` changes for both modes. A search of
`README.md`, `docs/`, and `shared/policies/` found no claim that
`multi-agent` is the only generator target.

## Open Questions / Next Steps

- Next: Phase C (`2026-09-24_phase-C-sidecar-install-and-provider-bridges`):
  `--mode`, mode detection, preflight, the ignore gate, and the apply step
  that executes this planner's actions.
