---
name: verification-authority
type: small-plan
parent_plan: verification-gate-semantic-hardening
phase_index: 1
status: complete
closeout_session_log: .claude/session_logs/2026-09-02_phase-1-verification-authority.md
---

# Phase 1 — Simplify Verification Authority

**Parent:** `verification-gate-semantic-hardening`  
**Phase:** 1 of 3  
**Primary objective:** delete the numeric score authority and make `verify.py` the single deterministic measurement authority without breaking in-progress consumer upgrades.

## 1. Problem

The current closeout binds a score JSON artifact, but the numeric score is not useful once the gate itself requires the underlying deterministic checks to pass.

Hardening the score would preserve duplicated machinery:

- a second measurement surface;
- score thresholds;
- gate labels;
- score JSON schema;
- session-log score duplication;
- report discovery;
- additional receipt hashes;
- extra documentation that can drift.

The simpler contract is PASS/FAIL deterministic verification plus review/lifecycle evidence.

## 2. Settled behavior

### 2.1 Remove the score concept from gate authority

Delete:

- `shared/scripts/quality_score.py`;
- generated copies of it;
- numeric score thresholds;
- `gate` labels such as `EXCELLENCE`;
- score deductions;
- authoritative `score-*.json` artifacts;
- receipt fields whose only purpose is binding the score file;
- session-log `## Score:` requirements;
- orchestrator/reviewer instructions that generate or validate score JSON.

Do not retain `quality_score.py` as an informational duplicate.

If a human-readable summary is useful, print it from `verify.py phase`.

Example shape only:

```text
Verification
  Ruff ........ PASS
  Mypy ........ PASS
  Pytest ...... PASS (N tests)
  Findings .... handled separately by closeout contract

Result ........ PASS
```

Do not add another 0–100 value.

### 2.2 Canonicalize remaining phase report naming

Use deterministic phase identity for findings artifacts, preferably:

`findings-<phase>.json`

Remove timestamp-based newest-report selection where the score deletion or findings update makes it unnecessary.

Do not preserve `latest_report()` solely for backward compatibility if migration can be handled at receipt-schema level.

### 2.3 Schema bump and migration

Update closeout receipt schema as required, expected v4.

The migration contract must explicitly cover a consumer that:

1. started an implementation plan under the current v3 runtime;
2. refreshes bootstrap runtime mid-plan;
3. still has one or more non-terminal phases or checkpointed closeout state;
4. must continue without manually rewriting old receipts or bypassing the gate.

Use PR #28's schema-version rejection/checkpoint machinery as the base.

Define:

- which existing v3 receipts remain readable as historical evidence;
- when a new v4 terminal receipt is required;
- what happens if the refresh occurs during a phase closeout checkpoint;
- what unsupported mixed states fail closed;
- the explicit removal condition for any temporary compatibility allowance.

Do not silently accept arbitrary old schemas.

## 3. Files to inspect and likely change

Primary:

- `shared/scripts/verify.py`
- `shared/scripts/quality_score.py` — delete
- `shared/scripts/record_findings.py`
- `scripts/generate_targets.py`
- `shared/agents/orchestrator/prompt.md`
- `shared/agents/reviewer/prompt.md`
- `shared/policies/workflow.instructions.md`
- `shared/policies/quality-and-testing.instructions.md`
- `shared/session_logs/README.md`
- `shared/templates/session-log.md`

Likely tests:

- `tests/test_verify.py`
- `tests/test_validate_targets.py`
- `tests/test_lifecycle_hooks.py`
- `tests/test_hook_gates.py`

Also search the full repo for:

- `quality_score`
- `score-`
- `EXCELLENCE`
- `score >=`
- `## Score`
- score-specific receipt keys
- score-specific regenerate instructions

Update all canonical and generated references.

## 4. Implementation sequence

### Step A — failing-first contract tests

Add tests that express the new contract before deleting code:

1. closeout no longer requires a score artifact;
2. score-specific receipt fields are rejected or ignored only according to the explicit schema migration design;
3. new receipt schema contains only authoritative evidence;
4. generated targets no longer contain `quality_score.py`;
5. session log no longer requires/duplicates a numeric score;
6. `verify.py phase` still reports enough deterministic measurement detail for a human;
7. supported v3 -> v4 mid-plan refresh succeeds;
8. unsupported schema/mixed state fails closed.

### Step B — make `verify.py` authoritative

Refactor existing measurement flow so:

- the verifier runs/collects the deterministic checks once per verification action;
- closeout consumes authoritative verifier results;
- no second script recomputes or republishes them as a score;
- receipt content binds the required evidence and exact state.

Avoid broad refactoring unrelated to the score removal.

### Step C — delete score surfaces

Delete the canonical scorer and remove generator wiring.

Remove score-era fields and instructions from:

- receipts;
- report validation;
- session-log validation;
- policies;
- templates;
- orchestrator/reviewer prompts;
- generated runtime.

### Step D — canonical findings naming

Update `record_findings.py` and its callers to produce deterministic phase-named output.

If migration support must read old timestamped findings for a v3 receipt, isolate that compatibility to the v3 reader. New v4 artifacts must use the canonical scheme.

### Step E — migration path

Implement and test the supported mid-plan transition explicitly.

Do not rely only on a fresh-plan happy path.

## 5. Acceptance criteria

Phase 1 is complete when:

- [ ] `shared/scripts/quality_score.py` is deleted.
- [ ] generated consumers do not receive `quality_score.py`.
- [ ] no new closeout requires a score JSON.
- [ ] no numeric score threshold or gate label affects commit/push/PR.
- [ ] `## Score:` is removed from the required session-log contract.
- [ ] `verify.py` remains the one authority for deterministic checks.
- [ ] verifier output provides a compact human-readable PASS/FAIL summary.
- [ ] findings use deterministic phase naming for new-schema artifacts.
- [ ] receipt schema is bumped as needed.
- [ ] supported v3 -> v4 mid-plan upgrade has a dedicated passing regression test.
- [ ] unsafe/unsupported migration states fail closed.
- [ ] generated targets are deterministic.
- [ ] all targeted tests pass.
- [ ] full relevant repo validation passes.

## 6. Non-goals

- Do not redesign findings semantics in this phase beyond what is required for artifact naming/schema compatibility.
- Do not implement all-phase historical receipt iteration yet.
- Do not add a replacement quality score.
- Do not add `produced_by` or similar provenance theater.

## 7. Closeout notes for the next phase

Record the exact new receipt schema and compatibility rules in the session log.

Phase 2 must consume those rules rather than re-deriving them.
