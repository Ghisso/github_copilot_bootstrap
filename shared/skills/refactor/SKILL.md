---
name: refactor
visibility: public
description: |
  Safe refactoring with test verification at every step. Establishes baseline,
  applies one change at a time, verifies after each, then runs full
  verification. Use when asked to refactor, clean up, or restructure code.
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

For EACH logical change:
1. Make the change
2. Run tests immediately: `uv run pytest tests/ -q`
3. Run type check: `uv run mypy src/ --ignore-missing-imports` (`mypy shared
   scripts tests` in this bootstrap's own authoring repository — `verify.py
   fast` does not run mypy)
4. If tests fail → **revert and investigate**
5. If tests pass → continue to next change

## Phase 4: Full Verification
```bash
uv run pytest tests/ -v --cov=src --cov-report=term-missing  # --cov=shared --cov=scripts in this bootstrap's own authoring repository
uv run python .claude/scripts/verify.py phase --format json --persist
```

## Rules

- **One logical change at a time** — never batch unrelated refactors
- **Tests must pass after every change** — revert if they don't
- **No behavior changes** — refactoring preserves external behavior
- **Coverage must not decrease** — add tests if gaps revealed

## Report
```
Refactoring Report:
  Files modified: N
  Changes applied: N
  Tests: X/Y passing (was A/B before)
  Coverage: XX% (was YY%)
```
