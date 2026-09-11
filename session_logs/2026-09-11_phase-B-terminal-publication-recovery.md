# Session: Terminal publication recovery

**Date:** 2026-09-11
**Plan:** `.claude/plans/2026-09-11_phase-B-terminal-publication-recovery.md`
**Status:** COMPLETED

## Goal

Make the terminal completion commit of a big plan publishable, give a stale
terminal receipt an honest recovery path, and stop recommending a refresh that
destroys the receipt chain.

## Why This Phase Exists

Phase A added an automatic outer-repository push after every successful commit,
then could not publish its own completion commit. The pre-push gate denied it
with `closeout receipt governing control-plane provenance is stale`.

The cause was a binding mismatch, not a missing feature. The terminal allowance
already existed: `terminal_control_plane_provenance_matches` ignores
`nested_head`, `tracked_state_fingerprint`, and `big_plan_digest`. But
`control_plane_provenance` records `big_plan_digest` from the big plan's
working-tree bytes, while its two gating predicates compare that digest against
the nested Git index (`has_only_terminal_big_plan_change`) or the blob at the
recorded nested `HEAD` (`has_only_checkpointed_terminal_big_plan_change`). A
big plan dirty in nested state when the receipt is persisted records a digest
that is neither indexed nor committed, so no later state can make it match.

Measured on this branch: recorded `668abceb8418...`, blob at recorded
`nested_head` `49c9654442...`, index and working tree `16db36e14e...`. All
three differ. `runtime_fingerprint` and `small_plan_digest` matched.

A multi-phase big plan hides this, because each intermediate commit checkpoints
nested state and leaves the big plan clean by final closeout. This plan had one
phase, so ticking its `## Phases` checkbox during closeout had no intervening
commit to absorb it.

Two secondary defects travelled with it. `verify.py` persisted a receipt before
checking that receipt's own status, so `--persist` on a failing run overwrote a
passing receipt with a failing one. And the complete-big-plan refusal message
recommended refreshing the phase receipt alone, which invalidates the closeout
receipt's bound `phase_receipt` hash. Running that suggestion made the state
worse, not better; the committed receipt bytes were restored afterward.

## Work Log

- Reopened the big plan and appended this phase rather than starting a new
  implementation branch. The fix depends on Phase A's `certified` route and
  `git_is_direct_child`, which exist only on this branch, and branch creation
  is gated on starting from a clean `dev`.
- Confirmed that reopening the plan let commit `05adbcc` publish through the
  intermediate `certified` route, because Phase A became a completed
  predecessor of an in-progress phase and that route passes
  `enforce_final_state=false`. Recorded plainly that this is a deferral of the
  strict terminal check, not an escape from it.
- Verified Phase A's three hash-bound artifacts stayed intact throughout.
- Wrote the failing harness before the fix, as the plan required.
- Added the persist-time precondition, the corrected recovery message, the
  persist guard, and the single-phase publication validator.
- Reordered the closeout ceremony so nested plan state is checkpointed after
  the plan, log, and memory edits are final and before the findings and
  receipts are persisted. This replaced guidance that said the opposite.
- Completed two review rounds across `code`, `architecture`, `security`,
  `tests`, and `ponytail`. Round one returned one CRITICAL, one MAJOR, and two
  MINOR findings; all four were fixed.

## Review Findings And Resolutions

- CRITICAL (`code`) — the no-nested-repository escape in
  `unpublishable_closeout_reason` did not fire. `nested_git_head` runs
  `git -C .claude rev-parse HEAD`, which walks *up* the directory tree when
  `.claude` has no `.git` of its own and resolves the outer repository's HEAD
  instead of failing. I reproduced this independently before fixing it: in a
  temp repository with `.claude` as a plain tracked directory, the returned SHA
  was byte-identical to the outer HEAD, so the guard never fired and
  `nested_revision_file` returned `None`, forcing the refusal for every phase's
  closeout. That is the documented `migrate-from-hf` consumer shape. Fixed by
  adding `nested_state_repository`, which tests for `.claude/.git` directly.
  `nested_git_head` itself was left alone: it walks up for every caller,
  including `control_plane_provenance`'s recorded `nested_head`, and changing
  that would alter provenance recording well beyond this phase.
- MAJOR (`architecture`) — the plan named three ceremony surfaces and only two
  were updated. `shared/skills/commit/SKILL.md` is separately invokable and
  restated a subset of the same sequence while saying nothing about the
  checkpoint in either direction, so anyone following only that skill could
  reproduce the defect this phase fixes. Added the ordering rule there.
- MINOR (`ponytail`) — the fetch-hash-compare sequence was duplicated between
  `unpublishable_closeout_reason` and
  `has_only_checkpointed_terminal_big_plan_change`. Extracted
  `plan_bytes_matching_digest`, which returns the bytes when they hash to the
  recorded digest, so the predicate still gets `source` for its
  `terminal_big_plan_bytes` call.
- MINOR (`tests`) — the persist guard was documented as covering every mode but
  exercised only through `closeout`. Added a `phase`-mode test, which needed a
  separate `_phase_check_list` helper because phase mode's fixed applicability
  differs: only `VFY-RECEIPT-001` may be `NOT_APPLICABLE` there.

Round two returned zero findings.

The reviewer also confirmed four scrutiny points as clean: `quality_reports/`
and `session_logs/` are in `NESTED_MUTABLE_STATE_ROOTS` and excluded from
`is_relevant_nested_path`, so writing findings and receipts after the
checkpoint is genuinely harmless as the new guidance claims; the persist guard
cannot block a legitimately passing run; and neither terminal predicate, the
provenance schema version, nor the strict `assert_closeout_invariants` path
used by `gh pr create` was relaxed.

## Test Adequacy

The implementer disclosed, correctly, that the new validator's final push
assertion is not a differential test of the persist-time precondition: once the
harness follows checkpoint-then-re-persist, the second persist writes correctly
bound bytes with or without the fix, so the push passes either way. The
genuinely fix-gated assertions are the dirty-state refusal and the
no-write-behind. The push assertion is kept because it proves the recommended
single-phase ceremony is publishable end to end, which is the shape that broke.

Both security-relevant guards were proven load-bearing by mutation:

- Removing the `nested_state_repository` gate failed the new plain-directory
  test while the pre-existing `skips_without_nested_repository` test still
  passed — exactly the blind spot the reviewer identified.
- Disabling the persist guard failed its own test.
- Swapping the recovery message's command order failed its ordering test.

## [LEARN] Entries

- [LEARN:security] A receipt must only bind bytes that Git already holds. The
  closeout receipt recorded a working-tree digest while the push predicates
  re-derive it from a nested revision, so a plan dirty at persist time bound a
  digest that existed nowhere and made the completion commit permanently
  unpublishable.
- [LEARN:workflow] Adding a phase to a big plan defers the strict terminal
  check; it never escapes it. The new final phase meets the same gate with no
  later phase to rescue it, so the deferral must never be treated as the fix.
- [LEARN:review] `git -C <dir> rev-parse HEAD` walks up the directory tree, so
  it cannot answer whether a directory is its own repository. Test for the
  `.git` entry instead.
- [LEARN:testing] A fixture that works around a hazard instead of reproducing
  it reports protection that is not being verified. The first escape-hatch test
  omitted `.claude` entirely, with a comment explaining it was avoiding the
  walk-up behavior that was itself the defect.
- [LEARN:quality] Check a persist path's ordering against its own status gate.
  `--persist` wrote the receipt before returning on status, which is what
  turned a misleading recovery hint into a destructive one.

## Stale-claims surfaces checked

Repository-wide sweep required by the big plan's `## Completion Evidence`, run
for its last phase. This phase inverted an existing ceremony rule, so the sweep
targeted every surface stating the old ordering as well as the push surfaces
Phase A touched. Each entry was verified against current code.

### Corrected

- `shared/policies/workflow.instructions.md` — the CLOSEOUT step list gained
  the checkpoint as step (b), renumbering staging, findings, and the two
  receipt steps to (c)-(f). The trailing rule previously read "Do not manually
  commit or checkpoint the nested `.claude` AI-state repository during
  CLOSEOUT: leave those changes uncommitted while (c)-(e) run", which is
  precisely what produced the defect. Rewritten to state both directions: check
  point after the plan, log, and memory edits are final, and never after the
  receipts are persisted.
- `shared/agents/orchestrator/prompt.md` — same inversion in the CLOSEOUT
  stage, corrected the same way.
- `shared/skills/commit/SKILL.md` — Phase 3 restated the sequence without the
  checkpoint in either direction. Added the rule, the command, and the reason.
- `docs/runtime-checks.md` — the paragraph beginning "The relevant nested
  tracked/dirty state that provenance binds to is not informational" told the
  reader explicitly not to checkpoint before `verify.py closeout --persist`.
  Replaced with the exact two-directional ordering, the reason grounded in the
  digest binding, the new fail-closed precondition, the persist guard, and the
  corrected recovery sequence with its working-tree precondition.
- `docs/architecture.md` — added the closeout precondition and the
  `.claude/.git` exemption rule to the lifecycle hook section.
- `docs/smoke-tests.md` — added acceptance lines for single-phase terminal
  publication, the negative digest case, the persist guard, and the recovery
  message ordering.
- `README.md` — the numbered post-refresh evidence sequence gained the
  checkpoint as step 3 and now states why its position is exact.

### Verified consistent, no change needed

- Root guidance `CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`,
  `.codex/`, `.agents/` — carry Phase A's `COMMIT -> PUSH` lifecycle and make no
  claim about nested-state ordering.
- `shared/hooks/scripts/` — no script comment or user-facing message stated the
  old ordering. `state-sync.sh` messages remain nested-scoped; its `checkpoint`
  dispatch warns and continues on failure, so a failed checkpoint leaves the new
  refusal in place rather than silently proceeding.
- `shared/policies/` — the remaining instruction files make no ordering claim.
  `quality-and-testing.instructions.md` is gate-contract text only.
- `shared/agents/` — `coder`, `planner`, `documenter`, `reviewer`, and the
  provider-specific coders make no nested-state ordering claim.
- `shared/skills/` — `safe-consumer-bootstrap-refresh` is local-only nested
  sync; `plan-decomposition` and `context-status` make no ordering claim.
- `shared/templates/` — plan and session-log templates make no ordering claim.
- `scripts/` — `generate_targets.py`, `validate_targets.py`, `check_runtime.py`,
  `install_bootstrap.py`, `update_consumers.py` carry no stale ordering text.
- `tests/` — no test asserted the old ordering. One dirty-big-plan assertion in
  `tests/test_install_bootstrap.py` moved from exit 1 to exit 2 because that
  case is now caught earlier and more precisely; the source and small-plan
  mutations in the same test still exit 1, which is correct since the new
  precondition covers only the big plan.
- Runtime mirror `.claude/` and `dist/multi-agent/` — regenerated and
  self-installed after every source edit; confirmed all three ceremony surfaces
  carry the new ordering in both generated trees.
- `tests/fixtures/schema-v3-verify.py.txt` — unchanged, confirming no
  provenance schema change and no invalidated existing receipts.
- Dated records under `.claude/plans/` and earlier `.claude/session_logs/` were
  left alone as historical, per the standing final-phase audit rule. Phase A's
  three hash-bound artifacts were confirmed untouched.

### Known gap, deliberately left open

`nested_git_head` walks up to the outer repository for every caller, including
`control_plane_provenance`'s recorded `nested_head`. For a consumer whose
`.claude` is a plain directory, that records the outer HEAD as the nested head.
Nothing in this phase depends on it, and `nested_head` is treated as
informational by both provenance comparisons, so no current gate is affected.
Changing it would alter provenance recording beyond this phase's scope.

This repository's own root `CLAUDE.md` and `AGENTS.md` remain hand-maintained
authoring variants that no gate validates, as recorded in Phase A's log. Adding
a drift gate for them, mirroring `stale_skill_contract_errors`, is still open.

## Verification Results

Final state, with targets regenerated and locally self-installed beforehand:

```text
uv run pytest tests/ -q --tb=short            1452 passed
uv run python scripts/validate_targets.py     exit 0
uv run python scripts/check_runtime.py        20 PASS, 0 FAIL
uv run python .claude/scripts/verify.py fast  PASS
uv run mypy shared scripts tests              no issues in 28 source files
uv run ruff check shared scripts tests        All checks passed
uv run ruff format --check shared scripts tests   28 files already formatted
generate_targets.py --all                     regenerated
install_bootstrap.py . --allow-self --local-only  installed
```

## Open Questions / Next Steps

1. Consider whether `nested_git_head` should resolve only a genuine nested
   repository, rather than walking up. See the known gap above.
2. Consider a drift gate for this repository's hand-maintained root guidance,
   mirroring `stale_skill_contract_errors`.
