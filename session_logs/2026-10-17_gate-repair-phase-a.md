# Session: Gate repair — Phase A, review gate integrity

**Date:** 2026-10-17
**Plan:** .claude/plans/2026-10-17_phase-A-review-gate-integrity.md
**Parent plan:** .claude/plans/gate-repair.md
**Status:** COMPLETED

## Goal

Make the commit and push gates check the review evidence they rely on:
the reviewer's gate result and open requests (GR-001), the review profiles
the changed paths require (GR-002), the missing unit and installed-hook
tests (GR-003), and post-closeout drift (GR-004).

## Task Tracking

- [x] PRE-FLIGHT: `dev` clean and equal to `origin/dev` (`050a1de`); plan
  approved by the user on 2026-10-17 with decisions GR-002 (recommended
  strictness), push-gate option (b), and user-managed `context-mode` plugin.
- [x] BRANCH: `gate-repair_implementation` created from `dev`; hooks set the
  big plan `in-progress` and Phase A `in-progress` (`started_at`
  2026-10-17T04:58:19Z).
- [x] PLAN WHEN NEEDED: approved plan is implementation-ready; no planner.
- [x] IMPLEMENT/VERIFY/REVIEW — three review rounds; final Gate Result `PASS`
  with no findings.
- [x] CLOSEOUT: documentation, final AI state, checkpoint, staged index,
  findings, phase receipt, closeout dry run, checkpoint, closeout receipt.
- [ ] COMMIT
- [ ] PUSH

## Work Log

- **04:58** - Plan approved; branch created. Devil's advocate review
  (separate Opus subagent, extra-high effort) already folded into the plan.
  Relevant MEMORY lessons for the coder: `validate_targets.py` is the
  adversarial suite with `tests/test_validate_targets.py` as its pytest
  entrypoint; `CHECK_IDS` must not change; findings reports bind the staged
  index; interrupted self-installs need nested-state inspection.
- **05:05** - Before delegation, extended the option (b) schema-version rule
  to GR-002 as well (push gates must not re-judge pre-upgrade reports for
  missing profiles either). Delegated steps 1–4 and step 5 guidance text to
  the coder with the verified line references.
- **05:30** - Coder finished steps 1–4 and step 5 guidance text (12 files).
  Deviations accepted: `tests/test_install_bootstrap.py` fixture and the
  `validate_targets.py` smoke default now carry the new fields and five
  profiles; orchestrator prompts needed no change; sidecar text untouched
  (no recorder there). Negative controls: every new check, when removed,
  failed its covering tests. A pre-push installed-hook WARN case was not
  added; unit tests cover the push gates, which the plan accepts.
- **05:35** - Self-install refreshed `.claude/`; `check_runtime.py` PASS.
  `verify.py phase --format text` PASS (Ruff 0, mypy 0, pytest 2372 passed).
  Documenter updated `README.md` and `docs/runtime-checks.md`;
  `validate_targets.py` PASS afterwards. Diff sent to a fresh reviewer with
  profiles code, architecture, security, tests, ponytail, documentation.
- **05:50** - Review round 1: Gate Result `PASS`, no CRITICAL or MAJOR, six
  MINOR (malformed-schema test values; reviewer prompt MINOR wording;
  upgrade notes and refresh-gate table; policy profile-rule precision;
  smoke-tests bullet; a comment's character count). All six sent back for
  fixing (FIX LOOP) rather than dispositioned. Reviewer confirmed no push or
  PR path re-judges a pre-upgrade phase.
- **06:05** - All six MINOR fixes landed. Re-ran generation, self-install,
  `check_runtime.py` PASS, `validate_targets.py` PASS, `verify.py phase`
  PASS (pytest 2378 passed). Fresh reviewer (round 2) on the full diff.
- **06:20** - Review round 2: all six round-1 fixes confirmed. Gate Result
  `WARN`: one open request (negative-control evidence for the new
  installed-hook smoke cases and the GR-004 test, which the round-2 packet
  omitted) and two MINOR documentation findings (a README link into the
  gitignored `.claude/`; "phase diff" should say branch diff from the
  merge-base).
- **06:30** - Documenter fixed both; `validate_targets.py` PASS. Open request
  answered with the coder's round-1 negative-control results. Same reviewer,
  final: open request closed (stated as an unverified limitation: relayed,
  not re-run by the reviewer), both MINORs resolved, Gate Result `PASS`,
  findings `[]`.

### Phase-boundary summary

- **Objective and change:** gates now read the reviewer's gate result and
  open requests, and require review profiles by changed path; see the plan
  and the diff (15 files, +773/-32).
- **Deviations from the plan:** GR-002 also uses the schema-version rule at
  push gates (approved option b, extended before delegation);
  `tests/test_install_bootstrap.py` fixture updated; no pre-push
  installed-hook WARN case (unit tests cover the push gates).
- **Checks:** see `## Verification` below and the receipts under
  `.claude/quality_reports/` for this phase.
- **Open findings:** none.
- **Next operation:** Phase B, the Context Mode hook sanitizer.

### Requirement mapping

- GR-001: `tests/test_verify.py` (`test_commit_gate_blocks_an_unclean_gate_result`,
  `test_commit_gate_accepts_a_pass_with_no_open_request`,
  `test_gate_result_is_not_required_outside_phase_completion`,
  `test_push_gates_do_not_rejudge_a_schema_1_report`,
  `test_push_gates_apply_the_gate_result_to_schema_2_reports`);
  `tests/test_commit_closeout.py` recorder tests; `scripts/validate_targets.py`
  recorder smoke and installed commit-msg hook WARN case.
- GR-002: `test_required_review_profiles_by_changed_surface` (18 cases from
  the plan table), gate tests for tests-profile, five-profile, docs-only, and
  push schema rule; installed-hook missing-`tests` case.
- GR-003: `test_report_requires_a_fresh_ponytail_review_when_the_gate_says_so`;
  existing installed-hook Ponytail smoke plus the two new cases.
- GR-004: `test_staged_documentation_change_after_closeout_makes_final_state_stale`;
  comment at the `tracked_state_hash` writer.
- GR-013: no `CHECK_IDS` or receipt-schema change; no model call; no network.

## [LEARN] Entries

- [LEARN:review] A fresh re-review packet must carry every earlier
  verification result, negative controls included; otherwise the reviewer
  answers `WARN` with an open request, which now blocks the commit.
- [LEARN:verification] Before calling a gate path untested, search
  `scripts/validate_targets.py` as well as `tests/`; its installed-hook smoke
  already covered the required-Ponytail block (audit D4 was wrong).
- [LEARN:workflow] A change to `record_findings.py` arguments or report
  fields must also update the recorder smoke and completion fixtures in
  `scripts/validate_targets.py` and the lifecycle fixture in
  `tests/test_install_bootstrap.py`.

## Verification

- PASS        0.3s  uv run python scripts/generate_targets.py --all
- PASS       43.2s  uv run python scripts/validate_targets.py
- PASS       56.8s  uv run pytest tests/test_verify.py tests/test_commit_closeout.py tests/test_validate_targets.py tests/test_lifecycle_hooks.py -q
- PASS        0.8s  uv run python scripts/check_runtime.py
- PASS        0.1s  uv run python scripts/validate_plan_frontmatter.py
- PASS        0.2s  uv run python .claude/scripts/verify.py fast --format json

Phase receipt: `verify.py phase --format json --persist` PASS (Ruff, mypy,
pytest, VFY-FRESH-001/002, VFY-GEN-001). Findings report:
`.claude/quality_reports/findings-2026-10-17_phase-A-review-gate-integrity.json`
(0 findings, `gate_result: PASS`, profiles code, architecture, security,
tests, ponytail, documentation).

- optional 1: NOT RUN — the native Claude Code and Codex commit attempt with a `WARN` report in a disposable clone is a user-run host check; the installed commit-msg hook smoke in `scripts/validate_targets.py` exercises the same shared `assert_commit_invariants` path and denies a `WARN` report.

## Open Questions / Next Steps

- Next: Phase B, `2026-10-17_phase-B-context-mode-hook-sanitizer`.
