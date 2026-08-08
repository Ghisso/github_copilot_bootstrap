# Session: Bootstrap guidance/runtime modernization — Phase D

**Date:** 2026-08-08
**Plan:** .claude/plans/2026-08-04_phase-D-codex-routing-compatibility.md
**Status:** COMPLETED

## Goal

Modernize documented Codex concurrency configuration while preserving the
runtime-proven routing shim, unpinned root, and exact six-role contract.

## Work Log

- Verified current official Codex configuration and subagent documentation.
  The canonical key is `agents.max_concurrent_threads_per_session`;
  `max_threads` is a legacy alias and `agents.enabled` defaults to true.
- Updated generated consumer config to the canonical key while retaining
  `max_depth = 1` and both MultiAgent V2 shim fields. The protected root
  `.codex/config.toml` remains intentionally shim-only.
- Added independent literal validation for all six model/effort pairs, coder
  Sol/xhigh escalation, root unpinning, and forbidden legacy/redundant keys.
- Recorded historical, parse-only, documentation, and future native evidence
  separately. Added independent routing-shim and nesting-limit removal gates.
- Final review found one documentation major; the independent `max_depth`
  child-to-grandchild gate resolved it. Focused re-review passed.
- Initial score exposed one repository-wide mypy fixture error missed by scoped
  verification. The typed fixture fix passed full mypy and focused re-review;
  the fresh persisted score is 100.

## [LEARN] Entries

- [LEARN:codex] Documentation and parsing evidence cannot retire a shim whose
  necessity was established by observed runtime routing.
- [LEARN:testing] Six-role routing and nesting depth require separate native
  removal probes with machine-readable evidence.

## Verification Results

```bash
uv run python scripts/generate_targets.py --all                 # PASS twice, deterministic
uv run pytest tests/test_validate_targets.py -q --tb=short     # 6 passed
uv run pytest tests/ -q --tb=short                              # 47 passed
uv run python scripts/validate_targets.py                       # PASS
uv run mypy . --ignore-missing-imports --explicit-package-bases  # PASS, 16 files
uv run ruff check scripts/ tests/                               # PASS
git diff --check                                                # PASS
```

The two unchanged Ruff-format findings remain pre-existing and outside the
Phase D diff.

## Score: 100/100 — EXCELLENCE

- Findings: `.claude/quality_reports/findings-20260808T113724Z.json`
- Score: `.claude/quality_reports/score-20260808T113724Z.json`

## Open Questions / Next Steps

- Commit Phase D atomically and advance to Phase E Codex agent
  self-containment.
- Execute native routing and nesting removal probes only in Phase I.
