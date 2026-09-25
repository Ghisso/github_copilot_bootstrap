# Session: Sidecar Phase C — install and provider bridges

**Date:** 2026-09-25
**Plan:** `.claude/plans/2026-09-24_phase-C-sidecar-install-and-provider-bridges.md`
**Status:** IN-PROGRESS

## Goal

Add `--mode`, mode detection, preflight, the exclude block and its ignore
gate, and the apply step that executes the Phase B planner, so that first
install and rerun use one path and a sidecar consumer can never be taken
over by a plain full install.

## Work Log

- Phase C activated by the Phase B completion commit `ede3591` (pushed).
- Material-impact check: Phase B delivered the planner API this plan
  assumes (plus SKIPPED reports for read-only-folder collisions and
  `retained` stored as paths). No planner revision.
- To let two coders work in parallel, the orchestrator added to
  `scripts/sidecar_overlay.py`: `git_path(target, name)` (absolute
  `--git-path`), `sidecar_evidence(target)` (manifest file, valid or not,
  or the marker block in `info/exclude`), and an `install_sidecar(target,
  source, *, dry_run=False) -> int` stub with the final signature. Smoke
  test in a scratch repository; ruff, format, and mypy pass; the 48 planner
  tests still pass.
- Coder C1 (steps 1-2 and their tests): `--mode`, `--source` default
  `None`, the one mode-detection function, refusals, `main()` order, the
  Decision 13 warning; owns `scripts/install_bootstrap.py` and
  `tests/test_install_bootstrap.py`.
- Coder C2 (steps 3-7 and the sidecar-behavior tests): preflight, input
  gathering, exclude block and ignore gate, atomic apply, report, dry-run,
  fault points; owns `scripts/sidecar_overlay.py` and
  `tests/test_sidecar_install.py`.
- C1 result: `detect_install_mode(target, requested_mode, allow_self)` with
  helpers `_full_install_evidence`, `_sidecar_evidence` (catches
  `CalledProcessError` for non-Git targets), `_team_config_evidence`
  (reuses `tracked_generated_paths`), `_is_linked_worktree`;
  `warn_full_only_options_ignored`; `DEFAULT_SIDECAR_SOURCE`. A non-Git or
  no-commit target still falls through to today's full default. 15
  detection unit tests and 7 CLI tests; `--mode full` added to
  `test_generated_session_pull_restores_ignored_adapter_after_branch_switch`.
  `tests/test_install_bootstrap.py`: 75 passed.
- Gap the plan's 2026-09-24 review missed: `validate_state_sync()` in
  `scripts/validate_targets.py` installs into machine C, a fresh clone of a
  full consumer whose `.claude/` is not restored (tracked `.devcontainer/`,
  no bootstrap evidence). The new Decision 18 refusal correctly blocks it.
  The orchestrator added `--mode full` to that fixture call with a comment,
  matching the plan's own remedy for that scenario. No real script runs the
  installer there: `check_runtime.py`'s reinstall command uses
  `--allow-self` (full evidence), and `update_consumers.py` targets
  consumers with `.claude/.git`. Phase D must document that a fresh clone
  of a full consumer needs `bash .devcontainer/state-sync.sh setup` (or
  `--mode full`) before a plain install. Note added to Phase D step 4.
- `validate_targets.py` after the fixture fix: PASS, no `FAIL` lines.
- C2 result: `install_sidecar` apply step (preflight -> gather ->
  `plan_sidecar_reconciliation` unchanged -> apply or dry-run), gate
  function `run_ignore_gate(target, must_be_ignored, candidate_exclude_text,
  *, dry_run)`, fault points `after_exclude_write`, `mid_unit_swap`,
  `before_manifest_write`; 36 tests in `tests/test_sidecar_install.py`, 3
  of them through the CLI. No planner change. C2 fixed one defect of its
  own before hand-over: `git rev-parse --git-path info/exclude` resolves a
  symlinked `info/exclude` to its target, so the symlink check now builds
  the path from the verified `--git-dir`.
- Optional check (orchestrator, 2026-09-25): `git clone` of the Phase A
  fixture into the scratch folder (committed team files only, so none of
  the old marker files or exclude block), then
  `install_bootstrap.py <clone> --mode sidecar`: `installed 10`; `git
  status --porcelain --untracked-files=all` empty before and after; no
  `core.hooksPath`; the exclude block lists exactly the 10 units; manifest
  in the Git directory; staging empty. A plain rerun with no `--mode`
  detected sidecar mode, reported `unchanged 10`, and left the exclude file
  and manifest byte-identical. Native checks in the clone: Claude Code
  2.1.226 (`--tools ""`, zero tool uses) listed `debug-investigator`,
  `humanize`, `ponytail`, `ponytail-review` in the init `skills` and quoted
  the Claude bridge line; Codex 0.147.0 `debug prompt-input` listed the
  four skills at `.agents/skills/<skill>/SKILL.md` and no `.claude/skills/`
  path. This also closes Phase A's residual frontmatter risk for these two
  clients: the real skills, with `visibility`, `license`, and
  `argument-hint`, load.

## [LEARN] Entries

Pending.

## Verification

Pending.

## Open Questions / Next Steps

- Integrate both coders' work, run the Phase C verification block and the
  full phase verifier, then review with `code`, `architecture`, `security`,
  `tests`, `ponytail`.
