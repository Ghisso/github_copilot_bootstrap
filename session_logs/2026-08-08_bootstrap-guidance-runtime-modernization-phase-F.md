# Session: Bootstrap guidance/runtime modernization — Phase F

**Date:** 2026-08-08
**Plan:** .claude/plans/2026-08-04_phase-F-hook-routing-efficiency.md
**Status:** COMPLETED

## Goal

Reduce irrelevant Codex and Claude hook fan-out while preserving fail-closed
guardrails, lifecycle durability, and nested code-mode protection.

## Work Log

- Rechecked current official Codex and Claude hook documentation and designed
  target-native native-edit, Bash, and best-effort observability matcher lanes.
- Added one ordered Bash guard wrapper and retained the existing Stop and
  SessionEnd lifecycle contracts.
- Replaced broad token scanning with per-segment mutation-target classification
  that permits proven read-only inspection and fails closed for ambiguous or
  opaque protected-file mutations without depending on `uv`.
- Added protected-source exfiltration defenses, complete protected-literal
  handling, wrapper/interpreter/newline coverage, and exact handler/child-order
  acceptance gates.
- Updated Codex/Claude-first architecture, runtime, smoke-test, and target
  mapping documentation.
- Completed repeated security remediation and two-pass review with zero
  surviving findings.

## [LEARN] Entries

- [LEARN:security] Treat opaque commands containing any protected literal as a
  fail-closed decision unless the operation is proven read-only.
- [LEARN:testing] Validate ordered wrappers structurally and with isolated
  executable fixtures so short-circuit and malformed-output behavior cannot
  regress behind production-script side effects.

## Verification Results

```bash
uv run python scripts/generate_targets.py --all                 # PASS twice, deterministic
uv run pytest tests/ -q --tb=short                              # 83 passed during scoring
uv run python scripts/validate_targets.py                       # PASS
uv run mypy . --ignore-missing-imports --explicit-package-bases  # PASS, 17 files
uv run ruff check scripts/ tests/                               # PASS
uv run ruff format --check <changed Python files>               # PASS
bash -n shared/hooks/scripts/protect-files.sh shared/hooks/scripts/pretool-bash-guard.sh  # PASS
git diff --check                                                # PASS
```

`check_runtime.py` reports stale installed runtime copies; generated source is
valid and deterministic, and no user runtime or trust state was mutated during
this source phase.

## Score: 100/100 — EXCELLENCE

- Findings: `.claude/quality_reports/findings-20260808T124537Z.json`
- Score: `.claude/quality_reports/score-20260808T124537Z.json`

## Open Questions / Next Steps

- Commit Phase F atomically and advance to Phase G task-lane contract.
- Run the real native nested-code-mode execution probe in Phase I.
