---
name: consumer-upgrade-notes
type: big-plan
status: in-progress
originating_branch: dev
implementation_branch: consumer-upgrade-notes_implementation
phases:
  - 2026-09-03_phase-1-consumer-upgrade-notes
current_phase: 2026-09-03_phase-1-consumer-upgrade-notes
started_at: 2026-09-03T07:34:05Z
---

# Big Plan — Consumer Upgrade Notes

**Date:** 2026-09-03
**Branch base:** `dev`
**Scope:** bootstrap authoring repo documentation only.

## 1. Goal

Document what a consumer must do when refreshing onto the runtime that
`verification-gate-semantic-hardening` produced, so an operator refreshing a
project is not surprised by a newly blocking gate.

## 2. Why this is needed

The seven phases merged as PR #29 added several gates that did not exist
before. Refreshing three real consumer projects surfaced that two of them
would be blocked immediately, and nothing in the repository told the operator
that in advance:

- `industrial-inspection` carries a small plan with `status: planned`, which
  was never a valid status but only became a **hard commit gate** once Phase 2
  shipped `validate_plan_frontmatter.py` to consumers. Measured: the shipped
  validator reports `invalid status for small-plan: planned`.
- All three projects have unformatted tracked files (2, 1, and 6
  respectively). Phase 6 folded `ruff format --check` into `VFY-RUFF-001`, so
  formatting is now gate-blocking where it previously was documented but never
  enforced.
- Phase 7 made `.claude/<state-dir>/README.md` bootstrap-owned, so a refresh
  now overwrites those four files. A consumer who hand-edited one loses it.
- Phase 3 removed the `MEMORY.md` mtime shortcut, so an existing closeout log
  that relied on it no longer satisfies the LEARN contract.
- Phase 7 requires a big plan's final phase to carry
  `## Stale-claims surfaces checked` in its closeout log.
- Phase 1 bumped the receipt schema to v4 and rejects v3 unconditionally.

The mid-plan receipt case is already documented from Phase 6's work. The rest
is not, and the operator-facing consequence of each is what is missing.

## 3. Settled behavior

Add one operator-facing section that states, for each newly blocking gate,
what changed and the exact recovery command. It must be findable from where an
operator actually looks — the README's consumer-refresh path and
`docs/runtime-checks.md` — rather than only in a plan or session log.

Prefer extending the existing mid-plan upgrade guidance over creating a new
parallel document, so there is one place an operator reads before refreshing.

Every recovery instruction must be one a reader can run verbatim, and must be
verified to work rather than asserted.

## 4. Non-goals

- Do not change any gate's behavior, strictness, or scope. This is
  documentation only.
- Do not weaken a gate to make an upgrade easier.
- Do not patch consumer repositories from here.
- Add no compatibility allowance.

## Phase

- `2026-09-03_phase-1-consumer-upgrade-notes` — document the newly blocking gates and their recovery in the README and runtime-checks docs.

## 5. Acceptance criteria

1. An operator refreshing a consumer can find, before running the refresh,
   every gate that newly blocks and its recovery command.
2. Each documented command is verified to run.
3. The plan-frontmatter status vocabulary is stated, since `planned` looked
   plausible and is not valid.
4. The state-directory README overwrite is disclosed as a behavior change.
5. Documentation and gate agree; no new stale claim is introduced.
6. Full repository tests and validation pass with no regeneration drift.
