---
name: data-and-graph-pitfalls
visibility: public
description: |
  Data and graph pitfalls: pandas NaN and numpy bool coercion, NetworkX versus
  igraph GraphML node IDs and control characters, pyvis XSS escaping tests, and
  CSV-driven integration tests. Use when one of these bugs appears or such a
  test is being built.
---

# Data and Graph Pitfalls

Four short lessons from past bugs. Read only the reference that matches the
task; each is a file in this skill's `references/` folder.

**pandas NaN and bool coercion.** Read `references/pandas-nan-bool.md` when
`bool(float("nan"))` is `True`, an `is True` check fails on a `numpy.bool_`, or
CSV integer or boolean columns arrive as `float64` with NaN.

**GraphML interop.** Read `references/graphml-interop.md` when a NetworkX graph
compared against an igraph- or R-exported GraphML file gives `edge_recall=0`
(opaque versus semantic node IDs), or when a GraphML export fails with XML parse
errors from control characters.

**pyvis XSS tests.** Read `references/pyvis-xss.md` when writing or reviewing a
test that asserts HTML escaping in pyvis output, or when such a test passes in
unit tests but fails against real pyvis output.

**CSV-driven integration tests.** Read `references/csv-driven-tests.md` when
building a CSV test dataset with expected outputs and `pytest` parametrize for a
classifier, router, or SQL generator. `references/csv-case-study.md` is a worked
example; read it only for the before and after numbers.
