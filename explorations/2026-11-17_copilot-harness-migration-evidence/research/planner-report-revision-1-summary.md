# Planner report: revision 1 of `copilot-harness-migration`

All 15 critique items and the six "Not blocking" notes are applied. On three points I chose a different fix than the critique, with evidence: item 1 (how patch headers are matched), item 2 (now designed as option B), and item 14 (one half). The A4 evidence is folded in.

The phases are re-ordered and re-lettered. The new order is: probe, tool inputs, answer format, lifecycle stand-down, sub-agent context, docs, knowledge refresh.

One new bounded probe (P4, discovery only) shows that on runtime `1.0.108-0` a session started two folders below the repository root still loads both hook sources. Its outputs are `disc-g-both.json` and `disc-deeper.json` in `/tmp/claude-1000/-home-ghisso-work-github-copilot-bootstrap/815a8a58-3869-4731-9e52-b1353be105f7/scratchpad/copilot-spike/`. Please copy them into the evidence folder together with P1 to P3.

## 1. Change log

### Critique items

| Item | Where applied | Note |
| --- | --- | --- |
| 1 HIGH, indented patch header | Phase B step 3; big plan decision rows L3 and T2; Phase B tests; probe check `patch-indented-hook-ask` | Applied with one change. Header lines are matched case-insensitively, with any leading or inner blanks, so indented and lowercase headers now give a target. This only adds targets, so it only tightens, for the shell and object inputs too. I did **not** fail closed on every unknown `*** ` line. A context line of an update hunk is the file's own text after one space, so a Markdown line such as ` *** bold ***` would deny an ordinary edit. An unknown header shape is still covered: it gives no target, so the decision rests on the other targets, and the runtime itself rejects a malformed header. The test rows include an indented header, a lowercase header, and a header with extra blanks. |
| 2 HIGH, stand-down trusts the file | Big plan "How much stands down" (options A, B, C); Phase D | Designed as option B, as you asked. Only the lifecycle hooks stand down. Conditions added: `COPILOT_HOOK_DIR` empty, and no `disableAllHooks` in the Copilot file. The subfolder case (b) is now evidence: P4 (both sources load from a subfolder on `1.0.108-0`), a Phase A probe check `hooks-subfolder`, and an optional item in gate check (c). Case (c), a malformed item dropped by the runtime, is in the risk table. Under option B, a wrong stand-down loses only logging, session-start context, AI-state sync, and the reminder; the guards keep running. |
| 3 MEDIUM, "offline" | Phase A step 2 (remove `.mcp.json` from the temporary project), new check `mcp-none` | |
| 4 MEDIUM, VS Code shell environment | Big plan gate check (c) | Runs `env \| grep -E '^(COPILOT\|CLAUDE)'` through the VS Code shell tool; `COPILOT_HOOK_DEPTH` must be absent. Phase D depends on it. |
| 5 MEDIUM, tools the guards do not map | Phase A prints a tool inventory per session; Phase B step 6 gives a decision per tool | The A4 names are added: `AskUserQuestion`/`ask_user`, `skill`, `tool_search_tool`. |
| 6 LOW, camelCase session | Phase C step 6 (checks for commit, branch, PR, and agent wrapper); big plan follow-up worded as "Phase C removes the output blocker" | |
| 7 LOW, budget placement | Phase E step 4 (a separate byte check, not in `ROOT_GUIDANCE_BUDGETS`) | |
| 8 LOW, wrong expected value | Phase B step 1 (`read_bash` with `command: "rm -f .env"`, deny) | |
| 9 LOW, differential comparison | Phase B step 9 (compare the parsed `permissionDecision` and the exit code) | Tool inputs now come before the answer-format change anyway. |
| 10 LOW, checks that pass today | Phase F verification (assigned sentences and headings no earlier phase writes; checked with `grep -c` today: 0) | |
| 11 LOW, folder command | Big plan gate precondition; Phase F step 2 | Full `sudo install -d -m 700 -o "$(id -u)" -g "$(id -g)" /run/user/$(id -u)`, repeated after every WSL restart. |
| 12 LOW, "newest" undefined | Phase A step 2 and step 4 | Newest by folder modification time. Only a VS Code server folder is known to ship `node`. |
| 13 LOW, "no" answer scope | Big plan gate; Phase B Scope | The full list of parts to remove. |
| 14 LOW, over-building | `--format` dropped everywhere | Applied in part. Phase F's probe run moved to Optional Verification. Phase F step 1 still runs `--discover` as an evidence step, not as a required check. The integration-gate-spike rule no longer applies there: Phases A to E have observed that path. |
| 15 LOW, `TARGET_ID` inheritance | Phase C step 4 | `openwiki-guard.sh` and every `reporting-reminder.sh` mode assign `TARGET_ID`; a test sets an exported `TARGET_ID=github-copilot`. |
| Not blocking: `json_escape` | Phase C step 2; decision row T3 | Control characters become spaces before escaping, so a reason can no longer produce invalid JSON, which lets the tool run on Copilot. |
| Not blocking: e3 step 6 | Phase A `evaluate`: a tool run with no pre-tool hook event is not judged | |
| Not blocking: lost state push | Phase D docs step | |
| Not blocking: context text now reaches the Copilot model | Phase C docs step | |
| Not blocking: `SubagentStart` | Phase E and F docs say "observed", not "documented" | |
| Not blocking: F10 policies offered twice | Big plan recorded follow-ups | |

### A4 points

| Point | Where applied |
| --- | --- |
| Gate check (a) passed | Big plan gate table and DA1 |
| Patch-text crash is urgent | Phases re-ordered: tool inputs are now Phase B; answer format C, before stand-down D; tool inputs before sub-agent E. The probe uses `gpt-5.2-codex` offline. The fact that VS Code can give a model a different tool set (`gpt-6-luna`) is stated in the big plan Context, Phase A docs (checked in its verification), and Phase F. |
| Tool names seen in VS Code | Phase B step 6 inventory; Phase B docs (and that reads are approved by VS Code's own `host_policy`) |
| Gate check (b), partly seen | Gate table records the hook-kind request with `hookMessage`; the number of questions and "Allow all" stay open |
| Gate check (c), still open | Gate table; the logger for the Claude-settings hooks is noted |

### Also new from probe P4

- Discovery entries carry `enabled` and `disableKey` fields, so the runtime has a per-hook disable switch.
- How that switch is set is not documented, and the key is a hash, so a generated repository file cannot use it.
- It is recorded as a follow-up, not used.

## 2. Plan files

The first-draft files whose slugs changed must be **deleted**:

- `/home/ghisso/work/github_copilot_bootstrap/.claude/plans/2026-11-17_phase-B-copilot-hook-answers.md`
- `/home/ghisso/work/github_copilot_bootstrap/.claude/plans/2026-11-17_phase-C-single-hook-run.md`
- `/home/ghisso/work/github_copilot_bootstrap/.claude/plans/2026-11-17_phase-D-copilot-tool-inputs.md`

New file names: `2026-11-17_phase-B-copilot-tool-inputs.md`, `2026-11-17_phase-C-copilot-hook-answers.md`, `2026-11-17_phase-D-lifecycle-hook-stand-down.md`. Files A, E, F, and G keep their names and are replaced.

