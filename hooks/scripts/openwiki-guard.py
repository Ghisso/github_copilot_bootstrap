#!/usr/bin/env python3
"""Guard `openwiki_begin` and restore the two managed root adapters.

OpenWiki 0.5.2 is host-driven: the coding agent calls OpenWiki's MCP tools
directly, and OpenWiki's server writes `openwiki/**` plus, at exactly one
point (`openwiki_begin`), a managed `<!-- OPENWIKI:START -->...
<!-- OPENWIKI:END -->` block into root `AGENTS.md` and `CLAUDE.md`
(`repository-run.js:51`; insertion is `content.trimEnd() + "\n\n" + snippet +
"\n"`, which loses the original trailing-newline shape, so a byte-exact
restore needs a pre-snapshot rather than a generic strip). This module is
`pre` (a PreToolUse guard invoked before `openwiki_begin` runs) and `post` (a
PostToolUse/PostToolUseFailure restore invoked after it returns, on the hosts
that fire those events).

Residual limits, inherited from the retired subprocess-runner design because
they still apply to a host-driven guard: a write made outside this
repository (for example to a path escaping `root`) is invisible to any
repository-local check, this guard fingerprints only the two adapters and
`WORKFLOW`, and it does not replace `protect-files`, which governs the
agent's own file-editing tool calls independently of anything OpenWiki does.
This guard does not run OpenWiki, take locks, or write outside its own
snapshot directory.
"""

from __future__ import annotations

import base64
import json
import os
import sys

MANAGED_START = "<!-- OPENWIKI:START -->"
MANAGED_END = "<!-- OPENWIKI:END -->"
ADAPTERS = ("AGENTS.md", "CLAUDE.md")
WORKFLOW = ".github/workflows/openwiki-update.yml"
# Consumer state under .claude/, already gitignored by the nested ai-state
# repository's own .cache/ entry - never committed, never drift-compared.
SNAPSHOT_DIR_RELATIVE = os.path.join(".claude", ".cache", "openwiki-guard")
MANIFEST_NAME = "manifest.json"


def _repo_root() -> str:
    """Three directories up from this script's own installed location
    (`<repo>/.claude/hooks/scripts/openwiki-guard.py`), mirroring
    `repo_root_from_script()` in `_lib-frontmatter.sh`.

    Deliberately lexical (`os.path.normpath`), never `os.path.realpath` /
    `Path.resolve()`: the shared bash helper tracks `$PWD` logically through
    `cd`, so a symlinked `shared/hooks/scripts/` (the isolated-test-root
    pattern used throughout this hook suite) resolves to the symlink's own
    location, not the real checkout it points at. Resolving physically here
    would silently break every test built on that pattern.
    """
    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(scripts_dir, "..", "..", ".."))


def _snapshot_dir(repo_root: str) -> str:
    return os.path.join(repo_root, SNAPSHOT_DIR_RELATIVE)


def _manifest_path(repo_root: str) -> str:
    return os.path.join(_snapshot_dir(repo_root), MANIFEST_NAME)


def _read_bytes(path: str) -> bytes | None:
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except FileNotFoundError:
        return None


def _write_bytes_atomic(path: str, data: bytes) -> None:
    directory = os.path.dirname(path)
    os.makedirs(directory, exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "wb") as handle:
        handle.write(data)
    os.replace(tmp_path, path)


def _has_exactly_one_managed_block(text: str) -> bool:
    if text.count(MANAGED_START) != 1 or text.count(MANAGED_END) != 1:
        return False
    return text.index(MANAGED_START) < text.index(MANAGED_END)


def _strip_managed_block(text: str) -> tuple[str, bool]:
    """Remove the managed block and one preceding blank line. Lossy: with no
    snapshot this cannot know the true original trailing-newline shape, only
    approximate it (the insertion shape is `trimEnd() + "\n\n" + snippet +
    "\n"`, so removing one of the two newlines before the block and the one
    newline right after it undoes exactly that insertion)."""
    if not _has_exactly_one_managed_block(text):
        return text, False
    start = text.index(MANAGED_START)
    end = text.index(MANAGED_END) + len(MANAGED_END)
    before, after = text[:start], text[end:]
    if after.startswith("\n"):
        after = after[1:]
    if before.endswith("\n\n"):
        before = before[:-1]
    return before + after, True


def _deny(reason: str) -> None:
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            },
            separators=(",", ":"),
        )
    )


def _read_payload(raw: str) -> dict:
    stripped = raw.strip()
    if not stripped:
        return {}
    value = json.loads(stripped)
    if not isinstance(value, dict):
        raise ValueError("payload must be a JSON object")
    return value


# --- manifest ---------------------------------------------------------


def _load_manifest(repo_root: str) -> dict | None:
    raw = _read_bytes(_manifest_path(repo_root))
    if raw is None:
        return None
    return json.loads(raw.decode("utf-8"))


def _snapshot_entry(repo_root: str, relative_path: str) -> dict:
    content = _read_bytes(os.path.join(repo_root, relative_path))
    if content is None:
        return {"present": False}
    return {"present": True, "content_b64": base64.b64encode(content).decode("ascii")}


def _write_manifest(repo_root: str) -> None:
    manifest = {
        "version": 1,
        "adapters": {name: _snapshot_entry(repo_root, name) for name in ADAPTERS},
        "workflow": _snapshot_entry(repo_root, WORKFLOW),
    }
    _write_bytes_atomic(
        _manifest_path(repo_root),
        json.dumps(manifest, separators=(",", ":")).encode("utf-8"),
    )


def _delete_manifest(repo_root: str) -> None:
    try:
        os.remove(_manifest_path(repo_root))
    except FileNotFoundError:
        pass


# --- restore ------------------------------------------------------------


class _RestoreResult:
    def __init__(self) -> None:
        self.actions: dict[str, str] = {}
        self.mismatches: list[str] = []


def _restore_one(
    repo_root: str,
    relative_path: str,
    snapshot_entry: dict | None,
    *,
    allow_managed_block: bool,
    result: _RestoreResult,
) -> None:
    path = os.path.join(repo_root, relative_path)
    current = _read_bytes(path)
    snapshot_present = bool(snapshot_entry and snapshot_entry.get("present"))

    if not snapshot_present:
        if current is None:
            result.actions[relative_path] = "unchanged"
            return
        # The path did not exist when `pre` snapshotted it; whatever created
        # it since is not this repository's pre-existing state, so it is
        # removed outright to restore the recorded absence.
        os.remove(path)
        result.actions[relative_path] = "removed"
        return

    assert snapshot_entry is not None  # implied by snapshot_present above
    snapshot_bytes = base64.b64decode(snapshot_entry["content_b64"])
    if current == snapshot_bytes:
        result.actions[relative_path] = "unchanged"
        return
    if allow_managed_block and current is not None:
        text = current.decode("utf-8", errors="surrogateescape")
        if _has_exactly_one_managed_block(text):
            _write_bytes_atomic(path, snapshot_bytes)
            result.actions[relative_path] = "restored"
            return
    # Either the path vanished, or it changed in a way not explained by
    # exactly one OpenWiki insertion (concurrent edit, unexpected content).
    # Leave it alone rather than guess.
    result.mismatches.append(relative_path)


def _restore_from_manifest(repo_root: str, manifest: dict) -> _RestoreResult:
    result = _RestoreResult()
    for name in ADAPTERS:
        _restore_one(
            repo_root,
            name,
            manifest.get("adapters", {}).get(name),
            allow_managed_block=True,
            result=result,
        )
    _restore_one(
        repo_root,
        WORKFLOW,
        manifest.get("workflow"),
        allow_managed_block=False,
        result=result,
    )
    return result


def _marker_strip_fallback(repo_root: str) -> _RestoreResult:
    """No snapshot exists (never ran, or already cleaned up): the only
    recoverable action is stripping a well-formed managed block from each
    adapter. `WORKFLOW` is left untouched - its absent-before/present-before
    state is only ever known from a snapshot."""
    result = _RestoreResult()
    for name in ADAPTERS:
        path = os.path.join(repo_root, name)
        current = _read_bytes(path)
        if current is None:
            result.actions[name] = "unchanged"
            continue
        text = current.decode("utf-8", errors="surrogateescape")
        new_text, stripped = _strip_managed_block(text)
        if stripped:
            _write_bytes_atomic(
                path, new_text.encode("utf-8", errors="surrogateescape")
            )
            result.actions[name] = "stripped"
        else:
            result.actions[name] = "unchanged"
    return result


def _summarize(result: _RestoreResult) -> str:
    return "; ".join(
        f"{name}={action}" for name, action in sorted(result.actions.items())
    )


# --- commands -------------------------------------------------------------


def _cmd_pre(payload: dict) -> int:
    repo_root = _repo_root()
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        tool_input = {}

    if tool_input.get("mode") == "init":
        _deny(
            'openwiki-guard: mode="init" replaces the wiki and is denied; '
            'only mode="update" is allowed through this guard'
        )
        return 0

    root = tool_input.get("root")
    if not isinstance(root, str) or not root:
        _deny(
            "openwiki-guard: tool_input.root is required and must name this "
            "repository's top level"
        )
        return 0

    real_repo_root = os.path.realpath(repo_root)
    if os.path.realpath(root) != real_repo_root:
        _deny(
            "openwiki-guard: tool_input.root ({!r}) is not this repository's "
            "top level ({!r})".format(root, real_repo_root)
        )
        return 0

    instructions = os.path.join(real_repo_root, "openwiki", "INSTRUCTIONS.md")
    if not os.path.isfile(instructions):
        _deny(
            "openwiki-guard: openwiki/INSTRUCTIONS.md is missing; install "
            "OpenWiki before running openwiki_begin"
        )
        return 0

    manifest = _load_manifest(real_repo_root)
    if manifest is not None:
        heal = _restore_from_manifest(real_repo_root, manifest)
        if heal.mismatches:
            _deny(
                "openwiki-guard: a prior run left "
                + ", ".join(sorted(heal.mismatches))
                + " unresolved; run openwiki-guard.sh post to resolve before retrying"
            )
            return 0

    _write_manifest(real_repo_root)
    return 0


def _cmd_post(_payload: dict) -> int:
    # `post`'s restore reads the snapshot and the files, never the payload -
    # Claude Code and Codex disagree on `tool_response`'s shape (spike
    # finding 3), and a manual `post </dev/null` invocation has no payload
    # at all.
    repo_root = _repo_root()
    manifest = _load_manifest(repo_root)
    if manifest is None:
        result = _marker_strip_fallback(repo_root)
        print("restored_from: marker-strip; " + _summarize(result))
        return 0

    result = _restore_from_manifest(repo_root, manifest)
    if result.mismatches:
        sys.stderr.write(
            "openwiki-guard: could not restore "
            + ", ".join(sorted(result.mismatches))
            + " - left unchanged; resolve manually, then rerun "
            "openwiki-guard.sh post\n"
        )
        return 2

    _delete_manifest(repo_root)
    print("restored_from: snapshot; " + _summarize(result))
    return 0


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("pre", "post"):
        sys.stderr.write("openwiki-guard: usage: openwiki-guard.py <pre|post>\n")
        return 2
    mode = sys.argv[1]
    try:
        payload = _read_payload(sys.stdin.read())
    except ValueError as error:
        sys.stderr.write(f"openwiki-guard: unparseable payload: {error}\n")
        return 2
    if mode == "pre":
        return _cmd_pre(payload)
    return _cmd_post(payload)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception as error:  # fail closed on anything unexpected
        sys.stderr.write(f"openwiki-guard: internal error: {error}\n")
        raise SystemExit(2)
