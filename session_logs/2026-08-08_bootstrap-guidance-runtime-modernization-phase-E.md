# Session: Bootstrap guidance/runtime modernization — Phase E

**Date:** 2026-08-08
**Plan:** .claude/plans/2026-08-04_phase-E-codex-agent-self-containment.md
**Status:** COMPLETED

## Goal

Make every generated Codex custom agent receive its complete canonical role
contract without an extra Claude-native file read.

## Work Log

- Verified official Codex custom-agent documentation: project TOMLs require
  `name`, `description`, and `developer_instructions`; omitted MCP and skill
  configuration inherits from the parent.
- Embedded the transformed canonical shared prompt behind a short generated
  metadata header for all six Codex roles. Used safe TOML basic-string escaping
  and removed the runtime instruction to read `.claude/agents/<id>.md`.
- Added exact parsed-body parity, stable-delimiter, legacy-pointer, mutation,
  MCP inheritance, and Phase D routing regression checks.
- Updated Codex-first documentation. Current instruction bodies are 3,145–8,202
  bytes; no official limit is claimed and native delivery remains Phase I.
- Full verification and two-pass review passed with zero findings.

## [LEARN] Entries

- [LEARN:codex] Put the complete role contract on the documented
  `developer_instructions` authority surface instead of depending on a first
  tool read of another client's agent file.
- [LEARN:config] Parent inheritance is safer than repeated per-agent MCP/skill
  tables when every role needs the same trusted project configuration.

## Verification Results

```bash
uv run python scripts/generate_targets.py --all                 # PASS twice, deterministic
uv run pytest tests/test_validate_targets.py -q --tb=short     # 7 passed
uv run pytest tests/ -q --tb=short                              # 48 passed
uv run python scripts/validate_targets.py                       # PASS
uv run mypy . --ignore-missing-imports --explicit-package-bases  # PASS, 16 files
uv run ruff check scripts/ tests/                               # PASS
git diff --check                                                # PASS
```

Two unrelated baseline files remain outside Ruff formatting; the changed Phase
E files are formatted.

## Score: 100/100 — EXCELLENCE

- Findings: `.claude/quality_reports/findings-20260808T120113Z.json`
- Score: `.claude/quality_reports/score-20260808T120113Z.json`

## Open Questions / Next Steps

- Commit Phase E atomically and advance to Phase F hook-routing efficiency.
- Phase I must verify native instruction delivery and truncation behavior.
