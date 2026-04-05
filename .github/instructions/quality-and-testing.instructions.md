---
description: "Always-on: Quality gates, verification commands, scoring rubric, and testing protocol. Load when verifying, testing, or scoring code."
---

# Quality Gates & Testing Protocol

---

## Verification Commands (run after every task)

```bash
uv run pytest tests/ -q --tb=short          # All tests
uv run mypy src/ --ignore-missing-imports --explicit-package-bases  # Type check
uv run ruff check src/ tests/              # Lint (0 violations required)
```

**Testing order:** unit tests → existing tests (regression) → E2E (if applicable).
**Never claim completion without running all three.**

---

## Mock vs Real Objects

See `tests.instructions.md` for detailed mocking rules.

> Quick guideline: Mock external services (API, DB, LLM). Use real objects for configs, dataclasses, pure functions.

---

## Coverage Target

80%+ on critical paths (`src/`). Run: `uv run pytest tests/ --cov=src --cov-report=term-missing`

Every bug fix MUST include a regression test.

---

## Async Tests

```python
@pytest.mark.asyncio
async def test_async_operation() -> None:
    result = await my_async_function()
    assert result is not None
```

---

## Quality Scoring Rubric

### Python Source (`src/**/*.py`)

| Severity | Issue | Deduction |
|---|---|---|
| Critical | Syntax errors / module won't import | -100 |
| Critical | mypy type errors | -20 |
| Critical | Security vulnerability (hardcoded secrets, injection, unsafe deser.) | -20 |
| Critical | Missing tests for new public functions | -15 |
| Major | Missing type hints on public functions | -10 |
| Major | Missing Google-style docstrings on public functions | -5 |
| Major | Deprecated types (`List`/`Dict`/`Optional`) | -5 |
| Major | ruff lint errors | -3 per error |
| Major | f-strings in logging | -3 |
| Minor | Import order violation | -2 |
| Minor | Line length > 120 chars | -1 per occurrence |

### Test Files (`tests/**/*.py`)

| Severity | Issue | Deduction |
|---|---|---|
| Critical | No assertions in test | -20 |
| Critical | Test passes when it should fail | -20 |
| Major | No edge cases | -10 |
| Major | Inappropriate mocking (mocking what you own) | -5 |
| Major | Missing parametrize for multi-input tests | -3 |

### API Services (`service.py`, `src/api/**`)

| Severity | Issue | Deduction |
|---|---|---|
| Critical | No Pydantic input validation | -15 |
| Critical | No error handling on endpoints | -10 |
| Major | Secrets in code (not env vars) | -20 |
| Major | Missing async for I/O endpoints | -5 |
| Major | No health check endpoint | -5 |

### Config Files (`src/configs/**`)

| Severity | Issue | Deduction |
|---|---|---|
| Critical | Hardcoded values that should be configurable | -10 |
| Critical | Missing `__post_init__` validation | -5 |
| Major | Config not registered with ConfigStore | -10 |

---

## Gates

| Score | Gate | Action |
|---|---|---|
| ≥ 95 | Excellence | Aspirational |
| ≥ 90 | PR-ready | Ready for review/deploy |
| ≥ 80 | Commit | Good enough to save |
| < 80 | Block | List blocking issues, do not commit |

---

## Common Pitfalls

- **Never assume tests pass** — always run them.
- **Deprecation warnings** = future breakage. Fix immediately, document in MEMORY.md.
- **Mock-heavy tests passing ≠ real code works** — verify with at least one integration test.
- **Partial testing** — run ALL tests, not just new ones. Catch regressions.
