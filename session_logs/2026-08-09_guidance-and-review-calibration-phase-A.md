# Session: Guidance and review calibration Phase A

**Date:** 2026-08-09
**Plan:** `.claude/plans/2026-08-09_phase-A-consumer-neutral-root-guidance.md`
**Status:** COMPLETED

## Goal

Make generated root guidance consumer-neutral while preserving this repository's tracked authoring root adapters through generation, self-refresh, and restoration.

## Work Log

- Implemented consumer-neutral generated root titles, introductions, and ownership language.
- Declared both root `AGENTS.md` and `CLAUDE.md` as tracked authoring adapters and force-tracked byte-identical `CLAUDE.md`.
- Added exact forbidden-phrase, installer-refresh, and real restoration-script regressions.
- Resolved the review's restoration-coverage MAJOR finding and repeated verification and review to a clean result.
- Updated README and target-mapping documentation.

## [LEARN] Entries

- [LEARN:testing] Authoring-adapter preservation needs separate regressions for installer refresh and state restoration; one path does not prove the other.

## Verification Results

```text
Focused tests: 66 passed
Full tests: 140 passed
mypy: success, 19 files
ruff check: passed
ruff format --check: passed
generate_targets.py --all: passed
validate_targets.py: passed
install_bootstrap.py . --allow-self --local-only: passed
check_runtime.py: passed
Root and restoration hashes: exact expected values
Findings: 0 critical, 0 major, 0 minor; Ponytail clean
Score report: .claude/quality_reports/score-20260809T041922Z-phase-A.json
Findings report: .claude/quality_reports/findings-20260809T041922Z-phase-A.json
```

## Score: 100/100

## Open Questions / Next Steps

- Continue with Phase B planner reliability and effort calibration.
