"""S8: CLI forms, the unpatched kit filter vs 2.1.8, and a gate-patched filter copy (scratch only) vs 2.1.8.
Usage: python3 -I s8_misc.py"""
import json
import pathlib
import shutil
import subprocess

HERE = pathlib.Path(__file__).resolve().parent.parent
NODEBIN = str(pathlib.Path(shutil.which("node")).parent)
CLI = str(HERE / "pkg/node_modules/context-mode/cli.mjs")
SERVER = ["node", CLI, "server", "--agent", "codex"]


def cm(label, flags, cmd, stdin=""):
    r = subprocess.run(["bash", str(HERE / "scripts/cmrun.sh"), label, NODEBIN, "--nonet", "--ro", *flags, "--", *cmd],
                       input=stdin, capture_output=True, text=True, timeout=120)
    return r


for name, args in (("bare", []), ("--version", ["--version"]), ("-v", ["-v"]), ("version", ["version"])):
    r = cm("s8-cli", ["-CLAUDE_PROJECT_DIR"], ["node", CLI, *args])
    print(f"cli {name!r}: exit {r.returncode} stdout[0:100]={r.stdout.strip().splitlines()[:1]} stderr[0:100]={r.stderr.strip().splitlines()[:1]}")


def probe(name, cmd, calls, flags=("-CLAUDE_PROJECT_DIR",)):
    cf = HERE / f"raw/s8-{name}-calls.json"
    cf.write_text(json.dumps(calls))
    subprocess.run(["python3", "-I", str(HERE / "scripts/mcp_probe.py"), str(HERE / f"raw/mcp/s8-{name}.json"), "codex-mcp-client", str(cf), "--",
                    "bash", str(HERE / "scripts/cmrun.sh"), "s8-filter", NODEBIN, "--nonet", "--ro", *flags, "--", *cmd],
                   capture_output=True, text=True, timeout=300, check=True)
    return json.load(open(HERE / f"raw/mcp/s8-{name}.json"))


call = lambda n, a: {"method": "tools/call", "params": {"name": n, "arguments": a}}
d = probe("mcp-alias", ["node", CLI, "mcp", "--agent", "codex"], [call("ctx_stats", {})])
print("alias `mcp --agent codex`: tools", len(d["responses"]["2"]["result"]["tools"]), "stats isError", d["responses"]["3"]["result"]["isError"])

d = probe("filter-unpatched", ["node", str(HERE / "context-mode-mcp-filter.mjs"), "--", *SERVER], [call("ctx_stats", {})])
print("unpatched kit filter vs 2.1.8: initialize ->", json.dumps(d["responses"].get("1"))[:160], "| tools/list ->", json.dumps(d["responses"].get("2"))[:120], "| exit", d["exit_code"])

calls = [call("ctx_index", {"content": "filter note quokka", "source": "n"}), call("ctx_index", {"url": "https://example.com"}),
         call("ctx_index", {"path": "README.md"}), call("ctx_search", {"queries": ["quokka"]}), call("ctx_doctor", {}),
         call("ctx_execute", {"language": "shell", "code": "echo hi"}), call("ctx_batch", {"commands": []}), call("ctx_resume", {})]
d = probe("filter-gate-dev", ["node", str(HERE / "filter-gate-dev.mjs"), "--", *SERVER], calls)
init = d["responses"]["1"]["result"]
tools = d["responses"]["2"]["result"]["tools"]
print("gate-patched filter: initialize keys", sorted(init), "instructions chars", len(init.get("instructions", "")), "| tools:", [t["name"] for t in tools])
print("  ctx_index properties after filter:", list(next(t for t in tools if t["name"] == "ctx_index")["inputSchema"]["properties"]))
for i, c in enumerate(calls):
    r = d["responses"].get(str(3 + i), {})
    res = r.get("result")
    print(f"  {c['params']['name']} {list(c['params']['arguments'])}: " + (f"result isError={res.get('isError')} {res['content'][0]['text'][:60]!r}" if res else f"error {r.get('error')}"))
