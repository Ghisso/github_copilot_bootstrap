"""Compare tools/list output of two mcp_probe result files for selected tools."""

import json
import re
import sys

ALLOWED = ["ctx_index", "ctx_search", "ctx_stats", "ctx_doctor"]


def tools_of(path: str) -> dict:
    data = json.load(open(path))
    listing = data["responses"]["2"]["result"]["tools"]
    return {tool["name"]: tool for tool in listing}


def main() -> int:
    old, new = tools_of(sys.argv[1]), tools_of(sys.argv[2])
    print("old tools:", sorted(old))
    print("new tools:", sorted(new))
    print("removed:", sorted(set(old) - set(new)))
    print("added:", sorted(set(new) - set(old)))
    for name in ALLOWED:
        print("\n" + "=" * 70)
        print(name)
        for label, table in (("1.0.169", old), ("2.1.7", new)):
            tool = table.get(name)
            if tool is None:
                print(f"  [{label}] MISSING")
                continue
            schema = tool.get("inputSchema", {})
            props = schema.get("properties", {})
            print(f"  [{label}] required={schema.get('required')} additionalProperties={schema.get('additionalProperties')} $schema={schema.get('$schema')}")
            for prop, spec in props.items():
                brief = {k: v for k, v in spec.items() if k != "description"}
                print(f"     - {prop}: {json.dumps(brief)[:300]}")
            other = {k: v for k, v in tool.items() if k not in ("name", "description", "inputSchema")}
            if other:
                print(f"     other keys: {json.dumps(other)[:300]}")
            desc = tool.get("description", "")
            refs = sorted(set(re.findall(r"ctx_[a-z_]+", desc)))
            print(f"     description: {len(desc)} chars; ctx_ names mentioned: {refs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
