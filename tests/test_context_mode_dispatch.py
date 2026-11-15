"""Focused tests for the Context Mode server launcher and cache boundary."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_SRC = REPO_ROOT / "shared/hooks/scripts/context-mode-dispatch.sh"
FILTER_SRC = REPO_ROOT / "shared/hooks/scripts/context-mode-mcp-filter.mjs"


def _dispatcher_constant(name: str) -> str:
    """Read one quoted ``NAME="value"`` assignment from the dispatcher source."""
    match = re.search(rf'^{name}="([^"]+)"$', SCRIPT_SRC.read_text(), re.MULTILINE)
    assert match, f"{name} not found in the dispatcher"
    return match.group(1)


# The pin changes with every bump, so the fakes follow the dispatcher source;
# the validator test checks the validator's copy against the same source.
PINNED_VERSION = _dispatcher_constant("PINNED_CONTEXT_MODE_VERSION")
# Everything else comes from the approved plan, not from the dispatcher source.
MIN_NODE_VERSION = "24.15.0"
FILES_ONLY_CONTRACT = "ctx-index-files-only-v2"
FOLDER_CONTRACT = "ctx-index-file-content-v1"
SERVER_ARGS = "server --agent codex"
# Node.js versions below the floor, and one that is not a version at all.
OLD_NODE_VERSIONS = [
    pytest.param("v22.22.0", id="node-22"),
    pytest.param("v24.14.9", id="just-below-floor"),
    pytest.param("not-a-version", id="unparseable"),
]
ENOUGH_NODE_VERSIONS = [
    pytest.param("v24.15.0", id="exactly-the-floor"),
    pytest.param("v25.0.0", id="next-major"),
]


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
    version: str | None = PINNED_VERSION,
    manifest_name: str = "context-mode",
) -> tuple[Path, Path]:
    """A fake `context-mode` mirroring the real npm install layout.

    The dispatcher reads the owning package.json to prove the pinned version,
    because that needs no Node.js start and the server itself reports `dev`.
    So the fake must be a bin symlink pointing into a package directory,
    exactly like a real global install. `version=None` omits the manifest
    entirely, modelling a binary whose version cannot be determined. The fake
    traces its own execution, so a test can prove the dispatcher never ran it.
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


LAUNCH_FIELDS = ("dir", "root", "data", "pwd", "claude_project_dir", "argv")


def _fake_node(tmp_path: Path, *, version: str = "v24.15.0") -> tuple[Path, Path]:
    """A fake `node` that answers `--version` and records every launch.

    A `--version` call adds one line to `node-version-probes`, so a test can
    count the dispatcher's Node.js checks. Any other call is a launch and adds
    one line to the returned trace, in `LAUNCH_FIELDS` order: the cache root,
    the filter's project root, `CONTEXT_MODE_DATA_DIR`, the physical working
    folder, `CLAUDE_PROJECT_DIR` (`UNSET` when absent), and the arguments. The
    fake never starts the filter.
    """
    bin_dir = tmp_path / "node-bin"
    bin_dir.mkdir(exist_ok=True)
    trace = tmp_path / "node-trace"
    probes = tmp_path / "node-version-probes"
    executable = bin_dir / "node"
    executable.write_text(
        "#!/usr/bin/env bash\n"
        'if [[ "${1:-}" == "--version" ]]; then\n'
        f'  echo probe >> "{probes}"\n'
        f'  echo "{version}"\n'
        "  exit 0\n"
        "fi\n"
        "printf '%s|%s|%s|%s|%s|%s\\n' \"$CONTEXT_MODE_DIR\" "
        '"$CONTEXT_MODE_PROJECT_ROOT" "${CONTEXT_MODE_DATA_DIR-UNSET}" "$(pwd -P)" '
        '"${CLAUDE_PROJECT_DIR-UNSET}" "$*" >> "$NODE_TRACE"\n'
    )
    executable.chmod(0o755)
    return bin_dir, trace


def _launch(node_trace: Path) -> dict[str, str]:
    """The fields the fake `node` recorded for its last launch."""
    last = node_trace.read_text().splitlines()[-1]
    return dict(zip(LAUNCH_FIELDS, last.split("|", 5), strict=True))


def _node_probe_count(node_trace: Path) -> int:
    probes = node_trace.parent / "node-version-probes"
    return len(probes.read_text().splitlines()) if probes.exists() else 0


def _run(
    dispatcher: Path,
    *args: str,
    env: dict[str, str],
    input_text: str | None = None,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(dispatcher), *args],
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, **env},
        cwd=cwd,
    )


def _server_env(
    tmp_path: Path, *, node_version: str = "v24.15.0"
) -> tuple[dict[str, str], Path, Path]:
    """Environment with a pinned fake `context-mode` and a fake `node`.

    Returns the environment, the fake upstream's trace, and the fake node's
    trace; read the latest launch from the node trace with `_launch`.
    """
    bin_dir, trace = _fake_context_mode(tmp_path)
    node_bin, node_trace = _fake_node(tmp_path, version=node_version)
    return (
        {
            "PATH": f"{bin_dir}:{node_bin}:/usr/bin:/bin",
            "CONTEXT_MODE_TRACE": str(trace),
            "NODE_TRACE": str(node_trace),
        },
        trace,
        node_trace,
    )


def _cache_root_of(node_trace: Path) -> str:
    return _launch(node_trace)["dir"]


@pytest.mark.parametrize(
    ("client", "event"),
    [
        ("claude-code", "sessionstart"),
        ("openai-codex", "pretooluse"),
        ("github-copilot", "posttooluse"),
    ],
)
def test_legacy_hook_call_reads_stdin_and_does_nothing(
    installed_dispatcher: tuple[Path, Path],
    tmp_path: Path,
    client: str,
    event: str,
) -> None:
    """Stale hook wiring in an adapter the installer keeps must stay harmless:
    no output, no upstream, no node, and no cache or secret on disk."""
    root, dispatcher = installed_dispatcher
    env, trace, node_trace = _server_env(tmp_path)
    payload = json.dumps({"session_id": "s", "hook_event_name": event})

    result = _run(dispatcher, client, event, env=env, input_text=payload)

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    assert not trace.exists(), "a legacy hook call started the upstream binary"
    assert not node_trace.exists(), "a legacy hook call started node"
    assert _node_probe_count(node_trace) == 0, "a legacy hook call checked Node.js"
    assert not (root / ".claude/.cache").exists()
    assert not (root / ".context-mode-provenance.secret").exists()


def test_legacy_hook_call_consumes_all_of_stdin(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    """A client that writes a large payload must never see a broken pipe."""
    _, dispatcher = installed_dispatcher
    env, _, _ = _server_env(tmp_path)
    result = subprocess.run(
        [
            "bash",
            "-c",
            'head -c 1000000 /dev/zero | bash "$0" claude-code posttooluse; '
            'echo "writer-status=${PIPESTATUS[0]}"',
            str(dispatcher),
        ],
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, **env},
    )

    assert result.stdout == "writer-status=0\n"
    assert result.stderr == ""


def test_missing_context_mode_and_npx_fail_the_server_clearly(
    installed_dispatcher: tuple[Path, Path],
) -> None:
    _, dispatcher = installed_dispatcher
    result = _run(dispatcher, "server", env={"PATH": "/usr/bin:/bin"})
    assert result.returncode == 127
    assert "context-mode and npx are unavailable" in result.stderr


@pytest.mark.parametrize("relative", ["relative-cache", "../escape"])
def test_relative_and_traversal_overrides_fall_back(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path, relative: str
) -> None:
    root, dispatcher = installed_dispatcher
    env, _, node_trace = _server_env(tmp_path)
    env["CONTEXT_MODE_DIR"] = relative
    result = _run(dispatcher, "server", env=env)
    assert result.returncode == 0
    assert _cache_root_of(node_trace) == str(
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
    env, _, node_trace = _server_env(tmp_path)
    requested = root / relative
    env["CONTEXT_MODE_DIR"] = str(requested)
    result = _run(dispatcher, "server", env=env)
    assert result.returncode == 0
    assert _cache_root_of(node_trace) == str(
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
    env, _, node_trace = _server_env(tmp_path)
    env["CONTEXT_MODE_DIR"] = str(link / "context-mode")
    result = _run(dispatcher, "server", env=env)
    assert result.returncode == 0
    assert _cache_root_of(node_trace) == str(
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
    env, _, node_trace = _server_env(tmp_path)
    env["CONTEXT_MODE_DIR"] = str(link / "context-mode")
    result = _run(dispatcher, "server", env=env)
    assert result.returncode == 0
    assert _cache_root_of(node_trace) == str(
        (root / ".claude/.cache/context-mode").resolve()
    )
    assert not (external / "context-mode").exists()


def test_absolute_traversal_override_falls_back_without_creating_destination(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    root, dispatcher = installed_dispatcher
    (root / ".claude/plans").mkdir(parents=True)
    requested = f"{root}/.claude/.cache/context-mode/../../../plans/escaped"
    env, _, node_trace = _server_env(tmp_path)
    env["CONTEXT_MODE_DIR"] = requested
    result = _run(dispatcher, "server", env=env)
    assert result.returncode == 0
    assert _cache_root_of(node_trace) == str(
        (root / ".claude/.cache/context-mode").resolve()
    )
    assert not (root / ".claude/plans/escaped").exists()


def test_approved_cache_subtree_override_is_preserved(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    root, dispatcher = installed_dispatcher
    env, _, node_trace = _server_env(tmp_path)
    approved = root / ".claude/.cache/context-mode/alternate"
    env["CONTEXT_MODE_DIR"] = str(approved)
    assert _run(dispatcher, "server", env=env).returncode == 0
    assert _cache_root_of(node_trace) == str(approved.resolve())
    # The server's own data root is that same approved subtree.
    assert _launch(node_trace)["data"] == str(approved.resolve())


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
    env, _, node_trace = _server_env(tmp_path)
    external = tmp_path / "user-owned-cache"
    external.mkdir()
    (external / "user-data.txt").write_text("owned by the user")
    env["CONTEXT_MODE_DIR"] = str(external)

    result = _run(dispatcher, "server", env=env)

    assert result.returncode == 0
    assert "unsupported CONTEXT_MODE_DIR" in result.stderr
    # Fell back to the project-local cache.
    assert _cache_root_of(node_trace) == str(
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
    env, _, _ = _server_env(tmp_path)
    external = tmp_path / "never-created"
    env["CONTEXT_MODE_DIR"] = str(external)

    assert _run(dispatcher, "server", env=env).returncode == 0
    assert not external.exists()


def test_fresh_cache_marker_holds_the_files_only_filter_contract(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    root, dispatcher = installed_dispatcher
    env, _, _ = _server_env(tmp_path)

    assert _run(dispatcher, "server", env=env).returncode == 0

    marker = root / ".claude/.cache/context-mode/.bootstrap-provenance"
    assert f"filter={FILES_ONLY_CONTRACT}" in marker.read_text().splitlines()


def test_cache_indexed_under_the_folder_contract_is_moved_aside(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    """Only the filter field differs: the marker still holds the right
    repository, pin, and secret, so a trusting dispatcher would keep it."""
    root, dispatcher = installed_dispatcher
    env, _, _ = _server_env(tmp_path)
    assert _run(dispatcher, "server", env=env).returncode == 0
    cache = root / ".claude/.cache/context-mode"
    marker = cache / ".bootstrap-provenance"
    old_marker = marker.read_text().replace(
        f"filter={FILES_ONLY_CONTRACT}", f"filter={FOLDER_CONTRACT}"
    )
    assert f"filter={FOLDER_CONTRACT}" in old_marker
    marker.write_text(old_marker)
    (cache / "folder-era.db").write_text("indexed with folder support")

    result = _run(dispatcher, "server", env=env)

    assert result.returncode == 0
    assert "preserved unaudited Context Mode cache" in result.stderr
    moved = list(cache.parent.glob("context-mode.untrusted.*"))
    assert len(moved) == 1
    assert (moved[0] / "folder-era.db").read_text() == "indexed with folder support"
    assert not (cache / "folder-era.db").exists()
    assert f"filter={FILES_ONLY_CONTRACT}" in marker.read_text().splitlines()


def test_server_uses_direct_binary_only_at_the_exact_pinned_version(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    root, dispatcher = installed_dispatcher
    env, _, node_trace = _server_env(tmp_path)

    result = _run(dispatcher, "server", env=env)

    assert result.returncode == 0, result.stderr
    filter_script = root / ".claude/hooks/scripts/context-mode-mcp-filter.mjs"
    assert _launch(node_trace)["argv"] == (
        f"{filter_script} -- context-mode {SERVER_ARGS}"
    )


@pytest.mark.parametrize(
    ("version", "manifest_name"),
    [
        pytest.param("0.0.0", "context-mode", id="far-older"),
        pytest.param("2.0.0-next.1", "context-mode", id="prerelease"),
        # Exact equality, not a prefix match: the pin followed by one more digit.
        pytest.param(f"{PINNED_VERSION}0", "context-mode", id="pin-plus-a-digit"),
        # A nested dependency's manifest must never be mistaken for Context
        # Mode's own, even when its version happens to be the pinned string.
        pytest.param(PINNED_VERSION, "some-other-package", id="other-package"),
    ],
)
def test_server_refuses_a_direct_binary_that_is_not_the_pinned_version(
    installed_dispatcher: tuple[Path, Path],
    tmp_path: Path,
    version: str,
    manifest_name: str,
) -> None:
    """A mismatched direct binary must never be launched; with no `npx` to fall
    back on, the server fails clearly instead of starting."""
    _, dispatcher = installed_dispatcher
    bin_dir, trace = _fake_context_mode(
        tmp_path, version=version, manifest_name=manifest_name
    )
    node_bin, node_trace = _fake_node(tmp_path)
    env = {
        "PATH": f"{bin_dir}:{node_bin}:/usr/bin:/bin",
        "CONTEXT_MODE_TRACE": str(trace),
        "NODE_TRACE": str(node_trace),
    }

    result = _run(dispatcher, "server", env=env)

    assert result.returncode == 127
    assert f"requires exactly {PINNED_VERSION}" in result.stderr
    assert not trace.exists(), "a non-pinned context-mode binary was executed"
    assert not node_trace.exists()


def test_server_refuses_a_direct_binary_with_an_undeterminable_version(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    """No manifest means the version cannot be proven, so the binary must be
    skipped rather than trusted."""
    _, dispatcher = installed_dispatcher
    bin_dir, trace = _fake_context_mode(tmp_path, version=None)
    node_bin, node_trace = _fake_node(tmp_path)
    env = {
        "PATH": f"{bin_dir}:{node_bin}:/usr/bin:/bin",
        "CONTEXT_MODE_TRACE": str(trace),
        "NODE_TRACE": str(node_trace),
    }

    result = _run(dispatcher, "server", env=env)

    assert result.returncode == 127
    assert "undeterminable" in result.stderr
    assert not trace.exists()
    assert not node_trace.exists()


def test_server_falls_back_to_pinned_npx_when_direct_binary_is_rejected(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    """A rejected direct binary must not disable Context Mode: the pinned npx
    fallback is correct by construction and must still be used."""
    root, dispatcher = installed_dispatcher
    bin_dir, trace = _fake_context_mode(tmp_path, version="0.0.0")
    node_bin, node_trace = _fake_node(tmp_path)
    npx_dir = tmp_path / "npx-bin"
    npx_dir.mkdir()
    npx = npx_dir / "npx"
    npx.write_text("#!/usr/bin/env bash\nexit 0\n")
    npx.chmod(0o755)
    env = {
        "PATH": f"{bin_dir}:{npx_dir}:{node_bin}:/usr/bin:/bin",
        "CONTEXT_MODE_TRACE": str(trace),
        "NODE_TRACE": str(node_trace),
    }

    result = _run(dispatcher, "server", env=env)

    assert result.returncode == 0, result.stderr
    assert not trace.exists(), "the rejected direct binary was executed"
    filter_script = root / ".claude/hooks/scripts/context-mode-mcp-filter.mjs"
    assert _launch(node_trace)["argv"] == (
        f"{filter_script} -- npx -y context-mode@{PINNED_VERSION} {SERVER_ARGS}"
    )


def test_self_check_reports_the_observed_version_and_contract_result(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    """--self-check must prove the version contract, not merely restate the pin."""
    _, dispatcher = installed_dispatcher
    bin_dir, _ = _fake_context_mode(tmp_path, version=PINNED_VERSION)

    ok = _run(dispatcher, "--self-check", env={"PATH": f"{bin_dir}:/usr/bin:/bin"})

    assert ok.returncode == 0
    assert f"required-version={PINNED_VERSION}" in ok.stdout
    assert f"resolved-path={bin_dir / 'context-mode'}" in ok.stdout
    assert f"observed-version={PINNED_VERSION}" in ok.stdout
    assert "version-contract=pinned-direct-binary" in ok.stdout


def test_self_check_reports_a_failing_version_contract(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    _, dispatcher = installed_dispatcher
    bin_dir, _ = _fake_context_mode(tmp_path, version="2.0.0-next.1")

    bad = _run(dispatcher, "--self-check", env={"PATH": f"{bin_dir}:/usr/bin:/bin"})

    assert bad.returncode == 0
    assert "observed-version=2.0.0-next.1" in bad.stdout
    assert "version-contract=pinned-direct-binary" not in bad.stdout
    assert "version-contract=FAIL" in bad.stderr
    # Context Mode has no hook route any more, so the warning talks about the server.
    assert "hook" not in bad.stderr


def test_self_check_without_context_mode_or_npx_warns_about_the_server(
    installed_dispatcher: tuple[Path, Path],
) -> None:
    _, dispatcher = installed_dispatcher

    result = _run(dispatcher, "--self-check", env={"PATH": "/usr/bin:/bin"})

    assert result.returncode == 0
    assert "MCP server cannot start" in result.stderr
    assert "hook" not in result.stderr
    # No fake node is on PATH here, and the Node.js line must still be honest.
    assert f"required-node={MIN_NODE_VERSION}" in result.stdout
    assert "observed-node=none-on-PATH" in result.stdout


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
    env, _, node_trace = _server_env(tmp_path)

    result = _run(dispatcher, "server", env=env)

    assert result.returncode == 0, result.stderr
    filter_script = root / ".claude/hooks/scripts/context-mode-mcp-filter.mjs"
    launch = _launch(node_trace)
    assert launch["dir"] == str((root / ".claude/.cache/context-mode").resolve())
    assert launch["root"] == str(root.resolve())
    assert launch["argv"] == f"{filter_script} -- context-mode {SERVER_ARGS}"
    # One server identity: the codex agent, and no workspace-folder argument.
    assert "--workspace-folder" not in launch["argv"]


def test_server_mode_execs_pinned_npx_fallback_through_filter(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    """When `context-mode` is not on PATH, `server` mode must fall back to
    `npx` pinned to the exact version the direct binary must also match."""
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
    argv = _launch(node_trace)["argv"]
    assert (
        argv == f"{filter_script} -- npx -y context-mode@{PINNED_VERSION} {SERVER_ARGS}"
    )
    assert "--workspace-folder" not in argv


def test_server_mode_fails_clearly_when_node_missing(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    _, dispatcher = installed_dispatcher
    context_mode_bin, trace = _fake_context_mode(tmp_path)
    env = {
        "PATH": f"{context_mode_bin}:/usr/bin:/bin",
        "CONTEXT_MODE_TRACE": str(trace),
    }

    result = _run(dispatcher, "server", env=env)

    assert result.returncode != 0
    assert "unavailable" in result.stderr
    assert not trace.exists()


def test_server_mode_fails_clearly_when_filter_script_missing(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    root, dispatcher = installed_dispatcher
    (root / ".claude/hooks/scripts/context-mode-mcp-filter.mjs").unlink()
    env, _, node_trace = _server_env(tmp_path)

    result = _run(dispatcher, "server", env=env)

    assert result.returncode != 0
    assert "unavailable" in result.stderr
    assert not node_trace.exists()


@pytest.mark.parametrize(
    "start",
    [
        pytest.param(".", id="repository-root"),
        pytest.param(".claude", id="nested-claude-repository"),
        pytest.param(".claude/hooks/scripts", id="scripts-folder"),
        pytest.param("../outside", id="unrelated-folder"),
    ],
)
def test_server_starts_in_the_outer_repository_root_from_any_folder(
    installed_dispatcher: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    start: str,
) -> None:
    """Context Mode 2.x with `--agent codex` keys its project to the working
    folder's Git repository, so a server started inside the nested `.claude`
    repository would index into a separate project. The dispatcher must move to
    the outer root first, and must not set `CLAUDE_PROJECT_DIR` to get there."""
    root, dispatcher = installed_dispatcher
    subprocess.run(["git", "init", "-q", str(root / ".claude")], check=True)
    (tmp_path / "outside").mkdir()
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    env, _, node_trace = _server_env(tmp_path)

    result = _run(dispatcher, "server", env=env, cwd=(root / start).resolve())

    assert result.returncode == 0, result.stderr
    launch = _launch(node_trace)
    assert launch["pwd"] == str(root.resolve())
    assert launch["claude_project_dir"] == "UNSET"


def test_server_leaves_an_inherited_claude_project_dir_alone(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    """Under `--agent codex` the server ignores it, so the dispatcher neither
    sets nor clears it."""
    _, dispatcher = installed_dispatcher
    env, _, node_trace = _server_env(tmp_path)
    env["CLAUDE_PROJECT_DIR"] = str(tmp_path / "somewhere-else")

    assert _run(dispatcher, "server", env=env).returncode == 0

    assert _launch(node_trace)["claude_project_dir"] == str(tmp_path / "somewhere-else")


def test_server_looks_up_the_launcher_from_the_repository_root(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    """A relative PATH entry is the observable difference: it only resolves from
    the repository root, so the version proof, the filter, and the server all
    search PATH from the folder the server runs in."""
    root, dispatcher = installed_dispatcher
    _fake_context_mode(root)  # <repo>/bin/context-mode, found only via PATH `bin`
    node_bin, node_trace = _fake_node(tmp_path)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    env = {"PATH": f"bin:{node_bin}:/usr/bin:/bin", "NODE_TRACE": str(node_trace)}

    result = _run(dispatcher, "server", env=env, cwd=elsewhere)

    assert result.returncode == 0, result.stderr
    assert _launch(node_trace)["argv"].endswith(f"-- context-mode {SERVER_ARGS}")


def test_self_check_looks_up_the_launcher_from_the_repository_root(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    root, dispatcher = installed_dispatcher
    _fake_context_mode(root)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()

    result = _run(
        dispatcher, "--self-check", env={"PATH": "bin:/usr/bin:/bin"}, cwd=elsewhere
    )

    assert result.returncode == 0
    assert f"observed-version={PINNED_VERSION}" in result.stdout
    assert "version-contract=pinned-direct-binary" in result.stdout


@pytest.mark.parametrize(
    ("set_dir", "set_data"),
    [
        pytest.param(False, False, id="nothing-inherited"),
        pytest.param(False, True, id="data-dir-elsewhere"),
        pytest.param(True, True, id="both-elsewhere"),
    ],
)
def test_data_root_is_the_guarded_cache_root_whatever_the_caller_exports(
    installed_dispatcher: tuple[Path, Path],
    tmp_path: Path,
    set_dir: bool,
    set_data: bool,
) -> None:
    """Context Mode 2.x ignores `CONTEXT_MODE_DIR` and keeps everything under
    `CONTEXT_MODE_DATA_DIR`, so an inherited value there could move data out of
    the guarded root. The dispatcher overwrites it with the chosen root."""
    root, dispatcher = installed_dispatcher
    env, _, node_trace = _server_env(tmp_path)
    foreign = tmp_path / "foreign-data"
    if set_dir:
        env["CONTEXT_MODE_DIR"] = str(foreign)
    if set_data:
        env["CONTEXT_MODE_DATA_DIR"] = str(foreign)

    result = _run(dispatcher, "server", env=env)

    assert result.returncode == 0, result.stderr
    guarded = str((root / ".claude/.cache/context-mode").resolve())
    launch = _launch(node_trace)
    assert launch["data"] == guarded
    assert launch["dir"] == guarded
    assert not foreign.exists()


@pytest.mark.parametrize("node_version", OLD_NODE_VERSIONS)
def test_server_refuses_node_below_the_floor_with_one_error_line(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path, node_version: str
) -> None:
    _, dispatcher = installed_dispatcher
    env, trace, node_trace = _server_env(tmp_path, node_version=node_version)

    result = _run(dispatcher, "server", env=env)

    assert result.returncode == 1
    lines = result.stderr.splitlines()
    assert len(lines) == 1, result.stderr
    assert lines[0].startswith("ERROR context-mode-dispatch:")
    assert MIN_NODE_VERSION in lines[0]
    assert not node_trace.exists(), "the server started on a Node.js below the floor"
    assert not trace.exists()
    assert _node_probe_count(node_trace) == 1


@pytest.mark.parametrize("node_version", ENOUGH_NODE_VERSIONS)
def test_server_starts_on_node_at_or_above_the_floor_after_one_check(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path, node_version: str
) -> None:
    _, dispatcher = installed_dispatcher
    env, _, node_trace = _server_env(tmp_path, node_version=node_version)

    result = _run(dispatcher, "server", env=env)

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert _node_probe_count(node_trace) == 1
    assert _launch(node_trace)["argv"].endswith(SERVER_ARGS)


@pytest.mark.parametrize("node_version", OLD_NODE_VERSIONS)
def test_self_check_warns_about_node_below_the_floor(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path, node_version: str
) -> None:
    _, dispatcher = installed_dispatcher
    bin_dir, _ = _fake_context_mode(tmp_path)
    node_bin, _ = _fake_node(tmp_path, version=node_version)

    result = _run(
        dispatcher,
        "--self-check",
        env={"PATH": f"{bin_dir}:{node_bin}:/usr/bin:/bin"},
    )

    assert result.returncode == 0
    assert f"required-node={MIN_NODE_VERSION}" in result.stdout
    assert f"observed-node={node_version}" in result.stdout
    assert MIN_NODE_VERSION in result.stderr


@pytest.mark.parametrize("node_version", ENOUGH_NODE_VERSIONS)
def test_self_check_passes_node_at_or_above_the_floor_without_a_warning(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path, node_version: str
) -> None:
    _, dispatcher = installed_dispatcher
    bin_dir, _ = _fake_context_mode(tmp_path)
    node_bin, _ = _fake_node(tmp_path, version=node_version)

    result = _run(
        dispatcher,
        "--self-check",
        env={"PATH": f"{bin_dir}:{node_bin}:/usr/bin:/bin"},
    )

    assert result.returncode == 0
    assert f"required-node={MIN_NODE_VERSION}" in result.stdout
    assert f"observed-node={node_version}" in result.stdout
    assert result.stderr == ""


def test_cache_stamped_with_an_older_pin_is_moved_aside_even_with_the_right_secret(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    """Exact-version provenance: only the pin differs, so a dispatcher that
    trusted the secret alone would keep an index the new server cannot read."""
    root, dispatcher = installed_dispatcher
    env, _, node_trace = _server_env(tmp_path)
    assert _run(dispatcher, "server", env=env).returncode == 0
    cache = root / ".claude/.cache/context-mode"
    marker = cache / ".bootstrap-provenance"
    secret = (root / ".context-mode-provenance.secret").read_text()
    older = marker.read_text().replace(
        f"context-mode={PINNED_VERSION}", "context-mode=0.0.0"
    )
    assert "context-mode=0.0.0" in older.splitlines()
    assert f"secret={secret}" in older.splitlines()
    marker.write_text(older)
    (cache / "older-pin.db").write_text("indexed under the previous pin")

    result = _run(dispatcher, "server", env=env)

    assert result.returncode == 0, result.stderr
    assert "preserved unaudited Context Mode cache" in result.stderr
    moved = list(cache.parent.glob("context-mode.untrusted.*"))
    assert len(moved) == 1
    assert (moved[0] / "older-pin.db").read_text() == "indexed under the previous pin"
    assert not (cache / "older-pin.db").exists()
    assert f"context-mode={PINNED_VERSION}" in marker.read_text().splitlines()
    launch = _launch(node_trace)
    assert launch["data"] == launch["dir"] == str(cache.resolve())


def _fake_failing_mv(tmp_path: Path, *, other_dispatcher_wins: bool) -> Path:
    """A `mv` that fails for the cache quarantine only; everything else runs the
    real one (the provenance secret is also written with `mv -n`).

    With `other_dispatcher_wins` it first renames the cache folder, as a second
    dispatcher that quarantined it first would have. Nothing is ever deleted.
    """
    bin_dir = tmp_path / "mv-bin"
    bin_dir.mkdir()
    rename = (
        '    /bin/mv "$1" "$1.moved-by-another-dispatcher"\n'
        if other_dispatcher_wins
        else ""
    )
    fake = bin_dir / "mv"
    fake.write_text(
        "#!/usr/bin/env bash\n"
        'case "$1" in\n'
        "  */.cache/context-mode)\n"
        f"{rename}"
        "    exit 1 ;;\n"
        "esac\n"
        'exec /bin/mv "$@"\n'
    )
    fake.chmod(0o755)
    return bin_dir


def test_quarantine_that_loses_a_race_still_starts_with_a_fresh_cache(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    root, dispatcher = installed_dispatcher
    env, _, node_trace = _server_env(tmp_path)
    cache = root / ".claude/.cache/context-mode"
    cache.mkdir(parents=True)
    (cache / "unaudited.db").write_text("unaudited bytes")  # no marker
    fake_mv = _fake_failing_mv(tmp_path, other_dispatcher_wins=True)
    env["PATH"] = f"{fake_mv}:{env['PATH']}"

    result = _run(dispatcher, "server", env=env)

    assert result.returncode == 0, result.stderr
    warnings = result.stderr.splitlines()
    assert len(warnings) == 1, result.stderr
    assert warnings[0].startswith("WARN context-mode-dispatch:")
    assert "another dispatcher" in warnings[0]
    # The folder the other dispatcher moved keeps its bytes; the new root is fresh.
    moved = cache.parent / "context-mode.moved-by-another-dispatcher"
    assert (moved / "unaudited.db").read_text() == "unaudited bytes"
    assert not (cache / "unaudited.db").exists()
    assert (cache / ".bootstrap-provenance").is_file()
    assert _cache_root_of(node_trace) == str(cache.resolve())


def test_quarantine_failure_with_the_folder_still_there_never_trusts_it(
    installed_dispatcher: tuple[Path, Path], tmp_path: Path
) -> None:
    """A move that fails while the unaudited folder still exists is not a lost
    race: the server must not start on it, stamp it, or delete it."""
    root, dispatcher = installed_dispatcher
    env, _, node_trace = _server_env(tmp_path)
    cache = root / ".claude/.cache/context-mode"
    cache.mkdir(parents=True)
    (cache / "unaudited.db").write_text("unaudited bytes")
    fake_mv = _fake_failing_mv(tmp_path, other_dispatcher_wins=False)
    env["PATH"] = f"{fake_mv}:{env['PATH']}"

    result = _run(dispatcher, "server", env=env)

    assert result.returncode == 1
    assert "guarded storage/provenance unavailable" in result.stderr
    assert not node_trace.exists()
    assert (cache / "unaudited.db").read_text() == "unaudited bytes"
    assert not (cache / ".bootstrap-provenance").exists()
