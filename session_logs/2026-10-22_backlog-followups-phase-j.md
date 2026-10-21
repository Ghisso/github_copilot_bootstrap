# Session: Backlog follow-ups — Phase J, guard hardening knowledge refresh

**Date:** 2026-10-22
**Plan:** .claude/plans/2026-10-21_phase-J-guard-hardening-knowledge-refresh.md
**Parent plan:** .claude/plans/backlog-followups.md
**Status:** COMPLETED

## Goal

Audit live advice for statements Phases H and I made false (BF-J1), refresh
the OpenWiki pages those phases made stale, and shorten long sentences in
the pages the refresh rewrites (BF-J2).

## Task Tracking

- [x] PRE-FLIGHT: Phase I committed (`61c30d6`) and pushed; the commit hook
  advanced `current_phase` to this phase. The user asked to continue to the
  end of the big plan. No planner.
- [x] IMPLEMENT/VERIFY/REVIEW/CLOSEOUT — repeat until verification and review pass
- [x] COMMIT
- [x] PUSH

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
- **Review round 1** - Gate Result FAIL, 1 major and 4 minor, all
  documentation. Fixed by the orchestrator: the `MEMORY.md` fail-closed
  clause (major) and two older `MEMORY.md` entries; the README note now
  says these commands are denied with no approval prompt (run them in your
  own shell instead of "approve it yourself"); the project-context
  paragraph split so "Pinned versions after the plan" is clear. For BF-J2
  a second scoped OpenWiki `update` run
  (`ae57b8ff-894c-443f-9cb9-f38939395f8a`, 1 page) restored the full
  `HOOK_CONFIGS` and `CONTROL_PLANE_DIRS` lists and the modelled mutators
  on `architecture/hooks-and-guardrails.md`, split the scanner paragraph
  into short paragraphs, and split the long `openwiki-guard` and
  `git-protection` sentences; no claim changed; `openwiki_finish`
  returned `complete`; no stamp, adapters unchanged, no `.run.json`.

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
  corrected in place, and after review round 1 its "only malformed syntax
  fails closed" clause was corrected too (the guard also fails closed on a
  variable assigned twice, `shopt -s dotglob`, a `case` inside `$( )`, and
  text too complex to read). Review round 1 also found two older entries
  the first pass missed: the one saying variable-built targets are only
  flagged uncertain and loops and functions cannot be modelled, and the one
  saying the guard never parses `bash -c` script content. Both corrected in
  place (`bash -c`, `sh -c`, and `eval` are read since Phase I; other
  interpreters' `-c` text is only literal-scanned, checked against the
  guard). The `protect-files.sh` entry corrected in Phase H still holds.
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

[LEARN] none - no new lessons this session

The Phase H and I lessons (systematic sweeps, the review acceptance bar,
guessed expansion values, never editing existing test inputs) are already
in `MEMORY.md`.

## Review

- Fresh reviewer, six profiles, the user's lighter bar. Round 1: Gate
  Result FAIL, 1 major (a `MEMORY.md` clause still said only malformed
  syntax fails closed) and 4 minor (two older `MEMORY.md` entries, the
  README "approve it yourself" wording, the project-context paragraph, and
  BF-J2 left partly met on the hooks page); all fixed (see Work Log).
  Round 2: Gate Result PASS, 0 critical, 0 major, 1 minor (the hooks page
  said "three parts" for a four-item list), fixed by a third scoped
  OpenWiki `update` run (`018f99df-4278-4b0d-904f-e3f054eb4fc6`, one word,
  `openwiki_finish` complete).

## Verification

Optional items:

- optional 1: PASS
- OpenWiki completion: run `898c38a6-7dd2-4cc2-b43c-a50054e9a11d`, finish
  `complete`, 4 pages (`architecture/agents-and-skills.md`,
  `architecture/hooks-and-guardrails.md`,
  `operations/deterministic-verification.md`, `quickstart.md`); corrective
  runs `ae57b8ff-894c-443f-9cb9-f38939395f8a` and
  `018f99df-4278-4b0d-904f-e3f054eb4fc6`, each finish `complete`, 1 page
  (`architecture/hooks-and-guardrails.md`). Every page diff was read; no
  link stamp, no root-absolute link, `AGENTS.md` and `CLAUDE.md` unchanged,
  no `openwiki/.run.json`.

Required items (summary lines from `verify.py closeout`):

```text
PASS        0.3s  uv run python scripts/generate_targets.py --all
PASS       44.5s  uv run python scripts/validate_targets.py
PASS        0.8s  uv run python scripts/check_runtime.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS        0.0s  test ! -e openwiki/.run.json
PASS        0.2s  uv run python .claude/scripts/verify.py fast --format json
closeout: PASS
VFY-FRESH-001: PASS - phase evidence matches relevant state
VFY-FRESH-002: PASS - phase evidence matches governing control-plane provenance
VFY-RECEIPT-001: PASS - reused successful phase receipt
```

Findings recorded: 1 finding (0 critical, 0 major, 1 minor, fixed);
`ponytail_reviewed=true`; `gate_result=PASS`
(`.claude/quality_reports/findings-2026-10-21_phase-J-guard-hardening-knowledge-refresh.json`).

## Open Questions / Next Steps

- After closeout, the big plan is complete. Opening a pull request from
  `backlog-followups_implementation` to `dev` is the user's decision.
- Recorded follow-ups: split or shrink `protect-files.py`; the forms in
  the not-yet-checked list of `docs/runtime-checks.md`; the policy choice
  on Bash reads of secret-shaped files.
