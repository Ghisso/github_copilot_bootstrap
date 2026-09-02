# Session: Phase 2 — Lifecycle Evidence

**Date:** 2026-09-02
**Plan:** `.claude/plans/2026-09-02_phase-2-lifecycle-evidence.md`
**Status:** COMPLETED

## Goal

Make findings, plan metadata, cancellation evidence, and the full
completed-phase receipt chain enforceable at the correct lifecycle boundaries.
Phase 2 of the `verification-gate-semantic-hardening` big plan.

## Work Log

- **11:00** - Delegated implementation to a fresh `coder` with the phase plan's
  four sections in order, and with Phase 1's v4 schema facts supplied so they
  would not be re-derived.
- **12:50** - Round 1 returned: findings contract, frontmatter shipping,
  cancellation at commit, and the historical receipt chain all implemented.
  1168 tests pass.
- **13:30** - Review round 1: **FAIL**. 5 CRITICAL + 1 MAJOR. The reviewer
  traced the core mechanics hard and found them correct; every blocking finding
  was a document asserting the opposite of the new behavior, including two
  files that contradicted themselves a few lines apart.
- **13:35** - The coder hit a session rate limit before applying any fix. Its
  earlier file timestamps made it look like partial progress had landed;
  direct inspection showed none of the six findings were addressed.
- **13:50** - Orchestrator applied all six fixes directly. Re-verified: 1169
  tests pass, all canonical checks green.
- **14:00** - Review round 2: **PASS**, zero surviving findings. Independent
  from-scratch sweep found nothing new.
- **14:10** - The completion commit was blocked twice by the gate acting on
  itself, surfacing two real bugs review could not have caught.
  First: `is_complete_small_plan` requires a small plan's `name:` to equal its
  file basename. All three of this plan's files used short names. Phase 1 had
  slipped through its terminal check on a digest match; the new chain check
  caught it. Corrected all three.
  Second, and more serious: the new historical tree rule was wrong. It required
  `tree_sha == head_sha^{tree}`, but receipts are generated before the
  completion commit, so `head_sha` is the parent and `tree_sha` is the staged
  tree that becomes the certified commit's tree. Measured on this repo: Phase
  1's receipt has `head_sha=7d16b64`, `tree_sha=cce376c6`; `7d16b64^{tree}` is
  `e7888f80`, while `2af3df7^{tree}` — the Phase 1 completion commit, child of
  `7d16b64` — is `cce376c6`. The rule would have blocked every legitimate
  second-phase commit.
- **14:30** - Delegated the fix. The rule now resolves the certified commit as
  the first entry of `git rev-list --ancestry-path --reverse
  earlier_head..chain_head` and compares that commit's tree. The fixture was
  rebuilt to real lifecycle shape, including one case built via `git write-tree`
  against a dirty index to reproduce the exact pre-commit window.
- **14:45** - The same coder flagged that `verify.py fast` was returning FAIL
  because Phase 1's deletion of `quality_score.py` left a deleted path in
  `relevant_paths`, which Ruff cannot open. `fast` is a shipped command the
  quality policy tells agents to run during IMPLEMENT, so this was pulled into
  scope rather than deferred. Fixed at root with an `existing_paths` filter
  applied only where a list reaches a tool that must open each file.
- **15:00** - Review round 3 on both fixes: **PASS**, three advisory MINORs.
  Fixed one (a reject-path fixture now uses an explicit never-read sentinel);
  dispositioned two with reasons.

## Design decisions

- **The completion boundary is a status read, not a new flag.** In
  `assert_commit_invariants`, `require_major` is computed as
  `[[ "$small_status" == "complete" ]]` instead of being hardcoded false. A
  paused checkpoint returns earlier in the function and never reaches the
  check, so MAJOR structurally cannot block a checkpoint. Every other status
  is already blocked for an unrelated reason, so MAJOR is never the additional
  cause. The reviewer confirmed this across amend, re-commit, cancelled,
  paused, and duplicate-completion-commit paths.
- **One flag gates both MAJOR blocking and MINOR disposition.** These are two
  rules with one activation condition — "at phase completion" — so a single
  flag is a faithful encoding rather than an overload.
- **The historical chain extends the existing reader.** `historical_chain_errors`
  reuses `load_receipt`, `git_is_ancestor`, and a new shared
  `artifact_reference_errors` helper that the terminal path also uses. No
  parallel verifier was created. It is called from `gate_receipt_errors`, so
  both commit and push paths get it with no new bash call sites.
- **Historical receipts check `tree_sha` against their own head**, not the
  current tree. That is the whole difference from the terminal check, which
  still uses current-state freshness.
- **No legacy allowance was added, and none is needed.** Phase 1 made
  `validate_receipt` reject any schema mismatch unconditionally. Within this
  big plan the chain never meets a mismatch, because every receipt was produced
  by the already-migrated verifier. A genuinely pre-receipt phase could only
  exist in an already-merged unrelated plan, which is not in any current big
  plan's `phases:` list.
- **The Python plan validator ships rather than being reimplemented in bash.**
  `validate_plan_frontmatter.py` is copied into consumer `.claude/scripts/`;
  its `REPO_ROOT` moved from `__file__`-relative to `Path.cwd()`. Both wired
  callers pin cwd explicitly, and git runs hooks from the worktree root.

## [LEARN] Entries

- [LEARN:review] A phase that changes documented behavior owns the affected
  claims, even ones sitting in files an earlier scope note deferred. Deferral
  covers stale prose, never a statement the current change just falsified. Two
  files here contradicted themselves because the prose was updated in one
  section and left standing in another.
- [LEARN:workflow] When a delegated agent dies mid-task, file mtimes are not
  evidence of progress — they may be from an earlier round of the same agent.
  Re-read the actual content against the finding list before deciding what is
  left to do.
- [LEARN:verification] Retiring a test because "a unit test covers it" needs
  the specific case checked, not the test family. All the historical-chain
  unit tests assumed the receipt file exists, so retiring the integration
  scenario silently dropped the only coverage of a completed phase with no
  receipt at all — the exact migration boundary the design verdict rested on.
- [LEARN:verification] A closeout receipt's `head_sha` is the **parent** of the
  commit it certifies, and its `tree_sha` is the staged tree that becomes that
  commit's tree, because receipts are generated before the completion commit.
  Any check comparing the two against the same commit is wrong. Resolve the
  certified commit as the first entry of `git rev-list --ancestry-path
  --reverse <head_sha>..<later_head>`.
- [LEARN:testing] A fixture that synthesizes an artifact to match the
  implementation's assumption cannot catch that assumption being wrong. The
  historical-chain tests passed review while building receipts as
  `tree_sha=head_sha^{tree}` — the exact error in the code. Build fixtures from
  what the lifecycle actually produces, not from what the code expects.
- [LEARN:verification] A changed-path set legitimately includes deletions, so
  never hand it straight to a tool that must open each file. Filter at the tool
  boundary and leave the recorded metadata unfiltered, since content and
  freshness hashes depend on deletions being represented.
- [LEARN:workflow] A gate flag that reads plan status at gate time needs no
  separate "is this the completion commit" signal. Status is already the
  single source of truth, and deriving from it keeps amend and re-commit
  correct for free.

## Verification Results

```bash
uv run pytest tests/ -q --tb=short
# 1169 passed (1147 after Phase 1; +22 net new)

uv run mypy scripts/ --ignore-missing-imports --explicit-package-bases
# Success: no issues found in 8 source files

uv run ruff check tests/ scripts/ shared/
# All checks passed!

uv run python scripts/validate_targets.py
# PASS generated target is structurally valid

uv run python scripts/validate_plan_frontmatter.py
# (clean)

uv run python .claude/scripts/verify.py phase --format text --persist
# phase: PASS (all applicable checks)
```

## Open Questions / Next Steps

- Phase 3 (`consistency-hardening`) owns session-log immutability and sibling
  errata, typo-bypass path restriction, stale-claims review guidance, and the
  repo-wide score-era sweep required by big plan §10.
- `docs/plan-deterministic-commit-gate.md:97` still carries score-era prose
  ("no score / score < 90"). Author-facing, not shipped to consumers.
  Confirmed as Phase 3 scope under big plan §10.
