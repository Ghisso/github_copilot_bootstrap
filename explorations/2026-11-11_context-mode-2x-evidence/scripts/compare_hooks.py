"""Compare replayed hook outputs with the recorded 1.0.169 fixtures.

Usage: python3 -I compare_hooks.py <replay-dir> [--detail]
Prints, per case: exit codes, JSON shape, decision, rewrite, advice tags,
ctx_ tool names, and what the repository filter forwards.
"""

import json
import re
import sys
from pathlib import Path

FIXDIR = Path("/home/ghisso/work/github_copilot_bootstrap/tests/fixtures/context_mode_hook/1.0.169")
TOOL = re.compile(r"(?:mcp__[A-Za-z0-9_-]+__|mcp_[A-Za-z0-9-]+_|context-mode-)?ctx_[a-z_]+")
TAG = re.compile(r"<([a-z_]+)(?:\s[^>]*)?>")


def shape(stdout: str) -> dict:
    try:
        parsed = json.loads(stdout) if stdout.strip() else None
    except json.JSONDecodeError:
        return {"json": "invalid", "raw": stdout[:120]}
    if parsed is None:
        return {"json": "empty"}
    if not isinstance(parsed, dict):
        return {"json": type(parsed).__name__}
    hso = parsed.get("hookSpecificOutput") if isinstance(parsed.get("hookSpecificOutput"), dict) else {}
    ctx = hso.get("additionalContext") or parsed.get("additionalContext") or ""
    reason = hso.get("permissionDecisionReason") or parsed.get("reason") or parsed.get("permissionDecisionReason") or ""
    return {
        "top": sorted(parsed),
        "hso": sorted(hso),
        "decision": hso.get("permissionDecision") or parsed.get("permissionDecision") or parsed.get("decision"),
        "rewrite": [k for k in ("updatedInput", "updatedMCPToolOutput", "updatedToolOutput", "tool_input") if k in hso or k in parsed],
        "ctx_tags": sorted(set(TAG.findall(ctx))) if isinstance(ctx, str) else "non-str",
        "tools": sorted(set(TOOL.findall(stdout))),
        "reason_head": reason[:90] if isinstance(reason, str) else reason,
    }


def main() -> int:
    replay = Path(sys.argv[1])
    detail = "--detail" in sys.argv
    same = 0
    total = 0
    for path in sorted(replay.glob("*/*.json")):
        rec = json.loads(path.read_text())
        fixture_path = FIXDIR / rec["client_id"] / path.name
        fixture = json.loads(fixture_path.read_text()) if fixture_path.exists() else None
        total += 1
        old = fixture["stdout"] if fixture else None
        new = rec["stdout"]
        identical = old == new
        same += identical
        print(f"== {rec['client_id']}/{path.stem}: exit {fixture['exit_code'] if fixture else '-'} -> {rec['exit_code']}  identical={identical}")
        if not identical or detail:
            print(f"   1.0.169: {json.dumps(shape(old)) if old is not None else 'no fixture'}")
            print(f"   replay : {json.dumps(shape(new))}")
        filtered = rec.get("filtered_stdout", "")
        print(f"   filter forwards: {len(filtered)} B {json.dumps(shape(filtered)) if filtered else ''}")
        if rec.get("stderr_tail"):
            print(f"   stderr: {rec['stderr_tail']}")
    print(f"\n{same}/{total} stdout identical to the recorded 1.0.169 fixtures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
