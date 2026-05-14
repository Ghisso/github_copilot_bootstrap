# Config Review Profile

Use for Hydra ConfigStore dataclasses and config-driven construction.

## Checklist

- Config dataclasses have type hints, defaults, and `__post_init__` validation.
- No YAML config variants; use pure ConfigStore registrations.
- `cs = ConfigStore.instance()` and `cs.store()` are module-level.
- No `register_*_configs()` wrapper functions.
- Top-level config contains composed dataclass fields only.
- Defaults lists put `_self_` first.
- Hydra dict includes `"mode": "RUN"`, `output_subdir: None`, and `run.dir: "."`.
- Logging overrides use `"none"`, not `"disabled"`.
- Config modules import before `@hydra.main` runs.
- Builders pass every relevant config field.
- Secrets are not stored in dataclass defaults.

## Severity

- Critical: Broken ConfigStore registration, hardcoded secrets, or missing validation that can break runtime.
- Major: Missing `__post_init__`, partial field wiring, top-level primitives, or bad Hydra defaults.
- Minor: Missing descriptions, naming, or default polish.

