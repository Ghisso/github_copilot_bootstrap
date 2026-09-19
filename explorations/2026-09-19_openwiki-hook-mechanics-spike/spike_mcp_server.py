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
