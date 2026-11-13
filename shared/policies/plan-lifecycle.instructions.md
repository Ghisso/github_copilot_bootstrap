---
description: "Always-on: rules for changing a plan's course. Load when declaring future phases, pausing, cancelling, or reopening a plan, or adding the knowledge-refresh final phase."
applicability: always
---

# Plan Lifecycle

This policy holds the rules for changing a plan's course: declaring future
phases, pausing, cancelling, reopening a completed big plan, and the
knowledge-refresh final phase. The workflow policy
(`.claude/instructions/workflow.instructions.md`) keeps one trigger line for
each topic and points here.

---

## Declaring future phases

`planned` is a small-plan-only status for a phase that has not started. New
small-plan files default to `planned` and need only the ordinary identity
fields; they carry no pause, cancellation, or closeout evidence. Branch
creation activates the first phase, and a completed-phase commit activates the
next non-cancelled phase, by flipping exactly that one phase from `planned` to
`in-progress`; every other declared phase is left untouched. An unexpected
next-phase status (`paused`, `complete`, invalid, duplicate, missing, or
unreadable) is never overwritten; the transition warns and leaves the phase
machine at its current phase instead. `planned` is unfinished and blocks the
same push/PR and completion gates as `in-progress`. Plans already installed
with a future phase marked `in-progress` remain valid.

## Pausing a phase for a checkpoint

`paused` is a small-plan-only, non-terminal status. Enter it only after an
explicit user request to stop, pause, or checkpoint and resume later; a failed
check alone does not authorize it. If the user names a safe boundary, reach it
before pausing when it is safe to do so.

A paused phase requires `paused_at` in exact UTC `YYYY-MM-DDTHH:MM:SSZ`
format, meaningful single-line `paused_reason`, and repository-relative
`pause_session_log` evidence that resolves to a readable UTF-8 log containing
`**Status:** PAUSED`. The log records the reason, completed and remaining work,
verification already run, incomplete checks, and the exact resume point.

After the evidence is recorded, a checkpoint commit may preserve tracked outer
repository work without final findings, LEARN, DOCUMENT, or COMPLETED
closeout. It is not a bypass, does not advance `current_phase`, and leaves the
big plan `in-progress`. Do not create an empty outer-repository checkpoint
commit when only AI-state files changed; persist the PAUSED plan and session log
through the normal AI-state checkpoint path instead. A paused phase remains
unfinished. After its checkpoint commit, it may be pushed as a durable remote
checkpoint only when paused-publication invariants pass. It still blocks PR
creation and final closeout.

On resume, read the paused small plan and PAUSED log, inspect `git log --oneline
-10`, `git status`, and the current diff, report the recorded resume point, set
the same phase back to `in-progress`, preserve the latest pause metadata, and
continue without creating another small plan. Complete the ordinary lifecycle
once the phase actually finishes.

## Conditional checkpoint branch

When the user explicitly requests a pause, write the PAUSED session log and
required pause frontmatter, then checkpoint tracked outer-repository work. Do
not run this branch merely because a gate failed. The checkpoint leaves the
phase active; on resume, reopen that same small plan and run the full loop
before its normal completion commit.

## Cancelling a plan or phase

`cancelled` means an authorized decision was made that a plan or phase will
never run. It is distinct from `complete` and requires `cancelled_at` as a real
UTC calendar date and time in exact `YYYY-MM-DDTHH:MM:SSZ` format; a meaningful
`cancelled_reason` written as plain single-line scalar prose without leading
quotes, YAML block headers, collections, list markers, or comment-only values;
and a repository-relative `cancelled_evidence` path that stays inside the
repository and resolves to an existing regular, readable UTF-8 text artifact
containing the same-line prefix `**Status:** CANCELLED`.

A cancelled phase requires no commit, findings report, or closeout
session log. A cancelled big plan is terminal and cannot start an implementation
branch. A branch containing cancelled phases reaches final push/PR closeout only
when at least one phase is complete, every cancelled phase has the full evidence
contract, and commit-count checks count completed phases only. The push gate
binds findings to the last completed phase. Commit closeout skips cancelled
phases when advancing `current_phase`, while a commit whose current phase is
cancelled remains blocked.

## Reopening a completed big plan

A `complete` big plan can take new phases instead of starting a new plan.
The "Knowledge-Refresh Final Phase" exemption below is what keeps this legal
for a plan that already ended with a knowledge-refresh phase.

1. Reopen only while the implementation branch exists and is not merged.
   After a merge, start a new big plan instead.
2. Inspect the completed phases' outcomes and review findings. Record new
   findings in a quality report.
3. Draft the new small plans as `planned`, with the next phase letters and
   `phase_index` values. Only a knowledge-refresh phase's slug may end in
   `-knowledge-refresh`; the validator counts any slug with that suffix.
4. If any listed phase is a knowledge-refresh phase, append one new
   `-knowledge-refresh` phase after the new phases. The validator requires a
   plan with knowledge-refresh phases to end with one.
5. Edit the big plan: `status: in-progress`, `current_phase:` the first new
   phase, and the new phases appended to `phases:` and to the body
   `## Phases` list in the same order. Update Done Criteria and Completion
   Evidence to name the new final phase. Keep `started_at` and the branch
   fields.
6. Never edit a completed phase's small plan, closeout session log,
   findings report, or receipts (Immutability in
   `.claude/instructions/closeout.instructions.md`). Never re-persist a
   completed phase's receipts, even when `verify.py` suggests it while the big
   plan is still `complete`.
7. Set the first new phase to `in-progress` when its implementation starts;
   no hook does this on an existing branch.
8. Checkpoint the nested `.claude` repository.
9. The new final phase meets the same strict terminal gates as any other
   phase. Reopening defers them; it never escapes them.

---

## Knowledge-Refresh Final Phase

This is the single authoritative definition of the knowledge-refresh final
phase. The planner prompt, orchestrator prompt, the `plan-decomposition`
skill, and the big-plan template link here instead of restating it.

**When to add it.** While drafting or revising a big plan's `phases:` list,
append one dedicated final small plan, after every phase already listed,
only when all of these hold: `openwiki/INSTRUCTIONS.md` exists; the plan has
more than one phase; the plan changes documentable outer-repository
behavior (not read-only/reporting, and not AI-state-only work); and the
plan's own purpose is not itself a knowledge/OpenWiki refresh. Name the
appended phase's slug so it ends with `-knowledge-refresh` (for example
`2026-09-19_phase-D-knowledge-refresh`, not `...-phase-D-openwiki-sync` or
any other conventionally reasonable but differently worded slug) — this
exact suffix is what the termination rule below and
`scripts/validate_plan_frontmatter.py` both key on; a phase named anything
else is invisible to both and the recursion guard silently does nothing.

**Termination.** This rule runs only while drafting or revising a plan's
`phases:` list, and only ever appends to the end of that list. Recognize an
existing knowledge-refresh phase by its slug suffix, `-knowledge-refresh`;
if the phase already at the end of the list carries that suffix, do not
append another one. The self-referential exclusion above means a plan whose
own purpose is a knowledge refresh never has one appended to itself, so
that phase can never produce a second one, whether through a later revision
of the same plan or as the reason for a follow-up plan.
`scripts/validate_plan_frontmatter.py` enforces this deterministically: a
big plan fails validation if more than one phase carries the
`-knowledge-refresh` suffix, or if one exists but is not the last phase.
Reopening a completed big plan (see "Reopening a completed big plan" above)
does not defeat this rule: the validator exempts an
earlier, non-final knowledge-refresh phase from that count once it confirms
the phase has settled, so a finished refresh phase stays where it is and the
rule still requires the reopened plan to end with one new knowledge-refresh
phase. Settled means the big plan's own `name` is non-empty, and the
sibling small-plan file next to it (named after the phase slug) is a
regular file, not a symlink, whose frontmatter declares `type: small-plan`,
a `name` equal to the phase slug, a `parent_plan` equal to the big plan's
`name`, and `status: complete` or `status: cancelled`.

**Shape.** Small, and only this: refresh through
`.claude/skills/knowledge-refresh/SKILL.md`, inspect the generated
diff, run the standing final-phase documentation/memory/LEARN audit in
`.claude/instructions/closeout.instructions.md` — the same
`## Stale-claims surfaces checked` requirement;
this phase is what satisfies it, not a second, competing one — then review,
verify, and commit like any other phase. Setup work, such as enabling
OpenWiki for the first time or upgrading it, belongs in an earlier phase, not
in this one.

**Failure.** A failed refresh blocks that phase's completion like any other
failed phase, without fabricating a deterministic verification failure —
see `.claude/skills/knowledge-refresh/SKILL.md` for that boundary. A provider or
authentication failure is reported with OpenWiki's own actionable error
and retried once fixed; an enabled repository's required refresh is never
silently skipped. An unreachable recorded base HEAD follows the skill's
rebaseline rule, never `--init`.
