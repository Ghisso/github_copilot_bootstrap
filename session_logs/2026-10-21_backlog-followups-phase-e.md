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
- [x] IMPLEMENT/VERIFY/REVIEW — one review round, Gate Result `PASS`, one
  MINOR (fixed).
- [x] CLOSEOUT: documentation, final AI state, checkpoint, staged index,
  findings, phase receipt, closeout dry run, checkpoint, closeout receipt.
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
- **Start** - Placed the evidence at
  `.claude/explorations/2026-10-20_ponytail-5-evaluation/evidence.md`
  (decision line passes the plan's check). Step 2 (NO-GO) does not apply.
  Delegated steps 3-7 to a coder with the five wording conditions.
- **Later** - Coder merged P1 ("Find every place", folding the fork's ladder
  paragraph), P2-P6, R1 (adapted), R3 (skill and profile), R5 (adapted, no
  expected-load clause), R6 (`Not checked:` in the skill only); declined
  P7-P12, R2, R4, R7; no `ponytail-audit` or plugin runtime vendored. Pins
  moved to `v5.3.2` (`ponytail` 85 lines, sha256 `1e0cf9db…`;
  `ponytail-review` 65 lines, sha256 `56f23aa9…`); `UPSTREAM.md` rewritten
  with a merge record and pin checklist; new anchor test for
  `SIDECAR_TEXT_REPLACEMENTS`; nine new guidance rows; snapshot hash
  recaptured. Negative controls: the hash pin, the anchor test, and every
  guidance row each failed when broken. Extras kept (judged in scope by the
  reviewer): a `ponytail.md` checklist item carrying R5 to the reviewer
  agent, two `reuse:` guidance rows, a standing anchor negative test.
- **Later** - Documenter updated `docs/architecture.md` (Ponytail section)
  and `docs/smoke-tests.md` (version); README claims stay true. Refresh;
  `verify.py phase`: PASS (3267 passed).
- **Later** - Review (six profiles, commit gate): `PASS`, one MINOR: the
  architecture doc said `ponytail-review` always ends with `Not checked:`
  and attributed it to the reviewer agent. Fixed: the line is added only
  when something mattered but could not be checked, and the reviewer agent
  reports such items as Open Requests.
- **Closeout** - Corrected the two Ponytail pin lessons in `MEMORY.md` in
  place (line counts and the pin checklist's new home), as step 8 requires.

## [LEARN] Entries

[LEARN] none - no new lessons this session

## Verification

```text
# verify closeout --format text summary lines
```

- optional 1: NOT RUN — the one-run-per-arm behavioral spot-check needs
  fresh interactive coder and reviewer sessions (the user was away); it is
  non-decisive by design, and the big plan records that model compliance
  has no available verification.

## Open Questions / Next Steps

- Phase F follows: OpenWiki 0.7.2 (spike already GO); its step 4 needs the
  user to run the global install and the two integration installs.
