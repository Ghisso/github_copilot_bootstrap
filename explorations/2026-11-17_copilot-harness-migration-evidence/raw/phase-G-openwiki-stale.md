# Phase G, step 3: OpenWiki pages, statements that are now false or incomplete

Date: 2026-11-18. Author: the `coder`. Nothing under `openwiki/` was edited. For each page: the line, the stale or missing
statement, and the source fact with its file and line, so the orchestrator can use the list in the refresh jobs. "Claim" ids are
from `openwiki/.claims/**` where a claim states the text; take fresh line ranges from a search run in the same step as each
`openwiki_submit_page`, as the skill says. Source line numbers are of the tree after my four edits (none of them touches code).

Counts by page: `architecture/hooks-and-guardrails.md` 13; `architecture/agents-and-skills.md` 1;
`architecture/source-generated-consumer-layout.md` 3; `operations/deterministic-verification.md` 3;
`operations/install-ownership-and-runtime-checks.md` 2; `operations/git-backed-ai-state-sync.md` 1;
`operations/sidecar-overlay.md` 2; `quickstart.md` 2; `INSTRUCTIONS.md` 1; the two index pages 1 note.
Total 28 statements on 9 pages (items 1 to 28), plus the index note (item 29). No stale statement:
`operations/context-mode-dispatcher.md`, `workflows/lifecycle-and-task-lanes.md`, `workflows/index.md`, `index.md`; the two index
pages carry only the derived-description note.

## Facts used below (source of truth)

- F-a. The Copilot hook file `shared/hooks/hooks.json` has five events and 14 entries: `SessionStart` (lines 4-40: `state-sync.sh pull`,
  `session-log.sh github-copilot`, `session-start-state.sh github-copilot`, `reporting-reminder.sh session github-copilot`),
  `PreToolUse` (42-88: the five guards), `PostToolUse` (89-99: `record-branch-state.sh`), `Stop` (100-128: `session-log.sh`,
  `stop-session-log-check.sh`, `state-sync.sh push`), `SubagentStart` (129-139: `subagent-context.sh github-copilot`).
- F-b. The Copilot harness loads both `.github/hooks/hooks.json` and `.claude/settings.json`. `README.md:1646-1726` ("Hooks on the
  Copilot harness"); `docs/target-mapping.md:99`; probe checks `hooks-sources`, `single-session-log`, `state-sync-once`
  (`docs/runtime-checks.md:611-635`).
- F-c. `shared/hooks/scripts/run-hook.sh:54-69` (`stands_down`) and `:71-74`: for `state-sync.sh`, `session-log.sh`,
  `session-start-state.sh`, `claude-stop.sh`, `reporting-reminder.sh` only, when `BOOTSTRAP_HOOK_SOURCE=claude-settings`,
  `COPILOT_CLI=1`, `COPILOT_HOOK_DEPTH` non-empty, `COPILOT_HOOK_DIR` empty, `CLAUDECODE` empty, and `.github/hooks/hooks.json` is a
  regular file (not a link) with no `disableAllHooks` that contains `session-log.sh github-copilot` and `state-sync.sh push`, the
  launcher reads and discards stdin, prints nothing, exits 0 and never starts the script. The marker is set only by the generated Claude
  settings (`scripts/generate_targets.py:1089-1115`), and `scripts/validate_targets.py:1607-1642` checks that no other hook file
  carries it. Guards never stand down (condition matrix: 247 rows, 0 guard rows).
- F-d. `shared/hooks/scripts/_lib-frontmatter.sh:16-20` (`json_escape`: control characters 1-31 become spaces) and `:44-57`, `:121-132`
  (`pretool_decision`, `additional_context`: for `TARGET_ID=github-copilot` the answer also carries top-level `permissionDecision`,
  `permissionDecisionReason`, `additionalContext`, and no top-level `hookEventName`); `protect-files.py:3639-3657` (`print_decision`)
  does the same.
- F-e. `shared/hooks/scripts/protect-files.py`: `TERMINAL_TOOLS` line 58; `SHELL_HELPER_TOOLS` (`read_bash`, `list_bash`, `stop_bash`)
  line 64, judged like a native tool when there is no `command` (3739-3740); `UNVERIFIED_CODE_TOOLS` line 71, denied by name on
  `github-copilot` only (3706-3712); `READ_ONLY_TOOLS` lines 76-89 now holds `read` (the hook name of `view`), `grep`, `rg`, `glob`;
  `PATH_KEYS` lines 90-93 holds `paths`, so an explicit secret-shaped entry in `paths` of a search tool is denied; patch text from
  `apply_patch` (a string `tool_input` that starts with the patch begin marker) is read at 3720-3735 through `add_patch_paths`
  (927-950), with headers matched in any letter case and with any blanks (`PATCH_HEADER`, 109-112).
- F-f. `shared/hooks/scripts/reporting-reminder.sh:26-52`: modes `prompt` and `late-report` for `claude-code` and `openai-codex`, mode
  `session` for `github-copilot` only; `session` prints the 183-byte reminder at `SessionStart`.
- F-g. `shared/hooks/scripts/subagent-context.sh` (113 lines): at `SubagentStart` gives each sub-agent the text of
  `.github/copilot-instructions.md` (at most 2,048 bytes, regular file, no link on the way) and one fixed line; never denies; builds
  the answer with `python3 -I` and `json.dumps` (line 113).
- F-h. `shared/hooks/scripts/session-log.sh:36-45` writes `target=<TARGET_ID>`, so a Copilot-harness session logs `target=github-copilot`
  once (probe check `single-session-log`).
- F-i. `shared/scripts/verify.py:66-78`: `COMMAND_TIMEOUT_SECONDS = 900` (line 74) and `VERIFICATION_ITEM_TIMEOUT_SECONDS = 1020`
  (line 78). The repository's suite: 5,927 tests, 424.6 s (Phase F log, full `verify.py phase`).
- F-j. `scripts/check_copilot_runtime.py:1-17` (module docstring), `:41-42` (session cap 150 s, run cap 480 s), `:1430-1455` (flags
  `--require`, `--vscode-bin`, `--keep`, `--discover`): an opt-in probe that starts the real Copilot runtime from the newest
  `~/.vscode-server/bin/*` with VS Code's `node`, a private data folder, no login, a scripted model on 127.0.0.1, a fresh full install in a
  temporary folder without `.mcp.json`; three sessions; 48 result lines; runtime `1.0.108-0` (SDK `1.0.30-preview.0`, VS Code 1.146.0)
  on 2026-11-18 (`docs/runtime-checks.md:565-640, 288-298`). Nothing in tests, hooks, or `verify.py` calls it. Tests:
  `tests/test_check_copilot_runtime.py` (117 test functions).
- F-k. New tests: `tests/test_protect_files_copilot_harness.py` (24), `tests/test_check_copilot_runtime.py` (117), and in
  `tests/test_hook_gates.py` the stand-down cases (line 5212 on), the sub-agent hook cases (5454 on), and the top-level answer cases
  (4370, 4404).
- F-l. `scripts/validate_targets.py:759-772` (2 KiB check of `.github/copilot-instructions.md`), `:1675-1680` (`COPILOT_EXPECTED_EVENTS`
  now includes `SubagentStart`), `:1895` (the `SubagentStart` entry must run `subagent-context.sh github-copilot`).

## `architecture/hooks-and-guardrails.md` (13)

1. L77, table row "GitHub Copilot | `.github/hooks/hooks.json` ... `run-hook.sh <script> [args]`". Incomplete. On the Copilot harness the
   runtime also loads `.claude/settings.json` (F-b); one sentence under the table, with a pointer to the README section.
2. L82, "`run-hook.sh` ... then runs `.claude/hooks/scripts/<name>` under `/bin/bash`." Incomplete, and false as a rule: the
   launcher does not run the script when it stands down (F-c). Claim `claim_577abfccd7214b578dafc049c57d3ba8` ("run-hook.sh is the shared
   dispatcher ... only warns and exits 0 when the named script file is missing") omits it; its evidence is the whole file, so the
   recheck covers `run-hook.sh:54-74`. Add the five scripts, the marker, the seven conditions, "guards never".
3. L87-104, "What runs on each event". Lists Claude Code and Codex events and, at L104, only the Copilot `PreToolUse` list. Missing: the
   Copilot file's `SessionStart` (four entries, the fourth the session-start reminder), `PostToolUse`, `Stop`, and `SubagentStart`
   (F-a). Claim `claim_772a4fb0d28f46228762876e9942510d` lists three `SessionStart` entries and no `SubagentStart`. The page must name
   `SubagentStart` (the Phase G plan's verification line greps for it) and the phrase "Copilot harness" (same line).
4. L91, "SessionStart ... `state-sync.sh pull`, `session-log.sh`, `session-start-state.sh`" stays true for Claude Code and Codex; add that
   on the Copilot harness the Claude-settings copy of each of these stands down (F-c).
5. L96-100, "Both hosts also run `state-sync.sh push` and `reporting-reminder.sh prompt` on `UserPromptSubmit` ... Claude Code runs
   `state-sync.sh push` on `SessionEnd` and a local `state-sync.sh checkpoint` on `StopFailure`." True for Claude Code. Add: on the
   Copilot harness these Claude-settings hooks stand down; the Copilot file still pushes at every `Stop` (F-c; `README.md:1714-1718`).
6. L106, "`is_bash_tool_payload` ... accepts ... `run_in_terminal` and `send_to_terminal`". Incomplete: on the Copilot harness the shell
   tool is `bash`, which a hook sees as `Bash` (`docs/target-mapping.md:210-218`); `read_bash`, `list_bash`, and `stop_bash` match
   `*bash*` but the file guard judges them like a native tool when they carry no `command` (F-e). Claim
   `claim_2089bfda47d34728bd027582974b2a75`.
7. L124, "Decisions are JSON `hookSpecificOutput` objects with `permissionDecision` set to `deny` or `ask` plus a reason." Incomplete: for
   `github-copilot` each decision is also printed at the top level, and reasons lose control characters (F-d).
8. L139, "The classifier understands edit payloads, patch blocks, ...". Incomplete: it also reads patch text sent as a string by
   `apply_patch`, matches the four header forms in any letter case and with extra blanks, and fails closed on an unterminated patch,
   on text that is neither JSON nor patch text, and on patch text sent to a shell or read tool (F-e).
9. L157, "Native read-only tools (such as `read_file`, `grep_search`, and the Copilot SDK harness's `view`) read hook and agent configs
   without a decision, but still get the secret-file deny." Incomplete and one wrong name: "Copilot SDK harness" is now "Copilot
   harness"; the hook name of `view` is `Read`, which the guard now treats as a read tool (L1); an explicit secret-shaped entry in the
   `paths` list of `grep`, `rg`, or `glob` is denied (T1); the shell helper tools are not stopped (L2); `run_dynamic_workflow` and
   `dynamic_workflows_manage` are denied by name on `github-copilot` only (T4) (F-e; `docs/target-mapping.md:240-258`). Claim
   `claim_b5686a991b86400d9e3f4bb7d15b4c83`.
10. L165, "`reporting-reminder.sh` (PostToolUse on Bash; Codex prompt submit). Advisory only." Incomplete: three modes (F-f); prompt
    submit applies to Claude Code too (the page says so at L96); `session` at `SessionStart` for Copilot. Claim
    `claim_4004699af35f4919a91b9058fef65c9b`. Add a new bullet for `subagent-context.sh` (F-g): a context hook, not a guard.
11. L169, "`record-branch-state.sh` runs after every Bash call (including Copilot's `run_in_terminal` and `send_to_terminal`)". Minor:
    add the Copilot harness's `bash`.
12. L171, "`session-log.sh` appends session events ... translating between Claude Code's snake_case and Codex's camelCase payload keys."
    Incomplete: it also writes `target=github-copilot` for the Copilot file; on the Copilot harness one session logs once (F-h). L183-185
    ("Logs") can carry the same sentence.
13. L187-193, "Representative tests". Add `tests/test_protect_files_copilot_harness.py`, `tests/test_check_copilot_runtime.py`, the stand-down
    and sub-agent hook cases in `tests/test_hook_gates.py` (F-k), and one sentence on the opt-in probe (F-j). Frontmatter `sources:` has
    no `subagent-context.sh` or `scripts/check_copilot_runtime.py`; `generated.at` is 2026-11-12.

## `architecture/agents-and-skills.md` (1)

14. L170, GitHub Copilot adapter bullet (claim `claim_2bb75e382f0b4e3caa089e45721d9c2d`, evidence `generate_targets.py#L1565-L1616`).
    Not wrong, but silent about what a sub-agent gets on the Copilot harness: only the wrapper plus, since Phase E, the text of
    `.github/copilot-instructions.md` and one fixed line from the `SubagentStart` hook (F-g); the Copilot harness ignores the wrapper's
    `agents:` field and finds the copies in `.claude/agents/`, a wrapper winning by name (`README.md:1519-1610`). The
    Phase G plan names this page for "sub-agent context". L242 ("Copilot reads the same folders and lists one copy per name") stays
    true (`docs/sidecar-provider-contract.md`, Copilot harness discovery check). Claim `claim_88cd74b1...` cites
    `docs/native-client-acceptance.md#L8-L12`: my edit added six lines at line 5, so that text is now at L14-L18; recheck it.

## `architecture/source-generated-consumer-layout.md` (3)

15. L100, "`render_claude` writes `CLAUDE.md`, `.mcp.json`, and `.claude/settings.json` with the hook wiring." Incomplete: every hook
    command carries the prefix `BOOTSTRAP_HOOK_SOURCE=claude-settings`, which no other hook file may carry
    (`generate_targets.py:1089-1115`; `validate_targets.py:1607-1642`).
16. L146, "Runtime loading by a real client is probed separately by `scripts/check_native_clients.py`; the structural validator does not
    claim it." Incomplete: `check_native_clients.py` covers Claude Code and Codex only (`docs/native-client-acceptance.md:5-12`); the
    Copilot harness has `scripts/check_copilot_runtime.py` (F-j). The validator also pins the Copilot hook file's five events, the
    `SubagentStart` entry, and the 2 KiB size of `.github/copilot-instructions.md` (F-l).
17. L150, "Representative tests". `tests/test_validate_targets.py` also covers the marker check, the event set, and the 2 KiB check
    (F-l). Optional.

## `operations/deterministic-verification.md` (3)

18. L79, "runs under `COMMAND_TIMEOUT_SECONDS = 480`" and "timed out after 480 seconds". False: 900 (F-i). Claim
    `claim_b4af1677422c46bfb7717bf156924598` (evidence `verify.py#L67-L76`, `#L162-L171`, `#L2968-L2972`: the first range now holds the
    comment and the 900 constant at lines 66-78).
19. L79, "The budget stays below the 600-second per-item budget ... this repository's own suite takes about 190 seconds." False: the item
    budget is 1,020 seconds; the suite takes about 410 to 425 seconds (F-i).
20. L103, "Each item gets `VERIFICATION_ITEM_TIMEOUT_SECONDS = 600`." False: 1,020 (F-i). Claim
    `claim_eaafd4e303a546289484822b57ea8cd1` ("with a 600-second per-item timeout"). `shared/policies/workflow.instructions.md:147` already
    says 1020.

## `operations/install-ownership-and-runtime-checks.md` (2)

21. L228-240, "What `check_runtime.py` reports". Missing: the other opt-in runtime check. The Phase G plan requires the page to contain
    `check_copilot_runtime.py` (its verification line greps for it). Add a short section after "What `check_runtime.py` reports": what the
    probe starts, that it is opt-in and offline, three sessions and 48 lines, the runtime version it prints, the flags `--require` and
    `--discover`, and that it does not see VS Code's own layer (F-j; `docs/runtime-checks.md:565-640`). The page's frontmatter
    `description` (and the line in `operations/index.md`) names no probe; update both.
22. L242-246, "Representative tests". Add `tests/test_check_copilot_runtime.py` (F-j, F-k).

## `operations/git-backed-ai-state-sync.md` (1)

23. L140-143, "Where sync runs" (claim `claim_26eabe3a099244c99f0980ef3c92c841`): "SessionStart on Claude Code, Codex, and GitHub Copilot ...
    UserPromptSubmit on Claude Code and Codex: `state-sync.sh push` ... Session end: ... Claude Code runs `push` on `SessionEnd` and a
    local `checkpoint` on `StopFailure`." Incomplete: on the Copilot harness the Claude-settings copies of `state-sync.sh` stand down
    (pull at `SessionStart`, push at `UserPromptSubmit` and `SessionEnd`, checkpoint at `StopFailure`), so the pull and the `Stop` push
    run once, from the Copilot file (F-c; `README.md:1714-1718`). Probe check `state-sync-once` (`docs/runtime-checks.md:620-627`).

## `operations/sidecar-overlay.md` (2)

24. L68, "No `.github/agents` or `.codex/agents` file ships in either profile, because neither Copilot nor Codex has a config-free way to
    discover a custom agent from an ignored file". The first half is still true. Incomplete: on 2026-11-18 offline discovery on the
    Copilot harness runtime `1.0.108-0` listed the five `.claude/agents/` files of the `workflow` profile as agents; VS Code was not
    checked and no support is claimed (`docs/sidecar-provider-contract.md`, "Copilot harness discovery check (2026-11-18)", lines
    1284-1364; `README.md:653-661`). L205 (the rule about agents in more than one folder) is unaffected.
25. L92-97, the client table: the Copilot Agent Host row says the bridge is the `.github/instructions/` file (the 2026-09-25 native run,
    VS Code 1.139.0). Incomplete: the 2026-11-18 offline discovery listed both `.github/instructions/` and `.claude/rules/` files as
    instruction sources and the `.agents/skills/` copy of every skill once; it shows listing only, not what reaches the model, and the two
    results differ in VS Code version and in kind (same section of the contract). Claim `claim_1306614210644b4ca40120b3839ad925` is a
    dated fact and stays true.

## `quickstart.md` (2)

26. L75 (claim `claim_b27346e0405e4fcb8fbc73cb99d3adab`), the row "check which guard or capability each client ... actually gets": it
    names two parity sections of `docs/target-mapping.md`. Incomplete: add the sections "Copilot harness tools and guard handling" (line
    192) and "What changed in the guard for the Copilot harness" (line 240), and that the two parity tables now have a Local harness and a
    Copilot harness column for Copilot.
27. L60-77 (routing table) and L82-88 (commands). Missing: a route for "check what the Copilot harness does with the hooks, or run the
    real-runtime probe" -> `operations/install-ownership-and-runtime-checks.md` (after item 21) and `architecture/hooks-and-guardrails.md`,
    sources `scripts/check_copilot_runtime.py`, `docs/runtime-checks.md`, `docs/smoke-tests.md` (section "VS Code Copilot harness (manual)").
    The commands block may list `uv run python scripts/check_copilot_runtime.py --require` marked opt-in.

## `openwiki/INSTRUCTIONS.md` (1; human-authored brief, report only)

28. L60-80, "Cover, at minimum" has no item for the Copilot harness (the stand-down, the answer shape, `SubagentStart`, the probe), and
    L52-58 (authority order) lists `README.md` and `docs/architecture.md` but not `docs/target-mapping.md` or `docs/runtime-checks.md`,
    which now hold the recorded Copilot behavior. Suggested bullet: "the Copilot harness adapter: the two hook files, the lifecycle
    stand-down in `run-hook.sh`, the answer shape for `github-copilot`, the `SubagentStart` hook, and the opt-in probe
    `scripts/check_copilot_runtime.py`". Without it, a future refresh has no instruction to keep this section current.

## Index pages (1 note)

29. `architecture/index.md` line 3 (hooks page description) and `operations/index.md` line 5 (install page description) are copies of each
    page's frontmatter `description`. They change only if the page descriptions change (items 3 and 21); update them in the same job.

## Claims whose cited line ranges moved because of my edits (recheck, not rewrite)

- `docs/native-client-acceptance.md`: six lines added at line 5. `agents-and-skills.json` cites `#L8-L12` (claim `claim_88cd74b1...`); the
  paragraph is now at `#L14-L18`.
- `README.md`: ten lines added at line 471. Ranges after 471 moved by 10: `#L683-L708` (sidecar-overlay, `claim_03211f9f`), `#L916-L935`
  (`claim_d97e645a`), `#L1029-L1038` (install-ownership, `claim_1d553cb4`), `#L1296-L1296` (agents-and-skills, `claim_c15d3172`),
  `#L1480-L1488` and `#L1563-L1567` (quickstart, `claim_5a899a6b`). Ranges before 471 (`#L13-L16`, `#L181-L201`) did not move from this
  edit, but Phase F had already inserted text above them (the Quick Install note, lines 73-130), so all README ranges need the usual
  recheck.
- `SECURITY.md`: four lines added at line 20; no claim cites it. `shared/skills/knowledge-refresh/SKILL.md`: three lines added at line 56;
  no claim cites it.
