#!/usr/bin/env python3
"""Run one guarded, user-configured OpenWiki refresh.

``restore-root-adapters.sh`` restores canonical mirrored adapters from nested
state. This runner instead preserves the exact working-tree bytes that existed
before OpenWiki ran, including legitimate uncommitted edits, and works before
any mirror exists. They therefore protect different boundaries.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path


PROTECTED_ADAPTERS = (Path("AGENTS.md"), Path("CLAUDE.md"))
PROTECTED_WORKFLOW = Path(".github/workflows/openwiki-update.yml")
OPENWIKI_ARGUMENTS = ("openwiki", "code", "--update", "--print")


@dataclass(frozen=True)
class FileSnapshot:
    """One protected file's bytes and, for runner-created sentinels, identity."""

    contents: bytes | None
    sentinel_identity: tuple[int, int] | None = None


def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run one local Git query without forwarding command output."""
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        text=True,
        capture_output=True,
        check=False,
    )


def _repository_root(start: Path) -> Path | None:
    """Return the outer repository root when ``start`` is inside one."""
    result = _git(start, "rev-parse", "--show-toplevel")
    if result.returncode != 0:
        return None
    return Path(result.stdout.strip())


def _git_directory(root: Path) -> Path:
    """Return the repository-local Git directory for the execution lock."""
    result = _git(root, "rev-parse", "--git-dir")
    if result.returncode != 0:
        raise RuntimeError("could not determine the Git directory")
    path = Path(result.stdout.strip())
    return path if path.is_absolute() else root / path


def _status_entries(root: Path) -> dict[str, str]:
    """Return NUL-delimited porcelain entries keyed by every affected path."""
    result = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    if result.returncode != 0:
        raise RuntimeError("could not read Git working-tree status")

    records = result.stdout.split("\0")
    entries: dict[str, str] = {}
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if len(record) < 4 or record[2] != " ":
            raise RuntimeError("Git returned malformed working-tree status")
        entries[record[3:]] = record[:2]
        if record[:1] in {"R", "C"} or record[1:2] in {"R", "C"}:
            if index >= len(records) or not records[index]:
                raise RuntimeError("Git returned malformed rename status")
            entries[records[index]] = record[:2]
            index += 1
    return entries


def _snapshot(root: Path, relative_path: Path) -> FileSnapshot:
    """Capture raw bytes while refusing symlinks and non-regular files."""
    path = root / relative_path
    try:
        file_descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except FileNotFoundError:
        return FileSnapshot(None)
    except OSError as error:
        raise RuntimeError(
            f"protected path is not a regular file: {relative_path}"
        ) from error
    with os.fdopen(file_descriptor, "rb") as file:
        if not stat.S_ISREG(os.fstat(file.fileno()).st_mode):
            raise RuntimeError(f"protected path is not a regular file: {relative_path}")
        return FileSnapshot(file.read())


def _prepare_adapter(root: Path, relative_path: Path) -> FileSnapshot:
    """Snapshot one adapter, reserving its absent path with a runner sentinel."""
    snapshot = _snapshot(root, relative_path)
    if snapshot.contents is not None:
        return snapshot
    path = root / relative_path
    try:
        file_descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return _snapshot(root, relative_path)
    with os.fdopen(file_descriptor, "wb"):
        pass
    state = path.stat(follow_symlinks=False)
    return FileSnapshot(None, (state.st_dev, state.st_ino))


def _restore(root: Path, relative_path: Path, original: FileSnapshot) -> None:
    """Restore a protected adapter without touching unrelated repository paths."""
    path = root / relative_path
    if original.contents is None:
        if not path.exists() and not path.is_symlink():
            return
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(
                f"protected path changed outside this refresh: {relative_path}"
            )
        state = path.stat(follow_symlinks=False)
        if original.sentinel_identity != (state.st_dev, state.st_ino):
            raise RuntimeError(
                f"protected path changed outside this refresh: {relative_path}"
            )
        if original.sentinel_identity is not None:
            path.unlink()
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        raise RuntimeError(
            f"OpenWiki replaced protected file with directory: {relative_path}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(original.contents)


def _enabled_error(root: Path) -> str | None:
    """Reject a symlinked OpenWiki tree before a child process can follow it."""
    openwiki_root = root / "openwiki"
    marker = openwiki_root / "INSTRUCTIONS.md"
    if not openwiki_root.exists() and not openwiki_root.is_symlink():
        return "not_enabled"
    if openwiki_root.is_symlink() or not openwiki_root.is_dir():
        return "openwiki must be a real directory, not a symlink"
    if not marker.exists() and not marker.is_symlink():
        return "not_enabled"
    if marker.is_symlink() or not marker.is_file():
        return "openwiki/INSTRUCTIONS.md must be a regular file"
    return None


def _fingerprint(root: Path, relative_path: str) -> tuple[str, ...]:
    """Capture one dirty path's observable state without modifying it."""
    path = root / relative_path
    try:
        state = path.lstat()
    except FileNotFoundError:
        return ("absent",)
    if stat.S_ISLNK(state.st_mode):
        return ("symlink", os.readlink(path))
    if not stat.S_ISREG(state.st_mode):
        return ("other", str(state.st_mode), str(state.st_dev), str(state.st_ino))
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return ("regular", str(state.st_mode), digest.hexdigest())


def _dirty_state(root: Path, entries: dict[str, str]) -> dict[str, tuple[str, ...]]:
    """Capture existing out-of-scope changes so OpenWiki cannot silently alter them."""
    return {
        path: (status, *_fingerprint(root, path))
        for path, status in entries.items()
        if not path.startswith("openwiki/")
    }


def _version(command: str) -> str | None:
    """Return a compact CLI version without exposing arbitrary command output."""
    if shutil.which(command) is None:
        return None
    try:
        result = subprocess.run(
            [command, "--version"],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    match = re.search(r"\b[vV]?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?\b", result.stdout)
    return match.group(0) if match else None


def _result(status: str, **details: object) -> dict[str, object]:
    """Build output that is useful for logs but excludes child output and env data."""
    return {"status": status, **details}


def _run(root: Path) -> tuple[int, dict[str, object]]:
    """Run OpenWiki once, restoring protected files even after a child failure."""
    enabled_error = _enabled_error(root)
    if enabled_error == "not_enabled":
        return 0, _result("not_enabled", repository_root=str(root))
    if enabled_error is not None:
        return 1, _result(
            "preflight_failed", repository_root=str(root), error=enabled_error
        )

    node_version = _version("node")
    openwiki_version = _version("openwiki")
    if node_version is None or openwiki_version is None:
        missing = [
            command
            for command, version in (
                ("node", node_version),
                ("openwiki", openwiki_version),
            )
            if version is None
        ]
        return 1, _result(
            "preflight_failed",
            repository_root=str(root),
            error=f"required command unavailable: {', '.join(missing)}",
        )

    try:
        lock_path = _git_directory(root) / "openwiki-refresh.lock"
    except RuntimeError as error:
        return 1, _result(
            "preflight_failed", repository_root=str(root), error=str(error)
        )

    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 1, _result(
                "busy",
                repository_root=str(root),
                error="another OpenWiki refresh is running",
            )

        enabled_error = _enabled_error(root)
        if enabled_error is not None:
            status = (
                "not_enabled" if enabled_error == "not_enabled" else "preflight_failed"
            )
            return (0 if status == "not_enabled" else 1), _result(
                status,
                repository_root=str(root),
                **({} if status == "not_enabled" else {"error": enabled_error}),
            )
        try:
            before_entries = _status_entries(root)
            before_paths = set(before_entries)
            existing_dirty_state = _dirty_state(root, before_entries)
            adapters = {
                path: _prepare_adapter(root, path) for path in PROTECTED_ADAPTERS
            }
            workflow = _snapshot(root, PROTECTED_WORKFLOW)
        except (OSError, RuntimeError) as error:
            return 1, _result(
                "preflight_failed", repository_root=str(root), error=str(error)
            )

        child_environment = os.environ.copy()
        child_environment.setdefault("OPENWIKI_TELEMETRY_DISABLED", "1")
        child_returncode: int | None = None
        try:
            try:
                child = subprocess.run(
                    list(OPENWIKI_ARGUMENTS),
                    cwd=root,
                    env=child_environment,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                child_returncode = child.returncode
            except OSError:
                child_returncode = None
        finally:
            restoration_errors: list[str] = []
            for path, original in adapters.items():
                try:
                    _restore(root, path, original)
                except (OSError, RuntimeError) as error:
                    restoration_errors.append(f"{path}: {error}")

        try:
            workflow_unchanged = _snapshot(root, PROTECTED_WORKFLOW) == workflow
        except RuntimeError:
            workflow_unchanged = False
        try:
            after_entries = _status_entries(root)
        except RuntimeError as error:
            return 1, _result(
                "failed",
                repository_root=str(root),
                error=str(error),
                openwiki_returncode=child_returncode,
            )
        after_paths = set(after_entries)
        new_paths = sorted(after_paths - before_paths)
        out_of_scope = [path for path in new_paths if not path.startswith("openwiki/")]
        try:
            after_dirty_state = _dirty_state(
                root,
                {path: after_entries.get(path, "") for path in existing_dirty_state},
            )
        except OSError as error:
            return 1, _result(
                "failed",
                repository_root=str(root),
                error=f"could not compare pre-existing changes: {error}",
                openwiki_returncode=child_returncode,
            )
        modified_pre_existing_paths = sorted(
            path
            for path, before_state in existing_dirty_state.items()
            if after_dirty_state.get(path) != before_state
        )
        if not workflow_unchanged and PROTECTED_WORKFLOW.as_posix() not in out_of_scope:
            out_of_scope.append(PROTECTED_WORKFLOW.as_posix())

        details: dict[str, object] = {
            "repository_root": str(root),
            "node_version": node_version,
            "openwiki_version": openwiki_version,
            "pre_existing_dirty_paths": sorted(before_paths),
            "modified_pre_existing_paths": modified_pre_existing_paths,
            "new_paths": new_paths,
            "out_of_scope_paths": sorted(out_of_scope),
            "workflow_unchanged": workflow_unchanged,
            "openwiki_returncode": child_returncode,
        }
        if restoration_errors:
            error = "protected-file restoration failed"
            if child_returncode not in (None, 0):
                error = "OpenWiki exited non-zero; protected-file restoration failed"
            return 1, _result(
                "failed", error=error, restoration_errors=restoration_errors, **details
            )
        if child_returncode is None:
            return 1, _result(
                "failed", error="OpenWiki could not be started", **details
            )
        if child_returncode != 0:
            return 1, _result("failed", error="OpenWiki exited non-zero", **details)
        if modified_pre_existing_paths:
            return 1, _result(
                "failed",
                error="modified pre-existing out-of-scope changes",
                **details,
            )
        if out_of_scope:
            return 1, _result("failed", error="new out-of-scope changes", **details)
        return 0, _result("success", **details)
    finally:
        os.close(lock_fd)


def parse_args() -> argparse.Namespace:
    """Parse the runner's deliberately small public interface."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--require-enabled",
        action="store_true",
        help="fail instead of returning not_enabled when OpenWiki is not configured",
    )
    return parser.parse_args()


def main() -> int:
    """Run the refresh and emit concise text plus one JSON result object."""
    args = parse_args()
    root = _repository_root(Path.cwd())
    if root is None:
        result = _result(
            "preflight_failed", error="run this command inside a Git repository"
        )
        print("openwiki-refresh: preflight failed", file=sys.stderr)
        print(json.dumps(result, sort_keys=True))
        return 1

    marker = root / "openwiki" / "INSTRUCTIONS.md"
    if not marker.is_file() and args.require_enabled:
        result = _result(
            "not_enabled",
            repository_root=str(root),
            error="OpenWiki is not enabled; create openwiki/INSTRUCTIONS.md first",
        )
        print("openwiki-refresh: OpenWiki is not enabled", file=sys.stderr)
        print(json.dumps(result, sort_keys=True))
        return 1

    returncode, result = _run(root)
    print(f"openwiki-refresh: {result['status']}", file=sys.stderr)
    print(json.dumps(result, sort_keys=True))
    return returncode


if __name__ == "__main__":
    raise SystemExit(main())
