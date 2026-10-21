# Session: Backlog follow-ups — Phase I, guard substitutions and restore messages

**Date:** 2026-10-21
**Plan:** .claude/plans/2026-10-21_phase-I-guard-substitutions-and-restore-messages.md
**Parent plan:** .claude/plans/backlog-followups.md
**Status:** IN-PROGRESS

## Goal

Close the write paths the file-protection guard still misses after Phase H
(command substitution in double quotes and backticks, grouped operators,
inline `sed` writes, the `cd`-folder gap, and the R9 and R10 forms), close
the Phase H loosening exception, and make the OpenWiki restore messages say
the user runs them (BF-I1 to BF-I7).

## Task Tracking

- [x] PRE-FLIGHT: Phase H committed (`b0dc4c3`) and pushed; the commit hook
  advanced `current_phase` to this phase and set it `in-progress`. The user
  asked to continue to the end of the big plan. No planner.
- [ ] IMPLEMENT/VERIFY/REVIEW/CLOSEOUT — repeat until verification and review pass
- [ ] COMMIT
- [ ] PUSH

## Work Log

- **Start** - Applying the Phase H lesson: the coder runs a sweep of every
  new construct under plain Bash, `bash --posix`, and dash before review,
  and adds each new shape class to the differential generators first.

## [LEARN] Entries

To be written at closeout.

## Verification

To be written at closeout.

## Open Questions / Next Steps

- Phase J (final knowledge refresh) follows.
