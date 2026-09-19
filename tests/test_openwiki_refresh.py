"""Deterministic boundary tests for the bootstrap-owned OpenWiki runner."""

from __future__ import annotations

import fcntl
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypedDict

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNNER = REPO_ROOT / "shared" / "scripts" / "openwiki_refresh.py"
RUNNER_SPEC = importlib.util.spec_from_file_location("openwiki_refresh_test", RUNNER)
assert RUNNER_SPEC is not None and RUNNER_SPEC.loader is not None
RUNNER_MODULE = importlib.util.module_from_spec(RUNNER_SPEC)
sys.modules[RUNNER_SPEC.name] = RUNNER_MODULE
RUNNER_SPEC.loader.exec_module(RUNNER_MODULE)


class RunnerResult(TypedDict, total=False):
    """The runner's real JSON result shape, keyed exactly as it prints them.

    Every field is optional here because which fields are present depends on
    ``status``: a ``not_enabled`` result carries only ``repository_root`` and
    ``status``, for example. Declaring the per-key value types (instead of a
    blanket ``object``) is what lets assertions like
    ``"x" in payload["out_of_scope_paths"]`` type-check against the actual
    ``list[str]`` the runner emits, rather than against an opaque ``object``.
    """

    status: str
    repository_root: str
    error: str
    node_version: str
    openwiki_version: str
    pre_existing_dirty_paths: list[str]
    modified_pre_existing_paths: list[str]
    control_plane_paths: list[str]
    new_paths: list[str]
    out_of_scope_paths: list[str]
    workflow_unchanged: bool
    openwiki_returncode: int | None
    restoration_errors: list[str]
    restoration_displaced_content: list[dict[str, object]]
    openwiki_tree_symlinks: dict[str, str]


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
import subprocess
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
if mode == "control-plane-cache-mutated":
    cache_file = root / ".claude" / ".cache" / "stats.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("after!\\n", encoding="utf-8")
if mode == "control-plane-memory-mutated":
    (root / ".claude" / "MEMORY.md").write_text("after!\\n", encoding="utf-8")
if mode == "control-plane-cache-deep-mutated":
    deep_file = root / ".claude" / "sub" / ".cache" / "file.txt"
    deep_file.write_text("after!\\n", encoding="utf-8")
if mode == "control-plane-cache-symlink-mutated":
    cache_link = root / ".claude" / ".cache"
    cache_link.unlink()
    # Point at another real, existing directory (not a dangling path): the
    # target must still satisfy ``is_dir()`` after the mutation so this only
    # passes if the code checks ``is_symlink()``, not just ``is_dir()``.
    cache_link.symlink_to(root.parent / "external-cache-after")
if mode == "control-plane-cache-file-mutated":
    (root / ".claude" / ".cache").write_text("after!\\n", encoding="utf-8")
if mode == "control-plane-cache-nearmiss-mutated":
    nearmiss_file = root / ".claude" / ".cache-extra" / "file.txt"
    nearmiss_file.write_text("after!\\n", encoding="utf-8")
if mode == "provenance-secret-mutated":
    (root / ".context-mode-provenance.secret").write_text(
        "after!\\n", encoding="utf-8"
    )
if mode == "nested-git-hook-mutated":
    hook = root / ".claude" / ".git" / "hooks" / "post-commit"
    hook.write_text("#!/bin/sh\\necho pwned\\n", encoding="utf-8")
if mode == "nested-git-config-mutated":
    config = root / ".claude" / ".git" / "config"
    with config.open("a", encoding="utf-8") as handle:
        handle.write("[core]\\n\\thooksPath = /tmp/evil\\n")
if mode == "nested-git-attributes-mutated":
    attributes = root / ".claude" / ".git" / "info" / "attributes"
    with attributes.open("a", encoding="utf-8") as handle:
        handle.write("*.bin filter=evil\\n")
if mode == "nested-git-submodule-config-mutated":
    submodule_config = root / ".claude" / ".git" / "modules" / "vendor" / "config"
    with submodule_config.open("a", encoding="utf-8") as handle:
        handle.write("[core]\\n\\thooksPath = /tmp/evil\\n")
if mode == "nested-git-submodule-nested-config-mutated":
    submodule_config = (
        root / ".claude" / ".git" / "modules" / "a" / "modules" / "b" / "config"
    )
    with submodule_config.open("a", encoding="utf-8") as handle:
        handle.write("[core]\\n\\thooksPath = /tmp/evil\\n")
if mode == "nested-git-worktree-config-mutated":
    worktree_config = root / ".claude" / ".git" / "config.worktree"
    with worktree_config.open("a", encoding="utf-8") as handle:
        handle.write("[core]\\n\\thooksPath = /tmp/evil\\n")
if mode == "decoy-git-payload":
    decoy = root / ".claude" / "subdir" / ".git"
    decoy.mkdir(parents=True, exist_ok=True)
    (decoy / "payload.sh").write_text("echo pwned\\n", encoding="utf-8")
if mode == "agents-decoy-git-payload":
    decoy = root / ".agents" / ".git"
    decoy.mkdir(parents=True, exist_ok=True)
    (decoy / "payload.sh").write_text("echo pwned\\n", encoding="utf-8")
if mode == "nested-git-non-allowlisted-mutated":
    description = root / ".claude" / ".git" / "description"
    description.write_text("mutated description\\n", encoding="utf-8")
if mode == "tracked-control-plane-mutated":
    tracked = root / ".github" / "CODEOWNERS"
    tracked.write_text("mutated\\n", encoding="utf-8")
if mode == "nested-git-maintenance":
    nested = root / ".claude"
    subprocess.run(
        [
            "git",
            "-C",
            str(nested),
            "-c",
            "user.name=OpenWiki Test",
            "-c",
            "user.email=openwiki-test@example.com",
            "commit",
            "--allow-empty",
            "-qm",
            "churn",
        ],
        check=True,
    )
    (nested / "tracked.txt").write_text("stash me\\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(nested), "stash", "-q"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(nested),
            "worktree",
            "add",
            "-q",
            "-b",
            "maintenance-worktree",
            os.environ["OPENWIKI_TEST_EXTERNAL_WORKTREE"],
        ],
        check=True,
    )
    subprocess.run(["git", "-C", str(nested), "gc", "-q"], check=True)
if mode == "symlink-escape":
    escape = root / "openwiki" / "escape.md"
    escape.symlink_to(Path("../CLAUDE.md"))
    escape.write_text("escaped write\\n", encoding="utf-8")
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
) -> tuple[subprocess.CompletedProcess[str], RunnerResult]:
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
    # The workflow file is now covered twice over (the dedicated
    # workflow_unchanged check and the disk-based control-plane walk of
    # .github); confirm the merge dedups instead of assuming it.
    assert (
        payload["out_of_scope_paths"].count(".github/workflows/openwiki-update.yml")
        == 1
    )


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
    assert (
        payload["out_of_scope_paths"].count(".github/workflows/openwiki-update.yml")
        == 1
    )


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
    assert payload["control_plane_paths"] == [".claude/generated-by-openwiki.txt"]


def test_changed_ignored_control_plane_path_is_reported(
    tmp_path: Path, fake_cli: Path
) -> None:
    root = _repository(tmp_path, ignored_control_plane=True)
    ignored = root / ".claude" / "existing.txt"
    ignored.parent.mkdir()
    ignored.write_text("before\n", encoding="utf-8")

    result, payload = _run(root, fake_cli, mode="ignored-existing")

    assert result.returncode != 0
    assert payload["control_plane_paths"] == [".claude/existing.txt"]
    assert ignored.read_text() == "after!\n"  # Same size as the pre-run bytes.


def test_control_plane_cache_mutation_does_not_cause_a_false_failure(
    tmp_path: Path, fake_cli: Path
) -> None:
    """.claude/.cache is disposable and churns during ordinary tool activity."""
    root = _repository(tmp_path, ignored_control_plane=True)
    cache_file = root / ".claude" / ".cache" / "stats.json"
    cache_file.parent.mkdir(parents=True)
    cache_file.write_text("before\n", encoding="utf-8")

    result, payload = _run(root, fake_cli, mode="control-plane-cache-mutated")

    assert result.returncode == 0, result.stderr
    assert payload["status"] == "success"
    assert payload["control_plane_paths"] == []
    assert cache_file.read_text() == "after!\n"


def test_control_plane_memory_mutation_outside_cache_is_still_detected(
    tmp_path: Path, fake_cli: Path
) -> None:
    """The .cache exclusion must not widen into the protected surface."""
    root = _repository(tmp_path, ignored_control_plane=True)
    memory = root / ".claude" / "MEMORY.md"
    memory.parent.mkdir(parents=True)
    memory.write_text("before\n", encoding="utf-8")

    result, payload = _run(root, fake_cli, mode="control-plane-memory-mutated")

    assert result.returncode != 0
    assert payload["control_plane_paths"] == [".claude/MEMORY.md"]
    assert memory.read_text() == "after!\n"


def _setup_deep_cache_not_immediate_child(root: Path, tmp_path: Path) -> None:
    """A .cache that is not an immediate child of the control-plane path."""
    deep = root / ".claude" / "sub" / ".cache"
    deep.mkdir(parents=True)
    (deep / "file.txt").write_text("before\n", encoding="utf-8")


def _setup_symlinked_cache(root: Path, tmp_path: Path) -> None:
    """A symlinked .cache in the immediate-child position, target a real dir.

    Both the before and after targets are real, existing directories, so
    ``is_dir()`` alone says yes to the symlink in both snapshots; only the
    accompanying ``is_symlink()`` check in the exclusion is what correctly
    keeps this from being exempted and lets the changed ``readlink()`` value
    be noticed.
    """
    (tmp_path / "external-cache-before").mkdir()
    (tmp_path / "external-cache-after").mkdir()
    cache_link = root / ".claude" / ".cache"
    cache_link.parent.mkdir(parents=True, exist_ok=True)
    cache_link.symlink_to(tmp_path / "external-cache-before")


def _setup_file_named_cache(root: Path, tmp_path: Path) -> None:
    """A regular file, not a directory, literally named .cache."""
    cache_file = root / ".claude" / ".cache"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("before\n", encoding="utf-8")


def _setup_near_miss_cache_name(root: Path, tmp_path: Path) -> None:
    """A directory name close to, but not exactly, .cache."""
    near_miss = root / ".claude" / ".cache-extra"
    near_miss.mkdir(parents=True)
    (near_miss / "file.txt").write_text("before\n", encoding="utf-8")


@pytest.mark.parametrize(
    ("setup", "mode", "expected_path"),
    (
        (
            _setup_deep_cache_not_immediate_child,
            "control-plane-cache-deep-mutated",
            ".claude/sub/.cache/file.txt",
        ),
        (
            _setup_symlinked_cache,
            "control-plane-cache-symlink-mutated",
            ".claude/.cache",
        ),
        (
            _setup_file_named_cache,
            "control-plane-cache-file-mutated",
            ".claude/.cache",
        ),
        (
            _setup_near_miss_cache_name,
            "control-plane-cache-nearmiss-mutated",
            ".claude/.cache-extra/file.txt",
        ),
    ),
    ids=(
        "deep-cache-not-immediate-child",
        "symlinked-cache-falls-through",
        "file-literally-named-cache",
        "near-miss-directory-name",
    ),
)
def test_cache_exclusion_boundary_cases_are_still_fingerprinted(
    tmp_path: Path,
    fake_cli: Path,
    setup: Callable[[Path, Path], None],
    mode: str,
    expected_path: str,
) -> None:
    """The .cache exclusion is narrow; pin every boundary so it cannot widen silently.

    Each case here is a way the exclusion could be loosened by a future edit
    (dropping the depth check, matching by substring, or trusting
    ``is_dir()`` without also checking ``is_symlink()``) without any existing
    test noticing. Some of these already pass against the current code --
    their job is to catch a future regression, not a present bug.
    """
    root = _repository(tmp_path, ignored_control_plane=True)
    setup(root, tmp_path)

    result, payload = _run(root, fake_cli, mode=mode)

    assert result.returncode != 0
    assert expected_path in payload["control_plane_paths"]


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
        raise AssertionError("sentinel identity must come from an open descriptor")

    monkeypatch.setattr(Path, "stat", unexpected_stat)
    snapshot = RUNNER_MODULE._prepare_adapter(root, Path("AGENTS.md"))

    assert snapshot.contents is None
    assert snapshot.sentinel_fd is not None
    os.close(snapshot.sentinel_fd)


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


def test_present_adapter_replaced_with_different_inode_is_not_deleted(
    tmp_path: Path, fake_cli: Path
) -> None:
    """A present-pre-run adapter swapped for a new inode mid-run must fail closed."""
    root = _repository(tmp_path)
    (root / "AGENTS.md").write_bytes(b"local agents\n")
    (root / "CLAUDE.md").write_bytes(b"local claude\n")
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


def test_in_place_concurrent_edit_is_restored_and_evidenced(
    tmp_path: Path, fake_cli: Path
) -> None:
    """A same-inode concurrent edit is restored in place and its loss is evidenced."""
    root = _repository(tmp_path)
    agents = root / "AGENTS.md"
    agents.write_bytes(b"local agents\n")
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
    before_inode = agents.stat().st_ino
    agents.write_bytes(b"concurrent edit\n")  # Same inode: a write, not a replace.
    release.touch()
    stdout, stderr = process.communicate(timeout=5)
    payload = json.loads(stdout)

    assert process.returncode == 0, stderr
    assert payload["status"] == "success"
    assert agents.read_bytes() == b"local agents\n"
    assert agents.stat().st_ino == before_inode
    assert payload["restoration_displaced_content"] == [
        {
            "path": "AGENTS.md",
            "sha256": hashlib.sha256(b"concurrent edit\n").hexdigest(),
            "length": len(b"concurrent edit\n"),
        }
    ]


def test_restore_leaves_matching_content_untouched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No write happens at all when the current bytes already match the snapshot."""
    root = _repository(tmp_path)
    agents = root / "AGENTS.md"
    agents.write_bytes(b"steady state\n")
    snapshot = RUNNER_MODULE._prepare_adapter(root, Path("AGENTS.md"))
    before_ino = agents.stat().st_ino

    def fail_if_called(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("must not write when content is unchanged")

    monkeypatch.setattr(RUNNER_MODULE.os, "ftruncate", fail_if_called)
    monkeypatch.setattr(RUNNER_MODULE.os, "write", fail_if_called)

    result = RUNNER_MODULE._restore(root, Path("AGENTS.md"), snapshot)

    assert result is None
    assert agents.read_bytes() == b"steady state\n"
    assert agents.stat().st_ino == before_ino


def test_symlink_created_during_run_escapes_openwiki_boundary(
    tmp_path: Path, fake_cli: Path
) -> None:
    """A symlink created after the pre-launch check still fails the run closed."""
    root = _repository(tmp_path)
    claude = root / "CLAUDE.md"
    claude.write_bytes(b"original claude content\n")

    result, payload = _run(root, fake_cli, mode="symlink-escape")

    assert result.returncode != 0
    assert "openwiki/escape.md" in payload["out_of_scope_paths"]
    assert claude.read_bytes() == b"original claude content\n"


def test_ignored_nested_git_repository_mutation_is_detected(
    tmp_path: Path, fake_cli: Path
) -> None:
    """A nested repo under an ignored control-plane path must not collapse to one entry."""
    root = _repository(tmp_path, ignored_control_plane=True)
    nested = root / ".claude"
    nested.mkdir()
    assert _git(nested, "init", "-q").returncode == 0
    existing = nested / "existing.txt"
    existing.write_text("before\n", encoding="utf-8")

    result, payload = _run(root, fake_cli, mode="ignored-existing")

    assert result.returncode != 0
    assert payload["control_plane_paths"] == [".claude/existing.txt"]
    assert existing.read_text() == "after!\n"


def test_nested_git_hook_mutation_is_detected(tmp_path: Path, fake_cli: Path) -> None:
    """A planted hook inside a nested repository's own .git is an execution vector."""
    root = _repository(tmp_path, ignored_control_plane=True)
    nested = root / ".claude"
    nested.mkdir()
    assert _git(nested, "init", "-q").returncode == 0
    hook = nested / ".git" / "hooks" / "post-commit"
    hook.write_text("#!/bin/sh\necho before\n", encoding="utf-8")

    result, payload = _run(root, fake_cli, mode="nested-git-hook-mutated")

    assert result.returncode != 0
    assert payload["control_plane_paths"] == [".claude/.git/hooks/post-commit"]
    assert hook.read_text() == "#!/bin/sh\necho pwned\n"


def test_nested_git_config_mutation_is_detected(tmp_path: Path, fake_cli: Path) -> None:
    """core.hooksPath/fsmonitor/include.path in a nested .git/config can run code."""
    root = _repository(tmp_path, ignored_control_plane=True)
    nested = root / ".claude"
    nested.mkdir()
    assert _git(nested, "init", "-q").returncode == 0
    config = nested / ".git" / "config"
    before = config.read_text(encoding="utf-8")

    result, payload = _run(root, fake_cli, mode="nested-git-config-mutated")

    assert result.returncode != 0
    assert payload["control_plane_paths"] == [".claude/.git/config"]
    assert config.read_text(encoding="utf-8") != before


def test_nested_git_attributes_mutation_is_detected(
    tmp_path: Path, fake_cli: Path
) -> None:
    """info/attributes binds paths to filter/textconv handlers sourced from config."""
    root = _repository(tmp_path, ignored_control_plane=True)
    nested = root / ".claude"
    nested.mkdir()
    assert _git(nested, "init", "-q").returncode == 0
    attributes = nested / ".git" / "info" / "attributes"
    attributes.write_text("*.txt text\n", encoding="utf-8")

    result, payload = _run(root, fake_cli, mode="nested-git-attributes-mutated")

    assert result.returncode != 0
    assert payload["control_plane_paths"] == [".claude/.git/info/attributes"]


def test_nested_git_submodule_config_mutation_is_detected(
    tmp_path: Path, fake_cli: Path
) -> None:
    """A submodule's git directory under .git/modules/*/ carries its own config."""
    root = _repository(tmp_path, ignored_control_plane=True)
    nested = root / ".claude"
    nested.mkdir()
    assert _git(nested, "init", "-q").returncode == 0
    submodule_git_dir = nested / ".git" / "modules" / "vendor"
    submodule_git_dir.mkdir(parents=True)
    submodule_config = submodule_git_dir / "config"
    submodule_config.write_text(
        "[core]\n\trepositoryformatversion = 0\n", encoding="utf-8"
    )

    result, payload = _run(root, fake_cli, mode="nested-git-submodule-config-mutated")

    assert result.returncode != 0
    assert payload["control_plane_paths"] == [".claude/.git/modules/vendor/config"]


def test_nested_git_doubly_nested_submodule_config_mutation_is_detected(
    tmp_path: Path, fake_cli: Path
) -> None:
    """modules/<a>/modules/<b>/config: nested submodules are ordinary, not adversarial."""
    root = _repository(tmp_path, ignored_control_plane=True)
    nested = root / ".claude"
    nested.mkdir()
    assert _git(nested, "init", "-q").returncode == 0
    submodule_git_dir = nested / ".git" / "modules" / "a" / "modules" / "b"
    submodule_git_dir.mkdir(parents=True)
    submodule_config = submodule_git_dir / "config"
    submodule_config.write_text(
        "[core]\n\trepositoryformatversion = 0\n", encoding="utf-8"
    )

    result, payload = _run(
        root, fake_cli, mode="nested-git-submodule-nested-config-mutated"
    )

    assert result.returncode != 0
    assert payload["control_plane_paths"] == [".claude/.git/modules/a/modules/b/config"]


def test_nested_git_worktree_config_mutation_is_detected(
    tmp_path: Path, fake_cli: Path
) -> None:
    """config.worktree carries config-equivalent settings once worktreeConfig is on."""
    root = _repository(tmp_path, ignored_control_plane=True)
    nested = root / ".claude"
    nested.mkdir()
    assert _git(nested, "init", "-q").returncode == 0
    worktree_config = nested / ".git" / "config.worktree"
    worktree_config.write_text("[core]\n\tbare = false\n", encoding="utf-8")

    result, payload = _run(root, fake_cli, mode="nested-git-worktree-config-mutated")

    assert result.returncode != 0
    assert payload["control_plane_paths"] == [".claude/.git/config.worktree"]


def test_decoy_git_directory_payload_is_detected(
    tmp_path: Path, fake_cli: Path
) -> None:
    """A directory merely named .git is not trusted without HEAD/objects/refs."""
    root = _repository(tmp_path, ignored_control_plane=True)
    nested = root / ".claude"
    nested.mkdir()
    assert _git(nested, "init", "-q").returncode == 0

    result, payload = _run(root, fake_cli, mode="decoy-git-payload")

    assert result.returncode != 0
    assert payload["control_plane_paths"] == [".claude/subdir/.git/payload.sh"]


def test_agents_decoy_git_directory_payload_is_detected(
    tmp_path: Path, fake_cli: Path
) -> None:
    """A decoy .git works even where the control-plane path is not itself a repo.

    ``.agents`` is ordinarily just an ignored directory, not a nested Git
    repository. Before enumeration moved to a direct filesystem walk,
    ``git ls-files --others --ignored`` silently omitted anything inside
    *any* directory literally named ``.git`` for *any* path, so a payload
    placed here was reachable by nothing in this module at all -- not even
    the validated-``.git`` check, since it was never invoked.
    """
    root = _repository(tmp_path)
    gitignore = root / ".gitignore"
    gitignore.write_text(
        gitignore.read_text(encoding="utf-8") + ".agents/\n", encoding="utf-8"
    )

    result, payload = _run(root, fake_cli, mode="agents-decoy-git-payload")

    assert result.returncode != 0
    assert payload["control_plane_paths"] == [".agents/.git/payload.sh"]


def test_tracked_control_plane_file_mutation_is_detected(
    tmp_path: Path, fake_cli: Path
) -> None:
    """Enumerating from disk also reaches tracked control-plane files."""
    root = _repository(tmp_path)
    tracked = root / ".github" / "CODEOWNERS"
    tracked.parent.mkdir(parents=True, exist_ok=True)
    tracked.write_text("base\n", encoding="utf-8")
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
            "add codeowners",
        ).returncode
        == 0
    )

    result, payload = _run(root, fake_cli, mode="tracked-control-plane-mutated")

    assert result.returncode != 0
    assert ".github/CODEOWNERS" in payload["control_plane_paths"]
    assert payload["out_of_scope_paths"].count(".github/CODEOWNERS") == 1


def test_pre_existing_tracked_control_plane_edit_is_not_a_false_failure(
    tmp_path: Path, fake_cli: Path
) -> None:
    """A tracked control-plane file already dirty, and untouched by OpenWiki,
    must not fail the refresh now that tracked files are enumerated too."""
    root = _repository(tmp_path)
    tracked = root / ".github" / "CODEOWNERS"
    tracked.parent.mkdir(parents=True, exist_ok=True)
    tracked.write_text("base\n", encoding="utf-8")
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
            "add codeowners",
        ).returncode
        == 0
    )
    tracked.write_text("locally edited before the run\n", encoding="utf-8")

    result, payload = _run(root, fake_cli, mode="success")

    assert result.returncode == 0, result.stderr
    assert payload["status"] == "success"
    assert payload["control_plane_paths"] == []
    assert tracked.read_text() == "locally edited before the run\n"


def test_nested_git_non_allowlisted_path_is_accepted_by_design(
    tmp_path: Path, fake_cli: Path
) -> None:
    """A validated Git directory still hides content outside the allowlist.

    This pins a deliberate, documented trade (see the module docstring), not
    an oversight: every code-execution vector Git defines is on the
    allowlist, so what remains hideable here -- a mutated ``description``
    file -- is inert data.
    """
    root = _repository(tmp_path, ignored_control_plane=True)
    nested = root / ".claude"
    nested.mkdir()
    assert _git(nested, "init", "-q").returncode == 0
    assert (nested / ".git" / "description").exists()

    result, payload = _run(root, fake_cli, mode="nested-git-non-allowlisted-mutated")

    assert result.returncode == 0, result.stderr
    assert payload["status"] == "success"
    assert payload["control_plane_paths"] == []


def test_nested_repository_maintenance_does_not_cause_false_failure(
    tmp_path: Path, fake_cli: Path
) -> None:
    """Ordinary commit, stash, worktree add, and git gc must not fail the refresh."""
    root = _repository(tmp_path, ignored_control_plane=True)
    nested = root / ".claude"
    nested.mkdir()
    assert _git(nested, "init", "-q").returncode == 0
    (nested / "tracked.txt").write_text("base\n", encoding="utf-8")
    assert _git(nested, "add", ".").returncode == 0
    assert (
        _git(
            nested,
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
    external_worktree = tmp_path / "external-worktree"

    result, payload = _run(
        root,
        fake_cli,
        mode="nested-git-maintenance",
        OPENWIKI_TEST_EXTERNAL_WORKTREE=str(external_worktree),
    )

    assert result.returncode == 0, result.stderr
    assert payload["status"] == "success"
    assert payload["control_plane_paths"] == []
    assert external_worktree.exists()


def test_ignored_provenance_secret_mutation_is_detected(
    tmp_path: Path, fake_cli: Path
) -> None:
    root = _repository(tmp_path)
    gitignore = root / ".gitignore"
    gitignore.write_text(
        gitignore.read_text(encoding="utf-8") + ".context-mode-provenance.secret*\n",
        encoding="utf-8",
    )
    secret = root / ".context-mode-provenance.secret"
    secret.write_text("before\n", encoding="utf-8")

    result, payload = _run(root, fake_cli, mode="provenance-secret-mutated")

    assert result.returncode != 0
    assert payload["control_plane_paths"] == [".context-mode-provenance.secret"]
    assert secret.read_text() == "after!\n"


def test_combined_comparison_and_restoration_failure_reports_both(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A post-child comparison failure must not hide a restoration failure."""
    root = _repository(tmp_path)
    monkeypatch.setattr(RUNNER_MODULE, "_version", lambda _command, **_kw: "0.5.2")

    real_run = RUNNER_MODULE.subprocess.run
    status_calls = {"count": 0}

    def patched_run(
        command: list[str], *args: object, **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        if command[:1] == ["openwiki"]:
            return subprocess.CompletedProcess(command, 0)
        if command[:2] == ["git", "-C"] and "status" in command:
            status_calls["count"] += 1
            if status_calls["count"] > 1:
                return subprocess.CompletedProcess(command, 1, stdout="", stderr="boom")
        return real_run(command, *args, **kwargs)

    monkeypatch.setattr(RUNNER_MODULE.subprocess, "run", patched_run)

    def failing_restore(_root: Path, relative_path: Path, original: Any) -> None:
        if original.sentinel_fd is not None:
            os.close(original.sentinel_fd)
        raise RuntimeError(
            f"protected path changed outside this refresh: {relative_path}"
        )

    monkeypatch.setattr(RUNNER_MODULE, "_restore", failing_restore)

    returncode, payload = RUNNER_MODULE._run(root)

    assert returncode != 0
    assert payload["status"] == "failed"
    assert payload["error"] == "could not read Git working-tree status"
    assert payload["restoration_errors"] == [
        "AGENTS.md: protected path changed outside this refresh: AGENTS.md",
        "CLAUDE.md: protected path changed outside this refresh: CLAUDE.md",
    ]
