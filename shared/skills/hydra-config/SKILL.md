---
name: hydra-config
visibility: public
description: |
  Master Hydra-based hierarchical configuration management. Pure ConfigStore
  approach — all config variants as Python dataclasses, NO YAML files. Use
  when creating config groups, composing runtime profiles, validating configs,
  or scaffolding new config variants.
---

## Core Principles

1. **Pure ConfigStore** — all config variants are Python dataclasses registered with `ConfigStore`. No YAML files.
2. **Typed schemas** — use `config_path=None` in `@hydra.main`; register top-level configs with `cs.store(name=..., node=...)`.
3. **Fail early** — validate in `__post_init__` and CI.
4. **`_self_` first** — always first in defaults list so group variant values override dataclass defaults.
5. **`"mode": "RUN"`** — always include in the `hydra` dict to prevent `AssertionError`.
6. **`"none"` not `"disabled"`** — use `"none"` in logging overrides to fully disable Hydra logging interception.

## Quick Checklist

- [ ] Register with ConfigStore: `cs.store(group="<group>", name="<name>", node=MyConfig)`
- [ ] `config_path=None` in `@hydra.main`
- [ ] `_self_` **first** in defaults list (so group variant values override dataclass defaults)
- [ ] `"mode": "RUN"` in hydra dict
- [ ] Logging overrides use `"none"`: `{"override hydra/hydra_logging": "none"}`
- [ ] `output_subdir: None` and `run.dir: "."` to suppress Hydra output folders
- [ ] `from_config(cfg)` builder method on all runtime classes
- [ ] `cs = ConfigStore.instance()` + `cs.store()` directly after each dataclass (no wrapper functions)
- [ ] Top-level config contains ONLY composed dataclass fields (no bare primitives)

---

## Directory Pattern

```
src/configs/
    training_config.py      # Top-level dataclass for training.py
    __init__.py             # Imports config modules to trigger registration
  model/
    model_config.py       # ModelConfig + module-level cs.store()
  optimizer/
    optimizer_config.py   # OptimizerConfig + module-level cs.store()
```

## Top-Level Config

> **Rule:** The top-level config must ONLY contain composed dataclass fields.
> Name the top-level config after its owning entrypoint (for example `TrainingConfig`, `PdfIngestionConfig`, `EvaluationConfig`).
> Never put bare primitive fields (`str`, `int`, `bool`) directly on the top-level config class.
> Encapsulate all primitives in a category-specific dataclass first.

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RunConfig:
    """Runtime configuration."""
    experiment_name: str = "my_experiment"
    seed: int = 42


@dataclass
class TrainingConfig:
    run: RunConfig = field(default_factory=RunConfig)
    model: ModelConfig = field(default_factory=ModelConfig)
    optimizer: OptimizerConfig = field(default_factory=OptimizerConfig)

    defaults: list[Any] = field(
        default_factory=lambda: [
            "_self_",                                  # MUST be first
            {"model": "bert_base"},
            {"optimizer": "adam"},
            {"override hydra/hydra_logging": "none"},  # NOT "disabled"
            {"override hydra/job_logging": "none"},    # NOT "disabled"
        ]
    )

    hydra: Any = field(
        default_factory=lambda: {
            "run": {"dir": "."},
            "output_subdir": None,
            "mode": "RUN",              # CRITICAL: always include
        }
    )
```

> **Warning:** Always include `"mode": "RUN"`. Without it, `hydra.run()` raises
> `AssertionError: cfg.hydra.mode == RunMode.RUN`.

> **Warning:** Use `"none"` (not `"disabled"`) in logging overrides. `"disabled"` does
> not fully disable logging interception and causes inconsistent per-module log output.

> **Note:** Setting logging overrides alone does not suppress Hydra output folders.
> Always also set `hydra.output_subdir: null` and `hydra.run.dir: "."`.

## Group Dataclass Pattern

```python
# src/configs/model/model_config.py
from dataclasses import dataclass
from hydra.core.config_store import ConfigStore


@dataclass
class ModelConfig:
    name: str = "bert-base-uncased"
    hidden_size: int = 768
    num_layers: int = 12

    def __post_init__(self) -> None:
        if self.hidden_size <= 0:
            raise ValueError(f"hidden_size must be positive, got {self.hidden_size}")


# Module-level registration — triggered on import
cs = ConfigStore.instance()
cs.store(group="model", name="bert_base", node=ModelConfig)
cs.store(group="model", name="gpt2",
         node=ModelConfig(name="gpt2", hidden_size=768, num_layers=12))
```

## Entry Point

```python
import hydra
from src.configs import model_config, optimizer_config  # import modules that register configs

# Module imports above trigger module-level cs.store() calls

@hydra.main(config_path=None, config_name="training_config", version_base="1.3")
def main(cfg: TrainingConfig) -> None:
    pipeline = Pipeline.from_config(cfg)
    ...
```

> **Note:** Ensure all config modules are imported before `@hydra.main` runs so
> their module-level `cs.store()` calls have executed. Individual config modules
> should NOT define `register_*_configs()` wrapper functions — use direct
> module-level `cs.store()` calls instead.

## Builder Pattern

```python
class Pipeline:
    @classmethod
    def from_config(cls, cfg: TrainingConfig) -> "Pipeline":
        return cls(
            model=Model.from_config(cfg.model),
            optimizer=Optimizer.from_config(cfg.optimizer),
        )
```

## CLI Overrides

```bash
uv run python train.py model=gpt2 run.seed=123
uv run python train.py optimizer=sgd optimizer.lr=0.01
```

---

## Logging & Debugging Workflow

When per-module logs disappear under Hydra:

1. **Use `"none"` not `"disabled"`** — check every `override hydra/*_logging` value.
2. **Check `_self_` is first** — if last, dataclass defaults override group variant values.
3. **Validate with a small run first** — confirm all expected loggers emit before long jobs.
4. **Compare against a no-Hydra baseline** — run same code without Hydra and compare output.
5. **Restore clean `logger.info()` calls** — do not patch logging from application code.

---

## Anti-Patterns

- **YAML files** — all variants in Python dataclasses only
- **`cfg["x"]["y"]`** — use `cfg.x.y` attribute access
- **Missing `__post_init__`** — always validate fields
- **Missing `"mode": "RUN"`** — causes `AssertionError`
- **`_self_` not first** — dataclass defaults override group variant values, making variant selection ineffective
- **`"disabled"` in logging overrides** — silently fails to suppress logging
- **No `output_subdir: None`** — creates `.hydra/` output directories
- **`register_*_configs()` wrapper functions** — use module-level `cs.store()` calls instead
- **Bare primitives on top-level config** — encapsulate in a category dataclass (e.g., `RunConfig`)

---

## `_self_` Composition Order Reference

Hydra's `_self_` keyword controls the merge priority between the current config
and defaults list entries. For structured configs (dataclasses), the key insight is:

| `_self_` position | What wins | Use case |
|---|---|---|
| **First** (recommended) | Group variant values override dataclass defaults | Selecting `model=gpt2` applies gpt2's values |
| **Last** (Hydra default) | Dataclass defaults override group variant values | Rarely desired for structured configs |

**This project uses `_self_` first** because when a user selects a group variant
(e.g., `model=gpt2`), the variant's values should take precedence over the base
dataclass defaults.

See: https://hydra.cc/docs/advanced/defaults_list/#composition-order
