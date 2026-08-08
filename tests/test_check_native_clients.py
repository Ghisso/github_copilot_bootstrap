"""Offline adversarial tests for the opt-in native-client acceptance runner."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_native_clients as native  # noqa: E402


def observation() -> dict[str, bool]:
    return {field: True for field in native.SENTINEL_FIELDS}


def events(value: dict[str, Any]) -> str:
    return json.dumps({"type": "task.completed", "structured_output": value})


def complete_roles() -> list[dict[str, str]]:
    return [
        {"role": name, "type": role_type, "model": model, "reasoning_effort": effort}
        for name, (role_type, model, effort) in native.CODEX_ROLES.items()
    ]


def owned_workspace(root: Path) -> tuple[Path, Path, Path]:
    workspace = root / "native-client-probe-test"
    workspace.mkdir()
    (workspace / native.WORKSPACE_MARKER).write_text(
        native.WORKSPACE_MARKER_CONTENT, encoding="utf-8"
    )
    control, candidate = workspace / "control", workspace / "candidate"
    control.mkdir()
    candidate.mkdir()
    return workspace, control, candidate


def test_claude_schema_is_inline_json_not_a_path(tmp_path: Path) -> None:
    schema = native.observation_schema()
    command = native.claude_command("claude", tmp_path, schema)
    schema_arg = command[command.index("--json-schema") + 1]

    # Inline, not a path — but without `$schema`, which Claude cannot resolve.
    assert json.loads(schema_arg) == {
        key: value for key, value in schema.items() if key != "$schema"
    }
    assert schema_arg != str(native.OBSERVATION_SCHEMA)
    assert "--no-session-persistence" in command
    assert "--strict-mcp-config" in command
    assert command[command.index("--permission-mode") + 1] == "dontAsk"
    assert command[command.index("--disallowedTools") + 1] == "Edit,Write,Bash,mcp__*"


def test_malformed_envelopes_partial_extra_and_wrong_types_fail_closed() -> None:
    assert native.parse_jsonl("not-json") is None
    assert (
        native.parse_observation(native.parse_jsonl(events({"root_instruction": True})))
        is None
    )
    extra = observation() | {"leak": "prompt"}
    assert native.parse_observation(native.parse_jsonl(events(extra))) is None
    wrong_type = observation() | {"hooks": 1}
    assert native.parse_observation(native.parse_jsonl(events(wrong_type))) is None
    two = native.parse_jsonl(events(observation()) + "\n" + events(observation()))
    assert native.parse_observation(two) is None


def test_role_metadata_only_comes_from_agent_or_thread_events() -> None:
    prose = {
        "type": "task.completed",
        "structured_output": {"role_metadata": complete_roles()},
    }
    assert native.event_role_records([prose]) == []
    event = {"type": "agent.started", "agent": complete_roles()[0]}
    assert native.event_role_records([event]) == [complete_roles()[0]]


def test_role_matrix_requires_exact_six_unique_well_formed_records() -> None:
    roles = complete_roles()
    assert native.valid_role_matrix(roles)
    assert not native.valid_role_matrix(roles[:-1])
    assert not native.valid_role_matrix([*roles[:-1], roles[0]])
    extra = [
        *roles,
        {"role": "other", "type": "other", "model": "x", "reasoning_effort": "low"},
    ]
    assert not native.valid_role_matrix(extra)
    malformed = [
        *roles[:-1],
        {"role": "verifier", "type": "verifier", "model": "gpt-5.6-luna"},
    ]
    assert not native.valid_role_matrix(malformed)


@pytest.mark.parametrize("require,status", [(False, native.WARN), (True, native.FAIL)])
def test_missing_client_and_require_semantics(
    monkeypatch: pytest.MonkeyPatch, require: bool, status: str
) -> None:
    monkeypatch.setattr(native.shutil, "which", lambda _client: None)
    result = native.probe_client("claude", require=require, timeout=1)
    assert result["status"] == status
    assert result["checks"][0]["evidence"] == native.EVIDENCE_UNAVAILABLE


def test_timeout_and_untrusted_preflight_are_redacted(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace, _control, _candidate = owned_workspace(tmp_path)
    monkeypatch.setattr(native.shutil, "which", lambda _client: "codex")
    monkeypatch.setattr(native, "run_process", lambda *_args, **_kwargs: None)
    result = native.probe_client("codex", require=False, timeout=1, workspace=workspace)
    assert result == native.unavailable_result("codex", "untrusted", False)
    assert "secret" not in json.dumps(result)


def test_commands_are_least_privilege_and_no_bypass(tmp_path: Path) -> None:
    command = native.codex_command("codex", tmp_path, tmp_path / "schema.json")
    assert "--ephemeral" in command
    assert command[command.index("--sandbox") + 1] == "read-only"
    assert 'approval_policy="never"' in command
    assert "mcp_servers={}" in command
    assert 'web_search="disabled"' in command
    assert not any("dangerously" in item or "yolo" in item for item in command)
    env = native.minimal_environment(tmp_path)
    assert set(env) <= {
        "PATH",
        "HOME",
        "CODEX_HOME",
        "CLAUDE_CONFIG_DIR",
        "LANG",
        "LC_ALL",
        "TMPDIR",
        "TEMP",
        "TMP",
        "NO_COLOR",
    }


def test_successful_probe_uses_control_and_candidate_separate_invocations(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace, control, candidate = owned_workspace(tmp_path)
    monkeypatch.setattr(native.shutil, "which", lambda _client: "codex")
    calls: list[list[str]] = []

    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        return subprocess.CompletedProcess(
            command, 0, events(observation()), "private output"
        )

    monkeypatch.setattr(native, "run_process", run)
    result = native.probe_client("codex", require=False, timeout=1, workspace=workspace)

    assert result["status"] == native.WARN
    assert len(calls) == 3  # auth preflight + control + candidate
    assert "-C" in calls[1] and str(control) in calls[1]
    assert "-C" in calls[2] and str(candidate) in calls[2]
    assert (
        native.check("candidate_sentinel_parity", native.PASS, native.EVIDENCE_SENTINEL)
        in result["checks"]
    )
    assert (
        native.check("codex_role_matrix", native.WARN, native.EVIDENCE_UNEXERCISED)
        in result["checks"]
    )
    assert (
        native.check("compact_resume", native.WARN, native.EVIDENCE_UNEXERCISED)
        in result["checks"]
    )
    assert "private output" not in json.dumps(native.build_report([result]))

    required = native.probe_client(
        "codex", require=True, timeout=1, workspace=workspace
    )
    assert (
        required["status"] == native.FAIL
    )  # unexercised resume/role evidence is required


def test_native_event_schema_drift_and_partial_roles_fail() -> None:
    role_events = [
        {"type": "agent.started", "agent": role} for role in complete_roles()
    ]
    assert native.valid_role_matrix(native.event_role_records(role_events))
    assert not native.valid_role_matrix(native.event_role_records(role_events[:-1]))


@pytest.mark.parametrize(
    "candidate_output,expected_check",
    [
        (
            events({field: False for field in native.SENTINEL_FIELDS}),
            "candidate_sentinel_parity",
        ),
        (events({"root_instruction": True}), "candidate_result_schema"),
    ],
)
def test_candidate_requires_valid_sentinel_parity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    candidate_output: str,
    expected_check: str,
) -> None:
    workspace, _control, _candidate = owned_workspace(tmp_path)
    monkeypatch.setattr(native.shutil, "which", lambda _client: "codex")
    calls = 0

    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        output = candidate_output if calls == 3 else events(observation())
        return subprocess.CompletedProcess(command, 0, output, "")

    monkeypatch.setattr(native, "run_process", run)

    result = native.probe_client("codex", require=False, timeout=1, workspace=workspace)

    assert result["status"] == native.FAIL
    assert any(
        item["id"] == expected_check and item["status"] == native.FAIL
        for item in result["checks"]
    )


def test_all_clients_prioritizes_codex(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(
        native,
        "probe_client",
        lambda client, **_kwargs: _record_client(seen, client),
    )
    monkeypatch.setattr(
        sys, "argv", ["check_native_clients.py", "--client", "all", "--json"]
    )

    assert native.main() == 0
    assert seen == ["codex", "claude"]


def test_prepare_only_creates_marker_owned_persistent_workspace(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace = tmp_path / "native-client-probe-prepared"

    def prepare(root: Path, _timeout: int) -> tuple[Path, Path]:
        control, candidate = root / "control", root / "candidate"
        control.mkdir()
        candidate.mkdir()
        return control, candidate

    monkeypatch.setattr(native, "prepare_variants", prepare)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "check_native_clients.py",
            "--workspace",
            str(workspace),
            "--prepare-only",
            "--json",
        ],
    )

    assert native.main() == 0
    assert workspace.is_dir()
    assert (workspace / native.WORKSPACE_MARKER).read_text(
        encoding="utf-8"
    ) == native.WORKSPACE_MARKER_CONTENT
    assert native.persistent_variants(workspace) == (
        workspace / "control",
        workspace / "candidate",
    )


def test_workspace_refuses_unmarked_or_broad_paths(tmp_path: Path) -> None:
    unmarked = tmp_path / "native-client-probe-unmarked"
    unmarked.mkdir()
    (unmarked / "keep.txt").write_text("user data", encoding="utf-8")

    assert not native.prepare_workspace(unmarked, 1)
    assert (unmarked / "keep.txt").read_text(encoding="utf-8") == "user data"
    assert native.safe_workspace(Path("/")) is None
    assert native.safe_workspace(native.REPO_ROOT / "native-client-probe") is None


def test_workspace_reuse_refreshes_only_owned_children(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    workspace, control, candidate = owned_workspace(tmp_path)
    (workspace / "generated").mkdir()
    (workspace / "generated" / "keep.txt").write_text("owned", encoding="utf-8")
    removed: list[Path] = []
    original_rmtree = native.shutil.rmtree

    def rmtree(path: Path) -> None:
        removed.append(path)
        original_rmtree(path)

    def prepare(root: Path, _timeout: int) -> tuple[Path, Path]:
        fresh_control, fresh_candidate = root / "control", root / "candidate"
        fresh_control.mkdir()
        fresh_candidate.mkdir()
        return fresh_control, fresh_candidate

    monkeypatch.setattr(native.shutil, "rmtree", rmtree)
    monkeypatch.setattr(native, "prepare_variants", prepare)

    assert native.prepare_workspace(workspace, 1)
    assert workspace.is_dir() and native.marker_owned(workspace)
    assert set(removed) == {control, candidate}
    assert (workspace / "generated" / "keep.txt").read_text(encoding="utf-8") == "owned"


def _record_client(seen: list[str], client: str) -> dict[str, Any]:
    seen.append(client)
    return {"client": client, "status": native.PASS, "checks": []}


# --- Phase J: regressions from the first real native run -------------------
# Shapes below are copied from actual client output: Codex 0.147.0 and
# Claude Code 2.1.226 against a trusted, authenticated workspace.


def test_codex_agent_message_json_text_is_parsed() -> None:
    """Codex returns the schema answer as JSON *text*, not a nested object."""
    event = {
        "type": "item.completed",
        "item": {
            "id": "item_2",
            "type": "agent_message",
            "text": json.dumps(
                {
                    "root_instruction": True,
                    "scoped_instruction": False,
                    "workflow_contract": True,
                    "hooks": True,
                }
            ),
        },
    }
    parsed = native.parse_observation([event])
    assert parsed == {
        "root_instruction": True,
        "scoped_instruction": False,
        "workflow_contract": True,
        "hooks": True,
    }


def test_non_observation_text_is_not_mistaken_for_a_result() -> None:
    """Prose and unrelated JSON text must not satisfy the sentinel."""
    for text in ("done", "[1, 2, 3]", json.dumps({"root_instruction": True})):
        event = {
            "type": "item.completed",
            "item": {"type": "agent_message", "text": text},
        }
        assert native.parse_observation([event]) is None


def test_claude_prompt_survives_variadic_disallowed_tools() -> None:
    """`--disallowedTools` is variadic; the prompt must not be consumed by it."""
    command = native.claude_command("claude", Path("/tmp/consumer"), {"type": "object"})
    assert command[-1] == native.probe_prompt("claude")
    assert "--" in command
    assert command.index("--") == len(command) - 2
    assert command.index("--") > command.index("--disallowedTools")


def test_nonzero_exit_is_not_reported_as_untrusted() -> None:
    """An argv/auth/version failure must not assert anything about trust."""
    result = native.unavailable_result("claude", "invocation_failed", False)
    assert result["status"] == native.WARN
    assert result["checks"][0]["id"] == "claude_invocation_failed"
    assert "untrusted" not in result["checks"][0]["id"]


def test_claude_inline_schema_drops_unresolvable_meta_schema_key() -> None:
    """Claude rejects the whole schema if it cannot resolve `$schema`."""
    schema = native.observation_schema()
    assert "$schema" in schema, "canonical file should keep the meta-schema key"
    command = native.claude_command("claude", Path("/tmp/consumer"), schema)
    inline = json.loads(command[command.index("--json-schema") + 1])
    assert "$schema" not in inline
    assert inline["required"] == list(native.SENTINEL_FIELDS)
