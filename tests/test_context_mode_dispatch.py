"""Focused tests for the Context Mode hook/server launcher and cache boundary."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_SRC = REPO_ROOT / "shared/hooks/scripts/context-mode-dispatch.sh"
FILTER_SRC = REPO_ROOT / "shared/hooks/scripts/context-mode-mcp-filter.mjs"


@pytest.fixture
def installed_dispatcher(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "repo"
    scripts = root / ".claude/hooks/scripts"
    scripts.mkdir(parents=True)
    dispatcher = scripts / "context-mode-dispatch.sh"
    shutil.copy(SCRIPT_SRC, dispatcher)
    # generate_targets.py copies the whole hooks/scripts/ directory, so the
    # filter always ships next to the dispatcher; mirror that here for the
    # `server` mode tests below.
    shutil.copy(FILTER_SRC, scripts / "context-mode-mcp-filter.mjs")
    return root, dispatcher


def _fake_context_mode(tmp_path: Path) -> tuple[Path, Path]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    trace = tmp_path / "trace"
    executable = bin_dir / "context-mode"
    executable.write_text(
        "#!/usr/bin/env bash\n"
        'printf \'%s|%s\\n\' "$CONTEXT_MODE_DIR" "$*" >> "$CONTEXT_MODE_TRACE"\n'
    )
    executable.chmod(0o755)
    return bin_dir, trace


def _fake_node(tmp_path: Path) -> tuple[Path, Path]:
    """A fake `node` that records its argv and the cache/root env vars it
    was launched with, instead of actually starting the MCP filter."""
    bin_dir = tmp_path / "node-bin"
    bin_dir.mkdir(exist_ok=True)
    trace = tmp_path / "node-trace"
    executable = bin_dir / "node"
    executable.write_text(
        "#!/usr/bin/env bash\n"
        'printf \'%s|%s|%s\\n\' "$CONTEXT_MODE_DIR" "$CONTEXT_MODE_PROJECT_ROOT" "$*" >> "$NODE_TRACE"\n'
    )
    executable.chmod(0o755)
    return bin_dir, trace


def _run(
    dispatcher: Path, *args: str, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(dispatcher), *args],
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, **env},
    )


def _hook_env(tmp_path: Path) -> tuple[dict[str, str], Path]:
    bin_dir, trace = _fake_context_mode(tmp_path)
    return {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "CONTEXT_MODE_TRACE": str(trace),
    }, trace


def test_hook_uses_project_local_storage_and_upstream_target_mapping(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    root, dispatcher = installed_dispatcher
    env, trace = _hook_env(tmp_path)
    assert _run(dispatcher, "github-copilot", "pretooluse", env=env).returncode == 0
    assert _run(dispatcher, "openai-codex", "sessionstart", env=env).returncode == 0
    expected = str((root / ".claude/.cache/context-mode").resolve())
    assert trace.read_text().splitlines() == [
        f"{expected}|hook vscode-copilot pretooluse",
        f"{expected}|hook codex sessionstart",
    ]


def test_missing_optional_tool_fails_open_for_hook(
    installed_dispatcher: tuple[Path, Path],
) -> None:
    _, dispatcher = installed_dispatcher
    result = _run(
        dispatcher, "claude-code", "posttooluse", env={"PATH": "/usr/bin:/bin"}
    )
    assert result.returncode == 0
    assert "skipping optional hook event" in result.stderr


@pytest.mark.parametrize("relative", ["relative-cache", "../escape"])
def test_relative_and_traversal_overrides_fall_back(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path, relative: str
) -> None:
    root, dispatcher = installed_dispatcher
    env, trace = _hook_env(tmp_path)
    env["CONTEXT_MODE_DIR"] = relative
    result = _run(dispatcher, "claude-code", "sessionstart", env=env)
    assert result.returncode == 0
    assert trace.read_text().split("|", 1)[0] == str(
        (root / ".claude/.cache/context-mode").resolve()
    )
    assert "using project-local cache" in result.stderr


@pytest.mark.parametrize("relative", [".claude/plans/cache", ".git/cache"])
def test_tracked_and_protected_in_repo_overrides_fall_back(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path, relative: str
) -> None:
    root, dispatcher = installed_dispatcher
    (root / ".git").mkdir()
    (root / ".claude/plans").mkdir(parents=True, exist_ok=True)
    env, trace = _hook_env(tmp_path)
    requested = root / relative
    env["CONTEXT_MODE_DIR"] = str(requested)
    result = _run(dispatcher, "claude-code", "sessionstart", env=env)
    assert result.returncode == 0
    assert trace.read_text().split("|", 1)[0] == str(
        (root / ".claude/.cache/context-mode").resolve()
    )
    assert not requested.exists()


def test_symlink_into_protected_path_falls_back(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    root, dispatcher = installed_dispatcher
    plans = root / ".claude/plans"
    plans.mkdir(parents=True)
    link = root / ".claude/.cache/link"
    link.parent.mkdir(parents=True)
    link.symlink_to(plans, target_is_directory=True)
    env, trace = _hook_env(tmp_path)
    env["CONTEXT_MODE_DIR"] = str(link / "context-mode")
    result = _run(dispatcher, "claude-code", "sessionstart", env=env)
    assert result.returncode == 0
    assert trace.read_text().split("|", 1)[0] == str(
        (root / ".claude/.cache/context-mode").resolve()
    )
    assert not (plans / "context-mode").exists()


def test_in_repo_symlink_escape_falls_back(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    root, dispatcher = installed_dispatcher
    external = tmp_path / "external"
    external.mkdir()
    link = root / ".claude/.cache/context-mode-link"
    link.parent.mkdir(parents=True)
    link.symlink_to(external, target_is_directory=True)
    env, trace = _hook_env(tmp_path)
    env["CONTEXT_MODE_DIR"] = str(link / "context-mode")
    result = _run(dispatcher, "claude-code", "sessionstart", env=env)
    assert result.returncode == 0
    assert trace.read_text().split("|", 1)[0] == str(
        (root / ".claude/.cache/context-mode").resolve()
    )
    assert not (external / "context-mode").exists()


def test_absolute_traversal_override_falls_back_without_creating_destination(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    root, dispatcher = installed_dispatcher
    (root / ".claude/plans").mkdir(parents=True)
    requested = f"{root}/.claude/.cache/context-mode/../../../plans/escaped"
    env, trace = _hook_env(tmp_path)
    env["CONTEXT_MODE_DIR"] = requested
    result = _run(dispatcher, "claude-code", "sessionstart", env=env)
    assert result.returncode == 0
    assert trace.read_text().split("|", 1)[0] == str(
        (root / ".claude/.cache/context-mode").resolve()
    )
    assert not (root / ".claude/plans/escaped").exists()


def test_approved_cache_subtree_and_external_absolute_override_are_preserved(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    root, dispatcher = installed_dispatcher
    env, trace = _hook_env(tmp_path)
    approved = root / ".claude/.cache/context-mode/alternate"
    env["CONTEXT_MODE_DIR"] = str(approved)
    assert _run(dispatcher, "claude-code", "sessionstart", env=env).returncode == 0
    external = tmp_path / "external-cache"
    env["CONTEXT_MODE_DIR"] = str(external)
    assert _run(dispatcher, "claude-code", "sessionstart", env=env).returncode == 0
    assert [line.split("|", 1)[0] for line in trace.read_text().splitlines()] == [
        str(approved.resolve()),
        str(external.resolve()),
    ]


def test_self_check_is_nondestructive_for_fresh_and_existing_storage(
    installed_dispatcher: tuple[Path, Path],
) -> None:
    root, dispatcher = installed_dispatcher
    cache_root = root / ".claude/.cache/context-mode"
    fresh = _run(dispatcher, "--self-check", env={"PATH": "/usr/bin:/bin"})
    assert fresh.returncode == 0
    assert f"storage-root={cache_root.resolve()}" in fresh.stdout
    assert "storage=creatable" in fresh.stdout
    assert not cache_root.exists()
    cache_root.mkdir(parents=True)
    existing = _run(dispatcher, "--self-check", env={"PATH": "/usr/bin:/bin"})
    assert existing.returncode == 0
    assert "storage=writable" in existing.stdout
    assert cache_root.is_dir()


def test_server_mode_execs_pinned_direct_binary_through_filter(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    """`server` mode must `exec` node on the filter, forwarding to the
    resolved `context-mode` binary -- not to some other command or with
    reordered/misquoted args."""
    root, dispatcher = installed_dispatcher
    context_mode_bin, _ = _fake_context_mode(tmp_path)
    node_bin, node_trace = _fake_node(tmp_path)
    env = {
        "PATH": f"{context_mode_bin}:{node_bin}:/usr/bin:/bin",
        "NODE_TRACE": str(node_trace),
    }

    result = _run(dispatcher, "server", env=env)

    assert result.returncode == 0, result.stderr
    filter_script = root / ".claude/hooks/scripts/context-mode-mcp-filter.mjs"
    cache_root, project_root, argv = node_trace.read_text().strip().split("|", 2)
    assert cache_root == str((root / ".claude/.cache/context-mode").resolve())
    assert project_root == str(root.resolve())
    assert argv == f"{filter_script} -- context-mode"


def test_server_mode_execs_pinned_npx_fallback_through_filter(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    """When `context-mode` is not on PATH, `server` mode must fall back to
    `npx` pinned to the exact same version the hooks use."""
    root, dispatcher = installed_dispatcher
    npx_bin_dir = tmp_path / "npx-bin"
    npx_bin_dir.mkdir()
    npx = npx_bin_dir / "npx"
    npx.write_text("#!/usr/bin/env bash\nexit 0\n")
    npx.chmod(0o755)
    node_bin, node_trace = _fake_node(tmp_path)
    env = {
        "PATH": f"{npx_bin_dir}:{node_bin}:/usr/bin:/bin",
        "NODE_TRACE": str(node_trace),
    }

    result = _run(dispatcher, "server", env=env)

    assert result.returncode == 0, result.stderr
    filter_script = root / ".claude/hooks/scripts/context-mode-mcp-filter.mjs"
    _, _, argv = node_trace.read_text().strip().split("|", 2)
    assert argv == f"{filter_script} -- npx -y context-mode@1.0.169"


def test_hook_and_server_modes_share_identical_cache_and_project_root(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    """Hooks and the MCP server must resolve the exact same guarded cache
    root and repository identity from one environment."""
    root, dispatcher = installed_dispatcher
    context_mode_bin, hook_trace = _fake_context_mode(tmp_path)
    node_bin, node_trace = _fake_node(tmp_path)
    env = {
        "PATH": f"{context_mode_bin}:{node_bin}:/usr/bin:/bin",
        "CONTEXT_MODE_TRACE": str(hook_trace),
        "NODE_TRACE": str(node_trace),
    }

    assert _run(dispatcher, "claude-code", "sessionstart", env=env).returncode == 0
    assert _run(dispatcher, "server", env=env).returncode == 0

    hook_cache_root = hook_trace.read_text().split("|", 1)[0]
    server_cache_root, server_project_root, _ = (
        node_trace.read_text().strip().split("|", 2)
    )
    expected_cache_root = str((root / ".claude/.cache/context-mode").resolve())
    assert hook_cache_root == expected_cache_root
    assert server_cache_root == expected_cache_root
    assert server_project_root == str(root.resolve())


def test_server_mode_fails_clearly_when_node_missing_but_hook_mode_stays_open(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    root, dispatcher = installed_dispatcher
    context_mode_bin, hook_trace = _fake_context_mode(tmp_path)
    env = {
        "PATH": f"{context_mode_bin}:/usr/bin:/bin",
        "CONTEXT_MODE_TRACE": str(hook_trace),
    }

    server_result = _run(dispatcher, "server", env=env)
    assert server_result.returncode != 0
    assert "unavailable" in server_result.stderr

    hook_result = _run(dispatcher, "claude-code", "sessionstart", env=env)
    assert hook_result.returncode == 0
    assert hook_trace.read_text().split("|", 1)[0] == str(
        (root / ".claude/.cache/context-mode").resolve()
    )


def test_server_mode_fails_clearly_when_filter_script_missing_but_hook_mode_stays_open(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    root, dispatcher = installed_dispatcher
    (root / ".claude/hooks/scripts/context-mode-mcp-filter.mjs").unlink()
    context_mode_bin, hook_trace = _fake_context_mode(tmp_path)
    node_bin, node_trace = _fake_node(tmp_path)
    env = {
        "PATH": f"{context_mode_bin}:{node_bin}:/usr/bin:/bin",
        "CONTEXT_MODE_TRACE": str(hook_trace),
        "NODE_TRACE": str(node_trace),
    }

    server_result = _run(dispatcher, "server", env=env)
    assert server_result.returncode != 0
    assert "unavailable" in server_result.stderr
    assert not node_trace.exists()

    hook_result = _run(dispatcher, "claude-code", "sessionstart", env=env)
    assert hook_result.returncode == 0
    assert hook_trace.read_text().split("|", 1)[0] == str(
        (root / ".claude/.cache/context-mode").resolve()
    )
