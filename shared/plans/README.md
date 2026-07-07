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

Required small-plan fields:

- `name`
- `type: small-plan`
- `parent_plan`
- `phase_index`
- `status`
- `closeout_session_log` once complete
