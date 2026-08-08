# Codex Routing Compatibility Record — 2026-08-08

## Purpose

This record preserves the compatibility decision for generated and authoring
`.codex/config.toml` files. It is paired with the generator comment and the
structural validator, so a documentation omission cannot silently remove a
runtime-proven routing safeguard.

## Configuration Status

| Setting | Classification | Decision |
| --- | --- | --- |
| `agents.max_concurrent_threads_per_session` | current documented key | Emit with value `6`. |
| `agents.max_threads` | legacy alias | Never emit. |
| `agents.enabled` | current documented default | Do not emit; its documented default is `true`. |
| `agents.max_depth = 1` | removal candidate | Retain until the native removal gate passes. |
| `features.multi_agent_v2.hide_spawn_agent_metadata = false` | required shim | Retain verbatim. |
| `features.multi_agent_v2.tool_namespace = "agents"` | required shim | Retain verbatim. |

The current Codex configuration reference documents the canonical concurrency
key, retains `max_threads` only as a legacy alias, and documents
`agents.enabled` as defaulting to `true`. It does not establish that the
MultiAgent V2 shim or `max_depth` can be removed.

## Version Evidence

| Client evidence | Result | Scope |
| --- | --- | --- |
| Codex 0.144.x trusted-project runtime probe (2026-07-18) | Required the MultiAgent V2 shim for six named roles to receive model and effort routing. | Runtime evidence. |
| Codex 0.146.0-alpha.9.2 local config diagnosis | Parses the configuration and reports stable `multi_agent`; it does not prove role routing. | Parsing evidence only. |
| Current official Codex configuration reference (2026-08-08) | Documents the concurrency key/defaults above; does not document native replacement behavior for the shim. | Documentation evidence. |

The historical runtime probe recorded documenter as `gpt-5.6-terra` /
`medium`. The current declared contract intentionally uses `gpt-5.6-luna` /
`medium`; the historical result is evidence for the shim, not the current role
tier. The six current declarations are: orchestrator Sol/xhigh, planner
Sol/max, coder Terra/high, reviewer Sol/high, documenter Luna/medium, and
verifier Luna/low. Coder alone may escalate to Sol/xhigh.

Phase I adds the opt-in `scripts/check_native_clients.py` acceptance runner.
It uses schema v2 instruction sentinels in separate ephemeral, read-only control
and shim-removed candidate consumers. It does not approve hooks, change project
trust, enable MCP/apps/web, or establish a PASS when Codex is unavailable,
unauthenticated, or untrusted. Exact role metadata is accepted only from
explicit client JSONL agent/thread/subagent events; model prose or an absent
event is never routing proof. Current compact/resume and coder-escalation
checks are intentionally unexercised WARNs. These results do not retroactively
turn the historical entries above into current PASS results. See [Native Client
Acceptance](native-client-acceptance.md).

## Status as of 2026-08-09 (Codex 0.147.0)

This section is the authoritative status for the shim and its probes. Other
documents point here rather than restating it.

| Phase | Outcome |
| --- | --- |
| I | Probe built, but shipped without ever executing against a real client |
| J | Four probe defects fixed on first real run: Codex returns its answer as JSON *text* in `agent_message`; the variadic `--disallowedTools` consumed the prompt; non-zero exits were mislabelled `untrusted`; Claude rejects the `$schema` meta-URI |
| K | `scoped_instruction` made per-client — Codex scopes by directory, this bootstrap scopes by glob and ships no Codex scoped adapter |
| L | `codex exec` has no persistent thread and cannot spawn; reported as `spawn_unsupported` rather than guessing an unobserved payload |
| M | **Role matrix verified.** Twelve child threads across the interactive CLI and the VS Code extension, all six roles matching their configured model/effort, confirmed in client spawn events and per-child session records |

**Verified.** Named-agent routing is correct on persistent-thread interfaces:
orchestrator Sol/xhigh, planner Sol/max, coder Terra/high, reviewer Sol/high,
documenter Terra/medium *(installed overlay; generated is Luna/medium)*,
verifier Luna/low.

**Still open.** Routing was verified with `[features.multi_agent_v2]`
**present**. The shim-removed candidate has never been exercised on an
interface capable of spawning, so removability remains untested and the shim
stays. `max_depth` retains its own separate gate.

**Newly known.** `tool_namespace = "agents"` is inert in 0.147.0: the
collaboration tools appear as `collaboration.*`, nothing under `agents.*`.
That is evidence about one key's mechanism, not grounds for removing the block,
because `hide_spawn_agent_metadata` remains untested — no spawn occurs under
the interface the probe drives.

**Probe limitation.** `check_native_clients.py` drives `codex exec` and
therefore cannot measure the matrix itself. Closing that means driving a
persistent-thread interface (`codex app-server` or `mcp-server`), not waiting
on upstream.

## MultiAgent V2 Routing-Shim Removal Gate

Do not remove either MultiAgent V2 key, and do not select a different
configuration based on the installer machine's Codex version. Shim removal
requires repeated successful trusted-project probes on **two supported native
Codex versions**, each with all of the following evidence:

1. No root CLI model or reasoning-effort override.
2. One spawned thread for each of the six named roles.
3. Client metadata or tool events—not model prose—show the exact declared
   model/effort pair for every role and coder's escalation behavior.
4. The candidate key is absent in each probe and routing remains exact.
5. The recorded evidence is reviewed before changing the generator and static
   validation contract.

For each run, first use `--workspace <dedicated-path> --prepare-only`, inspect
the stable generated control/candidate workspace, and trust it manually. Then
run `uv run python scripts/check_native_clients.py --workspace
<dedicated-path> --client codex --require --json`; the default temporary mode
does not launch Codex and cannot provide native evidence. Preserve the redacted
JSON evidence and repeat on two supported Codex versions. A schema sentinel,
docs-only conclusion, model prose, untrusted result, absent/undocumented event,
or candidate execution `WARN` cannot satisfy this gate. `--require` makes those
unresolved warnings nonzero; separate supported exercises are still needed for
compact/resume and coder escalation. The runner never changes trust, and its
workspace preparation refuses broad or nonempty unmarked paths.

## `max_depth` Removal Gate

Six-role model routing does not prove that nested spawning remains bounded.
Evaluate `max_depth` independently from the routing shim on the same two exact
supported versions:

1. Spawn a depth-one child and have that child attempt a child-of-child spawn.
2. Require machine-readable evidence that the grandchild tool is absent or the
   client deterministically rejects the request; model prose is not evidence.
3. Alternatively, cite documented native replacement semantics that impose the
   same depth-one ceiling on every supported backend and fallback path.
4. Keep `max_depth = 1` unless the negative nesting probe passes repeatedly or
   loss of the configuration-level bound is explicitly approved.
5. Review the recorded nesting evidence separately before changing the
   generator or validator contract.
