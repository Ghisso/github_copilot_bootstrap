---
name: 2026-08-04_phase-L-codex-role-matrix-evidence
type: small-plan
parent_plan: bootstrap-guidance-runtime-modernization
phase_index: 12
status: complete
closeout_session_log: .claude/session_logs/2026-08-09_bootstrap-guidance-runtime-modernization-phase-L.md
---

# Small Plan: 2026-08-04_phase-L-codex-role-matrix-evidence

## Scope

Make `codex_role_matrix` produce real evidence: spawn the six named roles and
read their model/effort metadata from client events. This is the one check that
would let the MultiAgent V2 shim ever be removed.

> **Corrected by Phase M (2026-08-09).** Blockers 2 and 4 are wrong as stated:
> they describe `codex exec`, not Codex. All six roles spawn with the correct
> model/effort on the interactive CLI and the VS Code extension (twelve child
> threads, client-confirmed). The openai/codex #14579/#18823 citation was
> incorrect. Blockers 1, 3 and 5 stand, scoped to `codex exec`.

## Investigation Result: Currently Impossible

Measured directly against Codex 0.147.0 in the trusted probe workspace. The
matrix cannot be exercised today, for reasons upstream of this repository.

1. **`--ephemeral` structurally precludes spawning.** With the probe's current
   least-privilege flags Codex fails outright:

   ```text
   ERROR codex_core::tools::router:
     error=collab spawn failed: no thread with id: 019fe23b-...
   ```

2. **Even without `--ephemeral`, no spawn occurs.** Repeated explicit requests
   ("call `collaboration.spawn_agent` with agent name 'verifier'") produce only
   a `wait` call with empty receivers, after which the model performs the task
   itself:

   ```json
   {"type":"collab_tool_call","tool":"wait",
    "receiver_thread_ids":[],"agents_states":{},"status":"completed"}
   ```

3. **The shim's `tool_namespace = "agents"` has no observable effect.** Codex
   0.147.0 exposes the collaboration tools under `collaboration.*`:
   `collaboration.spawn_agent`, `followup_task`, `send_message`,
   `interrupt_agent`, `list_agents`, `wait_agent`. Nothing is namespaced
   `agents.*`.

4. **The six project agents are not reachable by `spawn_agent`,** despite
   `.codex/agents/*.toml` being present and auto-discovery being documented.
   This matches upstream openai/codex issues #14579 and #18823.

5. **Control and candidate behave identically.** Removing the
   `[features.multi_agent_v2]` block changed nothing observable, because no
   spawn happens in either workspace.

Feature state in 0.147.0: `multi_agent` is stable/true; `multi_agent_v2` is
stable but default false.

## Decision

Do **not** write a parser for `agents_states` — its populated shape has never
been observed. Coding against a guessed shape is precisely the Phase I mistake
(shipping a probe that had never run). Report the blocker honestly instead.

Do **not** remove the shim. Point 3 is evidence that one of its two keys is
inert in 0.147.0, but `hide_spawn_agent_metadata` remains untested because no
spawn ever occurs. Partial evidence about one key is not grounds for removing
the block.

## Ownership

- `coder`: spawn-capability detection and honest status reporting.
- `verifier`: full suite plus a native run.
- `reviewer`: `code`, `architecture`, `security`, `tests`, `ponytail`.
- `documenter`: record the blockers and what would unblock them.

## Steps

- [x] Add a distinct `spawn_unsupported` evidence class so `codex_role_matrix`
  stops reporting the same `unexercised` value as checks that were simply never
  attempted.
- [x] Detect the observed shape — collaboration tool calls present, zero
  receivers and empty agent states — from real recorded output.
- [x] Do not guess the populated `agents_states` shape; leave matrix parsing
  unimplemented until a real spawn can be captured.
- [x] Add regression tests from the recorded 0.147.0 events.
- [x] Document all five blockers, the `collaboration.*` namespace finding, and
  the exact conditions that would let the matrix be measured.
- [x] Re-run the native matrix and record the result.

## Verification

```bash
uv run pytest tests/ -q --tb=short
uv run mypy . --ignore-missing-imports --explicit-package-bases
uv run ruff check scripts/ tests/
uv run ruff format --check scripts/ tests/
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_native_clients.py \
  --workspace /tmp/native-client-probe-release --client all --json
```

## Acceptance Criteria

- `codex_role_matrix` reports *why* it could not be measured, distinguishably
  from checks that were never attempted.
- No speculative parsing of an unobserved event shape is added.
- The MultiAgent V2 shim and nesting shims remain in place.
- The blockers and their upstream references are documented.

## Closeout Checklist

- [x] Verification passed
- [x] Review findings resolved
- [x] Score >= 90 persisted with branch/phase metadata
- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
