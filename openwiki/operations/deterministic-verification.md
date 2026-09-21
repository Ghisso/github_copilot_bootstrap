---
type: operations
title: "Deterministic verification: verify.py modes, receipts, and findings"
description: What the shared verifier's fast, phase, closeout, and gate modes measure, what each receipt binds (code state, nested AI state, and the bootstrap-root mirror), how closeout runs a plan's required verification items, which failures block a commit or push, and what record_findings.py records for the severity gate.
tags: [verification, verify.py, receipts, provenance, findings, gates, closeout]
verified:
  - by: openwiki/0.5.2
    at: 2026-09-21T03:23:13.016Z
sources:
  - id: openwiki-source-37cd5f3d3aa49832caf1a222
    resource: repo://docs/runtime-checks.md
  - id: openwiki-source-9fa38289fd921baabf765923
    resource: repo://shared/policies/workflow.instructions.md
  - id: openwiki-source-ac6151a0e717fb82e280dbaf
    resource: repo://shared/scripts/record_findings.py
  - id: openwiki-source-b7cd6d01f37550e855f61bdc
    resource: repo://shared/scripts/verify.py
generated: { by: "claude-code", at: "2026-09-21T03:23:13.016Z" }
---

# Deterministic verification: verify.py modes, receipts, and findings

Source, tests, and the policies under `shared/policies/` outrank this page.
Where this page and the code disagree, the code is right.

## Purpose

`shared/scripts/verify.py`, installed into every consumer as
`.claude/scripts/verify.py`, is the one deterministic authority for
verification evidence. It runs the lint, type, and test measurements itself,
emits receipts that bind the exact state they were measured against, and
exposes a `gate` mode that the commit, push, and pull-request hooks call to
decide whether the evidence still applies. Nothing in it is model-backed.

```
uv run python .claude/scripts/verify.py fast --format text
uv run python .claude/scripts/verify.py phase --format json --persist
uv run python .claude/scripts/verify.py closeout --format text
uv run python .claude/scripts/verify.py closeout --format json --persist
```

Every receipt carries the same seven check ids, each with a status of
`PASS`, `FAIL`, `UNVERIFIED`, or `NOT_APPLICABLE`:

| Check | Meaning |
|---|---|
| `VFY-RUFF-001` | Ruff lint and format |
| `VFY-MYPY-001` | mypy |
| `VFY-PYTEST-001` | pytest |
| `VFY-FRESH-001` | the evidence captured, or still matches, the relevant code state |
| `VFY-FRESH-002` | the evidence captured, or still matches, the governing control-plane provenance |
| `VFY-GEN-001` | the generated verifier matches its source and no OpenWiki managed state leaked into the tree |
| `VFY-RECEIPT-001` | closeout reused a passing phase receipt |

The aggregate `status` is derived from the checks, and `validate_receipt`
refuses a receipt whose aggregate disagrees with its checks or whose
metadata has unknown or missing fields.

## The three measurement modes

**`fast`** is focused feedback during IMPLEMENT. It runs Ruff only on the
changed Python paths that still exist and marks every other check
`NOT_APPLICABLE`. It never establishes reusable evidence.

**`phase`** runs the full measurement group and persists reusable evidence.
In this authoring repository it lints and type-checks `shared`, `scripts`,
and `tests` and runs `tests/`; in a consumer it lints the repository
excluding `.claude`, type-checks the configured mypy scope (or reports
`UNVERIFIED` with the fix: add `src/` or set `[tool.mypy]` files, packages,
or modules), and runs pytest. `VFY-GEN-001` compares
`shared/scripts/verify.py` with `.claude/scripts/verify.py` byte for byte
where the source exists, and first checks the OpenWiki managed-state
conditions described below.

**`closeout`** does not re-measure. It loads the persisted phase receipt
(`VFY-RECEIPT-001`), requires it to be a passing `phase` receipt, and then
proves freshness: `VFY-FRESH-001` passes only when `base_ref`, `branch`,
`head_sha`, `merge_base_sha`, and `content_hash` all equal the phase
receipt's values; `VFY-FRESH-002` passes only when the control-plane
provenance still matches. Either mismatch fails with
`relevant code evidence is stale` or
`governing control-plane provenance is stale`.

Both `phase` and `closeout` refuse to run at all when `.claude` is not its
own Git repository, because nested provenance is then unavailable; the
message tells you to run `git -C .claude add -A && git -C .claude commit`.

## What a receipt binds

Receipt metadata records `base_ref`, `branch`, `head_sha`,
`merge_base_sha`, `tree_sha` (from `git write-tree`, so it binds the index),
`phase`, `content_hash` (the diff against the merge base),
`tracked_state_hash`, the discovered `changed_paths` and `relevant_paths`,
`path_discovery_ok`, and a `control_plane_provenance` object.

`control_plane_provenance` is what stops evidence from one runtime or plan
being reused for another. It holds the nested repository's `nested_head`, a
`runtime_fingerprint` that hashes the nested `.claude` runtime paths
together with the bootstrap-root fingerprint, a
`tracked_state_fingerprint` over the active plans, and digests of the
active big plan and small plan. The bootstrap-root fingerprint hashes each
installer-owned live root adapter (`AGENTS.md`, `CLAUDE.md`, `.mcp.json`,
`.codex/**`, `.agents/**`, and the rest listed in
`.claude/bootstrap-ownership.env`) against its mirror under
`.claude/bootstrap-root/`; a marker-claimed third-party skill bundle such
as OpenWiki's `skills/openwiki` is excluded on both sides. When any adapter
is missing, symlinked, or differs from its mirror, the fingerprint is empty
and the receipt fails with
`receipt metadata control-plane provenance is invalid`. The usual cause is
a root adapter edited without a bootstrap refresh; the fix is the refresh,
not editing the mirror.

Receipts live under `.claude/quality_reports/` at fixed per-phase paths
(the closeout receipt is
`verification-closeout-<phase>.json`, with a sibling phase receipt). A
completed phase's receipts are immutable; regenerating one after the phase
closes is refused.

## Required verification items at closeout

A small plan's `## Verification` section contains fenced `bash` or `sh`
blocks. Every non-comment line is a required item. `closeout` runs those
items itself, in order, from the repository root, before it collects any
metadata, so files an item rewrites (regenerated targets, a persisted phase
receipt) are part of what the receipt binds. Each item gets
`VERIFICATION_ITEM_TIMEOUT_SECONDS = 600`. The run stops at the first
non-`PASS` item and exits 2 without a receipt. Results are stored at
`extensions.verification_items` in the closeout receipt with the item text,
status, exit code, duration, and the last 20 lines of output; in text
format one summary line per item is printed, for example
`PASS       75.5s  uv run python scripts/validate_targets.py`.

`## Optional Verification` bullets are numbered items that must each have a
`- optional <n>: PASS|FAIL|NOT RUN — <detail>` line in the closeout session
log. A bullet that says "None" still counts as optional item 1.

Closeout also requires the closeout session log to exist for the phase and
to carry LEARN evidence: either `[LEARN:category] ...` entries or the exact
marker `[LEARN] none - no new lessons this session`, outside fenced code
blocks; `MEMORY.md`'s modification time is never a substitute. When the
phase is the big plan's last declared phase, the log must also contain a
`## Stale-claims surfaces checked` section. A closeout whose diff touches
no documentation needs `--documentation-na "<reason>"`.

## The OpenWiki backstop inside `VFY-GEN-001`

`openwiki_managed_state_violations` checks three conditions with file reads
and `git ls-files` or `git diff --cached` only: an `AGENTS.md` or `CLAUDE.md`
that still carries the `<!-- OPENWIKI:START -->` managed block (fix: run
`bash .claude/hooks/scripts/openwiki-guard.sh post </dev/null`); an
untracked or newly staged `.github/workflows/openwiki-update.yml` (init
mode is forbidden; delete it); and a tracked or staged `openwiki/.run.json`
(`git rm --cached` it and keep it ignored). Any violation fails
`VFY-GEN-001` and, through the same function, the commit gate, independently
of whether the hook guard ran.

## The findings report

`shared/scripts/record_findings.py` persists the reviewer's surviving
findings as `.claude/quality_reports/findings-<phase>.json`. Each finding
needs a `severity` of `CRITICAL`, `MAJOR`, or `MINOR`, a non-empty `title`,
and a `profile` that appears among the repeated `--profile` arguments. The
report records `counts`, `profiles_reviewed`, the findings, Git metadata
(`branch`, `head_sha`, `merge_base_sha`, `content_hash`, `changed_files`),
and `dirty: true` when any tracked change is unstaged, which is why the
closeout sequence stages before recording. When `ponytail` was reviewed the
report also carries `ponytail_reviewed: true` and `ponytail_findings`. The
gate requires `counts.critical == 0` and `counts.major == 0`, and an
explicit `disposition` with a non-empty `reason` on every surviving MINOR.

## The gate mode and what blocks a commit

`verify.py gate --branch <b> --phase <p> --head <sha> --head-relation
exact|ancestor|certified [--require-major] [--require-ponytail]
[--enforce-final-state]` prints `{"errors": [...]}` and exits 1 on any
error. The hooks call it with the relation that fits the moment:

- `exact` at commit time: the receipt's `head_sha` must equal the current
  HEAD and its `tree_sha` must equal `git write-tree` on the index, so a
  receipt made before staging is rejected as stale.
- `ancestor` for pushes of later work: the receipt's head must be an
  ancestor of the pushed ref.
- `certified` for the exact phase-completion commit: the pushed commit must
  be the direct child of the receipt's `head_sha`, because receipts are
  generated before the commit they certify.

In every relation the receipt must be a passing `closeout` receipt for the
same `base_ref` (`dev`), branch, and phase, with a `merge_base_sha` that
still matches. With the `exact` relation the gate also enforces the
verification-items contract with these message prefixes:
`G1 verification-results-missing:` (no `extensions.verification_items`),
`G2 verification-item-unrun:` (a plan item without a result),
`G3 verification-item-failed:` (a recorded non-`PASS`), and
`G4 optional-verification-unaccounted:` (an optional item with no outcome
line in the log).

For pushes and pull requests, `historical_chain_errors` additionally walks
every earlier completed phase of the big plan: its receipt's `head_sha` must
resolve, be an ancestor of the next completed phase's head, and directly
certify exactly one commit whose tree matches `tree_sha`; the recorded
receipt, findings, and closeout-log artifact hashes must still match the
files. Only the terminal phase gets current-tree freshness checks. Because a
closed session log's bytes are hashed into its receipt, closed logs are
immutable; corrections go in a sibling `<log-name>.errata.md`.

## Representative tests

`tests/test_verify.py` covers receipt schema migration (v2 and v3 receipts
are rejected), per-phase receipt immutability, symlink rejection for
receipt and closeout paths, the explicit documentation-not-applicable
requirement, and every LEARN-section rule including fenced-block and
unedited-template rejections. `tests/test_commit_closeout.py` covers the
post-commit phase advance: a completed phase advances for every commit
message source, an incomplete or bypass commit does not, and a recorded head
cannot advance a second phase.

## Related pages

- [Task lanes and the enforced lifecycle](/openwiki/workflows/lifecycle-and-task-lanes.md)
- [Hook dispatcher and guardrail scripts](/openwiki/architecture/hooks-and-guardrails.md)
- [Installing the bootstrap, file ownership, and runtime drift checks](/openwiki/operations/install-ownership-and-runtime-checks.md)
