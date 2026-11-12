"""S2: run every server-identity case, print a one-line summary per case.

Usage: python3 -I s2_matrix.py   (run from anywhere; paths derive from this file)
"""
import json
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent.parent
RUN = HERE / "run"
NO_CPD = "-CLAUDE_PROJECT_DIR"


def cases():
    repo = lambda label: str(RUN / label / "repo")
    return [
        ("a1-claude-with-cpd", [], ["--agent", "claude-code"]),
        ("a2-claude-no-cpd", [NO_CPD], ["--agent", "claude-code"]),
        ("b1-codex-no-cpd", [NO_CPD], ["--agent", "codex"]),
        ("b2-codex-with-cpd", [], ["--agent", "codex"]),
        ("c1-vscode-ws", [NO_CPD], ["--agent", "vscode", "--workspace-folder", repo("c1-vscode-ws")]),
        ("c2-vscode-nows", [NO_CPD], ["--agent", "vscode"]),
        ("d1-noagent-cpd", [], []),
        ("d2-noagent-nocpd", [NO_CPD], []),
    ]


def main() -> None:
    for label, flags, args in cases():
        proc = subprocess.run(
            [str(HERE / "scripts/case.sh"), label, "claude-code", "scripts/calls-s2.json", "--nonet", "--ro", *flags, "--", *args],
            cwd=HERE, capture_output=True, text=True, timeout=300,
        )
        d = json.load(open(HERE / "raw/mcp" / f"{label}.json"))
        init = d["responses"].get("1", {})
        tool_results = {}
        for i, name in (("3", "index"), ("4", "search"), ("5", "stats")):
            r = d["responses"].get(i, {})
            res = r.get("result") or {}
            tool_results[name] = "error" if r.get("error") or res.get("isError") else ("ok" if res else "none")
        dbs = sorted(str(p.relative_to(RUN / label)) for p in (RUN / label).rglob("context.db"))
        print(label, "| init:", "error" if init.get("error") else (init.get("result") or {}).get("serverInfo"),
              "| tools:", len(((d["responses"].get("2") or {}).get("result") or {}).get("tools") or []),
              "|", tool_results, "| dbs:", dbs, "| exit", d["exit_code"], "| srv-reqs", len(d["server_requests"]))
        if proc.returncode:
            print("   case.sh rc", proc.returncode, proc.stderr[-300:])


main()
