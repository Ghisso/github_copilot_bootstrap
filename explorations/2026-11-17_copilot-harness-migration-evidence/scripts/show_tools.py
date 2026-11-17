"""Print built-in tool names and their argument names from a discover result file."""

from __future__ import annotations

import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for tool in data.get("tools.list", {}).get("tools", []):
    params = tool.get("parameters") or tool.get("inputSchema") or {}
    props = params.get("properties", {}) if isinstance(params, dict) else {}
    required = set(params.get("required", [])) if isinstance(params, dict) else set()
    args = ", ".join(f"{name}{'*' if name in required else ''}" for name in props)
    extra = {k: v for k, v in tool.items() if k not in ("parameters", "inputSchema", "description", "name", "instructions")}
    print(f"{tool.get('name')}({args}) {json.dumps(extra)[:160]}")
