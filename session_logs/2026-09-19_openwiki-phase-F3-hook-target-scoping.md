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
- Step F3.7 (docs) done in parallel with the code, written from the plan's
  step contracts rather than the in-progress code: `docs/runtime-checks.md`
  (classifier split, gate stand-down paragraph, reverse note under the
  refresh-gates table), `docs/smoke-tests.md`, `docs/architecture.md`. The
  pull-request exception is stated as a deliberate choice with its reason.
- Steps F3.1, F3.2, F3.5, F3.6 done by the git-gate coder: one resolver
  `_git_invocation_top_level` in the shared library, two predicates on it
  (`git_targets_other_repository`, `branch_create_targets_other_repository`),
  `reporting-reminder.sh` reusing it instead of its own copy, and the three
  gates exempting a provably foreign target. `enforce-pr-gate.sh` restructured
  into per-shape detection so a nested-state push can no longer excuse a
  chained `gh pr create`; the two hole-closing tests fail on the old hook and
  pass on the new one (stash-verified). 62 new tests across
  `tests/test_hook_gates.py` and `tests/test_lifecycle_hooks.py`;
  `tests/test_branch_state.py` passes unedited. `shellcheck` is not installed
  here, so only `bash -n` ran on the shell files.
- Plan correction accepted: `--git-dir <repo>/.git` **alone** stays gated. Git
  documents that without `--work-tree` the current directory is the working
  tree, so from inside this checkout that command commits this repository's
  files into a borrowed object store. The plan's test scenario listed it as
  foreign; the plan text was corrected and a pinned test added.
- Steps F3.3, F3.4 done by the classifier coder: every `PROTECTED_PATH_LITERAL`
  alternative gained the boundary the plan demonstrated a defect for; the
  three control-plane alternatives capture the whole path token; `protected()`
  gained one containment helper on resolved path components, applied only to
  the control-plane clause, with each name form paired to the single path it
  came from (a symlink inside the repository pointing at a foreign settings
  file is allowed; a symlink outside pointing inside stays denied). Secret-
  shaped rules untouched. 42 tests in the new `tests/test_protect_files_scoping.py`,
  including both Phase F reproductions now allowed.
- One legacy test (`test_protect_files_blocks_write_through_symlinked_directory`,
  2026-08-14) encoded the old defect: a hooks-looking path entirely outside any
  repository was expected to be denied. Decision: keep its intent and anchor
  it inside an isolated checkout; handed to the git-gate coder, which owns
  that file.
- Legacy test re-anchored inside an isolated checkout with its deny assertion
  unchanged. VERIFY round 1 in the correct order (regenerate, self overlay
  refresh, checks): `validate_targets.py` exit 0, `check_runtime.py` exit 0,
  plan lint exit 0, `verify.py phase` PASS with 1753 tests, ruff and mypy
  clean, generated verifier matches source.

## Review findings and dispositions

(pending)

## [LEARN] Entries

(pending)

## Verification

(pending: runner summary lines pasted at closeout)

- optional 1: (pending)

## Open Questions / Next Steps

(pending)
