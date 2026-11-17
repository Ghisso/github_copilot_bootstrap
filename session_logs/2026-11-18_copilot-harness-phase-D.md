# Session: Copilot harness migration, Phase D (lifecycle hooks stand down)

**Date:** 2026-11-18
**Plan:** `.claude/plans/2026-11-17_phase-D-lifecycle-hook-stand-down.md`
**Status:** IN-PROGRESS

## Goal

On the Copilot harness, every hook runs twice, because the runtime loads
both `.github/hooks/hooks.json` and `.claude/settings.json`. Implement
option B, which the user chose on 2026-11-17: the lifecycle hooks reached
through the Claude settings stand down there (read the input, print
nothing, exit 0). The guards keep running from both files. A real Claude
Code session and the Local harness never stand down.

## Work Log

- **00:51** - Phase C committed as `49d3460` and pushed; the commit hook
  activated Phase D. The user's test folder
  `~/copilot-harness-probe-20261117` was refreshed with the Phase C hooks.
- **00:55** - Re-planning check against Phase C's outcome. Points for the
  `coder`, all inside this phase's stated intent:
  - The probe has three sessions since Phase C. The new checks of step 4
    belong to session `main`; session `camel-rename` runs with the Claude
    settings switched off.
  - Step 4 names only `scripts/check_copilot_runtime.py`. The session
    script, the probe's tests, and the probe section of
    `docs/runtime-checks.md` change with it, as in Phases B and C.
  - One old gap from the Phase C review is added to step 4: the probe
    passes `GIT_DIR`, `GIT_WORK_TREE`, and `GH_REPO` through to the
    runtime; `GIT_*` and `GH_*` variables are removed there.
- **00:56** - Phase D delegated to a fresh `coder` with the evidence
  packet and the known traps from Phases A to C.
- **01:50** - `coder` finished steps 1 to 6. The launcher `run-hook.sh`
  stands the five lifecycle hooks down only when all seven conditions
  hold. Condition matrix: 234 rows, no guard row stands down, 5 lifecycle
  rows stand down (all seven conditions holding). Old launcher against the
  new one where no stand-down applies: 1,281 comparisons, 0 differences.
  On the real runtime, before the change `single-session-log` and
  `state-sync-once` fail (two `claude-code` lines, two pull lines); after
  it the probe prints 46 lines and 0 fail. Full suite: 5,826 passed,
  1 skipped, 426 s.
- **01:53** - Orchestrator checks: `verify.py fast` PASS; the probe PASS
  (0 of 46 failed). Scope-change record added to the small plan. One
  follow-up sent to the `coder` before review: `prepare_project` passed
  the host's `GIT_*` and `GH_*` variables to `git init` and the installer;
  it now starts from the filtered environment. The `coder` had also noted
  that `AI_STATE_REMOTE` passes through; it does not, the function sets it
  to an empty string.
- **02:01** - Follow-up done: `prepare_project` builds on the filtered
  environment. Two tests added; with the earlier line put back, both fail,
  and a probe run with `GIT_DIR` aimed at a scratch folder writes a `.git`
  there. With the fix the scratch folder stays untouched and the probe
  passes (0 of 46 failed). Orchestrator checks: `verify.py fast` PASS and
  the probe PASS. Review round 1 started with six profiles.
- **02:12** - Review round 1 (`code`, `architecture`, `security`, `tests`,
  `ponytail`, `documentation`): no finding on the stand-down rules (no
  guard can stand down; a real Claude Code or Local-harness session cannot
  stand down; the stand-down path cannot deny or fail). Gate FAIL on one
  MAJOR in the documentation: `README.md` and `docs/target-mapping.md`
  said a deny shows twice and a protected edit asks twice. The recorded
  runs show one deny reason per denied call, and in the one real VS Code
  run the second question was answered by VS Code itself, so the user saw
  one (A6). The wording came from the plan's own text. Two MINOR: `grep`
  errors on an unreadable Copilot hook file reach stderr; one new test and
  the `state-sync-once` check depend on ambient `AI_STATE_*` variables.
  One open request: a full suite run on the final tree. Sent to the
  `coder` with two small accuracy fixes (`docs/architecture.md`, one test
  comment).
- **02:36** - Fix round 1 done. The docs now state what was seen: a deny
  from either file blocks the call; the runtime raises two hook questions
  for one protected edit, and VS Code answered the second itself in the
  real run. `stands_down()` silences `grep` errors (81 more comparisons
  for an unreadable hook file, 0 differences). The probe drops `AI_STATE_*`
  variables; with the earlier filter and `AI_STATE_REPO_ROOT` aimed at a
  scratch folder, the installer wrote a `.claude` folder there. Condition
  matrix: 247 rows, no guard row stands down. Differential: 1,362
  comparisons, 0 differences. Full suite on the final tree: 5,829 passed,
  1 skipped, 434 s. Orchestrator checks: `verify.py fast` PASS, the probe
  PASS (0 of 46 failed). Review round 2 started.
- **02:39** - Review round 2: Gate PASS, no finding, no open request. From
  its notes: the big plan's options table (row B) still said "A deny also
  happens twice"; a dated correction is added below that table. Left as
  is: one docstring summary line and one test comment say "one question
  per hook source", which evidence A6 and the one-source control support.

### Phase-boundary summary

- **Objective and change:** on the Copilot harness the five lifecycle
  hooks reached through the Claude settings stand down; the guards run
  from both files. Changed: `shared/hooks/scripts/run-hook.sh` (the rule),
  `scripts/generate_targets.py` (the marker in the Claude settings
  commands), `scripts/validate_targets.py` (the marker check),
  `scripts/check_copilot_runtime.py` (three checks in session `main`, the
  environment filter), three test files, `README.md`,
  `docs/target-mapping.md`, `docs/runtime-checks.md`,
  `docs/architecture.md`.
- **Deviations:** the Scope-change record under step 6 of the small plan.
- **Checks:** the required items below; the probe prints 46 lines and 0
  fail on runtime `1.0.108-0`; before the change two of them fail; the
  condition matrix (247 rows, no guard row stands down); the differential
  against `49d3460` (1,362 comparisons, 0 differences); the mixed-install
  runs.
- **Open findings:** none.
- **Unverified limitations:** the stand-down was not seen in a real VS
  Code Copilot-harness chat (Phase F's manual checklist); bash and tools
  on macOS (the CI workflow's macOS job runs four launcher calls after
  the push).
- **Lost on purpose on the Copilot harness:** the state push from the
  Claude settings at `UserPromptSubmit` and `SessionEnd`; the Copilot hook
  file still pushes at every `Stop`.
- **Decision needed:** none.
- **Next operation:** Phase E,
  `.claude/plans/2026-11-17_phase-E-subagent-context.md` (sub-agent
  context and the session-start reminder).

## Stale-claims surfaces checked

This phase changed what the launcher does and what the generated Claude
settings hold.

- `README.md`: updated in this phase (the section "Hooks on the Copilot
  harness").
- `docs/target-mapping.md`, `docs/runtime-checks.md`: updated in this
  phase (Native Adapters; the probe section and its environment text).
- `docs/architecture.md`: its launcher paragraph said only that
  `run-hook.sh` resolves the root and dispatches; one sentence on the
  stand-down rule added in this phase.
- `docs/smoke-tests.md:225`: says the generated `run-hook.sh` is
  executable because Claude and Codex hook commands call it directly.
  Still true; the Claude command now has a variable assignment in front of
  the same call. Not changed.
- `docs/sidecar-provider-contract.md:1218`: names `run-hook.sh` as one of
  the scripts that identify an install. Not affected.
- `.claude/MEMORY.md`: the 2026-11-17 Copilot harness entry said every
  hook runs twice; extended in place with this phase's stand-down.
- `.claude/plans/copilot-harness-migration.md`: the options table said a
  deny happens twice; a dated correction is added below the table.
- `openwiki/`: not searched. `openwiki/architecture/hooks-and-guardrails.md`
  describes the earlier launcher; the final phase of this plan refreshes
  it through OpenWiki's tools.

## [LEARN] Entries

- [LEARN:tooling] A script that builds a temporary project must drop
  `GIT_*`, `GH_*`, and `AI_STATE_*` from the environment before it runs
  `git`, the installer, or `state-sync.sh`; with `GIT_DIR` or
  `AI_STATE_REPO_ROOT` set, they wrote into another folder. Recorded in
  `.claude/MEMORY.md`.
- [LEARN:documentation] Plan text is not evidence: name the run that shows
  a behavior before the claim goes into the docs. Recorded in
  `.claude/MEMORY.md`.
- No lesson recorded for: `grep -q` not silencing error messages (general
  shell knowledge), and the closed standard input on the stand-down path
  (the launcher's comment and its test carry it).

## Verification

```text
# filled at closeout step 4
```

- Findings: `.claude/quality_reports/findings-2026-11-17_phase-D-lifecycle-hook-stand-down.json`
  (no surviving finding; gate PASS; six profiles; round 1 FAIL with one
  MAJOR in the documentation and two MINOR, all fixed before round 2,
  which had no finding).
- optional 1: NOT RUN — it needs a person in a signed-in VS Code window with this phase's hooks installed in a test project; the offline probe on runtime `1.0.108-0` shows the same two facts for session `main` (`single-session-log`: no `target=claude-code` line for the session; `deny-git-reset`: still denied), and the check is on the manual checklist of Phase F.

## Open Questions / Next Steps

- Next: Phase E, sub-agent context and the session-start reminder.
- For the user: the result of the `macos-latest` job of the `Validate`
  workflow after the pushes of Phases C and D.
- For the user (from Phase B): one prompt in a Copilot-harness chat that
  asks for a new plain file, to confirm the patch-tool fix in the real
  client; and keep, narrow, or lift the deny of the two workflow tools.
