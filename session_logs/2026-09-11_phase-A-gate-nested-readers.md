# Session: Gate the nested-state readers on a real nested repository

**Date:** 2026-09-11
**Plan:** `.claude/plans/2026-09-11_phase-A-gate-nested-readers.md`
**Status:** COMPLETED

## Goal

Make every nested-state reader in `shared/scripts/verify.py` report absence
when `.claude` is not its own Git repository, so Git can never answer from the
outer repository on its behalf; give the verifier one plain diagnostic for that
state; close the same blind spot in the installer's durability check; and prove
it with tests that build the real plain-directory shape and the measured
fail-open fixture.

## Why This Phase Exists

The prior session left `.claude/explorations/2026-09-11_nested-git-walkup-scope-confusion.md`
open, asking for independent confirmation and a severity ruling. This session
re-ran every reproduction against `dev` at `2258f18` (Git 2.43.0) and confirmed
all four findings: `nested_git_head` returned the outer HEAD; `indexed_nested_file`
and `nested_revision_file` returned the outer repository's bytes for the same
relative path (`git show :path` resolves from the repository root); and
`git status --porcelain` reported outer top-level `plans/<slug>.md` edits with
a spelling identical to the nested one, so `relevant_nested_status_changes` and
the status half of `nested_tracked_state_fingerprint` bound outer state. The
fingerprint also moved on an unrelated new outer file, so it bound all outer
dirty state, not only colliding paths.

The brief's "no exploit I can construct" was refuted by construction. With an
outer top-level `plans/` directory holding bytes identical to the nested plans
at receipt time, `.claude` gitignored by the outer repository, and any edit to
the outer plan file, `has_only_terminal_big_plan_change` returned `True`;
after committing the outer terminal plan,
`has_only_checkpointed_terminal_big_plan_change` returned `True`; and
`terminal_control_plane_provenance_matches` returned `True` in both cases,
including while the nested later-phase plan on disk was `status: in-progress`
and the outer mirror said cancelled. A control run with a genuine nested
repository refused that state. Without an outer `plans/` directory both
predicates returned `False`, so the realistic path fails closed.

Two further measurements shaped the fix. First, in the plain-directory state
the gates already refused every publish: `tracked_state_fingerprint` differed
between closeout and the post-commit push gate because dirty implementation
files vanish at commit. There was no working path for the fix to break.
Second, `validate_receipt` requires a hex `nested_head` for every receipt
including `fast` mode, so a consumer with no nested repository already died
with an uncaught `ValueError` traceback; the fix moves that failure earlier and
makes it legible.

## Work Log

- Re-ran reproductions A, B, and C from the brief in throwaway repositories;
  all confirmed. Added the unrelated-outer-file fingerprint measurement and the
  `ls-files --stage` subtree-scoping confirmation.
- Built the fail-open fixture the brief could not, including the checkpointed
  variant it had not considered, and the genuine-nested-repository control.
- Measured provenance stability across closeout and commit for both the
  tracked-`.claude` and gitignored-`.claude` variants of the plain-directory
  consumer; both fail the strict match after commit.
- Found the same walk-up primitive in `require_nested_head` in
  `scripts/install_bootstrap.py`; the migration path has a second check on the
  commit log, the setup path does not.
- Wrote the big plan and this single phase, created the implementation branch
  from a clean `dev`, and delegated implementation to `coder` with the exact
  fixture bytes. The coder confirmed all five new or changed tests failed on
  the pre-fix code by stashing only the source changes, then passed after.
- One existing assertion changed: `test_unpublishable_closeout_reason_skips_for_plain_nested_directory`
  asserted `nested_git_head(tmp_path) != ""` to document the walk-up; it now
  asserts `== ""`. No fixture had relied on the walk-up to produce receipts.
- Regenerated targets and installed locally; `validate_targets.py` had failed
  only on the stale generated copy and passes after regeneration.
- One review round across `code`, `architecture`, `security`, `tests`, and
  `ponytail` returned zero findings. The reviewer traced every caller of the
  five readers, every `verify.main()` invocation in tests and validators, and
  the outer-mirror fixture's pre-fix predicate chain, and confirmed
  `relevant_nested_status_changes` previously had no guard at all, so the diff
  tightens rather than loosens that path.

## Design Decisions

- All five readers are gated on the existing `nested_state_repository`
  predicate, not only the three content readers the measured fail-open depends
  on. Leaving `nested_git_head` and the fingerprint reading outer state would
  keep recording an outer SHA into receipts for an unsupported state.
- No `CONTROL_PLANE_PROVENANCE_SCHEMA_VERSION` bump. No field changes shape.
  A receipt recorded by the old code for a plain-directory consumer holds an
  outer SHA; against a real nested repository `nested_revision_file` returns
  `None` for it, the gate reports stale, and a closeout re-run replaces it.
- The `main()` diagnostic runs before `state_metadata` in every mode except
  `gate`, which reads persisted receipts and must keep reporting its own
  errors. It exits 2, matching the existing pre-persist refusals, and names
  the same remediation as `unpublishable_closeout_reason`.
- Neither terminal predicate, the strict comparison, nor the
  `unpublishable_closeout_reason` precondition changed.
- The Phase B closeout log's "Known gap, deliberately left open" entry is
  receipt-bound; its existing sibling errata file gained a Resolution section
  instead.

## Stale-claims surfaces checked

- `docs/architecture.md` — the Git-backed state sync section said only the
  closeout precondition looked for `.claude/.git`; replaced with a paragraph
  stating every nested-state reader does, naming the three walk-up behaviors
  and the new diagnostic.
- `docs/runtime-checks.md` — added the plain-directory diagnostic and its exact
  message before the root-adapter provenance paragraph.
- `docs/smoke-tests.md` — checked; describes `state-sync.sh` subcommands only,
  no stale claim.
- `README.md` — checked; no mention of nested provenance readers, no change.
- `CLAUDE.md`, `AGENTS.md`, `shared/policies/*.md`, `shared/agents/*`,
  `shared/skills/*/SKILL.md` — searched for `walks up`, `provenance is
  unavailable`, `nested_state_repository`, and `rev-parse --verify HEAD`; no
  live-advice claim about the readers, no change.
- `.claude/explorations/2026-09-11_nested-git-walkup-scope-confusion.md` —
  status changed from OPEN to RESOLVED with a pointer to this plan and log.
- `.claude/session_logs/2026-09-11_phase-B-terminal-publication-recovery.errata.md`
  — appended a Resolution section; it previously said the issue was open and
  unfixed. The bound Phase B log itself was left unchanged.
- `.claude/MEMORY.md` — three new LEARN entries below; the earlier walk-up
  entries remain accurate and were kept.
- `tests/fixtures/schema-v3-verify.py.txt` — unchanged, confirming no
  provenance schema change.
- Runtime mirrors `.claude/` and `dist/multi-agent/` — regenerated and
  self-installed; `validate_targets.py` confirms the generated copies match.
- Dated records under `.claude/plans/` and earlier `.claude/session_logs/`
  were left alone as historical.

## [LEARN] Entries

- [LEARN:review] `git -C <dir>` is never a repository test, and it is not only
  `rev-parse` that walks up: `git show :path` resolves the path from the
  repository root, and `git status --porcelain` reports repository-root paths,
  so a plain `.claude` inside an outer repository returns outer file bytes and
  outer dirty paths spelled exactly like nested ones. When one reader in a
  family is found walking up, gate the whole family on the `.git` entry.
- [LEARN:testing] A fail-open reproduction must include the state the gate is
  meant to refuse, then a control run on the supported shape must refuse it.
  The walk-up predicates accepted an un-cancelled nested later-phase plan from
  an outer `plans/` mirror; the genuine nested repository refused it.
- [LEARN:review] Before ruling that a fix would break a documented state,
  measure whether that state works today. The plain-directory consumer already
  failed every publish gate, so gating the readers cost nothing.

## Verification Results

Final state, with targets regenerated and locally self-installed beforehand:

```text
uv run pytest tests/ -q --tb=short                       1456 passed
uv run mypy shared scripts tests                         no issues in 28 source files
uv run ruff check shared scripts tests                   All checks passed
uv run ruff format --check shared scripts tests          28 files already formatted
uv run python scripts/generate_targets.py --all          regenerated
uv run python scripts/install_bootstrap.py . --allow-self --local-only   installed
uv run python scripts/validate_targets.py                PASS generated target is structurally valid
uv run python scripts/check_runtime.py                   all PASS
uv run python .claude/scripts/verify.py fast             PASS
review: code, architecture, security, tests, ponytail    0 findings
```

Receipts: `.claude/quality_reports/verification-phase-2026-09-11_phase-A-gate-nested-readers.json`
and `.claude/quality_reports/verification-closeout-2026-09-11_phase-A-gate-nested-readers.json`,
findings at `.claude/quality_reports/findings-2026-09-11_phase-A-gate-nested-readers.json`.

## Open Questions / Next Steps

1. `is_relevant_nested_path` treats any first path component outside
   `NESTED_MUTABLE_STATE_ROOTS` as governing. That is correct for nested
   spellings and is now unreachable from outer spellings, so no change is
   needed, but a future reader that runs Git outside `.claude` would need the
   same care.
2. The drift gate for this repository's hand-maintained root `CLAUDE.md` and
   `AGENTS.md`, recorded as open in Phase A of the previous big plan, remains
   open.
