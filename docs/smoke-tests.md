# Smoke Tests

## Deterministic Generation

```bash
uv run python scripts/generate_targets.py --all
uv run --with pytest python scripts/validate_targets.py
```

The validator runs the hook smoke tests with `pytest`; use the explicit
`--with pytest` invocation above when it is not already installed in the
environment.

Expected:

- Validator prints `PASS generated target is structurally valid`.
- Re-running generation does not change generated output.

## Custom Agent Portability

Expected:

- GitHub Copilot has exactly the 5 universal `.github/agents/*.agent.md` files.
- Claude Code has exactly the same 5 universal `.claude/agents/*.md` files.
- OpenAI Codex has exactly 7 `.codex/agents/*.toml` files: the 5 universal
  agents plus Codex-only `luna_coder` and `sol_coder`.
- Neither Codex-only agent appears in `.claude/agents/` or `.github/agents/`,
  and omitting either one from `.codex/agents/` fails validation.
- Google Antigravity has exactly six structural `.agents/agents/*/agent.md`
  adapters: the five universal roles plus `antigravity_flash_coder`. It does not
  include Codex-only `luna_coder` or `sol_coder`.
- Antigravity's declared configuration uses Flash for the Flash coder and
  documenter, and Pro for orchestrator, planner, canonical coder, and
  reviewer. The Flash coder's only configured escalation is to the Pro coder.
  These checks do not prove native model routing or escalation.
- Root `AGENTS.md` is provider-neutral guidance shared by Codex and
  Antigravity. `.agents/skills/` and `.agents/mcp_config.json` are structural
  copies of the canonical skill tree and MCP registry. `.agents/rules/` is
  absent until an exact native rule schema is verified.
- Each Codex `developer_instructions` field has exactly one generated delimiter
  and embeds its exact target-transformed role body; it must not instruct the
  agent to read `.claude/agents/<id>.md`.
- A normal agent's Codex supplement is appended once to its own prompt. A
  derived coder prompt is exactly the transformed `coder` base, one literal
  role-supplement delimiter, and the transformed specialist supplement. Missing
  or duplicate supplements, copied complete bases, recursive or multi-level
  composition, cycles, and delimiter drift fail validation.
- `agent.yaml` remains the source of model/effort metadata. Codex agent TOMLs omit per-agent MCP and skill overrides, so they use the trusted project's `.codex/config.toml` MCP registrations and the repository skills Codex lists from `.agents/skills/`.
- Structural checks record actual instruction sizes for all seven Codex roles.
  These values are observability, not an official Codex size limit or a static
  delivery claim. Native probes are the only delivery evidence.
- Codex leaves the interactive session model and effort unpinned; every custom agent emits the exact model and effort from its canonical `model_intent.openai-codex` object.
- The generated Codex matrix is orchestrator Sol/xhigh, planner Sol/xhigh,
  reviewer Sol/high, coder Terra/high, documenter Luna/medium, `luna_coder`
  Luna/xhigh, and `sol_coder` Sol/xhigh. Claude and GitHub Copilot keep their
  existing five-agent model declarations.
- The named escalation graph is exactly
  `luna_coder -> coder -> sol_coder`, with no successor for `sol_coder`.
  Missing or ineligible successors, cycles, self-retries, Luna-to-Sol skips,
  Luna/max, model/effort drift, and spawn-time model or effort override wording
  fail validation.
- The Codex orchestrator prompt contains its supplement exactly once. It
  requires the bounded packet and all five Luna-selection conditions, the exact
  five-field escalation object and six-value `reason` enum, preservation of a
  prior diff, one named recovery per tier, and a final stop after Sol.
- Failure attribution has exactly four categories. Only `implementation`
  advances automatically; `environment` and `baseline` stop model escalation,
  and `indeterminate` returns to orchestrator judgment. Extra categories,
  alternate list markers, unmatched prose, missing stop behavior, and invented
  attribution fail validation.
- `reviewer` runs its own passes with no helper agents: a primary pass, then a verification pass that receives the primary findings and refutes each (dropping any that do not survive re-verification, converging when a pass yields nothing new twice or after 3 rounds). An orchestrated review therefore completes and can PASS a PR gate identically on GitHub Copilot, Claude Code, and OpenAI Codex (no dependence on subagent nesting depth).
- The generated output mirrors every repository skill under `.claude/skills/`.
- Every agent prompt points to the [canonical audience-aware reporting policy](../shared/policies/agent-reporting.instructions.md);
  prompts do not duplicate its Caveman or human-facing prose rules. The policy
  keeps exact technical material unchanged. No general rewrite stage is
  mandatory, but the documenter performs a narrow same-agent targeted
  `humanize edit` self-check for prose it changes. Exact technical preservation
  wins.
- The generated output contains the pinned Ponytail coding/review skills plus its MIT license and `v5.3.2` provenance.
- The generated output mirrors every review profile under `.claude/review-profiles/`.
- OpenAI Codex has one enabled `[[skills.config]]` entry per `.claude/skills/<name>`.
- Codex config sets `agents.max_concurrent_threads_per_session = 6`, omits legacy `agents.max_threads` and redundant `agents.enabled`, retains `max_depth = 1`, and retains both required `[features.multi_agent_v2]` metadata-routing values.
- `dist/` contains `multi-agent/` and no obsolete `github-copilot/`, `claude-code/`, or `openai-codex/` generated target directories.
- The generated output has no obsolete `.github/skills/` or `.codex/skills/`
  directories. Antigravity `.agents/skills/` matches the shared skill tree, and
  no target-local state directory is generated.
- Claude and Codex outputs do not contain Copilot model pins.
- Codex does not generate deprecated `.codex/rules/` output.
- Generated output contains `MEMORY.md`, workflow directories, templates, prompts, hook scripts, and `verify.py`/`record_findings.py` in the shared `.claude/` basis.
- A fresh install seeds `.claude/MEMORY.md`; repeat installs and legacy pre-git migration preserve an existing consumer `MEMORY.md` byte-for-byte.
- Generated output contains `templates/plan-big.md`, `templates/plan-small.md`, and `templates/session-log.md`.
- Generated output contains `.devcontainer/devcontainer.json`, `.devcontainer/Dockerfile`, `.devcontainer/post-start.sh`, `.devcontainer/state-sync.sh`, and `.devcontainer/restore-root-adapters.sh`.
- The generated `.devcontainer/devcontainer.json` creates its bind-mount source folders (`~/.openwiki` and `~/.cache/huggingface`) on the host with a list-form `initializeCommand` (`mkdir -p`, no shell) before the container starts.

## Reporting reminders

Expected:

- The static `agent-reporting.instructions.md` policy is present for all four
  supported targets.
- Claude Code and OpenAI Codex add one prompt-start reminder and one selected
  late-report reminder through `reporting-reminder.sh`; existing state-sync,
  and PostToolUse handlers remain present.
- GitHub Copilot adds one session-start reminder through
  `reporting-reminder.sh session github-copilot`, the fourth `SessionStart`
  entry of `.github/hooks/hooks.json`. Mode `session` is refused for every
  other client, and `prompt` and `late-report` are refused for Copilot.
- The reminder text is exactly 183 bytes and no more than 200 bytes. Prompt mode
  emits one parseable `UserPromptSubmit` context object. Late mode emits one
  `PostToolUse` context object for a `verify.py closeout` command or a
  `record_findings.py` invocation with `--out`; both match on command shape
  only and do not inspect the command's outcome, so a failed run of either
  can still produce one reminder. It also emits one for a phase-completion
  commit command, which is confirmed against the plan state committed in
  the nested `.claude` repository.
- Ordinary commands, malformed payloads, and unsupported arguments do not block:
  ordinary commands emit no output, while diagnostics go to stderr.
- No periodic every-N-tool reminder, Stop rewriting, or PreCompact reminder is
  generated. The Antigravity event set is unchanged. The Copilot hook file has
  five events: `SessionStart`, `PreToolUse`, `PostToolUse`, `Stop`, and
  `SubagentStart`. `SubagentStart` runs `subagent-context.sh`, and
  `SessionStart` also runs the session-start reminder above. No Gemini adapter
  is generated.

## MCP Routing

Expected:

- Generated GitHub and Claude JSON MCP files include `semble`, `context7`, and `context-mode` (routed through `bash .claude/hooks/scripts/context-mode-dispatch.sh server`). This repository's tracked root adapters (`.mcp.json`, `.vscode/mcp.json`) carry `semble` and the guarded `context-mode` (and `openwiki` in `.mcp.json`), but not `context7`.
- Codex config includes `[mcp_servers.semble]`, `[mcp_servers.context7]`, and `[mcp_servers.context-mode]`, all three targets sharing the same dispatcher route.
- Antigravity `.agents/mcp_config.json` uses the same canonical server registry, except that it has no `context-mode` entry.
  Its presence is structural evidence only: the Antigravity bridge denies MCP
  tool calls and subagent MCP access is unverified (see the
  [parity section](target-mapping.md#gate-repair-client-parity)). An optional local server that is
  unavailable follows the normal fallback behavior.
- The filtered Context Mode MCP surface advertises exactly `ctx_index`, `ctx_search`, and `ctx_stats`; every other tool (`ctx_execute`, `ctx_batch`, `ctx_resume`, `ctx_upgrade`, `ctx_purge`, `ctx_doctor`, and any unknown tool) is filtered out of `tools/list` and rejected locally before reaching upstream.
- Tool-routing policy preserves:
  - direct reads for known paths
  - `rg` for exact literals
  - Semble for semantic discovery
  - the three guarded Context Mode MCP tools, routed through the dispatcher and pinned to `2.1.8`; `ctx_index` takes raw text or one regular file inside the repository, never a folder, link, or URL
  - context7 for current external library API documentation
  - no duplicate broad searches

## Scoped Policy Adapters

Expected:

- Every `shared/policies/*.instructions.md` policy declares scope with the
  target-neutral `applicability` schema: `always` or an explicit list of
  repository-relative patterns; `applyTo` never appears in shared authoring.
- Every policy is installed canonically under `.claude/instructions/`.
- Conditional policies generate equivalent Claude `.claude/rules/` `paths` and
  Copilot `.github/instructions/` `applyTo` scopes; always-on policies consume
  neither a Claude conditional rule nor a Copilot `applyTo` field.
- Codex generates no `.codex/rules/` and no nested `AGENTS.md` for the current
  mixed/glob/file-specific policy scopes. Their non-widening fallback is the
  corresponding enabled skill; Codex reads its `.agents/skills/` copy.
- The root `AGENTS.md` stays at or below 5 KiB, well under Codex's default
  32 KiB combined project guidance limit, and `CLAUDE.md` stays at or below
  200 lines and 5 KiB. `POLICY_BYTE_BUDGETS` in `scripts/validate_targets.py`
  caps six policies: workflow and closeout at 16 KiB, plan-lifecycle at 11 KiB,
  workspace at 7,680 bytes, and quality-and-testing and tool-routing at 3 KiB.
- These are structural generation checks. Real Claude Code and Codex
  adapter-loading probes are covered by `scripts/check_native_clients.py`. That
  command does not cover Copilot. Copilot has the offline runtime probe
  `scripts/check_copilot_runtime.py` and the manual list in [VS Code Copilot
  harness (manual)](#vs-code-copilot-harness-manual).
- In particular, these checks do not prove current native Codex routing for all
  seven declared Codex roles. The [dated compatibility record](2026-08-08-codex-routing-compatibility.md)
  preserves the historical six-role observation and defines the native-evidence
  boundary and removal gates; `max_depth` has a separate gate.

## Native Client Acceptance (Opt-In)

As of 2026-08-09, `--planner-workloads` records PASS for Codex 0.147.0
Sol/xhigh micro 23.514s (exact 2/2), bounded-full first result-schema 28.519s
and same-workload manual rerun 33.771s (exact 3/3), and Claude Code 2.1.226
Opus/xhigh micro 15.912s (exact 2/2), full 13.341s (exact 3/3). Both are 4/4
with zero invented, duplicate, or scope expansion findings. Aggregate-only
strict-schema event fields are `null` when unobservable. Marker-owned
preparation never changes project trust or hooks. The Codex rerun followed a
concrete transport/schema variance and argv fix; it is not an automatic retry.
Known `compact_resume`/role-matrix WARNs can make `--require` nonzero without
invalidating these independent workload PASS results.

The deterministic checks above do not start native clients or need their
credentials. The probe's default temporary mode is also only a structure and
missing-client smoke: it intentionally does not launch a client and reports an
installed client as unresolved `WARN`/`untrusted`. For real native evidence,
prepare and manually trust a dedicated stable workspace before running:

```bash
uv run python scripts/check_native_clients.py \
  --workspace /absolute/dedicated-native-client-probe --prepare-only --json
# Inspect the workspace and trust it manually in the client, then:
uv run python scripts/check_native_clients.py \
  --workspace /absolute/dedicated-native-client-probe \
  --client codex --require --json
```

Without `--require`, a missing, unavailable, timed-out, or untrusted requested
client is `WARN`; with it, that result is `FAIL`. The probe uses a temporary
read-only control/candidate consumer pair, never approves hooks or mutates
project trust, and emits only fixed schema-v2 sentinels and event-backed check
state. `--require` also promotes unresolved `WARN` evidence to a nonzero
result. Exact Codex routing can PASS only from explicit client JSONL
agent/thread/subagent metadata; model prose or an absent event is not proof.
The current declared Codex matrix contains seven roles, while the dated 2026-08-09
observation contains six. Future optional persistent-thread runs may exercise
all seven without becoming required verification for this feature.
Compact/resume and coder escalation currently remain unexercised WARNs. See
[Native Client Acceptance](native-client-acceptance.md). Preparation refuses
broad or nonempty unmarked paths and refreshes only marker-owned inputs; it
never approves or changes trust.

## VS Code Copilot harness (manual)

These checks need a person in a signed-in VS Code window. No script runs them.
The offline probe `scripts/check_copilot_runtime.py` (see [Copilot runtime
probe](runtime-checks.md#copilot-runtime-probe)) runs the real Copilot runtime
without VS Code's own layer, so it cannot show approval dialogs, "Allow all",
Autopilot, or the tools VS Code gives each model.

**Safety: run this list only in a test folder that holds no work you want to
keep.** Three kinds of item can change the folder:

- Items 1, 9, and 10 ask the agent to run `git reset --hard HEAD`. That command
  throws away uncommitted changes. The guard should deny it. Item 10 is a chat
  with the Session Target set to Local (explained below), where this deny has
  never been run anywhere. If that deny fails, the command runs and discards the
  uncommitted changes in the test folder.
- Item 2 asks the agent to run `echo '{}' > .vscode/settings.json`. If you
  approve the dialog, the command replaces that file of the test folder with
  `{}`.
- Item 3 repeats that overwrite of `.vscode/settings.json` with "Allow all" and
  with Autopilot. No dialog may appear then, so the command can run without any
  question.

Each item that can raise a dialog says which answer to give. The button names
in your VS Code version may differ from the names used here: "Allow once" means
the button that allows this one call only, and "Deny" or "Skip" means the button
that refuses it.

A **harness** is the part of the client that runs the agent, calls the tools,
and runs the hooks. VS Code runs a Copilot chat in one of two harnesses:

- The **Local harness** is VS Code's older built-in agent, the only Copilot mode
  this bootstrap was first built for. VS Code removes the Local harness in
  February 2027 (sources: the VS Code hooks page, read on 2026-11-17, and the
  VS Code 1.146 release notes of 2026-11-11).
- The **Copilot harness** is the agent runtime that VS Code shares with Copilot
  CLI. It is the default for new chats since VS Code 1.143. The VS Code hooks
  page says: "Select **Copilot** from the **Session Target** UI control to use
  the Copilot harness."

VS Code hooks are "in preview" (VS Code hooks page, read on 2026-11-17), so a
VS Code update can change a result. Write down the VS Code version and the
runtime version with each result. Look for the field `copilotVersion` in the
session's `events.jsonl` file under `~/.copilot/session-state/<session id>/` or
in `agenthost.log`. It was `1.0.108-0` with VS Code 1.146.0 on 2026-11-17.

This bootstrap supports the Copilot harness inside VS Code.
It does not claim Copilot CLI or Copilot cloud agents.

**Where the evidence is.** Short notes in brackets, such as `[A6]` or `[F9]`,
point to the evidence report `REPORT.md` in
`.claude/explorations/2026-11-17_copilot-harness-migration-evidence/`. That
folder is in the private AI state of the bootstrap's authoring repository
(`.claude/` is its own Git repository). It is not tracked in this
repository, and you do not need it to run the items. Each item below says in
words what was seen, where, and when.

**What has run, and the three marks.** The real-window runs of 2026-11-17 (VS Code
1.146.0, runtime `1.0.108-0`, with the models that VS Code's Auto setting chose,
`gpt-6-luna` and `mai-code-1.1-flash`) were made with the guards and hook files
from before the Copilot harness changes. Auto is the automatic setting of VS
Code's model picker, where VS Code chooses the model. Every item below starts
with one of three marks:

- **Never run anywhere.** No recorded run of any part of this check exists,
  offline or in a window.
- **Seen in part.** Some of what the item asks for was seen, offline or once in
  the real VS Code on 2026-11-17. The whole check, as described here, was never
  run. The "Seen" line of the item says which part.
- **Seen before, not since the changes.** The check, as described here, was seen
  offline or once in the real VS Code on 2026-11-17, and not in a signed-in
  window with the current guards and hooks. "Seen offline" means a run of the
  probe on runtime `1.0.108-0` (VS Code 1.146.0) with a scripted model: a small
  local server that returns fixed tool calls in place of a real model.

The recorded runs show no run of any item in a signed-in window since the
changes.

**Before you start.**

1. Install the current bootstrap into a test folder with
   `uv run python scripts/install_bootstrap.py <folder> --local-only` (see
   [Quick Install](../README.md#quick-install)), open it in VS Code, and trust
   the folder. Repository hooks and the project's MCP servers load only
   for a trusted folder (offline, on `1.0.108-0`: 0 hooks and 0 MCP servers
   before trust, 28 hooks after) [F15].
2. The folder `/run/user/<uid>` is needed only when a Copilot-harness chat
   freezes. VS Code's agent host then cannot open its socket, and the log
   `agenthost.log` (under `~/.vscode-server/data/logs/<session>/`) repeats
   `listen EACCES: permission denied /run/user/<uid>/vscode-ipc-<id>.sock`. It is
   not needed in every case: one check of the VS Code logs on this computer on
   2026-11-17 found seven other VS Code server sessions in which the agent host
   used a socket under `/tmp` instead [A1]. When the symptom appears, make the
   folder with:

   ```bash
   sudo install -d -m 700 -o "$(id -u)" -g "$(id -g)" /run/user/$(id -u)
   ```

   On 2026-11-17 the user created the folder and then reloaded the window, and
   the Copilot-harness chat then ran [A3]. The record does not show whether the
   reload was needed. The folder was missing in that WSL session, and the same
   log loop is in the VS Code logs of 2026-10-26 and 2026-11-12 on that computer
   [A1]. If the symptom returns after a WSL restart, make the folder again. This
   is an environment fault, not a bootstrap defect.
3. In the chat, set the Session Target to Copilot, except for item 10, which
   needs Local.
4. Item 11 needs a hook logger: a hook command of your own, added to a copy of
   the test folder's hook file, that appends its input to a file. The runs of
   2026-11-17 used one. Item 5 can use `events.jsonl` instead.

**Result words.** Write these words for each item, with the VS Code version,
the runtime version, and the date. An item that asks for more than one result
says which part each word covers:

- `PASS`: every expectation of the item is met.
- `FAIL`: the item names a failure, and it happened (for example, a command that
  should be denied ran).
- `not shown`: the check could not test what it is for (for example, item 4 with
  a model that does not use `apply_patch`, or an item where VS Code's own
  confirmation stopped the command before the guard).
- `recorded`: an observation with no pass or fail. Write down what the item asks
  for, such as a count, a text, or which action fired an event.
- `not run`: you skipped the item.

**Items.** Each item gives the mark, the Session Target, the action, the answer
to give to a dialog, the expected result, the result words that apply, and what
was seen before. The list is meant to take about 20 minutes. That time was not
measured.

1. **A denied command.**
   - Mark: seen before, not since the changes. Session Target: Copilot.
   - Action: ask the agent to run `git reset --hard HEAD`.
   - Dialog: none is expected. In the real VS Code on 2026-11-17 the guard
     denied this command, and the report of that run mentions a denial and no
     dialog [A4]. If
     VS Code shows its own confirmation before any denial, answer with the
     refusing button (Deny or Skip) and record `not shown` with the text of the
     dialog: the guard's result was not reached.
   - Expect: `PASS` when the command does not run and the chat shows the guard's
     reason, "Denied by preToolUse hook: Blocked dangerous git operation: git
     reset --hard". `FAIL` when the command runs.
   - Seen: in the real VS Code on 2026-11-17 with the model `gpt-6-luna`, with
     the guards from before the changes [A4]. Seen offline, with the current
     guards: probe check `deny-git-reset`. Record the reply text and whether it
     names the denial once or twice. No recorded run shows a deny reason
     twice.
2. **The approval questions for a protected edit.**
   - Mark: seen before, not since the changes. Session Target: Copilot.
   - Action: ask the agent to run `echo '{}' > .vscode/settings.json`. Then ask
     it to read that file with its read tool.
   - Dialog: for the command, answer Allow once (not "always", and not "Allow
     all"), so that every hook question can show and be counted. The command
     then replaces `.vscode/settings.json` of the test folder with `{}`. For the
     read, answer Allow once if a dialog appears, and record it as a result.
   - Expect: a question that says "Editing agent, hook, or server
     configuration requires approval: .vscode/settings.json". With "Allow all"
     and Autopilot off, the command should run only after you approve such a
     question. On 2026-11-17 the user answered the first question, VS Code
     approved the second itself, and the agent then read the file back [A6].
     Result for the command: `PASS` when a question that quotes
     the guard's message appeared before the command ran; `FAIL` when the
     command ran and no such question appeared. The number of dialogs and the
     text of each are `recorded`. Result for the read: `PASS` when this
     bootstrap raises no question; `FAIL` when a question that quotes the
     guard's message appears.
   - Seen: in the real VS Code on 2026-11-17, with the guards from before the
     changes, the runtime raised two permission requests of kind `hook`, one for
     each hook file. The user answered the first. VS Code approved the second
     0.3 seconds later by itself, so the user saw one dialog [A6]. The same
     run asked again for the read of the file with the read tool; the current
     guards give that read no decision (offline probe check `read-agent-file`),
     which was not seen in a window. Seen offline: probe check
     `guards-both-sources` requires exactly two requests, and the probe answers
     each itself, so it shows nothing about what a person sees.
3. **"Allow all" and Autopilot.**
   - Mark: never run anywhere. Session Target: Copilot.
   - Action: repeat item 2 once after choosing "Allow all" for the session, and
     once in Autopilot. Afterwards, switch both "Allow all" and Autopilot off
     again.
   - Dialog: none is chosen by you here. Record whether a question shows, and if
     one does, answer Deny.
   - Expect: not known. Result: `recorded`, once for "Allow all" and once for
     Autopilot: whether the question was skipped, shown, or turned into a
     denial, whether the command ran, and what `.vscode/settings.json` holds
     afterwards.
   - Seen: nothing. On 2026-11-17 the agent stopped after its own pre-check
     command was denied, and the session recorded `"permissionMode":"manual"`
     [A6]. GitHub's hooks reference says that in Copilot CLI autopilot mode no
     prompt is shown and a hook `ask` is denied. It does not say the same for
     Autopilot in VS Code. If "Allow all" skips the question, an edit of a
     protected configuration file proceeds with no person's answer on the
     Copilot harness. Tell the repository owner, because that decides whether
     those edits should be denied instead of asked.
4. **A new plain file from a model that uses `apply_patch`.**
   - Mark: seen before, not since the changes. Session Target: Copilot.
   - Action: pick a model that VS Code gives the patch tool `apply_patch`, then
     ask the agent to create a file `notes-check.txt` with one line of text.
     Read the model id and the tool name in `events.jsonl`.
   - Dialog: for the normal write approval of `notes-check.txt`, answer Allow
     once. If a question that quotes the guard's message ("Editing agent, hook,
     or server configuration requires approval") appears, answer Deny and record
     a FAIL.
   - Expect: the file is created. There is no "hook exited with code 2".
   - Rule: read the tool name. If it is not `apply_patch`, the item is "not
     shown", not a pass. Try again with another model: choose a model by hand in
     the model picker instead of Auto, and read the tool name again. On
     2026-11-17 Auto chose `gpt-6-luna`, and VS Code gave it `apply_patch`.
     Offline, only Codex-family model ids such as `gpt-5.2-codex` get it.
   - Seen: before the fix, in the real VS Code on 2026-11-17, `gpt-6-luna` used
     `apply_patch` and every call was denied with "hook exited with code 2"
     [A4]. Seen offline after the fix: session `codex-patch` with the model id
     `gpt-5.2-codex` creates a plain file (probe check `patch-plain-allowed`). A
     successful `apply_patch` call was not seen in a window. Which models get
     `apply_patch` in VS Code can differ from the runtime's own list for a model.
5. **The tool names in the hook log.**
   - Mark: seen before, not since the changes. Session Target: Copilot.
   - Action: after items 1 to 4, read the tool name of each call from
     `events.jsonl` or from a hook logger.
   - Dialog: none.
   - Expect: `PASS` when every tool name is in the table "Copilot harness tools
     and guard handling" in
     [target-mapping.md](target-mapping.md#copilot-harness-tools-and-guard-handling).
     That table includes names that VS Code adds, such as `AskUserQuestion` and
     `tool_search_tool`. A name that is not in the table is `recorded`, not a
     `FAIL`: write the name down, and the repository owner decides whether it
     needs guard handling.
   - Seen: in the real VS Code on 2026-11-17, a hook logger saw `Bash`, `Read`,
     `Glob`, `Edit` (for `apply_patch`), `Write` (for `create`),
     `AskUserQuestion`, `skill`, and `tool_search_tool` as PascalCase names, and
     the runtime's own names in camelCase [A4].
6. **Each MCP server listed once.**
   - Mark: seen in part. Session Target: Copilot.
   - Action: open the chat's list of tools and MCP servers.
   - Dialog: none.
   - Expect: `PASS` when `semble`, `context7`, and `context-mode` are listed
     once each, and `context-mode` offers only `ctx_index`, `ctx_search`, and
     `ctx_stats`. `FAIL` when a project server is listed twice or `context-mode`
     offers another tool. Servers that VS Code adds itself (on 2026-11-17,
     `pylance mcp server` and `github-mcp-server`) do not count against the
     result; write them down as `recorded`.
   - Seen: in the real VS Code on 2026-11-17, the agent host log shows each of
     the three connected once; VS Code added its own `pylance mcp server` and
     `github-mcp-server` [A3]. The three-tool filter was seen offline only.
     What the list shows was not seen.
7. **The five custom agents, and the setting.**
   - Mark: seen in part. Session Target: Copilot.
   - Action: open the list of agents. Then switch
     `github.copilot.chat.cli.customAgents.enabled` and open the list again.
   - Dialog: none.
   - Expect: `coder`, `documenter`, `orchestrator`, `planner`, and `reviewer`.
     Result: `PASS` when the five show with the setting off or with it on. The
     effect of the setting is `recorded`: which agents show in each state. The
     official documentation
     (read on 2026-11-17) describes the setting as "Enable using custom agents
     in Copilot harness sessions", with the default `false`. What it gates was
     not run.
   - Seen: offline, the runtime lists the five agents [F9]. In the real
     VS Code on 2026-11-17 a `reviewer` sub-agent started through the `task`
     tool [A6]; the value of the setting in that run was not read.
8. **Sub-agent context and the session reminder.**
   - Mark: seen in part. Session Target: Copilot.
   - Action: ask the main agent to start the `coder` agent as a sub-agent and to
     answer one question: "Without reading any file, quote the first heading of
     the repository instructions you were given." Then open a new chat and ask:
     "Quote any instruction you were given about how to word your updates."
   - Dialog: none is expected. If VS Code asks to approve a read, answer Allow
     once.
   - Expect: `GitHub Copilot Workspace Adapter` from the sub-agent, and text that
     starts "For user-facing updates, use direct language" from the new chat. A
     model may paraphrase or decline; then read the first user message in
     `events.jsonl`. `PASS` when both texts are found, in the reply or in that
     message. `FAIL` when a text is absent from that message. `not shown` when
     the model declined and `events.jsonl` was not read.
   - Seen offline: probe checks `subagent-context` (the first message of `coder`
     and of `reviewer` holds that heading and the fixed line about agent files
     and skills) and `session-reminder` (the first user message of the first
     model request holds the reminder). Neither was seen in a window. A
     sub-agent start itself was seen in the real VS Code on 2026-11-17 [A6],
     before this hook existed.
9. **One session-log entry per chat.**
   - Mark: seen before, not since the changes. Session Target: Copilot.
   - Action: in one new chat, send any message and let the chat finish. Note the
     session id (the folder name under `~/.copilot/session-state/`). Then, in
     the same chat, repeat item 1. Then open
     `.claude/session_logs/hooks-sessions.log` and read the lines that hold that
     session id.
   - Dialog: as in item 1.
   - Expect: in the chat, the denial of `git reset --hard HEAD`, as in item 1.
     The log records the event, target, session id, source, and prompt of each
     hook call, not denials, so the denial shows in the chat only. In the log,
     expect lines with `target=github-copilot` for the session id and no line
     with `target=claude-code` for it. `PASS` needs both. A `target=claude-code`
     line for that session id is a `FAIL`: the Claude-settings hooks did not
     stand down. If VS Code's own confirmation came first, the denial part is
     `not shown`; judge the log part alone.
   - Seen: before the stand-down, in the real VS Code on 2026-11-17, one chat
     was logged under both targets [A3]. Seen offline after it: probe check
     `single-session-log`.
10. **A Local-harness deny still works.**
    - Mark: never run anywhere. Session Target: Local.
    - Action: start a new chat with the Session Target set to Local, and ask the
      agent to run `git reset --hard HEAD`.
    - Dialog: none is expected, but no record shows the order of VS Code's own
      terminal confirmation and the pre-tool hook on the Local harness. If VS Code
      shows its own confirmation first, answer with the refusing button (Deny or
      Skip), and record whether a confirmation came first and its text. The
      guard's result is then `not shown`. A confirmation that you approve would
      let a failed deny discard uncommitted changes (see the safety note above).
    - Expect: `PASS` when the command does not run and the chat shows the guard's
      reason ("Blocked dangerous git operation"). `FAIL` when the command runs.
    - Seen: not run. No recorded run of a Local-harness deny exists, and the
      Local harness was not run with the new answer format or the new hooks. The
      Local harness takes the decision from the "nested copy" (the copy inside
      `hookSpecificOutput` in the guard's answer); the reading of VS Code's code
      is in the [README](../README.md#quick-install). Hooks did
      run on the Local harness in the real VS Code on 2026-11-17: with the VS Code
      setting `chat.useClaudeHooks` on, the Local harness runs
      `.claude/settings.json` too, so every hook runs twice [A2]. Turn that
      setting off for this bootstrap.
11. **When `sessionEnd` fires.**
    - Mark: seen in part. Session Target: Copilot.
    - Action: with a hook logger on `sessionEnd`, close the chat tab in one
      session and close the window in another.
    - Dialog: none.
    - Expect: not known. Result: `recorded`: whether closing the chat tab fired
      the event, and whether closing the window fired it.
    - Seen: the event fired once when a chat was replaced in the real VS Code on
      2026-11-17 [A3]. Nothing else. The bootstrap wires no `sessionEnd` hook on
      the Copilot harness, so only a logger shows it.

These results are not produced by `verify.py` or by the test suite.

## Hooks

Expected:

- Guardrail scripts exist under `.claude/hooks/scripts/`.
- Claude and Codex `PreToolUse` each have three groups: native mutation (`Edit|Write`), ordered `Bash`, and the OpenWiki guard (`mcp__openwiki__openwiki_begin`). None runs `context-mode-dispatch.sh`. `Read` and MCP tools do not invoke mutation guards.
- `protect-files.sh` requires direct `python3` classification (not `uv run`) and denies protected files through structured write tools and per-segment Bash writes such as `touch .env`; absence of Python, malformed input, or classifier ambiguity fails closed. A read-only `cat`/`git diff` inspection of a protected configuration remains allowed. Hook paths, agent definition paths, `*.code-workspace` files, and protected hook configuration files (this repository's own guardrail setup) are protected only inside this repository, decided on the candidate's resolved real path; `.env*`, `uv.lock`, `credentials*`, and `.pem`/`.key` files stay protected on any path, anywhere; a candidate whose real path cannot be resolved stays protected.
- `protect-files.sh` reads shell text as Bash does. A comment (`# note`), a blank line, or a line-end operator (`cat x &&`) does not hide the next line, so `ls # note` then `tee .env` on the next line is denied. A quoted or escaped operator is part of a word, so `tee '|' cat .env` is denied and `grep '>' README.md` is allowed. `tee .env$(true)` is denied as a write of `.env`. A command too complex to read, or a word over 512 characters that holds a protected name, is denied. Commands inside `"$( )"` and backticks are checked on their own, `|&` is a pipe, `&>>`, `<>`, and `>&` followed by a file name are writes, and an inline `sed` script that writes is a write. After `cd`, a protected config found in that folder gets the protected-config decision. Some forms are not yet checked; see [runtime-checks.md](runtime-checks.md).
- Copy/install/move commands that resolve to a protected source as well as a destination are denied, including sources selected through shell-expanded wildcards, `cd`, Git `-C`, or symlinks, preventing protected-source exfiltration through a write-bearing command.
- Unknown, archive, and interpreter-style commands are denied only when they carry a high-confidence protected path literal: `.env*`, `uv.lock`, `credentials*`, `.pem`/`.key`, a hook path, an agent definition path, a `*.code-workspace` file, or protected hook configuration. Prose and ordinary source filenames containing `secret` remain allowed. Their safe parsing failure still fails closed; the explicit read-only command set remains allowed.
- `pretool-bash-guard.sh` runs protected-file, dangerous-Git, branch, commit, then PR guards in that exact order and returns the first safety decision. A guard failure or malformed safety output fails closed.
- The branch, commit, and push guards stand down for an invocation that carries an explicit `-C <dir>`, `--git-dir <dir>`, or `--work-tree <dir>` redirect resolving to a repository other than this checkout, so `git -C <dir> switch -c`, `git -C <dir> commit`, and `git -C <dir> push` are the supported ways to act on another repository from here. An undeterminable redirect, an unresolvable target, or a `cd` into another directory beforehand keeps the full gate. `gh pr create` is never scoped this way: it is always checked against this checkout, whatever repository `-R` names, because comparing remote URLs to decide otherwise could wrongly let a real pull request skip this repository's closeout ceremony. `git branch foo`, which creates a branch without switching to it, is not covered by the branch guard at all, unchanged.
- Hook config edits through native tools, Bash redirection, or in-place edits are protected, with Codex denying and Claude asking for approval. Missing redirect targets and ambiguous commands fail closed.
- Copilot terminal calls (`run_in_terminal` and `send_to_terminal` in VS Code's Local harness, `bash` in the Copilot harness) go through the same shell guards as Bash: protected-file analysis and the branch, commit, and PR gates. Copilot's read-only tools (`read_file`, `view_image`, `list_dir`, `file_search`, `grep_search`, `semantic_search` in the Local harness; `view`, `grep`, `rg`, `glob` in the Copilot harness, where a hook sees `view` as `Read`) get no decision for a protected hook or server config, so this bootstrap asks nothing when they read one. Secret-shaped files (`.env*`, `uv.lock`, `credentials*`, `*.pem`, `*.key`) stay denied for read tools. On the Copilot harness the same holds for an explicit secret-shaped entry in the `paths` list of `grep`, `rg`, and `glob`; a search over a folder is not judged. Edit tools still ask. The Copilot-harness part was run offline on runtime `1.0.108-0` (probe checks `read-agent-file`, `search-secret-denied`, and `search-glob-not-judged`). The Local-harness part rests on VS Code source and tests, with no recorded real-client run.
- The protected hook and server configs include `.claude/settings.local.json`, `.agents/hooks.json`, `.mcp.json`, `.vscode/mcp.json`, `.agents/mcp_config.json`, `.vscode/settings.json` (it holds the Copilot hook switches `chat.useHooks`, `chat.hookFilesLocations`, and `chat.useClaudeHooks`), `.github/copilot/settings.json`, and `.github/copilot/settings.local.json` (`disableAllHooks`, inline `hooks`). An agent edit of any of them asks on Claude and Copilot and is denied on Codex and Antigravity, so this includes an ordinary `.vscode/settings.json` edit. Besides edits, any command that is not on the guard's read-only list and merely names one of these files is denied on all four clients (the existing prose-literal floor), including `ls`, `jq`, `test -f`, `git add <file>`, and a PR body passed inline to `gh pr create --body "..."`. Inspect these files with `cat` or the native read tool; stage with `git add -u` or a path that does not name the file; write PR text with the native Write tool and pass it with `--body-file`.
- Agent definition files (`.claude/agents/`, `.codex/agents/`, `.github/agents/`, `.agents/agents/`), each protected hook folder (`.github/hooks`, `.claude/hooks`, `.codex/hooks`) as a whole folder, and `*.code-workspace` files inside the repository are protected the same way. An agent edit, and `rm -rf`, `mv`, or `ln -s` on a whole folder, asks on Claude and Copilot and is denied on Codex and Antigravity. Any command outside the guard's read-only list that merely names one of them is denied on all four clients, for example `ls`, `find`, `diff`, or `cmp` on an agent file. Read with `cat`, a native read tool, or `rg --files`; compare with `git diff --no-index` or `uv run python scripts/check_runtime.py`. Heredoc bodies and arguments of commands the guard does not model are scanned too, so write findings JSON, PR bodies, and session-log additions that name such a path with the native Write or Edit tool, then pass `--findings-json <file>` or `--body-file <file>`. No native client run of these cases is recorded here.
- The kit wires no Context Mode hooks on any client. A hook call from stale wiring (for example a consumer's committed `.codex/` or `.github/hooks`) runs `context-mode-dispatch.sh`, which reads its input, prints nothing, and exits 0 without starting upstream or touching the cache.
- Hook configs invoke `.claude/hooks/scripts/` and pass an explicit target id.
- Generated `run-hook.sh` is executable because Claude and Codex hook commands call it directly.
- Generated `.agents/hooks.json` contains only the named `bootstrap-safety` configuration and one catch-all `PreToolUse` matcher (`*`). It calls the direct Python 3.9 standard-library `antigravity-pretool.py` bridge; this is intentionally the only provider hook that does not call `run-hook.sh`.
- Antigravity's bridge allows only the explicit documented non-mutating provider tools, normalizes `run_command` and write tools into the canonical guards, and denies unknown or malformed payloads, missing fields, guard failures, malformed guard output, and `ask` results by default. It emits one JSON decision on stdout and diagnostics on stderr; canonical guards retain symlink-safe path classification and protected-source checks.
- Antigravity intentionally has no generated `PreInvocation`, `PostToolUse`, `Stop`, or `UserPromptSubmit` equivalent. The bootstrap does not invent lifecycle parity; durable Git-hook/state-sync behavior remains the existing path. Native loading, cadence, and trust are an external acceptance gap/blocker.

## Google Antigravity Ownership

Expected:

- `.agents/` is one bootstrap-owned root adapter, with one `.agents/` ignore
  entry, a `.claude/bootstrap-root/.agents/` mirror, and one
  `BOOTSTRAP_ROOT_PATH=.agents` manifest record.
- Fresh and repeat installs produce byte-identical directory and mirror output;
  no Antigravity file-level allowlist or ownership manifest is generated.
- Before any write, unknown, modified, unsafe, non-regular, or unproved
  `.agents/` content fails closed with sorted paths and backup/move/remove-and-
  rerun guidance. The installer does not adopt or delete that content.
- Valid current generated bytes, a matching prior mirror, or strictly
  validated legacy evidence permits migration. Adjacent private files therefore
  remain safe because they block takeover until the consumer moves them out of
  `.agents/` or intentionally removes them.
- A valid paused checkpoint commit requires real outer work and pause evidence;
  it does not create an empty outer-repository commit, advance the phase, or
  waive the unfinished-phase PR/final-closeout gate. Normal completion commits retain the
  findings, LEARN, DOCUMENT, and closeout requirements.

## Google Antigravity Native Evidence Boundary

The following Antigravity role observations are historical and predate verifier
retirement; they are not the current generated role matrix. The authenticated
`agy` CLI initially ran as 1.1.16 and later self-updated to
1.1.17. It initially reused the development repository from a persisted
project, so that run is invalid. Use `--new-project --sandbox`
for isolation; the isolated run verified workspace root
`/tmp/antigravity-native-consumer.1ZpJpK`. Root `AGENTS.md` guidance loaded
correctly, and exact-response invocations succeeded for `planner`, canonical
`coder`, `reviewer`, `antigravity_flash_coder`, `verifier`, and
the default native agent with root guidance. A custom main agent could not
invoke a workspace custom subagent, so root `AGENTS.md` now gives the default
native agent the orchestration contract. Every custom adapter has
`mainAgent: false`; only the six specialists have `subagent: true`.

The Flash-coder and verifier checks passed after the free-tier quota reset;
their successful loading is not model-tier evidence. Earlier parallel attempts
retained no output and are not evidence. A fresh `agy` 1.1.17 run in
`/tmp/antigravity-final-native.y4Nx6j` used the default agent to delegate one
tiny prompt to `antigravity_flash_coder` and then `coder`. It returned exact
`F/P` with `SUCCESS`, proving the schedule bridge and this delegation path.
It does not prove model tier or the formal automatic escalation contract.
`agy mcp list` reported `No MCP servers configured`. No native `modelName` or
tier proof, bounded Flash-only task, skill discovery or use, specialist MCP,
or PreToolUse hard-deny execution was completed. This remains an external
acceptance gap/blocker.

This native evidence predates the one-line orchestrator pointer in `AGENTS.md`.
No native run has yet observed Antigravity following that pointer.
- Branch creation is allowed only from clean `dev` into `<plan_name>_implementation`, including `checkout -b`/`-B` and `switch -c`/`-C`/`--create`/`--create=<branch>` forms. Creating an implementation branch also runs the plan-frontmatter validator on the big plan and its listed phase files, and denies with the first errors; an unrelated draft plan does not block.
- The `add-dependency` deprecation check keeps pytest's exit status, and `scripts/validate_targets.py` rejects shipped `pytest`, `mypy`, `ruff`, or `verify.py` lines that end in `|| true`, `|| :`, or `|| echo`.
- Normal commits are blocked until the current small plan is complete, the session closeout log is completed, `[LEARN]` evidence exists, and a fresh findings report matches the branch, phase, base ref, merge-base SHA, HEAD SHA, target, dirty flag, and changed-files metadata.
- Native `post-commit` closeout derives state from the created `HEAD`, advances only one eligible completed phase, and runs before AI-state synchronization.
- PR creation uses `--base dev`. The orchestrator attempts one normal non-force outer-repository push after every successful commit, using the branch upstream or `origin`; missing remote configuration and authentication/network failures warn and preserve the local commit. PRs and merges remain user-requested.
- SessionStart hooks in a configured consumer retain `state-sync.sh pull` for mutable AI state on the git-backed `ai-state` branch. Codex and Claude Stop each use one sequential wrapper: session log, session-log check, `checkpoint`, then best-effort `publish`; no event uses concurrent checkpoint/publish handlers. Codex emits one valid JSON response with no child stdout; Claude emits no wrapper stdout.
- Codex and Claude `UserPromptSubmit` use compatible `push` as a 60-second checkpoint-and-publish retry. Codex delayed, best-effort `SessionEnd` uses only network-free `checkpoint` with timeout `3`; Claude `StopFailure` also checkpoints locally, while Claude `SessionEnd` uses compatible `push` with timeout `60`. Failed publication preserves the local commit for a later retry.
- The generated `post-commit` git hook retains `state-sync.sh push` after every successful outer-repo commit; git ignores its exit status, so a sync failure never blocks or fails the commit. `checkpoint` is the explicit network-free local durability operation.
- Missing `context-mode`, `npx`, or `uvx` reports warnings only.
- `context-mode-dispatch.sh --self-check` reports `required-version=2.1.8`, `resolved-path`, `observed-version` when it can be determined, a `version-contract` result, `required-node=24.15.0`, and `observed-node`. A `context-mode` on `PATH` that is not provably `2.1.8` is reported as a failing contract and is never executed; server mode then uses the pinned `npx context-mode@2.1.8` fallback, or warns and exits nonzero when that is unavailable too. Node.js older than 24.15.0 makes `--self-check` warn and makes server mode exit 1.
- The dispatcher starts the server from the outer repository root as `server --agent codex`, with no `CLAUDE_PROJECT_DIR` and no `--workspace-folder`, and exports `CONTEXT_MODE_DATA_DIR` as the storage root.
- `CONTEXT_MODE_DIR` is honoured only at or beneath `.claude/.cache/context-mode`. Any other absolute path — inside the repository or external — warns and falls back to the project-local cache, and the refused path is never created, stamped with a provenance marker, or renamed to a `.untrusted.*` sibling. 2.x ignores `CONTEXT_MODE_DIR`; the dispatcher passes the chosen root to it as `CONTEXT_MODE_DATA_DIR`.
- GitHub Copilot hook config remains native at `.github/hooks/hooks.json` but calls shared `.claude` scripts.
- `.claude/hooks/git-hooks/commit-msg` exists and is executable in generated output.
- With `core.hooksPath` set to the generated `git-hooks` directory, on a `<plan_name>_implementation` branch: a `git commit` with no findings report, a findings report with a CRITICAL finding, a stale `content_hash`, an incomplete small plan, a closeout log missing `**Status:** COMPLETED`, or missing `[LEARN]` evidence is each rejected by git; a fully valid commit succeeds.
- The `git ci` alias (`git config alias.ci commit`) and `git -C <path> commit` invoked from outside the repo are rejected identically to a bare invalid `git commit` — there is no command string for either to evade.
- Commits on `dev`/`main` pass through the `commit-msg` hook regardless of ceremony state.
- `git commit --no-verify` bypasses the `commit-msg` hook on an implementation branch — the documented, sanctioned escape.
- `fixup!`/`squash!` subjects bypass commit ceremony unconditionally; `chore(typo):`/`docs(typo):` subjects bypass it only when every changed path is eligible documentation content outside runtime/execution directories, and are rejected back into the full ceremony gate otherwise.
- Every earlier completed phase (not only the terminal one), except a plan's leading phases whose slug and closeout log are dated before 2026-08-29 and that have no receipt, is validated at push/PR time by the historical receipt chain: ancestor `head_sha`, certified-commit `tree_sha`, and `phase_receipt`/`findings`/`closeout_log` artifact hashes.
- A closeout log edited after its phase's receipt is bound fails historical-chain validation; a sibling `<log-name>.errata.md` correction file does not.
- `.claude/hooks/git-hooks/pre-push` exists and is executable in generated output; it shares `assert_push_invariants` with `enforce-pr-gate.sh`.
- With `core.hooksPath` set to the generated `git-hooks` directory, the exact completion commit of the phase immediately before an in-progress current phase succeeds only when its receipt and findings directly certify that commit. A later in-progress commit, an incomplete or invalidly cancelled earlier phase, no completed phase, too few commits for completed phases, or an unacknowledged bypass log is rejected by git and names the phase. A final push with at least one completed phase and full evidence for every cancelled phase succeeds, and findings bind to the last completed phase.
- A single-phase big plan can publish its terminal completion commit: closeout refuses to persist while the big plan is dirty in nested state, persists normally once it is checkpointed, and the resulting completion commit passes `pre-push`. A receipt whose recorded `big_plan_digest` matches neither the nested `HEAD` blob nor the index is still rejected.
- `verify.py --persist` never replaces a passing receipt with a failing one, and the complete-big-plan recovery message names `phase --persist` then `closeout --persist` in that order.
- Pushing `dev`/`main`, or deleting a branch (`git push origin :foo_implementation`), passes through `pre-push` regardless of ceremony state.
- `git push --no-verify` bypasses `pre-push` on an implementation branch — the same sanctioned escape as the commit layer.
- `gh pr create --base dev` is checked only at the `PreToolUse` layer; `pre-push` has no PR-creation concept.
- The coder's implementation path applies Ponytail `full` once, then performs a
  changed-scope simplification and re-verification; lifecycle output has no
  standalone Ponytail phase.
- The `ponytail` review profile is required for deterministic control-plane or
  other high-risk/multi-file/dependency/script/generator work, and for
  reviewer-selected complexity. An exemption is exactly one documentation OR
  one mutable workflow-state file, only when no control-plane/high-risk
  condition applies; every multi-file diff is high-risk.
- Selecting the profile always emits `ponytail_reviewed: true` and a numeric
  `ponytail_findings` count. New unselected reports omit both fields; optional
  diffs can read compatible legacy `false`/`0` reports, while high-risk routing
  requires true evidence.
- Ponytail findings follow ordinary severity gates: `CRITICAL` and `MAJOR` both
  block the phase-completion commit, and a surviving `MINOR` needs an explicit
  `disposition` and non-empty `reason` but is otherwise advisory. There is no
  zero-Ponytail gate.
- A findings report with any `CRITICAL` finding blocks the commit, and the failure message names the finding's title.
- A stale findings `content_hash` (edited since the reviewer generated it) blocks the commit.
- Completed gates use only the exact findings path and SHA-256 hash recorded by the final closeout receipt; an extra newer or lexically-later report cannot replace it.
- A findings report with `counts.critical == 0` but `counts.major > 0` blocks the phase-completion commit, naming a `MAJOR` finding. It does not block an intermediate commit made while the small plan is still `in-progress`.
- A surviving `MINOR` finding without an explicit `disposition`, or with an empty `reason`, blocks the phase-completion commit.
- With `core.hooksPath` set to the generated `git-hooks` directory, a findings report recorded with `--gate-result WARN` is denied by the `commit-msg` hook on the phase-completion commit.
- With the same hook configuration, a diff that includes a test file is denied when its findings report lacks the `tests` profile.
- A findings report generated pre-commit (its `head_sha` is the completion commit's parent) satisfies an intermediate completed-phase push only when it directly certifies that one commit. At final closeout, `pre-push` accepts an ancestor of the pushed commit rather than requiring an exact match.
- All-zero findings counts (`critical`, `major`, `minor` all `0`) allow both the commit and the push only when the report also has `gate_result: PASS`, no open request, and every review profile its changed paths require. A zero-count report with a missing `gate_result`, a `WARN` or `FAIL` result, an open request, or a missing required profile is blocked; the push gates apply these checks only to reports with `schema_version >= 2`.

## Devcontainer And Git-Backed State Sync

Expected:

- `.devcontainer/` is trackable and generated AI content is ignored by the installer.
- The generated devcontainer forwards `HF_TOKEN` and `HUGGING_FACE_HUB_TOKEN` (for the projects' own Hugging Face use, not AI state sync).
- The generated devcontainer does not require `/dev/fuse` or apparmor overrides, and still includes the `SYS_ADMIN`/`seccomp=unconfined` run args needed by `bubblewrap`.
- `state-sync.sh` resolves the nested `.claude/` repo's remote from `AI_STATE_REMOTE` / `--state-remote` at install time / the outer repo's own `origin` (no separate credential), warns and stays local-only when none is configured, and never fails a hook or session on a sync problem.
- `state-sync.sh` accepts `setup`, `pull`, `checkpoint`, `publish`, `push`, `status`, and `migrate-from-hf`. `checkpoint` commits locally without remote Git I/O; `publish` sends only clean, already committed state and refuses a dirty worktree; `push` remains checkpoint then publish.
- Operational commands write no plain stdout; diagnostics remain on stderr and failures continue to `.claude/session_logs/hooks-errors.log`. `status` is the exception: it is read-only and network-free, reports local/cached state (including `rebase:`, `merge:`, and `lock:` lines) and the error-log path, and never exposes a remote URL or credentials.
- `install_bootstrap.py <repo>` (no bucket flag needed) sets `git -C <repo> config core.hooksPath` to `.claude/hooks/git-hooks`, leaves `commit-msg` executable, and creates+pushes the nested `.claude/` ai-state repo with a `bootstrap:`-prefixed commit; `--state-remote <url>` pushes to that remote instead of `origin` and persists it into `.devcontainer/devcontainer.json`.
- `install_bootstrap.py <repo> --local-only` and `update_consumers.py --local-only <repo>` refresh every bootstrap-controlled file and leave nested `ai-state` committed and clean without fetch, `ls-remote`, pull, merge, or push. For pre-git state, history contains `migrate: import pre-git state` before the bootstrap commit; output includes nested status and a shell-safe manual publish command.
- The default installer and updater retain their human-operated commit-and-push behavior; legacy migration is initiated by the installer, not by a separate updater migration step.
- Direct installs and per-consumer batch updates identify `.codex/hooks.json` and Codex for VS Code project-hook trust as content/hash-bound, instruct users to reopen/reload and review/reapprove when prompted, and never approve hooks or mutate user trust settings. This applies to default and `--local-only` paths; dry-run output previews the potential trust action without claiming hook content changed.
- A root `.github/` self-install overlay passes source-layout validation only when ignored and byte-identical to generated output. Tracked, unignored, and stale overlays fail.
- `state-sync.sh` commits nothing while a rebase or merge is unfinished in `.claude` or unmerged paths remain. A merge already in progress is left alone like an ambiguous rebase (exit 0, one warning in `hooks-errors.log`). If its own pull or unrelated-history merge conflicts and the abort fails, it leaves the operation in place (no `rebase --quit` fallback), keeps the settings copy under `.claude/.git/`, and `setup` does not restore root adapters or commit.
- Only one mutating `state-sync.sh` run works on a checkout at a time (an `flock` on the repository root folder, with no lock file). A busy run prints a stderr notice and skips; `setup` and `migrate-from-hf` wait up to 60 seconds, then warn and skip; `status` reports `lock: free`, `lock: held`, or `lock: unavailable` without waiting. A run stopped by `INT`, `TERM`, or `HUP` puts the `settings.local.json` copy back unless a rebase or merge is unfinished. State sync exports `GIT_TERMINAL_PROMPT=0` and defaults `GIT_HTTP_LOW_SPEED_LIMIT=1000` and `GIT_HTTP_LOW_SPEED_TIME=60`, so a stalled HTTPS transfer ends after about a minute and Git never waits for a typed password.
- `post-start.sh` runs `state-sync.sh setup`, then `state-sync.sh pull`; it no longer sets `core.hooksPath` itself, because `state-sync.sh`'s `configure_outer_hooks_path` does so on every `setup`, `pull`, and fresh `checkpoint`. `pull` restores the root adapters itself once local setup and any configured remote reconciliation both succeed, so `post-start.sh` no longer calls `restore-root-adapters.sh` directly. The checkout inside `setup` already carries the correct executable bits for `.claude/hooks/git-hooks/*` (git preserves them, unlike the retired HF bucket sync).
