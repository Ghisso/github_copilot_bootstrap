---
name: 2026-10-23_phase-A-pre-receipt-phase-exemption
type: small-plan
parent_plan: pre-receipt-phase-exemption
phase_index: 1
status: planned
closeout_session_log:
---

# Small Plan: Skip Phases That Predate Closeout Receipts

## Scope

`historical_chain_errors` in `shared/scripts/verify.py` requires a closeout receipt for every earlier completed phase. Receipts exist only since 2026-08-29, so a long-running plan whose first phases were completed before that day can never commit again. This phase skips only the leading run of such phases and leaves every other check as it is. See the big plan `pre-receipt-phase-exemption` for the approved rule, the user's 2026-10-23 decision, and the evidence.

Terms:

- **Terminal phase**: the last completed phase. The caller checks its receipt with the strict current-state rules before the walk starts.
- **Pre-receipt phase**: a phase whose slug starts with a `YYYY-MM-DD_` date before `2026-08-29`, whose small plan is complete, and whose closeout receipt path has no directory entry at all.
- **Leading pre-receipt run**: the phases at the start of the `phases:` list, before the terminal phase, that are each pre-receipt or cancelled. It ends at the first phase that is neither.

## Steps

- [ ] **1. Write the tests first.**
  - Owner: `coder`. File: `tests/test_verify.py` (modify), next to the `test_historical_chain_*` tests.
  - Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode), `.claude/skills/testing-patterns/SKILL.md`.
  - Add one fixture builder next to `_historical_chain_fixture`, reusing `_init_repo`, `_commit_all`, `_write_big_plan`, and `_write_historical_phase`. Suggested contract: `_pre_receipt_chain_fixture(tmp_path: Path, phases: list[tuple[str, str]]) -> dict[str, str]`, returning each built slug's commit SHA. Each `(slug, kind)` entry is one `phases:` item, in order, and `kind` is one of:
    - `receipt`: a complete phase with a valid closeout receipt (`head_sha` is the previous commit, `tree_sha` is this phase's own commit tree, as in `_historical_chain_fixture`);
    - `missing`: the same, then delete only its `verification-closeout-<slug>.json`;
    - `cancelled`: a cancelled small plan with `cancelled_at`, `cancelled_reason`, and a `cancelled_evidence` file holding `**Status:** CANCELLED` (the shape used near line 2695);
    - `terminal`: exactly one; it gets a commit and no files;
    - `later`: listed after the terminal phase; no commit and no files.
  - Make every commit first, then write the `.claude/` files, as `_historical_chain_fixture` does. Branch `big_implementation`, big plan slug `big`, receipt head `shas[<terminal slug>]`.
  - Consumer slugs, used where a test says "consumer shape": A to E are `2026-07-21_phase-a-early` to `2026-07-21_phase-e-early`; F is `2026-07-21_phase-f-eval-benchmark-parity`; G0 is `2026-09-04_phase-g0-state-sync-runtime-sync`; G1 is `2026-10-23_phase-g1-compatible-dependency-refresh`; the last is `2026-07-21_phase-g-documentation`.
  - New tests and expected results. "Fails today" means the test fails against the unchanged `verify.py` with `receipt is invalid`. "Guard" means it already passes today and its docstring says so.
    1. `test_historical_chain_skips_leading_pre_receipt_phases`: `2026-07-21_phase-a-early` missing, `2026-07-22_phase-b-early` missing, `2026-09-04_phase-c-receipt` receipt, `2026-09-05_phase-d-terminal` terminal. Expect `[]`. Fails today.
    2. `test_historical_chain_accepts_consumer_pre_receipt_shape`, two cases. Terminal G0: A to F missing, G0 terminal, G1 and the documentation phase later. Terminal G1: A to F missing, G0 receipt, G1 terminal, the documentation phase later. Expect `[]` for both. Both fail today, naming F.
    3. `test_historical_chain_still_validates_receipt_phase_after_pre_receipt_run`: the terminal-G1 consumer shape, then delete G0's closeout receipt. Expect an error starting `historical phase 2026-09-04_phase-g0-state-sync-runtime-sync receipt is invalid`. Guard.
    4. `test_historical_chain_rejects_pre_cutoff_phase_after_receipt_phase`: `2026-09-04_phase-a-receipt` receipt, `2026-07-21_phase-b-backdated` missing, `2026-09-05_phase-c-terminal` terminal. Expect an error starting `historical phase 2026-07-21_phase-b-backdated receipt is invalid`. Guard.
    5. `test_historical_chain_rejects_pre_cutoff_phase_after_pre_cutoff_receipt`: `2026-07-20_phase-a-receipt` receipt, `2026-07-21_phase-b-missing` missing, `2026-09-05_phase-c-terminal` terminal. Expect an error starting `historical phase 2026-07-21_phase-b-missing receipt is invalid`. Guard.
    6. `test_historical_chain_rejects_invalid_pre_cutoff_receipt`, three cases over `2026-07-21_phase-a-early` receipt and `2026-09-04_phase-b-terminal` terminal: overwrite the closeout receipt with `not json` (expect `historical phase 2026-07-21_phase-a-early receipt is invalid`); rewrite its findings bytes (expect `was tampered with`); replace the receipt with a symlink to a missing file (expect `receipt is invalid`). Guards. The symlink case fails if the new code tests for the receipt with `Path.exists()`, which follows the link.
    7. `test_historical_chain_rejects_post_cutoff_phase_without_receipt`: `2026-09-01_phase-a-missing` missing, `2026-09-04_phase-b-terminal` terminal. Expect an error starting `historical phase 2026-09-01_phase-a-missing receipt is invalid`. Guard.
    8. `test_historical_chain_receipt_cutoff_boundary`, two cases: `<day>_phase-a-early` missing, `2026-09-04_phase-b-receipt` receipt, `2026-09-05_phase-c-terminal` terminal. Day `2026-08-28`: expect `[]` (fails today). Day `2026-08-29`: expect an error starting `historical phase 2026-08-29_phase-a-early receipt is invalid` (guard).
    9. `test_historical_chain_allows_cancelled_phase_inside_pre_receipt_run`: `2026-07-20_phase-a-early` missing, `2026-07-21_phase-b-cancelled` cancelled, `2026-07-22_phase-c-early` missing, `2026-09-04_phase-d-receipt` receipt, `2026-09-05_phase-e-terminal` terminal. Expect `[]`. Fails today, naming phase C.
    10. `test_historical_chain_rejects_incomplete_pre_cutoff_phase`: `2026-07-21_phase-a-early` missing, with its small plan rewritten to `status: planned`, then `2026-09-04_phase-b-terminal` terminal. Expect an error starting `historical phase 2026-07-21_phase-a-early is neither complete nor cancelled`. Guard.
    11. `test_gate_receipt_errors_skips_consumer_pre_receipt_run`, two cases over the terminal-G0 consumer shape. Give G0 a real closeout receipt with `_write_historical_phase` (`head_sha` is F's commit, `tree_sha` is G0's commit tree). Call `verify.gate_receipt_errors` with `branch="big_implementation"`, `phase=G0`, `head=shas[G0]`, `head_relation="ancestor"`, and `require_major`, `require_ponytail`, and `enforce_final_state` all `False`. Case F dated `2026-07-21`: no returned error starts with `historical`; fails today. Case F renamed to `2026-08-29_phase-f-eval-benchmark-parity`: an error starts with `historical phase 2026-08-29_phase-f-eval-benchmark-parity receipt is invalid`; guard, and the proof that this fixture reaches the walk. Other gate errors from the minimal fixture, such as the missing `dev` merge base, are expected and not asserted. Should a gate check raise on this fixture, extend the fixture; do not change `verify.py` for it.
  - `test_historical_chain_rejects_missing_receipt_file` keeps its input and assertion. Update only its docstring: an undated phase with no receipt still fails closed; only the leading run of dated pre-receipt phases is skipped.
  - Negative control: before Step 2, run `uv run pytest tests/test_verify.py -q --tb=line -k "pre_receipt or receipt_cutoff or post_cutoff or pre_cutoff"`. Record in the session log that exactly the tests marked "fails today" fail, each with `receipt is invalid`, and every guard passes.

- [ ] **2. Skip the leading pre-receipt run.**
  - Owner: `coder`. File: `shared/scripts/verify.py` (modify).
  - Required Skills: `.claude/skills/ponytail/SKILL.md` (`full` mode).
  - Add the constant next to `CLOSEOUT_RECEIPT`: `RECEIPT_CHAIN_SINCE = "2026-08-29"`, with a short comment that closeout receipts exist only since commit `b3c6bec` and that `historical_chain_errors` skips only a plan's leading run of phases dated before it (user decision 2026-10-23).
  - Add `leading_pre_receipt_count(root: Path, phases: list[str], parent_plan: str) -> int` just above `historical_chain_errors`. For each phase in order: read `.claude/plans/<phase>.md` as bytes and stop the count on `OSError`. Count the phase when `is_cancelled_small_plan(root, source, phase, parent_plan)` is true, or when all of these are true: `re.match(r"^(\d{4}-\d{2}-\d{2})_", phase)` matches and its date is `< RECEIPT_CHAIN_SINCE`; `is_complete_small_plan(source, phase, parent_plan)`; and `not os.path.lexists(receipt_path(root, "closeout", phase))`. Stop at the first phase that is not counted.
  - In `historical_chain_errors`, take `earlier = phases[: phases.index(phase)]`, compute `skipped = leading_pre_receipt_count(root, earlier, slug)`, and walk `reversed(earlier[skipped:])`. Add one docstring paragraph that states the rule and why it stays narrow.
  - Must: keep every existing error message and check, byte for byte; keep the standard library only. Must not: read, hash, or validate anything else about a skipped phase; follow symlinks in the receipt test (`Path.exists()` does, `os.path.lexists` does not; `verify.py` already uses `os.path.lexists`); change the terminal-phase checks, `gate_receipt_errors`, or any hook.
  - Also correct the code comment in `shared/hooks/scripts/_lib-frontmatter.sh` (about lines 1540-1544) that says every earlier completed phase requires its own valid receipt: add that a plan's leading run of phases completed before closeout receipts existed is skipped. Comment only, no logic change; user-approved scope addition, 2026-10-23.
  - Run Step 1's command again: every new test passes. Then run `uv run python .claude/scripts/verify.py fast --format text`.

- [ ] **3. Update the documentation.**
  - Owner: `documenter` (CLOSEOUT step 1). Required Skills: `.claude/skills/documentation/SKILL.md`.
  - `docs/runtime-checks.md`: in the closeout-receipt paragraph (about line 565), note that phases completed before 2026-08-29 have no receipt. After the "Historical receipt-chain validation" paragraph (about line 828), add one paragraph that states the three conditions, names `RECEIPT_CHAIN_SINCE` and commit `b3c6bec`, says a malformed or tampered receipt still fails, says why deleting a receipt cannot exempt a later phase, and records the user's 2026-10-23 approval of this narrow reversal of the 2026-09-02 rule (commit `8ed2c9e`).
  - `README.md`: in "Upgrading a consumer with active work" (about line 284), add a short paragraph: a plan that began before 2026-08-29 needs no backfilled receipts; the commit, push, and PR gates skip its leading run of complete phases dated before that day that have no receipt; every later phase still needs one. At about line 1405, qualify "re-checks that same contract across every completed phase" with "except a plan's leading phases that predate closeout receipts".
  - `shared/policies/workflow.instructions.md`: at about line 537, after "a valid historical receipt chain across every completed phase, each with ...", add one sentence that states the exception and its reason. At about line 181, add the same short qualifier to "re-checked across every completed phase". Do not link to `docs/`: consumers receive the policies without it.
  - `shared/policies/quality-and-testing.instructions.md`, the Push / PR row (about line 135): add the same short qualifier.
  - `docs/smoke-tests.md` (about line 293) and `docs/architecture.md` (about line 376): add the same short qualifier to "every completed phase" / "every earlier completed phase".
  - Use plain words and short sentences.

- [ ] **4. Audit live advice for stale claims and record lessons.**
  - Owner: `documenter` for `README.md`, `docs/`, and `shared/` text; orchestrator for `.claude/MEMORY.md` and the session log.
  - Required Skills: `.claude/skills/documentation/SKILL.md`.
  - This phase is the big plan's last entry, so it runs the standing final-phase documentation, memory, and LEARN audit. Surfaces: root guidance (`CLAUDE.md`, `AGENTS.md`), `README.md`, `docs/`, `shared/policies/`, `shared/skills/` (at least `commit` and `safe-consumer-bootstrap-refresh`), `shared/agents/`, `shared/templates/`, `shared/review-profiles/`, state READMEs, the installed `.claude/` overlay after the self-install, and `.claude/MEMORY.md`.
  - Known items to record with their outcome:
    - `openwiki/operations/deterministic-verification.md` (line 157, "walks every earlier completed phase") and `openwiki/workflows/lifecycle-and-task-lanes.md` (line 115, "across every completed phase"): stale, left for the next knowledge-refresh phase. No hand edits.
    - `shared/hooks/scripts/_lib-frontmatter.sh` lines 1540-1544, a code comment saying every earlier completed phase "requires its own valid receipt": corrected in step 2.
    - `scripts/validate_targets.py` lines 6685-6694, a code comment about the removed "free pass": still accurate, because its scenario uses undated slugs.
    - `.claude/MEMORY.md`: a search for "historical", "implicit pass", and "free pass" found no entry that states the old rule; record that.
  - Leave dated records unchanged: archived plans, closed session logs, and `docs/` design narratives.
  - Record each surface and its outcome under the exact heading `## Stale-claims surfaces checked` in this phase's closeout session log.
  - Add this `[LEARN]` entry at the end of the `## Workflow` section of `.claude/MEMORY.md` (and in the session log):
    `- [LEARN:verification] A check that reads history must say how it treats records made before the check existed. historical_chain_errors required a closeout receipt for every earlier completed phase, but receipts only exist since b3c6bec (2026-08-29), so a consumer plan with July phases could never commit again. The fix skips only a plan's leading run of complete phases dated before that day with no receipt file at all; a malformed receipt, a later date, or an undated slug still fails. Test such rules with a fixture shaped like a real long-running consumer plan.`

- [ ] **5. Orchestrator closeout items.**
  - Owner: orchestrator.
  - Before CLOSEOUT step 2, run `uv run python scripts/generate_targets.py --all` and then `uv run python scripts/install_bootstrap.py . --allow-self --local-only`. Never hand-copy `dist/` or `.claude/scripts/verify.py`.

- [ ] **6. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`.
  - Focus: the skip covers only the leading run and cannot reach a phase after a receipt-bearing one; an undated slug, a 2026-08-29 slug, an incomplete phase, and any directory entry at the receipt path all stay on today's path; no error message changed; each new pass-test failed against the old code for the intended reason; the docs state exactly what is checked.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run pytest tests/test_verify.py -q --tb=short
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

- Read-only probe of real consumer files: import the updated `shared/scripts/verify.py` and call `historical_chain_errors` on `/home/ghisso/work/git_projects/industrial-inspection` with branch `2026-07-21_haystack-3-agent-refactor_implementation`, phase `2026-09-04_phase-g0-state-sync-runtime-sync`, and `receipt_head` taken from that phase's closeout receipt. Record that it returns `[]`. The consumer checkout lives only on this machine, so a script cannot rely on it.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT); the order below mirrors it
rather than restating it.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.
Set `status: paused`, record the three pause fields, and create a session log
with `**Status:** PAUSED`. A checkpoint commit preserves incomplete work; it
does not require final findings, LEARN, DOCUMENT, or a completed closeout.
After the checkpoint commit, it may be pushed as a durable remote backup when
paused-publication invariants pass. It remains unfinished and blocks PR creation
and final closeout.
Keep the big plan `in-progress` with the same `current_phase`. On resume, read
the pause log and Git state, restore this plan to `in-progress`, and continue
this same phase without creating another small plan.
