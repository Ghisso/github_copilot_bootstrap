"""S8: run the three synthetic hook sequences (steps-*.json) against 2.1.7 and 2.1.8 in the sandbox and compare.
Usage: python3 -I s8_sequences.py"""
import json
import pathlib
import shutil
import subprocess

HERE = pathlib.Path(__file__).resolve().parent.parent
NODEBIN = str(pathlib.Path(shutil.which("node")).parent)
TARGETS = {"claude": "claude-code", "codex": "codex", "vscode": "vscode-copilot"}
results = {}
for version, pkg in (("2.1.7", "pkg-2.1.7"), ("2.1.8", "pkg")):
    for name, target in TARGETS.items():
        label = f"seq-{name}-{version}"
        run = HERE / "run" / label
        run.mkdir(parents=True, exist_ok=True)
        out = run / "out.json"
        proc = subprocess.run(
            ["bash", str(HERE / "scripts/cmrun.sh"), label, NODEBIN, "--nonet", "--ro", "--", "python3", "-B", "-I",
             str(HERE / "scripts/run_sequence.py"), str(run), str(HERE / pkg / "node_modules/context-mode/cli.mjs"), target,
             str(HERE / f"scripts/steps-{name}.json"), str(out)],
            capture_output=True, text=True, timeout=600,
        )
        (HERE / f"raw/seq-{name}-{version}.json").write_text(out.read_text())
        results[(name, version)] = json.loads(out.read_text())
        print(name, version, "rc", proc.returncode, "steps", len(results[(name, version)]))
for name in TARGETS:
    a, b = results[(name, "2.1.7")], results[(name, "2.1.8")]
    for x, y in zip(a, b):
        same = all(x[k] == y[k] for k in ("exit_code", "stdout", "filtered_stdout"))
        print(f"  {name}/{x['label']}: identical={same} stdout_bytes {x['stdout_bytes']} -> {y['stdout_bytes']} hso_keys {y['hso_keys']}")
        if not same:
            print("     2.1.7:", x["stdout"][:400].replace("\n", " "))
            print("     2.1.8:", y["stdout"][:400].replace("\n", " "))
