# Host hook mechanics for MCP tool calls — observed 2026-09-19

Phase F of `2026-09-19_openwiki-knowledge-layer-integration`. Evidence only. This
document records what two coding-agent hosts actually do when an MCP tool is called,
because Phase G's `openwiki-guard` depends on that behavior and nobody had observed it.
Everything below was observed by running the hosts against a throwaway MCP server. No
value here is taken from documentation.

The preceding phases of this plan were built on a documented-but-unverified model of a
third-party program and had to be cancelled. This spike exists so that does not repeat.

## Decision

**GO with adaptations: build Phase G applying O2 to Codex.**

The exit condition — outcome O3 or O4 on Claude Code, or `PreToolUse` firing on neither
host — was not met. `PreToolUse` fires on both hosts, the tool name is
`mcp__<server>__<tool>` on both, and a deny is honored on both.

The adaptation is the error path. When the MCP tool returns `isError: true`, Claude Code
fires `PostToolUseFailure`, but Codex fires nothing at all. A guard that restores state
only from `PostToolUse` would silently not run on either host's failure path, and on
Codex no hook event can carry the restore.

## Method

| | Claude Code | Codex |
| --- | --- | --- |
| Version | 2.1.226 | codex-cli 0.147.0 |
| Version evidence | `host-versions.txt` in the raw evidence directory | same file |
| Model that issued the calls | `claude-opus-5[1m]` | `gpt-5.6-sol` |
| Session type | non-interactive (`claude -p`) | interactive, run by the user |
| Project trust | not applicable | granted at launch |

A scratch Git repository outside this checkout held a throwaway MCP server exposing one
tool, `write_marker`, taking `mode` ∈ `{init, update, fail}`, plus a hook script that
logs its stdin payload and denies `mode: init`. Three prompts were issued per host, one
per mode, in that order. Both scripts are reproduced at the end of this document.

The deny is proven by two absences — no `marker-init.txt` on disk and no `init` line in
the server's own call log — not by what the model said afterwards.

### Deviations from the planned method

- **Claude Code was observed non-interactively**, using
  `claude -p --mcp-config .mcp.json --strict-mcp-config --allowedTools mcp__spike__write_marker`.
  `/hooks` registration could not be recorded this way; that the three matchers were
  live is instead established by the hook script having run for each event.
- **Codex could not be observed non-interactively at all.** `codex exec` does not load a
  project-level `.codex/config.toml` without persisted project trust, and every MCP tool
  call under `codex exec` ended as `user cancelled MCP tool call` — including in a
  control directory containing no hooks, which rules out the untrusted hooks file as the
  cause. The two flags that would bypass these gates were deliberately not used. Phase I's
  guard re-probe against the real OpenWiki server must therefore be run interactively on
  Codex.
- **Codex was probed twice.** Round 1 used the planned config (`PreToolUse` and
  `PostToolUse` only). Round 2 added a `PostToolUseFailure` entry and re-ran the `fail`
  prompt, to separate "Codex has no failure event" from "a failure event exists but was
  not wired".

## Observations

One row per unknown per host. "Observed" means it appeared in the hook log, the server
call log, or the filesystem.

| ID | Unknown | Claude Code | Codex |
| --- | --- | --- | --- |
| U1 | `PreToolUse` fires on an MCP tool call | Yes — fired for all three calls | Yes — fired for all three calls |
| U2 | `tool_name` is `mcp__<server>__<tool>` and an exact-name matcher fires | Yes — `mcp__spike__write_marker`; matcher `mcp__spike__write_marker` fired | Yes — identical name and matcher behavior |
| U3 | A deny is honored: the tool does not execute | Yes — no `marker-init.txt`; no `init` line in the server log; the result JSON carried `permission_denials: [{"tool_name": "mcp__spike__write_marker", "tool_use_id": "…", "tool_input": {"mode": "init"}}]` | Yes — no `marker-init.txt`; no `init` line in the server log. The operator additionally reported the reason string surfacing in their terminal as `feedback: spike: mode init is denied by the PreToolUse hook`; that line is operator-reported, not captured by the spike tooling, and nothing here depends on it |
| U4 | `PostToolUse` fires after a successful call and carries `tool_input` | Yes — `tool_input` = `{"mode": "update"}` | Yes — `tool_input` = `{"mode": "update"}` |
| U5 | `tool_response` is present in the `PostToolUse` payload | Yes, **as the content array only**: `[{"type": "text", "text": "wrote marker-update.txt"}]` | Yes, **as the whole result object**: `{"content": [{"type": "text", "text": "wrote marker-update.txt"}], "isError": false}` |
| U6 | What fires when the tool returns `isError: true` | `PostToolUseFailure` fires. `PostToolUse` does not. The payload adds `error` (`"simulated failure for mode=fail"`), `is_interrupt` (`false`) and `duration_ms`, and carries **no** `tool_response` | **Nothing fires.** Only `PreToolUse` was logged, in both rounds. The call did reach the server (`fail` is in the server log), so the tool ran and returned an error with no post-event at all |
| U7 | Hook `cwd` and project-directory environment variable | `cwd` is the project root; `CLAUDE_PROJECT_DIR` is set to the same path | `cwd` is the project root; **no variable whose name ends in `PROJECT_DIR` exists**. The only `CODEX_*` variables present were `CODEX_MANAGED_BY_NPM` and `CODEX_MANAGED_PACKAGE_ROOT` |

### Payload keys, verbatim

Claude Code, `PreToolUse`:

```text
cwd, effort, hook_event_name, permission_mode, prompt_id, session_id,
tool_input, tool_name, tool_use_id, transcript_path
```

Claude Code, `PostToolUse` adds `duration_ms` and `tool_response`.
Claude Code, `PostToolUseFailure` adds `duration_ms`, `error` and `is_interrupt`.

Codex, `PreToolUse`:

```text
cwd, hook_event_name, model, permission_mode, session_id, tool_input,
tool_name, tool_use_id, transcript_path, turn_id
```

Codex, `PostToolUse` adds `tool_response`.

The keys common to both hosts and to every event are `cwd`, `hook_event_name`,
`permission_mode`, `session_id`, `tool_input`, `tool_name`, `tool_use_id` and
`transcript_path`. A guard that reads only those is portable.

### Unknown event names are ignored, not fatal

In Codex round 2 the hooks file declared a `PostToolUseFailure` array. `PreToolUse` still
fired and the tool still ran, and no `PostToolUseFailure` line was logged. Codex ignores
an event name it does not recognize rather than rejecting the whole hooks file. This
removes one risk from Phase G — emitting the key is harmless — but it also means a
generator cannot learn from Codex that the event does nothing.

### The deny JSON is portable

One hook script, printing one stdout payload, stopped the tool from executing on both
hosts — established on each host by the two absences under U3, not by either host
reporting a deny back:

```json
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"spike: mode init is denied by the PreToolUse hook"}}
```

Note the field says `"hookEventName":"PreToolUse"` on both hosts even though Codex has no
`PostToolUseFailure` event; nothing host-specific was needed.

## Outcome mapping

Applying the mapping fixed in the Phase F plan before any observation was made:

| Host | Outcome | Why |
| --- | --- | --- |
| Claude Code | **O1 (GO)** | U1–U4 all hold. `PostToolUse` fires after success and a post-event fires on `isError` |
| Codex | **O2** | `PostToolUse` fires after success, but nothing fires on `isError` |

## What Phase G must do, given this evidence

These follow from the table above. No adapter design beyond this is in scope here.

1. **Register the restore on both `PostToolUse` and `PostToolUseFailure` for Claude Code.**
   A restore wired only to `PostToolUse` does not run when `openwiki_begin` returns an
   error, which is precisely when the root adapter files are most likely to be left
   rewritten.
2. **Accept that Codex has no automatic restore on the failure path.** On Codex, a failed
   `openwiki_begin` fires nothing after `PreToolUse`. The `VFY-OPENWIKI-001` commit-time
   check and the manual `openwiki-guard.sh post </dev/null` recovery are the only
   protection there, and the skill must say so rather than implying the hook covers it.
3. **Do not read `tool_response` in a host-specific way.** Claude Code passes the content
   array; Codex passes the full result object including `isError`. Either normalize both
   shapes or do not depend on the field.
4. **Do not use a project-directory environment variable in the Codex hook command.**
   None exists. Absolute paths, or `cwd`, are the portable options; the generator already
   emits absolute paths for Codex.
5. **Phase I's Codex re-probe must be interactive.** The non-interactive path is closed by
   project trust and by MCP call cancellation, as recorded under Deviations.

## Residual limits

- Claude Code was observed in a non-interactive session. Hook dispatch is not documented
  as differing between session types and nothing observed suggested it does, but this was
  not tested interactively.
- Only one MCP server and one tool were exercised. Behavior with several servers
  registered, or with a tool that is slow or hangs, was not observed. The hook timeout of
  10 seconds was never reached.
- Codex `PostToolUseFailure` was probed with one spelling. If Codex names its failure
  event something else, this spike would not have found it.
- **Codex produces no structured session capture.** Claude Code was driven with
  `claude -p --output-format json`, so each run's full result object is archived. Codex
  was driven interactively and has no equivalent, so the Codex side of this spike rests
  entirely on what the hook script and the MCP server wrote to disk. Anything the Codex
  session displayed on screen is operator-reported and archived separately as
  `codex/operator-transcript.md`; no claim in this document depends on it.
- The spike server returns `isError: true` inside a successful JSON-RPC result. A
  transport-level JSON-RPC error, or a server that crashes mid-call, was not tested.

## Raw evidence

Complete hook logs, full untruncated hook payloads, server call logs and the host result
JSON are under `.claude/explorations/2026-09-19_openwiki-hook-mechanics-spike/`, split
into `claude-code/` and `codex/`. The Codex round 2 files carry the
`-round2-postfailure-probe` suffix.

## Reproduction

A scratch Git repository with one empty commit, containing the two scripts below.

`.mcp.json` for Claude Code registers the server as `spike` with command
`/usr/bin/python3` and the absolute path to `spike_mcp_server.py`. `.claude/settings.json`
declares `PreToolUse`, `PostToolUse` and `PostToolUseFailure`, each one entry with
`matcher` `mcp__spike__write_marker` and command
`/usr/bin/python3 "$CLAUDE_PROJECT_DIR/spike_hook.py" <pre|post|post-failure>`, timeout 10.
The Codex equivalents are `.codex/config.toml` with `[mcp_servers.spike]` and
`.codex/hooks.json` with the same matchers and absolute command paths.

### `spike_mcp_server.py`

If this is ever reused as a template: `_handle_tools_call` builds the marker filename
straight from the client-supplied `mode`, without checking it against the declared enum,
so an unexpected value could write outside the script directory. That was acceptable in a
single-operator throwaway driven only by prompts written here. It is not acceptable in
anything that outlives a spike.

```python
#!/usr/bin/env python3
"""Throwaway MCP server for the OpenWiki hook-mechanics spike (Step F1).

Newline-delimited JSON-RPC 2.0 over stdio. stdlib only. Not adapter code:
evidence tooling for `.claude/plans/2026-09-19_phase-F-openwiki-hook-mechanics-spike.md`.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
CALLS_LOG = SCRIPT_DIR / "server-calls.log"

TOOL_SCHEMA = {
    "name": "write_marker",
    "description": "Spike tool: appends a call record and writes a marker file.",
    "inputSchema": {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "enum": ["init", "update", "fail"]},
        },
        "required": ["mode"],
    },
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _send(response: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(response) + "\n")
    sys.stdout.flush()


def _record_call(mode: str) -> None:
    with open(CALLS_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"at": _now_iso(), "mode": mode}) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def _handle_tools_call(req_id: Any, params: dict[str, Any]) -> dict[str, Any]:
    arguments = params.get("arguments") or {}
    mode = arguments.get("mode")
    _record_call(mode)
    if mode == "fail":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "content": [{"type": "text", "text": f"simulated failure for mode={mode}"}],
                "isError": True,
            },
        }
    marker_path = SCRIPT_DIR / f"marker-{mode}.txt"
    marker_path.write_text(f"mode={mode} at {_now_iso()}\n", encoding="utf-8")
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "content": [{"type": "text", "text": f"wrote marker-{mode}.txt"}],
            "isError": False,
        },
    }


def _dispatch(req: dict[str, Any]) -> dict[str, Any] | None:
    method = req.get("method")
    has_id = "id" in req
    req_id = req.get("id")
    params = req.get("params") or {}

    if not has_id:
        # Notification: never respond, regardless of method.
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": params.get("protocolVersion"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "spike", "version": "0.0.1"},
            },
        }
    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": [TOOL_SCHEMA]}}
    if method == "tools/call":
        return _handle_tools_call(req_id, params)

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            print(f"spike_mcp_server: malformed JSON line ignored: {exc}", file=sys.stderr)
            continue
        try:
            response = _dispatch(req)
        except Exception as exc:  # spike server must keep serving other requests
            print(f"spike_mcp_server: error handling request: {exc}", file=sys.stderr)
            if "id" in req:
                response = {
                    "jsonrpc": "2.0",
                    "id": req.get("id"),
                    "error": {"code": -32603, "message": str(exc)},
                }
            else:
                response = None
        if response is not None:
            _send(response)


if __name__ == "__main__":
    main()
```

### `spike_hook.py`

```python
#!/usr/bin/env python3
"""Throwaway hook logger for the OpenWiki hook-mechanics spike (Step F1).

Reads the host's hook payload from stdin, appends one observation line to
`hook-log.jsonl`, and (only for `pre` + mode `init`) denies the tool call.
stdlib only. Must never crash the host and must always exit 0.
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
HOOK_LOG = SCRIPT_DIR / "hook-log.jsonl"
HOOK_PAYLOADS = SCRIPT_DIR / "hook-payloads.jsonl"

DENY_JSON = (
    '{"hookSpecificOutput":{"hookEventName":"PreToolUse",'
    '"permissionDecision":"deny",'
    '"permissionDecisionReason":'
    '"spike: mode init is denied by the PreToolUse hook"}}'
)


def _read_payload(raw: str) -> dict[str, Any]:
    if not raw.strip():
        return {}
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _build_log_line(stage: str, raw: str, payload: dict[str, Any]) -> dict[str, Any]:
    env = os.environ
    project_dir_env = {name: value for name, value in env.items() if name.endswith("PROJECT_DIR")}
    claude_codex_env_names = sorted(
        name for name in env if name.startswith("CLAUDE_") or name.startswith("CODEX_")
    )
    tool_response_present = "tool_response" in payload
    tool_response_preview = (
        str(payload.get("tool_response"))[:300] if tool_response_present else None
    )
    return {
        "stage": stage,
        "cwd": os.getcwd(),
        "project_dir_env": project_dir_env,
        "claude_codex_env_names": claude_codex_env_names,
        "payload_keys": sorted(payload.keys()),
        "hook_event_name": payload.get("hook_event_name"),
        "tool_name": payload.get("tool_name"),
        "tool_input": payload.get("tool_input"),
        "tool_response_present": tool_response_present,
        "tool_response_preview": tool_response_preview,
        "raw_preview": raw[:300],
    }


def main() -> int:
    stage = sys.argv[1] if len(sys.argv) > 1 else "unknown"
    try:
        raw = sys.stdin.read()
    except Exception as exc:  # never crash the host
        raw = ""
        print(f"spike_hook: failed to read stdin: {exc}", file=sys.stderr)

    payload = _read_payload(raw)

    try:
        log_line = _build_log_line(stage, raw, payload)
        with open(HOOK_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(log_line) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
    except Exception as exc:  # never crash the host
        print(f"spike_hook: failed to log: {exc}", file=sys.stderr)

    try:  # full untruncated payload, for the raw evidence record
        with open(HOOK_PAYLOADS, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"stage": stage, "raw": raw}) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
    except Exception as exc:  # never crash the host
        print(f"spike_hook: failed to record payload: {exc}", file=sys.stderr)

    if stage == "pre" and isinstance(payload.get("tool_input"), dict):
        if payload["tool_input"].get("mode") == "init":
            print(DENY_JSON)

    return 0


if __name__ == "__main__":
    sys.exit(main())
```
