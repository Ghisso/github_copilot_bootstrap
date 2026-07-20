# Test Review Profile

Use for test quality, coverage, fixtures, and mocking decisions.

## Checklist

- New public behavior has tests.
- Happy path, boundary, error, and state cases are covered where relevant.
- Regression tests exist for bug fixes.
- Tests have meaningful assertions.
- `pytest.raises` checks messages with `match=`.
- Test data is concrete, not vague placeholders.
- External systems are mocked; owned pure functions are not.
- Every mock has an assertion.
- Mocks are patched at the import boundary.
- Parametrize repeated test logic and use readable ids.
- Tests are isolated and order-independent.
- Async tests use `@pytest.mark.asyncio` unless project config enables auto mode.

## Severity

- Critical: Tests with no assertions, false positives, or tests that cannot fail for the intended behavior.
- Major: Missing failure paths, inappropriate mocks, missing edge cases, or unasserted mocks.
- Minor: Naming, fixture polish, or parametrization improvements.

