---
name: 2026-11-12_phase-A-context-mode-mcp-only-surface
type: small-plan
parent_plan: context-mode-2x-migration
phase_index: 1
status: planned
closeout_session_log:
---

# Small Plan: Context Mode MCP-Only Surface on 1.0.169

## Scope

While still on Context Mode 1.0.169, give the kit the Context Mode surface it keeps under 2.x (big plan, decisions 2, 3, 4, and 7):

- **No Context Mode hooks.**
  - Remove every Context Mode hook handler on Claude Code, Codex, and Copilot (SessionStart, PreToolUse, PostToolUse, PreCompact).
  - Delete the dispatcher's hook mode, the filter's `--hook-output` mode, the 32 recorded fixtures, `capture.py`, and their tests.
  - A hook call from stale wiring reads its input, prints nothing, and exits 0. Example: a consumer that commits `.codex/`, which the installer keeps on refresh.
- **Three tools.** The filter allows `ctx_index`, `ctx_search`, and `ctx_stats`. `ctx_doctor` joins the rejected tools.
- **A fixed `initialize` result and kit descriptions.** The filter sends only `protocolVersion`, `capabilities.tools`, and `serverInfo`, drops upstream `instructions`, and replaces tool descriptions with short kit descriptions.
- **`ctx_index` takes text or one file.** The filter accepts `content`, or a `path` that resolves to a regular file inside the repository. It rejects folders.
  - Why: spike S3 found that 2.x folder indexing has no limit on files, depth, or size. It follows symlinks that reach sibling projects inside the repository's parent folder, and it ignores a `.gitignore` above the indexed folder. The filter checks only the top-level path, so it cannot see inside a folder.
  - Why in this phase: it is a filter change that also works on 1.0.169, and this phase already rewrites every surface that describes `ctx_index`, so each one changes once.
  - The dispatcher's `FILTER_CONTRACT` gets a new value, so a cache indexed under the old folder rule is moved aside, never trusted.
  - The orchestrator's optional whole-repository index at pre-flight goes away. Direct reads, `rg`, and Semble stay the routes for discovery.
- **An identity gate instead of a version gate.** The filter checks that `serverInfo.name` is exactly `"context-mode"`. Spike S2 recorded that name for both 1.0.169 and 2.1.8, so the gate works in this phase and after Phase B, and it cannot tell the two apart. The dispatcher alone proves the version, from the package manifest or from the pin inside the `npx` command.
- **No Antigravity entry.** Antigravity's generated MCP config no longer gets a Context Mode server.
- **MCP adapters unchanged.** The spike chose one server identity for every client (decision 7), so `.mcp.json`, `.vscode/mcp.json`, and `.codex/config.toml` keep today's `... server` command.

Covers REQ-002, REQ-003, and REQ-004. Evidence: REPORT.md §5-§7, the pre-branch spike report (`.claude/explorations/2026-11-12_context-mode-2x-recheck/REPORT.md`, S2 and S3), and `scripts/generate_targets.py:1218`. That line gives the Codex SessionStart matcher `startup|resume|clear`, so no compaction restore reaches Codex as wired.

Side effect, on this branch only: until Phase B, this branch's own sessions run 1.0.169 without Context Mode hooks, so the small 1.x compaction restore on Claude Code stops. Consumers receive the whole plan at once. Also on this branch: the new `FILTER_CONTRACT` moves this repository's cache aside on the first server start after Step 10, and Phase B's pin moves it aside again, so two `.untrusted` folders appear here. Consumers get one move.

## Steps

- [ ] **1. Write the tests first.**
  - Owner: `coder`. Files (modify): `tests/test_context_mode_mcp_filter.py`, `tests/test_context_mode_dispatch.py`, `tests/test_validate_targets.py`, `tests/test_lifecycle_hooks.py`, `tests/test_state_sync.py`.
  - Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/testing-patterns/SKILL.md`.
  - Filter tests:
    - `initialize` reaches the client as exactly `protocolVersion`, `capabilities` holding only `tools`, and `serverInfo`. A fake upstream that also returns `instructions`, `capabilities.experimental`, `prompts`, and `resources` loses all four.
    - Identity gate (replaces `test_version_mismatch_exposes_no_tools`):
      - a server name other than the expected name returns error `-32002`, kills upstream, and refuses `tools/list` and `tools/call`;
      - the expected name passes with the versions `"dev"`, `"1.2.3"`, and `"2.9.9"`;
      - do not use the old pin as a literal; Phase B checks that no test names it.
    - `tools/list`:
      - returns exactly `ctx_index`, `ctx_search`, `ctx_stats`, with the kit descriptions and without `_meta`;
      - removes any property description that names a non-allowlisted `ctx_` tool;
      - `ctx_index` keeps only `content`, `path`, `source`.
    - `tools/call` for `ctx_doctor` is rejected locally with `-32601`.
    - `ctx_index` takes text or one file (spike S3), tested through the fake upstream:
      - a folder `path` (`.`, a subfolder, and the absolute path of a folder inside the repository) gets `-32602` and never reaches upstream;
      - a symbolic link to a regular file inside the repository gets `-32602` (today only links to folders are tested);
      - a regular file inside the repository, by relative and by absolute path, reaches upstream;
      - `test_allowed_calls_and_guarded_index_content_file_and_directories_pass_through` (lines 166-195) drops its two folder calls and is renamed to match; the message assertion at line 378 expects "regular file" without "or directory";
      - `test_index_rejects_directory_policy_override_arguments` keeps passing, because the argument check runs before the path check.
    - `test_racing_call_and_list_with_shared_id_never_leaks_blocked_tools` (lines 285-318) races `ctx_stats` instead of `ctx_doctor`, so the shared-id call still reaches upstream. Update the name lists at lines 106, 184-193, 281, and 317. The fake upstream (line 37) keeps advertising `ctx_doctor` as a tool the filter must hide.
    - Delete the `--hook-output` tests (line 504 onward).
  - Dispatcher tests:
    - The storage, override, provenance, quarantine, and launcher tests that drive the dispatcher through a hook event (lines 114-370 and 469-540) now drive it through `server` mode with the existing `_fake_node`. Their assertions stay.
    - New: `claude-code sessionstart`, `openai-codex pretooluse`, and `github-copilot posttooluse`, each with a JSON payload on stdin. Each exits 0, prints nothing, starts no upstream and no `node`, and creates no cache folder.
    - New: a fresh cache's marker holds the new `FILTER_CONTRACT`. A cache whose marker holds the correct secret and pin but `filter=ctx-index-file-content-v1` is moved aside on the first server start.
    - Delete the fixture-replay and hook-output tests from about line 545 onward, including `ALLOWED_CTX_TOOLS` and `test_real_upstream_hook_output_is_advisory_only`.
  - Generator and validator tests:
    - The rendered Claude settings, the rendered Codex hooks, and `shared/hooks/hooks.json` contain no handler that runs `context-mode-dispatch.sh`, and no `PreCompact` event. All other handlers are unchanged.
    - The validator rejects a `context-mode-dispatch.sh` handler in any hook event of any target. `pretool_routing_errors` accepts the three remaining groups. A Codex event set without `PreCompact` passes, and one with it fails.
    - The rendered Antigravity config has no `context-mode` entry. The validator fails when one is added back, and keeps the `semble` and `context7` parity checks.
    - Rename `test_context_mode_tool_surface_is_exactly_four_tools_everywhere`, and make it expect exactly three tools.
    - Delete `test_rendered_claude_context_mode_pretool_matcher_skips_agent`, `test_pretool_routing_requires_target_specific_context_mode_matcher`, and `CLAUDE_CONTEXT_MODE_MATCHER_LITERAL`.
    - Update any other test that expects a Context Mode hook handler.
    - The filter-surface check requires the regular-file check and fails when the filter text names `isDirectory`.
    - `test_execution_defaults_policy_contract_rejects_missing_clauses` (near line 746) mutates a files-only `ctx_index` phrase from Step 8 instead of "contained real directory".
  - State-sync test: `test_hostile_remote_cache_with_forged_marker_is_quarantined_not_trusted` (`tests/test_state_sync.py`, near line 1329) runs the dispatcher as `server` instead of `claude-code sessionstart`, because Step 3 turns hook calls into no-ops that never touch storage.
    - Put a fake `node` (prints `v24.15.0` for `--version`, exits 0 otherwise) and a fake `npx` first on `PATH`, so nothing real starts and Phase B's Node.js floor passes later.
    - The forged marker reads the pin and `FILTER_CONTRACT` from the dispatcher source, so only the secret differs. Its quarantine assertions stay.
  - Negative control before Step 2: run the new tests on today's code, and record in the session log which ones fail and why.

- [ ] **2. Filter.**
  - Owner: `coder`. File: `shared/hooks/scripts/context-mode-mcp-filter.mjs` (modify). Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Set `ALLOWED_TOOLS` to `ctx_index`, `ctx_search`, `ctx_stats`.
  - Delete `PINNED_VERSION` and its comparison.
    - Accept the first `initialize` response only when `result.serverInfo.name` is exactly `"context-mode"`. Spike S2 recorded that name for 1.0.169 and for 2.1.8 (`Server name: context-mode / context-mode`).
    - Do not check `serverInfo.version`: 1.0.169 reports `"1.0.169"`, 2.x reports `"dev"`, and this phase still runs on 1.0.169.
    - Otherwise keep today's failure path: error `-32002`, and kill upstream.
    - Rename `versionAccepted` to match, for example `serverAccepted`, and make the error text say that the server identity was not accepted.
  - Rewrite the accepted `initialize` result to `{ protocolVersion, capabilities: { tools: <upstream tools capability, or {}> }, serverInfo: { name, version } }`. Drop everything else, including `instructions`.
  - In `tools/list` responses, rebuild each allowed tool as `{ name, description, inputSchema }`:
    - `description` comes from a fixed kit map: one sentence per tool that names no other tool and gives no routing advice. Examples (`ctx_index` takes text or one file, spike S3):
      - `ctx_index`: "Index raw text, or one regular file inside this repository, into this repository's local Context Mode store; folders, links, and URLs are rejected."
      - `ctx_search`: "Search content indexed with ctx_index in this repository's local Context Mode store."
      - `ctx_stats`: "Report size and usage statistics for this repository's local Context Mode store."
    - `inputSchema` comes from upstream. `ctx_index` properties stay limited to `INDEX_ARGS`. Remove property descriptions that name a non-allowlisted `ctx_` tool.
  - Delete the `--hook-output` mode: `sanitizeHookOutput`, `ADVICE_TAGS`, `ADVICE_BLOCKS`, `PLUGIN_PREFIX`, and the argv branch.
  - `validateIndex` accepts only text or one regular file (spike S3):
    - keep every check it makes today: the closed argument set, the `source` bound, exactly one of `content` or `path`, no `..`, not a symbolic link, and a real path inside the repository;
    - then accept a `path` only when `lstat` reports a regular file;
    - anything else, a folder included, gets `-32602` with a message saying that a regular file inside the repository is required;
    - do not use `isDirectory`; the validator checks for it (Step 5).
  - Must not change: the batch and notification handling, or the pending-list bound.

- [ ] **3. Dispatcher.**
  - Owner: `coder`. File: `shared/hooks/scripts/context-mode-dispatch.sh` (modify). Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Delete hook mode: the client-to-target mapping, `run_upstream_hook`, and the output filtering (lines 320-358).
  - Any mode other than `server` and `--self-check` reads stdin to the end, prints nothing, and exits 0, before storage setup. One comment says why: stale hook wiring in an adapter that the installer keeps must stay harmless.
  - `server` mode stays as it is. Update the self-check and warning texts that mention hook events, so they talk about the MCP server.
  - Set `FILTER_CONTRACT="ctx-index-files-only-v2"`. Only the value changes. A cache indexed under the old folder rule no longer matches its marker, so it is moved aside on the first server start.
  - Must not change: storage selection, the override rule, the provenance secret, the quarantine, the marker format, or the version proof.

- [ ] **4. Generator and Copilot hooks.**
  - Owner: `coder`. Files (modify): `scripts/generate_targets.py`, `shared/hooks/hooks.json`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - `render_claude_settings`: remove the Context Mode handler from the SessionStart and PostToolUse groups. Remove the Context Mode PreToolUse group and the whole `PreCompact` event. Delete `CLAUDE_CONTEXT_MODE_MATCHER` and its comment.
  - `render_codex_hooks`: remove the SessionStart handler, the `*` PreToolUse group, the PostToolUse handler, and the `PreCompact` event. The Codex SessionStart matcher stays `startup|resume|clear`.
  - `shared/hooks/hooks.json`: delete the four Context Mode entries. The `PreCompact` event goes with them.
  - `render_antigravity`: write no `context-mode` entry.
  - Text: the tool-map comment (near lines 89-92) says three tools. The root-guidance sentence (near line 1389) says three tools, drops "alongside its lifecycle hooks", and replaces "A guarded bounded project index is optional for broader discovery" with a short files-only clause. It keeps "never repository truth".
  - Must not change: group order, timeouts, other handlers, or the MCP entries for Claude, Codex, and Copilot.

- [ ] **5. Validator.**
  - Owner: `coder`. File: `scripts/validate_targets.py` (modify). Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - `CONTEXT_MODE_ALLOWED_TOOLS` becomes three tools. Add `ctx_doctor` to `CONTEXT_MODE_BLOCKED_TOOLS`.
  - `validate_context_mode_tool_surface` (near line 3622):
    - replace the `if (!stat.isFile() && !stat.isDirectory())` check with a check for the regular-file test (for example `if (!stat.isFile())`), and fail when the filter text contains `isDirectory`;
    - delete the "directory input is temporarily disabled" check; it guarded the folder support this phase removes.
  - `EXECUTION_DEFAULTS_POLICY_FRAGMENTS["tool-routing.instructions.md"]` (near line 458):
    - replace "contained real directory", "one bounded directory index after direct pre-flight reads", and "no directory-policy override arguments" with the files-only phrases Step 8 writes (for example "one contained regular file" and "Folders and URLs are not accepted");
    - keep "never repository truth" and "Git and filesystem state are authoritative over cached content".
  - Delete the filter-pin check in `validate_context_mode_tool_surface` (near line 3606), and the dispatcher mapping check `'openai-codex) CONTEXT_MODE_TARGET="codex"'` (near line 3010). Keep the dispatcher pin check.
  - `reporting_reminder_hook_errors`: the expected PostToolUse group no longer holds the Context Mode handler (lines 1407-1424).
  - `pretool_routing_errors`: expect three groups. Remove the matcher import and the observer group.
  - Remove `PreCompact` from `CLAUDE_EXPECTED_EVENTS`, `COPILOT_EXPECTED_EVENTS`, and the local `expected_codex_events` (lines 3137-3145).
  - Delete only the R-CODEX-01 PreCompact check (lines 3155-3160), and leave a two-line comment: that event had only the Context Mode handler, and the 2.x Codex decoder rejects it. Keep the other two R-CODEX-01 checks (lines 3060 and 3124).
  - Add a check that no hook handler of any target runs `context-mode-dispatch.sh`.
  - Antigravity: require that `context-mode` is absent, and keep the `semble` and `context7` parity checks.
  - Keep the hook-script list entry for the dispatcher (line 241): the dispatcher still ships, for server mode.

- [ ] **6. Delete the fixtures.**
  - Owner: `coder`. Delete `tests/fixtures/context_mode_hook/` (32 fixtures, `capture.py`, and its `__pycache__`).

- [ ] **7. Real-binary server test.**
  - Owner: `coder`. File: `tests/test_context_mode_mcp_filter.py` (modify).
  - Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/testing-patterns/SKILL.md`, `.claude/skills/integration-gate-spike/SKILL.md`.
  - Add `test_real_upstream_server_surface_is_filtered`, skipped unless `CONTEXT_MODE_REAL=1`:
    - Set up a scratch repository with the dispatcher and the filter copied in; scratch `HOME`, `TMPDIR`, `CLAUDE_CONFIG_DIR`, and `CODEX_HOME`; and the caller's `PATH`.
    - It fails, never skips, when the variable is set and `--self-check` does not report `version-contract=pinned-direct-binary`. This way it can never download through `npx`.
  - Start `bash <dispatcher> server`. Send `initialize`, `notifications/initialized`, `tools/list`, `ctx_index` with `content` and a unique `source`, a `ctx_search` for a unique word from that content, and `ctx_doctor`. Use a timeout of 60 seconds per request.
  - Assert:
    - the `initialize` result keys are exactly `protocolVersion`, `capabilities`, `serverInfo`, and the capabilities hold only `tools`;
    - the tool names are exactly the three, and each description equals the kit text;
    - the search result contains the unique word;
    - `ctx_doctor` gets `-32601`;
    - `HOME/.context-mode` does not exist;
    - new files appear under `<repo>/.claude/.cache/context-mode/`.

- [ ] **8. Live-advice text in shared sources.**
  - Owner: `coder`. Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Files: `shared/agents/{coder,documenter,orchestrator,planner,reviewer}/prompt.md` and `shared/skills/onboard/SKILL.md`: "exactly four guarded MCP tools (...) alongside its lifecycle hooks" becomes three tools, with no hooks.
  - File: `shared/policies/tool-routing.instructions.md`:
    - three tools, and `ctx_doctor` in the filtered list;
    - the server is Context Mode's only route;
    - when Context Mode is unavailable, the server warns and exits nonzero;
    - fix the stale sentence "canonical external absolute overrides remain supported": the dispatcher refuses every override outside `.claude/.cache/context-mode`;
    - Routing Contract (near line 15): `ctx_index` accepts content or one contained regular file, and folders and URLs are not accepted. Remove the orchestrator's one bounded directory index, the upstream directory defaults, and the list of directory-policy arguments. Keep "never repository truth" (the validator requires it).
  - File: `shared/agents/orchestrator/prompt.md` (near lines 30-41): remove the pre-flight `ctx_index` of the whole repository root and the re-index advice. `ctx_index` stays for one large file or text that will be searched more than once.
  - File: `shared/skills/onboard/SKILL.md` (near lines 57-61): `ctx_index` accepts content or one contained regular file; drop the two sentences about folders.

- [ ] **9. Documentation and root guidance.**
  - Owner: `documenter`; the root guidance edits need the orchestrator's approval of the edit prompts. Required Skills: `.claude/skills/documentation/SKILL.md`.
  - `CLAUDE.md` line 13 and `AGENTS.md` line 14: drop the session-continuity claims.
  - `README.md`:
    - hooks section (near line 1086), and lines 1161 and 1196;
    - the Context Mode block near lines 1426-1434: no hooks, three tools, the identity gate, `ctx_index` for content or one regular file (no folders), and no Antigravity entry;
    - a refresh note: a consumer that commits `.codex/` or `.github/hooks` keeps stale Context Mode hook entries; they do nothing, and regenerating the adapters removes them.
  - `docs/runtime-checks.md`:
    - the Context Mode bullet (lines 94-114): no hook lane and no fixtures; `ctx_index` for content or one regular file; the pin-bump steps that remain until Phase B rewrites them; trimmed known limits;
    - the hook lists near lines 209 and 250, and lines 933-934.
  - `docs/smoke-tests.md`: near lines 103, 122-134, 209, 220, and 283-285.
  - `docs/architecture.md`: near lines 291-296.
  - `docs/target-mapping.md`: near lines 94-95, 102, 104, and 120-122.
  - Orchestrator: update `.claude/instructions/project-context.instructions.md` (AI state): the hook-lane and matcher design bullets, the fixture mention, four tools, the Antigravity entry, and any claim that `ctx_index` takes folders.
  - LEARN candidate: `[LEARN:security] Context Mode 2.x folder indexing has no bound, follows symlinks inside the repository's parent folder, and ignores a .gitignore above the folder; the kit's filter accepts only content or one regular file.`

- [ ] **10. Regenerate and refresh the self-install.**
  - Owner: orchestrator. Run `uv run python scripts/generate_targets.py --all`, then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`, after all edits, including the root guidance. Never hand-copy.
  - Reconnect the Context Mode MCP server in the running client (for example `/mcp` in Claude Code).

- [ ] **11. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `config`, `documentation`.
  - Focus:
    - nothing starts the filter except the dispatcher (check every caller of `context-mode-mcp-filter.mjs`);
    - the identity gate still blocks `tools/list` and `tools/call` until an accepted `initialize`;
    - `validateIndex` accepts only content or one regular file inside the repository, and the new `FILTER_CONTRACT` moves older caches aside;
    - only the allowlisted `initialize` keys reach the client;
    - a legacy hook call can never block a tool or touch storage;
    - the safety-lane hooks are unchanged on every client;
    - no surface still claims four tools or Context Mode hooks.

## Risks and Fallbacks

- A consumer that commits `.codex/` or `.github/hooks` keeps stale Context Mode hook entries after a refresh. The no-op in Step 3 keeps them harmless and quiet, and the README refresh note says how to remove them.
- A consumer that commits `.agents/` keeps Antigravity's Context Mode entry. Antigravity's bridge denies every MCP call, so the entry stays unused.
- Someone relied on the Context Mode hooks. Under 1.0.169 the only forwarded output was a 219-byte restore guide after a Claude compaction. Under 2.x, as wired, nothing reaches any client. Decision 4 lists the alternatives.
- 1.0.169 and 2.1.8 report the same server name, `context-mode` (spike S2), so the identity gate cannot tell 1.x from 2.x. The dispatcher's version proof is the only version check, and Step 11 checks that only the dispatcher starts the filter.
- Files-only `ctx_index` removes folder indexing and the orchestrator's optional whole-repository index. Agents index one large file or text at a time, and discovery stays with direct reads, `rg`, and Semble.
- Remaining limit: a hard link inside the repository to a file elsewhere passes the regular-file check. Making one needs write access to the repository, which already allows copying that file in.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run pytest tests/test_context_mode_mcp_filter.py tests/test_context_mode_dispatch.py tests/test_validate_targets.py tests/test_lifecycle_hooks.py tests/test_openwiki_guard.py tests/test_hook_gates.py -q --tb=short
uv run pytest tests/test_state_sync.py -q --tb=short -k cache
# Needs the host's global Context Mode 1.0.169 on PATH (~/.local/bin/context-mode); its server calls the npm registry at startup (REPORT.md §9).
CONTEXT_MODE_REAL=1 uv run pytest tests/test_context_mode_mcp_filter.py -q --tb=short -k real_upstream
test ! -e tests/fixtures/context_mode_hook
test "$(grep -c -F 'ctx_doctor' shared/hooks/scripts/context-mode-mcp-filter.mjs)" = "0"
test "$(grep -c -F 'PINNED_VERSION' shared/hooks/scripts/context-mode-mcp-filter.mjs)" = "0"
test "$(grep -c -F 'isDirectory' shared/hooks/scripts/context-mode-mcp-filter.mjs)" = "0"
test "$(grep -c -F 'ctx-index-file-content-v1' shared/hooks/scripts/context-mode-dispatch.sh)" = "0"
test "$(cat README.md scripts/generate_targets.py shared/policies/tool-routing.instructions.md shared/agents/orchestrator/prompt.md shared/skills/onboard/SKILL.md | grep -c -F -e 'contained real directory' -e 'bounded directory index' -e 'bounded project index' -e 'absolute repository root' -e 'Directory indexing')" = "0"
test "$(cat shared/hooks/scripts/context-mode-mcp-filter.mjs shared/hooks/scripts/context-mode-dispatch.sh | grep -c -F -e '--hook-output')" = "0"
test "$(cat shared/hooks/hooks.json dist/multi-agent/.claude/settings.json dist/multi-agent/.codex/hooks.json .claude/settings.json .github/hooks/hooks.json | grep -c -F 'context-mode-dispatch.sh')" = "0"
test "$(grep -c -F 'context-mode' dist/multi-agent/.agents/mcp_config.json)" = "0"
test "$(cat README.md docs/runtime-checks.md docs/smoke-tests.md scripts/generate_targets.py shared/agents/*/prompt.md shared/skills/onboard/SKILL.md shared/policies/tool-routing.instructions.md | grep -c -F 'four guarded')" = "0"
test "$(cat CLAUDE.md AGENTS.md | grep -c -i 'session continuity')" = "0"
test "$(cat scripts/generate_targets.py scripts/validate_targets.py tests/test_lifecycle_hooks.py tests/test_validate_targets.py docs/runtime-checks.md | grep -c -F 'CLAUDE_CONTEXT_MODE_MATCHER')" = "0"
git diff --quiet HEAD -- .mcp.json .vscode/mcp.json .codex/config.toml
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

- In a live Claude Code session in this repository, after `/mcp` reconnects Context Mode: the server lists three tools; `ctx_index` with `content` followed by `ctx_search` works; and the debug hook log shows no Context Mode hook.
- In live Codex and VS Code Copilot sessions, the server lists three tools. Record the tool names each client shows (an open question in REPORT.md).

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT); the order below mirrors it
rather than restating it.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.
Set `status: paused`, record the three pause fields, and create a session log
with `**Status:** PAUSED`. A checkpoint commit preserves incomplete work; it
does not require final findings, LEARN, DOCUMENT, or a completed closeout.
After the checkpoint commit, it may be pushed as a durable remote backup when
paused-publication invariants pass. It remains unfinished and blocks PR creation
and final closeout.
Keep the big plan `in-progress` with the same `current_phase`. On resume, read
the pause log and Git state, restore this plan to `in-progress`, and continue
this same phase without creating another small plan.
