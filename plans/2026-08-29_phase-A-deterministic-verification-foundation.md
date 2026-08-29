---
name: 2026-08-29_phase-A-deterministic-verification-foundation
type: small-plan
parent_plan: verification-evidence-workflow-consolidation
phase_index: 0
# status must occur exactly once: in-progress | paused | complete | cancelled
status: in-progress
closeout_session_log:
# Pause fields (required only when status is paused):
# paused_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# paused_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# pause_session_log: <repository-relative readable UTF-8 PAUSED session log>
# Cancellation fields (required only when status is cancelled):
# cancelled_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# cancelled_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# cancelled_evidence: <repository-relative readable UTF-8 CANCELLED artifact>
---
# Small Plan: 2026-08-29_phase-A-deterministic-verification-foundation

## Scope

Add the deterministic verification/evidence layer without changing current agent
routing or commit/push/PR authority. Existing verifier + legacy gates remain
authoritative while the new path is proved.

Use Ponytail `full`. Reuse current report metadata, Git freshness helpers,
Task-Lane/control-plane classification, validator functions, generator/runtime
ownership, and report directories.

## Pre-Flight

1. Update/rebase from fresh `dev`; record exact HEAD.
2. Run current generation, validation, runtime, hook, verifier, and score flows.
3. Inspect live `quality_score.py`, findings/report readers, target/runtime
   validators, generator/installer ownership, plan statuses, and all providers.
4. Confirm current conditional-planner, Context Mode, reporting/language, and
   paused-publication behavior.
5. Treat live code as authority over filenames in this plan.

## Steps

- [ ] **1. Add one strict verification entrypoint.**
  - Owner: `coder`
  - Create canonical source under the existing generated script surface, expected
    as `shared/scripts/verify.py` unless live ownership dictates another path.
  - Generated consumer command is `.claude/scripts/verify.py`.
  - Use stdlib + existing helpers; no new dependency.
  - Support exactly `fast`, `phase`, `closeout`.
  - Required check states: `PASS`, `FAIL`, `UNVERIFIED`, `NOT_APPLICABLE`.
  - Persist `schema_version`.
  - Reject malformed required fields and unknown required state values.
  - `NOT_APPLICABLE` comes only from deterministic applicability logic.

- [ ] **2. Implement fail-closed check adapters and harden current score measurement.**
  - Owner: `coder`
  - Successful process + valid expected output may PASS.
  - Measured lint/type/test failure -> FAIL.
  - Missing executable, timeout, abnormal tool/infrastructure exit, parser error,
    or required empty/unmeasured output -> UNVERIFIED unless documented tool
    semantics clearly establish FAIL.
  - Explicitly fix/fence current live defects:
    - Ruff nonzero + empty stdout cannot become zero clean violations.
    - Ruff malformed JSON cannot become zero clean violations.
    - Mypy abnormal failure cannot become zero clean errors.
    - Pytest infrastructure failure must be distinguishable from ordinary test failure.
  - Modify `quality_score.py` only as needed to prevent clean reports from failed
    measurement while preserving backward-compatible fields and score >=90 policy.
  - Do not remove blocked evidence merely because a command returns nonzero.

- [ ] **3. Add stable check IDs and falsifier regressions.**
  - Owner: `coder`
  - Minimum IDs:
    `VFY-STATUS-001`, `VFY-STATUS-002`, `VFY-RUFF-001`, `VFY-MYPY-001`,
    `VFY-FRESH-001`, `VFY-FRESH-002`, `VFY-CONTROL-001`, `VFY-GEN-001`,
    `VFY-DETERMINISM-001`, `VFY-RECEIPT-001`.
  - Negative fixtures must cover:
    Ruff empty/nonzero, Ruff malformed JSON, abnormal mypy output, pytest process
    failure, missing executable, timeout, missing check, malformed/unknown status,
    invalid free-form N/A, stale relevant evidence, and tampered referenced
    evidence where Phase A creates references.
  - Do not add generic mutation-testing infrastructure.

- [ ] **4. Add minimal scoped freshness.**
  - Owner: `coder`
  - Reuse existing Git metadata/content-hash helpers.
  - Distinguish only:
    `code/test/config/generator/control-plane`, `review`, `documentation-only`,
    `final closeout whole-diff`.
  - Reuse current Task Lanes/control-plane ownership.
  - Code/config/generator/control-plane changes stale relevant code evidence.
  - Ordinary unrelated docs-only changes may preserve unaffected code evidence.
  - Control-plane Markdown is never harmless docs-only.
  - Final closeout always binds the complete tracked state.

- [ ] **5. Add cheap verification groups without rewriting the validator.**
  - Owner: `coder`
  - `fast`: focused changed-scope feedback; no persisted commit authority.
  - `phase`: authoritative task-lane checks; persist reusable evidence.
  - `closeout`: validate/reuse fresh phase evidence and model final receipt, but
    remain non-authoritative until Phase C.
  - Wrap/select current validator functions with the smallest dispatcher.
  - Preserve a full CI/current-validation path with unchanged coverage.

- [ ] **6. Wire generation, installation, and runtime ownership.**
  - Owner: `coder`
  - Generated verification files must install/update/prune deterministically,
    survive self-install dogfood, and be covered by runtime drift checks.
  - Preserve consumer-owned AI state.
  - Never hand-edit `dist/`.
  - Add a separate schema file only if it makes strict validation materially
    safer/simpler than code-only validation.

- [ ] **7. Prove parity before anyone trusts the new path.**
  - Owner: `verifier`
  - Run current authoritative verifier commands and `verify phase` against the
    same clean state and matched negative fixtures.
  - New path may be stricter where current scorer is fail-open; document why.
  - Existing verifier/legacy score/findings/gates remain authoritative in Phase A.

- [ ] **8. Run consolidated control-plane review + Ponytail.**
  - Owner: `reviewer`
  - Profiles: `code`, `architecture`, `security`, `tests`, `documentation`, `ponytail`.
  - Challenge measurement-failure PASS, N/A bypass, unknown receipt states,
    freshness misclassification, accidental `fast` authority, reduced full
    validation coverage, generated/source drift, and unnecessary schema/framework.
  - Run Ponytail last.

## Expected Source Surfaces

```text
shared/scripts/verify.py
shared/scripts/quality_score.py
shared/scripts/record_findings.py          # only if helpers are reused
shared/schemas/<receipt schema>            # only if justified
scripts/validate_targets.py
scripts/generate_targets.py
scripts/check_runtime.py
scripts/runtime_ownership.py
scripts/install_bootstrap.py
tests/<focused verification tests>
minimal verification docs
```

Do not change canonical agent workflow except additive documentation required to
describe the non-authoritative command.

## Verification

```bash
uv run pytest tests/ -q --tb=short
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py fast --format json
uv run python .claude/scripts/verify.py phase --format json --persist
uv run python .claude/scripts/verify.py closeout --format json --persist
```

Use the actual CLI selected during implementation if equivalent. Persist the
legacy quality report because current gates remain authoritative.

## Acceptance Criteria

- [ ] Current lifecycle/gate authority unchanged.
- [ ] Existing verifier remains authoritative.
- [ ] One generated deterministic verifier exists.
- [ ] Missing/tool/parser/timeout/unmeasured required states cannot PASS.
- [ ] Proven Ruff/mypy fail-open cases are fixed or fenced by UNVERIFIED.
- [ ] Critical checks have falsifier regressions.
- [ ] N/A cannot be agent-selected.
- [ ] Freshness behaves correctly for code vs ordinary docs-only changes.
- [ ] Control-plane Markdown never gets docs-only treatment.
- [ ] Full validation coverage remains available.
- [ ] Generated consumer verifier executes correctly.
- [ ] Output is machine-readable/deterministic apart from documented volatile metadata.
- [ ] No provider/install/runtime regression exists.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`

## Pause Checkpoint

Use only after an explicit user request. Preserve current paused checkpoint
commit and durable backup-push semantics; this phase does not redefine them.
