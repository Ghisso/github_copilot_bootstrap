"""Public-stdio contract tests for the bounded Context Mode MCP filter."""

from __future__ import annotations

import json
import os
import select
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FILTER = REPO_ROOT / "shared/hooks/scripts/context-mode-mcp-filter.mjs"


@pytest.fixture
def fake_upstream(tmp_path: Path) -> tuple[Path, Path]:
    """A fake upstream that also accepts JSON-RPC batch arrays.

    A real-world (or malicious) upstream is not obligated to reject a batch,
    so the fake mirrors that: it processes every item in an array the same
    way it processes a lone object. This is what lets the CRITICAL-1 tests
    below prove a batch/notification actually reached upstream, rather than
    merely crashing a fake that could only understand single objects.
    """
    script = tmp_path / "fake_upstream.py"
    trace = tmp_path / "calls.log"
    script.write_text(
        "import json, os, sys\n"
        "def handle(m):\n"
        " mid=m.get('id'); method=m.get('method')\n"
        " if method=='initialize': r={'serverInfo':{'name':'context-mode','version':os.environ.get('FAKE_VERSION','1.0.169')}}\n"
        " elif method=='tools/list': r={'tools':[{'name':n} for n in ['ctx_index','ctx_search','ctx_stats','ctx_doctor','ctx_execute','ctx_fetch_and_index','future_tool']]}\n"
        " elif method=='tools/call':\n"
        "  open(os.environ['FAKE_TRACE'],'a').write(m['params']['name']+'\\n'); r={'content':[{'type':'text','text':'ok'}]}\n"
        " else: r={'echo':method}\n"
        " print(json.dumps({'jsonrpc':'2.0','id':mid,'result':r}),flush=True)\n"
        "for line in sys.stdin:\n"
        " payload=json.loads(line)\n"
        " for item in (payload if isinstance(payload, list) else [payload]):\n"
        "  handle(item)\n"
    )
    return script, trace


def _start(
    project: Path, fake: Path, trace: Path, *, version: str = "1.0.169"
) -> subprocess.Popen[str]:
    return subprocess.Popen(
        ["node", str(FILTER), "--", sys.executable, str(fake)],
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env={
            **os.environ,
            "CONTEXT_MODE_PROJECT_ROOT": str(project),
            "FAKE_TRACE": str(trace),
            "FAKE_VERSION": version,
        },
    )


def _request(
    process: subprocess.Popen[str], message: dict[str, object]
) -> dict[str, object]:
    assert process.stdin is not None and process.stdout is not None
    process.stdin.write(json.dumps(message) + "\n")
    process.stdin.flush()
    return json.loads(process.stdout.readline())


def _initialize(process: subprocess.Popen[str]) -> dict[str, object]:
    return _request(
        process,
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
    )


def _call(
    process: subprocess.Popen[str], request_id: int, name: str, arguments: object
) -> dict[str, object]:
    return _request(
        process,
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        },
    )


def test_initialize_and_tools_list_expose_exact_allowlist(
    tmp_path: Path, fake_upstream: tuple[Path, Path]
) -> None:
    fake, trace = fake_upstream
    process = _start(tmp_path, fake, trace)
    assert _initialize(process)["result"]["serverInfo"]["version"] == "1.0.169"  # type: ignore[index]
    response = _request(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    names = [tool["name"] for tool in response["result"]["tools"]]  # type: ignore[index]
    assert names == ["ctx_index", "ctx_search", "ctx_stats", "ctx_doctor"]
    process.terminate()


def test_version_mismatch_exposes_no_tools(
    tmp_path: Path, fake_upstream: tuple[Path, Path]
) -> None:
    fake, trace = fake_upstream
    process = _start(tmp_path, fake, trace, version="1.0.170")
    response = _initialize(process)
    assert response["error"]["code"] == -32002  # type: ignore[index]
    assert "1.0.169" in response["error"]["message"]  # type: ignore[index]


@pytest.mark.parametrize(
    "name", ["ctx_execute", "ctx_execute_file", "ctx_fetch_and_index", "future_tool"]
)
def test_blocked_and_unknown_calls_never_reach_upstream(
    tmp_path: Path, fake_upstream: tuple[Path, Path], name: str
) -> None:
    fake, trace = fake_upstream
    process = _start(tmp_path, fake, trace)
    _initialize(process)
    response = _call(process, 2, name, {"secret": "must-not-be-logged"})
    assert response["error"]["code"] == -32601  # type: ignore[index]
    assert not trace.exists()
    process.terminate()
    # `communicate()` drains and returns the *entire* accumulated stderr, so
    # this can actually fail if the filter ever logs a raw argument (unlike
    # `stderr.read(0)`, which always reads zero bytes and can never fail).
    _, stderr = process.communicate(timeout=5)
    assert "must-not-be-logged" not in stderr


def test_fragmented_and_multiple_messages_are_forwarded(
    tmp_path: Path, fake_upstream: tuple[Path, Path]
) -> None:
    fake, trace = fake_upstream
    process = _start(tmp_path, fake, trace)
    assert process.stdin is not None and process.stdout is not None
    initialize = json.dumps(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    )
    process.stdin.write(initialize[:10])
    process.stdin.flush()
    process.stdin.write(initialize[10:] + "\n")
    process.stdin.flush()
    assert json.loads(process.stdout.readline())["id"] == 1
    messages = "".join(
        json.dumps({"jsonrpc": "2.0", "id": request_id, "method": "ping"}) + "\n"
        for request_id in (2, 3)
    )
    process.stdin.write(messages)
    process.stdin.flush()
    assert [json.loads(process.stdout.readline())["id"] for _ in range(2)] == [2, 3]
    process.terminate()


def test_allowed_calls_and_guarded_index_content_and_file_pass_through(
    tmp_path: Path, fake_upstream: tuple[Path, Path]
) -> None:
    fake, trace = fake_upstream
    project = tmp_path / "repo"
    project.mkdir()
    ordinary = project / "ordinary.md"
    ordinary.write_text("safe")
    process = _start(project, fake, trace)
    _initialize(process)
    assert "result" in _call(
        process, 2, "ctx_index", {"content": "safe", "source": "fixture"}
    )
    assert "result" in _call(process, 3, "ctx_index", {"path": "ordinary.md"})
    for request_id, name in enumerate(("ctx_search", "ctx_stats", "ctx_doctor"), 4):
        assert "result" in _call(process, request_id, name, {})
    assert trace.read_text().splitlines() == [
        "ctx_index",
        "ctx_index",
        "ctx_search",
        "ctx_stats",
        "ctx_doctor",
    ]
    process.terminate()


def test_notification_shaped_tools_call_never_reaches_upstream(
    tmp_path: Path, fake_upstream: tuple[Path, Path]
) -> None:
    """A tools/call with no `id` (a JSON-RPC notification) has nobody to
    answer, so it must be dropped rather than forwarded -- even for an
    arbitrary-code-execution tool and even with no prior initialize
    (CRITICAL 1a). Before the fix, the gate lived inside a branch guarded by
    `Object.hasOwn(message, "id")`, so a notification fell straight through
    to `upstream.stdin.write(raw)`.
    """
    fake, trace = fake_upstream
    process = _start(tmp_path, fake, trace)
    assert process.stdin is not None
    notification = json.dumps(
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "ctx_execute", "arguments": {"command": "id"}},
        }
    )
    process.stdin.write(notification + "\n")
    process.stdin.flush()
    # A distinguishable follow-up proves no spurious response for the
    # notification arrived first on stdout.
    response = _request(process, {"jsonrpc": "2.0", "id": 2, "method": "ping"})
    assert not trace.exists()
    assert response["id"] == 2
    process.terminate()


def test_batch_array_tools_call_never_reaches_upstream(
    tmp_path: Path, fake_upstream: tuple[Path, Path]
) -> None:
    """A JSON-RPC batch array must be rejected/dropped whole rather than
    forwarded, even when it carries an arbitrary-code-execution tool call and
    even with no prior initialize (CRITICAL 1b). Before the fix, the gate
    checked `message.method === "tools/call"`, and `[].method` is
    `undefined`, so an array fell straight through to
    `upstream.stdin.write(raw)`.
    """
    fake, trace = fake_upstream
    process = _start(tmp_path, fake, trace)
    assert process.stdin is not None
    batch = json.dumps(
        [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": "ctx_batch_execute",
                    "arguments": {"commands": []},
                },
            }
        ]
    )
    process.stdin.write(batch + "\n")
    process.stdin.flush()
    response = _request(process, {"jsonrpc": "2.0", "id": 2, "method": "ping"})
    assert not trace.exists()
    assert response["id"] == 2
    process.terminate()


def test_duplicate_id_tools_list_never_leaks_blocked_tool_names(
    tmp_path: Path, fake_upstream: tuple[Path, Path]
) -> None:
    """Two tools/list requests that reuse one id must each be filtered on
    their own matching response (MAJOR 3). Before the fix, `listIds` was a
    `Set`, so the second of two same-id responses found the id already
    deleted and was written through raw, leaking the unfiltered tool list.
    """
    fake, trace = fake_upstream
    process = _start(tmp_path, fake, trace)
    assert process.stdin is not None and process.stdout is not None
    _initialize(process)
    duplicate = json.dumps({"jsonrpc": "2.0", "id": 9, "method": "tools/list"})
    process.stdin.write(duplicate + "\n")
    process.stdin.write(duplicate + "\n")
    process.stdin.flush()
    responses = [json.loads(process.stdout.readline()) for _ in range(2)]
    for response in responses:
        names = [tool["name"] for tool in response["result"]["tools"]]
        assert names == ["ctx_index", "ctx_search", "ctx_stats", "ctx_doctor"]
    process.terminate()


def test_racing_call_and_list_with_shared_id_never_leaks_blocked_tools(
    tmp_path: Path, fake_upstream: tuple[Path, Path]
) -> None:
    """If a client reuses one JSON-RPC id across a pending `tools/list` and
    another concurrently outstanding request (e.g. a `ctx_doctor` call), and
    the non-list response for that id arrives first, the pending counter must
    stay untouched so the later genuine `tools/list` response is still
    filtered (MAJOR finding: cross-method id collision). Before the fix, any
    response for that id -- list or not -- consumed the counter, so the
    genuine list response then fell through to raw, unfiltered passthrough.
    """
    fake, trace = fake_upstream
    process = _start(tmp_path, fake, trace)
    assert process.stdin is not None and process.stdout is not None
    _initialize(process)
    shared_id = 9
    call = json.dumps(
        {
            "jsonrpc": "2.0",
            "id": shared_id,
            "method": "tools/call",
            "params": {"name": "ctx_doctor", "arguments": {}},
        }
    )
    listing = json.dumps({"jsonrpc": "2.0", "id": shared_id, "method": "tools/list"})
    process.stdin.write(call + "\n")
    process.stdin.write(listing + "\n")
    process.stdin.flush()
    call_response = json.loads(process.stdout.readline())
    list_response = json.loads(process.stdout.readline())
    assert "tools" not in call_response.get("result", {})
    names = [tool["name"] for tool in list_response["result"]["tools"]]  # type: ignore[index]
    assert names == ["ctx_index", "ctx_search", "ctx_stats", "ctx_doctor"]
    process.terminate()


@pytest.mark.parametrize(
    ("path_value", "message"),
    [
        ("../outside.md", "traversal"),
        ("directory", "temporarily disabled"),
        ("missing.md", "must exist"),
    ],
)
def test_index_rejects_traversal_directory_and_missing_path(
    tmp_path: Path,
    fake_upstream: tuple[Path, Path],
    path_value: str,
    message: str,
) -> None:
    fake, trace = fake_upstream
    project = tmp_path / "repo"
    project.mkdir()
    (project / "directory").mkdir()
    process = _start(project, fake, trace)
    _initialize(process)
    response = _call(process, 2, "ctx_index", {"path": path_value})
    assert message in response["error"]["message"]  # type: ignore[index]
    assert not trace.exists()
    process.terminate()


def test_index_rejects_oversized_source_label(
    tmp_path: Path, fake_upstream: tuple[Path, Path]
) -> None:
    """`source` (MINOR 8) is passed through unchecked in INDEX_ARGS unlike
    content/path; it must be bounded to a short string."""
    fake, trace = fake_upstream
    process = _start(tmp_path, fake, trace)
    _initialize(process)
    response = _call(process, 2, "ctx_index", {"content": "safe", "source": "x" * 201})
    assert "source" in response["error"]["message"]  # type: ignore[index]
    assert not trace.exists()
    process.terminate()


def test_index_rejects_absolute_outside_and_symlink_paths(
    tmp_path: Path, fake_upstream: tuple[Path, Path]
) -> None:
    fake, trace = fake_upstream
    project = tmp_path / "repo"
    project.mkdir()
    outside = tmp_path / "outside.md"
    outside.write_text("outside")
    (project / "link.md").symlink_to(outside)
    process = _start(project, fake, trace)
    _initialize(process)
    outside_response = _call(process, 2, "ctx_index", {"path": str(outside)})
    link_response = _call(process, 3, "ctx_index", {"path": "link.md"})
    assert "inside the repository" in outside_response["error"]["message"]  # type: ignore[index]
    assert "symbolic link" in link_response["error"]["message"]  # type: ignore[index]
    assert not trace.exists()
    process.terminate()


@pytest.mark.parametrize("arguments", [{}, {"content": "x", "path": "x"}])
def test_index_requires_exactly_one_input(
    tmp_path: Path, fake_upstream: tuple[Path, Path], arguments: object
) -> None:
    fake, trace = fake_upstream
    process = _start(tmp_path, fake, trace)
    _initialize(process)
    response = _call(process, 2, "ctx_index", arguments)
    assert "exactly one" in response["error"]["message"]  # type: ignore[index]
    assert not trace.exists()
    process.terminate()


def test_pending_tools_list_capacity_fails_closed_without_untracking(
    tmp_path: Path, fake_upstream: tuple[Path, Path]
) -> None:
    """At capacity the filter must refuse a new id, never evict a tracked one.

    Evicting the oldest pending id would untrack a genuinely outstanding
    ``tools/list``; upstream's later response for it would then match nothing
    and be written straight through unfiltered, which is exactly the leak the
    allowlist exists to prevent.
    """
    _, trace = fake_upstream
    # An upstream that answers `initialize` but never answers `tools/list`, so
    # every tracked id stays pending and the bound is actually reached.
    silent = tmp_path / "silent_upstream.py"
    silent.write_text(
        "import json, sys\n"
        "for line in sys.stdin:\n"
        " m=json.loads(line)\n"
        " if m.get('method')=='initialize':\n"
        "  print(json.dumps({'jsonrpc':'2.0','id':m.get('id'),'result':"
        "{'serverInfo':{'name':'context-mode','version':'1.0.169'}}}),flush=True)\n"
    )
    process = _start(tmp_path, silent, trace)
    _initialize(process)
    assert process.stdin is not None
    for request_id in range(2, 2 + 256):
        process.stdin.write(
            json.dumps({"jsonrpc": "2.0", "id": request_id, "method": "tools/list"})
            + "\n"
        )
    process.stdin.flush()
    # The next distinct id is over capacity. Fail-closed answers it with an
    # error; an evicting version instead accepts it silently and untracks id 2,
    # so nothing is ever written back -- hence the bounded wait rather than a
    # blocking readline that would hang the suite on regression.
    assert process.stdout is not None
    process.stdin.write(
        json.dumps({"jsonrpc": "2.0", "id": 9999, "method": "tools/list"}) + "\n"
    )
    process.stdin.flush()
    assert select.select([process.stdout], [], [], 15)[0], (
        "over-capacity tools/list was silently accepted instead of refused"
    )
    response = json.loads(process.stdout.readline())
    assert response["id"] == 9999
    assert "too many pending" in response["error"]["message"]  # type: ignore[index]
    assert not trace.exists()
    process.terminate()
