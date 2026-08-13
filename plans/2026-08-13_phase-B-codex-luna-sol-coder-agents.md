---
name: 2026-08-13_phase-B-codex-luna-sol-coder-agents
type: small-plan
parent_plan: codex-luna-coder-routing
phase_index: 2
status: complete
closeout_session_log: .claude/session_logs/2026-08-13_codex-luna-routing-phase-b.md
---

# Small Plan: 2026-08-13_phase-B-codex-luna-sol-coder-agents

## Scope

Add two Codex-only named coding specialists with deterministic model/effort
configuration while keeping the existing Terra/high coder unchanged. Generate
all three from one shared implementation contract plus small Codex role
supplements, avoiding three copied coder prompts.

This phase creates the agent and prompt-composition contracts. It does not yet
teach the orchestrator when to select them.

## Ownership

- `coder`: metadata, prompt composition, Codex agent generation, focused tests.
- `verifier`: generated TOML inspection and local verification.
- `reviewer`: `code`, `architecture`, `security`, `tests`, and `ponytail`.
- `documenter`: skip until the final documentation phase unless an intermediate
  public contract becomes misleading.

## Required Skills

- `code-style`
- `testing-patterns`
- `ponytail`

## Steps

- [ ] Keep `shared/agents/coder/prompt.md` byte-for-byte unchanged as the
  canonical shared implementation contract.

- [ ] Extend canonical agent metadata with optional one-level
  `prompt_base` composition.
  - `prompt_base` names another canonical agent ID.
  - It is permitted only for explicitly target-scoped agents in this feature.
  - The base must exist and contain a normal `prompt.md`.
  - Reject self-reference, a base that itself declares `prompt_base`, missing
    bases, multi-level inheritance, and cycles.
  - A derived Codex-only agent must provide
    `prompt.openai-codex.md`; it does not copy the base prompt.
  - Do not build arbitrary mixins, multiple inheritance, or a model-profile
    framework.

- [ ] Define stable prompt composition in `scripts/generate_targets.py`.
  - For a normal agent, target-transform its own `prompt.md` as today.
  - For a derived Codex agent, target-transform the base `prompt.md`, append
    exactly one delimiter in the exact form
    `--- Codex role supplement: <agent-id> ---`, then append the
    target-transformed `prompt.openai-codex.md`.
  - Preserve the existing outer Codex canonical-instructions delimiter.
  - Return a fully self-contained `developer_instructions` value.
  - Make `codex_agent_prompt_body()` reconstruct the exact composition so
    validation compares the complete expected body, not substring sentinels.

- [ ] Add `shared/agents/luna_coder/agent.yaml`.
  - `id`: `luna_coder`.
  - `role_type`: `coder`.
  - `visibility`: `hidden`, documented as an internal orchestration convention,
    not a claim of native Codex UI invisibility.
  - `targets`: `["openai-codex"]`.
  - `prompt_base`: `coder`.
  - Match the existing coder capability list exactly.
  - `delegates`: empty.
  - Codex model: `gpt-5.6-luna`.
  - Codex effort: `xhigh`.
  - Deterministic escalation metadata points to agent `coder`, not a model
    override.
  - No Claude Code or GitHub Copilot model intent.
  - No Luna/max configuration.

- [ ] Add `shared/agents/luna_coder/prompt.openai-codex.md` containing only the
  Luna-specific supplement.
  - Require packet validation before editing where possible.
  - Preserve freedom over local implementation bodies, decomposition, and
    algorithms.
  - Prohibit invented architecture, interfaces, root cause, migrations,
    security decisions, ownership, and unrelated refactors.
  - Define the exact escalation result contract used in Phase C.

- [ ] Add `shared/agents/sol_coder/agent.yaml`.
  - `id`: `sol_coder`.
  - `role_type`: `coder`.
  - `visibility`: `hidden` with the same internal-convention caveat.
  - `targets`: `["openai-codex"]`.
  - `prompt_base`: `coder`.
  - Match the existing coder capability list exactly; `delegates` is empty.
  - Codex model: `gpt-5.6-sol`.
  - Codex effort: `xhigh`.
  - No further escalation metadata.

- [ ] Add `shared/agents/sol_coder/prompt.openai-codex.md` containing only the
  final-recovery supplement.
  - Require inspection of the existing diff and prior failure evidence.
  - Require the smallest safe recovery rather than restarting the phase or
    broadening scope.
  - State that another failed verification/review returns control to the
    orchestrator; it must not loop or delegate further.

- [ ] Replace the existing coder model-override escalation metadata with a
  deterministic agent reference.
  - Keep coder at Terra/high.
  - Set its Codex escalation target to `sol_coder` by agent ID.
  - Validate `luna_coder -> coder -> sol_coder` as an acyclic chain of eligible
    Codex agents.

- [ ] Update structural expectations in `scripts/validate_targets.py` and
  focused tests.
  - Claude expected agents: existing six.
  - Copilot expected agents: existing six.
  - Codex expected agents: existing six plus `luna_coder` and `sol_coder`.
  - Verify exact model/effort, target isolation, prompt composition, complete
    self-containment, and deterministic escalation metadata.
  - Reject a copied full coder prompt in either supplement.
  - Reject `luna_coder` or `sol_coder` target leakage.

## Must Not Change

- Existing `coder` base prompt, Terra/high model, capabilities, and behavior.
- Existing universal agent model/effort mappings.
- Claude Code or GitHub Copilot generated agents.
- Orchestrator routing; Phase C owns selection behavior.
- No paid/native runs or Luna/max route.

## Verification

```bash
uv run pytest tests/test_validate_targets.py -q --tb=short
uv run mypy scripts/generate_targets.py scripts/validate_targets.py tests/test_validate_targets.py --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/generate_targets.py scripts/validate_targets.py tests/test_validate_targets.py
uv run ruff format --check scripts/generate_targets.py scripts/validate_targets.py tests/test_validate_targets.py
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py

test -f dist/multi-agent/.codex/agents/luna_coder.toml
test -f dist/multi-agent/.codex/agents/sol_coder.toml
test ! -f dist/multi-agent/.claude/agents/luna_coder.md
test ! -f dist/multi-agent/.claude/agents/sol_coder.md
test ! -f dist/multi-agent/.github/agents/luna_coder.agent.md
test ! -f dist/multi-agent/.github/agents/sol_coder.agent.md
```

## Acceptance Criteria

- [ ] Codex has eight declared agents; Claude and Copilot retain six.
- [ ] `luna_coder`, `coder`, and `sol_coder` resolve to Luna/xhigh,
  Terra/high, and Sol/xhigh respectively.
- [ ] The deterministic escalation chain uses named agents, not model
  overrides.
- [ ] Generated Luna and Sol TOMLs are fully self-contained without copied
  coder source prompts.
- [ ] No Luna/max route exists.
- [ ] No paid/native run is required.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
