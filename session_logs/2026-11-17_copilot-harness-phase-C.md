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

## [LEARN] Entries

## Verification

```text
# filled at closeout step 4
```

## Open Questions / Next Steps
