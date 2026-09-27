# Personal Workflow Rule

This rule is part of a personal, Git-ignored sidecar. It adds working habits
for you, the person using this client here. Nothing in this file blocks a
commit, and none of these folders are visible to anyone else: they sit
under `.claude/ai-bootstrap/`, which is Git-ignored even though the rest of
`.claude/` in this repository is tracked by the team. If anything here
conflicts with this repository's own tracked instructions, follow the
repository.

## Before non-trivial work

Read `.claude/ai-bootstrap/MEMORY.md` first. It holds lessons you or a
past session recorded about this repository: patterns that work, traps
that do not, and facts worth not rediscovering.

## Decide whether a plan helps

A task that touches one file with an obvious fix does not need a plan —
implement it directly. A task that spans several files, several decisions,
or a design choice benefits from a plan. When it does, ask the planner
agent for one. Save it under `.claude/ai-bootstrap/plans/`, using the
templates under `.claude/templates/` (`plan-big.md` for a multi-phase
piece of work, `plan-small.md` for one phase). A plan here is a tool you
use when it earns its cost, not a gate you must clear.

## Implement

Once you know what to change, make the change. Prefer the smallest
correct diff over a rewrite, and keep the existing style of the file
you are editing.

## Run the project's own checks

Before you consider a change done, run this project's own test, lint, and
type-checking commands. Find them in this repository's own documentation
(its README or its `docs/` folder) rather than assuming a fixed command
line — every project names its own commands differently. Fix a failure
before moving on.

## Review non-trivial diffs

For a change that is more than a one-line fix, ask the reviewer agent to
look at the diff. It returns a short Markdown report grouped by severity.
Save that report under `.claude/ai-bootstrap/quality_reports/`. Read it,
fix what is worth fixing, and move on — there is no required second pass
and no gate that stops a commit.

## At the end of a task

Write a short session log under `.claude/ai-bootstrap/session_logs/`
describing what you did and why. If you learned something about this
repository that would help a future session — a pattern, a pitfall, a
useful command — add one line about it to
`.claude/ai-bootstrap/MEMORY.md`.

## Explorations

If you want to try something and keep the scratch work without committing
it, put it under `.claude/ai-bootstrap/explorations/`.

## What this is, and is not

These folders are yours. They are Git-ignored, so they never show up in
`git status`, never get committed, and never reach a colleague. They
survive a pull, a merge, or a branch switch. Nothing in this file is
enforced by any automated gate: it is guidance for how you choose to
work, and the repository's own guidance always wins when the two
disagree.

Because these folders are Git-ignored, `git clean -x` (and
`git clean -fdx`) deletes them along with every other ignored file, and
there is no automatic backup. Run `install_bootstrap.py <repo> --backup-state`
to copy them into the Git directory first, a location `git clean` never
touches.
