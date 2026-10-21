# Session: Backlog follow-ups — Phase J, guard hardening knowledge refresh

**Date:** 2026-10-22
**Plan:** .claude/plans/2026-10-21_phase-J-guard-hardening-knowledge-refresh.md
**Parent plan:** .claude/plans/backlog-followups.md
**Status:** IN-PROGRESS

## Goal

Audit live advice for statements Phases H and I made false (BF-J1), refresh
the OpenWiki pages those phases made stale, and shorten long sentences in
the pages the refresh rewrites (BF-J2).

## Task Tracking

- [x] PRE-FLIGHT: Phase I committed (`61c30d6`) and pushed; the commit hook
  advanced `current_phase` to this phase. The user asked to continue to the
  end of the big plan. No planner.
- [ ] IMPLEMENT/VERIFY/REVIEW/CLOSEOUT — repeat until verification and review pass
- [ ] COMMIT
- [ ] PUSH

## Work Log

- **Start** - Stale-claims audit of Phases H and I first, then one
  managed OpenWiki `update` refresh.

## Stale-claims surfaces checked

Audit of Phases H and I (how the guard reads shell text, which write
forms it catches, and how the OpenWiki restore runs), by search and
reading. Every live-advice surface and its outcome:

- Root `CLAUDE.md` and `AGENTS.md`: no guard-parsing or restore claim.
- `README.md`: the upgrade-notes section ("Upgrading a consumer with active
  work") had no note for the Phase H and I behavior changes; a documenter
  added one ("Shell parsing in the file-protection guard"). Its existing
  "guard also scans heredoc bodies" advice still holds (only commit-message
  heredocs are exempt).
- `docs/runtime-checks.md`, `docs/smoke-tests.md`, `docs/target-mapping.md`:
  rewritten during Phases H and I; current (the parity rows, the
  not-yet-checked list, the over-blocks, and the restore row's "Ask the user
  to run").
- `docs/architecture.md`: the restore line (~206) already says ask the
  user; the scoping paragraph (~398) is unchanged by H and I. No change.
- `shared/policies/workflow.instructions.md`: the `--findings-json -`
  advice (~194) and the file route for findings that name a protected path
  still hold (a quoted heredoc outside a commit message is still scanned).
  No change.
- `shared/skills/knowledge-refresh/SKILL.md` (restore by the user, ~88-93)
  and `shared/skills/commit/SKILL.md` (inline PR bodies scanned, ~112): still
  true. No change.
- Other skills, `shared/agents`, `shared/templates`, `shared/review-profiles`,
  state READMEs: no guard-parsing claim.
- `.claude/MEMORY.md`: the `[LEARN:tooling]` entry saying the guard cannot
  model `for`/`while`/`{ }` compound commands was partly false after Phase I
  (commands after `then`, `do`, `else`, `{`, `!`, `time` are classified);
  corrected in place. The `protect-files.sh` entry corrected in Phase H
  still holds.
- `.claude/instructions/project-context.instructions.md`: the status
  paragraph named only Phases A to G; it now names the reopen (H to J), the
  scanner, the not-yet-checked list, and the split follow-up.
- Dated records (closed plans and logs, `docs/2026-*`, `docs/evidence/**`,
  dated explorations): unchanged.
- Generated `openwiki/**` pages: left to the managed refresh (step 2).

## [LEARN] Entries

To be written at closeout.

## Verification

To be written at closeout.

## Open Questions / Next Steps

- After closeout, the big plan is complete. Opening a pull request from
  `backlog-followups_implementation` to `dev` is the user's decision.
