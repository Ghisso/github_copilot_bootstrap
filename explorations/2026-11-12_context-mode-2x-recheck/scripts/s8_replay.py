"""S8: replay the 32 recorded hook inputs against 2.1.7 and 2.1.8 inside the read-only, no-network sandbox,
then copy the outputs to raw/hooks-<version>. Usage: python3 -I s8_replay.py"""
import pathlib
import shutil
import subprocess

HERE = pathlib.Path(__file__).resolve().parent.parent
NODEBIN = str(pathlib.Path(shutil.which("node")).parent)
for version, pkg in (("2.1.7", "pkg-2.1.7"), ("2.1.8", "pkg")):
    label = f"hooks-{version}"
    run = HERE / "run" / label
    run.mkdir(parents=True, exist_ok=True)
    out = subprocess.run(
        ["bash", str(HERE / "scripts/cmrun.sh"), label, NODEBIN, "--nonet", "--ro", "--",
         "python3", "-B", "-I", str(HERE / "scripts/replay_hooks.py"), str(run),
         str(HERE / pkg / "node_modules/context-mode/cli.mjs"), version, str(run / "out")],
        capture_output=True, text=True, timeout=800,
    )
    (HERE / f"raw/hooks-{version}-replay.tsv").write_text(out.stdout)
    (HERE / f"raw/hooks-{version}-replay.err").write_text(out.stderr)
    dest = HERE / f"raw/hooks-{version}"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(run / "out", dest)
    print(version, "exit", out.returncode, "cases", len(out.stdout.splitlines()), "stderr tail:", out.stderr.strip().splitlines()[-2:])
