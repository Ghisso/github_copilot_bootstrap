# Session: Hook scripts activate Git hooks, keep the error log local, and explain the push refusal

**Date:** 2026-09-11
**Plan:** `.claude/plans/2026-09-11_phase-2-hooks-path-log-and-gate-hint.md`
**Status:** COMPLETED

## Goal

Make every supported first-machine path activate the Git hooks, stop tracking
the hook error log in `ai-state`, make the push gate explain a chained
commit-and-push refusal, keep the test suite out of the live error log, and
run the plan-wide final documentation, memory, and LEARN audit.

## Why This Phase Exists

`core.hooksPath` was set only by the installer and the devcontainer script.
The documented "new machine without a devcontainer" path never set it, so the
commit-msg, post-commit, and pre-push hooks never ran, phases never advanced,
and the next push was refused with no hint. `session_logs/hooks-errors.log`
was tracked in `ai-state` with no cap; in this repository it held 3513 lines,
about 3200 written by `tests/test_hook_gates.py` running hook scripts with
`REPO_ROOT` pointed at the live checkout. A chained `git commit … && git push`
was refused whole because the push gate evaluates HEAD before the commit
exists, and nothing said so.

## Work Log

- Delegated implementation to `coder` with the plan as the contract. It added
  `configure_outer_hooks_path()` called from `restore_root_adapters()`, the
  nested `.gitignore` seed and `untrack_error_log()`, the session-start
  warning, the push-gate prefix, the commit-skill sentence, validator
  assertions, symlink-based `REPO_ROOT` isolation for hook tests, a
  session-scoped leak guard in `tests/conftest.py`, and doc updates. It also
  changed two hard-coded assertions in `tests/test_install_bootstrap.py` that
  expected the error log to show as modified; the new untracking makes that
  status empty. Accepted as a necessary consequence.
- Regenerated targets and installed locally. `validate_targets.py` failed for
  two real reasons the coder's report had folded into "stale generated
  copies": the new error-log harness compared the stray log's content for
  byte equality although `warn` appends to that same file in local-only mode,
  and the post-start assertions still required the removed hooksPath block.
  Fixed both in the validator directly.
- Review round one (`code`, `architecture`, `security`, `tests`, `ponytail`)
  returned one CRITICAL, one MAJOR, two MINOR, each confirmed by execution:
  the leak guard ignored the absent-at-start, present-at-end case; the
  overwrite-with-warning branch had no test; the threat-model comment did not
  state the fixed-literal invariant; `core.hooksPath` being shared across
  worktrees was not noted. Second coder pass fixed all four with
  failure-before, pass-after proof.
- Review round two returned one CRITICAL and one MAJOR, both the same defect:
  the coder had added a second post-start check in a different validator
  function matching the bare word `core.hooksPath`, which the new post-start
  comment legitimately contains. Deleted the duplicate; the correctly scoped
  check in `validate_devcontainer_and_installer` remains.
- Final audit swept README, docs, root guidance, shared policies, agent
  prompts, and skills for claims touched by both phases. One stale line in
  `docs/smoke-tests.md` said post-start sets `core.hooksPath` itself; fixed.

## Design Decisions

- The hooks path is set inside `restore_root_adapters()`, which every restoring
  path shares, so `setup`, `pull`, and a fresh `checkpoint` all activate the
  hooks. The written value is a fixed literal; nothing from the nested
  checkout is interpolated, so a hostile `ai-state` remote can only affect
  whether the write happens, never where it points. This is the one write
  `state-sync.sh` makes to the outer repository outside `.claude/`.
- A different pre-existing value is overwritten with a warning naming the old
  one. `core.hooksPath` is repository-wide config shared by all worktrees, so
  the warning applies to sibling worktrees too. Recorded in the function
  comment.
- `hooks-errors.log` is gitignored and untracked, never deleted; no rotation
  or cap, because it is local. `hooks-bypass.log` stays tracked because the
  acknowledgement gate reads it. The `merge=union` attribute for
  `session_logs/*.log` is unchanged; it still serves the bypass ledger.
- The push-gate prefix appears only on a genuine denial whose command also
  contains a `git commit`. What is evaluated is unchanged.
- Test isolation uses a symlinked scripts directory under `tmp_path` rather
  than copying scripts, because the hook scripts derive `REPO_ROOT` from their
  own logical path with `pwd`, never `pwd -P`.

## Stale-claims surfaces checked

- `README.md` — consumer install section gained the prerequisites list in
  Phase 1; "Changing dev machines" paragraph updated in this phase to say
  `setup` activates the Git hooks; hooks section unchanged and accurate
  (prompt-time `push` remains by decision).
- `docs/runtime-checks.md` — `UNVERIFIED` semantics, pytest not-applicable
  rule, missing-tool message, nested-repository diagnostic wording (Phase 1);
  hooks-path ownership paragraph, local-only error log, separate-commands rule
  (this phase). All current.
- `docs/architecture.md` — `UNVERIFIED` paragraph (Phase 1); hook-error log
  local-only note and state-sync `setup` bullet (this phase). Current.
- `docs/smoke-tests.md` — one stale line said `post-start.sh` sets
  `core.hooksPath` before `pull`; corrected in this phase. Installer line
  still accurate.
- `shared/skills/commit/SKILL.md` — Phase 5 gained the separate-commands rule.
  Current.
- `shared/policies/workflow.instructions.md`, `quality-and-testing.instructions.md`
  — searched for `hooksPath`, `hooks-errors.log`, `UNVERIFIED`; the existing
  statements (errors logged to that path; `UNVERIFIED` blocks closeout) remain
  true. No change.
- `shared/agents/*/prompt.md`, `CLAUDE.md`, `AGENTS.md` — searched for the
  same terms plus the checkpoint remediation command; the orchestrator prompt
  already names the `git -C .claude` form. No change.
- `shared/devcontainer/post-start.sh` — comment rewritten to name
  `configure_outer_hooks_path` as the owner.
- `scripts/validate_targets.py` — assertions now match: state-sync carries the
  hooks-path configuration and the error-log seed; post-start does not set the
  path itself; setup precedes pull.
- `.claude/explorations/`, dated plans, and earlier session logs — left as
  historical records.
- Runtime mirrors `.claude/` and `dist/multi-agent/` — regenerated and
  self-installed after every source change; `validate_targets.py` passes on
  the final tree.

## [LEARN] Entries

- [LEARN:testing] Hook scripts derive `REPO_ROOT` from their own path, so
  tests that run them in place from `shared/hooks/scripts` log into the live
  `.claude/session_logs/hooks-errors.log`. Symlinking the scripts directory
  under `tmp_path` keeps bash's logical `$0` under `tmp_path` (the scripts use
  `pwd`, never `pwd -P`), isolating them without copying. Guard the live log
  with a session fixture that also fails on absent-at-start, present-at-end.
- [LEARN:quality] Do not assert byte-identical content on a file the script
  under test also writes; `warn` appends to `hooks-errors.log`, so the
  validator's equality check failed on correct behaviour. Assert a prefix or a
  tracked-state property instead.
- [LEARN:review] Two validator functions asserting one invariant with
  different literals drift: a bare-word `core.hooksPath` check matched the very
  comment that explained the removal. One owner per invariant, and match the
  invocation, not the word.
- [LEARN:workflow] When a coder attributes the only validator failure to
  "stale generated copies", regenerate and rerun before believing it. Twice in
  one phase the regenerated tree still failed for real reasons the report had
  folded into that explanation.

## Verification Results

Final state, with targets regenerated and locally self-installed beforehand:

```text
uv run pytest tests/ -q --tb=short                       1480 passed
.claude/session_logs/hooks-errors.log before / after     3582 / 3582 lines
uv run mypy shared scripts tests                         no issues in 29 source files
uv run ruff check shared scripts tests                   All checks passed
uv run ruff format --check shared scripts tests          29 files already formatted
uv run python scripts/generate_targets.py --all          regenerated
uv run python scripts/install_bootstrap.py . --allow-self --local-only   installed
uv run python scripts/validate_targets.py                exit 0, no FAIL lines
uv run python scripts/check_runtime.py                   all PASS
uv run python .claude/scripts/verify.py fast             PASS
git config --get core.hooksPath (this repository)        .claude/hooks/git-hooks
review round 1                                            1 CRITICAL, 1 MAJOR, 2 MINOR, all fixed
review round 2                                            1 CRITICAL, 1 MAJOR (one duplicate check), fixed
```

Receipts: `.claude/quality_reports/verification-phase-2026-09-11_phase-2-hooks-path-log-and-gate-hint.json`
and `.claude/quality_reports/verification-closeout-2026-09-11_phase-2-hooks-path-log-and-gate-hint.json`,
findings at `.claude/quality_reports/findings-2026-09-11_phase-2-hooks-path-log-and-gate-hint.json`.

## Open Questions / Next Steps

1. This repository's own nested repository still tracks
   `session_logs/hooks-errors.log` until the next `state-sync.sh` checkpoint
   runs `commit_local_state`; the closeout checkpoint below untracks it
   explicitly so the completion commit reflects the final state.
2. Whether `Failed to spawn` detection in the verifier should be narrowed to
   `rc == 2` remains open from Phase 1; it fails closed either way.
3. Prompt-time `state-sync.sh push` remains by decision; a later plan can
   revisit it.
