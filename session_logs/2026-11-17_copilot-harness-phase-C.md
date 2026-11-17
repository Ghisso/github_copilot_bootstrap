# Session: Copilot harness migration, Phase C (answer format for the Copilot client)

**Date:** 2026-11-17
**Plan:** `.claude/plans/2026-11-17_phase-C-copilot-hook-answers.md`
**Status:** IN-PROGRESS

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

## [LEARN] Entries

## Verification

```text
# filled at closeout step 4
```

## Open Questions / Next Steps
