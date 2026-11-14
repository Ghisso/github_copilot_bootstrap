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

Then route the lesson before creating anything: a cross-project reusable
lesson becomes a skill (Phase 3); a project-specific fact that current
repository evidence cannot reliably re-derive becomes a `.claude/MEMORY.md`
entry (Phase 5); a fact already derivable from current source, tests, or an
enabled OpenWiki refresh gets no redundant entry — see the canonical
Knowledge Ownership contract in `.claude/instructions/workspace.instructions.md`;
and a historical execution fact belongs in a session log or plan, never
MEMORY.

For an observed failure, connect it to its reproduction, cause, smallest
correction, and regression, and record those in the session log. Prefer an
existing test or skill as the durable home; add no new instruction where none
is justified. Not every failure yields a lesson.

Example with no new instruction: a test fails after a rename because one call
site still uses the old helper name. Reproduction: the failing test. Cause: the
missed call site. Smallest correction: update that call. Regression: the same
test, which already covers the path. Code and test now enforce the fact, so no
skill, `.claude/MEMORY.md` entry, or instruction is justified.

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
- Nothing related → create a new skill.
- Same trigger and fix, or partial overlap → extend the existing skill, but
  only where you own it:
  - In this bootstrap's authoring repository, update `shared/skills/<name>`.
  - In a consumer project, update a skill only when its folder holds
    `.project-skill`.
- Never edit a shipped skill in a consumer. A refresh overwrites it, and
  marking it is a name clash. Create a new marked project skill with its own
  name, or write a `.claude/MEMORY.md` entry instead.

## Phase 3: Create Skill

Create the skill in the canonical location for the repository you are in:
`shared/skills/[skill-name]/SKILL.md` in this bootstrap's authoring
repository, so it regenerates into every target; `.claude/skills/[skill-name]/SKILL.md`
in an installed consumer project, which has no `shared/skills/`.

In a consumer project, also create an empty `.project-skill` file in the
skill folder (`.claude/skills/[skill-name]/.project-skill`). Mark every
project skill when you create it. What a refresh does with an unmarked folder
depends on its name:

- The bootstrap neither ships the name nor shipped it before: the refresh
  refuses to run until you mark or remove the folder.
- The name is newly shipped and the shipped-before record does not list it:
  the refresh refuses and does not overwrite the folder.
- There is no shipped-before record and the bootstrap ships the name: the
  refresh overwrites the folder.
- The name is a retired bootstrap name: the refresh deletes the folder.

Rules:

- Use a lowercase kebab-case name equal to `name:`, and one no bootstrap or
  third-party skill uses.
- Put no symlinks in the folder.
- Keep `description` plus `when_to_use` to at most 300 characters, trigger
  words first. The validator enforces this in the authoring repository; keep
  to it in consumers too.
- Codex and Antigravity read only `.agents/skills/`, so they see the skill
  after the next refresh copies it to `.agents/skills/[skill-name]/`. Copilot
  also reads `.claude/skills/`, so it can find a new project skill without a
  refresh. Once a mirror copy exists in `.agents/skills/`, Copilot lists that
  copy, so edits show after the next refresh. Never create or edit that
  folder by hand.
- Create or edit the skill no later than CLOSEOUT step 2, because receipts
  bind `.claude/` runtime files.

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
[LEARN:category] Brief description -> see <shared/skills or .claude/skills>/[name]/SKILL.md
```

## Output

Report the path actually written, which depends on the repository type in
Phase 3: `shared/skills/` in the bootstrap authoring repository,
`.claude/skills/` in an installed consumer project.

```
Skill created: <shared/skills or .claude/skills>/[name]/SKILL.md
  Trigger: [when to use]
  Problem: [what it solves]
  .claude/MEMORY.md: Updated
  Marker (consumer project): .claude/skills/[name]/.project-skill
```
