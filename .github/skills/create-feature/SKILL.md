---
name: create-feature
description: |
  Config-first feature scaffolding. Creates config dataclass, ConfigStore
  registration, implementation module, tests, and wires everything together.
  Use when asked to create a feature, add a module, or scaffold new functionality.
argument-hint: "[feature-name]"
---

# create-feature — Config-First Scaffolding

## Phase 1: Config Dataclass

Create `src/configs/[feature]_config.py`:
```python
from dataclasses import dataclass
from hydra.core.config_store import ConfigStore


@dataclass
class FeatureConfig:
    """Configuration for [feature].

    Attributes:
        param: Description of parameter.
    """
    param: str = "default"

    def __post_init__(self) -> None:
        if not self.param:
            raise ValueError("param cannot be empty")


def register_feature_configs() -> None:
    """Register feature config variants with ConfigStore."""
    cs = ConfigStore.instance()
    cs.store(group="feature", name="default", node=FeatureConfig)
```

## Phase 2: Implementation Module

Create `src/[feature]/module.py`:
```python
class Feature:
    """[Feature] implementation."""

    @classmethod
    def from_config(cls, cfg: FeatureConfig) -> "Feature":
        """Create from config."""
        return cls(...)
```

## Phase 3: Tests

Create `tests/test_[feature].py`:
```python
class TestFeature:
    def test_config_validation(self) -> None:
        """Test config validates correctly."""
        ...

    def test_from_config(self, sample_config: FeatureConfig) -> None:
        """Test factory method."""
        ...
```

## Phase 4: Wire Up

1. Call `register_feature_configs()` before Hydra init in entry point
2. Add `FeatureConfig` field to `MainConfig` with defaults entry
3. Update project state in `copilot-instructions.md`

## Phase 5: Verify
```bash
uv run pytest tests/test_[feature].py -v
uv run mypy src/configs/[feature]_config.py src/[feature]/
uv run ruff check src/ tests/
```
