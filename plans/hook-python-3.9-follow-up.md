---
name: hook-python-3.9-follow-up
type: small-plan
parent_plan: hook-python-3.9-compatibility
phase_index: 1
status: complete
started_at: 2026-08-12T03:00:00Z
completed_at: 2026-08-12T03:30:00Z
---

# Small Plan: Hook Python 3.9 Follow-up Corrections

Fix three gaps in the Python 3.9 portability implementation:

## Tasks

1. **Add Python 3.9 CI regression test**: Create dedicated GitHub Actions job that runs protect-files.py and hook invocation with real Python 3.9 interpreter, proving the compatibility contract is maintained under actual Python 3.9 runtime.

2. **Move runtime contract to canonical source**: Relocate the Python >= 3.9 bootstrap hooks runtime contract from ai-state (`.claude/instructions/bootstrap-runtime.instructions.md`) to canonical distributable source (`shared/policies/workspace.instructions.md`).

3. **Record manual merge exception**: Update session log to document the circular content-hash dependency that caused the pre-push gate to fail and required manual merge by operator. Note the `bypass_acknowledged: true` flag in the big plan.

## Changes

- `.github/workflows/validate.yml`: Added `python_39_hooks` job with three focused tests
- `shared/policies/workspace.instructions.md`: Added "Bootstrap Hooks Runtime Contract" section
- `.claude/session_logs/2026-08-12_hook-python-3.9-compatibility.md`: Recorded lifecycle note explaining manual merge exception
- No new functionality, no behavior changes to runtime fix

## Verification

- All 813 tests pass
- Targets regenerated and validated deterministically
- Python 3.9 CI job syntax valid
- Generated consumer workspace.instructions.md contains the runtime contract

**Status:** COMPLETED
**Branch:** `hook-python-3.9-follow-up_implementation`
