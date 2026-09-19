"""Deterministic boundary tests for the bootstrap-owned OpenWiki runner."""

from __future__ import annotations

import fcntl
import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "shared" / "scripts" / "openwiki_refresh.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("openwiki_refresh_test", RUNNER)
assert RUNNER_SPEC is not None and RUNNER_SPEC.loader is not None
RUNNER_MODULE = importlib.util.module_from_spec(RUNNER_SPEC)
sys.modules[RUNNER_SPEC.name] = RUNNER_MODULE
RUNNER_SPEC.loader.exec_module(RUNNER_MODULE)


def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        text=True,
        capture_output=True,
        check=False,
    )


def _repository(
    tmp_path: Path, *, enabled: bool = True, ignored_control_plane: bool = False
) -> Path:
    root = tmp_path / "consumer"
    root.mkdir()
    assert _git(root, "init", "-q").returncode == 0
    ignore_patterns = ["openwiki/.run.json"]
    if ignored_control_plane:
        ignore_patterns.append(".claude/")
    (root / ".gitignore").write_text(
        "\n".join(ignore_patterns) + "\n", encoding="utf-8"
    )
    (root / "tracked.txt").write_text("base\n", encoding="utf-8")
    if enabled:
        marker = root / "openwiki" / "INSTRUCTIONS.md"
        marker.parent.mkdir()
        marker.write_text("enabled\n", encoding="utf-8")
    assert _git(root, "add", ".").returncode == 0
    assert (
        _git(
            root,
            "-c",
            "user.name=OpenWiki Test",
            "-c",
            "user.email=openwiki-test@example.com",
            "commit",
            "-qm",
            "base",
        ).returncode
        == 0
    )
    return root


@pytest.fixture
def fake_cli(tmp_path: Path) -> Path:
    """Create fake Node and OpenWiki executables with no network behavior."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    node = bin_dir / "node"
    node.write_text("#!/bin/sh\nprintf 'v22.22.0\\n'\n", encoding="utf-8")
    openwiki = bin_dir / "openwiki"
    openwiki.write_text(
        """#!/usr/bin/env python3
import json
import os
import sys
import time
from pathlib import Path

if sys.argv[1:] == ["--version"]:
    print("0.5.2")
    raise SystemExit(0)

trace = os.environ.get("OPENWIKI_TEST_TRACE")
if trace:
    Path(trace).write_text(json.dumps({
        "argv": sys.argv[1:],
        "telemetry": os.environ.get("OPENWIKI_TELEMETRY_DISABLED"),
        "secret": os.environ.get("OPENWIKI_TEST_PROVIDER_SECRET"),
    }), encoding="utf-8")

root = Path.cwd()
mode = os.environ.get("OPENWIKI_TEST_MODE", "success")
if mode in {"success", "fail"}:
    state = root / "openwiki" / ".run.json"
    state.write_text("resume state\\n", encoding="utf-8")
    (root / "openwiki" / "generated.md").write_text("generated\\n", encoding="utf-8")
if mode in {"adapters", "fail"}:
    (root / "AGENTS.md").write_bytes(b"upstream agents\\n")
    (root / "CLAUDE.md").write_bytes(b"upstream claude\\n")
if mode == "create-adapter":
    (root / "AGENTS.md").write_bytes(b"upstream created\\n")
if mode == "workflow-existing":
    workflow = root / ".github" / "workflows" / "openwiki-update.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_bytes(b"upstream workflow\\n")
if mode == "workflow-new":
    workflow = root / ".github" / "workflows" / "openwiki-update.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_bytes(b"new workflow\\n")
if mode == "workflow-fail":
    workflow = root / ".github" / "workflows" / "openwiki-update.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_bytes(b"failed workflow\\n")
if mode == "out-of-scope":
    (root / "unexpected.txt").write_text("unexpected\\n", encoding="utf-8")
if mode == "ignored-new":
    ignored = root / ".claude" / "generated-by-openwiki.txt"
    ignored.parent.mkdir(parents=True, exist_ok=True)
    ignored.write_text("unexpected\\n", encoding="utf-8")
if mode == "ignored-existing":
    (root / ".claude" / "existing.txt").write_text("after!\\n", encoding="utf-8")
if mode == "dirty-existing":
    (root / "local.txt").write_text("upstream changed\\n", encoding="utf-8")
if mode == "dirty-delete":
    (root / "local.txt").unlink()
if mode == "dirty-clean":
    (root / "tracked.txt").write_text("base\\n", encoding="utf-8")
if mode == "wait-for-replacement":
    Path(os.environ["OPENWIKI_TEST_READY"]).write_text("ready\\n", encoding="utf-8")
    release = Path(os.environ["OPENWIKI_TEST_RELEASE"])
    for _ in range(300):
        if release.exists():
            break
        time.sleep(0.01)
if mode in {"fail", "workflow-fail"}:
    raise SystemExit(7)
""",
        encoding="utf-8",
    )
    node.chmod(0o755)
    openwiki.chmod(0o755)
    return bin_dir


def _run(
    root: Path,
    fake_cli: Path,
    *,
    require_enabled: bool = False,
    mode: str = "success",
    cwd: Path | None = None,
    **environment: str,
) -> tuple[subprocess.CompletedProcess[str], dict[str, object]]:
    env = {
        **os.environ,
        "PATH": f"{fake_cli}{os.pathsep}{os.environ['PATH']}",
        "OPENWIKI_TEST_MODE": mode,
        **environment,
    }
    command = [sys.executable, str(RUNNER)]
    if require_enabled:
        command.append("--require-enabled")
    result = subprocess.run(
        command,
        cwd=cwd or root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return result, json.loads(result.stdout)


def test_disabled_repository_is_a_true_noop(tmp_path: Path, fake_cli: Path) -> None:
    root = _repository(tmp_path, enabled=False)

    result, payload = _run(root, fake_cli)

    assert result.returncode == 0
    assert payload == {"repository_root": str(root), "status": "not_enabled"}
    assert _git(root, "status", "--porcelain").stdout == ""


def test_require_enabled_fails_when_marker_is_absent(
    tmp_path: Path, fake_cli: Path
) -> None:
    root = _repository(tmp_path, enabled=False)

    result, payload = _run(root, fake_cli, require_enabled=True)

    assert result.returncode != 0
    assert payload["status"] == "not_enabled"
    assert "create openwiki/INSTRUCTIONS.md" in str(payload["error"])


def test_successful_update_only_changes_openwiki_content(
    tmp_path: Path, fake_cli: Path
) -> None:
    root = _repository(tmp_path)

    result, payload = _run(root, fake_cli)

    assert result.returncode == 0, result.stderr
    assert payload["status"] == "success"
    assert payload["new_paths"] == ["openwiki/generated.md"]
    assert payload["out_of_scope_paths"] == []
    assert (root / "openwiki/.run.json").read_text() == "resume state\n"


def test_existing_adapters_are_restored_byte_for_byte(
    tmp_path: Path, fake_cli: Path
) -> None:
    root = _repository(tmp_path)
    agents = root / "AGENTS.md"
    claude = root / "CLAUDE.md"
    agents.write_bytes(b"local agents\x00edit\n")
    claude.write_bytes(b"local claude\x00edit\n")

    result, payload = _run(root, fake_cli, mode="adapters")

    assert result.returncode == 0, result.stderr
    assert payload["status"] == "success"
    assert agents.read_bytes() == b"local agents\x00edit\n"
    assert claude.read_bytes() == b"local claude\x00edit\n"
    assert set(payload["pre_existing_dirty_paths"]) == {"AGENTS.md", "CLAUDE.md"}


def test_created_root_adapter_is_removed_when_previously_absent(
    tmp_path: Path, fake_cli: Path
) -> None:
    root = _repository(tmp_path)

    result, payload = _run(root, fake_cli, mode="create-adapter")

    assert result.returncode == 0, result.stderr
    assert payload["status"] == "success"
    assert not (root / "AGENTS.md").exists()


def test_existing_workflow_remains_byte_identical(
    tmp_path: Path, fake_cli: Path
) -> None:
    root = _repository(tmp_path)
    workflow = root / ".github/workflows/openwiki-update.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_bytes(b"local workflow\n")

    result, payload = _run(root, fake_cli)

    assert result.returncode == 0, result.stderr
    assert payload["workflow_unchanged"] is True
    assert workflow.read_bytes() == b"local workflow\n"


def test_existing_workflow_mutation_is_detected(tmp_path: Path, fake_cli: Path) -> None:
    root = _repository(tmp_path)
    workflow = root / ".github/workflows/openwiki-update.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_bytes(b"local workflow\n")

    result, payload = _run(root, fake_cli, mode="workflow-existing")

    assert result.returncode != 0
    assert payload["workflow_unchanged"] is False
    assert ".github/workflows/openwiki-update.yml" in payload["out_of_scope_paths"]
    assert workflow.read_bytes() == b"upstream workflow\n"


def test_failed_update_reports_workflow_mutation(
    tmp_path: Path, fake_cli: Path
) -> None:
    root = _repository(tmp_path)
    workflow = root / ".github/workflows/openwiki-update.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_bytes(b"local workflow\n")

    result, payload = _run(root, fake_cli, mode="workflow-fail")

    assert result.returncode != 0
    assert payload["openwiki_returncode"] == 7
    assert payload["workflow_unchanged"] is False
    assert ".github/workflows/openwiki-update.yml" in payload["out_of_scope_paths"]
    assert workflow.read_bytes() == b"failed workflow\n"


def test_new_workflow_is_detected_as_out_of_scope(
    tmp_path: Path, fake_cli: Path
) -> None:
    root = _repository(tmp_path)

    result, payload = _run(root, fake_cli, mode="workflow-new")

    assert result.returncode != 0
    assert ".github/workflows/openwiki-update.yml" in payload["out_of_scope_paths"]


def test_failed_update_restores_adapters_and_keeps_recovery_state(
    tmp_path: Path, fake_cli: Path
) -> None:
    root = _repository(tmp_path)
    agents = root / "AGENTS.md"
    agents.write_bytes(b"local agents\n")

    result, payload = _run(root, fake_cli, mode="fail")

    assert result.returncode != 0
    assert payload["openwiki_returncode"] == 7
    assert agents.read_bytes() == b"local agents\n"
    assert not (root / "CLAUDE.md").exists()
    assert (root / "openwiki/.run.json").read_text() == "resume state\n"
    assert (root / "openwiki/generated.md").exists()


def test_new_out_of_scope_mutation_fails_without_reverting_user_changes(
    tmp_path: Path, fake_cli: Path
) -> None:
    root = _repository(tmp_path)
    pre_existing = root / "local.txt"
    pre_existing.write_text("keep me\n", encoding="utf-8")

    result, payload = _run(root, fake_cli, mode="out-of-scope")

    assert result.returncode != 0
    assert payload["out_of_scope_paths"] == ["unexpected.txt"]
    assert payload["pre_existing_dirty_paths"] == ["local.txt"]
    assert pre_existing.read_text() == "keep me\n"
    assert (root / "unexpected.txt").read_text() == "unexpected\n"


def test_new_ignored_control_plane_path_is_reported(
    tmp_path: Path, fake_cli: Path
) -> None:
    root = _repository(tmp_path, ignored_control_plane=True)

    result, payload = _run(root, fake_cli, mode="ignored-new")

    assert result.returncode != 0
    assert payload["ignored_control_plane_paths"] == [
        ".claude/generated-by-openwiki.txt"
    ]


def test_changed_ignored_control_plane_path_is_reported(
    tmp_path: Path, fake_cli: Path
) -> None:
    root = _repository(tmp_path, ignored_control_plane=True)
    ignored = root / ".claude" / "existing.txt"
    ignored.parent.mkdir()
    ignored.write_text("before\n", encoding="utf-8")

    result, payload = _run(root, fake_cli, mode="ignored-existing")

    assert result.returncode != 0
    assert payload["ignored_control_plane_paths"] == [".claude/existing.txt"]
    assert ignored.read_text() == "after!\n"  # Same size as the pre-run bytes.


def test_mutation_of_existing_dirty_path_is_reported(
    tmp_path: Path, fake_cli: Path
) -> None:
    root = _repository(tmp_path)
    dirty_path = root / "local.txt"
    dirty_path.write_text("local edit\n", encoding="utf-8")

    result, payload = _run(root, fake_cli, mode="dirty-existing")

    assert result.returncode != 0
    assert payload["modified_pre_existing_paths"] == ["local.txt"]
    assert dirty_path.read_text() == "upstream changed\n"


@pytest.mark.parametrize(
    ("path", "mode"),
    (("local.txt", "dirty-delete"), ("tracked.txt", "dirty-clean")),
)
def test_deleting_or_cleaning_an_existing_dirty_path_is_reported(
    tmp_path: Path, fake_cli: Path, path: str, mode: str
) -> None:
    root = _repository(tmp_path)
    dirty_path = root / path
    dirty_path.write_text("local edit\n", encoding="utf-8")

    result, payload = _run(root, fake_cli, mode=mode)

    assert result.returncode != 0
    assert payload["modified_pre_existing_paths"] == [path]


@pytest.mark.parametrize("symlink_target", ("directory", "marker"))
def test_symlinked_openwiki_configuration_is_rejected_before_launch(
    tmp_path: Path, fake_cli: Path, symlink_target: str
) -> None:
    root = _repository(tmp_path)
    marker = root / "openwiki" / "INSTRUCTIONS.md"
    external = tmp_path / "external-openwiki"
    external.mkdir()
    (external / "INSTRUCTIONS.md").write_text("enabled\n", encoding="utf-8")
    if symlink_target == "directory":
        marker.unlink()
        (root / "openwiki").rmdir()
        (root / "openwiki").symlink_to(external, target_is_directory=True)
    else:
        marker.unlink()
        marker.symlink_to(external / "INSTRUCTIONS.md")

    result, payload = _run(root, fake_cli, OPENWIKI_TEST_TRACE=str(tmp_path / "trace"))

    assert result.returncode != 0
    assert payload["status"] == "preflight_failed"
    assert not (tmp_path / "trace").exists()


@pytest.mark.parametrize("relative", ("page.md", "pages/child.md", ".run.json"))
def test_symlink_anywhere_in_openwiki_tree_is_rejected_before_launch(
    tmp_path: Path, fake_cli: Path, relative: str
) -> None:
    root = _repository(tmp_path)
    link = root / "openwiki" / relative
    link.parent.mkdir(parents=True, exist_ok=True)
    target = tmp_path / "outside-openwiki"
    target.write_text("outside\n", encoding="utf-8")
    link.symlink_to(target)

    result, payload = _run(root, fake_cli, OPENWIKI_TEST_TRACE=str(tmp_path / "trace"))

    assert result.returncode != 0
    assert payload["status"] == "preflight_failed"
    assert not (tmp_path / "trace").exists()


def test_failed_preparation_removes_only_runner_sentinels(
    tmp_path: Path, fake_cli: Path
) -> None:
    root = _repository(tmp_path)
    (root / "CLAUDE.md").mkdir()
    trace = tmp_path / "trace"

    result, payload = _run(root, fake_cli, OPENWIKI_TEST_TRACE=str(trace))

    assert result.returncode != 0
    assert payload["status"] == "preflight_failed"
    assert not (root / "AGENTS.md").exists()
    assert not trace.exists()


def test_failed_workflow_snapshot_removes_runner_sentinels(
    tmp_path: Path, fake_cli: Path
) -> None:
    root = _repository(tmp_path)
    workflow = root / ".github" / "workflows" / "openwiki-update.yml"
    workflow.mkdir(parents=True)

    result, payload = _run(root, fake_cli)

    assert result.returncode != 0
    assert payload["status"] == "preflight_failed"
    assert not (root / "AGENTS.md").exists()
    assert not (root / "CLAUDE.md").exists()


def test_sentinel_identity_uses_open_file_descriptor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repository(tmp_path)

    def unexpected_stat(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("sentinel identity must come from os.fstat")

    monkeypatch.setattr(Path, "stat", unexpected_stat)
    snapshot = RUNNER_MODULE._prepare_adapter(root, Path("AGENTS.md"))

    assert snapshot.contents is None
    assert snapshot.sentinel_identity is not None


def test_lock_open_failure_is_structured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repository(tmp_path)
    original_open = RUNNER_MODULE.os.open

    def fail_lock(path: object, *args: object, **kwargs: object) -> int:
        if str(path).endswith("openwiki-refresh.lock"):
            raise PermissionError("lock denied")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(RUNNER_MODULE, "_version", lambda _command: "0.5.2")
    monkeypatch.setattr(RUNNER_MODULE.os, "open", fail_lock)

    returncode, payload = RUNNER_MODULE._run(root)

    assert returncode != 0
    assert payload["status"] == "preflight_failed"
    assert "could not acquire refresh lock" in str(payload["error"])


def test_nested_claude_cwd_resolves_to_outer_repository(
    tmp_path: Path, fake_cli: Path
) -> None:
    root = _repository(tmp_path)
    nested = root / ".claude" / "scripts"
    nested.mkdir(parents=True)
    assert _git(root / ".claude", "init", "-q").returncode == 0

    result, payload = _run(root, fake_cli, cwd=nested)

    assert result.returncode == 0, result.stderr
    assert payload["repository_root"] == str(root)


def test_argv_telemetry_default_and_secret_redaction(
    tmp_path: Path, fake_cli: Path
) -> None:
    root = _repository(tmp_path)
    trace = tmp_path / "trace.json"

    result, payload = _run(
        root,
        fake_cli,
        OPENWIKI_TEST_TRACE=str(trace),
        OPENWIKI_TEST_PROVIDER_SECRET="provider-secret-value",
    )

    assert result.returncode == 0
    assert json.loads(trace.read_text()) == {
        "argv": ["code", "--update", "--print"],
        "telemetry": "1",
        "secret": "provider-secret-value",
    }
    assert "provider-secret-value" not in result.stdout
    assert "provider-secret-value" not in result.stderr
    assert "provider-secret-value" not in json.dumps(payload)


def test_telemetry_explicit_user_value_is_preserved(
    tmp_path: Path, fake_cli: Path
) -> None:
    root = _repository(tmp_path)
    trace = tmp_path / "trace.json"

    result, _payload = _run(
        root,
        fake_cli,
        OPENWIKI_TEST_TRACE=str(trace),
        OPENWIKI_TELEMETRY_DISABLED="0",
    )

    assert result.returncode == 0
    assert json.loads(trace.read_text())["telemetry"] == "0"


def test_concurrent_refresh_is_rejected_before_openwiki_starts(
    tmp_path: Path, fake_cli: Path
) -> None:
    root = _repository(tmp_path)
    external = tmp_path / "outside"
    external.write_text("outside\n", encoding="utf-8")
    (root / "AGENTS.md").symlink_to(external)
    lock_path = root / ".git" / "openwiki-refresh.lock"
    lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result, payload = _run(root, fake_cli)
    finally:
        os.close(lock_fd)

    assert result.returncode != 0
    assert payload["status"] == "busy"
    assert not (root / "openwiki/generated.md").exists()


def test_concurrent_protected_file_replacement_is_not_deleted(
    tmp_path: Path, fake_cli: Path
) -> None:
    root = _repository(tmp_path)
    ready = tmp_path / "ready"
    release = tmp_path / "release"
    env = {
        **os.environ,
        "PATH": f"{fake_cli}{os.pathsep}{os.environ['PATH']}",
        "OPENWIKI_TEST_MODE": "wait-for-replacement",
        "OPENWIKI_TEST_READY": str(ready),
        "OPENWIKI_TEST_RELEASE": str(release),
    }
    process = subprocess.Popen(
        [sys.executable, str(RUNNER)],
        cwd=root,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    for _ in range(300):
        if ready.exists():
            break
        time.sleep(0.01)
    assert ready.exists()
    for name, contents in (
        ("AGENTS.md", b"external agents\n"),
        ("CLAUDE.md", b"external claude\n"),
    ):
        replacement = root / f"{name}.replacement"
        replacement.write_bytes(contents)
        replacement.replace(root / name)
    release.touch()
    stdout, stderr = process.communicate(timeout=5)
    payload = json.loads(stdout)

    assert process.returncode != 0, stderr
    assert payload["error"] == "protected-file restoration failed"
    assert len(payload["restoration_errors"]) == 2
    assert (root / "AGENTS.md").read_bytes() == b"external agents\n"
    assert (root / "CLAUDE.md").read_bytes() == b"external claude\n"
