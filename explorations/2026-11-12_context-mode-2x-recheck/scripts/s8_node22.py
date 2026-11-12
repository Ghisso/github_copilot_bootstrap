"""S8: Node 22.22.0 (the devcontainer's current image) with 2.1.8: install message, --version, and server tools.
Usage: python3 -I s8_node22.py"""
import json
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent.parent
IMG = "node:22.22.0-bookworm-slim"
r = subprocess.run(["docker", "run", "--rm", IMG, "bash", "-c",
                    "node --version; npm install -g --ignore-scripts context-mode@2.1.8 2>&1 | grep -i -E 'EBADENGINE|engine|required|added' | head -5; echo \"exit-after-install=$?\"; echo \"--version: $(context-mode --version 2>&1)\""],
                   capture_output=True, text=True, timeout=300)
print(r.stdout[-1500:], r.stderr[-300:])
out = HERE / "raw/mcp/s8-node22.json"
subprocess.run(["python3", "-I", str(HERE / "scripts/mcp_probe.py"), str(out), "codex-mcp-client", str(HERE / "scripts/calls-s2.json"), "--",
                "docker", "run", "--rm", "-i", "--network", "none", "-v", f"{HERE / 'pkg'}:/pkg:ro", IMG, "bash", "-c",
                "mkdir -p /tmp/r/.git && echo ref: refs/heads/main > /tmp/r/.git/HEAD && cd /tmp/r && CONTEXT_MODE_DATA_DIR=/tmp/r/.claude/.cache/context-mode exec node /pkg/node_modules/context-mode/cli.mjs server --agent codex"],
               check=True, capture_output=True, text=True, timeout=300)
d = json.load(open(out))
print("exit", d["exit_code"], "responses", list(d["responses"]), "stderr", d["stderr"][:4])
print("Node 22.22.0 server: serverInfo", d["responses"]["1"]["result"]["serverInfo"], "tools", [t["name"] for t in d["responses"]["2"]["result"]["tools"]])
print("  tool call 3:", json.dumps(d["responses"].get("3"))[:300])
print("  stderr:", d["stderr"][:3])
