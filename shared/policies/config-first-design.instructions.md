---
description: "Config-first design; pure ConfigStore (no YAML files) in Hydra projects"
applicability:
  - src/configs/**/*.py
---

# Config-First Design

## Core Rule

**Create config dataclass BEFORE implementing the feature.**

This rule holds for every project. The ConfigStore registration below applies
when the repository already uses Hydra. In a repository that does not, write
the same dataclass as a plain dataclass and wire it the way that repository
already loads configuration; do not add `hydra-core` to satisfy this policy.

## Pure ConfigStore (No YAML Files)

Everything from here to the end of this file is the Hydra pattern, and applies
only when the repository already uses Hydra. In a repository that does not, the
Core Rule above is the whole policy: write the config dataclass first, then wire
it the way that repository already loads configuration.

All config variants live as Python dataclass instances registered with
ConfigStore. Code examples for the group dataclass, top-level config, entry
point, and builder are in the `hydra-config` skill (`.claude/skills/hydra-config/SKILL.md`).

### Top-Level Config

> **Rule:** The top-level config must ONLY contain composed dataclass fields.
> Name the top-level config after its owning entrypoint (for example `TrainingConfig`, `PdfIngestionConfig`, `EvaluationConfig`).
> Never put bare primitive fields (`str`, `int`, `bool`) directly on the top-level config class.
> Encapsulate all primitives in a category-specific dataclass first.

- `defaults` lists `"_self_"` first, so group variants override dataclass defaults.
- The `hydra` dict always includes `"mode": "RUN"`.
- The entry point uses `@hydra.main(config_path=None, ...)`.

## Anti-Patterns

- **YAML config files** — in a Hydra project, all variants in Python
  dataclasses only; elsewhere, follow the configuration pattern the repository
  already uses (matching `code-standards.instructions.md`)
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
