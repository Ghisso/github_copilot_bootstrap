"""Print the three kit tools from probe result files, and diff them across files.

Usage: python3 -I dump_tools.py <probe.json> [<probe.json> ...]
First file is printed in full (description, inputSchema, property descriptions,
_meta, annotations); every file is then compared with the first for these three
tools plus the full tool-name list and the initialize result.
"""
import json
import sys

KIT = ["ctx_index", "ctx_search", "ctx_stats"]


def load(path):
    d = json.load(open(path))
    tools = {t["name"]: t for t in d["responses"]["2"]["result"]["tools"]}
    return d["responses"]["1"]["result"], tools


def main() -> int:
    base_init, base_tools = load(sys.argv[1])
    print("initialize keys:", sorted(base_init), "| serverInfo:", base_init["serverInfo"])
    print("capabilities:", json.dumps(base_init["capabilities"]))
    print("instructions chars:", len(base_init.get("instructions") or ""))
    print("tool names:", list(base_tools))
    for name in KIT:
        t = base_tools[name]
        print("\n" + "=" * 70 + "\n" + name)
        print("tool keys:", sorted(t))
        print("_meta:", json.dumps(t.get("_meta")), "| annotations:", json.dumps(t.get("annotations")))
        print("description (%d chars):\n%s" % (len(t["description"]), t["description"]))
        print("inputSchema:", json.dumps({k: v for k, v in t["inputSchema"].items() if k != "properties"}))
        for prop, spec in t["inputSchema"]["properties"].items():
            print("  property %s: %s" % (prop, json.dumps(spec)))
    for other in sys.argv[2:]:
        init, tools = load(other)
        print("\n--- diff vs", other)
        print("  tool names equal:", list(tools) == list(base_tools), "| initialize equal:", init == base_init)
        for name in KIT:
            print("  %s identical: %s" % (name, tools[name] == base_tools[name]))
    return 0


raise SystemExit(main())
