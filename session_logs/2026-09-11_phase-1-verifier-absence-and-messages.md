# Session: Verifier tells "nothing to measure" from "failed", and names runnable fixes

**Date:** 2026-09-11
**Plan:** `.claude/plans/2026-09-11_phase-1-verifier-absence-and-messages.md`
**Status:** COMPLETED

## Goal

Let a consumer with no tests yet produce a `PASS` receipt, keep every real
tool failure blocking with a message that names the exact fix, make the two
checkpoint remediation messages name a command the agent guard allows, and
document what the gates need from a consumer project.

## Why This Phase Exists

`aggregate_status` turns any `UNVERIFIED` check into an `UNVERIFIED` receipt,
and the commit and push gates accept only `PASS`. pytest exiting 5 (no tests
collected) mapped to `UNVERIFIED`, so a new project could never commit its
first phase. The same happened for a missing ruff, mypy, or pytest
executable and for mypy without a configured scope, and none of those
messages named the fix. Separately, both checkpoint remediation messages told
the agent to run `bash .claude/hooks/scripts/state-sync.sh checkpoint`, which
the PreToolUse guard denies for the agent.

## Work Log

- Delegated implementation to `coder` with the plan as the contract. First
  pass added the test-file scan, the exit-5 branch, `FileNotFoundError`
  handling, the two message rewrites, tests, and docs.
- Review round one (`code`, `architecture`, `security`, `tests`, `ponytail`)
  returned one CRITICAL, two MAJOR, two MINOR, each confirmed by executing the
  module: `validate_mode_applicability` rejected `VFY-PYTEST-001` as
  `NOT_APPLICABLE` in `phase` mode, so `build_receipt` raised for exactly the
  test-less case; `uv run <tool>` with the tool missing exits 2 with
  `Failed to spawn` rather than raising, so the new `FileNotFoundError`
  branches never fired for the intended case; the tests mocked the exception
  shape the wrapper never produces; the install message literal was
  duplicated; the scan swallowed permission errors in the fail-open direction.
- Second coder pass fixed all five: a per-mode `conditionally_applicable` set
  in `validate_mode_applicability` limited to `phase: {"VFY-PYTEST-001"}`;
  `_missing_tool(tool, rc, stderr)` after each `_run`; realistic
  `(2, "", "Failed to spawn …")` test cases plus one `uv`-missing case; the
  literal moved to `_tool_missing_detail`; a wider skip set and an `onerror`
  callback. Each fix was confirmed failing before and passing after.
- Review round two returned zero CRITICAL or MAJOR and two MINOR: the doc
  sentence understated the skip list, and the inconclusive-walk case reused
  the "although test files exist" wording. Fixed both directly: the scan now
  returns `bool | None`, the exit-5 branch has a third message for the
  unreadable-subtree case, the test asserts the new wording, and the doc lists
  the real skip set.
- Regenerated targets and installed locally after every source change;
  `validate_targets.py` passes on the final state.

## Design Decisions

- pytest exit 5 is `NOT_APPLICABLE` only when the repository has no test
  files at all. Test files that pytest does not collect stay `UNVERIFIED`
  with a `testpaths` hint. An unreadable subtree stays `UNVERIFIED` with a
  permissions hint.
- mypy without a scope stays blocking. Typed Python is this bootstrap's
  standard, and mypy over a flat layout without configuration produces worse
  errors than a clear refusal. The message names the two accepted fixes.
- The `conditionally_applicable` carve-out is the smallest shape that keeps
  every other phase check strictly applicable. The per-check rule binding
  `applicable` to `status` in `validate_receipt` is untouched, so a hand-built
  receipt gains nothing it could not already gain by writing `PASS`.
- `Failed to spawn` matching applies only when `rc != 0`; the residual risk
  is a misleading message on a tool whose own stderr contains that phrase,
  which still fails closed. Recorded, not fixed.
- No receipt schema change.

## [LEARN] Entries

- [LEARN:quality] `uv run <tool>` with the tool missing from the project
  environment does not raise `FileNotFoundError`; `uv` exits 2 with
  `Failed to spawn` on stderr. Detect the missing tool from that exit and
  message, and test the realistic `(rc, stdout, stderr)` shape rather than a
  raised exception the wrapper never produces.
- [LEARN:quality] A receipt check that can newly resolve to `NOT_APPLICABLE`
  must also be allowed by `validate_mode_applicability`'s per-mode table, or
  `build_receipt` raises for exactly the case the change exists to serve.
  Test through `build_receipt`, not only through `aggregate_status`.
- [LEARN:testing] A repository scan that can be blocked by permissions needs a
  three-way result (found, absent, inconclusive); collapsing inconclusive into
  "found" keeps the gate closed but produces a message that points the reader
  at the wrong cause.

## Verification Results

Final state, with targets regenerated and locally self-installed beforehand:

```text
uv run pytest tests/ -q --tb=short                       1469 passed
uv run pytest tests/test_verify.py -q                    243 passed
uv run mypy shared scripts tests                         no issues in 28 source files
uv run ruff check shared scripts tests                   All checks passed
uv run ruff format --check shared scripts tests          28 files already formatted
uv run python scripts/generate_targets.py --all          regenerated
uv run python scripts/install_bootstrap.py . --allow-self --local-only   installed
uv run python scripts/validate_targets.py                PASS generated target is structurally valid
uv run python scripts/check_runtime.py                   all PASS
uv run python .claude/scripts/verify.py fast             PASS
review round 1                                            1 CRITICAL, 2 MAJOR, 2 MINOR, all fixed
review round 2                                            0 CRITICAL, 0 MAJOR, 2 MINOR, both fixed
```

Receipts: `.claude/quality_reports/verification-phase-2026-09-11_phase-1-verifier-absence-and-messages.json`
and `.claude/quality_reports/verification-closeout-2026-09-11_phase-1-verifier-absence-and-messages.json`,
findings at `.claude/quality_reports/findings-2026-09-11_phase-1-verifier-absence-and-messages.json`.

## Open Questions / Next Steps

1. Phase 2 of this big plan: `state-sync.sh` sets `core.hooksPath` on
   restore and untracks the error log, the push gate explains the chained
   commit-and-push refusal, hook tests write only under `tmp_path`, final
   audit.
2. Whether `Failed to spawn` detection should be narrowed to `rc == 2` is
   left open; the current match fails closed either way.
