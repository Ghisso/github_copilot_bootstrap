"""Show what each sub-agent conversation received: tools, prompt sources, and instruction files."""

from __future__ import annotations

import json
import sys
from pathlib import Path

run = Path(sys.argv[1])
project = Path(sys.argv[2])

requests = [json.loads(line) for line in (run / "model-requests.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
main_system = "\n".join(next(r for r in requests if r.get("firstRequestSystem") is not None)["firstRequestSystem"])


def lines_of(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            text = parts[2]
    return [line.strip() for line in text.splitlines() if len(line.strip()) > 40]


def coverage(path: Path, haystack: str) -> str:
    lines = lines_of(path)
    if not lines:
        return "n/a"
    return f"{sum(1 for line in lines if line in haystack)}/{len(lines)}"


sources = {
    "AGENTS.md": project / "AGENTS.md",
    "CLAUDE.md": project / "CLAUDE.md",
    "copilot-instructions": project / ".github" / "copilot-instructions.md",
    "always-on adapter (workflow)": project / ".github" / "instructions" / "workflow.instructions.md",
}
print("main conversation: instruction lines present in system prompt")
for name, path in sources.items():
    print(f"   {name}: {coverage(path, main_system)}")
for request in requests:
    key = request.get("childFirstRequest")
    if not key:
        continue
    system = "\n".join(request.get("system") or [])
    users = "\n".join(request.get("userMessages") or [])
    everything = system + "\n" + users
    agent = key.rsplit("-", 1)[-1]
    print(f"\nchild {key}: tools={len(request['toolNames'])}: {', '.join(request['toolNames'])}")
    print(f"   system chars={len(system)} user chars={len(users)}")
    for name, path in sources.items():
        print(f"   {name}: {coverage(path, everything)}")
    for wrapper in (project / ".github" / "agents" / f"{agent}.agent.md", project / ".claude" / "agents" / f"{agent}.md"):
        if wrapper.exists():
            print(f"   agent file {wrapper.relative_to(project)}: {coverage(wrapper, everything)} lines present")
    print("   mentions skills list:", "<available_skills" in everything, "| mentions .claude/agents:", ".claude/agents" in everything)
