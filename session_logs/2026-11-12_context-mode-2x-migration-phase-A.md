# Session: Context Mode MCP-only surface on 1.0.169 (migration Phase A)

**Date:** 2026-11-12
**Plan:** `.claude/plans/2026-11-12_phase-A-context-mode-mcp-only-surface.md`
**Status:** IN-PROGRESS

## Goal

While still on Context Mode 1.0.169, give the kit the surface it keeps under 2.x: no Context Mode hooks on any client (a legacy hook call exits 0 silently), three tools (`ctx_index`, `ctx_search`, `ctx_stats`), a filtered `initialize` with kit descriptions and no upstream `instructions`, a name-only identity gate, files-only `ctx_index` with a new `FILTER_CONTRACT`, and no Antigravity Context Mode entry. MCP adapters keep today's command.

## Work Log

- Pre-flight (onboarding refresh, same session): `dev` at `9be6955`, equal to `origin/dev`; `check_runtime.py` 20 lines PASS; `uv run pytest tests/ -q` 5014 passed, 1 skipped. Cleanup at the user's request: 12 local branches already merged into `dev` deleted; the push gate refused `git push origin --delete` of 4 merged remote branches from `dev` (left for the user); empty folder `.claude/skills/antigravity-native-acceptance-isolation/` removed.
- Decision change: the user said "start the Context Mode migration now, don't want to wait. we can bump it up later". Recorded in the big plan's Approval record: decision 1 becomes "Start now", settle check waived, pin = newest stable at spike time; decisions 2 to 7 unchanged.
- Pre-branch spike (evidence-only `coder`, scratch folder): report `.claude/explorations/2026-11-12_context-mode-2x-recheck/REPORT.md`. Candidate 2.1.8, image `node:24.22.3-bookworm-slim`, identity `context-mode server --agent codex` from the outer repository root, server name `context-mode` for 1.0.169 and 2.1.8. No stop condition. S3: folder indexing has no bound and follows symlinks inside the repository's parent folder, so the files-only fallback is required.
- Planner revision (one run): 58 edits across the big plan and Phases A and B, applied from the planner's tested edit list; `validate_plan_frontmatter.py` exit 0 on the three plans. Files-only `ctx_index` moved from Phase B to Phase A (a filter-only change that works on 1.0.169; Phase A already rewrites every `ctx_index` description). Start Gate's settle line replaced by: 2.1.8 is published, not deprecated, and Phase B uses that pin. The planner also moved `test_hostile_remote_cache_with_forged_marker_is_quarantined_not_trusted` to `server` mode in Phase A, because hook calls become no-ops.
- Start Gate (run from `dev`, 2026-11-12):

```text
PASS  test "$(npm view context-mode@2.1.8 version)" = "2.1.8"
PASS  test -z "$(npm view context-mode@2.1.8 deprecated)"
PASS  grep -q -F 'PINNED_CONTEXT_MODE_VERSION="2.1.8"' .claude/plans/2026-11-12_phase-B-context-mode-2x-switch.md
PASS  node -e 'const[a,b]=process.versions.node.split(".").map(Number);process.exit(a>24||(a===24&&b>=15)?0:1)'
PASS  test "$(git rev-parse --abbrev-ref HEAD)" = "dev"
PASS  test -z "$(git status --porcelain)"
PASS  git show dev:README.md | grep -q -F 'The fourth generated target, Google Antigravity'
PASS  git show dev:openwiki/architecture/hooks-and-guardrails.md | grep -q -F 'mcp__.*)$'
PASS  docker version --format '{{.Server.Version}}'  -> 28.3.1
PASS  test -n "$(ls .claude/explorations/*_context-mode-2x-recheck/REPORT.md 2>/dev/null)"
PASS  test "$(cat <phase A> <phase B> | grep -c -F '_FROM_SPIKE')" = "0"
start gate: PASS
```

- Decisions recorded for the seven plan decisions: (1) start now, settle check waived, pin 2.1.8; (2) drop Antigravity's Context Mode entry; (3) drop `ctx_doctor`; (4) MCP-only; (5) Node.js 24 with the required slim-image check and an optional full CUDA build; (6) `CONTEXT_MODE_DATA_DIR` under `.claude/.cache/context-mode/`; (7) one server identity, `--agent codex` (spike S2).
- Branch: `git switch -c context-mode-2x-migration_implementation` from clean `dev` at `9be6955`. The branch hook set the big plan `in-progress` (`started_at: 2026-11-12T07:07:18Z`) and activated this phase.
- Coder (Steps 1-8) and documenter (Step 9) ran in parallel on disjoint files. Root guidance: the orchestrator approved the exact replacement bullets for `CLAUDE.md` line 13 and `AGENTS.md` line 14 (session-continuity claims dropped).
- Coder negative control (new tests on the old code, one at a time, 40 s limit): filter file 3 passed, 21 failed, 5 hung (the old version gate rejects the fake server's `dev` version and kills upstream, so replies never come); dispatcher file 24 passed (storage/override/launcher behavior kept, now driven through `server` mode), 8 failed; lifecycle file 4 failed; validator tests 19 failed, 2 passed (the files-only-filter-accepted test and the forged-marker state-sync test moved to `server` mode, both correctly pass on old code).
- Coder results: focused six-file pytest 1352 passed, 1 skipped; `tests/test_state_sync.py -k cache` 6 passed; `CONTEXT_MODE_REAL=1 ... -k real_upstream` 1 passed against the host's 1.0.169; full suite about 4960 passed, 1 skipped; ruff and mypy clean; `validate_targets.py` PASS. Off-plan items: kept the orchestrator-prompt sentence "do not index again for every subagent" (a required fragment); changed one generated Codex config comment that still claimed Context Mode hooks; the dist-copy validator tests now patch out `validate_hook_guardrails` (about 850 subprocesses, 28 s per call).
- Step 10 (orchestrator): `generate_targets.py --all`, then `install_bootstrap.py . --allow-self --local-only`. No hook file (`shared/hooks/hooks.json`, generated and installed Claude settings, Codex hooks, `.github/hooks/hooks.json`) names `context-mode-dispatch.sh` any more. `verify.py fast` PASS (it had failed for the coder only because `CLAUDE.md`/`AGENTS.md` differed from `.claude/bootstrap-root/` before the refresh).
- Orchestrator checks of the documenter's flagged claims: (1) `docs/smoke-tests.md` said Claude and Codex PreToolUse have two groups; the generated files have three (`Edit|Write`, `Bash`, `mcp__openwiki__openwiki_begin`), corrected. (2) README's `npx` fallback said `npx -y context-mode@1.0.169 server`; the dispatcher runs `npx -y "context-mode@$PINNED_CONTEXT_MODE_VERSION"` with no argument, corrected. (3) the real-binary test name `test_real_upstream_server_surface_is_filtered` and the no-op/no-handler tests (`tests/test_context_mode_dispatch.py:131,154`, `tests/test_validate_targets.py:2470,2485`) exist as cited.
- Orchestrator (Step 9, AI state): `.claude/instructions/project-context.instructions.md` now says three tools, no hooks, name-only gate, files-only `ctx_index`, no fixtures, and the migration status.

## [LEARN] Entries

- (filled at closeout)

## Verification

(filled at closeout)

## Open Questions / Next Steps

- Phase A implementation: coder Steps 1-8, documenter Step 9, orchestrator Step 10, reviewer Step 11.
