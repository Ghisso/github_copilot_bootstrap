# Plans

This directory stores implementation plans created during the workflow.

## Naming Convention

`YYYY-MM-DD_short-description.md`

## Skills-First Planning Rule

Before writing a plan, load relevant planning skills from `.agents/skills/`.

- Always: `plan-decomposition/SKILL.md`
- Always: `iterative-plan-review/SKILL.md`
- For feature work: `create-feature/SKILL.md`

Plans should include required skills per implementation step so coding agents know exactly what to load before editing.

## Plan Template

```markdown
# Plan: [Short Title]

**Date:** YYYY-MM-DD
**Status:** DRAFT | APPROVED | IN-PROGRESS | COMPLETED

## Goal
[What we're building and why]

## Approach
[High-level approach and rationale]

## Tasks

- [ ] Task 1
  - Owner: coder | designer | reviewer
  - Files: [path/file.py]
  - Required Skills: [.agents/skills/code-style/SKILL.md]
  - Verify: [command]
- [ ] Task 2
  - Owner: coder | designer | reviewer
  - Files: [path/file.py]
  - Required Skills: [skill paths]
  - Verify: [command]
- [ ] Task 3
  - Owner: coder | designer | reviewer
  - Files: [path/file.py]
  - Required Skills: [skill paths]
  - Verify: [command]

## Open Questions

- [Question 1]

## Risks

- [Risk 1]

## Definition of Done

- [ ] All tests pass
- [ ] Score ≥ 80
- [ ] PR ready
```
