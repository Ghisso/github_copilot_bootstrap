

######## v2.1.8 published 2026-11-11T22:09:13Z prerelease=False
### Fixes
- fix: quote the search.mjs line as POSIX single-quoted words (#1358, #1342)
- fix: OpenCode 2 subagent tool set and in-process replace (#1348, #1347)
- fix: Claude Code replace pointer names only tools the caller can call (#1342, #1358)
- fix: setup keeps the MCP and global OpenCode entry when only a project .opencode/plugins file loads twice, and its Fix: line names that file (#1349)
- fix: the CLI Fix: line names the OpenCode project plugins file to remove; doctor does not offer setup for it (#1349)
- fix: only the OpenCode config plugins dir decides the global entry; a project plugins file next to it names the file to remove (#1349)
- fix: OpenCode project .opencode/plugins file counts for setup, and a dir file with no package is no entry (#1349)
- fix: an OpenCode plugins dir file of ours counts as the hooks entry (#1349)
- fix: OpenCode 2 bare native entry plugins:["context-mode"] counts as the hooks entry (#1344)
- fix: OpenCode 1.x list check reads debug config --pure, not the slow mcp list (#1362)
- fix: isOwnFile checks for .. on the raw tool path, before resolve (#1345)
- fix: a skill file under a symlinked skill dir reaches the model whole (#1345)
- fix: main's build script stops a 1.0.x upgrade before any write (#1363)
- fix: Codex D4 keeps user tool approval tables and user hooks/codex/*.mjs hooks (#1359 #1364)
- fix: ctx_search treats a blank source as absent (#1354)
- fix: ctx_search accepts offset:0/after:0, ctx_resume treats a blank session as absent (#1354, #1353)
- fix: copilot-cli is SKIPPED with npm install -g @github/copilot when VS Code's copilot launcher has no CLI (#1360)
- fix: Pi tool_result keeps details and structuredContent, contextMode.excludeTools keeps a tool whole (#1352)

### Performance
- perf: keep own-dir root components, skip resolve for absolute POSIX paths (#1345)

### Who gets this

One version on both channels: the release commit on main (GitHub) and npm.

| Agent | Channel | Update with |
|---|---|---|
| Claude Code | GitHub | `claude plugin update context-mode@context-mode` |
| Codex | GitHub, npm for the one-time hook trust step | `codex plugin marketplace upgrade context-mode` |
| Gemini CLI | GitHub | `gemini extensions update context-mode` |
| Qwen Code | GitHub | `qwen extensions update context-mode` |
| Copilot CLI | npm | `context-mode upgrade` |
| VS Code (Copilot) | npm | `context-mode upgrade` |
| Kiro | npm | `context-mode upgrade` |
| ZCode | GitHub | `zcode plugins update context-mode@context-mode` |
| Pi | npm | `pi update --extensions` |
| OpenCode | npm | `opencode plugin update` |