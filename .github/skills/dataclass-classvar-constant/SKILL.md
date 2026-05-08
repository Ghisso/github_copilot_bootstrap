---
name: dataclass-classvar-constant
description: |
  Fix dataclass fields intended as immutable constants that are accidentally
  mutable at construction time. Trigger: a field like `_MAX_TOP_K = 500` or
  `MAX_RESULTS: int = 1000` in a dataclass that should be a class-level ceiling,
  not an instance attribute that callers can override.
user-invocable: false
---

## Problem

A dataclass field intended as an immutable constant can be overridden at
construction time, silently bypassing any guard that checks against it:

```python
@dataclass
class RuntimeOverrides:
    _MAX_TOP_K: int = 500   # WRONG: included in __init__, can be overridden

    def __post_init__(self) -> None:
        if self.top_k > self._MAX_TOP_K:
            raise ValueError(f"top_k must be <= {self._MAX_TOP_K}")

# Caller bypasses the guard:
cfg = RuntimeOverrides(_MAX_TOP_K=9999, top_k=9999)  # No error raised
```

## Solution

Annotate the constant with `ClassVar`. `ClassVar` fields are:
- Excluded from `__init__` (cannot be passed as constructor argument)
- Excluded from `dataclasses.fields()` (invisible to Hydra/OmegaConf)
- Excluded from `__eq__` and `__repr__`

```python
from dataclasses import dataclass
from typing import ClassVar


@dataclass
class RuntimeOverrides:
    _MAX_TOP_K: ClassVar[int] = 500   # CORRECT: class-level constant

    top_k: int = 10

    def __post_init__(self) -> None:
        if self.top_k > self._MAX_TOP_K:
            raise ValueError(
                f"top_k must be <= {self._MAX_TOP_K}, got {self.top_k}"
            )
```

## Verification

```python
import dataclasses

# ClassVar fields are excluded from fields()
assert "_MAX_TOP_K" not in {f.name for f in dataclasses.fields(RuntimeOverrides)}

# Cannot be passed at construction time
try:
    RuntimeOverrides(_MAX_TOP_K=9999)  # type: ignore[call-arg]
    assert False, "Should have raised TypeError"
except TypeError:
    pass  # Correct

# Guard still works
try:
    RuntimeOverrides(top_k=9999)
    assert False, "Should have raised ValueError"
except ValueError:
    pass  # Correct
```

## When to Use `ClassVar`

Use `ClassVar` for:
- Hard ceilings / limits enforced in `__post_init__`
- Lookup tables or sets (`_VALID_MODES: ClassVar[frozenset[str]] = ...`)
- Compiled regex patterns (`_RE: ClassVar[re.Pattern] = re.compile(...)`)
- Counters or registries shared across instances

Do NOT use `ClassVar` for fields that should vary per-instance or be
overridable via Hydra CLI.

## Anti-Patterns

- `_MAX_TOP_K: int = 500` — looks private, but is an `__init__` param
- `MAX_TOP_K = 500` — no type annotation; mypy treats it as a plain attribute,
  not a ClassVar; Hydra may still try to compose it
- `field(default=500, init=False)` — correct for per-instance non-init fields,
  but still shows up in `dataclasses.fields()` and may confuse config tooling;
  prefer `ClassVar` for true class-level constants
