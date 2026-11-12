# Context Mode 2.1.8 live client checks

**Date:** 2026-11-12. **Kind:** evidence only (no tracked file changed). **Branch tested:** `context-mode-2x-migration_implementation` at `7895856` (all three phases complete).
**Why:** the optional live-client checks in Phases A and B were recorded as NOT RUN. The user asked to try them.

## Method

- Clients: Claude Code CLI 2.1.226 (`claude -p`, model haiku) and Codex CLI 0.147.0 (`codex exec`, model `gpt-5.6-luna`, `-s read-only`, `approval_policy=never`), both started in this repository, so both used the project MCP adapters (`.mcp.json`, `.codex/config.toml`) and the dispatcher's `npx -y context-mode@2.1.8` route (the host's global `context-mode` is 1.x and is refused).
- Traffic capture: a scratch `node` wrapper first on `PATH` tees the filter's stdin and stdout when its first argument is `context-mode-mcp-filter.mjs`, and runs the real `node` otherwise. Scripts and logs: session scratchpad `live/`.
- Direct probes (no client): `pipeline_probe.py` sends `initialize`, `notifications/initialized`, and `tools/list` back to back; `discover_probe.py` sends `server/discover`.

## Results

| Check | Result |
|---|---|
| Claude Code, legacy handshake (4 runs) | PASS: exactly `mcp__context-mode__ctx_index`, `mcp__context-mode__ctx_search`, `mcp__context-mode__ctx_stats`; no `ctx_doctor`; `ctx_index(content)` then `ctx_search` found the word; `ctx_index` with path `docs` got `ctx_index path must be a regular file inside the repository`; `ctx_stats` worked. |
| Claude Code, first run | FAIL: debug log `MCP server "context-mode" Failed to fetch tools: Context Mode server is not initialized`, 3 ms after "connected" with `protocolEra: "modern"`, `negotiatedProtocolVersion: "2026-07-28"`. No Context Mode tool was available in that session. |
| Codex | PARTIAL: tools listed as exactly `mcp__context_mode__ctx_index`, `mcp__context_mode__ctx_search`, `mcp__context_mode__ctx_stats` (hyphen becomes underscore); no `ctx_doctor`. Both `ctx_index` calls ended `user cancelled MCP tool call` and never reached the server; `ctx_search` reached the server. |
| VS Code Copilot | NOT RUN: Copilot Chat cannot be driven from an agent shell. |
| Storage | PASS: data under `.claude/.cache/context-mode/projects/`; the root `.context-mode/` folder is old (last written 2026-10-27, from the user-level Codex server below) and was not touched. |

## Finding 1: a client that does not wait for the initialize reply gets no tools

- Reproduced without any client: `pipeline_probe.py` sends `tools/list` right after `initialize`. The filter answers `tools/list` with `-32001 Context Mode server is not initialized` before the upstream `initialize` reply arrives, then forwards the accepted `initialize` reply. Same result for requested protocol versions `2025-11-25` and `2026-07-28` (upstream negotiates `2025-11-25` either way).
- Cause: `handleClient` refuses `tools/list` and `tools/call` while `serverAccepted` is false, even when an `initialize` is already pending. The same rule existed before the migration (Context Mode 1.x filter), so the migration did not introduce it.
- Why it showed up now: Claude Code 2.1.226 has a newer MCP client path (debug fields `protocolEra`, `negotiatedProtocolVersion`, behind the feature flag `tengu_mcp_protocol_negotiation_stdio` or the setting `MCP_PROTOCOL_NEGOTIATION`). In the failing run it negotiated the "modern" era and asked for tools 3 ms after connecting. The other runs used the legacy path, which waits for the `initialize` reply. Which path a session gets is outside the kit's control.
- The upstream does not implement `server/discover` (it answers `-32601 Method not found`), so the failure is the early request, not a discovery handshake.
- Fail-closed: no tool was exposed and nothing unfiltered reached the client. The cost is that Context Mode is unavailable for the whole session.
- Fix direction: while an `initialize` is pending, hold `tools/list` and `tools/call` requests in a bounded queue and process them in order once the reply is accepted; answer each queued request with the identity error if the reply is rejected; keep the immediate `-32001` when no `initialize` was ever sent. Add a filter test that pipelines `initialize` and `tools/list` and expects the filtered list.

## Finding 2: Codex cancels `ctx_index` in non-interactive runs

- 2.1.8 sends `annotations: {readOnlyHint: true}` for `ctx_search` and `ctx_stats` and no annotations for `ctx_index` (the filter passes boolean hints through unchanged). Codex therefore treats `ctx_index` as a tool that needs approval; with `approval_policy=never` it cancels the call. An interactive Codex session asks the user instead.
- This is correct labeling (`ctx_index` writes to the local store), so the filter must not invent a read-only hint. Options: accept the approval prompt; or, if Codex supports a per-tool approval setting, set it for `ctx_index` in the generated `.codex/config.toml` (a root adapter change, so it needs its own plan).

## Other observations

- Codex's tool names are `mcp__context_mode__ctx_*`; Claude Code's are `mcp__context-mode__ctx_*` (an open question in the 2026-11-11 report).
- The user-level `~/.codex/config.toml` defines its own `[mcp_servers.context-mode]` that runs the global 1.x `context-mode` directly, with `CONTEXT_MODE_DIR` set to this repository's `.context-mode`. In this repository the project entry took over (the capture shows the filter in use), and the dispatcher refuses that `CONTEXT_MODE_DIR` override. In other repositories that user-level entry runs Context Mode 1.x unfiltered; that is the user's own configuration.
- Codex started two server processes in one session (two `initialize` requests in the capture); both went through the filter.

## Correction (2026-11-12, later the same day)

Finding 1's explanation above is wrong; the original text is kept as written.

- The cause is the forwarded MCP 2026-07-28 `server/discover` probe, not a pipelined `tools/list`. Claude Code's newer client path probes a stdio server with `server/discover` first; the filter forwarded it; Context Mode 2.1.8 answers the probe when it carries the 2026-07-28 `_meta` fields (`era_probe-output.txt`, case A: `supportedVersions: ["2026-07-28"]`, `serverInfo` `context-mode`/`dev`, and the full upstream `instructions`). The client then skipped `initialize`, and the filter refused its `tools/list` with `-32001`.
- `discover_probe.py` above sent the probe without `_meta`, so 2.1.8 answered `-32601`; that is why this report wrongly said 2.1.8 does not implement the probe (`era_probe-output.txt`, case B).
- The pipelined-`tools/list` theory cannot produce the logged `negotiatedProtocolVersion: "2026-07-28"`: through `initialize`, 2.1.8 negotiates `2025-11-25`.
- Side effect in the failing session: the probe's answer carried the upstream `instructions` that Phase A removes from `initialize` (they name tools the filter blocks).
- Two independent plan reviews (an Opus devil's-advocate subagent and a GPT-6 Sol agent) reproduced the failure and the fix (answer the probe with `-32601` so the client falls back to `initialize`) against the real 2.1.8; review B read the fallback rule (every probe error other than `-32022` means legacy) from both Claude Code binaries, 2.1.226 and the VS Code extension's 2.1.322.
- The fix is the reopened plan's Phase D (`.claude/plans/2026-11-12_phase-D-context-mode-discover-fallback.md`).
