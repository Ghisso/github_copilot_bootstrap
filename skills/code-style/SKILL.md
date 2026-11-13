---
name: code-style
visibility: public
description: |
  Python implementation style and repository code standards. Use when writing or
  reviewing Python code: type hints, docstrings, logging format, naming,
  pathlib, context managers, exception chaining. Reads the code-standards
  policy, then runs the fast verifier.
---

# Code Style

Read `.claude/instructions/code-standards.instructions.md`, then run:

```bash
uv run python .claude/scripts/verify.py fast --format text
```
