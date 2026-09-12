---
name: code-review
visibility: public
description: |
  Unified review workflow. Runs the `reviewer` agent with one or more
  profiles from `.claude/review-profiles/` and synthesizes findings into a gate result.
argument-hint: "[file-or-directory]"
---

# Code Review

Use the unified `reviewer` agent instead of separate specialist reviewer agents.

## Profile Routing

Select profiles from the single authoritative routing table in `.claude/instructions/workspace.instructions.md` (the **Review Profiles** section).

## Workflow

1. Identify scope:
   - Argument path: review that path.
   - No argument: review uncommitted changes.
2. Select review profiles from the table.
3. Ask `reviewer` to run its primary + verification passes with the selected profiles.
4. Resolve findings per the severity contract in
   `shared/policies/workflow.instructions.md`: CRITICAL and MAJOR both block
   the phase-completion commit; a surviving MINOR is advisory but needs an
   explicit disposition and a non-empty reason.
5. Re-run verification and review until the target gate passes.

## Reporting Findings

In lifecycle mode (the orchestrator's canonical loop), return findings to the
orchestrator; it persists them via `record_findings.py --out
.claude/quality_reports/findings-<current_phase>.json` per
`shared/policies/workflow.instructions.md`. Do not write a separate report
file in that mode.

For an ad-hoc, read-only review requested outside the lifecycle (no plan, no
commit), report findings directly in the response; no persisted artifact is
required.

