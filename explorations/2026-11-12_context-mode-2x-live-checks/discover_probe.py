"""Send the 2026-07-28 MCP 'server/discover' probe through the kit's dispatcher and filter."""

import json
import subprocess
import time
from pathlib import Path

REPO = Path("/home/ghisso/work/github_copilot_bootstrap")
proc = subprocess.Popen(
    ["bash", str(REPO / "shared/hooks/scripts/context-mode-dispatch.sh"), "server"],
    cwd=REPO, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
)


def rpc(obj, want_id):
    proc.stdin.write(json.dumps(obj) + "\n")
    proc.stdin.flush()
    end = time.time() + 120
    while time.time() < end:
        line = proc.stdout.readline()
        if not line:
            return "EOF"
        msg = json.loads(line)
        if msg.get("id") == want_id:
            return msg
    return "TIMEOUT"


disc = rpc({"jsonrpc": "2.0", "id": 0, "method": "server/discover", "params": {}}, 0)
print("server/discover ->", json.dumps(disc)[:900])
tl = rpc({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}, 1)
print("tools/list ->", json.dumps(tl)[:300])
proc.stdin.close()
proc.wait(timeout=30)
