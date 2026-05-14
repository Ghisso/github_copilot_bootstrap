---
name: documentation
description: |
  Apply consistent documentation standards: Google-style docstrings for all
  public classes and functions, structured README.md, and docs/ directory
  layout. Use when writing or reviewing module documentation.
---

## Google-Style Docstrings

### Classes

```python
class ResolutionRetriever:
    """Retrieve UNSC resolutions using semantic or BM25 search.

    Attributes:
        store: The document store backing retrieval.
        top_k: Maximum number of documents to return.
        mode: Retrieval mode — "semantic", "bm25", or "hybrid".

    Example:
        retriever = ResolutionRetriever(store, top_k=5, mode="semantic")
        docs = retriever.retrieve("sanctions on North Korea")
    """

    def __init__(self, store: DocumentStore, top_k: int = 5, mode: str = "semantic") -> None:
        ...
```

### Functions

```python
def chunk_resolution(text: str, chunk_size: int = 512) -> list[str]:
    """Split a resolution text into overlapping chunks.

    Args:
        text: Full resolution text. Must be non-empty.
        chunk_size: Target size of each chunk in tokens.

    Returns:
        List of text chunks, each ≤ chunk_size tokens with 10% overlap.

    Raises:
        ValueError: If text is empty or chunk_size < 64.

    Example:
        chunks = chunk_resolution(resolution_text, chunk_size=256)
        print(len(chunks))  # → 4
    """
    ...
```

### Omit docstrings for

- Private methods (`_method`)
- One-liner property getters
- Test functions (use descriptive names instead)
- `__init__` when the class docstring covers it

---

## README.md Structure

```markdown
# Project Name

One-sentence description of what this project does.

## Quick Start

Minimal working example — get to "hello world" in < 5 commands.

## Installation

```bash
uv sync
```

## Usage

Most common use cases with runnable examples.

## Configuration

Link to docs/CONFIGURATION.md.

## Development

How to run tests, linting, and type checking.

## License
```

---

## docs/ Directory Layout

| File | Content |
|------|---------|
| `QUICK_REFERENCE.md` | Commands cheat sheet — no prose |
| `CONFIGURATION.md` | All config options, env vars, defaults |
| `DEPLOYMENT.md` | Docker, BentoML, cloud deploy steps |
| `ARCHITECTURE.md` | Component diagram, data flow, decisions |
| `API.md` | Endpoint reference (input/output schemas) |
| `TROUBLESHOOTING.md` | Known issues + fixes |

---

## Anti-Patterns

- **Redundant docstrings** — `def get_name(): """Get the name."""` — omit if obvious
- **Stale parameter docs** — update docstrings when signatures change
- **Missing Raises section** — always document exceptions the caller must handle
- **Wall of prose in README** — prefer tables and code blocks
- **Undocumented env vars** — every env var must appear in `CONFIGURATION.md`
