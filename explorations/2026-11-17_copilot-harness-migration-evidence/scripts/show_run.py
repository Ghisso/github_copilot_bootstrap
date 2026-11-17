"""Print a compact timeline of a step3 run: tools, hooks, permissions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

run = Path(sys.argv[1])
project, home = sys.argv[2], sys.argv[3]
width = int(sys.argv[4]) if len(sys.argv) > 4 else 260


def short(value: object, limit: int = width) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    text = text.replace(project, "<project>").replace(home, "<home>")
    return text[:limit]


events = [json.loads(line) for line in (run / "events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
for event in events:
    kind = event.get("type")
    data = event.get("data", {})
    if kind == "tool.execution_start":
        print(f"TOOL start  {data.get('toolName')} args={short(data.get('arguments'), 200)} mcp={data.get('mcpServerName')}/{data.get('mcpToolName')}")
    elif kind == "tool.execution_complete":
        result = data.get("result") or {}
        text = result.get("content") if isinstance(result, dict) else result
        print(f"TOOL done   success={data.get('success')} error={short(data.get('error'), 300)} result={short(text, 300)}")
    elif kind == "hook.start":
        keys = sorted((data.get("input") or {}).keys())
        print(f"  HOOK start {data.get('hookType')} inputKeys={keys}")
    elif kind == "hook.end":
        print(f"  HOOK end   {data.get('hookType')} success={data.get('success')} output={short(data.get('output'), 300)} error={short(data.get('error'), 300)}")
    elif kind == "permission.requested":
        print(f"PERM ask    {short(data.get('permissionRequest') or data, 420)}")
    elif kind == "permission.completed":
        print(f"PERM done   {short(data.get('result') or data, 200)}")
    elif kind in ("session.error", "session.warning", "session.info"):
        print(f"SESSION {kind} {short(data, 400)}")
