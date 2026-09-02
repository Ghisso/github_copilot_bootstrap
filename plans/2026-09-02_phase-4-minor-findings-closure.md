---
name: 2026-09-02_phase-4-minor-findings-closure
type: small-plan
parent_plan: verification-gate-semantic-hardening
phase_index: 4
status: complete
closeout_session_log: .claude/session_logs/2026-09-02_phase-4-minor-findings-closure.md
---

# Phase 4 — Close the Dispositioned MINOR Findings

**Parent:** `verification-gate-semantic-hardening`
**Phase:** 4 of 4
**Primary objective:** fix the three MINOR findings that phases 2 and 3 closed
with an accepted disposition instead of a change, so no advisory residual
remains in the hardened gate.

## 1. Why this phase exists

Phases 1–3 completed with three MINOR findings recorded as
`disposition: accepted` with reasons. That was a valid closeout under the
contract this plan itself introduced: a surviving MINOR needs an explicit
disposition and reason, not a fix. The user has since asked for them to be
fixed, so the dispositions are withdrawn and each finding is resolved on its
merits.

Recorded findings being closed:

1. `shared/scripts/verify.py` — no regression test for merge-commit topology in
   `historical_chain_errors`' ancestry-path resolution
   (`findings-2026-09-02_phase-2-lifecycle-evidence.json`).
2. `tests/test_verify.py` — the reversed-order historical-chain test still
   builds its receipt with the old `tree_sha == head_sha^{tree}` shorthand
   (same report).
3. `shared/scripts/verify.py` — the fence scanner's closing-delimiter check
   does not tolerate a CRLF line ending
   (`findings-2026-09-02_phase-3-consistency-hardening.json`).

## 2. Settled behavior

### 2.1 Merge-topology resolution must be deterministic or fail closed

`historical_chain_errors` resolves the certified commit as the first entry of
`git rev-list --ancestry-path --reverse <earlier_head>..<chain_head>`. On a
strictly linear implementation branch that is unambiguously the completion
commit. If the range ever contains a merge producing two divergent,
reconverging paths, "first" is not guaranteed to be the true completion commit.

Required outcome:

- selection is deterministic and correct for the linear case, unchanged;
- an ambiguous or non-linear range does not silently select a plausible-looking
  wrong commit;
- ambiguity fails closed with a diagnosable message.

Prefer constraining the selection so the chosen commit is provably the child of
`earlier_head` (its parent set contains `earlier_head`) over inferring from
list position alone. Do not add a merge-tolerant traversal that widens what the
gate accepts.

The rest of the lifecycle assumes a linear `<plan>_implementation` branch. This
phase does not change that assumption; it stops the tree check from resting on
it silently.

### 2.2 The reversed-order fixture must not encode the disproven rule

`test_historical_chain_rejects_reversed_phase_order` still builds receipts as
`tree_sha = head_sha^{tree}` — the exact assumption Phase 2 proved wrong. It
currently passes only because the ancestor check fires before the tree value is
read, and only because its commits happen to share an identical tree.

Required outcome:

- the fixture builds receipts the way the real lifecycle does, with each
  receipt's `tree_sha` being the tree of the commit it actually certifies;
- commits carry genuinely distinct trees, so the test cannot pass by tree
  coincidence;
- the test still fails for the intended reason: out-of-order phase receipts.

The sibling `test_historical_chain_rejects_ancestor_failure` was already
converted to an explicit never-read sentinel and is correct; leave it.

### 2.3 The fence scanner must tolerate CRLF

The closing-delimiter check uses `[ \t]*$`, so a CRLF-terminated closing fence
does not match and the fence is treated as unterminated. Today this is
unreachable in-repo because `.gitattributes` normalizes text files to LF, but
the shipped verifier runs in consumer repositories whose settings are not
controlled here.

Required outcome:

- a CRLF-terminated fence, opening or closing, is recognized;
- LF behavior is byte-for-byte unchanged;
- a genuinely unterminated fence still swallows to end of section, so the
  fail-closed posture from Phase 3 is preserved.

## 3. Non-goals

- Do not widen what any gate accepts. Every change here either tightens a check
  or makes an existing one robust to input form.
- Do not tolerate merges inside an implementation branch as a supported state.
- Do not reintroduce a numeric score, or any authority-implying findings field.
- Do not touch the certified-commit rule itself, the typo-bypass exclusion, or
  the LEARN evidence contract beyond the CRLF handling.

## 4. Files to inspect and likely change

- `shared/scripts/verify.py` — `historical_chain_errors`,
  `_strip_fenced_code_blocks`
- `tests/test_verify.py` — the `test_historical_chain_*` family and the
  `closeout_log` fence tests

## 5. Implementation sequence

Write the failing-first test for each item before its fix, and capture the
failing output.

1. Merge-topology regression test, then the deterministic/fail-closed selection.
2. Reversed-order fixture rebuild.
3. CRLF fence test per vector, then the scanner fix.

## 6. Acceptance criteria

- [ ] a merge topology between two historical phases has a regression test.
- [ ] certified-commit selection is deterministic, or fails closed with a
      diagnosable message when it cannot be.
- [ ] the linear case behaves exactly as before.
- [ ] the reversed-order fixture uses real lifecycle receipt shape and distinct
      trees, and still fails for the ordering reason.
- [ ] a CRLF-terminated fence is recognized on open and close.
- [ ] an unterminated fence still fails closed.
- [ ] phase 1–3 session logs still satisfy the LEARN contract.
- [ ] the full historical receipt chain for phases 1–4 validates through the
      consumer gate path.
- [ ] full repository tests and validation pass with no regeneration drift.

## 7. Completion evidence

Updated plan status, deterministic verification PASS, a findings report with
zero surviving findings or explicit dispositions, the closeout session log
under the immutable-log contract, generated-target parity, and the receipt
chain validated across all four phases.
