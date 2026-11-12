"""S2 single-identity check.

Three sessions (Claude Code, Codex, VS Code clientInfo names) share one run folder
per (identity, layout, caps). Each session runs ctx_index(content) then ctx_search.
Prints, per combination: per-session results, server-to-client requests, project
folders created, expected keys, and every file outside the data root.

Usage: python3 -I s2_single.py
"""
import hashlib
import json
import os
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent.parent
RUN = HERE / "run"
NO_CPD = "-CLAUDE_PROJECT_DIR"
CLIENTS = [("claude-code", "alpha"), ("codex-mcp-client", "bravo"), ("Visual Studio Code", "charlie")]
IDENTITIES = {
    "X-codex-nocpd": ([NO_CPD], ["--agent", "codex"]),
    "X2-codex-cpd": ([], ["--agent", "codex"]),
    "Y-noagent-cpd": ([], []),
}
CAPS = {"nocaps": ("{}", ""), "roots": ('{"roots":{"listChanged":true}}', "file://REPO")}


def key_of(path: pathlib.Path) -> str:
    return hashlib.sha256(str(path.resolve()).encode()).hexdigest()[:16]


def prepare(label: str, nested: bool) -> pathlib.Path:
    repo = RUN / label / "repo"
    if not (repo / ".git").exists():
        repo.mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        (repo / "README.md").write_text("capture fixture\n")
    if nested and not (repo / ".claude/.git").exists():
        (repo / ".claude").mkdir(exist_ok=True)
        subprocess.run(["git", "init", "-q", str(repo / ".claude")], check=True)
    return repo


def calls(token: str, others: list[str]) -> list[dict]:
    out = [
        {"method": "tools/call", "params": {"name": "ctx_index", "arguments": {"content": f"# Note {token}\nThe {token} protocol handles marmot frames.", "source": f"note-{token}"}}},
        {"method": "tools/call", "params": {"name": "ctx_search", "arguments": {"queries": [f"{token} protocol"]}}},
    ]
    out += [{"method": "tools/call", "params": {"name": "ctx_search", "arguments": {"queries": [f"{o} protocol"]}}} for o in others]
    return out


def text_of(resp) -> str:
    res = (resp or {}).get("result") or {}
    return ("ERR: " if res.get("isError") or (resp or {}).get("error") else "") + (res.get("content") or [{}])[0].get("text", str(resp))[:90].replace("\n", " | ")


def main() -> None:
    for ident, (flags, args) in IDENTITIES.items():
        for layout in ("flat", "nested"):
            for capname, (caps, root) in CAPS.items():
                label = f"s2s-{ident}-{layout}-{capname}"
                repo = prepare(label, layout == "nested")
                env = dict(os.environ, PROBE_CAPS=caps, PROBE_ROOTS=root.replace("REPO", str(repo)))
                sub = ["CWD_SUB=.claude"] if layout == "nested" else []
                print(f"== {label}")
                for client, token in CLIENTS:
                    cf = HERE / "raw" / f"{label}-{token}-calls.json"
                    cf.write_text(json.dumps(calls(token, [t for _, t in CLIENTS if t != token][:1])))
                    proc = subprocess.run(
                        [str(HERE / "scripts/case.sh"), f"{label}", client, str(cf), "--nonet", "--ro", *flags, *sub, "--", *args],
                        cwd=HERE, env=env, capture_output=True, text=True, timeout=300,
                    )
                    d = json.load(open(HERE / "raw/mcp" / f"{label}.json"))
                    os.replace(HERE / "raw/mcp" / f"{label}.json", HERE / "raw/mcp" / f"{label}-{token}.json")
                    r = d["responses"]
                    print(f"  {client:20s} index={text_of(r.get('3'))[:60]!r} search-own={text_of(r.get('4'))[:70]!r} search-other={text_of(r.get('5'))[:50]!r} srv-reqs={[x['method'] for x in d['server_requests']]}")
                    if proc.returncode:
                        print("   case.sh rc", proc.returncode, proc.stderr[-200:])
                data = repo / ".claude/.cache/context-mode"
                projects = sorted(p.name for p in (data / "projects").glob("*")) if (data / "projects").exists() else []
                print("  project folders:", projects, "| outer key", key_of(repo / ".git"), "| nested key", key_of(repo / ".claude/.git") if layout == "nested" else "-")
                stray = sorted(
                    str(p.relative_to(RUN / label)) for p in (RUN / label).rglob("*")
                    if p.is_file() and ".git/" not in str(p.relative_to(RUN / label)) + "/"
                    and not str(p.relative_to(RUN / label)).startswith("repo/.claude/.cache/context-mode/")
                    and str(p.relative_to(RUN / label)) not in ("repo/README.md",)
                )
                print("  files outside data root (excluding .git, README fixture):", stray)


if __name__ == "__main__":
    main()
