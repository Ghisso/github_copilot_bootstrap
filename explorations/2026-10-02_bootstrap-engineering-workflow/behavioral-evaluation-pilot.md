# Plan 2: Optional Behavioral Evaluation Pilot

**Status:** Deferred proposal; not implementation-ready or activated.
**Requirement:** REQ-006 from [the guidance plan](../../plans/engineering-workflow-improvements.md).
**Dependency:** None for delivery of the guidance plan. Consider this separately
after its changes and knowledge refresh are complete.

## Purpose and Limits

Measure a specific change in agent behavior only after showing that the test
can detect it. The earlier evidence → evaluator → guidance sequence is
superseded. Do not collect a special baseline before delivering guidance:
the same later runner can exercise recorded before/after source versions.

This is a bounded investigation, not a new evaluation platform. Reuse
`scripts/check_native_clients.py` only where it fits. No new provider registry,
SDK wrapper, model judge, dashboard, prompt optimizer, or commit gate. Keep the
existing planner-workload outputs and historical calibration unchanged.

## First Prove That the Cases Work

The orchestrator already requires plan requirements in every delegation.
The reviewer change makes its own inputs and comparison rule explicit.
A reviewer-level case can therefore measure that change if the task itself
does not supply the new instruction.

| Candidate case | Ordinary task and supplied inputs | What must be established first |
| --- | --- | --- |
| Requirement review | Ask for an ordinary code review. Supply approved requirements, approved changes if any, and a diff that misses a material requirement. Do not say “check requirements,” “consistency review,” or identify the missing behavior. | The selected reviewer actually loads the intended role/profile instructions. It can distinguish defective and repaired implementations, respect approved scope changes, and avoid rejecting a valid alternative. |
| Decisive technical uncertainty | Request a plan where a supplied technical assumption could invalidate implementation, alongside a matched version with evidence settling it. | The task tests investigation of a technical fact rather than clarification of an unspecified user preference. Evidence-seeking behavior can be observed without the prompt telling the agent to conduct a spike. |
| Original-symptom verification | Consider a small debugging task with a supplied reproduction and evidence of a proposed fix. | The tested workflow can reveal whether the reproduction was rerun. Merely spotting a weak assertion tests existing review advice and does not establish this change. If this needs unsupported execution or session handling, defer the case. |

Start with the smallest useful case; these are candidates, not a required
three-case suite. For any handoff claim, compare a deliberately broken
handoff with a correct one and inspect both the supplied packet and outcome.
For a reviewer-rule claim, hold the supplied requirements fixed and test the
reviewer comparison itself. A handoff check alone does not validate a
reviewer-instruction comparison.

Use one bounded scratch investigation to check sensitivity before building
a general runner mode. Keep expected answers outside the supplied task and
avoid instructions that reveal the defect. Include a correct case to detect
invented findings. If the case cannot distinguish the intended defect, revise
or drop it; do not proceed to a before/after claim. A successful sensitivity
check makes the case usable, but does not guarantee a difference between
source versions. Both versions may pass.

## Confirm Role Loading and Source Selection

Inspect the actual client invocation. The current Claude workload command
selects the planner; the Codex workload command does not explicitly select a
specialist. These facts do not establish that a future reviewer run loads the
reviewer instructions. Demonstrate that loading for the selected client and
case. If it cannot be observed, limit the claim or defer that client.

The existing `prepare_variants()` generates both consumers from its own
checkout and changes a shim in one copy. It is not a general source-version
comparison. Before implementing source selection, demonstrate how one fixed
runner will prepare separate consumers from two recorded source revisions,
for example using isolated worktrees or pre-generated bundles. Keep the
runner fixed while changing only the supplied bootstrap version; preserve
workspace ownership, permission limits, and old invocation compatibility.
A worktree by itself does not make the current runner select another source.

## Minimum Comparison Contract

Only after case sensitivity and role loading are demonstrated:

1. Select the exact before/after guidance revisions. Record unrelated changes
   that prevent attributing differences to the guidance.
2. Run both through the same validated runner and one fixed scorer: the code
   or short human scoring guide that assesses outputs. Freeze task inputs,
   expected answers, and scoring rules for the comparison.
3. Preserve bounded task outputs and enough permitted observations to repeat
   the scoring. Record client/provider and version, model, reasoning effort,
   permissions, runner/scorer revision, and source/bundle identity. Unknown
   settings remain unknown. Do not save credentials or full client transcripts.
4. Count correct outputs, behavioral failures, invalid outputs, unavailable
   runs, and missing observations separately. State each rate's denominator.
   A correct answer does not prove an action occurred; absent action evidence
   stays unobserved.
5. Report when model, settings, task, or unrelated source differences make
   results not directly comparable. If scoring changes, apply the new fixed
   rules to both saved output sets and preserve earlier results.

Use a short report and companion saved outputs. Add more machinery only for
a demonstrated need. Before native execution, record one client, a bounded
run count, timeout, and total budget; do not inherit the old nine-run proposal
as a requirement. No automatic retries, provider switching, or effort increases.
Outcomes remain advisory and can honestly show no difference.

## Ownership and Decision Before Implementation

The orchestrator owns bounded native execution and recorded observations.
A coder owns any executable fixtures, runner changes, and offline tests.
An independent reviewer assesses case sensitivity and comparison validity;
a documenter records the results. Reviewer permissions remain read/search-only.

A future implementation-ready plan must name the demonstrated role-loading
path, accepted cases, source-selection approach, budget, exact files, focused
tests, and required knowledge refresh under the policy then in force.
Create its small plans only after these decisions are supported by evidence.
No optional pilot work is required to close the immediate guidance plan.
