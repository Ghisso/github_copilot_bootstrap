# OpenWiki Phase C: Lifecycle Integration

**Status:** IN PROGRESS
**Plan:** `.claude/plans/2026-09-19_phase-C-openwiki-lifecycle-integration.md`

## Goal

Teach the lifecycle how an OpenWiki-enabled big plan ends: a small final knowledge-refresh
phase. Narrow documenter, learn, and onboard so they stop duplicating facts OpenWiki can
regenerate. Repositories without the enablement marker keep the current lifecycle unchanged.

## Approach

- One canonical statement of the knowledge-refresh phase rule; every other location links to it.
  This follows the Phase B pattern that worked, and avoids the one failure Phase B had.
- The disabled-repository path must be provably unchanged, not merely intended to be.
- No recursion: a plan whose purpose is already a knowledge refresh must not gain another
  refresh phase.

## Inherited Context

- Phase A: the runner, with five documented residual limits.
- Phase B: the canonical Knowledge Ownership contract in
  `shared/policies/workspace.instructions.md`, and `shared/skills/openwiki/SKILL.md`.
  Phase C must link to that contract rather than restate it.

## Carried-Forward Lesson From Phase B

Phase B's only defect came from retyping one sentence into a second file instead of copying it,
which produced three drifts at once including a path no skill-loading runtime reads. Phase C
touches more files with more shared wording, so the same rule applies with more force: one
canonical home, links everywhere else, and copy rather than retype wherever a restatement is
genuinely required.

## Progress

- Phase B committed and pushed as `04fd159`; both repositories clean.
- Big plan `current_phase` advanced to Phase C by the branch hooks.

## Verification

Pending.

## Review

Pending. Profiles required: `code`, `architecture`, `security`, `tests`, `ponytail`,
`documentation`.

## [LEARN] Entries

Pending.

## Remaining Work

- C1 planning rule, C2 orchestrator/workflow integration, C3 documenter/learn/onboard narrowing,
  C4 review and closeout.
