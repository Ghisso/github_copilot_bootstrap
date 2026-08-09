# Planner Reliability Calibration — 2026-08-09

## Contract

Claude Code and OpenAI Codex planners use `xhigh` by default while preserving
their model intents: Claude `opus`, Codex `gpt-5.6-sol`, and GitHub Copilot
`Claude Opus 4.6`. Effort labels are local configuration labels; they are not
claims that vendors provide equal compute.

Planner handoffs contain a compact evidence packet: approved decisions,
verified facts and measurements, exact artifacts, constraints, rejected
approaches, and unresolved questions. The orchestrator delegates one planner at
a time. A pending wait means that no mailbox event arrived during that polling
window; it does not prove failure or progress. Health checks use runtime-native
state, recent observable activity, and terminal/tool/configuration errors.
Silence does not trigger duplicate spawns, effort escalation, or interruption.
User status updates follow the host cadence and occur at least every five
minutes when no stricter cadence applies. Thirty minutes is a provisional floor
before a health review, not an automatic kill timer. Explicit cancellation and
actual terminal errors remain immediate exceptions.

## Dated evidence

| Date | Observation | Status |
| --- | --- | --- |
| 2026-08-09 | Canonical and generated Claude planner configuration is `opus`/`xhigh`. | Deterministic configuration evidence |
| 2026-08-09 | Canonical and generated Codex planner configuration is `gpt-5.6-sol`/`xhigh`. | Deterministic configuration evidence |
| 2026-08-09 | GitHub Copilot planner intent remains `Claude Opus 4.6`. | Deterministic configuration evidence |
| 2026-08-09 | Prompt and validator checks cover evidence packets, bounded discovery, one active planner, pending waits, health checks, status cadence, and the 30-minute review floor. | Deterministic test evidence |
| 2026-08-09 | Codex 0.147.0 and Claude Code 2.1.226 are installed and authenticated; a dedicated workspace is prepared. | Native preflight state |
| 2026-08-09 | Codex 0.147.0 Sol/xhigh planner workloads: micro 23.514s (exact 2/2); bounded full first result-schema 28.519s, then same-workload retry 33.771s (exact 3/3). | PASS; 4/4, zero invented/duplicate/scope |
| 2026-08-09 | Claude Code 2.1.226 Opus/xhigh planner workloads: micro 15.912s (exact 2/2); bounded full 13.341s (exact 3/3). | PASS; 4/4, zero invented/duplicate/scope |

The workload harness is invoked with `--planner-workloads`. It emits an
aggregate-only strict-schema report: event tool count, unique files, time to
first activity, and largest observable gap are `null` when the client does not
expose those events. It does not retain prompts, transcripts, credentials, or
raw client output. The workspace is marker-owned. Control and candidate
consumers are read-only. Writable invocation-local HOME, XDG, client, and
temporary state lives under `runtime/<client>/<invocation>/`; temporary files
use its `tmp/` child. The runner refuses broad or unmarked paths and never
changes project trust or hook approval.

The two PASS results above mean the bounded workload checklist completed with
4/4 items and no invented surfaces, duplicate discovery, or scope expansion.
Known `compact_resume` and Codex role-matrix checks may still be WARNs and can
make `--require` return nonzero; that does not invalidate these independent
planner-workload PASS results. The installed/authenticated state is not a
vendor-wide acceptance claim.

The 33.771s Codex bounded-full result is a manual evidence rerun of the same
workload after a concrete transport/schema variance exposed by the first
28.519s result-schema run and an argv fix. It is not a generic, automatic, or
`max` retry policy.

## Exception policy

Keep `max` only when the same material checklist failure occurs on two matched
`xhigh` runs and a matched `max` control resolves it. Consider `high` only
through a later paired benchmark. Do not add generic retries, a second planner,
or an automatic interruption timer. Historical `max` observations remain
historical and are not rewritten by this calibration.
