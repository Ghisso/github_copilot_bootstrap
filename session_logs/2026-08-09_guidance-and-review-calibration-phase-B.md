# Session: Guidance and review calibration Phase B

**Date:** 2026-08-09
**Plan:** `.claude/plans/2026-08-09_phase-B-planner-reliability-calibration.md`
**Status:** COMPLETED

## Goal

Calibrate planner effort and supervision while recording bounded deterministic and native evidence.

## Work Log

- Implemented Claude `opus`/`xhigh` and Codex `gpt-5.6-sol`/`xhigh`; preserved GitHub Copilot `Claude Opus 4.6`.
- Added evidence-packet, bounded-discovery, conditional-interview, single-planner, pending-wait, health, update-cadence, interruption-floor, and measured-exception contracts.
- Resolved one architecture MAJOR and one Ponytail MINOR finding; repeated verification and review to clean.
- Deterministic verification passes 144 tests plus typing, linting, formatting, generation, validation, self-refresh, runtime, and root-hash checks.
- Updated required documentation and added the dated calibration record.
- Added safe marker-owned per-invocation runtime isolation and strict aggregate-only frozen planner workload evidence.
- Codex 0.147.0 Sol/xhigh and Claude 2.1.226 Opus/xhigh passed both frozen workloads with exact artifacts, 4/4 checklists, and zero invented, duplicate, or expanded scope.
- Hardened substantive acceptance, symlink-safe cleanup, temporary isolation, and native command boundaries after adversarial and real-client findings.

## [LEARN] Entries

- [LEARN:security] Native acceptance needs explicit human authorization, marker-owned writable runtime state, read-only generated inputs, isolated temporary state, and aggregate-only evidence; static parity cannot replace a real run.
- [LEARN:testing] A schema-valid model response is not a passing workload. Enforce complete checklists, exact artifact allowlists, and zero invented, duplicate, or expanded scope.

## Verification Results

```text
Focused tests: 71 passed
Full tests: 155 passed
mypy: success, 19 files
ruff check / format --check: passed
generation / validation / self-refresh / runtime: passed
root adapter hashes: unchanged
review: clean after adversarial fix loops
native Codex and Claude micro/full workloads: PASS
```

## Score: 100/100

## Open Questions / Next Steps

- Continue with Phase C human-facing writing guidance.
