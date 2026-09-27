# Session: Sidecar Phase L — detection and recovery follow-up

**Date:** 2026-09-27
**Plan:** `.claude/plans/2026-09-27_phase-L-sidecar-detection-and-recovery-follow-up.md`
**Status:** IN PROGRESS

## Goal

Fix every finding in
`.claude/quality_reports/2026-09-27_consumer-sidecar-bootstrap-overlay-review-3.md`
(N1-N20 and the NITs) as big plan Decisions 48-58 state them, with a
real-Git regression test per behavior finding, then harden the write path.

## Work Log

- PRE-FLIGHT: branch `consumer-sidecar-bootstrap-overlay_implementation`
  at `f6f36c8`, outer tree clean, nested `.claude` checkpointed at
  `81b4825` after the reopen. Big plan `in-progress`, current phase L,
  set to `in-progress` by hand (no hook does this on an existing branch).
- The planning session prototyped every BLOCKER, MAJOR, and MINOR fix in
  three scratch exports, merged them, and proved 467 sidecar and installer
  tests, ruff, and mypy pass on the merged tree. IMPLEMENT starts by
  applying that proven combined patch, then delegates the remaining plan
  steps (2, the takeover part of 9, the fsync part of 10, 12, 13, 14) to
  `coder` and `documenter`.
- IMPLEMENT part 1: the merged prototype files (`scripts/install_bootstrap.py`,
  `scripts/sidecar_overlay.py`, and the five sidecar and installer test
  files) were copied into the working tree from the merged scratch export.
  `git apply` could not read the `--no-index` patch headers, so the
  proven files themselves were used. Focused suite: 467 passed.
- IMPLEMENT part 2 delegated in parallel on disjoint files: `coder` A owns
  `scripts/sidecar_overlay.py`, `scripts/runtime_ownership.py`, and the
  sidecar tests (steps 6, 9, 10 leftovers, 12, 13); `coder` B owns
  `scripts/install_bootstrap.py` and its tests (step 2 and the uninstall
  option warning); `documenter` owns README and docs (step 14).
- `documenter` done: README ("Behavior changes", the sidecar intro, the
  report table, the uninstall paragraphs) and `docs/target-mapping.md`
  (the `.json.next` and `.lock` files). `docs/architecture.md` and
  `docs/runtime-checks.md` restate nothing that changed. Four phrases were
  taken from the plan text because the code had not landed yet: the
  fresh-default refusals, the "listed by the sidecar's exclude block but
  never recorded" wording, the still-ignored retained message, and the
  empty-folder cleanup; the orchestrator cross-checks them against the
  final code before REVIEW.
- `coder` B done: `_fresh_default_refusal(target) -> str | None` in
  `scripts/install_bootstrap.py` (subfolder, linked worktree, bare
  repository, `.claude` as a regular file), wired only into the
  no-evidence branches of `--mode full` and no-`--mode`; the team-config
  refusal still fires first; `--mode sidecar` untouched.
  `warn_full_only_options_ignored(args, uninstall=True)` now names
  `--source` and `--local-only` for `--uninstall`. Tests: 8 refusal cases
  failed first with `DID NOT RAISE SystemExit`, 3 guards, and the
  `--uninstall` warning test failed first with `assert 0 == 1`. Coder B
  ran a tree-wide `ruff format`, which reformatted
  `scripts/sidecar_overlay.py` while coder A was editing it; coder A was
  told to re-read before further exact-text edits.
- `coder` A done: step 6 docstring; step 9's `_team_takeover` now matches
  the pending record's files (test failed first with a RETAINED report);
  step 10's `fsync` of file and parent; step 12 (a)-(h), each with a
  failing-first test, including `_still_ignored_by_another_rule` and
  `_recheck_now_visible_reports` for the uninstall report,
  `_unsafe_path_segment`, blank-line silence, the gate diagnostic, the
  uninstall wording (`uninstall` flag on three remedies),
  `SIDECAR_FORBIDDEN_TEXT_TOKENS` (which lives in
  `scripts/validate_targets.py`, not `runtime_ownership.py` as the plan
  said), and `_remove_empty_sidecar_parents`; step 13's four test fixes
  and seven guard tests. Three pre-existing tests updated for the new
  "never recorded" wording.
- VERIFY: `generate_targets.py --all` (no `dist/` diff), `validate_targets.py`
  PASS, `check_runtime.py` PASS, `validate_plan_frontmatter.py` PASS, ruff
  check and format clean, mypy clean (41 files), `pytest tests/` 2223
  passed, `verify.py fast` PASS. Working tree: 10 files changed, 2861
  insertions, 169 deletions. Diff written to the session scratch folder
  for the reviewer.
- Documentation cross-check: the README quotes the "leaves ... alone",
  "never recorded", "a team rule still ignores it", "another sidecar run
  is active", and `ABORT: filesystem error at` messages as the code prints
  them; the fresh-default refusals are described in prose. Sent to REVIEW.
- REVIEW round 1 (`reviewer`, all six profiles, two passes): PASS, no
  CRITICAL, no MAJOR, two MINOR: (1) only two of the four fresh-default
  shapes had a `--mode sidecar` guard test; (2) the README bullet for the
  fresh-default refusals paraphrased the message. Both fixed instead of
  accepted: coder B adds the bare-repository and `.claude`-as-file
  `--mode sidecar` guards; the orchestrator changed the README bullet to
  quote `The full install supports only the root of a main worktree`, which
  every one of the four messages contains.

- REVIEW round 2 (`reviewer`, `tests` and `documentation`, on the delta
  since round 1): PASS, no findings; both round-1 MINORs confirmed
  resolved against the code. Verification after the delta: ruff, ruff
  format, mypy clean; 504 focused tests; `verify.py fast` PASS. Working
  tree: 10 files changed, 2919 insertions, 169 deletions.
- Findings persisted with all six reviewed profiles across the two rounds
  and an empty surviving list.
- CLOSEOUT step 4, first attempt: every required item PASS, but
  `verify.py phase` was UNVERIFIED: `VFY-PYTEST-001: UNVERIFIED - pytest
  did not run: Command '['uv', 'run', 'pytest', 'tests/', '-q', '--tb=no']'
  timed out after 180 seconds`. The full suite takes 187.99 s wall on an
  idle machine (2,223 tests). Root cause: the verifier's
  `COMMAND_TIMEOUT_SECONDS = 180` was already close to the suite before
  this phase; Phase L's real-Git tests pushed it over. No parallel test
  runner is installed, and the constant has no override. Decision
  (orchestrator, recorded as small-plan step 15): raise the constant to
  480 in `shared/scripts/verify.py`, below the 600-second item budget by
  more than the lint and type time, regenerate `dist/`, and self-install.
  This is a control-plane change, so the phase returns to VERIFY and
  REVIEW before closeout restarts at step 2.

## [LEARN] Entries

- [LEARN:workflow] Prototype every fix of a confirmed-defect phase in a
  `git archive` export before planning (regenerate `dist/` there, run
  tools with `uv run --project <repo>`, require failing-first tests); the
  plan then quotes proven designs and the implementation is mostly
  mechanical. Tests that read `.claude/` fail in such an export. Added to
  MEMORY.
- [LEARN:tooling] Do not transport a proven scratch tree as a patch:
  `git diff --no-index` headers between absolute paths are not consumable
  by `git apply`, and a naive three-way merge of append-only test files
  interleaves test bodies. Copy the proven files, or rebuild a test file as
  one side plus the other side's appended tail. Added to MEMORY.
- [LEARN:workflow] Tell parallel coders to scope `ruff format` to their own
  files; a tree-wide run by one coder reformatted the other's in-progress
  module. Added to MEMORY.
- [LEARN:tooling] `verify.py phase` runs the whole suite under
  `COMMAND_TIMEOUT_SECONDS` and reports `VFY-PYTEST-001: UNVERIFIED` when
  the suite is slower, which fails closeout's receipt check even though
  every required item passed. Time the suite on an idle machine before
  closeout when a phase adds many real-Git tests, and compare it with the
  constant. Added to MEMORY.

## Verification

Optional items: none (the plan has no `## Optional Verification` section).
The required items' summary lines from `verify.py closeout --format text`
follow.

## Documentation

`README.md` and `docs/target-mapping.md` updated by `documenter` (step 14),
with one bullet corrected by the orchestrator after review to quote the
refusal sentence. `docs/architecture.md` and `docs/runtime-checks.md`
restate nothing that changed. `openwiki/` untouched; Phase M refreshes it.

## Open Questions / Next Steps

- Next: Phase M (`2026-09-27_phase-M-sidecar-detection-follow-up-knowledge-refresh`),
  activated by this phase's commit.
- Disposition, pre-existing and outside this plan: a skill unit that is a
  cross-filesystem mount point and not a real folder is still not refused
  in preflight; since Phase L, an `OSError` from preserving it now ends in
  the clean `ABORT: filesystem error at <path>` line instead of a
  traceback, and a rerun converges.
- Antigravity remains unverified for the sidecar (no client available).
