---
name: domain-type-placement
visibility: background
description: |
  Where to place shared Python types (dataclasses, TypedDicts, protocols) in a
  layered codebase. Use when:
  - A type is imported by multiple layers (e.g., both eval/ and retrieval/)
  - A reviewer flags a layer violation (e.g., eval → retrieval import)
  - Deciding where a new shared type should live
  - Refactoring to remove cross-layer coupling
user-invocable: false
---

# Domain Type Placement

## Problem

When a type (dataclass, TypedDict, Protocol) is needed by two or more layers,
placing it in one layer creates an import dependency on that layer from every
other consumer. This creates coupling that makes layers harder to test, swap,
or evolve independently.

**Example violation:**
```python
# src/eval/protocols.py
from src.retrieval.types import QueryResult  # eval → retrieval coupling ❌
```

The eval layer now cannot be used without importing the retrieval layer.

## Context / Trigger Conditions

- Reviewer flags "layer violation" or cross-layer coupling
- A type appears in both `src/X/` and `src/Y/` imports
- Circular import errors between feature modules
- Adding a new type that will be used by 2+ modules

## Solution

### Step 1: Identify the type

Look for any dataclass/TypedDict/Protocol used in more than one top-level
`src/` subdirectory.

### Step 2: Create in `src/domain/`

```python
# src/domain/query_result.py
from dataclasses import dataclass, field
from haystack import Document


@dataclass
class QueryResult:
    """Result returned by RAG pipeline query execution."""

    documents: list[Document] = field(default_factory=list)
    answer: str = ""
    metadata: dict = field(default_factory=dict)
```

### Step 3: Re-export from origin for backward compatibility

```python
# src/retrieval/types.py (original location)
# Re-export for backward compatibility — canonical location is src/domain/
from src.domain.query_result import QueryResult as QueryResult  # noqa: F401

# Remove old definition
```

### Step 4: Update imports in consumer modules

```python
# src/eval/protocols.py
from src.domain.query_result import QueryResult  # ✅ no layer coupling
```

### Step 5: Verify

```bash
uv run mypy src/ --ignore-missing-imports --explicit-package-bases
uv run pytest tests/ -q
```

## What Belongs in `src/domain/`

| Type | Example | Move to domain? |
|------|---------|-----------------|
| Cross-layer result types | `QueryResult`, `EvalRow` | Yes |
| Shared protocols/ABCs | `RagComponent` protocol | Yes |
| Feature-internal types | `IndexingState`, `ChunkBuffer` | No |
| Config dataclasses | `EvalConfig`, `RetrievalConfig` | No (stay in `src/configs/`) |
| API models | `QueryRequest`, `QueryResponse` | No (stay in `src/api/`) |

## Rule of Thumb

> If removing a module from `src/X/` would break an import in `src/Y/` for
> a type definition (not a function call), that type belongs in `src/domain/`.

## Verification

```bash
# Check for cross-layer type imports
grep -r "from src\.\(retrieval\|embed\|ingestion\)" src/eval/ | grep "import.*[A-Z]"
```

Any uppercase (class) import from a sibling feature layer is a candidate for `src/domain/`.

## Example

```
Before:
  src/retrieval/types.py       → defines QueryResult
  src/eval/protocols.py        → from src.retrieval.types import QueryResult  ❌

After:
  src/domain/query_result.py   → defines QueryResult  ✅
  src/retrieval/types.py       → re-exports QueryResult (backward compat)
  src/eval/protocols.py        → from src.domain.query_result import QueryResult  ✅
```
