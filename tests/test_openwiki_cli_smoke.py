"""Real-binary smoke tests for the pinned OpenWiki CLI (Phase G, Step G4): the
MCP handshake, and an `openwiki_begin` round trip through the real guard.
These never `skipif`: the devcontainer image installs the pinned CLI, so a
missing binary here is a real gap, not an expected skip, and must fail loudly
enough to name what is missing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from test_openwiki_guard import (  # noqa: E402
    MANAGED_END,
    MANAGED_START,
    _guard_repo,
    _pre_payload,
    _run_guard,
)
from validate_targets import OPENWIKI_PINNED_VERSION  # noqa: E402

EXPECTED_TOOLS = frozenset(
    {
        "openwiki_begin",
        "openwiki_submit_plan",
        "openwiki_next_page",
        "openwiki_inspect_page_claims",
        "openwiki_submit_page",
        "openwiki_finish",
        "openwiki_list_workspaces",
        "openwiki_list_wikis",
        "openwiki_search",
        "openwiki_read",
    }
)
HANDSHAKE_TIMEOUT_SECONDS = 20
ADAPTERS = ("AGENTS.md", "CLAUDE.md")
WORKFLOW = ".github/workflows/openwiki-update.yml"
# Paths `openwiki_begin` may write; the guard's own snapshot lives under
# `.claude/.cache/openwiki-guard/`.
BEGIN_MAY_WRITE = ("openwiki/", ".claude/.cache/openwiki-guard/")


def _openwiki_binary() -> str:
    binary = shutil.which("openwiki")
    if binary is None:
        pytest.fail(
            "openwiki CLI not found on PATH: the devcontainer image installs "
            "openwiki@" + OPENWIKI_PINNED_VERSION + " and this test must prove "
            "the real MCP handshake ran, not report a pass it never attempted."
        )
    return binary


def _read_json_line(process: subprocess.Popen[str], deadline: float) -> dict[str, Any]:
    assert process.stdout is not None
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            process.kill()
            raise TimeoutError("openwiki mcp did not respond in time")
        line = process.stdout.readline()
        if not line:
            status = process.poll()
            stderr = process.stderr.read() if process.stderr else ""
            raise RuntimeError(
                f"openwiki mcp closed stdout unexpectedly (exit={status}): {stderr}"
            )
        stripped = line.strip()
        if not stripped:
            continue
        return json.loads(stripped)


def _send(process: subprocess.Popen[str], message: dict[str, object]) -> None:
    assert process.stdin is not None
    process.stdin.write(json.dumps(message) + "\n")
    process.stdin.flush()


def _start_server(binary: str, cwd: Path, env: dict[str, str]) -> subprocess.Popen[str]:
    return subprocess.Popen(
        [binary, "mcp", "--host", "claude"],
        cwd=cwd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )


def _stop_server(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _initialize(process: subprocess.Popen[str], deadline: float) -> dict[str, Any]:
    """Run the MCP initialize exchange and return the server's `serverInfo`."""
    _send(
        process,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "bootstrap-smoke-test", "version": "0.0.1"},
            },
        },
    )
    init_response = _read_json_line(process, deadline)
    assert "error" not in init_response, init_response
    _send(process, {"jsonrpc": "2.0", "method": "notifications/initialized"})
    return init_response["result"]["serverInfo"]


def _file_bytes(root: Path) -> dict[str, bytes]:
    """Bytes of every file under `root`, keyed by POSIX relative path. `.git/`
    is left out; `os.walk` does not follow the `shared/` harness symlink."""
    files: dict[str, bytes] = {}
    for current, dirs, names in os.walk(root):
        if Path(current) == root:
            dirs[:] = [name for name in dirs if name != ".git"]
        for name in names:
            path = Path(current) / name
            files[path.relative_to(root).as_posix()] = path.read_bytes()
    return files


def test_real_openwiki_mcp_handshake_reports_the_pinned_version_and_tools(
    tmp_path: Path,
) -> None:
    binary = _openwiki_binary()
    subprocess.run(
        ["git", "-c", "init.defaultBranch=main", "init", "-q"],
        cwd=tmp_path,
        check=True,
    )
    before = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*"))

    env = {**os.environ, "DO_NOT_TRACK": "1"}
    process = _start_server(binary, tmp_path, env)
    try:
        deadline = time.monotonic() + HANDSHAKE_TIMEOUT_SECONDS
        server_info = _initialize(process, deadline)
        assert server_info["version"] == OPENWIKI_PINNED_VERSION

        _send(
            process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        )
        tools_response = _read_json_line(process, deadline)
        assert "error" not in tools_response, tools_response
        tools = {tool["name"]: tool for tool in tools_response["result"]["tools"]}
        assert set(tools) == EXPECTED_TOOLS
        # The two fields `openwiki-guard.py` reads from `openwiki_begin`'s input.
        begin_schema = tools["openwiki_begin"]["inputSchema"]
        assert {"root", "mode"} <= set(begin_schema["required"])
        assert begin_schema["properties"]["mode"]["enum"] == ["init", "update"]
    finally:
        _stop_server(process)

    after = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*"))
    assert after == before, "the handshake must not write into the temporary repo"


def test_real_openwiki_begin_update_is_restored_by_the_guard(tmp_path: Path) -> None:
    """guard `pre` -> real `openwiki_begin` (`update`) -> guard `post`, offline
    and with an isolated HOME. Begin may write only `openwiki/`, the two root
    adapters, and the guard's own snapshot; `post` must give every other
    recorded file back byte for byte."""
    binary = _openwiki_binary()
    repo = tmp_path / "repo"
    repo.mkdir()
    _guard_repo(repo)
    subprocess.run(
        ["git", "-c", "init.defaultBranch=main", "init", "-q"], cwd=repo, check=True
    )
    home = tmp_path / "home"
    home.mkdir()
    env = {
        "PATH": os.environ["PATH"],
        "HOME": str(home),
        "OPENWIKI_CONFIG_DIR": str(home / ".openwiki"),
        "DO_NOT_TRACK": "1",
        "OPENWIKI_TELEMETRY_DISABLED": "1",
    }
    before = _file_bytes(repo)

    payload = _pre_payload(root=repo)
    pre = _run_guard(repo, "pre", payload)
    assert pre.returncode == 0 and pre.stdout == "", (pre.stdout, pre.stderr)

    process = _start_server(binary, repo, env)
    try:
        deadline = time.monotonic() + HANDSHAKE_TIMEOUT_SECONDS
        _initialize(process, deadline)
        _send(
            process,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": "openwiki_begin",
                    "arguments": payload["tool_input"],
                },
            },
        )
        begin = _read_json_line(process, deadline)
    finally:
        _stop_server(process)
    during = _file_bytes(repo)

    assert "error" not in begin and not begin["result"].get("isError"), begin
    assert "openwiki/.run.json" in during
    for name in ADAPTERS:
        text = during[name].decode("utf-8")
        assert text.count(MANAGED_START) == 1, name
        assert text.count(MANAGED_END) == 1, name
    assert WORKFLOW not in during
    stray = {
        path
        for path in before.keys() | during.keys()
        if before.get(path) != during.get(path)
        and path not in ADAPTERS
        and not path.startswith(BEGIN_MAY_WRITE)
    }
    assert not stray, f"begin wrote outside its allowed paths: {sorted(stray)}"

    post = _run_guard(repo, "post", {"tool_name": "mcp__openwiki__openwiki_begin"})
    assert post.returncode == 0, (post.stdout, post.stderr)
    after = _file_bytes(repo)

    def outside(files: dict[str, bytes]) -> dict[str, bytes]:
        return {
            path: data
            for path, data in files.items()
            if not path.startswith(("openwiki/", ".claude/.cache/"))
        }

    assert outside(after) == outside(before)
