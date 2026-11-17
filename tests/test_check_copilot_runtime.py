"""Offline tests for the opt-in Copilot runtime probe.

None of these tests starts Node or the Copilot runtime, and none makes a model
call. Synthetic events copy the shapes recorded in the evidence folder
`.claude/explorations/2026-11-17_copilot-harness-migration-evidence/` (raw run
`outcomes-g-both.txt`). Expected values come from the plan's baseline table,
not from the probe's own output.
"""

from __future__ import annotations

import atexit
import json
import os
import re
import shutil
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
    # Phase E: the two custom sub-agents, started by the main model.
    "subagent-coder": {"tool": "task"},
    "subagent-reviewer": {"tool": "task"},
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
    "single-session-log",
    "state-sync-once",
    "session-reminder",
    "deny-git-reset",
    "deny-force-push",
    "deny-secret-rm",
    "deny-secret-view",
    "ask-vscode-settings",
    "ask-agent-wrapper",
    "guards-both-sources",
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
    "subagent-context",
]


SESSION_ID = "2a8f5fb9-54e8-4b10-8f35-6ef6eeb121ec"
CHILD_SESSION_ID = "e8cf30a5-88ca-47c1-8816-662fabc14ee3"
SESSIONS_LOG = Path(".claude") / "session_logs" / "hooks-sessions.log"
ERRORS_LOG = Path(".claude") / "session_logs" / "hooks-errors.log"
# The exact text `state-sync.sh pull` logs with no state remote (see
# `test_the_pull_line_the_check_counts_is_what_state_sync_writes`).
PULL_LINE = "2026-11-17T15:58:48.000Z state-sync: no state remote configured; nothing to pull from."
# Lines of a real probe run (evidence raw/phase-D-probe-output.txt) in which the
# Claude-settings lifecycle hooks stood down: one session log entry per event and
# one pull. The sub-agent has a session of its own, with only a stop.
GOOD_SESSIONS_LOG = [
    f"2026-11-17T15:58:49.000Z,event=SessionStart,target=github-copilot,sessionId={SESSION_ID},source=new",
    f"2026-11-17T15:58:55.000Z,event=Stop,target=github-copilot,sessionId={CHILD_SESSION_ID}",
    f"2026-11-17T15:58:55.000Z,event=Stop,target=github-copilot,sessionId={SESSION_ID}",
]
GOOD_ERRORS_LOG = [
    "2026-11-17T15:58:47.000Z state-sync: no state remote configured (set AI_STATE_REMOTE, pass --state-remote at install time, or ensure this repo has an 'origin'); state will stay local-only until one is configured.",
    PULL_LINE,
    "2026-11-17T15:58:54.000Z state-sync: no state remote configured; local checkpoint remains unpublished.",
    "2026-11-17T15:58:55Z WARN stop-session-log-check: worktree changed but no session log was updated today",
]
# Phase E. What the model received as user messages in a real run (evidence
# raw/phase-E-probe-output.txt): the session reminder is a user message of its own
# before the prompt, and each sub-agent's first user message holds the guidance, the
# fixed line, and the task prompt. The literals are written out here from the plan.
GUIDANCE_HEADING = "GitHub Copilot Workspace Adapter"
SUBAGENT_LINE = (
    "Agent files live in `.claude/agents/<id>.md` and skills live in "
    "`.claude/skills/<name>/SKILL.md`. When your agent file lists a skill, read "
    "its SKILL.md file with the read tool."
)
REMINDER = (
    "For user-facing updates, use direct language; explain internal labels and "
    "uncommon abbreviations, and avoid idioms. State what options mean in "
    "practice. Preserve exact technical text."
)
CHILD_AGENTS = ("general", "coder", "reviewer")


def good_main_user_messages() -> list[str]:
    return [
        REMINDER,
        "<system_reminder>\n<environment_limitations>\n...\n</system_reminder>",
        "<current_datetime>2026-11-18T03:30:36.560+09:00</current_datetime>\n\n"
        "PROBE-MARKER Run the probe steps.",
    ]


def good_subagent_requests() -> dict[str, dict[str, Any]]:
    return {
        f"PROBE-CHILD-{agent}": {
            "toolNames": ["view"],
            "system": ["system prompt"],
            "user": [
                "<current_datetime>2026-11-18T03:30:42.496+09:00</current_datetime>"
                f"\n\n# {GUIDANCE_HEADING}\n\nThis target is generated from `shared/`."
                f"\n\n{SUBAGENT_LINE}\n\nPROBE-CHILD-{agent} say ok"
            ],
        }
        for agent in CHILD_AGENTS
    }


# Projects of records the caller did not give one: they hold the good logs and
# live in a folder made before any test patches `tempfile`.
RECORD_PROJECTS = Path(tempfile.mkdtemp(prefix="probe-test-records-"))
atexit.register(shutil.rmtree, RECORD_PROJECTS, ignore_errors=True)


def write_logs(
    project: Path,
    sessions: Sequence[str] | None = GOOD_SESSIONS_LOG,
    errors: Sequence[str] | None = GOOD_ERRORS_LOG,
) -> Path:
    """Write the two hook logs a session leaves in its project; None writes no file."""
    for relative, lines in ((SESSIONS_LOG, sessions), (ERRORS_LOG, errors)):
        if lines is not None:
            (project / relative).parent.mkdir(parents=True, exist_ok=True)
            (project / relative).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return project


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
    project: Path | None = None,
) -> probe.SessionRecord:
    """A record of a correct run, unless the caller passes wrong steps or discovery.

    `project` is the folder whose hook logs the log checks read; without one the
    record gets a folder that holds the good logs.
    """
    steps = EXPECTED_STEPS if steps is None else steps
    if project is None:
        project = write_logs(Path(tempfile.mkdtemp(dir=RECORD_PROJECTS)))
    events: list[dict[str, Any]] = [
        {"type": "session.start", "data": {"sessionId": SESSION_ID}}
    ]
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
        "mainFirstRequestUser": good_main_user_messages(),
        "subagentFirstRequests": good_subagent_requests(),
        "errors": [],
    }
    return probe.SessionRecord(
        name=name, events=events, summary=summary, project=project
    )


def build_patch_record(
    steps: dict[str, dict[str, Any]] | None = None,
) -> probe.SessionRecord:
    """A record of a correct `codex-patch` run, unless the caller passes wrong steps."""
    steps = EXPECTED_PATCH_STEPS if steps is None else steps
    return build_record(steps, name="codex-patch")


def record_for(
    scenario: dict[str, object], project: Path | None = None
) -> probe.SessionRecord:
    """The record of a correct run of the scenario a fake session was given."""
    if scenario["name"] == "codex-patch":
        return build_patch_record()
    if scenario["name"] == "camel-rename":
        return build_camel_record(project=project)
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
    " 'seenEnv': sorted(k for k in os.environ"
    " if k.startswith(('CLAUDE', 'ANTHROPIC', 'GIT_', 'GH_', 'AI_STATE_'))"
    " or k in ('GITHUB_TOKEN', 'COPILOT_GITHUB_TOKEN')),"
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


def test_runtime_environment_drops_every_git_gh_and_ai_state_variable() -> None:
    """A command that a broken guard lets run must not reach another repository.

    The probe sets nothing in the runtime's environment itself; its fixed Git
    identity goes only to the installer, in `prepare_project`.
    """
    kept = {"PATH": "/usr/bin:/bin", "HOME": "/home/someone", "LANG": "C.UTF-8"}
    aimed_elsewhere = {
        "GIT_DIR": "/work/other/.git",
        "GIT_WORK_TREE": "/work/other",
        "GIT_INDEX_FILE": "/work/other/.git/index",
        "GIT_CONFIG_COUNT": "1",
        "GIT_CONFIG_KEY_0": "url.https://example.invalid/.insteadOf",
        "GIT_CONFIG_VALUE_0": "https://github.com/",
        "GIT_AUTHOR_NAME": "Someone",
        "GIT_EDITOR": "true",
        "GH_REPO": "owner/other",
        "GH_HOST": "example.invalid",
        "GH_CONFIG_DIR": "/home/someone/.config/gh",
        # They steer `state-sync.sh` in the session hooks.
        "AI_STATE_REPO_ROOT": "/work/other",
        "AI_STATE_LOCAL_ONLY": "1",
        "AI_STATE_BRANCH": "other-branch",
        "AI_STATE_REMOTE": "https://example.invalid/state.git",
    }
    # Names that only start with the same letters are not Git, GitHub CLI, or
    # AI-state variables.
    similar = {"GHOST": "boo", "GITLAB_CI": "true", "AI_STATEMENT": "kept"}

    env = probe.runtime_environment({**kept, **aimed_elsewhere, **similar})

    assert env == {**kept, **similar}


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


# `guards-both-sources` (Phase D) judges the same step as `ask-vscode-settings`
# and counts its questions, so a wrong step fails both.
SAME_STEP_CHECKS = {"ask-vscode-settings": ["guards-both-sources"]}


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
    assert [n for n, r in results.items() if r.status == probe.FAIL] == [
        check,
        *SAME_STEP_CHECKS.get(check, []),
    ]


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


# --- Phase E: the sub-agent context and the session reminder -----------------


def test_the_main_session_starts_the_coder_and_the_reviewer_sub_agents() -> None:
    scenario = probe.baseline_scenario(Path("/work/project"))
    steps: dict[str, dict[str, Any]] = {
        step["label"]: step
        for step in scenario["steps"]  # type: ignore[attr-defined]
    }
    labels = list(steps)

    assert (
        labels.index("subagent-start")
        < labels.index("subagent-coder")
        < labels.index("subagent-reviewer")
    )
    for agent in ("coder", "reviewer"):
        task = steps[f"subagent-{agent}"]
        assert task["tool"] == "task"
        assert task["args"]["agent_type"] == agent
        # The marker keys the first request the runner records for the sub-agent.
        assert task["args"]["prompt"].startswith(f"PROBE-CHILD-{agent} ")
    # They play no tool steps: the check reads the first message each received.
    assert set(scenario["childSteps"]) == {probe.CHILD_MARKER}  # type: ignore[arg-type]


def test_the_probe_constants_are_the_text_of_the_shipped_hooks(tmp_path: Path) -> None:
    """The fixed line, the reminder, and the heading the checks look for are the
    ones the scripts and the generator produce, so a change of one fails here."""
    import generate_targets

    scripts = tmp_path / ".claude" / "hooks" / "scripts"
    scripts.parent.mkdir(parents=True)
    scripts.symlink_to(REPO_ROOT / "shared" / "hooks" / "scripts", True)
    done = subprocess.run(
        ["bash", str(scripts / "subagent-context.sh"), "github-copilot"],
        input="{}",
        text=True,
        capture_output=True,
        check=False,
        cwd=tmp_path,
    )
    reminder_script = (
        REPO_ROOT / "shared" / "hooks" / "scripts" / "reporting-reminder.sh"
    ).read_text(encoding="utf-8")

    assert probe.SUBAGENT_LINE == SUBAGENT_LINE
    assert probe.REMINDER_TEXT == REMINDER
    assert probe.GUIDANCE_HEADING == GUIDANCE_HEADING
    # No guidance file in the folder: the answer is the fixed line alone.
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["additionalContext"] == probe.SUBAGENT_LINE
    assert f'REMINDER="{probe.REMINDER_TEXT}"' in reminder_script
    guidance = generate_targets.render_copilot_instructions()
    assert guidance.splitlines()[0] == f"# {probe.GUIDANCE_HEADING}"


def test_the_session_reminder_check_passes_and_says_where_the_reminder_was() -> None:
    result = results_by_name(build_record())["session-reminder"]

    assert result.status == probe.PASS
    assert "first user message" in result.detail


@pytest.mark.parametrize(
    ("messages", "expected_in_detail"),
    [
        pytest.param(None, "no user message", id="nothing-recorded"),
        pytest.param([], "no user message", id="no-user-messages"),
        pytest.param(
            ["PROBE-MARKER Run the probe steps."],
            "not in the first of the 1 user message",
            id="the-hook-added-nothing",
        ),
        pytest.param(
            ["<current_datetime>x</current_datetime>", REMINDER],
            "not in the first of the 2 user message",
            id="the-reminder-came-after-another-message",
        ),
        pytest.param(
            [REMINDER[:-1]],
            "not in the first of the 1 user message",
            id="the-reminder-is-cut",
        ),
        pytest.param(
            [REMINDER.replace("direct", "plain")],
            "not in the first of the 1 user message",
            id="another-reminder-text",
        ),
    ],
)
def test_the_session_reminder_check_fails_on_a_wrong_first_request(
    messages: list[str] | None, expected_in_detail: str
) -> None:
    record = build_record()
    if messages is None:
        del record.summary["mainFirstRequestUser"]
    else:
        record.summary["mainFirstRequestUser"] = messages

    results = results_by_name(record)

    assert results["session-reminder"].status == probe.FAIL
    assert expected_in_detail in results["session-reminder"].detail
    assert [n for n, r in results.items() if r.status == probe.FAIL] == [
        "session-reminder"
    ]


def test_the_sub_agent_check_passes_and_names_both_custom_agents() -> None:
    result = results_by_name(build_record())["subagent-context"]

    assert result.status == probe.PASS
    assert "each of coder and reviewer" in result.detail


def _drop_request(agent: str) -> Any:
    return lambda requests: requests.pop(f"PROBE-CHILD-{agent}")


def _set_first_message(agent: str, text: str) -> Any:
    def edit(requests: dict[str, Any]) -> None:
        requests[f"PROBE-CHILD-{agent}"]["user"] = [text]

    return edit


@pytest.mark.parametrize(
    ("edit", "expected_in_detail"),
    [
        pytest.param(
            lambda requests: requests.clear(),
            "no first request was recorded for sub-agent coder",
            id="no-sub-agent-started",
        ),
        pytest.param(
            _drop_request("coder"),
            "no first request was recorded for sub-agent coder",
            id="the-coder-never-started",
        ),
        pytest.param(
            _drop_request("reviewer"),
            "no first request was recorded for sub-agent reviewer",
            id="the-reviewer-never-started",
        ),
        pytest.param(
            _set_first_message("coder", "PROBE-CHILD-coder say ok"),
            "sub-agent coder lacks the heading 'GitHub Copilot Workspace Adapter' "
            "and the fixed line",
            id="the-coder-got-only-its-task",
        ),
        pytest.param(
            _set_first_message(
                "reviewer", f"# {GUIDANCE_HEADING}\n\nPROBE-CHILD-reviewer say ok"
            ),
            "sub-agent reviewer lacks the fixed line",
            id="the-reviewer-got-no-fixed-line",
        ),
        pytest.param(
            _set_first_message("coder", f"{SUBAGENT_LINE}\n\nPROBE-CHILD-coder say ok"),
            "sub-agent coder lacks the heading",
            id="the-coder-got-no-guidance",
        ),
        pytest.param(
            _set_first_message(
                "coder",
                f"# {GUIDANCE_HEADING}\n\n{SUBAGENT_LINE[:-1]}\n\nPROBE-CHILD-coder",
            ),
            "sub-agent coder lacks the fixed line",
            id="the-fixed-line-is-cut",
        ),
        pytest.param(
            lambda requests: requests["PROBE-CHILD-coder"].update(
                user=["x", f"# {GUIDANCE_HEADING}\n\n{SUBAGENT_LINE}"]
            ),
            "sub-agent coder lacks the heading",
            id="the-context-came-in-a-later-message",
        ),
        pytest.param(
            lambda requests: requests["PROBE-CHILD-reviewer"].update(user=[]),
            "no first request was recorded for sub-agent reviewer",
            id="no-user-message",
        ),
    ],
)
def test_the_sub_agent_check_fails_on_a_wrong_first_request(
    edit: Any, expected_in_detail: str
) -> None:
    record = build_record()
    edit(record.summary["subagentFirstRequests"])

    results = results_by_name(record)

    assert results["subagent-context"].status == probe.FAIL
    assert expected_in_detail in results["subagent-context"].detail
    assert [n for n, r in results.items() if r.status == probe.FAIL] == [
        "subagent-context"
    ]


def test_the_sub_agent_check_does_not_need_the_general_purpose_request() -> None:
    record = build_record()
    del record.summary["subagentFirstRequests"]["PROBE-CHILD-general"]

    assert results_by_name(record)["subagent-context"].status == probe.PASS


def test_the_sub_agent_check_fails_without_a_recorded_requests_object() -> None:
    record = build_record()
    del record.summary["subagentFirstRequests"]

    result = results_by_name(record)["subagent-context"]

    assert result.status == probe.FAIL
    assert "no first request was recorded for sub-agent coder" in result.detail


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
    assert [session.name for session in probe.SESSIONS[:2]] == ["main", "codex-patch"]
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


# --- Phase D: the Claude-settings lifecycle hooks stand down ------------------
# Before the launcher change both hook sources log every session event and run
# the state pull, so the logs show each twice. The expected values are the
# plan's: one `github-copilot` entry per event, no `claude-code` entry, one pull
# line, and two questions (one per source) for a protected config.

BOTH_SOURCES_SESSIONS_LOG = [
    f"2026-11-17T15:58:49.000Z,event=SessionStart,target=github-copilot,sessionId={SESSION_ID},source=new",
    f"2026-11-17T15:58:50.000Z,event=SessionStart,target=claude-code,sessionId={SESSION_ID},source=new",
    f"2026-11-17T15:58:55.000Z,event=Stop,target=github-copilot,sessionId={SESSION_ID}",
    f"2026-11-17T15:58:55.000Z,event=Stop,target=claude-code,sessionId={SESSION_ID}",
]
STAND_DOWN_CHECKS = ["single-session-log", "state-sync-once", "guards-both-sources"]


def failing(record: probe.SessionRecord) -> list[str]:
    return [n for n, r in results_by_name(record).items() if r.status == probe.FAIL]


def test_a_correct_run_passes_the_stand_down_checks_and_says_what_they_read() -> None:
    results = results_by_name(build_record())

    assert [results[name].status for name in STAND_DOWN_CHECKS] == [probe.PASS] * 3
    assert results["single-session-log"].detail == (
        "2 target=github-copilot line(s) and no target=claude-code line for session 2a8f5fb9"
    )
    assert results["state-sync-once"].detail == (
        "1 state-sync pull line in .claude/session_logs/hooks-errors.log"
    )
    assert results["guards-both-sources"].detail == (
        "2 questions of kind hook; not denied"
    )


def test_the_stand_down_checks_belong_to_the_main_session_only() -> None:
    assert [c.name for c in probe.BASELINE_CHECKS if c.name in STAND_DOWN_CHECKS] == (
        STAND_DOWN_CHECKS
    )
    for checks in (probe.CODEX_PATCH_CHECKS, probe.CAMEL_CHECKS):
        assert not [c for c in checks if c.name in STAND_DOWN_CHECKS]


def test_the_session_log_check_fails_when_both_hook_sources_log_the_session(
    tmp_path: Path,
) -> None:
    record = build_record(
        project=write_logs(tmp_path, sessions=BOTH_SOURCES_SESSIONS_LOG)
    )

    results = results_by_name(record)

    assert failing(record) == ["single-session-log"]
    assert results["single-session-log"].detail == (
        "2 line(s) with target=claude-code for session 2a8f5fb9: "
        "the Claude-settings hooks did not stand down"
    )


@pytest.mark.parametrize(
    ("sessions", "expected_in_detail"),
    [
        pytest.param(
            [GOOD_SESSIONS_LOG[0].replace("github-copilot", "claude-code")],
            "1 line(s) with target=claude-code",
            id="only-the-claude-settings-copy-logged",
        ),
        pytest.param(
            [GOOD_SESSIONS_LOG[1]],
            "no target=github-copilot line for session 2a8f5fb9",
            id="the-session-has-no-line-at-all",
        ),
        pytest.param([], "no target=github-copilot line", id="the-log-is-empty"),
    ],
)
def test_the_session_log_check_fails_unless_the_copilot_copy_logged_alone(
    tmp_path: Path, sessions: list[str], expected_in_detail: str
) -> None:
    record = build_record(project=write_logs(tmp_path, sessions=sessions))

    assert failing(record) == ["single-session-log"]
    assert expected_in_detail in results_by_name(record)["single-session-log"].detail


def test_the_session_log_check_judges_only_the_lines_of_its_own_session(
    tmp_path: Path,
) -> None:
    other = BOTH_SOURCES_SESSIONS_LOG[1].replace(SESSION_ID, "another-session")
    project = write_logs(tmp_path, sessions=[*GOOD_SESSIONS_LOG, other])

    assert failing(build_record(project=project)) == []


def test_the_session_log_check_fails_when_the_log_is_missing(tmp_path: Path) -> None:
    record = build_record(project=write_logs(tmp_path, sessions=None))

    assert failing(record) == ["single-session-log"]
    assert "cannot read .claude/session_logs/hooks-sessions.log" in (
        results_by_name(record)["single-session-log"].detail
    )


def test_the_session_log_check_needs_a_session_id_and_a_project() -> None:
    no_id = build_record()
    no_id.events = [e for e in no_id.events if e["type"] != "session.start"]
    no_project = build_record()
    no_project.project = None

    assert (
        "no session.start event" in results_by_name(no_id)["single-session-log"].detail
    )
    assert (
        "no project folder" in results_by_name(no_project)["single-session-log"].detail
    )
    assert "no project folder" in results_by_name(no_project)["state-sync-once"].detail


def test_the_pull_check_fails_when_both_hook_sources_ran_the_pull(
    tmp_path: Path,
) -> None:
    second = PULL_LINE.replace("15:58:48", "15:58:49")
    project = write_logs(tmp_path, errors=[*GOOD_ERRORS_LOG, second])

    record = build_record(project=project)

    assert failing(record) == ["state-sync-once"]
    assert results_by_name(record)["state-sync-once"].detail == (
        "2 state-sync pull line(s) in .claude/session_logs/hooks-errors.log, "
        "expected exactly 1 (2 means both hook sources ran it)"
    )


@pytest.mark.parametrize(
    ("errors", "expected_in_detail"),
    [
        pytest.param(
            [line for line in GOOD_ERRORS_LOG if line != PULL_LINE],
            "0 state-sync pull line(s)",
            id="no-pull-ran",
        ),
        pytest.param(
            None, "cannot read .claude/session_logs/hooks-errors.log", id="no-log"
        ),
    ],
)
def test_the_pull_check_fails_without_exactly_one_pull_line(
    tmp_path: Path, errors: list[str] | None, expected_in_detail: str
) -> None:
    record = build_record(project=write_logs(tmp_path, errors=errors))

    assert failing(record) == ["state-sync-once"]
    assert expected_in_detail in results_by_name(record)["state-sync-once"].detail


def test_the_pull_check_counts_only_the_pull_line(tmp_path: Path) -> None:
    """Setup, checkpoint, and stop-check lines in the same log are not pulls."""
    assert len(GOOD_ERRORS_LOG) == 4
    assert sum(line.endswith(probe.PULL_TEXT) for line in GOOD_ERRORS_LOG) == 1

    assert failing(build_record(project=write_logs(tmp_path))) == []


@pytest.mark.parametrize(
    ("questions", "expected_in_detail"),
    [
        pytest.param(
            ("hook", "write"), "1 question(s) of kind hook, expected 2", id="one-source"
        ),
        pytest.param(("write",), "0 question(s) of kind hook, expected 2", id="none"),
        pytest.param(
            ("hook", "hook", "hook", "write"),
            "3 question(s) of kind hook, expected 2",
            id="a-third-source",
        ),
    ],
)
def test_the_guard_check_fails_unless_each_hook_source_asked_once(
    questions: tuple[str, ...], expected_in_detail: str
) -> None:
    steps = dict(EXPECTED_STEPS)
    steps["ask-vscode-settings"] = {"tool": "create", "questions": questions}

    results = results_by_name(build_record(steps))

    assert results["guards-both-sources"].status == probe.FAIL
    assert expected_in_detail in results["guards-both-sources"].detail
    # `ask-vscode-settings` still passes a single question: only this check pins two.
    expected_ask = probe.PASS if "hook" in questions else probe.FAIL
    assert results["ask-vscode-settings"].status == expected_ask


def test_the_guard_check_fails_when_the_step_never_ran() -> None:
    steps = {k: v for k, v in EXPECTED_STEPS.items() if k != "ask-vscode-settings"}

    results = results_by_name(build_record(steps))

    assert results["guards-both-sources"].status == probe.FAIL
    assert "did not run" in results["guards-both-sources"].detail


def test_the_pull_line_the_check_counts_is_what_state_sync_writes(
    tmp_path: Path,
) -> None:
    """The probe project has no state remote, so `state-sync.sh pull` logs one line.

    The text comes from running the shipped script, not from the probe's constant.
    """
    project = probe.prepare_project(tmp_path)
    errors = project / ERRORS_LOG
    before = errors.read_text(encoding="utf-8").splitlines() if errors.exists() else []

    done = subprocess.run(
        [
            "bash",
            str(project / ".claude" / "hooks" / "scripts" / "state-sync.sh"),
            "pull",
        ],
        cwd=project,
        text=True,
        capture_output=True,
        input="{}",
        check=False,
        # No state remote, the project as root, no local-only mode, and a fixed
        # identity, whatever the host sets (as tests/test_state_sync.py pins them).
        env={
            **os.environ,
            "AI_STATE_REMOTE": "",
            "AI_STATE_REPO_ROOT": str(project),
            "AI_STATE_BRANCH": "ai-state",
            "AI_STATE_LOCAL_ONLY": "0",
            "GIT_AUTHOR_NAME": "Copilot Probe",
            "GIT_AUTHOR_EMAIL": "probe@example.com",
            "GIT_COMMITTER_NAME": "Copilot Probe",
            "GIT_COMMITTER_EMAIL": "probe@example.com",
        },
    )

    assert done.returncode == 0, done.stderr
    added = errors.read_text(encoding="utf-8").splitlines()[len(before) :]
    pulls = [line for line in added if line.endswith(probe.PULL_TEXT)]
    assert len(pulls) == 1
    assert pulls[0].endswith(" " + probe.PULL_TEXT)
    assert re.fullmatch(
        r"\d{4}-\d\d-\d\dT[\d:.]+Z " + re.escape(probe.PULL_TEXT), pulls[0]
    )


# --- the camel-rename session -------------------------------------------------
# Phase C: the Copilot hook file's events are renamed to the documented camelCase
# names in a copy of the project, and the Claude settings source is switched off
# there, so only the Copilot file runs. The nested-only answer is ignored under
# camelCase names (F4), so before the guards print the top-level answer these
# denies fail.

CAMEL_EVENT_NAMES = {
    "SessionStart": "sessionStart",
    "PreToolUse": "preToolUse",
    "PostToolUse": "postToolUse",
    "Stop": "agentStop",
    "SubagentStart": "subagentStart",
}
# Each camel step has the same expected value as its twin in the baseline
# (Phase A). With one hook source the runtime raises one question, not two.
CAMEL_TWINS = {
    "camel-deny-git-reset": "deny-git-reset",
    "camel-deny-secret-rm": "deny-secret-rm",
    "camel-ask-vscode-settings": "ask-vscode-settings",
    "camel-ask-agent-wrapper": "ask-agent-wrapper",
    "camel-deny-branch": "deny-branch",
    "camel-deny-commit": "deny-commit",
    "camel-deny-pr": "deny-pr",
    "camel-allow-plain-bash": "allow-plain-bash",
    "camel-allow-plain-view": "allow-plain-view",
    "camel-allow-plain-create": "allow-plain-create",
    "camel-allow-plain-edit": "allow-plain-edit",
}
EXPECTED_CAMEL_STEPS: dict[str, dict[str, Any]] = {
    label: dict(EXPECTED_STEPS[twin]) for label, twin in CAMEL_TWINS.items()
}
EXPECTED_CAMEL_STEPS["camel-ask-vscode-settings"]["questions"] = ("hook", "write")
EXPECTED_CAMEL_STEPS["camel-ask-agent-wrapper"]["questions"] = ("hook",)
CAMEL_CHECK_STEPS = {
    "camel-deny-git-reset": "camel-deny-git-reset",
    "camel-deny-secret-rm": "camel-deny-secret-rm",
    "camel-deny-commit": "camel-deny-commit",
    "camel-deny-branch": "camel-deny-branch",
    "camel-deny-pr": "camel-deny-pr",
    "camel-ask-vscode-settings": "camel-ask-vscode-settings",
    "camel-ask-agent-wrapper": "camel-ask-agent-wrapper",
    "camel-allow-plain": "camel-allow-plain-edit",
}
EXPECTED_CAMEL_CHECK_NAMES = [
    "camel-hooks-source",
    "camel-events-renamed",
    "camel-mcp-none",
    *CAMEL_CHECK_STEPS,
]
RESTORE_COPY = Path(".claude") / "bootstrap-root" / ".github" / "hooks" / "hooks.json"
LIVE_COPY = Path(".github") / "hooks" / "hooks.json"


def camel_discovery(**parts: dict[str, Any]) -> dict[str, Any]:
    """Discovery of a run whose Claude settings source is off: Copilot file only."""
    github_only = {
        "hooks": {
            "hooks": [hook_row(GITHUB_HOOKS), hook_row(GITHUB_HOOKS, "sessionStart")],
            "warnings": [],
            "errors": [],
        },
        "mcp": {"servers": []},
    }
    base = {
        "untrusted": {"hooks": {"hooks": []}, "mcp": {"servers": []}},
        "trusted": github_only,
        "subfolder": github_only,
    }
    base.update(parts)
    return base


def write_camel_project(folder: Path, *, settings: str = "off") -> Path:
    """The files a camel session leaves behind when the setup survived."""
    for relative in (LIVE_COPY, RESTORE_COPY):
        (folder / relative).parent.mkdir(parents=True, exist_ok=True)
        (folder / relative).write_text(
            json.dumps(
                {"version": 1, "hooks": dict.fromkeys(CAMEL_EVENT_NAMES.values(), [])}
            ),
            encoding="utf-8",
        )
    claude = folder / ".claude"
    claude.mkdir(exist_ok=True)
    if settings == "off":
        (claude / "settings.json.off").write_text("{}", encoding="utf-8")
    elif settings == "on":
        (claude / "settings.json").write_text("{}", encoding="utf-8")
    return folder


def build_camel_record(
    steps: dict[str, dict[str, Any]] | None = None,
    discovery: dict[str, Any] | None = None,
    project: Path | None = None,
) -> probe.SessionRecord:
    """A record of a correct `camel-rename` run, unless the caller passes wrong parts."""
    steps = EXPECTED_CAMEL_STEPS if steps is None else steps
    record = build_record(steps, discovery or camel_discovery(), name="camel-rename")
    record.project = project
    return record


def camel_results_by_name(
    record: probe.SessionRecord,
) -> dict[str, probe.CheckResult]:
    return {r.name: r for r in probe.evaluate(record, probe.CAMEL_CHECKS)}


def test_the_camel_session_is_the_third_session_and_renames_events() -> None:
    assert [session.name for session in probe.SESSIONS] == [
        "main",
        "codex-patch",
        "camel-rename",
    ]
    assert probe.SESSIONS[2].checks == probe.CAMEL_CHECKS
    assert probe.SESSIONS[2].renamed_events is True
    assert not any(session.renamed_events for session in probe.SESSIONS[:2])
    assert probe.CAMEL_EVENT_NAMES == CAMEL_EVENT_NAMES


def test_the_camel_session_has_the_planned_checks_in_order() -> None:
    assert [c.name for c in probe.CAMEL_CHECKS] == EXPECTED_CAMEL_CHECK_NAMES


def test_the_camel_scenario_has_one_step_per_twin_of_the_baseline_step() -> None:
    project = Path("/work/project-camel")
    baseline = probe.baseline_scenario(project)
    scenario = probe.camel_rename_scenario(project)
    steps: dict[str, dict[str, Any]] = {
        step["label"]: step  # type: ignore[index]
        for step in scenario["steps"]  # type: ignore[attr-defined]
    }
    twins: dict[str, dict[str, Any]] = {
        step["label"]: step  # type: ignore[index]
        for step in baseline["steps"]  # type: ignore[attr-defined]
    }

    assert scenario["name"] == "camel-rename"
    assert list(steps) == list(CAMEL_TWINS)
    for label, twin in CAMEL_TWINS.items():
        assert steps[label]["tool"] == twins[twin]["tool"]
        assert steps[label]["args"] == twins[twin]["args"]
    # The paths name the copy the session runs in, not another project.
    assert steps["camel-deny-secret-rm"]["args"]["command"] == "rm -f .env"
    assert steps["camel-ask-vscode-settings"]["args"]["path"] == str(
        project / ".vscode" / "settings.json"
    )


def test_a_correct_camel_run_passes_every_check(tmp_path: Path) -> None:
    record = build_camel_record(project=write_camel_project(tmp_path))

    results = probe.evaluate(record, probe.CAMEL_CHECKS)

    assert [r.name for r in results] == EXPECTED_CAMEL_CHECK_NAMES
    assert [r.status for r in results] == [probe.PASS] * len(EXPECTED_CAMEL_CHECK_NAMES)


# The nested-only answer is ignored under camelCase names (F4): the tool runs.
WRONG_CAMEL_DENY_RESULTS = {
    "ran": {"tool": "bash", "success": True},
    "other-reason": {"tool": "bash", "reason": "some other reason"},
}
WRONG_CAMEL_RESULTS = {
    **dict.fromkeys(
        (
            "camel-deny-git-reset",
            "camel-deny-secret-rm",
            "camel-deny-commit",
            "camel-deny-branch",
            "camel-deny-pr",
        ),
        WRONG_CAMEL_DENY_RESULTS,
    ),
    "camel-ask-vscode-settings": {
        "denied": {"tool": "create", "reason": "Protected"},
        "no-question": {"tool": "create", "questions": ("write",)},
    },
    "camel-ask-agent-wrapper": {
        "denied": {"tool": "edit", "reason": "Protected"},
        "no-question": {"tool": "edit", "success": False},
    },
    "camel-allow-plain": {
        "denied": {"tool": "edit", "reason": "Protected"},
        "asked": {"tool": "edit", "questions": ("hook", "write")},
    },
}


@pytest.mark.parametrize(
    ("check", "wrong_step"),
    [
        pytest.param(check, wrong, id=f"{check}-{kind}")
        for check, variants in WRONG_CAMEL_RESULTS.items()
        for kind, wrong in variants.items()
    ],
)
def test_each_camel_check_fails_on_a_wrong_result_and_only_that_check(
    check: str, wrong_step: dict[str, Any], tmp_path: Path
) -> None:
    steps = dict(EXPECTED_CAMEL_STEPS)
    steps[CAMEL_CHECK_STEPS[check]] = wrong_step
    record = build_camel_record(steps, project=write_camel_project(tmp_path))

    results = camel_results_by_name(record)

    assert results[check].status == probe.FAIL
    assert results[check].detail
    assert [n for n, r in results.items() if r.status == probe.FAIL] == [check]


def test_a_camel_step_that_never_ran_fails_its_check(tmp_path: Path) -> None:
    steps = {k: v for k, v in EXPECTED_CAMEL_STEPS.items() if k != "camel-deny-pr"}
    record = build_camel_record(steps, project=write_camel_project(tmp_path))

    results = camel_results_by_name(record)

    assert results["camel-deny-pr"].status == probe.FAIL
    assert "did not run" in results["camel-deny-pr"].detail


def test_the_camel_ask_checks_pass_with_the_single_question_of_one_source(
    tmp_path: Path,
) -> None:
    record = build_camel_record(project=write_camel_project(tmp_path))

    result = camel_results_by_name(record)["camel-ask-agent-wrapper"]

    assert result.status == probe.PASS
    assert "1 question(s) of kind hook" in result.detail


@pytest.mark.parametrize(
    ("wrong", "expected_in_detail"),
    [
        pytest.param(
            {
                "hooks": {"hooks": [hook_row(GITHUB_HOOKS), hook_row(CLAUDE_SETTINGS)]},
                "mcp": {"servers": []},
            },
            "still load from .claude/settings.json",
            id="the-claude-settings-source-is-still-on",
        ),
        pytest.param(
            {"hooks": {"hooks": []}, "mcp": {"servers": []}},
            "no preToolUse hook from .github/hooks/hooks.json",
            id="no-hooks-at-all",
        ),
        pytest.param(
            {
                "hooks": {"hooks": [hook_row(GITHUB_HOOKS, "sessionStart")]},
                "mcp": {"servers": []},
            },
            "no preToolUse hook from .github/hooks/hooks.json",
            id="no-guard-event",
        ),
        pytest.param(
            {
                "hooks": {
                    "hooks": [
                        hook_row(GITHUB_HOOKS),
                        hook_row("file:///work/project/.github/hooks/evil.json"),
                    ]
                },
                "mcp": {"servers": []},
            },
            "another file",
            id="a-third-hook-file",
        ),
    ],
)
def test_camel_hooks_source_fails_unless_only_the_copilot_file_loads(
    wrong: dict[str, Any], expected_in_detail: str, tmp_path: Path
) -> None:
    record = build_camel_record(
        discovery=camel_discovery(trusted=wrong), project=write_camel_project(tmp_path)
    )

    results = camel_results_by_name(record)

    assert results["camel-hooks-source"].status == probe.FAIL
    assert expected_in_detail in results["camel-hooks-source"].detail
    assert [n for n, r in results.items() if r.status == probe.FAIL] == [
        "camel-hooks-source"
    ]


def test_camel_hooks_source_fails_without_a_recorded_discovery(tmp_path: Path) -> None:
    discovery = {k: v for k, v in camel_discovery().items() if k != "trusted"}
    record = build_camel_record(
        discovery=discovery, project=write_camel_project(tmp_path)
    )

    result = camel_results_by_name(record)["camel-hooks-source"]

    assert result.status == probe.FAIL
    assert "no hook list was recorded" in result.detail


def test_camel_events_renamed_reads_the_files_left_after_the_session(
    tmp_path: Path,
) -> None:
    result = camel_results_by_name(
        build_camel_record(project=write_camel_project(tmp_path))
    )["camel-events-renamed"]

    assert result.status == probe.PASS
    assert "sessionStart" in result.detail


def pascal_case(path: Path) -> None:
    """Put the original event names back, as the restore script would."""
    path.write_text(
        json.dumps({"version": 1, "hooks": dict.fromkeys(CAMEL_EVENT_NAMES, [])}),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("damage", "expected_in_detail"),
    [
        pytest.param(
            lambda root: pascal_case(root / LIVE_COPY),
            "hooks/hooks.json has events",
            id="the-live-file-went-back-to-pascal-case",
        ),
        pytest.param(
            lambda root: pascal_case(root / RESTORE_COPY),
            "bootstrap-root",
            id="the-restore-copy-would-undo-the-rename-at-the-next-start",
        ),
        pytest.param(
            lambda root: (root / LIVE_COPY).write_text("{", encoding="utf-8"),
            "cannot read",
            id="the-live-file-is-not-json",
        ),
        pytest.param(
            lambda root: (root / LIVE_COPY).unlink(),
            "cannot read",
            id="the-live-file-is-gone",
        ),
        pytest.param(
            lambda root: (root / ".claude" / "settings.json").write_text(
                "{}", encoding="utf-8"
            ),
            "settings.json is back",
            id="the-claude-settings-came-back",
        ),
        pytest.param(
            lambda root: (root / ".claude" / "settings.json.off").unlink(),
            "settings.json.off",
            id="the-claude-settings-were-never-switched-off",
        ),
    ],
)
def test_camel_events_renamed_fails_when_the_setup_did_not_survive(
    damage: Any, expected_in_detail: str, tmp_path: Path
) -> None:
    project = write_camel_project(tmp_path)
    damage(project)

    results = camel_results_by_name(build_camel_record(project=project))

    assert results["camel-events-renamed"].status == probe.FAIL
    assert expected_in_detail in results["camel-events-renamed"].detail
    assert [n for n, r in results.items() if r.status == probe.FAIL] == [
        "camel-events-renamed"
    ]


def test_camel_events_renamed_fails_when_no_project_was_recorded() -> None:
    result = camel_results_by_name(build_camel_record(project=None))[
        "camel-events-renamed"
    ]

    assert result.status == probe.FAIL
    assert "no project folder was recorded" in result.detail


@pytest.fixture(scope="module")
def installed_project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A project from the real installer. The tests below only copy it."""
    return probe.prepare_project(tmp_path_factory.mktemp("installed"))


def hook_events(path: Path) -> list[str]:
    events: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))["hooks"]
    return list(events)


def test_prepare_camel_project_renames_the_events_in_a_copy_only(
    installed_project: Path, tmp_path: Path
) -> None:
    before = {
        relative: (installed_project / relative).read_text(encoding="utf-8")
        for relative in (LIVE_COPY, RESTORE_COPY)
    }

    copy = probe.prepare_camel_project(installed_project, tmp_path)

    assert copy.parent == tmp_path
    assert copy != installed_project
    for relative in (LIVE_COPY, RESTORE_COPY):
        assert hook_events(copy / relative) == list(CAMEL_EVENT_NAMES.values())
        # Only the keys change: every hook command is the one of the original.
        original = json.loads(before[relative])["hooks"]
        renamed = json.loads((copy / relative).read_text(encoding="utf-8"))["hooks"]
        assert list(renamed.values()) == list(original.values())
        # The original project keeps its names.
        assert (installed_project / relative).read_text(encoding="utf-8") == before[
            relative
        ]
    assert not (copy / ".claude" / "settings.json").exists()
    assert (copy / ".claude" / "settings.json.off").is_file()
    assert (installed_project / ".claude" / "settings.json").is_file()
    assert not (installed_project / ".claude" / "settings.json.off").exists()
    assert not (copy / ".mcp.json").exists()


def test_the_session_start_restore_hook_keeps_the_camel_rename(
    installed_project: Path, tmp_path: Path
) -> None:
    """Regression: `state-sync.sh pull` runs the restore script at SessionStart,
    and the restore script copies `.claude/bootstrap-root/.github/hooks` back over
    the live file. The rename is applied to both, so it survives."""
    copy = probe.prepare_camel_project(installed_project, tmp_path)
    restore = copy / ".claude" / "hooks" / "scripts" / "restore-root-adapters.sh"

    done = subprocess.run(
        ["bash", str(restore)], cwd=copy, text=True, capture_output=True, check=False
    )

    assert done.returncode == 0, done.stderr
    assert hook_events(copy / LIVE_COPY) == list(CAMEL_EVENT_NAMES.values())
    assert not (copy / ".claude" / "settings.json").exists()
    assert not (copy / ".mcp.json").exists()


def test_a_rename_of_only_the_live_file_is_undone_by_the_restore_hook(
    installed_project: Path, tmp_path: Path
) -> None:
    """The control for the test above: with the restore copy left alone, the
    restore script puts the original names back, so renaming the live file
    alone would not make a camelCase session."""
    copy = tmp_path / "copy"
    shutil.copytree(installed_project, copy, symlinks=True)
    live = copy / LIVE_COPY
    hooks = json.loads(live.read_text(encoding="utf-8"))
    hooks["hooks"] = {
        CAMEL_EVENT_NAMES[name]: value for name, value in hooks["hooks"].items()
    }
    live.write_text(json.dumps(hooks), encoding="utf-8")
    assert hook_events(live) == list(CAMEL_EVENT_NAMES.values())  # renamed first
    restore = copy / ".claude" / "hooks" / "scripts" / "restore-root-adapters.sh"

    done = subprocess.run(
        ["bash", str(restore)], cwd=copy, text=True, capture_output=True, check=False
    )

    assert done.returncode == 0, done.stderr
    assert hook_events(live) == list(CAMEL_EVENT_NAMES)


@pytest.mark.parametrize("missing", sorted(CAMEL_EVENT_NAMES))
def test_prepare_camel_project_refuses_a_hook_file_without_an_expected_event(
    missing: str, tmp_path: Path
) -> None:
    project = tmp_path / "project"
    for relative in (LIVE_COPY, RESTORE_COPY):
        (project / relative).parent.mkdir(parents=True)
        hooks: dict[str, list[Any]] = {
            name: [] for name in CAMEL_EVENT_NAMES if name != missing
        }
        (project / relative).write_text(json.dumps({"hooks": hooks}), encoding="utf-8")
    (project / ".claude" / "settings.json").write_text("{}", encoding="utf-8")

    with pytest.raises(RuntimeError, match=missing):
        probe.prepare_camel_project(project, tmp_path / "work")


@pytest.mark.parametrize(
    "content",
    ("{", "[]", '{"hooks": []}', '{"version": 1}'),
    ids=lambda c: c or "empty",
)
def test_prepare_camel_project_refuses_a_hook_file_it_cannot_read(
    content: str, tmp_path: Path
) -> None:
    project = write_camel_project(tmp_path / "project")
    (project / LIVE_COPY).write_text(content, encoding="utf-8")

    with pytest.raises(RuntimeError, match="cannot read the events of"):
        probe.prepare_camel_project(project, tmp_path / "work")


def test_prepare_camel_project_refuses_a_project_whose_settings_are_missing(
    tmp_path: Path,
) -> None:
    project = write_camel_project(tmp_path / "project", settings="none")
    for relative in (LIVE_COPY, RESTORE_COPY):
        pascal_case(project / relative)

    with pytest.raises(RuntimeError, match="settings.json"):
        probe.prepare_camel_project(project, tmp_path / "work")


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

        def fake_prepare_camel(project: Path, work: Path) -> Path:
            return write_camel_project(work / "project-camel")

        monkeypatch.setattr(probe, "prepare_project", fake_prepare)
        monkeypatch.setattr(probe, "prepare_camel_project", fake_prepare_camel)
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
            return record_for(scenario, project)

        monkeypatch.setattr(probe, "run_session", fake_session)

        code = probe.main([])

        out = capsys.readouterr().out
        assert code == 0
        # main and codex-patch share a project; camel-rename has its own copy
        assert len(calls) == 3
        assert [project.name for project, _, _ in calls] == [
            "project",
            "project",
            "project-camel",
        ]
        assert len({home for _, home, _ in calls}) == 1
        assert "VS Code commit: 69047191fc427f2f92828279aae1d90d8eeda7ab" in out
        assert "SDK version: 1.0.30-preview.0" in out
        assert "runtime version: 1.0.108-0" in out
        assert len(re.findall(r"^PASS ", out, re.MULTILINE)) == (
            3
            + len(EXPECTED_CHECK_NAMES)
            + len(EXPECTED_PATCH_CHECK_NAMES)
            + len(EXPECTED_CAMEL_CHECK_NAMES)
        )
        assert "FAIL" not in out
        assert "PASS session-main:" in out
        assert "PASS session-codex-patch:" in out
        assert "PASS session-camel-rename:" in out
        assert "PASS camel-deny-git-reset:" in out
        assert "Tool inventory, session main" in out
        assert "Tool inventory, session codex-patch" in out
        assert "Tool inventory, session camel-rename" in out
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
                else record_for(scenario, project)
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
                else record_for(scenario, project)
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

    def test_the_camel_copy_is_made_before_any_session_touches_the_project(
        self,
        fake_runtime: probe.RuntimeInfo,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        order: list[str] = []
        make_copy = probe.prepare_camel_project

        def copy_first(project: Path, work: Path) -> Path:
            order.append("copy")
            return make_copy(project, work)

        def fake_session(
            runtime: probe.RuntimeInfo,
            project: Path,
            scenario: dict[str, object],
            home: Path,
            timeout: float = 0,
        ) -> probe.SessionRecord:
            order.append(str(scenario["name"]))
            return record_for(scenario, project)

        monkeypatch.setattr(probe, "prepare_camel_project", copy_first)
        monkeypatch.setattr(probe, "run_session", fake_session)

        probe.main([])

        # The first sessions leave files behind (`probe-plain.txt`), so a copy made
        # later would not be a fresh project.
        assert order == ["copy", "main", "codex-patch", "camel-rename"]

    def test_a_camel_copy_that_cannot_be_made_is_a_project_fail(
        self,
        fake_runtime: probe.RuntimeInfo,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        started: list[str] = []

        def broken(project: Path, work: Path) -> Path:
            raise RuntimeError("the hook file has no PreToolUse event")

        monkeypatch.setattr(probe, "prepare_camel_project", broken)
        monkeypatch.setattr(
            probe, "run_session", lambda *args, **kwargs: started.append("x")
        )

        code = probe.main([])

        assert code == 1
        assert started == []
        assert re.search(
            r"^FAIL project: the hook file has no PreToolUse event",
            capsys.readouterr().out,
            re.MULTILINE,
        )

    def test_the_session_gets_at_most_the_session_limit(
        self,
        fake_runtime: probe.RuntimeInfo,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        timeouts: list[float] = []

        def fake_session(*args: Any, **kwargs: Any) -> probe.SessionRecord:
            timeouts.append(kwargs["timeout"])
            return record_for(args[2], args[1])

        monkeypatch.setattr(probe, "run_session", fake_session)

        probe.main([])

        assert len(timeouts) == 3
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
        # Variables that aim a command at another repository.
        monkeypatch.setenv("GIT_DIR", "/work/other/.git")
        monkeypatch.setenv("GIT_WORK_TREE", "/work/other")
        monkeypatch.setenv("GH_REPO", "owner/other")
        monkeypatch.setenv("AI_STATE_REPO_ROOT", "/work/other")
        monkeypatch.setenv("AI_STATE_LOCAL_ONLY", "1")
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
        # Never guess an identity from the user and host name: a missing
        # identity then fails on every host, not only on hosts that cannot guess.
        # The setting is in the home folder's config file, because the probe now
        # drops every GIT_ variable (so GIT_CONFIG_COUNT and GIT_CONFIG_NOSYSTEM
        # would no longer arrive). A system-wide identity, on a host that has
        # one, can no longer be switched off for the child.
        (home / ".gitconfig").write_text("[user]\n\tuseConfigOnly = true\n")
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

    def test_the_installer_gets_the_filtered_environment_and_the_probes_own_values(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """No `GIT_`, `GH_`, `AI_STATE_`, agent, or token variable reaches the
        installer except the probe's own identity and empty state remote; other
        variables still arrive."""
        script = self.installer(
            tmp_path,
            "project = pathlib.Path(sys.argv[1])\n"
            "(project / '.claude').mkdir()\n"
            "(project / '.claude' / 'bootstrap-ownership.env').write_text("
            "'BOOTSTRAP_ROOT_PATH=AGENTS.md\\n')\n"
            "(project.parent / 'seen.json').write_text(json.dumps(dict(os.environ)))\n",
        )
        monkeypatch.setattr(probe, "INSTALLER", script)
        for name, value in {
            "GIT_DIR": "/work/other/.git",
            "GIT_WORK_TREE": "/work/other",
            "GIT_CONFIG_COUNT": "1",
            "GIT_AUTHOR_NAME": "Host Person",
            "GH_REPO": "owner/other",
            "GH_TOKEN": "ghp_example",
            "GITHUB_TOKEN": "ghp_example",
            "CLAUDE_PROJECT_DIR": "/work/agent",
            "ANTHROPIC_API_KEY": "sk-ant-example",
            "AI_STATE_REMOTE": "https://example.invalid/state.git",
            "AI_STATE_REPO_ROOT": "/work/other",
            "AI_STATE_LOCAL_ONLY": "1",
            "AI_STATE_BRANCH": "other-branch",
            "PROBE_KEPT_VARIABLE": "kept",
        }.items():
            monkeypatch.setenv(name, value)
        parent = tmp_path / "parent"
        parent.mkdir()

        probe.prepare_project(parent)

        seen = json.loads((parent / "seen.json").read_text("utf-8"))
        assert [n for n in seen if n.startswith(("CLAUDE", "ANTHROPIC", "GH_"))] == []
        assert "GITHUB_TOKEN" not in seen
        assert sorted(n for n in seen if n.startswith("GIT_")) == [
            "GIT_AUTHOR_EMAIL",
            "GIT_AUTHOR_NAME",
            "GIT_COMMITTER_EMAIL",
            "GIT_COMMITTER_NAME",
        ]
        assert seen["GIT_AUTHOR_NAME"] == "Copilot Probe"
        assert [n for n in seen if n.startswith("AI_STATE_")] == ["AI_STATE_REMOTE"]
        assert seen["AI_STATE_REMOTE"] == ""
        assert seen["PROBE_KEPT_VARIABLE"] == "kept"
        assert seen["PATH"] == os.environ["PATH"]

    def test_a_host_git_dir_and_work_tree_do_not_move_the_project(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With `GIT_DIR`, `GIT_WORK_TREE`, and `AI_STATE_REPO_ROOT` aimed at another
        folder, `git init` and the real installer still work in the temporary
        project and leave that folder alone."""
        other = tmp_path / "other"
        other.mkdir()
        (other / "keep.txt").write_text("untouched\n", encoding="utf-8")
        monkeypatch.setenv("GIT_DIR", str(other / ".git"))
        monkeypatch.setenv("GIT_WORK_TREE", str(other))
        monkeypatch.setenv("GH_REPO", "owner/other")
        monkeypatch.setenv("AI_STATE_REPO_ROOT", str(other))
        parent = tmp_path / "parent"
        parent.mkdir()

        project = probe.prepare_project(parent)

        assert project == parent / "project"
        assert (project / ".git").is_dir()
        assert (project / ".claude" / "bootstrap-ownership.env").is_file()
        assert sorted(path.name for path in other.iterdir()) == ["keep.txt"]

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
