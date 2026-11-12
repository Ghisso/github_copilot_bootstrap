"""Replay the recorded 1.0.169 hook fixture inputs against a chosen CLI.

Usage (inside cmrun.sh so the environment points at scratch):
  python3 -I replay_hooks.py <run-dir> <cli-path> <version-label> <out-dir>

For each client and case, in capture.py's CASES order, the recorded fixture
`input` is sent (with <TMP> mapped to <run-dir>) to
`node <cli-path> hook <target> <event>` -- the exact v1 form the repository's
dispatcher calls. The raw output is saved in the fixture format, and the raw
stdout is also passed through the repository filter in --hook-output mode.
"""

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path("/home/ghisso/work/github_copilot_bootstrap")
FIXDIR = REPO / "tests/fixtures/context_mode_hook/1.0.169"
FILTER = REPO / "shared/hooks/scripts/context-mode-mcp-filter.mjs"
CAPTURE = REPO / "tests/fixtures/context_mode_hook/capture.py"
# Same mapping as context-mode-dispatch.sh's case statement.
TARGETS = {
    "claude-code": "claude-code",
    "openai-codex": "codex",
    "github-copilot": "vscode-copilot",
}


def load_cases() -> dict:
    spec = importlib.util.spec_from_file_location("capture_fixture", CAPTURE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.CASES


def main() -> int:
    run_dir, cli, version, out_dir = sys.argv[1:5]
    only_clients = sys.argv[5].split(",") if len(sys.argv) > 5 else None
    out = Path(out_dir)
    cases = load_cases()
    rows = []
    for client, client_cases in cases.items():
        if only_clients and client not in only_clients:
            continue
        for event, case, _payload in client_cases:
            fixture = json.loads((FIXDIR / client / f"{event}-{case}.json").read_text())
            body = json.loads(json.dumps(fixture["input"]).replace("<TMP>", run_dir))
            result = subprocess.run(
                ["node", cli, "hook", TARGETS[client], event],
                input=json.dumps(body),
                capture_output=True,
                text=True,
                timeout=90,
                env=os.environ,
            )
            filtered = subprocess.run(
                ["node", str(FILTER), "--hook-output"],
                input=result.stdout,
                capture_output=True,
                text=True,
                timeout=30,
                env=os.environ,
            )

            def scrub(text: str) -> str:
                return text.replace(run_dir, "<TMP>")

            record = {
                "client_id": client,
                "event": event,
                "case": case,
                "context_mode_version": version,
                "input": json.loads(scrub(json.dumps(body))),
                "exit_code": result.returncode,
                "stdout": scrub(result.stdout),
                "stderr_tail": scrub(result.stderr).strip().splitlines()[-5:],
                "filtered_stdout": scrub(filtered.stdout),
                "filter_exit": filtered.returncode,
            }
            path = out / client / f"{event}-{case}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
            rows.append((client, event, case, result.returncode, len(result.stdout), len(filtered.stdout)))
    for row in rows:
        print(*row, sep="\t")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
