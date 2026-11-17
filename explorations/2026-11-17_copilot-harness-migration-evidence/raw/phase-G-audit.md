# Phase G, step 3: final audit of the live-advice surfaces

Date: 2026-11-18. Bootstrap HEAD `adfe3bc`, clean tree at the start. Author: the `coder`, for the orchestrator.
Scope: every live-advice surface named in "Standing final-phase audit" of `closeout.instructions.md`, and the
surfaces the orchestrator listed. The question for each: does a statement say something that this plan
(`copilot-harness-migration`, Phases A to F) or earlier work made false or incomplete?

## Method

- Facts were taken from the source first, then each statement was checked against them:
  `shared/hooks/hooks.json` (five events, 14 entries), `shared/hooks/scripts/run-hook.sh:54-74` (the stand-down),
  `shared/hooks/scripts/_lib-frontmatter.sh:16-20, 44-57, 121-132` (`json_escape`, the two answer shapes),
  `shared/hooks/scripts/protect-files.py:58-100, 3639-3657, 3700-3745` (tool sets, answer, main),
  `shared/hooks/scripts/reporting-reminder.sh:26-52` (the `session` mode), `shared/hooks/scripts/subagent-context.sh`,
  `shared/scripts/verify.py:66-78` (`COMMAND_TIMEOUT_SECONDS = 900`, `VERIFICATION_ITEM_TIMEOUT_SECONDS = 1020`),
  `scripts/check_copilot_runtime.py:41-42, 1430-1455` (session cap 150 s, run cap 480 s, flags),
  `scripts/generate_targets.py:1089-1115` (the marker), `scripts/validate_targets.py:759-772, 1607-1642, 1675-1680, 1895`.
  Small numbers in the docs were recounted: `.github/copilot-instructions.md` is 1,676 bytes; the reminder is 183 bytes;
  the Copilot hook file has 14 entries in five events (4 + 5 + 1 + 3 + 1).
- Searches: `grep -rnIiF` (fixed string, case-insensitive) over each folder, one run per term. Terms from the task:
  `Local harness`, `Copilot harness`, `Copilot SDK harness`, `Copilot CLI`, `run_in_terminal`, `send_to_terminal`,
  `apply_patch`, `chat.useClaudeHooks`, `chat.useHooks`, `hooks.json`, `SessionStart`, `SubagentStart`,
  `reporting-reminder`, `runs twice`, `run twice`, `nested`, `permissionDecision`, `additionalContext`,
  `check_native_clients`, `check_copilot_runtime`, `COMMAND_TIMEOUT_SECONDS`, `VERIFICATION_ITEM_TIMEOUT_SECONDS`,
  `480`, `600-second`, `read_bash`, `list_bash`, `stop_bash`, `view`, `secret-shaped`, `sub-agent`, `subagent`,
  `github-copilot`, `supported Copilot client`, `unsupported`, `February 2027`.
  My own terms: `reminder`, `twice`, `stand down`, `stands down`, `stand-down`, `no repository instructions`,
  `four events`, `three events`, `hook events`, `event set`, `crash`, `secondary`, `compatibility adapter`,
  `Copilot IDE`, `IDE users`, `Copilot SDK`, `SDK harness`, `Agent Host`, `first-class`, `custom-agent support`,
  `Copilot Chat`, `BOOTSTRAP_HOOK_SOURCE`, `read_file`, `` `view` ``, `SessionStart`, `PostToolUse`, `copilot` (any case,
  whole folders), `vs code|vscode|harness|run-hook|hooks.json|settings.json`, `.github`, `native client`,
  `check_runtime`, `probe`, `unverified|timed out|timeout`, `reload|reopen|restart`,
  the regular expressions `[0-9],[0-9]{3} (tests|passed)` (stale test counts) and `[0-9]+ seconds|-second` (stale budgets).
  Every term was first counted per file over all advice surfaces (`README.md`, `CLAUDE.md`, `AGENTS.md`, `SECURITY.md`, `docs/`
  without `docs/evidence/`, the `shared/` folders above without `third_party/`, root `plans/`, `targets/`), then each hit was read.
  Two terms match too much to read every hit: `nested` (41 files, nearly all "nested Git repository"; I read the hits that mean the
  answer's nested copy: README, `docs/target-mapping.md`, `docs/runtime-checks.md`) and `view` (118 files, mostly "review"; I read the
  hits for the tool name, using the backticked form `` `view` `` and `read_file`).
- Line numbers for `README.md` in the "Reading" cells below are as read, before my ten-line insertion at line 471.
- Reading: where the file is short, in full; where it is long, every section a search hit or a Copilot, hook, reminder,
  verifier, or upgrade statement sat in. Long files that were searched but not read in full are named in the table.
- Link check of the four files I changed (`README.md`, `SECURITY.md`, `docs/native-client-acceptance.md`, the skill) and the five
  documents around them (`docs/target-mapping.md`, `docs/runtime-checks.md`, `docs/smoke-tests.md`, `docs/architecture.md`,
  `docs/sidecar-provider-contract.md`): 138 relative links and their heading anchors, 0 broken
  (`scratchpad/phaseG/linkcheck.py`; it checked that the new anchors `#copilot-runtime-probe`, `#vs-code-copilot-harness-manual`,
  and `#what-changed-in-the-guard-for-the-copilot-harness` exist).

## Result in one line

Four statements corrected in four files (README, SECURITY, `docs/native-client-acceptance.md`, the `knowledge-refresh` skill).
Everything else in the editable surfaces is current or a dated record. Reported, not edited: 9 items for
`.claude/MEMORY.md` (M1 to M9), 9 for the project context file (C1 to C9), no stale statement and 2 reminders for the active plans
(P1, P2), and 28 stale statements on 9 OpenWiki pages plus one note on the two index pages (see the other two files).

## Surfaces, outcomes

### Root guidance

| Surface | How checked | Outcome |
| --- | --- | --- |
| `CLAUDE.md` (74 lines) | Read in full; searched `copilot`, `hook`, `harness`, `vs code`, `reminder`, `timeout` | No stale statement. It names the control-plane list and commands only; no client behavior. |
| `AGENTS.md` (24 lines) | Read in full | No stale statement. |
| `README.md` (1,851 lines before my edit) | Searched for every term. Read lines 1-135, 262-270, 336-362, 362-540, 536-566, 604-656, 966-992, 1026-1034, 1114-1252, 1273-1420, 1456-1760, 1757-1851. Lines 135-262 and 656-966 (installer and sidecar mechanics) were searched, not read. | Phase F text (Quick Install, Sub-agents, Hooks on the Copilot harness, policy applicability, sidecar client support) is current against the source. One omission found: the notes for an operator who refreshes a consumer (`Upgrading a consumer with active work`) did not mention the guard changes that tighten a decision on the Copilot harness (rows T1 and T4 of `docs/target-mapping.md`) or loosen one (L1 to L3). **Fixed**: bullet added at `README.md:471-480`, old text: none (the list stopped after "Shell parsing in the file-protection guard"), new text: "**Copilot harness: two new denies, three looser decisions.** The file guard now denies a search tool (`grep`, `rg`, or `glob`) whose `paths` list names a secret-shaped file such as `.env`, and, for the client `github-copilot` only, the tools `run_dynamic_workflow` and `dynamic_workflows_manage`. It no longer asks when the read tool reads a hook, server, or agent file, it no longer stops the shell helper tools `read_bash`, `list_bash`, and `stop_bash`, and it reads patch text from `apply_patch` instead of stopping it." plus a link to the table. Basis: `docs/target-mapping.md` rows L1, L2, L3, T1, T4; `protect-files.py:64-100, 3706-3745`. |
| `SECURITY.md` (85 lines) | Read in full; the validator checks only its headings and the README link (`validate_targets.py:9228-9261`) | The trust paragraph named Codex and Claude only. **Fixed**: added at `SECURITY.md:20-23`: "On the Copilot harness in VS Code, an offline run on runtime `1.0.108-0` found no repository hook before the folder was trusted. After trust it found the hooks of both `.github/hooks/hooks.json` and `.claude/settings.json` (see Runtime Checks)." Basis: `docs/runtime-checks.md:611-613` (checks `hooks-untrusted`, `hooks-sources`) and the row at `:765`; the probe printed 48 PASS lines on 2026-11-18. |

### `docs/`

| Surface | How checked | Outcome |
| --- | --- | --- |
| `docs/architecture.md` (567 lines) | Searched all terms; read 20-48, 100-135, 312-332, 420-460, 488-500 | No stale statement. The reminder scope (lines 29-31, 443-448), the launcher paragraph (317-328), and the Copilot subsection are current. |
| `docs/runtime-checks.md` (1,343 lines) | Searched all terms; read 224-380, 565-700, 740-794, 896-925, 1017-1050, 1106-1195 | No stale statement. `480` at line 591 is the probe's own run cap (`check_copilot_runtime.py:42`), correct. `1020-second` at line 1183 matches `verify.py:78`. The script list at 340-362 includes `subagent-context.sh`. |
| `docs/smoke-tests.md` (695 lines) | Searched all terms; read 1-217 and 545-640. The 11-item manual checklist (217-545) was searched and spot-checked (the 183-byte reminder, the fourth `SessionStart` entry, the five events), not re-read; Phase F's review opened about 75 of its basis rows. | No stale statement. |
| `docs/target-mapping.md` (370 lines) | Searched all terms; read 84-330, which holds every Copilot statement | No stale statement. Rows L1 to L3, T1 to T4, the tool table, and the follow-up list match the source. |
| `docs/sidecar-provider-contract.md` (1,364 lines) | Searched `copilot`; read 1-60, 958-980, 1272-1364 | The dated records (2026-09) stand as written; the 2026-11-18 note and section are current. No stale statement. |
| `docs/native-client-acceptance.md` (356 lines) | Searched all terms; read 1-40, 175-200 | Known candidate confirmed incomplete: it said Copilot "remains covered by the deterministic generated-target checks", with no pointer to the new checks. **Fixed** at lines 5-12. Old: "GitHub Copilot remains covered by the deterministic generated-target checks, not this native-client command." New: "This command does not cover GitHub Copilot. The generated Copilot files are covered by the deterministic generated-target checks. The Copilot harness (...) has its own opt-in offline check, `scripts/check_copilot_runtime.py` (see Copilot runtime probe). The checks that need a signed-in VS Code window are in VS Code Copilot harness (manual)." Basis: `scripts/check_copilot_runtime.py:1-17`; headings `runtime-checks.md:565` and `smoke-tests.md:217`. Its instruction-surface table (lines 185-192) lists the surface each target ships, still true. |
| `docs/plan-deterministic-commit-gate.md` | Header read: `**Date:** 2026-07-08`, "This is the original design record" | Dated design record. Left. (Its line 18 says a timeout means allow on Copilot; that was the 2026-07 finding, and the record says later work is in `architecture.md` and `runtime-checks.md`.) |
| `docs/2026-08-08-codex-routing-compatibility.md`, `docs/2026-08-09-planner-reliability-calibration.md`, `docs/2026-08-09-state-sync-rebase-recovery.md`, `docs/2026-09-19-openwiki-hook-mechanics-spike.md`, `docs/2026-10-06-behavioral-pilot-evidence.md` | Dated by file name | Dated records. Left. |
| `docs/evidence/behavioral-pilot/` | Folder of records | Left. |

### Canonical sources under `shared/`

| Surface | How checked | Outcome |
| --- | --- | --- |
| `shared/policies/` (12 files) | `copilot` (case-insensitive) 0 hits; all other terms read; `hook`, `reminder`, `timeout`, `read tool`, `inspect` lines read | No stale statement. `workflow.instructions.md:147` states 1020 seconds, correct. Lines 229-234 ("Automated via hooks") name no client. `workspace.instructions.md:57` (control-plane list) still holds: the new hook script sits under `.claude/hooks/`. |
| `shared/skills/` (37 skills, plus the sidecar `onboard`) | `copilot` hits: `learn/SKILL.md:99-104` (Copilot reads `.claude/skills/`; lists the `.agents/skills/` copy; still matches the Phase F discovery check), `deep-audit/SKILL.md:63` (names Copilot in a list; fine), `knowledge-refresh/SKILL.md:55-56`; `vs code`, `harness`, `hooks.json`, `settings.json`, `.github`, `native client`, `probe`, `timeout`, `reload` also searched | One statement changed: `knowledge-refresh/SKILL.md:55-56`. Old: "`copilot` targets GitHub Copilot CLI, which this bootstrap does not support." That was true but read as "no Copilot support" once the Copilot harness is supported, and it said nothing about the refresh guard. **Fixed**: "`copilot` targets GitHub Copilot CLI (it writes `.copilot/skills/openwiki` and `.copilot/mcp-config.json`), which this bootstrap does not claim. The bootstrap supports the Copilot harness inside VS Code, but the Copilot hook file has no `openwiki-guard.sh` entry, so run a refresh from Claude Code or Codex." Basis: OpenWiki's installed registry (`.../openwiki/dist/integrations/install/registry.js:135-147`, `displayName: "GitHub Copilot CLI"`, `skillDirectory: ".copilot/skills/openwiki"`, `mcpConfig .copilot/mcp-config.json`); `shared/hooks/hooks.json` has no `openwiki-guard.sh` entry (read in full); the big plan's non-goals ("the OpenWiki server and wiki guard for Copilot" are out of scope). Whether a refresh from a Copilot chat would also be caught by the Claude-settings `mcp__openwiki__openwiki_begin` matcher: not run. The sentence says only that the Copilot file has no entry. The generated copies (`.claude/skills/`, `.agents/skills/`, `dist/`) were regenerated and the self-refresh run. |
| `shared/agents/` (8 folders) | `copilot`, `subagent`, `sub-agent`, `hook`, `timeout`, `vscode` | No stale statement. `agent.yaml` `model_intent."github-copilot": "target-default"` is still the rule (the per-agent model pin is a recorded follow-up). The `vscode` capability is a tool group written into the wrappers. Prompts name subagents generally. |
| `shared/templates/` (6 files) | `copilot`, `probe`, `hook` | No Copilot or hook statement. |
| `shared/review-profiles/` (10 files) | `copilot`, `timeout`, `hook` | No statement. |
| `shared/sidecar/` (`bridge.md`, `workflow/instructions.md`, `rules/`, `skills.txt`, `skills/onboard`, `templates/`, `state/`) | `copilot`, `hook`, `reminder`, `sub-agent`, `timeout`, `verify` | No Copilot or hook statement. |
| State README sources: `shared/plans/README.md`, `shared/session_logs/README.md`, `shared/quality_reports/README.md`, `shared/sidecar/workflow/state/{explorations,plans,quality_reports,session_logs}/README.md`; the full install's explorations README is text inside `scripts/generate_targets.py:411-419` | Read in full | No stale statement; none names a client or a hook. |
| `shared/MEMORY.md`, `shared/sidecar/workflow/state/MEMORY.md` (seeds) | Read | No stale statement. |
| `shared/devcontainer/`, `shared/mcp/`, `shared/vscode/`, `shared/prompts/`, `shared/schemas/`, `shared/scripts/` | `copilot` search (0 hits in advice text); `verify.py` read at 60-82 | No advice text about Copilot. The verifier constants are 900 and 1020. |
| `shared/hooks/` (`hooks.json`, scripts, git hooks) | Read `hooks.json`, `run-hook.sh`, the reminder and sub-agent scripts, the library, the file guard's tool sets | Code and comments: not edited (rule). Follow-ups below. |
| `shared/third_party/` | `copilot` search | Vendored upstream text; not ours to edit. |

### `.github/`, generated and tracked configuration

| Surface | How checked | Outcome |
| --- | --- | --- |
| `.github/workflows/validate.yml` | Read in full | No stale statement. (It runs generation, the validator, and the Python 3.9 hook compatibility test; it does not run the opt-in probe, and no document says it does.) |
| `.github/copilot-instructions.md` (generated) | Read in full (1,676 bytes) | No false statement. Not edited (generated). |
| `.github/hooks/hooks.json`, `.github/agents/`, `.github/instructions/` (generated) | Compared in meaning with their sources (`shared/hooks/hooks.json` read in full) | Generated; not edited. |
| `targets/multi-agent/manifest.json`, `.vscode/mcp.json`, `.codex/config.toml` | `grep` for `copilot`, `hook`, `chat.` | No advice text. |
| Root `plans/` (13 files: ADR-001, ADR-002, the 2026-07 plans and review, five `2026-07-18_*` files) | Headers read; every one carries a `Date:`/`Status:` header or a dated name | Dated records and decision records. Left. (ADR-001 line 5 names Copilot in a revisit trigger; unaffected.) |
| `scripts/` and `tests/` | `copilot` search over the scripts outside the probe, validator, generator, and installer | Code. No change. |

### Report only (not edited)

| Surface | Outcome |
| --- | --- |
| `.claude/MEMORY.md` | 9 items, in `phase-G-memory-proposals.md`: the replacement for the 2026-11-17 `[LEARN:tooling]` entry (M1), two entries to correct (M2, M3), one optional addition (M4), and five draft entries (M5 to M9). |
| `.claude/instructions/project-context.instructions.md` | 9 items, in `phase-G-memory-proposals.md`. |
| Active plans: `copilot-harness-migration.md`, `2026-11-17_phase-G-knowledge-refresh.md` (Phases A to F are `complete`, so they are closed records) | No stale statement. Two closeout reminders (P1, P2), in `phase-G-memory-proposals.md`. |
| `openwiki/` (15 Markdown files: 14 pages and `INSTRUCTIONS.md`) | In `phase-G-openwiki-stale.md`: 28 statements on 9 pages (hooks-and-guardrails 13, agents-and-skills 1, source-generated-consumer-layout 3, deterministic-verification 3, install-ownership-and-runtime-checks 2, git-backed-ai-state-sync 1, sidecar-overlay 2, quickstart 2, INSTRUCTIONS 1), plus one note on the two index pages. No stale statement on `context-mode-dispatcher.md`, `lifecycle-and-task-lanes.md`, `workflows/index.md`, `index.md`. |

## Follow-ups that need a code change (not done)

1. Bare evidence labels (`F2`, `A2`, `A3`, `P1`, `P2`, `P3`, `P4`, `F9`) in comments of `shared/hooks/scripts/run-hook.sh:44-53`,
   `shared/hooks/scripts/subagent-context.sh:5-8`, `shared/hooks/scripts/protect-files.py:60`, and some test docstrings. Already
   recorded by the orchestrator (Phase G log, 07:50). A comment edit moves the line ranges the wiki cites, so it belongs after
   the refresh. (The same labels in the docs are explained once per document; the code comments have no such note.)

Open for the user, not code: keep, narrow, or lift the deny of the two workflow tools (already recorded in
`docs/target-mapping.md`, follow-up list, and in the Phase B and F logs). Not added to any document by me, as instructed:
inline Python without `-I` in older hooks, and the temp-file leak of `protect-files.sh`.

## Commands I ran (all from the repository root)

`uv run python scripts/generate_targets.py --all`; `uv run python scripts/install_bootstrap.py . --allow-self --local-only`
(the self-refresh made one nested checkpoint, `19c9b0a bootstrap: update 2026-11-17T22:56:53Z`, with the two changed copies of the
`knowledge-refresh` skill); `uv run python scripts/validate_targets.py` (PASS). The remaining checks are in the reply.
