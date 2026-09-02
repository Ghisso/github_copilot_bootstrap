# Session: Phase 1 — Verification Authority

**Date:** 2026-09-02
**Plan:** `.claude/plans/2026-09-02_phase-1-verification-authority.md`
**Status:** COMPLETED

## Goal

Delete the numeric quality-score authority and make `verify.py` the single
deterministic measurement authority, without breaking in-progress consumer
upgrades. Phase 1 of the `verification-gate-semantic-hardening` big plan.

## Work Log

- **01:16** - Pre-flight. Baseline on clean `dev`: 1135 tests pass, mypy clean,
  ruff clean, `verify.py phase` PASS at `schema_version: 3`.
- **01:16** - Branch ceremony blocked: the branch hook resolves the big plan at
  `.claude/plans/<name>.md`, but the file was written as
  `2026-09-02_verification-gate-semantic-hardening.md`. Renamed to the undated
  path. Also rewrote the `phases:` list from bare phase slugs at one-space
  indent to two-space-indented small-plan **file basenames**, and matched the
  body `## Phase` inventory to it. The hooks resolve `current_phase` as a
  filename, so slugs would not have resolved. Branch created after that.
- **01:20** - Delegated implementation to `coder` with the Step A–E sequence.
- **02:26** - Round 1 returned: scorer deleted, measurements relocated into
  `verify.py`, schema bumped to v4, deterministic findings naming, v3→v4
  migration implemented. 1138 tests pass, `verify.py phase` PASS at v4.
- **02:40** - Review round 1 (profiles `code`, `architecture`, `security`,
  `tests`, `ponytail`, `documentation`): **FAIL**. 1 CRITICAL, 3 MAJOR,
  3 MINOR. All four blocking findings were shipped, validated runtime files
  still describing the deleted rubric.
- **02:55** - Round 2 fixes: all 7 addressed. 1144 tests pass.
- **03:05** - Review round 2: all 7 confirmed closed, no regressions. But an
  independent from-scratch sweep found 2 more shipped files in the same class.
  **FAIL** again: 1 CRITICAL, 1 MAJOR, 2 MINOR.
- **03:20** - Round 3 fixes: all 4 addressed. The coder's own confirmatory grep
  sweep found and fixed 2 further instances (`refactor/SKILL.md`,
  `git-hooks/commit-msg`). 1146 tests pass.
- **03:30** - Verified independently: zero `quality_score`/`EXCELLENCE`
  references remain anywhere in `shared/`, `scripts/`, or `README.md`.
- **03:40** - Review round 3: **PASS**. All 4 prior findings closed, the 2
  self-found edits confirmed correct, and the `commit-msg` change confirmed
  comment-only and inert. One new MINOR: the R-AGENTS-08 bound of 120
  characters is narrower than the 132-character canonical long-form
  `record_findings.py` invocation documented in
  `quality-and-testing.instructions.md`, so that form would silently evade the
  check. Reviewer demonstrated the miss directly.
- **03:45** - Fixed that MINOR rather than dispositioning it: bound widened to
  240 with a comment naming the constraint, plus a `canonical-long-form`
  parametrize case. Confirmed it is a real regression test — the string does
  not match at 120 and does match at 240.

## Design decisions

- **The score is deleted, not hardened.** No replacement numeric score,
  confidence value, rubric, or `produced_by` provenance field was introduced.
- **Measurements moved, not rewritten.** `verify.py` on `dev` already delegated
  to `quality_score.measure_ruff/mypy/pytest`; deleting the scorer required
  inlining that same code as `_ruff_measurement`/`_mypy_measurement`/
  `_pytest_measurement`. Reviewer confirmed the port is line-for-line
  equivalent in exit-code, JSON-shape, and error-count logic.
- **No compatibility shim for v3→v4, and none is needed.** `validate_receipt()`
  rejects any schema mismatch unconditionally. This is recoverable rather than
  a dead end because `.claude/quality_reports/` is gitignored — receipts are
  ephemeral local artifacts, never committed history. Recovery is the ordinary
  lifecycle: re-run `verify.py phase --persist` then `closeout --persist`.
  **Removal condition: not applicable — no temporary allowance exists.**
- **Findings artifacts are exact-path, not newest-wins.** `latest_report()` is
  deleted; `closeout_artifacts()` exact-matches
  `.claude/quality_reports/findings-<phase>.json`. `confined_path()` already
  rejects `..` regardless of `PHASE_SLUG` validation order, so the phase
  component cannot traverse.

## Receipt schema v4 — facts Phase 2 must consume verbatim

- `schema_version: 4`. `CHECK_IDS`, `AUTHORITATIVE_RECEIPT_FIELDS`, and all
  metadata fields are **unchanged** from v3.
- `ARTIFACT_KEYS` (closeout only): `("phase_receipt", "findings",
  "closeout_log", "documentation")`. `"score"` removed, nothing added.
- `findings` path is deterministic and exact-matched:
  `.claude/quality_reports/findings-<phase>.json`.
- `report_errors()` no longer takes a `kind` parameter; it validates only the
  findings-report shape. The `score >= 90` / `tests_passed` / `tests_skipped`
  branch is gone with no replacement metric.
- `generation_check()` (VFY-GEN-001) compares only `verify.py` against its
  generated copy.

## [LEARN] Entries

- [LEARN:workflow] A big plan's `phases:` list and `current_phase` must hold
  small-plan **file basenames**, two-space indented. The branch and commit
  hooks resolve them as `.claude/plans/<value>.md`. Bare phase slugs and
  one-space YAML indent both fail, and the indent failure surfaces as the
  misleading "missing required field: phases".
- [LEARN:workflow] When deleting a cross-cutting concept, "shipped runtime
  surface" is decided by whether `generate_targets.py` copies the file or
  `validate_targets.py` requires it — not by whether it looks like prose. A
  skill or template that reaches consumers is runtime, and deferring it to a
  later documentation phase leaves a live contract pointing at deleted code.
- [LEARN:review] A grep sweep authored by the same agent that wrote the change
  inherits that agent's blind spot. Both blocking review rounds here were found
  by an independent from-scratch sweep, not by re-checking the change list.
  Instruct the reviewer to re-derive the affected set rather than verify it.
- [LEARN:verification] Size a bounded guard regex against the longest form the
  repository itself documents, not against the examples in its own test. The
  R-AGENTS-08 bound of 120 passed every test while silently missing the
  132-character canonical invocation printed in the policy file.
- [LEARN:verification] A detail-string enricher must not sit on the status
  path. `_pytest_result_summary()` only decorates the message; PASS/FAIL is
  still decided solely by the return code, so a parsing bug cannot flip a FAIL
  to a PASS. Exit code 5 (no tests collected) and 2 (collection error) stay
  UNVERIFIED.

## Verification Results

```bash
uv run pytest tests/ -q --tb=short
# 1147 passed (baseline on dev: 1135; +12 net new)

uv run mypy scripts/ --ignore-missing-imports --explicit-package-bases
# Success: no issues found in 8 source files

uv run ruff check tests/ scripts/ shared/
# All checks passed!

uv run python scripts/validate_targets.py
# PASS generated target is structurally valid

uv run python scripts/validate_plan_frontmatter.py
# (clean)

uv run python .claude/scripts/verify.py phase --format text --persist
# phase: PASS
# VFY-RUFF-001: PASS - Ruff completed with 0 violations
# VFY-MYPY-001: PASS - mypy completed with 0 errors
# VFY-PYTEST-001: PASS - pytest completed (1147 passed in 74.25s)
# VFY-FRESH-001: PASS - phase evidence captured relevant state
# VFY-FRESH-002: PASS - phase evidence captured governing control-plane provenance
# VFY-GEN-001: PASS - generated verifier runtime matches source
# VFY-RECEIPT-001: NOT_APPLICABLE - phase creates evidence; it does not reuse it
```

Receipts: `.claude/quality_reports/` (gitignored, regenerated at closeout).

## Open Questions / Next Steps

- Phase 2 (`lifecycle-evidence`) consumes the v4 schema facts recorded above
  rather than re-deriving them.
- `docs/architecture.md` and `docs/plan-deterministic-commit-gate.md` still
  carry score-era prose. Both are author-facing and not copied to consumers, so
  they are deliberately deferred to Phase 3's stale-claims review.
- Four files were already unformatted on `dev` before this work and were not
  touched: `shared/hooks/scripts/protect-files.py`,
  `shared/skills/caveman-compress/scripts/{detect,validate}.py`,
  `tests/test_check_native_clients.py`. Pre-existing drift, out of scope.
