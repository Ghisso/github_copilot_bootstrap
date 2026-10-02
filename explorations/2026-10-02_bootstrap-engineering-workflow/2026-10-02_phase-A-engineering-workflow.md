---
name: 2026-10-02_phase-A-engineering-workflow
type: small-plan
parent_plan: engineering-workflow-improvements
phase_index: 1
status: planned
closeout_session_log:
---

# Small Plan: Engineering Workflow Guidance

## Scope

Update existing guidance and its focused deterministic checks on `dev` after
sidecar repair PR #43. This phase covers REQ-001–005 and REQ-007–009.
REQ-006 is deferred to the separate optional pilot. Preserve `.ai-bootstrap/`,
caller-saved specialist output, independent review, and all existing gates.
No runner changes, executable benchmark fixtures, or model runs are included.

## Steps

- [ ] **1. Make outcome, risk, contract, and test reasoning explicit in planning.**
  **Owner:** coder for shared guidance; documenter for worked examples.
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
  fields or a second plan parser. Name the approved plan/spec and approved
  scope-change records as requirement authority, with version references in
  handoffs; separate specs and IDs remain optional for simple tasks.
  Retained experiment code must identify proven behavior and shortcuts.
  Explicitly prohibit treating a spike as authorization for production
  implementation.
  **Acceptance:** legacy/micro plans still validate; a simple known task
  needs no new artifact or approval; decisive uncertainty remains explicit;
  manual observations never enter executable command lists. A small reviewed
  example distinguishes a technical assumption needing evidence from a user
  preference needing clarification; it requires no executable fixture.

- [ ] **2. Integrate requirements and meaningful-test review into existing roles.**
  **Owner:** coder; reviewer evaluates the final result independently.
  **Files:** modify `shared/agents/orchestrator/prompt.md`,
  `shared/agents/coder/prompt.md`, `shared/agents/reviewer/prompt.md`,
  `shared/review-profiles/code.md`, `shared/review-profiles/tests.md`, and
  `shared/skills/debug-investigator/SKILL.md`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/testing-patterns/SKILL.md`,
  `shared/skills/debug-investigator/SKILL.md`,
  `shared/skills/code-review/SKILL.md`.
  The general delegation rule already names requirements and non-goals.
  Align it with the reviewer-specific packet and the reviewer's input list;
  add the explicit instruction to compare the diff against supplied approved
  requirements. Carry approved plan/specification, approved scope changes,
  and contract references into coder and reviewer packets, with artifact versions and IDs
  where present. The reviewer compares against that authority, not its own
  reconstruction. Approved changes supersede affected original requirements;
  ambiguity is surfaced rather than turned into an invented requirement.
  Review coverage and scope in the normal two-pass review. Map a
  missing material requirement to existing severity; return ordinary
  finding objects, with IDs in existing titles/locations as useful. Add
  independent expected-value checks and targeted negative controls for
  critical or suspect tests. The reviewer requests execution evidence from
  the orchestrator/coder and never receives execute tools. Add an explicit
  post-fix original-symptom check to debugging and coder guidance, with
  evidence of changed behavior or an honest unverified limitation.
  **Acceptance:** no separate convergence artifact/schema; no automatic
  appended tasks; no mutation dependency. Guidance respects approved scope
  changes and valid alternative implementations, with no separate spec/IDs
  required for simple tasks. Instruction checks establish those rules are
  shipped; they do not claim that a model followed them.
  A green suite with an untested original symptom is not represented as
  complete symptom verification.

- [ ] **3. Improve checkpoints and failure learning without duplicate records.**
  **Owner:** coder/documenter.
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

- [ ] **4. Adapt the same guidance to relaxed sidecars and validate generation.**
  **Owner:** coder.
  **Files:** modify relevant `shared/agents/*/workflow-prompt.md`,
  `shared/sidecar/workflow/rules/workflow.md`,
  `shared/sidecar/workflow/instructions.md`, and existing
  `shared/sidecar/workflow/templates/`; extend `tests/test_validate_targets.py`
  and `tests/test_sidecar_workflow_scenario.py` as needed. Change generator
  or validator logic only for a demonstrated rendering/contract gap.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/testing-patterns/SKILL.md`.
  Use concise advisory equivalents, including approved-requirement authority,
  in existing templates; no additional requirements-spec unit or skill is
  needed. Shared review profiles remain
  advice. Respect team ownership and absent specialists. Copilot instructions
  must work without shipped Copilot agents; Codex/Antigravity get no new
  discovery claim. Preserve the skills-profile unit set. Keep state under
  `.ai-bootstrap/`; planner/reviewer return text, and callers save it in
  `plans/` and `quality_reports/` beneath that root. Retain the merged
  repair's caller behavior, fallbacks, and team precedence.
  **Acceptance:** generated full guidance contains the intended optional
  extensions; workflow sidecar has no new hooks, settings, mandatory receipts,
  forced plan lifecycle, or references to unshipped files. Existing team
  collision/status/index assertions still pass. Tests check contracts and
  forbidden authority changes rather than entire prose snapshots.

- [ ] **5. Check instruction contracts, review, document, and close out.**
  **Owner:** coder for tests; orchestrator for execution; independent reviewer;
  documenter after review convergence.
  **Files:** modify `tests/test_validate_targets.py`, `README.md`, and
  `docs/architecture.md` as needed; reuse existing sidecar scenario tests.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`,
  `shared/skills/code-review/SKILL.md`,
  `shared/skills/documentation/SKILL.md`.
  Add small deterministic checks that general and reviewer-specific
  delegation instructions, reviewer inputs, and review steps agree on
  approved requirements and scope changes. Check that debug resolution
  requires the original reproduction to be rerun, with outcome or limitation
  recorded, and that source/generated variants preserve optional specs/IDs
  and sidecar authority. Prefer contract assertions over full prose snapshots;
  include changed skills in the generated-surface checks where shipped.
  Do not add a new semantic evaluator or require one exact wording.
  Run the required checks. Refresh the authoring overlay with
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
  after generation if changed shared files make runtime checks stale.
  **Acceptance:** focused checks and independent review pass; the eight
  in-scope requirements map to source/evidence in the log. Record REQ-006
  as deferred and before/after source revisions for traceability. Report
  instruction consistency, not measured agent improvement. Persist findings
  and receipts only through existing closeout.

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

- Inspect generated full and workflow guidance for coherent requirements,
  technical-risk examples, and caller-saved sidecar outputs. This is a prose
  review, not evidence of agent behavior. No native evaluation is required.

## Review Profiles

Use `.claude/review-profiles/code.md`,
`.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`. Review approved-requirement
comparison, optional specs/IDs, original-symptom evidence, unchanged receipts,
and sidecar state/authority boundaries explicitly.

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
