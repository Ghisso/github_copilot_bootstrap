---
name: 2026-08-13_phase-A-codex-agent-target-scoping
type: small-plan
parent_plan: codex-luna-coder-routing
phase_index: 1
status: complete
closeout_session_log: .claude/session_logs/2026-08-13_codex-luna-routing-phase-a.md
---

# Small Plan: 2026-08-13_phase-A-codex-agent-target-scoping

## Scope

Introduce target-scoped agent definitions and one canonical metadata
loader/validator. Existing agents omit `targets`, resolve to all supported
targets, and continue generating the same adapters. This phase adds no new
agent and no routing behavior.

## Ownership

- `coder`: schema, canonical loader, target-aware generation/validation, tests.
- `verifier`: generated-output parity and local verification.
- `reviewer`: `code`, `architecture`, `security`, `tests`, and `ponytail`.
- `documenter`: skip unless a public contract must be documented in this phase.

## Required Skills

- `code-style`
- `testing-patterns`
- `ponytail`

## Steps

- [ ] Add optional `targets` metadata to
  `shared/schemas/agent.schema.json`.
  - Allowed values are exactly `github-copilot`, `claude-code`, and
    `openai-codex`.
  - Use `minItems: 1` and `uniqueItems: true`.
  - Omission means all supported targets.
  - Keep existing agent metadata valid without churn.

- [ ] Define one canonical validated agent-loading contract in
  `scripts/generate_targets.py`, replacing ad hoc `shared_agents()` loading.
  - Use a stable supported-target constant and a single resolver for omitted
    `targets`.
  - Validate metadata before any renderer consumes it.
  - Enforce a non-empty unique target set, known target IDs, valid stable agent
    IDs, and required `model_intent` for every eligible target.
  - Reject target-specific model intent for an ineligible target so metadata
    cannot silently drift from its declared scope.
  - Produce actionable errors naming the metadata file and invalid field.
  - Keep the helper importable by `scripts/validate_targets.py`; generation and
    validation must not reimplement eligibility separately.

- [ ] Make every agent renderer filter through the canonical eligibility
  contract.
  - `.claude/agents/` receives only `claude-code`-eligible agents.
  - `.github/agents/` receives only `github-copilot`-eligible agents.
  - `.codex/agents/` receives only `openai-codex`-eligible agents.
  - Do not infer eligibility from `model_intent` presence.

- [ ] Refactor `scripts/validate_targets.py` to calculate expected agent names
  and counts independently per target.
  - Reject an eligible agent missing from its target.
  - Reject an ineligible agent leaking into a target.
  - Continue checking emitted model, effort, tools, visibility adapters, and
    Codex prompt self-containment.
  - Preserve current six-role model mappings and the existing escalation
    metadata for this infrastructure-only phase; deterministic escalation is
    replaced in Phase B.

- [ ] Add focused tests in `tests/test_validate_targets.py`.
  - Omitted `targets` resolves to all three targets.
  - Empty, duplicate, or unknown targets fail with actionable errors.
  - Missing eligible-target model intent fails.
  - Model intent for an ineligible target fails.
  - A synthetic Codex-only agent renders only under `.codex/agents/`.
  - Target leakage and target omission fail validation.
  - Existing six agents still render to all targets with unchanged model and
    prompt contracts.

- [ ] Regenerate only for verification; do not hand-edit `dist/`.

## Must Not Change

- No new shared agent.
- No agent prompt, model, effort, capability, visibility, or delegation change.
- No Claude/Copilot/Codex routing change.
- No hook, policy, state-sync, installer, or lifecycle change.

## Verification

```bash
uv run pytest tests/test_validate_targets.py -q --tb=short
uv run mypy scripts/generate_targets.py scripts/validate_targets.py tests/test_validate_targets.py --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/generate_targets.py scripts/validate_targets.py tests/test_validate_targets.py
uv run ruff format --check scripts/generate_targets.py scripts/validate_targets.py tests/test_validate_targets.py
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```

## Acceptance Criteria

- [ ] One validated loader is authoritative for agent metadata and target
  eligibility.
- [ ] Omitted `targets` preserves all existing agent output.
- [ ] Expected agent sets are calculated per target.
- [ ] Invalid target declarations and target leakage fail locally.
- [ ] Current generated behavior remains unchanged.
- [ ] No paid/native model run is required.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
