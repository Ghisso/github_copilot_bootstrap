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
     phases; a simple plan omits this section. A separate requirements spec is
     for requirements that span several artifacts. IDs such as REQ-001 are
     prose references, not frontmatter fields. -->

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
uv run python .claude/scripts/verify.py fast --format json
```

## Completion Evidence

The final phase listed under `phases:` must also run a documentation,
memory, and LEARN audit: sweep every live-advice surface for claims this plan
or earlier work invalidated, correct or supersede each one, leave dated
records (archived plans, dated design narratives, closed session logs)
unchanged, and record the audited surfaces and each one's outcome under a
`## Stale-claims surfaces checked` heading in that phase's closeout session
log. `verify.py`'s closeout gate requires that exact heading, non-empty,
whenever the phase it is closing out is this list's last entry.

In a repository where `openwiki/INSTRUCTIONS.md` exists, that final phase
may also need to be a dedicated knowledge-refresh phase: see the canonical
Knowledge-Refresh Final Phase rule in `.claude/instructions/workflow.instructions.md`
for exactly when and how, including its recursion guard.
