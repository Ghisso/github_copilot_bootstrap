# Session: Sidecar Phase G — ownership and precedence

**Date:** 2026-09-25
**Plan:** `.claude/plans/2026-09-25_phase-G-sidecar-ownership-and-precedence.md`
**Status:** IN-PROGRESS

## Goal

Make one precedence decision per skill before any unit action, prove
ownership by the manifest record or the sidecar's own exclude line, read
ownership from the Git index, preserve an edited copy of a taken skill in
the Git directory, and gate skill folders with a trailing slash (big plan
Decisions 22-25, 30, 32; findings R1, R2, R4, S3, S4, S9, S12, S15, S16, L1,
L3, L4).

## Work Log

- Phase G activated by the Phase F completion commit `f6e13af` (pushed).
- Material-impact check: Phase F changed only the plan validator and the
  workflow text; nothing in this phase's scope depends on it.
- IMPLEMENT: steps 1-8 delegated to `coder`; step 9 (docs) to `documenter`
  after the code lands.
- Coder round 1 landed steps 1-8: index-based ownership (`_read_index_entries`,
  `_unit_index_relpaths`), taken skills first with an allowlist of outcomes
  (`_ALLOWED_TAKEN_OUTCOMES`, `_convert_for_taken_skill`), symlinked and
  case-variant read folders, frontmatter names, block parsing
  (`unescape_exact_path`, `parse_exclude_block`), the unfinished outcome, the
  `preserve` action (`preserved_unit_slug`, `SIDECAR_PRESERVED_NAME`), empty
  unit folders as absent, `<unit>/` gate spelling, retired-namespace
  constants and backslash rejection, and the new remedies and per-path report
  lines. It found and fixed a real defect while testing L1: six call sites
  checked only the current bridges, so a retired bridge would have been
  gathered as an empty folder. Deviation accepted: the existing
  `excluded_units` parameter serves as the plan's "listed" set. Results: 161
  sidecar tests and 75 installer tests pass; ruff, mypy, `validate_targets.py`,
  and `verify.py fast` pass; `check_runtime.py` reports the expected stale
  installed `runtime_ownership.py` until the closeout self-install.
- The coder skipped some of the plan's listed regression scenarios. Sent
  back to add them: the case-insensitive team takeover (a MAJOR from the plan
  review), three R1 siblings, sparse checkout, `skip-worktree`, takeover then
  local delete, a tracked bridge deleted locally, two S3 real-Git scenarios,
  the named-pipe `SKILL.md`, and exact per-path report lines.
- Step 9 delegated to `documenter` in parallel (`README.md`,
  `docs/target-mapping.md` only). Done: the README "Personal Sidecar
  Install" report table (the taken-skill row lists every taking path, a new
  `PRESERVED` row, the `RETAINED` remedy with `git add -f`), both
  locally-modified remedies quoted verbatim from the code, a new "Preserved
  copies" paragraph (path format, `PRESERVED <unit> -> <path>`, conflict
  behavior, how to recover, never emptied), and the preserved folder in the
  `docs/target-mapping.md` sidecar layout. The strings were checked against
  `scripts/sidecar_overlay.py`.
- Coder round 2 added 14 regression tests. Each one fails on the pre-Phase-G
  code, except a forward guard for the named-pipe `SKILL.md` case (the old
  code had no frontmatter scan to guard). It found and fixed a real defect:
  under `core.ignorecase`, `_unit_index_relpaths` returned tracked paths in
  the index's casing, so a case-variant tracked file was still counted as
  untracked. It now takes the on-disk casing (new `disk_relpaths`
  parameter). It also fixed a test that asserted on the wrong run's output.
  Results: 175 sidecar tests and 75 installer tests pass; ruff, mypy,
  `validate_targets.py`, and `verify.py fast` pass.
- The documenter noted that the README's manual removal steps do not
  mention the preserved folder. Phase H's plan (step 11) now covers it.
- VERIFY and REVIEW (six profiles) started. `verify.py phase --format text`
  PASS (1966 tests).
- Review round 1: one MAJOR (`code`), confirmed by the orchestrator at
  `scripts/sidecar_overlay.py:1646`. `_declared_skill_names` keeps the first
  frontmatter declaration per name across all read folders, and the write
  roots sort first, so after any install the sidecar's own copies hide a
  team `SKILL.md` that declares the same name. The skill is then never taken
  and nothing is reported. The tests missed it because they injected
  `declared_skill_names` into the pure planner. Sent back to `coder` with
  three real-Git tests. No MINOR findings.
- Fix: `_declared_skill_names` now returns every declaring path per name, and
  `_extra_taking_paths` subtracts only the sidecar's own two unit paths. New
  real-Git tests:
  `test_frontmatter_collision_at_read_only_folder_takes_the_skill_and_removes_copies`,
  `test_frontmatter_collision_at_write_root_different_name_takes_the_skill`
  (both fail on the old collector), and the guard
  `test_own_installed_copies_never_take_their_own_skill`. 178 sidecar tests
  and 75 installer tests pass; ruff, mypy, `validate_targets.py`, and
  `verify.py fast` pass. Re-verification and review round 2 started.

## [LEARN] Entries

## Verification

## Documentation

## Open Questions / Next Steps
