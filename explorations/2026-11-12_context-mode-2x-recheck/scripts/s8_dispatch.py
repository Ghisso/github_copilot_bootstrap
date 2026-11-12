"""S8: dispatcher --self-check with the 2.1.8 binary first on PATH, and with the host 1.0.169 first. Sandboxed, no network.
Usage: python3 -I s8_dispatch.py"""
import pathlib
import subprocess

HERE = pathlib.Path(__file__).resolve().parent.parent
for variant, first in (("2.1.8", HERE / "pkg/node_modules/.bin"), ("host-1.0.169", pathlib.Path("/home/ghisso/.local/bin"))):
    r = subprocess.run(
        ["bash", str(HERE / "scripts/cmrun.sh"), "s8-dispatch", f"{first}:/home/ghisso/.local/bin", "--nonet", "--ro", "--",
         "bash", str(HERE / "context-mode-dispatch.sh"), "--self-check"],
        capture_output=True, text=True, timeout=120)
    print(f"## --self-check, {variant} first on PATH: exit {r.returncode}")
    print((r.stdout + r.stderr).strip()[:1500])
