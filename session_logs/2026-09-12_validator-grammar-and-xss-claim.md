# Validator grammar and XSS claim

**Status:** COMPLETED

**Plan:** `.claude/plans/2026-09-12_phase-A-validator-grammar-and-xss-claim.md`

## Goal

Correct the skill-frontmatter grammar, placeholder recognition, stale security
claim, and related documentation, with regression coverage.

## Approach

Use the approved one-phase plan. Keep the validator's intentionally small
frontmatter parser, normalize the supported scalar forms once, update the
claim and documentation, then run the required verification and review gates.

## Initial state

- Implementation branch: `2026-09-12_validator-grammar-and-xss-claim_implementation`
- Base branch: `dev`
- Working tree: clean before branch creation

## Completed work

- Normalized supported flat-frontmatter scalars for `name` and `visibility`.
- Recognized angle-bracket placeholder paths without relaxing concrete-path
  validation.
- Corrected the PyVis XSS attribution and removed stale provenance wrapping
  guidance.
- Added regression coverage for all newly supported forms and preserved
  denial coverage for concrete broken paths.

## Verification

- `uv run python .claude/scripts/verify.py fast --format json` — PASS
- `uv run python scripts/generate_targets.py --all` — PASS
- `uv run python scripts/validate_targets.py` — PASS
- `uv run python scripts/install_bootstrap.py . --allow-self --local-only` — PASS
- `uv run python scripts/check_runtime.py` — PASS
- `uv run pytest tests/ -q --tb=short` — PASS
- `uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases` — PASS
- `uv run ruff check shared scripts tests` — PASS
- `uv run ruff format --check shared scripts tests` — PASS
- `git diff --check` — PASS

## Review

The required `code`, `architecture`, `security`, `tests`, and `ponytail`
review passes returned no surviving findings.

## [LEARN] Entries

- [LEARN:validation] Normalize each supported flat-frontmatter scalar form
  before comparison and prove the regression against raw-text matching.

## Stale-claims surfaces checked

- `README.md` — no stale grammar, placeholder, PyVis, or provenance claim.
- `docs/` — updated `docs/architecture.md`; no other stale claim found.
- `shared/policies/`, `shared/skills/`, `shared/templates/`, `shared/agents/`,
  and `shared/review-profiles/` — corrected the PyVis skill and stale
  provenance note; no other stale claim found.
- State READMEs and `.claude` mirrors — no stale claim found.
- `.claude/MEMORY.md` — corrected obsolete wrap-sensitive-validator advice and
  recorded the scalar-normalization lesson.
