#!/usr/bin/env python3
"""Run one guarded, user-configured OpenWiki refresh.

``restore-root-adapters.sh`` restores canonical mirrored adapters from nested
state. This runner instead preserves the exact working-tree bytes that existed
before OpenWiki ran, including legitimate uncommitted edits, and works before
any mirror exists. They therefore protect different boundaries.

OpenWiki rewrites a managed block in the root ``AGENTS.md``/``CLAUDE.md``
adapters on every ``code`` run with no opt-out, so restoration overwriting
them is the expected normal path here, not a failure. Editing the root
adapters by hand while a refresh runs is unsupported: the ``flock`` this
runner takes prevents a second runner invocation from running concurrently,
but it does not prevent a concurrent human edit, which restoration can only
detect and report, never silently merge.

Residual limit: this phase detects and fails closed on a write that escapes
``openwiki/`` through a symlink inside the repository working tree, but a
write that lands outside the repository entirely, such as the user's home
directory, is not detected. Process-level sandboxing (for example a mount or
user namespace) is tracked as a follow-up phase, not implemented here.
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
IGNORED_CONTROL_PLANE_PATHS = (
    ".claude",
    ".agents",
    ".codex",
    ".github",
    ".vscode",
    ".mcp.json",
    "AGENTS.md",
    "CLAUDE.md",
    ".context-mode-provenance.secret*",
)


@dataclass(frozen=True)
class FileSnapshot:
    """One protected file's pre-run bytes, or an absent-path runner sentinel.

    ``identity`` is the pre-run file's ``(st_dev, st_ino)`` when it was
    present, used at restore time to detect a same-content-different-inode
    replacement race. ``sentinel_fd`` is the still-open descriptor of a
    sentinel this runner created for an absent path; restoration authenticates
    through this descriptor, an unforgeable handle on that inode, rather than
    a path lookup, which would be racy.
    """

    contents: bytes | None
    identity: tuple[int, int] | None = None
    sentinel_fd: int | None = None


@dataclass(frozen=True)
class DisplacedContent:
    """Evidence that restoration overwrote or removed non-empty content."""

    path: str
    sha256: str
    length: int


def _git(root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run one local Git query without forwarding command output."""
    return subprocess.run(
        ["git", "-C", str(root), *arguments],
        text=True,
        capture_output=True,
        check=False,
    )


def _repository_root(start: Path) -> Path | None:
    """Return the outermost repository root that contains ``start``."""
    root: Path | None = None
    for candidate in (start.resolve(), *start.resolve().parents):
        result = _git(candidate, "rev-parse", "--show-toplevel")
        if result.returncode == 0:
            root = Path(result.stdout.strip())
    return root


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


def _walk_ignored_directory(root: Path, relative_directory: str) -> set[str]:
    """List files and symlinks under an ignored nested-repository directory.

    Git does not recurse into a nested repository (for example an installed
    ``.claude``); ``git ls-files --others --ignored`` reports the directory
    itself as one entry instead of every file inside it, which would let a
    mutation anywhere inside it pass undetected. Nested ``.git`` metadata is
    excluded from the walk: its own object/index churn is expected noise, not
    evidence of a mutated tracked file.
    """
    paths: set[str] = set()
    for directory, directories, files in os.walk(
        root / relative_directory, followlinks=False
    ):
        directories[:] = [name for name in directories if name != ".git"]
        current = Path(directory)
        for name in files:
            paths.add((current / name).relative_to(root).as_posix())
        for name in directories:
            candidate = current / name
            if candidate.is_symlink():
                paths.add(candidate.relative_to(root).as_posix())
    return paths


def _ignored_control_plane_paths(root: Path) -> set[str]:
    """Return ignored control-plane files without reading their contents."""
    result = _git(
        root,
        "ls-files",
        "--others",
        "--ignored",
        "--exclude-standard",
        "-z",
        "--",
        *IGNORED_CONTROL_PLANE_PATHS,
    )
    if result.returncode != 0:
        raise RuntimeError("could not read ignored control-plane paths")
    paths: set[str] = set()
    for entry in result.stdout.split("\0"):
        if not entry:
            continue
        if entry.endswith("/"):
            paths.update(_walk_ignored_directory(root, entry))
        else:
            paths.add(entry)
    return paths


def _snapshot(root: Path, relative_path: Path) -> FileSnapshot:
    """Capture raw bytes and inode identity while refusing symlinks."""
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
        state = os.fstat(file.fileno())
        if not stat.S_ISREG(state.st_mode):
            raise RuntimeError(f"protected path is not a regular file: {relative_path}")
        return FileSnapshot(file.read(), (state.st_dev, state.st_ino))


def _prepare_adapter(root: Path, relative_path: Path) -> FileSnapshot:
    """Snapshot one adapter, reserving an absent path with a runner sentinel.

    The sentinel's descriptor is kept open, read-write, for the whole run so
    restoration can authenticate the exact inode it created through
    ``fstat`` instead of a racy path-based identity check, and can read back
    any bytes written into it before removal, as displaced-content evidence.
    """
    snapshot = _snapshot(root, relative_path)
    if snapshot.contents is not None:
        return snapshot
    path = root / relative_path
    try:
        file_descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return _snapshot(root, relative_path)
    return FileSnapshot(None, sentinel_fd=file_descriptor)


def _restore(
    root: Path, relative_path: Path, original: FileSnapshot
) -> DisplacedContent | None:
    """Restore one protected adapter without displacing a concurrent edit blindly.

    A file present before the run is restored in place, on the same inode, so
    a concurrent reader or writer is not silently detached; it is never
    unlinked and recreated. A sentinel this runner created is removed only
    through the descriptor it kept open for the whole run and then unlinked
    relative to an open directory descriptor, avoiding a second, re-resolved
    path lookup. A path or identity that no longer matches what was
    snapshotted is left untouched and reported as a restoration error instead
    of being guessed at.
    """
    name = str(relative_path)
    no_follow = getattr(os, "O_NOFOLLOW", 0)
    directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    try:
        if original.contents is None:
            return _restore_absent(name, relative_path, original, directory_fd)
        return _restore_present(name, relative_path, original, directory_fd, no_follow)
    finally:
        os.close(directory_fd)


def _restore_absent(
    name: str, relative_path: Path, original: FileSnapshot, directory_fd: int
) -> DisplacedContent | None:
    """Remove a sentinel this runner created, authenticated by its open fd."""
    if original.sentinel_fd is None:
        return None
    try:
        sentinel_state = os.fstat(original.sentinel_fd)
        try:
            current_state = os.lstat(name, dir_fd=directory_fd)
        except FileNotFoundError:
            return None
        if not stat.S_ISREG(current_state.st_mode) or (
            current_state.st_dev,
            current_state.st_ino,
        ) != (sentinel_state.st_dev, sentinel_state.st_ino):
            raise RuntimeError(
                f"protected path changed outside this refresh: {relative_path}"
            )
        displaced = None
        if sentinel_state.st_size:
            contents = os.pread(original.sentinel_fd, sentinel_state.st_size, 0)
            if contents:
                displaced = DisplacedContent(
                    name, hashlib.sha256(contents).hexdigest(), len(contents)
                )
        os.unlink(name, dir_fd=directory_fd)
        return displaced
    finally:
        os.close(original.sentinel_fd)


def _restore_present(
    name: str,
    relative_path: Path,
    original: FileSnapshot,
    directory_fd: int,
    no_follow: int,
) -> DisplacedContent | None:
    """Restore a pre-run file in place, on the same inode, or report a race."""
    assert original.contents is not None  # caller-enforced: only called when present
    try:
        read_fd = os.open(name, os.O_RDONLY | no_follow, dir_fd=directory_fd)
    except OSError as error:
        raise RuntimeError(
            f"protected path changed outside this refresh: {relative_path}"
        ) from error
    try:
        state = os.fstat(read_fd)
        if (
            not stat.S_ISREG(state.st_mode)
            or (
                state.st_dev,
                state.st_ino,
            )
            != original.identity
        ):
            raise RuntimeError(
                f"protected path changed outside this refresh: {relative_path}"
            )
        current = os.pread(read_fd, state.st_size, 0)
    finally:
        os.close(read_fd)

    if current == original.contents:
        return None  # Nothing changed; leave the inode untouched.

    displaced = (
        DisplacedContent(name, hashlib.sha256(current).hexdigest(), len(current))
        if current
        else None
    )
    try:
        write_fd = os.open(name, os.O_WRONLY | no_follow, dir_fd=directory_fd)
    except OSError as error:
        raise RuntimeError(
            f"protected path changed outside this refresh: {relative_path}"
        ) from error
    try:
        write_state = os.fstat(write_fd)
        if (write_state.st_dev, write_state.st_ino) != original.identity:
            raise RuntimeError(
                f"protected path changed outside this refresh: {relative_path}"
            )
        os.ftruncate(write_fd, 0)
        os.write(write_fd, original.contents)
    finally:
        os.close(write_fd)
    return displaced


def _symlinks_under(directory: Path) -> list[Path]:
    """List every symlink under ``directory``, without following any of them."""
    found: list[Path] = []
    for current, directories, files in os.walk(directory, followlinks=False):
        tree_root = Path(current)
        for name in (*directories, *files):
            candidate = tree_root / name
            if candidate.is_symlink():
                found.append(candidate)
    return found


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
    if _symlinks_under(openwiki_root):
        return "openwiki must not contain symlinks"
    return None


def _openwiki_tree_violations(root: Path) -> tuple[list[str], dict[str, str]]:
    """Re-walk ``openwiki/`` after the child exits to catch a check-then-use swap.

    The pre-launch check in ``_enabled_error`` can still be raced: a symlink
    created while the child runs, or by the child itself, would otherwise let
    a write land outside ``openwiki/`` even though the earlier walk saw a
    real directory. Returns out-of-scope paths to fold into the existing
    fail-closed reporting, plus symlink targets kept only for diagnostics.
    """
    openwiki_root = root / "openwiki"
    marker = openwiki_root / "INSTRUCTIONS.md"
    if openwiki_root.is_symlink() or not openwiki_root.is_dir():
        return ["openwiki"], {}
    violations: list[str] = []
    if marker.is_symlink() or not marker.is_file():
        violations.append("openwiki/INSTRUCTIONS.md")
    symlinks = {
        path.relative_to(root).as_posix(): os.readlink(path)
        for path in _symlinks_under(openwiki_root)
    }
    violations.extend(path for path in symlinks if path not in violations)
    return violations, symlinks


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


def _ignored_control_plane_state(
    root: Path, paths: set[str]
) -> dict[str, tuple[str, ...]]:
    """Fingerprint ignored control-plane files without emitting their contents."""
    return {path: _fingerprint(root, path) for path in paths}


def _remove_prepared_sentinels(
    root: Path, adapters: dict[Path, FileSnapshot]
) -> tuple[list[str], list[DisplacedContent]]:
    """Remove only sentinels created by this runner before a launch failure."""
    errors: list[str] = []
    displaced: list[DisplacedContent] = []
    for path, snapshot in adapters.items():
        if snapshot.sentinel_fd is None:
            continue
        try:
            result = _restore(root, path, snapshot)
        except (OSError, RuntimeError) as error:
            errors.append(f"{path}: {error}")
            continue
        if result is not None:
            displaced.append(result)
    return errors, displaced


def _version(command: str, *, env: dict[str, str] | None = None) -> str | None:
    """Return a compact CLI version without exposing arbitrary command output."""
    if shutil.which(command) is None:
        return None
    try:
        result = subprocess.run(
            [command, "--version"],
            text=True,
            capture_output=True,
            env=env,
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


def _restoration_evidence(
    restoration_errors: list[str], restoration_displaced: list[DisplacedContent]
) -> dict[str, object]:
    """Return restoration evidence fields to merge into any post-child result."""
    evidence: dict[str, object] = {}
    if restoration_errors:
        evidence["restoration_errors"] = restoration_errors
    if restoration_displaced:
        evidence["restoration_displaced_content"] = [
            {"path": item.path, "sha256": item.sha256, "length": item.length}
            for item in restoration_displaced
        ]
    return evidence


def _run(root: Path) -> tuple[int, dict[str, object]]:
    """Run OpenWiki once, restoring protected files even after a child failure."""
    enabled_error = _enabled_error(root)
    if enabled_error == "not_enabled":
        return 0, _result("not_enabled", repository_root=str(root))
    if enabled_error is not None:
        return 1, _result(
            "preflight_failed", repository_root=str(root), error=enabled_error
        )

    try:
        lock_path = _git_directory(root) / "openwiki-refresh.lock"
    except RuntimeError as error:
        return 1, _result(
            "preflight_failed", repository_root=str(root), error=str(error)
        )

    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    except OSError as error:
        return 1, _result(
            "preflight_failed",
            repository_root=str(root),
            error=f"could not acquire refresh lock: {error}",
        )
    try:
        adapters: dict[Path, FileSnapshot] = {}
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 1, _result(
                "busy",
                repository_root=str(root),
                error="another OpenWiki refresh is running",
            )
        except OSError as error:
            return 1, _result(
                "preflight_failed",
                repository_root=str(root),
                error=f"could not acquire refresh lock: {error}",
            )

        # The lock is held: only now is it safe to spawn OpenWiki, including
        # for a version probe, and only with the same privacy-default
        # environment every other OpenWiki subprocess in this module uses.
        child_environment = os.environ.copy()
        child_environment.setdefault("OPENWIKI_TELEMETRY_DISABLED", "1")

        node_version = _version("node", env=child_environment)
        openwiki_version = _version("openwiki", env=child_environment)
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
            before_ignored_paths = _ignored_control_plane_paths(root)
            before_ignored_state = _ignored_control_plane_state(
                root, before_ignored_paths
            )
            for path in PROTECTED_ADAPTERS:
                adapters[path] = _prepare_adapter(root, path)
            workflow = _snapshot(root, PROTECTED_WORKFLOW)
        except (OSError, RuntimeError) as error:
            sentinel_errors, sentinel_displaced = _remove_prepared_sentinels(
                root, adapters
            )
            details: dict[str, object] = {
                "repository_root": str(root),
                "error": str(error),
                **_restoration_evidence(sentinel_errors, sentinel_displaced),
            }
            return 1, _result("preflight_failed", **details)

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
            restoration_displaced: list[DisplacedContent] = []
            for path, original in adapters.items():
                try:
                    displaced = _restore(root, path, original)
                except (OSError, RuntimeError) as error:
                    restoration_errors.append(f"{path}: {error}")
                    continue
                if displaced is not None:
                    restoration_displaced.append(displaced)

        try:
            workflow_unchanged = (
                _snapshot(root, PROTECTED_WORKFLOW).contents == workflow.contents
            )
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
                **_restoration_evidence(restoration_errors, restoration_displaced),
            )
        try:
            after_ignored_paths = _ignored_control_plane_paths(root)
            after_ignored_state = _ignored_control_plane_state(
                root, after_ignored_paths
            )
        except (OSError, RuntimeError) as error:
            return 1, _result(
                "failed",
                repository_root=str(root),
                error=f"could not compare ignored control-plane paths: {error}",
                openwiki_returncode=child_returncode,
                **_restoration_evidence(restoration_errors, restoration_displaced),
            )
        after_paths = set(after_entries)
        new_paths = sorted(after_paths - before_paths)
        out_of_scope = [path for path in new_paths if not path.startswith("openwiki/")]
        changed_ignored_paths = sorted(
            path
            for path, state in before_ignored_state.items()
            if after_ignored_state.get(path) != state
        )
        new_ignored_paths = sorted(after_ignored_paths - before_ignored_paths)
        ignored_out_of_scope = sorted(
            path
            for path in {*changed_ignored_paths, *new_ignored_paths}
            if not path.startswith("openwiki/")
        )
        out_of_scope.extend(
            path for path in ignored_out_of_scope if path not in out_of_scope
        )
        try:
            tree_violations, tree_symlinks = _openwiki_tree_violations(root)
        except OSError as error:
            return 1, _result(
                "failed",
                repository_root=str(root),
                error=f"could not verify the OpenWiki write boundary: {error}",
                openwiki_returncode=child_returncode,
                **_restoration_evidence(restoration_errors, restoration_displaced),
            )
        out_of_scope.extend(
            path for path in tree_violations if path not in out_of_scope
        )
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
                **_restoration_evidence(restoration_errors, restoration_displaced),
            )
        modified_pre_existing_paths = sorted(
            path
            for path, before_state in existing_dirty_state.items()
            if after_dirty_state.get(path) != before_state
        )
        if not workflow_unchanged and PROTECTED_WORKFLOW.as_posix() not in out_of_scope:
            out_of_scope.append(PROTECTED_WORKFLOW.as_posix())

        details = {
            "repository_root": str(root),
            "node_version": node_version,
            "openwiki_version": openwiki_version,
            "pre_existing_dirty_paths": sorted(before_paths),
            "modified_pre_existing_paths": modified_pre_existing_paths,
            "ignored_control_plane_paths": ignored_out_of_scope,
            "new_paths": new_paths,
            "out_of_scope_paths": sorted(out_of_scope),
            "workflow_unchanged": workflow_unchanged,
            "openwiki_returncode": child_returncode,
            **_restoration_evidence(restoration_errors, restoration_displaced),
        }
        if tree_symlinks:
            details["openwiki_tree_symlinks"] = tree_symlinks
        if restoration_errors:
            failure_reason = "protected-file restoration failed"
            if child_returncode not in (None, 0):
                failure_reason = (
                    "OpenWiki exited non-zero; protected-file restoration failed"
                )
            return 1, _result("failed", error=failure_reason, **details)
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
