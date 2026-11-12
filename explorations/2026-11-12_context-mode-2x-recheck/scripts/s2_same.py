"""S2: do identities X (--agent codex) and Y (CLAUDE_PROJECT_DIR, no --agent) land in ONE project folder
for the same repository when a nested Git repo exists at <repo>/.claude? Server started from the repo
root, then from the nested folder. Usage: python3 -I s2_same.py"""
import json
import os
import pathlib
import subprocess
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import s2_single as s  # noqa: E402

for start in ("root", "nested"):
    label = f"s2same-{start}"
    repo = s.prepare(label, True)
    sub = ["CWD_SUB=.claude"] if start == "nested" else []
    for ident in ("X-codex-nocpd", "Y-noagent-cpd"):
        flags, args = s.IDENTITIES[ident]
        cf = s.HERE / "raw" / f"{label}-{ident}-calls.json"
        cf.write_text(json.dumps(s.calls("delta", [])))
        subprocess.run([str(s.HERE / "scripts/case.sh"), label, "claude-code", str(cf), "--nonet", "--ro", *flags, *sub, "--", *args],
                       cwd=s.HERE, env=dict(os.environ), capture_output=True, text=True, timeout=300, check=True)
        os.replace(s.HERE / "raw/mcp" / f"{label}.json", s.HERE / "raw/mcp" / f"{label}-{ident}.json")
        data = repo / ".claude/.cache/context-mode/projects"
        print(f"start={start} after {ident}: project folders {sorted(p.name for p in data.glob('*'))}")
    print(f"start={start}: outer key {s.key_of(repo / '.git')} nested key {s.key_of(repo / '.claude/.git')}")
