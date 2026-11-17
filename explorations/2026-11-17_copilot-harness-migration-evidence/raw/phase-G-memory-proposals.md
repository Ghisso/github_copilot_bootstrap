# Phase G, step 3: proposals for `.claude/MEMORY.md`, the project context file, and the active plans

Date: 2026-11-18. Author: the `coder`. Nothing in this file was applied. The orchestrator edits these three surfaces.
Every proposed sentence names its basis. A basis marked "not run" says so. Evidence paths are under
`.claude/explorations/2026-11-17_copilot-harness-migration-evidence/` (written `E/` below).

Counts: `.claude/MEMORY.md` 9 items (M1 to M9). Project context file 9 items (C1 to C9). Active plans 0 stale statements and 2
reminders (P1, P2).

---

## `.claude/MEMORY.md`

### M1. Replace the `[LEARN:tooling]` entry about the 2026-11-17 spike (lines 1704-1723)

Why: Phases B to E patched this entry in place four times. It now reads as "every hook runs twice (since Phase D ... stand
down)" and "sub-agents get no repository instructions (since Phase E ...)": each sentence says the old fact, then the new one.
After this plan the entry should state the current behavior first. Replace the whole entry (from `- [LEARN:tooling] VS Code removes`
to `... no account needed.`) with:

```markdown
- [LEARN:tooling] VS Code removes Copilot's Local harness in February 2027; the
  Copilot harness is the default since 1.143. The bootstrap supports the Copilot
  harness inside VS Code, not Copilot CLI or cloud agents. Behavior on the
  runtime in VS Code 1.146.0 (`1.0.108-0`; spike 2026-11-17, plan
  `copilot-harness-migration` after it): the PascalCase hook file works
  unchanged, and the runtime also loads `.claude/settings.json`. The five
  lifecycle hooks reached through the Claude settings (`state-sync.sh`,
  `session-log.sh`, `session-start-state.sh`, `claude-stop.sh`,
  `reporting-reminder.sh`) stand down there, so they run once (Phase D:
  `run-hook.sh`, marker `BOOTSTRAP_HOOK_SOURCE=claude-settings`); the guards run
  from both files and never stand down. With `chat.useClaudeHooks` on, the Local
  harness still runs every hook twice. For `github-copilot` the guards print the
  decision at the top level and nested (Phase C): the runtime reads the top level
  under both event spellings, a nested-only answer works only under PascalCase
  `PreToolUse`, the Local harness reads the nested copy, and a timeout or
  non-JSON output lets the tool run. `apply_patch` sends its patch text as a
  string `tool_input` (offline only Codex-family models get that tool; the real
  VS Code also gave it to `gpt-6-luna`); Phase B made `protect-files.py` read it,
  where it had crashed. A sub-agent gets only its agent file, plus, since Phase E,
  the text of `.github/copilot-instructions.md` (at most 2,048 bytes) and one
  fixed line from the `SubagentStart` hook `subagent-context.sh`. Read
  `.claude/explorations/2026-11-17_copilot-harness-migration-evidence/REPORT.md`
  before any Copilot change; `scripts/check_copilot_runtime.py --require` runs the
  real runtime offline with a scripted model (no account) and prints 48 lines.
```

Basis, sentence by sentence: the hook file works unchanged and `.claude/settings.json` also loads: E/REPORT.md F2, A3
(real VS Code); the five scripts and the marker: `shared/hooks/scripts/run-hook.sh:54-69`, `scripts/generate_targets.py:1089-1115`;
guards never stand down: the condition matrix, 247 rows, 0 guard rows (`E/raw/phase-D-condition-matrix.txt`); the Local double run:
E/REPORT.md A2 (real VS Code, hook log "Executing 8 hook(s)"); top level under both spellings and nested-only only under PascalCase:
`E/raw/planning-probe-e1-outcomes.txt` (P1) and F4; "a timeout or non-JSON output lets the tool run": F5;
the Local harness reads the nested copy: VS Code Copilot extension 0.74.0 source, `README.md:100-118`; `apply_patch`: F6, A4,
`protect-files.py:3720-3735`; sub-agents: F9, `shared/hooks/scripts/subagent-context.sh`, probe check `subagent-context`;
48 lines: `E/raw/phase-F-require-output.txt` (2026-11-18 07:17).

### M2. Replace the `[LEARN:tooling]` entry "Copilot hooks can be turned off from the repository" (lines 1700-1703)

Why: it is true for the Local harness only. VS Code's documentation says "Local settings such as `chat.useHooks` do not prevent
the Copilot harness from loading a configuration" (E/REPORT.md F1; `README.md:119-122`).
Replacement:

```markdown
- [LEARN:tooling] On the Local harness, hooks can be turned off from the
  repository: `.vscode/settings.json` (`chat.useHooks`, `chat.hookFilesLocations`,
  `chat.useClaudeHooks`). Those Local settings do not stop the Copilot harness
  from loading a hook file (VS Code docs, read 2026-11-17). For the Copilot
  runtime, `disableAllHooks` at the top of a hook file skips that file's hooks;
  a top-level `disableAllHooks` in repository `settings.json` is documented for
  Copilot CLI only (`E/research/github-docs-runtime-contract.md:110`). Protect all
  of these files like other hook configs; the launcher's stand-down also refuses to
  act when the Copilot hook file carries `disableAllHooks`.
```

Basis: F1; `E/research/github-docs-runtime-contract.md:110`; `run-hook.sh:66` (the `disableAllHooks` condition);
`protect-files.py` protects `.vscode/settings.json` and `.github/copilot/settings*.json` (`docs/target-mapping.md:109`).
Whether `disableAllHooks` in `.github/copilot/settings.json` affects the Copilot harness in VS Code: not run.

### M3. Extend the `[LEARN:security]` entry on tool names (lines 1689-1695)

Why: it names only the Local harness's tool names. Append one sentence to the end of the entry:

```markdown
  On the Copilot harness the hook names are PascalCase for built-ins (`Bash`,
  `Read` for `view`, `Glob`, `Edit` for `apply_patch`, `Write` for `create`) and the
  runtime's own names under camelCase events; VS Code's tool set for a model can
  differ from the runtime's own list (`docs/target-mapping.md`, "Copilot harness
  tools and guard handling").
```

Basis: E/REPORT.md A4; `docs/target-mapping.md:192-218`; `protect-files.py:76-90` (`read`, `grep`, `rg`, `glob`).

### M4. Optional: extend the `[LEARN:architecture]` sidecar discovery entry (lines 1326-1334)

Append: "On 2026-11-18 the Copilot harness runtime `1.0.108-0` listed both `.github/instructions/` and `.claude/rules/` as instruction
sources, and the five `.claude/agents/` files of the `workflow` profile as agents (discovery only; no session, no VS Code run;
`docs/sidecar-provider-contract.md`, section "Copilot harness check, 2026-11-18")." Basis: `E/raw/phase-F-sidecar-discover-skills.txt`,
`E/raw/phase-F-sidecar-discover-workflow.txt`. The 2026-09-25 sentences stand as written (dated runs, other VS Code version).

### Draft LEARN entries (M5 to M9)

M5. Shell helper tools (planning probe P3). Category `[LEARN:hooks]`.

```markdown
- [LEARN:hooks] The Copilot runtime's shell helper tools `read_bash`, `list_bash`,
  and `stop_bash` carry `shellId` and `delay`, no `command`. A guard that treats
  every tool whose name ends in `bash` as a shell command stops each of them
  ("Bash payload has no command"), so a background shell starts but is never read
  or stopped. `protect-files.py` now judges them like a native tool unless a
  `command` is present (`SHELL_HELPER_TOOLS`). The runtime's own read of a finished
  shell runs with no pre-tool hook at all, so a check must not demand a hook event
  for every tool run (probe check `helper-tools`). Evidence:
  `E/raw/planning-probe-e3-outcomes.txt`, `E/raw/built-in-tools.txt` (2026-11-17).
```

M6. `COPILOT_CLI` inheritance (planning probe P1). Category `[LEARN:tooling]`.

```markdown
- [LEARN:tooling] The Copilot runtime's shell tool gives every command
  `COPILOT_CLI=1` and `COPILOT_AGENT_SESSION_ID`, but not `COPILOT_HOOK_DEPTH` or
  `COPILOT_PROJECT_DIR`, which only hook processes get (planning probe P1,
  `E/raw/planning-probe-e1-outcomes.txt`). A Claude Code session started from such a
  shell therefore inherits `COPILOT_CLI=1` (inferred from P1; not run). A stand-down
  keyed on `COPILOT_CLI=1` alone would remove that session's hooks. The launcher
  also needs a non-empty `COPILOT_HOOK_DEPTH`, an empty `COPILOT_HOOK_DIR` and
  `CLAUDECODE`, and the marker. A `CLAUDE_CODE_*` variable in a Copilot hook is not
  proof of Claude Code: real Copilot hooks carry `CLAUDE_CODE_DISABLE_PRECOMPACT_SKIP=1`
  (E/REPORT.md A3). The condition matrix has a row for this environment
  (`E/raw/phase-D-condition-matrix.txt`, "Claude Code started from a Copilot shell").
```

M7. VS Code's own tool set per model (A4). Category `[LEARN:tooling]`.

```markdown
- [LEARN:tooling] VS Code can give a model a different tool set than the Copilot
  runtime's `tools.list` for that model. On 2026-11-17 in the real VS Code, Auto
  chose `gpt-6-luna` and VS Code gave it `apply_patch`; the runtime's own list
  gives that model `create` and `edit`. Offline, only Codex-family ids such as
  `gpt-5.2-codex` get `apply_patch`. So a guard maps tools by hook name and input,
  never by model, and the offline probe cannot show what VS Code offers; that part
  stays on the manual checklist (E/REPORT.md A4, `E/raw/tools-by-model.txt`,
  `docs/target-mapping.md`).
```

M8. Why no stand-down on the Local harness (A2). Category `[LEARN:tooling]`.

```markdown
- [LEARN:tooling] The double run on the Local harness (setting `chat.useClaudeHooks`
  on) is not covered by the stand-down, on purpose. Its Claude-settings hooks have
  the environment of a real Claude Code session (no `COPILOT_CLI=1`; E/REPORT.md A2),
  so no environment test separates them from Claude Code. Whether the other hook
  source also runs depends on user settings (`chat.useHooks`,
  `chat.hookFilesLocations`, `chat.useClaudeHooks`) that a hook cannot read, so a
  stand-down there could remove the only copy. The docs say to turn the setting off.
  The Local harness goes away in February 2027.
```

M9. Option B trade-off. Category `[LEARN:architecture]`.

```markdown
- [LEARN:architecture] On the Copilot harness only the five lifecycle hooks reached
  through `.claude/settings.json` stand down (option B of the plan
  `copilot-harness-migration`); the guards run from both files. Cost: one protected
  edit raises two hook questions in the probe (the real VS Code answered the second
  itself once, so the user saw one; E/REPORT.md A6), and a deny comes from either
  file. Gain: a wrong stand-down loses only session-log entries, session-start
  context, AI-state pull and push, and the reminder, never a guard (condition matrix:
  247 rows, 0 guard rows stand down). Lost on purpose: the Claude-settings state push
  at `UserPromptSubmit` and `SessionEnd`, and the checkpoint at `StopFailure`; the
  Copilot file still pushes at every `Stop`, and the `post-commit` hook publishes.
  Rejected: stand down every Claude-settings hook (a failed `.github/hooks` copy would
  leave no guard) and drop the Claude-settings asks (an ask would become an allow).
  The plan's "a deny happens twice" had no run behind it: the recorded runs show one
  deny reason per denied call.
```

Basis for M9: the plan's options table and the Phase D correction; `README.md:1646-1726`; probe check `guards-both-sources`
(`docs/runtime-checks.md:637-645`).

Other entries checked, no change needed: 1449-1460 (`verify.py phase` budget: 900 s and 1,020 s, correct), 1461-1466,
1467-1473 (`tr`), 1474-1479 (environment of a temporary project), 1480-1484 (plan text is not evidence), 1485-1491 (`-I`),
1492-1502 (temp-file leak), 1503-1518 (three documentation lessons), 1519-1524, 1525-1529 (macOS job; `.github/workflows/validate.yml`
agrees, read in this audit), 1530-1536. Lines 15-19 (`[LEARN:domain]`, project context "refreshed 2026-11-17 at `2e8c7bb`") stay
true until the context file is refreshed; if C4 is applied, update the date and commit there.

---

## `.claude/instructions/project-context.instructions.md`

C1. Lines 49-52 (`shared/hooks/`). Old: "lifecycle configuration and shell/Python guardrails, including `context-mode-dispatch.sh` (pins
Context Mode `2.1.8`). Its `git-hooks/` folder holds ...". Add: "`hooks.json` is the GitHub Copilot hook file (five events, including
`SubagentStart`, which runs `subagent-context.sh`); `run-hook.sh` makes five lifecycle hooks reached through the Claude settings stand
down on the Copilot harness." Basis: `shared/hooks/hooks.json`, `run-hook.sh:54-74`.

C2. Lines 105-106 (`scripts/check_native_clients.py`: "optional native-client probes and evidence (Claude Code and Codex only)"). Add
a bullet: "`scripts/check_copilot_runtime.py` with `scripts/copilot_runtime_probe.mjs`: opt-in, offline probe of the real Copilot runtime
inside VS Code (three sessions, 48 result lines on runtime `1.0.108-0`; run by hand, never by tests, hooks, or `verify.py`)."
Basis: `scripts/check_copilot_runtime.py:1-17`, `E/raw/phase-F-require-output.txt`.

C3. Lines 107-108 (`tests/`). Add "the Copilot harness tests (`test_protect_files_copilot_harness.py`, `test_check_copilot_runtime.py`, and
the stand-down and sub-agent hook cases in `test_hook_gates.py`)". Basis: `ls tests/`; `tests/test_hook_gates.py:5212, 5454`.

C4. Lines 224-237 ("Current status and verification"). Stale after this plan: "`uv run pytest tests/ -q` gave 5243 passed ... it was not run
again on 2026-11-17", and "The tracked documents ... were checked against the code on 2026-11-17 ... Nothing needed a change." Phase F
and G changed those documents. Facts for a refresh: full suite on the Phase F tree, 5,927 passed, 1 skipped, 424.6 s (`verify.py phase`
in the Phase F log); this audit changed four files (see `phase-G-audit.md`). The verifier budgets are now 900 s per command and 1,020 s per
required item (`shared/scripts/verify.py:74, 78`).

C5. Lines 245-262 ("Open follow-ups to start from"). Add the Copilot follow-ups the plan recorded: at the Local harness removal
(February 2027) rename the hook events to camelCase, drop the Local-only wrapper fields, decide on `.vscode/mcp.json`, shrink (not
remove) `.github/copilot-instructions.md`; the user's run of the manual checklist (`docs/smoke-tests.md`, "VS Code Copilot harness
(manual)") has not happened; the result of the `macos-latest` job; keep, narrow, or lift the deny of the two workflow tools. Do not
list the two open guard-hook defects here unless the user decides to (instruction of this phase).

C6. Lines 288-295 (what a refresh brings to a consumer not yet refreshed). Add: "a `BOOTSTRAP_HOOK_SOURCE=claude-settings` prefix in
the Claude settings hook commands, a `SubagentStart` entry and a session-start reminder entry in the Copilot hook file, and the guard
changes listed in `README.md:471-480`." Basis: `README.md:471-480`, `docs/target-mapping.md:240-258`.

C7. "Known documentation/status caveats" (lines 336-361). Add: "`README.md`, `docs/`, and the wiki cite the private evidence report
`REPORT.md` by bracket labels such as `[A6]` after a plain description; the report is in `.claude/explorations/` and is not tracked.
Never cite it by a bare label." Basis: the three paragraphs that define the labels (`README.md:124-130`, `docs/target-mapping.md:93`,
`docs/runtime-checks.md:275-280`) and the Phase F LEARN entry.

C8. "Design decisions" (lines 152-154, "Guardrails are shared shell scripts ..."). Add: "On the Copilot harness the guards print the decision
at the top level and nested; the lifecycle hooks reached through the Claude settings stand down and the guards never do (option B)."
Basis: `docs/target-mapping.md:97-99`, `README.md:1646-1726`.

C9. "Pinned versions" (lines 299-312). Add: "Copilot runtime `1.0.108-0` (Copilot SDK `1.0.30-preview.0`, VS Code 1.146.0) is the version the
probe last passed on, 2026-11-18; the probe prints the version on every run and says nothing about another." Basis:
`E/raw/phase-F-require-output.txt`, `docs/runtime-checks.md:288-298`.

---

## Active plans

P1 (reminder, not a stale statement). `.claude/plans/copilot-harness-migration.md:545`: `- [ ] 2026-11-17_phase-G-knowledge-refresh`
becomes `[x]` at the Phase G closeout, with the plan's `status` and `current_phase` per `plan-lifecycle.instructions.md`.

P2 (note). The Phase G plan's step 3 lists `.claude/instructions/` as a surface to sweep. That folder is the generated copy of
`shared/policies/`; this audit swept `shared/policies/` (the canonical source) and found no stale statement, so the copy has none either.
The plan's wording needs no change; the closeout log can say so under `## Stale-claims surfaces checked`.

No statement in the big plan or the Phase G plan is false after this plan. The big plan's "Context" list of real problems and its
risk table (600 seconds "at approval; 1020 seconds since Phase B") are as approved and corrected where the facts changed.
