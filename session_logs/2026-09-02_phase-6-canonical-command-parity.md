# Session: Phase 6 — Canonical Command Parity

**Date:** 2026-09-02
**Plan:** `.claude/plans/2026-09-02_phase-6-canonical-command-parity.md`
**Status:** COMPLETED

## Goal

Make the documented verification commands match what the gate actually runs,
in both the authoring repository and installed consumers, and close the
formatting drift the mismatch allowed. Final phase of
`verification-gate-semantic-hardening`.

## Work Log

- **06:00** - The user asked for the mypy scope gap to become a phase, and to
  fix as much as possible. Measured the documented commands first rather than
  assuming: `mypy src/` exits 2 with `Cannot read file 'src'`, `ruff check
  src/ tests/` exits 1, `ruff format --check src/ tests/` exits 2. Only
  `pytest tests/` works. There is no `src/` here.
- **06:05** - Found two further mismatches in the same class while scoping.
  `ruff format --check` is documented as required but never gated, which is
  why six files sat unformatted — two of them (`verify.py`, `test_verify.py`)
  edited by this very plan across five phases with nothing catching it. And
  `uv sync` also fails: no `pyproject.toml` has ever existed on any branch.
- **06:10** - Confirmed the code already knew the difference all along:
  `phase_checks` selects `["shared","scripts","tests"]` for an authoring
  repository and `["."]` plus `consumer_mypy_targets` otherwise. The
  documentation was the only wrong part.
- **08:30** - Round 1: root `CLAUDE.md` corrected, shipped surfaces swept with
  a recorded judgement per file, `VFY-FMT-001` added, six files formatted.
  1225 tests pass.
- **09:00** - I rejected the coder's decision to leave `uv sync` documented.
  Its reasoning deferred to my own plan text, which was an illustration, not a
  considered claim. The devcontainer already guards `uv sync` with
  `[ -f pyproject.toml ]` and the Dockerfile provisions tooling with
  `uv pip install --system`, so the authoring-versus-consumer split this phase
  applies everywhere else resolves it too.
- **09:40** - Review round 1: **FAIL**, 1 CRITICAL + 3 MAJOR + 1 MINOR.
- **10:30** - Round 2: all five fixed. 1230 tests pass.

## Design decisions

- **Route to the authority instead of restating its scope.** The whole failure
  was a hardcoded duplicate of `verify.py`'s scope drifting from it, which is
  the plan's own design rule being violated. Documents whose purpose is "how
  you verify this repository" now point at `verify.py fast`/`phase`, which
  picks the right scope for whichever repository it runs in and therefore
  cannot drift.
- **`src/` is correct for consumers, so this was never a substitution.** Four
  scaffolding skills that legitimately describe a `src/`-layout project were
  deliberately left alone, as was the consumer template in
  `generate_targets.py`. Where a shipped document is also installed here and
  would be wrong, routing through `verify.py` fixes both at once without
  branching the prose.
- **The formatting check folded into `VFY-RUFF-001` rather than adding an ID.**
  This is the phase's most important decision, and it was forced by review —
  see below.
- **`uv sync` is not documented for this repository.** It cannot work here and
  the runtime already treats it as conditional. It stays unconditional in the
  consumer template, where a `pyproject.toml` exists.

## The CRITICAL: a new check ID silently invalidated the plan's own history

Adding `VFY-FMT-001` grew `CHECK_IDS` from 7 to 8. `validate_receipt` enforces
`len(checks) == len(CHECK_IDS)` and exact set equality, so every already-
persisted phase 1–5 closeout receipt — each recording 7 checks — stopped
validating. Reproduced directly against the real receipts on disk:

```text
CHECK_IDS now: 8
historical_chain_errors -> ['historical phase 2026-09-02_phase-5-... receipt
is invalid: ... receipt must contain every required check exactly once']
```

That is the push/PR gate failing to validate this plan's own history, which
would have surfaced the moment a PR was opened. It passed 1225 green tests
because every `test_historical_chain_*` fixture builds receipts with current
code on both sides, so no test ever sees an older check set.

The durable lesson: **`CHECK_IDS` is part of the receipt schema contract,
because the gate validates its own history.** Adding a check is a schema
change, and this phase's non-goals forbade both a schema change and a
compatibility allowance. Folding both Ruff measurements under the existing
`VFY-RUFF-001` satisfies all three constraints: the check set never changes
shape, no historical receipt is invalidated, and the summary still names which
half failed so a diagnostic stays actionable.

Verified after the fix: the real-receipt chain returns `[]`, and an
intentionally unformatted file still produces
`VFY-RUFF-001: FAIL - lint: ... 0 violations | format: ... would reformat 1 file(s)`.

## [LEARN] Entries

- [LEARN:verification] `CHECK_IDS` is part of the receipt schema contract,
  because the gate validates its own history. Adding or removing a check ID
  invalidates every previously persisted receipt through
  `validate_receipt`'s exact set equality. Extend an existing check rather
  than adding an ID, unless a schema bump and a migration path are intended.
- [LEARN:testing] A fixture that builds both sides of a comparison from the
  current code can never detect a contract that changed between them. Every
  historical-chain test derived its check set from `verify.CHECK_IDS`, so a
  breaking change to that constant was invisible. Pin the previously persisted
  shape as a literal, independent of the constant under test.
- [LEARN:review] Validate against the artifacts actually on disk, not only
  synthetic fixtures. This CRITICAL was found by running the real validation
  function over the real phase 1–5 receipts; three prior review rounds and a
  full green suite had missed it.
- [LEARN:workflow] A documented command that cannot run is the same defect
  class as a documented behavior that is false. `mypy src/`, `ruff check
  src/ tests/`, and `uv sync` had all been documented and broken here for the
  whole life of this repository, and a contributor substituting a plausible
  scope passed locally while checking 8 of the 25 files the gate checks.
- [LEARN:verification] A documented requirement that nothing enforces will
  drift. `ruff format --check` was required in prose and gated nowhere, so
  this plan's own edits to `verify.py` and `test_verify.py` went unformatted
  across five phases. Either gate a requirement or stop claiming it.
- [LEARN:review] A word-boundary grep for `score` misses `scoring`. Root
  `CLAUDE.md` — the file governing every session — kept score-era text through
  three phases of sweeps by me and by the reviewer for exactly that reason.

## Verification Results

```bash
uv run pytest tests/ -q --tb=short
# 1230 passed (1135 on dev at the start of this plan; +95 across six phases)

uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
# Success: no issues found in 25 source files

uv run ruff check shared scripts tests
# All checks passed!

uv run ruff format --check shared scripts tests
# 25 files already formatted

uv run python scripts/validate_targets.py
# PASS generated target is structurally valid

uv run python scripts/validate_plan_frontmatter.py
# (clean)

uv run python .claude/scripts/verify.py phase --format text
# phase: PASS
# VFY-RUFF-001: PASS - lint: Ruff completed with 0 violations | format: Ruff format completed with 0 files needing reformatting
```

Real-receipt historical chain across phases 1–6: `[]`.

## Stale-claims surfaces checked

Triggered because this phase changed documented commands. Checked and updated:
root `CLAUDE.md`, `README.md`, `docs/runtime-checks.md`,
`shared/policies/{workspace,workflow,quality-and-testing,tests,code-standards}.instructions.md`,
`shared/templates/{plan-small,quality-report}.md`, and the
`code-style`, `refactor`, `context-status`, `run-tests`, and
`testing-patterns` skills. Deliberately unchanged with recorded reasons:
`deployment.instructions.md`, the `setup-project`, `create-feature`,
`domain-type-placement`, and `graph-schema-compat-migration` skills, and
`generate_targets.py`'s consumer template — all correctly consumer-shaped.

## Open Questions / Next Steps

- `uv sync` still cannot run here because no `pyproject.toml` exists. Root
  `CLAUDE.md` no longer claims it. Creating one would be a dependency and
  lockfile change needing its own plan.
- `uv.lock` remains named in the never-hand-edit prohibition although the file
  does not exist here. A prohibition about a file that may exist is harmless.
- No compatibility allowance exists in this plan, so none carries a removal
  condition.
- The user owns the merge decision; no PR was opened.
