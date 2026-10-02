# Personal Workflow Rule

This rule is part of a personal, Git-ignored sidecar. It adds working habits
for you, the person using this client here. Nothing in this file blocks a
commit, and none of these folders are visible to anyone else: they sit
under `.ai-bootstrap/`, which is Git-ignored even though the rest of
`.claude/` in this repository is tracked by the team. If anything here
conflicts with this repository's own tracked instructions, follow the
repository.

## Before non-trivial work

Read `.ai-bootstrap/MEMORY.md` first. It holds lessons you or a
past session recorded about this repository: patterns that work, traps
that do not, and facts worth not rediscovering.

## Decide whether a plan helps

A task that touches one file with an obvious fix does not need a plan —
implement it directly. A task that spans several files, several decisions,
or a design choice benefits from a plan. When it does and a planner agent
is available in this session, ask it for one; it returns the plan as text,
and you save it under `.ai-bootstrap/plans/`. When no planner agent is
available, write the plan yourself instead. Either way, use the templates
under `.claude/templates/` (`plan-big.md` for a multi-phase piece of work,
`plan-small.md` for one phase). A plan here is a tool you use when it
earns its cost, not a gate you must clear.

Before you split a plan into phases, check anything that would break the
design if it were false (a decisive assumption). Look in the code and docs
first. If they settle nothing, run a small experiment with one question and
a stop point, and say what it did not prove. An experiment is not approval
to change production code. Ask the person only about their own preferences,
such as a missing retention period, not about facts you can check, such as
whether a library supports streaming. Name the existing behavior each phase
must keep and the tests that show it, including a negative case, one that
should fail or be rejected. The templates offer an optional non-goals
section and requirement map. A simple plan needs neither, and requirement
IDs are labels in prose.

## Implement

Once you know what to change, make the change. Prefer the smallest
correct diff over a rewrite, and keep the existing style of the file
you are editing.

## Run the project's own checks

Before you consider a change done, run this project's own test, lint, and
type-checking commands. Find them in this repository's own documentation
(its README or its `docs/` folder) rather than assuming a fixed command
line — every project names its own commands differently. Fix a failure
before moving on. After a bug fix, rerun the original reproduction and
note what it now shows, or say plainly why you could not rerun it; a
passing test suite alone does not show the original symptom is gone.

## Review non-trivial diffs

For a change that is more than a one-line fix, and a reviewer agent is
available in this session, ask it to look at the diff, and give it the
approved requirements and any approved scope changes so it compares the
diff against them instead of its own guess. It returns a short
Markdown report grouped by severity as text, and you save that report
under `.ai-bootstrap/quality_reports/`. When no reviewer agent is
available, review the diff yourself against the review profiles under
`.claude/review-profiles/` that fit the change, and against the approved
requirements and scope changes (each should have an implementation and
evidence, and nothing unapproved should be added). For simple work the
request itself is the requirement. Write the same kind of report, say
plainly that it is a self-review, and save it the same way.
Read it, fix what is worth fixing, and move on — there is no required
second pass and no gate that stops a commit.

## At the end of a task

Write a short session log under `.ai-bootstrap/session_logs/`
describing what you did and why. If you learned something about this
repository that would help a future session — a pattern, a pitfall, a
useful command — add one line about it to
`.ai-bootstrap/MEMORY.md`. If a failure taught you something, put its
reproduction, cause, smallest fix, and guarding test in the log, and add a
`MEMORY.md` line only for a lesson the code and tests cannot show.

At the end of a task, or of a plan phase, give the person one short
summary: the goal, what changed, any departure from the plan, the checks you
ran and where their output is, open review findings, a decision only if one
is really needed, and the next step. Link the plan, report, and log instead
of copying them. The summary is not a new record and needs no approval.

## Explorations

If you want to try something and keep the scratch work without committing
it, put it under `.ai-bootstrap/explorations/`.

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
