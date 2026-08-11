---
description: "Bootstrap standalone hook runtime contract: minimum Python version and dependency expectations."
applicability: "When debugging hook failures, adding hook Python code, or installing the bootstrap in a new environment."
---

# Bootstrap Hook Runtime Contract

## Standalone Hook Python Version

The bootstrap's security and lifecycle hooks execute with **bare system `python3`** (not `uv run` or a project-managed environment). This ensures hooks function before any project infrastructure is initialized.

**Minimum required version: Python >= 3.9**

This includes:
- `python3` in `$PATH` on macOS (`/usr/bin/python3`)
- `python3` in `$PATH` on Linux (distribution-provided or user-installed)
- Any system on which `python3 --version` reports 3.9.0 or later

### Supported APIs

Hook Python code is limited to:
- Standard library modules available in Python 3.9 (`json`, `re`, `sys`, `pathlib`, `datetime`, `stat`, etc.)
- No external packages; no `import uv`, `import click`, or third-party libraries
- No syntax or runtime features added after Python 3.9 (e.g., no PEP 604 union syntax `X | Y` at module level; use `from __future__ import annotations` instead)
- No type annotations evaluated at runtime unless deferred via `from __future__ import annotations`

### Runtime Detection

When hook Python fails, the shell wrapper logs diagnostic information to `.claude/session_logs/hooks-errors.log`:
- Resolved `python3` path
- Python version output
- Classifier exit code
- First line of stderr (if available), sanitized to omit sensitive tool input

Example diagnostic line:
```
2026-08-12T16:45:00Z WARN hook fail-closed: protected-file classifier exited with status 1 (python: Python 3.9.6, path: /usr/bin/python3, error: TypeError: unsupported operand type(s) for |: ...)
```

Operators deploying the bootstrap should verify `python3 --version` before installing hooks or debug hook failures by checking this log.

### Known Safe Patterns

The following are confirmed compatible with Python 3.9:
- `Path.is_relative_to()` — available since Python 3.9.0
- `datetime.datetime.strptime()` — standard since before 3.0
- `json.load()` and `json.loads()` — standard since before 3.0
- `re.Pattern.fullmatch()` — available since Python 3.4
- `stat.S_ISREG()` — available since Python 2.0

### Migration Path

If a new hook feature requires Python 3.10+ or later, the implementation must:
1. Check the Python version at hook entry (not at import time)
2. Document the version requirement in this file
3. Gracefully degrade the hook or emit a clear error message directing the operator to upgrade system Python
4. Add a regression test that validates the version check under the previous minimum

### Locations

Standalone Python executed via bare `python3`:
- `shared/hooks/scripts/protect-files.py` — Protected-file classification
- Inline Python in `shared/hooks/scripts/_lib-frontmatter.sh` — Frontmatter reading, JSON validation, cancellation proof validation
- Inline Python in `shared/hooks/scripts/pretool-bash-guard.sh` — Safety output validation

**Related but different:** Project-managed Python (test suite, build tooling, utilities) runs under `uv run python` and may use Python 3.12+ or later; no version constraints apply there.
