---
name: code-review
description: |
  Multi-agent code review workflow. Runs 6+ specialized reviewers in parallel
  and synthesizes findings into a scored report. Use before PRs, after
  completing features, or for periodic quality audits.
argument-hint: "[file-or-directory]"
---

# code-review — Multi-Agent Code Review

## Phase 1: Identify Scope

- File path given: review that file
- Directory: review all `.py` files
- No argument: review all uncommitted changes (`git diff --name-only`)

## Phase 2: Parallel Review Agents

| Agent | Target Files | Focus |
|-------|-------------|-------|
| code-reviewer | `src/**/*.py` | SOLID, patterns, readability |
| security-reviewer | All `.py` files | Secrets, injection, unsafe ops |
| test-reviewer | `tests/**/*.py` | Coverage, assertions, edge cases |
| architecture-reviewer | `src/**/*.py` | Coupling, SoC, dependencies |
| config-reviewer | `src/configs/**` | Completeness, validation |
| documentation-reviewer | All files | Docstrings, README |

## Phase 3: Synthesis

| Severity | Code | Security | Tests | Architecture | Config | Docs |
|----------|------|----------|-------|--------------|--------|------|
| Critical | N | N | N | N | N | N |
| Major | N | N | N | N | N | N |
| Minor | N | N | N | N | N | N |

## Phase 4: Score

Apply `Quality Gates & Testing Protocol` rubric. Start at 100, deduct per tables.

```
Score: [N]/100
Gate: [Commit (≥80) / PR (≥90) / Excellence (≥95)]
Recommendation: [SHIP / FIX-THEN-SHIP / BLOCK]
```

## Phase 5: Fix Cycle (if score < threshold)

1. List critical issues (must fix)
2. List major issues (should fix)
3. Fix: critical → major → minor
4. Re-verify (pytest, mypy, ruff)
5. Re-score. Max 3 rounds.

Save report to `.codex/quality_reports/YYYY-MM-DD_code-review_[scope].md`.
