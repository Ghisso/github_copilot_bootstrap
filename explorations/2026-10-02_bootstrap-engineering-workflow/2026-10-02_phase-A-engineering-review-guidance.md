---
name: 2026-10-02_phase-A-engineering-review-guidance
type: small-plan
parent_plan: engineering-workflow-improvements
phase_index: 1
status: planned
closeout_session_log:
---

# Small Plan: Review and Original-Symptom Guidance

## Scope

Align review guidance with the approved requirements and add the
original-symptom check, on `dev` after sidecar repair PR #43. This is the
highest-value change, so it is delivered and reviewed on its own. It covers
REQ-004, REQ-005, and the review part of REQ-009. Planning, reporting, and
learning guidance belong to Phase B. REQ-006 is deferred to the separate
optional pilot. Preserve `.ai-bootstrap/`, caller-saved specialist output,
independent review, and all existing gates. No runner changes, executable
benchmark fixtures, or model runs are included.

## Steps

- [ ] **1. Align requirement authority and meaningful-test review in existing roles.**
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
  requirements. Name the approved plan/spec and approved scope-change records
  as requirement authority. Carry them, and contract references, into coder
  and reviewer packets, with artifact versions and IDs where present. The
  reviewer compares against that authority, not its own reconstruction.
  Approved changes supersede affected original requirements; ambiguity is
  surfaced rather than turned into an invented requirement.
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

- [ ] **2. Adapt the review guidance to relaxed sidecars.**
  **Owner:** coder.
  **Files:** modify the review and debugging parts of
  `shared/agents/orchestrator/workflow-prompt.md`,
  `shared/agents/coder/workflow-prompt.md`,
  `shared/agents/reviewer/workflow-prompt.md`,
  `shared/sidecar/workflow/rules/workflow.md`,
  `shared/sidecar/workflow/instructions.md`, and
  `shared/sidecar/workflow/templates/quality-report.md` as needed. Change
  generator or validator logic only for a demonstrated rendering/contract gap.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/testing-patterns/SKILL.md`.
  Use concise advisory equivalents of approved-requirement authority and the
  original-symptom check. Shared review profiles remain advice. Respect team
  ownership and absent specialists. Copilot instructions must work without
  shipped Copilot agents; Codex/Antigravity get no new discovery claim. Keep
  state under `.ai-bootstrap/`; the reviewer returns text, and its caller
  saves it in `quality_reports/` beneath that root. Retain the merged
  repair's caller behavior, fallbacks, and team precedence.
  **Acceptance:** workflow sidecar has no new hooks, settings, mandatory
  receipts, forced plan lifecycle, or references to unshipped files.
  Existing team collision/status/index assertions still pass.

- [ ] **3. Check instruction contracts, review, document, and close out.**
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
  sections: the general and reviewer-specific delegation rules and the
  reviewer's Inputs list name approved requirements and approved scope
  changes; the review steps compare the diff against them; and debug
  resolution requires rerunning the original reproduction and recording its
  outcome or limitation. Cover shared source and generated full and sidecar
  output. Do not snapshot whole files, require one exact sentence, or add a
  semantic evaluator.
  Run the required checks. Refresh the authoring overlay with
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
  after generation if changed shared files make runtime checks stale.
  **Acceptance:** focused checks and independent review pass; REQ-004 and
  REQ-005 map to source/evidence in the log. Report instruction consistency,
  not measured agent improvement. Persist findings and receipts only through
  existing closeout.

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

- Inspect generated full and workflow review guidance for coherent
  requirement authority, original-symptom evidence, and caller-saved sidecar
  review output. This is a prose review, not evidence of agent behavior. No
  native evaluation is required.

## Review Profiles

Use `.claude/review-profiles/code.md`,
`.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`. Review approved-requirement
comparison, original-symptom evidence, unchanged receipts, and sidecar
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
