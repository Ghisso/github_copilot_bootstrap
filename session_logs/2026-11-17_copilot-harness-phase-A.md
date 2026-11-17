# Session: Copilot harness migration, Phase A (offline runtime probe)

**Date:** 2026-11-17
**Plan:** `.claude/plans/2026-11-17_phase-A-copilot-runtime-probe.md`
**Status:** IN-PROGRESS

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

## [LEARN] Entries

- [LEARN:tooling] VS Code removes Copilot's Local harness in February 2027,
  and the Copilot harness is the default since 1.143. The runtime bundled
  in a VS Code server folder can be run offline through its SDK with a
  scripted local model (`provider` option), no account needed. Recorded in
  `.claude/MEMORY.md` on 2026-11-17.

## Verification

```text
# filled at closeout
```

## Open Questions / Next Steps

- Next: create the branch `copilot-harness-migration_implementation` and
  delegate Phase A to `coder`.
- Open: what "Allow all" does with a guard question in VS Code (Phase F
  manual checklist).
