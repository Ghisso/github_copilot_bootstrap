---
name: testing-patterns
visibility: background
description: |
  Pytest test-authoring workflow. Use when writing or reviewing unit tests,
  integration tests, async tests, fixtures, parametrization, or mocks.
  scope: test case authoring, enumeration, and structure
user-invocable: false
---

# Testing Patterns

This skill covers how to design tests. The authoritative hard rules are `.claude/instructions/tests.instructions.md`.

## Test-Authoring Workflow

1. Identify the public behavior under test.
2. Read function signatures, defaults, return types, and side effects.
3. Map dependencies:
   - Mock external systems: network, databases, LLM APIs, filesystem boundaries, time, randomness.
   - Use real objects for configs, dataclasses, pure functions, and lightweight framework objects.
4. Enumerate cases:
   - Happy path
   - Boundary values
   - Error paths
   - State transitions or side effects
5. Check existing tests and extend them instead of duplicating coverage.
6. Use concrete test data and meaningful assertions.

## Patterns

- Use `tmp_path` for file tests.
- Patch mocks at the import boundary of the module under test.
- Assert every mock call count or call arguments.
- Use `pytest.raises(..., match=...)` for expected exceptions.
- Parametrize repeated test logic and add readable `ids`.
- Mark async tests with `@pytest.mark.asyncio` unless project config enables auto mode.

## Verify

```bash
uv run pytest tests/ -q --tb=short
uv run pytest tests/ --cov=src --cov-report=term-missing
```
Use `--cov=shared --cov=scripts` instead of `--cov=src` in this bootstrap's
own authoring repository.

If the policy and this skill disagree, follow `.claude/instructions/tests.instructions.md`.

