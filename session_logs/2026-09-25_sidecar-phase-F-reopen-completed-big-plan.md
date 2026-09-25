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

## [LEARN] Entries

## Verification

## Documentation

## Open Questions / Next Steps
