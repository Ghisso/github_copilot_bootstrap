# Target Mapping

The repo generates two installable outputs: `dist/multi-agent/`, the full
bootstrap, and `dist/sidecar/`, the personal per-clone overlay described
below (both gitignored — run `uv run python scripts/generate_targets.py --all`
to build).

## Devcontainer Bootloader

The generated `.devcontainer/` directory is intended to be committed in consumer
repos. It provides a GPU-capable sandbox and a post-start sync helper that restores
ignored AI bootstrap/state files by checking `.claude/` out from its nested `ai-state`
git branch (see [ADR-002](../plans/adr-002-git-backed-state-sync.md)).

## Shared Basis

Bootstrap maintainers author reusable content in `shared/`. Generation
renders that content into `.claude/` — skills, review profiles, Ponytail
provenance, instructions and Claude policy rules, agents, prompts,
`verify.py`/`record_findings.py`, templates, `MEMORY.md`/plans/session
logs/quality reports/explorations, and hook scripts including the
executable `run-hook.sh` dispatcher — which is the canonical runtime basis
in an installed consumer project. See [Source, generated output, consumer
repo, and nested AI
state](../openwiki/architecture/source-generated-consumer-layout.md) for
the full render sequence and what each rendered path holds.

Keep `.claude/` when pruning optional tool adapters, because it is the shared basis for all supported systems.

Put consumer-specific facts in
`.claude/instructions/project-context.instructions.md`. Preserve consumer-owned
memory, plans, explorations, session logs, and quality reports during refreshes.
`.claude/MEMORY.md` is the curated portable project-memory authority and is
seeded copy-if-absent; an existing consumer file remains byte-identical across
install, update, and migration. Native Claude and Codex memory is optional,
machine-local client state, not generated or synchronized bootstrap state, and
this bootstrap does not disable it. Promote only sanitized, durable,
project-wide facts into the shared file; resolve conflicts in shared narrative
state by manual semantic merge. See [Memory Authority and
Privacy](architecture.md#memory-authority-and-privacy) and
[SECURITY.md](../SECURITY.md).

Passwords, API tokens, confidential material, personal or customer-sensitive
data, and unredacted logs belong in approved protected data systems, never
shared or native memory. Only non-sensitive preferences and scratch may remain
local.

## Native Adapters

Claude Code:

- `CLAUDE.md`
- `.mcp.json`
- `.claude/settings.json`
- `.claude/rules/*.instructions.md` for conditional policy adapters

`CLAUDE.md` is a consumer-neutral generated entrypoint; do not hand-edit it. Claude Code uses `.claude/agents/` and `.claude/skills/` natively and receives the five universal agents.

OpenAI Codex:

- `AGENTS.md`
- `.codex/config.toml`
- `.codex/hooks.json`
- `.codex/agents/*.toml`

`AGENTS.md` is a consumer-neutral generated entrypoint; do not hand-edit it. Codex generates seven project-scoped `.codex/agents/*.toml` files — the five universal agents plus Codex-only `luna_coder` and `sol_coder` — each self-contained with its own pinned model and reasoning effort.

Google Antigravity:

- `AGENTS.md` — provider-neutral root guidance shared with Codex.
- `.agents/agents/` — six static Markdown custom-agent adapters (the five universal agents plus `antigravity_flash_coder`; Codex-only `luna_coder`/`sol_coder` are not emitted here).
- `.agents/skills/` — the shared skill tree. A full install also mirrors each project-owned skill (a `.claude/skills/<name>/` folder with a `.project-skill` marker) here, marker included, so Codex and Antigravity see it after the next refresh. Copilot also reads `.claude/skills/`, so it finds a new project skill without a refresh; once a mirror copy exists, Copilot lists that copy and sees edits after the next refresh.
- `.agents/mcp_config.json` — the shared MCP servers under Antigravity's `mcpServers` schema.
- `.agents/hooks.json` — the named `bootstrap-safety` configuration.

`.agents/` is a bootstrap-owned root adapter, like `.codex/`, with the same pre-write takeover check described in [Installing the bootstrap, file ownership, and runtime drift checks](../openwiki/operations/install-ownership-and-runtime-checks.md).

GitHub Copilot (secondary compatibility adapter):

- `.github/copilot-instructions.md`
- `.github/instructions/*.instructions.md`
- `.github/agents/*.agent.md`
- `.github/hooks/hooks.json`
- `.vscode/mcp.json`

Copilot files are native adapters; agent wrappers preserve Copilot frontmatter and point to `.claude/agents/`, and Copilot generates only the five universal agents.

For the Copilot client (`github-copilot`), the guards print each decision in the answer format that Copilot documents: `permissionDecision` and `permissionDecisionReason` at the top level, with the same two values nested in `hookSpecificOutput`, in one line. The Copilot harness reads the top level under both event spellings. The Local harness reads the nested object (VS Code's Copilot extension 0.74.0 source; not run with the new output). Claude Code, Codex, and Antigravity get the nested object only, with the bytes they always got. The hook file's events stay PascalCase until the Local harness is removed in February 2027.

The context text from `session-start-state.sh` and `record-branch-state.sh` is printed both ways too, so it now reaches the Copilot model. Before this change the Copilot runtime dropped it.

## Gate-Repair Client Parity

Per-client status for the `gate-repair` changes. Clients are listed in the order Claude Code, Codex, GitHub Copilot, Antigravity.

| Change | Claude Code (`claude-code`) | Codex (`openai-codex`) | GitHub Copilot (`github-copilot`) | Antigravity | Evidence |
| --- | --- | --- | --- | --- | --- |
| No Context Mode hooks | None wired | None wired | None wired | None wired | `tests/test_context_mode_dispatch.py`, `tests/test_validate_targets.py` |
| Guarded Context Mode MCP server (three tools) | Root `.mcp.json` guarded; generated targets guarded | Root and generated Codex config guarded | Root `.vscode/mcp.json` guarded; generated targets guarded | No Context Mode entry; the PreToolUse bridge denies MCP calls anyway | `tests/test_validate_targets.py` |
| Hook- and server-config protection (ask on Claude and Copilot, deny on Codex and Antigravity) | `.claude/settings.json`, `.claude/settings.local.json`, `.claude/hooks/`, `.mcp.json` | `.codex/config.toml`, `.codex/hooks.json`, `.codex/hooks/` | `.github/hooks/`, `.vscode/mcp.json`, `.vscode/settings.json`, `.github/copilot/settings.json`, `.github/copilot/settings.local.json`. Local harness: `run_in_terminal`/`send_to_terminal` gated; read tools allowed. Copilot harness: `Bash`, `Write`, `Edit` (object input or patch text), and the shell helpers with a `command` are gated; read tools (`Read`, `view`, `grep`, `rg`, `glob`) get no decision for a config file; see [Copilot harness tools and guard handling](#copilot-harness-tools-and-guard-handling) | `.agents/hooks.json`, `.agents/mcp_config.json` | `tests/test_hook_gates.py`, `tests/test_protect_files_scoping.py`, `tests/test_state_sync.py` |
| Plan checks at branch creation | Shared guard | Shared guard | Shared guard. Local harness: `run_in_terminal`/`send_to_terminal` gated | Antigravity bridge | `tests/test_branch_state.py` |
| Review result and profile gate | Shared `verify.py` gate through `pretool-bash-guard.sh` and the installed Git hooks | Shared `verify.py` gate through `pretool-bash-guard.sh` and the installed Git hooks | `enforce-commit-gate.sh` listed directly; terminal commands covered since the `run_in_terminal`/`send_to_terminal` fix | Through the `antigravity-pretool.py` bridge; native deny never observed | `tests/test_verify.py`, `tests/test_commit_closeout.py`, `scripts/validate_targets.py` installed-hook smoke |
| Shipped commands cannot hide test failures | Shared skills and a `validate_targets.py` check | Same | Same | Same | `tests/test_validate_targets.py` |
| Context7 for subagents | Generated agents with the `search` capability list `mcp__context7` | Inherits session MCP servers ([official Codex subagents docs](https://learn.chatgpt.com/docs/agent-configuration/subagents) and [`openai/codex` source `codex-rs/core/src/agent/role.rs`](https://github.com/openai/codex/blob/7ac954ea24116700632906d89715f7755cd3523e/codex-rs/core/src/agent/role.rs), read 2026-10-17; no native run) | `context7/*` | Unverified: `inheritMcp` is not a documented field | `tests/test_validate_targets.py` |

A hook call from stale wiring (for example a committed `.codex/` or `.github/hooks`) reaches `context-mode-dispatch.sh`, which reads its input, prints nothing, and exits 0. See [runtime-checks.md](runtime-checks.md) for the pin and known limits.

The root `.mcp.json` and `.vscode/mcp.json` start Context Mode through `context-mode-dispatch.sh server`, like the root Codex config, and `scripts/validate_targets.py` fails if a root adapter's `context-mode` entry is not the shared guarded route. The root adapters do not carry Context7 (an authoring-repository choice); generated targets do.

The Copilot Local-harness tool names above (`run_in_terminal`, `send_to_terminal`, and the read tools) come from VS Code's source (`microsoft/vscode` at `9a59550fc841805ebb44cfd5a09b92beed591d15`, read 2026-10-17) and the [VS Code hooks reference](https://code.visualstudio.com/docs/agents/reference/hooks-reference).

Recorded follow-ups:

- The shell guards (branch, commit, PR) parse the payload VS Code's Local harness sends (the supported Copilot client): the model-facing tool name with an object `tool_input`. The Copilot SDK harness and Copilot CLI key casing (`toolName`, `toolArgs`) is not established from official sources. Copilot CLI is unsupported (see [runtime-checks.md](runtime-checks.md)), so this becomes work only if support for either is added.
- Phase C removed the output blocker for a camelCase rename; recheck the input side before renaming.
- Unverified: VS Code may have other command-running tools besides `run_in_terminal` and `send_to_terminal` (for example task tools such as `create_and_run_task`). The shell gates do not treat those as terminal commands. Check a source before changing anything.
- Workspace files outside this repository's root are not protected, like every other control-plane name. A `.code-workspace` file often sits beside the repository, not inside it.
- Codex read-only roles are read-only by instruction only. Codex ignores a custom agent's `sandbox_mode`, so the bootstrap no longer writes it, and the reviewer runs with the parent session's sandbox and approval policy.
- `protect-files.py` is now more than 3,000 lines holding a shell scanner and several command readers in one standalone hook. A later change should split it into modules or shrink it.
- Removing or replacing a whole parent folder (`.claude`, `.github`, `.codex`, `.agents`) gets no decision. Only the protected folders and the files inside them do. Protecting the parents would also deny `git -C .claude add -A`, the documented nested checkpoint.
- Skill folders (`.claude/skills/`, `.agents/skills/`) are not protected, although a Claude Code skill can register `hooks` and pre-approve tools with `allowed-tools` ([skills](https://code.claude.com/docs/en/skills), documented, read 2026-10-20).
- Plain Git commands that the guard does not model and that name a protected path (for example `git restore .claude/hooks` or `git stash push -- .claude/agents/coder.md`) stay denied on all four clients instead of asking. The guard did not loosen any earlier decision. Forms that go through `-C` or `cd` (for example `git -C .claude rm -r -q hooks`) ask on Claude Code and GitHub Copilot and deny on Codex and Antigravity, but only when no path in the command is also protected as written from the repository root. An absolute path (for example `git -C .claude restore <repo>/.claude/hooks/x`), or a command that also names the same file plainly (`git restore .claude/hooks/x && git -C .claude restore hooks/x`), is denied on all four clients.
- The fail-closed rule (big plan `backlog-followups`, decision 6) denies on all four clients some mixed commands that asked on Claude Code and GitHub Copilot before that plan, for example `git restore .claude/settings.json && rm .claude/settings.json`, or `cat > .claude/settings.json <<EOF` whose body names another protected path. Split the command, or write the file with the native Write or Edit tool. Evidence: `tests/test_hook_gates.py`.
- The OpenWiki guard has not been run on Codex against the real OpenWiki server. The 2026-09-19 spike saw Codex honor a `PreToolUse` deny on a test MCP server ([spike](2026-09-19-openwiki-hook-mechanics-spike.md)), but the re-probe in this checkout (deny `mode: "init"`, `noop` on a current wiki, root adapters clean after the turn) was optional evidence and recorded `NOT RUN` in `backlog-followups` Phase F because no Codex session was available. Offline evidence: `tests/test_openwiki_guard.py` and `tests/test_openwiki_cli_smoke.py`.
- The bootstrap wires no Context Mode hooks on any client and gives Antigravity no Context Mode server entry, so Antigravity has no Context Mode lane at all.
- Priority follow-up: the unsafe-destination check does not cover `state-sync.sh`'s own writes: the nested `.gitignore` and `.gitattributes` appends, and the `settings.local.json` restore. A link at one of those paths can still send a write outside the project.
- The unsafe-destination check does not cover hard links.
- Unverified: whether the macOS `strip_quarantine` step (`xattr -rc` over whole folders, consumer state included) follows links.
- The check on substitution files fires even when no rewrite would happen. Narrow it to when a rewrite would fire. A symlinked `AGENTS.md -> CLAUDE.md` is refused today.
- `populate_bootstrap_root` follows links inside the `.codex` and `.github/*` source adapters, and a preserved, tracked adapter that is a link, when it copies them. That is a read, not a write, but the content lands in the AI state, which can then be pushed to the AI-state remote.
- The wrong-kind refusal also refuses kind changes that the obsolete-file cleanup could resolve, for example a regular file at `.claude/templates` or a folder holding an untracked link at `CLAUDE.md`. Narrowing it to unsafe cases is a possible later change. Until then, a bootstrap version that turns a generated file into a folder, or the reverse, makes each refresh refuse until the old item is moved by hand.
- The inactive-adapter removal in `populate_bootstrap_root` and the plain `write_text` calls (the project-name and Python-version files, `.gitignore`, the devcontainer file, and `.claude/bootstrap-ownership.env`) are checked by the preflight only, with no copy-time second line.
- An unmarked folder under `.claude/skills/` whose name the bootstrap ships but that holds no `SKILL.md` is not refused: the refresh overwrites its shipped files and the obsolete-file cleanup deletes its other files as obsolete generated files.
- The commit gate enforces the Task Lanes five-profile review for control-plane, generator, and dependency paths, but not for every multi-file diff. A multi-file diff requires the Ponytail profile only.
- Antigravity needs a logged native run for two open questions. The MCP tool-name format inside a PreToolUse `toolCall.name` is undocumented ([hooks](https://antigravity.google/docs/hooks)), so the bridge keeps denying MCP calls. Subagent MCP access is unverified: the docs describe `mcpServers: object[]` ([subagents](https://antigravity.google/docs/subagents)), not the `inheritMcp: true` the bootstrap writes. A 2026-08 native run reported `agy mcp list` as "No MCP servers configured", and the docs do not explain it. The documented workspace config is `.agents/mcp_config.json` ([MCP](https://antigravity.google/docs/mcp)).
- Bash reads of secret-shaped files such as `cat .env` are allowed, while native read tools on them are denied. This is kept by user decision (2026-10-21) for a later policy choice. The Copilot harness search tools `grep`, `rg`, and `glob` are denied when `paths` names a secret-shaped file (row T1), and are not judged for a search over a folder.
- The 37 `[[skills.config]]` entries are inert. Removing or keeping them is a user decision, and their on/off effect is untested.
- A clone that already exists gets no automatic cleanup of stale `.agents/` content (big plan `skills-and-instructions-trim`, Decision 10).
- The skill listing still overflows on 200K-context models.
- Consumer MEMORY entries that name removed skills (RAG 14, industrial-inspection 1) need an update at each consumer's refresh.
- Consumers installed at `76887a8` (2026-08-22) cannot refresh because of an older takeover rule.
- The typo-bypass allowlist in `shared/hooks/scripts/_lib-frontmatter.sh` does not exclude `.agents/*.md`.

## Backlog-Followups Client Parity

Per-client status for the `backlog-followups` agent-definition protection. Clients are listed in the order Claude Code, Codex, GitHub Copilot, Antigravity. The evidence comes from offline tests and the installed-hook smoke in `scripts/validate_targets.py`. No native client run is recorded for these rows.

| Change | Claude Code (`claude-code`) | Codex (`openai-codex`) | GitHub Copilot (`github-copilot`) | Antigravity | Evidence |
| --- | --- | --- | --- | --- | --- |
| Agent definition protection (ask on Claude and Copilot, deny on Codex and Antigravity; each folder also protected as a whole) | `.claude/agents/`. Native `.claude` protection only reaches the classifier in `auto` and is off in `bypassPermissions`, so the hook still adds a prompt | `.codex/agents/` | `.github/agents/` and `.claude/agents/` (VS Code reads both). Read tools stay allowed, so the wrappers can read `.claude/agents/<id>.md`. In the Copilot harness this includes the read tool's name `Read`, which asked before the Copilot-harness change (row L1 in [Copilot harness tools and guard handling](#copilot-harness-tools-and-guard-handling)), so every sub-agent start asked | `.agents/agents/` | `tests/test_hook_gates.py`, `tests/test_protect_files_scoping.py`, `scripts/validate_targets.py` installed-hook smoke; [Claude Code permission modes](https://code.claude.com/docs/en/permission-modes) (documented) and [VS Code custom agents](https://code.visualstudio.com/docs/copilot/customization/custom-agents) (documented), read 2026-10-20 |
| Hook folders protected as whole folders | `.claude/hooks` | `.codex/hooks` | `.github/hooks` | `.claude/hooks` (the scripts the bridge runs) | `tests/test_hook_gates.py` |
| Workspace files (`*.code-workspace`, any letter case, inside the repository) protected | Same guard; Claude Code does not read the file | Same guard; Codex does not read the file | In a multi-root workspace the file holds the window-scoped hook switches `chat.useHooks`, `chat.hookFilesLocations`, and `chat.useClaudeHooks` ([multi-root workspaces](https://code.visualstudio.com/docs/editing/workspaces/multi-root-workspaces), documented; `microsoft/vscode` `9a59550f` source, read 2026-10-20) | Same guard; Antigravity does not read the file | `tests/test_hook_gates.py`, `tests/test_protect_files_scoping.py` |
| Codex agent `sandbox_mode` removed | Not applicable | Removed: Codex ignores it in a custom agent file. `validate_targets.py` now rejects it as a per-agent override. The reviewer is read-only by its instructions and runs in the parent session's sandbox ([Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents), documented, read 2026-10-20) | Not applicable | Not applicable | `tests/test_validate_targets.py`, `scripts/validate_targets.py` |
| Guard reads shell text as Bash does for quotes, escapes, comments, and line breaks; some forms are not yet checked, listed in [runtime-checks.md](runtime-checks.md) | Same classifier | Same classifier | Same classifier | Same classifier | `tests/test_protect_files_scoping.py`, `scripts/validate_targets.py` installed-hook smoke |
| Guard checks write paths through substitutions, grouped operators, inline `sed` writes, and `cd` folders; some forms are not yet checked, listed in [runtime-checks.md](runtime-checks.md) | Same classifier | Same classifier | Same classifier | Same classifier | `tests/test_protect_files_substitutions.py` |

Reads (`cat`, native read tools, Copilot `read_file`) stay allowed. `rm -rf`, `mv`, and `ln -s` on a whole protected folder ask on Claude Code and GitHub Copilot and are denied on Codex and Antigravity, like an edit. Any command outside the guard's read-only list that merely names a protected path is denied on all four clients, for example `ls`, `find`, `diff`, or `cmp` on an agent file, and `ls .claude/hooks`. An uncertain literal, such as interpreter code that names the path, is denied on every client. `git -C .claude add -A`, `git add -A`, and `git diff --no-index` stay allowed. When one command line names a protected path the guard cannot judge (an "uncertain" hit) and, in another part, a path it can (a "confirmed" hit), the uncertain hit decides and the command is denied on all four clients. A redirect target (`>`, `>>`, `2>`, `&>`, `>|`, also at the start of a command such as `> <hook config>`) counts only as a confirmed hit, so `echo x > <hook config>` still asks on Claude Code and GitHub Copilot. A secret-shaped target (for example `.env`) always denies on all four clients, even beside a hook or server config (`rm .env .mcp.json`) or inside a protected folder (`.claude/agents/.env`), and read tools are denied for it. Inside the older hook folders (for example `.claude/hooks/.env`) this is a tightening: an edit or `rm` asked and a read tool was allowed before this plan; both now deny. For the agent-definition rows above, no earlier decision was loosened (a deny never became ask or allow, and an ask never became allow).

The shell-reading row is different. It deliberately allows some commands the old guard blocked by mistake, for example `grep '>' .env`, which is a read. The later write-path change closed the forms the first change left open. Some commands now get a looser result than after the first change, by design. A word after `|&` is read as a command. Allowed mentions of a protected name are git message text (`git commit|tag|merge -m "..."`, `-am`, `git notes add -m`, `git stash push -m`, and `-m "$(cat <<'EOF' ... EOF)"` when that heredoc is the only command in the `$( )`; `git commit -F - <<'EOF'`), reads by `cat`, `head`, `wc`, `grep`, `rg`, `stat`, `git diff`, `git log --grep`, and `#` comments. Any other command that names it is still denied (`echo '.env'`, `printf`, `gh pr create --body '...'`). A config write through `|&`, `pushd`, or after `cd` gets the protected-config decision (ask on Claude Code and GitHub Copilot, deny on Codex and Antigravity) instead of a deny. The forms the guard still does not check are listed in [runtime-checks.md](runtime-checks.md).

## Copilot harness tools and guard handling

The Copilot harness is the agent runtime that VS Code shares with Copilot CLI. It is the default for new Copilot chats since VS Code 1.143. The Local harness is deprecated and VS Code removes it in February 2027. Both hook files in a project run on the Copilot harness: `.github/hooks/hooks.json` (client `github-copilot`) and `.claude/settings.json` (client `claude-code`). The file guard `protect-files.py` receives every tool call from the first file. The second file sends it only `Edit`, `Write`, and `Bash` calls.

**Hook names.** The hook files use PascalCase events. The runtime then sends the PascalCase tool name and the `tool_input` key. A camelCase event sends the runtime's own tool name and `toolArgs`. The guard reads both. The argument names stay the runtime's (`path`, `file_text`), not Claude Code's (`file_path`, `content`).

**Answer shape.** For `github-copilot`, every guard prints one line with the decision at the top level and nested, for example `{"permissionDecision":"deny","permissionDecisionReason":"R","hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"R"}}`. The context text uses `additionalContext` the same way. There is no top-level `hookEventName`, because the Local harness drops a result whose top-level event name is another event. The library `_lib-frontmatter.sh` and `protect-files.py` write the shape; each printing script names its client, so an exported `TARGET_ID` cannot turn the shape on for another client. The probe session `camel-rename` runs a copy of the project whose hook events have the camelCase names (`sessionStart`, `preToolUse`, `postToolUse`, `agentStop`) and whose `.claude/settings.json` is switched off. With the guards as they were before this change, that session's denies did not happen, and its asks raised no question: the runtime ignored the nested answers under camelCase names. Phase C removed the output blocker for a camelCase rename. The input side (tool names and keys under camelCase events) is a separate check, which the rename itself must repeat.

**Where the names come from.** The runtime tools were run offline on VS Code 1.146.0 with runtime `1.0.108-0`, by `scripts/check_copilot_runtime.py` and by one-off scripted sessions on 2026-11-17, with the real hook files installed. The names `AskUserQuestion` and `tool_search_tool` were seen only in the real VS Code (evidence A4, 2026-11-17). The tools `write_bash` and `bash_shutdown` are named in the source of VS Code's agent host. They were not run.

**VS Code can give a model a tool that the runtime's own list does not.** In the real VS Code, the automatic model choice picked `gpt-6-luna`, and VS Code gave it `apply_patch`, although the runtime's own list gives that model `create` and `edit` (A4). Offline, only Codex-family model ids such as `gpt-5.2-codex` get `apply_patch` and `rg`. So the guard maps tools by their hook name and input, never by model.

The handling column uses three kinds:

1. **No decision.** The tool has no command, path, or code to judge.
2. **Judged by path.** A path key (`path`, `paths`, `file`, ...) or a patch header names a file. A secret-shaped file is denied. A hook, server, or agent file asks on `github-copilot` and `claude-code`, and is denied on `openai-codex` and `google-antigravity`. A read-only tool gets no decision for a config file.
3. **Runs commands or code.** Either its inner steps pass through the pre-tool hooks, or the tool is denied by name.

| Runtime tool | Hook name | Input keys | Handling and proof |
| --- | --- | --- | --- |
| `bash` | `Bash` | `command`, `description`, `shellId`, `mode`, `detach`, `initial_wait` | 3. The command is read by the shell classifier. Unchanged. |
| `read_bash`, `list_bash`, `stop_bash` | same | `shellId`, `delay`; `list_bash` has none | 2, row L2. With no `command` key the input is judged like a native tool: no decision. With a `command` they are shell commands. Probe check `helper-tools`. |
| `write_bash` | not seen | `command` | 3. Shell command; with no `command` it fails closed. Not run offline. |
| `bash_shutdown` | not seen | not seen | 1. The name does not end in `bash`, so it is judged as a native tool: no decision. A `command` on it would not be read. Not run offline. |
| `view` | `Read` | `path`, `view_range`, `forceReadLargeFiles` | 2, row L1. A read tool: a secret-shaped file is denied, a config file gets no decision. Probe checks `deny-secret-view`, `read-agent-file`. |
| `create` | `Write` | `path`, `file_text` | 2. A config file asks or is denied. Unchanged. |
| `edit` | `Edit` | `path`, `old_str`, `new_str` | 2. Unchanged. |
| `apply_patch` | `Edit` | the patch text, a string | 2, rows L3 and T2. Each `Add File`, `Update File`, `Delete File`, and `Move to` header is a target. Probe session `codex-patch`. |
| `grep`, `rg` | `Grep` | `pattern`, `paths`, `glob`, `output_mode`, `type`, `-i`, `-A`, `-B`, `-C`, `-n`, `head_limit`, `multiline` | 2, row T1. Each `paths` entry is judged as a read. `pattern` and `glob` are not judged. Probe checks `search-secret-denied`, `search-glob-not-judged`. |
| `glob` | `Glob` | `pattern`, `paths` | 2, row T1. Same as `grep`. |
| `task` | `Agent` | `description`, `prompt`, `agent_type`, `name`, `model`, `reasoning_effort`, `context_tier`, `mode` | 3. The sub-agent's own tool calls pass through the pre-tool hooks: its `git reset --hard HEAD` is denied. Probe check `subagent-deny-git-reset`. |
| `read_agent`, `write_agent`, `list_agents` | same | `agent_id`, `wait`, `timeout`, `since_turn`; `agent_id`, `agent_ids`, `scope`, `message`; `include_completed`, `scope` | 1. They act on an agent that is already running. |
| `update_todo` | `TodoWrite` | `todos` | 1. A text checklist. |
| `web_fetch` | `WebFetch` | `url`, `max_length`, `start_index`, `raw` | 1. A `file://` address is refused by the tool itself (seen in an offline run). |
| `semantic_code_search` | same | `query`, `repo` | 1. Searches a GitHub repository; it needs a login. |
| `skill` | same | `skill` | 1. Loads a skill by name. |
| `fetch_copilot_cli_documentation` | same | `query`, `ids` | 1. Reads the documentation of the runtime build. |
| `sql` | same | `description`, `query` | 3. SQL on the private session database. Five statements were tried: the tool refuses `ATTACH`, `VACUUM INTO`, `load_extension`, and `PRAGMA database_list` itself, and `writefile` is not a function. No statement tried reached a project file. No guard decision. Probe check `sql-no-file-write`. |
| `session_store_sql` | same | `description`, `query`, `source` | 3. A read-only query on the session store. The tool refuses `CREATE TABLE` and `ATTACH`. Only a sub-agent of type `general-purpose` is offered it offline. No guard decision. Probe check `subagent-store-sql-refused`. |
| `run_dynamic_workflow`, `dynamic_workflows_manage` | same | `name`, `args`, `limits`, `resumeFromRunId`; `operation`, `name`, `runId`, `beforeSeq`, `meta`, `run` | 3, row T4. Denied by name on `github-copilot`. See below. Probe checks `deny-workflow-run`, `deny-workflow-manage`. |
| `ask_user` | `AskUserQuestion` | not recorded | 1. It asks the person a question. Seen only in the real VS Code. |
| `tool_search_tool` | same | not recorded | 1. It searches tool names. Seen only in the real VS Code. |
| MCP tools | `<server>-<tool>` | the server's own | Not offered offline (the probe project has no `.mcp.json`). Unchanged. |

**The workflow tools are denied by name.** A workflow is JavaScript that loads Node modules, spawns agents, and runs in an extension process. An offline session cannot start one: `author` answers "extensions are not configured for session", `run_dynamic_workflow` answers `workflow_not_found`, and a session that asks for extensions fails with "No extension launch provider is registered for standalone extensions", a provider that the probe does not have. So it was not shown whether the code's own steps pass through the pre-tool hooks, and the guard does not guess. On `github-copilot`, both tools are denied with the reason `Tool blocked by policy: <tool> runs workflow code that the pre-tool hooks cannot see`. The guard gives the other clients no decision for these names, because those tools do not reach them. To allow the tools again, a probe step must first show that a workflow's steps pass through the hooks. A later change can narrow the deny to the operation `author` of `dynamic_workflows_manage` and to `run_dynamic_workflow`.

### What changed in the guard for the Copilot harness

Each row is a decision that moved on purpose. Every other decision is the same as before.

| Row | Tool call | Before | After | Why |
| --- | --- | --- | --- | --- |
| L1 | The read tool (`Read`) on a hook, server, or agent file | Ask on `github-copilot` and `claude-code`, deny on `openai-codex` and `google-antigravity` | No decision. A secret-shaped file is still denied. | A deny or ask became allow, on purpose. The policy already says read tools stay allowed. `Read` is the PascalCase name of `view`, which was allowed. Every sub-agent reads `.claude/agents/<id>.md` when it starts, and each read asked. |
| L2 | `read_bash`, `list_bash`, `stop_bash` with no `command` | Deny: `protect-files classifier error: Bash payload has no command` | No decision | A deny became allow, on purpose. They carry only `shellId` and `delay`. They act on a shell that was already judged when it started. |
| L3 | Patch text from `apply_patch` | Deny: the guard stopped on text that is not JSON | The decision of each target in the patch: ask or deny for a hook, server, or agent file, deny for a secret-shaped file. The same patch inside a shell command is denied on every client. | A deny became the normal decision, on purpose. In the real VS Code, every file edit failed for a model that uses the patch tool. |
| T1 | `grep`, `rg`, or `glob` with a secret-shaped file in `paths` | No decision | Deny | Now denied: the read tool is denied on the same file, and the search tools could read it. A search over a folder is still not judged. |
| T2 | A patch header with blanks in front, extra blanks inside, or another letter case | No target, so no decision | The target is judged | Now judged: the runtime applies a patch whose header has blanks in front (in a one-off run on 2026-11-17 it created the file named by an indented `Add File` header), and the old check did not read that header. Other letter cases and inner blanks were not tried on the runtime. The change only adds targets. |
| T3 | A reason or context text that holds a control character (characters 1 to 31, tab and newline included), in the shell guards | Invalid JSON, for every client. On the Copilot runtime, invalid JSON lets the tool run. | Valid JSON with the same decision; each such character is a space | Only the shell guards change (`json_escape` in `_lib-frontmatter.sh`). The file guard `protect-files.py` prints through `json.dumps`, which always escaped control characters: its answer was never invalid JSON, and it still keeps the character (written as `\t`, `\n`, or `\u0001`), not a space. In the shell guards the bytes change only for text that holds such a character. A text that ended in a newline was valid before (the shell dropped the newline); it now ends in a space. The second `tr` set has one space for each of the 31 characters, so the mapping needs no padding rule (POSIX leaves a shorter second set unspecified, and BusyBox `tr` does not read `[c*]`). It was run on GNU `tr` and BusyBox `tr` 1.36.1, not on macOS or BSD `tr`. |
| T4 | `run_dynamic_workflow` or `dynamic_workflows_manage` | No decision | Deny, on `github-copilot` only | Now denied: see above. |

**Folder-wide search and glob filters are not judged.** Only an explicit secret-shaped path in `paths` is denied. A search over `.` or `src`, a `glob` pattern such as `.env*`, a `grep` filter such as `glob: ".env*"`, and a `pattern` that names a secret file get no decision. A secret file inside a searched folder can therefore be read. Shell reads such as `cat .env` stay allowed by the user decision of 2026-10-21.

**Reads are approved by VS Code itself.** When the guard gives a read no decision, VS Code decides. In the real VS Code, the read approvals were given by VS Code (`"decisionSource": "host_policy"`), not by the user (evidence A4).

**Not changed on purpose.** A hook, server, or agent file still asks (or is denied) for every tool that can change it. A patch with no end marker, text that is neither JSON nor patch text, and patch text sent to a read-only tool or a shell tool still fail closed. A line that starts with three asterisks but is not a header does not fail closed, because the context line of an update hunk is the file's own text. The reverse is a known false positive: a context line that spells a header (one space, then `*** Add File: <protected path>` as the file's own text) cannot be told from an indented header, so it is judged as that target. A patch to a document about patches can therefore get an ask or a deny it does not need.

## Sidecar Overlay

`dist/sidecar/` is a second generated target: a narrow, per-clone developer
overlay that `scripts/install_bootstrap.py --mode sidecar` installs inside a
repository whose agent harness a team already owns, without changing any
tracked file. The same installer, with `--uninstall`, removes the overlay
again. See [README.md's Personal Sidecar
Install](../README.md#personal-sidecar-install) for install, update, and
uninstall instructions, and
[docs/sidecar-provider-contract.md](sidecar-provider-contract.md) for the
native-run evidence behind every row below.

`dist/sidecar/` renders two profile trees, one per `--profile` value:
`dist/sidecar/skills/` (today's default) and `dist/sidecar/workflow/`.
`dist/sidecar/skills/` is byte-identical to the pre-profile `dist/sidecar/`
output. `--profile` selects which tree `install_bootstrap.py` reads from by
default (`dist/sidecar/<profile>/`); an explicit `--source` overrides that.

| Projection | Path(s) | Client(s) that read it |
| --- | --- | --- |
| Skill write root | `.claude/skills/<skill>/` | Claude Code; Copilot in VS Code (Local agent and Agent Host) |
| Skill write root | `.agents/skills/<skill>/` | Codex; Copilot in VS Code (Local agent and Agent Host) |
| Skill read-only check (never written) | `.github/skills/`, `.agent/skills/`, `.codex/skills/` | Scanned only to detect a name collision with team-owned content; the sidecar skips a skill at every write root rather than shadow a skill in one of these folders |
| Bridge (`skills` profile) | `.claude/rules/ai-bootstrap-sidecar.md` (no frontmatter) | Claude Code; also loaded by Copilot's Local agent |
| Bridge (`skills` profile) | `.github/instructions/ai-bootstrap-sidecar.instructions.md` (`applyTo: "**"`) | Copilot in VS Code (Local agent and Agent Host) |
| Agent (`workflow` profile) | `.claude/agents/<id>.md` | Claude Code only |
| Rule (`workflow` profile) | `.claude/rules/ai-bootstrap-*.md` | Claude Code |
| Instructions (`workflow` profile) | `.github/instructions/ai-bootstrap-workflow.instructions.md` (`applyTo: "**"`) | Copilot in VS Code (Local agent and Agent Host) |
| Review profile (`workflow` profile) | `.claude/review-profiles/<name>.md` | Claude Code only |
| Template (`workflow` profile) | `.claude/templates/plan-big.md`, `plan-small.md` | Claude Code only |
| State (`workflow` profile) | `.ai-bootstrap/` at the repository root (`MEMORY.md`, `plans/`, `session_logs/`, `explorations/`, `quality_reports/`, each with a README) | Claude Code, Copilot in VS Code, and Codex all read it; it is content, not a discovery mechanism, so every client that opens the file sees it |

The `skills` profile ships the four skills — `debug-investigator`,
`humanize`, `ponytail`, and `ponytail-review` — plus the two bridges above.
The `workflow` profile ships every eligible public skill (a fixed denylist
in `shared/sidecar/workflow/skills.txt` excludes skills that need the full
install; `scripts/runtime_ownership.py` holds the allowlist) plus the agent, rule, instructions, review-profile, template, and
state rows above. No `.github/agents` or `.codex/agents` file ships in
either profile: neither Copilot nor Codex has a config-free way to discover
a custom agent from an ignored file, so those two clients get the workflow
profile's skills and state folder only, never its agents. No bridge or
instructions file ships for Codex (skill-only by design) or for Google
Antigravity (unverified).

The workflow profile includes `onboard` at both skill write roots. After
checking tracked guidance, code, and tests, it writes
`.ai-bootstrap/project-context.instructions.md` and one pointer in
`.ai-bootstrap/MEMORY.md`. The context file's `## Team conventions` section
labels explicit rules separately from patterns inferred from repeated
examples, with evidence and limits. These private notes yield to tracked
team guidance. The `skills` profile does not include `onboard` or this
state folder.

The manifest, staging folder, preserved-copy folder, pending
ownership record, and run lock that track sidecar ownership live inside the
Git directory (`ai-bootstrap-sidecar.json`, `ai-bootstrap-sidecar-staging/`,
`ai-bootstrap-sidecar-preserved/`, `ai-bootstrap-sidecar.json.next`, and
`ai-bootstrap-sidecar.lock`), never in the worktree, so none of them can be
tracked. The manifest is schema version 2 and records `profile`; a
version-1 manifest (no `profile` field) reads as `skills`.

The pending record is written after the ignore proof passes and
before any unit moves, and removed once the real manifest lands — extra
ownership evidence for a rerun after an interrupted run, never an
instruction on its own. The run lock is held from just after preflight to
the end of the run and stays in place, empty, afterward; a dry run takes
neither. All five paths are built from the same already-verified `git
rev-parse --path-format=absolute --git-dir` value, never through `git
rev-parse --git-path`: `--git-path` resolves a symlink in the path before
printing it, which would hide exactly the symlinked Git-directory case the
sidecar's own preflight checks exist to catch. The preserved folder holds an
edited sidecar copy that a taken skill name displaced; see
[README.md's Personal Sidecar Install](../README.md#personal-sidecar-install)
for its naming and recovery, and its [Uninstall
section](../README.md#personal-sidecar-install) for `--uninstall`, which
removes the manifest and staging folder but leaves the preserved folder in
place.

The state unit (`.ai-bootstrap/` at the repository root, `workflow` profile
only) follows its own rules, not the ordinary unit rules above: seeded
once, from its seed files, when the folder is absent; an existing folder
only ever gets a missing seed file added, never a comparison or an
overwrite; kept in place and hidden by plain `--uninstall`; moved into the
preserved-copy folder and un-hidden only by `--uninstall --purge-state`;
copied to the preserved-copy folder, without uninstalling anything, by the
standalone `--backup-state` action. It lives at the repository root, not
under `.claude/`, because Claude Code refuses agent writes anywhere under
`.claude/`; an earlier workflow install's `.claude/ai-bootstrap/` folder is
migrated into it automatically on the next install or update when the
sidecar's own exclude block already shows it as owned — see
[docs/sidecar-provider-contract.md](sidecar-provider-contract.md), "Workflow
state write gate, 2026-10-02". See [README.md's Personal Sidecar
Install](../README.md#personal-sidecar-install), "The state folder", for
the exact messages each case prints and the `git clean -x` risk it
mitigates.

See [Agent roster, prompts, and the skill
library](../openwiki/architecture/agents-and-skills.md) for how each
target renders an agent from the same `shared/agents/<id>/` metadata,
including the Codex prompt-composition rules, the per-agent model/effort
matrix (also in [Custom Agents](architecture.md#custom-agents)), and the
Antigravity `mainAgent`/`subagent` layout. See [Hook dispatcher and
guardrail scripts](../openwiki/architecture/hooks-and-guardrails.md) for
the shared `PreToolUse` safety lane every target routes through, including
the Antigravity Python bridge.
