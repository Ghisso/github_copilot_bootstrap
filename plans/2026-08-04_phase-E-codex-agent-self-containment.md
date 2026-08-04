---
name: 2026-08-04_phase-E-codex-agent-self-containment
type: small-plan
parent_plan: bootstrap-guidance-runtime-modernization
phase_index: 5
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-08-04_phase-E-codex-agent-self-containment

## Scope

Generate self-contained Codex custom-agent instructions directly from the
canonical shared prompts. Eliminate the runtime instruction to read a
Claude-native agent file while preserving one editable source and exact model,
effort, sandbox, and escalation intent.

## Ownership

- `coder`: adapter renderer and prompt transformation.
- `verifier`: body parity, size, model/effort, and sandbox tests.
- `reviewer`: `code`, `architecture`, `security`, `tests`, `ponytail`.
- `documenter`: target-mapping explanation.

## Required Skills

- `ponytail` (`full`), `testing-patterns`, `context-manager-testing`,
  `documentation`, `ponytail-review`.

## Steps

- [ ] Change `render_codex_agent_adapter()` to embed the transformed
  `shared/agents/<id>/prompt.md` body in `developer_instructions`, preceded only
  by a short Codex-specific compatibility header.
- [ ] Keep canonical metadata in `agent.yaml`; do not copy model names into
  prompt bodies or create a second Codex prompt source.
- [ ] Remove the instruction to read `.claude/agents/<id>.md`; preserve shared
  skill/policy paths referenced by the canonical prompt.
- [ ] Validate exact normalized body parity for all six roles, not merely the
  presence of a marker string.
- [ ] Re-run MCP/tool-access checks so no generated role is instructed to use a
  tool it cannot access, preserving the regression fixed by `c72dfaa`.
- [ ] Gate rollout on the Phase-I native agent smoke; revert only this phase if
  native clients impose a `developer_instructions` size/behavior regression.

## Verification

```bash
uv run pytest tests/test_validate_targets.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
```

## Acceptance Criteria

- A Codex subagent receives its complete role contract without an extra file read.
- Generated instructions remain derived from one shared prompt.
- Exact model/effort routing from Phase D remains unchanged.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
