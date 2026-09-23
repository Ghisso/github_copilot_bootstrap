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
- Was every third-party binary, CLI, MCP server, or SDK this diff depends on
  exercised directly at least once — spike evidence, a real-binary test, or a
  recorded observation — or only through test doubles? Name the evidence.

## Severity

- Critical: Tests with no assertions, false positives, or tests that cannot fail for the intended behavior.
- Major: Missing failure paths, inappropriate mocks, missing edge cases, unasserted mocks, or a third-party binary/CLI/MCP server/SDK dependency exercised only through test doubles with no spike evidence, real-binary test, or recorded observation.
- Minor: Naming, fixture polish, or parametrization improvements.

