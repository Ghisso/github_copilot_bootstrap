"""Print probe hook logs: one entry per label (or all with --all), stdin as compact JSON."""

from __future__ import annotations

import json
import sys
from pathlib import Path

log_dir = Path(sys.argv[1])
project, home = sys.argv[2], sys.argv[3]
only = sys.argv[4] if len(sys.argv) > 4 else ""
show_all = "--all" in sys.argv
limit = 1500

seen: set[str] = set()
for path in sorted(log_dir.iterdir()):
    label = path.name.split("-", 1)[1].removesuffix(".log")
    if only and only not in label:
        continue
    if label in seen and not show_all:
        continue
    seen.add(label)
    text = path.read_text(encoding="utf-8", errors="replace")
    head, _, stdin = text.partition("stdin=")
    # VSCODE_* values come from the shell this spike ran in, not from the runtime.
    env_lines = [line for line in head.splitlines() if "=" in line and not line.startswith(("label=", "argv=", "VSCODE_", "replied-with=", "reply-skipped="))]
    stdin = stdin.strip()
    try:
        payload = json.loads(stdin)
        for key in ("transformedPrompt", "custom_instructions", "transformed_prompt"):
            if isinstance(payload, dict) and isinstance(payload.get(key), str) and len(payload[key]) > 120:
                payload[key] = payload[key][:120] + "...<cut>"
        stdin = json.dumps(payload)
    except json.JSONDecodeError:
        pass
    stdin = stdin.replace(project, "<project>").replace(home, "<home>")
    print(f"### {label}")
    if not only or show_all:
        print("   env:", "; ".join(line.replace(project, "<project>").replace(home, "<home>") for line in env_lines)[:500])
    print("   stdin:", stdin[:limit])
