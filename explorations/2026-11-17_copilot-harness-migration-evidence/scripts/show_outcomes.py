"""One line per tool call: what was asked, what the hooks and permission flow did, and the result."""

from __future__ import annotations

import json
import sys
from pathlib import Path

run = Path(sys.argv[1])
project, home = sys.argv[2], sys.argv[3]


def short(value: object, limit: int = 150) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text.replace(project, "<project>").replace(home, "<home>").replace("\n", " ")[:limit]


events = [json.loads(line) for line in (run / "events.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
current: dict | None = None
rows: list[dict] = []
for event in events:
    kind, data = event.get("type"), event.get("data", {})
    if kind == "tool.execution_start":
        args = data.get("arguments") or {}
        what = (args.get("command") or args.get("path") or args) if isinstance(args, dict) else args
        current = {"tool": data.get("toolName"), "what": short(what, 70), "pre": "", "perm": [], "post": [], "result": ""}
        rows.append(current)
    elif current is None:
        continue
    elif kind == "hook.end" and data.get("hookType") == "preToolUse":
        current["pre"] = short(data.get("output") or ("error:" + str(data.get("error")) if data.get("error") else "no output"), 170)
    elif kind == "permission.requested":
        request = data.get("permissionRequest") or {}
        current["perm"].append(f"{request.get('kind')}:{short(request.get('intention') or request.get('fullCommandText') or request.get('toolName') or '', 60)}")
    elif kind == "permission.completed":
        current["perm"].append("=> " + short((data.get("result") or {}).get("kind"), 60))
    elif kind == "hook.end" and data.get("hookType") in ("postToolUse", "postToolUseFailure"):
        current["post"].append(data.get("hookType"))
    elif kind == "tool.execution_complete":
        result = data.get("result") or {}
        text = result.get("content") if isinstance(result, dict) else result
        error = data.get("error") or {}
        current["result"] = f"success={data.get('success')} " + short(error.get("message") if isinstance(error, dict) and error else text, 150)
for index, row in enumerate(rows, 1):
    print(f"{index:02d} {row['tool']}: {row['what']}")
    print(f"     preToolUse hooks: {row['pre']}")
    print(f"     permission: {' '.join(row['perm']) or 'none requested'}")
    print(f"     result: {row['result']}  post={row['post']}")
