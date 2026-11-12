"""S8: compare hook replay outputs: 2.1.7 vs 2.1.8 (stdout, exit code, filtered stdout), and 2.1.8 vs the 1.0.169 fixtures.
Usage: python3 -I s8_hook_diff.py"""
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent.parent
FIX = pathlib.Path("/home/ghisso/work/github_copilot_bootstrap/tests/fixtures/context_mode_hook/1.0.169")
a, b = HERE / "raw/hooks-2.1.7", HERE / "raw/hooks-2.1.8"
same = diff = fixture_same = fwd = 0
for p in sorted(b.glob("*/*.json")):
    r8, r7 = json.loads(p.read_text()), json.loads((a / p.parent.name / p.name).read_text())
    fx = json.loads((FIX / p.parent.name / p.name).read_text())
    keys = ("exit_code", "stdout", "filtered_stdout")
    eq = all(r8[k] == r7[k] for k in keys)
    same += eq
    diff += not eq
    fixture_same += r8["stdout"] == fx["stdout"]
    fwd += bool(r8["filtered_stdout"])
    if not eq:
        print(f"CHANGED 2.1.7 -> 2.1.8: {p.parent.name}/{p.stem}")
        for k in keys:
            if r8[k] != r7[k]:
                print(f"   {k}: 2.1.7={r7[k][:300]!r}")
                print(f"   {k}: 2.1.8={r8[k][:300]!r}")
print(f"cases={same + diff} identical_2.1.7_vs_2.1.8={same} changed={diff}")
print(f"2.1.8 stdout identical to 1.0.169 fixture: {fixture_same}/32; cases where the kit filter forwards anything: {fwd}")
for p in sorted(b.glob("*/*.json")):
    r = json.loads(p.read_text())
    if r["filtered_stdout"]:
        print("FORWARDED by filter:", p.parent.name, p.stem, len(r["filtered_stdout"]), "B")
