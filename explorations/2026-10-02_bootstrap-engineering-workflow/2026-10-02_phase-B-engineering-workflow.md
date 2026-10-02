---
name: 2026-10-02_phase-B-engineering-workflow
type: small-plan
parent_plan: engineering-workflow-improvements
phase_index: 2
status: planned
closeout_session_log:
---

# Small Plan: Integrated Engineering Workflow Improvements

## Scope

Implement the accepted recommendations through existing source components,
using Phase A's frozen cases and native evidence. This phase covers all
nine requirements; keep the full/sidecar distinction and all current gate
contracts. Reconcile sidecar content with the separate repair's actual state
before editing. Do not import its installer changes into this phase.

## Steps

- [ ] **1. Extend existing native evaluation without rewriting its history.**
  **Owner:** coder.
  **Files:** modify `scripts/check_native_clients.py`,
  `tests/test_check_native_clients.py`, `docs/native-client-acceptance.md`;
  use the Phase A fixtures in `tests/fixtures/behavioral/`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`, `shared/skills/testing-patterns/SKILL.md`,
  `shared/skills/integration-gate-spike/SKILL.md`.
  Add the proposed `--behavioral-workloads` bootstrap option, isolated from
  the old planner-workload and shim-removal modes. Preserve existing public
  function calls and return structures unless an additive optional argument
  is necessary. Reuse workspace/process/timeout/version helpers; do not
  create a provider registry, SDK wrapper, or separate runner. Reject the
  ambiguous combination with `--planner-workloads` and preserve legacy
  invocations and report keys when the new option is absent.
  Copy only scenario inputs to the model-readable workspace. Evaluate
  returned task artifacts against the hidden oracle; never grade returned
  self-scores. Parse only event fields demonstrated in Phase A. Emit a
  separate versioned behavioral result section with allowlisted metadata,
  fixture/source/bundle/scorer identity, independent output results, observed
  action results, unavailable metrics, duration, and exposed usage. Do not
  change `native-client-observation.schema.json` to accept unrelated data.
  Preserve raw-output disposal and current workspace/auth protections.
  **Acceptance:** missing events, malformed or duplicate outputs, timeouts,
  unavailable clients, and changed runtime identity cannot become behavioral
  PASS. Scorer tests accept the true findings and reject planted false
  findings; repaired/clear controls detect over-reporting. Ordinary test and
  verification entrypoints never invoke models. Native results are advisory;
  even a user-selected strict runner exit mode is not a commit-gate input.

- [ ] **2. Make outcome, risk, contract, and test reasoning explicit in planning.**
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
  fields or a second plan parser. Retained experiment code must identify
  proven behavior and shortcuts. Explicitly prohibit treating a spike as
  authorization for production implementation.
  **Acceptance:** legacy/micro plans still validate; a simple known task
  needs no new artifact or approval; decisive uncertainty remains explicit;
  manual observations never enter executable command lists.

- [ ] **3. Integrate requirements and meaningful-test review into existing roles.**
  **Owner:** coder; reviewer evaluates the final result independently.
  **Files:** modify `shared/agents/orchestrator/prompt.md`,
  `shared/agents/coder/prompt.md`, `shared/agents/reviewer/prompt.md`,
  `shared/review-profiles/code.md`, `shared/review-profiles/tests.md`, and
  `shared/skills/debug-investigator/SKILL.md`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/testing-patterns/SKILL.md`,
  `shared/skills/debug-investigator/SKILL.md`,
  `shared/skills/code-review/SKILL.md`.
  Carry approved scope/requirement/contract references into coder and reviewer
  packets. Review coverage and scope in the normal two-pass review. Map a
  missing material requirement to existing severity; return ordinary
  finding objects, with IDs in existing titles/locations as useful. Add
  independent expected-value checks and targeted negative controls for
  critical or suspect tests. The reviewer requests execution evidence from
  the orchestrator/coder and never receives execute tools. Add an explicit
  post-fix original-symptom check to debugging and coder guidance, with
  evidence of changed behavior or an honest unverified limitation.
  **Acceptance:** no separate convergence artifact/schema; no automatic
  appended tasks; no mutation dependency. A green suite with an untested
  original symptom is not represented as complete symptom verification.

- [ ] **4. Improve checkpoints and failure learning without duplicate records.**
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

- [ ] **5. Adapt the same guidance to relaxed sidecars and validate generation.**
  **Owner:** coder.
  **Files:** modify relevant `shared/agents/*/workflow-prompt.md`,
  `shared/sidecar/workflow/rules/workflow.md`,
  `shared/sidecar/workflow/instructions.md`, and existing
  `shared/sidecar/workflow/templates/`; extend `tests/test_validate_targets.py`
  and `tests/test_sidecar_workflow_scenario.py` as needed. Change generator
  or validator logic only for a demonstrated rendering/contract gap.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/testing-patterns/SKILL.md`.
  Use concise advisory equivalents in existing templates; no additional
  requirements-spec unit or skill is needed. Shared review profiles remain
  advice. Respect team ownership and absent specialists. Copilot instructions
  must work without shipped Copilot agents; Codex/Antigravity get no new
  discovery claim. Preserve the skills-profile unit set and state semantics.
  **Acceptance:** generated full guidance contains the intended optional
  extensions; workflow sidecar has no new hooks, settings, mandatory receipts,
  forced plan lifecycle, or references to unshipped files. Existing team
  collision/status/index assertions still pass. Tests check contracts and
  forbidden authority changes rather than entire prose snapshots.

- [ ] **6. Run matched evaluation, review, document, and close out.**
  **Owner:** orchestrator for evaluation/checks; reviewer; documenter after
  review convergence.
  **Files:** `README.md`, `docs/architecture.md`,
  `docs/native-client-acceptance.md`, the dated baseline/results document,
  and relevant source help/comments.
  **Required Skills:** `shared/skills/integration-gate-spike/SKILL.md`,
  `shared/skills/code-review/SKILL.md`, `shared/skills/documentation/SKILL.md`,
  `shared/skills/humanize/SKILL.md`.
  Run the required deterministic checks. Refresh the authoring overlay with
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
  after generation if changed shared files make runtime checks stale.
  Run one candidate wave matched to Phase A. Record per-case outcomes,
  control false positives, event observability, duration/usage, and all
  confounders. Do not choose only favorable repeats or call missing data an
  improvement. A confirmed regression returns to the ordinary fix loop;
  noisy outcomes inform review and do not introduce an automatic model gate.
  Map REQ-001 through REQ-009 to changed files and final evidence. Persist
  findings and receipts only through the existing closeout sequence.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run pytest tests/test_check_native_clients.py tests/test_validate_plan_frontmatter.py tests/test_verify.py tests/test_hook_gates.py -q
uv run pytest tests/test_validate_targets.py tests/test_sidecar_workflow_scenario.py -q
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Run the bounded candidate native wave on the same trusted host/model as
  Phase A. Record failures, missing observations, cost, and any changed
  environment. This host observation is required to claim measured behavior,
  but never becomes a probabilistic commit-gate command.
- Repeat on a second provider only within a separate agreed budget; keep
  its evidence and support limitations separate.

## Review Profiles

Use `.claude/review-profiles/code.md`,
`.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`. Review oracle independence,
over-questioning controls, raw-data disposal, unchanged receipts, old
invocation compatibility, and sidecar authority boundaries explicitly.

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
