---
name: code-style
description: Python code style conventions for production development. Use when writing new code, reviewing PRs, or ensuring consistency in type hints, docstrings, logging, error handling, naming conventions, and import organization.
---

# Code Style Requirements

Python code style conventions for production AI engineering.

---

## Type Hints

**Required** on all functions. Use Python 3.12+ style:
```python
from typing import Any, Literal, TYPE_CHECKING

def query(self, message: str, config: RuntimeQueryConfig | None = None) -> str:
    ...

def process_items(items: list[str]) -> dict[str, int]:
    return {item: len(item) for item in items}

def handle_value(value: str | int | None) -> str:
    if value is None:
        return "empty"
    return str(value)
```

**Python 3.12+ (REQUIRED):**
- **Always use lowercase**: `list`, `dict`, `tuple`, `set`
- **Union syntax**: `str | int` instead of `Union[str, int]`
- **Optional**: `X | None` instead of `Optional[X]`
- Only import from `typing` when needed: `Any`, `Literal`, `TYPE_CHECKING`, `Protocol`
- **Never import**: `List`, `Dict`, `Tuple`, `Set`, `Union`, `Optional`

---

## Docstrings

**Required** in Google style with Args/Returns/Example:
```python
def query(self, message: str, config: RuntimeQueryConfig | None = None) -> str:
    """Query the RAG system with user message.

    Args:
        message: User query string.
        config: Optional query configuration.

    Returns:
        Query result as string.

    Example:
        >>> rag.query("What is mining?")
        'Mining is...'
    """
```

---

## Logging

Use module-level logger with `%` formatting:
```python
import logging
logger = logging.getLogger(__name__)

logger.info("Loading config: %s", config_name)   # Correct
logger.error("Error: %s", e)                      # Correct
logger.info(f"Loading {config_name}")             # WRONG
```

---

## Error Handling

Use specific exceptions with error chaining:
```python
try:
    result = builder._create_pipeline()
except ValueError as e:
    logger.error("Invalid configuration: %s", e)
    raise RuntimeError("Failed to create pipeline") from e
```

---

## Naming Conventions

- **Classes**: PascalCase (`RagBuilder`, `QueryConfig`)
- **Functions/methods**: snake_case (`build_async`, `query_system`)
- **Async variants**: `_async` suffix when sync version exists
- **Private methods**: Leading underscore (`_create_llm_func`)
- **Constants**: UPPER_SNAKE_CASE (`DEFAULT_TOP_K`)

---

## Import Organization

Three groups, blank line between, alphabetical within:
```python
# Standard library
import logging
from dataclasses import dataclass
from typing import Any

# Third-party
import bentoml
from pydantic import BaseModel

# Local application
from src.configs.main_config import MainConfig
```

---

## Other

- **String formatting**: f-strings (except logging: use `%`)
- **Path handling**: `pathlib.Path` (never `os.path`)
- **Context managers**: Always `with` for resources
- **Async**: `_async` suffix, provide both sync/async when wrapping async frameworks
