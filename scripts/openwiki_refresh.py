#!/usr/bin/env python3
"""Run one guarded, user-configured OpenWiki refresh.

``restore-root-adapters.sh`` restores canonical mirrored adapters from nested
state. This runner instead preserves the exact working-tree bytes that existed
before OpenWiki ran, including legitimate uncommitted edits, and works before
any mirror exists. They therefore protect different boundaries.
"""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


PROTECTED_ADAPTERS = (Path("AGENTS.md"), Path("CLAUDE.md"))
PROTECTED_WORKFLOW = Path(".github/workflows/openwiki-update.yml")
OPENWIKI_ARGUMENTS = ("openwiki", "code", "--update", "--print")


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


def _status_paths(root: Path) -> set[str]:
    """Return all paths represented by Git's NUL-delimited porcelain output."""
    result = _git(root, "status", "--porcelain=v1", "-z", "--untracked-files=all")
    if result.returncode != 0:
        raise RuntimeError("could not read Git working-tree status")

    records = result.stdout.split("\0")
    paths: set[str] = set()
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if len(record) < 4 or record[2] != " ":
            raise RuntimeError("Git returned malformed working-tree status")
        paths.add(record[3:])
        if record[:1] in {"R", "C"} or record[1:2] in {"R", "C"}:
            if index >= len(records) or not records[index]:
                raise RuntimeError("Git returned malformed rename status")
            paths.add(records[index])
            index += 1
    return paths


def _snapshot(root: Path, relative_path: Path) -> bytes | None:
    """Capture raw bytes, with ``None`` preserving the absence distinction."""
    path = root / relative_path
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise RuntimeError(f"protected path is not a regular file: {relative_path}")
    return path.read_bytes() if path.exists() else None


def _restore(root: Path, relative_path: Path, original: bytes | None) -> None:
    """Restore a protected adapter without touching unrelated repository paths."""
    path = root / relative_path
    if original is None:
        if path.is_symlink() or path.is_file():
            path.unlink()
        elif path.exists():
            raise RuntimeError(
                f"OpenWiki replaced protected file with directory: {relative_path}"
            )
        return
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        raise RuntimeError(
            f"OpenWiki replaced protected file with directory: {relative_path}"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(original)


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
    marker = root / "openwiki" / "INSTRUCTIONS.md"
    if not marker.is_file():
        return 0, _result("not_enabled", repository_root=str(root))

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
        before_paths = _status_paths(root)
        adapters = {path: _snapshot(root, path) for path in PROTECTED_ADAPTERS}
        workflow = _snapshot(root, PROTECTED_WORKFLOW)
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

        child_environment = os.environ.copy()
        child_environment.setdefault("OPENWIKI_TELEMETRY_DISABLED", "1")
        child_returncode: int | None = None
        cleanup_error: str | None = None
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
            try:
                for path, original in adapters.items():
                    _restore(root, path, original)
            except RuntimeError as error:
                cleanup_error = str(error)

        try:
            workflow_unchanged = _snapshot(root, PROTECTED_WORKFLOW) == workflow
        except RuntimeError as error:
            workflow_unchanged = False
            cleanup_error = cleanup_error or str(error)
        try:
            after_paths = _status_paths(root)
        except RuntimeError as error:
            return 1, _result(
                "failed",
                repository_root=str(root),
                error=str(error),
                openwiki_returncode=child_returncode,
            )
        new_paths = sorted(after_paths - before_paths)
        out_of_scope = [path for path in new_paths if not path.startswith("openwiki/")]
        if not workflow_unchanged and PROTECTED_WORKFLOW.as_posix() not in out_of_scope:
            out_of_scope.append(PROTECTED_WORKFLOW.as_posix())

        details: dict[str, object] = {
            "repository_root": str(root),
            "node_version": node_version,
            "openwiki_version": openwiki_version,
            "pre_existing_dirty_paths": sorted(before_paths),
            "new_paths": new_paths,
            "out_of_scope_paths": sorted(out_of_scope),
            "workflow_unchanged": workflow_unchanged,
            "openwiki_returncode": child_returncode,
        }
        if cleanup_error is not None:
            return 1, _result("failed", error=cleanup_error, **details)
        if child_returncode is None:
            return 1, _result(
                "failed", error="OpenWiki could not be started", **details
            )
        if child_returncode != 0:
            return 1, _result("failed", error="OpenWiki exited non-zero", **details)
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
