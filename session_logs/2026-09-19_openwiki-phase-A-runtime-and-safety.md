# OpenWiki Phase A: Runtime and Safety Boundary

**Status:** IN PROGRESS
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
- Round 3 result: 3 CRITICAL and 4 MAJOR findings.
  Exact results: `.claude/quality_reports/review-results-2026-09-19_phase-A-openwiki-round3.json`.
- Round 4 result: FAIL on 1 new MAJOR, plus 1 MINOR needing disposition.
  Exact results: `.claude/quality_reports/review-results-2026-09-19_phase-A-openwiki-round4.json`.
- Ponytail result across both rounds: no simplification finding survived. Round 4 judged the
  growth from roughly 460 to 766 lines proportionate to the round-3 CRITICAL fixes, with no
  speculative interface, reinvented standard library, or dead flexibility.

### Round 3 finding disposition (all seven accounted for)

| # | Finding | Disposition |
| --- | --- | --- |
| 1 | Nested repository collapses to one directory fingerprint | Resolved. `_walk_ignored_directory` expands any entry ending in `/`. Verified empirically that this is the exclusive signal for a non-recursed nested repository. |
| 2 | Adapter restoration can delete concurrent edits | Resolved. Restoration authenticates through retained file descriptors, never unlinks a present file, and performs no write at all when content already matches. |
| 3 | Symlink walk is check-then-use | Scope changed by user decision, not re-raised. Phase A detects and fails closed; operating-system-enforced isolation moved to Phase E. Detection verified to match the documented claim. |
| 4 | Control-plane allowlist omits the provenance secret | Resolved. |
| 5 | Version probe before the lock and outside the telemetry default | Resolved. Lock acquired first; both probes share the child environment. |
| 6 | Post-run failures drop restoration errors | Resolved. All nine post-child returns carry restoration evidence. |
| 7 | Credential validator heuristic too narrow | Resolved. Closed six-key allowlist asserted as a subset relation. |

### Round 4 MINOR disposition

`_run()` is roughly 240 lines covering lock, preflight, snapshot, launch, restore, and compare.
**Accepted as-is.** Reason: the ordering of those stages is itself the safety property. Splitting
them into helpers would move that ordering into call-site convention, where a later edit could
reorder it without an obvious tell. The reviewer raised the same counter-argument and did not
assert the finding should block.

## Completed Work

- Added the pinned OpenWiki runtime, optional Mermaid validators, and host config mount.
- Added the bootstrap-owned runner, generator/installer wiring, ignore entry, validator coverage, and deterministic fake-command tests.
- Completed two review-driven fix loops for lock ordering, dirty-path fingerprints, symlink checks, sentinel restoration, nested-root resolution, ignored-path checks, and structured failures.

## Remaining Work

- Resolve every finding in the saved round 3 review result.
- Re-run focused tests, generation, validation, runtime consistency, and fast verification.
- Re-run the full five-profile review until no CRITICAL or MAJOR finding remains.
- Complete normal Phase A closeout, findings persistence, phase/closeout receipts, commit, and push.

## Resume (2026-09-19)

Resumed on the same implementation branch. Plan restored to `in-progress`; no new phase created.

### Scope decision taken on resume

Round 3 CRITICAL finding 3 (the OpenWiki symlink walk is check-then-use) has no in-process fix:
Python cannot supervise another program's file writes. The user chose **detect and refuse now,
prevent later**:

- Phase A re-walks `openwiki/` after the child exits and fails closed, naming every symlink and
  every path that moved. The root adapters are restored from pre-run bytes regardless. Nothing
  is committed on a failed refresh.
- Operating-system-enforced isolation of the child process is recorded as a new
  `2026-09-19_phase-E-openwiki-child-process-sandbox`, added to the big plan's phase list,
  step summary, and risk table.
- Accepted residual limit, documented in the runner docstring: a write landing outside the
  repository entirely is not detected until Phase E.

### Original resume point (from the pause)

## Resume Point

Resume Phase A on the same implementation branch. Restore this plan to `in-progress`, then return the saved round 3 findings to the existing coder context if available. Start with the three CRITICAL runner findings before the four MAJOR findings. Do not create a new phase or treat the current verification as final after code changes.
