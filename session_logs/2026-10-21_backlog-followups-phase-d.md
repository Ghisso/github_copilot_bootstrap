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
- [ ] IMPLEMENT/VERIFY/REVIEW/CLOSEOUT — repeat until verification and review pass
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
  checkout, and near-miss cases passed. Final worktree checks: generate +
  validate PASS, 1138 targeted tests and 579 adjacent tests passed, ruff,
  format, mypy clean, `protect-files.py` parses and its tests pass under
  Python 3.9.0. Design choice accepted: unmodelled Git subcommand tokens are
  also resolved against the `-C`/`cd` directory as confirmed targets, and
  the existing repository-root uncertain (deny) rule stays, so no existing
  client decision is loosened.
- **Now** - Applied the worktree diff here (`git apply --check` clean;
  6 files) and removed the worktree. Delegated step 3 (docs) to a
  documenter.
- **Later** - Docs done (target-mapping parity section and follow-ups,
  smoke tests, runtime checks, README, File Protection Rules, commit skill
  `--body-file`). Regenerated and self-installed; `verify.py phase`: PASS
  (3074 passed). Live check: the installed guard now denies
  `ls <repo>/.claude/agents` in this session.
- **Later** - Review round 1: `FAIL`. MAJOR (security): resolving
  unmodelled Git tokens against the `-C`/`cd` directory also adds tokens
  that the repository-root rule already denies, and confirmed hits win in
  `emit()`, so an absolute-path `git -C .claude restore ...` became ask
  instead of deny on Claude Code and Copilot. MAJOR (documentation): the
  docs said `rm -rf`, `mv`, `ln -s` on a whole folder are denied on all four
  clients, but they ask on Claude Code and Copilot. MINORs: no mixed-case
  workspace-name test; a confusing colon in the commit skill's PR example.
  Sent the code fix to the coder and the docs fix to the documenter in
  parallel (disjoint files).
- **Later** - Documenter: split the docs' edit sentence (agent edits and
  `rm -rf`/`mv`/`ln -s` on a whole folder ask on Claude Code and Copilot,
  deny on Codex and Antigravity) from the "merely names" sentence
  (`ls`/`find`/`diff`/`cmp` denied everywhere) in runtime checks, smoke
  tests, README, and target mapping; named all four clients for the
  `git -C`/`cd` forms; fixed the commit skill colon. Generate + validate
  PASS.
- **Later** - Coder: offset-root resolution now runs only when no token of
  that Git command is already protected from the repository root (stricter
  than the reviewer's per-token suggestion, which would still soften a
  mixed-token command). Probe of `git -C .claude restore <abs>/.claude/hooks/...`:
  deny on all four clients at HEAD, ask on Claude Code and Copilot before
  the fix, deny on all four after. New deny-everywhere test for five Git
  forms (6 of its rows failed before the fix); `Team.CODE-WORKSPACE` added to
  the scoping and per-client tests (negative controls without `.lower()`: 13
  failures; without `re.IGNORECASE`: 2). 1179 targeted tests pass.
- **Orchestrator decision (within approved goals)** - The coder also found
  that across segments of one command line a confirmed hit beats an
  uncertain deny, so `git restore .claude/hooks/x && git -C .claude restore
  hooks/y` and `git restore .claude/hooks/x && rm -rf .claude/agents` would
  go from deny at HEAD to ask, which the plan forbids. Chosen fix: `emit()`
  decides on uncertain hits before confirmed ones (fail closed). Its only
  other effect is tightening some pre-existing mixed commands from ask to
  deny (for example `git restore` of a protected config chained with `rm`
  of it). Sent to the coder with deny-everywhere tests.

## [LEARN] Entries

To be written at closeout.

## Verification

To be written at closeout.

## Open Questions / Next Steps

- Phase E follows: Ponytail 5 partial adoption (step 1 evidence ready).
