---
name: testing-patterns
visibility: background
description: |
  Pytest test-authoring workflow and repository testing standards. Use when
  writing or reviewing unit tests, integration tests, async tests, fixtures,
  parametrization, or mocks. Reads the tests policy, then runs the fast
  verifier.
user-invocable: false
---

# Testing Patterns

Read `.claude/instructions/tests.instructions.md`, then run:

```bash
uv run python .claude/scripts/verify.py fast --format text
```

`fast` lints changed files only. Run the tests with the pytest commands in the
policy.
