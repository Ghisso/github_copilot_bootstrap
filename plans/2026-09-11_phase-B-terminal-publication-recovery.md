---
name: 2026-09-11_phase-B-terminal-publication-recovery
type: small-plan
parent_plan: 2026-09-11_outer-repo-auto-push
phase_index: 2
status: in-progress
closeout_session_log: .claude/session_logs/2026-09-11_phase-B-terminal-publication-recovery.md
---

# Small Plan: Terminal publication recovery

## Scope

Phase A added an automatic outer-repository push after every successful commit,
but Phase A's own completion commit could not be pushed. The push gate denied
it with `closeout receipt governing control-plane provenance is stale`. This
phase fixes the cause so the last commit of a big plan is publishable, and
gives a stale terminal receipt an honest recovery path instead of one that
breaks the receipt chain.

The cause is a binding mismatch, not a missing feature. `control_plane_provenance`
records `big_plan_digest` from the big plan's working-tree bytes
(`digest_file(big_plan)`). The two predicates that authorize a terminal push
compare that recorded digest against the nested Git index
(`has_only_terminal_big_plan_change`) or against the blob at the recorded
nested `HEAD` (`has_only_checkpointed_terminal_big_plan_change`). When the big
plan is dirty in the nested state repository at the moment the closeout receipt
is persisted, the recorded digest matches neither, and no later state can ever
make it match.

A multi-phase big plan hides this, because each intermediate phase's commit
checkpoints nested state, so the big plan is already committed by final
closeout. This big plan had one phase, so ticking its `## Phases` checkbox
during closeout left the big plan dirty at receipt time with no intervening
commit to absorb it.

## Findings This Plan Is Built On

All measured on branch `2026-09-11_outer-repo-auto-push_implementation`.

The recorded `big_plan_digest` was `668abceb8418...`. The blob at the recorded
`nested_head` (`8d0d291a`) was `49c9654442...`. The nested index and working
tree were `16db36e14e...`. All three differ. `runtime_fingerprint` and
`small_plan_digest` match, and `nested_head` plus `tracked_state_fingerprint`
are ignored by the terminal allowance, so the big-plan digest is the only real
divergence.

`verify.py` persists a receipt before it checks that receipt's own status: the
`if args.persist:` block precedes the `return 0 if receipt["status"] in {...}`
line. So `--persist` on a failing run overwrites a previously passing receipt
with a failing one, and the push gate rejects any non-passing closeout receipt.
This is why the refresh suggestion in the refusal message is worse than
useless: it does not merely fail, it destroys the only valid evidence.

Remedy (D) from the original framing needs no new code. The
`no active phase: the big plan is complete` refusal lives inside `if not phase:`
in `unresolved_phase_reason`, and `state_metadata` already honours
`args.phase`, so `closeout --persist --phase <slug>` on a complete big plan
already works. The only defect is that the message recommends mode `phase`
alone, which refreshes the phase receipt and invalidates the closeout receipt's
bound `phase_receipt` hash. The fix is an honest message, not a new capability.

Commit `05adbcc` is unblocked by opening this phase, not by any code change.
`assert_push_invariants` routes on the big plan's status: the `complete` route
calls `assert_closeout_invariants` with `enforce_final_state=true`, and that
flag is the sole guard on the provenance freshness check, while the
completed-phase `certified` route passes `enforce_final_state=false`. Phase A
is now a completed predecessor of an in-progress Phase B, so the push takes the
certified route. That route still requires the receipt head to be the direct
parent of the pushed commit, a matching `tree_sha`, zero critical findings,
untampered artifacts, Ponytail evidence, and every prior phase terminal. It
skips only certification of the final branch state, which is correct, because
the branch is not final.

This is why the phase is mandatory rather than optional cleanup. Adding a phase
defers the strict check; it never escapes it. Phase B's own completion commit
will hit the identical wall, and there will be no Phase C to rescue it.

## Remedy Evaluation

Recording an index or `HEAD` digest instead of the working tree is rejected.
Nothing stages the big plan before the receipt, so the recorded digest would
certify bytes that are not what closeout produced. It also removes the strict
path's only detector of a working-tree edit to the big plan:
`nested_tracked_state_fingerprint` hashes `git status --porcelain` records,
which carry the state letter and path rather than content, so it cannot cover
the gap. That would weaken the same strict path `gh pr create` relies on.

Extending the terminal predicates to accept a dirty-at-receipt digest is
rejected because it cannot be bounded. The dirty bytes are free-form prose and
are not reconstructible from the `HEAD` blob, so bounding it would mean
dropping the digest match — and that digest is the only thing identifying which
bytes the receipt certified. Without it, `terminal_big_plan_bytes` would
validate a frontmatter transition against an unauthenticated source. It also
recovers nothing the certified route does not already recover.

The primary approach is to refuse to persist a closeout receipt the terminal
gate could never accept, plus the honest-message and persist-guard fixes. This
preserves every existing binding, changes no predicate, and does not touch
`CONTROL_PLANE_PROVENANCE_SCHEMA_VERSION`, so existing receipts and
`tests/fixtures/schema-v3-verify.py.txt` stay valid.

State the precondition against the nested `HEAD`, not the index, because that
is what the surviving predicate needs. Evaluate the predicate's own test at
persist time, using the receipt's recorded values: read
`nested_revision_file(root, recorded["nested_head"], f"plans/{slug}.md")` and
require it to exist and to hash to `recorded["big_plan_digest"]`. That is
provably equivalent to "the terminal push gate can accept this receipt", with
no duplicated intent. It needs no special case for a re-persist after the
terminal transition: in that state the working tree, index, and `HEAD` blob
agree, so the condition holds and the strict path passes at push time.

Fail-closed boundary: apply the precondition only when nested provenance is
available, meaning `.claude` is a Git repository and `nested_git_head(root)` is
non-empty. A consumer with no nested state repository must keep working
unchanged; that configuration already surfaces through the separate
provenance-unavailable path.

## Decisions

- Step 1 is a pre-persist refusal that exits non-zero and writes nothing,
  matching the existing documentation-not-applicable precedent, rather than a
  new `VFY-FRESH-003` check that would write a failing receipt. Preserving the
  prior receipt is the whole point. If review prefers visible receipt evidence,
  the check form is the fallback.
- The precondition applies to every phase's closeout, not only the terminal
  one. It needs no new classification logic and keeps behavior predictable.
- The Step 4 persist guard covers all modes, narrowing to `closeout` only if a
  validator harness turns out to depend on overwriting a passing receipt.
- The remediation command is `bash .claude/hooks/scripts/state-sync.sh checkpoint`,
  confirmed to take no arguments. Note its dispatch warns and continues on
  failure, so a failed checkpoint leaves the refusal in place rather than
  silently proceeding.

## Steps

- [ ] Refuse to persist an unpublishable closeout receipt. In `main()` of
  `shared/scripts/verify.py`, add one function shaped like the existing
  `missing_documentation_na_reason` handling, for example
  `unpublishable_closeout_reason(root, metadata) -> str | None`. Return `None`
  when the mode is not `closeout`, when nested provenance is unavailable, or
  when the recorded `big_plan_digest` equals the digest of
  `nested_revision_file(root, recorded_nested_head, f"plans/{slug}.md")`.
  Otherwise return a message naming the cause and the remediation. Print to
  stderr and return non-zero before the `if args.persist:` block so nothing is
  written and the prior receipt survives. Reuse `nested_revision_file`,
  `nested_git_head`, and `active_big_plan_path`. Do not add a provenance field,
  change the provenance schema version, or modify either terminal predicate.
  Cover in `tests/test_verify.py`: a dirty big plan refuses and writes nothing;
  a checkpointed big plan persists normally; no nested repository skips the
  precondition; a re-persist after the terminal transition passes.
- [ ] Make the closeout ceremony checkpoint nested plan state before persisting
  the closeout receipt. Update `shared/policies/workflow.instructions.md`,
  `shared/agents/orchestrator/prompt.md`, and the commit skill under
  `shared/skills/` that owns the CLOSEOUT sequence. Make the ordering explicit:
  edit the plan files, then checkpoint nested state, then persist the closeout
  receipt. State the reason in one sentence — the receipt binds the big plan's
  bytes, and the automatic push after the completion commit can only verify
  bytes Git already holds. Name one command exactly; do not invent a new script.
- [ ] Replace the misleading refresh suggestion in `shared/scripts/verify.py`.
  The complete-big-plan message currently recommends
  `phase --format json --persist --phase <slug>` alone, which invalidates the
  closeout receipt's bound `phase_receipt` hash and adds
  `closeout receipt artifact phase_receipt was tampered with`. Recommend both
  commands in order — `phase --persist --phase <slug>` then
  `closeout --persist --phase <slug>` — because the closeout receipt records the
  phase receipt's digest at its own persist time, so the second heals the
  binding the first breaks. State the precondition the recovery needs: the
  working tree must still match the commit being certified, since
  `VFY-FRESH-001` compares code evidence against current state and the gate
  compares `tree_sha` against the commit's tree. Assert in `tests/test_verify.py`
  that the message names both modes in order and that a phase-then-closeout
  refresh leaves no `tampered with` error.
- [ ] Never overwrite a passing receipt with a failing one. In the
  `if args.persist:` block of `shared/scripts/verify.py`, refuse the write when
  the target receipt path already holds a receipt with `status == "PASS"` and
  the new receipt does not; explain why and exit non-zero. Leaving the previous
  passing receipt is safe because its own `head_sha`, `merge_base_sha`, and
  `tree_sha` freshness checks already reject it once stale, so this cannot turn
  a stale pass into an accepted one. Keep persisting failing receipts when no
  passing receipt exists. Cover both directions in `tests/test_verify.py`.
- [ ] Prove a single-phase big plan can publish its terminal commit. Add a
  validator to `scripts/validate_targets.py` beside
  `validate_end_to_end_receipt_chain_lifecycle` and
  `validate_completed_phase_stale_receipt_rejection`, reusing their local
  bare-remote pattern so nothing touches the network. Build a repository with a
  nested state repository and a big plan holding exactly one phase, then assert
  in order: closeout refuses to persist while the big plan is dirty and any
  prior receipt is unchanged; after checkpointing, closeout persists a passing
  receipt; the completion commit succeeds and the post-commit transition runs;
  and the push to the local bare remote succeeds. Also assert the negative: a
  receipt whose recorded `big_plan_digest` matches neither the nested `HEAD`
  blob nor the index is still rejected, so the fix is not a blanket allowance.
  Do not weaken `validate_completed_phase_stale_receipt_rejection`.
- [ ] Regenerate the target adapters and install locally with
  `uv run python scripts/generate_targets.py --all` then
  `uv run python scripts/install_bootstrap.py . --allow-self --local-only`.
  Never hand-edit generated files. The hook gate reads
  `.claude/scripts/verify.py`, so an unregenerated tree tests the old code.
- [ ] Perform the final documentation, memory, and LEARN audit. This phase is
  the last entry in the big plan's `phases:` list, so the audit must sweep every
  live-advice surface, not only what this phase changed. Document the new
  closeout precondition, the corrected recovery sequence, and the persist guard
  in `docs/runtime-checks.md`, `docs/architecture.md`, `docs/smoke-tests.md`,
  and `README.md` as needed. Record in `.claude/MEMORY.md` that a receipt must
  only bind bytes Git already holds, and that adding a phase defers the strict
  terminal check rather than escaping it. Record audited surfaces and outcomes
  under the exact heading `## Stale-claims surfaces checked` in this phase's
  closeout session log. Do not modify any file bound by Phase A's closeout
  receipt: `.claude/session_logs/2026-09-11_outer-repo-auto-push.md`,
  `.claude/quality_reports/findings-2026-09-11_phase-A-outer-repo-auto-push.json`,
  or `.claude/quality_reports/verification-phase-2026-09-11_phase-A-outer-repo-auto-push.json`.

## Review Profiles

This is control-plane and high-risk work — it changes hooks, scripts, and
generators — so the full profile set applies to the phase as a whole: `code`,
`architecture`, `security`, `tests`, and `ponytail`. Load
`.claude/skills/ponytail/SKILL.md` in `full` mode before every coding step.

## Verification

During implementation:

```bash
uv run python .claude/scripts/verify.py fast --format text
uv run pytest tests/ -q --tb=short
```

Before review:

```bash
uv run pytest tests/ -q
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests
uv run ruff format --check shared scripts tests
uv run python scripts/generate_targets.py --all
uv run python scripts/install_bootstrap.py . --allow-self --local-only
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py phase --format json --persist
```

Phase-specific proof, beyond the suites above:

1. Before the fix, `validate_targets.py` must fail on the new single-phase
   terminal-push assertion. A green run before the fix means the harness is not
   reproducing the defect; treat that as a harness bug.
2. After the fix, the same assertion passes.
3. The negative assertion still rejects a receipt whose recorded digest matches
   neither the nested `HEAD` blob nor the index.
4. `tests/fixtures/schema-v3-verify.py.txt` is unchanged, confirming no
   provenance schema change and no invalidated existing receipts.
5. This phase's own completion commit pushes without the provenance error — the
   end-to-end proof that the fix works on the shape that broke.

## Risks And Fallback Paths

- The precondition deadlocks closeout. The no-nested-repository escape covers
  consumers without nested state; if a configuration with nested state still
  deadlocks, convert Step 1 to the `VFY-FRESH-003` check form so the failure is
  visible in receipt evidence, and keep the persist guard to protect the prior
  receipt.
- The persist guard breaks a validator harness. Narrow it to mode `closeout`.
- The new validator passes for the wrong reason. Gate the step on seeing it fail
  first.
- This phase's own terminal push fails anyway. Do not add a Phase C to route
  around it; that is the deferral this plan exists to end. Diagnose against the
  new validator, which reproduces the shape locally.
- Commit `05adbcc` turns out not to be recovered. If the push is still denied,
  the cause will be a different gate — prior-phase status, bypass
  acknowledgement, or this small plan's `status: in-progress` requirement in
  `assert_completed_phase_publication_invariants` — not provenance.

## Done Criteria

- `verify.py closeout --persist` refuses, writes nothing, and names the
  remediation when the big plan's bytes are not yet in nested Git.
- The complete-big-plan message recommends a recovery sequence that leaves the
  receipt chain intact, with its preconditions stated.
- `--persist` cannot replace a passing receipt with a failing one.
- The new validator proves a single-phase big plan's terminal commit pushes,
  with the negative case still rejected.
- Neither terminal predicate, the provenance schema, nor the strict
  `gh pr create` path through `assert_closeout_invariants` is relaxed.
- Generated `dist/` and `.claude/` outputs are regenerated, never hand-edited.
- Phase A's three hash-bound files are untouched.

## Closeout Checklist

- [ ] All steps implemented and verified
- [ ] `uv run pytest tests/ -q` passes
- [ ] `uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases` passes
- [ ] `uv run ruff check shared scripts tests` and `ruff format --check` pass
- [ ] `uv run python scripts/validate_targets.py` passes
- [ ] `uv run python scripts/check_runtime.py` passes
- [ ] Targets regenerated and installed locally
- [ ] Code, architecture, security, tests, and Ponytail reviews complete
- [ ] Critical and major findings at zero
- [ ] `docs/` and `README.md` updated
- [ ] `.claude/MEMORY.md` records the reusable lessons
- [ ] Closeout session log complete, including `## Stale-claims surfaces checked`
- [ ] Nested state checkpointed before persisting the closeout receipt
- [ ] Verification passed (`verify phase` then `verify closeout` PASS)
