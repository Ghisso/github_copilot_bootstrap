# Session: Backlog follow-ups — Phase A, status and wording cleanup

**Date:** 2026-10-20
**Plan:** .claude/plans/2026-10-20_phase-A-status-and-wording-cleanup.md
**Parent plan:** .claude/plans/backlog-followups.md
**Status:** IN-PROGRESS

## Goal

Close the stale AI-state statuses (BF-A1), use one OpenWiki sentence in the
root guidance (BF-A2), remove an undefined term and the brief's em dashes
(BF-A3), correct the project-name advice in three skills (BF-A4), replace
the `verify closeout` traceback with a clear message (BF-A5), record an
outcome for every 2026-09-21 OpenWiki follow-up (BF-A6), and restore the
vendored Ponytail `LICENSE` verbatim (BF-A7).

## Task Tracking

- [x] PRE-FLIGHT: `dev` clean and equal to `origin/dev` (`f964551`); big plan
  approved by the user on 2026-10-20 with all four recommended decisions
  (behavioral retry parked; memory archive in `.claude/explorations/`;
  `ponytail-review` complexity-only; scope additions approved). The user
  then asked to continue to the end of the big plan while away.
- [x] BRANCH: `backlog-followups_implementation` created from `dev`; hooks
  set the big plan `in-progress` (`started_at` 2026-10-20T14:54:11Z) and
  Phase A `in-progress`.
- [x] PLAN WHEN NEEDED: approved plan is implementation-ready; no planner.
- [ ] IMPLEMENT/VERIFY/REVIEW/CLOSEOUT — repeat until verification and review pass
- [ ] COMMIT
- [ ] PUSH

## Work Log

- **14:55** - Steps 1 and 7 (orchestrator, nested AI state): set the two
  July big plans and their phase files to `complete` with Resolution notes
  (PR #7 `767fefc`, PR #8 `ab87dd7`; commits `82e9fbe`, `18e0a08`; score
  gate removed in `2af3df7`), ticked the pilot plan's Phase D with its
  completion pointer, and replaced only the status lines of the 2026-10-02
  sidecar review, the 2026-10-02 engineering exploration README (plus its
  Plan 2 link line), its pilot proposal, and the 2026-09-21 OpenWiki
  follow-ups. The two 2026-07-18 session logs are unchanged.
  `validate_plan_frontmatter.py` passes.
- **14:58** - Extracted upstream Ponytail `LICENSE` from the planning clone
  (`v4.8.4` = `bc9ee949…`, `v5.3.2` = `16352ac2…`): sha256 `fb1bc690…`; the
  local copy differs by `Dietrich Gebert` versus `DietrichGebert` and one
  trailing blank line.
- **15:00** - Delegated steps 2 and 6 (tests and `verify.py`) and steps 3,
  4, 5, and 8 (generator, root guidance, policy, brief, three skills,
  license and pin) to two coders on disjoint files.

## [LEARN] Entries

To be written at closeout.

## Verification

To be written at closeout.

## Open Questions / Next Steps

- Phase B follows: nested `.gitignore` and `.gitattributes` preservation.
