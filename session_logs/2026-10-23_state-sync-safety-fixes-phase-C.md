# Session: Restorer symlink checks and devcontainer mount folders

**Date:** 2026-10-23
**Plan:** `.claude/plans/2026-10-23_phase-C-restorer-and-devcontainer-hardening.md`
**Status:** IN-PROGRESS

## Goal

Make `restore-root-adapters.sh` refuse a symlinked `.claude` or `.claude/bootstrap-root` (defense in depth), and have the generated `devcontainer.json` create both bind-mount source folders on the host before the container starts.

## Work Log

- Phase B committed as `cedb3b0` and pushed; the post-commit hook advanced `current_phase` to this phase.
- This repository's own `.devcontainer/` is untracked (`.git/info/exclude`) and byte-identical to the generated copy, so the overlay refresh updates it without touching the outer diff.

## [LEARN] Entries

## Verification

## Open Questions / Next Steps

- Implement steps 1-3 (coder), then documentation (documenter), then review.
