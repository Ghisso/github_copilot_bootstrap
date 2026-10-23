# Session: Skip phases that predate closeout receipts

**Date:** 2026-10-23
**Plan:** `.claude/plans/2026-10-23_phase-A-pre-receipt-phase-exemption.md`
**Status:** IN-PROGRESS

## Goal

Unblock long-running plans whose first phases were completed before closeout receipts existed (commit `b3c6bec`, 2026-08-29): `historical_chain_errors` in `shared/scripts/verify.py` skips only the leading run of complete phases whose slug and closeout log are dated before 2026-08-29 and that have no receipt file. Every other case fails as before.

## Work Log

- Trigger: the consumer `industrial-inspection` could not commit its phase G0, because its July phases A-F of plan `2026-07-21_haystack-3-agent-refactor` have no closeout receipts (`historical phase 2026-07-21_phase-f-eval-benchmark-parity receipt is invalid`). Verified against `verify.py`; the user chose the narrow date-and-prefix rule and asked to plan and finish it.
- Planner draft, then a separate devil's-advocate review (Opus, xhigh): five plan fixes applied (a `prior` rename that avoids a mypy clash, the pull-request-time consumer test case, a base commit in the fixture, guard notes moved to the session log, one redundant test dropped, slug-date wording in docs). The review also found that the consumer's G0 closeout log was edited after its receipt, so the consumer must re-run G0's closeout after the refresh.
- User decision (2026-10-23): add the closeout-log date condition, because slug dates are planning dates. Scope addition approved earlier the same day: correct the now-inexact comment in `shared/hooks/scripts/_lib-frontmatter.sh` (comment only).
- Pre-flight: `dev` at `d911723` (PR #51 merged), clean and level with `origin/dev`. Created `pre-receipt-phase-exemption_implementation`; the branch hook set the big plan `in-progress` (`started_at: 2026-10-23T09:26:43Z`) and activated this phase.
- Coder, tests first: a fixture builder, three helpers, and the 11 planned tests (20 cases). Negative control on the unchanged `verify.py`: exactly the 7 "fails today" cases failed, each with `receipt is invalid`; the 12 guard cases passed. After the change all 20 pass. Mutations each caught by a test: `Path.exists()` instead of `lexists`, ignoring the log date, and `<=` instead of `<` on either date. Deviations: the empty-log case asserts `is neither complete nor cancelled` (an empty `closeout_session_log` is already incomplete); an undated-log-name case was added; the boundary test has three cases so each date is checked separately.
- Code: `RECEIPT_CHAIN_SINCE`, `leading_pre_receipt_count`, a docstring paragraph, and the `prior[skipped:]` walk in `shared/scripts/verify.py`; one comment in `shared/hooks/scripts/_lib-frontmatter.sh`. No error message changed.
- Coder checks: `tests/test_verify.py` 375 passed; full `tests/` 5008 passed, 1 skipped; `validate_targets.py` PASS; ruff and mypy clean. Read-only consumer probe: `historical_chain_errors` on `industrial-inspection` (G0 terminal, `receipt_head` `28378951c91c08abdb136f549ab6136e6919b7d6`) returned `[]` with 6 phases skipped.
- Documenter: the rule in `docs/runtime-checks.md` (full paragraph), README (upgrade paragraph plus one qualifier), both policies, `docs/smoke-tests.md`, and `docs/architecture.md`; `validate_targets.py` passed after the policy edits.
- Regenerated and refreshed the overlay; required checks on that tree all exit 0 (`verify.py phase` PASS, 5008 passed, 1 skipped).
- Review round 1 (six profiles): gate FAIL with two MAJORs and one MINOR, all fixed. (1) `docs/runtime-checks.md` said every phase with a pre-cutoff slug has no receipt, which ignored the closeout-log date; reworded. (2) Two guards had no test: an undated slug with an early-dated log, and a missing plan file in the leading run; the coder added both tests, and each failed under its own mutation. (3) Three short qualifiers dropped the "no receipt file" condition and the README opener keyed on plan start; fixed. The full negative control is now 22 cases: 7 fail on the old code (each `receipt is invalid`) and 15 guards pass; all 22 pass on the new code. `tests/test_verify.py` 377 passed; ruff and mypy clean.

## [LEARN] Entries

- [LEARN:verification] A check that reads history must say how it treats records made before the check existed. The receipt chain now skips only a plan's leading run of complete phases whose slug and closeout log are dated before 2026-08-29 with no receipt file; pair a planning date with a completion date, and test with the real consumer's shape.

## Stale-claims surfaces checked

- `CLAUDE.md`: clean.
- `AGENTS.md`: clean.
- `README.md`: fixed; an upgrade paragraph for plans begun before 2026-08-29, and the "across every completed phase" claim qualified (I re-wrapped one line).
- `docs/runtime-checks.md`: fixed; the closeout-receipt paragraph notes pre-cutoff phases have none, and a new paragraph after "Historical receipt-chain validation" states the full rule, the reason, and the user's approval. Its line saying the walk covers "every earlier completed phase" stays, with the exception stated right after it.
- `docs/smoke-tests.md`, `docs/architecture.md`: fixed; short qualifiers.
- Other undated `docs/` files: clean.
- `shared/policies/workflow.instructions.md`: fixed (two places); line 435 (log bytes hashed into the chain) is still true.
- `shared/policies/quality-and-testing.instructions.md`: fixed; the Push / PR row qualified.
- `shared/skills/` (including `commit` and `safe-consumer-bootstrap-refresh`): clean; `commit` says every phase must be terminal at final closeout, which is still true.
- `shared/agents/`, `shared/templates/`, `shared/review-profiles/`, state READMEs under `shared/`: clean.
- `shared/hooks/scripts/_lib-frontmatter.sh` comment: fixed in step 2.
- `scripts/validate_targets.py` comment about the removed "free pass" (~6685-6694): still accurate; its scenario uses undated slugs.
- Installed `.claude/` copies of the policies and scripts: refreshed by the self-install before closeout.
- `.claude/MEMORY.md`: no entry stated the old rule; the new `[LEARN:verification]` entry describes the new one.
- `openwiki/operations/deterministic-verification.md` (~157, "walks every earlier completed phase") and `openwiki/workflows/lifecycle-and-task-lanes.md` (~115, "across every completed phase"): stale, left for the next knowledge-refresh phase; OpenWiki pages change only through OpenWiki's tools, and a one-phase plan gets no refresh phase.
- Dated records (archived plans, closed session logs, `docs/2026-*`): left unchanged.

## Verification

## Open Questions / Next Steps

- Implement steps 1-2 (coder, tests first), then docs, audit, review, and closeout.
