"""Run a list of hook payloads through `node <cli> hook <target> <event>` in order.

Usage (inside cmrun.sh): python3 -I run_sequence.py <run-dir> <cli> <target> <steps.json> <out.json>
steps.json: [{"event": "posttooluse", "payload": {...}}, ...]; "<TMP>" in payloads maps to <run-dir>,
"<BIG:N>" in a string expands to N numbered log lines.
Each raw stdout is also passed through the repository filter's --hook-output mode.
"""

import json
import os
import subprocess
import sys

FILTER = "/home/ghisso/work/github_copilot_bootstrap/shared/hooks/scripts/context-mode-mcp-filter.mjs"


def expand(value, run_dir):
    if isinstance(value, str):
        value = value.replace("<TMP>", run_dir)
        if value.startswith("<BIG:") and value.endswith(">"):
            count = int(value[5:-1])
            return "".join(f"line {i:05d} level=INFO worker=alpha status=ok latency_ms={i % 97}\n" for i in range(count))
        return value
    if isinstance(value, list):
        return [expand(v, run_dir) for v in value]
    if isinstance(value, dict):
        return {k: expand(v, run_dir) for k, v in value.items()}
    return value


def main() -> int:
    run_dir, cli, target, steps_path, out_path = sys.argv[1:6]
    steps = json.load(open(steps_path))
    results = []
    for step in steps:
        payload = expand(step["payload"], run_dir)
        proc = subprocess.run(
            ["node", cli, "hook", target, step["event"]],
            input=json.dumps(payload), capture_output=True, text=True, timeout=90, env=os.environ,
        )
        filtered = subprocess.run(
            ["node", FILTER, "--hook-output"], input=proc.stdout, capture_output=True, text=True, timeout=30, env=os.environ,
        )
        scrub = lambda text: text.replace(run_dir, "<TMP>")
        out = proc.stdout
        try:
            parsed = json.loads(out) if out.strip() else None
        except json.JSONDecodeError:
            parsed = "invalid-json"
        results.append({
            "label": step.get("label", step["event"]),
            "event": step["event"],
            "exit_code": proc.returncode,
            "stdout_bytes": len(out),
            "stdout": scrub(out)[:6000],
            "hso_keys": sorted(parsed["hookSpecificOutput"]) if isinstance(parsed, dict) and isinstance(parsed.get("hookSpecificOutput"), dict) else None,
            "stderr": scrub(proc.stderr).strip().splitlines()[-4:],
            "filtered_stdout": scrub(filtered.stdout),
        })
        print(f"{step.get('label', step['event'])}\texit={proc.returncode}\tout={len(out)}B\tkeys={results[-1]['hso_keys']}\tfiltered={len(filtered.stdout)}B")
    with open(out_path, "w") as handle:
        json.dump(results, handle, indent=2, ensure_ascii=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
