---
name: pyvis-xss-testing
visibility: background
description: |
  Correctly test HTML escaping in pyvis-generated visualizations. Triggers:
  - Writing tests that assert `&lt;script&gt;` appears in pyvis HTML output
  - XSS escaping tests that pass in unit tests but fail against real pyvis output
  - pyvis double-encodes HTML entities via JSON serialization
version: 1.0.0
user-invocable: false
---

## Problem

Naive assertions like `assert "&lt;script&gt;" in content` fail because pyvis
further JSON-encodes HTML entities. `html.escape()` produces `&lt;script&gt;`,
but pyvis serializes this into JavaScript as `\u0026lt;script\u0026gt;`.

A test that checks `html.escape()` directly (stdlib) passes but doesn't exercise
production code — it tests the standard library, not your escaping logic.

Asserting only that the raw payload is **absent** is necessary but not
sufficient: absence from one specific serialized form does not prove what a
browser actually renders. Prove the escaping boundary you rely on instead —
decode the serialized value back to what vis.js receives, or exercise the
real rendering sink (a browser or a DOM parser).

## Solution

Assert against the actual escaping boundary in addition to the raw-absence
check:

```python
import json
import re
from html import escape


def test_html_special_chars_escaped_in_output(self, visualizer, tmp_path) -> None:
    """Node labels with HTML-special characters are escaped in visualizer output."""
    g = nx.DiGraph()
    raw_payload = '<script>alert("xss")</script>'
    title_text = "XSS Test & <script>"
    g.add_node(
        "res_xss",
        label=raw_payload,
        entity_type="Resolution",
        year=2001,
        symbol="S/RES/XSS",
        title=title_text,
    )
    path = visualizer.visualize_subgraph(g)
    content = Path(path).read_text()

    # DO: Assert raw XSS payload is absent (necessary, not sufficient)
    assert raw_payload not in content, "Unescaped XSS payload found in HTML output"

    # DO: Assert content wasn't silently dropped
    assert "alert" in content, "Label content missing from output"

    # DO: Decode the actual vis.js "title" payload and check the boundary
    # being relied on. vis.js renders `title` via innerHTML — the real XSS
    # sink — so the calling application must HTML-escape it before handing it
    # to pyvis. pyvis escapes neither `title` nor `label`; Jinja2's `tojson`
    # JavaScript-source-escapes the already-escaped string for its script
    # context. json.loads() is what the DOM receives, and it must equal the
    # escaped form, never the raw text. (`label` is canvas-rendered, not an
    # HTML sink, so it is JSON-escaped only, with no HTML-escaping needed.)
    match = re.search(r'"title":\s*(".*?")', content)
    assert match, "title field missing from vis.js payload"
    assert json.loads(match.group(1)) == escape(title_text), (
        "decoded title does not match the expected HTML-escaped form"
    )

    # DON'T: Assert specific escaped form — pyvis double-encodes via JSON
    # assert "&lt;script&gt;" in content  # FAILS: pyvis produces \u0026lt;
```

For assurance that a browser never executes the payload, drive `path` through
a real renderer (a headless browser, or an HTML/DOM parser that resolves
entities the way a browser does) and assert no unescaped `<script>` node
appears in the parsed DOM. Decoding the serialized value is a fast, strong
proxy for that; it is not a substitute when the rendering sink itself (for
example an `innerHTML` assignment) is the thing actually under test.

## Why This Works

1. **Tests production code** — calls `visualize_subgraph()`, not `html.escape()`
2. **Encoding-agnostic** — doesn't assume a specific escaping scheme
3. **Covers the real threat** — if raw `<script>` appears, XSS is possible
4. **Verifies content preserved** — the `"alert"` check ensures data wasn't dropped
5. **Proves the escaping boundary** — decoding the vis.js payload confirms
   what the renderer actually receives, not just what is absent

## What pyvis Actually Produces

The vis.js data payload in pyvis HTML looks like:
```javascript
nodes = new vis.DataSet([{
    "id": "res_xss",
    "label": "\\u003cscript\\u003ealert",
    "title": "\\u003cb\\u003e\\u0026lt;script\\u0026gt;..."
}]);
```

The raw `<script>` never appears — it is either HTML-escaped by your code and
then JavaScript-source-escaped by Jinja2's `tojson`, or canvas-rendered by
vis.js (labels).

## Anti-Patterns

- **Testing `html.escape()` directly** — tests stdlib, not your code
- **Asserting `&lt;` in pyvis output** — fails due to JSON double-encoding
- **Asserting `\u0026lt;` in output** — brittle, ties test to serialization implementation
