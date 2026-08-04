---
name: 2026-08-04_phase-A-runtime-drift-contract
type: small-plan
parent_plan: bootstrap-guidance-runtime-modernization
phase_index: 1
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-08-04_phase-A-runtime-drift-contract

## Scope

Define one machine-readable ownership map for tracked authoring files,
bootstrap-controlled installed files, and consumer-owned mutable state. Use it
to detect the current stale workflow order and future dogfood/install drift
without comparing consumer-specific state byte-for-byte.

## Ownership

- `coder`: ownership model, parity implementation, and regression fixtures.
- `verifier`: source-layout, installer, updater, and dogfood checks.
- `reviewer`: `code`, `architecture`, `security`, `tests`, `ponytail`.
- `documenter`: runtime/parity troubleshooting documentation.

## Required Skills

- `ponytail` (`full`), `testing-patterns`, `debug-investigator`, `run-tests`,
  `documentation`, `ponytail-review`.

## Steps

- [ ] Add a single ownership/classification contract reused by generation,
  installation, updating, restoration, and validation. It must distinguish
  tracked source adapters (for example root `AGENTS.md`), ignored generated
  overlays (for example root `CLAUDE.md` and runtime hook adapters), and
  consumer-owned `.claude` state.
- [ ] Extend source-repository validation to compare bootstrap-controlled
  dogfood surfaces with freshly generated output after applying documented
  substitutions. Exclude `MEMORY.md`, plans, explorations, logs, reports, and
  explicit project-context customizations.
- [ ] Fix all presently stale workflow spellings to
  `REVIEW -> DOCUMENT -> SCORE`, including tracked root guidance and installed
  dogfood policies.
- [ ] Add fixtures proving stale ignored overlays fail, consumer state does not
  fail, tracked authoring adapters are checked by invariants rather than naive
  byte equality, and dry-run performs no writes.
- [ ] Make diagnostics name the stale path, authoritative source, and exact
  regeneration/reinstall command.

## Verification

```bash
uv run pytest tests/test_validate_targets.py tests/test_install_bootstrap.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```

## Acceptance Criteria

- Current workflow-order drift is detected before the fix and passes after it.
- Consumer state preservation remains byte-for-byte tested.
- A synchronized `ai-state` branch cannot mask stale bootstrap-controlled files.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
