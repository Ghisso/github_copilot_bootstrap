# Session: Backlog follow-ups — Phase H, guard shell scanner

**Date:** 2026-10-21
**Plan:** .claude/plans/2026-10-21_phase-H-guard-shell-scanner.md
**Parent plan:** .claude/plans/backlog-followups.md
**Status:** IN-PROGRESS

## Goal

Replace `shlex` in the file-protection guard with a scanner that reads
shell text as Bash does, so comments, blank lines, line-end operators, and
quoted or escaped operators no longer hide or split commands (BF-H1),
prove no decision loosened (BF-H2), and document it (BF-H3).

## Task Tracking

- [x] PRE-FLIGHT: Phase G committed (`abdefa1`) and pushed; the big plan
  reopened with Phases H, I, and J after the user's decisions
  (big plan "Decisions recorded" item 7). No planner: the plan was drafted
  by the orchestrator and challenged by a devil's-advocate subagent.
- [ ] IMPLEMENT/VERIFY/REVIEW/CLOSEOUT — repeat until verification and review pass
- [ ] COMMIT
- [ ] PUSH

## Work Log

- **Reopen** - The user asked for a plan to fix the guard defect found
  after Phase G and to do the two Phase G follow-ups. Probes of the
  classifier (command text only, never run) confirmed R1 and, after the
  devil's-advocate review, R5 to R8. Findings:
  `.claude/quality_reports/2026-10-21_backlog-followups-reopen-findings.md`.
  The user chose two code phases, a dedicated Bash scanner, and to keep
  secret-file Bash reads as a follow-up.

## [LEARN] Entries

To be written at closeout.

## Verification

To be written at closeout.

## Open Questions / Next Steps

- Phase I and Phase J follow.
