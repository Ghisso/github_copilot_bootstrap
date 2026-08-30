---
name: 2026-08-30_phase-A-consumer-native-verification
type: small-plan
parent_plan: consumer-verification-provenance-hardening
phase_index: 0
status: in-progress
closeout_session_log:
---
# Small Plan: 2026-08-30_phase-A-consumer-native-verification

## Scope

Fix generic consumer verification so generated deterministic verification does
not assume bootstrap-authoring paths. Prove the fix in a realistic generated
consumer before adding provenance changes.

Do not change lifecycle/gate authority, receipt provenance schema, agent routing,
Context Mode, or provider behavior. Use Ponytail `full`.

## Pre-Flight

1. Update/rebase from fresh `dev`; record exact HEAD.
2. Read current `verify.py`, verification policy, `quality_score.py`,
   generator/installer/runtime ownership, and generated-consumer tests.
3. Run current bootstrap self-verification.
4. Create a disposable ordinary Python consumer with `pyproject.toml`, `src/`,
   and `tests/`; install current bootstrap and reproduce current behavior.
5. Inspect current consumer/test configuration patterns before deciding scope
   rules.
6. Preserve current planner/context/reporting/pause/gate behavior.

## Steps

- [ ] **1. Separate bootstrap-self targets from consumer targets.**
  - Owner: `coder`
  - Keep explicit authoring targets where valid for this repo.
  - Remove assumptions that arbitrary consumers have `shared/` or `scripts/`.
  - Reuse existing runtime/ownership markers to detect bootstrap self-verification;
    do not use a fragile repository-name check.
  - Missing paths must never imply PASS.

- [ ] **2. Add the smallest project-native consumer scope resolver.**
  - Owner: `coder`
  - Reuse current task-lane/applicability and changed-scope logic.
  - Do not add bootstrap verification config.
  - Ruff: use consumer-native project scope/config and avoid checking `.claude`
    bootstrap runtime as application source.
  - Pytest: use native discovery/configuration.
  - Mypy: honor configured `files`, `packages`, `modules`, or equivalent first;
    otherwise use only a narrowly proven conventional source root.
  - If a required check applies but trustworthy scope cannot be determined,
    return `UNVERIFIED`.
  - Do not build a generic framework/language detector or custom recursive walker
    unless live tool behavior proves it necessary.

- [ ] **3. Preserve strict failure semantics.**
  - Owner: `coder`
  - Missing tool, invalid configured target, timeout, parser failure, abnormal
    execution, and required unmeasured scope remain `UNVERIFIED`.
  - Ordinary lint/type/test findings remain `FAIL`.
  - `NOT_APPLICABLE` remains deterministic.
  - Keep existing verification-consolidation falsifier tests green.

- [ ] **4. Add a representative generated-consumer verification fixture.**
  - Owner: `coder`
  - Extend existing generator/installer integration tests.
  - Fixture contains `pyproject.toml`, `src/example_consumer/`, and `tests/`.
  - Install through the supported generated bootstrap path.
  - Prove generated `.claude/scripts/verify.py` runs.
  - Prove `verify fast` and `verify phase` measure consumer source/tests rather
    than bootstrap authoring paths.
  - Prove `.claude` bootstrap files do not pollute consumer lint/type results.
  - Execute installed generated artifacts; do not import source-side verifier
    helpers as a substitute.

- [ ] **5. Add negative consumer mutations.**
  - Owner: `coder`
  - Ruff violation -> FAIL.
  - Mypy violation -> FAIL when applicable.
  - Pytest failure -> FAIL.
  - Unresolvable required mypy scope -> UNVERIFIED.
  - Missing required executable -> UNVERIFIED where practical.
  - No false references to missing bootstrap `shared/`/`scripts/`.
  - Keep fixture variants minimal; do not create a packaging-layout matrix.

- [ ] **6. Update policy/docs only where needed.**
  - Owner: `documenter`
  - Explain bootstrap-self versus consumer verification.
  - Explain fail-closed behavior when required scope is not safely known.
  - Do not present heuristics as universal guarantees.
  - Apply mandatory `humanize` edit check.

- [ ] **7. Consolidated review + Ponytail.**
  - Owner: `reviewer`
  - Profiles: `code`, `architecture`, `security`, `tests`, `documentation`,
    `ponytail`.
  - Challenge hard-coded authoring layout, accidental `.claude` checking,
    aggressive guessing, unknown scope becoming PASS, bootstrap self-regression,
    fake integration tests, and unnecessary config/framework.
  - Run Ponytail last.

## Expected Source Surfaces

```text
shared/scripts/verify.py
shared/policies/quality-and-testing.instructions.md
scripts/generate_targets.py
scripts/validate_targets.py
scripts/check_runtime.py
scripts/runtime_ownership.py
scripts/install_bootstrap.py
tests/<verification tests>
tests/<generated-consumer tests>
README.md / verification docs
```

Use live paths as authority. Never hand-edit `dist/`.

## Verification

Run focused consumer tests first, then:

```bash
uv run pytest tests/ -q --tb=short
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```

In a disposable generated consumer:

```bash
uv run python .claude/scripts/verify.py fast --format json
uv run python .claude/scripts/verify.py phase --format json --persist
```

Use the actual supported invocation if equivalent.

## Acceptance Criteria

- [ ] Bootstrap self-verification remains green.
- [ ] Ordinary consumer verifier does not assume `shared/` or `scripts/`.
- [ ] Consumer Ruff/pytest/mypy scope follows project-native configuration/layout.
- [ ] `.claude` runtime is excluded from consumer application checks.
- [ ] Required unknown/unsafe scope yields UNVERIFIED.
- [ ] Clean generated consumer passes fast/phase verification.
- [ ] Consumer lint/type/test negative fixtures fail correctly.
- [ ] Integration test uses real generator/install path.
- [ ] Existing fail-closed semantics remain unchanged.
- [ ] No lifecycle/provider/gate regression exists.

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
