# Consumer Lifecycle Friction Hardening — Phase B Closeout

**Status:** COMPLETED
**Plan:** `.claude/plans/2026-09-10_phase-B-root-adapter-recovery-diagnostics.md`
**Branch:** `consumer-lifecycle-friction-hardening_implementation`
**Started:** 2026-09-10T11:52:00Z

## Goal

Restore installer-owned ignored root adapters after every successful state
pull, and make verifier provenance failures name the affected
manifest-relative path and failure category without exposing file contents.

## Completed phase

Phase B: `.claude/plans/2026-09-10_phase-B-root-adapter-recovery-diagnostics.md`

This phase was paused mid-remediation at 2026-09-10T12:24:00Z and resumed on
2026-09-11. The pause record is
`.claude/session_logs/2026-09-10_consumer-lifecycle-friction-hardening-phase-B.md`
and remains a historical PAUSED log; this file is the closeout record.

## Work log

- Resumed the paused phase, set the same small plan back to `in-progress`, and
  preserved its pause metadata rather than creating a replacement phase.
- Ran the recorded resume-point checks. 310 focused state-sync, verifier, and
  installer tests passed. `scripts/validate_targets.py`, which had failed
  before the pause, passed against the committed early-return fix.
- `scripts/check_runtime.py` reported the installed overlay stale for exactly
  the two files Phase B changed. Repaired with the documented self-refresh
  (`generate_targets.py --all` then `install_bootstrap.py . --allow-self
  --local-only`), after which all 19 runtime checks passed.
- Review round 1 (six profiles, two passes) failed the gate with two major and
  two minor findings: `cmd_setup` had silently lost its standalone
  root-adapter restoration, the `content-difference` diagnostic category had
  no test, `adapter_destination_is_replaceable` rejected a fully missing
  intermediate parent directory, and a ternary was written inverted. The
  orchestrator additionally found a redundant `reconcile_status` branch in
  `cmd_setup` whose two paths were byte-identical.
- Remediation reinstated `restore_root_adapters` in `cmd_setup`'s fresh-init
  path only, restored the original standalone-`setup` assertion in
  `scripts/validate_targets.py` while keeping the new post-pull assertion,
  added the missing tests, and collapsed the redundant branch.
- The documenter corrected the three live documentation surfaces the review
  identified.
- Review round 2 failed the gate with two further major findings:
  `adapter_destination_is_replaceable` compared tree shapes for equality when
  restoration only adds and overwrites, so a live tree that is a strict subset
  of its mirror was wrongly reported unrepairable; and the new
  `docs/runtime-checks.md` paragraph attributed an unsafe file type to the
  wrong diagnostic category. Round 2 also confirmed, by tracing every failure
  and abort path of `reconcile_committed_state` and reproducing the merge
  conflict case, that `cmd_setup`'s fresh-init restoration cannot see remote
  bytes from a partially applied reconciliation.
- Remediation replaced the equality test with a subset test, corrected the
  documentation, and made the post-pull assertion probative by deleting the
  adapter between `setup` and `pull`.
- Review round 3 confirmed all three round-2 findings resolved and raised one
  major test-coverage gap: the subset relaxation's rejection boundary had no
  regression tests for a kind mismatch or a symlink nested inside an otherwise
  valid adapter directory.
- Three parametrized cases were added. Review round 4 verified each reaches
  the claimed diagnostic category and would catch a realistic widening of the
  relaxation, and returned a PASS gate.

## Verification state

- `uv run pytest tests/ -q`: 1322 passed.
- `uv run pytest tests/test_state_sync.py tests/test_verify.py
  tests/test_install_bootstrap.py -q`: 314 passed.
- `scripts/generate_targets.py --all` and `install_bootstrap.py . --allow-self
  --local-only` completed, and `scripts/validate_targets.py` reported the
  generated target structurally valid.
- `scripts/check_runtime.py`: 19 passed, 0 failed.
- Ruff check and Ruff format check passed for `shared scripts tests`.
- Mypy passed for the changed scope.
- `scripts/validate_plan_frontmatter.py` passed.

## Review outcome

Four review rounds, each running the `code`, `architecture`, `security`,
`tests`, `ponytail`, and `documentation` profiles over two sequential passes.
Final gate: PASS, with no surviving critical or major finding.

One minor finding was accepted with an explicit reason rather than fixed. The
`nested-kind-mismatch` test case is confounded by an incidental extra-entry
effect, so in isolation it does not independently prove nested kind checking.
The `root-kind-mismatch` case in the same parametrized group proves that
property unambiguously, and the reviewer confirmed no realistic regression
shape passes `root-kind-mismatch` while evading detection, so the confound
leaves no real coverage gap.

## Scope note

Phase B's approved scope was unchanged. A separate defect reported during this
phase — unguarded empty-array expansion in the lifecycle hook scripts, which
aborts on the declared Bash 3.2 baseline — was deliberately not folded into
this phase, because it is unrelated control-plane work that would have made
this commit incoherent. It is now
`.claude/plans/2026-09-11_phase-B2-hook-empty-array-safety.md`, inserted into
the big plan after Phase B and before Phase C.

## [LEARN] Entries

- [LEARN:review] A refactor that extracts a shared helper can silently drop a
  side effect the original function performed. When `cmd_setup` was split into
  `setup_local_state` plus a caller, its `restore_root_adapters` call
  disappeared and the regression test that protected it was moved rather than
  preserved. Treat a moved assertion as a deleted assertion until its original
  invariant is shown to still hold.
- [LEARN:testing] When restoration only adds and overwrites and never deletes,
  the correct repairability test is subset, not equality. An equality check
  fails safe but withholds valid recovery advice for the ordinary case where
  the source gained a file the destination has not received yet.
- [LEARN:testing] A post-condition assertion placed after a step is only
  probative if the pre-condition was destroyed first. Asserting a file exists
  after `pull` proves nothing when the same assertion already passed after
  `setup`.
