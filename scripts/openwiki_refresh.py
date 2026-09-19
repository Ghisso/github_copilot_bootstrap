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

Control-plane enumeration: every ``CONTROL_PLANE_PATHS`` entry is resolved
directly against the filesystem (``_control_plane_paths``), not derived from
``git ls-files --others --ignored``. Git's own directory walker silently
omits anything inside a directory literally named ``.git``, valid or not,
for *any* ignored path, not only ones that are themselves nested
repositories; a payload written into, for example, ``.agents/.git/x`` was
therefore reachable by nothing in this module at all, since ``git ls-files``
never reported it in the first place. Enumerating from disk also naturally
picks up tracked control-plane files (for example ``.github/workflows/*.yml``),
which the git-ignored-only enumeration never saw; that is deliberate double
coverage with the separate outer ``git status`` comparison, not an
oversight, and matching paths are deduplicated before they reach
``out_of_scope_paths``. A directory literally named ``.cache`` immediately
under a control-plane path (for example ``.claude/.cache``) is the one
exception: it is excluded entirely (see ``_walk_control_plane_directory``).
That exclusion is narrow and does not generalize -- a future churning
directory needs the same explicit, one-off judgement, not an automatic
exemption; see the residual limits below for why that judgement does not
extend to the rest of a control-plane path's working tree.

Nested-repository control-plane fingerprinting: a control-plane path that is
itself a Git repository (for example an installed ``.claude``) is
fingerprinted file-by-file, because Git does not recurse into it. A directory
literally named ``.git`` is trusted as a real Git directory only after it is
validated -- see ``_is_real_git_directory`` -- because a directory anyone can
create with that name is not otherwise evidence of anything; an unvalidated
one is walked in full, like any other content. Inside a validated Git
directory, only the execution-relevant surface is checked: everything under
``hooks/`` (Git executes these directly); ``config`` and ``config.worktree``
(``core.hooksPath``, ``core.fsmonitor``, and ``include.path`` can each
redirect to or run arbitrary commands, and ``config.worktree`` carries the
same settings once ``extensions.worktreeConfig`` is enabled); ``worktrees/*/
config.worktree`` (the per-worktree counterpart); and ``info/attributes`` (it
binds paths to ``filter.*``/``diff.*.textconv`` handlers whose commands come
from ``config``, so it is part of that same execution path). The same
surface is checked again, recursively, for every submodule Git directory
under ``modules/`` at any depth (``modules/<a>/modules/<b>/...`` is an
ordinary configuration, not an adversarial one); a symlinked directory is not
followed while recursing, so a symlink cycle cannot make that recursion run
away. Everything else under a Git directory -- ``objects/``, ``refs/``,
``logs/``, ``info/refs``, ``index``, ``HEAD``, ``packed-refs``,
``COMMIT_EDITMSG``, and whatever a future Git version adds -- is not
fingerprinted, so it cannot produce a false failure. This is a considered
trade, not an oversight: an earlier denylist of known-churn names missed
``COMMIT_EDITMSG``, and after that was fixed, missed ``git gc``'s
``info/refs``, in successive reviews, because the set of files Git writes on
ordinary maintenance is open-ended and grows with every release -- a check
that fails closed on routine ``git gc`` gets bypassed rather than trusted.

Residual limits of nested-repository fingerprinting, stated without
softening: a code-execution vector a future Git version adds outside the
listed allowlist will not be detected until the allowlist is revisited,
which should happen whenever the pinned Git version changes. A file inside a
*validated* Git directory that is not on the allowlist is still not
fingerprinted, which can hide arbitrary content from this check -- but that
content is inert data, not a code-execution vector, because every
code-execution vector Git itself defines is in the allowlist. A nested
repository whose ``.git`` is a file containing a ``gitdir:`` pointer to a
location outside the tracked tree -- what ``git init --separate-git-dir``
produces -- escapes this mechanism entirely: the pointer file itself is
fingerprinted like any other file, but the real Git directory it points to
is not walked at all.

Residual limit: a control-plane path that is itself a live workspace for a
concurrent agent session -- most notably this bootstrap's own ``.claude``,
which ``state-sync.sh`` commits into on every prompt, among other agent
activity -- is fingerprinted in full, deliberately. Excluding files such as
``MEMORY.md``, plans, or session logs to avoid that churn would reopen
exactly the gap this mechanism exists to close: mutations there are supposed
to "pass undetected" no more than any other control-plane mutation. The
operational consequence is real and is stated here rather than left to be
discovered: this runner must be invoked as a discrete step, not while another
agent session is actively writing to ``.claude`` in the same checkout. If
that overlap happens, the run fails closed and names files OpenWiki never
touched; nothing is damaged and nothing is committed, but the run must be
repeated once the checkout is quiet. The ``flock`` this runner takes does not
help here: it serializes this runner's own invocations against each other,
not against an unrelated agent session's writes. There is no reliable way to
tell a bootstrap write from an OpenWiki write from the outside, so this
runner does not try to guess; an honest limit is preferable to a heuristic
that would sometimes be wrong.

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
CONTROL_PLANE_PATHS = (
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


def _walk_files_and_symlinks(directory: Path) -> list[Path]:
    """List every regular file and every symlink (file or directory) below ``directory``."""
    found: list[Path] = []
    for current_directory, directories, files in os.walk(directory, followlinks=False):
        current = Path(current_directory)
        found.extend(current / name for name in files)
        found.extend(
            current / name for name in directories if (current / name).is_symlink()
        )
    return found


def _is_real_git_directory(candidate: Path) -> bool:
    """Return whether ``candidate`` has the minimal markers of a real Git directory.

    A directory literally named ``.git`` is not itself evidence of anything;
    anyone able to write into a control-plane path can ``mkdir`` one to keep
    this walk's execution-vector allowlist from ever reaching content placed
    inside it. Requiring ``HEAD`` (a regular file), ``objects`` (a
    directory), and ``refs`` (a directory) -- present in every Git directory
    Git itself creates -- turns a decoy into ordinary content that gets the
    same full walk as anything else, instead of a narrower one.
    """
    return (
        (candidate / "HEAD").is_file()
        and (candidate / "objects").is_dir()
        and (candidate / "refs").is_dir()
    )


def _git_directory_allowed_paths(git_directory: Path) -> list[Path]:
    """List the execution-relevant paths directly inside one Git directory.

    Applied both to a nested repository's own Git directory and, recursively,
    to every submodule Git directory under its ``modules/`` -- a submodule
    Git directory is a Git directory in its own right, with the same
    hooks/config/worktree surface. Matched by path relative to
    ``git_directory``, not by bare name, so a rule can target one file
    several levels deep (``info/attributes``) without touching its
    high-churn sibling at the same depth (``info/refs``). See the module
    docstring for why this is an allowlist rather than a denylist of known
    churn, and for the trade that comes with it.
    """
    allowed: list[Path] = []
    hooks = git_directory / "hooks"
    if hooks.is_dir():
        allowed.extend(_walk_files_and_symlinks(hooks))
    for name in ("config", "config.worktree"):
        candidate = git_directory / name
        if candidate.exists() or candidate.is_symlink():
            allowed.append(candidate)
    attributes = git_directory / "info" / "attributes"
    if attributes.exists() or attributes.is_symlink():
        allowed.append(attributes)
    worktrees = git_directory / "worktrees"
    if worktrees.is_dir():
        for entry in worktrees.iterdir():
            if entry.is_symlink() or not entry.is_dir():
                continue
            worktree_config = entry / "config.worktree"
            if worktree_config.exists() or worktree_config.is_symlink():
                allowed.append(worktree_config)
    return allowed


def _submodule_git_directories(modules_directory: Path) -> list[Path]:
    """List every submodule Git directory under ``modules_directory``, at any depth.

    A submodule's own ``modules/`` (``modules/<a>/modules/<b>/...``) is an
    ordinary configuration, not an adversarial one, so this recurses without
    a depth limit. A symlinked directory is skipped rather than followed, so
    a symlink cycle cannot make the recursion run away.
    """
    directories: list[Path] = []
    if modules_directory.is_symlink() or not modules_directory.is_dir():
        return directories
    for entry in modules_directory.iterdir():
        if entry.is_symlink() or not entry.is_dir():
            continue
        directories.append(entry)
        directories.extend(_submodule_git_directories(entry / "modules"))
    return directories


def _nested_git_allowed_paths(git_root: Path) -> list[Path]:
    """List the execution-relevant paths under one nested repository's ``.git``.

    Everything not covered by ``_git_directory_allowed_paths`` -- ``objects/``,
    ``refs/``, ``logs/``, ``info/refs``, pointer files, ``packed-refs``,
    ``COMMIT_EDITMSG`` -- is data, not walked, and cannot produce a false
    failure.
    """
    allowed = list(_git_directory_allowed_paths(git_root))
    for submodule_git_directory in _submodule_git_directories(git_root / "modules"):
        allowed.extend(_git_directory_allowed_paths(submodule_git_directory))
    return allowed


def _walk_control_plane_directory(root: Path, relative_directory: str) -> set[str]:
    """List files and symlinks under one control-plane directory, fully.

    A directory literally named ``.git`` is walked too, but narrowed to the
    execution-relevant surface ``_nested_git_allowed_paths`` names only after
    ``_is_real_git_directory`` validates it; an unvalidated ``.git``-named
    directory is walked in full, the same as any other content, so a decoy
    cannot hide anything. See the module docstring for the full trade-off,
    including what a validated Git directory can still hide.

    A directory literally named ``.cache`` immediately under
    ``relative_directory`` itself (not one found deeper in the tree) is
    excluded entirely, provided it really is a directory and not a symlink
    standing in for one. This is disposable cache this bootstrap owns, not
    an open-ended external surface, and it holds no code-execution vector --
    a narrow, deliberate exception, not a precedent for excluding churn in
    general. See the module docstring for the reasoning and its limits.
    """
    top = root / relative_directory
    paths: set[str] = set()
    for directory, directories, files in os.walk(top, followlinks=False):
        current = Path(directory)
        if current == top:
            cache = current / ".cache"
            if cache.is_dir() and not cache.is_symlink():
                directories[:] = [name for name in directories if name != ".cache"]
        if current.name == ".git" and _is_real_git_directory(current):
            for candidate in _nested_git_allowed_paths(current):
                paths.add(candidate.relative_to(root).as_posix())
            directories[:] = []  # Do not also generically walk .git's data.
            continue
        for name in files:
            paths.add((current / name).relative_to(root).as_posix())
        for name in directories:
            candidate = current / name
            if candidate.is_symlink():
                paths.add(candidate.relative_to(root).as_posix())
    return paths


def _control_plane_paths(root: Path) -> set[str]:
    """Return every control-plane path on disk, without reading file contents.

    Enumerated directly from the filesystem for each ``CONTROL_PLANE_PATHS``
    pattern, rather than derived from ``git ls-files --others --ignored``:
    Git's own directory walker silently omits anything inside a directory
    literally named ``.git``, valid or not, for *any* ignored path, not only
    ones that are themselves nested repositories. A payload written into,
    for example, ``.agents/.git/x`` was therefore reachable by nothing in
    this module at all -- ``git ls-files`` never reported it, so
    ``_walk_control_plane_directory``'s validation was never reached.

    Enumerating from disk also naturally includes tracked control-plane
    files (for example ``.github/workflows/*.yml``), which the prior
    ignored-only enumeration never saw. That is deliberate double coverage
    with the separate outer ``git status`` comparison, not an oversight:
    both fail closed on the same mutation, and paths are deduplicated
    before they reach ``out_of_scope_paths``.
    """
    paths: set[str] = set()
    for pattern in CONTROL_PLANE_PATHS:
        for match in root.glob(pattern):
            relative = match.relative_to(root).as_posix()
            if match.is_symlink():
                paths.add(relative)
            elif match.is_dir():
                paths.update(_walk_control_plane_directory(root, relative))
            elif match.is_file():
                paths.add(relative)
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


def _race_error(relative_path: Path) -> RuntimeError:
    """Build the standard error for a path that no longer matches its snapshot."""
    return RuntimeError(f"protected path changed outside this refresh: {relative_path}")


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
            raise _race_error(relative_path)
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
        raise _race_error(relative_path) from error
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
            raise _race_error(relative_path)
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
        raise _race_error(relative_path) from error
    try:
        write_state = os.fstat(write_fd)
        if (write_state.st_dev, write_state.st_ino) != original.identity:
            raise _race_error(relative_path)
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


def _control_plane_state(root: Path, paths: set[str]) -> dict[str, tuple[str, ...]]:
    """Fingerprint control-plane files without emitting their contents."""
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
            before_control_plane_paths = _control_plane_paths(root)
            before_control_plane_state = _control_plane_state(
                root, before_control_plane_paths
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
            after_control_plane_paths = _control_plane_paths(root)
            after_control_plane_state = _control_plane_state(
                root, after_control_plane_paths
            )
        except (OSError, RuntimeError) as error:
            return 1, _result(
                "failed",
                repository_root=str(root),
                error=f"could not compare control-plane paths: {error}",
                openwiki_returncode=child_returncode,
                **_restoration_evidence(restoration_errors, restoration_displaced),
            )
        after_paths = set(after_entries)
        new_paths = sorted(after_paths - before_paths)
        out_of_scope = [path for path in new_paths if not path.startswith("openwiki/")]
        changed_control_plane_paths = sorted(
            path
            for path, state in before_control_plane_state.items()
            if after_control_plane_state.get(path) != state
        )
        new_control_plane_paths = sorted(
            after_control_plane_paths - before_control_plane_paths
        )
        control_plane_out_of_scope = sorted(
            path
            for path in {*changed_control_plane_paths, *new_control_plane_paths}
            if not path.startswith("openwiki/")
        )
        out_of_scope.extend(
            path for path in control_plane_out_of_scope if path not in out_of_scope
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
            "control_plane_paths": control_plane_out_of_scope,
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
