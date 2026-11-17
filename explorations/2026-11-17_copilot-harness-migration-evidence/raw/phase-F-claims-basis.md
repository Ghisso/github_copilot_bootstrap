# Phase F: basis of every Copilot claim written or kept in the six files

Date: 2026-11-18. Bootstrap HEAD 5a77d4b plus the uncommitted Phase F documentation edits.
Runtime for every "run" basis unless a row says otherwise: Copilot runtime `1.0.108-0` in VS Code 1.146.0
(commit `69047191fc427f2f92828279aae1d90d8eeda7ab`), Copilot SDK `1.0.30-preview.0`.

How to read the basis column. All paths without a prefix are in this evidence folder
(`.claude/explorations/2026-11-17_copilot-harness-migration-evidence/`):

- `REPORT F<n>` and `REPORT A<n>`: a finding or an addendum of `REPORT.md`. F1 to F16 are scripted runs on
  runtime `1.0.108-0` (offline, with a scripted model), Docs, or Source. A1 to A6 are runs in the real VS Code
  1.146.0 on 2026-11-17.
- `REPORT planning probe P1 to P4`: planning checks of 2026-11-17 on runtime `1.0.108-0`, as listed in the big plan;
  the raw files are `raw/planning-probe-e1-*` (P1), `raw/planning-probe-e2-*` (P2), `raw/planning-probe-e3-*`
  (P3), and `raw/planning-probe-p4-subfolder-discovery.txt` (P4).
- `RES §n`: `research/github-docs-runtime-contract.md`, the official-documentation research of 2026-11-17, with the
  exact quotes and URLs.
- `raw/...`: a raw output file in this folder. `raw/phase-F-*` files were written by this phase.
- `source`: a file in the repository with a line or symbol, or VS Code's installed files read in this phase.
- `not run`: the document itself says that the statement has no run behind it.
- `decision`: a user decision of 2026-11-17 recorded in the big plan `.claude/plans/copilot-harness-migration.md`
  ("Approved user decisions" and "Approval record"). It is a scope statement, not a result.

## README.md

| File | Short quote | Basis |
| --- | --- | --- |
| README.md | A harness is the part of the client that runs the agent, calls the tools, and runs the hooks. | The plain-language definition used by REPORT ("How the evidence was gathered"). Official pages: VS Code hooks page and VS Code agent-harnesses page, RES §13 ([VS-hooks], [VS-harness]), read 2026-11-17. |
| README.md | VS Code removes the Local harness in February 2027. | Official: VS Code hooks page "deprecated and will be removed in February 2027"; VS Code 1.146 release notes (2026-11-11) "removed in three months (February 2027)". REPORT F1. |
| README.md | It is the default for new chats since VS Code 1.143. | Official: VS Code 1.146 release notes "has been the default for new sessions since VS Code 1.143". REPORT F1. |
| README.md | The **Copilot harness** is the agent runtime that VS Code shares with Copilot CLI. | Official: VS Code hooks page "VS Code, the GitHub Copilot app, and GitHub Copilot CLI share this harness and its hook format". REPORT F1; RES §13. |
| README.md | the only Copilot mode this bootstrap was first built for | Project history, not a run: the 2026-09-25 sidecar native runs and the earlier docs name the Local agent. `docs/sidecar-provider-contract.md` Step 4. |
| README.md | This bootstrap supports the Copilot harness inside VS Code, and it keeps the Local harness working until VS Code removes it. | `decision` (approved user decisions 1 and 2). |
| README.md | It does not claim Copilot CLI or Copilot cloud agents. | `decision` (approved user decision 1). |
| README.md | VS Code hooks are "in preview" (VS Code hooks page, read on 2026-11-17) | Official: "**Agent hooks** is in preview and might change before it becomes generally available." RES §14. |
| README.md | On 2026-11-18 the probe printed runtime `1.0.108-0` (VS Code 1.146.0) and 48 result lines, none | `raw/phase-F-require-output.txt` (command `uv run python scripts/check_copilot_runtime.py --require`, exit 0, `Result: PASS (0 of 48 checks failed)`). |
| README.md | `git reset --hard HEAD` was denied. | REPORT A4, session `2c3106d8…`, model `gpt-6-luna`, real VS Code 1.146.0, runtime `1.0.108-0`, 2026-11-17: "Denied by preToolUse hook: Blocked dangerous git operation: git reset --hard". Guards from before this plan. |
| README.md | VS Code can give a model a different tool set than the runtime's own list for that model. | REPORT A4 (Auto chose `gpt-6-luna`; VS Code gave it `apply_patch`) and `raw/tools-by-model.txt` (the runtime's own list gives `gpt-6-luna` `create` and `edit`). |
| README.md | That file records no run of any of them in a signed-in window since these changes. | Phase B to E session logs (the optional items are `NOT RUN`); `docs/smoke-tests.md` marks every item "never run anywhere" or "seen before, not since the changes". |
| README.md | It was not run with the current answer format or the current | Phase C session log, "Unverified limitations". `not run`. |
| README.md | comes from VS Code's own code, not from a run: in the Copilot extension 0.74.0 of | `source`: `~/.vscode-server/bin/69047191…/extensions/copilot/dist/extension.js`, `ChatHookService.executePreToolUseHook`: `let E=_.hookSpecificOutput;if(!E)return;…let x=E.permissionDecision` (read on 2026-11-18; the excerpt is in `raw/phase-F-fix-round-1.txt`). Also `DEVILS-ADVOCATE-2026-11-17.md` line 196. |
| README.md | so every hook runs twice (seen in the real VS Code on | REPORT A2 (Local harness with `chat.useClaudeHooks: true`: "[SessionStart] Executing 8 hook(s)"). |
| README.md | its hook log showed 8 hooks at session start, three from | REPORT A2 (three from `.github/hooks/hooks.json`, three from `.claude/settings.json`, two probe loggers). |
| README.md | Turn that setting off for this bootstrap. | Advice, not a result: big plan Q1 ("The docs advise turning that setting off"). |
| README.md | says that Local settings such as `chat.useHooks` do not prevent the Copilot harness from loading a configuration [F1] | REPORT F1, quote from the official VS Code documentation read 2026-11-17. |
| README.md | is the file generated for the Local harness. How the Local harness reads it was not rechecked. | `not run`: stated in the text. The file exists in `dist/multi-agent/.vscode/mcp.json`. |
| README.md | in a scripted run on runtime `1.0.108-0` on 2026-11-17 it did not read `.vscode/mcp.json` [F12] | REPORT F12 ("The runtime does not read `.vscode/mcp.json`"). |
| README.md | in the real VS Code on the same day each project MCP server connected once [A3] | REPORT A3 ("`semble`, `context7`, and `context-mode` each connected once"). |
| README.md | VS Code can also forward server definitions to the runtime | Official, via REPORT F12: "Eligible existing definitions can be forwarded, but the harness doesn't read those files directly." |
| README.md | These files are for Copilot inside VS Code, on the Copilot harness and on the Local harness | `decision`; same as the scope rows above. |
| README.md | No `.github/agents` or `.codex/agents` file ships. | `raw/phase-F-sidecar-discover-workflow.txt` section "installed files outside any skills folder" (no `.github/agents`); `docs/sidecar-provider-contract.md` 2026-09-27 decision. |
| README.md | The 2026-09 native runs did not show a config-free way for either client | `docs/sidecar-provider-contract.md`, "Workflow profile evidence" (2026-09-27: Copilot unverified; Codex has no discovery mechanism from an ignored file). |
| README.md | offline discovery on runtime `1.0.108-0` (2026-11-18) lists the five `.claude/agents/` files | `raw/phase-F-sidecar-discover-workflow.txt`: `agents: 5 (coder, documenter, orchestrator, planner, reviewer)`; raw record shows `path` `<team-repo>/.claude/agents/<id>.md`, `source: project`. |
| README.md | were verified with a real client run on 2026-09-25, with VS Code 1.139.0 | `docs/sidecar-provider-contract.md` Step 4 matrix (rows "Copilot in VS Code"). |
| README.md | listed the skills and the instruction files of both profiles | `raw/phase-F-sidecar-discover-skills.txt` and `raw/phase-F-sidecar-discover-workflow.txt`. |
| README.md | The Copilot harness also reads `.claude/rules/` | `raw/phase-F-sidecar-discover-*.txt` (instruction sources with `sourcePath` `.claude/rules/...`); REPORT F10; `raw/phase-A-discover-output.txt`. |
| README.md | the runtime put the always-on instruction files into the system prompt | REPORT F10; `raw/instructions-in-system-prompt.txt`. |
| README.md | listed the path-scoped files of both folders (five policies in each) | REPORT F10; `raw/phase-A-discover-output.txt` (5 `.instructions.md` files from `.github/instructions/` and 5 from `.claude/rules/`). |
| README.md | The runtime listed all five generated custom agents in that run [F9]. | REPORT F9; `raw/phase-A-discover-output.txt` ("agents: 5 (coder, documenter, orchestrator, planner, reviewer)"). |
| README.md | Whether a signed-in VS Code window lists them was not run | `not run`: item 7 of the manual checklist, never run. |
| README.md | and `bash` on the Copilot harness | REPORT F8 (`bash` is the runtime shell tool; hook name `Bash`); probe checks `deny-git-reset`, `deny-force-push`, `deny-branch`, `deny-commit`, `deny-pr` in `raw/phase-F-require-output.txt`. |
| README.md | `run_in_terminal` and `send_to_terminal` on the Local harness | `source`: `microsoft/vscode` at `9a59550f…`, read 2026-10-17, as `docs/target-mapping.md` already cites. No real-client run. |
| README.md | The Copilot harness loads both `.github/hooks/hooks.json` and | REPORT F2 (`hooks.discover`: 12 hooks from the first file and 14 from the second, no warning); A3 (real VS Code). |
| README.md | one session logged as two, the AI-state pull and push each run twice, and two permission requests for one protected edit | REPORT F2 "Effects seen" (`raw/outcomes-g-both.txt`, `raw/session-log-double-entries.txt`, `raw/hook-timing.txt`). |
| README.md | The double session log was also seen in the real VS Code on | REPORT A3 (`hooks-sessions.log` has `target=github-copilot` and `target=claude-code` for one session). |
| README.md | and the two permission requests in the real VS Code too [A6] | REPORT A6 (two `hook` requests for `echo '{}' > .vscode/settings.json`). |
| README.md | the five lifecycle hooks that | `source`: `shared/hooks/scripts/run-hook.sh`; probe checks `single-session-log` and `state-sync-once` PASS in `raw/phase-F-require-output.txt`; `raw/phase-D-probe-output.txt`. |
| README.md | The guards never stand down. | `raw/phase-D-condition-matrix.txt` (247 rows, no guard row stands down); probe check `guards-both-sources` PASS. |
| README.md | a deny from either file blocks the call | REPORT F4 last table row ("A `PreToolUse` hook denies and a `preToolUse` hook allows the same call: Denied (deny wins)"). |
| README.md | For one protected edit the runtime raises two hook questions. | Probe check `guards-both-sources` (`raw/phase-F-require-output.txt`); REPORT A6. |
| README.md | VS Code answered the second one itself, so the user saw | REPORT A6 (first answered `"decisionSource":"human_response"`, second `"decisionSource":"host_policy"` 0.3 s later). |
| README.md | the recorded runs show one deny reason for each denied call | REPORT A4 (one "Denied by preToolUse hook" text per denied call); `raw/outcomes-g-both.txt`; Phase D review, recorded in the Phase D session log. |
| README.md | `COPILOT_HOOK_DEPTH` is set, which the Copilot runtime sets only for hook | Planning probe P1 and REPORT A3, A5, A6 (hook processes have it; the VS Code shell tool does not). |
| README.md | `COPILOT_HOOK_DIR` is empty, because the runtime sets it only for | REPORT F2 (file hooks get `COPILOT_HOOK_DIR`, Claude-settings hooks do not); A5. |
| README.md | extra protection: whether Claude Code's hook | `not run`: stated. `raw/phase-D-own-session-run.txt` shows `CLAUDECODE=1` only in the shell environment of the Claude Code session. |
| README.md | A hook from the Claude settings saw `COPILOT_CLI=1` and `COPILOT_HOOK_DEPTH=1` and no | REPORT A5 and A6 (real VS Code, 2026-11-17). |
| README.md | A command run by VS Code's shell tool saw `COPILOT_CLI=1` | REPORT A6 (session `cb2f6974…`, `env \| grep -E '^(COPILOT\|CLAUDE)'`). |
| README.md | A direct run of the launcher on 2026-11-18, in the shell environment of a real Claude Code session, did not stand down | `raw/phase-D-own-session-run.txt` (runs (a) and (b): the reminder printed its context line). |
| README.md | that session loses its session-log | `source`: `shared/hooks/scripts/run-hook.sh`; `raw/phase-D-probe-negative-controls.txt` (a launcher without condition 5 stood both copies down: no session log, 0 pull lines). |
| README.md | state push at `UserPromptSubmit` and `SessionEnd`, or the checkpoint at | `source`: `dist/multi-agent/.claude/settings.json` (those entries carry the marker and stand down); big plan Q1 "Lost by design". |
| README.md | gets only its three-line agent file. It gets no repository instructions and no skill | REPORT F9; `raw/subagent-context.txt` (scripted run, 2026-11-17, no sub-agent hook). |
| README.md | GitHub's documentation agrees. It was not checked in a VS Code window. | REPORT F9 ("Docs confirm it"); RES. `not run` in a window. |
| README.md | A `SubagentStart` hook adds two things to the | `source`: `shared/hooks/scripts/subagent-context.sh`; probe check `subagent-context` PASS (`raw/phase-F-require-output.txt`). |
| README.md | on any error it warns on | `source`: `shared/hooks/scripts/subagent-context.sh`; `raw/phase-E-context-hook-hard-inputs.txt`; `tests/test_hook_gates.py`. |
| README.md | (it is 1,676 bytes on 2026-11-18) | `wc -c dist/multi-agent/.github/copilot-instructions.md` = 1676 on 2026-11-18; the 2,048-byte limit is in `scripts/validate_targets.py`. |
| README.md | judges only that the first user message of each holds the heading | `source`: `scripts/check_copilot_runtime.py` (check `subagent-context`). |
| README.md | recorded run of the same probe on 2026-11-18, with a scratch script | `raw/phase-E-probe-output.txt`, section "What the model received" (from `probe_control.py baseline`; the script is `raw/phase-E-probe-control-harness.py.txt`). |
| README.md | The documentation says the built-in | RES §1 [HR]: "The built-in `general-purpose` agent does not emit `subagentStart` or `subagentStop` events." |
| README.md | lists this event as `subagentStart` and shows no PascalCase name | RES §1 table row for `subagentStart` ("no alias shown"). |
| README.md | also worked there, in a planning check on | Planning probe P2 (`raw/planning-probe-e2-outcomes.txt`, `raw/planning-probe-e2-model-requests.txt`). |
| README.md | reads the text from top-level | Planning probe P2; `raw/phase-E-probe-negative-controls.txt` (nested-only hook fails `subagent-context` in two runs). |
| README.md | also runs `reporting-reminder.sh session | `source`: `dist/multi-agent/.github/hooks/hooks.json` (fourth `SessionStart` entry); probe check `session-reminder` PASS. |
| README.md | In the scripted run of 2026-11-17 the Copilot harness loaded the wrappers and | REPORT F9 (wrappers load, `agents:` ignored; docs: "does not accept `handoffs`, `agents`, or `argument-hint`"). |
| README.md | listed the five wrappers in `.github/agents/` and also found the copies in | REPORT F9 first bullet ("The copies in `.claude/agents/` are also found and lose to the wrappers by name"). |
| README.md | the `reviewer` got `view`, | REPORT F9 ("As a sub-agent, `reviewer` gets only `view`, `grep`, `glob`, and the MCP tools; `bash` and `create` answer 'Tool ... does not exist'"). |
| README.md | A per-agent model pin for Copilot is not built | `decision`/big plan Non-Goals; `shared/agents/*/agent.yaml` `model_intent`; `not built`. |
| README.md | Whether the Local harness runs this hook, and | `not run`: Phase E session log, "Unverified limitations". |
| README.md | Copilot's shell tools go through the same guards | see the `bash` and `run_in_terminal` rows above. |

## docs/target-mapping.md

| File | Short quote | Basis |
| --- | --- | --- |
| docs/target-mapping.md | VS Code runs a Copilot chat in one of two **harnesses**. | Same as the README rows (VS Code hooks page, agent-harnesses page, release notes 1.146; REPORT F1). |
| docs/target-mapping.md | VS Code hooks are "in preview" (VS Code hooks page, read on 2026-11-17) | RES §14. |
| docs/target-mapping.md | (Copilot SDK `1.0.30-preview.0`), run offline with a scripted model | REPORT "How the evidence was gathered" (versions); `raw/phase-F-require-output.txt`. |
| docs/target-mapping.md | reads the top level under both event spellings (`PreToolUse` and `preToolUse`), in a planning check | Planning probe P1 (`raw/planning-probe-e1-outcomes.txt`); REPORT F4 table (top-level `deny` denied under both names). |
| docs/target-mapping.md | The Local harness reads the nested copy only; the reading of VS Code's code is in the [README](../README.md#quick-install). | `source`: see the README row on `executePreToolUseHook`. |
| docs/target-mapping.md | because it was not checked whether the Local harness accepts the camelCase names | `not run`: stated. Big plan "Rejected: renaming the hook events to camelCase". |
| docs/target-mapping.md | top-level `additionalContext` reached the model under `SessionStart` and `PostToolUse` and the nested copy did not [P1] | REPORT F13 table; planning probe P1. |
| docs/target-mapping.md | Before the change the runtime dropped this text. | REPORT F13 ("The bootstrap's reminder prints the nested shape, which is ignored here"); P1. |
| docs/target-mapping.md | The Copilot-harness cells report runs on runtime `1.0.108-0` | Scope sentence for the two parity tables; each cell has its own row. |
| docs/target-mapping.md | all three project servers connected and the Context Mode filter offered exactly | REPORT F12 (`raw/discover-after-trust-hooks-and-mcp.txt`). |
| docs/target-mapping.md | The runtime reads the project's `.mcp.json`, not `.vscode/mcp.json`. | REPORT F12. |
| docs/target-mapping.md | a shell write to `.vscode/settings.json` raised a hook question [A5] | REPORT A5 (real VS Code, 2026-11-17, session `db2427a6…`: the guard's `ask` reached VS Code as a permission request of kind `hook`). |
| docs/target-mapping.md | Offline: the probe checks `ask-*` and the patch checks. | `raw/phase-F-require-output.txt` (`ask-vscode-settings`, `ask-agent-wrapper`, `patch-hook-ask`, `patch-server-ask`, `patch-agent-ask`, `patch-indented-hook-ask` PASS). |
| docs/target-mapping.md | Seen offline: the probe checks `deny-branch` and `camel-deny-branch` | `raw/phase-F-require-output.txt` (both PASS). |
| docs/target-mapping.md | Seen offline: the probe checks `deny-commit` and `deny-pr`, and the camelCase copies | `raw/phase-F-require-output.txt` (`deny-commit`, `deny-pr`, `camel-deny-commit`, `camel-deny-pr` PASS). |
| docs/target-mapping.md | `enforce-commit-gate.sh` and `enforce-pr-gate.sh` are listed in the hook file. | `source`: `dist/multi-agent/.github/hooks/hooks.json` `PreToolUse` entries 4 and 5. |
| docs/target-mapping.md | a `reviewer` sub-agent was given `view`, `grep`, `glob`, and the project's MCP tools [F9] | REPORT F9. |
| docs/target-mapping.md | the runtime found the wrappers in `.github/agents/` and the copies in `.claude/agents/`, and a wrapper wins by name [F9] | REPORT F9. |
| docs/target-mapping.md | a test of the earlier guard, `raw/phase-B-read-tool-before.txt` | `raw/phase-B-read-tool-before.txt` (the Phase B test run against the earlier guard: `github-copilot` gave `ask` for `Read` on a config). A test, not a runtime run. |
| docs/target-mapping.md | No window run shows a sub-agent's read asking. | `not run`: stated. |
| docs/target-mapping.md | These switches do not control the Copilot harness | REPORT F1 (official quote). `Nothing was run for this cell` is stated. |
| docs/target-mapping.md | `bash` and `create` answered that the tool does not exist [F9] | REPORT F9. |
| docs/target-mapping.md | the Copilot harness tool is `bash`, which a hook sees as `Bash` | REPORT F8 table. |
| docs/target-mapping.md | The Copilot harness changes of 2026-11-17 later loosened three decisions on purpose | big plan decision-change table rows L1, L2, L3; `raw/phase-B-differential.md` (rows L1 16, L2 20, L3 148). |
| docs/target-mapping.md | The shell guards (branch, commit, PR) read the model-facing tool name with an object `tool_input`. | REPORT F8 (both key sets); `source`: `shared/hooks/scripts/` readers. |
| docs/target-mapping.md | the probe session `camel-rename` runs a renamed copy and passes | `raw/phase-F-require-output.txt` (`session-camel-rename` and the camel checks PASS). |
| docs/target-mapping.md | In one scripted run on runtime `1.0.108-0` on 2026-11-17 the runtime listed the five path-scoped policies of both folders | REPORT F10. |
| docs/target-mapping.md | Each hook the runtime listed in a planning check on 2026-11-17 carried `enabled` and `disableKey` fields [P4]. | Planning probe P4 (`raw/planning-probe-p4-subfolder-discovery.txt`). |
| docs/target-mapping.md | No documented switch turns off only the Claude-settings copy [F2]. | REPORT F2; RES (no documented switch). |
| docs/target-mapping.md | The two workflow tools are denied on `github-copilot` only, until a run shows | `source`: `shared/hooks/scripts/protect-files.py`; probe checks `deny-workflow-run`, `deny-workflow-manage` PASS; Phase B session log (user decision pending to keep, narrow, or lift). |
| docs/target-mapping.md | If "Allow all" approves a guard question with no person's answer | `not run`: stated; user decision recorded in the big plan "Pre-branch gate". |
| docs/target-mapping.md | reached the model in one scripted run on runtime `1.0.108-0`, although GitHub's documentation says the runtime drops that output [F13] | REPORT F13; RES §3 (the reference says command and HTTP hook output is dropped). |
| docs/target-mapping.md | The macOS job of the `Validate` workflow runs a short list of the new shell calls after a push. Its result has not been read. | `source`: `.github/workflows/validate.yml`; Phase C session log ("`gh` is not signed in on this machine"); the Phase D and E logs name the macOS job as a limitation. `not run`/unread. |
| docs/target-mapping.md | listed as agents by offline discovery on the Copilot harness, runtime `1.0.108-0` (2026-11-18) | `raw/phase-F-sidecar-discover-workflow.txt`. |
| docs/target-mapping.md | In the real VS Code on 2026-11-17 (VS Code 1.146.0, runtime `1.0.108-0`), the automatic model choice picked `gpt-6-luna` | REPORT A4. |
| docs/target-mapping.md | The names `AskUserQuestion` and `tool_search_tool` were seen only in the real VS Code, on 2026-11-17 [A4]. | REPORT A4. |
| docs/target-mapping.md | three `apply_patch` calls by the Auto-chosen `gpt-6-luna` were each denied with "hook exited with code 2" [A4] | REPORT A4 (session `e52234c6…`). |
| docs/target-mapping.md | Offline, on runtime `1.0.108-0`, the same happened for the six Codex-family models [F6]. | REPORT F6; `raw/outcomes-c1.txt`, `raw/guard-errors-patch-tool.txt`. |
| docs/target-mapping.md | the read approvals were given by VS Code (`"decisionSource": "host_policy"`), not by the user [A4]. | REPORT A4. |
| docs/target-mapping.md | the earlier guard asked for that read (a test of the earlier guard | `raw/phase-B-read-tool-before.txt`. |

## docs/runtime-checks.md

| File | Short quote | Basis |
| --- | --- | --- |
| docs/runtime-checks.md | VS Code runs a Copilot chat in one of two **harnesses**. | Same as the README rows. |
| docs/runtime-checks.md | This bootstrap supports the Copilot harness inside VS Code. | `decision`. |
| docs/runtime-checks.md | It does not claim Copilot CLI or Copilot cloud agents. | `decision`. |
| docs/runtime-checks.md | `Copilot runtime version: 1.0.108-0` (VS Code 1.146.0, Copilot SDK | `raw/phase-F-require-output.txt`. |
| docs/runtime-checks.md | `Result: PASS (0 of 48 checks failed)` | `raw/phase-F-require-output.txt`. |
| docs/runtime-checks.md | the custom-agent frontmatter, the hook file's events and commands, and the size of `.github/copilot-instructions.md` | `source`: `scripts/validate_targets.py` (`COPILOT_EXPECTED_EVENTS`, the 2,048-byte check). |
| docs/runtime-checks.md | the Auto choice was `gpt-6-luna`, and it was given | REPORT A4; `raw/tools-by-model.txt`. |
| docs/runtime-checks.md | The Local harness reads the nested copy only. That comes from VS Code's | `source`: see the README row on `executePreToolUseHook`. |
| docs/runtime-checks.md | found no difference (944 comparisons, | `raw/phase-C-byte-identity-battery.txt` ("github-copilot comparisons with an answer: 944 … nested object byte-identical, only top-level fields added"). |
| docs/runtime-checks.md | Its last full run, on 2026-11-18, printed runtime `1.0.108-0` (VS Code 1.146.0) and | `raw/phase-F-require-output.txt`. |
| docs/runtime-checks.md | VS Code answered the second request itself [A6] | REPORT A6. |
| docs/runtime-checks.md | The deny half was first seen in a scripted run with probe hooks on | REPORT F4 (`raw/outcomes-d1.txt`); `raw/phase-C-probe-negative-controls.txt` for the probe's own camelCase checks. |
| docs/runtime-checks.md | (seen in the real VS Code on 2026-11-17 [A4]) | REPORT A4. |
| docs/runtime-checks.md | freezes a Copilot chat in VS Code (on 2026-11-17 [A1]) | REPORT A1. |
| docs/runtime-checks.md | A planning check of 2026-11-17 on a subfolder two levels below the root [P4] | Planning probe P4. |
| docs/runtime-checks.md | a scripted run of 2026-11-17 with both hook files) [F3] | REPORT F3; `raw/outcomes-g-both.txt`. |
| docs/runtime-checks.md | A planning check of 2026-11-17 on the shell helper tools [P3] | Planning probe P3; `raw/planning-probe-e3-outcomes.txt`. |
| docs/runtime-checks.md | Since the Copilot hook file got its `SubagentStart` entry | `raw/phase-E-probe-output.txt` (28 hooks after trust: 14 and 14); `raw/phase-F-require-output.txt` (`hooks-sources`: 28 hooks). |
| docs/runtime-checks.md | the three stand-down checks (`single-session-log`, `state-sync-once`, and `guards-both-sources`) included | `raw/phase-E-probe-before.txt` (the install put back: only `session-reminder` and `subagent-context` failed). |

## docs/smoke-tests.md

| File | Short quote | Basis |
| --- | --- | --- |
| docs/smoke-tests.md | Select **Copilot** from the **Session Target** UI control to use the Copilot harness. | Official VS Code hooks page quote, RES §13 [VS-hooks], read 2026-11-17. |
| docs/smoke-tests.md | It was `1.0.108-0` with VS Code 1.146.0 on 2026-11-17. | REPORT A3 (`copilotVersion: 1.0.108-0`). |
| docs/smoke-tests.md | The real-window runs of 2026-11-17 | REPORT A3 to A6. Models: `mai-code-1.1-flash` (A3) and `gpt-6-luna` (A4). |
| docs/smoke-tests.md | The recorded runs show no run of any item in a signed-in window since the | Phase B to E session logs (optional items `NOT RUN`). |
| docs/smoke-tests.md | 0 hooks and 0 MCP servers before trust, 28 hooks after | REPORT F15 (0 and 0 before trust); `raw/phase-F-require-output.txt` (`hooks-untrusted`: 0; `hooks-sources`: 28). |
| docs/smoke-tests.md | `listen EACCES: permission denied /run/user/<uid>/vscode-ipc-<id>.sock` | REPORT A1 (198 starts in `agenthost.log`, VS Code's own logs). |
| docs/smoke-tests.md | the same log loop is in the VS Code logs of 2026-10-26 and 2026-11-12 | REPORT A1. |
| docs/smoke-tests.md | sudo install -d -m 700 -o "$(id -u)" -g "$(id -g)" /run/user/$(id -u) | The command the user ran on 2026-11-17 (REPORT A3: "created `/run/user/1000` with `sudo` and reloaded the window"; command text in the big plan "Pre-branch gate"). |
| docs/smoke-tests.md | Denied by preToolUse hook: Blocked dangerous git operation: git reset --hard | REPORT A4. |
| docs/smoke-tests.md | Seen offline, with the current guards: probe check `deny-git-reset` | `raw/phase-F-require-output.txt`. |
| docs/smoke-tests.md | No recorded run shows a deny reason twice. | Same as the README row. |
| docs/smoke-tests.md | Editing agent, hook, or server configuration requires approval: .vscode/settings.json | REPORT A5 (`hookMessage`). |
| docs/smoke-tests.md | the runtime raised two permission requests of kind `hook`, one for each hook file | REPORT A6. |
| docs/smoke-tests.md | VS Code approved the second 0.3 seconds later by itself, so the user saw one dialog [A6] | REPORT A6. |
| docs/smoke-tests.md | The same run asked again for the read of the file with the read tool | REPORT A6. |
| docs/smoke-tests.md | the current guards give that read no decision (offline probe check `read-agent-file`) | `raw/phase-F-require-output.txt` (`read-agent-file` PASS; the check reads `.claude/agents/coder.md`). |
| docs/smoke-tests.md | the session recorded `"permissionMode":"manual"` | REPORT A6. |
| docs/smoke-tests.md | GitHub's hooks reference says that in Copilot CLI autopilot mode no prompt is shown and a hook `ask` is denied | RES §1 [HR] decision table (https://docs.github.com/en/copilot/reference/hooks-reference). |
| docs/smoke-tests.md | `gpt-6-luna` used `apply_patch` and every call was denied with | REPORT A4. |
| docs/smoke-tests.md | session `codex-patch` with the model id `gpt-5.2-codex` creates a plain file (probe check `patch-plain-allowed`) | `raw/phase-F-require-output.txt` (`session-codex-patch`, `patch-plain-allowed` PASS). |
| docs/smoke-tests.md | `Glob`, `Edit` (for `apply_patch`), `Write` (for `create`), | REPORT A4. |
| docs/smoke-tests.md | the agent host log shows each of the three connected once; VS Code added its own `pylance mcp server` and | REPORT A3. |
| docs/smoke-tests.md | The three-tool filter was seen offline only. | REPORT F12 (`raw/discover-after-trust-hooks-and-mcp.txt`). |
| docs/smoke-tests.md | describes the setting as "Enable using custom agents in Copilot harness sessions", with the default `false` | REPORT F9 ("Docs: the setting `github.copilot.chat.cli.customAgents.enabled` … default `false`"). |
| docs/smoke-tests.md | offline, the runtime lists the five agents [F9] | REPORT F9; `raw/phase-A-discover-output.txt`. |
| docs/smoke-tests.md | a `reviewer` sub-agent started through the `task` tool [A6] | REPORT A6 (session `ed99e1e6…`). |
| docs/smoke-tests.md | probe checks `subagent-context` (the first message of `coder` | `raw/phase-F-require-output.txt` (`subagent-context` PASS). |
| docs/smoke-tests.md | `session-reminder` (the first user message of the first | `raw/phase-F-require-output.txt` (`session-reminder` PASS). |
| docs/smoke-tests.md | was logged under both targets [A3] | REPORT A3. |
| docs/smoke-tests.md | probe check `single-session-log` | `raw/phase-F-require-output.txt`. |
| docs/smoke-tests.md | No recorded run of a Local-harness deny exists | `not run`; a search of the six files and of the evidence report found none. |
| docs/smoke-tests.md | the event fired once when a chat was replaced in the real VS Code on | REPORT A3 ("`sessionEnd` fired when the chat was replaced"). |
| docs/smoke-tests.md | The bootstrap wires no `sessionEnd` hook on the Copilot harness | `source`: `dist/multi-agent/.github/hooks/hooks.json` (no `SessionEnd`); the Claude settings `SessionEnd` entry stands down there. |
| docs/smoke-tests.md | `bash` in the Copilot harness | REPORT F8. |
| docs/smoke-tests.md | The Copilot-harness part was run offline on runtime `1.0.108-0` (probe checks `read-agent-file`, `search-secret-denied`, and `search-glob-not-judged`) | `raw/phase-F-require-output.txt`. |
| docs/smoke-tests.md | That command does not cover Copilot. | `docs/native-client-acceptance.md` lines 3 to 6 ("GitHub Copilot remains covered by the deterministic generated-target checks, not this native-client command"). |
| docs/smoke-tests.md | five events: `SessionStart`, `PreToolUse`, `PostToolUse`, `Stop`, and | `source`: `dist/multi-agent/.github/hooks/hooks.json`. |

## docs/architecture.md

| File | Short quote | Basis |
| --- | --- | --- |
| docs/architecture.md | The Copilot adapter is five groups of generated files | `source`: `dist/multi-agent/` listing; `docs/target-mapping.md` Native Adapters file list. |
| docs/architecture.md | What the Copilot harness does with these files was seen in scripted runs on runtime `1.0.108-0` | REPORT; `raw/phase-F-require-output.txt`. |
| docs/architecture.md | The Copilot harness loads both `.github/hooks/hooks.json` and `.claude/settings.json` [F2] | REPORT F2. |
| docs/architecture.md | The Copilot harness reads the project's `.mcp.json`, not `.vscode/mcp.json` [F12]. | REPORT F12. |
| docs/architecture.md | How the Local harness reads it was not rechecked. | `not run`: stated. |
| docs/architecture.md | the copies in `.claude/agents/`, and a wrapper wins by name [F9] | REPORT F9. |
| docs/architecture.md | A sub-agent there gets only its three-line wrapper. | REPORT F9. |
| docs/architecture.md | loads `.github/copilot-instructions.md`, `AGENTS.md`, `CLAUDE.md`, and the always-on instruction files into its system prompt | REPORT F10; `raw/instructions-in-system-prompt.txt`. |
| docs/architecture.md | about 10.8 KB of a 48.6 KB system prompt was root guidance loaded three times | REPORT F10. |
| docs/architecture.md | `.github/copilot-instructions.md` is needed by the Local harness and, through the `SubagentStart` hook in the bullet above, by every sub-agent on the Copilot harness. | `source`: `shared/hooks/scripts/subagent-context.sh` reads `.github/copilot-instructions.md`; probe check `subagent-context` PASS (`raw/phase-F-require-output.txt`); the Local-harness use is the big plan's Q5 design note (not a run). |
| docs/architecture.md | for the Copilot harness (the agent runtime of VS Code's Copilot chat | scope; same as the README rows. |

## docs/sidecar-provider-contract.md

| File | Short quote | Basis |
| --- | --- | --- |
| docs/sidecar-provider-contract.md | VS Code 1.146.0 (commit `69047191fc427f2f92828279aae1d90d8eeda7ab`), | printed by `--discover`: `raw/phase-F-sidecar-discover-skills.txt` and `-workflow.txt`. |
| docs/sidecar-provider-contract.md | 10 units installed | `raw/phase-F-sidecar-discover-skills.txt` ("sidecar-install: installed 10"). |
| docs/sidecar-provider-contract.md | 68 units installed | `raw/phase-F-sidecar-discover-workflow.txt` ("installed 68"). |
| docs/sidecar-provider-contract.md | `.github/instructions/ai-bootstrap-sidecar.instructions.md` and `.claude/rules/ai-bootstrap-sidecar.md` | `raw/phase-F-sidecar-discover-skills.txt` ("instructions: 2 (...)" and the raw record `sourcePath` values). |
| docs/sidecar-provider-contract.md | `.claude/rules/ai-bootstrap-reporting.md`, `.claude/rules/ai-bootstrap-tool-routing.md`, and `.claude/rules/ai-bootstrap-workflow.md` | `raw/phase-F-sidecar-discover-workflow.txt` ("instructions: 4 (...)"). |
| docs/sidecar-provider-contract.md | Both runs printed 0 hooks and 0 MCP servers. | Both raw files ("hooks: 0", "MCP servers: 0"). |
| docs/sidecar-provider-contract.md | `git status --short` printed nothing after the install | Both raw files, section "git status --short". |
| docs/sidecar-provider-contract.md | the ignored paths were `.agents/`, `.claude/`, and `.github/` | Both raw files, section "git status --short --ignored". |
| docs/sidecar-provider-contract.md | an Agent Host session with the Copilot harness loaded only the `.github/instructions/` bridge | This document's own Step 4 matrix, row "Agent Host, Copilot harness" (2026-09-25, VS Code 1.139.0, Copilot Chat 0.67.0): "`.claude/rules/ai-bootstrap-sidecar.md` did not load". |
| docs/sidecar-provider-contract.md | Only the Local agent session loaded both. | Same document, row "Local agent". |
| docs/sidecar-provider-contract.md | the runtime lists the five `.claude/agents/<id>.md` files as agents (source `project`) | `raw/phase-F-sidecar-discover-workflow.txt`, raw record `agents.discover` (`path`, `source: project`). |
| docs/sidecar-provider-contract.md | The runtime listed the Claude-format `tools` names (`Edit`, | Same raw record (`tools: ["Edit","Write","Bash","Read",...]`, `model: sonnet`/`opus`). |
| docs/sidecar-provider-contract.md | attached a `github-mcp-server` entry with the tool `web_search` to `coder` and `planner` | Same raw record (`mcpServers.github-mcp-server`, `tools: ["web_search"]`). Cause not investigated, as stated. |
| docs/sidecar-provider-contract.md | the runtime listed the copy at `.agents/skills/<name>/SKILL.md` and none at | Same raw record `skills.discover` (`path` values; 4 of 4 and 22 of 22 under `.agents/skills/`). |
| docs/sidecar-provider-contract.md | the setting `github.copilot.chat.cli.customAgents.enabled` (documented default `false`) | REPORT F9 (Docs). `was not tried` is stated. |
| docs/sidecar-provider-contract.md | VS Code hooks are "in preview" (VS Code hooks page, read on 2026-11-17). | RES §14. |

## Kept claims (not rewritten in this phase; the basis is the one the earlier phases recorded)

| File | Short quote | Basis |
| --- | --- | --- |
| docs/target-mapping.md | Both hook files in a project run on the Copilot harness | REPORT F2; A3. |
| docs/target-mapping.md | The file guard `protect-files.py` receives every tool call from the first file. | REPORT F3 ("the Claude settings route only `Edit\|Write` and `Bash` to the file guard"); `source`: `dist/multi-agent/.claude/settings.json`. |
| docs/target-mapping.md | The runtime then sends the PascalCase tool name and the `tool_input` key. | REPORT F8 (first table). |
| docs/target-mapping.md | The argument names stay the runtime's (`path`, `file_text`) | REPORT F8. |
| docs/target-mapping.md | The runtime tools were run offline on VS Code 1.146.0 with runtime `1.0.108-0` | `raw/phase-B-tool-handling-evidence.txt` (tool inventory and one call per tool); `raw/phase-A-probe-evidence.txt`. |
| docs/target-mapping.md | The tools `write_bash` and `bash_shutdown` are named in the source of VS Code's agent host. | REPORT F8, paragraph "Source". |
| docs/target-mapping.md | Offline, only Codex-family model ids such as `gpt-5.2-codex` get `apply_patch` and `rg`. | REPORT F6; `raw/tools-by-model.txt`. |
| docs/target-mapping.md | So the guard maps tools by their hook name and input, never by model. | `source`: `shared/hooks/scripts/protect-files.py`; `raw/phase-B-differential.md`. |
| docs/target-mapping.md | Probe check `helper-tools` | `raw/phase-F-require-output.txt` (PASS); planning probe P3 (`raw/planning-probe-e3-outcomes.txt`). |
| docs/target-mapping.md | Probe session `codex-patch` | `raw/phase-F-require-output.txt` (`session-codex-patch` and six patch checks PASS). |
| docs/target-mapping.md | Searches a GitHub repository; it needs a login. | `raw/phase-B-tool-handling-evidence.txt` (call `semantic_code_search`: "401 … Requires authentication"). |
| docs/target-mapping.md | SQL on the private session database | `raw/phase-B-tool-handling-evidence.txt` (`sql` calls). |
| docs/target-mapping.md | Five statements were tried | `raw/phase-B-tool-handling-evidence.txt` (`ATTACH`, `VACUUM INTO`, `load_extension`, `PRAGMA database_list`, `writefile`). |
| docs/target-mapping.md | Only a sub-agent of type `general-purpose` is offered it offline. | `raw/phase-B-tool-handling-evidence.txt` (`session_store_sql` calls in the `general-purpose` sub-agent). |
| docs/target-mapping.md | It asks the person a question. Seen only in the real VS Code. | REPORT A4. |
| docs/target-mapping.md | It searches tool names. Seen only in the real VS Code. | REPORT A4. |
| docs/target-mapping.md | Not offered offline (the probe project has no `.mcp.json`). | `source`: `scripts/check_copilot_runtime.py` (`mcp-none`); `raw/phase-A-probe-evidence.txt`. |
| docs/target-mapping.md | An offline session cannot start one | `raw/phase-B-tool-handling-evidence.txt` ("extensions are not configured for session"; `workflow_not_found`). |
| docs/target-mapping.md | A patch with no end marker | `source`: `tests/test_protect_files_copilot_harness.py`; `raw/phase-B-differential.md`. |
| docs/target-mapping.md | in a probe run on 2026-11-18 on runtime `1.0.108-0`, after the probe approved the guard's question, it created the file named by an indented `Add File` header | `raw/phase-F-indented-patch-created.txt` (the file `.github/hooks/evil-indented.json` exists after `check_copilot_runtime.py --keep`). |
| docs/runtime-checks.md | The Copilot-harness search tools | Probe checks `search-secret-denied`, `search-glob-not-judged` in `raw/phase-F-require-output.txt`; REPORT F7. |
| docs/runtime-checks.md | The `main` session has 28 checks, `codex-patch` has 6, and `camel-rename` has 11. | `raw/phase-F-require-output.txt` (28 + 6 + 11 checks and 3 session lines = 48 lines). |
| docs/runtime-checks.md | A run prints 48 lines. | `raw/phase-F-require-output.txt`. |
| docs/runtime-checks.md | Evidence behind the design. | Each row of the table "Unknown / Result / Evidence" names its own evidence in its last column (`raw/phase-A-probe-evidence.txt` sections 1 to 7 and later `raw/phase-*` files). |
| docs/smoke-tests.md | The reminder text is exactly 183 bytes | `source`: `shared/hooks/scripts/reporting-reminder.sh` (`REMINDER`, 183 characters); `raw/phase-E-probe-output.txt` ("holds the reminder (183 characters)"). |
| docs/smoke-tests.md | `prompt` and `late-report` are refused for Copilot | `source`: `shared/hooks/scripts/reporting-reminder.sh` (the `case "$PROVIDER:$MODE"` list); `tests/test_hook_gates.py`. |

## Added in fix round 1 (2026-11-18)

| File | Short quote | Basis |
| --- | --- | --- |
| README.md | (Sources: the VS Code hooks page, read on 2026-11-17, and the VS Code 1.146 | REPORT F1: hooks page "The Local harness is deprecated and will be removed in February 2027"; VS Code 1.146 release notes (2026-11-11) "will be removed in three months (February 2027)"; RES §13 [VS-harness] "removed by February 2027". The same wording is used at the first mention of the date in each of the six files. |
| README.md | The guards print each decision twice in one line: once at the top | `raw/phase-C-byte-identity-battery.txt` ("nested object byte-identical, only top-level fields added"); `source`: `shared/hooks/scripts/_lib-frontmatter.sh`. Top level is the documented shape: REPORT F4 ("The documentation names only the top-level shape"). |
| README.md | A missing file is silent; the other cases (a link, over the limit | `source`: `shared/hooks/scripts/subagent-context.sh`; `tests/test_hook_gates.py`; `raw/phase-E-context-hook-hard-inputs.txt`. |
| README.md | with `python3` and `json.dumps`, because the shell library's | `source`: `shared/hooks/scripts/subagent-context.sh` and `_lib-frontmatter.sh` (`additional_context` replaces control characters with spaces). |
| README.md | The root-guidance budget table applies a header rule and lifecycle rules that this | `source`: `scripts/validate_targets.py` (`POLICY_BYTE_BUDGETS` and the separate check for `.github/copilot-instructions.md`). |
| README.md | The probe renames the event to `subagentStart` in its | `source`: `scripts/check_copilot_runtime.py` and `scripts/copilot_runtime_probe.mjs` (the `camel-rename` session has no `task` call). |
| README.md | reporting reminder once. The mode `session` is accepted only for | `source`: `shared/hooks/scripts/reporting-reminder.sh` (the `case "$PROVIDER:$MODE"` list; `REMINDER` is 183 characters, ceiling 200). |
| README.md | In the recorded run of 2026-11-18 the reminder was a user message of its own | `raw/phase-E-probe-output.txt` ("main user message [0] (183 characters)" holds the reminder, before the prompt). |
| README.md | A hook that prints only the nested copy did not reach the model, for the sub-agent text | `raw/phase-E-probe-negative-controls.txt` (two runs each). |
| README.md | `render_github_agent_adapter` did not change. | `git diff 2e8c7bb HEAD -- scripts/generate_targets.py` changes only `_claude_hook_cmd`. |
| README.md | The launcher never stands this | `source`: `shared/hooks/scripts/run-hook.sh` (list of five lifecycle scripts); `tests/test_lifecycle_hooks.py`. |
| README.md | The generated `.claude/settings.json` marks each hook command | `source`: `scripts/generate_targets.py` `_claude_hook_cmd`; `raw/phase-D-generated-files.txt`; `scripts/validate_targets.py` checks both. |
| README.md | A new launcher with old settings finds no marker and runs | `raw/phase-D-mixed-installs.txt`, `raw/phase-D-probe-negative-controls.txt`. |
| docs/target-mapping.md | The README holds the detail, with the run and version behind each statement | Pointer sentence; the README sections "Hooks on the Copilot harness" and "Sub-agents on the Copilot harness" hold the runs (rows above). |
| docs/target-mapping.md | A statement about the Local harness rests on tests and VS Code source unless it names a run. | Description of the method; tests are named in the Evidence columns, the source reading is in the README. |
| docs/target-mapping.md | The Copilot harness loads three files that hold hooks or MCP servers | REPORT F2 (both hook files) and F12 (`.mcp.json`); scripted runs of 2026-11-17 on runtime `1.0.108-0`. |
| docs/target-mapping.md | A `Write` or `Edit` of one of these files asks when the guard runs as `github-copilot`. | `raw/phase-F-fix-round-1.txt` section "guard decisions" (a run of `protect-files.sh github-copilot` on 2026-11-18: `Write` of four files and `Edit` of `.claude/settings.json` gave `ask`; `Read` of two files gave no decision). |
| docs/target-mapping.md | Edits of the Local-harness files ask, and so do edits of the three files | Same row. |
| docs/target-mapping.md | A per-agent Copilot model pin. The agent `model` stays `target-default`. | Big plan Non-Goals; `not built`. |
| docs/target-mapping.md | Do not remove it: the `SubagentStart` hook gives its text to sub-agents | `source`: `shared/hooks/scripts/subagent-context.sh`; probe check `subagent-context` PASS (`raw/phase-F-require-output.txt`). |
| docs/target-mapping.md | A planning check is a short offline run made on 2026-11-17 while the plan was written. | Big plan "Planning probes (2026-11-17, runtime `1.0.108-0`, offline, scripted local model)". |
| docs/target-mapping.md | "Auto" is the automatic setting of VS Code's model picker | REPORT A3 ("The model was chosen by Auto"). |
| docs/runtime-checks.md | VS Code 1.146 release notes of 2026-11-11 | Same as the README source row. |
| docs/runtime-checks.md | The dates differ. The probe note, the earlier scripted runs | `raw/phase-F-fix-round-1.txt` section "dates of the raw files" (the date at the top of each file, and the files that carry none). |
| docs/smoke-tests.md | Items 1, 9, and 10 ask the agent to run `git reset --hard HEAD`. | The item texts themselves; the command's effect is Git's documented behavior. |
| docs/smoke-tests.md | Item 2 asks the agent to run `echo '{}' > .vscode/settings.json`. | REPORT A5/A6 (the command used on 2026-11-17). |
| docs/smoke-tests.md | found seven other VS Code server sessions in which the agent host used a socket under `/tmp` | REPORT A1 ("absent from seven other VS Code server sessions, where the agent host listened on a socket under `/tmp`"). |
| docs/smoke-tests.md | On 2026-11-17 the recovery needed the folder and a window reload [A3]. | REPORT A3 ("The user created `/run/user/1000` with `sudo` and reloaded the window"). |
| docs/smoke-tests.md | The log records the event, target, session id, source, and prompt of each hook call, not | `source`: `shared/hooks/scripts/session-log.sh` lines 33 to 50 (`sessionId`, `source`, `prompt` fields); `raw/session-log-double-entries.txt` (line format). |
| docs/smoke-tests.md | Rule: read the tool name. If it is not `apply_patch`, the item is "not | Item rule; basis for the model facts: REPORT A4 and F6. |
| docs/smoke-tests.md | Auto is the automatic setting of VS Code's model picker | REPORT A3. |
| docs/architecture.md | The Local harness was not run with the current answer format or the current hooks. | Phase C session log, "Unverified limitations". |
| docs/architecture.md | sources: the VS Code hooks page, read on 2026-11-17, and the VS Code 1.146 release notes | Same as the README source row. |
| docs/sidecar-provider-contract.md | The dated records below also name a session type called "Agent Host, Claude harness". | This file's own Step 3 text and the 2026-09-27 matrix row "Agent Host, Claude harness" (all cells `unverified`). |
| docs/sidecar-provider-contract.md | (VS Code's older built-in agent, which VS Code removes in February 2027; sources: | Same as the README source row. |
