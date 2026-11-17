# Session: Copilot harness migration, Phase C (answer format for the Copilot client)

**Date:** 2026-11-17
**Plan:** `.claude/plans/2026-11-17_phase-C-copilot-hook-answers.md`
**Status:** COMPLETED

## Goal

Make the guards print their decision in the documented top-level shape as
well as the nested one, for the `github-copilot` client only, so a deny no
longer depends on the undocumented PascalCase rule of the Copilot harness.
Keep the exact output bytes for Claude Code, Codex, and Antigravity. Stop a
reason that holds a control character from producing invalid JSON.

## Work Log

- **22:08** - Phase B committed as `5d229e5` and pushed; the commit hook
  activated Phase C. The big plan's risk row on the limit per verification
  item now names both values (600 seconds at approval, 1020 seconds since
  Phase B).
- **22:10** - Re-planning check against Phase B's outcome. Two points for
  the `coder`, both inside this phase's stated intent:
  - Phase B gave `protect-files.py` one output function, `print_decision`,
    shared by `emit` and the deny of the two workflow tools. Step 3 names
    `emit`; the combined answer belongs in `print_decision`, so that the
    workflow-tool deny (a `github-copilot` answer) gets it too.
  - Step 6 names only `scripts/check_copilot_runtime.py`. The session
    script `scripts/copilot_runtime_probe.mjs`, the probe's tests, and the
    probe section of `docs/runtime-checks.md` change with it, as in Phase B.
  The user's test folder `~/copilot-harness-probe-20261117` was refreshed
  with the Phase B guard for the patch-tool check in the real VS Code.
- **22:12** - Phase C delegated to a fresh `coder` with the evidence packet
  and the known traps from Phases A and B (the restore of root adapters at
  `SessionStart`, checks on lasting state, the 480-second run limit of the
  probe).
- **23:10** - `coder` finished steps 1 to 8. For `github-copilot`, every
  guard prints the decision at the top level and nested; the other three
  clients keep their bytes (19,918 comparisons against `5d229e5`, 0
  differences). The probe has a third session, `camel-rename`, and prints
  43 lines. With the earlier guards, 7 of the 43 failed: the five denies
  and the two asks under camelCase event names. The asks are a new finding
  (F4 had left them untested). Full suite: 5,714 passed, 1 skipped, 424 s.
- **23:12** - Orchestrator checks: `verify.py fast` PASS; the probe PASS (0
  of 43 failed). Scope-change record added to the small plan. Decision on
  the one open point: a text that ends in a newline now ends in a space;
  kept, because no caller passes such a text.
- **23:24** - Review round 1 (`code`, `architecture`, `security`, `tests`,
  `ponytail`, `documentation`): no CRITICAL or MAJOR finding. Two MINOR:
  the T3 row in `docs/target-mapping.md` claimed the change for every
  guard, but the file guard always escaped control characters and keeps
  them; and only `git-protection.sh` had a suite test for the Copilot shape
  on its `fail_closed` path. One open request: the `tr` form was run on GNU
  `tr` only. Sent to the `coder`: both fixes, and a comment that no longer
  claims a BSD run.
- **23:26** - For the open request: the POSIX and FreeBSD manual texts for
  `tr` were fetched and quoted in
  `raw/phase-C-tr-documentation.txt`. Both define `[c*]` in the second set
  as padding to the length of the first, and an octal range as coded
  values. A run on macOS or BSD `tr` stays an unverified limitation.
  Recorded for a later phase (old gap from the review, from Phase A): the
  probe passes `GIT_DIR`, `GIT_WORK_TREE`, and `GH_REPO` through to the
  runtime; remove `GIT_*` and `GH_*` there.
- **23:40** - Fix round 1: the T3 row is limited to the shell guards; 42
  test cases cover the `fail_closed` paths of every guard for the Copilot
  shape, each shown to fail on a broken guard. The `coder` ran the `[ *]`
  form with BusyBox `tr` 1.36.1 and got `]` for each control character:
  BusyBox does not read `[c*]`. The manuals had not shown this.
- **23:58** - Decision: the second `tr` set is exactly 31 spaces, built
  with `printf -v`, so no padding rule is used. Run on GNU and BusyBox
  `tr`: spaces and valid JSON on both. Byte-identity battery again: 19,918
  comparisons, 0 differences. Full suite: 5,756 passed, 1 skipped, 423 s.
  Orchestrator checks: `verify.py fast` PASS, and one combined answer with
  a tab, a newline, a backslash, and a quote parsed as expected.
- **00:01 (2026-11-18)** - Review round 2: Gate PASS, no open request, one
  MINOR (the Scope-change record still said T3 turns control characters
  into spaces for every guard; narrowed to the shell guards). The reviewer
  also wrote that the macOS leg of `.github/workflows/validate.yml` runs
  the control-character test. That was not so: the workflow runs
  `tests/test_hook_gates.py` as a script, which calls five smoke tests
  only. Sent to the `coder`: add that test to the script list, so macOS
  really runs it after the push, and add one test with a stub `tr` that
  fails for a second set that is not 31 characters long.
- **00:14** - Both added. The stub test fails for `'[ *]'`, for `' '`, and
  for a 30-space set, while the existing control-character tests pass on
  all three (GNU `tr` pads). The script form of `tests/test_hook_gates.py`
  exits 0 and now calls the control-character test for two clients.
  Orchestrator checks: `verify.py fast` PASS and the script form exit 0.
  `gh` is not signed in on this machine, so the macOS result of the CI
  workflow cannot be read from here.
- **00:17** - Review round 3 on the two test additions: Gate PASS, no
  finding, no open request.

### Phase-boundary summary

- **Objective and change:** for `github-copilot`, every guard prints its
  decision at the top level (the shape Copilot documents) and nested; the
  other three clients keep their bytes. Changed:
  `shared/hooks/scripts/_lib-frontmatter.sh`,
  `shared/hooks/scripts/protect-files.py`, five scripts that now name their
  client (`enforce-pr-gate.sh`, `session-start-state.sh`,
  `record-branch-state.sh`, `reporting-reminder.sh`, `openwiki-guard.sh`),
  `shared/hooks/hooks.json`, `scripts/validate_targets.py`,
  `scripts/check_copilot_runtime.py`, three test files, and two docs.
- **Deviations:** the Scope-change record under step 8 of the small plan.
- **Checks:** the required items below; the probe prints 43 lines and 0
  fail on runtime `1.0.108-0`; with the earlier guards 7 of 43 fail; byte
  identity for the other three clients (19,918 comparisons, 0
  differences); negative controls for the session setup.
- **Open findings:** none.
- **Unverified limitations:** the shell escaping was run on GNU and BusyBox
  `tr`, not on macOS or BSD `tr` (the CI workflow's macOS job runs it after
  the push); the Local harness was not run with the new output (it reads
  only the nested object, by the source of VS Code's Copilot extension
  0.74.0).
- **Decision needed:** none.
- **Next operation:** Phase D,
  `.claude/plans/2026-11-17_phase-D-lifecycle-hook-stand-down.md` (the
  lifecycle hooks from the Claude settings stand down on the Copilot
  harness).

## Stale-claims surfaces checked

This phase changed documented guard output for `github-copilot` and row T3.

- `docs/target-mapping.md`: updated in this phase (Native Adapters, the
  "Answer shape" paragraph, the T3 row, one recorded follow-up).
- `docs/runtime-checks.md`: updated in this phase (the probe section:
  three sessions, 43 lines, the new checks).
- `README.md`, `docs/architecture.md`, `docs/smoke-tests.md`: searched for
  `hookSpecificOutput`, `permissionDecision`, `additionalContext`, and for
  Copilot statements about hook output or context text; no statement
  found, so nothing to correct.
- `docs/2026-09-19-openwiki-hook-mechanics-spike.md`: shows the nested
  answer of the OpenWiki guard in a dated spike record. That guard has no
  client argument and still prints the nested answer. Not changed.
- `.claude/MEMORY.md`: the 2026-11-17 Copilot harness entry said nested
  answers are honored only under PascalCase `PreToolUse`; extended in
  place with the camelCase finding and this phase's top-level answer.
- `openwiki/`: not searched; it is refreshed through OpenWiki's tools in
  the final phase of this plan.

## [LEARN] Entries

- [LEARN:hooks] Give `tr` two sets of equal length in a hook script;
  `'[ *]'` gives `]` on BusyBox `tr`, and GNU `tr` hides it. A manual quote
  is not a run. Recorded in `.claude/MEMORY.md`.
- [LEARN:testing] The CI workflow's macOS job runs only the calls under
  `__main__` in `tests/test_hook_gates.py`; check a claim about CI
  coverage against the workflow file. Recorded in `.claude/MEMORY.md`.
- No lesson recorded for: the restore of root adapters during the probe
  (already in `.claude/MEMORY.md` from Phase A, and it was passed to the
  `coder` in the brief), and the nested `ask` under camelCase event names
  (`docs/target-mapping.md` carries it).

## Verification

```text
PASS        0.3s  uv run python scripts/generate_targets.py --all
PASS      216.7s  uv run pytest tests/test_hook_gates.py tests/test_protect_files_copilot_harness.py tests/test_protect_files_scoping.py tests/test_protect_files_substitutions.py tests/test_validate_targets.py tests/test_check_copilot_runtime.py -q --tb=short
PASS       15.2s  uv run python scripts/check_copilot_runtime.py --require
PASS        0.0s  grep -q -F 'git-protection.sh github-copilot' dist/multi-agent/.github/hooks/hooks.json
PASS       44.6s  uv run python scripts/validate_targets.py
PASS        0.9s  uv run python scripts/check_runtime.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS      424.5s  uv run python .claude/scripts/verify.py phase --format text
closeout: PASS
```

- Phase receipt: `verify.py phase --persist` PASS (Ruff, mypy, pytest with 5757 passed and 1 skipped in 425.93 s, freshness, provenance, generation).

- Findings: `.claude/quality_reports/findings-2026-11-17_phase-C-copilot-hook-answers.json`
  (no surviving finding; gate PASS; six profiles; round 1 with two MINOR
  and one open request, round 2 PASS with one MINOR, all fixed before
  round 3, which had no finding).
- optional 1: NOT RUN — it needs a person in a signed-in VS Code window with the Local harness and this phase's hooks installed in a test project; the source of VS Code's Copilot extension 0.74.0 shows the Local harness reads only the nested object, which is byte-identical to the earlier answer (944 comparisons), and the check is on the manual checklist of Phase F.

## Open Questions / Next Steps

- Next: Phase D, the stand-down of the lifecycle hooks from the Claude
  settings on the Copilot harness.
- For Phase D: remove `GIT_*` and `GH_*` variables from the environment
  the probe gives the runtime (old gap from review round 1).
- For the user: the result of the `macos-latest` job of the `Validate`
  workflow after the push; it is the first run of the shell escaping on
  BSD `tr`.
- For the user (from Phase B): one prompt in a Copilot-harness chat that
  asks for a new plain file, to confirm the patch-tool fix in the real
  client; and keep, narrow, or lift the deny of the two workflow tools.
