---
name: code-style
visibility: public
description: Python implementation style reminders. Use when writing or reviewing code that must follow the repository code standards.
---

# Code Style

This skill is a short implementation reminder. The authoritative policy is `.claude/instructions/code-standards.instructions.md`.

## Use This Workflow

1. Read `.claude/instructions/code-standards.instructions.md`.
2. Check the local `pyproject.toml` for ruff and mypy configuration.
3. Apply the policy while editing:
   - Python 3.12+ type syntax: `list[str]`, `dict[str, int]`, `X | None`.
   - No `from __future__ import annotations` in Hydra/dataclass code.
   - Google-style docstrings for public APIs.
   - Percent formatting for logging.
   - `pathlib.Path` for file paths.
   - Context managers for resources.
   - Specific exceptions with `raise ... from e`.
4. Verify with:

```bash
uv run python .claude/scripts/verify.py fast --format json
```

`fast` selects the repository's real scope instead of assuming a `src/`
layout, so it stays correct in both the bootstrap authoring repository and an
installed consumer.

If the policy and this skill disagree, follow the policy file.

