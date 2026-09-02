# Session: Phase 4 — Close the Dispositioned MINOR Findings

**Date:** 2026-09-02
**Plan:** `.claude/plans/2026-09-02_phase-4-minor-findings-closure.md`
**Status:** COMPLETED

## Goal

Fix the three MINOR findings that phases 2 and 3 closed with an accepted
disposition, so no advisory residual remains in the hardened gate. Phase 4 of
`verification-gate-semantic-hardening`, appended after the plan had already
reached `complete`.

## Work Log

- **21:00** - The user asked for the dispositioned MINORs to be fixed. Counted
  them against the recorded findings reports: three, not two — my closing
  summary had under-reported. Phase 2 carried a merge-topology test gap and a
  reversed-order fixture still using the disproven tree rule; Phase 3 carried
  a CRLF fence-parsing gap.
- **21:05** - These touch `shared/scripts/verify.py`, which is control-plane,
  so they need the full lifecycle rather than a direct patch. The big plan was
  `complete` and `dev` does not yet have phases 1–3, so branching fresh from
  `dev` would have lost the base. Extended the big plan with a phase 4
  instead, following this repo's own precedent of appending phases J–M to an
  A–I plan, and recorded in the big plan why it grew.
- **22:30** - Round 1 returned all three fixed. 1193 tests pass.
- **23:00** - Review round 1: **FAIL**, 1 MAJOR + 1 MINOR. The MAJOR was
  `docs/runtime-checks.md` still documenting the selection algorithm that
  item 1 had just replaced — a stale claim created by the fix itself. The
  MINOR was a lone-`\r` blind spot in the same scanner item 3 had touched.
- **23:10** - Fixed the doc myself; delegated the lone-`\r` fix.
- **23:40** - Round 2 returned. 1196 tests pass.

## Design decisions

- **Parentage is proven, not inferred from position.** Item 1's selection now
  filters `git rev-list --ancestry-path --reverse --parents` to commits whose
  parent set contains `earlier_head`. Zero candidates keeps the existing
  no-ancestry-path message; more than one is a new fail-closed branch naming
  the ambiguity. Merges inside an implementation branch remain unsupported —
  this stops the tree check resting on that assumption silently, rather than
  tolerating them.
- **Item 1 was a latent correctness hole, not just missing coverage.** The
  reviewer independently reproduced a silent accept: with `tree_sha` set to
  whichever commit sorted first under the old command, the old code returned
  no errors while an equally valid sibling candidate with a different tree
  existed. Depending on arbitrary git ordering it would either misdiagnose as
  a tree mismatch or pass unproven.
- **Line splitting is explicit, not `str.splitlines()`.** `splitlines()` also
  breaks on `\v`, `\f`, `\x1c`-`\x1e`, `\x85`, and the Unicode separators,
  which would silently widen what counts as a line boundary in a scanner that
  decides whether evidence is real. `\r\n|\r|\n` says exactly what is meant.
- **The `\r?` tolerance was removed once splitting made it redundant.** With
  three-way splitting no segment can retain a trailing `\r`, so keeping both
  the tolerant regex and the tolerant split would have been duplication. The
  two CRLF test expectations changed to match, which is a test following a
  deliberate behavior change rather than being bent to pass.
- **The private helper is tested directly.** `closeout_log_errors` reads
  through `Path.read_text()`, whose universal-newline handling normalizes both
  `\r\n` and lone `\r` before the scanner runs, so a round-trip test would
  pass vacuously regardless of the fix. The reviewer confirmed this and judged
  the line-ending handling defensible defense-in-depth for a shipped module
  rather than unreachable code, since the helper's callers are not guaranteed
  to normalize first.

## [LEARN] Entries

- [LEARN:verification] A gate that picks one item from an ordered list is
  asserting an invariant it has not checked. Selecting "the first entry of
  `git rev-list --ancestry-path --reverse`" silently accepted an unproven
  commit whenever the range was not linear. Filter on the property that
  actually matters — here, that the candidate's parent set contains the
  expected commit — and fail closed when it does not hold for exactly one.
- [LEARN:workflow] Fixing a finding can create one. Item 1's improvement made
  `docs/runtime-checks.md` describe a superseded algorithm, which the same
  review then raised as MAJOR. When a change alters a documented mechanism,
  update its documentation in the same round rather than waiting for review
  to find it.
- [LEARN:review] A dispositioned MINOR is not necessarily small. Reopening
  three accepted MINORs surfaced one latent silent-accept in the receipt
  chain. An accepted disposition records a judgement that the finding was not
  worth fixing then; it is not evidence that the finding was shallow.
- [LEARN:code] When a fix makes an earlier guard redundant, remove the guard.
  Explicit `\r\n|\r|\n` splitting consumes every `\r`, so the trailing-`\r`
  tolerance added a round earlier became duplication and was deleted rather
  than carried alongside.

## Verification Results

```bash
uv run pytest tests/ -q --tb=short
# 1196 passed (1190 at the end of phase 3; +6)

uv run mypy scripts/ --ignore-missing-imports --explicit-package-bases
# Success: no issues found in 8 source files

uv run ruff check tests/ scripts/ shared/
# All checks passed!

uv run python scripts/validate_targets.py
# PASS generated target is structurally valid

uv run python scripts/validate_plan_frontmatter.py
# (clean)

uv run python .claude/scripts/verify.py fast --format text
# fast: PASS

uv run python .claude/scripts/verify.py phase --format text
# phase: PASS
```

## Stale-claims surfaces checked

Triggered because item 1 changed a documented mechanism. `docs/runtime-checks.md`
updated. Swept `docs/` and `shared/` for any other description of the
certified-commit selection; the big plan's §3.5 was already corrected during
phase 3.

## Open Questions / Next Steps

- Four files were already unformatted on `dev` and remain untouched:
  `shared/hooks/scripts/protect-files.py`,
  `shared/skills/caveman-compress/scripts/{detect,validate}.py`,
  `tests/test_check_native_clients.py`.
- No compatibility allowance exists in this plan, so none carries a removal
  condition.
- The user owns the merge decision; no PR was opened.
