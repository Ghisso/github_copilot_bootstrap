---
name: refactor
visibility: public
description: |
  Safe refactoring with focused verification at every step. Establishes
  baseline, applies one change at a time, verifies the affected scope after
  each, then runs full verification at the end. Use when asked to refactor,
  clean up, or restructure code.
argument-hint: "[target file or description]"
---

# refactor — Safe Refactoring

## Phase 1: Baseline
```bash
uv run pytest tests/ -v --cov=src --cov-report=term-missing
```
Record: X/Y tests passing, XX% coverage. Use `--cov=shared --cov=scripts`
instead of `--cov=src` in this bootstrap's own authoring repository.

## Phase 2: Identify Targets

Look for:
- Functions > 50 lines
- Duplicated code blocks
- Poor naming
- Missing abstractions
- Tight coupling
- Dead code

Prioritize: highest-impact, lowest-risk first.

## Phase 3: Apply Changes (One at a Time)

For EACH logical change, verify only the affected scope — reserve the full
suite and full coverage run for Phase 4, since re-running them after every
single edit is unnecessary overhead during a multi-step refactor:

1. Make the change
2. Run focused tests for the affected module/file:
   `uv run pytest tests/test_<affected>.py -q` (or
   `uv run python .claude/scripts/verify.py fast --format text`, which
   selects the repository's real scope)
3. Run type check on the affected files:
   `uv run mypy <affected files> --ignore-missing-imports`
4. If focused verification fails → **revert and investigate**
5. If it passes → continue to next change

## Phase 4: Full Verification
```bash
uv run pytest tests/ -v --cov=src --cov-report=term-missing  # --cov=shared --cov=scripts in this bootstrap's own authoring repository
uv run python .claude/scripts/verify.py phase --format json --persist
```

## Rules

- **One logical change at a time** — never batch unrelated refactors
- **Focused verification must pass after every change** — revert if it
  doesn't; the full suite and coverage run are Phase 4's job, not every
  step's
- **No behavior changes** — refactoring preserves external behavior
- **Coverage must not decrease** — add tests if gaps revealed (checked at
  Phase 4, the final floor)

## Report
```
Refactoring Report:
  Files modified: N
  Changes applied: N
  Tests: X/Y passing (was A/B before)
  Coverage: XX% (was YY%)
```
