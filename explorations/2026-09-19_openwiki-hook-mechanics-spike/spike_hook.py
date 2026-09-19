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
