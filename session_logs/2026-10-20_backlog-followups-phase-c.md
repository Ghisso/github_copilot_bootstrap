# Session: Backlog follow-ups — Phase C, memory split

**Date:** 2026-10-20
**Plan:** .claude/plans/2026-10-20_phase-C-memory-split.md
**Parent plan:** .claude/plans/backlog-followups.md
**Status:** COMPLETED

## Goal

Move the `MEMORY.md` entries that fail the current admission rule into a
dated archive without losing any (BF-C1, BF-C2), keep every gate, hook, and
skill working (BF-C3), keep `caveman-compress` backups where a refresh
cannot delete them (BF-C4), and mark the 2026-09-03 exploration decided
(BF-C5). After the step 1 stop condition, the user decided not to apply the
split (scope-change record in the small plan): BF-C1 and BF-C3 dropped,
BF-C2 delivered as evidence, BF-C4 and BF-C5 delivered.

## Task Tracking

- [x] PRE-FLIGHT: Phase B committed (`06eb8e0`) and pushed; Phase C is the
  current phase. Phase B outcomes do not affect Phase C (the archive lives in
  `explorations`, already preserved); no planner.
- [x] IMPLEMENT/VERIFY/REVIEW — stop condition at step 1; user decision
  (skip the split); one review round, Gate Result `PASS`, one MINOR (fixed).
- [x] CLOSEOUT: documentation, final AI state, checkpoint, staged index,
  findings, phase receipt, closeout dry run, checkpoint, closeout receipt.
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
- **16:35** - While waiting for the user, Phase D steps 1-2 were prepared
  by a coder in a detached scratch worktree (`scratchpad/wt-phase-d`, at
  `06eb8e0`); nothing there touched this checkout or the phase machine.
  The diff (`scratchpad/phase-d/coder.diff`, 6 files, negative controls
  recorded) will be applied here after this commit and then verified and
  reviewed as Phase D. Its one design choice is accepted: path tokens of
  unmodelled Git subcommands are also resolved against the `-C`/`cd`
  directory as confirmed targets, while the existing repository-root
  `uncertain` (deny) rule stays, so no existing client decision is loosened.
- **Later** - Evidence-only step 1 of Phases E and F, run in the scratch
  folder: Phase E `## Decision: PARTIAL ADOPT` (`scratchpad/phase-e/evidence.md`,
  all rows confirmed, no Q4 conflict); Phase F spike GO
  (`scratchpad/phase-f/capture.md`, all eight stop conditions PASS: exactly
  ten tools, offline guard round trip byte-identical, isolated integration
  install leaves copies of the root MCP adapters unchanged). Fixed a garbled
  Scope sentence and the stale R2 note in the Phase E small plan.
- **User decision** - Option 2: skip the split for now. Recorded a
  scope-change record in the small plan and the big plan (Design table,
  gates, hand-offs, Requirement Map rows BF-C1 to BF-C3 and BF-C5, phase
  list, risks, Decisions recorded item 5); removed the archive assumptions
  from Phases E and G (later phases correct superseded `MEMORY.md` entries
  in place); added the two flagged MEMORY entries to Phase G's required
  audit items. Kept the classification table beside the 2026-09-03
  exploration (`2026-10-20_classification.tsv`) and rewrote its Outcome
  line to the final decision. `split_memory.py` was not kept (no split).
- **Later** - Refresh, `verify.py phase`: PASS (2797 passed). Review (six
  profiles, commit gate): `PASS`, one MINOR: the Outcome line did not name
  the table's baseline commit or hash recipe. Verified the recipe directly
  (SHA-256 of the entry lines joined with `\n` plus a trailing `\n`, first
  12 hex digits; all 328 rows match) and added both to the Outcome line.

## [LEARN] Entries

- [LEARN:planning] When a plan's payoff depends on a classification or
  measurement nobody has run yet (for example how many `MEMORY.md` entries a
  rule would archive), make that measurement the first step and give it a
  numeric stop threshold. The Phase C split stopped at 6.11% against a 25%
  threshold before any archive, index, or tool landed in the repository.

## Verification

```text
PASS        0.3s  uv run python scripts/generate_targets.py --all
PASS       43.9s  uv run python scripts/validate_targets.py
PASS       54.6s  uv run pytest tests/test_caveman_compress_detect.py -q
PASS        1.0s  uv run python scripts/check_runtime.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS        0.2s  uv run python .claude/scripts/verify.py fast --format json
closeout: PASS
```

Phase receipt: `.claude/quality_reports/verification-phase-2026-10-20_phase-C-memory-split.json`.
Findings: `.claude/quality_reports/findings-2026-10-20_phase-C-memory-split.json`
(1 MINOR, fixed; gate result `PASS`).

- optional 1: PASS — the installed `detect.py` on a scratch
  `.claude/MEMORY.md` beside an `explorations` folder printed
  `Backup: .../.claude/explorations/caveman-compress-backups/MEMORY.original.md`
  and exited 0.

## Open Questions / Next Steps

- Phase D follows: apply the prepared worktree diff, add the docs step,
  verify, and review.
