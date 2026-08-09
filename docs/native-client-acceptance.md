# Native Client Acceptance

`scripts/check_native_clients.py` is an opt-in release probe for behavior that
offline structural validation cannot observe. It prioritizes Codex; Claude is
the second supported native client. GitHub Copilot remains covered by the
deterministic generated-target checks, not this native-client command.

## Client Version Requirements

| Client | Minimum | Verified against |
| --- | --- | --- |
| Codex | 0.144 | 0.147.0 (official `@openai/codex`) |
| Claude Code | 2.1 | 2.1.226 |

Install Codex from the official npm package. A Codex older than 0.144 does not
understand `[features.multi_agent_v2]` and aborts before the probe runs:

```text
Error loading configuration: .codex/config.toml:1:1:
  invalid type: map, expected a boolean
```

That message means the client is too old, **not** that the config is wrong.
Third-party repackages (for example the `codex` snap, published by
`jcat-nysasounds`) lag well behind and have caused exactly this failure. Check
what you actually have before trusting a probe result:

```bash
codex --version   # expect >= 0.144
claude --version  # expect >= 2.1
```

If a global npm install seems to vanish, confirm the npm global `bin`
directory is on `PATH` — `node`/`npm` are often exposed by individual symlinks
while sibling tools are not.

## Codex Role Matrix Evidence — Separate From Planner Calibration

**Verified 2026-08-09, Codex 0.147.0.** All six roles spawn with their
configured model and effort. Twelve child threads across two interfaces
(interactive CLI and VS Code extension), every one matching the installed
configuration:

| Role | Model | Effort |
| --- | --- | --- |
| orchestrator | `gpt-5.6-sol` | xhigh |
| planner | `gpt-5.6-sol` | max |
| coder | `gpt-5.6-terra` | high |
| reviewer | `gpt-5.6-sol` | high |
| documenter | `gpt-5.6-terra` | medium |
| verifier | `gpt-5.6-luna` | low |

Evidence is client-emitted twice: the spawn events, and each child's persisted
session record under `~/.codex/sessions` (`payload.model`, `payload.effort`).

This historical role-matrix observation does not benchmark planner quality.
Current planner workload evidence is recorded in the [dated calibration
record](2026-08-09-planner-reliability-calibration.md): Codex Sol/xhigh micro
23.514s (exact 2/2), bounded-full first result-schema 28.519s, then a same-
workload manual rerun PASS at 33.771s (exact 3/3); Claude Opus/xhigh micro
15.912s (exact 2/2), full 13.341s (exact 3/3). Both are 4/4 with zero
invented, duplicate, or scope-expanding work. Event-derived tool/file/first-
activity/gap fields are null when unobservable.

The Codex 33.771s run followed a concrete transport/schema variance and argv
fix. It is manual evidence, not a generic, automatic, or `max` retry policy.

The historical matrix used planner `max` and documenter `gpt-5.6-terra`;
current declarations are planner `xhigh` and documenter `gpt-5.6-luna`.

**This does not make the shim removable.** Routing was verified with
`[features.multi_agent_v2]` **present**. The candidate configuration, with the
block removed, was never exercised. The shim stays.

### Why the probe still reports `spawn_unsupported`

Spawning needs a **persistent thread**. `check_native_clients.py` drives Codex
through `codex exec`, which has none:

| Interface | Persistent thread | Spawn |
| --- | --- | --- |
| `codex exec --ephemeral` | no | fails: `no thread with id` |
| `codex exec` | no | never spawns; only `wait` |
| interactive CLI | yes | works, correct pairs |
| VS Code extension | yes | works, correct pairs |

This is the probe's own limitation, **not** an upstream defect. Closing it
means driving a persistent-thread interface (`codex app-server` or
`mcp-server` are the candidates), not waiting on openai/codex.

1. `--ephemeral` precludes spawning outright:
   `error=collab spawn failed: no thread with id: ...`.
2. Without `--ephemeral`, no spawn happens either. Explicit requests to call
   `collaboration.spawn_agent` produce only a `wait` with empty
   `receiver_thread_ids` and empty `agents_states`, after which the model does
   the task itself.
3. The shim's `tool_namespace = "agents"` has **no observable effect**. Codex
   0.147.0 exposes `collaboration.spawn_agent`, `collaboration.followup_task`,
   `collaboration.send_message`, `collaboration.interrupt_agent`,
   `collaboration.list_agents`, and `collaboration.wait_agent`. Nothing is
   namespaced `agents.*`.
4. **In `codex exec` only**, the six project agents are not reachable from
   `spawn_agent`. They *are* reachable from any persistent-thread interface —
   verified 2026-08-09 on both the interactive CLI and the VS Code extension.
   openai/codex issues #14579 and #18823 were cited here in error; this is a
   property of `codex exec`, not an upstream defect.
5. Control and candidate behave identically **under `codex exec`**, because no
   spawn occurs in either. The A/B cannot discriminate there, and has not yet
   been run on a persistent-thread interface.

Feature state in 0.147.0: `multi_agent` is stable/true, `multi_agent_v2` is
stable/false.

The probe reports this as `spawn_unsupported`, deliberately distinct from
`unexercised`, so the gate is not mistaken for a check that was simply never
run. No parser for a populated `agents_states` payload is written, because that
shape has never been observed — guessing it is how the probe first shipped
broken.

**The shim stays.** Point 3 is evidence that one of its two keys is inert in
0.147.0, but `hide_spawn_agent_metadata` is untested because no spawn ever
occurs. Partial evidence about one key does not justify removing the block.

### Why "the model said it spawned them correctly" is not evidence

A Codex session confirming that it spawned each role with the right model and
effort does **not** close this gate. The original defect this shim exists for
was that Codex 0.144.x silently spawned *every* named child as the parent
`gpt-5.6-sol/high`. A model asked "did you spawn with the configured models?"
would very plausibly answer yes in exactly that broken state, because it cannot
observe its children's actual model assignment. Self-report is least reliable
precisely where this gate needs it most.

Admissible evidence is client-emitted: a populated `agents_states` payload, or
per-child session records showing the configured model/effort pairs.

This is not hypothetical. In the 2026-08-09 runs, **not one of the twelve
children correctly identified its own model.** Every child reported "GPT-5",
with effort "unspecified" or "not exposed"; two named an effort that happened
to match. Meanwhile the client records showed all six routing correctly.

Trusting the children would have produced the conclusion "routing is broken,
everything is GPT-5 with no tiering" — precisely the 0.144.x symptom, and
precisely wrong. The client records were right; the prose was worthless.

Admissible evidence is client-emitted: the spawn events, a populated
`agents_states` payload, or per-child session records under
`~/.codex/sessions` (`payload.model`, `payload.effort`).

To make the *probe* measure this, drive a persistent-thread interface and
capture a populated `agents_states` payload, then implement the matrix parser
against that real shape. Do not write the parser before capturing it.

## Codex Has No Directory-Scoped Instructions Here

Codex discovers scoped instructions **by directory**: it walks from the Git
root down to the current working directory, taking at most one file per
directory (`AGENTS.override.md`, then `AGENTS.md`, then
`project_doc_fallback_filenames`), concatenating root -> cwd until
`project_doc_max_bytes` (32 KiB default). A nested file therefore loads only
when Codex is working inside that directory.

This bootstrap scopes policy by **glob** (`applicability:` in
`shared/policies/*.instructions.md`) and renders native adapters for two
targets:

| Target | Native scoped surface |
| --- | --- |
| Copilot | `.github/instructions/*.instructions.md` with `applyTo` |
| Claude | `.claude/rules/*.md` with `paths:` |
| Codex | none — deliberate |

No nested `AGENTS.md` is generated, and the target ships no `src/` or `tests/`
directory to host one. That is a deliberate decision, not an oversight:
emitting nested files would create directories in consumer repositories that
may not have them.

Consequently the probe asks each client only about the surface its own target
ships. For Codex, `scoped_instruction` means "the root `AGENTS.md` routes to
the canonical policies under `.claude/instructions/`". Asking Codex the Claude
question made the answer non-deterministic, because it was being asked to find
something that does not exist.

Revisit this if Codex-native directory scoping is ever wanted; the upstream
discovery rules above are what an implementation must satisfy.

## Run It Safely

The ordinary test suite is offline, mocked, deterministic, and credential-free:

```bash
uv run pytest tests/ -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
```

The default (no `--workspace`) is a deterministic temporary structure and
missing-client smoke. It intentionally does **not** launch Codex or Claude,
because a random temporary directory cannot be manually trusted; installed
clients therefore return `WARN`/`untrusted` (or `FAIL` with `--require`).

For actual native evidence, prepare one dedicated, stable workspace, inspect it,
and trust it manually in the appropriate client before the execution run:

```bash
# Create or refresh the dedicated probe workspace; starts neither client.
uv run python scripts/check_native_clients.py \
  --workspace /absolute/dedicated-native-client-probe --prepare-only --json

# Inspect its generated control/candidate inputs, then manually trust this
# stable workspace in Codex/Claude. The runner never performs that trust action.

# A release gate: unresolved evidence for the requested client is nonzero.
uv run python scripts/check_native_clients.py \
  --workspace /absolute/dedicated-native-client-probe \
  --client codex --require --json
uv run python scripts/check_native_clients.py \
  --workspace /absolute/dedicated-native-client-probe \
  --client claude --require --json

# Frozen planner calibration workloads in the prepared, trusted workspace.
uv run python scripts/check_native_clients.py \
  --workspace /absolute/dedicated-native-client-probe \
  --client all --planner-workloads --json
```

`--client` accepts `codex`, `claude`, or `all`; `--json` emits the
machine-readable report. `--require` makes every unresolved `WARN` for a
requested client nonzero, including missing, unavailable, timed-out, untrusted,
unexercised, or undocumented-event cases. The default timeout is 420s per
client, which covers the control and candidate runs it performs consecutively;
120s was not enough and produced spurious `codex_timeout` results. Do not claim
a current native PASS
from structural tests, a config parser, model prose, or absent trust/authentication.

Codex needs a signed-in CLI and a trusted project: Codex loads project-scoped
`.codex/config.toml` only after the project is trusted. Claude likewise needs a
working authenticated CLI and project customizations available to the session.
Review project hooks in the client when prompted. The probe never approves
hooks, changes a trust setting, writes credentials, enables a dangerous bypass,
or uses a destructive permission mode.

Choose a new, dedicated directory for `--workspace`; never pass a repository,
home directory, filesystem root, or a directory holding user files. Preparation
refuses broad paths and a nonempty workspace without the probe's ownership
marker. On later `--prepare-only` runs it refreshes only marker-owned
`control`/`candidate` children, preserving other contents instead of deleting a
user-selected directory. If preparation is refused, choose a fresh dedicated
path; do not add the marker by hand to force a refresh.

## What Is Observed

In persistent mode, preparation generates two distinct stable consumers: the
control retains the routing shim and the candidate removes it. Each is made
read-only before its own native execution. Codex runs ephemerally with a
read-only sandbox and non-interactive approvals; Claude runs print mode with
session persistence disabled and `Edit`, `Write`, and `Bash` disallowed. The
process receives a minimal environment, runs in its own process group for
timeout cleanup, and disables Codex MCP servers and web search. It does not
enable apps, MCP, web, or dangerous bypasses. Client stdout/stderr, prompts,
paths, IDs, transcripts, environment values, and credentials are discarded,
not retained for later redaction.

Schema v2 contains only four boolean instruction sentinels: root instruction,
scoped instruction, workflow contract, and hooks. Trust comes from the native
preflight/execution status, never from a model-produced field. The control's
sentinels are the only structured final output accepted. The candidate has a
separate execution result; a successful launch does not alone prove equivalent
routing.

For Codex, exact six-role type/model/reasoning-effort evidence is accepted only
from explicit JSONL agent/thread/subagent events—not final-answer prose. If the
installed client does not document or emit such events, role routing is `WARN`
and `unexercised`, not a PASS or a failure inferred from silence. Claude has no
Codex role-matrix requirement.

Compact/resume and coder escalation are currently `WARN`/`unexercised` unless a
separate supported native exercise is added and recorded. A candidate execution
`PASS` is likewise not sufficient removal evidence on its own. `WARN` is not
successful empirical evidence. The A/B consumers exist only in the
marker-owned probe workspace; generated defaults, source configuration, user
trust, and the user project are never modified.

## Read The JSON By Evidence Class

The JSON envelope has `schema_version`, per-client `results`, and a status
`summary`. Each check supplies a fixed `id`, `status`, and `evidence`:

| Evidence | Meaning |
| --- | --- |
| `native_preflight` | A client preflight or separate candidate execution outcome. |
| `client_schema_sentinel` | The schema-v2 instruction-sentinel response from the control execution. |
| `native_event_metadata` | Exact Codex role metadata from explicit client JSONL events only. |
| `unavailable_untrusted` | The binary, login/trust state, launch, or timeout prevented observation; default status is `WARN`, `--require` makes it `FAIL`. |
| `unexercised` | The client did not expose a documented, supported observation; this remains unresolved. |

`PASS` means the particular observed check passed; `FAIL` means a sentinel or
event-backed invariant failed, or `--require` promoted unresolved evidence.
A nonzero process result is classified as unavailable/untrusted to avoid
publishing raw client diagnostics.
Keep the JSON report with the release evidence, not client transcripts.

With `--planner-workloads`, schema v2 adds `planner_workloads` (one aggregate
record per client/workload) and `planner_workload_summary` (PASS/WARN/FAIL
counts). The substantive contract and artifact fields use strict allowlists;
unknown contracts or artifacts fail validation. Event-derived tool volume,
unique files, time to first activity, and largest observable gap are aggregate
fields and are `null` when the client does not expose them. The workspace is
marker-owned. Control and candidate consumers are read-only. Writable
invocation-local HOME, XDG, client, and temporary state lives under
`runtime/<client>/<invocation>/`; temporary files use its `tmp/` child. The
runner refuses broad or unmarked paths and never changes trust or hook approval.
Prompts, transcripts, credentials, and raw client output are not retained.
Unrelated `compact_resume` or role-matrix WARNs can make `--require` nonzero
without invalidating an individual planner-workload PASS.

## Codex Routing Removal Checklist

Do not remove either MultiAgent V2 routing-shim key based on documentation,
structural validation, a single successful run, or an untrusted result. On two
supported native Codex versions, run the trusted Codex `--require --json` probe
repeatedly with no root CLI model or reasoning-effort override. Each release
claim needs separately exercised, event-backed evidence for all six exact roles,
the coder escalation contract, and exact candidate routing without the shim.
Current v2 does not exercise compact/resume or coder escalation, so its WARNs
cannot satisfy those conditions. Review and record the resulting evidence before
changing the generator or validator.

`max_depth = 1` has a separate gate. Its removal needs repeated machine-readable
negative nested-spawn evidence on those same supported versions (or an equally
strong documented replacement); six-role routing alone does not prove nesting
is bounded. See the dated [Codex routing compatibility record](2026-08-08-codex-routing-compatibility.md).

Codex reference: [project-scoped configuration and trust](https://learn.chatgpt.com/docs/config-file/config-reference#configtoml) and [non-interactive `codex exec`](https://learn.chatgpt.com/docs/developer-commands#codex-exec).
Claude reference: [CLI print, JSON schema, session, permission, and resume flags](https://code.claude.com/docs/en/cli-reference).
