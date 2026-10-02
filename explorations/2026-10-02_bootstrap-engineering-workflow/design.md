# Implementation Design

**Status:** Proposed; source-supported gaps are in [the investigation](README.md).

## One Existing Lifecycle

```mermaid
flowchart LR
    P[PRE-FLIGHT: existing task lane and evidence] --> L[PLAN: decisive risks, outcomes, contracts, test strategy]
    L --> I[IMPLEMENT: approved scope and existing coder]
    I --> V[VERIFY: existing deterministic checks]
    V --> R[REVIEW: requirements, contracts, meaningful tests]
    R --> C[CLOSEOUT: evidence links and concise summary]
    R -->|surviving defect| I
```

Branch creation, plan approval, commit, push, and PR authorization retain
their current places in the canonical policy. The diagram emphasizes the
engineering steps; it does not replace the full lifecycle.

### PRE-FLIGHT and PLAN

Reuse the supplied evidence packet and approved decisions. Ask only about
material unresolved choices. A lightweight task does not gain a spec,
traceability table, spike, or extra approval by default.

For complex work, establish success evidence before splitting phases:

1. Identify assumptions that could invalidate the design. Resolve from
   existing code/docs first, then use a bounded experiment where needed.
   Specify question, observable result, stop condition, and remaining limits.
   A scratch experiment never authorizes production changes.
2. Use the existing requirements template when a separate spec helps; an
   equivalent section in the big plan is enough. Preserve user decisions.
3. Cite existing contracts and expected failure/compatibility behavior.
4. Identify critical tests, negative cases, real integration boundaries,
   independent expected values, and criteria with no available verification.
5. Decompose phases and check the requirement mapping for gaps or conflicts.

Use stable requirement IDs within one feature when references span artifacts.
Do not recycle an ID to mean something different. Requirement changes follow
the existing material-scope decision process; do not edit completed evidence.

Suggested optional table, maintained in one place:

| Requirement | Acceptance and existing contract | Owning phase | Implementation | Evidence |
| --- | --- | --- | --- | --- |
| REQ-001 | User-observable behavior; source/symbol | phase slug | Intended module, later actual symbol | Test/probe ID; later result/log/receipt link |

The spec/big plan owns required behavior. Small plans reference IDs rather
than duplicating the requirements. The session log records completion links;
it need not rewrite the table or copy receipt output beyond today's rules.
Deferred/untestable rows stay explicit. A valid Markdown table is not proof
of satisfaction and gets no new deterministic gate.

### IMPLEMENT, VERIFY, and REVIEW

Coder handoffs include the requirement/contract references. A changed
interface, extra feature, or failed decisive assumption is reported through
the existing scope-change route. The coder does not silently rewrite the
approved requirements to match its implementation.

Keep executable commands under `## Verification` and human/native-session
observations under `## Optional Verification`. Keep receipt and findings
schemas intact. Missing required executable evidence remains FAIL or
UNVERIFIED under the current contract. An unavailable optional observation
must limit the claim of completion for the affected behavior.

The existing reviewer receives the original approved scope, relevant IDs,
contracts, scoped diff, and verification evidence. Its normal passes ask:
Does every in-scope behavior have implementation and evidence? Is there
unapproved scope? Is a test expected value derived from the implementation?
Does the original bug reproduction now produce the expected behavior?

Return gaps using the ordinary finding fields and existing severity profiles;
put a requirement ID in a title/location when useful. Missing material
functionality is an ordinary correctness finding, not a new convergence
status. Style omissions alone must not be escalated into missing behavior.
The reviewer remains read/search-only. The orchestrator/coder run requested
tests or bounded negative controls and give back the evidence.

### CLOSEOUT and Learning

Use one short phase-boundary update: objective; completed scope; deviations;
verification with evidence links; open findings; any decision needed; next
operation. This is a view of existing artifacts, not a new persistent report.
Do not request approval when the next operation is already authorized.
Only an explicit user request activates the existing `paused` contract.

For a substantive observed failure, the existing log records reproduction,
cause, smallest correction, and regression evidence. LEARN routes the
durable lesson: code/test enforcement where possible, an existing skill
when reusable, or project memory for non-rederivable rationale. First check
whether the existing model/instructions already produce the desired behavior.
No automatic new rule per failure and no mandatory classification schema.

## Bounded Evaluation Pilot

### Existing machinery to reuse

Use `scripts/check_native_clients.py` for process limits, marker-owned
workspace checks, client isolation, versions, and controlled result output.
Keep `FROZEN_PLANNER_WORKLOADS`, `PLANNER_WORKLOAD_SCHEMA`, and the current
`--planner-workloads` behavior/results unchanged. Its existing candidate is
a shim-removal experiment; do not repurpose it as a general A/B workspace.

The proposed separate `--behavioral-workloads` option is a **new bootstrap
CLI option**, justified after inspecting `parse_args`, `prepare_workspace`,
`planner_workload_result`, and `build_report`. It is not a claimed vendor
flag. It runs only the new pilot workloads and version/preflight checks;
do not silently launch the older acceptance runs as well. Reject ambiguous
combinations with the old workload flag. Use existing provider command
shapes where the evidence phase confirms them. Do not introduce an SDK,
persistent-thread protocol, external judge, or plugin architecture.

### Three initial cases

Create small authored packets under `tests/fixtures/behavioral/`. Stage or
copy only the packet into the prepared model-readable workspace. Keep the
expected answers and scorer outside that workspace and omit them from the
supplied context. Read-only execution limits writes; it does not establish
that every host path is unreadable. Record the actual read boundary in the
evidence phase. An observed read of oracle/scorer material invalidates the
run; absent read events leave oracle non-access unverified. Do not claim
adversarial isolation from the working-directory layout alone. All cases
are read-only.

| Case | Packet and task | Independent expected result | Observable behavior |
| --- | --- | --- | --- |
| Ambiguous retention | A request to expire records, with no retention period or definition of eligible records; current code does not settle those choices. Ask for a plan. | Two material questions remain unresolved; no chosen period or deletion implementation is approved. A matched control supplies both answers and should need no repeated interview. | A returned question/action artifact grounded in the missing fields, no writes, no invented deletion policy. Assess the actual artifact; do not ask the agent to rate its own restraint. |
| Missing requirement coverage | Requirements for rejecting invalid input, preserving order, and retaining duplicates; a supplied plan covers only the first two and the code drops duplicates. Ask for consistency review. | The duplicate-preservation requirement lacks implementation and a regression check. A matched repaired packet must not receive the same finding. | Correct requirement ID and cited code/plan evidence; no extra component proposal. Expected gap IDs are not included in the prompt or result schema. |
| Weak regression test | A tiny function must reject a negative value; a generated test asserts only non-None output and passes with a broken implementation. Ask for test review. | The test fails to establish rejection. The corrected test fails against the planted broken variant and passes against the good variant, as the host verifies offline. | Identification of the missing behavioral assertion and an appropriate failure-case test. Reviewer execution is not required; the host owns the negative-control run. |

Use structured result fields to carry **task outputs**, such as questions,
requirement references, and issue locations. The host compares them with
independent fixture truth. Transport validity and behavioral correctness are
separate. Natural-language explanations are checked with a small human
rubric when a deterministic semantic check is inappropriate; do not compare
whole response strings or call an LLM judge a deterministic oracle.

For exposed tool events, derive only allowlisted indicators such as relevant
artifact read, attempted forbidden write, and observed check outcome. Keep
raw events in memory only and discard them after extraction. Missing event
coverage is `unobserved`, never zero calls or an inferred PASS. A correct
task answer does not prove a file was read. Preserve these as separate
result dimensions. Unknown event formats stop the relevant measurement.

### Scoring and evidence

Store fixed case IDs, fixture/scorer revision hashes, bootstrap source and
generated-bundle hashes, UTC date, provider/client/version, requested model
and effort, observed model metadata when available, permission mode,
result class, evidence class, duration, and exposed usage counts. Unavailable
metrics are null. Do not keep user paths, raw commands, prompts, transcripts,
credentials, arbitrary model strings, or environment dumps. Map an allowed
fixture path to its case-local identifier before storing it.

Distinguish three conclusions:

- Offline parser/scorer tests passed: deterministic implementation evidence.
- The agent produced a correct task output: fixture-specific behavioral result.
- A required action was observed: event-based execution evidence.

No conclusion implies the others. A missing client, timeout, unsupported
transport, or missing event signal remains a separate unavailable/unobserved
result, not a behavioral failure or a successful run. Existing deterministic
gate results remain authoritative and untouched.

### Cost, comparison, and baseline

Freeze packets and expected results in Phase A, before prompt changes.
Start with one installed, trusted provider and three repetitions of each
case: nine primary runs per revision. Run matched controls once each as
measurement checks. A second provider is optional and scored separately.
No automatic retries, provider/model switching, or escalation of effort.
Retain failures/timeouts in the denominator. Missing infrastructure is
reported separately; it is not removed from the record to improve a score.

With the runner's existing 420-second limit, nine primary attempts have a
63-minute timeout ceiling per provider/revision, plus up to 21 minutes for
three controls and setup. These are ceilings, not measured costs. Use one
explicitly bounded wave first; record actual time/usage before expanding.
Do not estimate token prices from memory or claim cost savings without data.

Compare the same provider/model/runtime/permissions and fixture/scorer
revisions before and after Phase B, using separately prepared workspaces
from recorded baseline and candidate commits. If any factor changes, label
the comparison confounded. The existing shim-control/candidate pair is not
the baseline/candidate pair for this experiment. Report per-case counts,
false positives on controls, missing evidence, time, and usage. Nine primary
runs are a diagnostic pilot, not statistical proof or a provider leaderboard.

The evidence phase first establishes the real transport for each selected
provider using existing commands and a small scratch packet. If it cannot
observe a capability, mark it unobserved and narrow the pilot. Do not write
a new provider adapter around an assumed event format. If no provider can
produce the bounded task outputs, Phase B's native extension waits; the
planner may revise only that affected future scope.

### Existing and deferred scenarios

Protected writes, incomplete receipts, and sidecar team preservation already
have real deterministic hook/verifier/Git tests. Reuse them instead of paying
for model runs to re-prove enforcement. Prompt restraint about unnecessary
infrastructure is included in the coverage case. Context recovery already
has policy and native-probe evidence classes, but robust interruption/resume
evaluation needs a persistent session; defer it. Writable agent E2E and
sidecar state-write evaluation belong to the existing native/provider work
and separate sidecar repair, not this read-only pilot.

## Risks and Alternatives

| Risk | Decision |
| --- | --- |
| Additional prose slows simple tasks | Scope new sections to material uncertainty/complexity; matched clear-task control measures over-questioning. |
| Agent can guess fixture answers without doing requested work | Keep the oracle outside its workspace, use repaired controls, and separate correct output from observed actions. Do not promise intent detection. |
| Native schema or permissions differ by provider/version | Phase A evidence first; supported observations only. No privilege changes to rescue a measurement. |
| Requirement IDs turn into a second state machine | Optional Markdown only; no new frontmatter parser, receipt fields, or auto-created tasks. |
| Reviewers mistake alternative designs for deviations | Compare user behavior and preserved contracts, not textual plan imitation; include a correct alternative fixture. |
| Large multi-file policy change is hard to review | One bounded integration phase with file ownership and focused tests; no per-recommendation phases. Required final wiki phase remains separate. |
| New workflow text conflicts with sidecar repair | Rebase on its final path/content choices. Keep this work out of installer state migration and discovery changes. |

## Devil's Advocate Result

CHANGE the initial idea of a new behavioral framework: extend the existing
runner. CHANGE mandatory traceability into optional complex-task guidance.
CHANGE convergence from an append-tasks operation to the existing read-only
review and scoped fix loop. INVESTIGATE native transport and baseline
behavior before adding provider-specific measurement. ACCEPT the limits of
a small, non-gating pilot and human judgment for semantic output. REJECT a
new agent, evaluator dependency, generalized mutation engine, or receipt gate.
