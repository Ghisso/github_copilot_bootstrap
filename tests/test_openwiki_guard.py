"""Regression coverage for the host-driven `openwiki-guard` hook (Phase G,
Step G1): `pre` gates `openwiki_begin`, `post` restores the two managed root
adapters (and the workflow path) afterwards.

Reuses `_isolated_hook_scripts_dir` from `tests/test_hook_gates.py` so
`REPO_ROOT` (both the shell wrapper's `repo_root_from_script()` and the
Python module's own lexical, symlink-preserving equivalent) resolves to a
synthetic checkout instead of the live repository.
"""

from __future__ import annotations

import base64
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from test_hook_gates import SCRIPT_SRC, _isolated_hook_scripts_dir  # noqa: E402

MANAGED_START = "<!-- OPENWIKI:START -->"
MANAGED_END = "<!-- OPENWIKI:END -->"
MANIFEST_PATH = ".claude/.cache/openwiki-guard/manifest.json"


def _guard_repo(tmp_path: Path) -> Path:
    """A synthetic checkout with `openwiki/INSTRUCTIONS.md` and both root
    adapters, isolated via `_isolated_hook_scripts_dir`."""
    _isolated_hook_scripts_dir(tmp_path)
    (tmp_path / "openwiki").mkdir()
    (tmp_path / "openwiki" / "INSTRUCTIONS.md").write_text("hi\n", encoding="utf-8")
    (tmp_path / "AGENTS.md").write_text("# Guidance\n\nSome text", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("# Claude\n\nStuff\n", encoding="utf-8")
    return tmp_path


def _run_guard(
    root: Path, mode: str, payload: dict | None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "bash",
            str(root / "shared" / "hooks" / "scripts" / "openwiki-guard.sh"),
            mode,
        ],
        cwd=root,
        input=json.dumps(payload) if payload is not None else "",
        text=True,
        capture_output=True,
        check=False,
    )


def _pre_payload(
    mode: str = "update", root: Path | None = None, **extra: object
) -> dict:
    tool_input: dict[str, object] = {"mode": mode}
    if root is not None:
        tool_input["root"] = str(root)
    tool_input.update(extra)
    return {"tool_name": "mcp__openwiki__openwiki_begin", "tool_input": tool_input}


def _manifest_path(root: Path) -> Path:
    return root / MANIFEST_PATH


def _snippet(body: str = "inserted content") -> str:
    return f"{MANAGED_START}\n{body}\n{MANAGED_END}"


def _apply_insertion(path: Path, snippet: str) -> None:
    """Mirror `code-mode.js`'s insertion shape: `content.trimEnd() + "\\n\\n"
    + snippet + "\\n"` - this deliberately drops the original trailing
    newline, which is why byte-exact restore needs a pre-snapshot."""
    original = path.read_bytes()
    mutated = original.rstrip(b"\n") + b"\n\n" + snippet.encode("utf-8") + b"\n"
    path.write_bytes(mutated)


# --- pre: deny paths -------------------------------------------------------


def test_pre_denies_mode_init(tmp_path: Path) -> None:
    root = _guard_repo(tmp_path)

    result = _run_guard(root, "pre", _pre_payload(mode="init", root=root))

    assert result.returncode == 0, result.stderr
    assert '"permissionDecision":"deny"' in result.stdout
    assert "update" in result.stdout
    assert not _manifest_path(root).exists()


def test_pre_denies_a_foreign_root(tmp_path: Path) -> None:
    root = _guard_repo(tmp_path)
    other = tmp_path.parent / f"{tmp_path.name}-other"
    other.mkdir(exist_ok=True)

    result = _run_guard(root, "pre", _pre_payload(root=other))

    assert result.returncode == 0, result.stderr
    assert '"permissionDecision":"deny"' in result.stdout
    assert not _manifest_path(root).exists()


def test_pre_denies_a_missing_root(tmp_path: Path) -> None:
    root = _guard_repo(tmp_path)

    result = _run_guard(root, "pre", {"tool_input": {"mode": "update"}})

    assert result.returncode == 0, result.stderr
    assert '"permissionDecision":"deny"' in result.stdout
    assert "root" in result.stdout


def test_pre_denies_a_missing_instructions_marker(tmp_path: Path) -> None:
    root = _guard_repo(tmp_path)
    (root / "openwiki" / "INSTRUCTIONS.md").unlink()

    result = _run_guard(root, "pre", _pre_payload(root=root))

    assert result.returncode == 0, result.stderr
    assert '"permissionDecision":"deny"' in result.stdout
    assert "INSTRUCTIONS.md" in result.stdout
    assert not _manifest_path(root).exists()


# --- pre: allow + snapshot ---------------------------------------------


def test_pre_allows_and_snapshots_otherwise(tmp_path: Path) -> None:
    root = _guard_repo(tmp_path)
    agents_before = (root / "AGENTS.md").read_bytes()
    claude_before = (root / "CLAUDE.md").read_bytes()

    result = _run_guard(root, "pre", _pre_payload(root=root))

    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    manifest = json.loads(_manifest_path(root).read_text(encoding="utf-8"))
    assert manifest["adapters"]["AGENTS.md"]["present"] is True
    assert (
        base64.b64decode(manifest["adapters"]["AGENTS.md"]["content_b64"])
        == agents_before
    )
    assert manifest["adapters"]["CLAUDE.md"]["present"] is True
    assert (
        base64.b64decode(manifest["adapters"]["CLAUDE.md"]["content_b64"])
        == claude_before
    )
    assert manifest["workflow"]["present"] is False


# --- post: restore ----------------------------------------------------


def test_post_restores_byte_for_byte_after_a_simulated_insertion(
    tmp_path: Path,
) -> None:
    """The exact shape `code-mode.js` produces, including trailing-newline
    loss: `pre` snapshots, the insertion mutates the file, `post` must
    reproduce the original bytes exactly, not merely something equivalent."""
    root = _guard_repo(tmp_path)
    agents_before = (root / "AGENTS.md").read_bytes()
    claude_before = (root / "CLAUDE.md").read_bytes()
    assert not agents_before.endswith(b"\n\n")

    pre_result = _run_guard(root, "pre", _pre_payload(root=root))
    assert pre_result.returncode == 0, pre_result.stderr

    _apply_insertion(root / "AGENTS.md", _snippet())
    assert (root / "AGENTS.md").read_bytes() != agents_before

    post_result = _run_guard(
        root, "post", {"tool_name": "mcp__openwiki__openwiki_begin"}
    )

    assert post_result.returncode == 0, post_result.stderr
    assert "restored_from: snapshot" in post_result.stdout
    assert (root / "AGENTS.md").read_bytes() == agents_before
    assert (root / "CLAUDE.md").read_bytes() == claude_before
    assert not _manifest_path(root).exists()


def test_post_removes_an_adapter_absent_before(tmp_path: Path) -> None:
    root = _guard_repo(tmp_path)
    (root / "CLAUDE.md").unlink()

    pre_result = _run_guard(root, "pre", _pre_payload(root=root))
    assert pre_result.returncode == 0, pre_result.stderr
    manifest = json.loads(_manifest_path(root).read_text(encoding="utf-8"))
    assert manifest["adapters"]["CLAUDE.md"]["present"] is False

    (root / "CLAUDE.md").write_text(_snippet("new file"), encoding="utf-8")

    post_result = _run_guard(root, "post", {})

    assert post_result.returncode == 0, post_result.stderr
    assert "CLAUDE.md=removed" in post_result.stdout
    assert not (root / "CLAUDE.md").exists()
    assert not _manifest_path(root).exists()


def test_post_leaves_a_concurrently_edited_adapter_alone_and_exits_2(
    tmp_path: Path,
) -> None:
    root = _guard_repo(tmp_path)
    pre_result = _run_guard(root, "pre", _pre_payload(root=root))
    assert pre_result.returncode == 0, pre_result.stderr

    edited = "a human rewrote this file with no OpenWiki marker\n"
    (root / "AGENTS.md").write_text(edited, encoding="utf-8")

    post_result = _run_guard(root, "post", {})

    assert post_result.returncode == 2, post_result.stdout
    assert "AGENTS.md" in post_result.stderr
    assert (root / "AGENTS.md").read_text(encoding="utf-8") == edited
    assert _manifest_path(root).exists(), "snapshot must survive an unresolved mismatch"


def test_post_removes_a_workflow_file_that_appeared(tmp_path: Path) -> None:
    root = _guard_repo(tmp_path)
    pre_result = _run_guard(root, "pre", _pre_payload(root=root))
    assert pre_result.returncode == 0, pre_result.stderr
    manifest = json.loads(_manifest_path(root).read_text(encoding="utf-8"))
    assert manifest["workflow"]["present"] is False

    workflow = root / ".github" / "workflows" / "openwiki-update.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text("name: openwiki-update\n", encoding="utf-8")

    post_result = _run_guard(root, "post", {})

    assert post_result.returncode == 0, post_result.stderr
    assert not workflow.exists()


def test_post_strips_as_fallback_with_no_snapshot(tmp_path: Path) -> None:
    root = _guard_repo(tmp_path)
    agents_before = (root / "AGENTS.md").read_bytes()
    _apply_insertion(root / "AGENTS.md", _snippet())
    assert not _manifest_path(root).exists()

    result = _run_guard(root, "post", {})

    assert result.returncode == 0, result.stderr
    assert "restored_from: marker-strip" in result.stdout
    stripped = (root / "AGENTS.md").read_text(encoding="utf-8")
    assert MANAGED_START not in stripped
    assert MANAGED_END not in stripped
    # Lossy fallback: content matches modulo the original's exact trailing
    # newline shape, which no snapshot exists to reproduce.
    assert stripped.rstrip("\n") == agents_before.decode("utf-8").rstrip("\n")


def test_pre_heals_a_stale_snapshot(tmp_path: Path) -> None:
    """A prior `pre` ran and snapshotted, but its matching `post` never ran
    (crash, skipped step). The next `pre` must heal that stale snapshot
    before taking its own, so restoring later still works."""
    root = _guard_repo(tmp_path)
    agents_before = (root / "AGENTS.md").read_bytes()

    first_pre = _run_guard(root, "pre", _pre_payload(root=root))
    assert first_pre.returncode == 0, first_pre.stderr
    _apply_insertion(root / "AGENTS.md", _snippet())
    assert (root / "AGENTS.md").read_bytes() != agents_before

    second_pre = _run_guard(root, "pre", _pre_payload(root=root))

    assert second_pre.returncode == 0, second_pre.stderr
    assert second_pre.stdout == ""
    # The stale snapshot was healed (restored) before the fresh one was
    # taken, so AGENTS.md is back to its original bytes right now.
    assert (root / "AGENTS.md").read_bytes() == agents_before
    manifest = json.loads(_manifest_path(root).read_text(encoding="utf-8"))
    assert (
        base64.b64decode(manifest["adapters"]["AGENTS.md"]["content_b64"])
        == agents_before
    )


# --- manifest integrity -------------------------------------------------

MALFORMED_MANIFESTS = (
    pytest.param('{"version":1}', id="missing-adapters-and-workflow"),
    pytest.param(
        json.dumps(
            {
                "version": 1,
                "adapters": {"AGENTS.md": {"present": False}},
                "workflow": {"present": False},
            }
        ),
        id="missing-one-adapter-entry",
    ),
    pytest.param(
        json.dumps(
            {
                "version": 1,
                "adapters": {"AGENTS.md": {}, "CLAUDE.md": {"present": False}},
                "workflow": {"present": False},
            }
        ),
        id="present-missing",
    ),
    pytest.param(
        json.dumps(
            {
                "version": 1,
                "adapters": {
                    "AGENTS.md": {"present": "yes"},
                    "CLAUDE.md": {"present": False},
                },
                "workflow": {"present": False},
            }
        ),
        id="present-non-boolean",
    ),
)


@pytest.mark.parametrize("manifest_text", MALFORMED_MANIFESTS)
def test_post_rejects_a_malformed_manifest_and_touches_nothing(
    tmp_path: Path, manifest_text: str
) -> None:
    """A manifest that is valid JSON but does not pass shape validation must
    never be read as "recorded absent" - that reading previously made
    `_restore_one` delete live, unsnapshotted AGENTS.md/CLAUDE.md."""
    root = _guard_repo(tmp_path)
    agents_before = (root / "AGENTS.md").read_bytes()
    claude_before = (root / "CLAUDE.md").read_bytes()
    manifest_path = _manifest_path(root)
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(manifest_text, encoding="utf-8")

    result = _run_guard(root, "post", {})

    assert result.returncode == 2, result.stdout
    assert str(manifest_path) in result.stderr or manifest_path.name in result.stderr
    assert (root / "AGENTS.md").read_bytes() == agents_before
    assert (root / "CLAUDE.md").read_bytes() == claude_before
    assert manifest_path.exists(), "a malformed manifest must not be deleted either"


@pytest.mark.parametrize("manifest_text", MALFORMED_MANIFESTS)
def test_pre_denies_when_healing_finds_a_malformed_manifest(
    tmp_path: Path, manifest_text: str
) -> None:
    root = _guard_repo(tmp_path)
    agents_before = (root / "AGENTS.md").read_bytes()
    claude_before = (root / "CLAUDE.md").read_bytes()
    manifest_path = _manifest_path(root)
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(manifest_text, encoding="utf-8")

    result = _run_guard(root, "pre", _pre_payload(root=root))

    assert result.returncode == 0, result.stderr
    assert '"permissionDecision":"deny"' in result.stdout
    assert (root / "AGENTS.md").read_bytes() == agents_before
    assert (root / "CLAUDE.md").read_bytes() == claude_before
    assert manifest_path.exists()


# --- symlink safety -------------------------------------------------------


def test_pre_denies_a_symlinked_adapter(tmp_path: Path) -> None:
    root = _guard_repo(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside-secret.md"
    outside.write_text("outside content\n", encoding="utf-8")
    (root / "AGENTS.md").unlink()
    (root / "AGENTS.md").symlink_to(outside)

    result = _run_guard(root, "pre", _pre_payload(root=root))

    assert result.returncode == 0, result.stderr
    assert '"permissionDecision":"deny"' in result.stdout
    assert "AGENTS.md" in result.stdout
    assert not _manifest_path(root).exists(), (
        "a symlinked adapter must never be snapshotted (its target's content "
        "would leak into the repo-local manifest)"
    )
    assert (root / "AGENTS.md").is_symlink()


def test_post_refuses_a_symlinked_adapter_and_leaves_it_intact(
    tmp_path: Path,
) -> None:
    root = _guard_repo(tmp_path)
    pre_result = _run_guard(root, "pre", _pre_payload(root=root))
    assert pre_result.returncode == 0, pre_result.stderr

    outside = tmp_path.parent / f"{tmp_path.name}-outside-secret.md"
    outside.write_text("outside content\n", encoding="utf-8")
    (root / "AGENTS.md").unlink()
    (root / "AGENTS.md").symlink_to(outside)

    result = _run_guard(root, "post", {})

    assert result.returncode == 2, result.stdout
    assert "AGENTS.md" in result.stderr
    assert (root / "AGENTS.md").is_symlink(), "os.replace must never flatten it"
    assert (root / "AGENTS.md").resolve() == outside.resolve()
    assert _manifest_path(root).exists(), "snapshot must survive an unresolved mismatch"


def test_marker_strip_fallback_skips_a_symlinked_adapter(tmp_path: Path) -> None:
    root = _guard_repo(tmp_path)
    outside = tmp_path.parent / f"{tmp_path.name}-outside-secret.md"
    outside.write_text(_snippet(), encoding="utf-8")
    (root / "AGENTS.md").unlink()
    (root / "AGENTS.md").symlink_to(outside)
    assert not _manifest_path(root).exists()

    result = _run_guard(root, "post", {})

    assert result.returncode == 0, result.stderr
    assert "AGENTS.md=unchanged" in result.stdout
    assert (root / "AGENTS.md").is_symlink()
    assert (root / "AGENTS.md").resolve() == outside.resolve()
    # The symlink's target is untouched - the fallback never wrote through it.
    assert MANAGED_START in outside.read_text(encoding="utf-8")


# --- fail-closed -------------------------------------------------------


def test_unparseable_payload_fails_closed(tmp_path: Path) -> None:
    root = _guard_repo(tmp_path)

    result = subprocess.run(
        [
            "bash",
            str(root / "shared" / "hooks" / "scripts" / "openwiki-guard.sh"),
            "pre",
        ],
        cwd=root,
        input="{not valid json",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert '"permissionDecision":"deny"' in result.stdout
    assert not _manifest_path(root).exists()


def test_unparseable_payload_fails_closed_for_post(tmp_path: Path) -> None:
    root = _guard_repo(tmp_path)

    result = subprocess.run(
        [
            "bash",
            str(root / "shared" / "hooks" / "scripts" / "openwiki-guard.sh"),
            "post",
        ],
        cwd=root,
        input="{not valid json",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert result.stdout == ""


def test_unknown_mode_fails_closed(tmp_path: Path) -> None:
    root = _guard_repo(tmp_path)

    result = subprocess.run(
        [
            "bash",
            str(root / "shared" / "hooks" / "scripts" / "openwiki-guard.sh"),
            "sideways",
        ],
        cwd=root,
        input="",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert '"permissionDecision":"deny"' in result.stdout


# --- 3.9 compatibility --------------------------------------------------


def test_openwiki_guard_py_compiles() -> None:
    """Regression pin for the 3.9-compatible stdlib-only contract. Compiles
    with a real Python 3.9 interpreter when one is available on this host,
    and always with whichever python3 is on PATH (matching the existing
    protect-files.py 3.9-compatibility check's tolerance)."""
    interpreters = ["python3"]
    python39 = shutil.which("python3.9")
    if python39:
        interpreters.insert(0, python39)
    for interpreter in interpreters:
        result = subprocess.run(
            [interpreter, "-m", "py_compile", str(SCRIPT_SRC / "openwiki-guard.py")],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert result.returncode == 0, f"{interpreter}: {result.stderr}"


# --- generated hook wiring ----------------------------------------------


def test_generated_claude_settings_wire_the_openwiki_guard(tmp_path: Path) -> None:
    from generate_targets import OPENWIKI_BEGIN_MATCHER, render_claude_settings

    settings_path = tmp_path / "settings.json"
    render_claude_settings(settings_path)
    hooks = json.loads(settings_path.read_text(encoding="utf-8"))["hooks"]

    pre_matchers = {group["matcher"] for group in hooks["PreToolUse"]}
    assert OPENWIKI_BEGIN_MATCHER in pre_matchers
    post_matchers = {group["matcher"] for group in hooks["PostToolUse"]}
    assert OPENWIKI_BEGIN_MATCHER in post_matchers
    assert "PostToolUseFailure" in hooks
    failure_matchers = {group["matcher"] for group in hooks["PostToolUseFailure"]}
    assert failure_matchers == {OPENWIKI_BEGIN_MATCHER}

    for event in ("PreToolUse", "PostToolUse", "PostToolUseFailure"):
        for group in hooks[event]:
            if group.get("matcher") != OPENWIKI_BEGIN_MATCHER:
                continue
            commands = [h["command"] for h in group["hooks"]]
            assert len(commands) == 1
            assert "openwiki-guard.sh" in commands[0]
            expected_arg = "pre" if event == "PreToolUse" else "post"
            assert commands[0].rstrip().endswith(expected_arg)


def test_generated_codex_hooks_wire_the_openwiki_guard(tmp_path: Path) -> None:
    from generate_targets import OPENWIKI_BEGIN_MATCHER, render_codex_hooks

    hooks_path = tmp_path / "hooks.json"
    render_codex_hooks(hooks_path)
    hooks = json.loads(hooks_path.read_text(encoding="utf-8"))["hooks"]

    pre_matchers = {group["matcher"] for group in hooks["PreToolUse"]}
    assert OPENWIKI_BEGIN_MATCHER in pre_matchers
    post_matchers = {group["matcher"] for group in hooks["PostToolUse"]}
    assert OPENWIKI_BEGIN_MATCHER in post_matchers
    assert "PostToolUseFailure" not in hooks, "Codex fires no failure event (spike U6)"

    stop_commands = [h["command"] for h in hooks["Stop"][0]["hooks"]]
    assert any("codex-stop.sh" in command for command in stop_commands)
    openwiki_stop_commands = [c for c in stop_commands if "openwiki-guard.sh" in c]
    assert len(openwiki_stop_commands) == 1
    assert openwiki_stop_commands[0].rstrip().endswith("post")


def test_validate_targets_accepts_the_generated_openwiki_wiring(tmp_path: Path) -> None:
    """Closes the loop: the validators this phase extends must accept
    exactly what the renderers this phase extends actually produce."""
    from generate_targets import render_claude_settings, render_codex_hooks
    from validate_targets import (
        pretool_routing_errors,
        reporting_reminder_hook_errors,
        validate_claude_lifecycle_hooks,
    )

    settings_path = tmp_path / "settings.json"
    render_claude_settings(settings_path)
    claude_hooks = json.loads(settings_path.read_text(encoding="utf-8"))["hooks"]
    assert pretool_routing_errors(claude_hooks, "claude-code") == []
    assert reporting_reminder_hook_errors(claude_hooks, "claude-code") == []
    lifecycle_errors: list[str] = []
    validate_claude_lifecycle_hooks(claude_hooks, lifecycle_errors)
    assert lifecycle_errors == []

    hooks_path = tmp_path / "hooks.json"
    render_codex_hooks(hooks_path)
    codex_hooks = json.loads(hooks_path.read_text(encoding="utf-8"))["hooks"]
    assert pretool_routing_errors(codex_hooks, "openai-codex") == []
    assert reporting_reminder_hook_errors(codex_hooks, "openai-codex") == []
