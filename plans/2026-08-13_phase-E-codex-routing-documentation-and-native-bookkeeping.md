---
name: 2026-08-13_phase-E-codex-routing-documentation-and-native-bookkeeping
type: small-plan
parent_plan: codex-luna-coder-routing
phase_index: 5
status: complete
closeout_session_log: .claude/session_logs/2026-08-13_codex-luna-routing-phase-e.md
---

# Small Plan: 2026-08-13_phase-E-codex-routing-documentation-and-native-bookkeeping

## Scope

Update every maintainer-facing agent-count, routing, prompt-composition, and
native-evidence contract after implementation. Document the Luna path as
experimental, preserve historical six-role evidence, and make future optional
native probes aware of the eight declared Codex agents without requiring a
native run now.

## Ownership

- `coder`: native-probe contract/constants and consistency-test updates.
- `verifier`: final full-suite, generated-output, and documentation checks.
- `reviewer`: `code`, `architecture`, `security`, `tests`, `documentation`, and
  `ponytail`.
- `documenter`: README, architecture, mapping, smoke/runtime, and native
  acceptance documentation.

## Required Skills

- `documentation`
- `testing-patterns`
- `ponytail`

## Steps

- [ ] Update `README.md` because it already contains the authoritative
  maintainer-facing agent list and model table.
  - Distinguish six universal agents from Codex-only `luna_coder` and
    `sol_coder`.
  - Describe the experimental bounded route concisely.
  - State that Claude Code and GitHub Copilot retain their existing six-agent
    path.
  - Do not claim measured cost or quality superiority.

- [ ] Update README consistency validation in `scripts/validate_targets.py` and
  its tests.
  - Stop assuming one flat README list equals every directory under
    `shared/agents/`.
  - Validate the documented universal set and Codex-only set against canonical
    target eligibility.
  - Keep model/effort tables consistent with metadata.

- [ ] Update `docs/architecture.md`.
  - Document canonical target eligibility and the shared loader.
  - Document one-level coder prompt composition and self-contained Codex TOMLs.
  - Document the Codex-only orchestrator supplement.
  - Document the bounded packet, named route, structured Luna escalation, and
    failure-attribution categories.
  - Clarify that `visibility: hidden` is an internal orchestration convention,
    not a native Codex invisibility guarantee.

- [ ] Update `docs/smoke-tests.md`.
  - Replace hardcoded six-agent parity with six Claude, six Copilot, and eight
    Codex expectations.
  - Update the Codex role/model matrix and prompt-size observability language.
  - Add target leakage, prompt composition, and escalation-graph checks.

- [ ] Update `docs/target-mapping.md`.
  - Describe universal versus Codex-only adapters.
  - Replace current six-role Codex delivery statements with the declared
    eight-role contract where they describe current output.
  - Preserve historical and removal-gate statements in their proper context.

- [ ] Update `docs/native-client-acceptance.md`,
  `docs/runtime-checks.md`, and
  `docs/2026-08-08-codex-routing-compatibility.md` where applicable.
  - Separate current declared eight-role routing from dated six-role observed
    evidence.
  - Do not rewrite old runs as if Luna/Sol roles existed.
  - Keep the MultiAgent V2 shim and `max_depth` removal gates unchanged.
  - State that future manual persistent-thread probes may exercise the eight
    current roles, but no run is required for this feature.

- [ ] Update `scripts/check_native_clients.py` and
  `tests/test_check_native_clients.py` for future optional probes.
  - Represent the six universal roles separately from the two Codex-only roles
    where the distinction affects historical bookkeeping.
  - Make the declared current role matrix expect all eight exact role/model/
    effort tuples.
  - Preserve existing persistent-thread versus `codex exec` evidence classes.
  - Preserve `spawn_unsupported`, unexercised, trust, and availability behavior.
  - Do not introduce a paid workload, benchmark, automatic trust change, or
    required native invocation.

- [ ] Document optional use of existing session logs for small routing facts.
  - Example fields may include `initial-coder`, `fallback`, and `reason`.
  - Make this observability optional and local to existing lifecycle logs.
  - Do not add a telemetry schema, new artifact, token tracker, or quality gate.

- [ ] Regenerate and inspect final output.
  - Claude and Copilot each expose only the universal six.
  - Codex exposes the universal six plus `luna_coder` and `sol_coder`.
  - Codex orchestrator and derived coder prompts contain their exact supplements.
  - No Codex-only prompt or agent leaks to another target.

- [ ] Run full verification after documentation so score/findings bind to final
  code-plus-docs content.

## Must Not Change

- Historical observations, dates, or evidence classifications.
- Compatibility removal gates.
- Claude/Copilot routing or model tiers.
- No native execution, paid benchmark, workload corpus, or empirical
  superiority claim.

## Verification

```bash
uv run pytest tests/test_validate_targets.py tests/test_check_native_clients.py -q --tb=short
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py

test -f dist/multi-agent/.codex/agents/luna_coder.toml
test -f dist/multi-agent/.codex/agents/sol_coder.toml
test ! -f dist/multi-agent/.claude/agents/luna_coder.md
test ! -f dist/multi-agent/.claude/agents/sol_coder.md
test ! -f dist/multi-agent/.github/agents/luna_coder.agent.md
test ! -f dist/multi-agent/.github/agents/sol_coder.agent.md
```

Do not invoke `scripts/check_native_clients.py --client codex` as required
verification for this plan.

## Acceptance Criteria

- [ ] README/docs consistently describe six universal agents and eight Codex
  agents.
- [ ] The route is labeled experimental and no benchmark claim is made.
- [ ] Current declared routing is distinct from historical six-role evidence.
- [ ] Future optional native probes know the eight-role matrix.
- [ ] Session-log observability remains minimal and introduces no new system.
- [ ] Full offline/local verification passes without a real client run.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
