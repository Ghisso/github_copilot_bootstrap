"""Send initialize and tools/list back to back (no wait), as a pipelining client would."""

import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path("/home/ghisso/work/github_copilot_bootstrap")
version = sys.argv[1] if len(sys.argv) > 1 else "2025-11-25"
proc = subprocess.Popen(
    ["bash", str(REPO / "shared/hooks/scripts/context-mode-dispatch.sh"), "server"],
    cwd=REPO, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
)
msgs = [
    {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": version, "capabilities": {}, "clientInfo": {"name": "pipeline-probe", "version": "0"}}},
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
    {"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
]
proc.stdin.write("".join(json.dumps(m) + "\n" for m in msgs))
proc.stdin.flush()
seen = {}
end = time.time() + 120
while len(seen) < 2 and time.time() < end:
    line = proc.stdout.readline()
    if not line:
        break
    msg = json.loads(line)
    seen[msg.get("id")] = msg
    print(f"id={msg.get('id')} ->", json.dumps(msg)[:260])
proc.stdin.close()
proc.wait(timeout=30)
