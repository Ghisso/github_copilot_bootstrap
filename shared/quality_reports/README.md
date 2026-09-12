# Quality Reports

This directory stores quality reports generated during code reviews and verification.

## Subdirectories

- **`merges/`** — merge-time quality reports (`YYYY-MM-DD_[branch].md`)
- **`specs/`** — requirements specs for features (`YYYY-MM-DD_[feature].md`)

Use `.claude/templates/quality-report.md` and `.claude/templates/requirements-spec.md` as starting points.

## Naming Convention

Review findings and verification receipts are written by tooling, not by hand:

- `findings-<phase>.json` — persisted by the orchestrator via
  `record_findings.py` after review converges. The reviewer returns findings
  to the orchestrator and does not write this file itself.
- `verification-phase-<phase>.json` and `verification-closeout-<phase>.json` —
  receipts written by `verify.py ... --persist`.

Hand-authored markdown reports remain only for the subdirectories above:
`YYYY-MM-DD_[branch].md` under `merges/` and `YYYY-MM-DD_[feature].md` under
`specs/`.

## Report Template

```markdown
# Quality Report: [Type] — [Scope]

**Date:** YYYY-MM-DD
**Reviewer:** [agent name(s)]

## Summary

| Severity | Count |
|----------|-------|
| Critical | N |
| Major | N |
| Minor | N |

**Verification:** [PASS / FAIL]

## Findings

### Critical
- [file:line] [description]

### Major
- [file:line] [description]

### Minor
- [file:line] [description]

## Recommendation

[SHIP / FIX-THEN-SHIP / BLOCK]
```
