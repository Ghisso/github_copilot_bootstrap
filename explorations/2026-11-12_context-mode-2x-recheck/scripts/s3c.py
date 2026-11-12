"""S3 extra: .gitignore at the repo root vs inside the indexed folder, and ctx_index path "." in a repo that
already holds the data root (<repo>/.claude/.cache/context-mode/.../context.db). Usage: python3 -I s3b.py"""
import json
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent.parent
RUN = HERE / "run" / "s3c"
REPO = RUN / "repo"
if RUN.exists():
    subprocess.run(["rm", "-rf", str(RUN)], check=True)
REPO.mkdir(parents=True)
subprocess.run(["git", "init", "-q", str(REPO)], check=True)
(REPO / ".gitignore").write_text("rootignored.txt\n")
(REPO / "rootignored.txt").write_text("rootignoredtoken\n")
(REPO / "readme.txt").write_text("plainreadmetoken\n")
(REPO / "sub").mkdir()
(REPO / "sub/.gitignore").write_text("nestedignored.txt\n")
(REPO / "sub/nestedignored.txt").write_text("nestedignoredtoken\n")
(REPO / "sub/kept.txt").write_text("keptsubtoken\n")
(REPO / ".claude").mkdir()
(REPO / ".claude/note.md").write_text("# claude folder note\nclaudenotetoken\n")
idx = lambda p: {"method": "tools/call", "params": {"name": "ctx_index", "arguments": {"path": p}}}
srch = lambda q: {"method": "tools/call", "params": {"name": "ctx_search", "arguments": {"queries": [q]}}}
calls = [
    {"method": "tools/call", "params": {"name": "ctx_index", "arguments": {"content": "seed note seedtoken", "source": "seed"}}},
    idx("sub"), srch("nestedignoredtoken"), srch("keptsubtoken"),
    idx("."), srch("rootignoredtoken"), srch("plainreadmetoken"), srch("claudenotetoken"),
    srch("SQLite format"), srch("zzzznomatchzzzz"),
]
(HERE / "scripts/calls-s3c.json").write_text(json.dumps(calls))
