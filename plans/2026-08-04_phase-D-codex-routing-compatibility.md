---
name: 2026-08-04_phase-D-codex-routing-compatibility
type: small-plan
parent_plan: bootstrap-guidance-runtime-modernization
phase_index: 4
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-08-04_phase-D-codex-routing-compatibility

## Scope

Modernize documented Codex agent configuration while retaining the proven
MultiAgent V2 routing shim. Removal of undocumented keys is explicitly out of
scope until native probes prove exact role routing on the supported version
matrix.

## Evidence And Decision

- `82e9fbe` introduced the shim with model tiering.
- `.claude/session_logs/2026-07-18_codex-gpt-5.6-model-tiering.md` records the
  initial all-Sol/high failure and successful six-agent probe after the shim.
- `.claude/MEMORY.md` records the routing invariant.
- `9310cbb` unpinned only the interactive root; custom-agent overrides remain.
- Local Codex `0.146.0-alpha.9.2` accepts the current config under strict
  config diagnosis and reports `multi_agent` stable/on while
  `multi_agent_v2` is stable/off. This proves parsing, not named-agent spawn
  behavior, and therefore is not evidence that the shim can be removed.
- Current validation is structural only; native routing is not automated.

**Decision:** retain `hide_spawn_agent_metadata = false` and
`tool_namespace = "agents"`. Treat `max_depth = 1` the same way until a probe
and minimum-version decision demonstrate safe removal. Modernize only the
documented concurrency alias immediately. Do not select config by the
installer machine's Codex version: collaborators may open the same project
with different supported clients.

## Ownership

- `coder`: generator/config comments, compatibility manifest, static tests.
- `verifier`: version matrix and exact six-role routing probe contract.
- `reviewer`: `code`, `architecture`, `config`, `tests`, `documentation`,
  `ponytail`.
- `documenter`: compatibility rationale and upgrade policy.

## Required Skills

- `ponytail` (`full`), `debug-investigator`, `testing-patterns`, `run-tests`,
  `documentation`, `ponytail-review`.

## Steps

- [ ] Replace `agents.max_threads` with
  `agents.max_concurrent_threads_per_session`; emit `agents.enabled = true`
  only if explicit enabling is required by the supported-version contract.
- [ ] Retain the MultiAgent V2 block verbatim and move its historical rationale
  into a dated compatibility record referenced by generator comments and docs.
- [ ] Record a minimum/current Codex version matrix. Classify each non-current
  key as required shim, legacy alias, or removal candidate.
- [ ] Update structural validation to assert the exact six custom-agent
  model/effort pairs, unpinned root, coder escalation, and required routing shim.
- [ ] Define a removal gate: two supported native versions, trusted project,
  no root CLI model override, all six named agents spawned, exact model/effort
  observed, and repeated success with the candidate key absent.
- [ ] Do not auto-edit user trust or infer success from a model's prose alone;
  use client metadata/tool events where available.

## Verification

```bash
uv run pytest tests/test_validate_targets.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```

Run the Phase-I native Codex probe before any future shim removal.

## Acceptance Criteria

- Verifier and documenter still spawn at Luna/low and Luna/medium.
- Other named roles retain their exact Sol/Terra model and effort.
- The interactive root remains unpinned.
- No undocumented compatibility key is removed merely because docs omit it.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
