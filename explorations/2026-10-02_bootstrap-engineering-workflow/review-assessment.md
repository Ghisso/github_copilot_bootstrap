# Assessment of the Second Review

I agree with the recommendation to separate the guidance changes from the
behavioral evaluation. I would revise my proposal before implementation.
The strongest objection is that the pilot does not establish that it exercises
the changed instructions and handoffs. More careful scoring cannot fix that.

I checked the relevant current source and proposal. The local `dev` is now
`1626364`, which merged sidecar repair PR #43. I did not rerun tests or reopen
the external articles. This assessment does not activate or revise the plans.

| Concern | Risk | Recommendation |
| --- | --- | --- |
| Sidecar assumptions are stale | Medium | Update future work against the merged repair, preserving the original investigation as dated evidence. |
| Baseline and candidate capture may differ | High | Use one validated runner against both source revisions; common scoring alone does not establish equivalent collection. |
| Cases bypass changed roles and handoffs | High | Redesign the evaluation before implementing it; first prove that the relevant instructions are loaded and the changed handoff is exercised. |
| Evaluation work delays useful guidance changes | Medium | Separate a two-phase guidance plan from an optional later evaluation proposal. |

The assessment needs four qualifications.

1. **The orchestrator already requires plan requirements in delegation.**
   Its [general delegation rule](../../../shared/agents/orchestrator/prompt.md)
   says every packet includes plan requirements and non-goals. The claim that
   its reviewer packet contains no such requirement is too broad. However,
   the [reviewer's explicit inputs](../../../shared/agents/reviewer/prompt.md)
   list only scope/diff, profiles, and gate. Neither contract clearly binds
   review to the approved plan/specification and approved scope changes.
   The fix should make those contracts agree and clarify authority, while
   preserving optional specifications and requirement IDs.

2. **Building a scorer after collecting outputs is not inherently invalid.**
   Saved outputs can be scored later with one common implementation. The
   unresolved problem in my design is collection: Phase A uses a scratch
   invocation, while Phase B builds the capture mode. I did not establish
   equivalent prompts, role loading, permissions, and evidence capture.
   The proposed later comparison with one runner is simpler and stronger.
   The [current runner](../../../scripts/check_native_clients.py) does
   generate both consumers from its own checkout, so source selection needs
   explicit design; a worktree alone does not make one runner select both.

3. **The cases have limited value, but cannot support the intended claim.**
   Supplying requirements directly can test a reviewer's reasoning; it cannot
   show that the orchestrator now supplies them correctly. Likewise, a weak
   assertion example can be a useful regression check without demonstrating
   improvement over the existing tests profile. The current Codex workload
   command does not explicitly select the changed specialist, and Claude's
   command selects the planner. The proposal leaves role loading unresolved.
   I would not assert that Codex can never load those instructions; I would
   require evidence that the tested invocation actually does. The retention
   example also fails to cover the promised investigation of an uncertain
   technical contract: clarification and investigation are different behaviors.

4. **Small sample size does not make evidence controls unnecessary.**
   Preserved outputs, fixed scoring, runtime identity, and separate missing
   or invalid results remain necessary for any credible comparison. The
   problem is building that machinery before establishing a useful test.
   Deterministic checks of generated guidance can establish that the required
   text is present and consistent; they cannot establish that agents follow it.

I recommend the proposed split: implement the bounded guidance changes and
their focused deterministic checks, then perform the required knowledge
refresh. Preserve the independent reviewer, existing verification authority,
relaxed sidecar semantics, and the merged repair's caller-saved outputs under
`.ai-bootstrap/`. Make no measured behavior-improvement claim from text checks.

Keep the behavioral pilot as a separate optional proposal. Before building
it, identify the exact changed behavior each case must exercise, establish
role loading and handoff observation, and demonstrate that a deliberately
broken handoff is distinguishable from a correct one. Then compare the
recorded before/after source revisions using the same runner and scorer.

I also accept the smaller corrections: a coder should own executable
fixtures, use “the author's profile,” and replace or explain terms such as
“oracle” and “confounded comparison.” “Same bounded native cost” should state
the actual planned run count and time limit instead.
