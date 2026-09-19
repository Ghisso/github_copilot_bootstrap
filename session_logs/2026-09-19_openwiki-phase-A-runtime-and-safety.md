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

Not run yet.

## Open Questions and Next Steps

- Implement all Phase A steps.
- Run focused and fast verification.
- Complete high-risk review and closeout.

