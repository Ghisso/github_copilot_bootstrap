"""Print the hooks and MCP servers recorded in a step3 summary.json."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
project, home = sys.argv[2], sys.argv[3]


def short(value: object) -> str:
    text = value if isinstance(value, str) else json.dumps(value)
    return text.replace(project, "<project>").replace(home, "<home>").replace("file://", "")


hooks = data.get("hooks", {})
counts: Counter[tuple[str, str, str, bool]] = Counter()
for hook in hooks.get("hooks", []):
    source = short(hook.get("source") or hook.get("definitionFileUri") or "")
    counts[(source, hook.get("origin"), hook.get("hookType"), hook.get("enabled"))] += 1
print("== hooks: count | source | origin | event | enabled")
for (source, origin, event, enabled), count in sorted(counts.items(), key=str):
    print(f"  {count} | {source} | {origin} | {event} | {enabled}")
for key in ("warnings", "errors"):
    for line in hooks.get(key, []):
        print(f"  {key[:-1]}: {short(line)[:500]}")
if hooks.get("hooks"):
    print("  sample row:", short(hooks["hooks"][0])[:700])

print("== mcp servers")
for server in data.get("mcp", {}).get("servers", []):
    print("  ", short(server)[:700])
