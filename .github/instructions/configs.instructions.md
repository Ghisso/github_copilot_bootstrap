---
applyTo: "src/configs/**/*.py"
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


def register_model_configs() -> None:
    """Register model config variants with ConfigStore."""
    cs = ConfigStore.instance()
    cs.store(group="model", name="bert_base", node=ModelConfig)
    cs.store(group="model", name="gpt2",
             node=ModelConfig(name="gpt2", hidden_size=768, num_layers=12))
```

### Top-Level Config

```python
@dataclass
class MainConfig:
    experiment_name: str = "my_experiment"
    seed: int = 42
    model: ModelConfig = field(default_factory=ModelConfig)

    defaults: list[Any] = field(
        default_factory=lambda: [
            "_self_",           # MUST be first
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
@hydra.main(config_path=None, config_name="main_config", version_base="1.3")
def main(cfg: MainConfig) -> None:
    ...
```

## Anti-Patterns

- **YAML config files** — all variants in Python dataclasses only
- **Ad-hoc dicts** — use typed dataclasses
- **Accessing `cfg["x"]["y"]`** — use `cfg.x.y` attribute access
- **Missing `__post_init__`** — always validate in post-init
- **Missing `"mode": "RUN"`** — causes `AssertionError` at runtime
- **`_self_` not first in defaults** — group variants won't override defaults

## Checklist

- [ ] Dataclass with type hints and defaults
- [ ] `__post_init__` validation
- [ ] `register_*_configs()` function
- [ ] ConfigStore registration before `hydra.main`
- [ ] `config_path=None` in `@hydra.main`
- [ ] `_self_` first in defaults list
- [ ] `"mode": "RUN"` in hydra dict
- [ ] Builder `from_config(cfg)` method on consuming class
- [ ] Environment variables for secrets (never in config defaults)
