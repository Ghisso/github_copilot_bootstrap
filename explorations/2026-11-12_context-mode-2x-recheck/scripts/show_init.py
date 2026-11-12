import json, re, sys
d = json.load(open(sys.argv[1]))
init = d["responses"]["1"]["result"]
print("protocolVersion:", init.get("protocolVersion"))
print("serverInfo:", init.get("serverInfo"))
print("capabilities:", json.dumps(init.get("capabilities")))
ins = init.get("instructions") or ""
print("instructions length:", len(ins), "ctx names:", sorted(set(re.findall(r"ctx_[a-z_]+", ins))))
print("--- instructions ---")
print(ins)
tools = {t["name"]: t for t in d["responses"]["2"]["result"]["tools"]}
for name in sys.argv[2:]:
    print("--- description", name, "---")
    print(tools[name]["description"])
