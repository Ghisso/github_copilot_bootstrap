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

## [LEARN] Entries

## Verification

```text
# filled at closeout step 4
```

## Open Questions / Next Steps
