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
- Review round 1 CRITICAL fixed by the classifier coder (containment true for
  either the literal or the resolved repository root; two tests for both
  spellings). VERIFY round 2, same order: `validate_targets.py` exit 0,
  `check_runtime.py` exit 0, plan lint exit 0, `verify.py phase` PASS with
  1755 tests.

## Review findings and dispositions

Round 1 (fresh reviewer; profiles `code`, `architecture`, `security`, `tests`,
`ponytail`, `documentation`): 1 CRITICAL, 0 MAJOR, 0 MINOR. Gate FAIL.

- CRITICAL security — `_control_plane_in_repo_root` compared the repository
  root without resolving symlinks against a candidate that was resolved, so
  when the checkout itself sits behind a symlink (macOS `/tmp` to
  `/private/tmp`, a symlinked home or mount) an in-repository control-plane
  file named by its physical path was judged outside and left unprotected.
  Reproduced by the reviewer against the real module. Fix: containment is
  true when either the literal or the resolved form of the repository root
  contains the source; docstring corrected; tests added for both root
  spellings.
- Dropped by the reviewer in its second pass: a ponytail candidate about the
  repeated git-invocation walk, because the same idiom already exists in the
  nested-repository predicate this phase must not touch.
- Orchestrator addition after review: `docs/runtime-checks.md` now states
  that `--git-dir` without `--work-tree` does not stand down, matching the
  accepted plan correction.

Round 2 (same reviewer, delta only): the fix re-run against the real module;
`/repo-evil`, outside-pointing-in denial, and inside-pointing-out allowance all
preserved; no other unresolved-root comparison exists. PASS with zero findings.

Held up on review: resolver forwards only the three redirect flags and
composes repeated `-C` in order; every `IS_PR=1` path in the push hook reaches
the branch, base, and closeout checks; `..` and sibling-name lookalikes; all
in-repository spellings of the settings file; the CLOSEOUT sequence prose
matches `verify.py`'s real ordering requirements.

## [LEARN] Entries

- [LEARN:security] When a containment check compares a candidate path against
  a root, resolve symlinks on both sides or on neither. `repo_root_from_script`
  derives the root with a plain `cd && pwd`, so on hosts where the checkout sits
  behind a symlink (macOS `/tmp`, symlinked homes) the root keeps the link while
  the candidate is realpath'd, and an in-repository file named by its physical
  path is judged outside. Accept containment under either form of the root.
- [LEARN:workflow] A plan can encode a wrong assumption about a tool. `--git-dir`
  without `--work-tree` makes git treat the current directory as the working
  tree, so the plan's "foreign" test scenario would have exempted a commit of
  this repository's own files. When a coder reports a contract deviation with a
  documented tool fact and a pinned test, accept it and correct the plan text
  in the same phase rather than forcing the plan.
- [LEARN:testing] A legacy test that asserts a guard fires on a path entirely
  outside any repository is a test of the defect, not of the guard. When
  scoping a guard, re-anchor such tests inside an isolated checkout with the
  same assertion instead of flipping the expected outcome.
- [LEARN:workflow] Two coders can share a phase safely when they own disjoint
  source files and each writes tests to its own test file; record the test-file
  deviation in the plan. The only cross-file dependency this produced (a legacy
  test in one coder's file broken by the other's change) was resolved by
  routing the fix to the owning coder, not by editing across ownership.

## Verification

(pending: runner summary lines pasted at closeout)

- optional 1: PASS — live host session (Claude Code) after the self overlay refresh:
  `git -C /tmp/claude-1000/f3live/work commit --allow-empty -m spike`,
  `git -C /tmp/claude-1000/f3live/work push origin HEAD` to a scratch bare remote, and
  `git -C /tmp/claude-1000/f3live/work switch -c throwaway` all ran; a Python heredoc
  naming the standard library's environment-variable mapping was allowed. The
  branch-state recorder correctly wrote nothing for the foreign branch. Two
  fail-closed refusals were observed on the way and are by design: a `-C` value
  passed through a shell variable, and `-c user.email=...` options before the
  subcommand; a redirect to a directory that did not exist yet also stayed gated.

## Open Questions / Next Steps

- Next phase is `2026-09-19_phase-G-openwiki-host-driven-guard`, built against
  the Phase F spike evidence with its five adaptations and the Step G2/G4
  rewrites from Phase F2.
- Known follow-up carried from Phase F2 (MINOR, `code`): `verify closeout`
  raises an unhandled traceback when the findings report does not exist yet.
- `shellcheck` is not installed in this environment; the shell changes were
  checked with `bash -n` and the real-git test suites only.
