#!/usr/bin/env python3
"""Normalize Antigravity PreToolUse input for the canonical safety guards."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Optional


MUTATION_TOOLS = {
    "write_to_file",
    "replace_file_content",
    "multi_replace_file_content",
}
NON_MUTATING_TOOLS = {
    "view_file",
    "list_dir",
    "find_by_name",
    "grep_search",
    "search_web",
    "read_url_content",
    "invoke_subagent",
    "send_message",
    "manage_subagents",
    # Native task coordination is non-mutating. These are bridge-only:
    # custom-agent tool declarations stay limited to the documented capability map.
    "manage_task",
    "schedule",
}


def diagnostic(message: str) -> None:
    """Keep protocol stdout clean while leaving failures observable."""
    print("WARN antigravity-pretool: %s" % message, file=sys.stderr)


def emit(decision: str, reason: str = "") -> int:
    """Write exactly one Antigravity protocol response."""
    response: dict[str, str] = {"decision": decision}
    if reason:
        response["reason"] = reason
    print(json.dumps(response, separators=(",", ":")))
    return 0


def deny(reason: str) -> int:
    """Deny an invalid or unsafe request without protocol contamination."""
    diagnostic(reason)
    return emit("deny", reason)


def repository_root() -> Path:
    """Resolve the generated workspace root without project dependencies."""
    configured = os.environ.get("REPO_ROOT")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[3]


def canonical_command(command: object, cwd: object) -> dict[str, object]:
    """Translate documented command fields to the existing Bash guard shape."""
    if not isinstance(command, str) or not command.strip():
        raise ValueError("run_command requires a non-empty CommandLine")
    if cwd is None:
        normalized_command = command
    elif isinstance(cwd, str) and cwd.strip():
        # The canonical classifier already models `cd`; prepend it instead of
        # creating a second CWD-aware protection implementation.
        normalized_command = "cd %s && %s" % (shlex.quote(cwd), command)
    else:
        raise ValueError("run_command Cwd must be a non-empty string when present")
    return {"tool_name": "Bash", "tool_input": {"command": normalized_command}}


def canonical_payload(payload: object) -> tuple[Optional[str], dict[str, object]]:
    """Validate and normalize one documented Antigravity PreToolUse payload."""
    if not isinstance(payload, dict):
        raise ValueError("hook payload must be an object")
    tool_call = payload.get("toolCall")
    if not isinstance(tool_call, dict):
        raise ValueError("PreToolUse requires toolCall")
    name = tool_call.get("name")
    args = tool_call.get("args")
    if not isinstance(name, str) or not isinstance(args, dict):
        raise ValueError("toolCall requires string name and object args")
    if name == "run_command":
        return "pretool-bash-guard.sh", canonical_command(
            args.get("CommandLine"), args.get("Cwd")
        )
    if name in MUTATION_TOOLS:
        target = args.get("TargetFile")
        if not isinstance(target, str) or not target.strip():
            raise ValueError("%s requires a non-empty TargetFile" % name)
        return "protect-files.sh", {
            "tool_name": "Write",
            "tool_input": {"path": target},
        }
    if name in NON_MUTATING_TOOLS:
        return None, {}
    raise ValueError("unsupported PreToolUse tool: %s" % name)


def guard_decision(output: str) -> tuple[str, str]:
    """Translate a canonical guard result to Antigravity's deny-or-allow form."""
    if not output.strip():
        return "allow", ""
    response = json.loads(output)
    if not isinstance(response, dict):
        raise ValueError("canonical guard returned a non-object response")
    specific = response.get("hookSpecificOutput")
    if not isinstance(specific, dict):
        raise ValueError("canonical guard returned no hook-specific output")
    decision = specific.get("permissionDecision")
    reason = specific.get("permissionDecisionReason")
    if decision not in {"deny", "ask"}:
        raise ValueError("canonical guard returned an unsupported decision")
    if not isinstance(reason, str):
        reason = "Blocked by bootstrap safety policy"
    # Antigravity has no approval response in this bridge. An existing ask is
    # conservatively a hard denial so protected writes never proceed by default.
    return "deny", reason


def main() -> int:
    """Run the one normalized PreToolUse safety lane."""
    try:
        payload = json.load(sys.stdin)
        script_name, canonical = canonical_payload(payload)
    except (ValueError, json.JSONDecodeError) as error:
        return deny("could not validate PreToolUse payload: %s" % error)

    if script_name is None:
        return emit("allow")
    script = repository_root() / ".claude" / "hooks" / "scripts" / script_name
    try:
        result = subprocess.run(
            ["bash", str(script), "google-antigravity"],
            input=json.dumps(canonical),
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as error:
        return deny("could not run canonical safety guard: %s" % error)
    if result.stderr:
        diagnostic(result.stderr.strip())
    if result.returncode != 0:
        return deny("canonical safety guard exited with status %s" % result.returncode)
    try:
        decision, reason = guard_decision(result.stdout)
    except (ValueError, json.JSONDecodeError) as error:
        return deny("canonical safety guard returned invalid output: %s" % error)
    return emit(decision, reason)


if __name__ == "__main__":
    raise SystemExit(main())
