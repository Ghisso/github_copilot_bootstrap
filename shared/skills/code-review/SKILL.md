---
name: code-review
visibility: public
description: |
  Unified review workflow. Runs the `reviewer` agent with one or more
  profiles from `shared/review-profiles/` and synthesizes findings into a gate result.
argument-hint: "[file-or-directory]"
---

# Code Review

Use the unified `reviewer` agent instead of separate specialist reviewer agents.

## Profile Routing

| Scope | Profiles |
|---|---|
| Python source | `code`, `security` |
| New modules or refactors | `architecture` |
| Tests | `tests` |
| API or service files | `api`, `security`, `tests` |
| Config dataclasses | `config` |
| I/O-heavy or ML-heavy paths | `performance` |
| Docs or user-facing behavior | `documentation` |
| Domain-specific correctness | `domain` |

## Workflow

1. Identify scope:
   - Argument path: review that path.
   - No argument: review uncommitted changes.
2. Select review profiles from the table.
3. Ask `reviewer` to run a dual-pass review with the selected profiles.
4. Fix findings by severity: critical, then major, then minor.
5. Re-run verification and review until the target gate passes.

Save reports to `.claude/quality_reports/YYYY-MM-DD_review_[scope].md`.

