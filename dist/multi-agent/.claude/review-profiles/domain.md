# Domain Review Profile

Use for project-specific correctness. Customize this profile in consumer repositories.

## Checklist

- Domain terminology is consistent across code, tests, and docs.
- Domain invariants are represented explicitly in types, configs, or validation.
- Data transformations preserve required meaning and units.
- Domain-specific edge cases are tested.
- Model, pipeline, and retrieval settings match documented domain expectations.
- Results are not silently coerced in ways that hide domain errors.

## Severity

- Critical: Domain logic errors, data corruption risks, or incorrect model/pipeline usage.
- Major: Missing domain validation, incorrect assumptions, or incomplete domain tests.
- Minor: Terminology, documentation, or clarity improvements.

