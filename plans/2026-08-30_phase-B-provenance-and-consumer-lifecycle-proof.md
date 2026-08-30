---
name: 2026-08-30_phase-B-provenance-and-consumer-lifecycle-proof
type: small-plan
parent_plan: consumer-verification-provenance-hardening
phase_index: 1
status: pending
closeout_session_log:
---
# Small Plan: 2026-08-30_phase-B-provenance-and-consumer-lifecycle-proof

## Scope

Bind verification evidence to governing nested `.claude` control-plane state,
then prove the complete generated-consumer deterministic lifecycle. Finish with a
small audit removing/reclassifying runtime checks that cannot genuinely be
falsified.

Phase A is prerequisite. Do not reopen its resolver without concrete evidence.
Use Ponytail `full`.

## Pre-Flight

1. Update/rebase from current `dev` after Phase A.
2. Re-run Phase A clean/broken generated-consumer fixtures.
3. Inspect nested `.claude` Git/state-sync model, runtime ownership, generated
   ownership metadata, plan storage, receipts, gates, and freshness helpers.
4. Identify exactly which nested state can change verification meaning without
   changing outer application code.
5. Inventory emitted runtime check IDs and classify them as measurements or
   structural/schema invariants.
6. Preserve lifecycle, planner, Context Mode, review, language, pause, score,
   findings, bypass, and provider semantics.

## Steps

- [ ] **1. Define minimal nested control-plane provenance.**
  - Owner: `coder`
  - Reuse existing nested Git/state-sync/runtime-ownership helpers.
  - Required semantic coverage:
    - nested control-plane HEAD when available;
    - tracked-state/dirty fingerprint when HEAD is insufficient;
    - active big-plan digest;
    - active small-plan digest;
    - verification/runtime ownership fingerprint;
    - schema/version.
  - Prefer one canonical runtime/control-plane fingerprint plus explicit active
    plan digests.
  - Exclude mutable evidence outputs that would self-invalidate receipts.
  - Do not create another state repository/database.

- [ ] **2. Capture/validate provenance in phase and closeout evidence.**
  - Owner: `coder`
  - `verify phase --persist` records governing provenance.
  - `verify closeout --persist` validates current outer + nested state before
    reusing phase evidence.
  - Final receipt binds outer final state + nested governing runtime + active plan.
  - Missing/unreadable required provenance is UNVERIFIED/invalid.
  - Do not hash caches, venvs, every package, or unrelated user-owned `.claude`
    state.

- [ ] **3. Make gates consume provenance without becoming expensive.**
  - Owner: `coder`
  - Reuse current canonical receipt validator/gate path.
  - Relevant nested runtime/plan change after verification must stale the receipt.
  - Normal report/receipt writes must not create circular self-staleness.
  - Preserve paused checkpoint publication as separate authority.
  - Hooks remain cheap.

- [ ] **4. Extend generated-consumer fixture through full lifecycle.**
  - Owner: `coder`
  - Establish deterministic minimal approved plan state, review/findings fixture,
    documentation applicability/update evidence, score, LEARN/no-learn, and
    COMPLETED session log using repository-supported helpers/formats.
  - Exercise:
    ```text
    install -> verify fast -> verify phase
    -> review/findings fixture -> closeout evidence
    -> verify closeout -> normal commit gate
    ```
  - No LLM calls.

- [ ] **5. Add provenance/lifecycle negative mutations.**
  - Owner: `coder`
  - Outer source change after phase -> stale.
  - Active small-plan content change -> stale.
  - Governing big-plan content change -> stale.
  - Verification runtime change -> stale.
  - Relevant nested tracked/dirty change -> stale.
  - Tampered receipt/referenced artifact -> deny.
  - Post-closeout outer change -> deny.
  - Post-closeout relevant nested change -> deny.
  - Normal receipt/report writes do not self-invalidate.
  - Unchanged valid consumer reaches commit allow.
  - Execute via installed consumer/native gate path, not only source helpers.

- [ ] **6. Audit runtime check IDs for falsifiability.**
  - Owner: `coder`
  - For every emitted check ask: can a realistic fixture make this check itself
    turn red?
  - If yes, keep it and ensure a focused falsifier exists.
  - If no because it is a schema/code invariant, remove it from runtime PASS
    output and enforce it with schema/validator/unit tests instead.
  - Inspect status-schema, applicability, control-plane classification, and
    deterministic-serialization style checks especially.
  - Do not add artificial runtime work just to preserve an ID.
  - Document intentional check-ID removals/migrations where needed.

- [ ] **7. Keep docs/generated ownership aligned.**
  - Owner: `documenter`
  - Document consumer-native scope, outer+nested provenance, staleness rules,
    self-referential-output exclusion, and measurement-vs-invariant distinction.
  - Do not overstate environment/cryptographic guarantees.
  - Apply `humanize` edit self-check.
  - Regenerate providers; never hand-edit `dist/`.

- [ ] **8. Final control-plane/security review + Ponytail.**
  - Owner: `reviewer`
  - Profiles: `code`, `architecture`, `security`, `tests`, `documentation`,
    `ponytail`.
  - Challenge HEAD-without-dirty coverage, self-invalidating fingerprints,
    unstaled plan/runtime changes, irrelevant-state over-staling, fake E2E tests,
    installed/source divergence, synthetic PASS checks, missing replacement
    invariant tests, and expensive hooks.
  - Run Ponytail last.

## Expected Source Surfaces

```text
shared/scripts/verify.py
shared/scripts/<receipt/provenance helpers>
shared/hooks/scripts/<receipt/gate helpers>
shared/hooks/scripts/enforce-commit-gate.sh
shared/hooks/scripts/enforce-pr-gate.sh
shared/hooks/git-hooks/pre-push
scripts/runtime_ownership.py
scripts/generate_targets.py
scripts/validate_targets.py
scripts/check_runtime.py
scripts/install_bootstrap.py
tests/test_hook_gates.py
tests/<verification/provenance/generated-consumer tests>
README.md / verification/gate docs
```

Touch state-sync helpers only if existing APIs cannot expose needed nested state.

## Verification

Run focused provenance/E2E tests first, then:

```bash
uv run pytest tests/ -q --tb=short
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```

In the generated consumer, prove clean allow and required stale/tamper denials
through installed verifier/gate paths.

## Acceptance Criteria

- [ ] Evidence binds relevant outer and nested control-plane state.
- [ ] Active plan changes stale evidence when they govern current work.
- [ ] Verification/runtime changes stale evidence.
- [ ] Relevant nested dirty state cannot hide behind unchanged HEAD.
- [ ] Mutable evidence outputs do not self-invalidate receipts.
- [ ] Missing required provenance fails closed.
- [ ] Hooks remain cheap.
- [ ] Paused publication remains unchanged/distinct.
- [ ] Generated consumer completes lifecycle to commit allow.
- [ ] Required source/plan/runtime/control-plane/tamper mutations deny.
- [ ] Every emitted runtime PASS is genuinely measured/falsifiable.
- [ ] Structural invariants are enforced outside runtime PASS output.
- [ ] Full provider/install/runtime/state-sync/determinism coverage passes.
- [ ] No workflow/model-routing regression exists.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted
- [ ] Documentation updated or explicitly skipped
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log is COMPLETED

## Pause Checkpoint

Use only after explicit user request. Preserve current paused checkpoint commit
and durable backup-push semantics.
