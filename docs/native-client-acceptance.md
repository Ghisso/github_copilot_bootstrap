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
```

`--client` accepts `codex`, `claude`, or `all`; `--json` emits the
machine-readable report. `--require` makes every unresolved `WARN` for a
requested client nonzero, including missing, unavailable, timed-out, untrusted,
unexercised, or undocumented-event cases. The default timeout is intentionally
internal so the release command stays small. Do not claim a current native PASS
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
