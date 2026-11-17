# Session: Copilot harness migration, Phase E (sub-agent context and session-start reminder)

**Date:** 2026-11-18
**Plan:** `.claude/plans/2026-11-17_phase-E-subagent-context.md`
**Status:** IN-PROGRESS

## Goal

On the Copilot harness a custom sub-agent (`coder`, `reviewer`, and the
others) gets only its three-line agent file: no repository instructions
and no skill list. Add a `SubagentStart` hook that gives each sub-agent the
text of `.github/copilot-instructions.md` plus one fixed line on where
agent files and skills live. Give Copilot sessions the plain-language
reporting reminder at session start.

## Work Log

- **03:12** - Phase D committed as `3402601` and pushed; the commit hook
  activated Phase E. The user's test folder
  `~/copilot-harness-probe-20261117` was refreshed with the Phase D
  launcher.
- **03:15** - Re-planning check against the outcome of Phases C and D.
  Points for the `coder`, all inside this phase's stated intent:
  - The probe's `camel-rename` session (Phase C) renames the events of the
    Copilot hook file. The new `SubagentStart` event must be renamed there
    too, and the setup check `camel-events-renamed` must still hold.
  - `reporting-reminder.sh` is one of the five names the launcher can
    stand down (Phase D). The new `SessionStart` entry sits in the Copilot
    hook file, which carries no marker, so it runs; a test pins that.
    `subagent-context.sh` is not a lifecycle name and never stands down.
  - Step 5 names only `scripts/check_copilot_runtime.py`. The session
    script, the probe's tests, and the probe section of
    `docs/runtime-checks.md` change with it, as in Phases B to D.
- **03:16** - Phase E delegated to a fresh `coder` with the evidence
  packet and the known traps from Phases A to D.
- **04:14** - `coder` finished steps 1 to 7. New script
  `subagent-context.sh`; mode `session` in `reporting-reminder.sh`; two
  new entries in the Copilot hook file. On the real runtime both `coder`
  and `reviewer` received the whole guidance text, then the fixed line,
  then the task prompt; before the change the two new probe checks fail.
  The probe prints 48 lines and 0 fail. The other three clients' hook
  files are byte-identical to `3402601`. Full suite: 5,923 passed,
  1 skipped, 433 s. Its first full run found one test in
  `tests/test_lifecycle_hooks.py` that pinned the old event list; updated.
- **04:15** - Orchestrator checks: `verify.py fast` PASS; the probe PASS
  (0 of 48 failed). Scope-change record added to the small plan. Two
  decisions: the built-in `general-purpose` sub-agent also received the
  guidance in the probe, which is accepted (no filter by agent type); the
  probe check stays as planned (heading and fixed line), because the unit
  tests of the hook pin the whole file text. Review round 1 started with
  six profiles.

## [LEARN] Entries

## Verification

```text
# filled at closeout step 4
```

## Open Questions / Next Steps
