"""Focused tests for the Context Mode hook/server launcher and cache boundary."""

from __future__ import annotations

import json
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


def _fake_context_mode(
    tmp_path: Path,
    *,
    version: str | None = "1.0.169",
    manifest_name: str = "context-mode",
) -> tuple[Path, Path]:
    """A fake `context-mode` mirroring the real npm install layout.

    The dispatcher reads the owning package.json to prove the pinned version,
    because Context Mode 1.0.169 has no working `--version` flag. So the fake
    must be a bin symlink pointing into a package directory, exactly like a real
    global install. `version=None` omits the manifest entirely, modelling a
    binary whose version cannot be determined.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    package_dir = tmp_path / "pkg"
    package_dir.mkdir(exist_ok=True)
    trace = tmp_path / "trace"
    script = package_dir / "cli.bundle.mjs"
    script.write_text(
        "#!/usr/bin/env bash\n"
        'printf \'%s|%s\\n\' "$CONTEXT_MODE_DIR" "$*" >> "$CONTEXT_MODE_TRACE"\n'
    )
    script.chmod(0o755)
    if version is not None:
        (package_dir / "package.json").write_text(
            json.dumps({"name": manifest_name, "version": version}, indent=2)
        )
    executable = bin_dir / "context-mode"
    if executable.is_symlink() or executable.exists():
        executable.unlink()
    executable.symlink_to(script)
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


def test_approved_cache_subtree_override_is_preserved(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    root, dispatcher = installed_dispatcher
    env, trace = _hook_env(tmp_path)
    approved = root / ".claude/.cache/context-mode/alternate"
    env["CONTEXT_MODE_DIR"] = str(approved)
    assert _run(dispatcher, "claude-code", "sessionstart", env=env).returncode == 0
    assert trace.read_text().split("|", 1)[0] == str(approved.resolve())


def test_external_override_falls_back_and_never_touches_that_path(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    """An absolute external CONTEXT_MODE_DIR is refused, not adopted.

    configure_storage quarantines an unaudited cache by renaming the directory,
    so adopting an arbitrary external path would let the bootstrap reorganize
    user-owned state outside the repository. The external path must be left
    exactly as it was: not created, not stamped with a provenance marker, and
    not renamed to a `.untrusted.*` sibling.
    """
    root, dispatcher = installed_dispatcher
    env, trace = _hook_env(tmp_path)
    external = tmp_path / "user-owned-cache"
    external.mkdir()
    (external / "user-data.txt").write_text("owned by the user")
    env["CONTEXT_MODE_DIR"] = str(external)

    result = _run(dispatcher, "claude-code", "sessionstart", env=env)

    assert result.returncode == 0
    assert "unsupported CONTEXT_MODE_DIR" in result.stderr
    # Fell back to the project-local cache.
    assert trace.read_text().split("|", 1)[0] == str(
        (root / ".claude/.cache/context-mode").resolve()
    )
    # The external directory is untouched: same contents, no marker, no rename.
    assert (external / "user-data.txt").read_text() == "owned by the user"
    assert not (external / ".bootstrap-provenance").exists()
    assert sorted(p.name for p in external.iterdir()) == ["user-data.txt"]
    assert not list(tmp_path.glob("user-owned-cache.untrusted.*"))


def test_external_override_is_not_created_when_absent(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    """Refusing an external override must not bring it into existence."""
    _, dispatcher = installed_dispatcher
    env, _ = _hook_env(tmp_path)
    external = tmp_path / "never-created"
    env["CONTEXT_MODE_DIR"] = str(external)

    assert _run(dispatcher, "claude-code", "sessionstart", env=env).returncode == 0
    assert not external.exists()


def test_hook_uses_direct_binary_only_at_the_exact_pinned_version(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    _, dispatcher = installed_dispatcher
    bin_dir, trace = _fake_context_mode(tmp_path, version="1.0.169")
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "CONTEXT_MODE_TRACE": str(trace)}

    result = _run(dispatcher, "claude-code", "sessionstart", env=env)

    assert result.returncode == 0, result.stderr
    assert "hook claude-code sessionstart" in trace.read_text()


@pytest.mark.parametrize(
    ("version", "manifest_name"),
    [
        ("1.0.170", "context-mode"),
        ("1.0.168", "context-mode"),
        ("0.9.0", "context-mode"),
        # A nested dependency's manifest must never be mistaken for Context
        # Mode's own, even when its version happens to be the pinned string.
        ("1.0.169", "some-other-package"),
    ],
)
def test_hook_refuses_a_direct_binary_that_is_not_the_pinned_version(
    installed_dispatcher: tuple[Path, Path],
    tmp_path: Path,
    version: str,
    manifest_name: str,
) -> None:
    """A mismatched direct binary must never be executed, and hooks must still
    fail open (exit 0) rather than breaking the session."""
    _, dispatcher = installed_dispatcher
    bin_dir, trace = _fake_context_mode(
        tmp_path, version=version, manifest_name=manifest_name
    )
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "CONTEXT_MODE_TRACE": str(trace)}

    result = _run(dispatcher, "claude-code", "sessionstart", env=env)

    assert result.returncode == 0
    assert "requires exactly 1.0.169" in result.stderr
    assert not trace.exists(), "a non-pinned context-mode binary was executed"


def test_hook_refuses_a_direct_binary_with_an_undeterminable_version(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    """No manifest means the version cannot be proven, so the binary must be
    skipped rather than trusted."""
    _, dispatcher = installed_dispatcher
    bin_dir, trace = _fake_context_mode(tmp_path, version=None)
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "CONTEXT_MODE_TRACE": str(trace)}

    result = _run(dispatcher, "claude-code", "sessionstart", env=env)

    assert result.returncode == 0
    assert "undeterminable" in result.stderr
    assert not trace.exists()


def test_hook_falls_back_to_pinned_npx_when_direct_binary_is_rejected(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    """A rejected direct binary must not disable Context Mode: the pinned npx
    fallback is correct by construction and must still be used."""
    _, dispatcher = installed_dispatcher
    bin_dir, trace = _fake_context_mode(tmp_path, version="1.0.170")
    npx_dir = tmp_path / "npx-bin"
    npx_dir.mkdir()
    npx_trace = tmp_path / "npx-trace"
    npx = npx_dir / "npx"
    npx.write_text('#!/usr/bin/env bash\nprintf \'%s\\n\' "$*" >> "$NPX_TRACE"\n')
    npx.chmod(0o755)
    env = {
        "PATH": f"{bin_dir}:{npx_dir}:/usr/bin:/bin",
        "CONTEXT_MODE_TRACE": str(trace),
        "NPX_TRACE": str(npx_trace),
    }

    result = _run(dispatcher, "claude-code", "sessionstart", env=env)

    assert result.returncode == 0, result.stderr
    assert not trace.exists(), "the rejected direct binary was executed"
    assert (
        npx_trace.read_text().strip()
        == "-y context-mode@1.0.169 hook claude-code sessionstart"
    )


def test_self_check_reports_the_observed_version_and_contract_result(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    """--self-check must prove the version contract, not merely restate the pin."""
    _, dispatcher = installed_dispatcher
    bin_dir, _ = _fake_context_mode(tmp_path, version="1.0.169")

    ok = _run(dispatcher, "--self-check", env={"PATH": f"{bin_dir}:/usr/bin:/bin"})

    assert ok.returncode == 0
    assert "required-version=1.0.169" in ok.stdout
    assert f"resolved-path={bin_dir / 'context-mode'}" in ok.stdout
    assert "observed-version=1.0.169" in ok.stdout
    assert "version-contract=pinned-direct-binary" in ok.stdout


def test_self_check_reports_a_failing_version_contract(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    _, dispatcher = installed_dispatcher
    bin_dir, _ = _fake_context_mode(tmp_path, version="1.0.170")

    bad = _run(dispatcher, "--self-check", env={"PATH": f"{bin_dir}:/usr/bin:/bin"})

    assert bad.returncode == 0
    assert "observed-version=1.0.170" in bad.stdout
    assert "version-contract=pinned-direct-binary" not in bad.stdout
    assert "version-contract=FAIL" in bad.stderr


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
