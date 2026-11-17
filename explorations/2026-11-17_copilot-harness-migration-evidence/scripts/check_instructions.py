"""Check which instruction files of the probe project appear in the model's system prompt."""

from __future__ import annotations

import json
import sys
from pathlib import Path

run = Path(sys.argv[1])
project = Path(sys.argv[2])
request_index = int(sys.argv[3]) if len(sys.argv) > 3 else 0

requests = [json.loads(line) for line in (run / "model-requests.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
with_system = [r for r in requests if r.get("firstRequestSystem") is not None]
system = "\n".join(with_system[request_index]["firstRequestSystem"])
print(f"system prompt: {len(system)} chars")


def body_lines(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            text = parts[2]
    return [line.strip() for line in text.splitlines() if len(line.strip()) > 40]


candidates = [project / ".github" / "copilot-instructions.md", project / "AGENTS.md", project / "CLAUDE.md"]
candidates += sorted((project / ".github" / "instructions").glob("*.md"))
candidates += sorted((project / ".claude" / "rules").glob("*.md"))
candidates += sorted((project / ".claude" / "instructions").glob("*.md"))
total = 0
for path in candidates:
    lines = body_lines(path)
    if not lines:
        print(f"  {path.relative_to(project)}: no usable lines")
        continue
    present = sum(1 for line in lines if line in system)
    probe = lines[len(lines) // 2]
    size = len(path.read_text(encoding="utf-8"))
    loaded = present / len(lines)
    if loaded > 0.5:
        total += size
    print(f"  {str(path.relative_to(project)):70s} size={size:6d} lines_in_prompt={present}/{len(lines)} mid_line_count={system.count(probe)}")
print(f"instruction bytes judged loaded: {total}")
for marker in ("<custom_instruction", "<skills", "<available_skills", "<agent", "applyTo"):
    print(f"  marker {marker!r} count: {system.count(marker)}")
