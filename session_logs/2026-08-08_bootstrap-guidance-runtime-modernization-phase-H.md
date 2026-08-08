# Session: Bootstrap guidance/runtime modernization — Phase H

**Date:** 2026-08-08
**Plan:** .claude/plans/2026-08-04_phase-H-memory-security-authority.md
**Status:** COMPLETED

## Goal

Define shared versus native memory authority and provide one authoritative
security threat model without changing user-owned client memory or consumer
state.

## Work Log

- Rechecked official Codex Memories, hooks, and security guidance first, then
  Claude memory, hooks, permissions, and security documentation.
- Defined `.claude/MEMORY.md` as curated, portable cross-target project memory;
  native client memories remain optional machine-local advisory scratch and
  are neither generated nor disabled.
- Documented promotion, sanitization, privacy, remote visibility, conflict, and
  manual semantic-merge rules. Sensitive material is excluded from both memory
  layers and belongs in approved protected-data systems.
- Added root `SECURITY.md` covering assets, trust boundaries, hostile inputs,
  hook trust, parsing limitations, protected paths, nested Git, credentials,
  accepted escapes, reporting criteria, and exclusions.
- Added exact-byte consumer MEMORY preservation tests for normal refresh and
  legacy migration, including non-text bytes and nested Git history.
- Added narrow threat-model heading/link validation and resolved all two-pass
  security/documentation/Ponytail findings.

## [LEARN] Entries

- [LEARN:security] Machine-local memory is not a secret vault; keep passwords,
  tokens, confidential data, and sensitive logs outside both native and shared
  memory.
- [LEARN:testing] Text-marker preservation checks do not prove byte identity;
  exercise binary content on disk and in migration history.

## Verification Results

```bash
uv run python scripts/generate_targets.py --all                 # PASS twice, deterministic
uv run pytest tests/ -q --tb=short                              # 95 passed
uv run python scripts/validate_targets.py                       # PASS
uv run mypy . --ignore-missing-imports --explicit-package-bases  # PASS, 17 files
uv run ruff check scripts/ tests/                               # PASS
uv run ruff format --check <changed Python files>               # PASS
git diff --check                                                # PASS
```

`check_runtime.py` continues to report the known stale installed dogfood
overlay; no runtime or trust state was changed in this source phase.

## Score: 100/100 — EXCELLENCE

- Findings: `.claude/quality_reports/findings-20260808T135223Z.json`
- Score: `.claude/quality_reports/score-20260808T135223Z.json`

## Open Questions / Next Steps

- Commit Phase H atomically and advance to Phase I native-client acceptance.
- Keep native client memory settings user-owned during Phase I probes.
