# OpenWiki Phase A: Runtime and Safety Boundary

**Status:** PAUSED
**Plan:** `.claude/plans/2026-09-19_phase-A-openwiki-runtime-and-safety-boundary.md`

## Goal

Implement the approved Phase A runtime, wrapper, installation, ignore, and deterministic safety-test contract for OpenWiki.

## Approach

- Keep OpenWiki behind one bootstrap-owned runner.
- Pin the runtime and optional Mermaid validators.
- Preserve user-owned root adapters and workflow files byte-for-byte.
- Restrict new mutations to `openwiki/**` and leave resumable run state on disk but ignored.
- Use fake executables for deterministic tests; do not make a provider or model request.

## Progress

- Pre-flight confirmed a clean outer `dev` branch and clean nested `ai-state` branch.
- Created `2026-09-19_openwiki-knowledge-layer-integration_implementation`.
- Branch hooks activated Phase A and updated the big-plan state.

## Verification

- Focused runner and installer tests: 31 passed.
- `scripts/generate_targets.py --all`: passed.
- `scripts/validate_targets.py`: passed.
- `scripts/check_runtime.py`: passed after local-only self-install.
- `.claude/scripts/verify.py fast --format json`: PASS.
- `git diff --check`: passed.
- Devcontainer Node/OpenWiki smoke build: not run because no build environment was used.

## Review

- Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`.
- Round 3 result: 3 CRITICAL and 4 MAJOR findings remain.
- Exact results: `.claude/quality_reports/review-results-2026-09-19_phase-A-openwiki-round3.json`.
- Ponytail result: no separate simplification finding survived.

## Completed Work

- Added the pinned OpenWiki runtime, optional Mermaid validators, and host config mount.
- Added the bootstrap-owned runner, generator/installer wiring, ignore entry, validator coverage, and deterministic fake-command tests.
- Completed two review-driven fix loops for lock ordering, dirty-path fingerprints, symlink checks, sentinel restoration, nested-root resolution, ignored-path checks, and structured failures.

## Remaining Work

- Resolve every finding in the saved round 3 review result.
- Re-run focused tests, generation, validation, runtime consistency, and fast verification.
- Re-run the full five-profile review until no CRITICAL or MAJOR finding remains.
- Complete normal Phase A closeout, findings persistence, phase/closeout receipts, commit, and push.

## Resume Point

Resume Phase A on the same implementation branch. Restore this plan to `in-progress`, then return the saved round 3 findings to the existing coder context if available. Start with the three CRITICAL runner findings before the four MAJOR findings. Do not create a new phase or treat the current verification as final after code changes.
