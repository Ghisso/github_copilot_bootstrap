---
name: graph-schema-compat-migration
description: |
  Safely migrate graph node/edge attribute keys without breaking existing retrieval/tests.
  Trigger when refactoring graph schema keys (for example `type` -> `entity_type` or
  `relation` -> `relation_type`) and seeing errors like:
  - `KeyError: 'type'`
  - `KeyError: 'relation'`
  - Traversal/retriever logic silently missing relations after key rename
user-invocable: false
---

## Problem

Refactoring graph schema keys in builders or retrievers can break backward compatibility across tests, merge logic, and downstream consumers that still read old keys. Direct key replacement often causes runtime regressions and partial semantic loss.

## Context / Trigger Conditions

Use this skill when any of the following appears during graph refactors:

- Test failures such as `KeyError: 'type'` or `KeyError: 'relation'`
- New graph builder writes `entity_type` / `relation_type`, while existing code reads `type` / `relation`
- Retriever/context logic no longer detects relation edges after migration
- Multiple graph sources (for example CSV + text extraction) emit mixed key schemas

## Solution

1. Introduce canonical keys but keep aliases during transition.

```python
# Node write path
graph.add_node(node_id, entity_type=etype, type=etype, ...)

# Edge write path
graph.add_edge(src, dst, relation_type=rel, relation=rel, ...)
```

2. Read through a normalization helper in consumers.

```python
def node_entity_type(data: dict) -> str:
    value = data.get("entity_type")
    if value is None:
        value = data.get("type")
    return str(value or "")

def edge_relation_type(data: dict) -> str:
    value = data.get("relation_type")
    if value is None:
        value = data.get("relation")
    return str(value or "")
```

3. Keep collision checks aligned with canonical key first, alias second.

```python
existing = edge_data.get("relation_type")
if existing is None:
    existing = edge_data.get("relation")
```

4. Add transition tests that assert both compatibility and canonical behavior.
- Existing tests expecting legacy keys still pass.
- New tests verify canonical keys are present.
- Retriever/traversal tests verify relation-aware paths still fire.

5. Defer alias removal until all producers/consumers are migrated and validated.

## Verification

Run:

```bash
uv run pytest tests/graph/test_text_graph_builder.py tests/graph/test_graph_retriever.py -q --tb=short
uv run pytest tests/ -q --tb=short
uv run mypy src/ --ignore-missing-imports --explicit-package-bases
uv run ruff check src/ tests/
```

Success criteria:

- No `KeyError` for legacy keys
- Relation-aware retrieval behavior unchanged
- Full suite green before alias cleanup

## Example

A migration changed `TextGraphBuilder` edges from `relation` to `relation_type` and nodes from `type` to `entity_type`. Existing tests failed with:
- `KeyError: 'type'`
- `KeyError: 'relation'`

Fix: write both key forms during transition and use read-normalization helpers in retriever/entity matcher. After patch, graph tests and full suite passed.