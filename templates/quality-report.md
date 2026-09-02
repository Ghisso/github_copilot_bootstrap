# Quality Report — [BRANCH NAME]

**Date:** YYYY-MM-DD
**Branch:** <plan_name>_implementation
**Phase:** <current_phase>
**Base Ref:** dev
**Status:** PASS / FAIL

---

## Summary

[Brief description of what this branch accomplished]

---

## Files Modified

| File | Type | Notes |
|------|------|-------|
| `src/...` | Code | |
| `tests/...` | Test | |
| `configs/...` | Config | |
| `docs/...` | Docs | |

---

## Verification

`verify.py phase --format text` deterministic result, one line per check:

```text
phase: PASS
VFY-RUFF-001: PASS - Ruff completed with 0 violations
VFY-FMT-001: PASS - Ruff format completed with 0 files needing reformatting
VFY-MYPY-001: PASS - mypy completed with 0 errors
VFY-PYTEST-001: PASS - pytest completed (N tests)
VFY-FRESH-001: PASS - phase evidence captured relevant state
VFY-FRESH-002: PASS - phase evidence captured governing control-plane provenance
VFY-GEN-001: PASS - generated verifier runtime matches source
```

| Check | Status |
|-------|--------|
| `verify phase` receipt | [ ] |
| `verify closeout` receipt | [ ] |
| E2E passes (if applicable) | [ ] |
| Findings report persisted under `.claude/quality_reports/` | [ ] |
| Findings report newer than changed files | [ ] |

---

## Notes

- [Learnings, follow-ups, tech debt introduced]
