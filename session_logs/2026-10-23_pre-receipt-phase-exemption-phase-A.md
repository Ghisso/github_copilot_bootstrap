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

## [LEARN] Entries

- [LEARN:verification] A check that reads history must say how it treats records made before the check existed. The receipt chain now skips only a plan's leading run of complete phases whose slug and closeout log are dated before 2026-08-29 with no receipt file; pair a planning date with a completion date, and test with the real consumer's shape.

## Stale-claims surfaces checked

## Verification

## Open Questions / Next Steps

- Implement steps 1-2 (coder, tests first), then docs, audit, review, and closeout.
