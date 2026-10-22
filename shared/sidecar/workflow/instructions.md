# Personal Workflow

This file is part of a personal, Git-ignored sidecar. It adds working
habits for you, the person using this client here, and nothing in it is
visible to a colleague or tracked by Git. If anything here conflicts with
this repository's own tracked instructions, follow the repository.

## Workflow

Read `.ai-bootstrap/MEMORY.md` before non-trivial work — it holds
lessons a past session recorded about this repository.

A task touching one file with an obvious fix does not need a plan —
implement it directly. A task spanning several files or several decisions
benefits from a plan: write one yourself, using a template under
`.claude/templates/` (`plan-big.md` for a multi-phase piece of work,
`plan-small.md` for one phase), and save it under `.ai-bootstrap/plans/`.
Before you split a plan into phases, check anything that would break the
design if it were false (a decisive assumption): look in the code and docs
first, then run a small experiment with one question and a stop point, and
say what it did not prove. An experiment is not approval to change production
code. Ask the person only about their own preferences, not about facts you
can check. Name the existing behavior each phase must keep and the tests that
show it, including a negative case, one that should fail or be rejected. The
templates offer an optional non-goals section and requirement map; a simple
plan needs neither, and requirement IDs are labels in prose.

Before you consider a change done, run this project's own test, lint, and
type-checking commands, taken from this repository's own documentation
rather than assumed. Fix a failure before moving on. After a bug fix,
rerun the original reproduction and note what it now shows, or say
plainly why you could not rerun it.

For a change bigger than a one-line fix, review the diff yourself against
the review profiles under `.claude/review-profiles/` that fit the change.
Compare it against the approved requirements and any approved scope
changes (for simple work the request itself is the requirement): each
should have an implementation and evidence, and nothing unapproved
should be added. Write a short Markdown report grouped by
severity and save it under `.ai-bootstrap/quality_reports/`. There is no
required second pass, and nothing here blocks a commit.

At the end of a task, write a short session log under
`.ai-bootstrap/session_logs/`, and add one line to
`.ai-bootstrap/MEMORY.md` if you learned something worth keeping. If a
failure taught you something, put its reproduction, cause, smallest fix, and
guarding test in the log; add a `MEMORY.md` line only for a lesson the code
and tests cannot show. At the end of a task, or of a plan phase, give the
person one short summary: the goal, what changed, any departure from the
plan, the checks you ran and where their output is, open review findings, a
decision only if one is really needed, and the next step. Link instead of
copying; the summary is not a new record and needs no approval.
Scratch work you want to keep without committing goes under
`.ai-bootstrap/explorations/`.

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
