---
name: engineering-workflow-improvements
type: big-plan
status: complete
originating_branch: dev
implementation_branch: engineering-workflow-improvements_implementation
started_at: 2026-10-02T12:32:48Z
phases:
  - 2026-10-02_phase-A-engineering-review-guidance
  - 2026-10-02_phase-B-engineering-planning-guidance
  - 2026-10-02_phase-C-engineering-knowledge-refresh
current_phase: 
---

# Big Plan: Engineering Workflow Guidance Improvements

## Context

The initial investigation inspected `dev` at `a2c68b3`. This revision uses
`dev` at `1626364`, after sidecar repair PR #43 merged. The repair is complete:
sidecar state lives under `.ai-bootstrap/`, and callers save returned planner
and reviewer text. Preserve those contracts.

The orchestrator already requires plan requirements and non-goals for every
delegation. The narrower gap is that the reviewer's own inputs and review
steps do not explicitly require comparison against the approved plan/spec
and approved scope changes. The investigation and design remain in
`.claude/explorations/2026-10-02_bootstrap-engineering-workflow/`.

This plan has three phases. Phase A delivers the highest-value change, the
review alignment and original-symptom check, so it is reviewed on its own.
Phase B adds the planning, reporting, and learning guidance. Phase C is the
required knowledge refresh. The user approved implementation on 2026-10-02,
and this big plan and its three small plans were moved together to
`.claude/plans/`. The separate `behavioral-evaluation-pilot.md` in the
exploration directory is an optional later proposal, not a dependency.

## Goals

- Investigate decisive technical assumptions before detailed planning.
- Keep specifications and requirement IDs optional; cite existing contracts.
- Make reviewer inputs, caller instructions, and review behavior agree.
- Require evidence that a fix addresses the original symptom.
- Improve phase summaries and failure learning within existing records.
- Preserve deterministic verification, independent review, and relaxed sidecars.

## Non-Goals

No behavioral runner changes, model runs, executable benchmark fixtures,
scorer, new provider support, model judge, or behavior-improvement claim.
No new agent, requirement parser, receipt schema, dependency, memory store,
mandatory spec, or routine approval. Do not reopen the merged sidecar repair,
change installer/state semantics, or rewrite historical evidence.

## Design Overview

Extend existing planner, template, review, debugging, reporting, and learning
guidance. Carry the approved plan/spec and approved scope changes in existing
handoffs and explicitly compare the implementation against them. The reviewer
must not substitute its own reconstruction of requirements. Equivalent
approved task instructions suffice for simple work without a separate spec.

Keep tests focused on instruction presence, consistency, generated output,
and preserved authority boundaries. They establish what guidance is shipped,
not whether a model follows it. The optional pilot must first demonstrate
that its cases can detect the intended defects before any version comparison.

## Requirements and Acceptance

IDs retain their original meanings. REQ-006 is explicitly deferred rather
than silently dropped, renumbered, or claimed complete.

| ID | Required behavior or guidance | Phase | Acceptance and evidence |
| --- | --- | --- | --- |
| REQ-001 | Investigate decisive assumptions before decomposition; a spike does not authorize production changes | B | Planner guidance names the decision, bounded evidence, and remaining limits. A reviewed technical-uncertainty example differs from a clarification question; known facts require no extra spike. |
| REQ-002 | Optional complex-task specification and requirement mapping | B | Templates support non-goals, constraints, acceptance/evidence, and phase mapping; old plans validate; simple tasks require no separate spec or IDs. |
| REQ-003 | Cite existing contracts and settle critical test strategy before steps | B | Source references, negative cases, and integration/mocking choices are supported without inventing a new schema layer. |
| REQ-004 | Review against approved requirements and approved scope changes | A | Orchestrator general/reviewer handoffs and reviewer inputs/steps agree; focused checks cover the shipped guidance. Missing behavior uses existing findings; no reconstructed requirements. |
| REQ-005 | Independent test expectations and original-symptom verification | A | Debug resolution and coder guidance require rerunning the original reproduction when feasible and recording outcome or limitation; reviewer assesses evidence without execute tools. |
| REQ-006 | Bounded independent behavioral evaluation | Deferred | Owned by the separate optional pilot proposal; no native baseline, scorer, or behavior measurement is required for this plan. |
| REQ-007 | Concise phase-boundary summary | B | Existing commentary/log guidance covers objective, changes, deviations, checks, findings, real decisions, and next operation without new records or approvals. |
| REQ-008 | Route observed failures to smallest correction and regression | B | LEARN guidance prefers an existing test/skill and permits no new instruction where none is justified. |
| REQ-009 | Preserve lifecycle, permissions, provider boundaries, history, and relaxed sidecars | A–C | Relevant generation/plan/verifier/hook/sidecar checks pass; caller-saved outputs and `.ai-bootstrap/` remain intact; no new sidecar gates. |

Material scope changes use the existing approval policy. The supplied
approved artifacts and changes remain the review authority. The completion
log must distinguish the eight in-scope requirements from deferred REQ-006.

## Phases

- [x] `2026-10-02_phase-A-engineering-review-guidance` — align requirement authority in handoffs and review, add the original-symptom check, adapt sidecars, and add focused checks.
- [x] `2026-10-02_phase-B-engineering-planning-guidance` — add planning, reporting, and learning guidance, adapt sidecars, and add focused checks.
- [x] `2026-10-02_phase-C-engineering-knowledge-refresh` — refresh derived knowledge and audit live advice.

## Ownership and Required Skills

The main-thread orchestrator owns activation, execution evidence, findings,
closeout, commits, and normal pushes. A coder owns guidance and focused test
changes. The independent reviewer remains read/search-only. The documenter
updates live docs after review converges.

Use `shared/skills/ponytail/SKILL.md` (full) for implementation,
`shared/skills/code-style/SKILL.md` and
`shared/skills/testing-patterns/SKILL.md` for Python checks, and
`shared/skills/documentation/SKILL.md` for documentation. Small plans name
further skills. Each phase uses code, architecture, security, tests, ponytail,
and documentation profiles from `.claude/review-profiles/`.

## Risks and Dependencies

- Wording checks can pass while model behavior remains unchanged. Report only
  instruction/generation evidence; behavioral improvement is unmeasured.
- Do not duplicate the existing general delegation rule. Align its requirement
  authority with the reviewer-specific handoff and recipient instructions.
- Additional guidance can burden simple tasks. Keep separate specs, IDs,
  investigations, and extra approvals conditional on actual need.
- Reuse the merged sidecar repair. Do not restore old state paths or make
  read-only specialists save their own output.
- OpenWiki availability is required for the final refresh; report an actual
  service failure without weakening the existing verification contract.

## Verification Strategy

Add small checks to existing `tests/test_validate_targets.py` that required
key terms appear in the named sections of shared source and generated output.
For example, the reviewer's Inputs list names approved scope changes. Cover
approved scope changes, reviewer comparison, original-symptom rerun, optional
specs/IDs, and preserved sidecar boundaries. Avoid complete prose snapshots
and exact sentence matching; do not build a semantic checker. Use existing scenario tests for caller persistence and
team-owned files; do not build a model benchmark to test text changes.

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
```

Small plans list focused tests. Existing phase and closeout receipts remain
authoritative; ordinary deterministic verification never invokes a model.

## Completion Evidence

The Phase A log maps REQ-004 and REQ-005. The Phase B log maps all eight
in-scope requirements to source and verification evidence and records
REQ-006 as deferred. Record exact before/after source
revisions for traceability; collecting a native baseline is not a prerequisite.
Completion means the agreed guidance shipped and its checks passed, not that
agent behavior measurably improved.

Follow canonical closeout, one completion commit per phase and a normal push
attempt; PR creation/merging retain their authorization rules. Phase C uses
OpenWiki's own MCP lifecycle and records the documentation/MEMORY/LEARN audit
under `## Stale-claims surfaces checked`. Preserve completed records. The
plan is complete only after this final phase.
