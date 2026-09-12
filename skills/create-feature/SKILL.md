---
name: create-feature
visibility: public
description: |
  Feature scaffolding: config, implementation module, tests, and wiring.
  Uses this repository's existing config pattern — Hydra's ConfigStore when
  the repository already uses Hydra, a plain dataclass otherwise. Use when
  asked to create a feature, add a module, or scaffold new functionality.
argument-hint: "[feature-name]"
---

# create-feature — Feature Scaffolding

## Phase 0: Detect the Config Pattern

Check what this repository already does before choosing a scaffold:

```bash
grep -n "hydra" pyproject.toml 2>/dev/null
rg -l "ConfigStore|@hydra.main" src/ 2>/dev/null | head -5
```

- **Hydra already in use** (dependency present and/or an existing
  `ConfigStore.instance()` / `@hydra.main` call) -> use Phase 1A.
- **No Hydra in this repository** -> use Phase 1B. Do not add `hydra-core`
  to a repository that doesn't already depend on it just to scaffold one
  feature — see the `ponytail` skill's dependency rung.

## Phase 1A: Config Dataclass (Hydra)

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

## Phase 1B: Config Dataclass (plain, no Hydra)

Create `src/configs/[feature]_config.py`:
```python
from dataclasses import dataclass


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
```

Wire it up the way this repository already loads configuration (environment
variables, a settings module, a plain constructor call) — do not invent a
new config-loading mechanism for one feature.

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

1. **Hydra path:** ensure the new config module is imported during app
   startup so its module-level `cs.store()` calls execute before
   `@hydra.main`, and add `FeatureConfig` to the entrypoint-specific
   top-level config class (for example `TrainingConfig`,
   `PdfIngestionConfig`) with a defaults entry.
2. **Plain path:** wire `FeatureConfig` into whatever already constructs
   this repository's other configs.
3. If the feature introduces a durable, project-wide fact (not an
   implementation detail), record it in
   `.claude/instructions/project-context.instructions.md`. The canonical
   source for the bootstrap's own `## Project State` slot is
   `shared/policies/workspace.instructions.md`; edit that (and regenerate)
   only when this repository *is* the bootstrap authoring repository —
   never hand-edit the generated `.claude/instructions/workspace.md` /
   `workspace.instructions.md` copy directly.

## Phase 5: Verify
```bash
uv run pytest tests/test_[feature].py -v
uv run mypy src/configs/[feature]_config.py src/[feature]/
uv run ruff check src/ tests/
```
