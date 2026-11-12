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
- Coder (Steps 2-5) and documenter (Step 7) ran in parallel on disjoint files.
- Coder negative control (new tests, pin still 1.0.169): dispatcher tests 27 failed (server arguments, working folder from 3 of 4 start folders, launcher lookup from the root, `CONTEXT_MODE_DATA_DIR` cases, Node floor cases, old pin with correct secret, lost race); 2 passed as expected (inherited `CLAUDE_PROJECT_DIR` left alone; `mv` fails with the folder still present, today's failure path). Validator three-tool test failed on the missing `ctx_batch`/`ctx_resume`. Real 2.1.8 test failed at the self-check (`pinned-via-npx@1.0.169`).
- Coder changes: dispatcher pin 2.1.8, `MIN_NODE_VERSION="24.15.0"`, `cd "$REPO_ROOT"` in server mode and `--self-check`, `server --agent codex` (direct and `npx`), `CONTEXT_MODE_DATA_DIR` export, lost-race tolerance (folder gone: warn and continue; folder present: old failure path); Dockerfile `node:24.22.3-bookworm-slim`, `context-mode@2.1.8`, `--version` test; validator pin, image, message, blocked `ctx_batch`/`ctx_resume`. Carry-overs done: real-binary test accepts a tool without `annotations` (boolean-only when present); filter comments reworded to "Context Mode 1.x" (comments only). One Bash 3.2 lint (unguarded `${SERVER_ARGS[@]}`) fixed by inlining the arguments. Mutation check: removing the server-mode `cd` made the real test fail only once the test started from a nested `<repo>/.claude` repository, so the real test now does.
- Coder checks: focused three-file pytest 346 passed, 1 skipped; `-k cache` 6 passed; private binary equals the pin; real 2.1.8 server test 1 passed; both Docker slim-image items PASS; `grep -r -l -I -F '1.0.169' shared scripts tests` count 0; `validate_targets.py` exit 0; rest of the suite exit 0; `verify.py fast` PASS; mypy clean.
- Documenter: `README.md`, `docs/runtime-checks.md`, `docs/smoke-tests.md`, `shared/policies/tool-routing.instructions.md`; both `1.0.169` doc greps 0. Orchestrator checked its flagged claims against the dispatcher: quarantine name `<cache>.untrusted.<timestamp>.<pid>` (line 206), the lost-race warning (213), the `CONTEXT_MODE_DATA_DIR` export (234-237), the `required-node`/`observed-node` self-check lines (267, 271) all match.
- Step 6 (orchestrator): `generate_targets.py --all`, `install_bootstrap.py . --allow-self --local-only`; `check_runtime.py` all PASS except the expected WARN (global `context-mode` is 1.0.169, so the dispatcher uses the pinned `npx`). This repository's own Context Mode server now runs 2.1.8 through `npx` after a `/mcp` reconnect.
- Orchestrator (AI state): project-context pinned-versions paragraph and the dispatcher line now name 2.1.8, the Node floor, the image, `--agent codex`, and `CONTEXT_MODE_DATA_DIR`.

## [LEARN] Entries

- (filled at closeout)

## Verification

(filled at closeout)

## Open Questions / Next Steps

- Coder Steps 2-5, documenter Step 7, orchestrator Step 6, reviewer Step 8.
