---
name: testing-patterns
description: |
  Comprehensive pytest testing patterns for production code. Use when writing
  unit tests, integration tests, async tests, mocking dependencies, or setting
  up test fixtures. Covers pytest-asyncio, mocking, parametrization, Hydra
  config testing, and coverage.
  scope: test case authoring, enumeration, and structure
user-invocable: false
---

## Test Generation Workflow

### Phase 1: Reconnaissance

Before writing any test, build a model of the target code:

1. **Identify scope** — What functions, classes, or modules need tests? If unspecified, check recent modifications: `git diff --name-only HEAD~5`
2. **Read function signatures** — Parameters, types, return types, defaults. Every parameter is a test dimension.
3. **Map dependencies** — Which calls go to external systems (DB, API, filesystem, clock)? These are mock candidates.
4. **Detect complexity hotspots** — Functions with high branch counts, deep nesting, or multiple return paths need more test cases.
5. **Check existing tests** — If tests already exist, understand what they cover. Do not duplicate; extend.
6. **Read project conventions** — Check `conftest.py`, `pytest.ini`/`pyproject.toml` for fixtures, markers, and test organization patterns.

### Phase 2: Test Case Enumeration

For each function under test, enumerate cases across four categories:

| Category   | What to Test                                | Example                                     |
|------------|---------------------------------------------|---------------------------------------------|
| Happy path | Expected inputs produce expected outputs    | `add(2, 3)` returns `5`                     |
| Boundary   | Edge values at limits of valid input        | Empty string, zero, max int, single element |
| Error      | Invalid inputs trigger proper exceptions    | `None` where `str` expected, negative index |
| State      | State transitions produce correct side effects | Object moves from `pending` to `active`  |

Parametrize cases that share the same test logic but differ only in input/output values.

### Phase 3: Scope Mode

| Mode            | Scope             | Depth                                        | When to Use                          |
|-----------------|-------------------|----------------------------------------------|--------------------------------------|
| `quick`         | Single function   | Happy path + 1 error case                    | Rapid iteration, TDD red-green cycle |
| `standard`      | File or class     | Happy + boundary + error + mocks             | Default for most requests            |
| `comprehensive` | Module or package | All categories + async + parametrized matrix | Pre-release, critical path code      |

---

## Project Structure

```
project/
├── src/
│   └── module.py
├── tests/
│   ├── conftest.py        # Shared fixtures
│   ├── unit/
│   │   └── test_module.py
│   ├── integration/
│   └── fixtures/          # Test data files
└── pyproject.toml
```

---

## Basic Test Structure

```python
"""Tests for module."""
import pytest
from src.module import MyModel


class TestMyModel:
    """Test suite for MyModel."""

    def test_initialization(self) -> None:
        model = MyModel(hidden_size=768)
        assert model.hidden_size == 768

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError, match="hidden_size must be positive"):
            MyModel(hidden_size=-1)
```

---

## Fixtures (conftest.py)

```python
import pytest
from pathlib import Path


@pytest.fixture
def sample_config():
    return {"model": {"name": "test", "hidden_size": 64}}


@pytest.fixture
def temp_dir(tmp_path):
    return tmp_path


@pytest.fixture(scope="session")
def test_data_dir():
    return Path(__file__).parent / "fixtures"
```

**Fixture Scope Selection:**

| Scope      | Use When                                   | Example                      |
|------------|--------------------------------------------|------------------------------|
| `function` | Default. Each test gets fresh state        | Most unit tests              |
| `class`    | Tests within a class share expensive setup | DB connection per test class |
| `module`   | All tests in a file share setup            | Loaded config file           |
| `session`  | Entire test run shares setup               | Docker container startup     |

**Fixture Design Rules:**
- If 3+ tests need the same object, extract a fixture.
- Use `yield` fixtures when cleanup is needed. Never leave side effects.
- Fixtures used across multiple test files → `conftest.py`.
- Fixtures used in one file → keep in that file.

---

## Async Tests

```python
import pytest
from unittest.mock import AsyncMock, patch


class TestAsyncOps:
    @pytest.mark.asyncio
    async def test_build_async(self, builder) -> None:
        with patch("src.builder.Component") as mock_cls:
            mock_instance = AsyncMock()
            mock_cls.return_value = mock_instance

            result = await builder.build_async()

            mock_instance.initialize.assert_called_once()
            assert result is not None
```

---

## Mocking

```python
from unittest.mock import Mock, AsyncMock, patch


class TestAPIClient:
    @patch("src.api_client.requests.post")
    def test_request_success(self, mock_post, api_client) -> None:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"result": "success"}
        mock_post.return_value = mock_response

        result = api_client.make_request("data")

        assert result == {"result": "success"}
        mock_post.assert_called_once()
```

**Mocking strategies:**
- `@patch()` for external functions
- `Mock()` for objects, `AsyncMock()` for async methods
- `side_effect` for exceptions, `return_value` for return values

**Mock Discipline:**
1. **Mock external dependencies only** — network calls, filesystem, time, random.
2. **Never mock** — the function under test, pure functions called by the target, data structures.
3. **Patch at the import boundary** — `@patch('mymodule.requests.get')`, not `@patch('requests.get')`.
4. **Assert every mock** — every mock should assert it was called with expected arguments and count. Mocks without assertions are coverage holes.
5. **Use concrete return values** — `"alice@example.com"` not `"test_email"`. Concrete values catch type mismatches.

---

## Parametrized Tests

```python
@pytest.mark.parametrize("email,expected", [
    ("user@example.com", True),
    ("invalid.email", False),
    ("", False),
    (None, False),
])
def test_validate_email(self, email, expected) -> None:
    assert validate_email(email) == expected
```

---

## Coverage

```bash
uv run pytest --cov=src --cov-report=html --cov-report=term-missing
```

**pyproject.toml:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["--verbose", "--tb=short"]
markers = [
    "asyncio: async tests",
    "slow: slow tests",
    "integration: integration tests",
]
```

---

## Run Commands

```bash
# All tests
uv run pytest tests/ -q --tb=short

# Single file
uv run pytest tests/test_module.py -v

# Single test
uv run pytest tests/test_module.py::TestMyModel::test_initialization -v

# Skip slow tests
uv run pytest -m "not slow"

# With coverage
uv run pytest --cov=src --cov-report=term-missing
```

---

## Calibration Rules

1. **Test isolation is non-negotiable.** Every test must pass when run alone and in any order. No test may depend on side effects of another test.
2. **One assertion focus per test.** A test should verify one behavior. Multiple assertions are acceptable when they verify different aspects of the same behavior (e.g., return value AND side effect), but not unrelated behaviors.
3. **Parametrize, don't duplicate.** If two tests differ only in input/output values, combine with `@pytest.mark.parametrize`. Use `ids` for readable test names.
4. **Match project conventions.** Follow existing `conftest.py` fixtures, class-based tests, or markers. Do not introduce conflicting test styles.

---

## Anti-Patterns

- **Test helpers calling private methods** — see `test-helper-public-api/SKILL.md`
- **No `match=` in `pytest.raises`** — always specify the expected message pattern
- **`scope="session"` for mutable fixtures** — use `function` scope to avoid state leakage
- **Testing stdlib instead of production code** — mock at the boundary, not the standard library
