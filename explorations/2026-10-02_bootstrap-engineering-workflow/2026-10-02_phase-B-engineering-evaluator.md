---
name: 2026-10-02_phase-B-engineering-evaluator
type: small-plan
parent_plan: engineering-workflow-improvements
phase_index: 2
status: planned
closeout_session_log:
---

# Small Plan: Behavioral Evaluator and Baseline Replay

## Scope

Implement and validate the bounded evaluator using Phase A's frozen cases,
oracles, and saved observations. Complete measurement work before Phase C
changes planner/reviewer/reporting/sidecar guidance. This phase covers REQ-006
and REQ-009. It introduces no new scenarios, native wave, provider registry,
model judge, receipt schema, or model-backed verification gate.

## Steps

- [ ] **1. Establish replay against Phase A's evidence contract.**
  **Owner:** coder; orchestrator supplies frozen evidence.
  **Files:** read the dated baseline document, `tests/fixtures/behavioral/`,
  and `docs/evidence/engineering-behavioral/`; modify
  `scripts/check_native_clients.py` and `tests/test_check_native_clients.py`.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`,
  `shared/skills/integration-gate-spike/SKILL.md`.
  Check scenario/oracle revisions, artifact hashes, capture format, and saved
  output sufficiency before coding. Implement deterministic scoring against
  independent fixture truth, with the frozen human rubric for semantic
  judgments. Never score self-ratings or tune expectations to baseline answers.
  Keep the replay path in the existing runner; it reads saved evidence without
  launching a model. Keep oracle/scorer content outside supplied task context.
  **Acceptance:** true defects and repaired, clear-task, valid-alternative,
  and approved-change controls have the expected outcomes. Approved plan/spec
  and approved changes supply coverage-case authority. Missing replay inputs
  are explicitly unscorable; no invented replacement baseline.

- [ ] **2. Add the isolated opt-in behavioral mode and evidence capture.**
  **Owner:** coder.
  **Files:** modify `scripts/check_native_clients.py`,
  `tests/test_check_native_clients.py`, and
  `docs/native-client-acceptance.md`; use Phase A's fixture definitions.
  **Required Skills:** `shared/skills/ponytail/SKILL.md` (full),
  `shared/skills/code-style/SKILL.md`,
  `shared/skills/testing-patterns/SKILL.md`.
  Add the proposed `--behavioral-workloads` bootstrap option, isolated from
  existing planner-workload and shim-removal modes. Reuse process, workspace,
  timeout, and version helpers. Preserve public calls and existing report keys
  when the new mode is absent; optional additive arguments only if needed.
  Reject combination with `--planner-workloads`. Run only the new pilot
  packets and necessary preflight/version checks. Use native invocation and
  event fields actually demonstrated in Phase A; no assumed provider adapter.
  Add a versioned behavioral result section without changing
  `native-client-observation.schema.json` or deterministic receipt schemas.
  Capture complete bounded task answers and allowlisted indicators for replay,
  with run/case/repetition IDs, input/evidence hashes, scenario/oracle/scorer
  revisions, provider/client/version, requested and observed model/effort,
  permission mode, source revision, generated-bundle identity, time, and usage.
  Unknown metadata stays unknown. Follow the design's privacy contract;
  legacy raw-output disposal and workspace/auth protections remain unchanged.
  **Acceptance:** missing observations, invalid outputs, unavailable runs,
  and behavioral failures remain separate, with explicit denominators and
  confounded comparisons. Malformed/duplicate output, oracle reads, timeouts,
  and unsupported transport cannot manufacture behavioral PASS. Ordinary
  tests and verification entrypoints never invoke models; a strict native
  runner exit mode does not become a commit-gate input.

- [ ] **3. Validate replay, independently review, and freeze the scorer.**
  **Owner:** orchestrator for execution; independent reviewer; documenter
  after review convergence.
  **Files:** runner/tests, `docs/native-client-acceptance.md`, dated baseline
  document, and versioned results beside preserved baseline evidence.
  **Required Skills:** `shared/skills/testing-patterns/SKILL.md`,
  `shared/skills/code-review/SKILL.md`,
  `shared/skills/documentation/SKILL.md`.
  Test valid/invalid outputs, missing events, unavailable runs, metadata drift,
  privacy, legacy invocation compatibility, and replay without native calls.
  Verify that replay scores the same saved answer consistently, detects
  mismatched scenario/oracle inputs, and never converts missing evidence into
  a behavioral verdict. Check fixture truth with the planted broken/good
  variants; inspect false positives independently of baseline performance.
  Run the final scorer over all saved Phase A attempts and preserve original
  observations and provisional judgments. Append results with input hashes
  and scorer/rubric identity, including any unscorable dimensions.
  **Acceptance:** deterministic scorer tests and independent review pass;
  scenario/oracle revisions and final scorer/rubric revision are frozen before
  Phase C begins. The handoff includes replayed baseline results and all
  limitations. If evidence is insufficient, report the affected measurement
  incomplete and resolve its scope before claiming comparability. Do not
  alter workflow prompts or run the candidate wave in this phase.

## Verification

```bash
uv run pytest tests/test_check_native_clients.py tests/test_validate_plan_frontmatter.py tests/test_verify.py tests/test_hook_gates.py -q
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Inspect the complete replay report against Phase A's preserved evidence;
  include human-rubric judgments and missing evidence as such. No additional
  native wave is planned. Phase C owns the matched candidate evaluation.

## Review Profiles

Use `.claude/review-profiles/code.md`,
`.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`. Review oracle independence,
safe replay retention, separate evidence states, metadata/confounding,
old invocation compatibility, and unchanged verification authority.

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
