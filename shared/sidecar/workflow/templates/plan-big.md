---
name: <slug>
type: big-plan
# status must occur exactly once: planning | in-progress | complete | cancelled
status: planning
originating_branch: dev
implementation_branch: <slug>_implementation
started_at:
phases:
  - <small-plan-slug-1>
  - <small-plan-slug-2>
current_phase:
# Cancellation fields (required only when status is cancelled):
# cancelled_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# cancelled_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# cancelled_evidence: <repository-relative readable UTF-8 CANCELLED artifact>
---

# Big Plan: <slug>

## Context

[Why this work exists]

## Goals

- [Goal]

## Non-Goals and Constraints (optional)

- [What this plan will not do, and limits it must respect]

## Design Overview

[High-level design]

## Requirement Map (optional)

<!-- The optional requirement map is for requirements that span several
     phases; a simple plan omits this section. IDs such as REQ-001 are prose
     references, not frontmatter fields. -->

| Requirement | Acceptance and existing contract | Owning phase | Evidence |
| --- | --- | --- | --- |
| REQ-001 | [Observable behavior; source or symbol] | `<small-plan-slug-1>` | [Test, probe, or log] |

## Phases

<!-- Each item's slug must match `phases:` exactly and in order. An optional
     trailing annotation may follow the closing backtick, but only after a
     whitespace boundary and only when it starts with one of `—`, `--`, `:`,
     `-`, or `(` (for example ` — description` or ` (note)`); anything else
     right after the backtick, including glued text, is rejected: -->
- [ ] `<small-plan-slug-1>`
- [ ] `<small-plan-slug-2>` (optional parenthetical note)

## Verification

```bash
# List this project's own test, lint, and type-check commands, taken from its
# README or docs/ folder.
```

## Completion Evidence

When the last phase closes, sweep the project's own docs for claims this
plan changed, correct each one, and note the surfaces checked in that
phase's session log under `.ai-bootstrap/session_logs/`. Nothing
here blocks a commit; the repository's own guidance wins on any conflict.
