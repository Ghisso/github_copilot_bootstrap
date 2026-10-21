# Session: Backlog follow-ups — Phase D, agent definition protection

**Date:** 2026-10-21
**Plan:** .claude/plans/2026-10-20_phase-D-agent-definition-protection.md
**Parent plan:** .claude/plans/backlog-followups.md
**Status:** IN-PROGRESS

## Goal

Protect agent definition folders (BF-D1), protect the hook and agent
folders as whole folders, including unmodelled Git subcommands under
`git -C` (BF-D2), protect in-repository `*.code-workspace` files (BF-D3),
drop the dead Codex agent `sandbox_mode` key (BF-D4), and document the
behavior, the recovery path, and the remaining gaps (BF-D5).

## Task Tracking

- [x] PRE-FLIGHT: Phase C committed (`69bdb64`) and pushed; Phase D is the
  current phase. Phase C outcomes do not affect Phase D; no planner.
- [x] IMPLEMENT/VERIFY/REVIEW — six review rounds (FAIL, FAIL, FAIL, FAIL,
  PASS with one MINOR, PASS clean); every MAJOR was a decision that
  became looser than before the plan, each fixed and pinned by tests.
- [x] CLOSEOUT: documentation, final AI state, checkpoint, staged index,
  findings, phase receipt, closeout dry run, checkpoint, closeout receipt.
- [ ] COMMIT
- [ ] PUSH

## Work Log

- **Earlier (during Phase C's wait)** - Steps 1-2 were implemented by a
  coder in a detached scratch worktree at `06eb8e0` (no effect on this
  checkout). Negative control on the unchanged code: all new whole-folder
  (84), interpreter `rmtree` (14), `git -C`/`cd` (12), agent-file and
  workspace-file (40), bash-guard chain (10), Antigravity bridge (10),
  literal must-match (6), and in-repository name (7) cases failed; the
  `sandbox_mode` override case failed; the still-allowed, read, foreign
  checkout, and near-miss cases passed. Worktree checks passed, including
  the guard tests under Python 3.9.0.
- **Start** - Applied the worktree diff here (`git apply --check` clean;
  6 files) and removed the worktree. Documenter wrote step 3 (target
  mapping parity section and follow-ups, smoke tests, runtime checks,
  README, File Protection Rules, commit skill `--body-file`). Regenerated
  and self-installed; `verify.py phase` PASS (3074 passed). Live check: the
  installed guard denies `ls <repo>/.claude/agents` in this session.
- **Review round 1: FAIL** - MAJOR (security): resolving unmodelled Git
  tokens against the `-C`/`cd` directory let an absolute-path
  `git -C .claude restore ...` ask instead of deny. MAJOR (docs): `rm -rf`,
  `mv`, `ln -s` on a whole folder were documented as denied everywhere but
  ask on Claude Code and Copilot. MINORs: no mixed-case workspace-name test;
  a confusing colon in the commit skill. Fixed: offset resolution only when
  no token is visible from the repository root (probe: deny at HEAD, ask
  before the fix, deny after); docs split the edit sentence from the
  "merely names" sentence; `Team.CODE-WORKSPACE` rows (negative controls:
  13 failures without `.lower()`, 2 without `re.IGNORECASE`); skill colon.
- **Review round 2: FAIL** - MAJOR: across segments of one command line a
  confirmed hit beat an uncertain deny (same-file two-segment forms asked;
  deny at HEAD). A plain reorder in `emit()` broke 44 existing redirect
  tests, so an interim same-name exemption was tried; the reviewer showed it
  still loosened. Final single rule (big-plan "Decisions recorded" item 6):
  `without_redirects()`/`is_redirect()` keep redirect targets out of the
  uncertain scan (also leading redirects), and any uncertain hit denies on
  every client.
- **Review round 3: FAIL** - MAJOR: a confirmed hook-config hit ranked
  above the secret-file rule, so `cp .env .claude/agents/x.md` asked (deny
  at HEAD). MINORs: leading redirect, three predicate copies. Fixed:
  `emit()` checks secret hits first; leading redirects drop correctly; one
  `is_redirect` helper. Required a systematic HEAD-versus-now battery.
- **Review round 4: FAIL** - MAJOR (the battery's blind spot): a
  secret-shaped name inside a newly protected folder (`.claude/agents/.env`)
  was classified as a hook config, so edits asked and Copilot reads were
  allowed (deny at HEAD). Fixed: `protected()` tests secret-shaped names
  first, in both the lexical and the symlink-resolved path form. Docs: the
  one-off battery counts moved out of the docs into this log; Phase D's
  Step 1 note points to decision 6.
- **Review round 5: PASS** - one MINOR: the tightening for secret names
  inside the older hook folders was untested and undisclosed. Added
  `.claude/hooks/.env` and `.github/hooks/credentials.json` test rows
  (negative control against HEAD's guard: 18 of 58 failed, exactly the new
  rows) and the disclosure in the docs and decision 6.
- **Review round 6: PASS** - no findings, no open request.
- **No-loosening evidence (session scratch folder `phase-d/`)** - Batteries
  `battery.py`, `battery_native.py`, and `battery2.py` compare the guard as
  it was at HEAD (`git archive HEAD`) with the working tree for all four
  clients. Final extended run: shell 9,476 inputs (37,904 per-client
  comparisons), native 5,685 payloads (22,740), Antigravity bridge 1,308 —
  0 defects (no deny that became ask or allow, no ask that became allow),
  0 errors. Changes versus HEAD: shell allow→ask 1,922, allow→deny 3,882,
  ask→deny 2,770, unchanged 29,330; native allow→ask 488, allow→deny 4,112,
  ask→deny 822, unchanged 17,318; bridge allow→deny 112, unchanged 1,196.
  Allow→ask/deny is new coverage; ask→deny is tightening. Controls: the
  same battery against the previous rounds' guards found 272 (round 4) and
  9,768 (round 5) defects, so it detects the classes the reviews found.
  Result files: `round6-shell-battery.txt`, `round6-*-results.tsv`,
  `round6-summary.txt`, `round6-changes.txt`.
- **Deviation to report at the phase boundary** - Decision 6 departs from
  the plan's "the decision rule in `emit()` stays as it is": it never
  loosens a decision, and it tightens several existing Claude Code and
  Copilot asks to denies (for example `rm .env .mcp.json`,
  `.claude/hooks/.env`, `git restore` of a protected config chained with
  `rm` of it, and a settings edit whose heredoc body names a hook script).

## [LEARN] Entries

- [LEARN:security] When a guard change adds protected names or new ways to
  reach a confirmed hit, prove "no decision loosened" with a generated
  battery that runs the pre-change guard and the new guard on every target
  kind (including secret names inside each newly protected folder and
  symlinks), every command shape (redirects, heredocs, interpreters, Git
  `-C`/`cd`, multi-segment `&&`), native and read-tool payloads, and every
  client. Hand-picked probes missed four loosenings in a row in the
  2026-10-21 Phase D review; a control run against the previous guard shows
  the battery detects the class.
- [LEARN:workflow] While a phase waits for a user decision, the next
  phase's code can be prepared in a detached worktree in the scratch folder
  (`git worktree add --detach <scratch> HEAD`), then applied with
  `git apply` once the current phase commits. Plain `uv run` there lacks the
  tools; use `VIRTUAL_ENV=<repo>/.venv uv run --active ...`.

## Verification

```text
# verify closeout --format text summary lines
```

- optional 1: NOT RUN — Claude Code interactive approval prompt for an
  agent-file edit needs an attended session (the user was away); the hook
  decision is covered by tests and the live `ls` denial above.
- optional 2: NOT RUN — Codex native session not available here.
- optional 3: NOT RUN — GitHub Copilot in VS Code (Local harness) session
  not available here.
- optional 4: NOT RUN — no disposable Antigravity install with a native
  session available here.

## Open Questions / Next Steps

- Phase E follows: Ponytail 5 partial adoption (step 1 evidence ready in
  the scratch folder).
