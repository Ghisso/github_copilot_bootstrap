---
name: learn
visibility: public
description: |
  Extract non-obvious discoveries into reusable skills that persist across
  sessions. Use when debugging took significant effort, found misleading errors,
  discovered undocumented behavior, or built a repeatable multi-step workflow.
  Trigger: "I learned something", "save this as a skill".
argument-hint: "[skill-name]"
---

# learn — Skill Extraction

## Phase 1: Evaluate

Answer these questions:
1. "What did I just learn that was not obvious before starting?"
2. "Would future-me benefit from this being documented?"
3. "Was the solution non-obvious from documentation alone?"
4. "Is this a repeatable workflow?"

**Continue only if YES to at least one.**

## Phase 2: Check Existing Skills

Search the authoring source when one exists, otherwise the installed copy.
In this bootstrap's authoring repository, `shared/skills/` is canonical and
`.claude/skills/` is a regenerated output. In an installed consumer project
there is no `shared/skills/`, so `.claude/skills/` is the only copy and is the
correct target.

```bash
# Bootstrap authoring repository (shared/skills/ exists):
ls shared/skills/ && grep -r -i "KEYWORD" shared/skills/
# Installed consumer project:
ls .claude/skills/ && grep -r -i "KEYWORD" .claude/skills/
```
- Nothing related → create new skill
- Same trigger & fix → update existing skill
- Partial overlap → add variant to existing

## Phase 3: Create Skill

Create the skill in the canonical location for the repository you are in:
`shared/skills/[skill-name]/SKILL.md` in this bootstrap's authoring
repository, so it regenerates into every target; `.claude/skills/[skill-name]/SKILL.md`
in an installed consumer project, which has no `shared/skills/`. A skill left
only in the generated overlay is deleted by the next refresh.

`name` must match the skill's directory name, and `visibility` is required
under `shared/skills/`; `scripts/validate_targets.py` fails the run otherwise.

```markdown
---
name: descriptive-kebab-case-name
visibility: public
description: |
  [Include specific trigger conditions and exact error messages]
  - What the skill does
  - When to use it
---

## Problem
[What situation triggers this skill]

## Context / Trigger Conditions
[Exact errors, symptoms, when to use]

## Solution
[Step-by-step with commands and code]

## Verification
[How to confirm it worked]

## Example
[Concrete example]
```

## Phase 4: Quality Gates

- [ ] Description has specific trigger conditions (not vague)
- [ ] Solution was verified to work
- [ ] Content is actionable AND reusable
- [ ] No sensitive information

## Phase 5: Update .claude/MEMORY.md
```markdown
[LEARN:category] Brief description -> see .claude/skills/[name]/SKILL.md
```

## Output
```
Skill created: .claude/skills/[name]/SKILL.md
  Trigger: [when to use]
  Problem: [what it solves]
  .claude/MEMORY.md: Updated
```
