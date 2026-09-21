---
type: workflow
title: Task lanes and the enforced lifecycle
description: How a request is classified into a task lane, how big and small plans drive the PRE-FLIGHT to PUSH lifecycle on an implementation branch, the fixed closeout sequence, the verification evidence contract, the pause and cancel paths, and which of these rules hooks and the verifier enforce mechanically versus policy text.
tags: [workflow, lifecycle, task-lanes, plans, closeout, verification, pause, cancel]
verified:
  - by: openwiki/0.5.2
    at: 2026-09-21T03:23:13.016Z
sources:
  - id: openwiki-source-cdb6e91f0fa049994704c487
    resource: repo://scripts/validate_plan_frontmatter.py
  - id: openwiki-source-fdc3f9ee55dbca2819c00001
    resource: repo://shared/hooks/scripts/record-branch-state.sh
  - id: openwiki-source-9fa38289fd921baabf765923
    resource: repo://shared/policies/workflow.instructions.md
  - id: openwiki-source-588c1b68a254d094494d64f9
    resource: repo://shared/templates/plan-small.md
generated: { by: "claude-code", at: "2026-09-21T03:23:13.016Z" }
---

# Task lanes and the enforced lifecycle

The normative source is `shared/policies/workflow.instructions.md`,
installed as `.claude/instructions/workflow.instructions.md`. This page
summarizes it and marks which rules are enforced by code. Where this page
and the policy or code disagree, they are right.

## Task lanes

Every request is classified before planning or delegating, using the one
decision table in the workflow policy. Time and line-count thresholds are
never used.

| Lane | Enter when | Owner and artifacts |
|---|---|---|
| Read-only/reporting | no change is requested; a diagnosis stays here until a fix is asked for | main agent; evidence only; no lifecycle artifacts |
| Lightweight edit | explicit, one non-control-plane file, low risk, no dependency, migration, user-data, security, or control-plane impact, and no commit or PR requested | main agent; focused edit plus proportionate verification; no lifecycle artifacts |
| Standard implementation | any other change, including anything with a requested commit or PR | main-thread orchestrator; micro-plan or full plan, then the specialist loop; full lifecycle |
| Control-plane/high-risk | any control-plane, security, dependency or lockfile, migration, multi-file, user-data, generator, or script change | main-thread orchestrator; full plan; review with `code`, `architecture`, `security`, `tests`, and `ponytail`; full lifecycle |

The lane table is policy text. What the hooks enforce is downstream of it:
any commit on an implementation branch must satisfy the full ceremony,
whichever lane the work was classified into. The narrow commit-subject
bypasses (`fixup!`, `squash!`, `chore(typo):`, `docs(typo):`) are audited
recovery exceptions, not a lane.

## Plans

Work is planned as one **big plan** at `.claude/plans/<plan_name>.md` with
`type: big-plan`, a `phases:` list, and `current_phase`, plus one **small
plan** per phase at `.claude/plans/<phase_slug>.md` with `type: small-plan`,
`parent_plan`, `phase_index`, `status`, and `closeout_session_log`. Big-plan
statuses are `planning`, `in-progress`, `complete`, and `cancelled`;
small-plan statuses add `planned` and `paused`. `status` must occur exactly
once. Templates live in `shared/templates/plan-big.md` and `plan-small.md`.

Plan-first means: check `.claude/MEMORY.md` for relevant lessons, clarify
ambiguous work with the user, draft into `.claude/plans/` (or
`.claude/explorations/` for proof-of-concept work), get approval, then
implement. An approved implementation-ready plan skips new planning; before
each new phase the orchestrator checks whether completed-phase outcomes or
review findings materially change the remaining work and, only then,
invokes one planner to revise affected future phases.

`scripts/validate_plan_frontmatter.py`, shipped verbatim into consumers as
`.claude/scripts/validate_plan_frontmatter.py`, enforces the frontmatter
contract mechanically: valid statuses, exact pause and cancellation fields
when those statuses are used, the body phase inventory matching `phases:`,
at most one `-knowledge-refresh` phase and only as the last phase, and the
verification-contract lints below. `check_runtime.py` and the `commit-msg`
Git hook both run it.

## The lifecycle

```
PRE-FLIGHT -> BRANCH -> PLAN when needed -> IMPLEMENT -> VERIFY -> REVIEW -> CLOSEOUT -> COMMIT -> PUSH
```

- **PRE-FLIGHT and BRANCH.** Work starts from a clean `dev`. Each big plan
  gets exactly one branch named `<plan_name>_implementation`. Enforced:
  `enforce-branch-state.sh` denies a branch that is misnamed, not created
  from clean `dev`, or lacking a big plan with `type: big-plan` and a
  `planning` or `in-progress` status. `record-branch-state.sh` then writes
  `originating_branch`, `implementation_branch`, `started_at`, and
  `current_phase`, flipping the first `planned` phase to `in-progress`.
- **IMPLEMENT.** Delegated to `coder`, which applies the `ponytail` skill
  once in `full` mode and simplifies the changed scope. Policy text.
- **VERIFY.** Focused checks and `verify.py fast` during implementation;
  `verify.py phase --persist` before review. A deterministic failure goes
  back to the coder with its changed scope.
- **REVIEW.** Delegated to `reviewer` with profiles from the routing table.
  The reviewer returns surviving findings as JSON and persists nothing.
- **CLOSEOUT.** The fixed sequence below.
- **FIX LOOP.** Any failure in verification, review, or closeout returns to
  IMPLEMENT; a later code change restarts verification and review.
- **COMMIT.** One commit per completed small plan, explicitly staged.
- **PUSH.** One normal non-force push to the branch upstream with
  `GIT_TERMINAL_PROMPT=0`; a missing remote or authentication failure is a
  warning that keeps the local commit. A PR to `dev` is opened only when
  the user asks and only after every phase is complete or cancelled; the
  user merges.

## The closeout sequence

The policy fixes eight steps because each step reads what the previous one
produced:

1. **Documentation.** Update `README.md` and `docs/` for changed public
   behavior; on the big plan's last phase, also run the stale-claims audit.
2. **Final AI state.** Small plan `status: complete` with
   `closeout_session_log` filled and every step ticked; big-plan phase
   ticked; `[LEARN]` entries or the no-lessons marker in the session log and
   `MEMORY.md`.
3. **First nested checkpoint.** `git -C .claude add -A && git -C .claude commit`;
   `verify closeout` refuses to run while the big plan is not retrievable
   from nested Git.
4. **Stage, findings, phase receipt, closeout dry run**, in one Bash command
   with no `git commit`: explicit `git add` of the intended files, an
   explicit `disposition` and `reason` on every surviving MINOR,
   `record_findings.py` with one `--profile` per reviewed profile,
   `verify.py phase --persist`, then `verify.py closeout --format text`
   whose per-item summary lines go into the log's `## Verification`
   section with `**Status:** COMPLETED`.
5. **Second nested checkpoint**, because the closeout receipt hashes the
   session log.
6. **Closeout receipt.** `verify.py closeout --format json --persist`.
7. **Commit**, in its own Bash command. The `post-commit` Git hook advances
   `current_phase` and publishes nested state.
8. **Push.**

Two hard rules are enforced by hooks, not just written down. A Bash command
that chains `git commit` after the findings or receipt steps is judged on
the receipts that existed before it ran and is denied whole. Touching
nested state between the receipt and the commit changes what the receipt
binds and fails the commit with
`closeout receipt governing control-plane provenance is stale`.

## What gates a completion commit

The commit gate (`enforce-commit-gate.sh` and the `commit-msg` Git hook)
requires, for an ordinary commit on an implementation branch: a passing
closeout receipt whose `head_sha` and `tree_sha` match the current HEAD and
index; a findings report for the same phase with `counts.critical == 0`
and `counts.major == 0` and a disposition on every MINOR; the closeout
session log with LEARN evidence; and a small plan whose frontmatter
validates. CRITICAL and MAJOR findings block the completion commit itself,
not only the push. The push and PR gates re-check the same contract across
every completed phase through the historical receipt chain, and a PR must
target `dev`.

## The verification evidence contract

A small plan's `## Verification` section holds fenced `bash` or `sh` blocks
whose non-comment lines are required items; `## Optional Verification`
holds numbered bullets for anything conditional or interactive. `verify.py
closeout` runs every required item itself and records the results in the
receipt; the commit gate refuses a plan item without a result, a failed
item, or an optional item without an outcome line in the log. At plan
approval, `validate_plan_frontmatter.py` refuses a live plan (status
`planned`, `in-progress`, or `paused`, dated on or after 2026-09-19) that
has no fenced block (`L1 verification-block-missing:`), hedged prose that
makes a check conditional (`L2 hedged-verification:`), an item that cannot
fail such as `|| true` (`L3 unfailable-verification:`), or an item that
lists `verify.py closeout` itself (`L4 self-listed-closeout:`). Completed
and cancelled plans are dated records and are never re-judged.

## Pause and cancel

**Pause** is a small-plan-only, non-terminal status entered only on an
explicit user request to stop and resume later; a failed check never
authorizes it. It requires `paused_at` in exact UTC `YYYY-MM-DDTHH:MM:SSZ`
form, a single-line `paused_reason`, and a `pause_session_log` that
contains `**Status:** PAUSED`. A checkpoint commit may then preserve
tracked work without findings, LEARN, or COMPLETED closeout; it does not
advance `current_phase`, and the phase still blocks PR creation. On resume
the same small plan goes back to `in-progress` with its pause metadata
preserved.

**Cancel** means an authorized decision that a plan or phase will never
run. It requires `cancelled_at`, a single-line `cancelled_reason`, and a
`cancelled_evidence` artifact containing `**Status:** CANCELLED`. A
cancelled phase needs no commit, findings, or closeout log; a cancelled big
plan cannot start a branch; commit closeout skips cancelled phases when
advancing, and commit-count checks count completed phases only.

Both sets of fields are validated mechanically, including rejection of YAML
block-scalar headers, impossible timestamps, and evidence files missing the
exact status marker.

## Declaring future phases

New small-plan files default to `status: planned`. Branch creation activates
the first phase and each completed-phase commit activates the next
non-cancelled phase by flipping exactly that one phase to `in-progress`. An
unexpected next-phase status (`paused`, `complete`, invalid, duplicate, or
missing) is never overwritten; the transition warns and leaves the phase
machine where it is. `planned` blocks the same push and completion gates as
`in-progress`.

## Representative tests

`tests/test_validate_plan_frontmatter.py` covers every pause and
cancellation field, the block-scalar and near-miss marker rejections, and
that `paused` is invalid for a big plan. `tests/test_commit_closeout.py`
covers the post-commit phase advance across commit-message sources and its
refusals. `tests/test_hook_gates.py` covers the commit and push gate
assertions against real temporary repositories.

## Related pages

- [Agent roster, prompts, and the skill library](/openwiki/architecture/agents-and-skills.md)
- [Hook dispatcher and guardrail scripts](/openwiki/architecture/hooks-and-guardrails.md)
- [Deterministic verification: verify.py modes, receipts, and findings](/openwiki/operations/deterministic-verification.md)
