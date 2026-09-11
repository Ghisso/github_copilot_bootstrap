# Errata: 2026-09-11_phase-B-terminal-publication-recovery

The closeout log is hash-bound by that phase's closeout receipt, so this
correction is a sibling errata file rather than an edit to the log.

## Correction to "Known gap, deliberately left open"

That section says only that `nested_git_head` "walks up to the outer repository
for every caller, including `control_plane_provenance`'s recorded `nested_head`",
and concludes that "nothing in this phase depends on it" and "no current gate is
affected".

The first part is accurate but incomplete, and the conclusion is stated with more
confidence than the evidence supported at the time. Investigation after the phase
closed established two further facts:

1. The nested file readers do not merely resolve the wrong `HEAD` — they return
   the wrong file's **contents**. With `.claude` lacking its own `.git` and the
   outer repository holding the same relative path at its root, both
   `indexed_nested_file` and `nested_revision_file` returned outer-repository
   bytes while a different nested file of that relative path existed on disk.
2. `git status --porcelain` reports repository-root-relative paths, so run inside
   a `.git`-less `.claude` an edit to the outer repository's top-level
   `plans/<slug>.md` is reported as exactly `plans/<slug>.md` — byte-identical to
   the nested-relative spelling the code expects. `relevant_nested_status_changes`
   and `nested_tracked_state_fingerprint` therefore cannot distinguish outer from
   nested edits, and the fingerprint was measured changing in response to outer
   state it should not bind at all.

Five call sites are affected, none changed by `f92fe22`:
`control_plane_provenance`, `nested_tracked_state_fingerprint`,
`relevant_nested_status_changes`, `indexed_nested_file` /
`nested_revision_file`, and `has_only_checkpointed_terminal_big_plan_change`.

The scoping decision the log records — leaving this out of Phase B — still stands.
The assessment that "no current gate is affected" should be read as unproven
rather than established: the observed failure direction is fail-closed, but a
theoretical substitution path through `has_only_terminal_big_plan_change` was
identified and not ruled out.

## Where this is now tracked

`.claude/explorations/2026-09-11_nested-git-walkup-scope-confusion.md` holds the
full brief, the reproductions, the severity reasoning, and the open questions.

## Resolution (2026-09-11)

The independent ruling confirmed every finding above and refuted the
"no current gate is affected" conclusion by measurement: with an outer
top-level `plans/` directory mirroring the nested plan bytes at receipt time,
`has_only_terminal_big_plan_change`,
`has_only_checkpointed_terminal_big_plan_change`, and
`terminal_control_plane_provenance_matches` all returned `True`, including
while a nested later-phase plan on disk was not cancelled. A genuine nested
repository refused the same state. The ruling also measured that the
plain-directory consumer already failed every publish in the normal flow, so
gating the readers could not break a working path.

Fixed by big plan `.claude/plans/2026-09-11_nested-walkup-gating.md`: all five
readers are gated on `nested_state_repository`, `verify.py` exits 2 with a plain
message in that state, and the installer's `require_nested_head` checks for
`.claude/.git` before asking Git. See
`.claude/session_logs/2026-09-11_phase-A-gate-nested-readers.md`.
