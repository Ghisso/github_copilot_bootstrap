# Session: Copilot harness migration, Phase F (documentation, manual checklist, sidecar check)

**Date:** 2026-11-18
**Plan:** `.claude/plans/2026-11-17_phase-F-copilot-docs.md`
**Status:** IN-PROGRESS

## Goal

Rewrite the Copilot statements in `README.md` and the docs so they match
what Phases A to E built and what was run, each with the runtime version it
was seen on. Add a short manual checklist for a signed-in VS Code window.
Record a check of the personal sidecar overlay on the Copilot harness. No
code change.

## Work Log

- **05:37** - Phase E committed as `5a77d4b` and pushed; the commit hook
  activated Phase F. The user's test folder
  `~/copilot-harness-probe-20261117` was refreshed with the Phase E hooks.
- **05:40** - Re-planning check against the outcome of Phases B to E.
  Points for the `coder`, all inside this phase's stated intent:
  - The plan's checklist item "the approval questions for a protected
    edit (two under option B)" follows the Phase D correction: the runtime
    raises two hook questions, and in the one real VS Code run VS Code
    answered the second itself. The item asks how many dialogs appear.
  - The manual checklist takes in the checks that Phases B to E left for
    a signed-in window (the patch tool, the Local-harness deny with the
    new answer, one session-log entry per chat, the sub-agent guidance,
    the session-start reminder).
  - The docs written in Phases B to E cite the evidence report by bare
    labels such as "A6" or "F13". The report is in the private AI state,
    not in the repository. Each label gets a plain description of what was
    seen and when.
  - Not added to the public docs in this phase: the follow-up on inline
    Python without `-I` in the older hooks. The user was told on
    2026-11-18 and decides how to handle it.

## [LEARN] Entries

## Verification

```text
# filled at closeout step 4
```

## Open Questions / Next Steps
