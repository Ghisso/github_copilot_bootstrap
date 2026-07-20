# Session: Preserve consumer memory

**Date:** 2026-07-18
**Plan:** .claude/plans/2026-07-18_phase-A-preserve-consumer-memory.md
**Status:** BLOCKED

## Goal

Prevent bootstrap refreshes from replacing consumer-accumulated
`.claude/MEMORY.md` content with the generated blank seed.

## Work Log

- **05:38** - Reproduced data loss for both git-backed reinstall and legacy
  pre-git migration. In both cases the resulting hash matched the blank seed.
- **05:45** - User authorized a fix. Traced the shared copy boundary and chose
  an exact-path preservation rule rather than a backup/restore subsystem.
- **05:50** - Implemented preservation, added both regression cases, and
  documented fresh-install versus refresh behavior.
- **05:50** - Full validator, Ruff, mypy, runtime checks, plan validation, and
  disposable end-to-end probes passed.
- **05:51** - Moved the isolated four-file fix from `dev` to
  `preserve-consumer-memory_implementation`, reran branch-scoped verification,
  and staged the exact patch.
- **05:52** - Correctness, configuration, documentation, security, and
  Ponytail review found no surviving issues. Formal score remained 85 because
  this authoring repository still has no pytest collection.

## [LEARN] Entries

- [LEARN:installer] Generated seeds for consumer-owned mutable state must be
  copy-if-absent. Migration or git history cannot protect data that the
  installer overwrites before state synchronization begins.

## Verification Results

```bash
uv run python scripts/generate_targets.py --all
# PASS

uv run python scripts/validate_targets.py
# PASS generated target is structurally valid

uv run python scripts/check_runtime.py
# PASS; optional gh warning only

uv run ruff check scripts/install_bootstrap.py scripts/validate_targets.py
# All checks passed

uv run mypy scripts --ignore-missing-imports --explicit-package-bases
# Success: no issues found in 6 source files
```

Disposable end-to-end probes confirmed:

- fresh install hash equals the generated seed hash;
- git-backed reinstall retains the exact pre-refresh hash and sentinel;
- legacy pre-git refresh retains the exact pre-refresh hash and sentinel;
- the legacy migration commit contains the original consumer memory.

## Review

- Zero critical, major, minor, or Ponytail findings.
- Report:
  `.claude/quality_reports/findings-20260718T055154Z.json`

## Score: 85 — BLOCKED

- Report: `.claude/quality_reports/score-20260718T055154Z.json`
- Ruff and mypy passed.
- The scorer deducted 15 because pytest collected no tests; the repository's
  executable regression suite is `scripts/validate_targets.py`, which passed.
- No commit was made.
