"""Focused regressions for bootstrap installation ownership boundaries."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from install_bootstrap import (  # noqa: E402
    copy_generated_tree,
    merge_gitignore,
    persisted_install_mode,
    populate_bootstrap_root,
    substitute_project_name,
    substitute_python_version,
    validate_agents_takeover,
    validate_install_roots,
)
from runtime_ownership import (  # noqa: E402
    bootstrap_root_paths,
    restore_manifest,
)
from check_runtime import runtime_drift_errors  # noqa: E402
import generate_targets as target_generator  # noqa: E402

INSTALLER = REPO_ROOT / "scripts" / "install_bootstrap.py"
GENERATED = REPO_ROOT / "dist" / "multi-agent"
LEGACY_SCHEMA_V2_RECEIPT = REPO_ROOT / "tests" / "fixtures" / "schema-v2-receipt.json"
LEGACY_SCHEMA_V2_CLOSEOUT_RECEIPT = (
    REPO_ROOT / "tests" / "fixtures" / "schema-v2-closeout-receipt.json"
)
LEGACY_SCHEMA_V2_RUNTIME = REPO_ROOT / "tests" / "fixtures" / "schema-v2-verify.py.txt"
LEGACY_SCHEMA_V2_RECEIPT_SHA256 = (
    "15c78e5320e23b1bb59c6751d165a87d2e74d146b431fd7320639bafd87e5c76"
)
LEGACY_SCHEMA_V2_CLOSEOUT_RECEIPT_SHA256 = (
    "5cf5c3477016200a817e0fa0de4db13aef06a84c64b791d3a90f51f90cb72f15"
)
LEGACY_SCHEMA_V2_SOURCE_COMMIT = "e2753a9f2fd24dd2fc952e20929a9c7bbb1eeb37"
LEGACY_SCHEMA_V2_RUNTIME_SHA256 = (
    "9abc7edbd1d31ab89c232ad451583867b5943ad42af7eee45d58ff60fbe35fad"
)


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _actor_env() -> dict[str, str]:
    return {
        **os.environ,
        "GIT_AUTHOR_NAME": "Installer Test",
        "GIT_AUTHOR_EMAIL": "installer@example.com",
        "GIT_COMMITTER_NAME": "Installer Test",
        "GIT_COMMITTER_EMAIL": "installer@example.com",
    }


def _tree_snapshot(root: Path) -> dict[Path, bytes | None]:
    return {
        path.relative_to(root): path.read_bytes() if path.is_file() else None
        for path in root.rglob("*")
    }


def _run_consumer_verifier(
    consumer: Path, mode: str, *extra_args: str
) -> subprocess.CompletedProcess[str]:
    """Run the installed verifier through its supported generated entrypoint."""
    return subprocess.run(
        [
            sys.executable,
            ".claude/scripts/verify.py",
            mode,
            "--format",
            "json",
            *extra_args,
        ],
        cwd=consumer,
        text=True,
        capture_output=True,
        check=False,
    )


def _content_hash(root: Path, merge_base: str) -> str:
    """Return the report freshness digest for the current staged consumer state."""
    diff = _git(root, "diff", "--no-color", "--no-ext-diff", merge_base)
    assert diff.returncode == 0, diff.stderr
    hashed = subprocess.run(
        ["git", "hash-object", "--stdin"],
        cwd=root,
        input=diff.stdout,
        text=True,
        capture_output=True,
        check=False,
    )
    assert hashed.returncode == 0, hashed.stderr
    return hashed.stdout.strip()


def _native_commit(consumer: Path) -> subprocess.CompletedProcess[str]:
    """Invoke the installed Git hook through a normal outer-repository commit."""
    return subprocess.run(
        ["git", "-C", str(consumer), "commit", "-m", "complete lifecycle"],
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )


def _trace_remote_git_commands(trace_path: Path) -> set[str]:
    """Return forbidden remote Git commands observed by a full process tree."""
    commands: set[str] = set()
    for line in trace_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        if event.get("event") == "start" and isinstance(event.get("argv"), list):
            commands.update(
                command
                for command in event["argv"]
                if command in {"fetch", "ls-remote", "pull", "merge", "push"}
            )
    return commands


def _historical_schema_v2_runtime() -> bytes:
    """Read the pinned pre-v3 verifier fixture without Git-history access."""
    runtime = LEGACY_SCHEMA_V2_RUNTIME.read_bytes()
    assert hashlib.sha256(runtime).hexdigest() == LEGACY_SCHEMA_V2_RUNTIME_SHA256
    assert b"SCHEMA_VERSION = 2" in runtime
    return runtime


def _write_lifecycle_reports(consumer: Path, metadata: dict[str, object]) -> None:
    """Write deterministic closeout inputs matching one installed phase receipt."""
    branch = metadata["branch"]
    phase = metadata["phase"]
    head = metadata["head_sha"]
    merge_base = metadata["merge_base_sha"]
    assert isinstance(branch, str) and branch
    assert isinstance(phase, str) and phase
    assert isinstance(head, str) and head
    assert isinstance(merge_base, str) and merge_base
    report_fields = {
        "branch": branch,
        "phase": phase,
        "base_ref": "dev",
        "head_sha": head,
        "merge_base_sha": merge_base,
        "dirty": False,
        "generated_at": "2026-08-30T00:00:00Z",
        "target": ".",
        "changed_files": ["src/example_consumer/__init__.py"],
        "content_hash": _content_hash(consumer, merge_base),
    }
    reports = consumer / ".claude" / "quality_reports"
    reports.mkdir(exist_ok=True)
    (reports / f"findings-{phase}.json").write_text(
        json.dumps(
            {
                **report_fields,
                "profiles_reviewed": ["code", "ponytail"],
                "findings": [],
                "counts": {"critical": 0, "major": 0, "minor": 0},
                "ponytail_reviewed": True,
                "ponytail_findings": 0,
            }
        ),
        encoding="utf-8",
    )


def _write_lifecycle_plans(consumer: Path) -> tuple[Path, Path]:
    """Create the smallest completed plan state accepted by the native gate."""
    plans = consumer / ".claude" / "plans"
    plans.mkdir(exist_ok=True)
    big_plan = plans / "consumer-lifecycle.md"
    small_plan = plans / "phase-one.md"
    big_plan.write_text(
        """---
name: consumer-lifecycle
type: big-plan
status: in-progress
current_phase: phase-one
phases:
  - phase-one
---
""",
        encoding="utf-8",
    )
    small_plan.write_text(
        """---
name: phase-one
type: small-plan
parent_plan: consumer-lifecycle
phase_index: 1
status: complete
closeout_session_log: .claude/session_logs/lifecycle.md
---
""",
        encoding="utf-8",
    )
    log = consumer / ".claude" / "session_logs" / "lifecycle.md"
    log.parent.mkdir(exist_ok=True)
    log.write_text(
        "**Status:** COMPLETED\n\n[LEARN] none - no new lessons this session\n",
        encoding="utf-8",
    )
    return big_plan, small_plan


def test_generated_verifier_requires_sibling_ownership_authority(
    tmp_path: Path,
) -> None:
    """A consumer runtime cannot borrow an arbitrary nearby authoring module."""
    generated_root = tmp_path / "generated"
    target_generator.generate(["multi-agent"], generated_root)
    consumer = generated_root / "multi-agent"
    (consumer / ".claude" / "scripts" / "runtime_ownership.py").unlink()
    (consumer / "scripts").mkdir()
    (consumer / "scripts" / "runtime_ownership.py").write_text(
        "raise RuntimeError('must not load')\n", encoding="utf-8"
    )

    result = _run_consumer_verifier(consumer, "fast")

    assert result.returncode != 0
    assert "runtime_ownership" in result.stderr


def test_generated_verifier_ignores_conflicting_pythonpath_authority(
    tmp_path: Path,
) -> None:
    """Only the generated verifier's sibling authority may govern a consumer."""
    generated_root = tmp_path / "generated"
    target_generator.generate(["multi-agent"], generated_root)
    consumer = generated_root / "multi-agent"
    conflicting = tmp_path / "conflicting"
    conflicting.mkdir()
    (conflicting / "runtime_ownership.py").write_text(
        "raise RuntimeError('must not load')\n", encoding="utf-8"
    )

    result = subprocess.run(
        [sys.executable, ".claude/scripts/verify.py", "fast", "--format", "json"],
        cwd=consumer,
        env={**os.environ, "PYTHONPATH": str(conflicting)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert "must not load" not in result.stderr


def test_installed_consumer_lifecycle_binds_nested_provenance_and_gate(
    tmp_path: Path,
) -> None:
    """The installed verifier and native commit gate reject stale provenance."""
    generated_root = tmp_path / "generated"
    target_generator.generate(["multi-agent"], generated_root)
    consumer = tmp_path / "consumer"
    source = consumer / "src" / "example_consumer" / "__init__.py"
    test_file = consumer / "tests" / "test_example.py"
    source.parent.mkdir(parents=True)
    test_file.parent.mkdir()
    (consumer / ".gitignore").write_text("__pycache__/\n", encoding="utf-8")
    (consumer / "pyproject.toml").write_text(
        """[project]
name = "example-consumer"
version = "0.1.0"
requires-python = ">=3.12"

[dependency-groups]
dev = ["mypy", "pytest", "ruff"]

[tool.mypy]
files = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
""",
        encoding="utf-8",
    )
    source.write_text('VALUE: str = "base"\n', encoding="utf-8")
    test_file.write_text(
        'from example_consumer import VALUE\n\n\ndef test_value() -> None:\n    assert VALUE == "base"\n',
        encoding="utf-8",
    )
    assert _git(consumer, "init", "-q", "-b", "dev").returncode == 0
    assert _git(consumer, "add", ".").returncode == 0
    assert (
        subprocess.run(
            ["git", "-C", str(consumer), "commit", "-q", "-m", "initial consumer"],
            env=_actor_env(),
            text=True,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )
    install = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            str(consumer),
            "--source",
            str(generated_root / "multi-agent"),
            "--local-only",
        ],
        cwd=REPO_ROOT,
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert install.returncode == 0, install.stdout + install.stderr
    for relative in bootstrap_root_paths(False):
        assert (consumer / relative).exists(), relative
        assert (consumer / ".claude" / "bootstrap-root" / relative).exists(), relative
    assert (
        _git(
            consumer, "checkout", "-qb", "consumer-lifecycle_implementation"
        ).returncode
        == 0
    )
    big_plan, small_plan = _write_lifecycle_plans(consumer)
    nested_plans = _git(consumer / ".claude", "add", "plans", "session_logs")
    assert nested_plans.returncode == 0, nested_plans.stderr
    nested_plan_commit = subprocess.run(
        ["git", "-C", str(consumer / ".claude"), "commit", "-qm", "plans"],
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert nested_plan_commit.returncode == 0, nested_plan_commit.stderr

    legacy_runtime = consumer / ".claude" / "scripts" / "verify.py"
    legacy_receipt = (
        consumer / ".claude" / "quality_reports" / "verification-phase-phase-one.json"
    )
    legacy_closeout_receipt = (
        consumer
        / ".claude"
        / "quality_reports"
        / "verification-closeout-phase-one.json"
    )
    legacy_receipt_bytes = LEGACY_SCHEMA_V2_RECEIPT.read_bytes()
    legacy_closeout_receipt_bytes = LEGACY_SCHEMA_V2_CLOSEOUT_RECEIPT.read_bytes()
    assert (
        hashlib.sha256(legacy_receipt_bytes).hexdigest()
        == LEGACY_SCHEMA_V2_RECEIPT_SHA256
    )
    assert (
        hashlib.sha256(legacy_closeout_receipt_bytes).hexdigest()
        == LEGACY_SCHEMA_V2_CLOSEOUT_RECEIPT_SHA256
    )
    legacy_runtime.write_bytes(_historical_schema_v2_runtime())
    legacy_receipt.parent.mkdir(exist_ok=True)
    legacy_receipt.write_bytes(legacy_receipt_bytes)
    legacy_closeout_receipt.write_bytes(legacy_closeout_receipt_bytes)
    assert (
        _git(
            consumer / ".claude", "add", "scripts/verify.py", "quality_reports"
        ).returncode
        == 0
    )
    legacy_commit = subprocess.run(
        ["git", "-C", str(consumer / ".claude"), "commit", "-qm", "legacy v2 state"],
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert legacy_commit.returncode == 0, legacy_commit.stderr
    legacy_complete_small_plan = small_plan.read_text(encoding="utf-8")
    small_plan.write_text(
        legacy_complete_small_plan.replace("status: complete", "status: in-progress")
        + "# dirty legacy state\n",
        encoding="utf-8",
    )
    legacy_small_plan_bytes = small_plan.read_bytes()
    application_before_refresh = {
        path: path.read_bytes() for path in (source, test_file)
    }
    refresh_trace = tmp_path / "legacy-refresh-trace.json"
    refresh = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            str(consumer),
            "--source",
            str(generated_root / "multi-agent"),
            "--local-only",
        ],
        cwd=REPO_ROOT,
        env={**_actor_env(), "GIT_TRACE2_EVENT": str(refresh_trace)},
        text=True,
        capture_output=True,
        check=False,
    )
    assert refresh.returncode == 0, refresh.stdout + refresh.stderr
    assert {
        path: path.read_bytes() for path in application_before_refresh
    } == application_before_refresh
    assert legacy_receipt.read_bytes() == legacy_receipt_bytes
    assert legacy_closeout_receipt.read_bytes() == legacy_closeout_receipt_bytes
    assert small_plan.read_bytes() == legacy_small_plan_bytes
    assert "SCHEMA_VERSION = 4" in legacy_runtime.read_text(encoding="utf-8")
    assert _trace_remote_git_commands(refresh_trace) == set()
    assert _git(consumer / ".claude", "status", "--porcelain").stdout == ""
    small_plan.write_text(legacy_complete_small_plan, encoding="utf-8")
    assert _git(consumer / ".claude", "add", "plans/phase-one.md").returncode == 0
    resumed_plan = subprocess.run(
        ["git", "-C", str(consumer / ".claude"), "commit", "-qm", "resume phase"],
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert resumed_plan.returncode == 0, resumed_plan.stderr
    original_source = source.read_text(encoding="utf-8")
    source.write_text('VALUE: str = "legacy-gate"\n', encoding="utf-8")
    assert _git(consumer, "add", "src/example_consumer/__init__.py").returncode == 0
    legacy_gate = _native_commit(consumer)
    assert legacy_gate.returncode != 0
    assert "unsupported schema_version" in legacy_gate.stderr
    source.write_text(original_source, encoding="utf-8")
    assert _git(consumer, "add", "src/example_consumer/__init__.py").returncode == 0
    legacy_archive = consumer / ".claude" / "quality_reports" / "legacy-v2"
    legacy_archive.mkdir()
    archived_phase = legacy_archive / legacy_receipt.name
    archived_closeout = legacy_archive / legacy_closeout_receipt.name
    legacy_receipt.rename(archived_phase)
    legacy_closeout_receipt.rename(archived_closeout)
    assert archived_phase.read_bytes() == legacy_receipt_bytes
    assert archived_closeout.read_bytes() == legacy_closeout_receipt_bytes
    assert _git(consumer / ".claude", "add", "quality_reports").returncode == 0
    archive_commit = subprocess.run(
        [
            "git",
            "-C",
            str(consumer / ".claude"),
            "commit",
            "-qm",
            "archive v2 evidence",
        ],
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert archive_commit.returncode == 0, archive_commit.stderr

    source.write_text('VALUE: str = "ready"\n', encoding="utf-8")
    test_file.write_text(
        'from example_consumer import VALUE\n\n\ndef test_value() -> None:\n    assert VALUE == "ready"\n',
        encoding="utf-8",
    )
    assert _git(consumer, "add", "src", "tests").returncode == 0
    assert _git(consumer, "add", ".gitignore").returncode == 0
    fast = _run_consumer_verifier(consumer, "fast")
    assert fast.returncode == 0, fast.stdout + fast.stderr
    assert _git(consumer, "add", "uv.lock").returncode == 0
    phase = _run_consumer_verifier(consumer, "phase", "--persist")
    assert phase.returncode == 0, phase.stdout + phase.stderr
    phase_receipt = json.loads(phase.stdout)
    metadata = phase_receipt["metadata"]
    assert isinstance(metadata, dict)
    _write_lifecycle_reports(consumer, metadata)
    nested_evidence = subprocess.run(
        [
            "git",
            "-C",
            str(consumer / ".claude"),
            "add",
            "quality_reports",
        ],
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert nested_evidence.returncode == 0, nested_evidence.stderr
    nested_evidence = subprocess.run(
        [
            "git",
            "-C",
            str(consumer / ".claude"),
            "commit",
            "-qm",
            "evidence",
        ],
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert nested_evidence.returncode == 0, nested_evidence.stderr

    original_source = source.read_text(encoding="utf-8")
    source.write_text('VALUE: str = "stale"\n', encoding="utf-8")
    assert (
        _run_consumer_verifier(
            consumer, "closeout", "--documentation-na", "fixture"
        ).returncode
        == 1
    )
    source.write_text(original_source, encoding="utf-8")

    original_small_plan = small_plan.read_text(encoding="utf-8")
    small_plan.write_text(original_small_plan + "\n# changed\n", encoding="utf-8")
    assert (
        _run_consumer_verifier(
            consumer, "closeout", "--documentation-na", "fixture"
        ).returncode
        == 1
    )
    small_plan.write_text(original_small_plan, encoding="utf-8")

    original_big_plan = big_plan.read_text(encoding="utf-8")
    big_plan.write_text(original_big_plan + "\n# changed\n", encoding="utf-8")
    assert (
        _run_consumer_verifier(
            consumer, "closeout", "--documentation-na", "fixture"
        ).returncode
        == 1
    )
    big_plan.write_text(original_big_plan, encoding="utf-8")

    runtime_file = consumer / ".claude" / "agents" / "coder.md"
    original_runtime = runtime_file.read_text(encoding="utf-8")
    runtime_file.write_text(original_runtime + "\nchanged\n", encoding="utf-8")
    assert (
        _run_consumer_verifier(
            consumer, "closeout", "--documentation-na", "fixture"
        ).returncode
        == 1
    )
    runtime_file.write_text(original_runtime, encoding="utf-8")

    closeout = _run_consumer_verifier(
        consumer, "closeout", "--persist", "--documentation-na", "fixture"
    )
    assert closeout.returncode == 0, closeout.stdout + closeout.stderr

    source.write_text('VALUE: str = "post-closeout"\n', encoding="utf-8")
    assert _git(consumer, "add", "src/example_consumer/__init__.py").returncode == 0
    stale_outer = _native_commit(consumer)
    assert stale_outer.returncode != 0
    source.write_text(original_source, encoding="utf-8")
    assert _git(consumer, "add", "src/example_consumer/__init__.py").returncode == 0

    runtime_file.write_text(original_runtime + "\nchanged\n", encoding="utf-8")
    stale_nested = _native_commit(consumer)
    assert stale_nested.returncode != 0
    runtime_file.write_text(original_runtime, encoding="utf-8")

    runtime_file.write_text(original_runtime + "\nstaged\n", encoding="utf-8")
    assert _git(consumer / ".claude", "add", "agents/coder.md").returncode == 0
    runtime_file.write_text(original_runtime, encoding="utf-8")
    index_only_nested = _native_commit(consumer)
    assert index_only_nested.returncode != 0
    assert _git(consumer / ".claude", "add", "agents/coder.md").returncode == 0

    for artifact in (
        consumer / ".claude" / "quality_reports" / "verification-phase-phase-one.json",
        consumer / ".claude" / "quality_reports" / "findings-phase-one.json",
        consumer / ".claude" / "session_logs" / "lifecycle.md",
        consumer
        / ".claude"
        / "quality_reports"
        / "verification-closeout-phase-one.json",
    ):
        original_artifact = artifact.read_text(encoding="utf-8")
        artifact.write_text(original_artifact + "\ntampered\n", encoding="utf-8")
        assert _native_commit(consumer).returncode != 0
        artifact.write_text(original_artifact, encoding="utf-8")

    committed = _native_commit(consumer)
    assert committed.returncode == 0, committed.stdout + committed.stderr

    big_plan.write_text(
        big_plan.read_text(encoding="utf-8")
        .replace("status: in-progress", "status: complete")
        .replace("current_phase: phase-one", "current_phase: "),
        encoding="utf-8",
    )
    remote = tmp_path / "remote.git"
    assert (
        _git(tmp_path, "init", "--bare", "-q", "-b", "dev", str(remote)).returncode == 0
    )
    assert _git(consumer, "remote", "add", "origin", str(remote)).returncode == 0
    assert _git(consumer, "push", "origin", "dev").returncode == 0

    big_plan.write_text(big_plan.read_text(encoding="utf-8") + "# changed\n")
    rejected_push = _git(
        consumer, "push", "origin", "consumer-lifecycle_implementation"
    )
    assert rejected_push.returncode != 0
    assert "control-plane provenance is stale" in rejected_push.stderr
    big_plan.write_text(
        big_plan.read_text(encoding="utf-8").replace("# changed\n", ""),
        encoding="utf-8",
    )

    immediate_push = _git(
        consumer, "push", "origin", "consumer-lifecycle_implementation"
    )
    assert immediate_push.returncode == 0, immediate_push.stdout + immediate_push.stderr

    checkpoint = subprocess.run(
        [
            "git",
            "-C",
            str(consumer / ".claude"),
            "add",
            "plans/consumer-lifecycle.md",
        ],
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert checkpoint.returncode == 0, checkpoint.stderr
    checkpoint = subprocess.run(
        ["git", "-C", str(consumer / ".claude"), "commit", "-qm", "checkpoint"],
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert checkpoint.returncode == 0, checkpoint.stderr

    checkpoint_remote = tmp_path / "checkpoint.git"
    assert (
        _git(
            tmp_path, "init", "--bare", "-q", "-b", "dev", str(checkpoint_remote)
        ).returncode
        == 0
    )
    assert (
        _git(consumer, "remote", "add", "checkpoint", str(checkpoint_remote)).returncode
        == 0
    )
    pushed = _git(
        consumer,
        "push",
        "checkpoint",
        "consumer-lifecycle_implementation:checkpointed-terminal",
    )
    assert pushed.returncode == 0, pushed.stdout + pushed.stderr


def test_installed_verifier_uses_consumer_native_scopes(tmp_path: Path) -> None:
    """A generated bootstrap verifies consumer code without authoring paths."""
    generated_root = tmp_path / "generated"
    target_generator.generate(["multi-agent"], generated_root)
    consumer = tmp_path / "consumer"
    source = consumer / "src" / "example_consumer" / "__init__.py"
    test_file = consumer / "tests" / "test_example.py"
    source.parent.mkdir(parents=True)
    test_file.parent.mkdir()
    (consumer / "pyproject.toml").write_text(
        """[project]
name = "example-consumer"
version = "0.1.0"
requires-python = ">=3.12"

[dependency-groups]
dev = ["mypy", "pytest", "ruff"]

[tool.mypy]
files = ["src"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]

[tool.ruff.lint]
select = ["E", "F"]
""",
        encoding="utf-8",
    )
    source.write_text(
        '"""Example consumer package."""\n\n\ndef greet() -> str:\n    return "hello"\n',
        encoding="utf-8",
    )
    test_file.write_text(
        'from example_consumer import greet\n\n\ndef test_greet() -> None:\n    assert greet() == "hello"\n',
        encoding="utf-8",
    )
    assert _git(consumer, "init", "-q", "-b", "dev").returncode == 0
    assert _git(consumer, "add", ".").returncode == 0
    initial_commit = subprocess.run(
        ["git", "-C", str(consumer), "commit", "-q", "-m", "initial consumer"],
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert initial_commit.returncode == 0, initial_commit.stderr

    install = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            str(consumer),
            "--source",
            str(generated_root / "multi-agent"),
            "--local-only",
        ],
        cwd=REPO_ROOT,
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert install.returncode == 0, install.stdout + install.stderr

    (consumer / ".claude" / "consumer_noise.py").write_text(
        "import never_used\n", encoding="utf-8"
    )

    fast = _run_consumer_verifier(consumer, "fast")
    phase = _run_consumer_verifier(
        consumer, "phase", "--persist", "--phase", "consumer-native-fixture"
    )
    assert fast.returncode == 0, fast.stdout + fast.stderr
    assert phase.returncode == 0, phase.stdout + phase.stderr

    source.write_text(
        '"""Example consumer package."""\n\n\nimport os\n\n\ndef greet() -> str:\n    return "hello"\n',
        encoding="utf-8",
    )
    ruff_failure = _run_consumer_verifier(consumer, "fast")
    ruff_receipt = json.loads(ruff_failure.stdout)
    assert ruff_failure.returncode == 1
    assert (
        next(
            check for check in ruff_receipt["checks"] if check["id"] == "VFY-RUFF-001"
        )["status"]
        == "FAIL"
    )
    assert "shared" not in ruff_failure.stdout
    assert "scripts" not in ruff_failure.stdout

    source.write_text(
        '"""Example consumer package."""\n\n\ndef greet() -> str:\n    return "hello"\n\n\ndef broken() -> str:\n    return 1\n',
        encoding="utf-8",
    )
    mypy_failure = _run_consumer_verifier(
        consumer, "phase", "--phase", "consumer-native-fixture"
    )
    mypy_receipt = json.loads(mypy_failure.stdout)
    assert mypy_failure.returncode == 1
    assert (
        next(
            check for check in mypy_receipt["checks"] if check["id"] == "VFY-MYPY-001"
        )["status"]
        == "FAIL"
    )

    source.write_text(
        '"""Example consumer package."""\n\n\ndef greet() -> str:\n    return "hello"\n',
        encoding="utf-8",
    )
    test_file.write_text(
        'from example_consumer import greet\n\n\ndef test_greet() -> None:\n    assert greet() == "goodbye"\n',
        encoding="utf-8",
    )
    pytest_failure = _run_consumer_verifier(
        consumer, "phase", "--phase", "consumer-native-fixture"
    )
    pytest_receipt = json.loads(pytest_failure.stdout)
    assert pytest_failure.returncode == 1
    assert (
        next(
            check
            for check in pytest_receipt["checks"]
            if check["id"] == "VFY-PYTEST-001"
        )["status"]
        == "FAIL"
    )


@pytest.mark.parametrize("gitfile", (False, True), ids=("directory", "gitfile"))
def test_copy_preserves_nested_git_metadata(tmp_path: Path, gitfile: bool) -> None:
    """Obsolete-file pruning never treats nested Git metadata as bootstrap data."""
    source = tmp_path / "generated"
    target = tmp_path / "consumer"
    (source / ".claude").mkdir(parents=True)
    (source / ".claude" / "generated.md").write_text("fresh\n")
    nested_git = target / ".claude" / ".git"
    if gitfile:
        nested_git.parent.mkdir(parents=True)
        nested_git.write_text("gitdir: ../ai-state.git\n")
    else:
        nested_git.mkdir(parents=True)
        (nested_git / "HEAD").write_text("ref: refs/heads/ai-state\n")

    copy_generated_tree(source, target, dry_run=False)

    if gitfile:
        assert nested_git.read_text() == "gitdir: ../ai-state.git\n"
    else:
        assert (nested_git / "HEAD").read_text() == "ref: refs/heads/ai-state\n"
    assert (target / ".claude" / "generated.md").read_text() == "fresh\n"


def test_substitutions_update_root_guidance_and_workspace_facts(tmp_path: Path) -> None:
    """Installer reconciles project and Python facts across generated guidance."""
    target = tmp_path / "example-consumer"
    project_fact = "**Project:** [TODO: project name and one-liner description]\n"
    python_facts = (
        "**Python:** 3.12+ | **Package Manager:** uv\n**Stack:** Python 3.12+ with uv\n"
    )
    for relative in (
        Path("CLAUDE.md"),
        Path("AGENTS.md"),
        Path(".claude/instructions/workspace.instructions.md"),
        Path(".claude/instructions/workspace.md"),
    ):
        path = target / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(project_fact + python_facts)
    (target / "pyproject.toml").write_text('[project]\nrequires-python = ">=3.13"\n')

    substitute_project_name(target, dry_run=False)
    substitute_python_version(target, dry_run=False)

    for relative in (
        Path("CLAUDE.md"),
        Path("AGENTS.md"),
        Path(".claude/instructions/workspace.instructions.md"),
        Path(".claude/instructions/workspace.md"),
    ):
        text = (target / relative).read_text()
        assert "[TODO: project name" not in text
        assert "**Project:** example-consumer" in text
        assert "**Python:** 3.13+" in text
        assert "**Stack:** Python 3.13+ with uv" in text


def test_copy_preserves_genuine_tracked_copilot_authoring(tmp_path: Path) -> None:
    """Local-only mode preserves tracked Copilot files without prior bootstrap ownership."""
    source = tmp_path / "generated"
    target = tmp_path / "consumer"
    generated_agent = source / ".github" / "agents" / "reviewer.agent.md"
    generated_agent.parent.mkdir(parents=True)
    generated_agent.write_text("generated\n")
    authored_agent = target / ".github" / "agents" / "reviewer.agent.md"
    authored_agent.parent.mkdir(parents=True)
    authored_agent.write_text("project-authored\n")
    assert _git(target, "init", "-q").returncode == 0
    assert _git(target, "add", ".github/agents/reviewer.agent.md").returncode == 0

    copy_generated_tree(source, target, dry_run=False)

    assert authored_agent.read_text() == "project-authored\n"


def test_copy_preserves_tracked_authoring_root_adapters(tmp_path: Path) -> None:
    """Dogfood refreshes never overwrite either tracked root adapter."""
    source = tmp_path / "generated"
    target = tmp_path / "bootstrap-authoring"
    target.mkdir()
    assert _git(target, "init", "-q").returncode == 0
    for name in ("AGENTS.md", "CLAUDE.md"):
        (source / name).parent.mkdir(parents=True, exist_ok=True)
        (source / name).write_text(f"generated {name}\n")
        (target / name).write_text(f"authoring {name}\n")
        assert _git(target, "add", name).returncode == 0

    copy_generated_tree(source, target, dry_run=False)

    for name in ("AGENTS.md", "CLAUDE.md"):
        assert (target / name).read_text() == f"authoring {name}\n"


@pytest.mark.parametrize(
    "relation", ("equal", "source-inside-target", "target-inside-source")
)
@pytest.mark.parametrize("dry_run", (False, True), ids=("write", "dry-run"))
def test_installer_rejects_overlapping_roots_before_writes(
    tmp_path: Path, relation: str, dry_run: bool
) -> None:
    """Every overlap direction fails before legacy migration or generated copying."""
    if relation == "equal":
        source = target = tmp_path / "same"
    elif relation == "source-inside-target":
        target = tmp_path / "consumer"
        source = target / "generated"
    else:
        source = tmp_path / "generated"
        target = source / "consumer"
    source.mkdir(parents=True)
    marker = target / ".claude" / "MEMORY.md"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("consumer state\n")
    before = _tree_snapshot(tmp_path)
    command = [sys.executable, str(INSTALLER), str(target), "--source", str(source)]
    if dry_run:
        command.append("--dry-run")

    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "must be separate, non-overlapping directories" in result.stderr
    assert _tree_snapshot(tmp_path) == before
    assert not (target / ".claude" / ".git").exists()


def test_committed_to_local_copilot_migration_refreshes_owned_files(
    tmp_path: Path,
) -> None:
    """Explicit local mode refreshes prior bootstrap-owned tracked Copilot bytes."""
    target = tmp_path / "consumer"
    target.mkdir()
    assert _git(target, "init", "-q").returncode == 0
    first = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            str(target),
            "--source",
            str(GENERATED),
            "--commit-copilot-surface",
            "--local-only",
        ],
        cwd=REPO_ROOT,
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert first.returncode == 0, first.stdout + first.stderr

    agent_relative = Path(".github/agents/orchestrator.agent.md")
    agent = target / agent_relative
    obsolete_relative = Path(".github/agents/removed.agent.md")
    obsolete = target / obsolete_relative
    assert agent.is_file()
    obsolete.write_text("obsolete bootstrap file\n")
    assert _git(target, "add", ".github").returncode == 0
    agent.write_text("stale tracked bootstrap file\n")

    migrated = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            str(target),
            "--source",
            str(GENERATED),
            "--no-commit-copilot-surface",
            "--local-only",
        ],
        cwd=REPO_ROOT,
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert migrated.returncode == 0, migrated.stdout + migrated.stderr
    expected = (GENERATED / agent_relative).read_bytes()
    assert agent.read_bytes() == expected
    assert (
        target / ".claude" / "bootstrap-root" / agent_relative
    ).read_bytes() == expected
    assert not obsolete.exists()
    assert not (target / ".claude" / "bootstrap-root" / obsolete_relative).exists()
    manifest = (target / ".claude" / "bootstrap-ownership.env").read_text()
    assert "BOOTSTRAP_COMMIT_COPILOT_SURFACE=0\n" in manifest


def test_installer_preserves_consumer_memory_bytes_on_refresh_and_migration(
    tmp_path: Path,
) -> None:
    """Consumer-owned MEMORY.md survives both supported installation paths."""
    memory = b"# Consumer memory\r\n\r\n- preserve \xff\x00 exact bytes\r\n"

    refreshed = tmp_path / "refreshed-consumer"
    refreshed.mkdir()
    assert _git(refreshed, "init", "-q").returncode == 0
    first_install = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            str(refreshed),
            "--source",
            str(GENERATED),
            "--local-only",
        ],
        cwd=REPO_ROOT,
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert first_install.returncode == 0, first_install.stdout + first_install.stderr
    refreshed_memory = refreshed / ".claude" / "MEMORY.md"
    refreshed_memory.write_bytes(memory)
    assert _git(refreshed / ".claude", "add", "MEMORY.md").returncode == 0
    assert (
        _git(
            refreshed / ".claude", "commit", "-q", "-m", "session: consumer memory"
        ).returncode
        == 0
    )

    update = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            str(refreshed),
            "--source",
            str(GENERATED),
            "--local-only",
        ],
        cwd=REPO_ROOT,
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert update.returncode == 0, update.stdout + update.stderr
    assert refreshed_memory.read_bytes() == memory
    refreshed_state = subprocess.run(
        ["git", "-C", str(refreshed / ".claude"), "show", "HEAD:MEMORY.md"],
        capture_output=True,
        check=False,
    )
    assert refreshed_state.returncode == 0
    assert refreshed_state.stdout == memory

    legacy = tmp_path / "legacy-consumer"
    legacy.mkdir()
    assert _git(legacy, "init", "-q").returncode == 0
    legacy_memory = legacy / ".claude" / "MEMORY.md"
    legacy_memory.parent.mkdir(parents=True)
    legacy_memory.write_bytes(memory)

    migration = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            str(legacy),
            "--source",
            str(GENERATED),
            "--local-only",
        ],
        cwd=REPO_ROOT,
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert migration.returncode == 0, migration.stdout + migration.stderr
    assert legacy_memory.read_bytes() == memory
    legacy_state = subprocess.run(
        ["git", "-C", str(legacy / ".claude"), "show", "HEAD:MEMORY.md"],
        capture_output=True,
        check=False,
    )
    assert legacy_state.returncode == 0
    assert legacy_state.stdout == memory


# --- --allow-self: the bootstrap repo refreshing its own dogfood overlay ----


def test_overlapping_roots_rejected_without_allow_self(tmp_path: Path) -> None:
    """Default stays fail-closed for every overlapping-root shape."""
    target = tmp_path / "repo"
    inside = target / "dist" / "multi-agent"
    for source in (target, inside):
        with pytest.raises(SystemExit) as excinfo:
            validate_install_roots(source, target)
        assert "non-overlapping" in str(excinfo.value)
    with pytest.raises(SystemExit) as excinfo:
        validate_install_roots(target, inside)
    assert "non-overlapping" in str(excinfo.value)


def test_rejection_without_the_flag_names_the_opt_in(tmp_path: Path) -> None:
    """A blocked dogfood refresh should say how to proceed deliberately."""
    target = tmp_path / "repo"
    with pytest.raises(SystemExit) as excinfo:
        validate_install_roots(target / "dist" / "multi-agent", target)
    assert "--allow-self" in str(excinfo.value)


def test_allow_self_permits_only_the_bootstrap_repo(tmp_path: Path) -> None:
    """Source inside target is permitted for this repo, refused elsewhere."""
    validate_install_roots(GENERATED, REPO_ROOT, allow_self=True)

    other = tmp_path / "someone-elses-repo"
    with pytest.raises(SystemExit) as excinfo:
        validate_install_roots(other / "dist" / "multi-agent", other, allow_self=True)
    assert "--allow-self only refreshes" in str(excinfo.value)


def test_allow_self_still_rejects_the_dangerous_overlaps() -> None:
    """The flag must not unlock installing a tree over or under itself."""
    with pytest.raises(SystemExit):
        validate_install_roots(REPO_ROOT, REPO_ROOT, allow_self=True)
    with pytest.raises(SystemExit):
        validate_install_roots(GENERATED, GENERATED / "nested", allow_self=True)


def test_separate_roots_are_unaffected_by_the_flag(tmp_path: Path) -> None:
    """Ordinary consumer installs behave identically with or without it."""
    consumer = tmp_path / "consumer"
    validate_install_roots(GENERATED, consumer)
    validate_install_roots(GENERATED, consumer, allow_self=True)


def test_local_client_settings_are_consumer_state() -> None:
    """`settings.local.json` is machine-local; a refresh must not delete it."""
    from runtime_ownership import is_consumer_state_path

    assert is_consumer_state_path("settings.local.json")
    assert is_consumer_state_path(".cache/context-mode/sessions/local.db")


def test_refresh_preserves_local_context_mode_cache_bytes(tmp_path: Path) -> None:
    source = tmp_path / "generated"
    target = tmp_path / "consumer"
    (source / ".claude/hooks").mkdir(parents=True)
    (source / ".claude/hooks/generated.txt").write_text("generated\n")
    cache = target / ".claude/.cache/context-mode/sessions/local.db"
    cache.parent.mkdir(parents=True)
    cache.write_bytes(b"local-cache\x00bytes")

    copy_generated_tree(source, target, dry_run=False)

    assert cache.read_bytes() == b"local-cache\x00bytes"


def test_fresh_install_gitignore_excludes_provenance_secret(tmp_path: Path) -> None:
    """context-mode-dispatch.sh creates its anti-forgery provenance secret
    (`.context-mode-provenance.secret`) at the consumer repository root,
    outside `.claude/`. A freshly-installed `.gitignore` must exclude it, or
    a routine `git add -A` at the consumer root commits the secret into the
    consumer's main history (MAJOR finding)."""
    target = tmp_path / "consumer"
    target.mkdir()
    assert _git(target, "init", "-q").returncode == 0

    result = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            str(target),
            "--source",
            str(GENERATED),
            "--local-only",
        ],
        cwd=REPO_ROOT,
        env=_actor_env(),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    gitignore = (target / ".gitignore").read_text(encoding="utf-8")
    assert ".context-mode-provenance.secret" in gitignore


def test_agents_directory_is_a_refreshable_root_adapter(tmp_path: Path) -> None:
    """A generated `.agents` directory is mirrored and ignored as one adapter."""
    source = tmp_path / "generated"
    generated_agent = source / ".agents/agents/coder/agent.md"
    generated_agent.parent.mkdir(parents=True)
    generated_agent.write_text("generated coder v1\n", encoding="utf-8")
    target = tmp_path / "consumer"
    target.mkdir()
    assert _git(target, "init", "-q").returncode == 0
    validate_agents_takeover(source, target)
    copy_generated_tree(source, target, dry_run=False)
    populate_bootstrap_root(target, False, False)
    merge_gitignore(target, False)

    assert (
        target / ".claude/bootstrap-root/.agents/agents/coder/agent.md"
    ).read_text() == "generated coder v1\n"
    ignore_block = (target / ".gitignore").read_text(encoding="utf-8")
    assert ignore_block.count(".agents/") == 1
    manifest = (target / ".claude/bootstrap-ownership.env").read_text()
    assert "BOOTSTRAP_ROOT_PATH=.agents\n" in manifest
    assert "BOOTSTRAP_ANTIGRAVITY_PATH" not in manifest
    assert not (target / ".claude/antigravity-ownership.env").exists()

    generated_agent.write_text("generated coder v2\n", encoding="utf-8")
    validate_agents_takeover(source, target)
    copy_generated_tree(source, target, dry_run=False)
    populate_bootstrap_root(target, False, False)
    assert (
        target / ".agents/agents/coder/agent.md"
    ).read_text() == "generated coder v2\n"
    assert (
        target / ".claude/bootstrap-root/.agents/agents/coder/agent.md"
    ).read_text() == "generated coder v2\n"


@pytest.mark.parametrize("dry_run", (False, True), ids=("write", "dry-run"))
def test_agents_takeover_refuses_unproved_content_before_writes(
    tmp_path: Path, dry_run: bool
) -> None:
    """Private or modified `.agents` content blocks both installer modes unchanged."""
    source = tmp_path / "generated"
    generated = source / ".agents/agents/coder/agent.md"
    generated.parent.mkdir(parents=True)
    generated.write_text("bootstrap adapter\n", encoding="utf-8")
    target = tmp_path / "consumer"
    private = target / ".agents/skills/company-private/SKILL.md"
    private.parent.mkdir(parents=True)
    private.write_text("company-owned\n", encoding="utf-8")
    before = _tree_snapshot(tmp_path)
    command = [
        sys.executable,
        str(INSTALLER),
        str(target),
        "--source",
        str(source),
        "--local-only",
    ]
    if dry_run:
        command.append("--dry-run")

    result = subprocess.run(
        command, cwd=REPO_ROOT, text=True, capture_output=True, check=False
    )

    assert result.returncode != 0
    assert ".agents/skills/company-private/SKILL.md" in result.stderr
    assert "move or back up" in result.stderr
    assert _tree_snapshot(tmp_path) == before


@pytest.mark.parametrize("outer", ("absent", "current"))
def test_agents_takeover_refuses_private_mirror_before_writes(
    tmp_path: Path, outer: str
) -> None:
    """A mirror is classified before any copy, even when the outer tree is safe."""
    source = tmp_path / "generated"
    generated = source / ".agents/agents/coder/agent.md"
    generated.parent.mkdir(parents=True)
    generated.write_text("generated\n", encoding="utf-8")
    target = tmp_path / "consumer"
    if outer == "current":
        outer_agent = target / ".agents/agents/coder/agent.md"
        outer_agent.parent.mkdir(parents=True)
        outer_agent.write_text("generated\n", encoding="utf-8")
    private_mirror = target / ".claude/bootstrap-root/.agents/private.txt"
    private_mirror.parent.mkdir(parents=True)
    private_mirror.write_text("private\n", encoding="utf-8")
    before = _tree_snapshot(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            str(target),
            "--source",
            str(source),
            "--local-only",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert ".claude/bootstrap-root/.agents/private.txt" in result.stderr
    assert _tree_snapshot(tmp_path) == before


def test_agents_takeover_reports_sorted_mirror_and_legacy_conflicts(
    tmp_path: Path,
) -> None:
    """Unsafe evidence and multiple mirror paths produce stable actionable output."""
    source = tmp_path / "generated"
    generated = source / ".agents/agents/coder/agent.md"
    generated.parent.mkdir(parents=True)
    generated.write_text("generated\n", encoding="utf-8")
    target = tmp_path / "consumer"
    for name in ("z-private.txt", "a-private.txt"):
        path = target / ".claude/bootstrap-root/.agents" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("private\n", encoding="utf-8")
    allowlist = target / ".claude/antigravity-ownership.env"
    allowlist.parent.mkdir(parents=True, exist_ok=True)
    allowlist.write_text("invalid\n", encoding="utf-8")

    with pytest.raises(SystemExit, match=r"Refusing \.agents takeover") as error:
        validate_agents_takeover(source, target)

    message = str(error.value)
    assert (
        message.index(".claude/antigravity-ownership.env")
        < message.index(".claude/bootstrap-root/.agents/a-private.txt")
        < message.index(".claude/bootstrap-root/.agents/z-private.txt")
    )


def test_agents_takeover_rejects_symlink_and_malformed_root_evidence(
    tmp_path: Path,
) -> None:
    """Legacy evidence requires regular files and a complete valid root manifest."""
    source = tmp_path / "generated"
    generated = source / ".agents/agents/coder/agent.md"
    generated.parent.mkdir(parents=True)
    generated.write_text("generated\n", encoding="utf-8")
    target = tmp_path / "consumer"
    agent = target / ".agents/agents/coder/agent.md"
    agent.parent.mkdir(parents=True)
    agent.write_text("generated\n", encoding="utf-8")
    allowlist = target / ".claude/antigravity-ownership.env"
    allowlist.parent.mkdir(parents=True)
    allowlist.symlink_to(tmp_path / "outside")

    with pytest.raises(SystemExit, match=r"antigravity-ownership.env"):
        validate_agents_takeover(source, target)

    allowlist.unlink()
    records = "BOOTSTRAP_ANTIGRAVITY_PATH=.agents/agents/coder/agent.md\n"
    allowlist.write_text(records, encoding="utf-8")
    (target / ".claude/bootstrap-ownership.env").write_text(
        "BOOTSTRAP_COMMIT_COPILOT_SURFACE=0\n"
        "BOOTSTRAP_ROOT_PATH=../../outside\n" + records,
        encoding="utf-8",
    )

    with pytest.raises(SystemExit, match=r"bootstrap-ownership.env"):
        validate_agents_takeover(source, target)


def test_agents_takeover_refuses_identical_unowned_outer_and_mirror(
    tmp_path: Path,
) -> None:
    """Matching old trees alone never authorize a directory takeover."""
    source = tmp_path / "generated"
    generated = source / ".agents/agents/coder/agent.md"
    generated.parent.mkdir(parents=True)
    generated.write_text("current\n", encoding="utf-8")
    target = tmp_path / "consumer"
    for root in (
        target / ".agents",
        target / ".claude/bootstrap-root/.agents",
    ):
        agent = root / "agents/coder/agent.md"
        agent.parent.mkdir(parents=True, exist_ok=True)
        agent.write_text("unowned old copy\n", encoding="utf-8")
    before = _tree_snapshot(tmp_path)

    result = subprocess.run(
        [
            sys.executable,
            str(INSTALLER),
            str(target),
            "--source",
            str(source),
            "--local-only",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert ".agents/agents/coder/agent.md" in result.stderr
    assert _tree_snapshot(tmp_path) == before


def test_agents_takeover_refuses_unproved_current_mirror_when_outer_is_missing(
    tmp_path: Path,
) -> None:
    """A byte-identical mirror alone is not ownership evidence."""
    source = tmp_path / "generated"
    generated = source / ".agents/agents/coder/agent.md"
    generated.parent.mkdir(parents=True)
    generated.write_text("current\n", encoding="utf-8")
    target = tmp_path / "consumer"
    mirror = target / ".claude/bootstrap-root/.agents/agents/coder/agent.md"
    mirror.parent.mkdir(parents=True)
    mirror.write_text("current\n", encoding="utf-8")
    before = _tree_snapshot(tmp_path)

    with pytest.raises(SystemExit, match=r"\.claude/bootstrap-root/\.agents"):
        validate_agents_takeover(source, target)

    assert _tree_snapshot(tmp_path) == before


def test_agents_takeover_accepts_managed_mirror_when_outer_is_missing(
    tmp_path: Path,
) -> None:
    """A valid current root manifest proves an older mirror is safe to refresh."""
    source = tmp_path / "generated"
    generated = source / ".agents/agents/coder/agent.md"
    generated.parent.mkdir(parents=True)
    generated.write_text("current\n", encoding="utf-8")
    target = tmp_path / "consumer"
    mirror = target / ".claude/bootstrap-root/.agents/agents/coder/agent.md"
    mirror.parent.mkdir(parents=True)
    mirror.write_text("older managed copy\n", encoding="utf-8")
    (target / ".claude/bootstrap-ownership.env").write_text(
        restore_manifest(False), encoding="utf-8"
    )

    validate_agents_takeover(source, target)
    copy_generated_tree(source, target, dry_run=False)
    populate_bootstrap_root(target, False, False)

    assert (target / ".agents/agents/coder/agent.md").read_text() == "current\n"
    assert mirror.read_text() == "current\n"


@pytest.mark.parametrize(
    ("evidence", "relative"),
    (
        ("invalid-utf8", ".claude/antigravity-ownership.env"),
        ("directory", ".claude/antigravity-ownership.env"),
        ("invalid-utf8", ".claude/bootstrap-ownership.env"),
        ("directory", ".claude/bootstrap-ownership.env"),
    ),
)
def test_agents_takeover_rejects_nonregular_or_invalid_legacy_evidence(
    tmp_path: Path, evidence: str, relative: str
) -> None:
    """Unreadable ownership evidence is an actionable blocker, never a traceback."""
    source = tmp_path / "generated"
    generated = source / ".agents/agents/coder/agent.md"
    generated.parent.mkdir(parents=True)
    generated.write_text("generated\n", encoding="utf-8")
    target = tmp_path / "consumer"
    agent = target / ".agents/agents/coder/agent.md"
    agent.parent.mkdir(parents=True)
    agent.write_text("generated\n", encoding="utf-8")
    evidence_path = target / relative
    evidence_path.parent.mkdir(parents=True)
    if evidence == "invalid-utf8":
        evidence_path.write_bytes(b"\xff\xfe")
    else:
        evidence_path.mkdir()

    with pytest.raises(SystemExit, match=relative.removeprefix(".claude/")):
        validate_agents_takeover(source, target)


def test_agents_takeover_rejects_unsafe_links_and_malformed_legacy_evidence(
    tmp_path: Path,
) -> None:
    """Neither a link nor a forged old manifest can authorize directory takeover."""
    source = tmp_path / "generated"
    generated = source / ".agents/agents/coder/agent.md"
    generated.parent.mkdir(parents=True)
    generated.write_text("bootstrap adapter\n", encoding="utf-8")
    target = tmp_path / "consumer"
    agents = target / ".agents"
    agents.mkdir(parents=True)
    (agents / "agents").symlink_to(tmp_path / "outside", target_is_directory=True)

    with pytest.raises(SystemExit, match=r"\.agents/agents"):
        validate_agents_takeover(source, target)

    (agents / "agents").unlink()
    collision = agents / "agents/coder/agent.md"
    collision.parent.mkdir(parents=True)
    collision.write_text("bootstrap adapter\n", encoding="utf-8")
    evidence = target / ".claude/antigravity-ownership.env"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("not a legacy record\n", encoding="utf-8")

    with pytest.raises(SystemExit, match=r"Refusing \.agents takeover"):
        validate_agents_takeover(source, target)


def test_agents_takeover_refuses_modified_or_later_consumer_content(
    tmp_path: Path,
) -> None:
    """A later `.agents` edit remains a blocker even after a valid takeover."""
    source = tmp_path / "generated"
    generated = source / ".agents/agents/coder/agent.md"
    generated.parent.mkdir(parents=True)
    generated.write_text("bootstrap adapter\n", encoding="utf-8")
    target = tmp_path / "consumer"
    validate_agents_takeover(source, target)
    copy_generated_tree(source, target, dry_run=False)
    populate_bootstrap_root(target, False, False)

    generated_target = target / ".agents/agents/coder/agent.md"
    generated_target.write_text("consumer edit\n", encoding="utf-8")
    with pytest.raises(SystemExit, match=r"\.agents/agents/coder/agent\.md"):
        validate_agents_takeover(source, target)

    generated_target.write_text("bootstrap adapter\n", encoding="utf-8")
    private = target / ".agents/skills/company-private/SKILL.md"
    private.parent.mkdir(parents=True)
    private.write_text("consumer file\n", encoding="utf-8")
    with pytest.raises(SystemExit, match=r"\.agents/skills/company-private/SKILL.md"):
        validate_agents_takeover(source, target)


def test_agents_legacy_migration_prunes_only_mirrored_generated_paths(
    tmp_path: Path,
) -> None:
    """Legacy evidence migrates generated-only content and retains Copilot mode."""
    source = tmp_path / "generated"
    current = source / ".agents/agents/coder/agent.md"
    current.parent.mkdir(parents=True)
    current.write_text("current\n", encoding="utf-8")
    target = tmp_path / "consumer"
    current_target = target / ".agents/agents/coder/agent.md"
    obsolete_target = target / ".agents/agents/obsolete/agent.md"
    current_target.parent.mkdir(parents=True)
    current_target.write_text("current\n", encoding="utf-8")
    obsolete_target.parent.mkdir(parents=True)
    obsolete_target.write_text("obsolete\n", encoding="utf-8")
    records = (
        "BOOTSTRAP_ANTIGRAVITY_PATH=.agents/agents/coder/agent.md\n"
        "BOOTSTRAP_ANTIGRAVITY_PATH=.agents/agents/obsolete/agent.md\n"
    )
    allowlist = target / ".claude/antigravity-ownership.env"
    allowlist.parent.mkdir(parents=True)
    allowlist.write_text(records)
    legacy_roots = "\n".join(
        line
        for line in restore_manifest(True).splitlines()
        if line != "BOOTSTRAP_ROOT_PATH=.agents"
    )
    (target / ".claude/bootstrap-ownership.env").write_text(
        f"{legacy_roots}\n{records}", encoding="utf-8"
    )

    validate_agents_takeover(source, target)
    assert persisted_install_mode(target) is True
    copy_generated_tree(source, target, dry_run=False)
    populate_bootstrap_root(target, False, True)
    merge_gitignore(target, False, True)

    assert not obsolete_target.exists()
    assert not (target / ".claude/bootstrap-root/.agents/agents/obsolete").exists()
    assert not (target / ".claude/antigravity-ownership.env").exists()
    assert (
        "BOOTSTRAP_ROOT_PATH=.agents"
        in (target / ".claude/bootstrap-ownership.env").read_text()
    )


def test_runtime_check_accepts_root_owned_agents_manifest(tmp_path: Path) -> None:
    """A successful install validates `.agents` through the root manifest."""
    target = tmp_path / "consumer"
    target.mkdir()
    assert _git(target, "init", "-q").returncode == 0

    validate_agents_takeover(GENERATED, target)
    copy_generated_tree(GENERATED, target, dry_run=False)
    for name in ("AGENTS.md", "CLAUDE.md"):
        (target / name).write_bytes((REPO_ROOT / name).read_bytes())
    assert _git(target, "add", "AGENTS.md", "CLAUDE.md").returncode == 0
    populate_bootstrap_root(target, False, False)

    assert runtime_drift_errors(target, GENERATED) == []

    manifest = target / ".claude/bootstrap-ownership.env"
    manifest.write_text(
        manifest.read_text().replace("BOOTSTRAP_ROOT_PATH=.agents\n", "")
    )
    (target / ".agents/hooks.json").unlink()
    (target / ".claude/bootstrap-root/.agents/hooks.json").unlink()
    missing_hook_errors = runtime_drift_errors(target, GENERATED)
    assert any(
        ".claude/bootstrap-ownership.env" in error for error in missing_hook_errors
    )
    assert any(".agents/hooks.json" in error for error in missing_hook_errors)
