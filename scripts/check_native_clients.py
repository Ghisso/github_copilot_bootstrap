#!/usr/bin/env python3
"""Run opt-in, least-privilege native acceptance probes for Codex and Claude.

The ordinary suite does not invoke either client.  A release operator may invoke
this script in an authenticated environment.  It never changes trust, user
configuration, or the source/generated target.  Native stdout/stderr, prompts,
paths, IDs, and credentials are deliberately discarded rather than redacted.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
GENERATOR = REPO_ROOT / "scripts" / "generate_targets.py"
OBSERVATION_SCHEMA = (
    REPO_ROOT / "shared" / "schemas" / "native-client-observation.schema.json"
)
WORKSPACE_MARKER = ".native-client-probe-owned"
WORKSPACE_MARKER_CONTENT = "native-client-probe-v1\n"
# Each client runs control and candidate consecutively; 120s timed Codex out.
TIMEOUT_SECONDS = 420
PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
EVIDENCE_PRECHECK = "native_preflight"
EVIDENCE_SENTINEL = "client_schema_sentinel"
EVIDENCE_EVENTS = "native_event_metadata"
EVIDENCE_UNAVAILABLE = "unavailable_untrusted"
EVIDENCE_UNEXERCISED = "unexercised"

CODEX_ROLES = {
    "orchestrator": ("orchestrator", "gpt-5.6-sol", "xhigh"),
    "planner": ("planner", "gpt-5.6-sol", "max"),
    "coder": ("coder", "gpt-5.6-terra", "high"),
    "reviewer": ("reviewer", "gpt-5.6-sol", "high"),
    "documenter": ("documenter", "gpt-5.6-luna", "medium"),
    "verifier": ("verifier", "gpt-5.6-luna", "low"),
}
SENTINEL_FIELDS = (
    "root_instruction",
    "scoped_instruction",
    "workflow_contract",
    "hooks",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--client", choices=("claude", "codex", "all"), default="all")
    parser.add_argument("--require", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--workspace",
        type=Path,
        help="Persistent, marker-owned probe directory prepared separately before trust.",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Create or refresh the marked workspace without executing either client.",
    )
    parser.add_argument(
        "--timeout", type=int, default=TIMEOUT_SECONDS, help=argparse.SUPPRESS
    )
    return parser.parse_args()


def check(check_id: str, status: str, evidence: str) -> dict[str, str]:
    """Create a report entry from controlled strings only."""
    return {"id": check_id, "status": status, "evidence": evidence}


def minimal_environment(temp_root: Path) -> dict[str, str]:
    """Pass only client location/auth and portable temporary/locale settings."""
    names = ("PATH", "HOME", "CODEX_HOME", "CLAUDE_CONFIG_DIR", "LANG", "LC_ALL")
    env = {name: os.environ[name] for name in names if os.environ.get(name)}
    env.update(
        {
            "TMPDIR": str(temp_root),
            "TEMP": str(temp_root),
            "TMP": str(temp_root),
            "NO_COLOR": "1",
        }
    )
    return env


def run_process(
    command: list[str], *, cwd: Path, timeout: int, temp_root: Path
) -> subprocess.CompletedProcess[str] | None:
    """Start a new process group and always reap it; discard failure text."""
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            text=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=minimal_environment(temp_root),
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            return None
        return subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
    except OSError:
        return None


def prepare_variants(root: Path, timeout: int) -> tuple[Path, Path] | None:
    """Generate separate disposable control/candidate consumers before locking."""
    generated = root / "generated"
    result = run_process(
        [sys.executable, str(GENERATOR), "--all", "--output", str(generated)],
        cwd=REPO_ROOT,
        timeout=timeout,
        temp_root=root,
    )
    source = generated / "multi-agent"
    if result is None or result.returncode != 0 or not source.is_dir():
        return None
    control, candidate = root / "control", root / "candidate"
    shutil.copytree(source, control)
    shutil.copytree(source, candidate)
    config = candidate / ".codex" / "config.toml"
    if not remove_multi_agent_v2(config):
        return None
    if not lock_readonly(control) or not lock_readonly(candidate):
        return None
    return control, candidate


def safe_workspace(path: Path) -> Path | None:
    """Reject broad, repository, and ambiguously named persistent workspaces."""
    candidate = path.expanduser().resolve()
    home = Path.home().resolve()
    repo = REPO_ROOT.resolve()
    if (
        "native-client-probe" not in candidate.name
        or candidate == Path("/")
        or candidate == home
        or home in candidate.parents
        or candidate == repo
        or candidate in repo.parents
        or repo in candidate.parents
    ):
        return None
    return candidate


def marker_owned(workspace: Path) -> bool:
    marker = workspace / WORKSPACE_MARKER
    try:
        return (
            marker.is_file()
            and marker.read_text(encoding="utf-8") == WORKSPACE_MARKER_CONTENT
        )
    except OSError:
        return False


def persistent_variants(workspace: Path) -> tuple[Path, Path] | None:
    if not marker_owned(workspace):
        return None
    control, candidate = workspace / "control", workspace / "candidate"
    if not control.is_dir() or not candidate.is_dir():
        return None
    return control, candidate


def prepare_workspace(workspace: Path, timeout: int) -> bool:
    """Refresh only marker-owned children, never delete the persistent workspace."""
    safe = safe_workspace(workspace)
    if safe is None:
        return False
    if safe.exists() and any(safe.iterdir()) and not marker_owned(safe):
        return False
    try:
        safe.mkdir(mode=0o700, parents=True, exist_ok=True)
        marker = safe / WORKSPACE_MARKER
        if not marker.exists():
            marker.write_text(WORKSPACE_MARKER_CONTENT, encoding="utf-8")
        for name in ("control", "candidate"):
            child = safe / name
            if child.exists():
                unlock_for_cleanup(child)
                shutil.rmtree(child)
    except OSError:
        return False
    return prepare_variants(safe, timeout) is not None


def remove_multi_agent_v2(config: Path) -> bool:
    """Remove the candidate shim solely from the temporary candidate config."""
    if not config.is_file():
        return False
    text = config.read_text(encoding="utf-8")
    start = text.find("[features.multi_agent_v2]")
    if start < 0:
        return False
    next_header = text.find("\n[", start + 1)
    config.write_text(
        text[:start] + (text[next_header + 1 :] if next_header >= 0 else ""),
        encoding="utf-8",
    )
    return True


def lock_readonly(root: Path) -> bool:
    try:
        for path in sorted(root.rglob("*"), reverse=True):
            path.chmod(stat.S_IRUSR | (stat.S_IXUSR if path.is_dir() else 0))
        root.chmod(stat.S_IRUSR | stat.S_IXUSR)
    except OSError:
        return False
    return True


def unlock_for_cleanup(root: Path) -> None:
    for path in root.rglob("*"):
        try:
            path.chmod(stat.S_IRWXU if path.is_dir() else stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
    try:
        root.chmod(stat.S_IRWXU)
    except OSError:
        pass


def observation_schema() -> dict[str, Any]:
    return json.loads(OBSERVATION_SCHEMA.read_text(encoding="utf-8"))


def scoped_instruction_question(client: str) -> str:
    """Ask each client only about the scoped surface its target actually ships.

    Codex discovers scoped instructions by directory (nested `AGENTS.md` on the
    root->cwd path). This bootstrap scopes policy by glob and renders native
    adapters for Copilot (`applyTo`) and Claude (`paths:`) only, so there is no
    nested `AGENTS.md` to find. Asking Codex the Claude question made the answer
    non-deterministic; ask it about the routing that does exist instead.
    """
    if client == "codex":
        return (
            "`scoped_instruction` is true only if the root AGENTS.md routes you to the "
            "canonical shared policies under .claude/instructions/."
        )
    return (
        "`scoped_instruction` is true only if a path-scoped rule adapter under "
        ".claude/rules/ declares `paths:` frontmatter."
    )


def probe_prompt(client: str) -> str:
    role_request = (
        "Spawn each configured named role once. Do not report role metadata in your final answer; "
        "the runner only accepts client event metadata for that evidence."
        if client == "codex"
        else "Do not create subagents."
    )
    return (
        "Read only the current generated project. Do not write files, approve hooks, expose "
        "prompts, paths, transcript content, IDs, credentials, or environment values. Return only "
        "the schema booleans for whether the root instruction, scoped instruction, required workflow "
        "contract, and project hooks were discovered. "
        + scoped_instruction_question(client)
        + " "
        + role_request
    )


def codex_command(binary: str, consumer: Path, schema: Path) -> list[str]:
    return [
        binary,
        "exec",
        "--ephemeral",
        "--sandbox",
        "read-only",
        "-c",
        'approval_policy="never"',
        "-c",
        "mcp_servers={}",
        "-c",
        'web_search="disabled"',
        "--json",
        "--output-schema",
        str(schema),
        "--skip-git-repo-check",
        "-C",
        str(consumer),
        probe_prompt("codex"),
    ]


def claude_command(binary: str, consumer: Path, schema: dict[str, Any]) -> list[str]:
    """Claude requires JSON Schema inline, unlike Codex's schema-file flag."""
    # Claude's inline validator cannot resolve the 2020-12 meta-schema URI and
    # rejects the whole schema; Codex reads the canonical file and keeps it.
    inline_schema = {key: value for key, value in schema.items() if key != "$schema"}
    return [
        binary,
        "-p",
        "--permission-mode",
        "dontAsk",
        "--no-session-persistence",
        "--output-format",
        "json",
        "--json-schema",
        json.dumps(inline_schema, separators=(",", ":")),
        "--strict-mcp-config",
        "--disallowedTools",
        "Edit,Write,Bash,mcp__*",
        # `--disallowedTools` is variadic; without `--` it consumes the prompt
        # and Claude exits non-zero demanding input.
        "--",
        probe_prompt("claude"),
    ]


def parse_jsonl(text: str) -> list[dict[str, Any]] | None:
    """Accept complete JSON or JSONL objects; reject malformed envelopes entirely."""
    if not text.strip():
        return None
    values: list[dict[str, Any]] = []
    for line in text.splitlines():
        try:
            parsed = json.loads(line)
        except json.JSONDecodeError:
            return None
        if not isinstance(parsed, dict):
            return None
        values.append(parsed)
    return values


def find_structured_observation(value: Any) -> dict[str, Any] | None:
    if isinstance(value, str):
        # Codex returns the schema answer as JSON text in `agent_message.text`
        # rather than as a nested object.
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            return None
        return (
            decoded
            if isinstance(decoded, dict) and set(decoded) == set(SENTINEL_FIELDS)
            else None
        )
    if isinstance(value, dict):
        if set(value) == set(SENTINEL_FIELDS):
            return value
        for key in ("structured_output", "output", "result", "item", "text"):
            if key in value:
                found = find_structured_observation(value[key])
                if found is not None:
                    return found
    return None


def valid_observation(observation: dict[str, Any] | None) -> bool:
    return (
        observation is not None
        and set(observation) == set(SENTINEL_FIELDS)
        and all(type(observation[field]) is bool for field in SENTINEL_FIELDS)
    )


def parse_observation(events: list[dict[str, Any]] | None) -> dict[str, Any] | None:
    if events is None:
        return None
    observations = [
        found
        for event in events
        if (found := find_structured_observation(event)) is not None
    ]
    if len(observations) != 1 or not valid_observation(observations[0]):
        return None
    return observations[0]


def event_role_records(events: list[dict[str, Any]] | None) -> list[dict[str, str]]:
    """Read only explicit client agent/thread events, never a model final response."""
    if events is None:
        return []
    records: list[dict[str, str]] = []
    for event in events:
        event_type = event.get("type")
        if not isinstance(event_type, str) or not any(
            word in event_type.lower() for word in ("agent", "thread", "subagent")
        ):
            continue
        payload = (
            event.get("agent") or event.get("thread") or event.get("data") or event
        )
        if not isinstance(payload, dict):
            continue
        role = payload.get("role") or payload.get("name") or payload.get("agent_name")
        role_type = (
            payload.get("role_type") or payload.get("agent_type") or payload.get("type")
        )
        model = payload.get("model")
        effort = payload.get("reasoning_effort") or payload.get("reasoningEffort")
        if (
            isinstance(role, str)
            and isinstance(role_type, str)
            and isinstance(model, str)
            and isinstance(effort, str)
        ):
            records.append(
                {
                    "role": role,
                    "type": role_type,
                    "model": model,
                    "reasoning_effort": effort,
                }
            )
    return records


def valid_role_matrix(records: list[dict[str, str]]) -> bool:
    if len(records) != len(CODEX_ROLES):
        return False
    names = [record.get("role") for record in records]
    if len(set(names)) != len(names) or set(names) != set(CODEX_ROLES):
        return False
    return all(
        (record.get("type"), record.get("model"), record.get("reasoning_effort"))
        == expected
        for record in records
        if (expected := CODEX_ROLES.get(record["role"])) is not None
    )


def unavailable_result(client: str, reason: str, require: bool) -> dict[str, Any]:
    status = FAIL if require else WARN
    safe_reason = (
        reason
        if reason
        in {
            "missing",
            "timeout",
            "untrusted",
            "unavailable",
            "workspace_unprepared",
            "invocation_failed",
        }
        else "unavailable"
    )
    return {
        "client": client,
        "status": status,
        "checks": [check(f"{client}_{safe_reason}", status, EVIDENCE_UNAVAILABLE)],
    }


def preflight(binary: str, client: str, root: Path) -> bool:
    if client != "codex":
        return True
    result = run_process(
        [binary, "login", "status"], cwd=REPO_ROOT, timeout=20, temp_root=root
    )
    return result is not None and result.returncode == 0


def client_command(
    binary: str, client: str, consumer: Path, schema_path: Path, schema: dict[str, Any]
) -> list[str]:
    return (
        codex_command(binary, consumer, schema_path)
        if client == "codex"
        else claude_command(binary, consumer, schema)
    )


def probe_client(
    client: str, *, require: bool, timeout: int, workspace: Path | None = None
) -> dict[str, Any]:
    binary = shutil.which(client)
    if binary is None:
        return unavailable_result(client, "missing", require)
    if workspace is None:
        # Keep the default useful for generated-structure/missing-client smoke,
        # but a random directory cannot be manually pre-trusted by an operator.
        with tempfile.TemporaryDirectory(prefix="native-client-probe-") as temp_dir:
            root = Path(temp_dir)
            variants = prepare_variants(root, timeout)
            if variants is None:
                return unavailable_result(client, "unavailable", require)
            for variant in variants:
                unlock_for_cleanup(variant)
        return unavailable_result(client, "untrusted", require)
    workspace_root = safe_workspace(workspace)
    if workspace_root is None:
        return unavailable_result(client, "workspace_unprepared", require)
    variants = persistent_variants(workspace_root)
    if variants is None:
        return unavailable_result(client, "workspace_unprepared", require)
    control, candidate = variants
    if not preflight(binary, client, workspace_root):
        return unavailable_result(client, "untrusted", require)
    schema_path = workspace_root / "probe-schema.json"
    schema = observation_schema()
    try:
        schema_path.write_text(json.dumps(schema), encoding="utf-8")
    except OSError:
        return unavailable_result(client, "unavailable", require)
    control_result = run_process(
        client_command(binary, client, control, schema_path, schema),
        cwd=control,
        timeout=timeout,
        temp_root=workspace_root,
    )
    candidate_result = run_process(
        client_command(binary, client, candidate, schema_path, schema),
        cwd=candidate,
        timeout=timeout,
        temp_root=workspace_root,
    )
    if control_result is None or candidate_result is None:
        return unavailable_result(client, "timeout", require)
    if control_result.returncode != 0:
        # A non-zero exit is not evidence about trust: it is equally an argv,
        # auth, or version problem. Claiming `untrusted` here would assert
        # something untrue about the operator's environment.
        return unavailable_result(client, "invocation_failed", require)
    events = parse_jsonl(control_result.stdout)
    observation = parse_observation(events)
    if observation is None:
        return {
            "client": client,
            "status": FAIL,
            "checks": [check("result_schema", FAIL, EVIDENCE_SENTINEL)],
        }
    checks = [check("project_trust_preflight", PASS, EVIDENCE_PRECHECK)]
    checks.extend(
        check(
            f"{field}_sentinel", PASS if observation[field] else FAIL, EVIDENCE_SENTINEL
        )
        for field in SENTINEL_FIELDS
    )
    if candidate_result.returncode != 0:
        checks.append(check("candidate_shim_execution", WARN, EVIDENCE_UNEXERCISED))
    else:
        candidate_events = parse_jsonl(candidate_result.stdout)
        candidate_observation = parse_observation(candidate_events)
        if candidate_observation is None:
            checks.append(check("candidate_result_schema", FAIL, EVIDENCE_SENTINEL))
        else:
            checks.append(check("candidate_shim_execution", PASS, EVIDENCE_PRECHECK))
            checks.append(
                check(
                    "candidate_sentinel_parity",
                    PASS if candidate_observation == observation else FAIL,
                    EVIDENCE_SENTINEL,
                )
            )
    checks.append(check("compact_resume", WARN, EVIDENCE_UNEXERCISED))
    if client == "codex":
        records = event_role_records(events)
        if not records:
            checks.extend(
                [
                    check("codex_role_matrix", WARN, EVIDENCE_UNEXERCISED),
                    check("coder_escalation", WARN, EVIDENCE_UNEXERCISED),
                ]
            )
        else:
            matrix_status = PASS if valid_role_matrix(records) else FAIL
            checks.append(check("codex_role_matrix", matrix_status, EVIDENCE_EVENTS))
            # Current documented JSONL does not expose a stable escalation event field.
            checks.append(check("coder_escalation", WARN, EVIDENCE_UNEXERCISED))
    has_fail = any(item["status"] == FAIL for item in checks)
    has_warn = any(item["status"] == WARN for item in checks)
    status = FAIL if has_fail or (require and has_warn) else WARN if has_warn else PASS
    return {"client": client, "status": status, "checks": checks}


def build_report(results: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(result["status"] for result in results)
    return {
        "schema_version": "2.0",
        "results": results,
        "summary": {key.lower(): counts.get(key, 0) for key in (PASS, WARN, FAIL)},
    }


def main() -> int:
    args = parse_args()
    if args.prepare_only:
        prepared = args.workspace is not None and prepare_workspace(
            args.workspace, args.timeout
        )
        status = PASS if prepared else FAIL
        report = {
            "schema_version": "2.0",
            "results": [
                {
                    "client": "workspace",
                    "status": status,
                    "checks": [
                        check(
                            "workspace_prepared" if prepared else "workspace_refused",
                            status,
                            EVIDENCE_PRECHECK,
                        )
                    ],
                }
            ],
            "summary": {"pass": int(prepared), "warn": 0, "fail": int(not prepared)},
        }
        if args.json:
            print(json.dumps(report, sort_keys=True))
        else:
            print(f"workspace: {status}")
        return 0 if prepared else 1
    clients = ("codex", "claude") if args.client == "all" else (args.client,)
    results = [
        probe_client(
            client,
            require=args.require,
            timeout=args.timeout,
            workspace=args.workspace,
        )
        for client in clients
    ]
    report = build_report(results)
    if args.json:
        print(json.dumps(report, sort_keys=True))
    else:
        for result in results:
            print(f"{result['client']}: {result['status']}")
    return 1 if any(result["status"] == FAIL for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
