# Session: Copilot harness migration, Phase A (offline runtime probe)

**Date:** 2026-11-17
**Plan:** `.claude/plans/2026-11-17_phase-A-copilot-runtime-probe.md`
**Status:** COMPLETED

## Goal

Start the big plan `copilot-harness-migration` and complete its first phase:
an opt-in, offline check of the real Copilot runtime that ships inside
VS Code (`scripts/check_copilot_runtime.py` and
`scripts/copilot_runtime_probe.mjs`), with baseline checks for the guard
results that are correct today.

## Work Log

- **15:20** - Onboarding refresh; project notes updated (`dev` released to
  `main` by PR #57; local consumers refreshed on 2026-11-15).
- **16:00** - The user asked how GitHub Copilot compares with Claude Code
  and Codex, then asked for a migration to VS Code's Copilot harness and to
  "investigate well first". Evidence spike on the Copilot runtime bundled in
  VS Code 1.146.0 (runtime `1.0.108-0`), run offline with a scripted local
  model. Report:
  `.claude/explorations/2026-11-17_copilot-harness-migration-evidence/REPORT.md`
  (findings F1 to F16).
- **16:40** - The user's first VS Code check froze. Cause: the folder
  `/run/user/1000` was missing, so VS Code's agent host could not open its
  socket (Addendum A1). After the user created the folder, the Copilot
  harness ran and matched the offline runs (A3).
- **16:50 to 17:40** - The user's checks in the real VS Code (A4 to A6): the
  dangerous Git command was denied; file creation through the patch tool was
  denied by the guard crash whenever Auto chose `gpt-6-luna`; the guard's
  question arrives as a `hook` permission request; a sub-agent start was
  seen; the hook and shell-tool environments match the plan's assumptions.
  "Allow all" was not exercised.
- **16:45 to 17:25** - Planner (full plan), independent critique (separate
  Opus `xhigh` agent, `DEVILS-ADVOCATE-2026-11-17.md`, 15 change items, two
  HIGH), planner revision 1. The plan passes
  `scripts/validate_plan_frontmatter.py`.
- **17:45** - The user approved the plan with these choices: stand-down
  option B (lifecycle hooks only), search tools refused on secret-shaped
  paths, both less strict rules agreed (read tool on configuration files,
  shell helper tools). Recorded in the big plan's "Approval record".
  Approach: seven phases in the order probe, tool inputs, answer format,
  lifecycle stand-down, sub-agent context, docs, knowledge refresh.
  Rationale: the patch-tool crash blocks file edits in the real client
  today, so the tool-input fix comes right after the probe; the answer
  format must change before any hook stands down.
- **17:43** - Branch `copilot-harness-migration_implementation` created from
  `dev` at `2e8c7bb`; Phase A set to `in-progress` by the branch hook.
- **17:45 to 18:25** - `coder` implemented steps 1 to 4. Deviation found and
  approved: deleting the project's `.mcp.json` is not enough, because the
  `SessionStart` hook restores it from the mirror copy and the runtime then
  starts the MCP servers (seen with `strace` in a loopback-only namespace).
  The probe now also removes the mirror copy and its manifest line in the
  temporary project. Recorded in the small plan's Scope-change record.
- **18:30** - Review round 1 (`code`, `architecture`, `security`, `tests`,
  `ponytail`, `documentation`): Gate FAIL. Two MAJOR (a relative
  `--vscode-bin` crashed, and an unstartable `node` was not reported as a
  failed check; no offline test of the real launcher code), six MINOR, three
  open requests for run evidence.
- **18:40 to 19:10** - Fix round: all eight findings fixed; evidence note
  written
  (`.claude/explorations/2026-11-17_copilot-harness-migration-evidence/raw/phase-A-probe-evidence.txt`,
  sections 1 to 7). The control runs showed the first `mcp-none` check
  depended on timing (FAIL in 1 of 4 runs with the file back in 4 of 4), so
  the check now also fails for a project that holds `.mcp.json` after the
  session (FAIL in 4 of 4 control runs). Approved and recorded as a scope
  change.
- **19:15** - Review round 2: Gate PASS, two MINOR (two tests weaker than
  they looked; the docs did not name the `session-main` and `FAIL project`
  lines). Both fixed. Review round 3: Gate PASS, no finding, no open
  request.

### Phase-boundary summary

- **Objective and change:** an opt-in probe that runs the real Copilot
  runtime from a VS Code server folder with a scripted local model, against
  a fresh full install in a temporary folder. New files:
  `scripts/check_copilot_runtime.py`, `scripts/copilot_runtime_probe.mjs`,
  `tests/test_check_copilot_runtime.py`; one new section in
  `docs/runtime-checks.md`.
- **Deviations:** the Scope-change record under step 2 of the small plan
  (three removals for `.mcp.json`, a one-line `README.md`, token variables
  dropped, the `session-main` line, `--discover` without trust, the
  file-based `mcp-none` condition, and a fixed Git identity with a time
  limit for the project build).
- **Checks:** the required items below; the probe printed 15 PASS lines on
  runtime `1.0.108-0`; the evidence note holds the traced runs and the
  negative controls.
- **Open findings:** none.
- **Decision needed:** none.
- **Next operation:** Phase B,
  `.claude/plans/2026-11-17_phase-B-copilot-tool-inputs.md` (patch text,
  shell helpers, the read tool's name, search tools on secret-shaped paths).

## [LEARN] Entries

- [LEARN:tooling] Deleting a root adapter from an installed project does not
  last one session: the `SessionStart` hook restores every path listed in
  `.claude/bootstrap-ownership.env` from `.claude/bootstrap-root/`. To keep
  a project without one adapter, remove the file, its mirror copy, and its
  manifest line. Recorded in `.claude/MEMORY.md`.
- [LEARN:testing] A check that reads events can pass in a wrong setup when
  the run ends before the event arrives; run a negative control several
  times and prefer a condition on state that outlasts the run. Recorded in
  `.claude/MEMORY.md`.
- [LEARN:testing] A "no Git identity" test needs `user.useConfigOnly=true`
  (through `GIT_CONFIG_COUNT`) to fail on every host. Recorded in
  `.claude/MEMORY.md`.
- [LEARN:workflow] In Claude Code a resumed subagent delivers only one
  hand-back per result; ask it to write its report to a scratch file as
  well. Recorded in `.claude/MEMORY.md`.
- [LEARN:tooling] VS Code removes Copilot's Local harness in February 2027,
  and the bundled runtime can be run offline through its SDK with a scripted
  local model. Recorded in `.claude/MEMORY.md` on 2026-11-17.
- No lesson recorded for: linking session events by tool call id (the probe
  code and its tests carry it), and a wait loop on `pgrep -f` matching its
  own command line (general shell knowledge).

## Verification

```text
PASS        0.3s  uv run python scripts/generate_targets.py --all
PASS       13.4s  uv run pytest tests/test_check_copilot_runtime.py -q --tb=short
PASS        5.9s  uv run python scripts/check_copilot_runtime.py --require
PASS        0.0s  grep -q -F 'Copilot runtime probe' docs/runtime-checks.md
PASS        0.0s  grep -q -F 'VS Code can give a model a different tool set than the runtime' docs/runtime-checks.md
PASS       44.7s  uv run python scripts/validate_targets.py
PASS        0.7s  uv run python scripts/check_runtime.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS      373.1s  uv run python .claude/scripts/verify.py phase --format text
closeout: PASS
```

- Phase receipt: `verify.py phase --persist` PASS (Ruff, mypy, pytest, freshness, provenance, generation).

- Findings: `.claude/quality_reports/findings-2026-11-17_phase-A-copilot-runtime-probe.json`
  (no surviving finding; gate PASS; six profiles; round 1 FAIL with two
  MAJOR and six MINOR, round 2 PASS with two MINOR, all fixed before
  round 3).
- optional 1: PASS — the probe was run repeatedly on runtime `1.0.108-0` and every run printed the same 15 PASS lines: three coder runs before the fix round (`diff` empty), two after each fix round, and three orchestrator runs.
- optional 2: PASS — VS Code commit `69047191fc427f2f92828279aae1d90d8eeda7ab`; Copilot SDK version `1.0.30-preview.0`; Copilot runtime version `1.0.108-0`; tool inventory of session `main` (19 tools): `bash` (command, description, shellId, mode, detach, initial_wait), `read_bash` (shellId, delay), `stop_bash` (shellId), `list_bash` (no input), `view` (path, view_range, forceReadLargeFiles), `create` (path, file_text), `edit` (path, old_str, new_str), `web_fetch` (url, max_length, start_index, raw), `semantic_code_search` (query, repo), `skill` (skill), `run_dynamic_workflow` (name, args, limits, resumeFromRunId), `dynamic_workflows_manage` (operation, name, runId, beforeSeq, meta, run), `sql` (description, query), `read_agent` (agent_id, wait, timeout, since_turn), `list_agents` (include_completed, scope), `write_agent` (agent_id, agent_ids, scope, message), `grep` (pattern, paths, output_mode, glob, type, -i, -A, -B, -C, -n, head_limit, multiline), `glob` (pattern, paths), `task` (description, prompt, agent_type, name, model, reasoning_effort, context_tier, mode).

## Open Questions / Next Steps

- Next: Phase B, the tool-input fixes in the file guard.
- Open: what "Allow all" does with a guard question in VS Code (Phase F
  manual checklist).
- The probe passes only on a computer with a VS Code server folder
  (`~/.vscode-server/bin/*`) or with `--vscode-bin`; later phases list it as
  required verification.
