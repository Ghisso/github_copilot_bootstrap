# Session: Context Mode 2.1.8 switch (migration Phase B)

**Date:** 2026-11-12
**Plan:** `.claude/plans/2026-11-12_phase-B-context-mode-2x-switch.md`
**Status:** IN-PROGRESS

## Goal

Move the kit from Context Mode 1.0.169 to 2.1.8 and the devcontainer's Node.js image to `node:24.22.3-bookworm-slim`. The dispatcher pins 2.1.8, refuses Node.js older than 24.15.0 in server mode and `--self-check`, starts `context-mode server --agent codex` from the outer repository root with `CONTEXT_MODE_DATA_DIR` set to the guarded root and no `CLAUDE_PROJECT_DIR`, and tolerates a lost quarantine race. Docs get 2.x behavior, a new pin-bump procedure, and a rollback note.

## Work Log

- Phase A committed as `51d89b9` and pushed (`origin/context-mode-2x-migration_implementation`, new upstream). The post-commit hook set `current_phase` to this phase and set it `in-progress`.
- Material-impact check before this phase (Plan-First Protocol): Phase A's round-2 review left two Phase B carry-overs and one nit. (1) `test_real_upstream_server_surface_is_filtered` requires an `annotations` key on every tool, but 2.1.8's `ctx_index` has none (spike S2), so it must accept "key absent, or every value boolean". (2) Filter comments at lines 6 and 96 name `1.0.169` and would fail this phase's `grep -r -l -I -F '1.0.169' shared scripts tests` item; reword them to "Context Mode 1.x" (comment-only; the filter's code stays unchanged, as Step 4 says). (3) Nit, not taken: `booleanAnnotations` returns `{}` for an object with no boolean entries. These are mechanical and change no design, so no planner run; the orchestrator folded them into the coder brief.
- Step 1 (orchestrator): `npm install -g --prefix "$HOME/.cache/context-mode-pin" --ignore-scripts "context-mode@2.1.8"` added 1 package; `$HOME/.cache/context-mode-pin/bin/context-mode --version` prints `2.1.8`.

## [LEARN] Entries

- (filled at closeout)

## Verification

(filled at closeout)

## Open Questions / Next Steps

- Coder Steps 2-5, documenter Step 7, orchestrator Step 6, reviewer Step 8.
