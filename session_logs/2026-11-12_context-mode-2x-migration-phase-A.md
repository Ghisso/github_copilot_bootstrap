# Session: Context Mode MCP-only surface on 1.0.169 (migration Phase A)

**Date:** 2026-11-12
**Plan:** `.claude/plans/2026-11-12_phase-A-context-mode-mcp-only-surface.md`
**Status:** COMPLETED

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
- Required Verification block, run by the orchestrator before review (scratch runner, same parsing rules as `verify closeout`): 21 items, 0 failed; `verify.py phase` PASS (310 s).
- Review round 1 (seven profiles: code, architecture, security, tests, ponytail, config, documentation): gate FAIL. MAJOR (tests): no test shows the identity gate refusing `tools/list` and `tools/call` before an accepted `initialize`; the name-mismatch test accepts silence, so it passes with the gate removed. MAJOR (code): `kitTool` drops upstream `annotations` (`readOnlyHint`, `destructiveHint`); upstream notes that Codex cancelled an unannotated `ctx_stats` (issue #846), so auto-approved calls could become cancelled or prompted. MINOR (code): the real 1.0.169 `ctx_index` `path` property description ("File OR directory path ... bounded recursive walk") reaches the client and contradicts the files-only kit description. Answers: a legacy hook call blocking until stdin closes is not a finding; guardrail checks still run through the full validator test and `verify.py phase`; the kept orchestrator sentence still reads correctly; both orchestrator doc corrections confirmed. Open requests: a negative control for the new gate test; a live Codex run if annotations stay dropped.
- Fix loop: all three sent back to the coder. Annotations pass through as boolean entries only (MCP's string `title` could carry advice text, so it is dropped). Every property description is dropped (deletes `namesFilteredTool`), which is also the 2.x shape (spike S2: no property descriptions).
- Coder fixes: new `test_tools_list_and_call_are_refused_until_an_initialize_is_accepted` (no `initialize`; request-shaped `tools/list` id 2 and `tools/call` id 3 must get -32001 and the upstream trace must not exist). Negative control on a scratch copy with both `if (!serverAccepted)` returns removed: `KeyError: 'error'` at the first assert, 1 failed; removing either gate alone fails at its own assert line. `booleanAnnotations()` plus a five-case test; recursive `withoutDescriptions()` plus `test_tools_list_keeps_no_description_anywhere_in_a_schema`; validator literal updated. Checks: six-file focused pytest 1358 passed, 1 skipped; `-k cache` 6 passed; real-binary 1 passed; `validate_targets.py` PASS; ruff/mypy clean; `verify.py fast` PASS.
- Regenerated `dist/` and refreshed the self-install after the fixes. README and docs needed no change (they say "kit descriptions" and never described annotations or property descriptions).
- Review round 2 (same reviewer, seven profiles): gate PASS, 0 findings, no open requests; both round-1 open requests satisfied (negative control shown; the live Codex request was conditional on annotations staying dropped). Its answers: the recursive strip only sees `JSON.parse` output (no cycles), and very deep nesting throws before anything is sent, which fails closed; no key allowlist needed for boolean annotations. Phase B carry-overs (not this phase): (1) the real-binary test requires an `annotations` key on every tool, but 2.1.8's `ctx_index` has none (spike S2), so Phase B must allow "key absent, or all values boolean"; (2) filter comments at lines 6 and 96 name `1.0.169` and will trip Phase B's `grep -r -l -I -F '1.0.169' shared scripts tests` check; (3) nit: `booleanAnnotations` returns `{}` for a plain object with no boolean entries (harmless).
- Required Verification block rerun after the fixes (orchestrator scratch runner): 21 items, 0 failed.
- Closeout AI state: small plan `status: complete`, `closeout_session_log` set, all 19 boxes ticked; Phase A ticked in the big plan; `validate_plan_frontmatter.py` exit 0. MEMORY.md: two security lessons under Domain-Specific, one workflow and one testing lesson appended; the existing `[LEARN:security] Upstream context-mode hook output is not advisory` entry now says the kit wires no Context Mode hook since this phase.

## [LEARN] Entries

- [LEARN:security] Context Mode 2.x folder indexing has no bound on files, depth, or size, follows symlinks anywhere inside the repository's parent folder (sibling projects), and ignores a `.gitignore` above the indexed folder (2026-11-12 spike S3). The kit's filter therefore accepts only `content` or one regular file inside the repository for `ctx_index`.
- [LEARN:security] A filter that rebuilds MCP tool objects must carry the boolean `annotations` hints (`readOnlyHint`, `destructiveHint`) through. Context Mode's source notes that Codex cancelled an unannotated `ctx_stats` (issue #846). Keep only boolean entries: the `title` annotation is free text and could carry advice.
- [LEARN:workflow] A subagent's Write tool refuses report files ("Subagents should return findings as text"). An evidence spike therefore returns its report as text and keeps raw outputs in its scratch folder; the orchestrator saves the report under `.claude/explorations/`.
- [LEARN:testing] A refusal test that accepts "no reply" cannot fail when the refusal is deleted. Make the forwarded path produce a `result`, assert the exact error code and id, and prove the test fails against a copy with the refusal removed.

## Verification

```text
PASS        0.3s  uv run python scripts/generate_targets.py --all
PASS      146.1s  uv run pytest tests/test_context_mode_mcp_filter.py tests/test_context_mode_dispatch.py tests/test_validate_targets.py tests/test_lifecycle_hooks.py tests/test_openwiki_guard.py tests/test_hook_gates.py -q --tb=short
PASS        4.8s  uv run pytest tests/test_state_sync.py -q --tb=short -k cache
PASS        4.4s  CONTEXT_MODE_REAL=1 uv run pytest tests/test_context_mode_mcp_filter.py -q --tb=short -k real_upstream
PASS        0.0s  test ! -e tests/fixtures/context_mode_hook
PASS        0.0s  test "$(grep -c -F 'ctx_doctor' shared/hooks/scripts/context-mode-mcp-filter.mjs)" = "0"
PASS        0.0s  test "$(grep -c -F 'PINNED_VERSION' shared/hooks/scripts/context-mode-mcp-filter.mjs)" = "0"
PASS        0.0s  test "$(grep -c -F 'isDirectory' shared/hooks/scripts/context-mode-mcp-filter.mjs)" = "0"
PASS        0.0s  test "$(grep -c -F 'ctx-index-file-content-v1' shared/hooks/scripts/context-mode-dispatch.sh)" = "0"
PASS        0.0s  test "$(cat README.md scripts/generate_targets.py shared/policies/tool-routing.instructions.md shared/agents/orchestrator/prompt.md shared/skills/onboard/SKILL.md | grep -c -F -e 'contained real directory' -e 'bounded directory index' -e 'bounded project index' -e 'absolute repository root' -e 'Directory indexing')" = "0"
PASS        0.0s  test "$(cat shared/hooks/scripts/context-mode-mcp-filter.mjs shared/hooks/scripts/context-mode-dispatch.sh | grep -c -F -e '--hook-output')" = "0"
PASS        0.0s  test "$(cat shared/hooks/hooks.json dist/multi-agent/.claude/settings.json dist/multi-agent/.codex/hooks.json .claude/settings.json .github/hooks/hooks.json | grep -c -F 'context-mode-dispatch.sh')" = "0"
PASS        0.0s  test "$(grep -c -F 'context-mode' dist/multi-agent/.agents/mcp_config.json)" = "0"
PASS        0.0s  test "$(cat README.md docs/runtime-checks.md docs/smoke-tests.md scripts/generate_targets.py shared/agents/*/prompt.md shared/skills/onboard/SKILL.md shared/policies/tool-routing.instructions.md | grep -c -F 'four guarded')" = "0"
PASS        0.0s  test "$(cat CLAUDE.md AGENTS.md | grep -c -i 'session continuity')" = "0"
PASS        0.0s  test "$(cat scripts/generate_targets.py scripts/validate_targets.py tests/test_lifecycle_hooks.py tests/test_validate_targets.py docs/runtime-checks.md | grep -c -F 'CLAUDE_CONTEXT_MODE_MATCHER')" = "0"
PASS        0.0s  git diff --quiet HEAD -- .mcp.json .vscode/mcp.json .codex/config.toml
PASS       50.4s  uv run python scripts/validate_targets.py
PASS        0.9s  uv run python scripts/check_runtime.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS      329.9s  uv run python .claude/scripts/verify.py phase --format text
```

- Findings: `.claude/quality_reports/findings-2026-11-12_phase-A-context-mode-mcp-only-surface.json` (0 findings after review round 2; gate PASS; seven profiles; round 1 had two MAJORs and one MINOR, all fixed before round 2).
- optional 1: NOT RUN — needs the user to reconnect the Context Mode server with `/mcp` in a live Claude Code session; this session's running server process predates the change, so its tool list is not evidence. The real-binary test (`CONTEXT_MODE_REAL=1 ... -k real_upstream`) covers the same filtered surface against the host's 1.0.169 without a client.
- optional 2: NOT RUN — no live Codex or VS Code Copilot session is available to this agent; the client-side tool names stay an open question for Phase B's live checks.

## Open Questions / Next Steps

- Phase B: apply the two carry-overs above (real-binary test annotations rule; `1.0.169` in filter comments), then the 2.1.8 switch.
- Optional live checks need the user: `/mcp` reconnect in Claude Code, and Codex / VS Code Copilot sessions.
