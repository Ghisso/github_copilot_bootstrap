# Planner report: `copilot-harness-migration` (full plan, draft for the critique round)

The draft is ready: one big plan with seven phases. Both coordinator updates are folded in (Addendum A1 to A3). I ran three bounded offline probes against the real runtime. Two of them changed the plan:

- **New defect (probe P3).** The runtime's shell helper tools `read_bash`, `list_bash`, and `stop_bash` reach the bootstrap's file guard under their own names. The guard treats any name ending in `bash` as a shell command, finds no `command`, and fails closed. So every one of those calls is denied: a background shell can be started but never read or stopped.
- **Rejected design (probe P1).** The runtime's shell tool passes `COPILOT_CLI=1` to every command it runs. A Claude Code session started from a Copilot shell would inherit it. So an early exit keyed only on `COPILOT_CLI=1` would turn off every guard in that Claude Code session. Phase C uses a stricter signal instead.

Inline devil's advocate was skipped, as instructed.

## 1. Goal and constraints

- **Goal:** make Copilot support correct on VS Code's Copilot harness while the Local harness keeps working until February 2027.
- **Constraints:** as in your packet:
  - Phases A to G each get the five review profiles; Phase F also gets `documentation`. Changed paths accumulate from the merge-base, so every phase needs all five.
  - Hook Python stays standard library only and compiles on Python 3.9.
  - No model calls.
  - No hand edits to `dist/`.
  - Byte budgets stay in force.
  - Changes must be safe for older installs.
  - The last phase is the `-knowledge-refresh` phase.

### Planning probes (the orchestrator should keep these; the scratch folder can be cleared)

All three ran on runtime `1.0.108-0`, offline. Outputs are under `/tmp/claude-1000/-home-ghisso-work-github-copilot-bootstrap/815a8a58-3869-4731-9e52-b1353be105f7/scratchpad/copilot-spike/`: folders `e1`, `e2`, `e3` and `hooklogs/e1` to `hooklogs/e3`. The inputs are `sc_e1_planner.json`, `sc_e2_planner.json`, `sc_e3_planner.json`, `replies_e1.json`, and `replies_e2.json`. Please add them to the evidence folder as "Planning probes P1 to P3" before approval.

- **P1 (`e1`, probe hooks only):**
  - Commands run by the shell tool see `COPILOT_CLI=1`, `COPILOT_AGENT_SESSION_ID`, `COPILOT_HOME`, `COPILOT_CLI_ENABLED_FEATURE_FLAGS`, and `COPILOT_RUNTIME_PROCESS_FILE_LOGGING`. They do not see `COPILOT_HOOK_DEPTH` or `COPILOT_PROJECT_DIR`.
  - An answer that carries both shapes (top-level plus nested, same decision) works:
    - `deny` is honored under both `PreToolUse` and `preToolUse`;
    - `ask` produces exactly one question under each;
    - top-level `additionalContext` under PascalCase `SessionStart` and `PostToolUse` reaches the model; the nested copy is ignored.
- **P2 (`e2`):** `SubagentStart` and `subagentStart` hooks with top-level `additionalContext` reach the first user message of both the `coder` and `reviewer` sub-agents. The nested copy is ignored. The hook input carries `agentName` and `agent_type`.
- **P3 (`e3`, the real `.github/hooks/hooks.json` only):** `read_bash`, `list_bash`, and `stop_bash` keep their own names in the hook input. All three are denied with `protect-files classifier error: Bash payload has no command`.

### Other evidence I relied on

- **Source, Local harness:** VS Code's Copilot extension 0.74.0 (`ChatHookService.executePreToolUseHook`) reads only `hookSpecificOutput` for its decision. It drops a whole result only when a top-level `hookEventName` names a different event. The answer with both shapes has no top-level `hookEventName`.
- **Environment leak:** this Claude Code session was started by VS Code's extension host. Its environment carries `COPILOT_CLI_ENABLED_FEATURE_FLAGS` and `COPILOT_OTEL_FILE_EXPORTER_PATH`, leaked from the Copilot extension, and no `COPILOT_CLI` or `COPILOT_HOOK_DEPTH`.
- **Not run during planning:** a run that would show a `Read` of an agent file asking. The session's auto-mode safety classifier refused my command. My claim that it asks today rests on reading the code, and Phase D's first test checks it.

## 2. Phase breakdown

| Phase | Goal |
| --- | --- |
| A `copilot-runtime-probe` | Opt-in offline check of the real runtime inside VS Code; baseline checks; becomes required verification for every later phase |
| B `copilot-hook-answers` | For `github-copilot` only, guards print the decision at the top level and nested; other clients' output byte-identical |
| C `single-hook-run` | Hooks reached through `.claude/settings.json` exit early (stand down) on the Copilot harness only; never on Claude Code or Local |
| D `copilot-tool-inputs` | `protect-files.py`: patch text, shell helpers, `read` alias, search tools on secret-shaped paths (your answer decides this item) |
| E `subagent-context` | `SubagentStart` hook gives sub-agents `.github/copilot-instructions.md`; reporting reminder at session start; agent-file (wrapper) fields kept |
| F `copilot-docs` | Rewrite Copilot claims, manual VS Code checklist (with the A1 precondition), sidecar recorded check, follow-ups |
| G `knowledge-refresh` | OpenWiki refresh plus the final documentation, memory, and LEARN audit |

## 3. Step table (summary; full steps are in the files)

| Phase | Owner | Main files | Required skills | Review profiles | Verification |
| --- | --- | --- | --- | --- | --- |
| A | coder, then reviewer | `scripts/check_copilot_runtime.py`, `scripts/copilot_runtime_probe.mjs`, `tests/test_check_copilot_runtime.py`, `docs/runtime-checks.md` | ponytail (full), integration-gate-spike, testing-patterns, code-style, documentation | code, architecture, security, tests, ponytail, documentation | new pytest file, probe `--require`, validate_targets, check_runtime, plan validator, `verify.py phase` |
| B | coder, then reviewer | `shared/hooks/scripts/_lib-frontmatter.sh`, `protect-files.py`, three scripts that need `TARGET_ID`, `shared/hooks/hooks.json`, `scripts/validate_targets.py`, probe, `tests/test_hook_gates.py`, `docs/target-mapping.md` | same, minus code-style for the bash steps | same | targeted pytest, probe, generate, validate_targets, check_runtime, plan validator, `verify.py phase` |
| C | coder, then reviewer | `shared/hooks/scripts/run-hook.sh`, `scripts/generate_targets.py` (`_claude_hook_cmd`), `scripts/validate_targets.py`, probe, tests, `README.md`, `docs/target-mapping.md` | same | same | same, plus a check that the marker appears in the generated settings |
| D | coder, then reviewer | `shared/hooks/scripts/protect-files.py`, tests (decision battery), probe, docs | same | same | same |
| E | coder, then reviewer | new `shared/hooks/scripts/subagent-context.sh`, `reporting-reminder.sh`, `shared/hooks/hooks.json`, `scripts/validate_targets.py`, probe, tests, docs | same | same | same |
| F | coder (documenter role), then reviewer | `README.md`, `docs/*.md` (six files) | documentation, ponytail | five plus documentation | stale-text and new-text checks, probe `--discover`, `verify.py phase` |
| G | orchestrator plus coder, then reviewer | `openwiki/`, `.claude/MEMORY.md` audit | knowledge-refresh, documentation | five plus documentation | OpenWiki checks, `verify.py phase` |

## 4. Risks, and the evidence or remaining limit for each decisive assumption

- **DA1: VS Code runs repository hooks like the SDK run does.**
  - Evidence: A3. In the real VS Code there was trust, a double session log, and the same hook environment.
  - Limit: no tool call has been made in VS Code yet (gate check a).
- **DA2: the answer with both shapes works everywhere.**
  - Copilot harness: shown by P1.
  - Local harness: safe by reading its code (0.74.0); not run in VS Code.
- **DA3: `COPILOT_HOOK_DEPTH` is set only for processes the runtime starts as hooks.**
  - Evidence: P1, the F2 logs, A3 (VS Code file-source hook environment), and this session's environment.
  - Limit: the Claude-settings source in VS Code is not logged yet (gate check c).
  - Fallback: `COPILOT_PROJECT_DIR`, which is also hook-only in P1.
- **DA4: the Copilot harness always loads `.github/hooks/*.json` in a trusted folder.**
  - Evidence: Docs ("Local settings ... do not prevent the Copilot harness from loading"), F2, F15.
- **DA5: sub-agent context reaches custom agents.** Evidence: P2. Not yet seen in VS Code.
- **DA6: the shell helper tools never carry a command.**
  - Evidence: P3 and the runtime's tool list.
  - VS Code's own `write_bash` carries a `command` (from reading VS Code's code), so it stays a shell tool.
- **DA7: `Read` of a hook or agent file asks today.** Evidence: the code only (`READ_ONLY_TOOLS` has no `read`). Phase D's first test confirms it.

Main risks:

- **VS Code differs from the SDK run.** The gate checks catch it before the branch exists.
- **Local double run with `chat.useClaudeHooks: true`.** Phase C cannot safely remove it:
  - Local's hook sources are chosen by user settings, so a hook cannot know that the other source runs.
  - Its environment equals a real Claude Code session's.
  - So the plan documents the effect and recommends turning the setting off.
- **The probe breaks when VS Code updates.** It picks the newest server folder. A FAIL is a real signal and is handled like any failed check.
- **Probe running time.** The plan caps it at 480 seconds against the 600-second limit per verification item.

## 5. Done criteria

- All seven phases are complete.
- The probe passes every check on the newest VS Code server runtime.
- Claude Code, Codex, and Antigravity hook output is byte-identical to before. Tests pin this.
- Local behavior is unchanged, except for the context it newly receives. That change is documented.
- Every planned change to a guard decision is in the decision-change table in the big plan. The battery and the differential run show no other change.
- Docs state exactly what was run and on which runtime version, and call VS Code hooks "in preview".
- Follow-ups are recorded.
- The knowledge refresh is done and the final audit is logged.

## 6. Devil's Advocate Report

Skipped, as instructed. The orchestrator's critique agent will send change items.

## Questions for the user (genuine preferences only)

1. **Search tools on secret-shaped files.** Should `grep`, `rg`, and `glob` be denied when you name a secret-shaped file, such as `.env`, as their path? This would match the read tool.
   - I recommend **yes**, for paths you name explicitly.
   - A search over a whole folder, or with a filename pattern such as `.env*`, would still not be judged. That is the same as shell reads like `cat .env`, which stay allowed by your 2026-10-21 decision.
   - If you say no, Phase D step 5 and its tests are removed before the branch is created.
2. **`chat.useClaudeHooks` on this computer.** With it on, the Local harness runs every hook twice: two approval questions, and two session entries per chat.
   - The plan documents this and recommends turning it off for this bootstrap.
   - It does not change the setting, which lives in your user settings.
   - Do you want to keep it on while you run the three VS Code checks? Either way the checks still work, but in Local you will see doubles.

Two things in the plan need your explicit approval, though I did not phrase them as questions: the two allow-more changes in the decision-change table. Reading a hook or agent file with the read tool no longer asks, and the shell helper tools are no longer denied. Both reasons are written in the big plan.

## File paths for the orchestrator

Save each block verbatim. Then run `uv run python scripts/validate_plan_frontmatter.py` on these eight files:

- `/home/ghisso/work/github_copilot_bootstrap/.claude/plans/copilot-harness-migration.md`
- `/home/ghisso/work/github_copilot_bootstrap/.claude/plans/2026-11-17_phase-A-copilot-runtime-probe.md`
- `/home/ghisso/work/github_copilot_bootstrap/.claude/plans/2026-11-17_phase-B-copilot-hook-answers.md`
- `/home/ghisso/work/github_copilot_bootstrap/.claude/plans/2026-11-17_phase-C-single-hook-run.md`
- `/home/ghisso/work/github_copilot_bootstrap/.claude/plans/2026-11-17_phase-D-copilot-tool-inputs.md`
- `/home/ghisso/work/github_copilot_bootstrap/.claude/plans/2026-11-17_phase-E-subagent-context.md`
- `/home/ghisso/work/github_copilot_bootstrap/.claude/plans/2026-11-17_phase-F-copilot-docs.md`
- `/home/ghisso/work/github_copilot_bootstrap/.claude/plans/2026-11-17_phase-G-knowledge-refresh.md`

I could not run the plan validator myself: I have no write tool, and the shell file guard refuses heredocs that name protected paths. I checked the small plans by hand against the L1 to L4 rules and the hedge patterns: none of the trigger words appear in their prose.

