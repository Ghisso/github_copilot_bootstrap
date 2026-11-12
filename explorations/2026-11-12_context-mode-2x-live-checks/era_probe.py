"""Evidence only: what does real Context Mode 2.1.8 answer to modern (2026-07-28) stdio requests?"""
import json, os, select, subprocess, sys, time

run, binary = sys.argv[1], sys.argv[2]
env = {"PATH": os.environ["PATH"], "HOME": f"{run}/home", "TMPDIR": f"{run}/tmp",
       "CONTEXT_MODE_DATA_DIR": f"{run}/data", "LANG": "C.UTF-8"}
META = {"io.modelcontextprotocol/protocolVersion": "2026-07-28",
        "io.modelcontextprotocol/clientCapabilities": {},
        "io.modelcontextprotocol/clientInfo": {"name": "era-probe", "version": "0"}}

def session(messages, label):
    p = subprocess.Popen([binary, "server", "--agent", "codex"], cwd=f"{run}/repo", env=env, text=True,
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    p.stdin.write("".join(json.dumps(m) + "\n" for m in messages)); p.stdin.flush()
    want = {m["id"] for m in messages if "id" in m}; got = {}; buf = b""; end = time.time() + 40
    fd = p.stdout.fileno()
    while want - set(got) and time.time() < end:
        if not select.select([fd], [], [], max(0, end - time.time()))[0]: break
        chunk = os.read(fd, 65536)
        if not chunk: break
        buf += chunk
        while b"\n" in buf:
            line, _, buf = buf.partition(b"\n")
            msg = json.loads(line); got[msg.get("id")] = msg
    p.terminate(); p.wait(timeout=20)
    print(f"=== {label}")
    for i in sorted(want, key=str):
        m = got.get(i, "NO ANSWER")
        if isinstance(m, dict) and "result" in m:
            r = m["result"]
            keys = sorted(r) if isinstance(r, dict) else type(r).__name__
            print(f"id={i} result keys={keys}")
            if isinstance(r, dict):
                for k in ("supportedVersions", "serverInfo", "_meta"):
                    if k in r: print(f"   {k}={json.dumps(r[k])[:300]}")
                if "instructions" in r: print(f"   instructions starts: {r['instructions'][:160]!r}")
                if "tools" in r: print(f"   tools={[t.get('name') for t in r['tools']]}")
        else:
            print(f"id={i} -> {json.dumps(m)[:300]}")

session([{"jsonrpc": "2.0", "id": 0, "method": "server/discover", "params": {"_meta": META}}], "A: modern server/discover with _meta")
session([{"jsonrpc": "2.0", "id": 0, "method": "server/discover", "params": {}}], "B: server/discover without _meta")
session([{"jsonrpc": "2.0", "id": 0, "method": "server/discover", "params": {"_meta": META}},
         {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {"_meta": META}}], "C: modern discover then modern tools/list, no initialize")
