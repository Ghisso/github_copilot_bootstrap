# Independent critique of the draft plan `copilot-harness-migration`

**Date:** 2026-11-17. **By:** a separate read-only agent (Opus, effort
`xhigh`) with the `devils-advocate` skill. **Subject:** planner draft 1
(`.claude/plans/copilot-harness-migration.md` and its seven phase files as
first saved). The agent did not know Addendum A4 of `REPORT.md` (the user's
real VS Code checks), which arrived while it ran.

## Verdict

Most of the plan is supported by the code and the recorded runs. The order
(A, then B, C, D, E, F, G) is right, and the stand-down signal cannot switch
guards off in Claude Code, Codex, Antigravity, or the Local harness.

Two problems block approval:

- The patch-text change opens a new hole. It is not in the decision-change
  table.
- The stand-down trusts that `.github/hooks/hooks.json` exists, not that the
  runtime actually loads it. The documentation names cases where the
  Claude-settings copy would stand down while the Copilot-file copy never
  runs. That leaves no guards at all.

Separately, the probe is described as "offline", but it is not: it starts MCP
servers that reach the network.

## Change items

**1. HIGH. Phase D step 2 and decision row L3 (patch text).**

- `add_patch_paths` only matches header lines that start exactly with the
  marker (`line.startswith(prefix)`,
  `shared/hooks/scripts/protect-files.py:911-917`). A header with leading
  blanks gives no target, so no decision.
- Run: `protect-files.py github-copilot` with
  `{"tool_name":"apply_patch","tool_input":{"input":"*** Begin Patch\n  *** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n"}}`
  gives exit 0 and no output. The same patch without the leading blanks
  gives `ask`. Today a patch sent as plain text always crashes and is denied
  (exit 2). After Phase D, an indented header would pass with no decision.
- The runtime binary contains the patch parser messages from Codex
  (`is not a valid hunk header. Valid hunk headers: '*** Add File: {path}'...`,
  `The first line of the patch must be '*** Begin Patch'`). Codex's
  open-source parser trims the first line of each hunk. Whether the runtime
  kept that behavior was not run.
- Smallest fix: in `add_patch_paths`, match on `line.strip()` (this only
  adds targets, so it only tightens, for the shell and object paths too);
  fail closed on any stripped line that starts with `*** ` but is not a
  known marker; add test rows for an indented header and a lowercase header;
  add one probe step: an indented `*** Add File: .github/hooks/evil.json`
  must ask.

**2. HIGH. Phase C step 2, condition 5, and decisive assumption DA4.**

- The stand-down checks only that the Copilot hook file exists and contains
  the five strings. In these cases the Claude-settings hooks still run, the
  Copilot-file hooks do not, and after Phase C nothing guards (today the
  Claude copy still guards):
  - (a) `"disableAllHooks": true` inside `.github/hooks/hooks.json` skips
    only that file. A consumer may have added it to stop the double run.
  - (b) A session started from a subfolder of the repository. Copilot CLI
    changelog 1.0.111 warns that, run from a subdirectory, "the hooks at the
    repository root were not loaded". Whether the root
    `.claude/settings.json` loads there is unknown.
  - (c) The runtime drops a malformed item "and logs" it, while sibling
    sources still load.
- Smallest fixes: condition 5 also requires that the file does not contain
  `disableAllHooks`; add a Phase A discovery check started from a subfolder
  of the probe project, and the same question to gate check (c); add the
  condition that `COPILOT_HOOK_DIR` is empty (it is set only for
  `.github/hooks` hooks; without it an inherited `BOOTSTRAP_HOOK_SOURCE`
  would make both copies stand down); put the remaining risk (c) in the
  risk table. See the question for the user below.

**3. MEDIUM. Phase A (the "offline" claim).** The real full install's
`.mcp.json` starts `uvx --from semble[mcp] semble` and
`npx -y @upstash/context7-mcp`. The planning probes show all three servers
"connected" in every session. So the probe needs PyPI and npm on a cold
cache, can spend MCP connect time inside the 480-second cap, and is not
deterministic. Fix: delete `.mcp.json` from the temporary project, or start
the session with no MCP servers; check that zero servers connected; only
then call the probe offline.

**4. MEDIUM. Gate check (c), Phase C negative case.** "Claude Code started
from a Copilot shell has no `COPILOT_HOOK_DEPTH`" rests on P1, which measured
the SDK runtime's own `bash`. VS Code can replace the shell tool with its
own `bash` and `write_bash`. Condition 4 (`CLAUDECODE`) is also unverified
for hook processes. Fix: in gate check (c), run
`env | grep -E '^(COPILOT|CLAUDE)'` through the VS Code shell tool and
require that `COPILOT_HOOK_DEPTH` is absent.

**5. MEDIUM. Unmapped tools.** Sessions offer `run_dynamic_workflow`,
`dynamic_workflows_manage`, `sql`, `semantic_code_search`, `write_agent`,
and `fetch_copilot_cli_documentation`. F8 and Phase D never map their
inputs. If one of them can run a command or write a file, `protect-files`
gives no decision and the shell guards skip it. Fix: Phase A prints each
tool's input schema (the runner already records `firstRequestTools`); Phase
D then adds a row per tool or a recorded follow-up.

**6. LOW. Phase B step 5 and the "rename safe after Phase B" follow-up.**
The camelCase session checks only `git reset`, `rm .env`, the settings
question, and plain calls. The commit, branch, and pull-request gates read
`"command"` with awk from the raw text (`_lib-frontmatter.sh:108-162`). Fix:
add `camel-deny-commit`, `camel-deny-branch`, `camel-deny-pr`, and
`camel-ask-agent-wrapper`; word the follow-up as "Phase B removes the output
blocker".

**7. LOW. Phase E step 4.** Putting the 2 KiB budget in
`ROOT_GUIDANCE_BUDGETS` would fail the Copilot file, because
`validate_root_guidance` (`scripts/validate_targets.py:1259-1265`) runs
`root_guidance_errors` (`:685-700`) on every entry, which requires
`ROOT_GUIDANCE_HEADERS` and the canonical lifecycle. Fix: a separate byte
check.

**8. LOW. Phase D step 1.** "`read_bash` with a `command` that names `.env`:
deny" is the wrong expected value; shell reads of `.env` are allowed
(`tests/test_hook_gates.py:2134-2152`). Fix: use `rm -f .env`.

**9. LOW. Phase D step 8.** Comparing the working copy with
`git show dev:...protect-files.py` byte for byte will list every Copilot
deny or ask row, because Phase B changed `emit`. Fix: compare the parsed
`permissionDecision` and the exit code, or compare against the Phase C
commit.

**10. LOW. Phase F verification.** Two checks already pass today
(`grep -q -F 'chat.useClaudeHooks' docs/smoke-tests.md` and
`grep -q -F 'Copilot harness' docs/sidecar-provider-contract.md`). Fix: grep
for text only the new content has.

**11. LOW. The missing-folder note (gate, Phase F).** "Create the folder
first" is not enough: a folder created with plain `sudo mkdir` is owned by
root, and the folder is lost at every WSL restart. Fix: give the full
command
`sudo install -d -m 700 -o "$(id -u)" -g "$(id -g)" /run/user/$(id -u)` and
say it must be repeated after each restart.

**12. LOW. Phase A runtime discovery.** "Newest folder" is not defined, and
only a VS Code server install is known to ship a separate `node`. Fix: say
"newest by folder modification time" and record this limit in the docs.

**13. LOW. Phase D scope.** If the user answers "no" to the search-tools
question, removing step 5 is not enough: also remove the step 6 check
`search-secret-denied`, the T1 text in step 7, the T1 row, and REQ-005.

**14. LOW. Over-building.** `--format json` has no consumer; drop it. Phase
F is documentation only; its required probe run could move to Optional
Verification.

**15. LOW. Phase B.** The library will choose the output shape from
`${TARGET_ID:-}`. Scripts that never assign it (`openwiki-guard.sh`, the
existing modes of `reporting-reminder.sh`) would follow an exported
`TARGET_ID=github-copilot`. Fix: have those scripts assign or unset
`TARGET_ID`.

**Not blocking:**

- `json_escape` does not escape control characters
  (`_lib-frontmatter.sh:8-10`). On Copilot, invalid JSON means the tool
  runs. An old weakness, now more relevant.
- Planning probe e3 step 06: a `read_bash` ran with no pre-tool hook at all.
  It looks like the runtime's own read of a finished background shell. The
  probe's evaluation should expect this.
- After the stand-down, the Copilot harness loses the Claude-settings state
  push at `SessionEnd` and `UserPromptSubmit`. The Copilot file still pushes
  at every `Stop`. Document it.
- After Phase B, the context text from `session-start-state.sh` and
  `record-branch-state.sh` starts reaching the Copilot model. Today it is
  dropped. Document it.
- `SubagentStart` has no documented PascalCase alias. The docs must say
  "observed", not "documented".
- F10 says the path-scoped policies are offered twice
  (`.github/instructions/` and `.claude/rules/`). This is not recorded as a
  follow-up.

## Question for the user

How much should stand down on the Copilot harness?

- **(A) As planned:** every Claude-settings hook stands down when the
  conditions hold. One approval question per protected edit and one
  session-log entry. Risk: if the runtime ever silently stops running the
  `.github/hooks` copy on some consumer's machine, Copilot sessions there
  have no guards until someone runs the probe.
- **(B) Only the lifecycle hooks stand down** (session log, state sync,
  session-start state, reminders). The Claude-settings guards keep running.
  Denies happen twice, which is harmless because a deny wins. Cost: an edit
  to a protected configuration file still asks twice on the Copilot harness.
  No failure case removes the guards. This is the smallest safe change.
- **(C) Hybrid:** lifecycle hooks stand down. Claude-settings guards run,
  but `run-hook.sh` throws away only their "ask" answers. One question, and
  denies stay in both copies. Cost: `run-hook.sh` must capture guard output
  and keep the exit code, plus new tests. If the Copilot copy stops running,
  only the approval questions for configuration edits are lost.

## Checked and found sound

- The Local harness (Copilot extension 0.74.0, read in `dist/extension.js`)
  reads a pre-tool decision only from `hookSpecificOutput`, ignores a whole
  result only when a top-level `hookEventName` names a different event,
  keeps extra top-level keys without using them, and reads nested
  `SubagentStart` context.
- `pretool-bash-guard.sh:27` and `antigravity-pretool.py:115` read the
  nested object. Antigravity calls the guard scripts directly and never goes
  through `run-hook.sh`.
- The read-tool change is as narrow as claimed: the Claude and Codex
  matchers are `Edit|Write` (`generate_targets.py:1138`, `:1229`), so `Read`
  reaches the guard only through `.github/hooks`. A `Read` on
  `.claude/agents/coder.md` asks today (run).
- The shell-helper change is as narrow as claimed: the helper tools carry
  only `shellId` and `delay`, and `write_bash` stays on the shell path.
- The stand-down signal is absent from Claude Code, from SDK shell commands,
  and from the Local harness. If it disappears in a later runtime, the hooks
  run twice, which fails safe.
- Mixed old and new copies never stand down wrongly: condition 5 needs
  `git-protection.sh github-copilot`, which only the new hook file contains.
- Phase B must come before Phase C, and D before E.
- The plan files pass `validate_plan_frontmatter.py`; all named scripts and
  doc sections exist; `verify.py phase` runs the full test suite.
- Three sessions plus discovery fit under the 480-second cap once MCP is
  removed.
