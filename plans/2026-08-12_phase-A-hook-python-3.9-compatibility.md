---
name: hook-python-3.9-compat
type: small-plan
parent_plan: hook-python-3.9-compatibility
phase_index: 1
status: complete
started_at: 2026-08-12T16:30:00Z
completed_at: 2026-08-12T17:50:00Z
closeout_session_log: .claude/session_logs/2026-08-12_hook-python-3.9-compatibility.md
---

# Phase A: Hook Runtime Python 3.9 Compatibility Fix

## Summary

Fixed a cross-platform consumer regression where `protect-files.py` failed on macOS system Python 3.9.6 due to PEP 604 union syntax (`X | Y`) in type annotations. Added deferred annotation import, improved diagnostics, documented the Python >= 3.9 runtime contract, and added regression tests.

## Changes

- **shared/hooks/scripts/protect-files.py**: Added `from __future__ import annotations` to defer evaluation of union-type annotations
- **shared/hooks/scripts/protect-files.sh**: Improved diagnostics to log Python version, path, and classifier stderr in hooks-errors.log on failure
- **New: .claude/instructions/bootstrap-runtime.instructions.md**: Documented minimum Python >= 3.9 requirement and safe APIs for standalone hooks
- **tests/test_hook_gates.py**: Added comprehensive regression test for Python 3.9 compatibility

## Root Cause

`protect-files.py` line 77 used `tuple[str, bool] | None` return type annotation. The PEP 604 union syntax (`X | Y`) for type annotations was added in Python 3.10. The bootstrap invokes hooks with bare `python3` (not `uv run`), which on macOS resolves to system Python 3.9.6.

## Audit Results

Audited all standalone Python executed via bare `python3`:

- `protect-files.py`: **Fixed** (union syntax now deferred)
- Embedded Python in `_lib-frontmatter.sh`: **Compatible** (uses only standard library APIs available in 3.9)
- Embedded Python in `pretool-bash-guard.sh`: **Compatible** (simple JSON validation)

No Python 3.10+ features found in other hook code.

## Verification

- All tests pass: 813 tests including new regression test
- `pytest tests/test_hook_gates.py` ✓ (71 tests, all pass)
- `pytest tests/test_validate_targets.py` ✓ (34 tests, deterministic generation)
- `ruff check` ✓ (Python files)
- Generated targets regenerated and verified to contain the fix

## Consumer Acceptance

The fix enables the consumer reproduction case from the issue:

```bash
echo '{"tool_name":"Bash","tool_input":{"command":"ls"}}' | \
  .claude/hooks/scripts/protect-files.sh claude-code
```

This now succeeds under Python 3.9.6 without classifier crashes.
