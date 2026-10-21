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
- **Step 1, audit** - see the next section. A documenter added the README
  upgrade note; the orchestrator corrected one `MEMORY.md` entry and the
  project-context status paragraph.
- **Step 2, refresh** - one managed `update` run
  (`898c38a6-7dd2-4cc2-b43c-a50054e9a11d`) after all source edits.
  `openwiki_begin` reported 4 stale claims on 3 pages. Planned 4 pages:
  `architecture/agents-and-skills.md` (style pass: the "Reading outside
  the diff" bullet and five other long sentences split, no fact or claim
  changed); `architecture/hooks-and-guardrails.md` (the `protect-files`
  bullet rewritten in short sentences with the scanner, fail-closed rules,
  4-second alarm, and the Git message exemption; the OpenWiki restore
  messages; the new test file; one stale claim revised with new evidence,
  one confirmed, three new claims); `operations/deterministic-verification.md`
  (the managed-block message gives the fix; stale claim revised, one new
  claim); `quickstart.md` (a routing row for guard denials; stale claim
  evidence moved to `docs/target-mapping.md#L88-L141`). `openwiki_finish`
  returned `complete`. No link stamp, no root-absolute link, `AGENTS.md`
  and `CLAUDE.md` unchanged, `openwiki/.run.json` absent.
- **Verify** - regenerated, self-installed; `verify.py phase` PASS (4932
  passed, 1 skipped). Fresh reviewer requested with the user's lighter
  bar.

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

## Requirement Evidence (BF-H1 to BF-J2)

Phase commits after the reopen: H `b0dc4c3`, I `61c30d6`, J this commit.
Each phase's own log carries its detailed evidence.

| ID | Outcome | Evidence |
| --- | --- | --- |
| BF-H1 | Done | `b0dc4c3`; `2026-10-21_backlog-followups-phase-h.md`; Bash-reading checks and the three-reading sweep |
| BF-H2 | Done, with the accepted exception (big plan item 8) | Phase H differential; the exception closed in Phase I |
| BF-H3 | Done | `docs/runtime-checks.md`, `docs/smoke-tests.md`, `docs/target-mapping.md` |
| BF-I1 to BF-I4 | Done | `61c30d6`; `2026-10-21_backlog-followups-phase-i.md`; `tests/test_protect_files_substitutions.py` |
| BF-I5 | Done | restore messages in `verify.py` and `openwiki-guard.py`, failing-first assertions |
| BF-I6 | Done | differential against Phase H: 0 under-protected; all 261 original exception commands blocked |
| BF-I7 | Done, with listed gaps | closed forms in Phase I's log; the rest listed in `docs/runtime-checks.md` |
| BF-J1 | Done | "Stale-claims surfaces checked" above; OpenWiki run `898c38a6-...` `complete`; `test ! -e openwiki/.run.json` |
| BF-J2 | Done | both named bullets split, plus five more sentences on the agents page and two on the hooks page; reviewer read of the page diff |

## [LEARN] Entries

- No new lessons: the Phase H and I lessons (systematic sweeps, the
  review acceptance bar, guessed expansion values, never editing existing
  test inputs) are already in `MEMORY.md`.

## Verification

To be written at closeout.

## Open Questions / Next Steps

- After closeout, the big plan is complete. Opening a pull request from
  `backlog-followups_implementation` to `dev` is the user's decision.
