---
applicability:
  - src/**/*.py
  - tests/**/*.py
---

# Code Standards

> **Most style rules are enforced by ruff (pyproject.toml).** This file covers only what ruff cannot check: naming, architecture patterns, and deprecation protocol.

---

## What ruff Enforces (see pyproject.toml)

- **I**: Import ordering (stdlib → third-party → local)
- **UP**: `List`→`list`, `Optional[X]`→`X | None`, deprecated stdlib usage
- **D**: Google-style docstrings on public classes and functions
- **G**: `%`-formatting in logging (no f-strings)
- **S/B**: Security and common bugs
- **SIM/C4**: Simplification and comprehension style

Run `uv run python .claude/scripts/verify.py fast --format json` — zero
violations required before commit. `fast` selects the repository's real
scope instead of assuming a `src/` layout, so it stays correct whether this
file attached because of a `src/**/*.py` or a `tests/**/*.py` match.

---

## Naming Conventions (not ruff-enforceable)

- **Classes**: `PascalCase` — `RagBuilder`, `QueryConfig`
- **Functions/methods**: `snake_case` — `build_async`, `query_system`
- **Async variants**: `_async` suffix when sync version exists
- **Private**: `_leading_underscore`
- **Constants**: `UPPER_SNAKE_CASE`

---

## Architecture Patterns

- **Config-first**: dataclasses in `src/configs/` with `__post_init__` validation before feature code
- **Builder pattern**: `from_config(cfg)` factory method on consuming classes
- **Composition over inheritance**
- **`pathlib.Path`** for all file ops (never `os.path`)
- **Context managers** (`with`) for all resources
- **`ClassVar`** for dataclass class-level constants (prevent `__init__` override attacks)
- **`from __future__ import annotations`**: fine in general modules (scripts, services, tests), but NEVER in Hydra-managed config/dataclass modules (`src/configs/**` and any ConfigStore-registered dataclass) — it stringizes annotations and breaks Hydra's dataclass introspection in Python 3.12+

## Anti-Patterns (prohibited)

- **`import argparse`** — forbidden in `src/` and `gradio_app/`; use Hydra ConfigStore CLI overrides for all production entrypoints. Test harnesses (`tests/`) are the only allowed exception.
- **YAML config files** — all config variants as Python dataclasses only (pure ConfigStore)
- **Ad-hoc `os.getenv()` arg parsing** — use Hydra config fields with env-var defaults only at system boundaries (service.py / BentoML)

---

## Error Handling

```python
try:
    result = create_pipeline(config)
except ValueError as e:
    logger.error("Invalid config: %s", e)
    raise RuntimeError("Pipeline creation failed") from e
```

Always chain exceptions with `from e`. Use specific exception types.

---

## Deprecation Protocol

**Never ignore deprecation warnings. Stop and fix immediately.**

1. Identify deprecated API from warning message
2. Find replacement in library docs/changelog
3. Update imports and usage
4. Run `uv run pytest tests/ -q` — verify no new warnings
5. Add `[LEARN:deprecation]` entry to `.claude/MEMORY.md`

Common sources: `datetime.utcnow()` → `datetime.now(UTC)`, Pydantic v1 validators → `field_validator`, `typing.Optional` → `X | None`.
