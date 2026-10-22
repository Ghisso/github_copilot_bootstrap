"""Re-capture the raw Context Mode hook output recorded as test fixtures.

The dispatcher filters hook output (GR-007), so these fixtures record what the
real pinned `context-mode hook` binary emits *before* filtering, for each wired
client id. `tests/test_context_mode_dispatch.py` replays them through the real
dispatcher. Each run is isolated: a temporary Git repository, a temporary
HOME, CLAUDE_CONFIG_DIR, CODEX_HOME and TMPDIR (so no user-level file reaches
the session store or a fixture, and no state leaks between runs), one throwaway
session id per client, and temporary paths replaced by `<TMP>`.

Re-run it from the repository root after changing PINNED_CONTEXT_MODE_VERSION in
`shared/hooks/scripts/context-mode-dispatch.sh`, then review the fixture diff:

    uv run python tests/fixtures/context_mode_hook/capture.py

The fixtures are written to `<out-root>/<PINNED_CONTEXT_MODE_VERSION>/`. The
default out-root is this directory; pass `--out-root DIR` to write elsewhere
(for example a scratch directory, to compare without touching the fixtures).
The direct pinned `context-mode` binary and `node` must be on PATH. The run
first asserts, through the dispatcher's `--self-check`, that the launcher is
the direct pinned binary, so it can never fall back to an `npx` download.
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HOOK_SCRIPTS = REPO / "shared/hooks/scripts"
DISPATCHER = HOOK_SCRIPTS / "context-mode-dispatch.sh"
SESSION = "gate-repair-capture"
TOOL_NAME = re.compile(r"(?:mcp__[A-Za-z0-9_-]+__|mcp_[A-Za-z0-9-]+_)?ctx_[a-z_]+")

TOOL_EVENT_NAMES = {"pretooluse": "PreToolUse", "posttooluse": "PostToolUse"}

Case = tuple[str, str, dict[str, object]]
CASES: dict[str, list[Case]] = {
    "claude-code": [
        (
            "sessionstart",
            "startup",
            {"hook_event_name": "SessionStart", "source": "startup"},
        ),
        (
            "pretooluse",
            "bash-ls",
            {"tool_name": "Bash", "tool_input": {"command": "ls"}},
        ),
        (
            "pretooluse",
            "bash-curl",
            {
                "tool_name": "Bash",
                "tool_input": {"command": "curl -s https://example.com"},
            },
        ),
        (
            "pretooluse",
            "read",
            {"tool_name": "Read", "tool_input": {"file_path": "README.md"}},
        ),
        ("pretooluse", "grep", {"tool_name": "Grep", "tool_input": {"pattern": "x"}}),
        (
            "pretooluse",
            "webfetch",
            {
                "tool_name": "WebFetch",
                "tool_input": {"url": "https://example.com", "prompt": "x"},
            },
        ),
        (
            "pretooluse",
            "agent",
            {
                "tool_name": "Agent",
                "tool_input": {
                    "description": "d",
                    "prompt": "Summarize README.md",
                    "subagent_type": "Explore",
                },
            },
        ),
        (
            "pretooluse",
            "ctx-execute",
            {
                "tool_name": "mcp__context-mode__ctx_execute",
                "tool_input": {"language": "shell", "code": "ls"},
            },
        ),
        (
            "posttooluse",
            "bash",
            {
                "tool_name": "Bash",
                "tool_input": {"command": "ls"},
                "tool_response": {"stdout": "README.md\n", "stderr": ""},
            },
        ),
        (
            "precompact",
            "manual",
            {"hook_event_name": "PreCompact", "trigger": "manual"},
        ),
        (
            "sessionstart",
            "compact",
            {"hook_event_name": "SessionStart", "source": "compact"},
        ),
    ],
    "openai-codex": [
        (
            "sessionstart",
            "startup",
            {"hook_event_name": "SessionStart", "source": "startup"},
        ),
        (
            "pretooluse",
            "bash-ls",
            {"tool_name": "Bash", "tool_input": {"command": "ls"}},
        ),
        (
            "pretooluse",
            "bash-curl",
            {
                "tool_name": "Bash",
                "tool_input": {"command": "curl -s https://example.com"},
            },
        ),
        (
            "pretooluse",
            "read",
            {"tool_name": "read", "tool_input": {"path": "README.md"}},
        ),
        (
            "pretooluse",
            "web-fetch",
            {"tool_name": "web_fetch", "tool_input": {"url": "https://example.com"}},
        ),
        (
            "pretooluse",
            "ctx-execute",
            {
                "tool_name": "mcp__context-mode__ctx_execute",
                "tool_input": {"language": "shell", "code": "ls"},
            },
        ),
        (
            "posttooluse",
            "bash",
            {
                "tool_name": "Bash",
                "tool_input": {"command": "ls"},
                "tool_response": {"stdout": "README.md\n"},
            },
        ),
        (
            "precompact",
            "manual",
            {"hook_event_name": "PreCompact", "trigger": "manual"},
        ),
        (
            "sessionstart",
            "compact",
            {"hook_event_name": "SessionStart", "source": "compact"},
        ),
    ],
    "github-copilot": [
        (
            "sessionstart",
            "startup",
            {"hook_event_name": "SessionStart", "source": "startup"},
        ),
        (
            "pretooluse",
            "terminal-ls",
            {"tool_name": "run_in_terminal", "tool_input": {"command": "ls"}},
        ),
        (
            "pretooluse",
            "terminal-curl",
            {
                "tool_name": "run_in_terminal",
                "tool_input": {"command": "curl -s https://example.com"},
            },
        ),
        (
            "pretooluse",
            "read",
            {"tool_name": "read_file", "tool_input": {"filePath": "README.md"}},
        ),
        (
            "pretooluse",
            "grep",
            {"tool_name": "grep_search", "tool_input": {"query": "x"}},
        ),
        (
            "pretooluse",
            "fetch",
            {"tool_name": "fetch", "tool_input": {"urls": ["https://example.com"]}},
        ),
        (
            "pretooluse",
            "subagent",
            {
                "tool_name": "runSubagent",
                "tool_input": {"prompt": "Summarize README.md"},
            },
        ),
        (
            "pretooluse",
            "agent",
            {"tool_name": "agent", "tool_input": {"prompt": "Summarize README.md"}},
        ),
        (
            "pretooluse",
            "ctx-execute",
            {
                "tool_name": "mcp_context-mode_ctx_execute",
                "tool_input": {"language": "shell", "code": "ls"},
            },
        ),
        (
            "posttooluse",
            "terminal",
            {
                "tool_name": "run_in_terminal",
                "tool_input": {"command": "ls"},
                "tool_response": "README.md\n",
            },
        ),
        (
            "precompact",
            "manual",
            {"hook_event_name": "PreCompact", "trigger": "manual"},
        ),
        (
            "sessionstart",
            "compact",
            {"hook_event_name": "SessionStart", "source": "compact"},
        ),
    ],
}


def read_dispatcher() -> tuple[str, dict[str, str]]:
    """Return the pinned version and the client-id to upstream-target mapping,
    read from the dispatcher itself so neither can drift from this tool."""
    text = DISPATCHER.read_text(encoding="utf-8")
    pin = re.search(r'^PINNED_CONTEXT_MODE_VERSION="([^"]+)"', text, re.M)
    if pin is None:
        raise SystemExit("PINNED_CONTEXT_MODE_VERSION not found in the dispatcher")
    targets = dict(
        re.findall(r'^\s*([\w-]+)\) CONTEXT_MODE_TARGET="([^"]+)" ;;', text, re.M)
    )
    return pin.group(1), targets


def scrub(text: str, temp: Path) -> str:
    return text.replace(str(temp), "<TMP>").replace(str(Path.home()), "<USER_HOME>")


def summarize(
    client: str, event: str, case: str, exit_code: int, stdout: str, stderr: str
) -> dict[str, object]:
    try:
        parsed: object = json.loads(stdout) if stdout.strip() else None
    except json.JSONDecodeError:
        parsed = None
    top = parsed if isinstance(parsed, dict) else {}
    specific = top.get("hookSpecificOutput")
    hso = specific if isinstance(specific, dict) else {}
    return {
        "client": client,
        "event": event,
        "case": case,
        "exit": exit_code,
        "bytes": len(stdout),
        "top": sorted(top)
        if isinstance(parsed, dict) or parsed is None
        else ["<non-object>"],
        "hso": sorted(hso),
        "decision": hso.get("permissionDecision")
        or top.get("permissionDecision")
        or top.get("decision"),
        "rewrite": "updatedInput" in hso or "tool_input" in hso,
        "tools": sorted(set(TOOL_NAME.findall(stdout))),
        "plugin_prefix": "mcp__plugin_context-mode_" in stdout,
        "stderr": bool(stderr.strip()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Re-capture raw Context Mode hook fixtures."
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=Path(__file__).resolve().parent,
        help="directory that receives <version>/<client>/<event>-<case>.json",
    )
    out_root: Path = parser.parse_args().out_root
    version, targets = read_dispatcher()
    missing = sorted(set(CASES) - set(targets))
    if missing:
        print(
            f"dispatcher has no target mapping for: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 1
    context_mode = shutil.which("context-mode")
    node = shutil.which("node")
    if context_mode is None or node is None:
        print("context-mode and node must be on PATH", file=sys.stderr)
        return 1
    out = out_root / version

    with tempfile.TemporaryDirectory(prefix="cm-capture-") as tmp:
        temp = Path(tmp)
        root = temp / "repo"
        scripts = root / ".claude/hooks/scripts"
        scripts.mkdir(parents=True)
        for script in HOOK_SCRIPTS.glob("context-mode-*"):
            shutil.copy(script, scripts / script.name)
        (root / "README.md").write_text("capture fixture\n")
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        home = temp / "home"
        (home / ".claude").mkdir(parents=True)
        (home / ".codex").mkdir(parents=True)
        # Upstream throttles its once-per-session tips with files in the OS temp
        # directory, keyed by session id. A shared TMPDIR would make a re-run
        # drop them and silently record a different output.
        (temp / "tmp").mkdir()
        env = {
            "HOME": str(home),
            "TMPDIR": str(temp / "tmp"),
            "CLAUDE_CONFIG_DIR": str(home / ".claude"),
            "CODEX_HOME": str(home / ".codex"),
            "CLAUDE_PROJECT_DIR": str(root),
            "PATH": ":".join(
                [
                    str(Path(context_mode).parent),
                    str(Path(node).parent),
                    "/usr/bin",
                    "/bin",
                ]
            ),
            "LANG": "C.UTF-8",
        }
        check = subprocess.run(
            ["bash", str(scripts / DISPATCHER.name), "--self-check"],
            env=env,
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if (
            "launcher=context-mode" not in check.stdout
            or "version-contract=pinned-direct-binary" not in check.stdout
        ):
            print(check.stdout + check.stderr, file=sys.stderr)
            print(
                "refusing to capture: not the direct pinned context-mode binary",
                file=sys.stderr,
            )
            return 1
        # The dispatcher gives upstream this cache and project root; mirror it.
        env["CONTEXT_MODE_DIR"] = str(root / ".claude/.cache/context-mode")
        env["CONTEXT_MODE_PROJECT_ROOT"] = str(root)

        rows: list[dict[str, object]] = []
        for client, cases in CASES.items():
            for event, case, payload in cases:
                body: dict[str, object] = {
                    "session_id": f"{SESSION}-{client}",
                    "cwd": str(root),
                    **payload,
                }
                if "hook_event_name" not in body:
                    body["hook_event_name"] = TOOL_EVENT_NAMES[event]
                result = subprocess.run(
                    [context_mode, "hook", targets[client], event],
                    input=json.dumps(body),
                    env=env,
                    cwd=root,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                stdout = scrub(result.stdout, temp)
                stderr = scrub(result.stderr, temp)
                fixture = {
                    "client_id": client,
                    "event": event,
                    "case": case,
                    "context_mode_version": version,
                    "input": json.loads(scrub(json.dumps(body), temp)),
                    "exit_code": result.returncode,
                    "stdout": stdout,
                    "stderr_tail": stderr.strip().splitlines()[-5:],
                }
                path = out / client / f"{event}-{case}.json"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    json.dumps(fixture, indent=2, ensure_ascii=False) + "\n"
                )
                rows.append(
                    summarize(client, event, case, result.returncode, stdout, stderr)
                )
    print(json.dumps(rows, indent=1))
    print(f"wrote {len(rows)} fixtures to {out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
