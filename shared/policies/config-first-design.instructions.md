---
description: "Config-first design using pure ConfigStore (no YAML files)"
applicability:
  - src/configs/**/*.py
---

# Config-First Design

## Core Rule

**Create config dataclass BEFORE implementing the feature.**

## Pure ConfigStore (No YAML Files)

All config variants live as Python dataclass instances registered with ConfigStore.

### Pattern

```python
from dataclasses import dataclass, field
from typing import Any
from hydra.core.config_store import ConfigStore


@dataclass
class ModelConfig:
    """Model configuration.

    Attributes:
        name: Model identifier.
        hidden_size: Hidden layer dimension.
    """
    name: str = "bert-base-uncased"
    hidden_size: int = 768
    num_layers: int = 12

    def __post_init__(self) -> None:
        if self.hidden_size <= 0:
            raise ValueError(f"hidden_size must be positive, got {self.hidden_size}")


cs = ConfigStore.instance()
cs.store(group="model", name="bert_base", node=ModelConfig)
cs.store(group="model", name="gpt2",
            node=ModelConfig(name="gpt2", hidden_size=768, num_layers=12))
```

```python
from dataclasses import dataclass
from hydra.core.config_store import ConfigStore

@dataclass
class RunConfig:
    """Runtime configuration."""
    experiment_name: str = "my_experiment"
    seed: int = 42

cs = ConfigStore.instance()
cs.store(group="run", name="default", node=RunConfig)
```

### Top-Level Config

> **Rule:** The top-level config must ONLY contain composed dataclass fields.
> Name the top-level config after its owning entrypoint (for example `TrainingConfig`, `PdfIngestionConfig`, `EvaluationConfig`).
> Never put bare primitive fields (`str`, `int`, `bool`) directly on the top-level config class.
> Encapsulate all primitives in a category-specific dataclass first.

```python
# WRONG — bare primitives on top-level config
@dataclass
class TrainingConfig:
    experiment_name: str = "my_experiment"  # ✗ bare primitive
    seed: int = 42                          # ✗ bare primitive
    model: ModelConfig = field(default_factory=ModelConfig)
```

```python
# CORRECT — all fields are composed dataclasses
@dataclass
class TrainingConfig:
    run: RunConfig = field(default_factory=RunConfig)
    model: ModelConfig = field(default_factory=ModelConfig)

    defaults: list[Any] = field(
        default_factory=lambda: [
            "_self_",           # MUST be first — group variants override dataclass defaults
            {"model": "bert_base"},
        ]
    )

    hydra: Any = field(
        default_factory=lambda: {
            "run": {"dir": "."},
            "output_subdir": None,
            "mode": "RUN",      # CRITICAL: always include
        }
    )
```

### Entry Point

```python
@hydra.main(config_path=None, config_name="training_config", version_base="1.3")
def main(cfg: TrainingConfig) -> None:
    ...
```

## Anti-Patterns

- **YAML config files** — all variants in Python dataclasses only
- **Ad-hoc dicts** — use typed dataclasses
- **Accessing `cfg["x"]["y"]`** — use `cfg.x.y` attribute access
- **Missing `__post_init__`** — always validate in post-init
- **Missing `"mode": "RUN"`** — causes `AssertionError` at runtime
- **Bare primitives on top-level config** — encapsulate in a category dataclass first
- **`_self_` not first in defaults** — group variants won't override defaults

## Group Variant Pitfall

For top-level configs that include `defaults` and `hydra`, ConfigStore group variants
should usually be plain dict nodes rather than full dataclass instances. Registering
full top-level dataclass instances as group variants can trigger recursive resolution
errors such as `Could not find 'group/group/default'`.

Safe pattern:
- Keep top-level config as a dataclass type for `config_name`
- Register group variants as dict-like nodes for the group override values
- Keep simple leaf configs (without top-level Hydra metadata) as dataclass instances

## Checklist

- [ ] Dataclass with type hints and defaults
- [ ] `__post_init__` validation
- [ ] `cs = ConfigStore.instance()` + `cs.store()` directly after each dataclass (no wrapper functions)
- [ ] Config modules are imported before `hydra.main` so module-level `cs.store()` has executed
- [ ] `config_path=None` in `@hydra.main`
- [ ] `_self_` first in defaults list
- [ ] `"mode": "RUN"` in hydra dict
- [ ] Top-level config class name matches the owning entrypoint/script role
- [ ] Top-level config contains ONLY composed dataclass fields (no bare primitives)
- [ ] Builder `from_config(cfg)` method on consuming class
