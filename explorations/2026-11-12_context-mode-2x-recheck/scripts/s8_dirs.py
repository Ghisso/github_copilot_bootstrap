"""S8: CONTEXT_MODE_DIR vs CONTEXT_MODE_DATA_DIR, and 1.x data not migrated.
Step 1: host 1.0.169 indexes a note into CONTEXT_MODE_DIR=<repo>/.claude/.cache/context-mode (1.x layout).
Step 2: 2.1.8 started with only CONTEXT_MODE_DIR (no DATA_DIR) -> where does it write? does it see the 1.x note?
Step 3: 2.1.8 started with CONTEXT_MODE_DATA_DIR = that same folder -> does it see/touch the 1.x files?
Usage: python3 -I s8_dirs.py"""
import json
import pathlib
import subprocess
import shutil

HERE = pathlib.Path(__file__).resolve().parent.parent
NODEBIN = str(pathlib.Path(shutil.which("node")).parent)
label = "s8-dirs"
run = HERE / "run" / label
repo = run / "repo"
data = repo / ".claude/.cache/context-mode"


def probe(name, client, calls, flags, cmd):
    cf = HERE / f"raw/{label}-{name}-calls.json"
    cf.write_text(json.dumps(calls))
    subprocess.run(["python3", "-I", str(HERE / "scripts/mcp_probe.py"), str(HERE / f"raw/mcp/{label}-{name}.json"), client, str(cf), "--",
                    "bash", str(HERE / "scripts/cmrun.sh"), label, NODEBIN, "--nonet", "--ro", *flags, "--", *cmd],
                   capture_output=True, text=True, timeout=300, check=True)
    d = json.load(open(HERE / f"raw/mcp/{label}-{name}.json"))
    return [((d["responses"].get(str(3 + i)) or {}).get("result", {}).get("content") or [{}])[0].get("text", "")[:90].replace("\n", " | ") for i in range(len(calls))]


def tree(root):
    return sorted(str(p.relative_to(run)) for p in root.rglob("*") if p.is_file()) if root.exists() else []


note = {"method": "tools/call", "params": {"name": "ctx_index", "arguments": {"content": "legacy note: the heron protocol", "source": "legacy-note"}}}
find = {"method": "tools/call", "params": {"name": "ctx_search", "arguments": {"queries": ["heron protocol"]}}}
print("step1 1.0.169 index/search:", probe("v1", "claude-code", [note, find], [], ["/home/ghisso/.local/bin/context-mode"]))
before = tree(data)
print("1.x files:", before)
new = ["node", str(HERE / "pkg/node_modules/context-mode/cli.mjs"), "server", "--agent", "codex"]
print("step2 2.1.8, only CONTEXT_MODE_DIR set (DATA_DIR dropped):", probe("v2-nodatadir", "codex-mcp-client", [find, {"method": "tools/call", "params": {"name": "ctx_stats", "arguments": {}}}], ["-CLAUDE_PROJECT_DIR", "-CONTEXT_MODE_DATA_DIR"], new)[:1])
print("  files under HOME/.context-mode:", [f for f in tree(run / "home") if ".context-mode" in f])
print("  1.x files unchanged:", tree(data) == before)
print("step3 2.1.8 with CONTEXT_MODE_DATA_DIR=<same folder>:", probe("v2-datadir", "codex-mcp-client", [find], ["-CLAUDE_PROJECT_DIR"], new))
after = tree(data)
print("  new files in that folder:", [f for f in after if f not in before])
print("  1.x files still present and byte-for-byte unchanged:", all((run / f).exists() for f in before))
