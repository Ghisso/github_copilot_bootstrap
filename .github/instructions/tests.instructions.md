---
applyTo: "tests/**/*.py"
---

# Testing Standards

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

**Mock external services:** HTTP clients, LLM APIs, embedding models, databases.
**Use real objects for:** dataclasses, configs, pure functions, lightweight framework components.

```python
# Good: mock external LLM call
with patch("src.retrieval.generator.OpenAIChatGenerator") as mock_gen:
    mock_gen.return_value.run.return_value = {"replies": ["answer"]}
    result = pipeline.run(query="test")

# Bad: mocking your own pure function
with patch("src.utils.helpers.clean_text") as mock:  # don't do this
    ...
```

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

- 80%+ coverage on `src/` paths
- Every bug fix includes a regression test
- Edge cases: empty input, None, boundary values, error paths

## Anti-Patterns

- Tests with no assertions (`assert True` or bare function call)
- Mocking what you own (testing mock behavior, not real behavior)
- Tests that depend on execution order
- No `match=` parameter on `pytest.raises` — always verify error message
