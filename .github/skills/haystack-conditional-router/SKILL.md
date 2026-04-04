---
name: haystack-conditional-router
description: |
  Wire Haystack ConditionalRouter correctly for multi-branch pipelines (semantic,
  SQL, hybrid). Triggers: output names causing silent skips, wrong route definitions
  per retriever mode, DocumentJoiner merging branches, SQL source metadata tagging.
---

## Rule 1: Output Names Must Exactly Match Downstream Input Names

A typo in `output_name` causes the route to silently fire with no data reaching
the downstream component — no error, no output.

```python
from haystack.components.routers import ConditionalRouter

routes = [
    {
        "condition": "{{ route == 'semantic' }}",
        "output": "{{ query }}",
        "output_name": "semantic_query",      # MUST match add_component() name
        "output_type": str,
    },
    {
        "condition": "{{ route == 'sql' }}",
        "output": "{{ query }}",
        "output_name": "sql_query",           # MUST match add_component() name
        "output_type": str,
    },
]
pipeline.add_component("query_router", ConditionalRouter(routes=routes))
pipeline.connect("query_router.semantic_query", "embedder.text")   # exact match
pipeline.connect("query_router.sql_query", "text_to_sql.query")    # exact match
```

---

## Rule 2: Routes Are Mode-Dependent

Each retriever mode (`semantic`, `bm25`, `hybrid`) uses different component names.
Define separate routes per mode rather than trying to share a single route definition:

```python
def _build_routes(mode: str) -> list[dict]:
    if mode == "semantic":
        return [
            {"condition": "{{ route == 'semantic' or route == 'both' }}",
             "output": "{{ query }}", "output_name": "semantic_query", "output_type": str},
            {"condition": "{{ route == 'sql' or route == 'both' }}",
             "output": "{{ query }}", "output_name": "sql_query", "output_type": str},
        ]
    elif mode == "bm25":
        return [
            {"condition": "{{ route == 'semantic' or route == 'both' }}",
             "output": "{{ query }}", "output_name": "bm25_query", "output_type": str},
            {"condition": "{{ route == 'sql' or route == 'both' }}",
             "output": "{{ query }}", "output_name": "sql_query", "output_type": str},
        ]
    # etc.
```

Use separate OR-condition routes per branch instead of list-valued `output_name`.

---

## Rule 3: DocumentJoiner Merges Branches

Both branches must converge at a single `DocumentJoiner`:

```python
from haystack.components.joiners import DocumentJoiner

pipeline.add_component("result_joiner", DocumentJoiner())

pipeline.connect("retriever.documents", "result_joiner.documents")
pipeline.connect("text_to_sql.documents", "result_joiner.documents")
pipeline.connect("result_joiner.documents", "prompt_builder.documents")
```

**Haystack lazy execution:** When `sql_query` output doesn't fire, `text_to_sql`
never receives input, never runs, and `result_joiner` receives documents only from
the retrieval branch. This is correct — Haystack skips components with no inputs.

---

## Rule 4: Always-Direct Inputs (Not Routed)

Some inputs must always be provided regardless of route:

```python
inputs = {
    "prompt_builder": {"query": text},   # always needed — NOT routed
}
if ranker_enabled:
    inputs["ranker"] = {"query": text}   # always needed for re-ranking

# Only the branch-selecting input goes through the router
inputs["query_router"] = {"query": text, "route": route}
```

---

## Rule 5: Tag SQL Documents for Downstream Handling

SQL results bypass soft filters (already constrained by WHERE clauses):

```python
# In TextToSQLQuerier._to_documents():
doc = Document(content=content, meta={"source": "sql", ...})

# In downstream soft filter stage:
sql_docs = [d for d in docs if d.meta.get("source") == "sql"]
non_sql_docs = [d for d in docs if d.meta.get("source") != "sql"]
filtered = apply_soft_filters(non_sql_docs) + sql_docs  # SQL bypasses filters
```

---

## Rule 6: SQL Route Has No Fallback

SQL queries either succeed or don't — there are no filters to relax:

```python
if route == "sql":
    pass                # No progressive fallback
elif route == "both":
    pass                # Fallback only applies to semantic branch
else:
    # Standard progressive fallback for semantic only
    ...
```

---

## Verification

```python
def test_semantic_route_skips_sql(pipeline):
    result = pipeline.run({
        "query_router": {"query": "summarize resolution", "route": "semantic"},
        "prompt_builder": {"query": "summarize resolution"},
    })
    assert all(d.meta.get("source") != "sql" for d in result["documents"])

def test_sql_route_skips_retrieval(pipeline):
    result = pipeline.run({
        "query_router": {"query": "count resolutions", "route": "sql"},
        "prompt_builder": {"query": "count resolutions"},
    })
    assert all(d.meta.get("source") == "sql" for d in result["documents"])
```

## Known Pitfalls

- BM25 mode names the retriever `"retriever"` (not `"bm25_retriever"`)
- Hybrid mode has an inner `"joiner"` (embedder+bm25) AND an outer `"result_joiner"` (semantic+sql)
- `prompt_builder.query` is always a direct pipeline input, never routed
