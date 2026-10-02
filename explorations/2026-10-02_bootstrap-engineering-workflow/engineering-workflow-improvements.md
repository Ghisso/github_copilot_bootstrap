---
name: engineering-workflow-improvements
type: big-plan
status: planning
originating_branch: dev
implementation_branch: engineering-workflow-improvements_implementation
started_at:
phases:
  - 2026-10-02_phase-A-engineering-evidence
  - 2026-10-02_phase-B-engineering-evaluator
  - 2026-10-02_phase-C-engineering-workflow
  - 2026-10-02_phase-D-engineering-knowledge-refresh
current_phase:
---

# Big Plan: Engineering Workflow Improvements

## Context

Investigation against `dev` at `a2c68b3` found substantial existing coverage
for the handoff's proposals. The remaining gaps concern connecting approved
outcomes to evidence, verifying original symptoms, and distinguishing native
task performance from self-reported checklist compliance. The investigation
and source register are at
`.claude/explorations/2026-10-02_bootstrap-engineering-workflow/README.md`;
the implementation design is its sibling `design.md`.

These are draft exploration artifacts. After user approval, promote this
file and its four small plans together to `.claude/plans/`. Keep the
investigation/design at their original paths. Do not activate a phase,
create an implementation branch, or approve the proposal while drafting.

## Goals

- Resolve decisive uncertainty before detailed phase decomposition.
- Reuse existing specs/plans to connect requirements, contracts, and evidence.
- Review the original outcome and meaningful tests, not only a coherent diff.
- Measure a small set of behaviors independently of agent self-assessment.
- Improve phase summaries and failure learning without another report stream.
- Preserve provider differences, relaxed sidecars, and deterministic authority.

## Non-Goals

No new permanent role, lifecycle status, requirement parser, receipt schema,
Spec Kit dependency, memory store, model judge, dashboard, automatic prompt
tuner, mandatory mutation package, or provider discovery expansion. No new
approval for already-authorized routine steps. No installer/state-location
repair, automatic PR, merge, force push, or historical evidence rewrite.

## Design Overview

Follow the design document's single-lifecycle integration. Risk, acceptance,
contract, and test-strategy work lives inside existing planner discovery.
One optional table in the spec/big plan maps stable requirement IDs to
phases, symbols, and evidence. Reviewer handoffs carry the approved plan/spec
and approved scope changes, with version references. These are the authority
for required behavior, not the reviewer's reconstructed interpretation.
Separate specs and IDs stay optional for simple tasks. Coverage/contract
defects use ordinary findings and severity rules.

The original bug reproduction is re-exercised by the coder/orchestrator
when feasible. An unavailable environment limits the claim of resolution.
The reviewer evaluates supplied evidence and retains read/search-only tools.
Manual probes never enter executable Verification blocks.

Extend `check_native_clients.py` only after a native evidence phase. Preserve
its legacy workload schema and shim experiment. A new, separate opt-in
behavioral mode runs the design's three read-only packets with independent
expected results and separately classified action evidence. Ordinary
deterministic tests and commit receipts never invoke a model. Phase B validates
and freezes the evaluator using Phase A's preserved outputs before Phase C
changes workflow guidance. Score saved baseline and candidate outputs with
the same final scorer; retain original evidence and version each rescore.

## Requirements and Acceptance

| ID | Required behavior | Phase | Acceptance and evidence |
| --- | --- | --- | --- |
| REQ-001 | Investigate decisive assumptions before decomposition; no production edits from a spike | C | Unknown-contract packet prompts a bounded evidence step; clear-contract control does not demand a spike or repeated approval. |
| REQ-002 | Optional complex-task specification and stable requirement mapping | C | Template supports non-goals, constraints, acceptance/evidence, and phase mapping; existing plans still validate unchanged. |
| REQ-003 | Cite existing contracts and settle critical test strategy before implementation steps | C | A schema-free example cites source invariants and negative cases without inventing a schema; integration/mocking choices have reasons. |
| REQ-004 | Review against the approved plan/spec and approved scope changes within the existing findings model | C | Seeded duplicate-preservation gap is found; repaired, valid-alternative, and approved-change controls avoid invented requirements; current JSON/receipts are unchanged. |
| REQ-005 | Review independent expected values and recheck the original symptom | C | Weak-test fixture is identified; host negative control distinguishes good/broken variants; unreproduced symptom is not called resolved. |
| REQ-006 | Bounded independent behavioral evaluation and comparable before/after evidence | A, B, C | Preserved outputs replay through the same final scorer; frozen scenario/oracle/scorer revisions and complete run identity; three repetitions per primary case; missing observations, invalid outputs, unavailable runs, and behavioral failures reported separately; confounding explicit; no automatic model gate. |
| REQ-007 | Concise phase-boundary summary from existing artifacts | C | Objective, completed scope, deviations, checks, findings, needed decision, and next operation are visible without another persistent report or routine approval. |
| REQ-008 | Route observed failures to smallest correction and regression | C | LEARN example prefers an existing test/skill and adds no duplicate rule or source-derived memory entry. |
| REQ-009 | Preserve lifecycle, permissions, provider boundaries, historical evidence, and relaxed sidecars | A–D | Existing verifier/hook/plan tests pass; full/skills/workflow generation validates; no new sidecar gates, discovery claims, or receipt schema. |

No acceptance row may be silently dropped or rewritten to match an
implementation. Record approved material scope changes through the current
policy and supply them with the original approved artifacts to the reviewer.
Before Phase B starts, incorporate Phase A's actual native limitations into
affected steps only. Freeze scenario/oracle revisions in A and the validated
scorer in B. Record provider, model, reasoning effort, permission mode,
client/runtime version, source revision, and generated-bundle identity for
each attempt. Hold comparison settings fixed apart from the intended workflow
change; report unknown or changed controls as confounded comparisons.

## Phases

- [ ] `2026-10-02_phase-A-engineering-evidence` — freeze the three cases and establish native transport/baseline evidence.
- [ ] `2026-10-02_phase-B-engineering-evaluator` — implement, validate, and freeze the evaluator using Phase A's saved evidence.
- [ ] `2026-10-02_phase-C-engineering-workflow` — integrate planner, review, reporting, learning, and sidecar guidance; run matched candidate evaluation.
- [ ] `2026-10-02_phase-D-engineering-knowledge-refresh` — refresh derived knowledge and audit all live advice.

## Ownership and Required Skills

Main-thread orchestrator owns activation, bounded native runs, deterministic
verification, findings, final state, closeout, commits, and normal pushes.
The Phase B coder owns the native runner/tests. Phase C prompt/template work
starts only after evaluator validation and freezing; do not develop the
measurement and measured workflow changes concurrently. Reviewer remains
independent and cannot execute tests.
Documenter updates live docs after review converges.

All coding uses `shared/skills/ponytail/SKILL.md` in full mode plus
`shared/skills/code-style/SKILL.md` and
`shared/skills/testing-patterns/SKILL.md`. Native probes use
`shared/skills/integration-gate-spike/SKILL.md`. Documentation uses
`shared/skills/documentation/SKILL.md` and
`shared/skills/humanize/SKILL.md`. Small plans name further skills per step.

Every phase uses the control-plane review profiles at
`.claude/review-profiles/code.md`, `architecture.md`, `security.md`,
`tests.md`, `ponytail.md`, and `documentation.md` in that directory.
No reviewer or evaluation output replaces authoritative receipts.

## Risks and Dependencies

- Phase A needs a trusted native host and an explicitly bounded invocation
  budget. If no provider supports the proposed observations, record the
  limitation and revise affected future work; do not invent transport data.
- `.claude` write failures and old-full detection remain owned by
  `sidecar-workflow-repair`. Prefer its completion before sidecar text edits;
  otherwise reconcile the two plans without copying a retired state path.
- Requirement guidance can become excessive. Clear-task controls and the
  no-new-parser rule bound its cost. IDs and separate specs stay optional.
- Evaluation can reward guessing. Independent hidden oracles, repaired
  controls, and separate observed-action fields bound claims, not intent.
- A single provider's three-run pilot cannot establish universal model
  quality. Never publish it as a cross-provider leaderboard.
- Native authentication and OpenWiki availability are operational
  prerequisites, not reasons to weaken permissions or skip required work.

## Verification Strategy

Keep the existing executable `## Verification`, findings/severity model,
and immutable receipt validation. Focused unit tests cover the new scorer,
missing events, privacy, fixture truth, and output compatibility. Existing
plan/verifier/hook/sidecar tests cover preserved boundaries. Native outcomes
remain separately recorded, repeated, and advisory as model measurements.

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
```

The ordinary phase receipt supplies full tests, lint, and typing. Do not
put an authenticated or probabilistic run into `verify.py` or its receipt.
Small plans retain their concrete focused checks and host-evidence items.

## Completion Evidence

All nine requirements map to final source and evidence in the Phase C log,
including Phase B's evaluator validation. Preserve baseline and candidate
task outputs and allowlisted observations, not just scores, in companion
evidence artifacts. The dated evaluation document identifies the common
final scorer, frozen scenario/oracle revisions, complete run identity,
separate invalid/unavailable/unobserved counts, and any confounding factors.
Describe honestly whether measurements improved, regressed, or were
inconclusive; a valid pilot need not manufacture an improvement claim.

Follow the canonical closeout sequence, one completion commit per phase and
one normal push attempt. PR creation and merging remain user decisions.
The final phase refreshes OpenWiki through its own MCP lifecycle and records
the full documentation/MEMORY/LEARN audit under the exact heading
`## Stale-claims surfaces checked`. Preserve completed logs, receipts, and
older calibration evidence. The plan is complete only after that final phase.
