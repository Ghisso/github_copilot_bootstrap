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

## [LEARN] Entries

## Verification

## Documentation

## Open Questions / Next Steps
