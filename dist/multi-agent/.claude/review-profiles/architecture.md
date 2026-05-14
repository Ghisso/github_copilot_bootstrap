# Architecture Review Profile

Use for new modules, refactors, dependency direction, and ownership boundaries.

## Checklist

- Config, business logic, framework code, and I/O are separated.
- Dependencies flow inward; no circular imports.
- Core logic does not depend on framework-specific APIs.
- Shared types used across layers live in `src/domain/`.
- Config objects are passed explicitly; no hidden global mutable state.
- `from_config()` construction is used for config-driven runtime objects.
- Public module surfaces are minimal and intentional.
- `__init__.py` exports only stable public APIs.

## Severity

- Critical: Circular dependencies, business logic in service layers, global mutable state, or layer inversions.
- Major: Tight coupling, missing boundaries, monolithic modules, or misplaced shared types.
- Minor: Naming or boundary clarity improvements.

