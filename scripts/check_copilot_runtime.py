#!/usr/bin/env python3
"""Opt-in, offline check of the real Copilot runtime that ships inside VS Code.

The probe starts the runtime through its own SDK, with VS Code's `node`, a
private data folder, and no login. A small server on 127.0.0.1 plays the model
and returns scripted tool calls, so no model call is made and no account is
needed. The runtime works in a fresh full install of this bootstrap in a
temporary folder whose `.mcp.json` is removed, so no MCP server starts. A third
session runs in a copy of that folder whose hook events have the documented
camelCase names and whose Claude settings source is off.

It does not exercise VS Code's own layer: approval dialogs, "Allow all", or the
tool set VS Code gives each model. Nothing in the test suite, a hook, or
`verify.py` calls it; run it by hand:

    uv run python scripts/check_copilot_runtime.py --require
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
INSTALLER = SCRIPTS_DIR / "install_bootstrap.py"
PROBE_SCRIPT = SCRIPTS_DIR / "copilot_runtime_probe.mjs"
SESSION_LIMIT_SECONDS = 150
RUN_LIMIT_SECONDS = 480
# The runtime waits this long for the scripted conversation; the hard limit
# above also covers start-up, discovery, and shutdown.
SEND_TIMEOUT_MS = 120_000
PASS, WARN, FAIL = "PASS", "WARN", "FAIL"

SDK_ENTRY = Path("node_modules") / "@github" / "copilot-sdk" / "dist" / "index.js"
# Names starting with these belong to the agent that started the probe (the
# hooks inherit the runtime's environment); CLAUDECODE is covered by CLAUDE.
# GIT_ and GH_ names can point a command at another repository (GIT_DIR,
# GIT_WORK_TREE, GH_REPO), so a to-be-denied command that runs because of a
# broken guard could act outside the temporary project. GH_TOKEN is covered.
# AI_STATE_ names steer `state-sync.sh`: an ambient AI_STATE_REPO_ROOT would aim
# the session hooks at another repository, and AI_STATE_LOCAL_ONLY would keep the
# pull line that `state-sync-once` counts from being written.
DROPPED_PREFIXES = ("CLAUDE", "ANTHROPIC", "GIT_", "GH_", "AI_STATE_")
# Tokens that would give the runtime an account to sign in with.
DROPPED_NAMES = frozenset({"GITHUB_TOKEN", "COPILOT_GITHUB_TOKEN"})
HOOK_FILES = (".github/hooks/hooks.json", ".claude/settings.json")
GUARD_EVENT = "preToolUse"
DENIED_PREFIX = "Denied by preToolUse hook: "
BRANCH_GUARD_REASONS = (
    "implementation branch must be named",
    "implementation branches must be created from dev",
    "working tree must be clean before creating an implementation branch",
    "missing big-plan file for branch",
)
ABSENT = "no pre-tool hook event"
CHILD_MARKER = "PROBE-CHILD-general"
# The custom sub-agents the `main` session starts (Phase E); each task prompt carries
# its own marker, which keys the first request the runner records for it.
CUSTOM_AGENTS = ("coder", "reviewer")
# The first heading of the generated `.github/copilot-instructions.md`.
GUIDANCE_HEADING = "GitHub Copilot Workspace Adapter"
# The fixed line `subagent-context.sh` adds, and the reminder `reporting-reminder.sh`
# prints at session start. Tests pin both to the shipped scripts.
SUBAGENT_LINE = (
    "Agent files live in `.claude/agents/<id>.md` and skills live in "
    "`.claude/skills/<name>/SKILL.md`. When your agent file lists a skill, read "
    "its SKILL.md file with the read tool."
)
REMINDER_TEXT = (
    "For user-facing updates, use direct language; explain internal labels and "
    "uncommon abbreviations, and avoid idioms. State what options mean in "
    "practice. Preserve exact technical text."
)
WORKFLOW_DENIAL = "Tool blocked by policy"
SQL_REFUSAL = "Blocked SQL statement"
# The documented camelCase names of the events the hook file uses (Phase C).
CAMEL_EVENT_NAMES = {
    "SessionStart": "sessionStart",
    "PreToolUse": "preToolUse",
    "PostToolUse": "postToolUse",
    "Stop": "agentStop",
    "SubagentStart": "subagentStart",
}
LIVE_HOOK_FILE = Path(".github/hooks/hooks.json")
# `state-sync.sh pull` (a SessionStart hook) runs `restore-root-adapters.sh`, which
# copies this mirror over the live file; a rename of the live file alone is undone
# during the first session. The rename is applied to both.
RESTORE_HOOK_FILE = Path(".claude/bootstrap-root/.github/hooks/hooks.json")
CLAUDE_SETTINGS_FILE = Path(".claude/settings.json")
CLAUDE_SETTINGS_OFF = Path(".claude/settings.json.off")
HOOKS_SESSIONS_LOG = Path(".claude/session_logs/hooks-sessions.log")
HOOKS_ERRORS_LOG = Path(".claude/session_logs/hooks-errors.log")
# What `state-sync.sh pull` appends to the errors log, after a timestamp, in a
# project with no state remote (the probe project has none): one line per run.
PULL_TEXT = "state-sync: no state remote configured; nothing to pull from."
# The step that creates `.vscode/settings.json`: a protected config, so each
# hook source that runs the guard raises one question for it.
PROTECTED_CREATE_STEP = "ask-vscode-settings"


@dataclass(frozen=True)
class RuntimeInfo:
    """A VS Code server folder that holds `node` and the Copilot SDK."""

    node: Path
    sdk_root: Path
    sdk_version: str
    vscode_commit: str


@dataclass
class SessionRecord:
    """What one probe session recorded.

    Attributes:
        name: Session name.
        events: Every session event, as the runtime emitted it.
        summary: The runner's `record.json` (status, discovery, step ids, tools).
        failure: Why the session did not finish (limit, crash, runtime error), or "".
        project: The folder the session ran in, so a check can read the files the
            session left behind.
    """

    name: str = "main"
    events: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)
    failure: str = ""
    project: Path | None = None


@dataclass(frozen=True)
class CheckResult:
    """The outcome of one check."""

    name: str
    status: str
    detail: str


@dataclass(frozen=True)
class Check:
    """A named expectation. `judge` returns (passed, detail)."""

    name: str
    judge: Callable[[SessionRecord], tuple[bool, str]]


@dataclass(frozen=True)
class Session:
    """One scripted session: how to build its scenario and what to check.

    `renamed_events` runs the session in the copy of the project that has
    camelCase hook events and no Claude settings source.
    """

    name: str
    scenario: Callable[[Path], dict[str, object]]
    checks: tuple[Check, ...]
    renamed_events: bool = False


@dataclass(frozen=True)
class LimitedRun:
    """The outcome of a process run under a time limit."""

    returncode: int | None
    stdout: str
    stderr: str
    timed_out: bool


@dataclass
class ToolRun:
    """What the events say about one tool call."""

    tool: str = ""
    pre_hook: bool = False
    deny: str | None = None
    questions: list[str] = field(default_factory=list)
    success: bool | None = None
    result: str = ""


# --- runtime, environment, project ----------------------------------------


def _runtime_in(folder: Path) -> RuntimeInfo | None:
    node = folder / "node"
    sdk_root = (folder / SDK_ENTRY).parents[1]
    if not (node.is_file() and (folder / SDK_ENTRY).is_file()):
        return None
    version = "unknown"
    with contextlib.suppress(OSError, ValueError, AttributeError):
        manifest = json.loads((sdk_root / "package.json").read_text(encoding="utf-8"))
        version = str(manifest.get("version") or version)
    return RuntimeInfo(node, sdk_root, version, folder.name)


def find_runtime(vscode_bin: Path | None = None) -> RuntimeInfo | None:
    """Find the VS Code server folder to run.

    Args:
        vscode_bin: A folder that holds `node` and the SDK; skips discovery. A
            relative path is resolved against the current folder.

    Returns:
        The runtime, or None. Without `vscode_bin`, the folder under
        `~/.vscode-server/bin/` with the newest modification time that holds
        both `node` and the SDK.
    """
    if vscode_bin is not None:
        # Absolute, because node is started in another folder.
        return _runtime_in(vscode_bin.expanduser().resolve())
    root = Path.home() / ".vscode-server" / "bin"
    folders = sorted(
        (path for path in root.glob("*") if path.is_dir()),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    return next((r for r in map(_runtime_in, folders) if r is not None), None)


def runtime_environment(base: Mapping[str, str]) -> dict[str, str]:
    """Return `base` without agent, Git, GitHub CLI, and AI-state variables or tokens.

    The runtime, the temporary project's `git init`, and its installer all get this.
    """
    return {
        key: value
        for key, value in base.items()
        if not key.startswith(DROPPED_PREFIXES) and key not in DROPPED_NAMES
    }


def prepare_project(parent: Path, deadline: float | None = None) -> Path:
    """Install a fresh full copy of this bootstrap, without MCP servers.

    Args:
        parent: An existing folder; the project is created inside it.
        deadline: A `time.monotonic()` time by which the whole run must end; the
            commands share what is left. Default: the run limit, from now.

    Returns:
        The project folder: `git init -b dev`, no commit, `.mcp.json` removed,
        and a one-line `README.md` for the plain read step.

    Raises:
        RuntimeError: If git or the installer fails, cannot start, or runs out
            of time.
    """
    project = parent / "project"
    project.mkdir()
    if deadline is None:
        deadline = time.monotonic() + RUN_LIMIT_SECONDS
    # The runtime's filtered environment, so a host GIT_DIR, GIT_WORK_TREE, or
    # GH_REPO cannot aim `git init` or the installer at another repository. Then
    # what is set on purpose: no state remote, and a fixed identity because
    # `state-sync.sh setup` makes a plain `git commit` and a host may have none.
    env = {
        **runtime_environment(os.environ),
        "AI_STATE_REMOTE": "",
        "GIT_AUTHOR_NAME": "Copilot Probe",
        "GIT_AUTHOR_EMAIL": "probe@example.com",
        "GIT_COMMITTER_NAME": "Copilot Probe",
        "GIT_COMMITTER_EMAIL": "probe@example.com",
    }
    commands = (
        ["git", "init", "-q", "-b", "dev", str(project)],
        [
            sys.executable,
            str(INSTALLER),
            str(project),
            "--mode",
            "full",
            "--local-only",
        ],
    )
    for command in commands:
        name = " ".join(command[:2])
        left = deadline - time.monotonic()
        if left <= 0:
            raise RuntimeError(f"{name} not started: the run limit is used up")
        try:
            done = run_limited(command, cwd=REPO_ROOT, env=env, timeout=left)
        except OSError as error:
            raise RuntimeError(f"{name} cannot start: {error}") from error
        if done.timed_out:
            raise RuntimeError(f"{name} timed out at the run limit")
        if done.returncode != 0:
            tail = (done.stderr.strip() or done.stdout.strip())[-500:]
            raise RuntimeError(f"{name} failed ({done.returncode}): {tail}")
    _remove_mcp_file(project)
    (project / "README.md").write_text("# probe project\n", encoding="utf-8")
    return project


def _remove_mcp_file(project: Path) -> None:
    """Remove `.mcp.json` so that it cannot come back during a session.

    The SessionStart hook `state-sync.sh pull` runs `restore-root-adapters.sh`,
    which copies every adapter named in the ownership manifest back from
    `.claude/bootstrap-root/`. Deleting only `<project>/.mcp.json` therefore
    fails: the file returns mid-session and the runtime starts the project's
    MCP servers (`npx`, `uvx`). So the mirror copy and the manifest line go too;
    a manifest line without its mirror makes the restore script stop.
    """
    (project / ".mcp.json").unlink(missing_ok=True)
    (project / ".claude" / "bootstrap-root" / ".mcp.json").unlink(missing_ok=True)
    manifest = project / ".claude" / "bootstrap-ownership.env"
    kept = [
        line
        for line in manifest.read_text(encoding="utf-8").splitlines(keepends=True)
        if line.strip() != "BOOTSTRAP_ROOT_PATH=.mcp.json"
    ]
    manifest.write_text("".join(kept), encoding="utf-8")


def _rename_events(path: Path, relative: Path) -> None:
    """Give the hook file at `path` the camelCase event names, keeping its hooks."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        hooks = data["hooks"]
        if not isinstance(hooks, dict):
            raise TypeError("`hooks` is not an object")
        missing = sorted(set(CAMEL_EVENT_NAMES) - set(hooks))
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise RuntimeError(f"cannot read the events of {relative}: {error}") from error
    if missing:
        raise RuntimeError(f"{relative} has no {', '.join(missing)} event")
    data["hooks"] = {
        CAMEL_EVENT_NAMES.get(name, name): value for name, value in hooks.items()
    }
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def prepare_camel_project(project: Path, work: Path) -> Path:
    """Copy `project` and rename its hook events to camelCase, in the copy only.

    The Claude settings file is renamed to `settings.json.off` in the copy, so only
    the Copilot hook file runs: the runtime reads `.claude/settings.json` too, and
    its PascalCase hooks would deny the same calls on their own.

    Args:
        project: The prepared project. Copy it before any session has run in it.
        work: An existing folder; the copy is created inside it.

    Returns:
        The copy, `work/project-camel`.

    Raises:
        RuntimeError: If a hook file lacks an event to rename, or the Claude
            settings file is missing.
        OSError: If the copy fails.
    """
    copy = work / "project-camel"
    shutil.copytree(project, copy, symlinks=True)
    for relative in (LIVE_HOOK_FILE, RESTORE_HOOK_FILE):
        _rename_events(copy / relative, relative)
    settings = copy / CLAUDE_SETTINGS_FILE
    if not settings.is_file():
        raise RuntimeError(f"{CLAUDE_SETTINGS_FILE} is missing from the project")
    settings.rename(copy / CLAUDE_SETTINGS_OFF)
    return copy


# --- running the runtime ---------------------------------------------------


def run_limited(
    command: Sequence[str], *, cwd: Path, env: Mapping[str, str], timeout: float
) -> LimitedRun:
    """Run `command` in its own process group and kill the group on timeout.

    Args:
        command: Program and arguments.
        cwd: Working folder.
        env: Environment for the process.
        timeout: Seconds before the whole process group is killed.

    Returns:
        The exit code, the output, and whether the limit was hit.
    """
    process = subprocess.Popen(
        list(command),
        cwd=cwd,
        env=dict(env),
        text=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    stdout = stderr = ""
    timed_out = False
    try:
        stdout, stderr = process.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
    except BaseException:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        raise
    if timed_out:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        with contextlib.suppress(subprocess.TimeoutExpired):
            stdout, stderr = process.communicate(timeout=10)
    return LimitedRun(
        None if timed_out else process.returncode, stdout, stderr, timed_out
    )


def _launch(
    runtime: RuntimeInfo, config: Mapping[str, object], timeout: float
) -> tuple[dict[str, Any], str]:
    """Run the Node runner on `config`; return its record and a failure text."""
    out = Path(str(config["outDir"]))
    out.mkdir(parents=True, exist_ok=True)
    config_file = out / "config.json"
    config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")
    try:
        run = run_limited(
            [str(runtime.node), str(PROBE_SCRIPT), str(config_file)],
            cwd=out,
            env=runtime_environment(os.environ),
            timeout=timeout,
        )
    except OSError as error:
        return {}, f"cannot start {runtime.node}: {error}"
    record: dict[str, Any] = {}
    with contextlib.suppress(OSError, ValueError):
        loaded = json.loads((out / "record.json").read_text(encoding="utf-8"))
        record = loaded if isinstance(loaded, dict) else {}
    if run.timed_out:
        return record, f"stopped after the {timeout:.0f} s limit"
    if run.returncode != 0:
        return record, f"node exited with {run.returncode}: {run.stderr.strip()[-300:]}"
    if not record:
        return record, "the runner wrote no record.json"
    errors = record.get("errors") or []
    if errors:
        return record, "runtime errors: " + "; ".join(str(e)[:200] for e in errors)
    return record, ""


def _read_events(path: Path) -> list[dict[str, Any]]:
    """Read a JSON-lines event file; skip a line cut off by a kill."""
    events: list[dict[str, Any]] = []
    with contextlib.suppress(OSError):
        for line in path.read_text(encoding="utf-8").splitlines():
            with contextlib.suppress(ValueError):
                event = json.loads(line)
                if isinstance(event, dict):
                    events.append(event)
    return events


def run_session(
    runtime: RuntimeInfo,
    project: Path,
    scenario: dict[str, object],
    home: Path,
    timeout: float = SESSION_LIMIT_SECONDS,
) -> SessionRecord:
    """Run one scripted session on the real runtime.

    Args:
        runtime: The VS Code server folder to run.
        project: The project folder the runtime works in.
        scenario: Session name, model, marker, subfolder, and scripted steps.
        home: The runtime's private data folder (also holds the folder trust).
        timeout: Seconds before the session is stopped.

    Returns:
        The recorded events and summary; `failure` is set when it did not finish.
    """
    name = str(scenario["name"])
    out = home.parent / "sessions" / name
    config = {
        "mode": "session",
        "sdkRoot": str(runtime.sdk_root),
        "baseDir": str(home),
        "project": str(project),
        "outDir": str(out),
        "scenario": scenario,
    }
    summary, failure = _launch(runtime, config, timeout)
    return SessionRecord(
        name, _read_events(out / "events.jsonl"), summary, failure, project
    )


# --- reading events --------------------------------------------------------


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def tool_runs(events: Sequence[Mapping[str, Any]]) -> dict[str, ToolRun]:
    """Group session events by tool call id, whatever their order."""
    runs: dict[str, ToolRun] = {}

    def run(call_id: object) -> ToolRun:
        return runs.setdefault(str(call_id), ToolRun())

    for event in events:
        kind, data = event.get("type"), _dict(event.get("data"))
        if kind == "tool.execution_start":
            run(data.get("toolCallId")).tool = str(data.get("toolName"))
        elif kind == "hook.start" and data.get("hookType") == GUARD_EVENT:
            for call in _dict(data.get("input")).get("toolCalls") or []:
                run(_dict(call).get("id")).pre_hook = True
        elif kind == "hook.end" and data.get("hookType") == GUARD_EVENT:
            for call_id, reason in _dict(data.get("output")).items():
                if str(reason).startswith(DENIED_PREFIX):
                    run(call_id).deny = str(reason)
        elif kind == "permission.requested":
            request = _dict(data.get("permissionRequest"))
            if request.get("toolCallId"):
                run(request["toolCallId"]).questions.append(str(request.get("kind")))
        elif kind == "tool.execution_complete":
            finished = run(data.get("toolCallId"))
            finished.success = data.get("success")
            finished.result = str(_dict(data.get("result")).get("content") or "")
    return runs


def _step_run(record: SessionRecord, step: str) -> tuple[ToolRun | None, str]:
    """The run of a scripted step, or None with the reason it did not run.

    Only scripted steps are judged. A tool run that is not one of them (the
    runtime's own read of a finished shell, probe P3) has no pre-tool hook
    event and is left alone.
    """
    call_id = _dict(record.summary.get("stepCalls")).get(step)
    if call_id is None:
        why = _dict(record.summary.get("skippedSteps")).get(step)
        return None, f"step {step} did not run" + (f" ({why})" if why else "")
    run = tool_runs(record.events).get(str(call_id))
    if run is None:
        return None, f"no event for step {step} ({call_id})"
    return run, ""


def _scripted_run(record: SessionRecord, step: str) -> tuple[ToolRun | None, str]:
    """The run of a scripted step that the pre-tool hooks saw, or None with why not."""
    run, problem = _step_run(record, step)
    if run is not None and not run.pre_hook:
        return None, f"{ABSENT} for step {step}: the hooks did not run"
    return run, problem


# --- checks ----------------------------------------------------------------


def evaluate(record: SessionRecord, checks: Sequence[Check]) -> list[CheckResult]:
    """Judge `record` with each check; a wrong result is FAIL, never skipped."""
    results = []
    for check in checks:
        passed, detail = check.judge(record)
        results.append(CheckResult(check.name, PASS if passed else FAIL, detail))
    return results


def denied(name: str, step: str, *reasons: str) -> Check:
    """The step must be denied by a preToolUse hook, with one of `reasons`."""

    def judge(record: SessionRecord) -> tuple[bool, str]:
        run, problem = _scripted_run(record, step)
        if run is None:
            return False, problem
        if run.deny is None:
            return False, f"not denied: the {run.tool} call ran (success={run.success})"
        if not any(reason in run.deny for reason in reasons):
            return False, f"denied for another reason: {run.deny}"
        if run.success is not False:
            return False, f"denied, but the tool completed (success={run.success})"
        return True, run.deny.removeprefix(DENIED_PREFIX)

    return Check(name, judge)


def asked(name: str, step: str) -> Check:
    """The step must raise a permission question of kind `hook`, and not be denied."""

    def judge(record: SessionRecord) -> tuple[bool, str]:
        run, problem = _scripted_run(record, step)
        if run is None:
            return False, problem
        if run.deny is not None:
            return False, f"denied instead of asked: {run.deny}"
        count = run.questions.count("hook")
        if count < 1:
            return (
                False,
                f"no question of kind hook (questions: {run.questions or 'none'})",
            )
        return True, f"{count} question(s) of kind hook; not denied"

    return Check(name, judge)


def allowed(name: str, *steps: str) -> Check:
    """Each step must succeed with no deny and no question of kind `hook`."""

    def judge(record: SessionRecord) -> tuple[bool, str]:
        for step in steps:
            run, problem = _scripted_run(record, step)
            if run is None:
                return False, problem
            if run.deny is not None:
                return False, f"{step} denied: {run.deny}"
            if "hook" in run.questions:
                return False, f"{step} raised a question of kind hook"
            if run.success is not True:
                return False, f"{step} did not succeed (success={run.success})"
        return True, f"{len(steps)} steps succeeded with no hook question"

    return Check(name, judge)


def not_denied(name: str, step: str) -> Check:
    """The step must get no denial and no question of kind `hook`.

    What the tool itself returns is not judged: a search for a file that does
    not exist may fail, and that is not the guard's doing.
    """

    def judge(record: SessionRecord) -> tuple[bool, str]:
        run, problem = _scripted_run(record, step)
        if run is None:
            return False, problem
        if run.deny is not None:
            return False, f"denied: {run.deny}"
        if "hook" in run.questions:
            return False, "raised a question of kind hook"
        return True, f"the {run.tool} call got no hook denial and no hook question"

    return Check(name, judge)


def refused(name: str, text: str, *steps: str) -> Check:
    """Each step must fail with `text` in the tool's own answer, not from a hook."""

    def judge(record: SessionRecord) -> tuple[bool, str]:
        for step in steps:
            run, problem = _scripted_run(record, step)
            if run is None:
                return False, problem
            if run.deny is not None:
                return False, f"{step} was denied by a hook, not refused by the tool"
            if run.success is not False or text not in run.result:
                return False, (
                    f"{step} was not refused with {text!r} "
                    f"(success={run.success}, result: {run.result[:120]!r})"
                )
        return True, f"{len(steps)} steps refused by the tool: {text}"

    return Check(name, judge)


def helpers_not_denied(name: str, *steps: str) -> Check:
    """No step may be denied by a pre-tool hook; a step with no hook event is not judged.

    The runtime's own read of a finished shell has no pre-tool hook event (probe P3),
    so a helper call with none is left alone. Each step must still have run.
    """

    def judge(record: SessionRecord) -> tuple[bool, str]:
        notes = []
        for step in steps:
            run, problem = _step_run(record, step)
            if run is None:
                return False, problem
            if run.deny is not None or DENIED_PREFIX in run.result:
                return False, f"{step} denied: {run.deny or run.result[:160]}"
            notes.append(f"{step}: " + ("not denied" if run.pre_hook else "not judged"))
        return True, "; ".join(notes)

    return Check(name, judge)


def _hook_rows(found: object) -> list[Any] | None:
    rows = _dict(_dict(found).get("hooks")).get("hooks")
    return rows if isinstance(rows, list) else None


def _hook_file(row: object) -> str:
    uri = str(_dict(row).get("definitionFileUri") or "")
    return next((name for name in HOOK_FILES if uri.endswith("/" + name)), "other")


def hooks_untrusted(record: SessionRecord) -> tuple[bool, str]:
    """Discovery before folder trust must list no hooks."""
    rows = _hook_rows(_dict(record.summary.get("discovery")).get("untrusted"))
    if rows is None:
        return False, "no hook list was recorded before trust"
    if rows:
        return False, f"{len(rows)} hooks loaded before the folder was trusted"
    return True, "0 hooks before trust"


def hooks_from_both_sources(phase: str) -> Callable[[SessionRecord], tuple[bool, str]]:
    """Discovery in `phase` must list a guard hook from each hook file."""

    def judge(record: SessionRecord) -> tuple[bool, str]:
        rows = _hook_rows(_dict(record.summary.get("discovery")).get(phase))
        if rows is None:
            return False, f"no hook list was recorded for {phase}"
        events: dict[str, set[str]] = {}
        for row in rows:
            events.setdefault(_hook_file(row), set()).add(
                str(_dict(row).get("hookType"))
            )
        missing = [
            name for name in HOOK_FILES if GUARD_EVENT not in events.get(name, set())
        ]
        counts = Counter(_hook_file(row) for row in rows)
        found = ", ".join(f"{name}: {counts[name]}" for name in HOOK_FILES)
        if missing:
            return (
                False,
                f"no {GUARD_EVENT} hook from {', '.join(missing)} (found {found})",
            )
        return True, f"{len(rows)} hooks ({found})"

    return judge


def only_copilot_hook_file(record: SessionRecord) -> tuple[bool, str]:
    """After trust, the Copilot hook file loads and the Claude settings do not."""
    rows = _hook_rows(_dict(record.summary.get("discovery")).get("trusted"))
    if rows is None:
        return False, "no hook list was recorded for trusted"
    counts = Counter(_hook_file(row) for row in rows)
    github, claude = HOOK_FILES
    if counts[claude]:
        return False, f"{counts[claude]} hooks still load from {claude}"
    if counts["other"]:
        return False, f"{counts['other']} hooks load from another file"
    if not any(
        _hook_file(row) == github and _dict(row).get("hookType") == GUARD_EVENT
        for row in rows
    ):
        return False, f"no {GUARD_EVENT} hook from {github} (found {len(rows)} hooks)"
    return True, f"{len(rows)} hooks, all from {github}"


def events_renamed(record: SessionRecord) -> tuple[bool, str]:
    """After the session, the camelCase rename and the switched-off Claude settings stand.

    The files are read after the run, so the check does not depend on when an
    event arrives. A hook that restores the original hook file would show here.
    """
    project = record.project
    if project is None:
        return False, "no project folder was recorded"
    expected = sorted(CAMEL_EVENT_NAMES.values())
    for relative in (LIVE_HOOK_FILE, RESTORE_HOOK_FILE):
        try:
            found = sorted(json.loads((project / relative).read_text("utf-8"))["hooks"])
        except (OSError, ValueError, KeyError, TypeError) as error:
            return False, f"cannot read {relative} after the session: {error}"
        if found != expected:
            return False, (
                f"{relative} has events {found} after the session, expected {expected}"
            )
    if (project / CLAUDE_SETTINGS_FILE).exists():
        return False, f"{CLAUDE_SETTINGS_FILE} is back after the session"
    if not (project / CLAUDE_SETTINGS_OFF).is_file():
        return False, f"{CLAUDE_SETTINGS_OFF} is missing after the session"
    return True, (
        f"events {', '.join(expected)} in both hook files; Claude settings still off"
    )


def _read_log(record: SessionRecord, relative: Path) -> tuple[list[str], str]:
    """The lines of a log the session left in its project, or `[]` and why not."""
    if record.project is None:
        return [], "no project folder was recorded"
    try:
        text = (record.project / relative).read_text(encoding="utf-8")
    except OSError as error:
        return [], f"cannot read {relative} after the session: {error}"
    return text.splitlines(), ""


def _session_id(record: SessionRecord) -> str:
    for event in record.events:
        if event.get("type") == "session.start":
            return str(_dict(event.get("data")).get("sessionId") or "")
    return ""


def single_session_log(record: SessionRecord) -> tuple[bool, str]:
    """The session is in the session log under `github-copilot` only.

    Both hook sources log the session start and every stop, the Copilot file as
    `target=github-copilot` and the Claude settings as `target=claude-code` (F2).
    Once the Claude-settings lifecycle hooks stand down, only the first remains.
    The log is read after the run, so the check does not depend on when an
    event arrives.
    """
    session = _session_id(record)
    if not session:
        return False, "the session recorded no session.start event with an id"
    lines, problem = _read_log(record, HOOKS_SESSIONS_LOG)
    if problem:
        return False, problem
    targets: Counter[str] = Counter()
    for line in lines:
        fields = line.split(",")
        if f"sessionId={session}" in fields:
            targets.update(
                f.removeprefix("target=") for f in fields if f.startswith("target=")
            )
    claude, copilot = targets["claude-code"], targets["github-copilot"]
    if claude:
        return False, (
            f"{claude} line(s) with target=claude-code for session {session[:8]}: "
            "the Claude-settings hooks did not stand down"
        )
    if not copilot:
        return False, f"no target=github-copilot line for session {session[:8]}"
    return True, (
        f"{copilot} target=github-copilot line(s) and no target=claude-code line "
        f"for session {session[:8]}"
    )


def state_sync_once(record: SessionRecord) -> tuple[bool, str]:
    """The errors log has exactly one state-sync pull line.

    The log carries no session id. The check relies on `main` being the first
    session to run in the probe project, so the log holds only its pulls: one
    per hook source before the Claude-settings hooks stood down, one after.
    """
    lines, problem = _read_log(record, HOOKS_ERRORS_LOG)
    if problem:
        return False, problem
    pulls = sum(line.endswith(" " + PULL_TEXT) for line in lines)
    if pulls != 1:
        return False, (
            f"{pulls} state-sync pull line(s) in {HOOKS_ERRORS_LOG}, expected exactly "
            "1 (2 means both hook sources ran it)"
        )
    return True, f"1 state-sync pull line in {HOOKS_ERRORS_LOG}"


def guards_both_sources(record: SessionRecord) -> tuple[bool, str]:
    """Creating a protected config raises one hook question per hook source.

    The guards never stand down (option B), so with both sources loaded the
    runtime raises two permission requests of kind `hook` for one protected
    create (the one-source `camel-rename` session raises one). The probe does not
    see which source raised which.
    """
    run, problem = _scripted_run(record, PROTECTED_CREATE_STEP)
    if run is None:
        return False, problem
    if run.deny is not None:
        return False, f"denied instead of asked: {run.deny}"
    count, expected = run.questions.count("hook"), len(HOOK_FILES)
    if count != expected:
        return False, (
            f"{count} question(s) of kind hook, expected {expected} "
            f"(questions: {run.questions or 'none'})"
        )
    return True, f"{count} questions of kind hook; not denied"


def session_reminder(record: SessionRecord) -> tuple[bool, str]:
    """The reporting reminder is in the first user message the model received.

    `reporting-reminder.sh session github-copilot` prints it at `SessionStart` as
    top-level `additionalContext`, the documented route for context on this
    runtime (F13). The runner records the user messages of the first model
    request, so the check reads what the model got, not what the hook printed.
    """
    messages = record.summary.get("mainFirstRequestUser")
    if not isinstance(messages, list) or not messages:
        return False, "the runner recorded no user message of the first model request"
    if REMINDER_TEXT not in str(messages[0]):
        return False, (
            f"the reminder is not in the first of the {len(messages)} user "
            "message(s) of the first model request"
        )
    return True, (
        f"the first user message holds the reminder ({len(REMINDER_TEXT)} characters)"
    )


def subagent_context(record: SessionRecord) -> tuple[bool, str]:
    """Each custom sub-agent's first user message holds the guidance and the fixed line.

    `subagent-context.sh` answers `SubagentStart` with the text of
    `.github/copilot-instructions.md` and one fixed line (F9: a custom sub-agent
    otherwise gets only its agent file). The runner records the user messages of
    each sub-agent's first model request, keyed by the marker in its task prompt.
    """
    requests = _dict(record.summary.get("subagentFirstRequests"))
    for agent in CUSTOM_AGENTS:
        messages = _dict(requests.get(f"PROBE-CHILD-{agent}")).get("user")
        if not isinstance(messages, list) or not messages:
            return False, (
                f"no first request was recorded for sub-agent {agent}: it did not start"
            )
        first = str(messages[0])
        missing = [
            what
            for what, text in (
                (f"the heading {GUIDANCE_HEADING!r}", GUIDANCE_HEADING),
                ("the fixed line", SUBAGENT_LINE),
            )
            if text not in first
        ]
        if missing:
            return False, (
                f"the first user message of sub-agent {agent} lacks {' and '.join(missing)}"
            )
    return True, (
        f"the first user message of each of {' and '.join(CUSTOM_AGENTS)} holds the "
        f"heading {GUIDANCE_HEADING!r} and the fixed line"
    )


def mcp_none(record: SessionRecord) -> tuple[bool, str]:
    """No MCP server after trust or in the session, and no MCP file after the session.

    The last condition does not depend on timing: if a hook puts the project's
    `.mcp.json` back, the runtime may start its servers later, whether or not one
    started before the session ended.
    """
    found = _dict(_dict(record.summary.get("discovery")).get("trusted"))
    servers = _dict(found.get("mcp")).get("servers")
    if not isinstance(servers, list):
        return False, "no MCP discovery was recorded after trust"
    if servers:
        return False, "discovered MCP servers: " + ", ".join(
            str(_dict(s).get("name")) for s in servers
        )
    for event in record.events:
        data = _dict(event.get("data"))
        if event.get("type") == "session.mcp_server_status_changed":
            return False, f"the session reported MCP server {data.get('serverName')}"
        if event.get("type") == "session.mcp_servers_loaded" and data.get("servers"):
            return False, "the session loaded MCP servers"
    file_after = record.summary.get("mcpFileAfterSession")
    if file_after is True:
        return (
            False,
            "the project has a .mcp.json after the session: a hook put it back",
        )
    if file_after is not False:
        return (
            False,
            "the runner did not record whether .mcp.json exists after the session",
        )
    return True, "0 MCP servers discovered or started; no .mcp.json after the session"


def _step(label: str, tool: str, **args: object) -> dict[str, object]:
    return {"label": label, "tool": tool, "args": args}


def _shell(label: str, command: str, **args: object) -> dict[str, object]:
    return _step(
        label, "bash", command=command, description=f"probe step {label}", **args
    )


def _patch(label: str, patch: str) -> dict[str, object]:
    """A free-form call: the text is the whole input, as the patch tool takes it."""
    return {"label": label, "tool": "apply_patch", "input": patch}


def baseline_scenario(project: Path) -> dict[str, object]:
    """The scripted tool calls of the baseline session, in the plan's table order."""
    step, shell = _step, _shell
    plain = str(project / "probe-plain.txt")
    return {
        "name": "main",
        "model": "probe-model",
        "marker": "PROBE-MARKER",
        "subfolder": "docs/deeper",
        "timeoutMs": SEND_TIMEOUT_MS,
        "steps": [
            shell("deny-git-reset", "git reset --hard HEAD"),
            shell("deny-force-push", "git push --force origin dev"),
            shell("deny-secret-rm", "rm -f .env"),
            step("deny-secret-view", "view", path=str(project / ".env")),
            step(
                "ask-vscode-settings",
                "create",
                path=str(project / ".vscode" / "settings.json"),
                file_text="{}\n",
            ),
            step(
                "ask-agent-wrapper",
                "edit",
                path=str(project / ".github" / "agents" / "coder.agent.md"),
                old_str="PROBE-NO-SUCH-TEXT",
                new_str="x",
            ),
            shell("deny-branch", "git checkout -b probe_implementation"),
            shell("deny-commit", "git commit -m probe"),
            shell("deny-pr", "gh pr create --base dev --title probe --body probe"),
            shell("allow-plain-bash", "echo probe"),
            step("allow-plain-view", "view", path=str(project / "README.md")),
            step("allow-plain-create", "create", path=plain, file_text="probe\n"),
            step(
                "allow-plain-edit",
                "edit",
                path=plain,
                old_str="probe",
                new_str="probe two",
            ),
            # The shell helpers carry a shell id, not a command (probe P3).
            shell("helper-start", "sleep 2; echo async-done", mode="async"),
            step("helper-read", "read_bash", shellId="0", delay=1),
            step("helper-list", "list_bash"),
            step("helper-stop", "stop_bash", shellId="0"),
            step(
                "read-agent-file",
                "view",
                path=str(project / ".claude" / "agents" / "coder.md"),
            ),
            step("search-secret", "grep", pattern="SECRET", paths=[".env"]),
            step("search-glob", "glob", pattern=".env*"),
            # Tools that run code or commands outside the pre-tool hooks.
            step("deny-workflow-run", "run_dynamic_workflow", name="probe-workflow"),
            step("deny-workflow-manage", "dynamic_workflows_manage", operation="list"),
            step(
                "sql-attach",
                "sql",
                description="Attach a file",
                query=f"ATTACH DATABASE '{project / 'probe-attached.db'}' AS x",
            ),
            step(
                "sql-vacuum-into",
                "sql",
                description="Copy the database",
                query=f"VACUUM INTO '{project / 'probe-vacuum.db'}'",
            ),
            step(
                "subagent-start",
                "task",
                description="probe general",
                prompt=f"{CHILD_MARKER} run the child steps",
                agent_type="general-purpose",
                name="probe-general",
                mode="sync",
            ),
            # The custom sub-agents. They play no tool steps: the check reads the
            # first message each one received.
            *(
                step(
                    f"subagent-{agent}",
                    "task",
                    description=f"probe {agent}",
                    prompt=f"PROBE-CHILD-{agent} say ok",
                    agent_type=agent,
                    name=f"probe-{agent}",
                    mode="sync",
                )
                for agent in CUSTOM_AGENTS
            ),
        ],
        # What the sub-agent does: its own tool calls pass through the hooks too.
        "childSteps": {
            CHILD_MARKER: [
                _shell("child-git-reset", "git reset --hard HEAD"),
                _step(
                    "child-store-attach",
                    "session_store_sql",
                    description="Attach a file",
                    query=f"ATTACH DATABASE '{project / 'probe-store.db'}' AS x",
                    source="local",
                ),
            ]
        },
    }


# The patch texts of the evidence scenario `sc5_codex_patch.json`, then one with an
# indented header.
PATCH_PLAIN = (
    "*** Begin Patch\n*** Add File: probe-patch.txt\n+plain file\n*** End Patch\n"
)
PATCH_SECRET = "*** Begin Patch\n*** Add File: .env\n+SECRET=1\n*** End Patch\n"
PATCH_HOOK = (
    "*** Begin Patch\n*** Add File: .github/hooks/evil.json\n+{}\n*** End Patch\n"
)
PATCH_SERVER = (
    "*** Begin Patch\n*** Update File: .mcp.json\n@@\n-{\n+{ \n*** End Patch\n"
)
PATCH_AGENT = (
    "*** Begin Patch\n*** Delete File: .claude/agents/coder.md\n*** End Patch\n"
)
PATCH_INDENTED = (
    "*** Begin Patch\n  *** Add File: .github/hooks/evil-indented.json\n+{}\n"
    "*** End Patch\n"
)


def codex_patch_scenario(project: Path) -> dict[str, object]:
    """Patch-tool calls. Only Codex-family model ids are offered `apply_patch` offline."""
    return {
        "name": "codex-patch",
        "model": "gpt-5.2-codex",
        "marker": "PROBE-MARKER",
        "subfolder": "docs/deeper",
        "timeoutMs": SEND_TIMEOUT_MS,
        "steps": [
            _patch("patch-plain", PATCH_PLAIN),
            _patch("patch-secret", PATCH_SECRET),
            _patch("patch-hook", PATCH_HOOK),
            _patch("patch-server", PATCH_SERVER),
            _patch("patch-agent", PATCH_AGENT),
            _patch("patch-indented-hook", PATCH_INDENTED),
        ],
    }


# Each `camel-rename` step repeats the baseline step named here, with the same input.
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


def camel_rename_scenario(project: Path) -> dict[str, object]:
    """The baseline's gate steps, run where the hook events have camelCase names."""
    baseline: Any = baseline_scenario(project)["steps"]
    twins = {step["label"]: step for step in baseline}
    return {
        "name": "camel-rename",
        "model": "probe-model",
        "marker": "PROBE-MARKER",
        "subfolder": "docs/deeper",
        "timeoutMs": SEND_TIMEOUT_MS,
        "steps": [
            {**twins[twin], "label": label} for label, twin in CAMEL_TWINS.items()
        ],
    }


BASELINE_CHECKS = (
    Check("hooks-untrusted", hooks_untrusted),
    Check("hooks-sources", hooks_from_both_sources("trusted")),
    Check("hooks-subfolder", hooks_from_both_sources("subfolder")),
    Check("mcp-none", mcp_none),
    Check("single-session-log", single_session_log),
    Check("state-sync-once", state_sync_once),
    Check("session-reminder", session_reminder),
    denied("deny-git-reset", "deny-git-reset", "Blocked dangerous git operation"),
    denied("deny-force-push", "deny-force-push", "Blocked dangerous git operation"),
    denied(
        "deny-secret-rm", "deny-secret-rm", "Protected file blocked by policy: .env"
    ),
    denied(
        "deny-secret-view", "deny-secret-view", "Protected file blocked by policy: .env"
    ),
    asked("ask-vscode-settings", "ask-vscode-settings"),
    asked("ask-agent-wrapper", "ask-agent-wrapper"),
    Check("guards-both-sources", guards_both_sources),
    denied("deny-branch", "deny-branch", *BRANCH_GUARD_REASONS),
    denied("deny-commit", "deny-commit", "commit gate failed for github-copilot"),
    denied("deny-pr", "deny-pr", "PR/push gate only allows implementation branches"),
    allowed(
        "allow-plain",
        "allow-plain-bash",
        "allow-plain-view",
        "allow-plain-create",
        "allow-plain-edit",
    ),
    helpers_not_denied("helper-tools", "helper-read", "helper-list", "helper-stop"),
    allowed("read-agent-file", "read-agent-file"),
    denied(
        "search-secret-denied",
        "search-secret",
        "Protected file blocked by policy: .env",
    ),
    not_denied("search-glob-not-judged", "search-glob"),
    denied("deny-workflow-run", "deny-workflow-run", WORKFLOW_DENIAL),
    denied("deny-workflow-manage", "deny-workflow-manage", WORKFLOW_DENIAL),
    refused("sql-no-file-write", SQL_REFUSAL, "sql-attach", "sql-vacuum-into"),
    denied(
        "subagent-deny-git-reset",
        "child-git-reset",
        "Blocked dangerous git operation",
    ),
    refused("subagent-store-sql-refused", SQL_REFUSAL, "child-store-attach"),
    Check("subagent-context", subagent_context),
)
CODEX_PATCH_CHECKS = (
    allowed("patch-plain-allowed", "patch-plain"),
    denied(
        "patch-secret-denied",
        "patch-secret",
        "Protected file blocked by policy: .env",
    ),
    asked("patch-hook-ask", "patch-hook"),
    asked("patch-server-ask", "patch-server"),
    asked("patch-agent-ask", "patch-agent"),
    asked("patch-indented-hook-ask", "patch-indented-hook"),
)
# Same expected values as the baseline twins. The nested-only answer is ignored
# under camelCase event names (F4), so these fail until the guards also print the
# top-level answer. With one hook source the runtime raises one question, not two.
CAMEL_CHECKS = (
    Check("camel-hooks-source", only_copilot_hook_file),
    Check("camel-events-renamed", events_renamed),
    Check("camel-mcp-none", mcp_none),
    denied(
        "camel-deny-git-reset",
        "camel-deny-git-reset",
        "Blocked dangerous git operation",
    ),
    denied(
        "camel-deny-secret-rm",
        "camel-deny-secret-rm",
        "Protected file blocked by policy: .env",
    ),
    denied(
        "camel-deny-commit",
        "camel-deny-commit",
        "commit gate failed for github-copilot",
    ),
    denied("camel-deny-branch", "camel-deny-branch", *BRANCH_GUARD_REASONS),
    denied(
        "camel-deny-pr",
        "camel-deny-pr",
        "PR/push gate only allows implementation branches",
    ),
    asked("camel-ask-vscode-settings", "camel-ask-vscode-settings"),
    asked("camel-ask-agent-wrapper", "camel-ask-agent-wrapper"),
    allowed(
        "camel-allow-plain",
        "camel-allow-plain-bash",
        "camel-allow-plain-view",
        "camel-allow-plain-create",
        "camel-allow-plain-edit",
    ),
)
SESSIONS = (
    Session("main", baseline_scenario, BASELINE_CHECKS),
    Session("codex-patch", codex_patch_scenario, CODEX_PATCH_CHECKS),
    Session("camel-rename", camel_rename_scenario, CAMEL_CHECKS, renamed_events=True),
)


# --- output ----------------------------------------------------------------


def tool_inventory(record: SessionRecord) -> list[str]:
    """One line per tool the first model request offered: name and input keys."""
    lines = []
    for tool in record.summary.get("firstRequestTools") or []:
        function, custom = (
            _dict(_dict(tool).get("function")),
            _dict(_dict(tool).get("custom")),
        )
        if function:
            keys = ", ".join(_dict(_dict(function.get("parameters")).get("properties")))
            lines.append(f"{function.get('name')}: {keys or '(no input)'}")
        elif custom:
            lines.append(f"{custom.get('name')}: (free-form text)")
        else:
            lines.append(f"{_dict(tool).get('name', '?')}: (unrecognised tool shape)")
    return lines


def summarize_discovery(result: Mapping[str, Any]) -> list[str]:
    """Describe what the runtime found in a folder (the `--discover` output)."""

    def items(key: str, field_name: str) -> list[Any] | str:
        found = _dict(result.get(key))
        if "__error" in found:
            return f"ERROR {found['__error']}"
        listed = found.get(field_name)
        return listed if isinstance(listed, list) else "ERROR no answer"

    lines = []
    hooks = items("hooks", "hooks")
    if isinstance(hooks, str):
        lines.append(f"hooks: {hooks}")
    else:
        lines.append(f"hooks: {len(hooks)}")
        counts = Counter(_hook_file(row) for row in hooks)
        lines += [f"  {name}: {count}" for name, count in sorted(counts.items())]
    for label, key, field_name, name_key in (
        ("MCP servers", "mcp", "servers", "name"),
        ("instructions", "instructions", "sources", "label"),
        ("skills", "skills", "skills", None),
        ("agents", "agents", "agents", "name"),
    ):
        found = items(key, field_name)
        if isinstance(found, str):
            lines.append(f"{label}: {found}")
            continue
        names = (
            ", ".join(str(_dict(row).get(name_key)) for row in found)
            if name_key
            else ""
        )
        lines.append(f"{label}: {len(found)}" + (f" ({names})" if names else ""))
    lines.append(
        "note: repository hooks and MCP servers load only for a trusted folder; "
        "this command adds no trust, so none are listed."
    )
    return lines


def _print_versions(runtime: RuntimeInfo, runtime_version: str) -> None:
    print(f"VS Code commit: {runtime.vscode_commit}")
    print(f"Copilot SDK version: {runtime.sdk_version}")
    print(f"Copilot runtime version: {runtime_version}")


def _version_of(record: Mapping[str, Any]) -> str:
    return str(_dict(record.get("status")).get("version") or "unknown")


# --- main ------------------------------------------------------------------


def run_probe(runtime: RuntimeInfo, work: Path) -> int:
    """Run every session in a fresh project under `work`; print and return the exit code."""
    deadline = time.monotonic() + RUN_LIMIT_SECONDS
    try:
        project = prepare_project(work, deadline)
        # Copied before any session runs: the sessions leave files behind.
        camel_project = prepare_camel_project(project, work)
    except (RuntimeError, OSError) as error:
        print(f"{FAIL} project: {error}")
        return 1
    home = work / "copilot-home"
    results: list[CheckResult] = []
    inventories: list[tuple[str, list[str]]] = []
    runtime_version = "unknown"
    for session in SESSIONS:
        label = f"session-{session.name}"
        budget = min(SESSION_LIMIT_SECONDS, deadline - time.monotonic())
        if budget <= 0:
            results.append(
                CheckResult(
                    label,
                    FAIL,
                    f"run limit of {RUN_LIMIT_SECONDS} s exceeded; not started",
                )
            )
            continue
        folder = camel_project if session.renamed_events else project
        record = run_session(
            runtime, folder, session.scenario(folder), home, timeout=budget
        )
        if runtime_version == "unknown":
            runtime_version = _version_of(record.summary)
        if record.failure:
            results.append(CheckResult(label, FAIL, record.failure))
        else:
            replies = record.summary.get("modelCalls", "?")
            results.append(
                CheckResult(
                    label, PASS, f"finished after {replies} scripted model replies"
                )
            )
        results += evaluate(record, session.checks)
        inventories.append((session.name, tool_inventory(record)))
    _print_versions(runtime, runtime_version)
    for result in results:
        print(f"{result.status} {result.name}: {result.detail}")
    for name, lines in inventories:
        print(f"Tool inventory, session {name} ({len(lines)} tools):")
        print("\n".join(f"  {line}" for line in lines))
    failed = [r for r in results if r.status == FAIL]
    print(
        f"Result: {FAIL if failed else PASS} ({len(failed)} of {len(results)} checks failed)"
    )
    return 1 if failed else 0


def run_discover(runtime: RuntimeInfo, folder: Path, work: Path) -> int:
    """Print what the runtime discovers in `folder`, without a session."""
    folder = folder.expanduser().resolve()
    if not folder.is_dir():
        print(f"{FAIL} discover: {folder} is not a folder")
        return 1
    config = {
        "mode": "discover",
        "sdkRoot": str(runtime.sdk_root),
        "baseDir": str(work / "copilot-home"),
        "project": str(folder),
        "outDir": str(work / "discover"),
    }
    record, failure = _launch(runtime, config, SESSION_LIMIT_SECONDS)
    _print_versions(runtime, _version_of(record))
    if failure:
        print(f"{FAIL} discover: {failure}")
        return 1
    print("\n".join(summarize_discovery(_dict(record.get("discovery")))))
    return 0


def build_parser() -> argparse.ArgumentParser:
    """Build the parser for `--require`, `--vscode-bin`, `--keep`, and `--discover`."""
    parser = argparse.ArgumentParser(
        description="Opt-in, offline check of the Copilot runtime shipped in VS Code."
    )
    parser.add_argument(
        "--require", action="store_true", help="exit 1 when no runtime is found"
    )
    parser.add_argument(
        "--vscode-bin",
        type=Path,
        metavar="DIR",
        help="folder that holds `node` and the Copilot SDK (default: newest ~/.vscode-server/bin/*)",
    )
    parser.add_argument("--keep", action="store_true", help="keep the temporary folder")
    parser.add_argument(
        "--discover",
        type=Path,
        metavar="DIR",
        help="print what the runtime discovers in DIR (no session) and exit",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the probe. Returns 0 when every check passes, 1 on any FAIL."""
    args = build_parser().parse_args(argv)
    runtime = find_runtime(args.vscode_bin)
    if runtime is None:
        where = args.vscode_bin or "~/.vscode-server/bin/*"
        level = FAIL if args.require else WARN
        print(
            f"{level} copilot-runtime: no folder with `node` and the Copilot SDK in {where}"
        )
        return 1 if args.require else 0
    work = Path(tempfile.mkdtemp(prefix="copilot-runtime-probe-"))
    try:
        if args.discover is not None:
            return run_discover(runtime, args.discover, work)
        return run_probe(runtime, work)
    finally:
        if args.keep:
            print(f"Kept the temporary folder: {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
