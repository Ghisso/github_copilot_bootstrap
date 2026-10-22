---
name: 2026-10-22_phase-B-validator-pytest-error
type: small-plan
parent_plan: sidecar-onboard-and-validator
phase_index: 2
status: planned
closeout_session_log:
---

# Small Plan: Actionable Validator Dependency Error

## Scope

`validate_hook_gate_regression_tests()` runs `tests/test_hook_gates.py` with the current interpreter, but that file imports `pytest` at module load. Make the missing dependency a single clear validation error while keeping the hook gate check mandatory. Give CI an explicit `pytest` environment and audit the validator's other launched Python files for the same issue.

## Steps

- [ ] **1. Confirm the dependency boundary.** Inspect `scripts/validate_targets.py` subprocess calls and the imported modules of each launched Python file. Record any other direct-run test with an undeclared third-party import. The known reproduction is `uv run --no-project --isolated python -c 'import pytest'`, which raises `ModuleNotFoundError` on this host.
- [ ] **2. Give the hook gate check a clear failure.** Modify `scripts/validate_targets.py::validate_hook_gate_regression_tests(errors: list[str])` to detect unavailable `pytest` before spawning the test file and append one actionable error naming the devcontainer and `uv run --with pytest` route. Return from this check only after recording that error. Keep the existing direct-run test invocation and its nonzero result handling in the normal environment; do not turn the hook safety test into a warning or silent skip. Update the misleading docstring that claims the file has no `pytest` dependency.
- [ ] **3. Make CI's environment explicit and cover both paths.** Modify `.github/workflows/validate.yml` so its `Validate targets` command provisions `pytest` through `uv run --with pytest python scripts/validate_targets.py`; this preserves the mandatory test on hosted runners without relying on preinstalled packages. Add a focused regression in `tests/test_validate_targets.py` that simulates missing `pytest`, asserts one actionable error with no raw traceback, and confirms the hook test is not spawned. Retain or add a present-`pytest` case proving the hook test still runs and a nonzero result still fails validation. Fix any other analogous dependency found in step 1 at its shared root cause.

## Verification

```bash
uv run pytest tests/test_validate_targets.py -q --tb=short
uv run python scripts/validate_targets.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

- Run `uv run --no-project --isolated python scripts/validate_targets.py` with a fresh cache and inspect the nonzero result for one actionable dependency line. This host check can also report unrelated environment limits, so the focused regression is the required proof.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
