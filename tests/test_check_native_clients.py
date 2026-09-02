"""Offline adversarial tests for the opt-in native-client acceptance runner."""

from __future__ import annotations

import json
import stat
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_native_clients as native  # noqa: E402


EXPECTED_CURRENT_CODEX_ROLES = {
    "orchestrator": ("orchestrator", "gpt-5.6-sol", "xhigh"),
    "planner": ("planner", "gpt-5.6-sol", "xhigh"),
    "coder": ("coder", "gpt-5.6-terra", "high"),
    "reviewer": ("reviewer", "gpt-5.6-sol", "high"),
    "documenter": ("documenter", "gpt-5.6-luna", "medium"),
    "luna_coder": ("coder", "gpt-5.6-luna", "xhigh"),
    "sol_coder": ("coder", "gpt-5.6-sol", "xhigh"),
}


def observation() -> dict[str, bool]:
    return {field: True for field in native.SENTINEL_FIELDS}


def events(value: dict[str, Any]) -> str:
    return json.dumps({"type": "task.completed", "structured_output": value})


def workload_observation(workload: str = "micro-plan") -> dict[str, Any]:
    return {
        "checklist": {
            "scope": True,
            "artifacts": True,
            "constraints": True,
            "verification": True,
        },
        "artifacts": list(native.FROZEN_PLANNER_WORKLOADS[workload]["artifacts"]),
        "invented_surfaces": [],
        "duplicated_discovery": False,
        "scope_expansion": [],
    }


def role_records(
    roles: dict[str, tuple[str, str, str]] = native.CODEX_ROLES,
) -> list[dict[str, str]]:
    return [
        {"role": name, "type": role_type, "model": model, "reasoning_effort": effort}
        for name, (role_type, model, effort) in roles.items()
    ]


def complete_roles() -> list[dict[str, str]]:
    return role_records()


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


def test_role_matrix_requires_exact_seven_unique_well_formed_records() -> None:
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
        {"role": "documenter", "type": "documenter", "model": "gpt-5.6-luna"},
    ]
    assert not native.valid_role_matrix(malformed)


def test_native_role_matrix_uses_the_calibrated_codex_planner_tier() -> None:
    """Current probes use seven roles while dated evidence remains universal-six."""
    assert native.CODEX_ROLES == EXPECTED_CURRENT_CODEX_ROLES
    assert native.valid_role_matrix(role_records(EXPECTED_CURRENT_CODEX_ROLES))
    assert set(native.CODEX_CURRENT_UNIVERSAL_ROLES) == {
        "orchestrator",
        "planner",
        "coder",
        "reviewer",
        "documenter",
    }
    assert set(native.CODEX_HISTORICAL_UNIVERSAL_ROLES) == {
        *native.CODEX_CURRENT_UNIVERSAL_ROLES,
        "verifier",
    }
    assert native.CODEX_ONLY_ROLES == {
        "luna_coder": ("coder", "gpt-5.6-luna", "xhigh"),
        "sol_coder": ("coder", "gpt-5.6-sol", "xhigh"),
    }
    assert set(native.CODEX_ROLES) == {
        *native.CODEX_CURRENT_UNIVERSAL_ROLES,
        *native.CODEX_ONLY_ROLES,
    }
    assert native.CODEX_ROLES["planner"] == ("planner", "gpt-5.6-sol", "xhigh")
    assert native.valid_universal_role_matrix(
        role_records(native.CODEX_HISTORICAL_UNIVERSAL_ROLES)
    )
    assert not native.valid_role_matrix(
        role_records(native.CODEX_HISTORICAL_UNIVERSAL_ROLES)
    )
    for role in native.CODEX_CURRENT_UNIVERSAL_ROLES:
        drifted_roles = dict(EXPECTED_CURRENT_CODEX_ROLES)
        role_type, _model, effort = drifted_roles[role]
        drifted_roles[role] = (role_type, "wrong-model", effort)
        assert not native.valid_role_matrix(role_records(drifted_roles))


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


def test_client_runtime_is_marker_owned_and_links_only_existing_auth(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Native state is writable outside the read-only generated consumer."""
    source = tmp_path / "existing-codex"
    source.mkdir()
    credential = source / "auth.json"
    credential.write_text("credential", encoding="utf-8")
    monkeypatch.setenv("CODEX_HOME", str(source))
    runtime = native.client_runtime_root(tmp_path, "codex", "control")

    assert native.prepare_client_runtime(runtime, "codex")
    linked = runtime / "codex" / "auth.json"
    assert linked.is_symlink()
    assert linked.resolve() == credential
    assert (runtime / "home").is_dir()
    env = native.minimal_environment(tmp_path, client="codex", runtime_root=runtime)
    assert env["HOME"] == str(runtime / "home")
    assert env["CODEX_HOME"] == str(runtime / "codex")
    assert env["XDG_STATE_HOME"] == str(runtime / "xdg-state")
    assert {env[name] for name in ("TMPDIR", "TEMP", "TMP")} == {str(runtime / "tmp")}
    assert str(source) not in env.values()


def test_runtime_temp_is_cleared_for_each_invocation(tmp_path: Path) -> None:
    """Client temporary files cannot persist in the workspace between invocations."""
    workspace, _control, _candidate = owned_workspace(tmp_path)
    runtime = native.client_runtime_root(workspace, "codex", "control")

    assert native.prepare_client_runtime(runtime, "codex")
    stale = runtime / "tmp" / "previous-run.tmp"
    stale.write_text("temporary", encoding="utf-8")
    assert native.prepare_client_runtime(runtime, "codex")

    env = native.minimal_environment(workspace, client="codex", runtime_root=runtime)
    assert not stale.exists()
    assert {env[name] for name in ("TMPDIR", "TEMP", "TMP")} == {str(runtime / "tmp")}
    assert not (workspace / "previous-run.tmp").exists()


def test_workspace_cleanup_unlinks_runtime_credentials_without_touching_target(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Removing a marker-owned runtime must not chmod its external credential link."""
    workspace, _control, _candidate = owned_workspace(tmp_path)
    source = tmp_path / "external-codex"
    source.mkdir()
    credential = source / "auth.json"
    credential.write_text("credential", encoding="utf-8")
    credential.chmod(0o400)
    credential_mode = stat.S_IMODE(credential.stat().st_mode)
    monkeypatch.setenv("CODEX_HOME", str(source))
    runtime = native.client_runtime_root(workspace, "codex", "control")
    assert native.prepare_client_runtime(runtime, "codex")
    assert (runtime / "codex" / "auth.json").is_symlink()

    def prepare(root: Path, _timeout: int) -> tuple[Path, Path]:
        control, candidate = root / "control", root / "candidate"
        control.mkdir()
        candidate.mkdir()
        return control, candidate

    monkeypatch.setattr(native, "prepare_variants", prepare)
    assert native.prepare_workspace(workspace, 1)

    assert credential.read_text(encoding="utf-8") == "credential"
    assert stat.S_IMODE(credential.stat().st_mode) == credential_mode
    assert not runtime.exists()


def test_frozen_workload_commands_preserve_read_only_execution(tmp_path: Path) -> None:
    """Planner calibration uses fixed prompts and the existing read-only clients."""
    schema = tmp_path / "schema.json"
    codex = native.codex_workload_command("codex", tmp_path, schema, "micro-plan")
    claude = native.claude_workload_command(
        "claude", native.PLANNER_WORKLOAD_SCHEMA, "bounded-full-plan"
    )
    micro_prompt = native.planner_workload_prompt("micro-plan")
    full_prompt = native.planner_workload_prompt("bounded-full-plan")

    assert set(native.FROZEN_PLANNER_WORKLOADS) == {"micro-plan", "bounded-full-plan"}
    assert codex[codex.index("--sandbox") + 1] == "read-only"
    assert 'model_reasoning_effort="xhigh"' in codex
    assert codex[codex.index("--model") + 1] == "gpt-5.6-sol"
    assert codex[-2:] == ["--", micro_prompt]
    assert claude[claude.index("--agent") + 1] == "planner"
    assert "Edit,Write,Bash,mcp__*" in claude
    assert micro_prompt.startswith("--mode micro-plan\n")
    assert full_prompt.startswith("--mode full-plan\n")
    for prompt in (micro_prompt, full_prompt):
        assert "only `checklist`, `artifacts`, `invented_surfaces`, " in prompt
        assert "Do not include `plan`" in prompt
        assert "do not use `exact_artifacts`" in prompt
        assert "MUST be the JSON boolean `true` or `false`" in prompt
        assert "never a string, array, or object" in prompt


def test_workload_metrics_are_aggregate_and_keep_unobservable_fields_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Frozen workload output records only bounded metrics, not client transcripts."""
    workspace, control, _candidate = owned_workspace(tmp_path)
    monkeypatch.setattr(native.shutil, "which", lambda _client: "codex")
    output = events(workload_observation())

    def run(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        stdout = "codex-cli 0.147.0\n" if "--version" in command else output
        return subprocess.CompletedProcess(command, 0, stdout, "private output")

    monkeypatch.setattr(native, "run_process", run)
    result = native.planner_workload_result(
        "codex", "codex", workspace, control, "micro-plan", 1
    )

    assert result["status"] == native.PASS
    assert result["checklist_completed"] == result["checklist_required"] == 4
    assert result["artifact_allowlist_match"] is True
    assert result["artifact_count"] == result["artifact_expected_count"] == 2
    assert result["invented_surface_count"] == result["scope_expansion_count"] == 0
    assert result["duplicated_discovery"] is False
    assert result["tool_volume"] is result["unique_files_read"] is None
    assert result["first_activity_seconds"] is None
    assert result["largest_observable_gap_seconds"] is None
    assert "private output" not in json.dumps(result)


def test_workload_schema_fails_closed() -> None:
    """No final prose becomes fabricated benchmark data."""
    assert native.parse_workload_observation(native.parse_jsonl("not-json")) is None


def test_workload_contract_rejects_each_adversarial_self_audit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Only the complete frozen self-audit can turn a workload into a PASS."""
    workspace, control, _candidate = owned_workspace(tmp_path)
    missing_auth = tmp_path / "missing-auth.json"
    monkeypatch.setattr(native, "client_auth_source", lambda _client: missing_auth)
    cases: list[tuple[str, dict[str, Any], int]] = []

    incomplete = workload_observation()
    incomplete["checklist"]["scope"] = False
    cases.append(("checklist_incomplete", incomplete, 2))
    extra_artifact = workload_observation()
    extra_artifact["artifacts"].append(".claude/extra.md")
    cases.append(("artifact_allowlist_mismatch", extra_artifact, 3))
    missing_artifact = workload_observation()
    missing_artifact["artifacts"].pop()
    cases.append(("artifact_allowlist_mismatch", missing_artifact, 1))
    invented_surface = workload_observation()
    invented_surface["invented_surfaces"] = ["shared/agents/new-agent.yaml"]
    cases.append(("invented_surfaces", invented_surface, 2))
    duplicated = workload_observation()
    duplicated["duplicated_discovery"] = True
    cases.append(("duplicated_discovery", duplicated, 2))
    expanded_scope = workload_observation()
    expanded_scope["scope_expansion"] = ["docs/new-surface.md"]
    cases.append(("scope_expansion", expanded_scope, 2))

    for failure, observation, artifact_count in cases:

        def run(
            command: list[str], **_kwargs: object
        ) -> subprocess.CompletedProcess[str]:
            return subprocess.CompletedProcess(command, 0, events(observation), "")

        monkeypatch.setattr(native, "run_process", run)
        result = native.planner_workload_result(
            "codex", "codex", workspace, control, "micro-plan", 1
        )

        assert result["status"] == native.FAIL
        assert result["reason"] == "workload_contract"
        assert result["contract_failures"] == [failure]
        assert result["artifact_count"] == artifact_count
        assert result["artifact_expected_count"] == 2


def test_workload_summary_matches_workload_statuses() -> None:
    """The report summary must count workload PASS/WARN/FAIL outcomes exactly."""
    workloads = [
        {"client": "codex", "workload": "micro-plan", "status": native.PASS},
        {"client": "claude", "workload": "micro-plan", "status": native.FAIL},
        {
            "client": "claude",
            "workload": "bounded-full-plan",
            "status": native.WARN,
        },
    ]

    report = native.build_report([], workloads)

    assert report["planner_workload_summary"] == {"pass": 1, "warn": 1, "fail": 1}


def test_claude_aggregate_result_accepts_one_fenced_workload_json() -> None:
    """Claude's print JSON envelope carries the structured workload result in `result`."""
    observation = {
        "checklist": {
            "scope": True,
            "artifacts": True,
            "constraints": True,
            "verification": True,
        },
        "artifacts": [".claude/agents/planner.md"],
        "invented_surfaces": [],
        "duplicated_discovery": False,
        "scope_expansion": [],
    }
    envelope = {
        "type": "result",
        "subtype": "success",
        "result": f"```json\n{json.dumps(observation)}\n```",
    }

    assert native.parse_workload_observation([envelope]) == observation
    assert "```" not in json.dumps(native.parse_workload_observation([envelope]))


def test_claude_workload_result_rejects_malformed_or_ambiguous_aggregate_json() -> None:
    """A malformed fence or duplicate aggregate result cannot satisfy the workload."""
    observation = {
        "checklist": {
            "scope": True,
            "artifacts": True,
            "constraints": True,
            "verification": True,
        },
        "artifacts": [],
        "invented_surfaces": [],
        "duplicated_discovery": False,
        "scope_expansion": [],
    }
    malformed = {"type": "result", "result": "```json\n{not json}\n```"}
    ambiguous = {
        "type": "result",
        "result": json.dumps(observation),
        "structured_output": json.dumps(observation),
    }
    extra_plan = observation | {"plan": "unexpected"}
    alternate_checklist = observation | {
        "checklist": {
            "scope": True,
            "artifacts": True,
            "constraints": True,
            "verification": True,
            "exact_artifacts": True,
        }
    }
    non_boolean_checklist = observation | {
        "checklist": {
            "scope": "bounded",
            "artifacts": [".claude/agents/planner.md"],
            "constraints": ["read-only"],
            "verification": "uv run python scripts/validate_targets.py",
        }
    }

    assert native.parse_workload_observation([malformed]) is None
    assert native.parse_workload_observation([ambiguous]) is None
    assert (
        native.parse_workload_observation([{"result": json.dumps(extra_plan)}]) is None
    )
    assert (
        native.parse_workload_observation([{"result": json.dumps(alternate_checklist)}])
        is None
    )
    assert (
        native.parse_workload_observation(
            [{"result": json.dumps(non_boolean_checklist)}]
        )
        is None
    )


def test_unprepared_workloads_stay_visible_and_require_promotes_them() -> None:
    """A missing trusted workspace cannot masquerade as an unrun success."""
    optional = native.run_planner_workloads(
        "codex", require=False, timeout=1, workspace=None
    )
    required = native.run_planner_workloads(
        "codex", require=True, timeout=1, workspace=None
    )

    assert len(optional) == len(required) == 2
    assert {item["status"] for item in optional} == {native.WARN}
    assert {item["status"] for item in required} == {native.FAIL}


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
    runtime = workspace / native.RUNTIME_DIRECTORY
    runtime.mkdir()
    (runtime / "state.txt").write_text("owned", encoding="utf-8")
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
    assert set(removed) == {control, candidate, runtime}
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


# --- Phase K: per-client scoped-instruction semantics ----------------------


def test_scoped_instruction_question_differs_per_client() -> None:
    """Codex scopes by directory; this target ships no nested AGENTS.md."""
    codex_question = native.scoped_instruction_question("codex")
    claude_question = native.scoped_instruction_question("claude")
    assert codex_question != claude_question
    assert "AGENTS.md" in codex_question
    assert ".claude/instructions/" in codex_question
    assert ".claude/rules/" in claude_question
    assert "paths:" in claude_question


def test_no_prompt_claims_a_surface_the_target_does_not_generate() -> None:
    """Codex must never be asked about nested AGENTS.md scoping."""
    codex_prompt = native.probe_prompt("codex")
    assert ".claude/rules/" not in codex_prompt
    assert "nested" not in codex_prompt.lower()
    for client in ("codex", "claude"):
        assert native.scoped_instruction_question(client) in native.probe_prompt(client)


def test_default_timeout_allows_consecutive_control_and_candidate() -> None:
    """120s timed Codex out mid-matrix; the default must cover both runs."""
    assert native.TIMEOUT_SECONDS >= 300


# --- Phase L: spawn capability, from recorded Codex 0.147.0 output ---------


def collab_wait_event(status: str = "completed") -> dict[str, Any]:
    """Verbatim shape captured from Codex 0.147.0 when no spawn occurs."""
    return {
        "type": f"item.{status}",
        "item": {
            "id": "item_1",
            "type": "collab_tool_call",
            "tool": "wait",
            "sender_thread_id": "019fe23f-469a-77b1-a3d1-4532aa24cb5e",
            "receiver_thread_ids": [],
            "prompt": None,
            "agents_states": {},
            "status": status,
        },
    }


def test_collaboration_without_spawn_is_detected() -> None:
    assert native.collaboration_attempted_without_spawn([collab_wait_event()])


def test_no_collaboration_tools_is_not_spawn_unsupported() -> None:
    """Absent collaboration calls means unexercised, not an unsupported spawn."""
    assert not native.collaboration_attempted_without_spawn([])
    assert not native.collaboration_attempted_without_spawn(None)
    plain = {"type": "item.completed", "item": {"type": "agent_message", "text": "ok"}}
    assert not native.collaboration_attempted_without_spawn([plain])


def test_a_real_spawn_is_not_reported_as_unsupported() -> None:
    """Any receiver thread or agent state means spawning did happen."""
    spawned = collab_wait_event()
    spawned["item"]["receiver_thread_ids"] = ["019fe000-0000-0000-0000-000000000001"]
    assert not native.collaboration_attempted_without_spawn([spawned])


def test_spawn_unsupported_is_distinct_from_unexercised() -> None:
    """The removal gate must not read as 'simply never run'."""
    assert native.EVIDENCE_SPAWN_UNSUPPORTED != native.EVIDENCE_UNEXERCISED
