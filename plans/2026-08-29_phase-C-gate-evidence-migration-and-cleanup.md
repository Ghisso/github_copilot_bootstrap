---
name: 2026-08-29_phase-C-gate-evidence-migration-and-cleanup
type: small-plan
parent_plan: verification-evidence-workflow-consolidation
phase_index: 2
# status must occur exactly once: in-progress | paused | complete | cancelled
status: in-progress
closeout_session_log:
# Pause fields (required only when status is paused):
# paused_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# paused_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# pause_session_log: <repository-relative readable UTF-8 PAUSED session log>
# Cancellation fields (required only when status is cancelled):
# cancelled_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# cancelled_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# cancelled_evidence: <repository-relative readable UTF-8 CANCELLED artifact>
---
# Small Plan: 2026-08-29_phase-C-gate-evidence-migration-and-cleanup

## Scope

Make the completed-phase closeout receipt authoritative for normal
commit/push/PR, prove fail-closed freshness/tamper behavior, then remove redundant
legacy evidence discovery.

Keep the live paused checkpoint commit + durable backup push as a **separate
non-final authority path**. A paused phase remains unfinished and can never
satisfy completed closeout or PR/final push authority.

## Pre-Flight

1. Update/rebase from current `dev` after Phase B.
2. Confirm deterministic workflow works while legacy gates still authorize.
3. Capture the complete live allow/deny matrix before gate edits.
4. Inspect live commit/push/PR helpers, report readers, pause/cancel/bypass rules,
   score/findings freshness, and Bash/runtime constraints.
5. Treat current code/tests as authority for paused-publication semantics.

## Authority Contract

Normal completed commit cheaply validates:

```text
plan/lifecycle
receipt schema/version
phase/branch/base correlation
final tracked-state freshness
required PASS/canonical NOT_APPLICABLE checks
score >= 90
critical findings == 0
fresh reviewer evidence
required docs + LEARN/no-learn + COMPLETED session log
referenced child artifacts present and untampered
```

Final push/PR additionally preserves live all-phase terminal/cancellation,
bypass-acknowledgement, branch/ref, and `major == 0` behavior.

Paused publication remains:

```text
valid paused evidence + live paused checkpoint/publication invariants
!= completed closeout receipt
```

Hooks must not run pytest/mypy/Ruff/full validation.

## Steps

- [ ] **1. Freeze the live gate baseline.**
  - Owner: `coder`
  - Record allow/deny for valid completed commit, low score, critical/major
    findings, stale/missing evidence, paused checkpoint commit, paused backup
    push, paused PR, cancellation, bypass, incomplete phase, and post-closeout edit.
  - Use this matrix as authority over cached plan wording.

- [ ] **2. Make closeout receipt parsing strict.**
  - Owner: `coder`
  - Require `schema_version` and exact phase/branch/base/final-state correlation.
  - Reference exact existing child artifacts instead of guessing "latest".
  - Reject malformed receipt, unknown required status/check state, missing
    required check ID, invalid N/A, missing/out-of-scope child path, tampered/stale
    child artifact, wrong phase/branch/base, and stale final state.
  - If forward-compatible metadata exists, isolate it from authoritative fields;
    never ignore an unknown authoritative value.

- [ ] **3. Add one provider-neutral receipt reader/validator.**
  - Owner: `coder`
  - Reuse current JSON/report/frontmatter helpers.
  - Keep policy shared; provider hook adapters only normalize protocol.
  - Preserve Bash 3.2 boundaries; use current Python helper pattern for structured
    JSON validation if safer.
  - Do not duplicate receipt policy per provider.

- [ ] **4. Make normal completed commit consume the receipt.**
  - Owner: `coder`
  - Replace ambiguous report reconstruction with validated receipt references
    only after matched parity.
  - Preserve score >=90, critical==0, docs/learn/session/review requirements and
    existing final freshness.
  - Keep hooks cheap.
  - Keep old logic until regression parity proves removal safe.

- [ ] **5. Preserve paused checkpoint commit and backup push separately.**
  - Owner: `coder`
  - Keep current paused evidence, checkpoint commit, and durable backup-push rules.
  - Do not require completed receipt/final score/findings/docs/learn for the
    special paused path unless current live policy does.
  - Paused PR remains denied.
  - Add regressions proving paused != completed closeout and completed receipt is
    not required for valid paused backup publication.

- [ ] **6. Make final push/PR consume completed-phase receipts.**
  - Owner: `coder`
  - Preserve all-phase terminal/cancellation semantics, completed-phase counting,
    bypass acknowledgement, major==0, correct final findings binding, and live
    branch/ref checks.
  - Missing/stale completed-phase receipt denies.
  - Cancelled phase is not a completed receipt.

- [ ] **7. Add the full fail-closed gate matrix.**
  - Owner: `coder`
  - Prove at minimum:
    ```text
    valid completed receipt -> commit allow
    score < 90 -> deny
    critical > 0 -> commit deny
    major > 0 -> final push/PR deny
    missing/UNVERIFIED/unknown required check -> deny
    invalid N/A -> deny
    malformed receipt -> deny
    missing/tampered child artifact -> deny
    wrong phase/branch/base -> deny
    stale final/relevant code/review state -> deny
    docs-only edit -> refresh docs/final receipt; unaffected code evidence reusable
    code/config/control-plane edit -> relevant evidence stale
    post-closeout tracked edit -> deny
    valid paused checkpoint commit -> preserve live allow
    valid paused backup push -> preserve live allow
    paused PR -> deny
    cancelled/bypass/incomplete-phase behavior -> preserve live semantics
    ```
  - Run shared logic through every current native hook adapter.

- [ ] **8. Remove redundant compatibility only after equivalence.**
  - Owner: `coder`
  - Stop scanning "newest" reports where receipt gives exact validated references.
  - Remove retired-verifier/gate compatibility wording and dead code only where
    no real migration case remains.
  - Keep receipt compact: references + validation, not one giant duplicated JSON.

- [ ] **9. Re-run generated consumer/install/runtime/state-sync coverage.**
  - Owner: `coder`
  - Generate all providers; run fresh install, update, prune, self-install,
    runtime drift, hook adapters, state-sync, and determinism.
  - Preserve execution defaults and Context Mode routing.
  - Never hand-edit `dist/`.

- [ ] **10. Final security/control-plane review + Ponytail.**
  - Owner: `reviewer`
  - Profiles: `code`, `architecture`, `security`, `tests`, `documentation`, `ponytail`.
  - Challenge unknown-value acceptance, path/reference substitution, stale/tampered
    evidence, freshness misclassification, pause/completed authority confusion,
    severity/bypass drift, provider divergence, expensive hook work, and premature
    legacy deletion.
  - Run Ponytail last.

## Expected Source Surfaces

```text
shared/hooks/scripts/enforce-commit-gate.sh
shared/hooks/scripts/enforce-pr-gate.sh
shared/hooks/git-hooks/pre-push
shared/hooks/scripts/record-commit-closeout.sh
shared/hooks/scripts/_lib-frontmatter.sh
shared/hooks/scripts/<receipt JSON helper if needed>
shared/scripts/verify.py
shared/scripts/quality_score.py          # only if final correlation needs it
shared/scripts/record_findings.py        # only if exact references need it
scripts/generate_targets.py
scripts/validate_targets.py
scripts/check_runtime.py
scripts/runtime_ownership.py
scripts/validate_plan_frontmatter.py     # only if live receipt refs require it
tests/test_hook_gates.py
focused receipt/gate tests
README.md / gate-runtime docs
```

## Verification

```bash
uv run pytest tests/ -q --tb=short
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py phase --format json --persist
uv run python .claude/scripts/verify.py closeout --format json --persist
```

Also run generated native-adapter gate tests, fresh install/update/prune/self-install,
state-sync, and determinism checks.

## Acceptance Criteria

- [ ] Completed normal commit uses fresh valid closeout receipt as evidence entrypoint.
- [ ] Hooks remain cheap.
- [ ] Missing/malformed/stale/FAIL/UNVERIFIED/unknown authoritative evidence denies.
- [ ] N/A is accepted only through canonical applicability.
- [ ] Score >=90 and CRITICAL/MAJOR semantics remain unchanged.
- [ ] Review/docs/learn/session evidence remains enforced.
- [ ] Docs-only reuse and code/control-plane invalidation behave correctly.
- [ ] Final receipt binds final tracked state.
- [ ] Paused checkpoint commit + backup push remain distinct and functional.
- [ ] Paused cannot satisfy completed closeout or PR.
- [ ] Cancellation and bypass behavior remain correct.
- [ ] All providers share canonical gate authority.
- [ ] Legacy code is removed only after parity.
- [ ] Full generation/runtime/install/state-sync/determinism coverage passes.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`

## Pause Checkpoint

Use only after an explicit user request. Keep live paused checkpoint/publication
authority separate from completed closeout receipt authority.
