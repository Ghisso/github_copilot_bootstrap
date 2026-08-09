---
name: 2026-08-09_phase-B-planner-reliability-calibration
type: small-plan
parent_plan: guidance-and-review-calibration
phase_index: 2
status: complete
closeout_session_log: .claude/session_logs/2026-08-09_guidance-and-review-calibration-phase-B.md
---

# Small Plan: 2026-08-09_phase-B-planner-reliability-calibration

## Scope

Calibrate Claude Code and Codex planners to `xhigh`, make planner delegation reuse curated evidence without repeated discovery, define reliable single-planner supervision, and record bounded native benchmark evidence without changing GitHub Copilot's model intent.

## Ownership

- `coder`: canonical planner/orchestrator configuration and prompts, validators, native-check code, tests, generation, and frozen benchmark harness/evidence support.
- `verifier`: generation, self-refresh, full verification, native compatibility checks, and frozen workload measurements.
- `reviewer`: `code`, `architecture`, `security`, `tests`, `documentation`, and `ponytail` profiles.
- `documenter`: README, architecture, smoke tests, native acceptance, dated compatibility record, and dated calibration evidence.

## Required Skills

- `ponytail` in `full` mode for code changes.
- `code-style` and `testing-patterns` where applicable.

## Steps

- [x] Change Claude Code and Codex planner effort from `max` to `xhigh`; preserve Claude `opus`, Codex `gpt-5.6-sol`, and GitHub Copilot `Claude Opus 4.6`.
- [x] Bound planner discovery by explicit artifacts, supplied evidence, approved decisions, constraints, and unresolved questions; prohibit repeated answered intake during bounded revisions.
- [x] Require orchestrator evidence packets, fresh/minimal scoped delegation, one active planner, pending-wait semantics, evidence-based health checks, regular user updates, and a provisional 30-minute interruption floor absent cancellation or terminal error.
- [x] Update validators and tests for configuration parity and the complete supervision contract.
- [x] Regenerate targets and refresh the dogfood overlay without changing the authoring root adapter hashes established in Phase A.
- [x] Run frozen micro-plan and bounded full-plan workloads on Claude Code and Codex; record timing, observable gaps, tool volume, unique files, checklist completeness, invented surfaces, duplicated discovery, and scope expansion.
- [x] Keep `max` only if two matched `xhigh` runs reproduce a material checklist failure and a matched `max` control resolves it; do not add a generic retry.
- [x] Verify Claude's resolved Opus accepts `xhigh`; if native execution rejects it, record exact evidence and fall back only Claude to `high`.
- [x] Update current documentation and add dated planner calibration evidence without rewriting historical observations.

## Verification

```bash
uv run pytest tests/test_validate_targets.py tests/test_check_native_clients.py -q --tb=short
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/install_bootstrap.py . --allow-self --local-only
uv run python scripts/check_runtime.py
```

## Acceptance Criteria

- [x] Canonical/generated Claude planner is `opus`/`xhigh`, or an evidence-backed Claude-only `high` fallback records native rejection.
- [x] Canonical/generated Codex planner is `gpt-5.6-sol`/`xhigh`; GitHub Copilot remains `Claude Opus 4.6`.
- [x] Planner/orchestrator prompts carry evidence-packet, bounded-discovery, one-planner, pending-wait, health-check, status-update, and interruption-floor contracts.
- [x] Both frozen workloads satisfy all mandatory planning checklist items without invented surfaces or duplicate discovery.
- [x] Measurements are dated observations, not generalized vendor claims.
- [x] No generic `max` retry, second planner, or unbenchmarked `high` change exists.
- [x] Authoring root hashes remain unchanged.

## Closeout Checklist

- [x] Verification passed
- [x] Review findings resolved
- [x] Score >= 90 persisted with branch/phase metadata
- [x] Documentation updated
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
