---
name: 2026-10-02_phase-B-engineering-planning-guidance
type: small-plan
parent_plan: engineering-workflow-improvements
phase_index: 2
status: planned
closeout_session_log:
---

# Small Plan: Planning, Reporting, and Learning Guidance

## Scope

Make outcome, risk, contract, and test reasoning explicit in planning, and
improve phase summaries and failure learning. Build on Phase A's
requirement-authority and original-symptom guidance; point to it rather than
restating it. This phase covers REQ-001–003, REQ-007, REQ-008, and the
remaining part of REQ-009. Before starting, check Phase A's outcome and
findings, and revise this phase only where they materially affect it.
REQ-006 is deferred to the separate optional pilot. Preserve `.ai-bootstrap/`,
caller-saved specialist output, independent review, and all existing gates.
No runner changes, executable benchmark fixtures, or model runs are included.

## Steps

- [ ] **1. Make outcome, risk, contract, and test reasoning explicit in planning.**
  **Owner:** coder, including the worked example.
  **Files:** modify `shared/agents/planner/prompt.md`,
  `shared/skills/plan-decomposition/SKILL.md`,
  `shared/templates/requirements-spec.md`, `shared/templates/plan-big.md`,
  `shared/templates/plan-small.md`, and the planning portion of
  `shared/policies/workflow.instructions.md` only where a canonical pointer
  or scope rule is needed. Use `shared/skills/integration-gate-spike/SKILL.md`
  without duplicating its contract.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/plan-decomposition/SKILL.md`,
  `shared/skills/documentation/SKILL.md`.
  Add the design's compact risk/evidence decision, optional non-goals and
  requirement map, source-contract references, and test strategy before
  phase decomposition. Keep approved evidence-packet reuse and conditional
  clarification. A separate spec is optional; equivalent approved content
  in the plan suffices. Treat IDs as prose references, not new frontmatter
  fields or a second plan parser. Point to Phase A's requirement-authority
  rule instead of restating it.
  Retained experiment code must identify proven behavior and shortcuts.
  Explicitly prohibit treating a spike as authorization for production
  implementation.
  **Acceptance:** legacy/micro plans still validate; a simple known task
  needs no new artifact or approval; decisive uncertainty remains explicit;
  manual observations never enter executable command lists. A small reviewed
  example distinguishes a technical assumption needing evidence from a user
  preference needing clarification; it requires no executable fixture.

- [ ] **2. Improve checkpoints and failure learning without duplicate records.**
  **Owner:** coder.
  **Files:** modify `shared/policies/agent-reporting.instructions.md`,
  `shared/templates/session-log.md`, and `shared/skills/learn/SKILL.md`;
  use pointers in the orchestrator rather than duplicating reporting policy.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/learn/SKILL.md`, `shared/skills/humanize/SKILL.md`.
  Define the design's short boundary summary using links to current plans,
  findings, and receipts. Keep it within existing commentary and log
  surfaces. Extend LEARN's evaluation step to connect an observed failure
  to reproduction, cause, smallest correction, and regression. Prefer an
  existing test or skill; source-derived facts do not become memory entries.
  **Acceptance:** summaries name an unresolved decision only when real;
  no new approval loop, pause status transition, report stream, or lesson
  quota. Include one worked example where no new instruction is justified.

- [ ] **3. Adapt planning, reporting, and learning guidance to relaxed sidecars.**
  **Owner:** coder.
  **Files:** modify the planning and reporting parts of
  `shared/agents/planner/workflow-prompt.md`,
  `shared/agents/orchestrator/workflow-prompt.md`,
  `shared/agents/documenter/workflow-prompt.md`,
  `shared/sidecar/workflow/rules/workflow.md`,
  `shared/sidecar/workflow/instructions.md`, and the existing
  `shared/sidecar/workflow/templates/plan-big.md`, `plan-small.md`, and
  `session-log.md` as needed. Change generator or validator logic only for
  a demonstrated rendering/contract gap.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/testing-patterns/SKILL.md`.
  Use concise advisory equivalents in existing templates; no additional
  requirements-spec unit or skill is needed. Respect team ownership and
  absent specialists. Copilot instructions must work without shipped Copilot
  agents; Codex/Antigravity get no new discovery claim. Preserve the
  skills-profile unit set. Keep state under `.ai-bootstrap/`; the planner
  returns text, and its caller saves it in `plans/` beneath that root.
  Retain the merged repair's caller behavior, fallbacks, and team precedence.
  **Acceptance:** generated full guidance contains the intended optional
  extensions; workflow sidecar has no new hooks, settings, mandatory receipts,
  forced plan lifecycle, or references to unshipped files. Existing team
  collision/status/index assertions still pass.

- [ ] **4. Check instruction contracts, review, document, and close out.**
  **Owner:** coder for tests; orchestrator for execution; independent reviewer;
  documenter after review convergence.
  **Files:** modify `tests/test_validate_targets.py`, and only as needed
  `tests/test_sidecar_workflow_scenario.py`, `README.md`, and
  `docs/architecture.md`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`,
  `shared/skills/code-review/SKILL.md`,
  `shared/skills/documentation/SKILL.md`.
  Add small deterministic checks that required key terms appear in the named
  sections: the planner names the risk/evidence decision before phase
  decomposition; the templates offer optional non-goals and a requirement
  map; separate specs and IDs stay optional; and LEARN's evaluation step
  routes an observed failure to a regression. Cover shared source and
  generated full and sidecar output, including changed skills where shipped.
  Do not snapshot whole files, require one exact sentence, or add a semantic
  evaluator.
  Run the required checks. Refresh the authoring overlay with
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
  after generation if changed shared files make runtime checks stale.
  **Acceptance:** focused checks and independent review pass. The log maps
  all eight in-scope requirements (Phase A's and this phase's) to source and
  evidence, records REQ-006 as deferred, and records before/after source
  revisions for traceability. Report instruction consistency, not measured
  agent improvement. Persist findings and receipts only through existing
  closeout.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run pytest tests/test_validate_plan_frontmatter.py tests/test_verify.py tests/test_hook_gates.py -q
uv run pytest tests/test_validate_targets.py tests/test_sidecar_workflow_scenario.py -q
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Inspect generated full and workflow planning guidance for coherent
  requirement maps, technical-risk examples, and caller-saved sidecar plans.
  This is a prose review, not evidence of agent behavior. No native
  evaluation is required.

## Review Profiles

Use `.claude/review-profiles/code.md`,
`.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`. Review optional specs/IDs,
the risk-versus-clarification distinction, unchanged receipts, and sidecar
state/authority boundaries explicitly.

## Closeout Checklist

Follow the fixed CLOSEOUT order in `shared/policies/workflow.instructions.md`.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
