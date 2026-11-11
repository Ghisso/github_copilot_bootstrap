# Context Mode 1.0.169 -> 2.x upgrade evidence

Date: 2026-11-11. Evidence only, not a plan. Gathered by a research subagent in a session scratch folder; saved here by the orchestrator from the agent's hand-back (the agent could not write files). Only this report and the harness scripts (`scripts/`) were kept. The `raw/`, `pkg-*/`, `src/`, and `run/` paths cited below lived in that temporary scratch folder (several MB, including copies of upstream Context Mode source) and were not kept; re-run `scripts/` against fresh installs to regenerate them. The repository was only read; the real home was unchanged.

## Method

- Both versions installed side by side with scripts disabled (`pkg-1.0.169/`, `pkg-2.1.7/`), scratch npm cache.
- Every run through `scripts/cmrun.sh`: `env -i`, all home/config/temp variables (`HOME`, `XDG_*`, `TMPDIR`, `CONTEXT_MODE_DIR`, `CONTEXT_MODE_PROJECT_ROOT`, `CLAUDE_CONFIG_DIR`, `CODEX_HOME`, `COPILOT_HOME`, `KIRO_HOME`, `GEMINI_CLI_HOME`, `OPENCODE_CONFIG_DIR`, `PI_CODING_AGENT_DIR`, `CLAUDE_PROJECT_DIR`) pointed at `run/<label>/`; cwd a scratch Git repository; most runs under bubblewrap with no network.
- 1.0.169 runs used the installed copy under `~/.local/nodejs/.../lib/node_modules/context-mode` with scratch variables, as `capture.py` does. No `setup`, `install`, `upgrade`, or `doctor --fix`; `ctx_doctor` (allowed by the kit) was called.
- v2.1.7 source fetched with `git clone --depth 1 --no-checkout` into `src/src-2.1.7/`, read with `git show`, never executed; key files copied to `raw/src-2.1.7/`.
- The repository guard blocks commands whose text contains `.claude/hooks/scripts`, so the scratch dispatcher copy lives at `run/dispatch-test/repo/kit/hooks/scripts/`.

## 1. Versions, release notes, security

- Latest 2.1.7 (npm 2026-11-08T15:02:06Z). dist-tags: `latest: 2.1.7`, `next: 2.0.0-next.40` (stale). 1.0.169 (2026-06-29) is the last 1.x. Since then: 31 prereleases (2026-10-27 to 11-04) and 11 stable releases (2.0.0 on 11-04 to 2.1.7 on 11-08). Evidence: `raw/npm-time.json`, `raw/npm-versions.json`, `raw/npm-dist-tags.json`.
- Release notes (`raw/release-notes-v1.0.169-to-v2.1.7.md`): 2.0.0 is a full rewrite (307 commits). Node 24.15.0+ and `node:sqlite` (line 402); one `context.db` per project under `~/.context-mode`, no 1.x data copy (403); new CLI with `setup`, `doctor`, `upgrade`, while the 1.x forms `context-mode hook <platform> <event>` and `mcp` still run (404); nine tools with renames (405-409); routing text moved into tool descriptions (410); dropped agents include Antigravity ("to keep one of them, stay on 1.0.169", 411); hook never errors, one fallback decision (457); output replaced after the tool runs (463); PowerShell routes like Bash (540); Claude project from `CLAUDE_PROJECT_DIR` then payload `cwd` (543); 2.1.4 keeps Claude Code Agent input unchanged (#1319, 799); 2.1.4 `CONTEXT_MODE_DATA_DIR` moves the data root (807); doctor checks npm dist-tags then Git tags (501) and writes an issue report with a `gh` command (392).
- The notes are not fully reliable: 2.1.7 lists a `policy.json` WebFetch switch (#1336, line 892) that the tag source records as reverted (`DEVIATIONS.md` D-R52-REVERT-1336-1); the npm bundle has no `policy.json` or `allowHosts`.
- Security: 2.1.4 "Security" (793-796): deny rules for every `ctx_execute` shell language and `ctx_batch`; URL fetcher blocks more private ranges and checks redirects; `ctx_upgrade` keeps v1 data; PostToolUse reads persisted output only from its own session folder (16 MiB cap). 2.0.0 hardened the shell-dump deny (458-460). No published advisories (`raw/gh-security-advisories.json`, `raw/gh-global-advisories.json`). The fixed paths are in tools the kit blocks or 2.x-only features; no known 1.0.169 flaw the kit is exposed to (medium confidence).
- Supply chain: 2.1.7 has npm provenance; 38 `SHA256SUMS` entries verify; `npm audit signatures`: verified registry signature and attestation. 1.0.169 has no attestation (`raw/npm-audit-signatures.txt`).
- Files to change: `docs/runtime-checks.md`, `README.md`, `docs/target-mapping.md` (Antigravity).

## 2. License

No change: both `Elastic-2.0`; LICENSE files byte-identical (sha256 `92f11a86...05caa0`). ELv2 is source-available, already true for 1.0.169. 2.x bundles third-party code into single files.

## 3. Node, dependencies, install scripts

| | 1.0.169 | 2.1.7 |
|---|---|---|
| `engines.node` | `>=22.5.0` | `>=24.15.0` |
| Dependencies | 8 incl. native better-sqlite3 (141 packages) | none (bundled, 39 files) |
| Install scripts | `postinstall: node scripts/postinstall.mjs` | none |
| Unpacked size | 4.25 MB | 6.58 MB |

Node 22.22.0 test (`raw/node22-2.1.7.txt`): `npm install` succeeds with only `EBADENGINE` (fails with `--engine-strict`); `--version` prints 2.1.7; the server starts degraded with only `ctx_doctor` in `tools/list` (`isDegraded()`, server.mjs:58445); every hook call fails with NODE_TOO_OLD and the fallback denies Bash (even `ls`), Grep, WebFetch, appending to `~/.context-mode/hook-errors.log` (the kit filter drops the denies). The Dockerfile's current checks (`npm install -g`, `context-mode --help`) would still pass. Other global tools allow Node 24 by engines (openwiki@0.7.2 `>=22.22.0`, jsdom@29.1.1, mermaid); not run.

Files to change: `shared/devcontainer/Dockerfile` (and generated `.devcontainer/Dockerfile`), `scripts/validate_targets.py`, `tests/test_validate_targets.py`, `README.md`, `docs/runtime-checks.md`.

## 4. CLI

- Today: hooks `context-mode hook <target> <event>` with targets `claude-code`, `codex`, `vscode-copilot` (dispatch.sh 320-325); events sessionstart, pretooluse, posttooluse, precompact (`generate_targets.py` 1117-1170, 1223-1266; `shared/hooks/hooks.json` 34-123); the filter spawns bare `context-mode` (line 317) or `npx -y context-mode@1.0.169` (315).
- 2.1.7 (cli.mjs:10861-10898; `raw/cli-2.1.7.txt`): `hook <platform> <event>` runs through `V1_PLATFORM_AGENT` (`vscode-copilot` -> `vscode`); the `<event>` argument is dropped (event read from stdin JSON); unknown platform exits 0; new form `hook --agent <id>`. Claude Code and Codex decoders accept only SessionStart, UserPromptSubmit, PreToolUse, PostToolUse (Codex also Stop): the kit's PreCompact call returns empty, exit 0, prints `hooks: decode failed: claude-code: unknown hook event PreCompact`, and appends to `hook-errors.log`; VS Code still handles PreCompact. Bare `context-mode` prints help; the server is `context-mode server [--agent <id>]` (alias `mcp`); through the filter the bare form fails with "invalid JSON-RPC message" (`raw/mcp/G2-*.json`). `--version`/`-v` print 2.1.7 (`version` exits 2); in 1.0.169 all three print nothing.
- The dispatcher's offline `package.json` version check reads the 2.x layout; a scratch dispatcher copy reported `observed-version=2.1.7` and refused it in favor of `npx@1.0.169` (`raw/dispatcher-self-check-with-2.1.7-on-path.txt`).

Files to change: `context-mode-dispatch.sh`, `scripts/generate_targets.py`, `shared/hooks/hooks.json`, `tests/test_context_mode_dispatch.py`.

## 5. Hook output compared with the fixtures

`scripts/replay_hooks.py` replays each fixture's input in `capture.py` order with the dispatcher's mapping and variables, then pipes raw output through `context-mode-mcp-filter.mjs --hook-output`. Against 1.0.169 it reproduces 32/32 byte for byte (`raw/hooks-1.0.169-replay-vs-fixtures.txt`); against 2.1.7, 7/32 identical (all empty) and 25 changed (`raw/hooks-2.1.7/`, `raw/hooks-2.1.7-vs-fixtures.txt`). Extra synthetic sequences: `raw/hooks-2.1.7-sequence-{claude,codex,vscode}.json`.

| Case | 1.0.169 | 2.1.7 | Filter forwards |
|---|---|---|---|
| Claude SessionStart startup | advice block | resume sentence naming `mcp__plugin_context-mode_context-mode__ctx_resume` | nothing |
| Claude SessionStart compact | advice + session data (219 B forwarded) | `<context_mode_state>` with plugin-prefixed `ctx_search` | nothing |
| Claude Agent | `updatedInput` | empty | nothing |
| Claude ctx-execute | `updatedInput` | empty | nothing |
| Claude Read and Grep | tips | empty | nothing |
| Claude Bash curl | deny | empty (curl runs; Claude has the output-replace channel) | nothing |
| Claude WebFetch | deny | deny, new wording | nothing |
| Claude and Codex PreCompact | `{}` | empty + stderr line | nothing |
| Codex curl | allow + `updatedInput` | deny | nothing |
| Codex PostToolUse bash | `additionalContext` | empty | nothing |
| Codex SessionStart compact | advice block | `<context_mode_state>` with `mcp__context_mode__ctx_search` | forwarded, 246 B |
| Copilot terminal-curl | allow + `updatedInput` | deny | nothing |
| Copilot fetch | top-level deny | empty (`fetch` unknown to 2.x VS Code) | nothing |
| Copilot agent | `updatedInput` | empty | nothing |
| Copilot SessionStart compact | advice block | empty (state comes on next UserPromptSubmit) | nothing |

New or changed shapes: no `updatedInput` anywhere (a subagent shell rewrite exists only as deny-reason text, dispatch.ts:359-367); new `updatedToolOutput` (Claude only, PostToolUse output over 4096 B, `CTX_REPLACE_TRIGGER_BYTES`; a 23,550 B Bash output became a one-line `ctx_search` pointer; encoder claude-code.ts:197-211; the filter drops it, so the model keeps full output); new denies (Read over 16,384 B without offset/limit, Codex/VS Code `cat` of a big file, VS Code `fetch_webpage`), all dropped by the filter; failure fallback denies shell, Grep, fetch, large Read (fallback.ts:3-4), dropped. `additionalContext`: 1.0.169 advice tags never appear; new resume sentence and `<context_mode_state session=".." upto="N">` with `now: <last prompt>`, `asked #n: ...`, `edited <path> xN`, `more: <prefix>ctx_search(...)` - restored session data containing the user's prompt text and file paths, not in `ADVICE_TAGS`, so it passes the filter whenever every tool name in it is allowed. Tool-name prefixes are fixed per host (Claude `mcp__plugin_context-mode_context-mode__`, hard-coded claude-code.ts:6; Codex `mcp__context_mode__`; VS Code `mcp_context-mode_`; Copilot CLI `context-mode-`); the kit's Claude server is named `context-mode` (`mcp__context-mode__ctx_*`), so the filter drops all Claude text. Compaction state arrives on SessionStart(compact) for Claude and Codex, on the next UserPromptSubmit for VS Code (the kit wires no UserPromptSubmit Context Mode hook; that hook also records `now:`).

Net: with today's filter the 2.x hook lane forwards only the Codex compaction block. Remaining value would come from side effects (session journal, indexing large outputs), which need wider PostToolUse matchers (the kit's Claude PostToolUse matcher is Bash only) and a UserPromptSubmit hook. Confidence: high for recorded inputs; medium for real clients.

Files to change: new fixtures folder (32 to re-record), `capture.py`, `tests/test_context_mode_dispatch.py` (e.g. 684-692), the filter (`ADVICE_TAGS`, `context_mode_state`, tool prefixes), `docs/runtime-checks.md` known limits, `docs/smoke-tests.md`.

## 6. PreToolUse routing

- 1.0.169 `routePreToolUse` (routing.mjs:670): Bash 704, Read 848, Grep 870, WebFetch 875, Agent 894 (prompt rewrite), own `ctx_execute`/`ctx_execute_file`/`ctx_batch_execute` 925-1012.
- 2.1.7: `routing.mjs` is gone; the npm package ships only minified `hook.mjs`. Successor `decide()` in `src/core/policy/decide.ts:59-80`, called from `dispatch.ts:325-342`: (1) user deny rules from `<project>/.claude/settings(.local).json` and `$CLAUDE_CONFIG_DIR/settings.json` for Bash, Read, `ctx_execute`, `ctx_batch`; (2) WebFetch denied with a redirect to `ctx_index` then `ctx_search` (except `claude.ai`, `claude.site`, `claudeusercontent.com`); (3) Bash (PowerShell counts as Bash): curl/wget/inline HTTP/build commands denied only on hosts without the output-replace channel (Codex, VS Code) or for subagent calls, plus one-file shell dumps over the cap; (4) Read denied over 16,384 B; (5) everything else allowed ("Steps 5d, 7, 8 ... hints are retired", decide.ts:78). No hints; no database writes in PreToolUse (dispatch.ts:341). Agent: no branch, input never changed.
- Matcher check: `^(Bash|Read|Grep|WebFetch|mcp__.*)$` covers everything 2.x acts on except PowerShell (Windows-only Claude Code tool); `Grep` and `mcp__.*` are now no-ops. Upstream plugin matcher: `^(Bash|PowerShell|Read|Grep|WebFetch|Write|Edit|NotebookEdit|mcp__plugin_context-mode_context-mode__ctx_.*)$`. Because the kit drops every decision, this hook would forward nothing (0 B in every replay) and cost one Node start per matching call.

Files to change: `scripts/generate_targets.py` (41-45), `tests/test_lifecycle_hooks.py` (`test_rendered_claude_context_mode_pretool_matcher_skips_agent`), `docs/runtime-checks.md` step 3 (routing source no longer in the npm package).

## 7. MCP server

| | 1.0.169 | 2.1.7 |
|---|---|---|
| `serverInfo` | version `1.0.169` | version `"dev"`, hard-coded (server.mjs:58621) |
| Server `instructions` | empty | 509 characters |
| Capabilities | prompts, resources, tools | experimental `codex/sandbox-state-meta`, tools |
| Tools | 11 | 9 |

- Removed: `ctx_execute_file`, `ctx_batch_execute`, `ctx_fetch_and_index`, `ctx_insight`; added `ctx_batch`, `ctx_resume`; `ctx_execute` has `_meta` `anthropic/alwaysLoad`. The four allowed tools keep their names (`raw/mcp/compare-allowed-tools.txt`).
- `ctx_index`: 1.0.169 content, path, source, include, exclude, maxDepth, maxFiles, extensions, respectGitignore, followSymlinks; 2.1.7 path, content, url, source with `additionalProperties: false`. The filter keeps content, path, source, so `url` is stripped and a call with `url` is rejected; the description still says "Required: one of path, content, url"; 2.x checks path containment itself.
- `ctx_search`: 1.0.169 queries, limit, source, contentType, sort; 2.1.7 queries (required), scope (`session`/`worktree`/`project`), source, offset, sort, after. `ctx_stats`, `ctx_doctor`: no inputs.
- Filter breakage: (1) version gate returns `-32002 "Context Mode 1.0.169 required"` and kills the server (`raw/mcp/G1-*.json`); changing the pin cannot fix it because 2.x reports `"dev"`; (2) bare launch prints help (`raw/mcp/G2-*.json`); (3) `instructions` passes unfiltered and tells the model to use `ctx_execute` and that a large Read is denied, both wrong under the kit.
- Agent identity: tool calls need `--agent <id>` or `CLAUDE_PROJECT_DIR` (then `claude-code`; `resolveAgent`, server.mjs:58416); with neither, every call fails "Project source --agent is missing" (`raw/mcp/I1`); `--agent codex` works from cwd (I2); `--agent vscode` needs `--workspace-folder` or MCP roots (I3). The kit renders one shared server command with no host identity into `.mcp.json`, `.codex/config.toml`, `.vscode/mcp.json`, `.agents/mcp_config.json` (from `shared/mcp/servers.json`). Antigravity has no 2.x agent id.
- `ctx_doctor`: D1 goes online; D3 always fails for the kit's wiring ("wrong: MCP entry, hook entries. Fix: context-mode setup --agents claude-code" - running it would install upstream's unfiltered hooks); on failure it writes `<data root>/reports/doctor-<ts>.md` and prints `gh issue create` (`raw/mcp/H1-*.json`). 1.0.169's doctor already suggested `context-mode upgrade`.
- 2.1.7 exits 1 when stdin closes.

Files to change: the filter (version gate, `instructions`, `ctx_index` description), `context-mode-dispatch.sh`, `shared/mcp/servers.json` and `generate_targets.py` (per-host `--agent`), `validate_targets.py` (~2993), `tests/test_context_mode_mcp_filter.py` (34, 103, 416), `shared/policies/tool-routing.instructions.md`.

## 8. Storage and environment

- `CONTEXT_MODE_DIR`: read by 1.0.169, never by 2.1.7. `CONTEXT_MODE_PROJECT_ROOT`: read by neither upstream version (only the kit's filter, line 60). `CONTEXT_MODE_DATA_DIR`: the 2.x data root (`dataRootOf`, server.mjs:29650), default `~/.context-mode`.
- Observed: with only the dispatcher's variables, data went to `HOME/.context-mode/projects/<key>/context.db` plus `reports/`; with `CONTEXT_MODE_DATA_DIR`, to `repo/.claude/.cache/context-mode/projects/<key>/context.db`. Other 2.x files: `hook-errors.log`, `backups/` (setup), `projects/<key>/owners/`.
- 1.0.169 layout: `$CONTEXT_MODE_DIR/content/<hash>.db`, `sessions/<hash>.db`, `sessions/stats-pid-<pid>.json`, temp files under `$TMPDIR`.
- 2.x project key: first 16 hex of SHA-256 of the Git common directory (worktrees share one database). `node:sqlite` schema 6; no 1.x import (`ctx_upgrade`, blocked by the kit, moves v1 folders aside). After a pin bump the dispatcher's provenance check would quarantine the old cache folder.

Files to change: `context-mode-dispatch.sh` (export `CONTEXT_MODE_DATA_DIR`, `FILTER_CONTRACT`), `tests/test_context_mode_dispatch.py` (many `CONTEXT_MODE_DIR` tests), `tests/test_state_sync.py`, `docs/runtime-checks.md`.

## 9. Network

- 1.0.169's MCP server fetches `https://registry.npmjs.org/context-mode/latest` at startup and every hour (`raw/server-1.0.169-split.txt:5734`, called at :6861; 5 s timeout) and prefixes tool replies with the "outdated" notice at most 3 times per hour; no setting turns it off. Its hooks did not touch the network but started the Codex CLI.
- 2.1.7 (strace in the no-network sandbox, `raw/strace/`): 0 outbound attempts for server startup and normal tool calls, 0 for all 32 hook inputs; `ctx_doctor` does DNS lookups (npm dist-tags with 10 s timeout, then `git ls-remote --tags --refs https://github.com/mksglu/context-mode.git "v*"`, server.mjs:28531 and 49650-49730). Other outbound paths (`ctx_index` with `url`, `ctx_execute`/`ctx_batch`, `setup`, `upgrade`) are blocked or never run by the kit. No telemetry code found (`git grep` for telemetry, analytics, posthog, sentry, beacon, insight).

Files to change: `docs/runtime-checks.md`, dispatcher comment (22-28), filter `ALLOWED_TOOLS` if `ctx_doctor` is dropped.

## 10. Writes to user configuration

- Install: 1.0.169's `postinstall` (run by the devcontainer's `npm install -g` without `--ignore-scripts`) can rewrite `~/.claude/plugins/installed_plugins.json`, `~/.claude/settings.json` (`enabledPlugins`), plugin `plugin.json` server entries, and stale `.mcp.json` files, and repairs the better-sqlite3 binding (postinstall.mjs:114-200), only when the upstream Claude plugin is present. 2.1.7 has no install scripts.
- Run time: 2.1.7 wrote only under `~/.context-mode` (`projects/<key>/context.db`, `reports/doctor-*.md`, `hook-errors.log`); it reads `settings.json` files for deny rules but never writes them; client configuration changes only through `setup`, `upgrade`, `ctx_upgrade`. 1.0.169's hooks wrote `~/.claude/context-mode/heal-partial-install.log` and a `~/.codex/tmp/arg0/.../.lock` (from starting the Codex CLI); its server can create folders and symlinks under `~/.claude/plugins/cache` when the plugin is installed (not exercised).

## Go or no-go

What 2.x gives: cleaner install (no native module, no install script, provenance, checksums); no startup or hourly network calls; a working `--version`; no Agent prompt rewrite; better search and upstream containment checks; a maintained release line.

What it costs: (1) Node 24.15+ in the devcontainer, with a real runtime check because install still succeeds on Node 22; (2) per-host `--agent` server arguments, with no Antigravity agent id; (3) a new filter version gate (2.x reports `"dev"`) and stripping or replacing the `instructions` text; (4) `CONTEXT_MODE_DATA_DIR` for project-local storage, old data abandoned; (5) hook-lane rework (PreCompact no-op on Claude and Codex, PreToolUse forwards nothing, output replacement dropped by design, Claude compaction state dropped by the plugin prefix, VS Code needs UserPromptSubmit); (6) a `ctx_doctor` policy decision; (7) fixtures, tests, docs, and a pin-bump procedure that points at the upstream source repository; (8) release churn (11 stable releases in 4 days).

Verdict: no-go as a simple pin bump. A dedicated, fully planned control-plane migration is reasonable once 2.1.x settles. Until then 1.0.169 stays safe, because the dispatcher refuses any other version.

Open questions: real client hook payloads not observed live (Claude Code `persistedOutputPath`, Codex and VS Code key names); how Codex and VS Code name the kit's server tools; Antigravity agent id; whether the rest of the devcontainer works on Node 24; how 2.x keys its project when started inside the nested `.claude` Git repository; whether auto mode would accept `updatedToolOutput` (moot while the filter drops it).
