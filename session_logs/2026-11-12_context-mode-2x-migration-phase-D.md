# Session: Answer the MCP 2026-07-28 discovery probe (migration Phase D, reopen)

**Date:** 2026-11-12
**Plan:** `.claude/plans/2026-11-12_phase-D-context-mode-discover-fallback.md`
**Status:** COMPLETED

## Goal

The filter answers `server/discover` itself with `-32601` and never forwards it, before or after an accepted `initialize`, so a client that speaks both MCP revisions falls back to `initialize` and gets the three tools, and no upstream `instructions` reach it through the probe (REQ-007, Finding 1). Plus the separable Finding 3 unit (three overstated comments and one README sentence), which the user chose to keep.

## Work Log

- Reopen: after the three phases completed (`7895856`, pushed), live client checks found one Claude Code session with no Context Mode tools. The user said "fix problem 1". Quality report `.claude/quality_reports/2026-11-12_context-mode-2x-live-check-findings.md` recorded the findings. A planner drafted Phases D and E; its probe of the real 2.1.8 showed the cause is the forwarded `server/discover` probe, not a pipelined `tools/list` (my first explanation, wrong because my probe lacked the 2026-07-28 `_meta`).
- The user asked to see the plan first and for a review prompt. Two independent reviews ran: GPT-6 Sol (the user's, verdict BLOCK pending two MAJORs: the notification test could not see an extra reply; Phase E's line-count rule protected positions, not meaning) and an Opus devil's-advocate subagent at max effort (verdict approve with changes: the verdict-cache risk was backwards, the live check could not confirm the fix, plus wording, evidence, scope, and process items). Both reproduced the failure and the `-32601` fix against the real 2.1.8. The planner applied all 12 changes (`reopen-v2`); the user kept the separable Finding 3 unit and said "go until the end of the big plan".
- Applied: Phases D and E saved, big plan edited (status `in-progress`, `current_phase` Phase D, Reopened note, REQ-007, follow-ups), `validate_plan_frontmatter.py` exit 0; evidence copied into the live-check exploration (`era_probe.py`, `era_probe-output.txt`, `shim.sh`, `pipeline_probe.py`, `discover_probe.py`); Phase D set `in-progress` by hand (reopen step 7); nested checkpoint `d7bd246` (reopen step 8).
- Step 1: dated Correction sections appended to the live-check `REPORT.md` and the quality report (original text kept). The wrong `[LEARN:tooling]` entry about a pipelined `tools/list` in `.claude/MEMORY.md` was corrected in place to the `server/discover` lesson.

- Coder (Steps 2-4, Step 5 comments) and documenter (Step 5 README sentence, Step 6) ran in parallel. Negative control on today's filter (`-k "discover or refused_until"`): 3 failed, 2 passed, exactly as the plan predicted (test 1: the probe's answer passed through with `supportedVersions` and `instructions`; test 2: the id-less probe reached the fake and the trace appeared; test 3: failed at its first probe; the parametrized refused-until-initialize test passed with and without `_meta`). Extra mutation by the coder: with the new branch limited to `!serverAccepted`, test 3 failed at the probe after `initialize`. Real-binary test on today's filter: failed (2.1.8 answered the probe with its `instructions`); after the fix: 1 passed.
- Coder results: three test files 350 passed, 1 skipped; filter test file 38 passed, 1 skipped; `validate_targets.py` PASS; `verify.py fast` PASS; ruff and mypy clean. New comments: filter line 13 ("each naming no tool outside the allowlist"), the `server/discover` branch comment, and two dispatcher comments stating that `state-sync.sh` adds and commits only under `.claude/`, the root restore copies only allowlisted adapter files, and this gives no protection against a remote that replaces the synced scripts.
- Documenter: README `server/discover` sentence (plan wording), README secret clause replaced (plus "ever" dropped from "To keep that scenario from ever becoming a trusted cache"), runtime-checks sentence and a new first "Known limits" bullet. It flagged one README clause it left absolute.
- Step 6 orchestrator part: project-context Context Mode bullet now says the filter answers `server/discover` itself with `-32601`.
- Step 7: `generate_targets.py --all`, then `install_bootstrap.py . --allow-self --local-only`.
- Review round 1 (six profiles): gate PASS, no CRITICAL or MAJOR; two MINORs, both fixed rather than disposed. (1) README line 1432 "no cache is ever searched or cited ... unless the dispatcher produced it" contradicted the new limit sentence; now scoped "short of a remote that replaces the synced scripts themselves". (2) `test_discover_probe_is_refused_before_initialize` had no ordering barrier before its trace check; it now sends a `ping` and reads its reply first. Orchestrator mutation check of that barrier: with the filter changed to answer AND forward the probe, the test failed at the ping read (`assert 0 == 2`); the filter was restored byte-identical (SHA-256). Filter test file after the fix: 38 passed, 1 skipped; ruff clean.

- Review round 2 (same reviewer, six profiles): gate PASS, 0 findings, no open requests; both round-1 fixes confirmed.
- Required Verification block, orchestrator scratch runner (before the two round-1 fixes; closeout reruns every item): 15 items, 0 failed; `verify.py phase` PASS (325 s).
- Optional live checks after Step 7 (script `live_probe_check.sh`, saved in the live-check exploration; `MCP_PROTOCOL_NEGOTIATION=auto`, `--debug`, model haiku, capture shim on the filter's stdin):
  - Claude Code 2.1.226 probed this time. The capture shows `server/discover` first, then `initialize`, `notifications/initialized`, `tools/list`, `tools/call`. Debug line: `MCP server "context-mode": Connection established with capabilities: {... "serverVersion":{"name":"context-mode","version":"dev"},"protocolEra":"legacy","negotiatedProtocolVersion":"2025-11-25"}`; no `Failed to fetch tools`; `ctx_stats` answered.
  - Claude Code 2.1.322 (VS Code extension binary) did not probe: its debug line has no `protocolEra` field (`... "serverVersion":{"name":"context-mode","version":"dev"}}`) and the capture shows `initialize` first; `ctx_stats` answered. `~/.claude/state/mcp-discover-verdicts.json`: 2 entries before and after, none new (no probe, so none expected).
  - Default path (2.1.226, no setting): exactly `mcp__context-mode__ctx_index`, `mcp__context-mode__ctx_search`, `mcp__context-mode__ctx_stats`; `ctx_index(content)` then `ctx_search` found the word.
- Closeout AI state: small plan `status: complete`, boxes ticked, Phase D ticked in the big plan; `validate_plan_frontmatter.py` exit 0. MEMORY.md: the wrong pipelined-`tools/list` lesson was corrected in place at Step 1 to the `server/discover` lesson; a testing lesson about ordering barriers was appended.

## [LEARN] Entries

- [LEARN:mcp] MCP 2026-07-28 clients probe stdio servers with `server/discover` and skip `initialize` when the probe succeeds; a filter that gates on `initialize` must answer the probe itself (`-32601`) so they fall back. Context Mode 2.1.8 answers the probe only when it carries the 2026-07-28 `_meta`, so a probe without `_meta` proves nothing.
- [LEARN:testing] A "never forwarded" assertion on a fake upstream's trace file needs an ordering barrier (one more request whose reply is read first). Prove it with a mutation that answers AND forwards.

## Verification

```text
PASS        0.3s  uv run python scripts/generate_targets.py --all
PASS       87.3s  uv run pytest tests/test_context_mode_mcp_filter.py tests/test_context_mode_dispatch.py tests/test_validate_targets.py -q --tb=short
PASS        0.8s  PATH="$HOME/.cache/context-mode-pin/bin:$PATH" CONTEXT_MODE_REAL=1 uv run pytest tests/test_context_mode_mcp_filter.py -q --tb=short -k real_upstream
PASS        0.0s  grep -q -F 'server/discover' shared/hooks/scripts/context-mode-mcp-filter.mjs
PASS        0.0s  grep -q -F 'server/discover' tests/test_context_mode_mcp_filter.py
PASS        0.0s  grep -q -F 'FILTER_CONTRACT="ctx-index-files-only-v2"' shared/hooks/scripts/context-mode-dispatch.sh
PASS        0.0s  grep -q -F '`server/discover`' README.md
PASS        0.0s  grep -q -F '`server/discover`' docs/runtime-checks.md
PASS        0.0s  git diff --quiet HEAD -- CLAUDE.md AGENTS.md .mcp.json .vscode/mcp.json .codex/config.toml openwiki
PASS        0.0s  test "$(grep -c -F 'naming no other tool' shared/hooks/scripts/context-mode-mcp-filter.mjs)" = "0"
PASS        0.0s  test "$(cat shared/hooks/scripts/context-mode-dispatch.sh README.md | grep -c -F -e 'or restores anything' -e 'can never read or overwrite' -e 'can never read or write' -e 'cannot learn or plant')" = "0"
PASS       50.5s  uv run python scripts/validate_targets.py
PASS        0.9s  uv run python scripts/check_runtime.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS      334.3s  uv run python .claude/scripts/verify.py phase --format text
```

- Findings: `.claude/quality_reports/findings-2026-11-12_phase-D-context-mode-discover-fallback.json` (0 findings after review round 2; gate PASS; six profiles; round 1 had two MINORs, both fixed before round 2).
- optional 1: PASS — Claude Code 2.1.226 with `MCP_PROTOCOL_NEGOTIATION=auto --debug` sent `server/discover`, got `-32601`, fell back to `initialize`, and logged `"protocolEra":"legacy","negotiatedProtocolVersion":"2025-11-25"` with no `Failed to fetch tools`; 2.1.322 did not probe (no `protocolEra` field; `initialize` first), recorded as evidence only, and wrote no new verdict entry.
- optional 2: PASS — default-path session: exactly three Context Mode tools; `ctx_index` with `content` then `ctx_search` found the word (a regression check only; it cannot tell a fixed filter from an unfixed one).

## Open Questions / Next Steps

- Phase E: OpenWiki refresh of the dispatcher page and the final audit.
- Follow-ups (big plan Reopened note): refuse every method except `initialize` and `ping` before an accepted `initialize`; check whether VS Code Copilot or Codex send `server/discover`.
