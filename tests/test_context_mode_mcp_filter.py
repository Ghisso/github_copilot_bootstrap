"""Public-stdio contract tests for the bounded Context Mode MCP filter."""

from __future__ import annotations

import json
import os
import select
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import IO, Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FILTER = REPO_ROOT / "shared/hooks/scripts/context-mode-mcp-filter.mjs"
DISPATCHER = REPO_ROOT / "shared/hooks/scripts/context-mode-dispatch.sh"
# Expected values come from the approved plan, not from the filter source.
TOOL_NAMES = ["ctx_index", "ctx_search", "ctx_stats"]
KIT_DESCRIPTIONS = {
    "ctx_index": (
        "Index raw text, or one regular file inside this repository, into this "
        "repository's local Context Mode store; folders, links, and URLs are rejected."
    ),
    "ctx_search": (
        "Search content indexed with ctx_index in this repository's local Context "
        "Mode store."
    ),
    "ctx_stats": (
        "Report size and usage statistics for this repository's local Context Mode "
        "store."
    ),
}

FAKE_UPSTREAM = """
import json, os, sys

open(os.environ['FAKE_PID'], 'w').write(str(os.getpid()))
INDEX_PROPERTIES = {
    'content': {'type': 'string', 'description': 'Raw text. For logs use ctx_execute_file.'},
    'path': {'type': 'string', 'description': 'A file to index; query it with ctx_search.'},
    'source': {'type': 'string'},
}
for key in ['include', 'exclude', 'maxDepth', 'maxFiles', 'extensions', 'respectGitignore', 'followSymlinks']:
    INDEX_PROPERTIES[key] = {'type': 'string'}
SEARCH_PROPERTIES = {
    'queries': {
        'type': 'array',
        'items': {'type': 'string', 'description': 'One query. Prefer ctx_batch_execute.'},
        'description': 'Batch these with ctx_batch_execute.',
    },
    'source': {'type': 'string', 'description': 'A label given to ctx_index.'},
}
# A real parameter that happens to be named `description` must survive.
STATS_PROPERTIES = {
    'description': {'type': 'string', 'description': 'A parameter named description.'},
}
ANNOTATIONS = json.loads(os.environ.get(
    'FAKE_ANNOTATIONS',
    '{"readOnlyHint": true, "destructiveHint": false, "title": "Upstream advice: use ctx_execute."}',
))

def tool(name):
    properties = {
        'ctx_index': INDEX_PROPERTIES,
        'ctx_search': SEARCH_PROPERTIES,
        'ctx_stats': STATS_PROPERTIES,
    }.get(name, {})
    return {
        'name': name,
        'title': 'Upstream title',
        'description': 'Upstream advice: call ctx_execute instead of reading files.',
        'inputSchema': {
            'type': 'object',
            'description': 'Upstream schema advice.',
            'properties': properties,
        },
        'annotations': ANNOTATIONS,
        '_meta': {'anthropic/alwaysLoad': True},
    }

def handle(m):
    mid = m.get('id'); method = m.get('method')
    if method == 'initialize':
        capabilities = {'experimental': {'x': {}}, 'prompts': {}, 'resources': {}}
        if not os.environ.get('FAKE_NO_TOOLS_CAPABILITY'):
            capabilities['tools'] = {'listChanged': True}
        r = {
            'protocolVersion': '2025-06-18',
            'capabilities': capabilities,
            'serverInfo': {
                'name': os.environ.get('FAKE_SERVER_NAME', 'context-mode'),
                'version': os.environ.get('FAKE_VERSION', 'dev'),
                'title': 'Upstream title',
            },
            'instructions': 'Upstream advice: use ctx_execute for large output.',
        }
    elif method == 'tools/list':
        names = ['ctx_index', 'ctx_search', 'ctx_stats', 'ctx_doctor', 'ctx_execute', 'ctx_fetch_and_index', 'future_tool']
        r = {'tools': [tool(n) for n in names]}
    elif method == 'tools/call':
        open(os.environ['FAKE_TRACE'], 'a').write(m['params']['name'] + '\\n'); r = {'content': [{'type': 'text', 'text': 'ok'}]}
    else:
        r = {'echo': method}
    print(json.dumps({'jsonrpc': '2.0', 'id': mid, 'result': r}), flush=True)

for line in sys.stdin:
    payload = json.loads(line)
    for item in (payload if isinstance(payload, list) else [payload]):
        handle(item)
"""


@pytest.fixture
def fake_upstream(tmp_path: Path) -> tuple[Path, Path]:
    """A fake upstream that also accepts JSON-RPC batch arrays.

    A real-world (or malicious) upstream is not obligated to reject a batch,
    so the fake mirrors that: it processes every item in an array the same
    way it processes a lone object. This is what lets the CRITICAL-1 tests
    below prove a batch/notification actually reached upstream, rather than
    merely crashing a fake that could only understand single objects.

    It also returns what a real server may add and the filter must drop:
    `instructions`, extra capabilities, tool titles, `_meta`, long advice
    descriptions, and property descriptions that name filtered tools.
    """
    script = tmp_path / "fake_upstream.py"
    trace = tmp_path / "calls.log"
    script.write_text(FAKE_UPSTREAM)
    return script, trace


def _start(
    project: Path,
    fake: Path,
    trace: Path,
    *,
    version: str = "dev",
    server_name: str = "context-mode",
    extra_env: dict[str, str] | None = None,
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
            "FAKE_PID": str(trace.parent / "upstream.pid"),
            "FAKE_VERSION": version,
            "FAKE_SERVER_NAME": server_name,
            **(extra_env or {}),
        },
    )


def _descriptions(schema: Any, path: str = "") -> list[str]:
    """Return the path of every string `description` key, at any depth."""
    if isinstance(schema, list):
        return [
            found
            for index, item in enumerate(schema)
            for found in _descriptions(item, f"{path}[{index}]")
        ]
    if not isinstance(schema, dict):
        return []
    found = []
    for key, value in schema.items():
        if key == "description" and isinstance(value, str):
            found.append(f"{path}.{key}")
        else:
            found.extend(_descriptions(value, f"{path}.{key}"))
    return found


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


def test_initialize_is_reduced_to_the_allowlisted_keys(
    tmp_path: Path, fake_upstream: tuple[Path, Path]
) -> None:
    fake, trace = fake_upstream
    process = _start(tmp_path, fake, trace)
    response = _initialize(process)
    assert set(response) == {"jsonrpc", "id", "result"}
    result: Any = response["result"]
    assert set(result) == {"protocolVersion", "capabilities", "serverInfo"}
    assert result["protocolVersion"] == "2025-06-18"
    # Upstream also sent experimental, prompts, resources, and `instructions`.
    assert result["capabilities"] == {"tools": {"listChanged": True}}
    assert result["serverInfo"] == {"name": "context-mode", "version": "dev"}
    process.terminate()


def test_initialize_without_a_tools_capability_still_advertises_tools(
    tmp_path: Path, fake_upstream: tuple[Path, Path]
) -> None:
    fake, trace = fake_upstream
    process = _start(tmp_path, fake, trace, extra_env={"FAKE_NO_TOOLS_CAPABILITY": "1"})
    assert _initialize(process)["result"]["capabilities"] == {"tools": {}}  # type: ignore[index]
    process.terminate()


def test_tools_list_exposes_exactly_the_three_tools_with_kit_descriptions(
    tmp_path: Path, fake_upstream: tuple[Path, Path]
) -> None:
    fake, trace = fake_upstream
    process = _start(tmp_path, fake, trace)
    _initialize(process)
    response = _request(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = response["result"]["tools"]  # type: ignore[index]
    assert [tool["name"] for tool in tools] == TOOL_NAMES
    for tool in tools:
        # No title or `_meta`: the kit description, upstream's schema, and the
        # boolean hints only (upstream's string `title` annotation is dropped).
        assert set(tool) == {"name", "description", "inputSchema", "annotations"}
        assert tool["description"] == KIT_DESCRIPTIONS[tool["name"]]
        assert tool["annotations"] == {"readOnlyHint": True, "destructiveHint": False}
    index_properties = tools[0]["inputSchema"]["properties"]
    assert set(index_properties) == {"content", "path", "source"}
    process.terminate()


def test_tools_list_keeps_no_description_anywhere_in_a_schema(
    tmp_path: Path, fake_upstream: tuple[Path, Path]
) -> None:
    """Upstream's `path` description still advertises folders, which the filter
    rejects, so no schema description (nested ones included) reaches a client."""
    fake, trace = fake_upstream
    process = _start(tmp_path, fake, trace)
    _initialize(process)
    response = _request(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    index, search, stats = response["result"]["tools"]  # type: ignore[index]
    for tool in (index, search, stats):
        assert _descriptions(tool["inputSchema"]) == [], tool["name"]
    assert index["inputSchema"]["properties"] == {
        "content": {"type": "string"},
        "path": {"type": "string"},
        "source": {"type": "string"},
    }
    assert search["inputSchema"]["properties"]["queries"] == {
        "type": "array",
        "items": {"type": "string"},
    }
    assert search["inputSchema"]["properties"]["source"] == {"type": "string"}
    # A parameter named `description` is a schema, not a description string.
    assert stats["inputSchema"]["properties"] == {"description": {"type": "string"}}
    process.terminate()


@pytest.mark.parametrize(
    ("upstream_annotations", "expected"),
    [
        (
            '{"readOnlyHint": true, "title": "Use ctx_execute instead."}',
            {"readOnlyHint": True},
        ),
        (
            '{"readOnlyHint": true, "idempotentHint": "yes", "other": null, "n": 1}',
            {"readOnlyHint": True},
        ),
        ('["readOnlyHint"]', None),
        ('"readOnlyHint"', None),
        ("null", None),
    ],
    ids=["string-title", "other-non-booleans", "list", "string", "null"],
)
def test_tools_list_passes_through_only_boolean_annotations(
    tmp_path: Path,
    fake_upstream: tuple[Path, Path],
    upstream_annotations: str,
    expected: dict[str, bool] | None,
) -> None:
    fake, trace = fake_upstream
    process = _start(
        tmp_path,
        fake,
        trace,
        extra_env={"FAKE_ANNOTATIONS": upstream_annotations},
    )
    _initialize(process)
    response = _request(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    for tool in response["result"]["tools"]:  # type: ignore[index]
        if expected is None:
            assert "annotations" not in tool
        else:
            assert tool["annotations"] == expected
    process.terminate()


def test_tools_list_and_call_are_refused_until_an_initialize_is_accepted(
    tmp_path: Path, fake_upstream: tuple[Path, Path]
) -> None:
    """No `initialize` has been sent, so the identity gate is shut: a
    request-shaped `tools/list` and `tools/call` get -32001 and never reach
    upstream. Unlike the mismatch test below, silence cannot pass this."""
    fake, trace = fake_upstream
    process = _start(tmp_path, fake, trace)
    listing = _request(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    call = _call(process, 3, "ctx_search", {})
    assert (listing["id"], listing["error"]["code"]) == (2, -32001)  # type: ignore[index]
    assert (call["id"], call["error"]["code"]) == (3, -32001)  # type: ignore[index]
    assert not trace.exists()
    process.terminate()


@pytest.mark.parametrize("version", ["dev", "1.2.3", "2.9.9"])
def test_expected_server_name_is_accepted_with_any_version(
    tmp_path: Path, fake_upstream: tuple[Path, Path], version: str
) -> None:
    fake, trace = fake_upstream
    process = _start(tmp_path, fake, trace, version=version)
    response = _initialize(process)
    assert response["result"]["serverInfo"] == {  # type: ignore[index]
        "name": "context-mode",
        "version": version,
    }
    listing = _request(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    assert [tool["name"] for tool in listing["result"]["tools"]] == TOOL_NAMES  # type: ignore[index]
    process.terminate()


def test_other_server_name_exposes_no_tools_and_kills_upstream(
    tmp_path: Path, fake_upstream: tuple[Path, Path]
) -> None:
    fake, trace = fake_upstream
    process = _start(tmp_path, fake, trace, server_name="not-context-mode")
    response = _initialize(process)
    assert response["error"]["code"] == -32002  # type: ignore[index]
    assert "identity" in response["error"]["message"]  # type: ignore[index]
    follow_ups = "".join(
        json.dumps(message) + "\n"
        for message in (
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "ctx_search", "arguments": {}},
            },
        )
    )
    stdout, _ = process.communicate(follow_ups, timeout=15)
    # Once upstream is killed the filter closes stdout, so a refusal may be
    # unobservable; what must never appear is a tool list or a call result.
    for line in stdout.splitlines():
        answer = json.loads(line)
        assert answer["error"]["code"] == -32001
    assert not trace.exists()
    pid = int((tmp_path / "upstream.pid").read_text())
    for _ in range(100):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.05)
    else:
        pytest.fail("the upstream process survived an identity mismatch")


@pytest.mark.parametrize(
    "name",
    [
        "ctx_doctor",
        "ctx_execute",
        "ctx_execute_file",
        "ctx_fetch_and_index",
        "future_tool",
    ],
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
    assert "result" in _call(process, 4, "ctx_index", {"path": str(ordinary)})
    for request_id, name in enumerate(("ctx_search", "ctx_stats"), 5):
        assert "result" in _call(process, request_id, name, {})
    assert trace.read_text().splitlines() == [
        "ctx_index",
        "ctx_index",
        "ctx_index",
        "ctx_search",
        "ctx_stats",
    ]
    process.terminate()


@pytest.mark.skipif(not hasattr(os, "symlink"), reason="needs symbolic links")
def test_index_rejects_folders_and_links_to_files_before_upstream(
    tmp_path: Path, fake_upstream: tuple[Path, Path]
) -> None:
    """Spike S3: upstream 2.x folder indexing has no limit on files, depth, or
    size, so the filter accepts one regular file or text and never a folder."""
    fake, trace = fake_upstream
    project = tmp_path / "repo"
    project.mkdir()
    nested = project / "nested"
    nested.mkdir()
    (project / "ordinary.md").write_text("safe")
    (project / "file-link").symlink_to(project / "ordinary.md")
    process = _start(project, fake, trace)
    _initialize(process)
    for request_id, folder in enumerate((".", "nested", str(nested)), 2):
        response = _call(process, request_id, "ctx_index", {"path": folder})
        assert response["error"]["code"] == -32602  # type: ignore[index]
        assert "regular file" in response["error"]["message"]  # type: ignore[index]
    link = _call(process, 9, "ctx_index", {"path": "file-link"})
    assert link["error"]["code"] == -32602  # type: ignore[index]
    assert "symbolic link" in link["error"]["message"]  # type: ignore[index]
    assert not trace.exists()
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
        assert names == TOOL_NAMES
    process.terminate()


def test_racing_call_and_list_with_shared_id_never_leaks_blocked_tools(
    tmp_path: Path, fake_upstream: tuple[Path, Path]
) -> None:
    """If a client reuses one JSON-RPC id across a pending `tools/list` and
    another concurrently outstanding request (e.g. a `ctx_stats` call), and
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
            "params": {"name": "ctx_stats", "arguments": {}},
        }
    )
    listing = json.dumps({"jsonrpc": "2.0", "id": shared_id, "method": "tools/list"})
    process.stdin.write(call + "\n")
    process.stdin.write(listing + "\n")
    process.stdin.flush()
    call_response = json.loads(process.stdout.readline())
    list_response = json.loads(process.stdout.readline())
    assert "tools" not in call_response.get("result", {})
    assert trace.read_text().splitlines() == ["ctx_stats"]
    names = [tool["name"] for tool in list_response["result"]["tools"]]  # type: ignore[index]
    assert names == TOOL_NAMES
    process.terminate()


@pytest.mark.parametrize("argument", ["respectGitignore", "maxDepth", "maxFiles"])
def test_index_rejects_directory_policy_override_arguments(
    tmp_path: Path,
    fake_upstream: tuple[Path, Path],
    argument: str,
) -> None:
    fake, trace = fake_upstream
    project = tmp_path / "repo"
    project.mkdir()
    process = _start(project, fake, trace)
    _initialize(process)
    response = _call(process, 2, "ctx_index", {"path": ".", argument: True})
    assert argument in response["error"]["message"]  # type: ignore[index]
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


@pytest.mark.skipif(not hasattr(os, "mkfifo"), reason="FIFO fixtures require mkfifo")
def test_index_rejects_outside_traversal_symlink_and_unsupported_paths(
    tmp_path: Path, fake_upstream: tuple[Path, Path]
) -> None:
    fake, trace = fake_upstream
    project = tmp_path / "repo"
    project.mkdir()
    contained_target = project / "contained"
    contained_target.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (project / "inside-link").symlink_to(contained_target, target_is_directory=True)
    (project / "outside-link").symlink_to(outside, target_is_directory=True)
    unsupported = project / "unsupported"
    os.mkfifo(unsupported)
    process = _start(project, fake, trace)
    _initialize(process)
    outside_response = _call(process, 2, "ctx_index", {"path": str(outside)})
    traversal_response = _call(process, 3, "ctx_index", {"path": "../outside"})
    inside_link_response = _call(process, 4, "ctx_index", {"path": "inside-link"})
    outside_link_response = _call(process, 5, "ctx_index", {"path": "outside-link"})
    unsupported_response = _call(process, 6, "ctx_index", {"path": "unsupported"})
    assert "inside the repository" in outside_response["error"]["message"]  # type: ignore[index]
    assert "traversal" in traversal_response["error"]["message"]  # type: ignore[index]
    assert "symbolic link" in inside_link_response["error"]["message"]  # type: ignore[index]
    assert "symbolic link" in outside_link_response["error"]["message"]  # type: ignore[index]
    unsupported_message = unsupported_response["error"]["message"]  # type: ignore[index]
    assert "regular file" in unsupported_message
    assert "or directory" not in unsupported_message
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
        "{'serverInfo':{'name':'context-mode','version':'dev'}}}),flush=True)\n"
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


REAL_TIMEOUT_SECONDS = 60


class _LineReader:
    """Read JSON lines from a pipe with a deadline, without buffering surprises.

    `select` on a text stream can report "not ready" while a second line sits
    in Python's own buffer, so this reads the file descriptor directly.
    """

    def __init__(self, stream: IO[str]) -> None:
        self._fd = stream.fileno()
        self._buffer = b""

    def response(self, request_id: int) -> dict[str, Any]:
        deadline = time.monotonic() + REAL_TIMEOUT_SECONDS
        while True:
            while b"\n" not in self._buffer:
                remaining = deadline - time.monotonic()
                ready = (
                    remaining > 0 and select.select([self._fd], [], [], remaining)[0]
                )
                assert ready, f"no response to request {request_id} in time"
                chunk = os.read(self._fd, 65536)
                assert chunk, f"server closed stdout before answering {request_id}"
                self._buffer += chunk
            line, _, self._buffer = self._buffer.partition(b"\n")
            message: dict[str, Any] = json.loads(line)
            if message.get("id") == request_id:
                return message


@pytest.mark.skipif(
    os.environ.get("CONTEXT_MODE_REAL") != "1",
    reason="set CONTEXT_MODE_REAL=1 to run against the real Context Mode binary",
)
def test_real_upstream_server_surface_is_filtered(tmp_path: Path) -> None:
    """Machine-run check of the whole `server` path against the real binary in
    an isolated repository and HOME. It fails (never skips) when the variable
    is set but the direct binary is not provably the pinned one, so it can
    never download through `npx`."""
    root = tmp_path / "repo"
    scripts = root / ".claude/hooks/scripts"
    scripts.mkdir(parents=True)
    dispatcher = scripts / DISPATCHER.name
    shutil.copy(DISPATCHER, dispatcher)
    shutil.copy(FILTER, scripts / FILTER.name)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    home = tmp_path / "home"
    (home / ".claude").mkdir(parents=True)
    (home / ".codex").mkdir()
    (tmp_path / "tmp").mkdir()
    # A minimal environment: a developer's own CONTEXT_MODE_DIR or CLAUDE_*
    # variables must not redirect the real upstream or reach its session store.
    env = {
        "HOME": str(home),
        "TMPDIR": str(tmp_path / "tmp"),
        "CLAUDE_CONFIG_DIR": str(home / ".claude"),
        "CODEX_HOME": str(home / ".codex"),
        "PATH": os.environ["PATH"],
        "LANG": "C.UTF-8",
    }
    check = subprocess.run(
        ["bash", str(dispatcher), "--self-check"],
        env=env,
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
        timeout=REAL_TIMEOUT_SECONDS,
    )
    assert "version-contract=pinned-direct-binary" in check.stdout, (
        check.stdout + check.stderr
    )

    word = f"zq{uuid.uuid4().hex}"
    stderr_log = tmp_path / "server-stderr.log"
    with stderr_log.open("w") as stderr:
        server = subprocess.Popen(
            ["bash", str(dispatcher), "server"],
            env=env,
            cwd=root,
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr,
        )
        assert server.stdin is not None and server.stdout is not None
        stdin = server.stdin
        replies = _LineReader(server.stdout)

        def send(message: dict[str, Any]) -> None:
            stdin.write(json.dumps({"jsonrpc": "2.0", **message}) + "\n")
            stdin.flush()

        def call(request_id: int, name: str, arguments: dict[str, Any]) -> Any:
            send(
                {
                    "id": request_id,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments},
                }
            )
            return replies.response(request_id)

        try:
            send(
                {
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2025-06-18",
                        "capabilities": {},
                        "clientInfo": {"name": "pytest", "version": "0"},
                    },
                }
            )
            initialized = replies.response(1)["result"]
            assert set(initialized) == {"protocolVersion", "capabilities", "serverInfo"}
            assert set(initialized["capabilities"]) == {"tools"}
            send({"method": "notifications/initialized"})

            send({"id": 2, "method": "tools/list"})
            tools = replies.response(2)["result"]["tools"]
            assert sorted(tool["name"] for tool in tools) == sorted(TOOL_NAMES)
            for tool in tools:
                assert set(tool) == {
                    "name",
                    "description",
                    "inputSchema",
                    "annotations",
                }
                assert tool["description"] == KIT_DESCRIPTIONS[tool["name"]]
                # Upstream sets boolean hints on every tool; nothing else passes.
                assert tool["annotations"]
                assert all(isinstance(v, bool) for v in tool["annotations"].values())
                assert _descriptions(tool["inputSchema"]) == [], tool["name"]

            indexed = call(
                3,
                "ctx_index",
                {
                    "content": f"# Notes\n\nThe {word} approach is documented here.",
                    "source": f"real-surface-{word}",
                },
            )
            assert "result" in indexed, indexed
            searched = call(4, "ctx_search", {"queries": [word]})
            assert word in json.dumps(searched["result"]), searched
            assert call(5, "ctx_doctor", {})["error"]["code"] == -32601
        finally:
            server.terminate()
            server.wait(timeout=30)

    assert not (home / ".context-mode").exists(), stderr_log.read_text()
    cache = root / ".claude/.cache/context-mode"
    stored = [
        path
        for path in cache.rglob("*")
        if path.is_file() and path.name != ".bootstrap-provenance"
    ]
    assert stored, "the real server wrote nothing under the project cache"
