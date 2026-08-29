---
name: 2026-08-29_phase-B-workflow-and-agent-migration
type: small-plan
parent_plan: verification-evidence-workflow-consolidation
phase_index: 1
# status must occur exactly once: in-progress | paused | complete | cancelled
status: complete
closeout_session_log: .claude/session_logs/2026-08-29_verification-evidence-workflow-consolidation-phase-b.md
# Pause fields (required only when status is paused):
# paused_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# paused_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# pause_session_log: <repository-relative readable UTF-8 PAUSED session log>
# Cancellation fields (required only when status is cancelled):
# cancelled_at: <valid UTC YYYY-MM-DDTHH:MM:SSZ timestamp>
# cancelled_reason: <meaningful single-line prose; no YAML block/collection/list/comment forms or leading quotes>
# cancelled_evidence: <repository-relative readable UTF-8 CANCELLED artifact>
---
# Small Plan: 2026-08-29_phase-B-workflow-and-agent-migration

## Scope

Migrate the canonical lifecycle and every current provider to Phase A's proved
deterministic verification foundation. This phase removes the model-consuming
standalone verifier and redundant full-suite repetition, but current
commit/push/PR hooks remain authoritative until Phase C.

Preserve current `dev` execution defaults: conditional planning, prior-phase
impact checks, Context Mode project indexing, retrieval/context reuse, evidence
packets, same-role continuation, independent reviewer isolation, send-time
language self-check, and documenter `humanize`.

A consumer updated from current bootstrap correctly exposed a residual ambiguity:
generated `workflow.instructions.md` still presents the old unqualified canonical
chain with mandatory-looking `PLAN`, even though the detailed planner rule is
conditional. Phase B must remove that ambiguity from canonical and generated
guidance rather than relying on nearby prose to reinterpret the lifecycle.

## Pre-Flight

1. Update/rebase from current `dev` after Phase A.
2. Prove all three verification modes in source and a disposable consumer.
3. Inventory every source/generated agent, provider role/model intent, delegate
   list, root guidance, lifecycle fragment, and literal `verifier` reference.
4. Search canonical source and generated consumers for stale lifecycle/routing
   representations, including:
   - `PRE-FLIGHT -> BRANCH -> PLAN -> IMPLEMENT`;
   - `DOCUMENT -> SCORE -> LEARN -> SESSION LOG`;
   - `VERIFY -> verifier`;
   - `orchestrator -> planner -> coder` where planner is shown as unconditional.
5. Confirm current conditional planner and paused-publication semantics.
6. Preserve provider work added after this plan.

## Target Lifecycle

```text
PRE-FLIGHT -> BRANCH -> PLAN when needed -> IMPLEMENT
-> VERIFY -> REVIEW -> CLOSEOUT -> COMMIT
```

Planner remains conditional. Approved valid future work skips planner; material
completed-phase evidence triggers one planner for affected future phases only.

## Steps

- [ ] **1. Migrate orchestrator/workflow lifecycle.**
  - Owner: `coder`
  - Preserve direct authoritative pre-flight reads and optional/nonblocking
    Context Mode indexing.
  - Preserve Git/filesystem authority and context/evidence reuse.
  - Replace verifier delegation with orchestrator execution of `verify phase`.
  - Replace separate DOCUMENT/SCORE/LEARN/SESSION LOG top-level steps with CLOSEOUT.
  - Update every canonical lifecycle rendering so `PLAN` is explicitly
    conditional, not merely explained as conditional in prose below an
    unconditional-looking chain.
  - Deterministic script failure routes implementation problems to coder; do not
    escalate merely by spawning a stronger verifier model.

- [ ] **2. Define CLOSEOUT ordering without weakening gates.**
  - Owner: `coder`
  - Order:
    1. docs applicability/update;
    2. persisted converged findings;
    3. final deterministic quality score;
    4. LEARN or no-learn evidence;
    5. COMPLETED session log;
    6. `verify closeout` receipt.
  - Preserve docs-before-final-binding freshness.
  - Reviewer is not score writer; coder is not final receipt authority.
  - Preserve score >=90 and current severity semantics.
  - Write new receipt in parallel; legacy hooks remain authority in Phase B.

- [ ] **3. Update coder verification behavior.**
  - Owner: `coder`
  - Keep Ponytail `full` and focused fix-until-green checks.
  - Use `verify fast`/project-native focused checks during implementation.
  - Do not require the complete fixed suite after every small edit.
  - Orchestrator runs authoritative `verify phase` before REVIEW.
  - Coder cannot fabricate verification states/receipts.

- [ ] **4. Retire standalone verifier LLM after live parity check.**
  - Owner: `coder`
  - Remove verifier from canonical agents, delegates, provider role/model tables,
    generated adapters, root guidance, role-count/runtime invariants.
  - Remove any temporary compatibility adapter before Phase B acceptance.
  - Do not retain a model-consuming verifier for stale wording.

- [ ] **5. Keep reviewer independent and semantic.**
  - Owner: `coder`
  - Preserve current profile routing, adversarial review, Ponytail/documentation
    precedence, and reviewer independence.
  - Return enough exact reviewed scope metadata for freshness.
  - Deterministic verification does not replace architecture/security/code review.

- [ ] **6. Preserve documenter and language contracts.**
  - Owner: `coder`
  - Keep pure-internal documentation skip rules.
  - Keep required public/config/workflow/user-facing docs.
  - Keep `humanize` edit self-check and canonical reporting send-time self-check.
  - Do not expose compressed internal handoffs verbatim to users.

- [ ] **7. Simplify planner verification content.**
  - Owner: `coder`
  - When planner is actually needed, it names acceptance criteria, required
    skills/reviews, and verification groups/check IDs.
  - Stop duplicating long command lists owned by the verification entrypoint.
  - Do not make PLAN mandatory again.

- [ ] **8. Update every generated/provider/runtime contract atomically.**
  - Owner: `coder`
  - Update canonical metadata, generator, target/runtime validators, ownership
    checks, root guidance, and current provider adapters.
  - Preserve provider tool/model behavior except verifier removal.
  - Preserve Copilot VS Code, Claude, Codex, Antigravity/Gemini, Context Mode,
    and current retrieval instructions.
  - Add validator/regression coverage that fails if a generated consumer still
    contains the old unqualified lifecycle:
    ```text
    PRE-FLIGHT -> BRANCH -> PLAN -> IMPLEMENT -> VERIFY -> REVIEW
    -> DOCUMENT -> SCORE -> LEARN -> SESSION LOG -> COMMIT
    ```
    except in explicitly historical/migration fixtures.
  - Also reject generated routing text that presents planner as unconditional
    when an approved implementation-ready plan exists.
  - Verify the generated `.claude/instructions/workflow.instructions.md`, root
    guidance, and orchestrator adapter all agree on the same conditional-PLAN
    lifecycle.
  - Never hand-edit `dist/`.

- [ ] **9. Prove legacy-gate compatibility and measure savings.**
  - Owner: transition verifier/orchestrator
  - Existing gates must accept valid Phase B closeout and reject the same
    invalid/stale cases.
  - Preserve legacy score/findings/docs/learn/session-log artifacts.
  - Record concrete savings: verifier LLM delegations removed and redundant full
    verification invocations removed. Do not invent percentage savings.

- [ ] **10. Consolidated control-plane review + Ponytail.**
  - Owner: `reviewer`
  - Profiles: `code`, `architecture`, `security`, `tests`, `documentation`, `ponytail`.
  - Challenge planner regression, stale old lifecycle strings in generated
    consumers, generated/canonical lifecycle disagreement, lost retrieval/context
    reuse, reduced verification coverage, weakened reviewer independence,
    CLOSEOUT ordering, missing LEARN/session-log enforcement, provider role drift,
    language/humanize regression, and legacy gate incompatibility.
  - Run Ponytail last.

## Expected Source Surfaces

```text
shared/policies/workflow.instructions.md
shared/policies/workspace.instructions.md
shared/policies/quality-and-testing.instructions.md
shared/agents/orchestrator/*
shared/agents/planner/*
shared/agents/coder/*
shared/agents/verifier/*                # retired
shared/agents/reviewer/*
shared/agents/documenter/*
provider-derived role metadata/supplements
shared/scripts/verify.py
shared/scripts/quality_score.py
shared/scripts/record_findings.py
scripts/generate_targets.py
scripts/validate_targets.py
scripts/check_runtime.py
scripts/runtime_ownership.py
README.md / relevant workflow docs
generated-provider/runtime tests
```

## Verification

```bash
uv run python .claude/scripts/verify.py phase --format json --persist
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run pytest tests/ -q --tb=short
uv run mypy shared scripts tests --ignore-missing-imports --explicit-package-bases
uv run ruff check shared scripts tests
```

Also run disposable consumer install/update/runtime and current hook regressions.

Inspect for stale lifecycle/routing text in canonical source and generated
consumer output. Use exact paths produced by the live generator:

```bash
rg -n "PRE-FLIGHT -> BRANCH -> PLAN -> IMPLEMENT|DOCUMENT -> SCORE -> LEARN -> SESSION LOG|VERIFY -> verifier|orchestrator -> planner -> coder" \
  shared dist
```

Every remaining match must be either updated or explicitly historical/migration
documentation; generated runtime guidance must not retain the old unqualified
lifecycle.

## Acceptance Criteria

- [ ] Lifecycle uses PLAN only when needed.
- [ ] No generated consumer guidance retains the old unqualified mandatory-looking
      PLAN/DOCUMENT/SCORE/LEARN/SESSION LOG chain, except explicit historical
      migration material.
- [ ] Canonical workflow, root guidance, and generated orchestrator/runtime
      guidance agree on the same conditional-PLAN lifecycle.
- [ ] Target validation fails on regression to the stale lifecycle representation.
- [ ] Conditional planning/prior-phase impact behavior remains correct.
- [ ] Context Mode/retrieval/context reuse remains intact.
- [ ] Orchestrator runs deterministic `verify phase`.
- [ ] Standalone verifier LLM role is removed from final role inventory.
- [ ] Coder no longer repeats the full suite before another model repeats it.
- [ ] Reviewer remains independent semantic/adversarial review.
- [ ] Score >=90 and current findings severity rules remain unchanged.
- [ ] Docs/LEARN/session log remain enforced in CLOSEOUT.
- [ ] Language self-check and documentation humanize remain intact.
- [ ] Legacy commit/push/PR gates accept/reject equivalently.
- [ ] Every provider agrees on lifecycle/roles.
- [ ] Full generation/runtime/install/state-sync/determinism coverage passes.
- [ ] Actual orchestration savings are recorded.

## Closeout Checklist

- [x] Verification passed
- [x] Review findings resolved
- [x] Score >= 90 persisted with branch/phase metadata
- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`

## Pause Checkpoint

Use only after an explicit user request. Preserve the current paused checkpoint
commit and durable backup-push path. Paused remains unfinished and blocks PR/final closeout.
