---
applicability:
  - tests/**/*.py
---

# Testing Standards

## Test Generation Workflow

Before writing tests, follow the reconnaissance protocol:

1. **Identify scope** — functions, classes, or modules to test.
2. **Read signatures** — parameters, types, return types. Every parameter is a test dimension.
3. **Map dependencies** — external calls (API, DB, filesystem) are mock candidates.
4. **Enumerate cases** across four categories:
   - **Happy path:** expected inputs → expected outputs
   - **Boundary:** edge values (empty, zero, max, single element)
   - **Error:** invalid inputs → proper exceptions
   - **State:** transitions produce correct side effects
5. **Check existing tests** — extend, don't duplicate.

## Test File Structure

```python
import pytest
from unittest.mock import MagicMock, patch


class TestMyFeature:
    """Tests for MyFeature."""

    def test_happy_path(self, sample_config: MyConfig) -> None:
        feature = MyFeature.from_config(sample_config)
        result = feature.process("input")
        assert result == "expected"

    def test_invalid_input_raises(self) -> None:
        with pytest.raises(ValueError, match="cannot be empty"):
            MyFeature.process("")

    @pytest.mark.parametrize("value,expected", [
        ("a", 1),
        ("b", 2),
        ("c", 3),
    ])
    def test_multiple_inputs(self, value: str, expected: int) -> None:
        assert transform(value) == expected
```

## Fixtures (conftest.py)

```python
@pytest.fixture
def sample_config() -> MyConfig:
    return MyConfig(param="test_value")

@pytest.fixture
def mock_external_api() -> MagicMock:
    with patch("src.module.ExternalAPI") as mock:
        mock.return_value.call.return_value = {"result": "ok"}
        yield mock
```

## Mocking Rules

**Mock external services:** HTTP clients, LLM APIs, embedding models, databases, time, randomness.
**Use real objects for:** dataclasses, configs, pure functions, lightweight framework components.
**Patch at the import boundary:** `@patch("src.module.ExternalAPI")`, not `@patch("external_lib.API")`.
**Assert every mock:** every mock must have at least one assertion on call count/args.
**Use concrete values:** `"alice@example.com"` not `"test_email"`. Concrete values catch type mismatches.

```python
# Good: mock external LLM call
with patch("src.retrieval.generator.OpenAIChatGenerator") as mock_gen:
    mock_gen.return_value.run.return_value = {"replies": ["answer"]}
    result = pipeline.run(query="test")

# Bad: mocking your own pure function
with patch("src.utils.helpers.clean_text") as mock:  # don't do this
    ...
```

## Test Design Rules

- **Files:** use `tmp_path` for file tests.
- **Context managers:** test that `__exit__` calls its cleanup, also when the body raises: `with patch.object(obj, "close", wraps=obj.close) as mock_close, obj: pass`, then `mock_close.assert_called_once()`. A bare `with obj: pass` is a zero-assertion test.
- **Test helpers:** call the narrowest public method that covers the behavior, never a chain of private methods (`_build_nodes()`, `_extract()`); that chain lets a bug in the public method (wrong step order, missing state update) pass. With no public method, assert observable behavior or use an existing seam; add a public method only if it is a useful abstraction on its own. Break the public method on purpose to confirm a test fails.

## Async Tests

```python
@pytest.mark.asyncio
async def test_async_endpoint() -> None:
    service = MyService()
    await service.on_startup()
    result = await service.predict(QueryRequest(message="test"))
    assert result.answer is not None
```

Requires `pytest-asyncio` and in `pytest.ini` or `pyproject.toml`:
```ini
[pytest]
asyncio_mode = auto
```

## Coverage Requirements

- 80%+ coverage on critical paths (`src/` for an installed consumer, or
  `shared`/`scripts` in the bootstrap authoring repository). Consumers run
  `uv run pytest tests/ --cov=src --cov-report=term-missing` (or their
  configured source root); the authoring repository runs
  `uv run pytest tests/ --cov=shared --cov=scripts --cov-report=term-missing`
- Every bug fix MUST include a regression test
- Edge cases: empty input, None, boundary values, error paths

## Anti-Patterns

- Tests with no assertions (`assert True` or bare function call)
- Mocking what you own (testing mock behavior, not real behavior)
- Tests that depend on execution order
- No `match=` parameter on `pytest.raises` — always verify error message
- Unasserted mocks (mock exists but no `assert_called_*` check)
- Abstract test data (`"test_value"`) instead of concrete data (`"S/RES/1234"`)
- Duplicated test logic instead of `@pytest.mark.parametrize` with readable `ids`
- `scope="session"` for mutable fixtures — use `function` scope to avoid state leakage
- Treating a mock-heavy pass as proof — verify with at least one integration test
- Ignoring deprecation warnings — fix them and note the cause in `.claude/MEMORY.md`
