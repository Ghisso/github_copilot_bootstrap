---
name: hydra-config
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
4. **`_self_` last** — always last in defaults list so local config values override composed group configs.
5. **`"mode": "RUN"`** — always include in the `hydra` dict to prevent `AssertionError`.
6. **`"none"` not `"disabled"`** — use `"none"` in logging overrides to fully disable Hydra logging interception.

## Quick Checklist

- [ ] Register with ConfigStore: `cs.store(group="<group>", name="<name>", node=MyConfig)`
- [ ] `config_path=None` in `@hydra.main`
- [ ] `_self_` **last** in defaults list (so local values win over group variants)
- [ ] `"mode": "RUN"` in hydra dict
- [ ] Logging overrides use `"none"`: `{"override hydra/hydra_logging": "none"}`
- [ ] `output_subdir: None` and `run.dir: "."` to suppress Hydra output folders
- [ ] `from_config(cfg)` builder method on all runtime classes
- [ ] `register_*_configs()` called before hydra init

---

## Directory Pattern

```
src/configs/
  main_config.py          # Top-level dataclass
  model/
    model_config.py       # ModelConfig + register_model_configs()
  optimizer/
    optimizer_config.py   # OptimizerConfig + register_optimizer_configs()
```

## Top-Level Config

```python
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MainConfig:
    experiment_name: str = "my_experiment"
    seed: int = 42
    model: ModelConfig = field(default_factory=ModelConfig)
    optimizer: OptimizerConfig = field(default_factory=OptimizerConfig)

    defaults: list[Any] = field(
        default_factory=lambda: [
            {"model": "bert_base"},
            {"optimizer": "adam"},
            {"override hydra/hydra_logging": "none"},  # NOT "disabled"
            {"override hydra/job_logging": "none"},    # NOT "disabled"
            "_self_",                                  # MUST be last
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


def register_model_configs() -> None:
    cs = ConfigStore.instance()
    cs.store(group="model", name="bert_base", node=ModelConfig)
    cs.store(group="model", name="gpt2",
             node=ModelConfig(name="gpt2", hidden_size=768, num_layers=12))
```

## Entry Point

```python
import hydra

# Register all configs before hydra.main
register_model_configs()
register_optimizer_configs()

@hydra.main(config_path=None, config_name="main_config", version_base="1.3")
def main(cfg: MainConfig) -> None:
    pipeline = Pipeline.from_config(cfg)
    ...
```

## Builder Pattern

```python
class Pipeline:
    @classmethod
    def from_config(cls, cfg: MainConfig) -> "Pipeline":
        return cls(
            model=Model.from_config(cfg.model),
            optimizer=Optimizer.from_config(cfg.optimizer),
        )
```

## CLI Overrides

```bash
uv run python train.py model=gpt2 seed=123
uv run python train.py optimizer=sgd optimizer.lr=0.01
```

---

## Logging & Debugging Workflow

When per-module logs disappear under Hydra:

1. **Use `"none"` not `"disabled"`** — check every `override hydra/*_logging` value.
2. **Check `_self_` is last** — if first, a group variant could override logging overrides.
3. **Validate with a small run first** — confirm all expected loggers emit before long jobs.
4. **Compare against a no-Hydra baseline** — run same code without Hydra and compare output.
5. **Restore clean `logger.info()` calls** — do not patch logging from application code.

---

## Anti-Patterns

- **YAML files** — all variants in Python dataclasses only
- **`cfg["x"]["y"]`** — use `cfg.x.y` attribute access
- **Missing `__post_init__`** — always validate fields
- **Missing `"mode": "RUN"`** — causes `AssertionError`
- **`_self_` not last** — group variants override local config values unexpectedly
- **`"disabled"` in logging overrides** — silently fails to suppress logging
- **No `output_subdir: None`** — creates `.hydra/` output directories
