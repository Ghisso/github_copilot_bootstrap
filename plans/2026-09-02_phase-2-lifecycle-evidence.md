---
name: lifecycle-evidence
type: small-plan
parent_plan: verification-gate-semantic-hardening
phase_index: 2
status: in-progress
---

# Phase 2 — Enforce Lifecycle Evidence

**Parent:** `verification-gate-semantic-hardening`  
**Phase:** 2 of 3  
**Primary objective:** make findings, plan metadata, cancellation evidence, and the full completed-phase receipt chain enforceable at the correct lifecycle boundaries.

## 1. Problem

The current lifecycle still permits several invalid-but-committable states:

- a completed phase can retain an open MAJOR finding;
- MINOR findings can survive without explicit acknowledgement;
- plan-frontmatter validation is stronger in the authoring repo than in consumers;
- cancellation evidence is not enforced at the commit boundary;
- push/PR checks validate only the terminal completed phase receipt.

The fix must preserve one important distinction:

> MAJOR findings block the **phase-completion commit**, not every intermediate commit while a phase remains active.

## 2. Findings contract

### 2.1 CRITICAL and MAJOR

At phase completion:

- `critical == 0`
- `major == 0`

Do not provide a waiver field that allows CRITICAL or MAJOR findings to survive a completed phase.

Intermediate implementation commits may still exist while a phase is in progress.

### 2.2 MINOR

Each surviving MINOR finding must include:

```json
{
  "severity": "MINOR",
  "title": "...",
  "disposition": "accepted",
  "reason": "..."
}
```

Exact field names may follow the current findings schema, but the semantics must remain minimal:

- disposition is explicit;
- reason is non-empty meaningful text;
- no authority-implying metadata.

The gate verifies presence/shape, not truth.

### 2.3 Counts

Keep or strengthen deterministic counts-vs-findings validation.

Counts must be derived from the finding list or cross-checked exactly.

Do not trust independently asserted counts.

## 3. Ship and hard-enforce plan-frontmatter validation

The current authoring validator checks fields such as:

Big plan:

- `name`
- `type`
- `status`
- `originating_branch`
- `implementation_branch`
- `phases`
- lifecycle-specific required fields

Small plan:

- `name`
- `type`
- `parent_plan`
- `phase_index`
- `status`
- lifecycle-specific required fields

It also checks body phase inventory consistency and paused/cancelled contracts.

Consumers must receive equivalent validation.

Preferred approach:

- render the validator into consumer runtime via `scripts/generate_targets.py`;
- call it as a hard failure from the ordinary commit/lifecycle gate, or reuse its logic through `verify.py` if that creates one authoritative code path;
- promote bootstrap-side `scripts/check_runtime.py` plan-frontmatter failure from WARN to FAIL.

Do not maintain a third independent partial schema in bash if the Python validator can be safely shipped and invoked under current runtime constraints.

If a stock-`python3` constraint applies to hooks, preserve it.

## 4. Cancellation evidence at commit

When the active plan set contains a small plan with `status: cancelled`, commit validation must require the standard cancellation evidence contract:

- valid UTC `cancelled_at`;
- meaningful plain scalar `cancelled_reason`;
- repository-relative evidence path;
- evidence file contains `**Status:** CANCELLED`.

Reuse the stricter existing cancellation validation logic.

Do not defer this until push/PR.

## 5. Validate the complete historical receipt chain

### 5.1 Do not loop terminal validation blindly

Earlier phase receipts bind older HEADs by design.

A current-state check such as:

`receipt.head_sha == current HEAD`

must apply only to the terminal receipt.

### 5.2 Historical receipt validation mode

Extend the existing receipt reader/validator.

For every completed historical phase:

1. receipt schema is supported;
2. phase identity matches the big-plan phase entry;
3. parent/plan identity is consistent;
4. recorded `head_sha` resolves to a commit;
5. recorded `tree_sha` equals:
   `git rev-parse <head_sha>^{tree}`;
6. immutable bound artifacts still hash-match current bytes at their required immutable paths;
7. receipt HEAD is an ancestor of the next phase receipt HEAD;
8. final historical receipt HEAD is an ancestor of the terminal/current pushed HEAD;
9. phase order matches the big plan;
10. no phase is silently skipped unless an explicit migration rule says why.

Reuse:

- existing `head_relation == ancestor` behavior;
- `git merge-base --is-ancestor`;
- `enforce_final_state` or its equivalent;
- existing receipt parsing and artifact digest verification.

Add a dedicated historical mode rather than forking the verifier.

### 5.3 Terminal receipt

Only the terminal completed phase receives strict current-state checks such as:

- exact current HEAD where required;
- current tree/staged state;
- current runtime fingerprint;
- current merge-base/freshness requirements;
- terminal closeout checkpoint rules.

### 5.4 Legacy allowance

If v3 historical receipts require a compatibility allowance:

- key it to an explicit schema/version or bounded migration condition;
- document why;
- test it;
- define when it can be removed.

Do not retain a permanent comment equivalent to "earlier phases may predate receipts."

## 6. Files to inspect and likely change

Primary:

- `shared/scripts/verify.py`
- `shared/scripts/record_findings.py`
- `shared/hooks/scripts/_lib-frontmatter.sh`
- `shared/hooks/scripts/enforce-commit-gate.sh`
- `shared/hooks/scripts/enforce-pr-gate.sh`
- `shared/hooks/git-hooks/commit-msg`
- `shared/hooks/git-hooks/pre-push`
- `scripts/generate_targets.py`
- `scripts/validate_plan_frontmatter.py`
- `scripts/check_runtime.py`

Policies/prompts:

- `shared/agents/orchestrator/prompt.md`
- `shared/agents/reviewer/prompt.md`
- `shared/policies/workflow.instructions.md`
- `shared/policies/quality-and-testing.instructions.md`

Tests:

- `tests/test_verify.py`
- `tests/test_hook_gates.py`
- `tests/test_lifecycle_hooks.py`
- `tests/test_validate_plan_frontmatter.py`
- `tests/test_validate_targets.py`

## 7. Failing-first regression cases

Add targeted tests for at least:

### Findings

- phase-completion commit + open MAJOR -> blocked;
- in-progress/non-completion commit + open MAJOR -> not blocked solely for that reason;
- MINOR without disposition -> completion blocked;
- MINOR with empty reason -> completion blocked;
- MINOR with accepted disposition + reason -> findings contract passes;
- forged counts inconsistent with findings -> blocked.

### Frontmatter

- consumer plan missing `name` -> blocked;
- small plan missing `phase_index` -> blocked;
- invalid big-plan body phase inventory -> blocked;
- paused-plan validation remains supported;
- bootstrap `check_runtime.py` surfaces invalid plan metadata as FAIL.

### Cancellation

- cancelled small plan without evidence -> commit blocked;
- malformed cancelled timestamp/reason/path/status -> blocked;
- valid cancellation evidence -> allowed when other invariants pass.

### Receipt chain

- two or more historical receipts in valid order -> pass;
- historical receipt HEAD missing -> fail;
- `tree_sha` does not match historical commit -> fail;
- old artifact bytes changed -> fail;
- phase receipt order reversed -> fail;
- historical HEAD not ancestor of next/current -> fail;
- valid historical receipts with terminal fresh receipt -> pass;
- terminal stale current-state receipt -> fail;
- supported legacy/schema migration path from Phase 1 -> pass.

## 8. Acceptance criteria

Phase 2 is complete when:

- [ ] open MAJOR findings block the phase-completion commit.
- [ ] open MAJOR findings do not automatically block every intermediate in-progress commit.
- [ ] surviving MINOR findings require explicit disposition and non-empty reason.
- [ ] counts are derived or exactly cross-checked against findings.
- [ ] consumers receive hard plan-frontmatter validation.
- [ ] `scripts/check_runtime.py` treats invalid plan frontmatter as FAIL.
- [ ] cancellation evidence is checked at commit for cancelled plans.
- [ ] push/PR validation evaluates every completed phase.
- [ ] historical receipts use ancestor/tree/artifact semantics.
- [ ] only the terminal receipt uses current-state freshness rules.
- [ ] migration allowances are explicit and bounded.
- [ ] all new invariants have regression tests.
- [ ] generated targets contain the required shipped validator/runtime.
- [ ] full relevant tests and validation pass.

## 9. Non-goals

- Do not authenticate review judgments.
- Do not turn MINOR dispositions into a trust mechanism.
- Do not make every commit require a review-clean completed-phase state.
- Do not mutate historical artifacts to simplify validation.
