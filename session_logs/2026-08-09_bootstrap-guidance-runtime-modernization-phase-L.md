# Session: Bootstrap guidance/runtime modernization — Phase L

**Date:** 2026-08-09
**Plan:** .claude/plans/2026-08-04_phase-L-codex-role-matrix-evidence.md
**Status:** COMPLETED

## Goal

Make `codex_role_matrix` spawn the six named roles and read their model/effort
metadata — the one check that would let the MultiAgent V2 shim be removed.

## Result: The Matrix Cannot Be Measured Today

The goal was not achieved, and the investigation shows why it cannot be, with
Codex 0.147.0. Five findings, each measured directly in the trusted probe
workspace rather than inferred.

1. **`--ephemeral` precludes spawning.** With the probe's least-privilege
   flags, Codex fails outright:
   `error=collab spawn failed: no thread with id: 019fe23b-...`.

2. **Without `--ephemeral`, still no spawn.** Explicit instructions to call
   `collaboration.spawn_agent` for the `verifier` agent produced only a `wait`
   with empty receivers, after which the model performed the task itself:

   ```json
   {"type":"collab_tool_call","tool":"wait",
    "receiver_thread_ids":[],"agents_states":{},"status":"completed"}
   ```

3. **The shim's `tool_namespace = "agents"` is inert.** Codex 0.147.0 exposes
   `collaboration.spawn_agent`, `followup_task`, `send_message`,
   `interrupt_agent`, `list_agents`, `wait_agent`. Nothing is namespaced
   `agents.*`.

4. **Project agents are unreachable from `spawn_agent`** despite
   `.codex/agents/*.toml` being present and auto-discovery being documented
   (openai/codex #14579, #18823).

5. **Control and candidate are indistinguishable.** Removing the
   `[features.multi_agent_v2]` block changed nothing observable, because no
   spawn occurs in either workspace. The A/B cannot discriminate.

Feature state in 0.147.0: `multi_agent` stable/true, `multi_agent_v2`
stable/false.

## What Was Built Instead

- A distinct `spawn_unsupported` evidence class, so the removal gate no longer
  reports the same value as checks that were simply never attempted.
- `collaboration_attempted_without_spawn()`, which detects the observed shape
  (collaboration calls present, zero receivers, empty agent states) from real
  recorded 0.147.0 output.
- Regression tests built from the verbatim captured event, including the
  inverse case: any receiver thread or agent state means a spawn did happen.
- Documentation of all five blockers and the exact conditions that would
  unblock the measurement.

**No parser for a populated `agents_states` payload was written.** That shape
has never been observed, and coding against an imagined payload is exactly how
the probe first shipped broken in Phase I. Applying that lesson here meant
deliberately writing less code.

## The Shim Stays

Finding 3 is genuine evidence that one of the shim's two keys is inert in
0.147.0. But `hide_spawn_agent_metadata` remains untested, because no spawn
ever occurs to expose or hide metadata. Partial evidence about one key is not
grounds for removing the block, so it stays.

## Verification Results

```bash
uv run pytest tests/ -q --tb=short                               # 123 passed
uv run mypy . --ignore-missing-imports --explicit-package-bases  # PASS, 19 files
uv run ruff check scripts/ tests/                                # PASS
uv run ruff format --check <changed Python files>                # PASS
uv run python scripts/generate_targets.py --all                  # PASS twice
uv run python scripts/validate_targets.py                        # PASS
git diff --cached --check                                        # PASS
```

Live native run, reporting the real reason rather than a generic one:

```text
codex   WARN
  PASS  trust, root, scoped, workflow, hooks, shim, parity
  WARN  compact_resume        unexercised
  WARN  codex_role_matrix     spawn_unsupported
  WARN  coder_escalation      spawn_unsupported
```

## Score: 100/100 — EXCELLENCE

- Findings: `.claude/quality_reports/findings-20260808T164815Z.json`
- Score: `.claude/quality_reports/score-20260808T164815Z.json`

## [LEARN] Entries

- [LEARN:testing] "Cannot be measured" is a finding, not a failure to deliver.
  Recording *why* a gate is unmet, with reproducible evidence, is worth more
  than a check that silently reports `unexercised` forever.
- [LEARN:testing] Do not write a parser for an event shape you have never
  captured. The correct move when the payload is unobserved is to write less
  code and document the gap.
- [LEARN:config] A config key can be silently inert. `tool_namespace =
  "agents"` has no effect in Codex 0.147.0, which exposes `collaboration.*`.
  Config presence is not config effect.
- [LEARN:tooling] Least-privilege flags can preclude the very behavior under
  test: `--ephemeral` makes agent spawning structurally impossible.

## Open Questions / Next Steps

- Unblocking requires a Codex version where `spawn_agent` reaches
  project-scoped custom agents, run without `--ephemeral`. Capture a populated
  `agents_states` payload first, then write the matrix parser against the real
  shape.
- Track openai/codex #14579 and #18823.
- The MultiAgent V2 removal gate remains unmet; the shim remains in place.
