# Session: Phase 5 — Diagnose an Inactive Phase Instead of Crashing

**Date:** 2026-09-02
**Plan:** `.claude/plans/2026-09-02_phase-5-inactive-phase-diagnostics.md`
**Status:** COMPLETED

## Goal

Make `verify.py` report a clear, actionable message when no phase is active,
instead of exiting with an unhandled traceback, and land the big-plan §3.5
correction Phase 4 could not. Phase 5 of
`verification-gate-semantic-hardening`, appended after Phase 4 closed.

## Work Log

- **01:00** - The user asked for the inactive-phase traceback to be fixed by
  adding a phase. Measured the failure across modes first: `fast` and `phase`
  died with `receipt metadata control-plane provenance is invalid`, `closeout`
  with `receipt persistence needs a safe phase slug`. `gate` was unaffected
  because it takes `--phase` explicitly.
- **01:05** - Confirmed pre-existing rather than caused by phases 1–4 by
  extracting `control_plane_provenance`, `active_plan_paths`, and
  `state_metadata` and comparing each against `dev`: all three byte-identical.
- **01:10** - Extended the big plan with phase 5. Opening the phase made all
  modes work again, which confirmed the diagnosis directly: the failure is
  entirely a function of `current_phase` being empty.
- **02:30** - Round 1: new `unresolved_phase_reason` guard in `main()`,
  following the existing `print(..., file=sys.stderr); return 2` convention a
  few lines from the failure site. 1201 tests pass. §3.5 corrected.
- **03:10** - Review round 1: **FAIL**, 2 CRITICAL + 2 MINOR, all reproduced
  by running the CLI against real fixtures rather than by reading. The fix
  meant to remove a traceback left the same traceback reachable two ways.
- **04:00** - Round 2: all four fixed. 1210 tests pass.

## Design decisions

- **The guard reports; it does not relax anything.** It runs before mode
  dispatch and only inspects plan resolution on disk. `validate_receipt`, the
  provenance guard, and the phase-slug check are untouched. An unresolvable
  phase still produces no receipt at all — that was already correct and stayed
  correct. The change is that the condition is now stated instead of thrown.
- **`fast` keeps requiring an active phase.** Exempting it would have meant
  either passing malformed provenance through `validate_receipt`, which the
  non-goals forbid relaxing, or printing raw checks in a second output shape
  whose `--format json` still emits `metadata` and `checks` and so reads as a
  receipt without valid provenance. The contract said to keep the requirement
  when in doubt, and there was doubt.
- **Two message categories, not one string.** "No active phase" and "active
  phase metadata is malformed" are different situations for a consumer, and
  the review round proved the distinction has teeth: the first attempt
  collapsed an unreadable plan and an unparseable one into the "complete or
  not yet started" message, which was actively wrong about the cause.
- **Readability is checked by reading.** The first cut used `is_file()` as a
  proxy for readable. It is not one, and downstream `digest_file` swallows the
  `PermissionError` and returns an empty digest, reproducing the exact crash
  this phase exists to remove. The guard now attempts the read that
  `digest_file` will attempt.
- **An explicit `--phase` on a non-implementation branch stays supported.**
  This is the consumer-native path, already covered by
  `test_installed_verifier_uses_consumer_native_scopes`, which runs
  `verify.py phase --persist --phase <slug>` on a fresh `dev` with no plan
  machinery. The guard is therefore conditioned on `requires_phase and not
  phase`, not on branch shape alone.

## [LEARN] Entries

- [LEARN:code] `Path.is_file()` is not a readability check. It reads the
  file-type bit and nothing else, so a `chmod 000` file passes it. Where a
  later step will actually open the file — and especially where that step
  swallows `OSError` and returns an empty digest — the guard must attempt the
  same read, or it certifies a condition it never tested.
- [LEARN:verification] A fix that removes an exception can leave the same
  exception reachable by another route. This guard eliminated the traceback
  for an empty `current_phase` while leaving it reachable on a
  non-implementation branch and through an unreadable plan file. Enumerate the
  ways the failing state can arise, not just the one that was reported.
- [LEARN:testing] Gate a permission-dependent test on `os.geteuid() == 0` and
  skip, or it passes vacuously under a root-run CI where `chmod 000` does not
  deny reads. A test that cannot fail proves nothing.
- [LEARN:workflow] Adding a guard before mode dispatch can break a legitimate
  path that bypasses the machinery the guard assumes. The consumer-native
  `--phase` override runs `phase` on a plain `dev` branch with no plan at all;
  conditioning on branch shape alone regressed it. Check what already exercises
  the code path being fenced off.

## Verification Results

```bash
uv run pytest tests/ -q --tb=short
# 1210 passed (1196 at the end of phase 4; +14)

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

Big plan §3.5 corrected to record the Phase 4 parentage-proof rule after the
Phase 2 correction it builds on, so the section reads as a history rather than
a contradiction. This is the edit Phase 4 could not make: editing the plan
after that phase closed invalidated the closeout receipt's bound plan digest
with no active phase left to regenerate against. Swept `docs/` and `shared/`
for any description of the inactive-phase behavior; none existed to update,
since the previous behavior was an unhandled exception rather than a
documented contract.

## Open Questions / Next Steps

- Four files were already unformatted on `dev` and remain untouched:
  `shared/hooks/scripts/protect-files.py`,
  `shared/skills/caveman-compress/scripts/{detect,validate}.py`,
  `tests/test_check_native_clients.py`.
- No compatibility allowance exists in this plan, so none carries a removal
  condition.
- The user owns the merge decision; no PR was opened.
