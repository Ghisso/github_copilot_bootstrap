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
- **05:41** - Phase F delegated to a fresh `coder` in the documenter role.
- **06:22** - `coder` finished steps 1 and 2. Six files changed, docs
  only. Sidecar check on runtime `1.0.108-0`: the `skills` profile shows 2
  instruction sources, 4 skills, 0 agents; the `workflow` profile shows 4
  instruction sources, 22 skills, and the five sidecar agent files as
  Copilot agents. The docs had said Copilot gets no sidecar agents;
  corrected to what the discovery showed. A claims table with 238 rows
  gives the basis of each Copilot claim. The plan's Verification lines
  pass. The full suite had 1 failure and 1 error.
- **06:25** - Cause of that failure found by the orchestrator, and it is
  an old defect, not this phase. `protect-files.sh` makes a file with
  `mktemp` on every call and removes it only when the classifier fails, so
  each guard call leaves one empty `/tmp/tmp.XXXXXXXXXX` file
  (`openwiki-guard.sh` removes its file on both paths). `/tmp` held
  142,664 of them, all empty and all from 2026-11-17 and 2026-11-18. The
  classifier expands a glob with `glob.glob`, so the test
  `test_protect_files_checks_original_cwd_when_cd_is_not_provable[cd /tmp
  | mv * /tmp/out]` ran past the 4-second limit (exit 142). The error in
  `tests/test_verify.py` came from the same run: the fail-closed line went
  into the live `hooks-errors.log`, which a test guard reports. Cleanup:
  140,397 empty files of that name pattern, owned by the user and older
  than 30 minutes, were deleted; `/tmp` has 2,416 entries. The same test
  then passed in 0.20 s (2.75 s before). The fix of the leak is not part
  of this docs-only phase; it is recorded as an open follow-up with the
  `-I` item, and the user is told.
- **06:27** - Orchestrator checks: `verify.py fast` PASS. Scope-change
  record added to the small plan. Review round 1 started with six
  profiles.

## [LEARN] Entries

## Verification

```text
# filled at closeout step 4
```

## Open Questions / Next Steps
