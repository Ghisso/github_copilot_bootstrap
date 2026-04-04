---
name: pyvis-xss-testing
description: |
  Correctly test HTML escaping in pyvis-generated visualizations. Triggers:
  - Writing tests that assert `&lt;script&gt;` appears in pyvis HTML output
  - XSS escaping tests that pass in unit tests but fail against real pyvis output
  - pyvis double-encodes HTML entities via JSON serialization
version: 1.0.0
---

## Problem

Naive assertions like `assert "&lt;script&gt;" in content` fail because pyvis
further JSON-encodes HTML entities. `html.escape()` produces `&lt;script&gt;`,
but pyvis serializes this into JavaScript as `\u0026lt;script\u0026gt;`.

A test that checks `html.escape()` directly (stdlib) passes but doesn't exercise
production code — it tests the standard library, not your escaping logic.

## Solution

Assert the **raw payload is absent**, not that a specific escaped form is present:

```python
def test_html_special_chars_escaped_in_output(self, visualizer, tmp_path) -> None:
    """Node labels with HTML-special characters are escaped in visualizer output."""
    g = nx.DiGraph()
    g.add_node(
        "res_xss",
        label='<script>alert("xss")</script>',
        entity_type="Resolution",
        year=2001,
        symbol="S/RES/XSS",
        title='XSS Test & <script>',
    )
    path = visualizer.visualize_subgraph(g)
    content = Path(path).read_text()

    # DO: Assert raw XSS payload is absent
    raw_payload = '<script>alert("xss")</script>'
    assert raw_payload not in content, "Unescaped XSS payload found in HTML output"

    # DO: Assert content wasn't silently dropped
    assert "alert" in content, "Label content missing from output"

    # DON'T: Assert specific escaped form — pyvis double-encodes via JSON
    # assert "&lt;script&gt;" in content  # FAILS: pyvis produces \u0026lt;
```

## Why This Works

1. **Tests production code** — calls `visualize_subgraph()`, not `html.escape()`
2. **Encoding-agnostic** — doesn't assume a specific escaping scheme
3. **Covers the real threat** — if raw `<script>` appears, XSS is possible
4. **Verifies content preserved** — the `"alert"` check ensures data wasn't dropped

## What pyvis Actually Produces

The vis.js data payload in pyvis HTML looks like:
```javascript
nodes = new vis.DataSet([{
    "id": "res_xss",
    "label": "\\u003cscript\\u003ealert",
    "title": "\\u003cb\\u003e\\u0026lt;script\\u0026gt;..."
}]);
```

The raw `<script>` never appears — it's either HTML-escaped by your code, then
JSON-escaped by pyvis, or canvas-rendered by vis.js (labels).

## Anti-Patterns

- **Testing `html.escape()` directly** — tests stdlib, not your code
- **Asserting `&lt;` in pyvis output** — fails due to JSON double-encoding
- **Asserting `\u0026lt;` in output** — brittle, ties test to serialization implementation
