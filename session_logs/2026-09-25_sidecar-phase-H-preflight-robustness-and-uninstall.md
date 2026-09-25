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
- `verify.py phase --format text` PASS (2085 tests); the installed validator
  passes every plan.
- Step 11 done by `documenter`:
  - `README.md`: the Quick Install detection sentence (full is the
    default with no evidence); in "Personal Sidecar Install", the
    linked-worktree reason (shared `info/exclude`, per-worktree manifest),
    the timing of the exclude proof, and "Uninstall" plus a safe "Manual
    fallback" in place of the manual removal steps; new bullets under
    "Behavior changes you should know about".
  - `docs/target-mapping.md`: `--uninstall`, and which command resolves
    each Git-directory path.
  - `docs/architecture.md`: the exact source allowlist shared by the
    validator and the installer.
  - `docs/sidecar-provider-contract.md` checked and left unchanged: it is
    Phase A's dated evidence and still matches the code.
  - One S17 claim ("a second run writes nothing") is not in the current
    README; its OpenWiki form is Phase I's.
- REVIEW split into two parallel `reviewer` runs, each with all six
  profiles: part A (detection, preflight, bytes-safety, sources) and part B
  (`--uninstall` and the docs).
- Review round 1, part A: PASS with no findings. It confirmed the
  linked-worktree refusal via the common-directory `info/exclude`, the
  environment list against `git rev-parse --local-env-vars`, the unchanged
  full-install path, refusal ordering, and that patched-profile tests never
  hide a real regression. Side note: detection still resolves the manifest
  through `git_path`.
- Orchestrator finding, from that note: `sidecar_evidence` builds the
  manifest and exclude paths with `git_path`, and `--git-path` resolves
  symlinks. A dangling manifest symlink is therefore not counted as
  evidence, although Decision 27 requires it.
- Review round 1, part B: FAIL.
  - CRITICAL (`code`): with a lost manifest and a block holding only
    unrecognized lines, `--uninstall` says "nothing to do" and leaves the
    block. Installs keep refusing on that block, so it is a dead end.
  - MAJOR (`code`): when uninstall is the first run to notice a team
    takeover, `_team_takeover` reports a retained file as "stays hidden"
    and then un-hides it.
  The docs were checked accurate: the S17 claims are fixed, and the manual
  fallback is safe.
- All three sent back to `coder`, with tests.
- Fixes (12 new tests, each failing on the previous code):
  - `ExcludeBlockContents.has_block`; uninstall's "nothing to do" check is
    now "no manifest entry and no block".
  - `_team_takeover(..., uninstall=...)` threaded through `_classify_unit`.
  - `sidecar_evidence` builds the manifest path from `--git-dir` (checked
    with `lexists`) and the exclude path from `--git-common-dir` (checked
    with `lstat`), through the new `_git_rev_parse_or_raise`.
  The full suite passes (2093). Re-verification and review round 2 (parts
  A and B) started.
- `verify.py phase --format text` PASS (2093 tests).
- Review round 2, part A: PASS. It confirmed the three changes and found
  the Git-directory paths consistent across detection, preflight, install,
  and uninstall, with the full-install path unchanged apart from the
  intended refusals. One MINOR (`tests`): a vacuous `assert ... or True` in
  `tests/test_sidecar_overlay.py`.
- Review round 2, part B: both earlier fixes confirmed, and detection and
  uninstall agree on "a sidecar is present". One new CRITICAL (`code`),
  reproduced live: the uninstall preserve-conflict branch rewrites the
  block without running the ignore gate. With the person's own negation
  after the block, a "kept" unit is reported as kept while `git status`
  shows it. It is the same defect class as round 1's MAJOR.
- Both sent back to `coder`.
- Fixes:
  - `_uninstall_conflict_pre_write_gate` runs before any unit action, and
    `_uninstall_conflict_post_rewrite_gate` runs after the rewrite and
    restores the exclude file on failure. Both run only when there are
    preserve conflicts, and the dry run mirrors both.
  - New test `test_preserve_conflict_with_a_negation_aborts_before_any_write`
    (dry and real), which fails on the old code; the no-drift guard still
    passes.
  - The vacuous assertion was replaced with real ones.
  The full suite passes (2094). Re-verification and review round 3 (the
  uninstall area) started. The rest of Phase H is unchanged since its two
  clean reviews, apart from that assertion.
- `verify.py phase --format text` PASS (2094 tests).
- Review round 3 (the uninstall area): the fix is confirmed for recorded
  units, and the corrected assertion is right. One new CRITICAL
  (`security`), reproduced live: an unrecorded ("unfinished") unit that
  hits a preserve conflict has no actions and no record, so it is in
  neither gate path set. With a negation, it is reported as kept while
  visible. One MINOR (`ponytail`): an unused `unrecognized_lines`
  parameter on `_uninstall_sidecar_dry_run`.
- Pattern: every uninstall finding so far is in the preserve-conflict
  path. The fix now builds the gate paths from `preserved_conflicts`
  itself, so no category of kept unit can slip past. Sent back to
  `coder`.
- Fixes: both gates now take `preserved_conflicts` directly, and
  `_preserve_conflict_remedy(..., unfinished=...)` reports a kept
  unfinished unit accurately. The unused parameter is removed. Three new
  tests: an unfinished conflict with a negation (fails on the old code), an
  unfinished conflict without one, and a conflicting bridge. The full suite
  passes (2097).
- Review round 4 asked for an exhaustive matrix over the conflict path
  (unit kind, state, destination, ignore state, run, and crash point)
  instead of spot checks.
- `verify.py phase --format text` PASS (2097 tests).
- Review round 4: PASS with no findings. It traced the whole matrix and
  reproduced 11 live scenarios: symlinked, dangling, and wrong-type preserve
  destinations; a directory-only negation; both fault points followed by a
  rerun; conflicts at both write roots; both bridges; and an unfinished unit
  with different content.
- Self-install before closeout committed nested state (`2c1a213`);
  `check_runtime.py` reports nothing stale, and all plans validate.

## [LEARN] Entries

- [LEARN:review] When review keeps finding defects in one code path (here
  four rounds in uninstall's preserve-conflict path: a missing gate, a gate
  path set that missed unrecorded units, and wrong reports), stop asking
  for spot checks. Ask the reviewer for an exhaustive matrix over that
  path's input dimensions (unit kind, state, destination, ignore state, run,
  crash point), and ask the coder to build safety checks from the
  authoritative set (`preserved_conflicts`), not from sets derived from
  outcome shapes. The matrix review then passed clean on its first run.
  Added to MEMORY.
- [LEARN:workflow] Splitting a large phase's review by area into two
  parallel reviewers, each with all six profiles, kept every review round
  reviewable. The clean area needed no rerun after later changes that did
  not touch it, apart from a note on the one test assertion that did.

## Verification

Required items are pasted at closeout step 4.

- optional 1: NOT RUN — the Phase A fixture is the operator's own folder outside the repository, which this session does not write to. The same check is automated: `test_clean_install_then_uninstall_restores_status_and_removes_everything` installs into a real temporary Git repository, uninstalls, and asserts that `git status --porcelain --untracked-files=all` matches the state before the install and that no block, manifest, staging folder, or sidecar file remains.

## Documentation

Updated in this phase:

- `README.md`: the Quick Install detection sentence; in "Personal Sidecar
  Install", "Uninstall" and a safe "Manual fallback" replace the manual
  removal steps, plus the linked-worktree reason, the timing of the
  exclude proof, and "Switching modes manually"; new bullets under
  "Behavior changes you should know about".
- `docs/target-mapping.md`: `--uninstall`, and which command resolves each
  Git-directory path.
- `docs/architecture.md`: the exact source allowlist.
- `docs/sidecar-provider-contract.md`: checked and unchanged.
OpenWiki pages are refreshed in Phase I.

## Open Questions / Next Steps

- Next: Phase I (`2026-09-25_phase-I-sidecar-hardening-knowledge-refresh`),
  the final knowledge refresh and stale-claims audit. The post-commit hook
  activates it after this phase's commit.
- For Phase I's audit: `sidecar_evidence` now builds its paths from
  `--git-dir` and `--git-common-dir`, and the OpenWiki claims `229e75d4`
  and `e46454b4` are known to be stale.
