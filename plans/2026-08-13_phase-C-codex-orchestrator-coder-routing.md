---
name: 2026-08-13_phase-C-codex-orchestrator-coder-routing
type: small-plan
parent_plan: codex-luna-coder-routing
phase_index: 3
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-08-13_phase-C-codex-orchestrator-coder-routing

## Scope

Add a concrete Codex-only orchestrator supplement that selects an initial coder
per implementation step from observable packet completeness and uses the named
Luna -> Terra -> Sol recovery chain. Claude Code and GitHub Copilot must never
consume the supplement.

Phase D hardens failure attribution and adversarial validation. This phase owns
the routing contract, packet format, structured Luna escalation, and bounded
retry state.

## Ownership

- `coder`: Codex supplement generation, orchestrator routing text, tests.
- `verifier`: generated prompt inspection and local verification.
- `reviewer`: `code`, `architecture`, `security`, `tests`, and `ponytail`.
- `documenter`: defer consolidated documentation to Phase E.

## Required Skills

- `code-style`
- `testing-patterns`
- `ponytail`

## Steps

- [ ] Add `shared/agents/orchestrator/prompt.openai-codex.md` as the only source
  of Codex model-routing guidance.
  - Keep `shared/agents/orchestrator/prompt.md` as the universal workflow
    contract.
  - Move/remove the obsolete Codex-only Terra->Sol spawn-override instructions
    from the universal prompt.
  - Do not add Luna/Sol routing language to Claude or Copilot output.

- [ ] Extend the existing additive supplement renderer from Phase B to normal
  agents that own both `prompt.md` and `prompt.openai-codex.md`.
  - Compose base prompt, exactly one
    `--- Codex role supplement: <agent-id> ---` delimiter, and supplement in
    that order.
  - Update exact prompt reconstruction in validation.
  - Reject duplicate delimiters, missing supplements, and supplement leakage to
    non-Codex targets.

- [ ] Define per-step initial routing in the Codex orchestrator supplement.
  - Build the packet from the approved small-plan step and evidence already
    gathered by planner/orchestrator retrieval.
  - Choose `luna_coder` only when all five bounded conditions hold:
    1. clear desired outcome;
    2. known relevant files, symbols, entry points, or failing checks;
    3. known constraints and must-not-change behavior;
    4. objective acceptance criteria and verification commands;
    5. no unresolved architecture, interface, root-cause, migration, security,
       or ownership decision.
  - Otherwise choose `coder` directly.
  - Decide independently for every implementation step.
  - Do not run extra discovery solely to qualify a packet for Luna.

- [ ] Define the exact bounded packet fields.
  - Goal and plan-step identity.
  - Relevant files, symbols, entry points, patterns, or failing checks.
  - Approved constraints and must-not-change behavior.
  - Rejected approaches when relevant.
  - Required skills.
  - Acceptance criteria and verification commands.
  - Explicit freedom to choose the smallest maintainable local implementation.
  - Exclude broad conversation history and raw discovery output.

- [ ] Define Luna's exact escalation-only final object:

  ```json
  {
    "status": "escalate",
    "reason": "unknown-root-cause",
    "workspace_changed": false,
    "evidence": ["..."],
    "needed": ["..."]
  }
  ```

  - Permit only `unresolved-design-decision`, `unknown-root-cause`,
    `scope-not-bounded`, `missing-interface-contract`,
    `security-or-migration-decision`, and `ownership-unclear`.
  - Require packet validation before editing where possible.
  - Require accurate `workspace_changed` reporting.
  - If true, Terra inspects and takes ownership of the existing diff; it does
    not assume a clean workspace or blindly restart.
  - The object is prompt-enforced model output, not falsely described as a
    native typed protocol.

- [ ] Define bounded named-agent recovery state.
  - Luna structured blocker or attributable Luna-produced failure routes once
    to `coder` with the original packet, blocker/failure evidence, and current
    diff state.
  - Attributable Terra-produced failure routes once to `sol_coder` with the
    full prior evidence and current diff.
  - Sol failure stops the loop and reports to the user.
  - Never retry the same tier, jump directly from Luna to Sol, introduce
    Luna/max, or let a subagent choose its successor.

- [ ] Keep optional route evidence in the existing closeout/session log only.
  - Allow concise facts such as `initial-coder`, `fallback`, and `reason`.
  - Do not create a routing database, telemetry file, cost tracker, or merge
    gate.

- [ ] Add focused generation/validation tests.
  - Codex orchestrator instructions contain exactly one supplement.
  - Claude/Copilot orchestrator output contains no Luna/Sol route.
  - All five bounded conditions, named agent chain, structured escalation
    fields, and stop condition are present in the exact canonical composition.
  - The route never references a spawn-time model override.

## Must Not Change

- Claude/Copilot agent sets, model metadata, or routing behavior.
- Universal planner, coder, verifier, reviewer, or documenter contracts.
- Lifecycle phase order or specialist ownership.
- No paid/native runs, benchmarks, new telemetry, or Luna/max.

## Verification

```bash
uv run pytest tests/test_validate_targets.py -q --tb=short
uv run mypy scripts/generate_targets.py scripts/validate_targets.py tests/test_validate_targets.py --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/generate_targets.py scripts/validate_targets.py tests/test_validate_targets.py
uv run ruff format --check scripts/generate_targets.py scripts/validate_targets.py tests/test_validate_targets.py
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
```

## Acceptance Criteria

- [ ] Codex chooses Luna or Terra per step from packet properties.
- [ ] Luna receives bounded context without implementation micromanagement.
- [ ] Recovery is the named chain Luna -> Terra -> Sol -> stop.
- [ ] Structured Luna escalation carries workspace state and evidence.
- [ ] Codex-specific guidance does not leak to Claude/Copilot.
- [ ] No paid/native run is required.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
