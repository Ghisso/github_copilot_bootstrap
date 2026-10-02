# Session: Engineering workflow Phase B — planning, reporting, and learning guidance

**Date:** 2026-10-02
**Plan:** `.claude/plans/2026-10-02_phase-B-engineering-planning-guidance.md`
**Status:** COMPLETED

## Goal

Make outcome, risk, contract, and test reasoning explicit in planning before
phase decomposition; add a short phase-boundary summary and failure-to-
regression routing in LEARN; adapt the same advice to the relaxed workflow
sidecar; add focused deterministic text checks. Covers REQ-001–003,
REQ-007, REQ-008, and the remaining part of REQ-009 from
`.claude/plans/engineering-workflow-improvements.md`.

## Work Log

- **Resume** - User approved continuing after Phase A (`ca0fb37`, pushed).
  The post-commit hook set `current_phase` to Phase B and Phase B
  `in-progress`; outer tree clean.
- **Material-impact check** - Phase A outcomes do not change Phase B scope.
  Carry-over for the coder: Phase A's coder rule already uses "failed
  decisive assumption", so Phase B's planner risk/evidence decision should
  define that term; point to Phase A's requirement-authority rule instead of
  restating it. Phase A review lesson applied: scope follow-up review rounds
  to defects that round introduced.
- **Starting facts** - `shared/agents/planner/prompt.md` full-plan flow:
  Phase 0 intake, Phase 1 Bounded Discovery (~53), Phase 2 Focused
  Clarification (~60), Phase 4 Plan Draft (~73); `## Plan Requirements`
  (~86) already holds the external-integration `integration-gate-spike`
  rule (~97-102). `shared/skills/learn/SKILL.md` Phase 1 Evaluate (~14-32)
  routes lessons but has no failure-to-regression route.
- **IMPLEMENT** - Fresh `coder` (new phase). Result: 18 `shared/` files plus
  `tests/test_validate_targets.py` (6 new test cases, ~100 section-scoped
  key phrases; negative control: reverse-applying `shared/` fails all 6).
  Deviations: an existing reporting-pointer test changed from a single
  replace to replace-all; noted, not fixed: the sidecar plan-small template's
  pre-existing `L1 verification-block-missing` example and three orphan
  lines left by the sidecar repair.
- **VERIFY** - Verification block: all items exit 0 except
  `check_runtime.py` (22 stale-copy notices only); 1230 and 229 passed.
- **REVIEW round 1** - Fresh `reviewer`, six profiles, with an explicit
  question on whether ~100 asserted phrases is a near-snapshot. Gate WARN:
  0 CRITICAL, 0 MAJOR, 4 MINOR, and one open request (show `check_runtime.py`
  exit 0 after the self-overlay refresh) — the first real use of Phase A's
  open-request mechanism. MINORs: B1-#1 111 exact phrases plus a 111-step
  removal loop (trim to ~45 anchors, Phase A-style move + removal cases);
  B1-#2 two placement-negative assertions with no requirement behind them;
  B1-#3 ambiguous sidecar orchestrator sentence; B1-#4 requirement-map
  trigger worded "several artifacts" vs "several phases". All four sent to
  the same coder. The open request will be answered after the fix round,
  since an earlier refresh would go stale again. Coder deviations accepted by
  the reviewer; the authoring-path pointer in the session-log template and
  the sidecar plan-small orphan lines are suggested for the Phase C audit.
- **FIX LOOP round 2** - Coder applied B1-#1..#4: 48 unique anchors (full
  32, sidecar 21, shared template 5; down from 111), Phase A-style move +
  removal test, placement-negative assertions removed, sidecar orchestrator
  sentence clarified, requirement-map trigger consistent in four files.
  Deviations: session-log template anchors and two other anchors dropped.
  Open request answered: `generate_targets --all` and the self-overlay
  refresh exit 0, then the full Verification block passed every item,
  including `check_runtime.py` exit 0 with 0 FAIL lines. Round-2 delta and
  the answer sent to the same reviewer.
- **REVIEW round 2** - Scoped to defects this round introduced. Gate PASS,
  findings `[]`; B1-#1..#4 confirmed fixed; the open request closed; all
  three coder deviations accepted. Optional (not a finding): three more
  one-word anchors would cover the planner "remaining limit" clauses and the
  sidecar rule's summary paragraph; not added.
- **DOCUMENT** - `documenter` added one sentence to `README.md` `## Agent
  System` on the planner's evidence step; the sidecar flow text and
  `docs/architecture.md` were checked and are not stale.
  `check_runtime.py` rechecked after the doc edit: exit 0.
- **Findings** - 4 MINOR recorded from round 1, all `fixed`.
- **Phase C audit follow-ups** - the full session-log template's
  authoring-path pointer to the Verification Evidence Contract
  (`shared/policies/...`), and the orphan lines plus comment-only example
  block in `shared/sidecar/workflow/templates/plan-small.md`.

## [LEARN] Entries

- [LEARN:testing] Section-scoped guidance tests drift toward prose
  snapshots (111 phrases at first); one to five short anchors per section,
  one removal case, and one moved-out-of-section case keep the check
  meaningful and tolerate harmless rewording.

## Verification

```text
PASS        0.4s  uv run python scripts/generate_targets.py --all
PASS       25.1s  uv run pytest tests/test_validate_plan_frontmatter.py tests/test_verify.py tests/test_hook_gates.py -q
PASS       65.9s  uv run pytest tests/test_validate_targets.py tests/test_sidecar_workflow_scenario.py -q
PASS       54.7s  uv run python scripts/validate_targets.py
PASS        1.1s  uv run python scripts/check_runtime.py
PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
PASS        0.3s  uv run python .claude/scripts/verify.py fast --format json
closeout: PASS
findings: .claude/quality_reports/findings-2026-10-02_phase-B-engineering-planning-guidance.json (critical 0, major 0, minor 4; dirty false)
```

- optional 1: PASS — orchestrator inspected generated `dist/multi-agent/.claude/agents/planner.md`, `.codex/agents/planner.toml`, and `.claude/templates/plan-big.md` (decisive-assumption and experiment rules, optional requirement map) and `dist/sidecar/workflow/.claude/agents/planner.md` and its `plan-big.md` (advisory versions; planner returns its plan as reply text); prose review only, not evidence of agent behavior.

## Open Questions / Next Steps

- Phase C (`2026-10-02_phase-C-engineering-knowledge-refresh`) is next: the
  OpenWiki refresh and the final live-advice audit, including the two
  follow-ups above.
