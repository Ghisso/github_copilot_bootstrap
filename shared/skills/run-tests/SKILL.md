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

## Step 2: Specific Tests (if argument provided)
Run explicitly requested or focused tests before broader suites.
```bash
uv run pytest [path] -v --tb=short -k "[pattern]"
```

## Step 3: Full Suite with Coverage (optional, for local breadth)
```bash
uv run pytest tests/ -v --cov=src --cov-report=term-missing
```
Use `--cov=shared --cov=scripts` instead of `--cov=src` in this bootstrap's
own authoring repository. Final phase-closeout breadth is delegated to
`uv run python .claude/scripts/verify.py phase --format text`; do not
prescribe repeated full-suite runs beyond what that canonical check already
covers.

## Step 4: E2E Validation (if examples exist)
```bash
shopt -s nullglob
scripts=(examples/run_*.py)
if [ ${#scripts[@]} -eq 0 ]; then
  echo "No E2E scripts"
else
  status=0
  for script in "${scripts[@]}"; do
    uv run python "$script" || status=1
  done
  if [ "$status" -eq 0 ]; then
    echo "E2E scripts passed"
  else
    echo "E2E scripts FAILED" >&2
    exit 1
  fi
fi
```
Never let a real failure print as "No E2E scripts" — check existence first,
then report exactly one of: absent, passed, or failed.

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
