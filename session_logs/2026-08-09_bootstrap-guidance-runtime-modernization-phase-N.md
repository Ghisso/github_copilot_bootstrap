# Session: Bootstrap guidance/runtime modernization — Phase N

**Date:** 2026-08-09
**Plan:** .claude/plans/2026-08-04_phase-N-phase-extension-narrative.md
**Status:** COMPLETED

## Goal

Explain phases J–N in the big plan's narrative, and correct documentation that
still described Phase I native probes as unbuilt future work.

## Why This Phase Existed

Phases J–M were appended to the big plan's frontmatter and checklist but never
explained in prose. A reader could see four extra phases and not know why the
plan grew or what they found. Separately, nine documentation locations still
framed "Phase I" as the pending gate, and three repeated a claim that turned
out to be false.

## Work Log

- Added a `Phase Extensions (J–N)` section to the big plan: a per-phase table
  of why each was added and what it established, plus the three findings worth
  carrying forward — the score never moved across fourteen phases, model
  self-report is worthless for routing, and the MultiAgent V2 removal gate is
  still open.
- Made `docs/2026-08-08-codex-routing-compatibility.md` the single
  authoritative status home with a dated 2026-08-09 section: verified routing,
  what remains open, the inert `tool_namespace` key, and the probe's own
  `codex exec` limitation.
- Corrected the false claim in three files. `docs/architecture.md`,
  `docs/target-mapping.md`, and `README.md` all stated that spawn metadata is
  exposed "through the `agents` namespace". Codex 0.147.0 exposes
  `collaboration.*` and nothing under `agents.*`, so `tool_namespace` is inert.
- Retargeted nine stale "Phase I will..." references across `README.md`,
  `docs/architecture.md`, `docs/runtime-checks.md`, `docs/smoke-tests.md`, and
  `docs/target-mapping.md` to describe what is now known, deferring to the
  dated record rather than restating it.

## What Did Not Change

The shim's status. Routing was verified with `[features.multi_agent_v2]`
present; the shim-removed candidate has never been exercised on an interface
capable of spawning. One inert key is not grounds for removal.

## Verification Results

```bash
uv run python scripts/generate_targets.py --all                  # PASS twice
uv run python scripts/validate_targets.py                        # PASS
uv run pytest tests/ -q --tb=short                               # 123 passed
uv run mypy . --ignore-missing-imports --explicit-package-bases  # PASS, 19 files
uv run ruff check scripts/ tests/                                # PASS
uv run python scripts/validate_plan_frontmatter.py .claude/plans/*.md  # PASS
git diff --cached --check                                        # PASS
```

Post-edit greps confirm zero remaining `Phase I`-as-future-work references and
zero remaining "through the `agents` namespace" claims outside the dated
record.

## Score: 100/100 — EXCELLENCE

- Findings: `.claude/quality_reports/findings-20260808T172755Z.json`
- Score: `.claude/quality_reports/score-20260808T172755Z.json`

## [LEARN] Entries

- [LEARN:documentation] Appending phases to a plan's frontmatter does not
  update the plan. Context, Goals, and narrative describe the plan a reader
  actually reads; a checklist entry explains nothing.
- [LEARN:documentation] A wrong mechanism claim propagates. "Spawn metadata
  through the `agents` namespace" appeared in three files; single-homing status
  in the dated record and pointing at it prevents the next divergence.

## Open Questions / Next Steps

- Decide the dogfood refresh mechanism, then refresh and re-test the hooks
  after Codex quota resets (2026-08-15).
- Run the shim A/B on a persistent-thread interface to test removability.
- Consider driving `codex app-server` or `mcp-server` so the probe can measure
  the role matrix itself.
