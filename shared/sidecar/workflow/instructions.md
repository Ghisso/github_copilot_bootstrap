# Personal Workflow

This file is part of a personal, Git-ignored sidecar. It adds working
habits for you, the person using this client here, and nothing in it is
visible to a colleague or tracked by Git. If anything here conflicts with
this repository's own tracked instructions, follow the repository.

## Workflow

Read `.claude/ai-bootstrap/MEMORY.md` before non-trivial work — it holds
lessons a past session recorded about this repository.

A task touching one file with an obvious fix does not need a plan —
implement it directly. A task spanning several files or several decisions
benefits from a plan: ask the planner agent for one, saved under
`.claude/ai-bootstrap/plans/` using the templates under
`.claude/templates/`.

Before you consider a change done, run this project's own test, lint, and
type-checking commands, taken from this repository's own documentation
rather than assumed. Fix a failure before moving on.

For a change bigger than a one-line fix, ask the reviewer agent to look at
the diff. It returns a short Markdown report grouped by severity; save it
under `.claude/ai-bootstrap/quality_reports/`. There is no required second
pass, and nothing here blocks a commit.

At the end of a task, write a short session log under
`.claude/ai-bootstrap/session_logs/`, and add one line to
`.claude/ai-bootstrap/MEMORY.md` if you learned something worth keeping.
Scratch work you want to keep without committing goes under
`.claude/ai-bootstrap/explorations/`.

These folders are personal, Git-ignored, and survive a pull, a merge, or a
branch switch. This guidance is not enforced by any automated gate; the
repository's own guidance always wins when the two disagree.

## Reporting

Write to a person in precise, clear, direct, natural prose: use common
words when they are as precise as uncommon ones, one term per concept,
short direct sentences, and active voice where practical. Avoid idioms,
buzzwords, and unnecessary abbreviations; define an uncommon term the
first time you use it, and keep an established technical term when it is
the most precise word available.

Keep exact technical material exact: do not paraphrase identifiers, API
names, commands, paths, logs, error messages, or source code. Do not use a
bare label such as "P1" without saying what it means, and when you offer a
choice, say what each option actually changes.

## Tool routing

Use a direct file read when you know the path. Use exact text search (for
example `rg`) for literals such as symbols, error text, and filenames. Use
this client's own semantic or repository-search feature, when it has one,
for broader questions such as "where is this implemented?" — try the
direct read or exact search first, and only reach for semantic search when
those leave a real gap. Read a file normally before you edit it; the files
on disk are always the current truth.
