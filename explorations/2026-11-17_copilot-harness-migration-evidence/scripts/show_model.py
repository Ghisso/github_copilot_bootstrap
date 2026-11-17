"""Print what the runtime sent to the scripted model: tool names, system prompt facts, MCP status."""

from __future__ import annotations

import json
import sys
from pathlib import Path

run = Path(sys.argv[1])
project, home = sys.argv[2], sys.argv[3]
needles = sys.argv[4:]


def short(text: object, limit: int = 300) -> str:
    value = text if isinstance(text, str) else json.dumps(text, default=str)
    return value.replace(project, "<project>").replace(home, "<home>")[:limit]


requests = [json.loads(line) for line in (run / "model-requests.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
for index, request in enumerate(requests):
    if "toolNames" not in request:
        print(f"[{index}] note: {short(request, 400)}")
        continue
    print(f"[{index}] main={request.get('isMain')} lastRole={request.get('lastRole')} tools={len(request['toolNames'])} ctxHits={short(request.get('ctxHits'), 500)}")
    if request.get("firstRequestTools") is not None:
        print("    tool names:", ", ".join(request["toolNames"]))
        system = "\n".join(request.get("firstRequestSystem") or [])
        print(f"    system prompt chars: {len(system)}")
        for needle in needles:
            print(f"    system contains {needle!r}: {needle in system}")
    if request.get("lastRole") == "tool":
        print("    tool result seen by model:", short(request.get("lastContent"), 260))

events = [json.loads(line) for line in (run / "events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
for event in events:
    kind = event.get("type")
    data = event.get("data", {})
    if kind in ("session.mcp_server_status_changed", "session.mcp_servers_loaded", "session.mcp_server_tools_loaded"):
        print(kind, short(data, 420))
    elif kind in ("session.skills_loaded",):
        skills = data.get("skills") or []
        print(kind, len(skills), "skills; sources:", sorted({str(s.get("source")) for s in skills}))
    elif kind == "session.tools_updated":
        print(kind, short(data, 300))
