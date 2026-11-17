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
- **05:01** - Fix round 1 done. `docs/smoke-tests.md` corrected; the docs
  say what the two probe checks judge and what comes from one recorded
  run. New tests: a planted `json.py` (three cases), a failing `python3`,
  a closed standard input, exact warning texts. One line changed in the
  hook: a closed standard input now counts as malformed input. Mutation
  checks in a scratch copy: 22 of 23 killed; the survivor is the removal
  of `O_NOFOLLOW`, the second layer behind the real-path comparison, whose
  gap no test can create. Hard runs: closed input, failing `python3`, and
  100 MB of input all exit 0 within 0.21 s. Full suite: 5,927 passed,
  1 skipped, 430 s. Orchestrator checks: `verify.py fast` PASS, the probe
  PASS (0 of 48 failed). Review round 2 started.
- **05:04** - Review round 2: Gate PASS, no finding, no open request. The
  surviving `O_NOFOLLOW` mutation is accepted as recorded. One clause
  added to the Scope-change record for small items inside steps 1, 5,
  and 6.

### Phase-boundary summary

- **Objective and change:** on the Copilot harness each sub-agent gets
  the text of `.github/copilot-instructions.md` and one fixed line on
  where agent files and skills live, and a Copilot session gets the
  reporting reminder at session start. New:
  `shared/hooks/scripts/subagent-context.sh`. Changed:
  `shared/hooks/scripts/reporting-reminder.sh` (mode `session`),
  `shared/hooks/hooks.json` (two entries), `scripts/validate_targets.py`,
  `scripts/check_copilot_runtime.py`, `scripts/copilot_runtime_probe.mjs`,
  four test files, `README.md`, and four docs.
- **Deviations:** the Scope-change record under step 7 of the small plan.
- **Checks:** the required items below; the probe prints 48 lines and 0
  fail on runtime `1.0.108-0`; before the change the two new checks fail;
  six negative controls; the hard-input table of the hook on Python 3.13.6
  and 3.9.0; unchanged bytes for the other three clients; 23 mutations,
  22 killed.
- **Open findings:** none.
- **Unverified limitations:** the hook was not seen in a real VS Code
  Copilot-harness chat; whether the Local harness runs this hook, and
  whether its sub-agents already get the instructions, was not checked;
  the camelCase event name `subagentStart` rests on planning probe P2
  only; bash and tools on macOS (the CI workflow's macOS job runs three
  calls after the push).
- **Decision for the user (not blocking):** a separate small plan for the
  older hooks that run inline Python without `-I` (see 04:28).
- **Next operation:** Phase F,
  `.claude/plans/2026-11-17_phase-F-copilot-docs.md` (documentation, the
  manual VS Code checklist, the sidecar recorded check).

## Stale-claims surfaces checked

This phase changed the Copilot hook file's event list and who gets the
reporting reminder.

- `README.md`: updated in this phase (new subsection "Sub-agents on the
  Copilot harness"; the sentence that the Copilot file has no reporting
  reminder).
- `docs/target-mapping.md`: updated in this phase (Native Adapters; the
  same reminder sentence).
- `docs/runtime-checks.md`: updated in this phase (the reminder sentence,
  the guardrail script list that the validator compares with the shipped
  scripts, the probe section with 48 lines).
- `docs/architecture.md`: said the reminder is only for Claude Code and
  OpenAI Codex; corrected in this phase.
- `docs/smoke-tests.md`: said the Copilot event set is unchanged and
  named only Claude Code and Codex for the reminder; found by review round
  1 and corrected in this phase.
- Other files under `docs/` and `shared/` policies: searched in fix round
  1 and by the reviewer for the event list, the number of `SessionStart`
  entries, and the reminder's scope; no other statement found.
- `.claude/MEMORY.md`: the 2026-11-17 Copilot harness entry said
  sub-agents get no repository instructions; extended in place with this
  phase's hook.
- `openwiki/`: not searched; it is refreshed through OpenWiki's tools in
  the final phase of this plan.

## [LEARN] Entries

- [LEARN:hooks] Run inline Python in a hook with `python3 -I`; a
  `json.py` in the working folder is imported otherwise. Older hooks do
  not use it yet (open follow-up). Recorded in `.claude/MEMORY.md`.
- [LEARN:testing] For a new script, a failing-first run only shows the
  file was missing; follow it with one mutation for each stated property.
  Recorded in `.claude/MEMORY.md`.
- No lesson recorded for: the test in `tests/test_lifecycle_hooks.py`
  that pinned the Copilot event list (the full suite found it, as it
  should), and `sys.stdin` being `None` for a closed descriptor (the
  hook's test carries it).

## Verification

```text
# filled at closeout step 4
```

- Findings: `.claude/quality_reports/findings-2026-11-17_phase-E-subagent-context.json`
  (no surviving finding; gate PASS; six profiles; round 1 FAIL with one
  MAJOR in the documentation and four MINOR, all fixed before round 2,
  which had no finding).
- optional 1: NOT RUN — it needs a person in a signed-in VS Code window with this phase's hooks installed in a test project; in the offline probe on runtime `1.0.108-0` the first user message of the `coder` sub-agent holds the heading `GitHub Copilot Workspace Adapter` and the fixed line (check `subagent-context`), and the check is on the manual checklist of Phase F.

## Open Questions / Next Steps

- Next: Phase F, the documentation, the manual VS Code checklist, and the
  sidecar recorded check.
- For the user: decide on a separate small plan for inline Python without
  `-I` in the older hooks.
- For the user: the result of the `macos-latest` job of the `Validate`
  workflow after the pushes of Phases C to E.
- For the user (from Phase B): one prompt in a Copilot-harness chat that
  asks for a new plain file, to confirm the patch-tool fix in the real
  client; and keep, narrow, or lift the deny of the two workflow tools.
