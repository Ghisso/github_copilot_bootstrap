# Copilot harness migration: evidence report

**Date:** 2026-11-17. **Kind:** evidence only; no tracked file was changed.
**Asked by the user:** "I want migration so investigate well first!"
**Bootstrap under test:** `dev` at `2e8c7bb`, installed into a scratch probe project
with `scripts/install_bootstrap.py <probe> --mode full --local-only`.

## Short answer

1. VS Code is removing the "Local" harness, the only Copilot mode this
   bootstrap supports, in February 2027. The "Copilot" harness has been the
   default for new chats since VS Code 1.143. This computer runs 1.146.0, so
   new Copilot chats here most likely already use the Copilot harness.
2. The bootstrap's guards already work on the Copilot harness runtime. The
   earlier estimate ("the guards must be rewritten for a new tool-call
   format") was wrong. The existing hook file is accepted as it is, and
   the guards gave the expected result in 16 of 16 scripted tool calls.
3. Six real problems were found. None needs a guard rewrite:
   - every hook runs twice, because the runtime also loads the Claude Code
     hook settings (F2);
   - the guards answer in a format that works only by an undocumented
     compatibility rule, and a rename to the documented event names would
     silently switch every deny off (F4);
   - with the six Codex-family models every file edit is refused, because the
     guard crashes on the patch tool's input (F6);
   - sub-agents (`coder`, `reviewer`, and the others) receive none of the
     repository instructions and no skill list (F9);
   - the root guidance is loaded three times (F10);
   - the search tools can read a secret-shaped file that the read tool
     cannot (F7).
4. A repeatable, offline test of the real runtime is possible. It needs no
   GitHub account and makes no model call (F16). This closes the "no proof
   on the real client" gap.

## How the evidence was gathered

"Harness" means the part of the client that runs the agent, calls tools, and
runs hooks.

| Label | Meaning |
| --- | --- |
| **Run** | Seen in a live run of the Copilot runtime that ships inside this computer's VS Code. |
| **Source** | Read in the installed VS Code 1.146.0 files (the agent host program and the runtime's type files). |
| **Docs** | Official VS Code or GitHub documentation, read on 2026-11-17 by two research agents. Quotes are exact. |
| **Not checked** | Needs a person in a real VS Code window. Listed in "Checks that need you". |

Versions (all found on disk under `~/.vscode-server/bin/69047191…/`):

- VS Code `1.146.0`, commit `69047191fc427f2f92828279aae1d90d8eeda7ab`.
- `@github/copilot-sdk` `1.0.30-preview.0` with the native runtime, which
  reports version `1.0.108-0`, protocol 3.
- Built-in `copilot` extension `0.74.0`, holding `@github/copilot` `1.0.73`.

Method for the **Run** rows: `scripts/step3_session.mjs` starts that runtime
through its own SDK with a private data folder (`baseDirectory`), no login
(`useLoggedInUser: false`), and the SDK's custom model `provider` option
pointed at a small local server that returns scripted tool calls. The runtime
then does everything a real session does: it loads hooks, instructions,
skills, agents, and MCP servers, runs the tools, and runs the hooks. Probe
hooks (`scripts/hooklog.sh`) record the exact input each hook receives and can
send scripted answers back. The environment variables of the Claude Code
session that ran the spike were removed before starting the runtime.

Limit of this method: it exercises the runtime, not VS Code's own layer on
top of it (the approval dialogs, the tools VS Code adds, what VS Code
forwards). Those points are marked **Not checked** or **Source**.

## Findings

### F1. The Local harness is being removed (Docs)

- "The Local harness is deprecated and will be removed in February 2027.
  Move your workflows to the Copilot harness before then."
  (<https://code.visualstudio.com/docs/agent-customization/hooks>)
- Release notes 1.146 (2026-11-11): "As of this release, the Local harness
  is deprecated and will be removed in three months (February 2027)" and
  "it's functionally frozen". (<https://code.visualstudio.com/updates/v1_146>)
- "The Copilot harness is our latest agent harness and has been the default
  for new sessions since VS Code 1.143." (same page)
- Hooks get no automatic conversion: "**Hooks**: there is no automatic hook
  migration." and "A file can load in the Copilot harness while its script
  no longer matches a tool, reads the wrong arguments, or returns an output
  the destination does not use."
  (<https://code.visualstudio.com/docs/agent-customization/migrate-customizations>)
- `chat.useHooks`, `chat.hookFilesLocations`, and `chat.useClaudeHooks`
  apply to Local only: "Local settings such as `chat.useHooks` do not
  prevent the Copilot harness from loading a configuration."
- VS Code, the GitHub Copilot app, and GitHub Copilot CLI "share this
  harness and its hook format".

### F2. Every hook runs twice (Run, Docs, Source)

After the probe folder is trusted, `hooks.discover` returns, with no warning
and no error (`raw/discover-after-trust-hooks-and-mcp.txt`):

| Source file | Hook actions | Events |
| --- | --- | --- |
| `.github/hooks/hooks.json` (the Copilot adapter) | 12 | `sessionStart` 3, `preToolUse` 5, `postToolUse` 1, `agentStop` 3 |
| `.claude/settings.json` (the Claude Code adapter) | 14 | `sessionStart` 3, `userPromptSubmitted` 2, `preToolUse` 3, `postToolUse` 3, `postToolUseFailure` 1, `agentStop` 1, `sessionEnd` 1 |

Docs confirm it: "It also reads repository `.claude/settings.json` and
`.claude/settings.local.json`" and "When the same event appears in multiple
sources, all hook entries from all sources are run." No documented switch
turns off only the Claude files. The VS Code agent host lists the same four
settings files as hook sources (Source).

Effects seen in the run with both sources (`raw/outcomes-g-both.txt`,
`raw/session-log-double-entries.txt`, `raw/hook-timing.txt`):

- A protected-file edit asks for approval twice.
- One Copilot session is written to `hooks-sessions.log` as two sessions,
  `target=github-copilot` and `target=claude-code`.
- State sync pull and push each run twice.
- Session start takes 1.72 s instead of 0.85 s.

A hook can tell which program started it. The Copilot runtime sets
`COPILOT_CLI=1`, `COPILOT_PROJECT_DIR`, `COPILOT_HOOK_DEPTH`, and also
`CLAUDE_PROJECT_DIR`. File hooks also get `COPILOT_HOOK_DIR`; hooks from the
Claude settings file do not (`raw/hook-inputs-from-claude-settings.txt`).

### F3. The guards already work (Run)

With only `.github/hooks/hooks.json` active, 16 scripted tool calls gave the
expected result every time (`raw/outcomes-g-copilot.txt`):

| Tool call | Result |
| --- | --- |
| `git reset --hard HEAD`, `git push --force origin dev` | Denied: "Blocked dangerous git operation" |
| `rm -f .env`; read of `.env` with the read tool | Denied: "Protected file blocked by policy: .env" |
| Create `.vscode/settings.json`; `echo '{}' > .github/copilot/settings.json`; edit `.claude/agents/coder.md`; edit `.github/agents/coder.agent.md` | Approval asked once (permission kind `hook`) |
| `git checkout -b probe_implementation` | Denied by the branch guard |
| `git commit ...` | Denied: "commit gate failed for github-copilot: ..." |
| `gh pr create ...` | Denied by the pull-request gate |
| Plain `echo`, read, create, edit, and an MCP tool | Allowed |

Why it works: the hook file uses PascalCase event names (`PreToolUse`,
`Stop`). The runtime accepts them and then sends the Claude-style input,
which the guards already read (F8). The same guards also work when loaded
from `.claude/settings.json` alone (`raw/outcomes-g-claude.txt`), with one
difference: the read of `.env` is not denied there.

The guard phase is fast: at most 0.25 s per tool call with one source and
0.37 s with both, against the 10 s limit in the hook file.

### F4. The answer format works only by a compatibility rule (Run, Docs)

The guards print one shape:
`{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":...}}`
(`shared/hooks/scripts/_lib-frontmatter.sh:39-45`,
`shared/hooks/scripts/protect-files.py:3652`). Tested with probe hooks
(`raw/outcomes-d1.txt`):

| Hook answer | Event named `preToolUse` | Event named `PreToolUse` |
| --- | --- | --- |
| Top-level `permissionDecision: "deny"` | Denied | Denied |
| Nested `hookSpecificOutput.permissionDecision: "deny"` | **Ignored: the tool ran** | Denied |
| Top-level `"ask"` | Approval asked | Approval asked |
| Nested `"ask"` | not tested | Approval asked |
| Top-level `modifiedArgs` / nested `updatedInput` | Arguments replaced | Arguments replaced |
| `{"decision":"block"}` or `{"continue":false}` | not tested | Ignored: the tool ran |
| A `PreToolUse` hook denies and a `preToolUse` hook allows the same call | Denied (deny wins) | Denied (same call) |

The documentation names only the top-level shape and warns: "accepting a
PascalCase input alias does not establish support for every Local
`hookSpecificOutput` field. Emit the documented Copilot output."

Consequence: today's denies depend on an undocumented rule. A change of the
hook file to the documented camelCase names, with no change to the guards'
output, would let every tool call through with no error.

### F5. What happens when a hook fails (Run, Docs)

| Case | Result |
| --- | --- |
| Hook exits 2 | Denied: "hook exited with code 2" |
| Hook exits 1 | Denied: "(hook errored)" |
| Hook prints text that is not JSON, exits 0 | **Tool runs** |
| Hook runs longer than its time limit | **Tool runs** (`HookTimeoutError`) |
| Hook asks, and no person can answer | Denied: "(unable to ask user for confirmation)" (`raw/outcomes-a1.txt`) |

Docs agree: "Command hook **timeouts are always fail-open**" and a non-zero
exit "denies the tool call". The default time limit is 30 seconds; the
bootstrap sets 10. Docs also say that autopilot mode denies an `ask`.

### F6. Codex-family models: every file edit is refused (Run)

The runtime's catalog has 69 models. 63 get the tools `create` and `edit`.
Six (`gpt-5-codex`, `gpt-5.1-codex`, `gpt-5.1-codex-max`,
`gpt-5.1-codex-mini`, `gpt-5.2-codex`, `gpt-5.3-codex`) get `apply_patch`
and `rg` instead (`raw/tools-by-model.txt`).

`apply_patch` is a free-form tool. Its hook input is the patch text as a
string, not an object (`raw/hook-inputs-patch-tool.txt`):

```json
{"hook_event_name":"PreToolUse","tool_name":"Edit","tool_input":"*** Begin Patch\n*** Add File: probe-patch.txt\n+plain file\n*** End Patch\n"}
```

`protect-files.py:3668-3669` runs `json.loads` on a string `tool_input`. The
patch text is not JSON, so the classifier stops with
`protect-files classifier error: Expecting value: line 1 column 1 (char 0)`
and the guard fails closed. All five patch calls were denied, including a
harmless new file (`raw/outcomes-c1.txt`, `raw/guard-errors-patch-tool.txt`).
This is safe but makes those models unusable. The file already has a parser
for `apply_patch` text inside shell commands (near line 910).

### F7. Search tools can read a secret-shaped file (Run)

The read tool on `.env` is denied. `grep` and `rg` with `paths: [".env"]`,
and `glob` with `.env*`, get no guard decision; only the runtime's normal
read approval applies (`raw/outcomes-s1.txt` steps 17-18,
`raw/outcomes-c1.txt` step 6). Shell reads such as `cat .env` are already
allowed by a recorded user decision (2026-10-21), so this is the same policy
question, on new tools.

### F8. Tool names and inputs (Run)

The event name chooses the input format:

| | camelCase event (`preToolUse`) | PascalCase event (`PreToolUse`) |
| --- | --- | --- |
| Tool name key | `toolName` | `tool_name` |
| Tool input key | `toolArgs` (an object; a string for `apply_patch`) | `tool_input` (same value) |
| Other keys | `sessionId`, `timestamp` (number), `cwd`, `toolCallId` | `hook_event_name`, `session_id`, `timestamp` (ISO text), `cwd`, `tool_use_id` |
| In a sub-agent | `agentId`, `agentType`, `parentAgentId` | `agent_id`, `agent_type`, `parent_agent_id` |

| Runtime tool | Arguments | Name in a PascalCase hook |
| --- | --- | --- |
| `bash` | `command`, `description`, `shellId`, `mode`, `detach`, `initial_wait` | `Bash` |
| `view` | `path`, `view_range` | `Read` |
| `create` | `path`, `file_text` | `Write` |
| `edit` | `path`, `old_str`, `new_str` | `Edit` |
| `apply_patch` | patch text | `Edit` |
| `grep`, `rg` | `pattern`, `paths`, `glob`, ... | `Grep` |
| `glob` | `pattern`, `paths` | `Glob` |
| `task` (start a sub-agent) | `description`, `prompt`, `agent_type`, `name`, `model`, `reasoning_effort`, `mode` | `Agent` |
| MCP tool | the server's own | `<server>-<tool>`, for example `semble-search` |

The argument names stay the runtime's (`path`, `file_text`), not Claude
Code's (`file_path`, `content`). `shared/hooks/scripts` already reads both
name keys and both input keys.

Source: VS Code's agent host can replace the shell tool with its own tools
named `bash`, `read_bash`, `write_bash`, and `bash_shutdown` (`powershell`
on Windows). `write_bash` sends text to a running shell in its `command`
argument. The guards treat any tool name that ends in `bash` as a terminal
tool.

### F9. Custom agents (Run, Docs, Source)

- The five wrappers in `.github/agents/` load. The copies in
  `.claude/agents/` are also found and lose to the wrappers by name.
- Tool aliases map as expected. As a sub-agent, `reviewer` gets only `view`,
  `grep`, `glob`, and the MCP tools; `bash` and `create` answer "Tool ...
  does not exist". The read-only reviewer is enforced by the runtime, which
  is stronger than on Codex.
- Guards also run for tool calls inside a sub-agent.
- `subagentStart` and `subagentStop` fire for the custom agents.
- **Sub-agents get no repository instructions.** `coder` and `reviewer`
  received 0 lines of `AGENTS.md`, `CLAUDE.md`, and
  `.github/copilot-instructions.md`, no skill list, and (for `coder`) no
  `skill` tool. They receive only the three-line wrapper, which tells them
  to read `.claude/agents/<name>.md` (`raw/subagent-context.txt`). Docs
  confirm it and add that the opt-in field `include-custom-instructions` is
  one VS Code does not forward.
- The orchestrator, when selected as the session agent, gets everything,
  including the `task` tool.
- Docs: the Copilot harness does not accept `handoffs`, `agents`, or
  `argument-hint`. The wrappers carry `agents:`; the runtime loads them and
  ignores the field. There is no documented way to limit which sub-agents a
  coordinator may call.
- Docs and Source: `model` and `reasoning-effort` are supported agent
  fields. `scripts/generate_targets.py:1575` already writes a model when the
  agent metadata is not `target-default`.
- Docs: the setting `github.copilot.chat.cli.customAgents.enabled`
  ("Enable using custom agents in Copilot harness sessions", default
  `false`) exists. What it gates today is **Not checked**.

### F10. Instructions (Run, Docs)

The runtime puts all of these into the system prompt
(`raw/instructions-in-system-prompt.txt`): `.github/copilot-instructions.md`
(1,676 bytes), `AGENTS.md` (4,740), `CLAUDE.md` (4,409), and the always-on
files in `.github/instructions/`. The three root files say largely the same
thing, so about 10.8 KB of a 48.6 KB system prompt is root guidance loaded
three times. The path-scoped files in `.github/instructions/` and
`.claude/rules/` are both listed for on-demand loading, so those five
policies are offered twice. What VS Code forwards on top of this is
**Not checked**.

### F11. Skills (Run)

The runtime looks in `.github/skills`, `.agents/skills`, `.claude/skills`,
and `~/.copilot/skills`. It found 37 skills, all from `.agents/skills`, with
no duplicates. The `skill` tool loaded `caveman` correctly.

### F12. MCP servers (Run, Docs)

The runtime reads `.mcp.json` at the project root, the file the bootstrap
writes for Claude Code. All three servers connected. The Context Mode filter
held: exactly `context-mode-ctx_index`, `context-mode-ctx_search`, and
`context-mode-ctx_stats`. The runtime does not read `.vscode/mcp.json`. Docs:
"Eligible existing definitions can be forwarded, but the harness doesn't
read those files directly." Whether VS Code then offers each server once or
twice is **Not checked**.

### F13. Adding text for the model from a hook (Run, Docs)

| Hook and answer | Reached the model? |
| --- | --- |
| `sessionStart`, top-level `additionalContext` | Yes |
| `SessionStart`, nested `hookSpecificOutput.additionalContext` | No |
| `userPromptSubmitted`, top-level `additionalContext` | **Yes in this run**; Docs say this output is dropped |
| `UserPromptSubmit`, plain text | No |
| `postToolUse` / `PostToolUse`, top-level `additionalContext` | Yes, appended to the tool result |
| `PostToolUse`, nested | No |
| `agentStop`, `{"decision":"block","reason":...}` | Yes: the reason starts another turn |

So the reporting reminder can be given at session start (documented). A
reminder at every prompt worked on runtime `1.0.108-0` but contradicts the
documentation, so it cannot be relied on without a VS Code check. The
bootstrap's reminder prints the nested shape, which is ignored here.

### F14. Events (Run, Docs)

`agentStop` fires at the end of every turn, like Claude Code's `Stop`.
`sessionEnd` fires once when the session closes. Also seen:
`postToolUseFailure`, `permissionRequest`, `notification`, `preMcpToolCall`,
`userPromptTransformed`, `subagentStart`, `subagentStop`. The bootstrap's
session log, session check, and state sync hooks ran without error.

### F15. Trust (Run, Source)

Repository hooks and the `.mcp.json` servers load only when the runtime
trusts the folder. Before trust, `hooks.discover` returned 0 hooks and
`mcp.discover` 0 servers; skills, agents, and instructions loaded anyway.
VS Code's agent host passes `trustWorkingDirectory` when it creates a
session in a trusted workspace (log text: "Granting the runtime '...' trust
for trusted working directory"), so a trusted VS Code workspace gets the
hooks.

### F16. Proof on the real runtime can be automated (Run, Docs)

- The harness in `scripts/` runs the real runtime offline, with no account;
  each scenario here finished in under a minute. It could become a third
  client in
  `scripts/check_native_clients.py`, pinned to an `@github/copilot-sdk`
  version, or stay an opt-in probe that uses the copy inside VS Code.
- Docs: Copilot CLI has a one-shot mode, `copilot -p "PROMPT"`, with
  `--trust-folder`, `--agent`, and `--output-format=json`. It needs a token
  with the "Copilot Requests" permission. It is not installed here, and `gh`
  is not logged in.

## What the migration has to do

These are inputs for a plan, not a plan. Every item touches hooks, the
generator, or the installer, so the work is control-plane and needs a full
plan with the five review profiles.

| # | Work item | Why | Size |
| --- | --- | --- | --- |
| 1 | Stop the double hook run on the Copilot harness | F2 | Small to medium |
| 2 | Make the guards print the documented top-level answer (and decide whether to keep the nested one for the other clients) | F4 | Medium: every guard and its tests |
| 3 | Read the patch tool's text input | F6 | Small |
| 4 | Decide whether the search tools may read secret-shaped files | F7 | Small; a policy choice first |
| 5 | Give sub-agents the rules they need, and remove the wrapper fields the harness does not accept | F9 | Medium |
| 6 | Load the root guidance once for Copilot | F10 | Small to medium |
| 7 | Decide what happens to `.vscode/mcp.json` | F12 | Small |
| 8 | Reporting reminder at session start; wiki guard only if Copilot gets the wiki server | F13 | Small |
| 9 | Add the offline runtime test, and one short manual VS Code checklist | F16 | Medium |
| 10 | Rewrite the Copilot claims in `README.md`, `docs/target-mapping.md`, `docs/runtime-checks.md`, `docs/smoke-tests.md`, and recheck the sidecar's Copilot contract | F1 | Medium |

Design points the plan must settle with evidence:

- For item 1, a hook started from the Claude settings file can stop early
  when `COPILOT_CLI=1` is set. The other way is to drop the Copilot hook
  file and let the Claude settings serve both clients; that would label
  Copilot sessions as `claude-code` and lose the `.env` read deny (F3).
- For item 2, check that Claude Code, Codex, and the Antigravity bridge
  accept an answer that carries both shapes before printing both.
- Keep the PascalCase event names until item 2 is done. Changing the names
  first would switch the denies off (F4).
- The Local harness stays until February 2027. The plan must say whether the
  bootstrap supports both during that time or moves at once.

## Checks that need you (Not checked)

Each needs a signed-in VS Code window on a trusted test folder with the
bootstrap installed. `scripts/setup_probe_hooks.mjs <folder> <path to
hooklog.sh> both` adds the logging hooks used here.

1. A new chat shows "Copilot" in the harness picker, and
   `git reset --hard HEAD` is denied there.
2. Whether a protected-file edit asks once or twice, and what the question
   looks like. What it does under "Allow all" and in Autopilot.
3. The tool names the hooks see in VS Code, above all the shell tool and
   any tool VS Code adds.
4. Whether each MCP server appears once or twice.
5. Whether the five custom agents are listed, and whether
   `github.copilot.chat.cli.customAgents.enabled` must be on.
6. Whether text from a `userPromptSubmitted` hook reaches the model.
7. When `sessionEnd` fires (closing the chat, closing the window).

## Addendum, 2026-11-17 16:40: first attempt at the VS Code checks

The user opened the test folder `~/copilot-harness-probe-20261117` in VS Code
1.146.0. The Local harness worked; switching to the Copilot harness or
opening a new session froze. Two facts came out of the logs.

**A1. The freeze is an environment fault, not a bootstrap fault (Source:
VS Code's own logs).** The VS Code process that runs Copilot-harness
sessions (the "agent host") could not start. `agenthost.log` under
`~/.vscode-server/data/logs/20261117T151427/` shows 198 starts, each ending
in `listen EACCES: permission denied
/run/user/1000/vscode-ipc-<id>.sock`. The folder `/run/user/1000` did not
exist in that WSL session (`XDG_RUNTIME_DIR` pointed at it;
`user-runtime-dir@1000.service` and `user@1000.service` were inactive;
`loginctl` listed no session). The same loop is in the logs of 2026-10-26 and
2026-11-12, and absent from seven other VS Code server sessions, where the
agent host listened on a socket under `/tmp`. No hook ran in any
Copilot-harness session on this computer during the attempt, so the three
checks are still open.

**A2. On this computer the Local harness also runs the Claude Code hooks
(Run, in the real VS Code).** The user's VS Code settings contain
`"chat.useClaudeHooks": true`. VS Code's `GitHub Copilot Chat Hooks.log`
shows "[SessionStart] Executing 8 hook(s)": three from
`.github/hooks/hooks.json`, three from `.claude/settings.json` (with the
`claude-code` argument), and the two probe loggers. So the double run of F2
already happens on the Local harness here. In that Local run the hooks'
environment had no `COPILOT_CLI=1` (only
`COPILOT_CLI_ENABLED_FEATURE_FLAGS` and `COPILOT_OTEL_FILE_EXPORTER_PATH`),
and every hook, camelCase-named or not, received the Local format
(`hook_event_name`, `session_id`, `transcript_path`). The reporting reminder
from the Claude settings ran at `UserPromptSubmit` and returned its nested
`additionalContext`.

## Corrections to earlier statements in this session

- "The guards must read a different tool-call format" was wrong. They read
  it already (F3, F8).
- "The Copilot harness also reads `.claude/settings.json`, so the hooks
  could run twice" is confirmed (F2).
- "Both harnesses give no way to add text for the model at prompt submit"
  is not settled: it worked in the run and the documentation says it does
  not (F13).

## Files in this folder

- `scripts/`: the harness. `run.sh <name> <scenario.json> <both|copilot-only|claude-only|probe-only>`
  copies the probe project, sets the hook sources, and runs one scripted
  session. Paths inside are specific to this computer.
- `raw/`: the text outputs cited above. Machine paths are replaced.
- `research/github-docs-runtime-contract.md`: the GitHub documentation
  research, with quotes and URLs. The VS Code documentation quotes are in
  the findings above.

The probe project, the private runtime data folder, and the full event logs
stayed in the session scratch folder and are not kept.
