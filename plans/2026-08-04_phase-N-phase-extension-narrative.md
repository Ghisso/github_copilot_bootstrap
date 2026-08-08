---
name: 2026-08-04_phase-N-phase-extension-narrative
type: small-plan
parent_plan: bootstrap-guidance-runtime-modernization
phase_index: 14
status: complete
closeout_session_log: .claude/session_logs/2026-08-09_bootstrap-guidance-runtime-modernization-phase-N.md
---

# Small Plan: 2026-08-04_phase-N-phase-extension-narrative

## Scope

Phases J–M were appended to the big plan's frontmatter and checklist but never
explained in its narrative, and the documentation set still describes Phase I
as the pending native-probe gate. One statement is now provably false.

### 1. The big plan does not explain why it grew

`Context`, `Goals`, and `Design Overview` describe an A–I plan. Phases J–M
appear only as list entries. A reader cannot tell why four phases were added or
what they established.

### 2. Documentation still points at "Phase I" as the open gate

Nine locations across `README.md`, `docs/architecture.md`,
`docs/runtime-checks.md`, `docs/smoke-tests.md`, `docs/target-mapping.md`, and
`docs/2026-08-08-codex-routing-compatibility.md` describe Phase I native probes
as future work. The probes exist, have run, and their outcome is known.

### 3. A false claim about the shim

`docs/architecture.md` states the config "exposes MultiAgent V2 spawn metadata
through the `agents` namespace so named model/effort profiles are selectable."
Measured against Codex 0.147.0, the collaboration tools are exposed as
`collaboration.spawn_agent`, `followup_task`, `send_message`,
`interrupt_agent`, `list_agents`, `wait_agent`. Nothing is namespaced
`agents.*`, so `tool_namespace = "agents"` has no observable effect.

Correct routing was nonetheless verified with the shim present, so this
corrects the *stated mechanism*, not the shim's status.

## Approach

The dated compatibility record is the single authoritative home for shim and
probe status. Update it fully; elsewhere correct only what is wrong or stale
and point at that record rather than restating it.

## Steps

- [x] Add a `Phase Extensions (J–M)` section to the big plan explaining why
  each phase was added and what it concluded.
- [x] Update `docs/2026-08-08-codex-routing-compatibility.md` with the current
  status: probes built (I), fixed (J, K), spawn limits found (L), matrix
  verified and record corrected (M).
- [x] Correct the `agents` namespace claim in `docs/architecture.md`.
- [x] Retarget stale "Phase I will..." references so they describe what is now
  known and defer to the dated record.
- [x] Do not restate the dated record's content in multiple files.
- [x] Do not change the shim's status: routing was verified with it present.

## Verification

```bash
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py .claude/plans/*.md
```

## Acceptance Criteria

- The big plan explains phases J–N in prose, not just as list entries.
- No document claims spawn metadata is exposed through an `agents` namespace.
- No document describes the native probes as unbuilt future work.
- Shim and probe status live in one authoritative place.

## Closeout Checklist

- [x] Verification passed
- [x] Review findings resolved
- [x] Score >= 90 persisted with branch/phase metadata
- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
