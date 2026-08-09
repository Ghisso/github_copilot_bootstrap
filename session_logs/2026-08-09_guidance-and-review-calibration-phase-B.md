# Session: Guidance and review calibration Phase B

**Date:** 2026-08-09
**Plan:** `.claude/plans/2026-08-09_phase-B-planner-reliability-calibration.md`
**Status:** IN-PROGRESS

## Goal

Calibrate planner effort and supervision while recording bounded deterministic and native evidence.

## Work Log

- Implemented Claude `opus`/`xhigh` and Codex `gpt-5.6-sol`/`xhigh`; preserved GitHub Copilot `Claude Opus 4.6`.
- Added evidence-packet, bounded-discovery, conditional-interview, single-planner, pending-wait, health, update-cadence, interruption-floor, and measured-exception contracts.
- Resolved one architecture MAJOR and one Ponytail MINOR finding; repeated verification and review to clean.
- Deterministic verification passes 144 tests plus typing, linting, formatting, generation, validation, self-refresh, runtime, and root-hash checks.
- Updated required documentation and added the dated calibration record.
- Prepared `/tmp/phase-b-native-client-probe`; Codex 0.147.0 and Claude 2.1.226 are installed and authenticated.

## [LEARN] Entries

- [LEARN:security] Native acceptance evidence must remain unexercised when the dedicated workspace has not received explicit human trust; static parity or agent-authored prose cannot replace that boundary.

## Verification Results

```text
Focused tests: 60 passed
Full tests: 144 passed
mypy: success, 19 files
ruff check / format --check: passed
generation / validation / self-refresh / runtime: passed
root adapter hashes: unchanged
review: clean after fix loop
native workloads and Claude Opus xhigh acceptance: UNEXERCISED/WARN
```

## Score: pending final native evidence

## Open Questions / Next Steps

- Human operator must inspect and trust `/tmp/phase-b-native-client-probe` in Codex and Claude without delegating trust approval to the agent.
- After trust, run the frozen micro/full workloads and record the required dated measurements, then finish score, closeout, and the atomic Phase B commit.
