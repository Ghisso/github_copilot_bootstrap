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


# Module-level registration — triggered on import
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

1. Ensure the new config module is imported during app startup so its module-level `cs.store()` calls execute before `@hydra.main`
2. Add `FeatureConfig` field to the entrypoint-specific top-level config class (for example `TrainingConfig`, `PdfIngestionConfig`) with a defaults entry
3. Update project state in `AGENTS.md`

## Phase 5: Verify
```bash
uv run pytest tests/test_[feature].py -v
uv run mypy src/configs/[feature]_config.py src/[feature]/
uv run ruff check src/ tests/
```
