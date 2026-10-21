# Session: Backlog follow-ups — Phase E, Ponytail 5 adoption

**Date:** 2026-10-21
**Plan:** .claude/plans/2026-10-20_phase-E-ponytail-5-adoption.md
**Parent plan:** .claude/plans/backlog-followups.md
**Status:** IN-PROGRESS

## Goal

Evaluate upstream Ponytail `v5.3.2` against the vendored `v4.8.4` fork
(BF-E1) and merge only what the evaluation confirms: the A2 rules for the
coder and the review (BF-E3, BF-E4), with every skill pin moved (BF-E5),
both sidecar profiles consistent (BF-E6), and no plugin runtime or
`ponytail-audit` vendored (BF-E7).

## Task Tracking

- [x] PRE-FLIGHT: Phase D committed (`86756e0`) and pushed; Phase E is the
  current phase. Phase D's guard does not protect `shared/` sources, so
  Phase E's edits are unaffected; no planner.
- [ ] IMPLEMENT/VERIFY/REVIEW/CLOSEOUT — repeat until verification and review pass
- [ ] COMMIT
- [ ] PUSH

## Work Log

- **Earlier (during Phase C's wait)** - Step 1 ran as evidence only in the
  scratch folder (a read-only research agent): provenance confirmed
  (`v4.8.4` = `bc9ee949…`, `v5.3.2` = `16352ac2…`, LICENSE blob `715d483`
  equal at both tags and locally after Phase A); Q1 found the A2 hunks
  (P1, P2, R1, R5); Q2 keeps all eight fork never-cut items; Q3 no adopted
  hunk depends on plugin runtime; Q4 no conflict, with five wording
  conditions. `## Decision: PARTIAL ADOPT`; every provisional row confirmed.
- **Now** - Placed the evidence at
  `.claude/explorations/2026-10-20_ponytail-5-evaluation/evidence.md`
  (decision line passes the plan's check). Step 2 (NO-GO) does not apply.
  Delegated steps 3-7 to a coder with the five wording conditions.

## [LEARN] Entries

To be written at closeout.

## Verification

To be written at closeout.

## Open Questions / Next Steps

- Phase F follows: OpenWiki 0.7.2 (spike already GO); its step 4 needs the
  user to run the global install and the two integration installs.
