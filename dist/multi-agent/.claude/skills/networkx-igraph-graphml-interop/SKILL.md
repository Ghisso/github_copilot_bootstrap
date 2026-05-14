---
name: networkx-igraph-graphml-interop
description: |
  Fix two related problems when comparing NetworkX graphs against igraph/R-exported
  GraphML files, or when exporting NetworkX graphs to GraphML:
  1. edge_recall=0 despite visually correct output (opaque vs semantic node IDs)
  2. GraphML export fails with XML parse errors (illegal control characters from OCR)
version: 1.0.0
user-invocable: false
---

## Problem 1: Cross-Format Node ID Comparison Gives 0% Recall

igraph writes GraphML with opaque integer node IDs (`n0`, `n1`, `n2`, ...):
```xml
<node id="n0"><data key="body">S</data><data key="res_no">1</data></node>
<edge source="n0" target="n1"/>
```

NetworkX uses semantic IDs (`res_S_1`, `res_S_1973`). Direct edge-set intersection
is always empty — recall = 0% — even when the graphs are semantically identical.

## Problem 2: OCR Data Breaks GraphML XML

CSV/OCR columns often contain control characters (`\x00-\x08`, `\x0b`, `\x0c`,
`\x0e-\x1f`) that are illegal in XML 1.0. `write_graphml` embeds these verbatim,
causing downstream parsers to fail with `ParseError: not well-formed`. Full-text
columns also inflate file size (10 KB × 2,800 nodes = 28 MB).

---

## Fix 1: Normalize Both Graphs to Attribute-Based Keys

Parse node attributes from the igraph GraphML (`body`, `res_no` stored as data elements),
build `(body, res_no)` tuple keys for each edge in both graphs, then intersect.

```python
import re
import networkx as nx
from pathlib import Path

_RE_S_ID = re.compile(r"^res_S_(\d+)$")
_RE_A_ID = re.compile(r"^res_A_(?:\d+_)?(\d+)$")


@staticmethod
def _ref_node_key(attrs: dict[str, object]) -> tuple[str, int] | None:
    """Map igraph GraphML node attributes to (body, res_no) key."""
    body = attrs.get("body", "S")
    res_no = attrs.get("res_no")
    if res_no is None:
        return None
    try:
        return (str(body), int(str(res_no)))
    except (ValueError, TypeError):
        return None


@staticmethod
def _gen_node_key(node_id: str) -> tuple[str, int] | None:
    """Map semantic node ID to (body, res_no) key."""
    if node_id.startswith("res_S_"):
        try:
            return ("S", int(node_id[6:]))
        except ValueError:
            return None
    if node_id.startswith("res_A_"):
        parts = node_id[6:].split("_")
        try:
            return ("A", int(parts[-1]))
        except (ValueError, IndexError):
            return None
    return None


def compare_graphs(generated: nx.DiGraph, ref_path: Path) -> dict[str, float]:
    ref_graph = nx.read_graphml(str(ref_path))

    ref_edges: set[tuple[tuple[str, int], tuple[str, int]]] = set()
    for src_id, tgt_id in ref_graph.edges():
        src_key = _ref_node_key(ref_graph.nodes[src_id])
        tgt_key = _ref_node_key(ref_graph.nodes[tgt_id])
        if src_key and tgt_key:
            ref_edges.add((src_key, tgt_key))

    gen_edges: set[tuple[tuple[str, int], tuple[str, int]]] = set()
    for src_id, tgt_id in generated.edges():
        src_key = _gen_node_key(src_id)
        tgt_key = _gen_node_key(tgt_id)
        if src_key and tgt_key:
            gen_edges.add((src_key, tgt_key))

    matched = gen_edges & ref_edges
    return {
        "edge_recall": len(matched) / len(ref_edges) if ref_edges else 0.0,
        "edge_precision": len(matched) / len(gen_edges) if gen_edges else 0.0,
    }
```

**Key insights:**
- igraph GraphML stores `body` and `res_no` as node data elements; NetworkX reads
  them as `graph.nodes[node_id]["body"]` — **without** any `v_` prefix (NetworkX strips it).
- `res_no` arrives as a string from GraphML — use `int(str(res_no))`, not
  `int(float(str(res_no)))`. The float intermediate silently converts `"NaN"` → `0`
  and scientific notation `"1e4"` → `10000`.

---

## Fix 2: Exclude Large Text Columns and Sanitize Control Chars

Two-part defence — both are needed:

```python
import re
import pandas as pd

# Part A: Exclude full-text and large columns entirely from node attrs.
_SKIP_NODE_ATTRS: frozenset[str] = frozenset({
    "text",           # full resolution text (OCR output)
    "text_draft",     # draft text column
    "text_meeting",   # meeting record text
    "text_len",       # derived numeric (not in reference GraphML)
})

# Part B: Strip XML 1.0 illegal control characters from remaining strings.
# Covers \x00-\x08, \x0b, \x0c, \x0e-\x1f (tab \x09, LF \x0a, CR \x0d are OK).
_CTRL_CHAR_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

# In _build_nodes():
keep_cols = [c for c in df.columns if c not in _SKIP_NODE_ATTRS]

for _, row in df.iterrows():
    attrs: dict[str, object] = {}
    for col in keep_cols:
        val = row[col]
        if isinstance(val, bool):
            attrs[col] = bool(val)
        elif pd.isna(val) if not isinstance(val, (bool, str)) else False:
            attrs[col] = ""
        elif isinstance(val, str):
            attrs[col] = _CTRL_CHAR_RE.sub("", val)
        else:
            attrs[col] = val
    graph.add_node(node_id, **attrs)
```

**Note:** `<`, `>`, `&` in strings are safe — `xml.etree.ElementTree` escapes them.
Only control chars in `\x00-\x1f` (minus tab, LF, CR) are problematic.

---

## Verification

```python
# Fix 1: recall > 0
stats = compare_graphs(generated_graph, Path("reference.graphml"))
assert stats["edge_recall"] > 0.0, "Still getting 0 recall — check attribute names"

# Fix 2: valid XML
import xml.etree.ElementTree as ET
nx.write_graphml(graph, "out.graphml")
ET.parse("out.graphml")  # raises ParseError if control chars remain
```

Expected metrics on UNSC 2025 dataset:
- `edge_recall ≈ 0.97`
- `edge_precision ≈ 0.88`
