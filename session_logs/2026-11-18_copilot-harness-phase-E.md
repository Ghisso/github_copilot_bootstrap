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
- **04:26** - Review round 1: the hook held on every safety point (valid
  JSON for any file text, no path that denies or fails, only the one file
  read). Gate FAIL on one MAJOR in the documentation:
  `docs/smoke-tests.md` still said the Copilot event set is unchanged and
  named only Claude Code and Codex for the reminder. Four MINOR: two doc
  sentences tie more to the probe check than it judges; four stated
  properties had no test that can fail (`python3 -I`, a failing `python3`,
  closed standard input, the changed warning text); two over-engineering
  items in the tests and the probe. Two evidence requests: three hard runs
  of the hook, and targeted negative controls. All sent to the `coder`.
- **04:28** - Old gap from the review, kept out of this phase and
  recorded as a follow-up: older hook scripts run inline Python without
  `-I` (`_lib-frontmatter.sh`, `pretool-bash-guard.sh`, `session-log.sh`),
  with the repository root as the working folder. Confirmed with a scratch
  run: `python3 -c 'import json'` in a folder that holds `json.py` imports
  that file, and `python3 -I -c` does not. A `json.py` in the repository
  root is not a protected name, so its code would run inside the guards.
  The user is told, with the recommendation of a separate small plan.

## [LEARN] Entries

## Verification

```text
# filled at closeout step 4
```

## Open Questions / Next Steps
