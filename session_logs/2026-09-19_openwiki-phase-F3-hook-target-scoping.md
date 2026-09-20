# Session: OpenWiki Phase F3 — hook target scoping

**Date:** 2026-09-20
**Plan:** `.claude/plans/2026-09-19_phase-F3-hook-target-scoping.md`
**Status:** IN-PROGRESS

## Goal

Make four guards judge the repository a command acts on instead of the
command's text or the hook's own install location: the commit, push, and
branch-creation gates stand down for a command whose explicit `-C`,
`--git-dir`, or `--work-tree` resolves to another repository; the
protected-file classifier gains token boundaries and scopes this repository's
control-plane filenames to this repository while keeping secret-shaped names
protected everywhere. Pull-request creation stays checked every time. The
push hook's restructure closes a pre-existing hole where a nested-state push
let a chained pull request through unchecked.

## Work Log

- Phase started 2026-09-20 after Phase F2's completion commit `2c3ba61`.
  Four policy-prose files edited after that commit ride in this phase (the
  numbered `### CLOSEOUT sequence` in the workflow policy and its pointers in
  the orchestrator prompt, commit skill, and README); recorded in the plan's
  Scope with the `documentation` review profile added to Step F3.8.
- Three more instances of this phase's defect were hit during Phase F2's
  closeout: the file-protection hook blocked read-only commands whose text
  contained a dictionary key-listing call, the standard library's
  environment-variable mapping name, and a log sentence naming those two.
- Agent reuse: the Phase F2 script coder's context was large and centred on
  the verifier, so two fresh coders own this phase's code, split by file:
  one for the shell library and the three git gates (Steps F3.1, F3.2, F3.5,
  F3.6), one for the classifier (Steps F3.3, F3.4). The Phase F2 prose coder
  is reused for Step F3.7. Plan deviation recorded: the classifier's tests go
  in a new `tests/test_protect_files_scoping.py` so the two coders never edit
  the same test file.

## Review findings and dispositions

(pending)

## [LEARN] Entries

(pending)

## Verification

(pending: runner summary lines pasted at closeout)

- optional 1: (pending)

## Open Questions / Next Steps

(pending)
