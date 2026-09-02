---
name: 2026-09-02_phase-5-inactive-phase-diagnostics
type: small-plan
parent_plan: verification-gate-semantic-hardening
phase_index: 5
status: complete
closeout_session_log: .claude/session_logs/2026-09-02_phase-5-inactive-phase-diagnostics.md
---

# Phase 5 — Diagnose an Inactive Phase Instead of Crashing

**Parent:** `verification-gate-semantic-hardening`
**Phase:** 5 of 5
**Primary objective:** make `verify.py` report a clear, actionable message when
no phase is active, instead of exiting with an unhandled traceback, and correct
the one big-plan claim Phase 4 superseded.

## 1. Problem

When a big plan is `complete`, its `current_phase` is empty, so no small plan
resolves. Every receipt-producing mode then dies with an unhandled exception
rather than a diagnostic:

```
verify.py fast     -> ValueError: receipt metadata control-plane provenance is invalid
verify.py phase    -> ValueError: receipt metadata control-plane provenance is invalid
verify.py closeout -> ValueError: receipt persistence needs a safe phase slug
```

`verify.py gate` is unaffected, because it takes `--phase` explicitly.

This is pre-existing rather than introduced by phases 1–4:
`control_plane_provenance`, `active_plan_paths`, and `state_metadata` are all
byte-identical to `dev`. It is in scope now because this window — after a plan
closes and before the next opens — is a normal state that every consumer
reaches at the end of every plan, and the first thing they see is a stack
trace from the tool that is supposed to be the deterministic authority.

A traceback is also actively misleading here. It reads as a broken verifier
rather than as "there is nothing to verify against yet", which is the real
situation and is not an error in the user's work.

## 2. Settled behavior

### 2.1 A clean, actionable diagnostic with a non-zero exit

`main()` already has the convention, a few lines from the failure site:

```python
print("fast mode never persists evidence", file=sys.stderr)
return 2
```

Follow it. When the active phase cannot be resolved, print one short message
naming the actual condition and what to do about it, and return a non-zero
status. Do not print a traceback, and do not return 0.

The message must distinguish the genuine cases. "No plan is active" is a
different situation from "a plan is active but its metadata is malformed", and
a consumer needs to know which. Do not collapse them into one string.

### 2.2 Do not weaken any evidence

This phase changes only how an unresolvable phase is *reported*. It must not:

- make any receipt valid without control-plane provenance;
- make any mode report `PASS` when it could not measure;
- persist a receipt that binds no active plan;
- turn a real measurement failure into a diagnostic;
- relax `validate_receipt`, the provenance guard, or the phase-slug check.

An unresolvable phase means no receipt is produced at all. That is the correct
outcome and stays the correct outcome.

### 2.3 Decide deliberately whether `fast` needs a phase

`fast` exists for focused feedback during IMPLEMENT, marks
`VFY-FRESH-001`/`VFY-RECEIPT-001` as `NOT_APPLICABLE`, never persists, and
establishes no reusable evidence. Whether it should require plan provenance at
all is therefore a real design question, not a foregone conclusion.

Investigate and choose one, then say which and why:

- `fast` keeps requiring an active phase, and simply reports the condition
  cleanly; or
- `fast` runs its deterministic checks without binding plan provenance,
  because it produces nothing anyone can later rely on.

The second is only acceptable if it provably cannot yield an artifact,
receipt, or output that another gate could mistake for evidence. If there is
any doubt, choose the first. Do not widen what `fast` can be used to prove.

### 2.4 Correct the superseded big-plan claim

Big plan §3.5 still describes Phase 2's certified-commit selection as "the
first entry of `git rev-list --ancestry-path --reverse`". Phase 4 replaced
that with parentage-proof selection and a fail-closed branch for zero or
multiple candidates.

Phase 4 could not correct it: editing the plan after the plan closed
invalidated the closeout receipt's bound plan digest, with no active phase
left to regenerate against. This phase is active, so the correction lands
before this phase's receipts are generated and is bound by them.

Record the Phase 4 rule and keep the Phase 2 correction it builds on, so the
section reads as a history rather than a contradiction.

### 2.5 Two further reachable tracebacks, added to scope after review

The Phase 5 review's from-scratch sweep found two more unhandled tracebacks in
receipt-producing modes. Both reproduce identically against the pre-Phase-5
`HEAD`, so neither is a regression from this work. Both are being fixed here
rather than deferred, and this section records that as a deliberate scope
addition rather than leaving the plan of record silent about it.

1. **Unsafe explicit `--phase` slug on a non-implementation branch.** The
   guard short-circuits to `None` on any truthy `--phase`, so it never reaches
   the `PHASE_SLUG` check it already performs two lines below for the
   implementation-branch path. `phase` then crashes with `receipt metadata
   base_ref or phase is invalid` and `closeout` with `receipt persistence
   needs a safe phase slug`. This is phase-resolution behavior in the exact
   function this phase adds, and the docstring's claim that a `--phase`
   override means the phase "is resolved" overclaims: an unsafe override is
   untested, not resolved. No traversal is possible — both crash sites
   validate the slug before touching a path — so this is a diagnostics gap,
   not a security hole.

2. **`closeout` without `--documentation-na` when documentation was not
   updated.** Raised from `closeout_artifacts`, unrelated to phase
   resolution, and reachable on a fully valid active phase. It is in scope
   only because `closeout` is run at the end of every phase, so this is the
   traceback a consumer is most likely to meet in normal use.

Both take the same treatment as §2.1: a clean stderr message and a non-zero
exit, with no relaxation of any check. Fixing them must not turn a real
measurement failure into a diagnostic, and must not make either state a
supported way to produce evidence.

## 3. Non-goals

- Do not restructure `main()`'s argument handling or mode dispatch.
- Do not add a flag, config, or environment variable to control this.
- Do not make an inactive phase a supported state for producing evidence.
- Do not touch the certified-commit rule, the typo-bypass exclusion, the LEARN
  evidence contract, `existing_paths`, or receipt schema v4.
- Add no compatibility allowance.

## 4. Files to inspect and likely change

- `shared/scripts/verify.py` — `main()`, and whichever of
  `state_metadata`/`control_plane_provenance`/`build_receipt` the chosen
  approach requires
- `tests/test_verify.py`

## 5. Implementation sequence

Failing-first: add a test asserting a clean non-zero exit with a diagnostic
for each affected mode, confirm each fails against current code because of the
unhandled exception, then implement.

## 6. Acceptance criteria

- [ ] `fast`, `phase`, and `closeout` all report a clean diagnostic and a
      non-zero exit when no phase is active, with no traceback.
- [ ] an unsafe explicit `--phase` slug on a non-implementation branch is
      diagnosed rather than crashing.
- [ ] `closeout` without `--documentation-na` is diagnosed rather than
      crashing.
- [ ] the message distinguishes no-active-plan from malformed-plan-metadata.
- [ ] no mode reports `PASS` when it could not measure.
- [ ] no receipt is persisted without an active plan.
- [ ] `gate` behavior is unchanged.
- [ ] behavior with an active phase is unchanged for every mode.
- [ ] the `fast` provenance decision is recorded with its justification.
- [ ] big plan §3.5 records the Phase 4 rule.
- [ ] the phases 1–5 receipt chain validates through the consumer gate path.
- [ ] full repository tests and validation pass with no regeneration drift.

## 7. Completion evidence

Updated plan status, deterministic verification PASS, a findings report with
zero surviving findings or explicit dispositions, the closeout session log
under the immutable-log contract, generated-target parity, and the receipt
chain validated across all five phases.
