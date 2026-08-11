# Plans

This directory stores implementation plans created during the workflow.

## Naming Convention

Big plans: `<slug>.md`

Small plans: `YYYY-MM-DD_phase-X-short-description.md`

## Skills-First Planning Rule

Before writing a plan, load relevant planning skills from `.claude/skills/`.

- Always: `plan-decomposition/SKILL.md`
- For feature work: `create-feature/SKILL.md`

Plans should include required skills per implementation step so coding agents know exactly what to load before editing.

## Plan Templates

Use `.claude/templates/plan-big.md` for big plans and `.claude/templates/plan-small.md` for small plans.

Plan files must start with YAML-like frontmatter on line 1. The lifecycle hooks and `scripts/validate_plan_frontmatter.py` intentionally read only top-of-file frontmatter.

Required big-plan fields:

- `name`
- `type: big-plan`
- `status`
- `originating_branch`
- `implementation_branch`
- `started_at` once work starts
- `phases`
- `current_phase` while in progress

Big-plan status vocabulary is `planning`, `in-progress`, `complete`, or
`cancelled`. `complete` means the authorized work shipped; `cancelled` means
the plan itself was called off and remaining phases will never be authorized.
The top-level `status` field must occur exactly once; duplicate status keys are
invalid even when their values match.

Required small-plan fields:

- `name`
- `type: small-plan`
- `parent_plan`
- `phase_index`
- `status`
- `closeout_session_log` once complete

Small-plan status vocabulary is `in-progress`, `complete`, or `cancelled`.
The same exactly-once `status` rule applies to small plans.

Cancelled big plans and small plans require all three of these fields:

- `cancelled_at`: a real UTC calendar date and time in exact
  `YYYY-MM-DDTHH:MM:SSZ` format
- `cancelled_reason`: meaningful plain single-line scalar prose without leading
  quotes, YAML block headers, collections, list markers, or comment-only values
- `cancelled_evidence`: a repository-relative path that stays inside the
  repository and resolves to an existing regular, readable UTF-8 text artifact
  containing the same-line prefix `**Status:** CANCELLED`

A cancelled phase requires no commit, findings report, score, or closeout
session log. Its cancellation evidence is required instead and provides the
auditable record for work that will never run.
