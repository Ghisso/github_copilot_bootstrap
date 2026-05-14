---
name: run-tests
visibility: public
description: |
  Pytest orchestration with coverage reporting. Runs unit tests, backward
  compatibility checks, and E2E validation in sequence. Use when asked to
  run tests, test this, or verify the test suite.
  scope: test execution orchestration and coverage reporting
argument-hint: "[path or test pattern]"
---

# run-tests — Test Orchestration

## Step 0: Reconnaissance (for test generation)
If generating new tests, follow the reconnaissance workflow from `testing-patterns/SKILL.md`:
1. Identify scope and read function signatures.
2. Map dependencies (mock candidates).
3. Enumerate test cases: happy path, boundary, error, state.
4. Choose scope mode: `quick` (single function), `standard` (file/class), `comprehensive` (module/package).

## Step 1: Quick Run
```bash
uv run pytest tests/ -q --tb=short
```

## Step 2: Full Suite with Coverage (if step 1 passes)
```bash
uv run pytest tests/ -v --cov=src --cov-report=term-missing
```

## Step 3: Specific Tests (if argument provided)
```bash
uv run pytest [path] -v --tb=short -k "[pattern]"
```

## Step 4: E2E Validation (if examples exist)
```bash
uv run python examples/run_*.py 2>/dev/null || echo "No E2E scripts"
```

## Step 5: Deprecation Check
```bash
uv run pytest tests/ -W default::DeprecationWarning 2>&1 | grep -i deprecat || echo "Clean"
```

## Report

```
Test Results:
  Unit:        X/Y passed
  Integration: X/Y passed (or SKIP)
  Coverage:    XX% (src/)

Deprecation Warnings: N found

Failed Tests (first 3):
  [test name] -- [error summary]
```

## Flags
- `--slow`: Include `@pytest.mark.slow` tests
- `--integration`: Run `tests/integration/` only
- `-k "pattern"`: Run matching tests only
