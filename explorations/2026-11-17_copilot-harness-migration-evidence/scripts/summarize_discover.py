"""Print a compact view of a step2_discover.mjs result file."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
project = sys.argv[2]
home = sys.argv[3]


def short(value: object) -> str:
    text = value if isinstance(value, str) else json.dumps(value)
    return text.replace(project, "<project>").replace(home, "<home>").replace("file://", "")


def section(name: str) -> dict:
    value = data.get(name) or {}
    print(f"\n== {name}")
    if "__error" in value:
        print("  ERROR", short(value["__error"]))
        return {}
    return value


hooks = section("hooks.discover")
for hook in hooks.get("hooks", []):
    print("  ", hook.get("hookType"), "|", hook.get("origin"), "|", hook.get("enabled"), "|", short(hook.get("source", "")))
for key in ("warnings", "errors"):
    for line in hooks.get(key, []):
        print(f"  {key[:-1]}:", short(line)[:400])
counts = Counter((h.get("hookType"), h.get("origin"), short(h.get("source", ""))) for h in hooks.get("hooks", []))
if counts:
    print("  -- counts by (event, origin, source)")
    for key, count in sorted(counts.items()):
        print("  ", count, key)

mcp = section("mcp.discover")
for server in mcp.get("servers", []):
    print("  ", short({k: server.get(k) for k in ("name", "type", "source", "enabled", "sourcePath", "effectiveSource")})[:400])

paths = section("instructions.getDiscoveryPaths")
for entry in paths.get("paths", []):
    print("  ", short(entry)[:300])
sources = section("instructions.discover")
for entry in sources.get("sources", []):
    view = {k: v for k, v in entry.items() if k not in ("content", "contents", "text", "body")}
    size = len(entry.get("content") or entry.get("contents") or entry.get("text") or "")
    print("  ", short(view)[:330], f"| chars={size}")

paths = section("skills.getDiscoveryPaths")
for entry in paths.get("paths", []):
    print("  ", short(entry)[:300])
skills = section("skills.discover")
skill_sources = Counter()
for skill in skills.get("skills", []):
    location = short(skill.get("path") or skill.get("location") or skill.get("filePath") or "")
    root = "/".join(location.split("/")[:3])
    skill_sources[(skill.get("source"), root)] += 1
for key, count in sorted(skill_sources.items(), key=str):
    print("  ", count, key)
if skills.get("skills"):
    print("   sample:", short({k: v for k, v in skills["skills"][0].items() if k != "content"})[:500])

paths = section("agents.getDiscoveryPaths")
for entry in paths.get("paths", []):
    print("  ", short(entry)[:300])
agents = section("agents.discover")
for agent in agents.get("agents", []):
    view = {k: v for k, v in agent.items() if k not in ("prompt", "instructions", "content")}
    print("  ", short(view)[:600])

tools = section("tools.list")
print("  ", ", ".join(sorted(t.get("name", "?") for t in tools.get("tools", []))))

settings = section("user.settings.get").get("settings", {})
for key in sorted(settings):
    if any(word in key.lower() for word in ("hook", "trust", "folder", "permission", "mcp", "skill", "instruction", "claude")):
        print("  ", key, "=", short(settings[key])[:200])
print("   all setting keys:", ", ".join(sorted(settings)))
