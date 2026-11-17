"""Decision battery for the tool inputs the Copilot harness sends to ``protect-files``.

The real runtime and the real VS Code send inputs the guard did not read:
patch text from ``apply_patch`` (a string, not an object), the shell helper
tools ``read_bash``/``list_bash``/``stop_bash`` (no command), the read tool's
PascalCase name ``Read``, and a ``paths`` list on the search tools. The main
payloads copy shapes recorded in the evidence folder
``.claude/explorations/2026-11-17_copilot-harness-migration-evidence/``
(``raw/hook-inputs-patch-tool.txt``, ``raw/planning-probe-e3-hook-inputs.txt``,
``raw/outcomes-s1.txt``); the other rows try the same tools with other keys and
other targets.

Expected decisions come from ``docs/target-mapping.md`` ("Read tools stay
allowed", an ask on Claude Code and GitHub Copilot and a deny on Codex and
Antigravity for hook and agent files, a deny on a secret-shaped file for every
tool) and from the decision-change table of the big plan
``copilot-harness-migration`` (rows L1, L2, L3, T1, T2). They never come from
running the guard. The table compares the parsed ``permissionDecision`` and the
exit code, not bytes, so a later change of the output shape does not break it.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_hook_gates import _run_protect_files  # noqa: E402

CLIENTS = ("github-copilot", "claude-code", "openai-codex", "google-antigravity")
ALLOW, ASK, DENY = "allow", "ask", "deny"
# A deny that comes from a failed classification: the shell hook prints a deny
# and exits 2, so the runtime refuses the call.
FAIL_CLOSED = (DENY, 2)

PLAIN = "notes.txt"
SECRET = ".env"
HOOK_FILE = ".github/hooks/hooks.json"
AGENT_FILE = ".claude/agents/coder.md"
AGENT_SECRET = ".claude/agents/.env"
TARGETS = (PLAIN, SECRET, HOOK_FILE, AGENT_FILE, AGENT_SECRET)
# A clean `Add File` target in a hook folder that does not exist yet.
EVIL_HOOK = ".github/hooks/evil.json"

# docs/target-mapping.md: a hook or agent file asks where the client can ask and
# is denied where it cannot.
CONFIG_DECISION = {
    "github-copilot": ASK,
    "claude-code": ASK,
    "openai-codex": DENY,
    "google-antigravity": DENY,
}


def writer_decision(client: str, target: str) -> str:
    """A tool that can change the file."""
    if target in (SECRET, AGENT_SECRET):
        return DENY
    if target in (HOOK_FILE, AGENT_FILE):
        return CONFIG_DECISION[client]
    return ALLOW


def reader_decision(client: str, target: str) -> str:
    """A read tool: no decision for a config, a deny for a secret-shaped file."""
    return DENY if target in (SECRET, AGENT_SECRET) else ALLOW


def _patch(*hunks: str) -> str:
    return "*** Begin Patch\n" + "".join(hunks) + "*** End Patch\n"


def update_patch(target: str) -> str:
    return _patch(f"*** Update File: {target}\n@@\n-a\n+b\n")


def _payload(tool: str, tool_input: object) -> dict:
    return {
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": tool_input,
    }


def _camel_payload(tool: str, tool_args: object) -> dict:
    return {"toolName": tool, "toolArgs": tool_args}


def outcomes(payload: dict, root: Path) -> dict[str, tuple[str, int]]:
    """Run the shell guard for every client: the parsed decision and the exit code."""
    found: dict[str, tuple[str, int]] = {}
    for client in CLIENTS:
        process = _run_protect_files(payload, root, client)
        decision = ALLOW
        if process.stdout.strip():
            body = json.loads(process.stdout)
            # The decision is nested today; read a top-level one too.
            decision = body.get("hookSpecificOutput", body)["permissionDecision"]
        found[client] = (decision, process.returncode)
    return found


def assert_outcomes(
    payload: dict, root: Path, expected: Callable[[str], str | tuple[str, int]]
) -> None:
    """Every client must give its expected outcome; all mismatches are listed."""
    wanted = {
        client: (value if isinstance(value, tuple) else (value, 0))
        for client in CLIENTS
        for value in [expected(client)]
    }
    found = outcomes(payload, root)
    wrong = {c: (found[c], wanted[c]) for c in CLIENTS if found[c] != wanted[c]}
    assert not wrong, "(found, expected) per client: %r" % wrong


# --- tools whose decision depends on the target ------------------------------

# (tool name, input for a target). Read tools get no decision for a config.
READERS = (
    pytest.param("Read", lambda t: {"path": t}, id="Read-path"),
    pytest.param("Read", lambda t: {"file_path": t}, id="Read-file_path"),
    pytest.param("view", lambda t: {"path": t}, id="view"),
    pytest.param("read_file", lambda t: {"filePath": t}, id="read_file"),
    pytest.param("Grep", lambda t: {"pattern": "x", "paths": [t]}, id="Grep-paths"),
    pytest.param("Grep", lambda t: {"pattern": "x", "path": t}, id="Grep-path"),
    pytest.param("Glob", lambda t: {"pattern": "*", "paths": [t]}, id="Glob-paths"),
    pytest.param("grep", lambda t: {"pattern": "x", "paths": [t]}, id="grep-paths"),
    pytest.param("rg", lambda t: {"pattern": "x", "paths": [t]}, id="rg-paths"),
    pytest.param("glob", lambda t: {"pattern": "*", "paths": [t]}, id="glob-paths"),
)
SHELL_WRITERS = ("Bash", "write_bash", "read_bash", "list_bash", "stop_bash")
WRITERS = (
    pytest.param("Write", lambda t: {"path": t, "file_text": "x"}, id="Write-object"),
    pytest.param(
        "Edit",
        lambda t: {"path": t, "old_str": "a", "new_str": "b"},
        id="Edit-object",
    ),
    pytest.param("Edit", update_patch, id="Edit-patch-text"),
    *(
        pytest.param(
            name, lambda t: {"command": f"rm -f {t}"}, id=f"{name}-with-command"
        )
        for name in SHELL_WRITERS
    ),
)


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(("tool", "build"), READERS)
def test_read_tools_get_no_decision_for_a_config_and_a_deny_for_a_secret(
    tmp_path: Path, tool: str, build: Callable[[str], object], target: str
) -> None:
    # L1 (the `Read` rows on a hook or agent file asked before the change; DA7)
    # and T1 (the search rows on a secret-shaped file got no decision).
    assert_outcomes(
        _payload(tool, build(target)), tmp_path, lambda c: reader_decision(c, target)
    )


@pytest.mark.parametrize("target", TARGETS)
@pytest.mark.parametrize(("tool", "build"), WRITERS)
def test_tools_that_change_files_keep_their_decision(
    tmp_path: Path, tool: str, build: Callable[[str], object], target: str
) -> None:
    # L3 for the patch text row (it crashed and was denied before the change);
    # the other rows keep today's decision, shell helpers with a command included.
    assert_outcomes(
        _payload(tool, build(target)), tmp_path, lambda c: writer_decision(c, target)
    )


# --- shell helper tools (L2) -------------------------------------------------


@pytest.mark.parametrize(
    ("tool", "tool_input"),
    (
        pytest.param("read_bash", {"shellId": "0", "delay": 1}, id="read_bash"),
        pytest.param("list_bash", {}, id="list_bash"),
        pytest.param("stop_bash", {"shellId": "0"}, id="stop_bash"),
        pytest.param("bash_shutdown", {"shellId": "0"}, id="bash_shutdown"),
    ),
)
def test_shell_helpers_without_a_command_get_no_decision(
    tmp_path: Path, tool: str, tool_input: dict
) -> None:
    assert_outcomes(_payload(tool, tool_input), tmp_path, lambda c: ALLOW)


@pytest.mark.parametrize("tool", ("read_bash", "list_bash", "stop_bash"))
def test_a_shell_helper_is_still_judged_for_a_path_key(
    tmp_path: Path, tool: str
) -> None:
    payload = _payload(tool, {"shellId": "0", "path": SECRET})

    assert_outcomes(payload, tmp_path, lambda c: DENY)


@pytest.mark.parametrize(
    ("tool", "tool_input"),
    (
        pytest.param("write_bash", {"shellId": "0"}, id="write_bash-no-command"),
        pytest.param("write_bash", {}, id="write_bash-empty"),
        pytest.param("Bash", {"description": "x"}, id="Bash-no-command"),
        pytest.param("bash", {"command": None}, id="bash-null-command"),
        pytest.param(
            "read_bash", {"shellId": "0", "command": None}, id="read_bash-null-command"
        ),
        pytest.param(
            "stop_bash", {"shellId": "0", "command": 3}, id="stop_bash-number-command"
        ),
    ),
)
def test_a_shell_tool_with_no_usable_command_fails_closed(
    tmp_path: Path, tool: str, tool_input: dict
) -> None:
    assert_outcomes(_payload(tool, tool_input), tmp_path, lambda c: FAIL_CLOSED)


# --- patch text (L3) ---------------------------------------------------------

# The five payloads of the evidence file raw/hook-inputs-patch-tool.txt. The
# folder placeholder is not part of any of them.
EVIDENCE_PATCHES = (
    pytest.param(
        "*** Begin Patch\n*** Add File: probe-patch.txt\n+plain file\n*** End Patch\n",
        lambda c: ALLOW,
        id="plain-file-added",
    ),
    pytest.param(
        "*** Begin Patch\n*** Add File: .env\n+SECRET=1\n*** End Patch\n",
        lambda c: DENY,
        id="secret-added",
    ),
    pytest.param(
        "*** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n",
        lambda c: CONFIG_DECISION[c],
        id="hook-file-added",
    ),
    pytest.param(
        "*** Begin Patch\n*** Update File: .mcp.json\n@@\n-{\n+{ \n*** End Patch\n",
        lambda c: CONFIG_DECISION[c],
        id="server-config-updated",
    ),
    pytest.param(
        "*** Begin Patch\n*** Delete File: .claude/agents/coder.md\n*** End Patch\n",
        lambda c: CONFIG_DECISION[c],
        id="agent-file-deleted",
    ),
)


@pytest.mark.parametrize(("patch", "expected"), EVIDENCE_PATCHES)
@pytest.mark.parametrize(
    "build",
    (
        pytest.param(lambda text: _payload("Edit", text), id="pascal-Edit"),
        pytest.param(lambda text: _camel_payload("apply_patch", text), id="camel"),
    ),
)
def test_patch_text_gets_the_decision_of_its_target(
    tmp_path: Path,
    build: Callable[[str], dict],
    patch: str,
    expected: Callable[[str], str],
) -> None:
    assert_outcomes(build(patch), tmp_path, expected)


def _header(shape: str) -> str:
    """One `Add File` header in each shape the plan names (row T2)."""
    return {
        "indented": f"  *** Add File: {EVIL_HOOK}\n",
        "lowercase": f"*** add file: {EVIL_HOOK}\n",
        "extra-blanks": f"***  Add  File:  {EVIL_HOOK}\n",
        "plain": f"*** Add File: {EVIL_HOOK}\n",
    }[shape]


HEADER_SHAPES = ("plain", "indented", "lowercase", "extra-blanks")


@pytest.mark.parametrize("shape", HEADER_SHAPES)
def test_a_patch_header_in_any_shape_gives_its_target_as_text(
    tmp_path: Path, shape: str
) -> None:
    patch = _patch(_header(shape), "+{}\n")

    assert_outcomes(_payload("Edit", patch), tmp_path, lambda c: CONFIG_DECISION[c])


@pytest.mark.parametrize("shape", HEADER_SHAPES)
def test_a_patch_header_in_any_shape_gives_its_target_as_an_object_input(
    tmp_path: Path, shape: str
) -> None:
    patch = _patch(_header(shape), "+{}\n")

    assert_outcomes(
        _payload("apply_patch", {"input": patch}),
        tmp_path,
        lambda c: CONFIG_DECISION[c],
    )


@pytest.mark.parametrize("shape", HEADER_SHAPES)
def test_a_patch_header_in_any_shape_is_denied_in_a_shell_heredoc(
    tmp_path: Path, shape: str
) -> None:
    """A command that names a protected file but runs an unknown program is an
    uncertain hit: denied on every client (docs/target-mapping.md)."""
    patch = _patch(_header(shape), "+{}\n")
    command = "apply_patch <<'EOF'\n" + patch + "EOF"

    assert_outcomes(_payload("Bash", {"command": command}), tmp_path, lambda c: DENY)


@pytest.mark.parametrize(
    "header",
    (
        pytest.param("*** Update File: {t}\n@@\n-a\n+b\n", id="update"),
        pytest.param("*** Delete File: {t}\n", id="delete"),
        pytest.param(
            "*** Update File: notes.txt\n*** Move to: {t}\n@@\n-a\n+b\n", id="move"
        ),
        pytest.param("  *** UPDATE FILE : {t}\n@@\n-a\n+b\n", id="update-blanks-case"),
        pytest.param("***\tDelete\tFile:\t{t}\n", id="delete-tabs"),
        pytest.param(
            "*** Update File: notes.txt\n  ***   move   to :  {t}\n@@\n-a\n+b\n",
            id="move-indented",
        ),
    ),
)
def test_every_patch_header_kind_gives_its_target(tmp_path: Path, header: str) -> None:
    patch = _patch(header.format(t=EVIL_HOOK))

    assert_outcomes(_payload("Edit", patch), tmp_path, lambda c: CONFIG_DECISION[c])


def test_a_hunk_context_line_that_looks_like_a_marker_is_not_denied(
    tmp_path: Path,
) -> None:
    """An update hunk's context line is the file's own text after one space; a
    Markdown line ` *** bold ***` must not block an ordinary edit."""
    patch = _patch("*** Update File: notes.txt\n@@\n *** bold ***\n-a\n+b\n")

    assert_outcomes(_payload("Edit", patch), tmp_path, lambda c: ALLOW)


@pytest.mark.parametrize("spelled_target", (HOOK_FILE, SECRET))
def test_a_hunk_context_line_that_spells_a_header_is_judged_as_that_target(
    tmp_path: Path, spelled_target: str
) -> None:
    """Known false positive, pinned. A context line is the file's own text after
    one space, but ` *** Add File: <path>` cannot be told from an indented
    header (the runtime applies one). So a patch to a document about patches
    gets the target's decision, though it only edits `notes.txt`."""
    patch = _patch(
        f"*** Update File: notes.txt\n@@\n *** Add File: {spelled_target}\n-a\n+b\n"
    )

    assert_outcomes(
        _payload("Edit", patch),
        tmp_path,
        lambda c: writer_decision(c, spelled_target),
    )


def test_added_content_that_looks_like_a_header_is_data(tmp_path: Path) -> None:
    patch = _patch("*** Add File: notes.txt\n+*** Add File: .env\n")

    assert_outcomes(_payload("Edit", patch), tmp_path, lambda c: ALLOW)


# Built in pieces so this file never holds an unterminated patch marker.
BEGIN = "*** Begin " + "Patch\n"
END = "*** End " + "Patch\n"


@pytest.mark.parametrize(
    ("tool", "tool_input"),
    (
        pytest.param(
            "Edit", BEGIN + "*** Add File: notes.txt\n+x\n", id="no-end-marker"
        ),
        pytest.param("Edit", "hello world", id="neither-json-nor-patch"),
        pytest.param("Edit", "", id="empty-string"),
        pytest.param("Edit", END, id="end-marker-only"),
        pytest.param("Edit", "x\n" + BEGIN + END, id="text-before-the-begin-marker"),
        pytest.param("Edit", "[1]", id="json-that-is-not-an-object"),
        pytest.param("Edit", BEGIN + "*** Add File: \n+x\n" + END, id="empty-target"),
        pytest.param("Read", BEGIN + END, id="to-a-read-tool-Read"),
        pytest.param("view", BEGIN + END, id="to-a-read-tool-view"),
        pytest.param("grep", BEGIN + END, id="to-a-read-tool-grep"),
        pytest.param("Bash", BEGIN + END, id="to-a-shell-tool-Bash"),
        pytest.param("read_bash", BEGIN + END, id="to-a-shell-helper"),
        pytest.param("write_bash", BEGIN + END, id="to-write_bash"),
        pytest.param("", BEGIN + END, id="to-no-tool-name"),
    ),
)
def test_text_that_is_not_a_usable_patch_fails_closed(
    tmp_path: Path, tool: str, tool_input: str
) -> None:
    assert_outcomes(_payload(tool, tool_input), tmp_path, lambda c: FAIL_CLOSED)


def test_a_patch_to_a_missing_tool_name_in_camel_case_fails_closed(
    tmp_path: Path,
) -> None:
    assert_outcomes({"toolArgs": BEGIN + END}, tmp_path, lambda c: FAIL_CLOSED)


def test_blanks_before_the_begin_marker_are_read(tmp_path: Path) -> None:
    patch = "  \n" + _patch(f"*** Add File: {EVIL_HOOK}\n+{{}}\n")

    assert_outcomes(_payload("Edit", patch), tmp_path, lambda c: CONFIG_DECISION[c])


def test_json_text_input_keeps_its_old_path(tmp_path: Path) -> None:
    """A string that parses as a JSON object is still read as that object."""
    encoded = json.dumps({"path": SECRET})

    assert_outcomes(_payload("Write", encoded), tmp_path, lambda c: DENY)
    assert_outcomes(_camel_payload("create", encoded), tmp_path, lambda c: DENY)


# --- search tools: what is not judged (T1 limit) ------------------------------


@pytest.mark.parametrize(
    ("tool", "tool_input"),
    (
        pytest.param("Glob", {"pattern": ".env*"}, id="glob-filter-pattern"),
        pytest.param("glob", {"pattern": "**/.env*"}, id="glob-recursive-pattern"),
        pytest.param("Grep", {"pattern": "x", "glob": ".env*"}, id="grep-glob-filter"),
        pytest.param("grep", {"pattern": "x", "paths": ["."]}, id="folder-search"),
        pytest.param(
            "rg", {"pattern": "x", "paths": [".claude/agents"]}, id="agent-folder"
        ),
        pytest.param("rg", {"pattern": "x", "paths": ["src", "docs"]}, id="folders"),
        pytest.param("grep", {"pattern": SECRET}, id="pattern-names-a-secret"),
    ),
)
def test_a_folder_search_or_a_glob_filter_is_not_judged(
    tmp_path: Path, tool: str, tool_input: dict
) -> None:
    assert_outcomes(_payload(tool, tool_input), tmp_path, lambda c: ALLOW)


@pytest.mark.parametrize("tool", ("grep", "rg", "Grep"))
def test_a_search_over_several_paths_is_denied_for_one_secret(
    tmp_path: Path, tool: str
) -> None:
    payload = _payload(tool, {"pattern": "x", "paths": ["src", AGENT_SECRET, "docs"]})

    assert_outcomes(payload, tmp_path, lambda c: DENY)


# --- no early return skips a later check -------------------------------------


@pytest.mark.parametrize("tool", ("Edit", "apply_patch"))
def test_a_secret_stays_denied_beside_a_hook_file_in_one_patch(
    tmp_path: Path, tool: str
) -> None:
    patch = _patch(f"*** Add File: {EVIL_HOOK}\n+{{}}\n", "*** Delete File: .env\n")

    assert_outcomes(_payload(tool, patch), tmp_path, lambda c: DENY)


def test_a_secret_stays_denied_for_a_helper_that_also_names_a_hook_file(
    tmp_path: Path,
) -> None:
    payload = _payload("read_bash", {"shellId": "0", "path": SECRET, "file": HOOK_FILE})

    assert_outcomes(payload, tmp_path, lambda c: DENY)


# --- the other runtime tools (docs/target-mapping.md, "Copilot harness tools and
# guard handling"): the hook names and input keys are from the offline probe
# runs of Phase B; handling 1 has no command, path, or code to judge --------------

NO_DECISION_TOOLS = (
    pytest.param(
        "sql",
        {"description": "List tables", "query": "SELECT name FROM sqlite_master"},
        id="sql",
    ),
    pytest.param(
        "session_store_sql",
        {"description": "Recent sessions", "query": "SELECT 1", "source": "local"},
        id="session_store_sql",
    ),
    pytest.param("TodoWrite", {"todos": "- [ ] one"}, id="update_todo"),
    pytest.param("WebFetch", {"url": "https://example.com/docs"}, id="web_fetch"),
    pytest.param("skill", {"skill": "caveman"}, id="skill"),
    pytest.param(
        "semantic_code_search",
        {"query": "main", "repo": "octocat/hello-world"},
        id="semantic_code_search",
    ),
    pytest.param(
        "fetch_copilot_cli_documentation", {"query": "hooks"}, id="documentation"
    ),
    pytest.param(
        "write_agent", {"agent_id": "a1", "message": "go on"}, id="write_agent"
    ),
    pytest.param("read_agent", {"agent_id": "a1"}, id="read_agent"),
    pytest.param("list_agents", {}, id="list_agents"),
    pytest.param(
        "Agent",
        {
            "agent_type": "coder",
            "description": "probe coder",
            "mode": "sync",
            "name": "probe-coder",
            "prompt": "Edit the file named in the plan.",
        },
        id="task",
    ),
)


@pytest.mark.parametrize(("tool", "tool_input"), NO_DECISION_TOOLS)
def test_tools_with_no_command_path_or_code_get_no_decision(
    tmp_path: Path, tool: str, tool_input: dict
) -> None:
    assert_outcomes(_payload(tool, tool_input), tmp_path, lambda c: ALLOW)


# T4: the workflow tools run JavaScript outside the hooks; denied by name, on
# the Copilot client only.
WORKFLOW_TOOLS = (
    pytest.param("run_dynamic_workflow", {"name": "probe-wf", "args": None}, id="run"),
    pytest.param("dynamic_workflows_manage", {"operation": "list"}, id="manage-list"),
    pytest.param(
        "dynamic_workflows_manage",
        {
            "operation": "author",
            "meta": {"name": "probe-wf", "description": "x", "phases": []},
            "run": "async ({ args, log }) => 'done'",
        },
        id="manage-author",
    ),
)


@pytest.mark.parametrize(("tool", "tool_input"), WORKFLOW_TOOLS)
@pytest.mark.parametrize(
    "build",
    (
        pytest.param(_payload, id="pascal"),
        pytest.param(_camel_payload, id="camel"),
    ),
)
def test_the_workflow_tools_are_denied_by_name_on_the_copilot_client_only(
    tmp_path: Path,
    build: Callable[[str, object], dict],
    tool: str,
    tool_input: dict,
) -> None:
    assert_outcomes(
        build(tool, tool_input),
        tmp_path,
        lambda c: DENY if c == "github-copilot" else ALLOW,
    )


def test_the_workflow_tool_deny_names_the_tool_in_its_reason(tmp_path: Path) -> None:
    process = _run_protect_files(
        _payload("run_dynamic_workflow", {"name": "probe-wf"}),
        tmp_path,
        "github-copilot",
    )

    assert process.returncode == 0, process.stderr
    body = json.loads(process.stdout)
    reason = body.get("hookSpecificOutput", body)["permissionDecisionReason"]
    assert "run_dynamic_workflow" in reason
