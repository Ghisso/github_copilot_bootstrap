---
name: 2026-09-11_phase-A-gate-nested-readers
type: small-plan
parent_plan: 2026-09-11_nested-walkup-gating
phase_index: 1
status: in-progress
closeout_session_log:
---

# Small Plan: Gate the nested-state readers

## Scope

Make the five nested-state readers in `shared/scripts/verify.py` report absence
when `.claude` is not its own Git repository, give the verifier a plain
diagnostic for that state, close the same blind spot in
`scripts/install_bootstrap.py`, and prove all of it with tests that build the
real plain-directory shape and the outer-mirror fail-open fixture.

## Findings This Plan Is Built On

All measured against `dev` at `2258f18` with Git 2.43.0; reproduction scripts
were run from throwaway temporary repositories.

- `nested_git_head(root)` returns the outer repository's HEAD when
  `.claude/.git` is absent. `git show :plans/big.md` run from inside `.claude`
  resolves the path from the repository root, so `indexed_nested_file` and
  `nested_revision_file` return the outer repository's `plans/big.md` bytes
  while a different nested file of that path exists on disk.
- `git status --porcelain` reports paths relative to the repository root. An
  edit to the outer top-level `plans/<slug>.md` is reported as
  `plans/<slug>.md`, byte-identical to the nested-relative spelling the code
  expects. `relevant_nested_status_changes` and the status half of
  `nested_tracked_state_fingerprint` therefore bind outer state. The
  fingerprint also moved on an unrelated new file at the outer root, because
  spellings like `src/app.py` pass `is_relevant_nested_path`.
- `git ls-files --stage` run from inside `.claude` limits to that subtree with
  cwd-relative paths, so only the status half is confused.
- Fail-open, measured: outer repository gitignoring `.claude/`, with top-level
  `plans/<slug>.md`, `plans/<phase>.md`, and `plans/<later>.md` tracked with
  bytes identical to the nested plans at receipt time. After the nested big
  plan moves to its terminal bytes and the outer plan file receives any edit,
  `has_only_terminal_big_plan_change` returns `True`. After committing the
  outer terminal plan, `has_only_checkpointed_terminal_big_plan_change`
  returns `True`. `terminal_control_plane_provenance_matches` returns `True`
  in both cases, including when the nested `plans/<later>.md` on disk has
  `status: in-progress` while the outer mirror says cancelled. The control run
  with a genuine nested repository returns `False` for that state. Without an
  outer `plans/` directory both predicates return `False`.
- In the plain-directory state the gates already fail closed in the normal
  flow: `tracked_state_fingerprint` differs between closeout and the
  post-commit push gate in both the tracked-`.claude` and gitignored-`.claude`
  variants, because dirty implementation files vanish at commit.
- `validate_receipt` requires a hex `nested_head` for every receipt, including
  `fast` mode, and `build_receipt` calls it. A consumer with no `.claude` at
  all today exits with an uncaught `ValueError: receipt metadata control-plane
  provenance is invalid` traceback.
- `require_nested_head` in `scripts/install_bootstrap.py` uses
  `git -C .claude rev-parse --verify HEAD`, so it is satisfied by the outer
  HEAD when `git init` inside `.claude` failed. The migration path has a
  second check on the commit log; the setup path does not.

## Decisions

- Guard all five readers with `nested_state_repository`, not only the three
  content readers that the measured fail-open depends on. The predicate
  exists for exactly this question, and leaving `nested_git_head` and the
  fingerprint reading outer state would keep recording an outer SHA into
  receipts for a state the tool does not support.
- No `CONTROL_PLANE_PROVENANCE_SCHEMA_VERSION` bump. No field changes shape.
  A receipt recorded by the old code for a plain-directory consumer holds an
  outer SHA; against a real nested repository `nested_revision_file` returns
  `None` for that revision, the terminal predicates return `False`, the gate
  reports stale, and a closeout re-run replaces it.
- The `main()` diagnostic covers `.claude` present without `.git` and `.claude`
  absent alike, because both reach the same `ValueError` today and both have
  the same remediation. It runs before `state_metadata` in every mode except
  `gate`, which reads persisted receipts and must keep reporting its own
  errors. Exit code 2, matching the existing pre-persist refusals.
- The installer fix checks for `.claude/.git` before asking Git for HEAD.
  `require_clean_nested_state` calls `require_nested_head`, so one change
  covers both.
- Do not modify either terminal predicate, the strict comparison, or the
  `unpublishable_closeout_reason` precondition.

## Steps

- [ ] Gate the readers. In `shared/scripts/verify.py`, make `nested_git_head`
  and `nested_tracked_state_fingerprint` return `""`, and
  `indexed_nested_file`, `nested_revision_file`, and
  `relevant_nested_status_changes` return `None`, when
  `nested_state_repository(root)` is false. Replace each function's existing
  `is_dir`/`is_symlink` guard with the predicate call, since the predicate
  already performs those checks. Update the `nested_git_head` docstring to say
  it never walks up. Keep every other line of these functions unchanged.
- [ ] Add the plain diagnostic. In `main()` of `shared/scripts/verify.py`,
  after the `gate` branch returns and before `state_metadata` runs, when
  `nested_state_repository(root)` is false print one message to stderr and
  return 2. Name the cause (`.claude` is not its own Git repository, so nested
  provenance is unavailable and no receipt can be built) and the remediation
  (`bash .claude/hooks/scripts/state-sync.sh checkpoint`, then re-run). Reuse
  the wording shape of `unpublishable_closeout_reason`.
- [ ] Fix the installer check. In `require_nested_head` of
  `scripts/install_bootstrap.py`, raise the same `SystemExit` when
  `target / ".claude" / ".git"` does not exist, before running `rev-parse`.
- [ ] Add regression tests to `tests/test_verify.py`, reusing
  `_write_terminal_precondition_repo(tmp_path, plain_nested_directory=True)`
  for the plain-directory shape. Cover: each of the five readers reports
  absence for that shape while an outer file of the same relative path exists;
  the outer-mirror fail-open fixture from the findings above returns `False`
  from `has_only_terminal_big_plan_change`,
  `has_only_checkpointed_terminal_big_plan_change`, and
  `terminal_control_plane_provenance_matches`; `control_plane_provenance` for
  the plain-directory shape yields metadata that fails
  `has_control_plane_provenance`; running `main()` in that shape exits 2 with
  the diagnostic on stderr and no traceback. Add one test to
  `tests/test_install_bootstrap.py` proving `require_nested_head` raises for a
  plain `.claude` directory inside an outer repository. Before the fix, the
  outer-mirror test and the reader tests must fail; treat a green run before
  the fix as a harness bug.
- [ ] Check the harnesses. Run `uv run pytest tests/ -q` and
  `uv run python scripts/validate_targets.py`. Any existing fixture that
  produced valid receipts only because `.claude` was a plain directory inside
  the outer repository will now fail; convert each to a real nested repository
  with `git init`, since the walk-up was masking the shape under test. Do not
  relax the new guards to keep such a fixture green.
- [ ] Regenerate the target adapters and install locally with
  `uv run python scripts/generate_targets.py --all` then
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`.
  Never hand-edit generated files; the hook gate reads
  `.claude/scripts/verify.py`, so an unregenerated tree tests the old code.
- [ ] Perform the final documentation, memory, and LEARN audit. This phase is
  the only entry in the big plan's `phases:` list. Mark the exploration
  `.claude/explorations/2026-09-11_nested-git-walkup-scope-confusion.md` as
  resolved with a pointer to this plan. Write
  `.claude/session_logs/2026-09-11_phase-B-terminal-publication-recovery.errata.md`
  stating that the "Known gap, deliberately left open" entry understated the
  defect: two gates were affected and the readers returned outer file bytes,
  not only an outer SHA. Document the new diagnostic in
  `docs/runtime-checks.md` and, where the migration state is described, in
  `docs/architecture.md`. Record in `.claude/MEMORY.md` that `git -C <dir>`
  is never a repository test, that `git show :path` and
  `status --porcelain` resolve from the repository root rather than the
  working directory, and that a fail-open reproduction must include the state
  the gate is meant to refuse. Record audited surfaces and outcomes under the
  exact heading `## Stale-claims surfaces checked` in this phase's closeout
  session log. Do not edit any file bound by an earlier completed receipt.

## Review Profiles

This is control-plane and high-risk work — it changes a canonical script and
the installer — so the full profile set applies: `code`, `architecture`,
`security`, `tests`, and `ponytail`. Load `.claude/skills/ponytail/SKILL.md`
in `full` mode before every coding step.

## Verification

During implementation:

```bash
uv run python .claude/scripts/verify.py fast --format text
uv run pytest tests/test_verify.py tests/test_install_bootstrap.py -q --tb=short
```

Before review:

```bash
uv run pytest tests/ -q
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests
uv run ruff format --check shared scripts tests
uv run python scripts/generate_targets.py --all
uv run python scripts/install_bootstrap.py . --allow-self --local-only
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py phase --format json --persist
```

Phase-specific proof:

1. The outer-mirror test fails before the fix and passes after it.
2. `tests/fixtures/schema-v3-verify.py.txt` is unchanged, confirming no
   provenance schema change.
3. This repository's own `verify.py phase` and `closeout` keep passing, since
   its `.claude` is a genuine nested repository.

## Risks And Fallback Paths

- A validator or test harness depended on the walk-up to build receipts from
  a plain `.claude` directory. Convert the fixture to a real nested repository;
  do not weaken the guards.
- The `main()` diagnostic fires in a harness that runs `verify.py` with no
  `.claude` at all and asserted on the old traceback. Update the assertion to
  the new message; the exit is non-zero in both cases.
- The installer check breaks a fixture that relied on the walk-up. Give the
  fixture a real nested repository.

## Done Criteria

- All five readers report absence for a plain `.claude` directory while an
  outer file of the same relative path exists.
- The outer-mirror fixture returns `False` from both terminal predicates and
  from `terminal_control_plane_provenance_matches`.
- `verify.py` exits 2 with one plain message, and no traceback, when
  `.claude` is not its own repository.
- `require_nested_head` raises for a plain `.claude` directory.
- Neither terminal predicate, the provenance schema, nor the strict comparison
  is changed.
- Generated `dist/` and `.claude/` outputs are regenerated, never hand-edited.

## Closeout Checklist

- [ ] All steps implemented and verified
- [ ] `uv run pytest tests/ -q` passes
- [ ] `uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases` passes
- [ ] `uv run ruff check shared scripts tests` and `ruff format --check` pass
- [ ] `uv run python scripts/validate_targets.py` passes
- [ ] `uv run python scripts/check_runtime.py` passes
- [ ] Targets regenerated and installed locally
- [ ] Code, architecture, security, tests, and Ponytail reviews complete
- [ ] Critical and major findings at zero
- [ ] `docs/` updated
- [ ] `.claude/MEMORY.md` records the reusable lessons
- [ ] Closeout session log complete, including `## Stale-claims surfaces checked`
- [ ] Nested state checkpointed before persisting the closeout receipt
- [ ] Verification passed (`verify phase` then `verify closeout` PASS)
