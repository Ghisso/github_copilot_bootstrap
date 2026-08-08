---
name: 2026-08-04_phase-G-task-lane-contract
type: small-plan
parent_plan: bootstrap-guidance-runtime-modernization
phase_index: 7
status: complete
closeout_session_log: .claude/session_logs/2026-08-08_bootstrap-guidance-runtime-modernization-phase-G.md
---

# Small Plan: 2026-08-04_phase-G-task-lane-contract

## Scope

Reconcile “plan first for non-trivial work,” “orchestrator only for
non-trivial work,” and blanket lifecycle language. Define a lightweight lane
without creating a broad commit-gate or safety bypass.

## Ownership

- `coder`: policy/agent contract and validator changes.
- `verifier`: classification and gate-behavior fixtures.
- `reviewer`: `architecture`, `security`, `tests`, `documentation`, `ponytail`.
- `documenter`: contributor examples and decision table.

## Required Skills

- `ponytail` (`full`), `plan-decomposition`, `testing-patterns`,
  `documentation`, `ponytail-review`.

## Steps

- [x] Define an authoritative task-size decision table: read-only/reporting,
  lightweight edit, standard implementation, and control-plane/high-risk.
- [x] Keep the orchestrator exclusive to non-trivial implementation; allow the
  main agent to handle explicit small edits with focused verification when no
  commit/PR closeout is requested.
- [x] Require all commit-bound implementation work to produce the lifecycle
  artifacts expected by existing Git gates. Do not add an implicit command-
  string bypass or weaken control-plane classification.
- [x] State that control-plane, security, dependency, migration, multi-file,
  or user-data changes always use the full orchestrated lane.
- [x] Align root guidance, workspace/workflow policies, orchestrator prompt,
  planner prompt, skills, templates, and docs to the same decision table.
- [x] Add positive/negative fixtures for typo/docs-only, single-file behavior,
  dependency, hook, config, and commit-request cases.

## Verification

```bash
uv run pytest tests/test_hook_gates.py tests/test_validate_targets.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
```

## Acceptance Criteria

- Clear small tasks avoid unnecessary orchestration when no closeout is requested.
- Commit/PR and control-plane gates are unchanged.
- No authoritative instruction contradicts the task-size decision table.

## Closeout Checklist

- [x] Verification passed
- [x] Review findings resolved
- [x] Score >= 90 persisted with branch/phase metadata
- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
