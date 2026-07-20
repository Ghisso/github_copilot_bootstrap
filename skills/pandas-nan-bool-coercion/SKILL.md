---
name: pandas-nan-bool-coercion
visibility: background
description: |
  Fix silent NaN/bool coercion bugs in pandas DataFrames. Triggers:
  - `bool(float('nan'))` returns True (false positive in boolean checks)
  - `numpy.bool_(True) is True` returns False (identity comparison fails)
  - CSV boolean columns read as float64 with NaN values
  - Vote counts treated as truthy when they should be zero/missing
user-invocable: false
---

## Problem

Three related pitfalls when working with pandas boolean/integer columns from CSV:

**1. NaN is truthy**
```python
bool(float("nan"))  # True — NaN coerces to True!
df["voted"].fillna(False).astype(bool)  # NaN → True if not handled first
```

**2. numpy.bool_ is not Python bool**
```python
import numpy as np
np.bool_(True) is True   # False — different identity
np.bool_(True) == True   # True — equality works
isinstance(np.bool_(True), bool)  # True — isinstance works
```

**3. CSV integer columns become float64 (with NaN)**
```python
# votes_yes column: [5, 3, NaN, 12]
# pandas reads as float64: [5.0, 3.0, nan, 12.0]
df["votes_yes"].dtype  # float64, not int64
int(df["votes_yes"][2])  # ValueError: cannot convert float NaN to integer
```

## Solution

Use a `_safe_int` helper that checks for NaN before conversion:

```python
import math
import numpy as np
import pandas as pd


def _safe_int(value: object) -> int:
    """Convert value to int, returning 0 for NaN/None/empty."""
    if value is None:
        return 0
    if isinstance(value, str) and not value.strip():
        return 0
    try:
        if pd.isna(value):  # handles float NaN, numpy NaN, pd.NA
            return 0
    except (TypeError, ValueError):
        pass  # pd.isna raises on non-scalar types
    return int(value)
```

For boolean columns that may contain NaN:

```python
def _safe_bool(value: object) -> bool:
    """Convert value to bool, treating NaN/None as False."""
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    return bool(value)
```

## Verification

```python
assert _safe_int(None) == 0
assert _safe_int("") == 0
assert _safe_int(float("nan")) == 0
assert _safe_int(np.nan) == 0
assert _safe_int(pd.NA) == 0
assert _safe_int(5.0) == 5
assert _safe_int(np.int64(7)) == 7

assert _safe_bool(float("nan")) is False
assert _safe_bool(None) is False
assert _safe_bool(np.bool_(True)) is True   # works via bool()
assert _safe_bool(1.0) is True
```

## Anti-Patterns

- **`int(row["votes"])` directly** — raises on NaN
- **`bool(row["flag"])` directly** — NaN becomes True (false positive)
- **`row["flag"] is True`** — fails for numpy.bool_; use `== True` or `bool()`
- **`df["col"].fillna(0).astype(int)`** — correct for batch, but `_safe_int`
  is needed for row-by-row iteration
- **`if row["col"]:`** — NaN truthy, 0 falsy — use `_safe_bool` / `_safe_int`
