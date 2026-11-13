---
type: workflow
title: Task lanes and the enforced lifecycle
description: How a request is classified into a task lane, how big and small plans drive the PRE-FLIGHT to PUSH lifecycle on an implementation branch, the fixed closeout sequence, the verification evidence contract, the pause and cancel paths, and which of these rules hooks and the verifier enforce versus policy text.
tags: [workflow, lifecycle, task-lanes, plans, closeout, verification, pause, cancel]
sources:
  - id: openwiki-source-cdb6e91f0fa049994704c487
    resource: repo://scripts/validate_plan_frontmatter.py
  - id: openwiki-source-71fc4d2e4c5527b7b8a068ba
    resource: repo://scripts/validate_targets.py
  - id: openwiki-source-fd43a5fc69056375b46b4386
    resource: repo://shared/agents/reviewer/prompt.md
  - id: openwiki-source-6aab0600aa722da66b818111
    resource: repo://shared/hooks/scripts/enforce-branch-state.sh
  - id: openwiki-source-fdc3f9ee55dbca2819c00001
    resource: repo://shared/hooks/scripts/record-branch-state.sh
  - id: openwiki-source-3bb98e65d9ade30d41bb39f0
    resource: repo://shared/policies/agent-reporting.instructions.md
  - id: openwiki-source-9fd0a35cebe588e6f39e1d28
    resource: repo://shared/policies/closeout.instructions.md
  - id: openwiki-source-d7818695b5f298cbcabc4568
    resource: repo://shared/policies/plan-lifecycle.instructions.md
  - id: openwiki-source-9fa38289fd921baabf765923
    resource: repo://shared/policies/workflow.instructions.md
  - id: openwiki-source-b7cd6d01f37550e855f61bdc
    resource: repo://shared/scripts/verify.py
  - id: openwiki-source-4a96f2f176ecd3fcc4f95f18
    resource: repo://shared/templates/plan-big.md
  - id: openwiki-source-588c1b68a254d094494d64f9
    resource: repo://shared/templates/plan-small.md
  - id: openwiki-source-a4eba4a0a79b0b185ca39ae9
    resource: repo://tests/test_validate_plan_frontmatter.py
generated: { by: "claude-code", at: "2026-11-13T15:20:28.565Z" }
verified:
  - by: openwiki/0.7.2
    at: 2026-11-13T15:30:24.556Z
---

# Task lanes and the enforced lifecycle

Source, tests, and the policies under `shared/policies/` outrank this page. The normative text is split across three policies, installed under `.claude/instructions/`: `workflow.instructions.md` (task lanes, plan first, branches, the orchestrator loop, the verification evidence contract), `closeout.instructions.md` (the CLOSEOUT steps through commit and push), and `plan-lifecycle.instructions.md` (future phases, pause, cancel, reopen, and the knowledge-refresh final phase).

Every change follows one lifecycle on one branch per big plan, and most of its rules are enforced by a hook, the plan validator, or the verifier rather than by policy text alone. Each rule below says which.

## Task lanes

A request is classified before planning or delegating, using the one decision table in the workflow policy. Time and line-count thresholds are never used. This is policy text; the hooks enforce what follows from it.

| Lane | Enter when | Owner and artifacts |
| --- | --- | --- |
| Read-only/reporting | no change is requested | main agent; evidence only; no lifecycle artifacts |
| Lightweight edit | explicit, one non-control-plane file, low risk, no commit or PR requested | main agent; focused edit plus proportionate verification; no lifecycle artifacts |
| Standard implementation | any other change, including anything with a requested commit or PR | orchestrator; micro-plan or full plan, then the specialist loop; full lifecycle |
| Control-plane/high-risk | any control-plane, security, dependency, migration, multi-file, user-data, generator, or script change | orchestrator; full plan; review with `code`, `architecture`, `security`, `tests`, `ponytail`; full lifecycle |

Any commit on an implementation branch must satisfy the full ceremony, whichever lane the work was classified into. The commit-subject bypasses (`fixup!`, `squash!`, `chore(typo):`, `docs(typo):`) are audited recovery exceptions, not a lane.

## Plans

- A **big plan** lives at `.claude/plans/<plan_name>.md` with `type: big-plan`, a `phases:` list, and `current_phase`. Statuses: `planning`, `in-progress`, `complete`, `cancelled`.
- A **small plan** lives at `.claude/plans/<phase_slug>.md` with `type: small-plan`, `parent_plan`, `phase_index`, `status`, and `closeout_session_log`. Statuses add `planned` and `paused`.
- `status` must occur exactly once. Templates are `shared/templates/plan-big.md` and `plan-small.md`.

`scripts/validate_plan_frontmatter.py`, shipped verbatim into consumers, enforces the frontmatter contract: valid statuses, exact pause and cancellation fields, the body phase inventory matching `phases:`, at most one unfinished `-knowledge-refresh` phase and only as the last phase, and the verification lints below. An earlier knowledge-refresh phase is exempt from that count only once it has settled, but a plan that has any knowledge-refresh phase must still end with one. Settled means the big plan's own `name` is not empty, and the sibling small-plan file named after the phase slug is a regular file, not a symlink, that declares `type: small-plan`, a `name` equal to the phase slug, a `parent_plan` equal to the big plan's `name`, and `status: complete` or `status: cancelled`. `check_runtime.py` and the `commit-msg` Git hook both run it.

Plan-first, as policy text: search `.claude/MEMORY.md` for the task's area tags (for example `[LEARN:installer]`) and keywords and read only the matching entries (the whole file is read only for a memory audit), clarify user preferences on ambiguous work, settle decisive technical assumptions with evidence in planner Phase 1, draft into `.claude/plans/` (or `.claude/explorations/` for proofs of concept), get approval, then implement. Before each new phase the orchestrator checks whether earlier outcomes materially change the remaining work and, only then, invokes one planner to revise affected future phases.

A separate spec and requirement IDs are optional, and equivalent approved content in the plan is enough. The big-plan template offers an optional non-goals section and an optional requirement map for requirements that span several phases; IDs such as `REQ-001` are prose references, not frontmatter fields, so the plan validator neither requires nor reads them.

At a phase boundary, agents give one short summary defined in `shared/policies/agent-reporting.instructions.md`: the objective and what changed, deviations, checks with links to evidence, open findings, a decision only when one is needed, and the next operation. It is written policy, not a gate. It creates no new record, asks for no approval when the next step is already authorized, and never pauses the work.

## The lifecycle

This diagram shows the stages and the loop back from a failed check.

```mermaid
flowchart LR
    A[PRE-FLIGHT] --> B[BRANCH] --> P[PLAN when needed] --> I[IMPLEMENT]
    I --> V[VERIFY] --> R[REVIEW] --> C[CLOSEOUT] --> K[COMMIT] --> U[PUSH]
    V -->|fail| I
    R -->|finding| I
    C -->|fail| I
```

- **PRE-FLIGHT and BRANCH.** Work starts from a clean `dev`; each big plan gets exactly one branch named `<plan_name>_implementation`. `enforce-branch-state.sh` denies a misnamed branch, a dirty or non-`dev` start, or a missing big plan with the wrong type or status, and then runs `validate_plan_frontmatter.py` on the big plan and its listed phase files, denying on any frontmatter or verification-contract error. `record-branch-state.sh` then writes the branch metadata and flips the first `planned` phase to `in-progress`.
- **IMPLEMENT.** Delegated to `coder`, which applies the `ponytail` skill once in `full` mode. Policy text.
- **VERIFY.** `verify.py fast` during implementation and `verify.py phase --persist` before review. The verifier is code.
- **REVIEW.** Delegated to `reviewer` with profiles from the routing table; findings return as JSON and are not yet persisted. Policy text, but the commit gate later requires the persisted report.
- **CLOSEOUT.** On entering CLOSEOUT, read and follow `.claude/instructions/closeout.instructions.md` step by step (summarized below).
- **FIX LOOP.** Any failure returns to IMPLEMENT; a later code change restarts verification and review.
- **COMMIT.** One explicitly staged commit per completed small plan, gated by `enforce-commit-gate.sh` and the `commit-msg` Git hook.
- **PUSH.** One normal non-force push with `GIT_TERMINAL_PROMPT=0`; a missing remote or authentication failure is a warning. `enforce-pr-gate.sh` and the `pre-push` Git hook gate it. A PR to `dev` is opened only when the user asks and only after every phase is complete or cancelled.

## The closeout sequence

`closeout.instructions.md` is the only place that lists the CLOSEOUT order; the orchestrator prompt, the `commit` and `code-review` skills, README, and the plan templates point to it. Each of its eight numbered steps carries a `*Why` reason, because each step reads what the one before produced:

1. documentation;
2. final AI state, which starts by reading the `learn` skill and routing each lesson to a project skill, a `MEMORY.md` entry, or none;
3. a first nested checkpoint (`git -C .claude add -A && git -C .claude commit`);
4. staging, findings, the phase receipt, and a closeout dry run, in one Bash command with no `git commit`;
5. a second nested checkpoint, because the closeout receipt hashes the session log;
6. the closeout receipt;
7. the commit, in its own Bash command;
8. one non-force push.

When the findings text names a protected path, step 4 writes the findings JSON with the Write tool to a scratch file and passes it as `--findings-json <file>`, because `protect-files` denies heredoc text that names a protected path. The plan-small template's Closeout Checklist has two boxes, both ticked at step 2; the sequence, not the checklist, gates the commit.

Two hard rules are enforced by the hooks:

- A Bash command that chains `git commit` after the findings or receipt steps is judged on the receipts that existed before it ran and is denied whole.
- Touching nested state between the receipt and the commit changes what the receipt binds and fails the commit with `closeout receipt governing control-plane provenance is stale`.

The file also says how to recover from the two stale-receipt errors. After `closeout receipt final tracked state is stale`, restage, then repeat step 6 alone for a documentation-only change or go back through the fix loop and steps 4 to 6 for anything else. After the provenance error, make the change final and repeat steps 3 to 6. `validate_targets.py` pins the step numbers, the reasons, the learn-skill read, both hard rules, and both messages in the generated file.

## What gates a completion commit

The commit gate requires, for an ordinary commit on an implementation branch (the written form is the `## Completion-commit gate` section of `closeout.instructions.md`):

- a passing closeout receipt whose `head_sha` and `tree_sha` match HEAD and the index;
- a findings report for the same phase with `counts.critical == 0` and `counts.major == 0` and a disposition on every MINOR;
- every review profile the changed paths require in that report (test surfaces need `tests`; control-plane, generator, and dependency paths need `code`, `architecture`, `security`, `tests`, and `ponytail`; any multi-file diff needs `ponytail`);
- at phase completion, the reviewer's recorded `gate_result` of `PASS` with no open request (the reviewer answers `FAIL` when a CRITICAL or MAJOR survives and `WARN` while a request is open);
- the closeout session log with LEARN evidence;
- a small plan whose frontmatter validates.

CRITICAL and MAJOR findings block the completion commit itself, not only the push. The push and PR gates re-check the same contract across every completed phase through the historical receipt chain, and a PR must target `dev`. The one exception is a plan's leading run of phases dated before 2026-08-29 that have no receipt file: closeout receipts did not exist then, so `verify.py` skips that run (`RECEIPT_CHAIN_SINCE`), and the skip ends at the first phase that does not qualify.

## The verification evidence contract

- A small plan's `## Verification` section holds fenced `bash` or `sh` blocks whose non-comment lines are required items. `verify.py closeout` runs them and records the results; the commit gate refuses a plan item without a result, a failed item, or an optional item without an outcome line.
- `## Optional Verification` holds numbered bullets for anything conditional or interactive. Each needs `- optional <n>: PASS|FAIL|NOT RUN — <detail>` in the log.
- When an implementation branch is created, and again at commit, `validate_plan_frontmatter.py` refuses a live plan (status `planned`, `in-progress`, or `paused`, dated on or after 2026-09-19) with no fenced block (`L1 verification-block-missing:`), hedged prose that makes a check conditional (`L2 hedged-verification:`), an item that cannot fail such as `|| true` (`L3 unfailable-verification:`), or an item that lists `verify.py closeout` (`L4 self-listed-closeout:`). Completed and cancelled plans are never re-judged.

## Pause and cancel

These rules, and the two sections after them, live in `.claude/instructions/plan-lifecycle.instructions.md`.


- **Pause** is small-plan-only and non-terminal, entered only on an explicit user request. It requires `paused_at` in exact UTC `YYYY-MM-DDTHH:MM:SSZ` form, a single-line `paused_reason`, and a `pause_session_log` containing `**Status:** PAUSED`. A checkpoint commit may then preserve tracked work without full closeout; it does not advance `current_phase` and still blocks PR creation. On resume the same plan returns to `in-progress`.
- **Cancel** means an authorized decision that a plan or phase will never run. It requires `cancelled_at`, a single-line `cancelled_reason`, and a `cancelled_evidence` artifact containing `**Status:** CANCELLED`. A cancelled phase needs no commit, findings, or closeout log; a cancelled big plan cannot start a branch; commit-count checks count completed phases only.

Both field sets are validated by `validate_plan_frontmatter.py`, including rejection of YAML block-scalar headers, impossible timestamps, and evidence missing the exact marker.

## Declaring future phases

New small plans default to `status: planned`. Branch creation activates the first phase and each completed-phase commit activates the next non-cancelled phase, flipping exactly one phase to `in-progress`. An unexpected next-phase status is never overwritten; the transition warns and leaves the phase machine where it is. `planned` blocks the same gates as `in-progress`.

## Reopening a completed big plan

A `complete` big plan can take new phases while its implementation branch still exists and is not merged; after a merge, a new big plan starts instead. The numbered procedure lives under "Reopening a completed big plan" in `shared/policies/plan-lifecycle.instructions.md`. In short:

1. Record the new findings, then draft the new small plans as `planned`. Only a knowledge-refresh phase's slug may end in `-knowledge-refresh`, because the validator counts any slug with that suffix.
2. If any listed phase is a knowledge-refresh phase, append one new `-knowledge-refresh` phase after the new phases. The validator requires this, so the final refresh and the stale-claims audit always follow the final code.
3. Set the big plan to `in-progress`, point `current_phase` at the first new phase, and append the new phases to `phases:` and to the body phase list in the same order.
4. Never edit a completed phase's plan, closeout log, findings, or receipts, and never re-persist its receipts. Set the first new phase to `in-progress` by hand, because no hook does it on an existing branch.

Reopening defers the strict terminal gates to the new final phase; it never escapes them.

## Representative tests

- `tests/test_validate_plan_frontmatter.py` covers every pause and cancellation field, the block-scalar and near-miss marker rejections, and the knowledge-refresh position rule, including a completed or cancelled earlier refresh phase, appending after a finished refresh, a slug that fails the slug pattern, and a sibling that fails the identity check (a symlink, an unrelated `parent_plan`, the wrong `type` or `name`, or an empty big-plan `name`).
- `tests/test_commit_closeout.py` covers the post-commit phase advance across commit-message sources and its refusals.
- `tests/test_hook_gates.py` covers the commit and push gate assertions against real temporary repositories.
- `tests/test_validate_targets.py` covers the closeout procedure pin (`closeout_procedure` tests, one negative case per rule) and the plan-small checklist shape.

## Related pages

- [Agent roster, prompts, and the skill library](../architecture/agents-and-skills.md)
- [Hook dispatcher and guardrail scripts](../architecture/hooks-and-guardrails.md)
- [Deterministic verification: verify.py modes, receipts, and findings](../operations/deterministic-verification.md)
