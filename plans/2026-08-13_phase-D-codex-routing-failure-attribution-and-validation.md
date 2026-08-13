---
name: 2026-08-13_phase-D-codex-routing-failure-attribution-and-validation
type: small-plan
parent_plan: codex-luna-coder-routing
phase_index: 4
status: complete
closeout_session_log: .claude/session_logs/2026-08-13_codex-luna-routing-phase-d.md
---

# Small Plan: 2026-08-13_phase-D-codex-routing-failure-attribution-and-validation

## Scope

Make automatic escalation conditional on implementation-attributable evidence
and harden the complete six-agent Claude/Copilot versus eight-agent Codex
contract with adversarial tests. The Codex orchestrator owns attribution; this
phase does not alter universal verifier or reviewer behavior.

## Ownership

- `coder`: attribution contract, validator hardening, adversarial tests.
- `verifier`: full local suite and generated-output inspection.
- `reviewer`: `code`, `architecture`, `security`, `tests`, and `ponytail`.
- `documenter`: defer consolidated documentation to Phase E.

## Required Skills

- `code-style`
- `testing-patterns`
- `ponytail`

## Steps

- [ ] Add the four-category attribution contract to the Codex-only
  orchestrator supplement:
  - `implementation`: the current implementation caused the failure; advance
    exactly one tier automatically.
  - `environment`: missing dependency/service/credential, sandbox restriction,
    unavailable tool, or other execution environment blocker; stop model
    escalation and report it.
  - `baseline`: evidence shows the failure existed on the originating branch or
    outside the changed scope; stop model escalation and report it.
  - `indeterminate`: evidence cannot reliably attribute the failure; return to
    orchestrator judgment with no automatic escalation.

- [ ] Define evidence handling without changing universal specialist outputs.
  - The orchestrator classifies existing verifier commands/results and reviewer
    findings.
  - A verifier failure alone is not sufficient for `implementation`.
  - A reviewer CRITICAL/MAJOR finding escalates only when it applies to the
    current implementation diff.
  - Infrastructure errors, flaky/unreproduced failures, and unrelated baseline
    findings must not spend a stronger model automatically.
  - The orchestrator may request focused evidence using existing agents/tools;
    it must not invent attribution.

- [ ] Harden canonical metadata validation.
  - Expected Claude/Copilot sets are exactly the six universal agents.
  - Expected Codex set is exactly those six plus `luna_coder` and `sol_coder`.
  - `luna_coder` is Luna/xhigh, `coder` is Terra/high, and `sol_coder` is
    Sol/xhigh.
  - The escalation graph is exactly
    `luna_coder -> coder -> sol_coder`, with no successor for `sol_coder`.
  - Reject cycles, missing successors, ineligible successors, direct
    Luna->Sol, spawn-override fallback metadata, and Luna/max.

- [ ] Extend `tests/test_validate_targets.py` with adversarial cases.
  - Either Codex-only agent leaks into `.claude/agents` or `.github/agents`.
  - Either Codex-only agent is missing from `.codex/agents`.
  - Model or effort drifts at any coder tier.
  - Target declarations are empty, duplicated, unknown, or inconsistent with
    model intent.
  - Prompt base is missing, recursive, multi-level, or cyclic.
  - Role supplement is missing, duplicated, copied from the entire coder
    prompt, or leaked to Claude/Copilot.
  - Orchestrator supplement is missing or leaked.
  - Route skips Terra, retries a tier, uses Luna/max, or uses a spawn-time model
    override.
  - Failure categories or their stop/decision behavior drift.
  - An existing agent without `targets` stops rendering to any current target.

- [ ] Preserve self-containment and target-native contracts.
  - Codex TOMLs embed the exact reconstructed base-plus-supplement prompt.
  - No Codex agent reads `.claude/agents/<id>.md` at runtime.
  - No per-agent MCP or skill override is introduced unintentionally.
  - Claude/Copilot structural parity remains validated for the universal six.

- [ ] Run the complete offline/local suite, target generation, validation, and
  runtime checks. Do not invoke real clients.

## Must Not Change

- Universal verifier/reviewer prompts and ownership.
- Claude/Copilot routing or generated Codex-specific prose.
- Historical native evidence or compatibility removal gates.
- No benchmark harness, paid workload, native smoke test, or telemetry system.

## Verification

```bash
uv run pytest tests/test_validate_targets.py -q --tb=short
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```

## Acceptance Criteria

- [ ] Only implementation-attributable failures auto-escalate.
- [ ] Environment/baseline failures stop escalation; indeterminate failures
  return to orchestrator judgment.
- [ ] Structural validation enforces six Claude/Copilot and eight Codex agents.
- [ ] The named escalation graph and prompt composition fail closed on drift.
- [ ] The complete offline/local suite passes.
- [ ] No paid/native run is required.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
