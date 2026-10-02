# Bootstrap Engineering Workflow Improvements

**Date:** 2026-10-02  
**Baseline:** `dev`, `a2c68b3`; outer and nested worktrees were clean at intake.  
**Status:** Investigation complete; recommendations and plans are drafts for review. No implementation is authorized by this document.

## Recommendation

Extend the existing planner, templates, reviewer, native probe, and session
log. Add no permanent agent, planning system, receipt type, or mandatory
model-evaluation gate. The highest-value changes are explicit acceptance
mapping, verification of the original bug symptom, and a small behavioral
evaluation whose expected results are independent of the evaluated agent.

The bootstrap already implements much of the handoff. Treating the whole
list as new functionality would duplicate existing controls. The concrete
gaps are mostly missing connections between existing artifacts, plus a
measurement limitation in the native planner calibration.

## Deliverables

- This file: research, source register, gap analysis, and decision summary.
- [Implementation design](design.md): integration, evidence contracts,
  evaluation cases, limits, and risks.
- [Draft big plan](engineering-workflow-improvements.md).
- [Phase A: evidence and baseline](2026-10-02_phase-A-engineering-evidence.md).
- [Phase B: integrated improvements](2026-10-02_phase-B-engineering-workflow.md).
- [Phase C: knowledge refresh](2026-10-02_phase-C-engineering-knowledge-refresh.md).

All deliverables stay in this exploration directory as requested. Three
phases retain the user's preference for minimal ceremony. After approval,
move the four plan files together into `.claude/plans/`, validate them, and
use the ordinary branch/phase lifecycle. Nothing here starts that lifecycle.
The separate `sidecar-workflow-repair` draft remains separate work.

## Method and Evidence Limits

Read canonical source on the actual checked-out `dev`, including role
metadata/prompts, workflow and quality policy, review profiles, required
skills, templates, verification functions/tests, native probes/tests,
sidecar installer/generator/provider evidence, recent plans/logs, MEMORY,
and relevant OpenWiki pages. Source and tests outrank generated wiki pages.
Known paths and exact searches were sufficient; guarded Context Mode was
used for targeted retrieval from the larger verifier and native probe.

Visited all twelve reference starting points. R1's short link failed, but
the matching public author post was found through his own profile. R3's
homepage exposed little text, so its archive and two original articles were
read. Paywalls were not bypassed. The article register below distinguishes
visible claims from inaccessible material. These are practitioner accounts
and design guidance, not controlled proof of productivity gains.

Executed only existing offline checks:

| Command | Result | What it establishes |
| --- | --- | --- |
| `UV_CACHE_DIR=/tmp/github-copilot-bootstrap-uv-cache uv run pytest tests/test_check_native_clients.py -q` | 40 passed, 0.22s | Existing runner/parser/privacy contracts pass with offline doubles. |
| `UV_CACHE_DIR=/tmp/github-copilot-bootstrap-uv-cache uv run pytest tests/test_verify.py -q -k 'run_verification_items or forged_counts_inconsistent or completed_receipts_are_immutable or closeout_rejects_non_passing_phase_receipt'` | 15 passed, 286 deselected, 1.50s | Selected command-execution, findings, receipt, and immutability boundaries pass. |

No fresh native model session, consumer install, complete test suite, or
behavioral benchmark was run. The earlier sidecar review's 699 tests and
native observations remain dated evidence, not results of this investigation.

At final validation, another session had activated
`sidecar-workflow-repair_implementation` and updated its plan state. This
investigation did not create that branch or alter those plans. Findings here
remain tied to the inspected `dev` baseline; recheck source changes before
promoting the draft.

## Source Register

All web sources were checked on 2026-10-02. Live documentation was not pinned
to an upstream commit. Recheck it at implementation time. Newsletter facts
below are attributed to the visible original interviews, not treated as
vendor guarantees. No article's recommendation alone justifies a change.

| Ref | Verified content and access limit | Implication for this repository |
| --- | --- | --- |
| R1 | The [matching Hoogvliets supervision post](https://www.linkedin.com/posts/hoogvliets_softwareengineering-activity-7509179500690173953-zGip) calls for readable execution, following agent work, and decision checkpoints. The supplied short URL was inaccessible; matching content was reached through the author's public profile. Its displayed age is relative, so no exact publication date is asserted. | Improve concise boundary reporting. Repeated approval of routine work does not follow from this evidence. |
| R2 | [Hoogvliets on explicit contracts](https://www.linkedin.com/posts/hoogvliets_coding-programming-sofwareengineering-activity-7457011290801209344-IQ0n) names system, data, UI, and API contracts as constraints that make agent output checkable. This is an author's experience-based argument, not a comparative benchmark. | Reference existing contracts before creating new schemas. |
| R3 | The [ML platform ghost ship](https://mettlesome.substack.com/p/issue-1-the-ml-platform-ghost-ship), May 30, 2024, describes a platform blocked by organizational integration restrictions. [Pre-commit heaven](https://mettlesome.substack.com/p/welcome-to-pre-commit-heaven), February 7, 2024, discusses automated safeguards and code checks. Both are publicly readable. | Investigate access/operational constraints as well as code feasibility. Existing deterministic guardrails already cover the general automation recommendation. Neither article specifies the proposed failure taxonomy. |
| R4 | [How to Do Spec-Driven Development](https://newsletter.eng-leadership.com/p/how-to-do-spec-driven-development), July 27, 2026, visibly attributes risk-first spikes and annotated reference implementations to Larridin CTO Ameya Kanitkar. The public spec outline includes non-goals, assumptions, architecture, and testing. The heading places test planning before implementation planning; that section's details are paywalled. | Reuse the spike skill. Retain a reference only with explicit shortcuts and limits. Do not attribute inaccessible test-plan mechanics to the interview. |
| R5 | [Michael Bolin interview](https://newsletter.eng-leadership.com/p/how-openai-codex-tech-lead-does-ai), June 4, 2026, publicly describes team-reviewed requirements, reviewable PR sizes, and related-PR discussions as context. Later review/integration-test sections are paywalled. | Existing bounded evidence packets and phase-sized work already fit. The article's preference for early PR creation and CI-first testing must not override this repository's PR authorization or verification rules. |
| R6 | [How to Do AI-Assisted Engineering](https://newsletter.eng-leadership.com/p/how-to-do-ai-assisted-engineering), March 22, 2026: visible section 7 attributes separation of generation and verification, negative cases, early contracts, and regression learning to **Lucian Lature, Solutions Architect at Wiley**. | Keep coder and reviewer independent. Extend the existing test checklist; do not credit these practices to every contributor or to OpenAI/Anthropic collectively. |
| R7 | [Codex team interview](https://newsletter.eng-leadership.com/p/how-openais-codex-team-works-and), February 22, 2026, publicly describes ownership and lean coordination based on a conversation with Thibault Sottiaux. Detailed AI-use material begins at the paywall. | Broad ownership advice is supported; specific repository-skill practices in that inaccessible section are unverified. No additional change is justified by it. |
| R8 | [Katelyn Lesse interview](https://newsletter.eng-leadership.com/p/how-anthropic-builds-ai-native-engineering), July 1, 2026, publicly discusses explicit outcomes, careful automated testing, evaluation, and engineering ownership of design. Later material is paywalled. | Supports measuring outcomes; does not establish that adding another agent or copying Anthropic's product workflow would help this bootstrap. |
| R9 | [Player-coach article](https://newsletter.eng-leadership.com/p/the-player-coach-role-is-becoming), August 31, 2026, exposes its title/subtitle and paywall, not the substantive article. | Detailed claims about review capacity and implementation-first behavior are unverified. Do not use them as design evidence. |
| R10 | [Official Spec Kit repository](https://github.com/github/spec-kit) documents feature and separate opt-in bug workflows. The [bug guide](https://github.github.io/spec-kit/guides/bugfix.html) explicitly returns to the original reproduction; missing verification is not success. | Add symptom-resolution evidence to existing debugging/closeout guidance. Do not install `.specify/` or its bug extension. |
| R11 | [Agentic SDD reference](https://github.github.io/spec-kit/reference/agentic-sdd.html) distinguishes specification, clarification, planning, tasks, and read-only consistency analysis. Its convergence step is **not entirely read-only**: it may append tasks. | Borrow consistency checks, but keep our reviewer read-only and route scope changes through the existing orchestrator. The convergence loop is not a termination guarantee. |
| R12 | [Google harness-evaluation article](https://developers.googleblog.com/the-anatomy-of-harness-engineering-how-to-evaluate-iterate-and-guard-ai-coding-agents/), September 9, 2026, by Taylor Mullen and Christian Gunderman, advocates intermediate observable actions, small failure-focused cases, and aggregate evaluation rather than gating PRs on single noisy runs. | Start with three cases and independent expected results. A deterministic assertion over a stochastic model run does not make the complete evaluation deterministic. Do not adopt its SDK or prompt-optimization loop by default. |

## Existing Components and Concrete Gaps

The final three columns are recommendations, not claims made by the sources.

| Candidate | What exists on `dev` | Concrete gap | Smallest change | Risk and acceptance evidence |
| --- | --- | --- | --- | --- |
| A. Risk-first investigation | [Planner](../../../shared/agents/planner/prompt.md) requires bounded discovery and an external-integration evidence gate. [Integration spike skill](../../../shared/skills/integration-gate-spike/SKILL.md) already defines focused probes. [Plan decomposition](../../../shared/skills/plan-decomposition/SKILL.md) flags unverified assumptions. | General architecture-invalidating assumptions are not an explicit pre-decomposition decision: local performance, data availability, permissions, or organizational constraints can escape an external-API-only reading. | Add a short risk/evidence decision to planner discovery. Reuse the skill for external contracts; allow a bounded exploration for other decisive unknowns. | Avoid mandatory spikes. A known-contract task needs none; an unsupported decisive assumption is investigated or explicitly left blocked, never silently implemented. |
| B. Specification and traceability | [Requirements template](../../../shared/templates/requirements-spec.md) has objective, MUST/SHOULD/MAY, clarity, success criteria, and approval. [Workflow](../../../shared/policies/workflow.instructions.md) permits optional specs under quality reports. | No reusable behavior→phase→implementation→evidence table; non-goals and evidence methods are not explicit fields in the spec. | Extend this template and add an optional reference/table in existing plans. Use stable IDs only when they help complex work. | Do not require another spec for clear work or rewrite historical plans. Test generation with old and new Markdown bodies; review planted coverage gaps. |
| C. Implementation contracts | [Domain](../../../shared/review-profiles/domain.md), [architecture](../../../shared/review-profiles/architecture.md), API/config profiles, and planning steps already address invariants and boundaries. | The planner does not consistently enumerate the relevant existing source contracts before choosing steps. | Add a compact contract map: source/symbol, preserved behavior, planned change, evidence. | No mandatory Pydantic/schema layer. A schema-free consumer can cite functions and tests; existing signatures/error behavior remain authoritative. |
| D. Test strategy first | [Quality policy](../../../shared/policies/quality-and-testing.instructions.md), test guidance, and executable plan verification already exist. | Command lists do not show why those checks cover the original outcome. The planner sequence does not explicitly settle success evidence before phase decomposition. | Determine critical cases, levels, mocking boundaries, regression scope, and untestable criteria before the phase list. Keep commands in the existing Verification section. | Do not mix manual probes into executable blocks or add another verifier. A deliberate acceptance gap must remain visible despite a green unit suite. |
| E. Consistency and convergence | Plan decomposition checks cross-phase names/dependencies. [Reviewer](../../../shared/agents/reviewer/prompt.md) refutes findings; [verify.py](../../../shared/scripts/verify.py) binds receipts and findings. | Reviewer inputs require diff/profiles/gate but not the approved requirements or their evidence mapping. A coherent implementation of the wrong behavior can pass existing structural checks. | Add approved-scope evidence to handoffs and a requirements comparison within the same review. Return gaps as ordinary findings. | The verifier already states that it cannot certify reviewer honesty. No new JSON schema, numerical convergence score, or gate. Test a missing requirement, an invented feature, and a correct alternative implementation. |
| F. Independent tests and original symptom | [Tests profile](../../../shared/review-profiles/tests.md) already requires meaningful assertions, failure cases, and real dependency evidence; a fresh reviewer is independent from the coder. [Debug skill](../../../shared/skills/debug-investigator/SKILL.md) captures symptoms and reproduces before fixing. | Independence of expected values is implicit; the debug resolution section does not explicitly rerun and record the original symptom after the fix. | Strengthen those two instructions; let coder/orchestrator execute targeted negative controls when warranted. | Reviewer has read/search only: it must not run tests or mutation tools itself. A no-op fix and an implementation-derived expected value must be caught. Mutation tooling remains optional and deferred. |
| G. Behavioral evaluation | [Native runner](../../../scripts/check_native_clients.py) has isolated workspaces, two frozen planner workloads, versions, timings, output validation, and [40 offline tests](../../../tests/test_check_native_clients.py). Hook, verifier, and sidecar suites already cover deterministic failure cases. | Planner quality fields are self-reported. It supplies the exact artifact allowlist and requests booleans; tool/file metrics are null. `run_planner_workloads` uses only the control consumer; the existing candidate removes a Codex shim, not an arbitrary prompt revision. | Extend this runner through a separate opt-in workload mode, with three fixtures, hidden independent expected results, typed evidence, and explicit revision identity. Keep legacy workloads unchanged. | Do not relabel existing PASS as proof of behavior. Validate scoring offline, then obtain a bounded native baseline. Missing events mean unobserved, not success. |
| H. Readable checkpoints | [Reporting policy](../../../shared/policies/agent-reporting.instructions.md), [session log](../../../shared/templates/session-log.md), orchestrator task tracking, and explicit pause/resume already exist. | Relevant facts are spread across work log, next steps, and receipts; no short phase-boundary summary shape is specified. | One concise summary in existing reporting/log surfaces, linking the evidence already produced. | No dashboard, extra report, or routine permission prompt. Failed checks remain failures, not unauthorized `paused` transitions. |
| I. Failure learning | [Learn skill](../../../shared/skills/learn/SKILL.md), MEMORY ownership rules, debugging, and required regression tests already exist. | The route from a failed outcome to reproduction, smallest correction, and independent regression is not explicit in LEARN's decision step. | Add a short failure-origin routing question to that step. Prefer a test, code fix, or existing-skill correction before a new instruction. | No new taxonomy schema or memory store. Record no redundant lesson for source-derived facts or behavior already produced without added guidance. |

### The Native Calibration Limit

`planner_workload_prompt()` explicitly tells the model the required artifact
list and asks it to emit only self-audit JSON, with no plan field.
`planner_workload_result()` checks those returned booleans/lists.
The offline `test_workload_metrics_are_aggregate_and_keep_unobservable_fields_none`
constructs a successful response with no observed read/tool evidence and
expects PASS. This is valid testing of the existing contract, but it cannot
establish execution fidelity or planning quality.

Keep the [August calibration record](../../../docs/2026-08-09-planner-reliability-calibration.md)
unchanged. Its results are observations under that contract. Clarify future
claims and add independent evidence rather than retroactively failing old
runs. The quality policy likewise explicitly accepts that deterministic
gates validate findings metadata, not the truth of the model's judgment.

## Full Install, Sidecar, and Provider Boundaries

Full installs receive richer optional planning/review guidance through the
existing generator. No mandatory frontmatter fields, receipt schema changes,
new lifecycle status, or retroactive completed-plan requirement is proposed.
Skills-only sidecars stay skills-only. Workflow sidecars receive only concise
advisory guidance in their existing rules, role prompts, templates, and
review profiles. They do not gain a required spec file, verification runner,
findings JSON, or commit gate.

The [sidecar provider contract](../../../docs/sidecar-provider-contract.md)
records Claude agent/rule discovery, a negative config-free Codex-agent
observation on 0.147.0, and narrower Copilot coverage. The hands-on review
separately found protected-state writes. These are different capabilities.
This proposal does not fix the state location or legacy full detection;
rebase its sidecar content edits on the separate repair when it lands.

Current [Claude subagent documentation](https://code.claude.com/docs/en/sub-agents)
describes `.claude/agents/`; [GitHub instructions documentation](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions)
describes instruction surfaces with product-specific support. Neither
establishes identical discovery or write permissions across clients.
[Current OpenAI subagent documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents)
now includes `.codex/agents/*.toml` examples. That is a reason to revalidate
the older negative observation, not permission to change the shipped support
matrix without a native run. Antigravity's article/SDK example also does not
prove this repository's adapter behavior. Provider expansion is deferred.

## Decision Summary

| Decision | Classification | Value and added complexity |
| --- | --- | --- |
| General risk/evidence decision before decomposition | Implement now | One short planner step; reuse existing spike/exploration paths. |
| Optional spec, requirement mapping, contracts, test strategy | Implement now | Extend existing Markdown; no parser or mandatory second document. |
| Requirements comparison in reviewer handoff and findings | Implement now | Adds approved-scope evidence to existing review; no permanent role. |
| Independent expectations and original-symptom verification | Implement now | A few checklist/debugging edits; optional negative controls run by existing execution roles. |
| Three-case behavioral pilot and independent evaluation | Implement now, after the evidence phase | Extend one existing runner and test module; modest fixture/report maintenance and explicitly bounded native cost. |
| Concise boundary summary and failure-to-regression routing | Implement now | Extend existing log/reporting/LEARN guidance, not another report stream. |
| Independent reviewer, deterministic receipts, protected operations, team precedence, provenance | Already covered | Preserve and regression-test them; duplicating them adds no value. |
| General mutation-testing dependency, broad model/provider leaderboard, writable agent E2E suite, automatic prompt tuning | Implement later only with evidence of need | Runtime/version/cost complexity is not justified by the current three gaps. |
| Codex discovery revalidation and sidecar repair | Separate work | Relevant dependency/risk; do not silently add it to this scope. |
| Spec Kit install, new verifier/planner/reviewer, new memory store, compulsory spec for every task, LLM convergence receipt | Reject | Duplicates authority or adds ceremony without a demonstrated gap. |
| Automatic commits, PRs, merges, force pushes, pause-on-failure, approvals for routine steps | Reject | Conflicts with existing authorization and lifecycle boundaries. |

“Implement now” means recommended in the draft, not approved. The next
decision is whether to authorize this three-phase proposal after the
separate sidecar repair ordering is settled. Native baseline outcomes and
event observability remain unmeasured; the first phase resolves them before
any production evaluator change. No behavioral improvement is claimed yet.
