# Session: OpenWiki Phase F2 — verification evidence guardrails

**Date:** 2026-09-20
**Plan:** `.claude/plans/2026-09-19_phase-F2-verification-evidence-guardrails.md`
**Status:** IN-PROGRESS

## Goal

Make the Phase A failure class impossible without judgement: a small plan's
required verification is a machine-read list of shell commands that
`verify closeout` runs itself and records in the closeout receipt; hedged
check wording is refused at plan approval; optional checks have one declared
home; the spike skill is routed to third-party binaries, CLIs, and MCP
servers; and the `tests` review profile asks whether an external dependency
was ever exercised directly.

## Work Log

- Plan amended before implementation (user decision 2026-09-20): the
  commit-time check runs the required items itself instead of reading
  "PASS" out of the session log. Results live under the closeout receipt's
  existing optional `extensions` object, so `CHECK_IDS` and
  `SCHEMA_VERSION` are unchanged and Phase A–C receipts still load.
- Hedge-pattern list settled by the orchestrator after re-measuring all 110
  small plans: the earlier count's `best-effort` phrase is design prose about
  sync behaviour, not a hedged check, and was dropped; plural verb forms were
  added. The three final patterns flag five plans, all genuine hedged checks
  (four complete, plus the planned Phase G comment "runs only if a Docker
  host is available"). Zero false positives on the current corpus.
- Steps F2.1, F2.4, F2.5 (policy, templates, prompts, skills, review
  profile): one coder, ten files under `shared/`. Canonical section
  `## Verification Evidence Contract` added to
  `shared/policies/workflow.instructions.md`; every other surface links to it.
  Orchestrator corrected two enforcement-table rows to match the code (L1 is
  specific to `bash`/`sh` fences; L3 is "contains", not "ends in").
- Steps F2.2, F2.3 (lint, runner, gate, tests): one coder. 38 new tests;
  suite went from 829 to 867 in the two affected files. Deviations accepted:
  L1/L3/L4 messages point at the `## Verification` heading line rather than
  the offending item; the hedge scan masks fenced and optional spans with
  spaces so line numbers stay bound to the file.
- Step F2.6 (live plans and docs): one coder. Phase G Step G2 redesigned to
  add no check ID (`VFY-OPENWIKI-001` retired everywhere in live plans; the
  conditions move into `VFY-GEN-001` and a commit-gate error with prefix
  `openwiki-managed-state:`); Step G4's Docker assumption comment removed and
  the smoke test made non-skippable; Phase G and Phase I gained
  `## Optional Verification`; three rows and one paragraph added to
  `docs/runtime-checks.md`. Orchestrator renamed the two remaining risk-table
  mentions in the big plan.
- VERIFY round 1: `tests/test_hook_gates.py` fixture created an undated
  in-progress small plan with no `## Verification` block and was correctly
  rejected by the new lint; fixture given a one-command block. After
  `generate_targets.py --all`: 1624 tests pass; `validate_targets.py` fails in
  its two-phase end-to-end scenario with pre-existing freshness errors
  ("closeout receipt final tracked state is stale", "findings report
  content_hash is stale", historical tree_sha mismatch). Handed to the script
  coder as a deterministic regression.
- Root cause of the validator failure: the new gates working as designed. The
  scenario's fixture helpers write undated plans with no `## Verification`
  block (rejected by L1 through the real commit-msg hook) and build closeout
  receipts directly, without `extensions.verification_items` (rejected by
  G1). The stale-tree messages were downstream of the first refused commit.
  Orchestrator decision: the two fixture helpers in
  `scripts/validate_targets.py` gain a one-command `true` block and the
  matching PASS result. 20 FAIL lines across six scenarios went to zero with
  no other edits.
- VERIFY round 2 after `generate_targets.py --all` and the self overlay
  refresh: `validate_targets.py` exit 0; `check_runtime.py` exit 0;
  `validate_plan_frontmatter.py` exit 0; `verify.py phase` PASS with 1625
  tests, ruff and mypy clean, generated verifier matches source.

## Review findings and dispositions

(pending)

## [LEARN] Entries

(pending)

## Verification

(pending: the runner's summary lines are pasted here at closeout; this plan
has no optional items)

## Open Questions / Next Steps

(pending)
