"""Offline tests for the opt-in Copilot runtime probe.

None of these tests starts Node or the Copilot runtime, and none makes a model
call. Synthetic events copy the shapes recorded in the evidence folder
`.claude/explorations/2026-11-17_copilot-harness-migration-evidence/` (raw run
`outcomes-g-both.txt`). Expected values come from the plan's baseline table,
not from the probe's own output.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_copilot_runtime as probe  # noqa: E402

GITHUB_HOOKS = "file:///work/project/.github/hooks/hooks.json"
CLAUDE_SETTINGS = "file:///work/project/.claude/settings.json"
# The guard's reason for a workflow tool (row T4), with the tool's name in it.
WORKFLOW_REASON = (
    "Tool blocked by policy: {tool} runs workflow code that the pre-tool hooks "
    "cannot see"
)
# What the tool itself answers (seen in a real run), not a hook.
SQL_ATTACH = (
    'Error: Blocked SQL statement: "ATTACH" is not allowed for security reasons.'
)
SQL_VACUUM = (
    'Error: Blocked SQL statement: "VACUUM INTO" is not allowed for security reasons.'
)

# Plan step 3 table: the tool each scripted step uses, the deny reason (or the
# permission questions) the guards must give for it on a fresh install on `dev`.
EXPECTED_STEPS: dict[str, dict[str, Any]] = {
    "deny-git-reset": {
        "tool": "bash",
        "reason": "Blocked dangerous git operation: git reset --hard",
    },
    "deny-force-push": {
        "tool": "bash",
        "reason": "Blocked dangerous git operation: force push",
    },
    "deny-secret-rm": {
        "tool": "bash",
        "reason": "Protected file blocked by policy: .env",
    },
    "deny-secret-view": {
        "tool": "view",
        "reason": "Protected file blocked by policy: .env",
    },
    "ask-vscode-settings": {"tool": "create", "questions": ("hook", "hook", "write")},
    "ask-agent-wrapper": {
        "tool": "edit",
        "questions": ("hook", "hook"),
        "success": False,
    },
    # `dev` has no commit, so git names the branch HEAD (as in the recorded run).
    "deny-branch": {
        "tool": "bash",
        "reason": "implementation branches must be created from dev; "
        "current branch is HEAD",
    },
    "deny-commit": {
        "tool": "bash",
        "reason": "commit gate failed for github-copilot: commits must happen on a "
        "<plan_name>_implementation branch, not HEAD",
    },
    "deny-pr": {
        "tool": "bash",
        "reason": "PR/push gate only allows implementation branches; "
        "current branch is HEAD",
    },
    "allow-plain-bash": {"tool": "bash"},
    "allow-plain-view": {"tool": "view", "questions": ("read",)},
    "allow-plain-create": {"tool": "create", "questions": ("write",)},
    "allow-plain-edit": {"tool": "edit", "questions": ("write",)},
    # Phase B steps (the Phase B plan, steps 6 and 7; shapes from a real run).
    "helper-start": {"tool": "bash", "questions": ("shell",)},
    "helper-read": {"tool": "read_bash"},
    "helper-list": {"tool": "list_bash"},
    "helper-stop": {"tool": "stop_bash"},
    "read-agent-file": {"tool": "view", "questions": ("read",)},
    "search-secret": {
        "tool": "grep",
        "reason": "Protected file blocked by policy: .env",
    },
    "search-glob": {"tool": "glob", "questions": ("read",)},
    "deny-workflow-run": {
        "tool": "run_dynamic_workflow",
        "reason": WORKFLOW_REASON.format(tool="run_dynamic_workflow"),
    },
    "deny-workflow-manage": {
        "tool": "dynamic_workflows_manage",
        "reason": WORKFLOW_REASON.format(tool="dynamic_workflows_manage"),
    },
    "sql-attach": {"tool": "sql", "success": False, "result": SQL_ATTACH},
    "sql-vacuum-into": {"tool": "sql", "success": False, "result": SQL_VACUUM},
    "subagent-start": {"tool": "task"},
    "child-git-reset": {
        "tool": "bash",
        "reason": "Blocked dangerous git operation: git reset --hard",
    },
    "child-store-attach": {
        "tool": "session_store_sql",
        "success": False,
        "result": SQL_ATTACH,
    },
}
# The steps the sub-agent plays; every other step is the main model's.
CHILD_STEP_LABELS = ("child-git-reset", "child-store-attach")
MAIN_STEP_LABELS = [label for label in EXPECTED_STEPS if label not in CHILD_STEP_LABELS]
# Plan step 7, session `codex-patch`: the five patch calls of the evidence scenario
# `sc5_codex_patch.json` (both hook sources ask twice), then an indented header.
EXPECTED_PATCH_STEPS: dict[str, dict[str, Any]] = {
    "patch-plain": {"tool": "apply_patch", "questions": ("write",)},
    "patch-secret": {
        "tool": "apply_patch",
        "reason": "Protected file blocked by policy: .env",
    },
    "patch-hook": {"tool": "apply_patch", "questions": ("hook", "hook")},
    # The server file is not in the temporary project, so the patch itself fails.
    "patch-server": {
        "tool": "apply_patch",
        "questions": ("hook", "hook"),
        "success": False,
    },
    "patch-agent": {"tool": "apply_patch", "questions": ("hook", "hook")},
    "patch-indented-hook": {"tool": "apply_patch", "questions": ("hook", "hook")},
}
EXPECTED_PATCH_CHECK_NAMES = [
    "patch-plain-allowed",
    "patch-secret-denied",
    "patch-hook-ask",
    "patch-server-ask",
    "patch-agent-ask",
    "patch-indented-hook-ask",
]
EXPECTED_CHECK_NAMES = [
    "hooks-untrusted",
    "hooks-sources",
    "hooks-subfolder",
    "mcp-none",
    "deny-git-reset",
    "deny-force-push",
    "deny-secret-rm",
    "deny-secret-view",
    "ask-vscode-settings",
    "ask-agent-wrapper",
    "deny-branch",
    "deny-commit",
    "deny-pr",
    "allow-plain",
    "helper-tools",
    "read-agent-file",
    "search-secret-denied",
    "search-glob-not-judged",
    "deny-workflow-run",
    "deny-workflow-manage",
    "sql-no-file-write",
    "subagent-deny-git-reset",
    "subagent-store-sql-refused",
]


def call_events(
    call_id: str,
    tool: str,
    *,
    reason: str | None = None,
    questions: Sequence[str] = (),
    success: bool | None = None,
    hooked: bool = True,
    result: str = "",
) -> list[dict[str, Any]]:
    """Events of one tool call, in the order the runtime emits them."""
    denied = reason is not None
    events: list[dict[str, Any]] = [
        {
            "type": "tool.execution_start",
            "data": {"toolCallId": call_id, "toolName": tool, "arguments": {}},
        }
    ]
    if hooked:
        invocation = f"invocation-{call_id}"
        end: dict[str, Any] = {
            "hookInvocationId": invocation,
            "hookType": "preToolUse",
            "success": True,
        }
        if denied:
            end["output"] = {call_id: f"Denied by preToolUse hook: {reason}"}
        events.append(
            {
                "type": "hook.start",
                "data": {
                    "hookInvocationId": invocation,
                    "hookType": "preToolUse",
                    "input": {"toolCalls": [{"id": call_id, "name": tool, "args": {}}]},
                },
            }
        )
        events.append({"type": "hook.end", "data": end})
    for kind in questions:
        events.append(
            {
                "type": "permission.requested",
                "data": {
                    "requestId": f"request-{call_id}-{kind}",
                    "permissionRequest": {"kind": kind, "toolCallId": call_id},
                },
            }
        )
    events.append(
        {
            "type": "tool.execution_complete",
            "data": {
                "toolCallId": call_id,
                "success": (not denied) if success is None else success,
                "result": {"content": result},
            },
        }
    )
    return events


def hook_row(definition: str, event: str = "preToolUse") -> dict[str, Any]:
    return {
        "id": f"hook:{definition}:{event}",
        "hookType": event,
        "origin": "repository",
        "enabled": True,
        "definitionFileUri": definition,
    }


def both_sources() -> dict[str, Any]:
    return {
        "hooks": {
            "hooks": [
                hook_row(GITHUB_HOOKS),
                hook_row(GITHUB_HOOKS, "sessionStart"),
                hook_row(CLAUDE_SETTINGS),
                hook_row(CLAUDE_SETTINGS, "postToolUse"),
            ],
            "warnings": [],
            "errors": [],
        },
        "mcp": {"servers": []},
    }


def build_record(
    steps: dict[str, dict[str, Any]] | None = None,
    discovery: dict[str, Any] | None = None,
    extra_events: Sequence[dict[str, Any]] = (),
    name: str = "main",
) -> probe.SessionRecord:
    """A record of a correct run, unless the caller passes wrong steps or discovery."""
    steps = EXPECTED_STEPS if steps is None else steps
    events: list[dict[str, Any]] = []
    step_calls: dict[str, str] = {}
    for number, (label, step) in enumerate(steps.items(), start=1):
        call_id = f"call_probe_{number}"
        step_calls[label] = call_id
        events += call_events(
            call_id,
            step["tool"],
            reason=step.get("reason"),
            questions=step.get("questions", ()),
            success=step.get("success"),
            hooked=step.get("hooked", True),
            result=step.get("result", ""),
        )
    events += list(extra_events)
    summary: dict[str, Any] = {
        "status": {"version": "1.0.108-0"},
        "stepCalls": step_calls,
        "discovery": discovery
        or {
            "untrusted": {"hooks": {"hooks": []}, "mcp": {"servers": []}},
            "trusted": both_sources(),
            "subfolder": both_sources(),
        },
        "firstRequestTools": [
            {
                "type": "function",
                "function": {
                    "name": "bash",
                    "parameters": {
                        "type": "object",
                        "properties": {"command": {}, "description": {}},
                    },
                },
            },
            {"type": "custom", "custom": {"name": "apply_patch"}},
        ],
        "mcpFileAfterSession": False,
        "errors": [],
    }
    return probe.SessionRecord(name=name, events=events, summary=summary)


def build_patch_record(
    steps: dict[str, dict[str, Any]] | None = None,
) -> probe.SessionRecord:
    """A record of a correct `codex-patch` run, unless the caller passes wrong steps."""
    steps = EXPECTED_PATCH_STEPS if steps is None else steps
    return build_record(steps, name="codex-patch")


def record_for(scenario: dict[str, object]) -> probe.SessionRecord:
    """The record of a correct run of the scenario a fake session was given."""
    if scenario["name"] == "codex-patch":
        return build_patch_record()
    return build_record()


def results_by_name(record: probe.SessionRecord) -> dict[str, probe.CheckResult]:
    return {r.name: r for r in probe.evaluate(record, probe.BASELINE_CHECKS)}


def patch_results_by_name(
    record: probe.SessionRecord,
) -> dict[str, probe.CheckResult]:
    return {r.name: r for r in probe.evaluate(record, probe.CODEX_PATCH_CHECKS)}


def make_runtime(
    folder: Path,
    *,
    node: bool = True,
    sdk: bool = True,
    version: str | None = "1.0.30-preview.0",
    mtime: int | None = None,
) -> Path:
    """A fake VS Code server folder; the modification time is set last."""
    folder.mkdir(parents=True)
    if node:
        (folder / "node").write_text("#!/bin/sh\n", encoding="utf-8")
    if sdk:
        sdk_root = folder / "node_modules" / "@github" / "copilot-sdk"
        (sdk_root / "dist").mkdir(parents=True)
        (sdk_root / "dist" / "index.js").write_text("export {};\n", encoding="utf-8")
        if version is not None:
            (sdk_root / "package.json").write_text(
                json.dumps({"version": version}), encoding="utf-8"
            )
    if mtime is not None:
        os.utime(folder, (mtime, mtime))
    return folder


NODE_PREAMBLE = (
    "import json, os, pathlib, sys, time\n"
    "config = json.load(open(sys.argv[2]))\n"
    "out = pathlib.Path(config['outDir'])\n"
)
# Fake `node` bodies. They get the arguments the real runner gets: the probe
# script and the config file.
WRITE_RECORD = (
    "(out / 'record.json').write_text(json.dumps({'status': {'version': '1.0.108-0'},"
    " 'modelCalls': 2, 'errors': ERRORS, 'config': config,"
    " 'seenArgs': sys.argv[1:2], 'seenCwd': os.getcwd(),"
    " 'seenEnv': sorted(k for k in os.environ if k.startswith(('CLAUDE', 'ANTHROPIC'))"
    " or k in ('GITHUB_TOKEN', 'GH_TOKEN', 'COPILOT_GITHUB_TOKEN')),"
    " 'discovery': DISCOVERY}))\n"
)
FINISHED_NODE = (
    "ERRORS = []\nDISCOVERY = {}\n"
    + WRITE_RECORD
    + "(out / 'events.jsonl').write_text("
    + "json.dumps({'type': 'session.idle', 'data': {}}) + '\\n{\"type\": \"tool.exec')\n"
)
ERRORS_NODE = (
    "ERRORS = ['send: Timeout waiting for session.idle', 'stop: already stopped']\n"
    "DISCOVERY = {}\n" + WRITE_RECORD
)
FAILING_NODE = "sys.stderr.write('boom: runtime did not start\\n')\nsys.exit(3)\n"
SILENT_NODE = "pass\n"
SLEEPING_NODE = "time.sleep(60)\n"
DISCOVERY_NODE = (
    "ERRORS = []\n"
    "DISCOVERY = {'hooks': {'hooks': []}, 'mcp': {'servers': []},"
    " 'instructions': {'sources': [{'label': 'AGENTS.md'}]},"
    " 'skills': {'skills': [{'name': 'ponytail'}]},"
    " 'agents': {'agents': [{'name': 'coder'}]}}\n" + WRITE_RECORD
)


def make_fake_node(folder: Path, body: str) -> probe.RuntimeInfo:
    """A VS Code server folder whose `node` is a Python script that runs `body`."""
    make_runtime(folder)
    node = folder / "node"
    node.write_text(f"#!{sys.executable}\n{NODE_PREAMBLE}{body}", encoding="utf-8")
    node.chmod(0o755)
    runtime = probe.find_runtime(folder)
    assert runtime is not None
    return runtime


def load_record(out: Path) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads((out / "record.json").read_text("utf-8"))
    return loaded


# --- runtime discovery -------------------------------------------------------


class TestFindRuntime:
    def test_picks_newest_complete_folder_and_skips_incomplete_ones(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))
        bin_dir = tmp_path / ".vscode-server" / "bin"
        make_runtime(bin_dir / "aaa-old", mtime=1_000)
        make_runtime(bin_dir / "bbb-no-node", node=False, mtime=3_000)
        make_runtime(bin_dir / "ccc-no-sdk", sdk=False, mtime=4_000)
        make_runtime(bin_dir / "ddd-newer", version="1.0.31", mtime=2_000)
        (bin_dir / "compatibilty-check").write_text("1", encoding="utf-8")

        found = probe.find_runtime(None)

        assert found is not None
        assert found.vscode_commit == "ddd-newer"
        assert found.sdk_version == "1.0.31"
        assert found.node == bin_dir / "ddd-newer" / "node"
        assert found.sdk_root == (
            bin_dir / "ddd-newer" / "node_modules" / "@github" / "copilot-sdk"
        )

    def test_vscode_bin_overrides_discovery(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))
        make_runtime(tmp_path / ".vscode-server" / "bin" / "newest", mtime=9_000)
        chosen = make_runtime(tmp_path / "elsewhere" / "desktop-1", mtime=1_000)

        found = probe.find_runtime(chosen)

        assert found is not None
        assert found.vscode_commit == "desktop-1"
        assert found.node == chosen / "node"

    def test_vscode_bin_without_both_files_finds_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))
        make_runtime(tmp_path / ".vscode-server" / "bin" / "newest")
        incomplete = make_runtime(tmp_path / "elsewhere" / "no-node", node=False)

        assert probe.find_runtime(incomplete) is None

    def test_missing_package_json_gives_unknown_sdk_version(
        self, tmp_path: Path
    ) -> None:
        folder = make_runtime(tmp_path / "commit", version=None)

        found = probe.find_runtime(folder)

        assert found is not None
        assert found.sdk_version == "unknown"

    def test_no_server_folder_finds_nothing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))

        assert probe.find_runtime(None) is None


class TestMainWithoutRuntime:
    def test_require_exits_1_with_a_fail_line(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))

        code = probe.main(["--require"])

        assert code == 1
        assert re.search(r"^FAIL ", capsys.readouterr().out, re.MULTILINE)

    def test_without_require_exits_0_with_a_warn_line(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))

        code = probe.main([])

        assert code == 0
        out = capsys.readouterr().out
        assert re.search(r"^WARN ", out, re.MULTILINE)
        assert "FAIL" not in out

    def test_format_option_does_not_exist(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        with pytest.raises(SystemExit) as raised:
            probe.main(["--format", "json"])

        assert raised.value.code == 2
        assert "unrecognized arguments" in capsys.readouterr().err


# --- runtime environment -----------------------------------------------------


def test_runtime_environment_drops_claude_anthropic_and_github_tokens() -> None:
    base = {
        "PATH": "/usr/bin:/bin",
        "HOME": "/home/someone",
        "CLAUDE_PROJECT_DIR": "/work/repo",
        "CLAUDECODE": "1",
        "CLAUDE_CODE_ENTRYPOINT": "cli",
        "ANTHROPIC_API_KEY": "sk-ant-example",
        "ANTHROPIC_BASE_URL": "https://example.invalid",
        "GH_TOKEN": "ghp_example",
        "GITHUB_TOKEN": "ghp_example",
        "COPILOT_GITHUB_TOKEN": "ghp_example",
        "LANG": "C.UTF-8",
    }

    env = probe.runtime_environment(base)

    assert env == {"PATH": "/usr/bin:/bin", "HOME": "/home/someone", "LANG": "C.UTF-8"}
    assert "CLAUDECODE" in base  # the input is not changed


# --- the temporary project ---------------------------------------------------


def test_prepare_project_installs_a_full_copy_without_mcp_json(
    tmp_path: Path,
) -> None:
    generated = REPO_ROOT / "dist" / "multi-agent"
    # Not vacuous: the shipped tree has a project MCP file for the builder to remove.
    assert (generated / ".mcp.json").is_file()

    project = probe.prepare_project(tmp_path)

    assert project.is_dir()
    assert project.parent == tmp_path
    assert not (project / ".mcp.json").exists()
    assert (project / ".github" / "hooks" / "hooks.json").is_file()
    assert (project / ".claude" / "settings.json").is_file()
    assert (project / ".github" / "agents" / "coder.agent.md").is_file()
    assert (project / "README.md").is_file()
    branch = subprocess.run(
        ["git", "-C", str(project), "symbolic-ref", "--short", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert branch.stdout.strip() == "dev"
    commits = subprocess.run(
        ["git", "-C", str(project), "rev-parse", "--verify", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert commits.returncode != 0  # no commit was made


def test_the_session_start_restore_hook_does_not_bring_back_mcp_json(
    tmp_path: Path,
) -> None:
    """Regression: the hook that restores root adapters re-created `.mcp.json`.

    `state-sync.sh pull` (a SessionStart hook) runs this script. With only
    `<project>/.mcp.json` deleted, it copied the file back from
    `.claude/bootstrap-root/` mid-session and the runtime started the project's
    MCP servers (`npx`, `uvx`), which reach the network.
    """
    project = probe.prepare_project(tmp_path)
    restore = project / ".claude" / "hooks" / "scripts" / "restore-root-adapters.sh"
    assert restore.is_file()

    done = subprocess.run(
        ["bash", str(restore)],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
    )

    assert done.returncode == 0, done.stderr
    assert not (project / ".mcp.json").exists()
    assert not (project / ".claude" / "bootstrap-root" / ".mcp.json").exists()
    manifest = (project / ".claude" / "bootstrap-ownership.env").read_text(
        encoding="utf-8"
    )
    assert "BOOTSTRAP_ROOT_PATH=.mcp.json" not in manifest
    # Other adapters are still restored by the same script.
    assert "BOOTSTRAP_ROOT_PATH=AGENTS.md" in manifest
    assert (project / "AGENTS.md").is_file()


# --- evaluate: tool-call checks ----------------------------------------------


def test_the_baseline_has_the_planned_checks_in_order() -> None:
    assert [check.name for check in probe.BASELINE_CHECKS] == EXPECTED_CHECK_NAMES


def test_a_correct_run_passes_every_check() -> None:
    results = probe.evaluate(build_record(), probe.BASELINE_CHECKS)

    assert [r.name for r in results] == EXPECTED_CHECK_NAMES
    assert [r.status for r in results] == [probe.PASS] * len(EXPECTED_CHECK_NAMES)


def test_the_scenario_has_one_scripted_step_per_expected_step() -> None:
    scenario = probe.baseline_scenario(Path("/work/project"))
    steps: list[dict[str, Any]] = scenario["steps"]  # type: ignore[assignment]
    child_steps: list[dict[str, Any]] = scenario["childSteps"][  # type: ignore[index]
        probe.CHILD_MARKER
    ]

    assert [step["label"] for step in steps] == MAIN_STEP_LABELS
    assert [step["label"] for step in child_steps] == list(CHILD_STEP_LABELS)
    assert {step["label"]: step["tool"] for step in steps + child_steps} == {
        label: expected["tool"] for label, expected in EXPECTED_STEPS.items()
    }
    assert scenario["model"] == "probe-model"


def test_the_sub_agent_is_started_with_the_marker_that_keys_its_steps() -> None:
    scenario = probe.baseline_scenario(Path("/work/project"))
    steps: list[dict[str, Any]] = scenario["steps"]  # type: ignore[assignment]

    task = next(step for step in steps if step["label"] == "subagent-start")

    assert task["tool"] == "task"
    assert probe.CHILD_MARKER == "PROBE-CHILD-general"
    assert probe.CHILD_MARKER in task["args"]["prompt"]
    assert task["args"]["agent_type"] == "general-purpose"


def test_the_helper_steps_start_an_async_shell_and_name_its_id() -> None:
    scenario = probe.baseline_scenario(Path("/work/project"))
    steps: dict[str, dict[str, Any]] = {
        step["label"]: step
        for step in scenario["steps"]  # type: ignore[attr-defined]
    }

    assert steps["helper-start"]["args"]["mode"] == "async"
    assert steps["helper-read"]["args"] == {"shellId": "0", "delay": 1}
    assert steps["helper-stop"]["args"] == {"shellId": "0"}
    assert steps["helper-list"]["args"] == {}


def test_the_search_steps_name_the_secret_file_and_a_glob_filter() -> None:
    scenario = probe.baseline_scenario(Path("/work/project"))
    steps: dict[str, dict[str, Any]] = {
        step["label"]: step
        for step in scenario["steps"]  # type: ignore[attr-defined]
    }

    assert steps["search-secret"]["tool"] == "grep"
    assert steps["search-secret"]["args"]["paths"] == [".env"]
    assert steps["search-glob"]["tool"] == "glob"
    assert steps["search-glob"]["args"]["pattern"] == ".env*"
    assert steps["read-agent-file"]["args"]["path"] == (
        "/work/project/.claude/agents/coder.md"
    )


def test_the_workflow_and_sql_steps_use_the_tool_names_the_guard_denies() -> None:
    scenario = probe.baseline_scenario(Path("/work/project"))
    steps: dict[str, dict[str, Any]] = {
        step["label"]: step
        for step in scenario["steps"]  # type: ignore[attr-defined]
    }

    assert steps["deny-workflow-run"]["tool"] == "run_dynamic_workflow"
    assert steps["deny-workflow-manage"]["tool"] == "dynamic_workflows_manage"
    assert "ATTACH DATABASE '/work/project/" in steps["sql-attach"]["args"]["query"]
    assert steps["sql-vacuum-into"]["args"]["query"].startswith("VACUUM INTO '")


# The evidence file raw/hook-inputs-patch-tool.txt holds these five payloads.
EVIDENCE_PATCHES = {
    "patch-plain": "*** Begin Patch\n*** Add File: probe-patch.txt\n+plain file\n*** End Patch\n",
    "patch-secret": "*** Begin Patch\n*** Add File: .env\n+SECRET=1\n*** End Patch\n",
    "patch-hook": "*** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n",
    "patch-server": "*** Begin Patch\n*** Update File: .mcp.json\n@@\n-{\n+{ \n*** End Patch\n",
    "patch-agent": "*** Begin Patch\n*** Delete File: .claude/agents/coder.md\n*** End Patch\n",
}


def test_the_patch_scenario_sends_the_five_evidence_patches_and_an_indented_one() -> (
    None
):
    scenario = probe.codex_patch_scenario(Path("/work/project"))
    steps: list[dict[str, Any]] = scenario["steps"]  # type: ignore[assignment]

    assert scenario["name"] == "codex-patch"
    assert scenario["model"] == "gpt-5.2-codex"
    assert [step["label"] for step in steps] == list(EXPECTED_PATCH_STEPS)
    assert {step["label"]: step["tool"] for step in steps} == dict.fromkeys(
        EXPECTED_PATCH_STEPS, "apply_patch"
    )
    # A free-form call carries its text as `input`, never as `args`.
    assert all(isinstance(step["input"], str) and "args" not in step for step in steps)
    inputs = {step["label"]: step["input"] for step in steps}
    assert {label: inputs[label] for label in EVIDENCE_PATCHES} == EVIDENCE_PATCHES
    indented = inputs["patch-indented-hook"].splitlines()
    assert indented[0] == "*** Begin Patch"
    assert indented[1] == "  *** Add File: .github/hooks/evil-indented.json"
    assert indented[-1] == "*** End Patch"


@pytest.mark.parametrize(
    ("check", "wrong_step"),
    [
        pytest.param(
            "deny-git-reset", {"tool": "bash"}, id="reset-not-denied-runs-instead"
        ),
        pytest.param(
            "deny-git-reset",
            {"tool": "bash", "reason": "Protected file blocked by policy: .env"},
            id="reset-denied-for-the-wrong-reason",
        ),
        pytest.param(
            "deny-git-reset",
            {
                "tool": "bash",
                "reason": "Blocked dangerous git operation: git reset --hard",
                "success": True,
            },
            id="reset-denied-but-the-tool-completed",
        ),
        pytest.param("deny-force-push", {"tool": "bash"}, id="force-push-allowed"),
        pytest.param("deny-secret-rm", {"tool": "bash"}, id="secret-rm-allowed"),
        pytest.param(
            "deny-secret-view",
            {"tool": "view", "reason": "Blocked dangerous git operation: force push"},
            id="secret-view-wrong-reason",
        ),
        pytest.param(
            "ask-vscode-settings",
            {"tool": "create", "questions": ("write",)},
            id="settings-edit-asks-no-hook-question",
        ),
        pytest.param(
            "ask-vscode-settings",
            {"tool": "create", "reason": "Protected file blocked by policy: .env"},
            id="settings-edit-denied-instead-of-asked",
        ),
        pytest.param(
            "ask-agent-wrapper",
            {"tool": "edit", "questions": ("write",), "success": False},
            id="agent-wrapper-asks-no-hook-question",
        ),
        pytest.param("deny-branch", {"tool": "bash"}, id="branch-created"),
        pytest.param(
            "deny-branch",
            {"tool": "bash", "reason": "Blocked dangerous git operation: force push"},
            id="branch-denied-by-another-guard",
        ),
        pytest.param(
            "deny-commit",
            {
                "tool": "bash",
                "reason": "PR/push gate only allows implementation branches",
            },
            id="commit-denied-by-the-pr-gate",
        ),
        pytest.param("deny-pr", {"tool": "bash"}, id="pr-allowed"),
        pytest.param(
            "deny-pr",
            {"tool": "bash", "reason": "commit gate failed for github-copilot: x"},
            id="pr-denied-by-the-commit-gate",
        ),
        pytest.param(
            "allow-plain",
            {
                "label": "allow-plain-bash",
                "tool": "bash",
                "reason": "Blocked dangerous git operation: git reset --hard",
            },
            id="plain-bash-denied",
        ),
        pytest.param(
            "allow-plain",
            {
                "label": "allow-plain-view",
                "tool": "view",
                "questions": ("hook", "read"),
            },
            id="plain-view-asks-a-hook-question",
        ),
        pytest.param(
            "allow-plain",
            {
                "label": "allow-plain-create",
                "tool": "create",
                "questions": ("write",),
                "success": False,
            },
            id="plain-create-fails",
        ),
        pytest.param(
            "allow-plain",
            {"tool": "edit", "reason": "Protected file blocked by policy: .env"},
            id="plain-edit-denied",
        ),
        pytest.param(
            "allow-plain",
            {"tool": "edit", "questions": ("hook", "write")},
            id="plain-edit-asks-a-hook-question",
        ),
        pytest.param(
            "allow-plain",
            {"tool": "edit", "questions": ("write",), "success": False},
            id="plain-edit-fails",
        ),
        # Phase B checks. A `label` names the step when it differs from the check.
        pytest.param(
            "helper-tools",
            {
                "label": "helper-read",
                "tool": "read_bash",
                "reason": "hook exited with code 2",
            },
            id="read-helper-denied",
        ),
        pytest.param(
            "helper-tools",
            {
                "label": "helper-list",
                "tool": "list_bash",
                "reason": "hook exited with code 2",
            },
            id="list-helper-denied",
        ),
        pytest.param(
            "helper-tools",
            {
                "label": "helper-stop",
                "tool": "stop_bash",
                "reason": "hook exited with code 2",
            },
            id="stop-helper-denied",
        ),
        pytest.param(
            "read-agent-file",
            {"tool": "view", "questions": ("hook", "read")},
            id="agent-file-read-asks-a-hook-question",
        ),
        pytest.param(
            "read-agent-file",
            {"tool": "view", "reason": "Protected file blocked by policy: .env"},
            id="agent-file-read-denied",
        ),
        pytest.param(
            "search-secret-denied",
            {"label": "search-secret", "tool": "grep"},
            id="secret-search-allowed",
        ),
        pytest.param(
            "search-secret-denied",
            {
                "label": "search-secret",
                "tool": "grep",
                "reason": "Blocked dangerous git operation: force push",
            },
            id="secret-search-denied-for-the-wrong-reason",
        ),
        pytest.param(
            "search-glob-not-judged",
            {
                "label": "search-glob",
                "tool": "glob",
                "reason": "Protected file blocked by policy: .env",
            },
            id="glob-filter-denied",
        ),
        pytest.param(
            "search-glob-not-judged",
            {"label": "search-glob", "tool": "glob", "questions": ("hook", "read")},
            id="glob-filter-asks-a-hook-question",
        ),
        pytest.param(
            "deny-workflow-run",
            {"tool": "run_dynamic_workflow", "success": False},
            id="workflow-run-reaches-the-tool",
        ),
        pytest.param(
            "deny-workflow-run",
            {
                "tool": "run_dynamic_workflow",
                "reason": "Protected file blocked by policy: .env",
            },
            id="workflow-run-denied-for-another-reason",
        ),
        pytest.param(
            "deny-workflow-manage",
            {"tool": "dynamic_workflows_manage"},
            id="workflow-manage-allowed",
        ),
        pytest.param(
            "sql-no-file-write",
            {
                "label": "sql-attach",
                "tool": "sql",
                "success": True,
                "result": "Schema operation completed successfully.",
            },
            id="sql-attach-ran",
        ),
        pytest.param(
            "sql-no-file-write",
            {
                "label": "sql-vacuum-into",
                "tool": "sql",
                "success": False,
                "result": "SQL Error: Error: boom",
            },
            id="sql-vacuum-failed-for-another-reason",
        ),
        pytest.param(
            "sql-no-file-write",
            {
                "label": "sql-attach",
                "tool": "sql",
                "reason": "Protected file blocked by policy: .env",
            },
            id="sql-denied-by-a-hook-not-refused-by-the-tool",
        ),
        pytest.param(
            "subagent-deny-git-reset",
            {"label": "child-git-reset", "tool": "bash"},
            id="sub-agent-reset-runs",
        ),
        pytest.param(
            "subagent-deny-git-reset",
            {
                "label": "child-git-reset",
                "tool": "bash",
                "reason": "Protected file blocked by policy: .env",
            },
            id="sub-agent-reset-denied-for-the-wrong-reason",
        ),
        pytest.param(
            "subagent-store-sql-refused",
            {
                "label": "child-store-attach",
                "tool": "session_store_sql",
                "success": True,
                "result": "1 row(s) returned",
            },
            id="sub-agent-store-attach-ran",
        ),
    ],
)
def test_each_tool_check_fails_on_a_wrong_result_and_only_that_check(
    check: str, wrong_step: dict[str, Any]
) -> None:
    wrong = dict(wrong_step)
    default_label = "allow-plain-edit" if check == "allow-plain" else check
    steps = dict(EXPECTED_STEPS)
    steps[wrong.pop("label", default_label)] = wrong

    results = results_by_name(build_record(steps))

    assert results[check].status == probe.FAIL
    assert results[check].detail
    assert [n for n, r in results.items() if r.status == probe.FAIL] == [check]


def test_a_denial_whose_tool_still_completed_says_so() -> None:
    steps = dict(EXPECTED_STEPS)
    steps["deny-git-reset"] = {
        "tool": "bash",
        "reason": "Blocked dangerous git operation: git reset --hard",
        "success": True,
    }

    result = results_by_name(build_record(steps))["deny-git-reset"]

    assert result.status == probe.FAIL
    assert "denied, but the tool completed" in result.detail


def test_a_denial_reports_the_hook_reason() -> None:
    result = results_by_name(build_record())["deny-git-reset"]

    assert result.status == probe.PASS
    assert "Blocked dangerous git operation: git reset --hard" in result.detail


def test_a_step_that_never_ran_fails_its_check() -> None:
    steps = {k: v for k, v in EXPECTED_STEPS.items() if k != "deny-commit"}

    results = results_by_name(build_record(steps))

    assert results["deny-commit"].status == probe.FAIL
    assert "did not run" in results["deny-commit"].detail


def test_a_scripted_step_with_no_pre_tool_hook_event_fails() -> None:
    steps = dict(EXPECTED_STEPS)
    steps["allow-plain-bash"] = {"tool": "bash", "hooked": False}
    steps["deny-pr"] = {"tool": "bash", "hooked": False}

    results = results_by_name(build_record(steps))

    assert results["allow-plain"].status == probe.FAIL
    assert "pre-tool hook" in results["allow-plain"].detail
    assert results["deny-pr"].status == probe.FAIL


def test_a_runtime_tool_run_with_no_pre_tool_hook_event_is_not_judged() -> None:
    # The runtime's own read of a finished shell (probe P3) has no hook event
    # and is not one of the scripted steps.
    own_read = call_events("call_runtime_read", "read_bash", hooked=False)
    own_denied_read = call_events(
        "call_runtime_read_2", "read_bash", reason="unrelated", hooked=False
    )

    results = probe.evaluate(
        build_record(extra_events=own_read + own_denied_read), probe.BASELINE_CHECKS
    )

    assert [r.status for r in results] == [probe.PASS] * len(EXPECTED_CHECK_NAMES)


def test_events_in_another_order_are_judged_the_same() -> None:
    record = build_record()
    record.events.reverse()

    results = probe.evaluate(record, probe.BASELINE_CHECKS)

    assert [r.status for r in results] == [probe.PASS] * len(EXPECTED_CHECK_NAMES)


def test_a_helper_step_with_no_pre_tool_hook_event_is_not_judged() -> None:
    steps = dict(EXPECTED_STEPS)
    steps["helper-read"] = {"tool": "read_bash", "hooked": False}

    result = results_by_name(build_record(steps))["helper-tools"]

    assert result.status == probe.PASS
    assert "helper-read: not judged" in result.detail
    assert "helper-list: not denied" in result.detail


def test_a_helper_step_that_never_ran_fails_its_check() -> None:
    steps = {k: v for k, v in EXPECTED_STEPS.items() if k != "helper-list"}

    result = results_by_name(build_record(steps))["helper-tools"]

    assert result.status == probe.FAIL
    assert "helper-list did not run" in result.detail


def test_a_helper_result_that_names_a_denial_fails_even_with_no_hook_event() -> None:
    steps = dict(EXPECTED_STEPS)
    steps["helper-stop"] = {
        "tool": "stop_bash",
        "hooked": False,
        "success": False,
        "result": "Denied by preToolUse hook: hook exited with code 2",
    }

    result = results_by_name(build_record(steps))["helper-tools"]

    assert result.status == probe.FAIL
    assert "helper-stop denied" in result.detail


def test_a_skipped_step_says_why_it_did_not_run() -> None:
    record = build_record()
    del record.summary["stepCalls"]["child-store-attach"]
    record.summary["skippedSteps"] = {
        "child-store-attach": "tool session_store_sql not offered"
    }

    result = results_by_name(record)["subagent-store-sql-refused"]

    assert result.status == probe.FAIL
    assert "tool session_store_sql not offered" in result.detail


# --- the codex-patch session -------------------------------------------------

PATCH_CHECK_STEPS = {
    "patch-plain-allowed": "patch-plain",
    "patch-secret-denied": "patch-secret",
    "patch-hook-ask": "patch-hook",
    "patch-server-ask": "patch-server",
    "patch-agent-ask": "patch-agent",
    "patch-indented-hook-ask": "patch-indented-hook",
}
# F6: the file guard crashed on the patch text, so every patch was denied this way.
PATCH_CRASH = {"tool": "apply_patch", "reason": "hook exited with code 2"}
PATCH_ASKED = {"tool": "apply_patch", "questions": ("hook", "hook")}
PATCH_ALLOWED = {"tool": "apply_patch", "questions": ("write",)}
WRONG_PATCH_RESULTS = {
    "patch-plain-allowed": {"crashed": PATCH_CRASH, "asked": PATCH_ASKED},
    "patch-secret-denied": {
        "crashed": PATCH_CRASH,
        "allowed": PATCH_ALLOWED,
        "asked": PATCH_ASKED,
    },
    **{
        check: {"crashed": PATCH_CRASH, "allowed": PATCH_ALLOWED}
        for check in PATCH_CHECK_STEPS
        if check.endswith("-ask")
    },
}


def test_the_patch_session_has_the_planned_checks_in_order() -> None:
    assert [c.name for c in probe.CODEX_PATCH_CHECKS] == EXPECTED_PATCH_CHECK_NAMES
    assert [session.name for session in probe.SESSIONS] == ["main", "codex-patch"]
    assert probe.SESSIONS[1].checks == probe.CODEX_PATCH_CHECKS


def test_a_correct_patch_run_passes_every_check() -> None:
    results = probe.evaluate(build_patch_record(), probe.CODEX_PATCH_CHECKS)

    assert [r.name for r in results] == EXPECTED_PATCH_CHECK_NAMES
    assert [r.status for r in results] == [probe.PASS] * len(EXPECTED_PATCH_CHECK_NAMES)


@pytest.mark.parametrize(
    ("check", "wrong_step"),
    [
        pytest.param(check, wrong, id=f"{check}-{kind}")
        for check, variants in WRONG_PATCH_RESULTS.items()
        for kind, wrong in variants.items()
    ],
)
def test_each_patch_check_fails_on_a_wrong_result_and_only_that_check(
    check: str, wrong_step: dict[str, Any]
) -> None:
    steps = dict(EXPECTED_PATCH_STEPS)
    steps[PATCH_CHECK_STEPS[check]] = wrong_step

    results = patch_results_by_name(build_patch_record(steps))

    assert results[check].status == probe.FAIL
    assert results[check].detail
    assert [n for n, r in results.items() if r.status == probe.FAIL] == [check]


def test_a_patch_step_that_never_ran_fails_its_check() -> None:
    steps = {k: v for k, v in EXPECTED_PATCH_STEPS.items() if k != "patch-agent"}

    results = patch_results_by_name(build_patch_record(steps))

    assert results["patch-agent-ask"].status == probe.FAIL
    assert "did not run" in results["patch-agent-ask"].detail


def test_the_hook_asks_report_how_many_questions_the_runtime_raised() -> None:
    result = patch_results_by_name(build_patch_record())["patch-indented-hook-ask"]

    assert result.status == probe.PASS
    assert "2 question(s) of kind hook" in result.detail


# --- evaluate: discovery checks ----------------------------------------------


def discovery(**parts: dict[str, Any]) -> dict[str, Any]:
    base = {
        "untrusted": {"hooks": {"hooks": []}, "mcp": {"servers": []}},
        "trusted": both_sources(),
        "subfolder": both_sources(),
    }
    base.update(parts)
    return base


@pytest.mark.parametrize(
    ("check", "wrong"),
    [
        pytest.param(
            "hooks-untrusted",
            discovery(untrusted=both_sources()),
            id="hooks-load-before-trust",
        ),
        pytest.param(
            "hooks-untrusted",
            {k: v for k, v in discovery().items() if k != "untrusted"},
            id="no-untrusted-discovery-recorded",
        ),
        pytest.param(
            "hooks-sources",
            discovery(
                trusted={
                    "hooks": {"hooks": [hook_row(GITHUB_HOOKS)]},
                    "mcp": {"servers": []},
                }
            ),
            id="claude-settings-hooks-missing",
        ),
        pytest.param(
            "hooks-sources",
            discovery(
                trusted={
                    "hooks": {"hooks": [hook_row(CLAUDE_SETTINGS)]},
                    "mcp": {"servers": []},
                }
            ),
            id="github-hooks-missing",
        ),
        pytest.param(
            "hooks-sources",
            discovery(
                trusted={
                    "hooks": {
                        "hooks": [
                            hook_row(GITHUB_HOOKS, "sessionStart"),
                            hook_row(CLAUDE_SETTINGS, "sessionStart"),
                        ]
                    },
                    "mcp": {"servers": []},
                }
            ),
            id="no-guard-event-from-either-source",
        ),
        pytest.param(
            "hooks-subfolder",
            discovery(subfolder={"hooks": {"hooks": []}, "mcp": {"servers": []}}),
            id="no-hooks-from-the-subfolder",
        ),
        pytest.param(
            "hooks-subfolder",
            discovery(
                subfolder={
                    "hooks": {"hooks": [hook_row(GITHUB_HOOKS)]},
                    "mcp": {"servers": []},
                }
            ),
            id="one-source-from-the-subfolder",
        ),
        pytest.param(
            "mcp-none",
            discovery(
                trusted={
                    **both_sources(),
                    "mcp": {"servers": [{"name": "semble", "type": "stdio"}]},
                }
            ),
            id="an-mcp-server-is-discovered",
        ),
    ],
)
def test_each_discovery_check_fails_on_a_wrong_answer_and_only_that_check(
    check: str, wrong: dict[str, Any]
) -> None:
    results = results_by_name(build_record(discovery=wrong))

    assert results[check].status == probe.FAIL
    assert [n for n, r in results.items() if r.status == probe.FAIL] == [check]


@pytest.mark.parametrize(
    "event",
    [
        pytest.param(
            {
                "type": "session.mcp_server_status_changed",
                "data": {"serverName": "semble", "status": "pending"},
            },
            id="status-change",
        ),
        pytest.param(
            {
                "type": "session.mcp_servers_loaded",
                "data": {"servers": [{"name": "semble", "status": "connected"}]},
            },
            id="servers-loaded",
        ),
    ],
)
def test_mcp_none_fails_when_the_session_reports_an_mcp_server(
    event: dict[str, Any],
) -> None:
    results = results_by_name(build_record(extra_events=[event]))

    assert results["mcp-none"].status == probe.FAIL


def test_mcp_none_passes_when_the_session_loads_an_empty_server_list() -> None:
    empty = {"type": "session.mcp_servers_loaded", "data": {"servers": []}}

    results = results_by_name(build_record(extra_events=[empty]))

    assert results["mcp-none"].status == probe.PASS


def test_mcp_none_passes_on_the_good_record_and_says_what_it_read() -> None:
    result = results_by_name(build_record())["mcp-none"]

    assert result.status == probe.PASS
    assert "no .mcp.json after the session" in result.detail


def test_mcp_none_fails_when_the_project_has_a_mcp_file_after_the_session() -> None:
    """Regression: a hook restored the file and no server had started yet.

    Discovery found no server and the session reported none, so the old check
    passed. The file on disk is the timing-free sign.
    """
    record = build_record()
    record.summary["mcpFileAfterSession"] = True

    results = results_by_name(record)

    assert results["mcp-none"].status == probe.FAIL
    assert "has a .mcp.json after the session" in results["mcp-none"].detail
    assert [n for n, r in results.items() if r.status == probe.FAIL] == ["mcp-none"]


@pytest.mark.parametrize("recorded", [None, "no", 0])
def test_mcp_none_fails_when_the_runner_did_not_record_the_file(
    recorded: object,
) -> None:
    record = build_record()
    record.summary["mcpFileAfterSession"] = recorded

    result = results_by_name(record)["mcp-none"]

    assert result.status == probe.FAIL
    assert "did not record" in result.detail


# --- output helpers -----------------------------------------------------------


def test_tool_inventory_lists_each_tool_with_its_input_keys() -> None:
    lines = probe.tool_inventory(build_record())

    assert lines == [
        "bash: command, description",
        "apply_patch: (free-form text)",
    ]


def test_summarize_discovery_names_hook_sources_and_notes_missing_trust() -> None:
    lines = probe.summarize_discovery(
        {
            "hooks": both_sources()["hooks"],
            "mcp": {"servers": []},
            "instructions": {"sources": [{"label": "AGENTS.md"}]},
            "skills": {"skills": [{"name": "ponytail"}]},
            "agents": {"agents": [{"name": "coder"}, {"name": "planner"}]},
        }
    )

    text = "\n".join(lines)
    assert "hooks: 4" in text
    assert ".github/hooks/hooks.json: 2" in text
    assert ".claude/settings.json: 2" in text
    assert "MCP servers: 0" in text
    assert "instructions: 1" in text and "AGENTS.md" in text
    assert "skills: 1" in text
    assert "agents: 2" in text and "coder" in text and "planner" in text
    assert "trusted folder" in text


# --- time limits and cleanup --------------------------------------------------


def test_run_limited_kills_the_whole_process_group_on_timeout(
    tmp_path: Path,
) -> None:
    beat = tmp_path / "heartbeat"
    child = (
        "import pathlib, sys, time\n"
        "path = pathlib.Path(sys.argv[1])\n"
        "while True:\n"
        "    path.write_text(str(time.monotonic()))\n"
        "    time.sleep(0.05)\n"
    )
    parent = (
        "import subprocess, sys, time\n"
        f"subprocess.Popen([sys.executable, '-c', {child!r}, sys.argv[1]])\n"
        "time.sleep(60)\n"
    )

    started = time.monotonic()
    run = probe.run_limited(
        [sys.executable, "-c", parent, str(beat)],
        cwd=tmp_path,
        env=dict(os.environ),
        timeout=1.5,
    )

    assert run.timed_out is True
    assert time.monotonic() - started < 15
    assert beat.exists()  # the child did start
    before = beat.read_text(encoding="utf-8")
    time.sleep(0.5)
    assert beat.read_text(encoding="utf-8") == before  # and it was killed


def test_run_limited_returns_output_and_exit_code(tmp_path: Path) -> None:
    run = probe.run_limited(
        [sys.executable, "-c", "import sys; print('out'); sys.exit(3)"],
        cwd=tmp_path,
        env=dict(os.environ),
        timeout=30,
    )

    assert run.timed_out is False
    assert run.returncode == 3
    assert run.stdout.strip() == "out"


class TestMainOrchestration:
    """`main` with the runtime launcher replaced by a recorded fake."""

    @pytest.fixture
    def fake_runtime(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> probe.RuntimeInfo:
        runtime = probe.RuntimeInfo(
            node=tmp_path / "node",
            sdk_root=tmp_path / "sdk",
            sdk_version="1.0.30-preview.0",
            vscode_commit="69047191fc427f2f92828279aae1d90d8eeda7ab",
        )
        monkeypatch.setattr(probe, "find_runtime", lambda vscode_bin=None: runtime)
        temp_root = tmp_path / "temp-root"
        temp_root.mkdir()
        monkeypatch.setattr(tempfile, "tempdir", str(temp_root))

        def fake_prepare(parent: Path, deadline: float | None = None) -> Path:
            project = parent / "project"
            project.mkdir()
            return project

        monkeypatch.setattr(probe, "prepare_project", fake_prepare)
        return runtime

    def test_a_correct_run_prints_versions_checks_and_inventory(
        self,
        fake_runtime: probe.RuntimeInfo,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        calls: list[tuple[Path, Path, Path]] = []

        def fake_session(
            runtime: probe.RuntimeInfo,
            project: Path,
            scenario: dict[str, object],
            home: Path,
            timeout: float = probe.SESSION_LIMIT_SECONDS,
        ) -> probe.SessionRecord:
            calls.append((project, home, runtime.node))
            return record_for(scenario)

        monkeypatch.setattr(probe, "run_session", fake_session)

        code = probe.main([])

        out = capsys.readouterr().out
        assert code == 0
        assert len(calls) == 2  # main, then codex-patch; one project and one home
        assert len({(project, home) for project, home, _ in calls}) == 1
        assert "VS Code commit: 69047191fc427f2f92828279aae1d90d8eeda7ab" in out
        assert "SDK version: 1.0.30-preview.0" in out
        assert "runtime version: 1.0.108-0" in out
        assert len(re.findall(r"^PASS ", out, re.MULTILINE)) == (
            2 + len(EXPECTED_CHECK_NAMES) + len(EXPECTED_PATCH_CHECK_NAMES)
        )
        assert "FAIL" not in out
        assert "PASS session-main:" in out
        assert "PASS session-codex-patch:" in out
        assert "Tool inventory, session main" in out
        assert "Tool inventory, session codex-patch" in out
        assert "bash: command, description" in out
        assert "Result: PASS (0 of " in out

    def test_a_wrong_result_exits_1(
        self,
        fake_runtime: probe.RuntimeInfo,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        steps = dict(EXPECTED_STEPS)
        steps["deny-git-reset"] = {"tool": "bash"}
        monkeypatch.setattr(
            probe,
            "run_session",
            lambda runtime, project, scenario, home, timeout=0: (
                build_record(steps)
                if scenario["name"] == "main"
                else record_for(scenario)
            ),
        )

        code = probe.main([])

        out = capsys.readouterr().out
        assert code == 1
        assert re.search(r"^FAIL deny-git-reset", out, re.MULTILINE)
        assert len(re.findall(r"^FAIL ", out, re.MULTILINE)) == 1

    def test_a_wrong_patch_result_exits_1_and_names_the_check(
        self,
        fake_runtime: probe.RuntimeInfo,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        crashed = dict(EXPECTED_PATCH_STEPS)
        crashed["patch-plain"] = {
            "tool": "apply_patch",
            "reason": PATCH_CRASH["reason"],
        }
        monkeypatch.setattr(
            probe,
            "run_session",
            lambda runtime, project, scenario, home, timeout=0: (
                build_patch_record(crashed)
                if scenario["name"] == "codex-patch"
                else record_for(scenario)
            ),
        )

        code = probe.main([])

        out = capsys.readouterr().out
        assert code == 1
        assert re.search(r"^FAIL patch-plain-allowed", out, re.MULTILINE)
        assert len(re.findall(r"^FAIL ", out, re.MULTILINE)) == 1

    def test_a_session_failure_such_as_a_timeout_is_a_fail_line(
        self,
        fake_runtime: probe.RuntimeInfo,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        def timed_out(*args: Any, **kwargs: Any) -> probe.SessionRecord:
            return probe.SessionRecord(
                name="main", failure="stopped after the 150 s session limit"
            )

        monkeypatch.setattr(probe, "run_session", timed_out)

        code = probe.main([])

        out = capsys.readouterr().out
        assert code == 1
        assert re.search(r"^FAIL session-main.*150 s", out, re.MULTILINE)

    def test_the_run_limit_is_a_fail_and_no_session_starts(
        self,
        fake_runtime: probe.RuntimeInfo,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        started: list[str] = []
        monkeypatch.setattr(probe, "RUN_LIMIT_SECONDS", 0)
        monkeypatch.setattr(
            probe, "run_session", lambda *args, **kwargs: started.append("x")
        )

        code = probe.main([])

        assert code == 1
        assert started == []
        assert re.search(
            r"^FAIL session-main.*run limit", capsys.readouterr().out, re.MULTILINE
        )

    def test_the_session_gets_at_most_the_session_limit(
        self,
        fake_runtime: probe.RuntimeInfo,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        timeouts: list[float] = []

        def fake_session(*args: Any, **kwargs: Any) -> probe.SessionRecord:
            timeouts.append(kwargs["timeout"])
            return record_for(args[2])

        monkeypatch.setattr(probe, "run_session", fake_session)

        probe.main([])

        assert len(timeouts) == 2
        assert all(0 < t <= probe.SESSION_LIMIT_SECONDS == 150 for t in timeouts)
        assert sum(timeouts) <= probe.RUN_LIMIT_SECONDS == 480

    @pytest.mark.parametrize(("keep", "expect_left"), [(False, 0), (True, 1)])
    def test_temporary_folder_is_removed_unless_keep(
        self,
        fake_runtime: probe.RuntimeInfo,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
        keep: bool,
        expect_left: int,
    ) -> None:
        monkeypatch.setattr(
            probe, "run_session", lambda *args, **kwargs: build_record()
        )

        probe.main(["--keep"] if keep else [])

        left = list((tmp_path / "temp-root").glob("copilot-runtime-probe-*"))
        assert len(left) == expect_left
        assert (str(left[0]) in capsys.readouterr().out) if keep else True


# --- the real launcher code, with a fake node ---------------------------------


class TestRunSession:
    """`run_session` and `_launch` start a fake `node`, never the real runtime."""

    @staticmethod
    def run(
        runtime: probe.RuntimeInfo, tmp_path: Path, timeout: float = 30
    ) -> tuple[probe.SessionRecord, Path]:
        project = tmp_path / "project"
        home = tmp_path / "work" / "copilot-home"
        scenario = probe.baseline_scenario(project)
        record = probe.run_session(runtime, project, scenario, home, timeout=timeout)
        return record, home.parent / "sessions" / "main"

    def test_a_finished_session_returns_events_summary_and_no_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/work/agent")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-example")
        for token in ("GITHUB_TOKEN", "GH_TOKEN", "COPILOT_GITHUB_TOKEN"):
            monkeypatch.setenv(token, "ghp_example")
        runtime = make_fake_node(tmp_path / "vscode", FINISHED_NODE)

        record, out = self.run(runtime, tmp_path)

        assert record.failure == ""
        assert record.name == "main"
        # The event line cut off by a kill is skipped; the whole one is kept.
        assert record.events == [{"type": "session.idle", "data": {}}]
        summary = record.summary
        assert summary["seenEnv"] == []
        assert summary["seenArgs"] == [str(probe.PROBE_SCRIPT)]
        assert summary["seenCwd"] == str(out)
        config = summary["config"]
        assert config["mode"] == "session"
        assert config["sdkRoot"] == str(runtime.sdk_root)
        assert config["baseDir"] == str(tmp_path / "work" / "copilot-home")
        assert config["project"] == str(tmp_path / "project")
        assert config["outDir"] == str(out)
        assert config["scenario"]["model"] == "probe-model"
        assert [s["label"] for s in config["scenario"]["steps"]] == MAIN_STEP_LABELS
        assert [
            s["label"] for s in config["scenario"]["childSteps"][probe.CHILD_MARKER]
        ] == list(CHILD_STEP_LABELS)

    def test_errors_in_the_record_are_the_failure(self, tmp_path: Path) -> None:
        runtime = make_fake_node(tmp_path / "vscode", ERRORS_NODE)

        record, _ = self.run(runtime, tmp_path)

        assert record.failure == (
            "runtime errors: send: Timeout waiting for session.idle; "
            "stop: already stopped"
        )
        assert record.summary["modelCalls"] == 2

    def test_a_nonzero_exit_is_the_failure(self, tmp_path: Path) -> None:
        runtime = make_fake_node(tmp_path / "vscode", FAILING_NODE)

        record, _ = self.run(runtime, tmp_path)

        assert record.failure == "node exited with 3: boom: runtime did not start"
        assert record.summary == {}

    def test_no_record_is_the_failure(self, tmp_path: Path) -> None:
        runtime = make_fake_node(tmp_path / "vscode", SILENT_NODE)

        record, _ = self.run(runtime, tmp_path)

        assert record.failure == "the runner wrote no record.json"

    def test_a_sleep_past_the_limit_is_the_failure(self, tmp_path: Path) -> None:
        runtime = make_fake_node(tmp_path / "vscode", SLEEPING_NODE)

        started = time.monotonic()
        record, _ = self.run(runtime, tmp_path, timeout=1)

        assert record.failure == "stopped after the 1 s limit"
        assert time.monotonic() - started < 20

    @pytest.mark.parametrize(
        ("node_exists", "reason"),
        [
            pytest.param(True, "Permission denied", id="node-not-executable"),
            pytest.param(False, "No such file or directory", id="node-missing"),
        ],
    )
    def test_a_node_that_cannot_start_is_a_failure_not_a_traceback(
        self, tmp_path: Path, node_exists: bool, reason: str
    ) -> None:
        folder = tmp_path / "vscode"
        make_runtime(folder, node=node_exists)  # make_runtime writes a plain file
        runtime = probe.RuntimeInfo(
            folder / "node", folder / "sdk", "1.0.30-preview.0", "vscode"
        )

        record, _ = self.run(runtime, tmp_path)

        assert record.failure.startswith("cannot start ")
        assert reason in record.failure
        assert record.events == []


class TestRunDiscover:
    def test_a_folder_that_does_not_exist_is_a_fail_line(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        runtime = make_fake_node(tmp_path / "vscode", FINISHED_NODE)
        missing = tmp_path / "no-such-folder"

        code = probe.run_discover(runtime, missing, tmp_path / "work")

        assert code == 1
        assert capsys.readouterr().out == f"FAIL discover: {missing} is not a folder\n"

    def test_a_node_failure_is_a_fail_line(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        runtime = make_fake_node(tmp_path / "vscode", FAILING_NODE)
        folder = tmp_path / "project"
        folder.mkdir()

        code = probe.run_discover(runtime, folder, tmp_path / "work")

        out = capsys.readouterr().out
        assert code == 1
        assert "FAIL discover: node exited with 3: boom: runtime did not start" in out
        assert "hooks:" not in out

    def test_it_prints_versions_and_what_the_runtime_found(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        runtime = make_fake_node(tmp_path / "vscode", DISCOVERY_NODE)
        folder = tmp_path / "project"
        folder.mkdir()

        code = probe.run_discover(runtime, folder, tmp_path / "work")

        lines = capsys.readouterr().out.splitlines()
        assert code == 0
        assert lines[:7] == [
            f"VS Code commit: {runtime.vscode_commit}",
            "Copilot SDK version: 1.0.30-preview.0",
            "Copilot runtime version: 1.0.108-0",
            "hooks: 0",
            "MCP servers: 0",
            "instructions: 1 (AGENTS.md)",
            "skills: 1",
        ]
        assert lines[7] == "agents: 1 (coder)"
        assert lines[8].startswith("note: repository hooks and MCP servers load only")
        config = json.loads(
            (tmp_path / "work" / "discover" / "config.json").read_text("utf-8")
        )
        assert config["mode"] == "discover"
        assert config["project"] == str(folder.resolve())
        assert "scenario" not in config


class TestRelativeVscodeBin:
    def test_a_relative_folder_is_resolved(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        make_runtime(tmp_path / "rel-runtime")
        monkeypatch.chdir(tmp_path)

        found = probe.find_runtime(Path("rel-runtime"))

        assert found is not None
        assert found.node == tmp_path / "rel-runtime" / "node"
        assert found.sdk_root.is_absolute()

    def test_a_home_relative_folder_is_expanded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("HOME", str(tmp_path))
        make_runtime(tmp_path / "server" / "commit-1")

        found = probe.find_runtime(Path("~/server/commit-1"))

        assert found is not None
        assert found.vscode_commit == "commit-1"

    def test_main_runs_node_from_a_relative_vscode_bin(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Regression: node starts in another folder, so a relative path crashed."""
        make_fake_node(tmp_path / "rel-runtime", DISCOVERY_NODE)
        project = tmp_path / "project"
        project.mkdir()
        temp_root = tmp_path / "temp-root"
        temp_root.mkdir()
        monkeypatch.setattr(tempfile, "tempdir", str(temp_root))
        monkeypatch.chdir(tmp_path)

        code = probe.main(["--vscode-bin", "rel-runtime", "--discover", str(project)])

        out = capsys.readouterr().out
        assert code == 0, out
        assert "VS Code commit: rel-runtime" in out
        assert "Copilot runtime version: 1.0.108-0" in out


class TestPrepareProjectLimits:
    @staticmethod
    def installer(tmp_path: Path, body: str) -> Path:
        script = tmp_path / "fake_installer.py"
        script.write_text("import json, os, pathlib, sys, time\n" + body)
        return script

    def test_the_commands_get_an_identity_and_no_state_remote(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        script = self.installer(
            tmp_path,
            "project = pathlib.Path(sys.argv[1])\n"
            "(project / '.claude').mkdir()\n"
            "(project / '.claude' / 'bootstrap-ownership.env').write_text("
            "'BOOTSTRAP_ROOT_PATH=AGENTS.md\\n')\n"
            "(project.parent / 'seen.json').write_text(json.dumps(dict(os.environ)))\n",
        )
        monkeypatch.setattr(probe, "INSTALLER", script)
        monkeypatch.setenv("AI_STATE_REMOTE", "https://example.invalid/state.git")
        parent = tmp_path / "parent"
        parent.mkdir()

        probe.prepare_project(parent)

        seen = json.loads((parent / "seen.json").read_text("utf-8"))
        assert seen["AI_STATE_REMOTE"] == ""
        for name in ("AUTHOR", "COMMITTER"):
            assert seen[f"GIT_{name}_NAME"]
            assert seen[f"GIT_{name}_EMAIL"]

    def test_it_works_on_a_host_with_no_git_identity(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Regression: `state-sync.sh setup` makes a plain `git commit`."""
        home = tmp_path / "home"
        home.mkdir()
        for name in list(os.environ):
            if name.startswith("GIT_"):
                monkeypatch.delenv(name)
        monkeypatch.setenv("HOME", str(home))
        monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
        monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
        # Never guess an identity from the user and host name: a missing
        # identity then fails on every host, not only on hosts that cannot guess.
        monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
        monkeypatch.setenv("GIT_CONFIG_KEY_0", "user.useConfigOnly")
        monkeypatch.setenv("GIT_CONFIG_VALUE_0", "true")
        parent = tmp_path / "parent"
        parent.mkdir()

        project = probe.prepare_project(parent)

        nested = subprocess.run(
            ["git", "-C", str(project / ".claude"), "rev-parse", "--verify", "HEAD"],
            text=True,
            capture_output=True,
            check=False,
        )
        assert nested.returncode == 0, nested.stderr

    def test_a_command_past_the_deadline_is_killed_and_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            probe, "INSTALLER", self.installer(tmp_path, "time.sleep(60)\n")
        )
        parent = tmp_path / "parent"
        parent.mkdir()

        started = time.monotonic()
        with pytest.raises(RuntimeError, match="timed out at the run limit"):
            probe.prepare_project(parent, deadline=time.monotonic() + 2)

        assert time.monotonic() - started < 30

    def test_an_used_up_deadline_starts_nothing(self, tmp_path: Path) -> None:
        parent = tmp_path / "parent"
        parent.mkdir()

        with pytest.raises(RuntimeError, match="git init not started"):
            probe.prepare_project(parent, deadline=time.monotonic() - 1)

        assert not (parent / "project" / ".git").exists()

    def test_main_reports_a_slow_installer_as_fail_project(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        runtime = make_fake_node(tmp_path / "vscode", FINISHED_NODE)
        monkeypatch.setattr(probe, "find_runtime", lambda vscode_bin=None: runtime)
        monkeypatch.setattr(probe, "RUN_LIMIT_SECONDS", 3)
        monkeypatch.setattr(
            probe, "INSTALLER", self.installer(tmp_path, "time.sleep(60)\n")
        )
        temp_root = tmp_path / "temp-root"
        temp_root.mkdir()
        monkeypatch.setattr(tempfile, "tempdir", str(temp_root))

        code = probe.main([])

        out = capsys.readouterr().out
        assert code == 1
        assert re.search(r"^FAIL project: .*timed out at the run limit", out, re.M)
        assert "session-main" not in out
        assert list(temp_root.iterdir()) == []  # the temporary folder is removed

    def test_main_reports_a_failing_installer_as_fail_project(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        runtime = make_fake_node(tmp_path / "vscode", FINISHED_NODE)
        monkeypatch.setattr(probe, "find_runtime", lambda vscode_bin=None: runtime)
        monkeypatch.setattr(
            probe,
            "INSTALLER",
            self.installer(
                tmp_path, "sys.stderr.write('installer boom\\n')\nsys.exit(1)\n"
            ),
        )
        temp_root = tmp_path / "temp-root"
        temp_root.mkdir()
        monkeypatch.setattr(tempfile, "tempdir", str(temp_root))

        code = probe.main([])

        assert code == 1
        assert re.search(
            r"^FAIL project: .*failed \(1\): installer boom",
            capsys.readouterr().out,
            re.M,
        )


# --- boundaries ---------------------------------------------------------------


def test_probe_script_is_a_regular_file_named_by_the_python_script() -> None:
    script = REPO_ROOT / "scripts" / "copilot_runtime_probe.mjs"

    assert script.is_file()
    assert not script.is_symlink()
    assert probe.PROBE_SCRIPT == script
    python_source = (REPO_ROOT / "scripts" / "check_copilot_runtime.py").read_text(
        encoding="utf-8"
    )
    assert "copilot_runtime_probe.mjs" in python_source


def test_probe_code_names_no_host_but_loopback() -> None:
    for name in ("check_copilot_runtime.py", "copilot_runtime_probe.mjs"):
        text = (REPO_ROOT / "scripts" / name).read_text(encoding="utf-8")
        hosts = re.findall(r"https?://[A-Za-z0-9._-]+", text)
        assert set(hosts) <= {"http://127.0.0.1"}, (name, hosts)


def test_no_verifier_hook_script_or_other_test_calls_the_probe() -> None:
    this_test = Path(__file__).resolve()
    searched = [
        *sorted((REPO_ROOT / "shared" / "hooks").rglob("*")),
        *sorted((REPO_ROOT / "shared" / "scripts").rglob("*.py")),
        *sorted((REPO_ROOT / "tests").glob("*.py")),
        *sorted((REPO_ROOT / "scripts").glob("*.py")),
    ]
    callers = [
        path
        for path in searched
        if path.is_file()
        and path.resolve() not in (this_test, Path(probe.__file__).resolve())
        and "check_copilot_runtime" in path.read_text(encoding="utf-8", errors="ignore")
    ]

    assert callers == []
