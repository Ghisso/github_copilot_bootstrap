---
name: test-helper-public-api
description: |
  Prevent test helpers that chain private methods from hiding bugs in public APIs.
  Trigger: A test helper directly calls _build_nodes(), _extract_foo(), etc.
  instead of the public method. Symptom: Tests pass even when a bug is introduced
  in the public method (wrong step order, missing state update, etc.).
user-invocable: false
---

## Problem

Test helpers that bypass the public API by chaining private methods provide
false confidence — they verify internals in isolation but never exercise the
public method that real callers use.

```python
# BAD — bypasses build_from_dataframe() entirely
def _builder_with_df(df, config):
    builder = MyBuilder(config)
    builder._build_nodes(df)          # private
    citations = builder._extract(df)  # private
    builder._add_edges(citations)     # private
    builder._build_complete = True    # private
    return builder._graph             # private

# If build_from_dataframe() has a bug (e.g. wrong step order),
# all tests using this helper will still pass.
```

## Solution

Make the test helper call the public API:

```python
# GOOD — tests the real code path
def _builder_with_df(df: pd.DataFrame, config: MyConfig) -> nx.DiGraph:
    """Build a graph by calling the public build_from_dataframe() API."""
    builder = MyBuilder(config)
    return builder.build_from_dataframe(df)
```

If no suitable public method exists, add one:

```python
class MyBuilder:
    def build(self) -> Result:
        """Load data and build. Public CLI entry point."""
        return self.build_from_dataframe(self._load_data())

    def build_from_dataframe(self, df: pd.DataFrame) -> Result:
        """Build from an already-loaded DataFrame. Public API for tests."""
        self._build_nodes(df)
        citations = self._extract(df)
        self._add_edges(citations)
        self._build_complete = True
        return self._graph
```

**Rule:** A test helper should call the narrowest PUBLIC method that covers the
functionality being tested. If none exists, add one.

## Verification

After refactoring to use the public API, intentionally break the method to
confirm tests catch it:

```python
def build_from_dataframe(self, df):
    # Deliberately wrong order — tests should now fail
    self._add_edges({})    # edges before nodes — should raise KeyError
    self._build_nodes(df)
    return self._graph
```

If tests still pass, the helper isn't calling the public method.

## Example

From the UNSC citation graph pipeline:

```python
# Before
def _builder_with_df(df, cfg):
    builder = CitationGraphBuilder(cfg)
    builder._build_nodes(df)
    citations = builder._extract_all_citations(df)
    builder._add_citation_edges(citations)
    builder._build_complete = True
    return builder._graph

# After
def _builder_with_df(df, cfg):
    """Build a graph by calling the public build_from_dataframe() API."""
    builder = CitationGraphBuilder(cfg)
    return builder.build_from_dataframe(df)
```

This was caught by the architecture reviewer (not the code reviewer) — it shows
up as "no public seam for injection." The fix also simplified comparison tests
that were using two different builder instances.

## Related

- See `testing-patterns/SKILL.md` for general pytest patterns.
