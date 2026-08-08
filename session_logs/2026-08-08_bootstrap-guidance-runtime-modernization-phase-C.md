# Session: Bootstrap guidance/runtime modernization — Phase C

**Date:** 2026-08-08
**Plan:** .claude/plans/2026-08-04_phase-C-scoped-policy-adapters.md
**Status:** COMPLETED

## Goal

Single-home policy applicability metadata and generate native scoped adapters,
with Codex and Claude as the primary clients and Copilot as secondary
compatibility.

## Work Log

- Researched current official Codex and Claude documentation before finalizing
  the design. Codex uses hierarchical `AGENTS.md` discovery with a 32 KiB
  combined default cap; Claude uses `.claude/rules/*.md` with `paths` metadata.
- Replaced source Copilot `applyTo` metadata and implicit always-on behavior
  with one validated target-neutral applicability schema across all policies.
- Generated native Claude conditional rules, retained the canonical installed
  policy library, and derived secondary Copilot metadata from the same source.
- Kept Codex docs-faithful: no fabricated glob rules and no speculative nested
  `AGENTS.md` without stable directory ownership; relevant skills are the
  conditional fallback.
- Updated architecture, mapping, smoke-test, and README guidance before score.
  Final two-pass review returned zero findings across code, architecture,
  security, tests, documentation, and Ponytail.

## [LEARN] Entries

- [LEARN:architecture] Portable policy authoring requires neutral metadata and
  target-native projections; do not force one client's scoping primitive onto
  another client that lacks it.
- [LEARN:documentation] Structural adapter parity is not native-client loading
  proof; authenticated client probes remain Phase I work.

## Verification Results

```bash
uv run python scripts/generate_targets.py --all                 # PASS
uv run pytest tests/test_validate_targets.py -q --tb=short     # 5 passed
uv run pytest tests/ -q --tb=short                              # 46 passed
uv run python scripts/validate_targets.py                       # PASS
uv run mypy scripts/ --ignore-missing-imports --explicit-package-bases  # PASS
uv run ruff check scripts/ tests/                               # PASS
git diff --check                                                # PASS
```

Deterministic regeneration passed. The two unchanged Ruff-format findings and
the script-package import probe limitation predate Phase C and are not current
diff findings.

## Score: 100/100 — EXCELLENCE

- Findings: `.claude/quality_reports/findings-20260808T110620Z.json`
- Score: `.claude/quality_reports/score-20260808T110620Z.json`

## Open Questions / Next Steps

- Commit Phase C atomically and advance to Phase D Codex routing compatibility.
- Keep real Codex/Claude client discovery probes in Phase I.
