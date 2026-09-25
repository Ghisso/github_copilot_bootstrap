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

## [LEARN] Entries

Pending.

## Verification

Pending.

## Open Questions / Next Steps

- Integrate both coders' work, run the Phase C verification block and the
  full phase verifier, then review with `code`, `architecture`, `security`,
  `tests`, `ponytail`.
