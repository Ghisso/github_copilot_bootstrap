# Session: Sidecar Phase J — safety follow-up

**Date:** 2026-09-26
**Plan:** `.claude/plans/2026-09-26_phase-J-sidecar-safety-follow-up.md`
**Status:** IN-PROGRESS

## Goal

Fix every finding in the two 2026-09-26 reviews of Phases A-I (R1-R5 and
O1-O19): unit-level repository boundaries, complete snapshots, uninstall on
the install's write order, gate paths from the planner, one path-identity
rule for collision sources, Git line splitting, accurate reports, the
settled-refresh identity check, and corrected docs (big plan Decisions
37-47).

## Work Log

- Orchestration handed over from the planning session. The user confirmed
  the plan is approved, including three choices: a team submodule
  (gitlink) at a skill path is skipped as team-owned and never touched; a
  personal nested repository at a skill path that the sidecar never
  recorded or listed is skipped as foreign (only a recorded or listed one
  is refused); `.gitignore` is not an agent-harness path, so only the docs
  wording changes (Decision 46).
- Material-impact check: the plan was drafted against HEAD `010f08c`, and
  nothing has landed since. No change to scope.
- Phase J set to `in-progress`; nested state checkpointed.
- IMPLEMENT, split three ways. Coder A takes steps 1-5 in
  `scripts/sidecar_overlay.py` first. The same coder then gets steps 6-9,
  so the first half can be checked before uninstall is rebuilt on it.
  Coder B takes step 10 (the plan validator) in parallel, on disjoint
  files. Step 11 goes to `documenter` after the code lands. Each coder got
  every scenario listed under its steps, the before/after rule on
  `010f08c`, and the real-Git test rule.
- Coder B (step 10) landed: `_knowledge_refresh_phase_settled` takes the
  big plan's `name` and requires a non-empty name, an `lstat` regular file,
  `type: small-plan`, a matching `name` and `parent_plan`, and a settled
  status; the docstring and module comment state the same rule. The three
  Phase F fixtures are now valid small plans, the slug guard test follows
  `lstat`, and there are five new rejection tests (symlink, unrelated
  parent, wrong type, wrong name, empty big-plan name). It ran under a
  real Python 3.9.0. Orchestrator re-check: 627 validator tests pass, every
  real plan validates, and all five rejection tests fail against the
  `010f08c` validator in a scratch copy.
- Step 11 part 1 (`documenter`, in parallel with coder A, only for the
  docs that do not depend on coder A's code): the Termination paragraph
  in `shared/policies/workflow.instructions.md` states the settled-refresh
  identity check; README's source-check bullet says full mode checks only
  `state-sync.sh` while the sidecar source must match its exact allowlist
  (O14 first bullet); README lines 65 and 659 say "an agent-harness path"
  and exclude `.gitignore` (O15, Decision 46). `docs/target-mapping.md`
  restates neither. Checked against the code. Part 2 (boundary rule,
  uninstall behavior) waits for coder A.
- Coder A run 1 (steps 1-5) landed in `scripts/sidecar_overlay.py` and
  `tests/test_sidecar_install.py`:
  - Step 1: `_split_exclude_text` (split on `\n`, compare without one
    trailing `\r`, write original bytes) in every exclude parser and
    writer.
  - Step 2: `_gather_unit` stops at a gitlink or a nested `.git` entry
    (`UnitSnapshot.is_gitlink`, `nested_repo_relpath`); a new `gitlink`
    outcome with a "never touches files inside a submodule" remedy; a
    planner `nested_repo` abort for a recorded or listed unit; the
    `_unit_device_violations` check on every existing unit folder;
    `GitCheckIgnoreError` when `check-ignore` exits outside 0 and 1.
  - Step 3: `UnitSnapshot.incomplete` and `kind`; an incomplete unit never
    matches a hash; `_team_takeover` retains untracked symlinks; the
    retained carry-forward loop also keeps retained symlinks.
  - Step 4: `required_snapshot_units(..., listed_files)`.
  - Step 5: `PlanResult.gate_paths_write` and `gate_paths_final`,
    `_gate_spelling` by snapshot kind, `_ALL_SKILL_WRITE_ROOTS` in
    `_gate_spelling` and `_skill_name`, and `run_ignore_gate` fails closed
    and explains only `expected - ignored`.
  - 20 new tests: 17 fail on `010f08c`, and 3 are named guards (a
    personal clone, a real submodule, a team skill with its own
    submodule). The uninstall wiring of `gate_paths_final` is left for
    step 6.
  - Deviation accepted: the existing gitlink test now asserts the Decision
    37 submodule wording.
  - Full suite 2122 passed; the one failure (`test_validate_targets`) was
    stale `dist/`, which the orchestrator then regenerated.
- Orchestrator re-check: no exclude reader or writer uses `splitlines`;
  the remaining calls parse frontmatter and legacy records. 12 sampled new
  tests run against the `010f08c` code (with a shim for the new exception
  name): 11 fail on behavior assertions (a deleted pipe, an edited unit
  reported unchanged, a decoy hidden by a raw pattern), and the
  personal-clone guard passes.
- Open point sent back with steps 6-9: Decision 37 also covers a gitlink
  below a unit (a listed file line under `<unit>/vendor` after `vendor`
  becomes a submodule must be dropped and reported, never sent to
  `check-ignore`).
- Coder A run 2 (steps 6-9 and the open point) landed; it also touched
  `scripts/install_bootstrap.py`, `tests/test_sidecar_uninstall.py`,
  `tests/test_sidecar_overlay.py`, and `tests/test_install_bootstrap.py`:
  - Step 2 open point: `UnitSnapshot.gitlink_child_relpaths`; a listed
    file line under a gitlink below a unit is dropped and reported first,
    whatever the unit's outcome.
  - Step 6: `PlanResult.kept_conflicts` (taken units that are locally
    modified or unfinished and whose preserve destination exists); during
    uninstall `taken_units` is every classified unit and the required set
    uses `_ALL_SKILL_WRITE_ROOTS` and `_ALL_BRIDGES`. Uninstall apply and
    dry run follow the install's order: the write-phase block (skipped when
    there is nothing to write), one gate over `gate_paths_final`, the
    shared `_apply_actions` (with an assert that nothing is installed,
    updated, or adopted), then a branch on `kept_conflicts` only. The two
    conflict-only gates, `_apply_uninstall_actions`, and the now-dead
    `_write_raw_paths` are removed; the fault-point names are unchanged.
  - Step 7: `_read_only_taken_conflict_remedy` for a taken skill with a
    kept conflict; `_report_preserved_folder_if_nonempty` on every
    uninstall path, including both "nothing to do" paths; the `--mode
    full` refusal mentions `--uninstall`; `warn_tracked_paths` turns
    `GitDetectionError` into a warning; the named-pipe test uses a plain
    `subprocess.run(..., timeout=30)`.
  - Step 8: `_enumerate_read_entries` is the one enumerator for folder
    names and frontmatter names. Root cause of O6: `_reflects_a_write_root`
    matched every ordinary entry inside a write root.
  - Step 9: the property test's `unchanged` and `adopt` fixtures now
    produce those outcomes. Mutation check: with `"adopt"` added to
    `_ALLOWED_TAKEN_OUTCOMES`, the property test failed on its assertion
    (`AssertionError: assert ['adopt'] not in (['install'], ['unchanged'],
    ['update'], ['adopt'])`, the `adopt` case), not on an exception; after
    the revert, all 97 planner tests pass.
  - Tests: 17 fail on `010f08c`, and 5 are named guards (two retired
    bridges, a team negation added after install, a symlink unit
    uninstall, and the O15 code-plus-`.gitignore` repository).
  - Full suite: 2141 passed. Ruff, mypy, and `verify.py fast` pass.
- Orchestrator re-check: 17 sampled round-2 tests run against `010f08c`;
  14 fail on behavior assertions, and the 3 guards among them pass.
- Orchestrator finding (MINOR, sent back to coder A before review): the
  preserved-folder message says "from an earlier run" even after the same
  uninstall run preserved a copy.
- Step 11 part 2 sent to `documenter`. REVIEW part A (steps 1-5, 8, 9;
  all six profiles) started in parallel; the wording fix is outside it.
- Wording fix landed: "preserved copies are in {preserved_root}; the
  sidecar never empties this folder". `test_edited_copy_is_preserved_on_uninstall`
  asserts it for a run that preserves its own copy, and that "an earlier
  run" never appears.

## [LEARN] Entries

## Verification

## Open Questions / Next Steps

- Next: Phase K (`2026-09-26_phase-K-sidecar-follow-up-knowledge-refresh`),
  activated by this phase's commit.
