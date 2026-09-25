# Session: Sidecar Phase H — preflight, robustness, and uninstall

**Date:** 2026-09-26
**Plan:** `.claude/plans/2026-09-25_phase-H-sidecar-preflight-robustness-and-uninstall.md`
**Status:** IN-PROGRESS

## Goal

Refuse unsafe targets before any write, and make every run safe with unusual
repositories, file names, and sources: harden mode detection, validate
Git-directory metadata and exclude markers, make paths bytes-safe, check
repository boundaries and filesystem shape, require complete sources, remove
`bootstrap_commit`, add `--uninstall`, correct messages, and do the full
documentation pass (big plan Decisions 26-29, 31, 33-36).

## Work Log

- Phase H activated by the Phase G completion commit `8d153c3` (pushed).
- Material-impact check: Phase G supplies the index reader
  (`_read_index_entries`, with modes) that steps 2 and 6 reuse. It builds the
  preserved path from `--git-dir`, which step 3 moves to `--absolute-git-dir`
  with the other Git-directory paths. It keeps unrecognized block lines,
  which step 9 must preserve on uninstall (already added to the plan). The
  manual removal fallback in step 11 must name the preserved folder (already
  added). No other change to this phase's scope.
- IMPLEMENT, split into two sequential coder runs: run 1 covers steps 1-8
  and 10; run 2 covers step 9 (`--uninstall`) on top of run 1. Step 11 goes
  to `documenter`. Lesson from Phase G: the coder gets the full list of
  required test scenarios up front.
- Coder run 1 (steps 1-8, 10) landed:
  - `scrub_inherited_git_environment()` with `GIT_REPO_LOCAL_ENV_VARS`.
  - Mode detection: `lstat` on `.claude/.git` plus an index check, Git run
    with `LC_ALL=C`, `GitDetectionError` for any failure other than "not a
    git repository", bytes-safe `tracked_generated_paths`, and a
    `sidecar_evidence` that reads only a regular file.
  - Git-directory paths built from `--git-dir` and checked with `lstat`
    before any write.
  - `_find_exclude_markers` and `ExcludeMarkerError` refuse unbalanced
    markers.
  - `os.fsencode`/`os.fsdecode` throughout, `check-ignore -v --stdin -z`,
    and `_can_express_in_gitignore`.
  - Repository-boundary, filesystem-shape, and writability checks.
  - `sidecar_source_violations` shared with `validate_targets.py`, and
    `require_full_source_complete` for full mode.
  - `bootstrap_commit` removed.
  - Message fixes.
  Results: 345 tests across the four suites pass, the full `tests/` suite
  passes (2060), and ruff, mypy, `validate_targets.py`, and `verify.py fast`
  pass.
- Deviation rejected: the source check required only a non-empty tree with
  the same skills at each root, so a half-rendered source could still
  silently uninstall missing skills or bridges (S13). Sent back: enforce
  Decision 31's full set, use a monkeypatched profile in the tests that need
  a reduced one, and add refusal tests for missing skills, bridges, and
  licenses.
- Deviation accepted, for review to confirm: the boundary check covers the
  four structural paths (both write roots and the bridge parents), not
  every unit path. A nested repository at a unit path is an untracked
  foreign unit, which the sidecar never writes into.
- Coder run 2 (the same agent, keeping its context): fix the completeness
  check, then step 9 (`--uninstall`) with every listed scenario.
- Run 2 landed:
  - `sidecar_source_exact_allowlist()` builds the exact required set from
    the live profile constants; `sidecar_source_violations` reports each
    missing and each unexpected path. It is shared by the installer and
    `validate_targets.py`, and the validator's own license and bridge
    checks are unchanged.
  - Tests that use a reduced profile now go through
    `patch_sidecar_skills` / `install_sidecar_with_profile` in
    `tests/sidecar_test_helpers.py`, which patch `SIDECAR_SKILLS` in both
    modules. The test fixture always writes both bridges and the Ponytail
    licenses.
  - New refusal tests for a source with 2 of 4 skills, a missing bridge,
    and a missing license.
  - `--uninstall`: `_run_uninstall` runs before mode detection, so the
    team-config refusal cannot apply. `uninstall_sidecar` shares
    `_run_target_preflight` with the install, and the planner runs with
    `uninstall=True` (every skill and bridge treated as taken; retained
    files un-hidden and reported). `_remove_exclude_block` writes
    unrecognized lines back as plain lines. The order is: units, fault
    point `after_units_removed`, the block, fault point
    `before_manifest_write`, the manifest, then the staging folder is
    removed. A preserve conflict exits 1.
  - 21 tests in the new file `tests/test_sidecar_uninstall.py`.
  Results: the full `tests/` suite passes (2085); ruff, mypy,
  `validate_targets.py`, and `verify.py fast` pass.
- Added `tests/test_sidecar_uninstall.py` to this plan's required pytest
  line. The documentation pass (step 11) was delegated to `documenter`.
  VERIFY started.

## [LEARN] Entries

## Verification

## Documentation

## Open Questions / Next Steps
