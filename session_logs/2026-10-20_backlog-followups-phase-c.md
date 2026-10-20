# Session: Backlog follow-ups — Phase C, memory split

**Date:** 2026-10-20
**Plan:** .claude/plans/2026-10-20_phase-C-memory-split.md
**Parent plan:** .claude/plans/backlog-followups.md
**Status:** IN-PROGRESS

## Goal

Move the `MEMORY.md` entries that fail the current admission rule into a
dated archive without losing any (BF-C1, BF-C2), keep every gate, hook, and
skill working (BF-C3), keep `caveman-compress` backups where a refresh
cannot delete them (BF-C4), and mark the 2026-09-03 exploration decided
(BF-C5).

## Task Tracking

- [x] PRE-FLIGHT: Phase B committed (`06eb8e0`) and pushed; Phase C is the
  current phase. Phase B outcomes do not affect Phase C (the archive lives in
  `explorations`, already preserved); no planner.
- [ ] IMPLEMENT/VERIFY/REVIEW/CLOSEOUT — repeat until verification and review pass
- [ ] COMMIT
- [ ] PUSH

## Work Log

- **16:10** - Baseline: `.claude/MEMORY.md` clean at nested commit
  `337cc538a200403b5f874ec5d386951f29152aec` (1,540 lines, 106,665 bytes,
  328 entries).
- **16:11** - Delegated steps 1-2 (classification table and
  `split_memory.py`, scratch folder only) and step 5 (`caveman-compress`
  backup location) to two coders on disjoint files.
- **16:12** - Step 4: the 2026-09-03 exploration's status line updated,
  with one Outcome line; the rest of that dated record is unchanged.
- **16:25** - Step 5 done (coder): `detect.py` gains `backup_path()` and a
  `backup_path` result field and prints `Backup:`; SKILL.md steps 4, 5, 8,
  10 and its Verification list use that path. 15 new cases failed first
  (`15 failed, 5 passed`), then 20 passed; `validate_targets.py` PASS
  (sidecar forbidden-token scan clean); ruff, mypy clean; full pytest 2797
  passed.
- **16:31** - Steps 1-2 done (coder, scratch only): `classification.tsv`
  and `split_memory.py` (stdlib; `write`, `check`, `selftest` proven in a
  scratch clone). **Stop condition hit:** only 18 of 328 entries qualify
  (E=7, S=11, H=0; 6,505 of 106,520 entry bytes = 6.11%, below the plan's
  25%). Applying it would shrink the working file from 106,665 to 100,972
  bytes (-5.3%). Per step 1 the split is not applied; the user is asked.
  Widening data from the coder: 22 near-miss entries (7,026 B) would reach
  about 12.7% but each has an instruction beyond its evidence; a
  topic-scoped cut (OpenWiki, sidecar, Codex, Copilot/VS Code/Antigravity,
  Context Mode, Graphify; 57 entries, 20.6 KB) would reach about 25.4% but
  makes the archive live advice, which the plan says needs its own
  preserved path and a policy change. Coder flags for the Phase G audit:
  entry 35 (status `complete` only after findings) appears to contradict
  CLOSEOUT step 2; entry 23 names a renamed `state-sync.sh` function.
- **16:35** - While waiting for the user, Phase D steps 1-2 are being
  prepared by a coder in a detached scratch worktree
  (`scratchpad/wt-phase-d`, at `06eb8e0`); nothing there touches this
  checkout or the phase machine. The diff will be applied here only after
  Phase C is committed, then verified and reviewed as Phase D.
- **Later** - Phase D prep finished in the worktree (diff at
  `scratchpad/phase-d/coder.diff`, 6 files, negative controls recorded).
  Its one design choice is accepted: path tokens of unmodelled Git
  subcommands are also resolved against the `-C`/`cd` directory as
  confirmed targets, while the existing repository-root `uncertain` (deny)
  rule stays, so no existing client decision is loosened. Started the
  evidence-only step 1 of Phases E (Ponytail 5 comparison) and F (isolated
  OpenWiki 0.7.2 spike) in the scratch folder while the Phase C decision is
  pending.
- **Later** - Phase E step 1 evidence ready (`scratchpad/phase-e/evidence.md`):
  `## Decision: PARTIAL ADOPT`, all table rows confirmed, no Q4 conflict.
  Fixed a garbled Scope sentence and the stale R2 "open user decision"
  note in the Phase E small plan. Phase F step 1 spike ready
  (`scratchpad/phase-f/capture.md`): all eight stop conditions PASS, GO;
  `0.7.2` has exactly the expected ten tools, the guard round trip restores
  both adapters byte for byte offline, and an isolated integration install
  leaves copies of the root MCP adapters unchanged.

## [LEARN] Entries

To be written at closeout.

## Verification

To be written at closeout.

## Open Questions / Next Steps

- Phase D follows: agent definition protection.
