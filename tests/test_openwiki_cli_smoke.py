"""Real-binary MCP handshake smoke test for the pinned OpenWiki CLI (Phase G,
Step G4). This never `skipif`s: the devcontainer image installs the pinned
CLI, so a missing binary here is a real gap, not an expected skip, and must
fail loudly enough to name what is missing.
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
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from validate_targets import OPENWIKI_PINNED_VERSION  # noqa: E402

EXPECTED_TOOLS = frozenset(
    {
        "openwiki_begin",
        "openwiki_submit_plan",
        "openwiki_next_page",
        "openwiki_inspect_page_claims",
        "openwiki_submit_page",
        "openwiki_finish",
    }
)
HANDSHAKE_TIMEOUT_SECONDS = 20


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
    process = subprocess.Popen(
        [binary, "mcp", "--host", "claude"],
        cwd=tmp_path,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        deadline = time.monotonic() + HANDSHAKE_TIMEOUT_SECONDS
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
        server_info = init_response["result"]["serverInfo"]
        assert server_info["version"] == OPENWIKI_PINNED_VERSION

        _send(process, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        _send(
            process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        )
        tools_response = _read_json_line(process, deadline)
        assert "error" not in tools_response, tools_response
        tool_names = {tool["name"] for tool in tools_response["result"]["tools"]}
        assert tool_names == EXPECTED_TOOLS
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    after = sorted(p.relative_to(tmp_path) for p in tmp_path.rglob("*"))
    assert after == before, "the handshake must not write into the temporary repo"
