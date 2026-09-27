---
name: <YYYY-MM-DD_phase-X-slug>
type: small-plan
parent_plan: <big-plan-slug>
phase_index: 1
# status must occur exactly once: planned | in-progress | paused | complete | cancelled
# New phase files default to planned (not yet started); the branch-creation
# and post-commit hooks flip the active phase to in-progress automatically.
status: planned
closeout_session_log:
# Pause fields (required only when status is paused):
# paused_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# paused_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# pause_session_log: <repository-relative readable UTF-8 PAUSED session log>
# Cancellation fields (required only when status is cancelled):
# cancelled_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# cancelled_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# cancelled_evidence: <repository-relative readable UTF-8 CANCELLED artifact>
---

# Small Plan: <YYYY-MM-DD_phase-X-slug>

## Scope

[What this phase changes]

## Steps

- [ ] [Step]

## Verification

<!-- List the project's own test, lint, and type commands, taken from its
     README or contributing guide, one per line, run from the repository
     root. Anything a script cannot run belongs under
     `## Optional Verification` instead. -->

```bash
# for example: uv run pytest -q
```

## Optional Verification

<!-- The only place a check may be conditional or non-executable. One `- `
     bullet per item, numbered in the order it appears. -->

- [Optional check]

## Closeout Checklist

None of this blocks a commit; it is the order that keeps the record honest.

- [ ] Documentation updated for changed public behavior, or noted as internal
- [ ] Lessons recorded in `.claude/ai-bootstrap/MEMORY.md`, or "none" noted
- [ ] Session log under `.claude/ai-bootstrap/session_logs/` has `**Status:** COMPLETED`
- [ ] Reviewer's report saved under `.claude/ai-bootstrap/quality_reports/` and its Critical and Major items resolved or explicitly deferred
- [ ] The Verification commands above ran and passed
Keep the big plan `in-progress` with the same `current_phase`. On resume, read
the pause log and Git state, restore this plan to `in-progress`, and continue
this same phase without creating another small plan.
