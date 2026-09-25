# Session: Sidecar Phase F — reopen a completed big plan

**Date:** 2026-09-25
**Plan:** `.claude/plans/2026-09-25_phase-F-reopen-completed-big-plan.md`
**Status:** IN-PROGRESS

## Goal

Let the reopened big plan `consumer-sidecar-bootstrap-overlay` continue after
its completed knowledge-refresh phase E: change the plan validator so a
completed or cancelled, non-final knowledge-refresh phase no longer counts
toward "unique and last", and write the reopening procedure into the canonical
workflow instructions (big plan, Decision 21).

## Work Log

- 2026-09-25: two reviews of the completed Phases A-E
  (`.claude/quality_reports/2026-09-25_consumer-sidecar-bootstrap-overlay-review.md`
  and `...-review-2.md`) failed the branch. A read-only investigation of the
  workflow gates, tested in a scratch clone, showed that appending a phase
  after E fails the validator, inserting before E blocks the post-commit
  advance and the final gates, and renaming E breaks the receipt chain.
- User decisions: fix within this big plan with a validator change; four new
  phases F-I; move an edited copy of a taken skill into a backup folder in the
  Git directory; cover every confirmed finding plus an uninstall command and
  L1-L4.
- The big plan was reopened (`status: in-progress`, `current_phase` = this
  phase, Phases F-I appended, Decisions 21-36 added, design text updated). An
  independent review of the plan text found no blocker; its corrections were
  applied before approval.
- The first draft of this phase's slug ended in `-knowledge-refresh`; the
  validator counted it as a third refresh phase. Renamed to
  `2026-09-25_phase-F-reopen-completed-big-plan` before approval.
- Known state until this phase lands: the installed validator rejects the
  reopened big plan ("at most one knowledge-refresh phase is allowed, found
  2"), so no outer commit is possible. The scratch-tested rule accepts every
  real plan.
- User approved the plan on 2026-09-25. Phase F set to `in-progress`, and the
  nested `.claude` repository checkpointed (`2367c5f`).
- Owner change for plan step 4: the coder regenerates `dist/` only. The
  self-install (`install_bootstrap.py . --allow-self --local-only`) commits
  nested AI state, so the orchestrator runs it at closeout (MEMORY LEARN on
  `check_runtime.py` staleness in the authoring repository).
- IMPLEMENT: steps 1-3 and the `dist/` regeneration delegated to `coder`.
  Changed `scripts/validate_plan_frontmatter.py` (new
  `_knowledge_refresh_phase_settled`, rewritten
  `validate_knowledge_refresh_phase_position`),
  `tests/test_validate_plan_frontmatter.py` (9 new cases), and
  `shared/policies/workflow.instructions.md` (Termination paragraph and a new
  "Reopening a completed big plan" subsection). The planner, orchestrator,
  plan-decomposition, and template sources restate no rule, so they are
  unchanged. Coder checks: 635 validator and runtime tests passed; the
  canonical validator passed every real plan; ruff, mypy, and
  `validate_targets.py` passed.
- VERIFY: `verify.py phase --format text` PASS (ruff, mypy, 1892 tests).
- REVIEW: `reviewer` with `code`, `architecture`, `security`, `tests`,
  `ponytail`, and `documentation`. Orchestrator note for the fix loop: the
  new subsection calls the Knowledge-Refresh exemption "above", but that
  section comes later in the file.
- Review round 1: no CRITICAL or MAJOR. Two MINOR, both fixed rather than
  accepted: (1) `documentation`, the "above" cross-reference in the new
  subsection should say "below"; (2) `ponytail` shrink, the slug regex was
  duplicated in `scripts/validate_plan_frontmatter.py` instead of one
  module-level `PHASE_SLUG_PATTERN` constant. Fixes delegated to `coder`.
- Fix loop: `coder` fixed both; `verify.py phase --format text` PASS again
  (1892 tests). Review round 2 over the whole diff with all six profiles:
  both fixes confirmed, no findings (`[]`).
- CLOSEOUT step 1: `docs/runtime-checks.md` stated the old "at most one, and
  it must be last" rule (line 526); `documenter` updated that row. A focused
  `documentation` and `code` review of the row: no findings (`[]`).
- Self-install (`install_bootstrap.py . --allow-self --local-only`) ran
  before closeout; it committed nested state (`fba22bd`). The installed
  validator now passes every real plan, including the reopened big plan, and
  `check_runtime.py` passes.

## [LEARN] Entries

- [LEARN:workflow] Run `validate_plan_frontmatter.py` on every new or
  renamed phase slug before approval. The validator counts any slug ending in
  `-knowledge-refresh` as a knowledge-refresh phase, whatever the phase does:
  a first draft of this phase's slug was counted as a third refresh phase.
  The reopening procedure in `shared/policies/workflow.instructions.md` now
  warns about this, so MEMORY carries no separate entry for it.
- [LEARN:tooling] The protected-file guard refuses any Bash command that
  names a script under `.claude/hooks/scripts/`, even a read-only run of
  `session-start-state.sh`. Observe a hook's output at the next session
  start, or through tests that isolate `REPO_ROOT`; do not try to run it by
  hand. Added to MEMORY.

## Verification

Optional items:

- optional 1: NOT RUN — the protected-file guard refuses running `.claude/hooks/scripts/session-start-state.sh` from Bash, and this phase ends before a new session starts. Evidence instead: the scratch-clone investigation ran the real hook functions on the reopened shape and reported `phases done=5 pending=2, current_phase=...F...`; the installed validator now passes the reopened big plan; the next session start will show `phases done=6 pending=3` with Phase G current.

## Documentation

Updated in this phase: `shared/policies/workflow.instructions.md` (the
Termination paragraph of "Knowledge-Refresh Final Phase", and the new
"Reopening a completed big plan" subsection under "Branch Lifecycle") and the
knowledge-refresh row of `docs/runtime-checks.md`. `README.md` does not state
the rule, so it is unchanged. Generated copies were refreshed through
`generate_targets.py --all` and the self-install.

## Open Questions / Next Steps

- Next: Phase G (`2026-09-25_phase-G-sidecar-ownership-and-precedence`). The
  post-commit hook activates it after this phase's commit.
