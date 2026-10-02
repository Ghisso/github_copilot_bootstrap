---
name: 2026-10-02_phase-A-engineering-evidence
type: small-plan
parent_plan: engineering-workflow-improvements
phase_index: 1
status: planned
closeout_session_log:
---

# Small Plan: Engineering Evidence and Behavioral Baseline

## Scope

Freeze the smallest useful evaluation and establish its native transport
before changing production prompts or writing a provider-specific evaluator.
This is an evidence/fixture phase, not a new runtime or an implicit approval
to implement the policy proposals. It covers REQ-006 and REQ-009.

## Steps

- [ ] **1. Revalidate the baseline and freeze packets/oracles.**
  **Owner:** orchestrator with documenter.
  **Files:** create `docs/2026-10-02-engineering-behavioral-baseline.md`;
  create authored packets, repaired controls, and expected results under
  `tests/fixtures/behavioral/`. Read `scripts/check_native_clients.py`,
  `tests/test_check_native_clients.py`, the two calibration docs, and this
  exploration's `design.md` first.
  **Required Skills:** `shared/skills/integration-gate-spike/SKILL.md`,
  `shared/skills/documentation/SKILL.md`, `shared/skills/ponytail/SKILL.md`.
  Record the actual source revision and generated-bundle digest. Freeze
  the three cases from the design, with independent expected results and
  matched repaired/clear controls. Expected answers stay outside the
  model-readable workspace. Use two tiny function/test variants for the
  weak-test case: host execution must demonstrate that the weak test lets
  the bug through and the corrected test detects it. List any shortcut or
  hardcoded value in the fixture; it is not a production reference library.
  **Acceptance:** each case tests one concrete gap; oracle/result fields
  are defined without exposing the expected answer in the task prompt.

- [ ] **2. Prove the native invocation and observable fields.**
  **Owner:** orchestrator on the native host.
  **Files:** update the dated baseline document; scratch files only in the
  existing runner's marker-owned workspace.
  **Required Skills:** `shared/skills/integration-gate-spike/SKILL.md`.
  Inspect existing `parse_args`, command builders, `safe_workspace`,
  `prepare_workspace`, and `parse_jsonl` before invocation. An existing
  supported setup command is `uv run python scripts/check_native_clients.py
  --client claude --workspace /tmp/native-client-probe-engineering-baseline
  --prepare-only`; use Codex instead only if that is the available provider.
  The existing `--planner-workloads --json` command in that prepared,
  trusted workspace remains a transport control, not the new benchmark.
  It can also run existing acceptance checks: account for those calls in
  the budget rather than assuming the flag runs only two workloads.
  Run one bounded scratch case using the inspected provider command shape
  and a task-output schema. Record exact argv shape, version, requested and
  observed model metadata, permission mode, available event fields, result
  format, and artifact hashes without retaining raw transcripts or auth.
  Never change trust/settings automatically or enable extra execution tools
  to force an observation. Withhold the scorer/oracle from supplied inputs;
  record actual read boundaries rather than assuming a read-only sandbox
  hides host files. An observed oracle read invalidates a run; missing read
  events leave that property unverified.
  **Acceptance:** at least one real client produces usable bounded task
  output; any event-based capability to be implemented has observed evidence.
  A self-audit response alone does not satisfy the behavioral requirement.

- [ ] **3. Record one bounded baseline wave.**
  **Owner:** orchestrator; documenter records the evidence.
  **Files:** dated baseline document and fixture definitions.
  **Required Skills:** `shared/skills/integration-gate-spike/SKILL.md`,
  `shared/skills/documentation/SKILL.md`.
  Follow the design's nine primary attempts and three controls on one
  provider, with no automatic retry. Count setup/transport calls separately.
  Preserve failed, unavailable, and unobserved results. A second provider
  is optional, separately budgeted, and not averaged into the first.
  Score actual task output against independent expectations; record human
  rubric judgments as such. Separate output correctness from observed reads,
  forbidden writes, or check execution. No overall action PASS without events.
  **Acceptance:** freeze baseline and cost observations before prompt edits.
  If the client or transport is unavailable, leave native evidence incomplete
  and report the blocker. Replan the affected future native step if needed;
  do not fabricate a successful baseline or cancel work unilaterally.

- [ ] **4. Review the measurement design and close the phase.**
  **Owner:** reviewer; orchestrator for closeout.
  **Required Skills:** `shared/skills/code-review/SKILL.md`,
  `shared/skills/documentation/SKILL.md`, `shared/skills/humanize/SKILL.md`.
  Check answer leakage, planted-defect truth, false-positive controls,
  event completeness, privacy, cost bound, and provider claims. Resolve
  high-severity findings. Give Phase B the exact measured transport and
  limitations; do not add a new permanent agent or general experiment engine.

## Verification

```bash
uv run pytest tests/test_check_native_clients.py -q
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- Native host sessions from steps 2–3 are recorded here because they require
  a trusted host and are not deterministic closeout commands. Successful
  transport evidence and the bounded baseline are acceptance conditions for
  implementing the corresponding native measurement in Phase B.
- A second provider may repeat the same packet/control wave with its own
  budget and evidence record; unavailable support is recorded, not inferred.

## Review Profiles

Use `.claude/review-profiles/code.md`,
`.claude/review-profiles/architecture.md`,
`.claude/review-profiles/security.md`, `.claude/review-profiles/tests.md`,
`.claude/review-profiles/ponytail.md`, and
`.claude/review-profiles/documentation.md`.

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
