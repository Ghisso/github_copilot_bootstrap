# Quality Reports

This directory stores quality reports generated during code reviews and verification.

## Subdirectories

- **`merges/`** — merge-time quality reports (`YYYY-MM-DD_[branch].md`)
- **`specs/`** — requirements specs for features (`YYYY-MM-DD_[feature].md`)

Use `.github/templates/quality-report.md` and `.github/templates/requirements-spec.md` as starting points.

## Naming Convention

`YYYY-MM-DD_[type]_[scope].md`

Types: `code-review`, `security-review`, `verification`, `merge`

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

**Score:** [N]/100
**Gate:** [Commit / PR-ready / Excellence / BLOCKED]

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
