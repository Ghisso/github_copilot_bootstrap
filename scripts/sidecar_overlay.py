"""Reconciliation planner and apply step for the consumer sidecar overlay.

The module has two parts:

* The planner (``load_desired_units`` through ``plan_sidecar_reconciliation``)
  is pure. Its only filesystem access is reading the desired content tree
  (``load_desired_units``, a deliberately narrow reader); every other
  function there is a transformation over data the caller gathers with Git:
  tracked-file lists, per-file hashes of what is on disk, and which
  untracked files are currently ignored. It decides actions; it does not
  perform them.
* The apply step (``install_sidecar`` and its helpers, from ``git_path``
  onward) is Phase C's caller: it runs the Git queries the planner needs
  (worktree, filesystem, and version preflight; tracked files; ignore
  status), calls the planner, then executes its ``PlanResult`` in the
  required write order — the exclude block, Decision 17's ignore gate
  (``run_ignore_gate``), the atomic unit/file moves, and the manifest —
  through same-directory temp-file-plus-``os.replace`` writes.

Terminology, matching the big plan
(``.claude/plans/consumer-sidecar-bootstrap-overlay.md``, "Reconciliation
rules"):

* A **unit** is one skill directory at one write root (for example
  ``.claude/skills/ponytail``) or one bridge file (for example
  ``.github/instructions/ai-bootstrap-sidecar.instructions.md``).
* A unit's **hash** is a SHA-256 digest over its files. The exact framing,
  used by both ``compute_unit_hash`` and the manifest it feeds, is: for each
  file, sorted by its POSIX path relative to the unit, hash the relative
  path (``os.fsencode``, Decision 29: byte-identical to UTF-8 for every
  legal name), a NUL byte, the file's own SHA-256 hex digest (ASCII), and a
  newline; concatenate those records in sorted order and hash the result.
  The NUL cannot appear in a POSIX relative path and the digest is a
  fixed-width hex string, so no relative path or digest can be crafted to
  collide across the framing boundary.
* A **manifest** records, per unit, its per-file hashes and its unit hash,
  plus the paths of any ``retained`` files (Decision 16, paths only: no
  decision reads a stored hash for them, since a retained file's ledger
  entry is recomputed from the live snapshot on every run).

Preflight checks the planner can decide from data alone are a symlinked unit
(or a symlinked ancestor) and manifest schema/namespace problems
(``parse_manifest`` raising ``ManifestError``). Git version, filesystem,
worktree, and ``info/exclude`` symlink checks need live Git state; they run
in ``install_sidecar`` before the planner is ever called.
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from collections.abc import Callable, Mapping, Sequence, Set as AbstractSet
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import IO, Literal

from runtime_ownership import (
    SIDECAR_BRIDGES,
    SIDECAR_DEFAULT_PROFILE,
    SIDECAR_EXCLUDE_BEGIN,
    SIDECAR_EXCLUDE_END,
    SIDECAR_FILE_UNIT_READ_ROOTS,
    SIDECAR_MANIFEST_NAME,
    SIDECAR_PRESERVED_NAME,
    SIDECAR_PROFILE_FILE_UNITS,
    SIDECAR_PROFILE_SKILLS,
    SIDECAR_PROFILE_STATE_ROOT,
    SIDECAR_PROFILES,
    SIDECAR_RETIRED_BRIDGES,
    SIDECAR_RETIRED_SKILL_WRITE_ROOTS,
    SIDECAR_SKILL_READ_ROOTS,
    SIDECAR_SKILL_WRITE_ROOTS,
    SIDECAR_SKILLS,
    SIDECAR_STAGING_NAME,
    SIDECAR_STATE_SEED_FILES,
)
from runtime_ownership import sidecar_source_violations as _shared_source_violations

# Manifest schema (big plan sidecar-workflow-profile, Decision 1): version 1
# (no ``profile`` key) parses as the ``skills`` profile; version 2 adds
# ``profile`` and is the only version ever written from here on.
KNOWN_SCHEMA_VERSIONS = (1, 2)
CURRENT_SCHEMA_VERSION = 2
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_READ_ONLY_ROOTS = tuple(
    root for root in SIDECAR_SKILL_READ_ROOTS if root not in SIDECAR_SKILL_WRITE_ROOTS
)
# Every single-file unit of every profile, plus retired ones (Decision 9):
# a bridge, rule, agent, review profile, or template all behave like the
# original two bridges (one write root, one opaque file). The two original
# bridges are also members of ``SIDECAR_PROFILE_FILE_UNITS["skills"]``, so
# this already covers them without listing them twice.
_ALL_BRIDGES: frozenset[str] = frozenset(
    unit for units in SIDECAR_PROFILE_FILE_UNITS.values() for unit in units
) | frozenset(SIDECAR_RETIRED_BRIDGES)
# Every agent read-only root (Decision 9): a client folder a team member
# could plausibly place a same-named agent in, other than the one write
# root this profile ships to (``.claude/agents``). No other file-unit kind
# has more than one folder in ``SIDECAR_FILE_UNIT_READ_ROOTS`` today, so only
# agents need this extra cross-folder precedence check.
_AGENT_WRITE_ROOT = ".claude/agents"
_AGENT_READ_ONLY_ROOTS = tuple(
    root
    for root in SIDECAR_FILE_UNIT_READ_ROOTS
    if PurePosixPath(root).name == "agents" and root != _AGENT_WRITE_ROOT
)
# The one namespaced state root every profile that has one shares (Decision
# 2, 3). A ``frozenset`` even though only one exists today, so a future
# profile's own state root needs no new plumbing here.
_ALL_STATE_ROOTS: frozenset[str] = frozenset(
    root for root in SIDECAR_PROFILE_STATE_ROOT.values() if root is not None
)
_ESCAPE_CHARS = frozenset("\\*?[")

# Every write root and bridge/file-unit-parent folder (Decision 28): the
# structural boundary and filesystem-shape preflight checks these, rather
# than every individual skill or file unit. A unit path that does not exist
# yet always resolves to one of these through the nearest-existing-ancestor
# walk, so this is equivalent for every currently required test scenario at
# a fraction of the Git calls.
# ponytail: a unit that already exists on disk as its own nested clone,
# without its write root also being one, is not covered; extend this set to
# every required unit path if that scenario needs the same abort.
_SIDECAR_STRUCTURAL_PATHS: frozenset[str] = (
    frozenset(SIDECAR_SKILL_WRITE_ROOTS)
    | frozenset(str(PurePosixPath(bridge).parent) for bridge in _ALL_BRIDGES)
    | _ALL_STATE_ROOTS
)

ActionKind = Literal[
    "install",
    "update",
    "remove",
    "adopt",
    "drop_record",
    "team_takeover_delete",
    "retain",
    "unchanged",
    "preserve",
    "seed_missing",
]
ReportCategory = Literal["SKIPPED", "RETAINED", "PRESERVED"]

# Every outcome a taken skill's unit may end up with (Decision 22). Kept as
# an allowlist, not an enumerated conversion, so a future outcome kind that
# is not covered here fails loudly (``_convert_for_taken_skill``) instead of
# silently escaping team precedence the way ``adopt`` once did (R1).
_ALLOWED_TAKEN_OUTCOMES = frozenset(
    {
        "team_owned",
        "team_takeover",
        "gitlink",
        "foreign",
        "noop",
        "drop_record",
        "remove",
        "preserve",
    }
)
# Outcome kind -> the outcome it becomes for a taken skill's unit.
_TAKEN_OUTCOME_CONVERSION = {
    "install": "noop",
    "unchanged": "remove",
    "update": "remove",
    "adopt": "remove",
    "locally_modified": "preserve",
    "unfinished": "preserve",
}


class ManifestError(ValueError):
    """The sidecar manifest is unreadable, malformed, or names an unsafe path."""


class GitCheckIgnoreError(RuntimeError):
    """``git check-ignore`` exited with a code other than 0 (something
    matched) or 1 (nothing matched) -- for example 128 for a path inside a
    submodule (Decision 37, 40) -- so its output cannot be trusted as a
    partial ignore set. The caller must abort with Git's own message rather
    than silently treating the missing paths as not ignored."""


class ExcludeMarkerError(ValueError):
    """The sidecar's own exclude-block markers are missing a partner,
    duplicated, or out of order (Decision 26; S7). Raised by
    ``_find_exclude_markers``, shared by mode detection (``sidecar_evidence``)
    and the sidecar's own preflight (``_read_exclude_block``), so both abort
    the same way before any write instead of silently erasing the person's
    own ignore lines."""


# --------------------------------------------------------------------------
# Hashing
# --------------------------------------------------------------------------


def compute_file_hash(data: bytes) -> str:
    """Return the SHA-256 hex digest of one file's bytes."""
    return hashlib.sha256(data).hexdigest()


def compute_unit_hash(files: Mapping[str, str]) -> str:
    """Return a unit's hash from its ``{relpath: sha256 hex}`` file map.

    See the module docstring for the exact framing: sorted by relpath, each
    record is ``relpath.encode("utf-8") + b"\\0" + digest.encode("ascii") +
    b"\\n"``.
    """
    hasher = hashlib.sha256()
    for relpath in sorted(files):
        # os.fsencode, not .encode("utf-8") (Decision 29): byte-identical to
        # UTF-8 for every legal name, so existing hashes are unchanged, but
        # it never raises on a relative path holding a surrogate-escaped
        # non-UTF-8 byte from a Git query decoded with os.fsdecode.
        hasher.update(os.fsencode(relpath))
        hasher.update(b"\0")
        hasher.update(files[relpath].encode("ascii"))
        hasher.update(b"\n")
    return hasher.hexdigest()


def preserved_unit_slug(unit_path: str, content_hash: str) -> str:
    """Return the one-level-deep name for a unit's preserved-copy folder or
    file (Decision 24): the unit path with ``/`` replaced by ``__``, plus
    its content hash. A repeat preserve of byte-identical content reuses the
    same destination, so a later preserve of the same bytes is detected as
    a conflict deterministically rather than by chance."""
    return f"{unit_path.replace('/', '__')}--{content_hash}"


def state_backup_slug(preserved_root: Path) -> str:
    """Return a free preserved-copy folder name for one state-folder backup
    or purge (Decision 3): ``state--<UTC timestamp>``, with ``-2``, ``-3``,
    and so on appended while that name already exists under
    ``preserved_root``. Never content-hashed like ``preserved_unit_slug``,
    since the state root is never hashed at all. The suffix keeps a backup
    and an uninstall in the same second from colliding, which would
    otherwise read as a preserve conflict and fail the uninstall."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = f"state--{timestamp}"
    counter = 1
    while (preserved_root / slug).exists() or (preserved_root / slug).is_symlink():
        counter += 1
        slug = f"state--{timestamp}-{counter}"
    return slug


# --------------------------------------------------------------------------
# Manifest schema
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ManifestUnit:
    """One recorded unit: its per-file hashes and their aggregate hash."""

    files: Mapping[str, str]
    hash: str


@dataclass(frozen=True)
class Manifest:
    """The parsed sidecar manifest (schema_version 1 or 2).

    ``retained`` holds only the paths of files kept alongside a team-taken
    unit (Decision 16); no hash is stored for them because no decision reads
    one back, and the ledger is recomputed from the live snapshot each run.
    ``profile`` (schema_version 2; Decision 1) is the sidecar profile this
    manifest was written for. A version-1 manifest has no ``profile`` key at
    all and always parses as ``SIDECAR_DEFAULT_PROFILE``; the default here
    lets every existing direct ``Manifest(...)`` construction (tests, mostly)
    keep working unchanged.
    """

    schema_version: int
    units: Mapping[str, ManifestUnit]
    retained: frozenset[str]
    profile: str = SIDECAR_DEFAULT_PROFILE


# Manifest validation accepts the current write roots and bridges plus any
# retired ones (Decision 32): a recorded unit outside the current desired set
# still goes through the normal remove row instead of failing schema
# validation the moment a bridge or write root is retired.
_ALL_SKILL_WRITE_ROOTS = SIDECAR_SKILL_WRITE_ROOTS + SIDECAR_RETIRED_SKILL_WRITE_ROOTS


def _unsafe_path_segment(segment: str) -> bool:
    """A segment gitignore can technically store but that names nothing a
    person could sensibly see or use: a control character (``\\n``,
    ``\\r``, ``\\x00``), or one made only of spaces (N14 NIT)."""
    return (
        "\n" in segment
        or "\r" in segment
        or "\x00" in segment
        or (segment != "" and segment.strip(" ") == "")
    )


def _validate_unit_path(unit_path: str) -> None:
    pure = PurePosixPath(unit_path)
    if not unit_path or "\\" in unit_path or pure.is_absolute() or ".." in pure.parts:
        raise ManifestError(f"unsafe unit path: {unit_path!r}")
    if any(_unsafe_path_segment(segment) for segment in unit_path.split("/")):
        raise ManifestError(f"unsafe unit path: {unit_path!r}")
    if unit_path in _ALL_BRIDGES or unit_path in _ALL_STATE_ROOTS:
        # A state root is a unit too (Decision 3): its exclude line is the
        # sidecar's own, so a rerun recognizes it instead of keeping it as a
        # person's line and appending another.
        return
    for write_root in _ALL_SKILL_WRITE_ROOTS:
        prefix = f"{write_root}/"
        if unit_path.startswith(prefix):
            remainder = unit_path[len(prefix) :]
            if remainder and "/" not in remainder and remainder not in (".", ".."):
                return
    raise ManifestError(f"unit path outside the sidecar namespace: {unit_path!r}")


def _validate_retained_path(path: str) -> None:
    """A retained path is a person's own file name, so unlike a unit path
    (fixed ASCII) it may hold a backslash: ``escape_exact_path`` and
    ``unescape_exact_path`` round-trip it, and ``_team_takeover`` retains
    any name gitignore can express (N6). ``PurePosixPath`` silently drops a
    ``.`` segment instead of keeping it in ``.parts``, so that check runs on
    ``path.split("/")`` directly (NIT: such a line made ``required_snapshot_units``
    walk a whole write root as one unit)."""
    pure = PurePosixPath(path)
    if not path or pure.is_absolute() or ".." in pure.parts or "." in path.split("/"):
        raise ManifestError(f"unsafe retained path: {path!r}")
    for write_root in _ALL_SKILL_WRITE_ROOTS:
        prefix = f"{write_root}/"
        if path.startswith(prefix):
            remainder = path[len(prefix) :].split("/", 1)
            if len(remainder) == 2 and remainder[0] and remainder[1]:
                return
    raise ManifestError(f"retained path outside a sidecar unit: {path!r}")


def _owning_unit(path: str) -> str | None:
    """Return the skill unit path that contains a retained file, if any."""
    for write_root in _ALL_SKILL_WRITE_ROOTS:
        prefix = f"{write_root}/"
        if path.startswith(prefix):
            skill = path[len(prefix) :].split("/", 1)[0]
            return f"{write_root}/{skill}"
    return None


def _under_a_gitlink_child(relpath: str, gitlink_children: AbstractSet[str]) -> bool:
    """Return whether a unit-relative path sits at or under one of the
    unit's own gitlink children (Decision 37): nothing at or under any
    gitlink index entry, anywhere in the index, keeps a file line -- not
    only when the unit itself is the gitlink."""
    return relpath in gitlink_children or any(
        relpath.startswith(f"{child}/") for child in gitlink_children
    )


def _parse_manifest_unit(unit_path: str, record: object) -> ManifestUnit:
    if not isinstance(record, dict):
        raise ManifestError(f"unit record must be an object: {unit_path!r}")
    files_raw = record.get("files")
    if not isinstance(files_raw, dict) or not files_raw:
        raise ManifestError(f"unit record is missing per-file hashes: {unit_path!r}")
    files: dict[str, str] = {}
    for relpath, digest in files_raw.items():
        if not isinstance(relpath, str) or not isinstance(digest, str):
            raise ManifestError(f"unit file entries must be strings: {unit_path!r}")
        rel_pure = PurePosixPath(relpath)
        if not relpath or rel_pure.is_absolute() or ".." in rel_pure.parts:
            raise ManifestError(f"unsafe file path in unit {unit_path!r}: {relpath!r}")
        if not _HEX64.match(digest):
            raise ManifestError(f"file hash is not sha256 hex: {unit_path!r}/{relpath}")
        files[relpath] = digest
    unit_hash = record.get("hash")
    if not isinstance(unit_hash, str) or not _HEX64.match(unit_hash):
        raise ManifestError(f"unit hash is not sha256 hex: {unit_path!r}")
    return ManifestUnit(files=files, hash=unit_hash)


def parse_manifest(text: str) -> Manifest:
    """Parse and schema-validate the sidecar manifest.

    Raises ``ManifestError`` on invalid JSON, a schema violation, an unknown
    ``schema_version``, or any path outside the sidecar namespace (an
    absolute path, a ``..`` component, a unit path that is not
    ``<write root>/<one safe segment>`` or a fixed bridge path, or a
    ``retained`` path that is not a file nested inside one of those units).
    ``retained`` is a JSON array of paths; it carries no hash.

    Schema version (Decision 1): version 1 must carry no ``profile`` key at
    all and always parses as ``SIDECAR_DEFAULT_PROFILE`` ("skills"); version
    2 must carry a ``profile`` key naming one of ``SIDECAR_PROFILES``. Either
    way the caller always writes version 2 back out on its next real run
    (``plan_sidecar_reconciliation`` always builds ``CURRENT_SCHEMA_VERSION``),
    so an old manifest upgrades in place with no unit change.
    """
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ManifestError(f"invalid JSON: {exc}") from exc
    if not isinstance(raw, dict):
        raise ManifestError("manifest must be a JSON object")

    schema_version = raw.get("schema_version")
    if not isinstance(schema_version, int) or isinstance(schema_version, bool):
        raise ManifestError("manifest is missing an integer schema_version")
    if schema_version not in KNOWN_SCHEMA_VERSIONS:
        raise ManifestError(f"unknown schema_version: {schema_version!r}")

    profile_raw = raw.get("profile")
    if schema_version == 1:
        if profile_raw is not None:
            raise ManifestError("schema_version 1 must not carry a profile")
        profile = SIDECAR_DEFAULT_PROFILE
    else:
        if not isinstance(profile_raw, str) or profile_raw not in SIDECAR_PROFILES:
            raise ManifestError(f"unknown or missing profile: {profile_raw!r}")
        profile = profile_raw

    # bootstrap_commit (Decision 33, R6): no longer written, but an old
    # manifest that still carries it must keep parsing; the key is simply
    # ignored on read.

    units_raw = raw.get("units", {})
    if not isinstance(units_raw, dict):
        raise ManifestError("units must be an object")
    units: dict[str, ManifestUnit] = {}
    for unit_path, record in units_raw.items():
        if not isinstance(unit_path, str):
            raise ManifestError("unit paths must be strings")
        _validate_unit_path(unit_path)
        units[unit_path] = _parse_manifest_unit(unit_path, record)

    retained_raw = raw.get("retained", [])
    if not isinstance(retained_raw, list):
        raise ManifestError("retained must be an array of paths")
    retained: set[str] = set()
    for path in retained_raw:
        if not isinstance(path, str):
            raise ManifestError("retained entries must be strings")
        _validate_retained_path(path)
        retained.add(path)

    return Manifest(
        schema_version=schema_version,
        units=units,
        retained=frozenset(retained),
        profile=profile,
    )


def serialize_manifest(manifest: Manifest) -> bytes:
    """Render the manifest deterministically: sorted keys, trailing newline.

    An unchanged ``Manifest`` always re-serializes to identical bytes, so the
    caller can skip the write when nothing changed. Fails closed: every
    retained path must pass the same rule ``parse_manifest`` enforces, so a
    run can never write a manifest the next run refuses (N6). A
    ``schema_version`` 1 manifest never carries a ``profile`` key, matching
    what ``parse_manifest`` requires of one (Decision 1); every profile this
    module actually writes uses ``CURRENT_SCHEMA_VERSION`` (2), so this only
    matters for a manifest a test built by hand.
    """
    for path in manifest.retained:
        _validate_retained_path(path)
    payload: dict[str, object] = {
        "schema_version": manifest.schema_version,
        "units": {
            unit_path: {"files": dict(record.files), "hash": record.hash}
            for unit_path, record in manifest.units.items()
        },
        "retained": sorted(manifest.retained),
    }
    if manifest.schema_version != 1:
        if manifest.profile not in SIDECAR_PROFILES:
            raise ManifestError(f"unknown sidecar profile: {manifest.profile!r}")
        payload["profile"] = manifest.profile
    return (json.dumps(payload, sort_keys=True, indent=2) + "\n").encode("utf-8")


# --------------------------------------------------------------------------
# Desired content (read-only reader)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class DesiredUnit:
    """The content a unit should have, read from a generated source tree."""

    files: Mapping[str, str]
    hash: str


def _hash_tree(root: Path) -> dict[str, str]:
    return {
        file_path.relative_to(root).as_posix(): compute_file_hash(
            file_path.read_bytes()
        )
        for file_path in sorted(root.rglob("*"))
        if file_path.is_file()
    }


def load_desired_units(
    source_root: Path, profile: str = SIDECAR_DEFAULT_PROFILE
) -> dict[str, DesiredUnit]:
    """Read the desired sidecar units from a generated tree
    (``dist/sidecar/<profile>/``) for ``profile`` (Decision 1, 9, 2).

    This is the one allowed reader: it only reads files under ``source_root``
    and turns them into data. It never writes anything. Reads
    ``SIDECAR_SKILLS``/``SIDECAR_BRIDGES`` fresh for the ``skills`` profile
    (matching ``sidecar_source_exact_allowlist``'s own reasoning), so a test
    that monkeypatches those keeps seeing a matching desired set even though
    ``SIDECAR_PROFILE_SKILLS["skills"]``/``SIDECAR_PROFILE_FILE_UNITS["skills"]``
    were already built from the real values at import time. When ``profile``
    has a state root (Decision 2), its seed files are read the same way and
    returned as one more unit, keyed by the state root itself; the state
    unit never plays by the ordinary install/update/remove rules (see
    ``_classify_state_unit``), so its hash here is otherwise unused.
    """
    if profile not in SIDECAR_PROFILES:
        raise ValueError(f"unknown sidecar profile: {profile!r}")
    skills = SIDECAR_SKILLS if profile == "skills" else SIDECAR_PROFILE_SKILLS[profile]
    file_units = (
        tuple(SIDECAR_BRIDGES)
        if profile == "skills"
        else SIDECAR_PROFILE_FILE_UNITS[profile]
    )
    units: dict[str, DesiredUnit] = {}
    for write_root in SIDECAR_SKILL_WRITE_ROOTS:
        for skill in skills:
            skill_dir = source_root / write_root / skill
            if not skill_dir.is_dir():
                continue
            files = _hash_tree(skill_dir)
            if files:
                units[f"{write_root}/{skill}"] = DesiredUnit(
                    files=files, hash=compute_unit_hash(files)
                )
    for file_unit_path in file_units:
        file_path = source_root / file_unit_path
        if file_path.is_file():
            files = {
                PurePosixPath(file_unit_path).name: compute_file_hash(
                    file_path.read_bytes()
                )
            }
            units[file_unit_path] = DesiredUnit(
                files=files, hash=compute_unit_hash(files)
            )
    state_root = SIDECAR_PROFILE_STATE_ROOT[profile]
    if state_root is not None:
        seed_files = {
            seed: compute_file_hash((source_root / state_root / seed).read_bytes())
            for seed in SIDECAR_STATE_SEED_FILES
            if (source_root / state_root / seed).is_file()
        }
        if seed_files:
            units[state_root] = DesiredUnit(
                files=seed_files, hash=compute_unit_hash(seed_files)
            )
    return units


# --------------------------------------------------------------------------
# Snapshot (caller-gathered Git facts) and output data shapes
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class UnitSnapshot:
    """What the caller found on disk and in Git for one unit.

    ``tracked_files`` is every Git index path at or under the unit
    (Decision 25), relative to the unit itself (the file's own name for a
    bridge; the sentinel ``""`` when the unit path itself is a non-directory
    index entry such as a gitlink or a tracked symlink), whether or not it
    currently exists on disk. It therefore is not a subset of
    ``file_hashes``: a deleted tracked file stays in ``tracked_files`` but
    never appears in ``file_hashes``. ``file_hashes`` covers every regular
    file present at the unit path on disk, relative to the unit itself
    (tracked and untracked alike), excluding anything at or under a gitlink
    index entry or a nested ``.git`` entry (Decision 37). ``symlinked`` means
    an ancestor directory of the unit is a symlink (always an abort); a
    symlink at the unit path itself is not ancestor-symlinked and is instead
    classified as team-owned (tracked) or foreign (untracked). ``is_gitlink``
    means the unit path itself is a gitlink index entry (mode ``160000``): a
    submodule the sidecar never touches (Decision 37), regardless of
    ``tracked_files``' sentinel shape, which a tracked symlink shares.
    ``nested_repo_relpath`` is the unit-relative path of the first ``.git``
    entry found at any depth whose parent folder is not itself a gitlink --
    a disk-only nested repository (Decision 37) -- or ``None``. ``incomplete``
    means the unit holds a symlink, named pipe, socket, device, empty
    subfolder, or unreadable subfolder (Decision 38): it never matches its
    record or the desired content. ``kind`` is the unit path's own
    filesystem shape: ``"folder"`` (or absent), ``"symlink"``, or ``"other"``
    (Decision 40's gate spelling). ``gitlink_child_relpaths`` is every
    immediate gitlink found inside the unit (unit-relative), used to
    recognize a stale retained or listed path that now falls under one
    (Decision 37): such a path is dropped and reported as now visible, even
    while the unit itself keeps some other outcome this run. ``ignored_files``
    is a relative-path subset of ``file_hashes``.
    """

    exists: bool = False
    symlinked: bool = False
    tracked_files: frozenset[str] = frozenset()
    file_hashes: Mapping[str, str] = field(default_factory=dict)
    ignored_files: frozenset[str] = frozenset()
    symlink_relpaths: frozenset[str] = frozenset()
    is_gitlink: bool = False
    nested_repo_relpath: str | None = None
    incomplete: bool = False
    kind: Literal["folder", "symlink", "other"] = "folder"
    gitlink_child_relpaths: frozenset[str] = frozenset()

    @property
    def untracked_files(self) -> frozenset[str]:
        return frozenset(self.file_hashes) - self.tracked_files

    @property
    def untracked_symlinks(self) -> frozenset[str]:
        """Untracked symlinks found inside the unit (Decision 38): they carry
        no hash, so they are handled separately from ``untracked_files``, the
        same way ``_team_takeover`` treats an untracked file that matches
        nothing -- retained with its own line when ignored, left alone when
        visible, never deleted."""
        return frozenset(self.symlink_relpaths) - self.tracked_files


@dataclass(frozen=True)
class Action:
    """One planned operation. ``path`` is set only for file-level actions."""

    kind: ActionKind
    unit: str
    path: str | None = None


@dataclass(frozen=True)
class Report:
    """One ``SKIPPED``/``RETAINED`` line with its remedy."""

    category: ReportCategory
    path: str
    remedy: str


@dataclass(frozen=True)
class Abort:
    """A preflight abort the planner decided from data alone."""

    reason: str
    message: str


@dataclass(frozen=True)
class PlanResult:
    """Everything the caller needs to apply a run, or why it must not."""

    aborts: tuple[Abort, ...] = ()
    actions: tuple[Action, ...] = ()
    reports: tuple[Report, ...] = ()
    next_manifest: Manifest | None = None
    exclude_lines_write: tuple[str, ...] = ()
    exclude_lines_final: tuple[str, ...] = ()
    gate_paths_write: tuple[str, ...] = ()
    """Decision 40: every path (gate-spelled) the write-phase block lists --
    unfinished and locally modified units, retained files, and takeover
    deletions included, unrecognized lines never included. Install and
    update gate exactly this set."""
    gate_paths_final: tuple[str, ...] = ()
    """Decision 40: every path (gate-spelled) the final block keeps. Used by
    uninstall, which gates only the paths whose lines survive (Decision 39)."""
    kept_conflicts: frozenset[str] = frozenset()
    """Decision 39: the taken units this run actually kept in place because
    their preserve destination already exists -- a strict subset of the
    caller's own, deliberately over-broad ``preserved_conflicts`` input.
    Uninstall's exit code and kept manifest depend only on this set, never
    on the raw input (O3)."""


def required_snapshot_units(
    desired_units: Mapping[str, DesiredUnit],
    manifest: Manifest | None,
    excluded_units: AbstractSet[str] = frozenset(),
    listed_files: AbstractSet[str] = frozenset(),
) -> frozenset[str]:
    """Return every unit path the caller must snapshot for this run.

    This is the union of the desired units, the manifest's recorded units,
    the owning unit of every ``retained`` file, the owning unit of every
    file-level line the sidecar's own exclude block lists (``listed_files``,
    Decision 23 and 43: a listed retained file can outlive both its unit's
    manifest record and the manifest itself), and every unit the block lists
    at the unit level (``excluded_units``, Decision 23), so a skill dropped
    from the profile or a unit whose record was already dropped by a team
    takeover -- or a unit whose record was lost with the manifest -- is
    still classified and cleaned up correctly instead of silently un-hidden.

    Every state root (Decision 2, 3) is always included too, regardless of
    ``desired_units`` or the manifest: a run in the ``skills`` profile, or an
    uninstall, must still see a state folder a previous ``workflow`` install
    left behind, so it can keep it hidden instead of silently un-hiding it.
    """
    units: set[str] = set(desired_units) | set(excluded_units) | set(_ALL_STATE_ROOTS)
    if manifest is not None:
        units.update(manifest.units)
        for path in manifest.retained:
            owner = _owning_unit(path)
            if owner is not None:
                units.add(owner)
    for path in listed_files:
        owner = _owning_unit(path)
        if owner is not None:
            units.add(owner)
    return frozenset(units)


# --------------------------------------------------------------------------
# Exclude-line rendering (Decision 17)
# --------------------------------------------------------------------------


def escape_ignore_segment(segment: str) -> str:
    """Escape one path segment so ``git check-ignore`` matches it literally.

    Backslash-escapes the gitignore glob metacharacters (``\\``, ``*``,
    ``?``, ``[``) wherever they occur, escapes a leading ``!`` or ``#``
    (which would otherwise start a negation or comment line), and escapes
    every trailing literal space (otherwise stripped by gitignore's parser).
    Non-ASCII text is left as raw UTF-8; git matches it literally.
    """
    escaped = "".join(f"\\{ch}" if ch in _ESCAPE_CHARS else ch for ch in segment)
    if escaped[:1] in ("!", "#"):
        escaped = f"\\{escaped}"
    trimmed = escaped.rstrip(" ")
    trailing = len(escaped) - len(trimmed)
    if trailing:
        escaped = trimmed + "\\ " * trailing
    return escaped


def escape_exact_path(relative_path: str) -> str:
    """Render an anchored, escaped exact-match gitignore line for one path."""
    segments = relative_path.split("/")
    return "/" + "/".join(escape_ignore_segment(segment) for segment in segments)


def unit_exclude_line(unit_path: str) -> str:
    """Render the anchored exclude line for one unit (no trailing slash)."""
    return escape_exact_path(unit_path)


def unescape_ignore_segment(segment: str) -> str:
    """Best-effort inverse of ``escape_ignore_segment``.

    Drops each backslash that escapes the following character. Not a full
    gitignore parser: the caller (``unescape_exact_path``) always re-escapes
    the result and keeps it only when that round-trips to the original line
    exactly, so a many-to-one escaping can never be trusted silently.
    """
    result: list[str] = []
    index = 0
    while index < len(segment):
        char = segment[index]
        if char == "\\" and index + 1 < len(segment):
            result.append(segment[index + 1])
            index += 2
        else:
            result.append(char)
            index += 1
    return "".join(result)


def unescape_exact_path(line: str) -> str | None:
    """Best-effort inverse of ``escape_exact_path`` (Decision 23).

    Returns ``None`` when ``line`` is not shaped like an anchored exact-path
    line (it must start with ``/``). A path can never legally contain ``/``,
    so splitting the unescaped line on ``/`` always finds the true segment
    boundaries. The caller must re-escape the result and keep it only when
    it matches ``line`` byte for byte.
    """
    if not line.startswith("/"):
        return None
    segments = line[1:].split("/")
    return "/".join(unescape_ignore_segment(segment) for segment in segments)


@dataclass(frozen=True)
class ExcludeBlockContents:
    """The sidecar's own exclude block, parsed into its three kinds of line
    (Decision 23)."""

    listed_units: frozenset[str] = frozenset()
    listed_files: frozenset[str] = frozenset()
    unrecognized_lines: tuple[str, ...] = ()
    has_block: bool = False
    """Whether a balanced BEGIN/END pair is present at all -- true even for
    an entirely empty block, or one that holds only unrecognized lines.
    ``listed_units``/``listed_files``/``unrecognized_lines`` being all empty
    cannot tell "no block" apart from "an empty block"; this field can
    (Decision 34, S18: uninstall's own "is a sidecar present" definition)."""


def _split_exclude_text(text: str, *, keepends: bool = False) -> list[str]:
    """Split exclude-file text into lines the way Git reads ``info/exclude``:
    only ``\\n`` ends a line (Decision 42; O5). ``str.splitlines()`` also
    breaks on ``\\f``, ``\\v``, ``\\x1c``-``\\x1e``, U+0085, U+2028, and
    U+2029, none of which Git treats as a line boundary; splitting on one of
    those inside an escaped retained-file line turns one pattern into two,
    and the extra, unanchored one can hide unrelated team files (O5).

    With ``keepends=False`` (the default), a lone trailing carriage return is
    also stripped from each line, matching Git's own CRLF tolerance, so a
    caller can compare a line to known content. With ``keepends=True`` every
    original byte -- including any carriage return -- is kept, and each line
    but a genuinely final, terminator-less one keeps its own trailing
    ``\\n``, so a caller rebuilding the file around the sidecar's own block
    stays byte-for-byte faithful outside it.
    """
    if not keepends:
        return [line[:-1] if line.endswith("\r") else line for line in text.split("\n")]
    if text == "":
        return []
    parts = text.split("\n")
    lines = [f"{part}\n" for part in parts[:-1]]
    if parts[-1]:
        lines.append(parts[-1])
    return lines


def parse_exclude_block(text: str) -> ExcludeBlockContents:
    """Parse the sidecar's own exclude block into unit lines, file lines,
    and everything else.

    A unit line is one whose unescaped path passes ``_validate_unit_path``
    (current plus retired roots and bridges) and re-escapes to the same
    line; this also finds a listed unit for a skill that no longer ships. A
    file line is one whose unescaped path passes ``_validate_retained_path``
    and re-escapes to the same line. Any other line is kept and reported
    once, so a run never un-hides a file through a line it does not
    understand. Raises ``ExcludeMarkerError`` when the markers are
    unbalanced or repeated (Decision 26).
    """
    lines = _split_exclude_text(text)
    markers = _find_exclude_markers(lines)
    if markers is None:
        return ExcludeBlockContents()
    begin, end = markers
    listed_units: set[str] = set()
    listed_files: set[str] = set()
    unrecognized: list[str] = []
    for line in lines[begin + 1 : end]:
        path = unescape_exact_path(line)
        if path is not None and escape_exact_path(path) == line:
            try:
                _validate_unit_path(path)
            except ManifestError:
                pass
            else:
                listed_units.add(path)
                continue
            try:
                _validate_retained_path(path)
            except ManifestError:
                pass
            else:
                listed_files.add(path)
                continue
        unrecognized.append(line)
    return ExcludeBlockContents(
        listed_units=frozenset(listed_units),
        listed_files=frozenset(listed_files),
        unrecognized_lines=tuple(unrecognized),
        has_block=True,
    )


# --------------------------------------------------------------------------
# Remedies (exact wording from the big plan)
# --------------------------------------------------------------------------


def _skill_write_root_name(unit_path: str) -> str | None:
    """Return the skill name for a unit path under a skill write root, or
    ``None`` for anything else (a bridge, a new-profile file unit, or the
    state root). The skill-only half of ``_unit_name``: use this, not
    ``_unit_name``, wherever the caller means "is this a skill" rather than
    "what do I call this unit in a remedy" -- a file unit's own stem must
    never be treated as a skill name by the skill-precedence machinery."""
    for write_root in _ALL_SKILL_WRITE_ROOTS:
        prefix = f"{write_root}/"
        if unit_path.startswith(prefix):
            return unit_path[len(prefix) :]
    return None


def _unit_name(unit_path: str) -> str | None:
    """Return the unit's own display name: the skill name for a skill unit,
    or the file stem for a new-profile single-file unit (an agent, rule,
    review profile, or template; Decision 9). Returns ``None`` for the two
    original skills-profile bridges, preserving their own "does not install
    this bridge" wording exactly (they never had a bare name before), and
    for the state root, which has no comparable name at all -- in practice
    neither ever reaches a remedy that reads this, since a tracked or
    gitlinked state root aborts before classification (Decision 3) and the
    two bridges' own callers already branch on ``None`` first."""
    skill = _skill_write_root_name(unit_path)
    if skill is not None:
        return skill
    if unit_path in SIDECAR_BRIDGES or unit_path in _ALL_STATE_ROOTS:
        return None
    if unit_path in _ALL_BRIDGES:
        # The part before the first dot, not ``.stem``: the Copilot
        # instructions unit carries two suffixes
        # (``ai-bootstrap-workflow.instructions.md``) and its name is
        # ``ai-bootstrap-workflow``.
        return _entry_id(PurePosixPath(unit_path).name)
    return None


def _entry_id(entry_name: str) -> str:
    """Return the identity a client-folder entry carries: its name up to the
    first dot. One agent is ``reviewer.md`` for Claude Code,
    ``reviewer.agent.md`` for Copilot, ``reviewer.toml`` for Codex, and the
    folder ``reviewer/`` for Google Antigravity (Decision 9: a team file of
    the same name in any agent folder takes the sidecar's unit, whatever
    that client's own file shape is)."""
    return entry_name.partition(".")[0]


def _same(name: str) -> str:
    """The identity key: a skill folder's name is its own identity."""
    return name


# Unit-path parent folder name -> the word a remedy names it by (Decision 9's
# new single-file kinds and the state root). Never applied to a skill or to
# the two original bridges (``_unit_kind_word`` returns ``None`` for both),
# so their wording never changes.
_UNIT_KIND_WORDS: dict[str, str] = {
    "agents": "agent",
    "rules": "rule",
    "instructions": "instructions",
    "review-profiles": "review profile",
    "templates": "template",
}


def _unit_kind_word(unit_path: str) -> str | None:
    """Return the display word for ``unit_path``'s kind, or ``None`` for a
    skill unit and the two original bridges (Decision 9; the small plan's
    step 7: reports name the unit kind for every new single-file kind and
    the state root)."""
    if unit_path in _ALL_STATE_ROOTS:
        return "state"
    if unit_path in SIDECAR_BRIDGES:
        return None
    if unit_path in _ALL_BRIDGES:
        return _UNIT_KIND_WORDS.get(PurePosixPath(unit_path).parent.name)
    return None


def _named(name: str, kind_word: str | None) -> str:
    """Format one unit's display name for a remedy: backticked alone for a
    skill or an original bridge, or prefixed with its kind word for one of
    Decision 9's new single-file kinds or the state root."""
    return f"the {kind_word} `{name}`" if kind_word else f"`{name}`"


def _representative_tracked_path(
    unit_path: str, tracked_relpaths: AbstractSet[str]
) -> str:
    """Return the specific tracked path to name in a report: the unit path
    itself when the unit path is the tracked entry (a bridge, or a gitlink
    with no folder), otherwise the first tracked file inside it (S15: naming
    the whole folder is wrong when only one file inside is tracked)."""
    if not tracked_relpaths or "" in tracked_relpaths or unit_path in _ALL_BRIDGES:
        return unit_path
    return f"{unit_path}/{sorted(tracked_relpaths)[0]}"


def _team_owned_remedy(
    unit_path: str,
    tracked_relpaths: AbstractSet[str] = frozenset(),
    *,
    uninstall: bool = False,
) -> str:
    name = _unit_name(unit_path)
    tracked_path = _representative_tracked_path(unit_path, tracked_relpaths)
    if name is None:
        return f"the repository tracks `{tracked_path}`; the sidecar does not install this bridge"
    display = _named(name, _unit_kind_word(unit_path))
    if uninstall:
        # NIT (step 12f): "skips at every root" describes install/update
        # placement; uninstall has nothing left to place, so it just leaves
        # the team's own path alone.
        return f"the repository tracks `{tracked_path}`; the sidecar leaves {display} alone"
    return f"the repository tracks `{tracked_path}`; the sidecar skips {display} at every root"


def _gitlink_remedy(unit_path: str, *, uninstall: bool = False) -> str:
    """Decision 37: a unit that is itself a gitlink is team-owned, but the
    wording must say plainly that the sidecar never looks inside a
    submodule -- the ordinary team-owned wording implies the sidecar checked
    the tracked content, which it deliberately never does here."""
    name = _unit_name(unit_path)
    if name is None:
        return (
            f"`{unit_path}` is a submodule; the sidecar never touches files "
            "inside a submodule and does not install this bridge"
        )
    display = _named(name, _unit_kind_word(unit_path))
    if uninstall:
        # NIT (step 12f): uninstall has nothing left to place at any root.
        return (
            f"`{unit_path}` is a submodule; the sidecar never touches files "
            f"inside a submodule and leaves {display} alone"
        )
    return (
        f"`{unit_path}` is a submodule; the sidecar never touches files "
        f"inside a submodule and skips {display} at every root"
    )


def _read_only_taken_remedy(path: str, name: str, kind_word: str | None = None) -> str:
    display = _named(name, kind_word)
    return f"the repository has `{path}`; the sidecar skips {display} at every root"


def _read_only_taken_conflict_remedy(
    path: str, name: str, kind_word: str | None = None
) -> str:
    """Decision 44/O12: while a preserve conflict keeps one of the unit's
    own edited copies in place, this taking path is reported as keeping it
    until that conflict is resolved, never as skipping it everywhere -- the
    copy the conflict kept is still there."""
    display = _named(name, kind_word)
    return (
        f"the repository has `{path}`; {display} is kept in place until its "
        "edited-copy conflict is resolved, not skipped at every root"
    )


def _locally_modified_remedy(path: str, *, skill_still_shipped: bool) -> str:
    if skill_still_shipped:
        return (
            f"`{path}` has local edits, so the sidecar keeps it. A pull can "
            "overwrite hidden files without warning. To take the current "
            f"version, copy your edits elsewhere, delete `{path}`, and rerun"
        )
    name = _unit_name(path) or path
    return (
        f"`{path}` has local edits and the sidecar no longer ships `{name}`; "
        f"copy your edits elsewhere, then delete `{path}`"
    )


def _unfinished_remedy(path: str) -> str:
    # N14: naming this "an unfinished sidecar copy" or "your edited copy"
    # implies the sidecar once shipped it; with no manifest record at all,
    # its own exclude-block line is the only evidence, so say that plainly.
    return (
        f"`{path}` is listed by the sidecar's exclude block but never "
        "recorded. It stays hidden. Copy anything you need from it, delete "
        "it, and rerun"
    )


def _foreign_remedy(unit_path: str, *, uninstall: bool = False) -> str:
    name = _unit_name(unit_path)
    if name is None:
        return (
            f"the sidecar will not replace `{unit_path}`; rename or remove "
            "it only if you do not need it"
        )
    display = _named(name, _unit_kind_word(unit_path))
    if uninstall:
        # NIT (step 12f): uninstall has nothing left to place at any root.
        return (
            f"the sidecar will not replace `{unit_path}` and leaves {display} "
            f"alone; rename or remove `{unit_path}` only if you do not need it"
        )
    return (
        f"the sidecar will not replace `{unit_path}` and skips {display} at "
        f"every root; rename or remove `{unit_path}` only if you do not need it"
    )


def _retained_remedy(path: str) -> str:
    return (
        f"`{path}` was left behind when the repository started tracking its "
        "folder. It stays hidden, and a pull can overwrite it. Move it out "
        "of the folder, or commit it with `git add -f`"
    )


def _can_express_in_gitignore(relative_path: str) -> bool:
    """Return whether ``relative_path`` can get its own exact-match
    gitignore line (Decision 29). gitignore reads patterns line by line and
    strips one trailing carriage return, so a name that itself contains a
    newline anywhere, or ends in a carriage return, can never be expressed:
    such a name must never get a line, even transiently during the gate."""
    return "\n" not in relative_path and not relative_path.endswith("\r")


def _unexpressible_retained_remedy(path: str) -> str:
    return (
        f"`{path}` cannot be hidden: its name contains a newline or ends "
        "with a carriage return, which gitignore cannot match. It stays "
        "visible in `git status`; rename it without those characters if "
        "you want it hidden"
    )


def _now_visible_remedy(path: str) -> str:
    return f"`{path}` is no longer hidden; it is now visible to `git add -A`"


def _still_ignored_after_uninstall_remedy(path: str) -> str:
    """N16: some other rule (a team ``.gitignore``, or an unrelated
    ``info/exclude`` line) still ignores a path uninstall just un-hid, so
    promising it is visible to ``git add -A`` would be wrong."""
    return f"`{path}` is no longer hidden by the sidecar; a team rule still ignores it"


def _unrecognized_line_remedy(line: str) -> str:
    return (
        f"the sidecar does not recognize `{line}` in its own exclude block "
        "and keeps it; move it outside the block to keep it, or delete it "
        "if you do not need it"
    )


def _preserved_remedy(unit_path: str) -> str:
    name = _unit_name(unit_path)
    display = _named(name, _unit_kind_word(unit_path)) if name else f"`{unit_path}`"
    return (
        f"the repository now uses {display}, so your edited copy was moved "
        "out of the client folders"
    )


def _preserve_conflict_remedy(
    unit_path: str, preserved_path: str, *, unfinished: bool = False
) -> str:
    if unfinished:
        # An unfinished sidecar copy has no manifest record to begin with
        # (Decision 23): its own exclude-block line is its only ownership
        # proof, so say that plainly instead of the "local edits" wording
        # that fits a locally modified, recorded unit.
        return (
            f"`{unit_path}` is an unfinished sidecar copy the sidecar cannot "
            f"verify, and a preserved copy already sits at `{preserved_path}`; "
            f"the sidecar keeps `{unit_path}` in place, still hidden by its own "
            "exclude line (it has no manifest record). Resolve the two copies "
            "by hand, then rerun"
        )
    return (
        f"`{unit_path}` has local edits, and a preserved copy already sits at "
        f"`{preserved_path}`; the sidecar keeps `{unit_path}` in place. "
        "Resolve the two copies by hand, then rerun"
    )


# --------------------------------------------------------------------------
# Classification (the big plan's table, first matching row wins)
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _UnitOutcome:
    kind: str
    record: ManifestUnit | None
    actions: list[Action]
    reports: list[Report]
    retained_here: frozenset[str]
    line_write: bool
    line_final: bool


def _team_takeover(
    unit_path: str,
    snapshot: UnitSnapshot,
    record: ManifestUnit | None,
    desired: DesiredUnit | None,
    uninstall: bool = False,
    next_record: ManifestUnit | None = None,
) -> _UnitOutcome:
    """Classify a tracked unit as a team takeover (Decision 16, 23, 25).

    An untracked file is recognized as the sidecar's own -- and deleted --
    when its bytes match the manifest record, the pending record, or the
    desired content (Decision 23, N8): a crash during an update can leave a
    stale record while the swap already landed the new bytes (the pending
    manifest an interrupted update left behind is the proof then), and a
    unit that is merely listed (no record yet) has only the desired content
    as its ownership reference.

    ``uninstall`` (Decision 34): a file that would otherwise be retained
    (kept hidden) instead gets no line at all and the "now visible" report,
    the same as every other already-retained file during an uninstall --
    even when this run is the very first one to see this team takeover.
    """
    record_files = record.files if record is not None else {}
    next_record_files = next_record.files if next_record is not None else {}
    desired_files = desired.files if desired is not None else {}
    actions: list[Action] = []
    if record is not None:
        actions.append(Action("drop_record", unit_path))
    reports: list[Report] = [
        Report(
            "SKIPPED",
            unit_path,
            _team_owned_remedy(unit_path, snapshot.tracked_files, uninstall=uninstall),
        )
    ]
    retained_here: set[str] = set()
    untracked_entries = sorted(snapshot.untracked_files | snapshot.untracked_symlinks)
    for relpath in untracked_entries:
        full_path = f"{unit_path}/{relpath}"
        # Decision 38: an untracked symlink carries no hash, so it can never
        # match the record or the desired content -- it is treated like an
        # untracked file that matches nothing, never deleted.
        current_hash = snapshot.file_hashes.get(relpath)
        if current_hash is not None and (
            record_files.get(relpath) == current_hash
            or next_record_files.get(relpath) == current_hash
            or desired_files.get(relpath) == current_hash
        ):
            actions.append(Action("team_takeover_delete", unit_path, full_path))
        elif relpath in snapshot.ignored_files and uninstall:
            reports.append(
                Report("RETAINED", full_path, _now_visible_remedy(full_path))
            )
        elif relpath in snapshot.ignored_files and _can_express_in_gitignore(full_path):
            actions.append(Action("retain", unit_path, full_path))
            retained_here.add(full_path)
            reports.append(Report("RETAINED", full_path, _retained_remedy(full_path)))
        elif relpath in snapshot.ignored_files:
            # Decision 29: gitignore cannot express this name (a newline or
            # a trailing carriage return), so it never gets a line and stays
            # visible instead of being silently un-hidden later.
            reports.append(
                Report("RETAINED", full_path, _unexpressible_retained_remedy(full_path))
            )
        # else: a visible untracked file that does not match the record is
        # left alone: no action, no record, no line.
    return _UnitOutcome(
        "team_takeover", None, actions, reports, frozenset(retained_here), False, False
    )


def _state_kept_remedy(unit_path: str) -> str:
    return f"kept {unit_path} and its exclude line; pass --purge-state to remove it"


def _state_purged_remedy(unit_path: str) -> str:
    return (
        f"the sidecar was uninstalled with --purge-state, so {unit_path} was "
        "moved out of the client folders"
    )


def _classify_state_unit(
    unit_path: str,
    snapshot: UnitSnapshot,
    desired: DesiredUnit | None,
    *,
    uninstall: bool,
    purge_state: bool,
) -> _UnitOutcome:
    """Classify the namespaced state unit (Decision 2, 3; the big plan's
    Design Overview, "Unit kinds"). Never hashed or compared against
    ``desired`` or any record: a missing seed file is added whenever the
    folder already exists, on every run, but a present file -- whatever its
    own content -- is never touched, and no per-file or unit hash is ever
    recorded for it (Decision 6's own state seeding rule).

    Not uninstalling: an absent folder is seeded from scratch (an ordinary
    ``install`` action, since a fresh source folder holds only the seed
    files) when the active profile still has a state root, or left alone
    when it does not; an existing folder gets one ``seed_missing`` action
    per seed file the profile still ships that is not already there, and
    keeps its exclude line either way (Decision 10: switching to a profile
    with no state root must still keep an *existing* folder hidden).

    Uninstalling: kept and hidden by default (Decision 3), reported so the
    person knows to pass ``--purge-state``; ``purge_state`` instead preserves
    it like an edited unit's own copy, dropping the line.
    """
    if uninstall:
        if not snapshot.exists:
            return _UnitOutcome("noop", None, [], [], frozenset(), False, False)
        if purge_state:
            # ponytail: unlike an ordinary preserve, this never checks
            # preserved_conflicts/kept_conflicts -- state_backup_slug()
            # picks a name that does not exist yet, so a purge can never
            # collide with an earlier backup, even within the same second.
            report = Report("PRESERVED", unit_path, _state_purged_remedy(unit_path))
            return _UnitOutcome(
                "preserve",
                None,
                [Action("preserve", unit_path)],
                [report],
                frozenset(),
                True,
                False,
            )
        report = Report("RETAINED", unit_path, _state_kept_remedy(unit_path))
        return _UnitOutcome("state_kept", None, [], [report], frozenset(), True, True)

    if not snapshot.exists:
        if desired is None:
            return _UnitOutcome("noop", None, [], [], frozenset(), False, False)
        return _UnitOutcome(
            "install", None, [Action("install", unit_path)], [], frozenset(), True, True
        )

    missing = sorted(
        name
        for name in (desired.files if desired is not None else {})
        if name not in snapshot.file_hashes
    )
    actions = [
        Action("seed_missing", unit_path, f"{unit_path}/{name}") for name in missing
    ]
    return _UnitOutcome("state_kept", None, actions, [], frozenset(), True, True)


def _classify_unit(
    unit_path: str,
    snapshot: UnitSnapshot,
    record: ManifestUnit | None,
    desired: DesiredUnit | None,
    excluded_units: AbstractSet[str],
    uninstall: bool = False,
    next_record: ManifestUnit | None = None,
    *,
    purge_state: bool = False,
) -> _UnitOutcome:
    """Classify one unit (the big plan's table, first matching row wins).

    ``next_record`` (N8) is this unit's record in the pending manifest an
    interrupted update left behind (``<manifest>.next``, written after the
    gate passes and removed after the real manifest lands). It is extra
    ownership evidence only, never an intent record: a hash match against
    it, like a match against ``record``, proves the bytes on disk are the
    sidecar's own, so the ordinary update/remove row runs instead of a
    false "local edits". It is threaded into ``_team_takeover`` too, so a
    team takeover mid-crash deletes the sidecar's own matching file instead
    of retaining it.

    ``purge_state`` only affects the namespaced state root (Decision 3):
    every other unit ignores it. The state root dispatches to
    ``_classify_state_unit`` immediately, before the gitlink and
    tracked-files checks below: a tracked or gitlinked state root is caught
    by ``_run_target_preflight``'s own hard abort before any unit is ever
    classified (Decision 3's "aborts before any write"), so those checks
    would never fire for it anyway.
    """
    if unit_path in _ALL_STATE_ROOTS:
        return _classify_state_unit(
            unit_path, snapshot, desired, uninstall=uninstall, purge_state=purge_state
        )

    if snapshot.is_gitlink:
        # Decision 37: the unit itself is a gitlink. The outer exclude file
        # does not apply inside a submodule, so no check-ignore call and no
        # file action ever touches anything inside it -- unlike an ordinary
        # team takeover, which inspects untracked files one by one.
        actions = [Action("drop_record", unit_path)] if record is not None else []
        report = Report(
            "SKIPPED", unit_path, _gitlink_remedy(unit_path, uninstall=uninstall)
        )
        return _UnitOutcome(
            "gitlink", None, actions, [report], frozenset(), False, False
        )

    if snapshot.tracked_files:
        if record is not None or unit_path in excluded_units:
            # Tracked, and either recorded or merely listed (Decision 23):
            # team takeover either way. A listed-only unit uses the desired
            # content as its ownership reference.
            return _team_takeover(
                unit_path, snapshot, record, desired, uninstall, next_record
            )
        report = Report(
            "SKIPPED",
            unit_path,
            _team_owned_remedy(unit_path, snapshot.tracked_files, uninstall=uninstall),
        )
        return _UnitOutcome("team_owned", None, [], [report], frozenset(), False, False)

    if not snapshot.exists:
        if desired is not None:
            new_record = ManifestUnit(files=dict(desired.files), hash=desired.hash)
            return _UnitOutcome(
                "install",
                new_record,
                [Action("install", unit_path)],
                [],
                frozenset(),
                True,
                True,
            )
        if record is not None:
            return _UnitOutcome(
                "drop_record",
                None,
                [Action("drop_record", unit_path)],
                [],
                frozenset(),
                False,
                False,
            )
        return _UnitOutcome("noop", None, [], [], frozenset(), False, False)

    # Decision 38: an incomplete unit (a symlink, named pipe, socket, device,
    # empty subfolder, or unreadable subfolder anywhere inside it) can never
    # be represented by a hash, so it never matches its record or the
    # desired content; skip straight to the locally-modified/unfinished/
    # foreign fallback below instead of a false "unchanged" or "remove".
    current_hash = compute_unit_hash(snapshot.file_hashes)
    if not snapshot.incomplete and record is not None and current_hash == record.hash:
        if desired is None:
            return _UnitOutcome(
                "remove",
                None,
                [Action("remove", unit_path)],
                [],
                frozenset(),
                True,
                False,
            )
        if desired.hash == record.hash:
            new_record = ManifestUnit(files=dict(record.files), hash=record.hash)
            return _UnitOutcome(
                "unchanged",
                new_record,
                [Action("unchanged", unit_path)],
                [],
                frozenset(),
                True,
                True,
            )
        new_record = ManifestUnit(files=dict(desired.files), hash=desired.hash)
        return _UnitOutcome(
            "update",
            new_record,
            [Action("update", unit_path)],
            [],
            frozenset(),
            True,
            True,
        )

    if (
        not snapshot.incomplete
        and desired is not None
        and current_hash == desired.hash
        and (unit_path in excluded_units or record is not None)
    ):
        # Decision 23: a record alone is proof enough to adopt, even with no
        # exclude line (a crash, or the person deleting the block, must not
        # turn matching bytes into a false "locally modified" report).
        new_record = ManifestUnit(files=dict(desired.files), hash=desired.hash)
        return _UnitOutcome(
            "adopt",
            new_record,
            [Action("adopt", unit_path)],
            [],
            frozenset(),
            True,
            True,
        )

    if (
        not snapshot.incomplete
        and next_record is not None
        and current_hash == next_record.hash
    ):
        # N8: an interrupted update already swapped in the bytes the pending
        # manifest describes; that record is ownership proof, so the unit
        # updates to the current desired content (or is removed when nothing
        # is desired any more), exactly like a record match above.
        if desired is None:
            return _UnitOutcome(
                "remove",
                None,
                [Action("remove", unit_path)],
                [],
                frozenset(),
                True,
                False,
            )
        new_record = ManifestUnit(files=dict(desired.files), hash=desired.hash)
        return _UnitOutcome(
            "update",
            new_record,
            [Action("update", unit_path)],
            [],
            frozenset(),
            True,
            True,
        )

    if record is not None:
        report = Report(
            "SKIPPED",
            unit_path,
            _locally_modified_remedy(
                unit_path, skill_still_shipped=desired is not None
            ),
        )
        return _UnitOutcome(
            "locally_modified", record, [], [report], frozenset(), True, True
        )

    if unit_path in excluded_units:
        # Decision 23: listed, no record, content does not match desired (or
        # nothing is desired any more) -- an unfinished sidecar copy. Keep
        # the files and the line; record nothing.
        report = Report("SKIPPED", unit_path, _unfinished_remedy(unit_path))
        return _UnitOutcome("unfinished", None, [], [report], frozenset(), True, True)

    report = Report(
        "SKIPPED", unit_path, _foreign_remedy(unit_path, uninstall=uninstall)
    )
    return _UnitOutcome("foreign", None, [], [report], frozenset(), False, False)


# --------------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------------


def _case_variant_taking_paths(
    name: str,
    read_list_names: Mapping[str, AbstractSet[str]],
    ignorecase: bool,
    all_roots: Sequence[str] = SIDECAR_SKILL_READ_ROOTS,
    *,
    key: Callable[[str], str] = _same,
) -> tuple[str, ...]:
    """Return every read-list path whose entry is a case variant of
    ``name`` (Decision 22), when ``core.ignorecase`` is true. Covers every
    root of ``all_roots``, including the write root(s): a case-variant entry
    there is a different filesystem entry the sidecar must never touch.
    Defaults to the skill roots; the file-unit precedence checks in
    ``plan_sidecar_reconciliation`` (Decision 9) pass a unit kind's own
    roots and ``key``, the function that reduces an entry's file name to
    the identity it is compared by (``_entry_id`` for agents)."""
    if not ignorecase:
        return ()
    paths: list[str] = []
    for root in all_roots:
        for existing in sorted(read_list_names.get(root, frozenset())):
            existing_id = key(existing)
            if existing_id != name and existing_id.casefold() == name.casefold():
                paths.append(f"{root}/{existing}")
    return tuple(paths)


def _extra_taking_paths(
    name: str,
    read_list_names: Mapping[str, AbstractSet[str]],
    declared_names: Mapping[str, AbstractSet[str]],
    ignorecase: bool,
    *,
    read_only_roots: Sequence[str] = _READ_ONLY_ROOTS,
    all_roots: Sequence[str] = SIDECAR_SKILL_READ_ROOTS,
    write_roots: Sequence[str] = SIDECAR_SKILL_WRITE_ROOTS,
    key: Callable[[str], str] = _same,
) -> frozenset[str]:
    """Return every path -- besides ``name``'s own write-root unit(s), which
    self-report through their own classification -- that takes it (Decision
    22, generalized by Decision 9 to every file-unit kind): an exact name in
    a read-only folder of the same kind, a case variant in any folder of
    that kind, or (skills only) a non-sidecar ``SKILL.md`` frontmatter
    declaration.

    ``declared_names`` includes the sidecar's own write-root entries (a
    skill declares its own name too); they are removed by the same trailing
    subtraction that already removes ``name``'s own write-root units from
    every other source here, so a team or foreign declaration under a
    different folder name is never hidden behind the sidecar's own entry.
    Every keyword defaults to the skill roots, so an existing skill call
    site needs no change; an agent unit (the one other kind with more than
    one read root today) passes its own roots, an empty ``declared_names``,
    and ``key=_entry_id``, so that ``reviewer.agent.md``, ``reviewer.toml``,
    and the folder ``reviewer/`` each take the agent ``reviewer``. The paths
    returned name the entries as they exist on disk or in the index.
    """
    paths: set[str] = set()
    for root in read_only_roots:
        for existing in read_list_names.get(root, frozenset()):
            if key(existing) == name:
                paths.add(f"{root}/{existing}")
    paths.update(
        _case_variant_taking_paths(
            name, read_list_names, ignorecase, all_roots, key=key
        )
    )
    paths.update(declared_names.get(name, frozenset()))
    paths -= {f"{write_root}/{name}" for write_root in write_roots}
    return frozenset(paths)


def _preserved_uninstall_remedy(unit_path: str, *, unfinished: bool = False) -> str:
    name = _unit_name(unit_path)
    display = _named(name, _unit_kind_word(unit_path)) if name else f"`{unit_path}`"
    if unfinished:
        # N14: no manifest record backs this copy, so it was never "your
        # edited copy" of anything the sidecar shipped -- only its own
        # exclude-block line ever claimed it.
        return (
            f"the sidecar was uninstalled; {display} was listed by the "
            "sidecar's exclude block but never recorded, so it was moved "
            "out of the client folders"
        )
    return f"the sidecar was uninstalled, so your edited copy of {display} was moved out of the client folders"


def _convert_for_taken_skill(
    unit_path: str,
    outcome: _UnitOutcome,
    preserved_conflicts: AbstractSet[str],
    preserved_destinations: Mapping[str, str],
    uninstall: bool = False,
) -> _UnitOutcome:
    """Convert one taken skill's unit outcome to an allowed one (Decisions
    22 and 24; uninstall reuses this for every skill and bridge, Decision
    34). Looks the target up in an allowlist, not an enumerated switch, so a
    future outcome kind fails loudly instead of silently escaping team
    precedence the way ``adopt`` once did (R1)."""
    target = _TAKEN_OUTCOME_CONVERSION[outcome.kind]
    if target == "noop":
        return _UnitOutcome("noop", None, [], [], frozenset(), False, False)
    if target == "remove":
        return _UnitOutcome(
            "remove", None, [Action("remove", unit_path)], [], frozenset(), True, False
        )
    if target == "preserve":
        destination = preserved_destinations.get(unit_path, "")
        if unit_path in preserved_conflicts:
            report = Report(
                "SKIPPED",
                unit_path,
                _preserve_conflict_remedy(
                    unit_path, destination, unfinished=outcome.kind == "unfinished"
                ),
            )
            return _UnitOutcome(
                outcome.kind,
                outcome.record,
                [],
                [report],
                frozenset(),
                outcome.line_write,
                outcome.line_final,
            )
        remedy = (
            _preserved_uninstall_remedy(
                unit_path, unfinished=outcome.kind == "unfinished"
            )
            if uninstall
            else _preserved_remedy(unit_path)
        )
        report = Report("PRESERVED", unit_path, remedy)
        return _UnitOutcome(
            "preserve",
            None,
            [Action("preserve", unit_path)],
            [report],
            frozenset(),
            True,
            False,
        )
    raise AssertionError(
        f"unhandled taken-skill conversion target: {target!r}"
    )  # pragma: no cover


def plan_sidecar_reconciliation(
    *,
    desired_units: Mapping[str, DesiredUnit],
    manifest: Manifest | None,
    excluded_units: AbstractSet[str],
    read_list_skill_names: Mapping[str, AbstractSet[str]],
    snapshots: Mapping[str, UnitSnapshot],
    listed_files: AbstractSet[str] = frozenset(),
    unrecognized_lines: Sequence[str] = (),
    declared_skill_names: Mapping[str, AbstractSet[str]] | None = None,
    read_list_file_names: Mapping[str, AbstractSet[str]] | None = None,
    ignorecase: bool = False,
    preserved_conflicts: AbstractSet[str] = frozenset(),
    preserved_destinations: Mapping[str, str] | None = None,
    uninstall: bool = False,
    purge_state: bool = False,
    pending_manifest: Manifest | None = None,
    profile: str = SIDECAR_DEFAULT_PROFILE,
) -> PlanResult:
    """Plan one sidecar reconciliation run. Performs no I/O.

    Args:
        desired_units: The content the sidecar wants, keyed by unit path
            (see ``load_desired_units``).
        manifest: The previously parsed manifest, or ``None`` on a fresh
            install.
        excluded_units: The unit paths the sidecar's own exclude block
            currently lists (Decision 10 and 23: proves ownership for adopt
            and team-takeover-when-listed, and every one of them is
            classified even with no record and no desired content, so a
            lost record or a dropped skill is never silently un-hidden).
        read_list_skill_names: For every read-list folder (Decision 8, the
            keys of ``SIDECAR_SKILL_READ_ROOTS``), the skill names found
            there (directory and index names; presence only, no hashing
            needed).
        snapshots: A ``UnitSnapshot`` for every unit in
            ``required_snapshot_units(desired_units, manifest, excluded_units)``.
            A unit missing here is treated as absent (safe default: it plans
            as an install rather than as a destructive guess).
        listed_files: The file-level paths the sidecar's own exclude block
            lists; kept retained while they exist and are untracked, even
            with no manifest at all (Decision 23).
        unrecognized_lines: Every line inside the sidecar's own exclude
            block that ``parse_exclude_block`` could not classify as a unit
            or a file line, in file order. Kept in the block, after the
            sidecar's own sorted lines and in that same order (N7: gitignore
            is last-match-wins, so re-sorting a person's ``*.log`` and
            ``!keep.log`` would flip their meaning), and reported every run
            (as ``RETAINED``), so a hand-inserted line, or a line the
            sidecar no longer understands, is never silently dropped -- that
            could un-hide the file it was hiding.
        declared_skill_names: Skill name -> every read-list path whose
            ``SKILL.md`` frontmatter ``name:`` declares it, including the
            sidecar's own write-root entries (Decision 22, L3). This
            function removes the sidecar's own write-root paths from the
            result, the same way it already does for the other taking-path
            sources, so a team or foreign declaration under a different
            folder name is never hidden behind the sidecar's own entry.
        read_list_file_names: For every agent folder (Decision 9; the
            write root and the keys of ``_AGENT_READ_ONLY_ROOTS``), the
            entry names found there, in each client's own file shape
            (``reviewer.agent.md``, ``reviewer.toml``, the folder
            ``reviewer``). Generalizes ``read_list_skill_names`` to the one other
            file-unit kind with more than one folder of its own; every other
            kind's precedence is already decided by its own team-owned or
            foreign classification, since it has only the one write root.
        ignorecase: ``git config --bool core.ignorecase`` (Decision 22, 25).
        preserved_conflicts: Unit paths whose preserved-copy destination
            already exists, so preserving now would overwrite it (Decision
            24: the caller precomputes this so dry-run matches a real run).
        preserved_destinations: Unit path -> the display string for its
            preserved-copy destination, real or candidate.
        uninstall: Reconcile toward removing the sidecar entirely (Decision
            34; the small plan's step 9), with an empty ``desired_units``.
            Every skill and every bridge is treated as taken, so every unit
            converts to remove (unchanged/update/adopt), preserve (locally
            modified/unfinished), or noop (install), exactly like a taken
            skill's units already do; every carried-forward retained file
            loses its record and its line instead of being re-hidden, so it
            becomes visible; and every well-known unit is included even
            with no record, no exclude line, and nothing on disk. The
            namespaced state root is the one exception (Decision 3): it is
            kept and hidden by default, or preserved (moved out, line
            dropped) when ``purge_state`` is set, never removed outright.
        purge_state: Only meaningful with ``uninstall`` (Decision 3): move
            the namespaced state root into the preserved-copy folder and
            drop its line, instead of the default "kept and hidden".
        pending_manifest: The manifest an interrupted update left at
            ``<manifest>.next`` (N8), or ``None``. Its per-unit records are
            passed to ``_classify_unit`` as extra ownership evidence only.
        profile: The sidecar profile this run installs (Decision 1). Only
            used to stamp ``next_manifest.profile``; every other decision
            here is driven purely by ``desired_units`` (already built for
            this profile by the caller's own ``load_desired_units`` call).

    Returns:
        A ``PlanResult``. When ``aborts`` is non-empty, every other field is
        empty: the caller must not write anything.
    """
    declared_skill_names = declared_skill_names or {}
    read_list_file_names = read_list_file_names or {}
    preserved_destinations = preserved_destinations or {}

    required = required_snapshot_units(
        desired_units, manifest, excluded_units, listed_files
    )
    if uninstall:
        # Decision 39: every well-known unit is included, including a
        # retired write root or a retired bridge, so it is classified and
        # cleaned up even with no manifest record and no exclude line left.
        required = (
            required
            | frozenset(
                f"{write_root}/{skill}"
                for write_root in _ALL_SKILL_WRITE_ROOTS
                for skill in SIDECAR_SKILLS
            )
            | frozenset(_ALL_BRIDGES)
        )
    symlinked = sorted(
        unit for unit in required if snapshots.get(unit, UnitSnapshot()).symlinked
    )
    if symlinked:
        message = "symlinked unit or ancestor: " + ", ".join(symlinked)
        return PlanResult(aborts=(Abort("symlink", message),))

    # Decision 37: a recorded or listed unit holding a disk-only nested
    # repository (a ".git" entry whose parent is not itself a gitlink)
    # aborts before any write. A unit that is neither recorded nor listed is
    # foreign instead (handled by ordinary classification below): its skill
    # is taken, and nothing inside it is touched.
    nested_repo_units = sorted(
        unit
        for unit in required
        if snapshots.get(unit, UnitSnapshot()).nested_repo_relpath is not None
        and (
            (manifest is not None and unit in manifest.units) or unit in excluded_units
        )
    )
    if nested_repo_units:
        return PlanResult(
            aborts=tuple(
                Abort(
                    "nested_repo",
                    _nested_repo_message(
                        f"{unit}/{snapshots[unit].nested_repo_relpath}"
                    ),
                )
                for unit in nested_repo_units
            )
        )

    outcomes: dict[str, _UnitOutcome] = {}
    for unit_path in required:
        snapshot = snapshots.get(unit_path, UnitSnapshot())
        record = manifest.units.get(unit_path) if manifest is not None else None
        desired = desired_units.get(unit_path)
        next_record = (
            pending_manifest.units.get(unit_path) if pending_manifest else None
        )
        outcomes[unit_path] = _classify_unit(
            unit_path,
            snapshot,
            record,
            desired,
            excluded_units,
            uninstall,
            next_record,
            purge_state=purge_state,
        )

    # One precedence decision per skill (Decision 22): a skill is taken by
    # non-sidecar content at a write root (already self-reporting through
    # its own outcome above), an exact or case-variant name on the read
    # list, or a frontmatter declaration. Every taking path is reported.
    # A skill that left the profile but still has a recorded or listed unit
    # is decided too, so its edited copy is preserved when the team ships
    # its own version instead of staying hidden next to it.
    decided_skills = set(SIDECAR_SKILLS) | {
        skill for unit_path in required if (skill := _skill_write_root_name(unit_path))
    }
    taken_by_write_root: set[str] = set()
    for skill in sorted(decided_skills):
        for write_root in SIDECAR_SKILL_WRITE_ROOTS:
            outcome = outcomes.get(f"{write_root}/{skill}")
            if outcome is not None and outcome.kind in (
                "team_owned",
                "team_takeover",
                "gitlink",
                "foreign",
            ):
                taken_by_write_root.add(skill)
                break

    taken_skills: set[str] = set(taken_by_write_root)
    # Decision 44/O12: the exact wording (plain "skipped everywhere" versus
    # "kept until the conflict is resolved") depends on kept_conflicts,
    # computed below, so only the (path, name, kind word) triples are
    # collected here.
    extra_taking: list[tuple[str, str, str | None]] = []
    for skill in sorted(decided_skills):
        extra_paths = _extra_taking_paths(
            skill, read_list_skill_names, declared_skill_names, ignorecase
        )
        if not extra_paths:
            continue
        taken_skills.add(skill)
        for path in sorted(extra_paths):
            extra_taking.append((path, skill, None))

    # The same precedence decision, generalized by Decision 9 to every
    # file-unit kind with more than one folder of its own: today only an
    # agent unit (`.claude/agents/<id>.md`) has read-only siblings besides
    # its one write root. Every other new-profile file-unit kind (rule,
    # instructions, review profile, template) has exactly one folder, so its
    # own team-owned/foreign classification above already covers it fully.
    file_units_taken: set[str] = set()
    for unit_path in sorted(required):
        if (
            unit_path in _ALL_STATE_ROOTS
            or _skill_write_root_name(unit_path) is not None
            or str(PurePosixPath(unit_path).parent) != _AGENT_WRITE_ROOT
        ):
            continue
        name = _entry_id(PurePosixPath(unit_path).name)
        extra_paths = _extra_taking_paths(
            name,
            read_list_file_names,
            {},
            ignorecase,
            read_only_roots=_AGENT_READ_ONLY_ROOTS,
            all_roots=(_AGENT_WRITE_ROOT, *_AGENT_READ_ONLY_ROOTS),
            write_roots=(_AGENT_WRITE_ROOT,),
            key=_entry_id,
        )
        if not extra_paths:
            continue
        file_units_taken.add(unit_path)
        kind_word = _unit_kind_word(unit_path)
        for path in sorted(extra_paths):
            extra_taking.append((path, name, kind_word))

    if uninstall:
        # Decision 39: every classified unit is taken during uninstall,
        # including a dropped skill, a retired write root, or a retired
        # bridge -- every unit that reached `outcomes`, not only units under
        # the current profile's own skills and write roots. The state unit is
        # never taken: uninstall keeps it (Decision 3), so it stays out of the
        # taken-outcome conversion.
        taken_units = set(outcomes) - _ALL_STATE_ROOTS
    else:
        taken_units = {
            f"{write_root}/{skill}"
            for skill in taken_skills
            for write_root in _ALL_SKILL_WRITE_ROOTS
        } | file_units_taken
    kept_conflicts: set[str] = set()
    for unit_path in taken_units:
        outcome = outcomes.get(unit_path)
        if outcome is None or outcome.kind in _ALLOWED_TAKEN_OUTCOMES:
            continue
        if (
            outcome.kind in ("locally_modified", "unfinished")
            and unit_path in preserved_conflicts
        ):
            # Decision 39/O3: the caller's own preserved_conflicts input is
            # deliberately over-broad (every required unit whose hash-based
            # destination happens to exist, including absent and
            # about-to-be-removed ones); kept_conflicts narrows that to the
            # units that actually hit a conflict while trying to preserve.
            kept_conflicts.add(unit_path)
        outcomes[unit_path] = _convert_for_taken_skill(
            unit_path,
            outcome,
            preserved_conflicts,
            preserved_destinations,
            uninstall=uninstall,
        )

    # Decision 44/O12: while a conflict copy remains, a taken unit's own
    # other taking paths are reported as kept until it is resolved, never
    # as skipped at every root -- the Done Criterion is not absolute when
    # Decision 24 keeps a copy on a conflict.
    conflicted_names = {
        conflict_name
        for unit_path in kept_conflicts
        if (conflict_name := _unit_name(unit_path))
    }
    extra_reports = [
        Report(
            "SKIPPED",
            path,
            _read_only_taken_conflict_remedy(path, name, kind_word)
            if name in conflicted_names
            else _read_only_taken_remedy(path, name, kind_word),
        )
        for path, name, kind_word in extra_taking
    ]

    # Carry forward retained files: everything the manifest already tracks,
    # plus every file-level line the exclude block still lists (Decision 23:
    # a line keeps hiding its file even with no manifest), skipping a unit
    # that is undergoing a fresh team takeover this run (its own outcome
    # already made the authoritative retain/delete decision above).
    next_retained: set[str] = set()
    retained_reports: list[Report] = []
    retained_actions: list[Action] = []
    retained_line_paths: set[str] = set()
    retained_candidates: set[str] = set(listed_files)
    if manifest is not None:
        retained_candidates.update(manifest.retained)
    for path in sorted(retained_candidates):
        owner = _owning_unit(path)
        owner_outcome = outcomes.get(owner) if owner else None
        owner_snapshot = (
            snapshots.get(owner, UnitSnapshot()) if owner else UnitSnapshot()
        )
        relpath = path[len(owner) + 1 :] if owner else path
        if _under_a_gitlink_child(relpath, owner_snapshot.gitlink_child_relpaths):
            # Decision 37: nothing at or under any gitlink index entry keeps
            # a file line, including a gitlink nested inside the unit (not
            # only when the whole unit is one); dropped and reported as now
            # visible regardless of the owning unit's own outcome this run.
            retained_actions.append(Action("drop_record", owner or path, path))
            retained_reports.append(Report("RETAINED", path, _now_visible_remedy(path)))
            continue
        if owner_outcome is not None and owner_outcome.kind == "team_takeover":
            continue
        if owner_outcome is not None and owner_outcome.kind == "gitlink":
            # Decision 37: the outer exclude file does not apply inside a
            # submodule, so a stale line from before the unit became a
            # gitlink is dropped and reported as now visible, never
            # silently carried forward.
            retained_actions.append(Action("drop_record", owner or path, path))
            retained_reports.append(Report("RETAINED", path, _now_visible_remedy(path)))
            continue
        # Decision 38: a retained symlink carries no hash, so it never
        # appears in file_hashes; check symlink_relpaths too, so it is
        # carried forward while it exists instead of being dropped the
        # moment its owning unit stops being a fresh team takeover.
        still_present = (
            relpath in owner_snapshot.file_hashes
            or relpath in owner_snapshot.symlink_relpaths
        )
        if relpath in owner_snapshot.tracked_files or not still_present:
            retained_actions.append(Action("drop_record", owner or path, path))
            continue
        if uninstall:
            # Decision 34: uninstall un-hides every retained file instead of
            # re-hiding it, regardless of whether its name could be
            # expressed as a line in the first place.
            retained_actions.append(Action("drop_record", owner or path, path))
            retained_reports.append(Report("RETAINED", path, _now_visible_remedy(path)))
            continue
        if not _can_express_in_gitignore(path):
            # Decision 29: never write a line for this name; it stays
            # visible and is reported every run instead of being dropped
            # from the manifest's retained set into a false "not ours".
            retained_reports.append(
                Report("RETAINED", path, _unexpressible_retained_remedy(path))
            )
            continue
        next_retained.add(path)
        retained_line_paths.add(path)
        retained_reports.append(Report("RETAINED", path, _retained_remedy(path)))

    for outcome in outcomes.values():
        next_retained.update(outcome.retained_here)

    actions: list[Action] = []
    reports: list[Report] = list(extra_reports)
    next_units: dict[str, ManifestUnit] = {}
    exclude_write: set[str] = set()
    exclude_final: set[str] = set()
    # Decision 40: the gate paths are built next to the exclude lines, from
    # the same per-unit and per-file knowledge, spelled for the gate instead
    # of escaped for the exclude file. Unrecognized lines never join this
    # set (they are not necessarily even valid paths).
    gate_write: set[str] = set()
    gate_final: set[str] = set()
    for unit_path, outcome in sorted(outcomes.items()):
        actions.extend(outcome.actions)
        reports.extend(outcome.reports)
        if outcome.record is not None:
            next_units[unit_path] = outcome.record
        if outcome.line_write:
            exclude_write.add(unit_exclude_line(unit_path))
            gate_write.add(_gate_spelling(unit_path, snapshots))
        if outcome.line_final:
            exclude_final.add(unit_exclude_line(unit_path))
            gate_final.add(_gate_spelling(unit_path, snapshots))
        for action in outcome.actions:
            if (
                action.kind in ("team_takeover_delete", "retain")
                and action.path is not None
            ):
                exclude_write.add(escape_exact_path(action.path))
                gate_write.add(_gate_spelling(action.path, snapshots))
                if action.kind == "retain":
                    exclude_final.add(escape_exact_path(action.path))
                    gate_final.add(_gate_spelling(action.path, snapshots))

    actions.extend(retained_actions)
    reports.extend(retained_reports)
    for path in retained_line_paths:
        exclude_write.add(escape_exact_path(path))
        exclude_final.add(escape_exact_path(path))
        gate_write.add(_gate_spelling(path, snapshots))
        gate_final.add(_gate_spelling(path, snapshots))

    # Decision 23 / the big plan's exclude-block rules: keep any line the
    # sidecar does not understand, and report it once, every run, so a run
    # never un-hides a file through a line it does not recognize. Decision
    # 40: such a line is never gated. N7: these lines are appended after
    # the sidecar's own sorted lines, in their original file order, never
    # sorted -- gitignore is last-match-wins.
    for line in unrecognized_lines:
        if line.strip() == "":
            # A blank or whitespace-only line has nothing to report: it is
            # still kept in place, silently, every run (step 12d).
            continue
        reports.append(Report("RETAINED", line, _unrecognized_line_remedy(line)))
    kept_lines = tuple(unrecognized_lines)

    next_manifest = Manifest(
        schema_version=CURRENT_SCHEMA_VERSION,
        units=next_units,
        retained=frozenset(next_retained),
        profile=profile,
    )

    return PlanResult(
        aborts=(),
        actions=tuple(actions),
        reports=tuple(sorted(reports, key=lambda item: (item.category, item.path))),
        next_manifest=next_manifest,
        exclude_lines_write=tuple(sorted(exclude_write)) + kept_lines,
        exclude_lines_final=tuple(sorted(exclude_final)) + kept_lines,
        gate_paths_write=tuple(sorted(gate_write)),
        gate_paths_final=tuple(sorted(gate_final)),
        kept_conflicts=frozenset(kept_conflicts),
    )


# --- Git queries shared by mode detection and the apply step -----------------


def _c_locale_env() -> dict[str, str]:
    """Return a copy of the process environment with ``LC_ALL=C`` (Decision
    27), so Git's own error messages are in English regardless of the
    person's locale. Every caller that classifies Git's stderr text (for
    example "not a git repository") needs this, or the classification
    silently stops matching under a non-English locale."""
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    return env


def _git_rev_parse_or_raise(target: Path, *args: str) -> str:
    """Run ``git rev-parse --path-format=absolute <args>`` and return its
    one line of output, raising ``CalledProcessError`` (with ``stderr``
    populated) on failure, with ``LC_ALL=C`` so a caller can classify that
    failure (Decision 27). Shared by ``git_path`` and by
    ``sidecar_evidence``'s own Git-directory and common-directory lookups,
    so both use exactly one implementation of "run this rev-parse and raise
    like a caller can classify"."""
    result = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "--path-format=absolute", *args],
        check=True,
        capture_output=True,
        text=True,
        env=_c_locale_env(),
    )
    return result.stdout.removesuffix("\n")


def git_path(target: Path, name: str) -> Path:
    """Return the absolute path of a Git-directory file of ``target``.

    ``--path-format=absolute`` matters: plain ``--git-path`` prints a relative
    path in the main worktree. ``info/exclude`` resolves to the common Git
    directory, shared by every worktree; the manifest is per worktree. Read
    only, for reporting: never a detection or a write path (Decision 26
    moved the manifest, staging, and preserved paths off this function, and
    Decision 27/the orchestrator finding moved sidecar_evidence's own
    manifest/exclude lookups off it too, since ``--git-path`` resolves
    symlinks in the path -- exactly the thing both of those checks exist to
    catch).
    """
    return Path(_git_rev_parse_or_raise(target, "--git-path", name))


def sidecar_evidence(target: Path) -> tuple[str, ...]:
    """Describe the sidecar evidence in ``target``, or return ``()``.

    Evidence is a manifest file at the Git-directory path, valid or not
    (including a dangling symlink), or the sidecar marker block in
    ``info/exclude``. Both paths are built directly from ``--git-dir`` and
    ``--path-format=absolute --git-common-dir`` (never through
    ``git_path()``'s ``--git-path``, which resolves a symlink at the final
    path component before printing it -- the orchestrator finding: that
    silently hid a dangling manifest symlink, and silently read a symlinked
    ``info/exclude`` through the link, instead of treating it by its own
    type). ``info/exclude`` is checked with ``lstat`` and never opened
    unless it is a regular file (Decision 27): a non-regular one (folder,
    pipe, symlink) is simply not sidecar evidence -- sidecar preflight
    refuses it (Decision 26). Raises ``ExcludeMarkerError`` when a regular
    ``info/exclude`` carries unbalanced or repeated sidecar markers
    (Decision 26; S7); the caller must abort detection in every mode.
    """
    evidence = []
    git_dir = Path(_git_rev_parse_or_raise(target, "--git-dir"))
    manifest = git_dir / SIDECAR_MANIFEST_NAME
    if os.path.lexists(manifest):
        evidence.append(f"sidecar manifest {manifest}")
    git_common_dir = Path(_git_rev_parse_or_raise(target, "--git-common-dir"))
    exclude = git_common_dir / "info" / "exclude"
    try:
        exclude_lstat = os.lstat(exclude)
    except OSError:
        exclude_lstat = None
    if exclude_lstat is not None and stat.S_ISREG(exclude_lstat.st_mode):
        try:
            lines = _split_exclude_text(os.fsdecode(exclude.read_bytes()))
        except OSError as exc:
            # N11: an exclude file that cannot be read may hold a sidecar
            # block, so it counts as evidence; sidecar preflight then aborts
            # with the read error instead of a full install guessing.
            evidence.append(f"unreadable {exclude} ({exc.strerror})")
            return tuple(evidence)
        if _find_exclude_markers(lines) is not None:
            evidence.append(f"sidecar block in {exclude}")
    return tuple(evidence)


def read_sidecar_profile(target: Path) -> str | None:
    """Return the profile an existing sidecar manifest in ``target`` was
    written for, or ``None`` when there is no manifest, or it fails to
    parse (Decision 1). The caller falls back to ``SIDECAR_DEFAULT_PROFILE``,
    exactly like a fresh install with no ``--profile``. Read only, for
    choosing a CLI default -- ``install_sidecar``'s own preflight parses the
    manifest again, authoritatively, before any write."""
    try:
        git_dir = Path(_git_rev_parse_or_raise(target, "--git-dir"))
    except subprocess.CalledProcessError:
        return None
    manifest_path = git_dir / SIDECAR_MANIFEST_NAME
    if not manifest_path.is_file():
        return None
    try:
        return parse_manifest(manifest_path.read_text(encoding="utf-8")).profile
    except (ManifestError, OSError, UnicodeDecodeError):
        return None


_GIT_VERSION_RE = re.compile(r"git version (\d+)\.(\d+)(?:\.(\d+))?")
_MIN_GIT_VERSION = (2, 31, 0)


def _invalid_manifest_remedy(manifest_path: Path) -> str:
    """The big plan's exact remedy text (Decision 36; S16): a listed unit
    that does not match current content stays hidden and reported, it is
    never exposed as foreign, so this must not warn people it will vanish."""
    return (
        f"move `{manifest_path}` aside and rerun with --mode sidecar. Units "
        "that the exclude block lists are recovered: matching units are "
        "adopted, and any other listed unit is kept hidden and reported. "
        "Keep the old manifest until the report looks right."
    )


_EXCLUDE_MARKER_REMEDY = (
    "fix info/exclude by hand: the sidecar's own BEGIN/END markers must "
    "appear exactly once each, with BEGIN before END, then rerun"
)


def _fault_point(name: str) -> None:
    """No-op checkpoint a test can monkeypatch to raise at a named point.

    Named points, matching the big plan's crash-recovery cases (Decision
    10): ``"after_exclude_write"`` (the write-phase exclude block is on disk
    and the ignore gate passed, before any unit or file action runs),
    ``"mid_unit_swap"`` (inside one unit's install/update: any old copy has
    already moved into staging, but the new copy has not replaced it yet),
    and ``"before_manifest_write"`` (every unit and file action is done and
    the final exclude block is written, but the manifest is not yet).

    Uninstall (Decision 39) shares this same write order but never passes
    through ``"after_exclude_write"``: it has its own ``"after_units_removed"``,
    placed after the write-phase block is written and its gate
    (``gate_paths_final``, over only the lines the final block keeps) has
    already passed, and after every unit and file action has run. At that
    point the exclude file holds the write-phase block, not the
    pre-uninstall bytes -- for example, a retained file's line is already
    gone, since uninstall never carries one forward -- but a unit this run
    removes still keeps its own write-phase line, not yet dropped.
    Uninstall reuses ``"before_manifest_write"`` for its own, same-named
    last step (the manifest is deleted or rewritten there instead of
    written fresh), placed after the final exclude block -- with every
    removed unit's line now dropped -- is already written.
    """


def _printable(message: str) -> str:
    """Decision 29 (N11): a path with undecodable bytes reaches here as a
    surrogate-escaped string; printing that raw raises under a strict
    stdout encoding, so render the raw bytes as ``\\xNN`` escapes instead."""
    return os.fsencode(message).decode("utf-8", "backslashreplace")


def _info(message: str) -> None:
    print(f"sidecar-install: {_printable(message)}")


def _report_preserved_folder_if_nonempty(preserved_root: Path) -> None:
    """Decision 44/O16: print the preserved-copy folder's path whenever it
    holds anything, even when there is otherwise nothing to do -- both here
    and in the CLI's own "no sidecar found" path (``install_bootstrap.py``).
    A person who never re-checks after an old uninstall must still be able
    to find an edited copy it kept.

    The wording must stay true from every caller, including the end of a
    run that just preserved a copy of its own (already reported by its own
    ``PRESERVED ...`` line): it never claims the folder's contents are from
    "an earlier run"."""
    try:
        has_content = preserved_root.is_dir() and any(preserved_root.iterdir())
    except OSError:
        return
    if has_content:
        _info(
            f"preserved copies are in {preserved_root}; the sidecar never empties this folder"
        )


# NIT: leaf folders first, then their parents, so a parent is only ever
# removed once every folder it holds is already gone.
_EMPTY_SIDECAR_CLEANUP_ORDER = (
    ".claude/skills",
    ".agents/skills",
    ".claude/rules",
    ".claude/agents",
    ".claude/review-profiles",
    ".claude/templates",
    ".github/instructions",
    ".claude",
    ".agents",
    ".github",
)


def _remove_empty_sidecar_parents(target: Path) -> None:
    """After a successful uninstall, or an install that removed units, remove
    the sidecar's own folders it may have created, but only when each is now
    completely empty (NIT): a team
    file, another tool's folder, or anything a preserve conflict kept in
    place must never be swept away. ``os.rmdir`` already refuses a
    non-empty or missing folder with ``OSError``, so ignoring it is the
    whole safety check."""
    for relative in _EMPTY_SIDECAR_CLEANUP_ORDER:
        with contextlib.suppress(OSError):
            os.rmdir(target / PurePosixPath(relative))


def _abort(evidence: str, remedy: str) -> int:
    print(f"sidecar-install: ABORT: {_printable(evidence)}", file=sys.stderr)
    print(f"sidecar-install: {_printable(remedy)}", file=sys.stderr)
    return 1


_WRITE_FAILURE_REMEDY = (
    "fix the permissions or the filesystem problem at that path, then rerun; "
    "the run stopped part-way and a rerun picks up where it stopped"
)


def _abort_write_failure(exc: OSError) -> int:
    """N10/N11: an ``OSError`` past preflight (the apply step, an atomic
    write, or a read while gathering) is a clean abort naming the path,
    never a traceback."""
    where = exc.filename or "the target"
    return _abort(
        f"filesystem error at {where}: {exc.strerror or exc}", _WRITE_FAILURE_REMEDY
    )


def _git_version() -> tuple[int, int, int] | None:
    result = subprocess.run(
        ["git", "--version"], capture_output=True, text=True, check=False
    )
    match = _GIT_VERSION_RE.search(result.stdout)
    if not match:
        return None
    major, minor, patch = match.groups()
    return (int(major), int(minor), int(patch or 0))


def rev_parse(target: Path, *args: str) -> str | None:
    """Run ``git rev-parse --path-format=absolute`` and return its output.

    Returns ``None`` on failure instead of raising, so the caller can read a
    non-repository ``target`` as evidence rather than a crash. Shared by this
    module's own preflight and by ``install_bootstrap.py``'s mode detection
    (``_is_linked_worktree``), so there is one implementation of this query.
    """
    result = subprocess.run(
        ["git", "-C", str(target), "rev-parse", "--path-format=absolute", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.removesuffix("\n") if result.returncode == 0 else None


def _device_id(path: Path) -> int:
    """Return a path's filesystem device id.

    A module-level seam: a test monkeypatches this to fake the Git directory
    and the worktree sitting on two different filesystems.
    """
    return os.stat(path).st_dev


def _lstat_or_none(path: Path) -> os.stat_result | None:
    """Return ``os.lstat(path)``, or ``None`` when it does not exist. Uses
    the plain ``os`` function, not ``Path.lstat``, so a test can monkeypatch
    ``os.lstat`` to fake a path's type or device (Decision 26, 28)."""
    try:
        return os.lstat(path)
    except OSError:
        return None


def _nearest_existing_ancestor(target: Path, relative: str) -> Path:
    """Return the nearest existing ancestor of ``target/relative``: the path
    itself if it exists (a symlink counts), otherwise the first existing
    parent found by walking upward. Always terminates at ``target``, which
    the caller has already confirmed exists (Decision 28)."""
    current = target / PurePosixPath(relative)
    while current != target and _lstat_or_none(current) is None:
        current = current.parent
    return current


_NESTED_REPO_REMEDY = "move or remove the nested repository or submodule, then rerun"


def _nested_repo_message(relative: str) -> str:
    return (
        f"sidecar mode does not support the nested repository or submodule "
        f"at `{relative}`; nothing was written"
    )


def _plan_abort_remedy(aborts: tuple[Abort, ...]) -> str:
    """Return the remedy for a planner abort (Decision 37): the nested-
    repository remedy when any abort is a unit-level nested repository,
    otherwise the existing symlink remedy."""
    if any(abort.reason == "nested_repo" for abort in aborts):
        return _NESTED_REPO_REMEDY
    return (
        "sidecar mode does not support a symlinked skill folder or "
        "projection parent; nothing was written"
    )


def _repository_boundary_violations(
    target: Path,
    planned_relatives: AbstractSet[str],
    index_entries: Sequence[tuple[str, str]],
) -> tuple[str, ...]:
    """Decision 28: abort before any write when a planned path's nearest
    existing ancestor belongs to another Git repository -- a nested clone,
    proven by ``git rev-parse --show-toplevel`` reporting a different
    toplevel, or an unpopulated submodule, proven by a gitlink (mode
    ``160000``) at or above the path in the outer index (Phase G's index
    reader, reused here rather than a second one)."""
    violations: list[str] = []
    target_resolved = target.resolve()
    for relative in sorted(planned_relatives):
        parts = PurePosixPath(relative).parts
        ancestor_relatives = {
            "/".join(parts[:index]) for index in range(1, len(parts) + 1)
        }
        gitlinked = next(
            (
                path
                for mode, path in index_entries
                if mode == "160000" and path in ancestor_relatives
            ),
            None,
        )
        if gitlinked is not None:
            violations.append(_nested_repo_message(gitlinked))
            continue
        ancestor = _nearest_existing_ancestor(target, relative)
        if ancestor == target:
            continue
        info = _lstat_or_none(ancestor)
        if info is None or not stat.S_ISDIR(info.st_mode):
            continue  # a different check (filesystem shape) reports this
        toplevel = rev_parse(ancestor, "--show-toplevel")
        if toplevel is not None and Path(toplevel).resolve() != target_resolved:
            violations.append(
                _nested_repo_message(ancestor.relative_to(target).as_posix())
            )
    return tuple(violations)


def _symlinked_projection_parent_message(relative: str) -> str:
    return (
        f"sidecar mode does not support a symlinked skill folder or "
        f"projection parent at `{relative}`; nothing was written"
    )


def _filesystem_shape_violations(
    target: Path, planned_relatives: AbstractSet[str]
) -> tuple[str, ...]:
    """Decision 28: abort before any write when an existing ancestor of a
    planned path is not a real folder, or sits on a different device than
    ``target``. A symlinked ancestor (Decision 36; S16) gets its own message
    naming it as a symlinked projection parent, not a generic shape error --
    and never tells the person to replace tracked team content."""
    violations: list[str] = []
    target_device = _device_id(target)
    for relative in sorted(planned_relatives):
        ancestor = _nearest_existing_ancestor(target, relative)
        if ancestor == target:
            continue
        info = _lstat_or_none(ancestor)
        if info is None:
            continue
        display = ancestor.relative_to(target).as_posix()
        if stat.S_ISLNK(info.st_mode):
            violations.append(_symlinked_projection_parent_message(display))
        elif not stat.S_ISDIR(info.st_mode):
            violations.append(f"{display} exists and is not a folder")
        elif info.st_dev != target_device:
            violations.append(f"{display} is on a different filesystem than {target}")
    return tuple(violations)


def _unit_device_violations(
    target: Path,
    required_units: AbstractSet[str],
    snapshots: Mapping[str, UnitSnapshot],
) -> tuple[str, ...]:
    """Decision 37: the device check also runs on every existing unit
    folder, not only the write roots and bridge parents (Decision 28). Only
    the device is checked here: a unit that exists as a symlink or another
    non-folder is not a shape violation at the unit level (Decision 25), and
    is left to its own, already-safe classification."""
    target_device = _device_id(target)
    violations: list[str] = []
    for unit_path in sorted(required_units):
        snapshot = snapshots.get(unit_path)
        if snapshot is None or not snapshot.exists or snapshot.kind != "folder":
            continue
        info = _lstat_or_none(target / PurePosixPath(unit_path))
        if info is not None and info.st_dev != target_device:
            violations.append(f"{unit_path} is on a different filesystem than {target}")
    return tuple(violations)


def _iter_dirs_under(base: Path) -> list[Path]:
    """Return ``base`` and every folder inside it, for a writability sweep
    before a destructive move, replace, or removal (Decision 28). Returns
    ``[]`` when ``base`` is not a real, unlinked folder."""
    if base.is_symlink() or not base.is_dir():
        return []
    dirs = [base]
    dirs.extend(
        entry
        for entry in sorted(base.rglob("*"))
        if entry.is_dir() and not entry.is_symlink()
    )
    return dirs


def _unwritable_paths_for_actions(
    target: Path,
    actions: Sequence[Action],
    git_dir: Path,
    preserved_destinations: Mapping[str, Path],
) -> tuple[Path, ...]:
    """Decision 28: every folder a planned action must move, replace, or
    empty needs write access -- the parent of every unit that moves, every
    unit folder that itself moves, every folder inside a unit that is
    removed, replaced, or later emptied from staging, the folder holding
    every file a team takeover deletes, the nearest existing ancestor of
    every preserve destination, and the Git directory itself (staging, the
    manifest, and ``info/exclude`` all live there; N10). Checked with
    ``os.access`` before any write.

    A unit's parent that does not exist yet (a fresh install under a write
    root nobody has created on this run) is not itself checked: ``mkdir``
    creates it later, so its nearest *existing* ancestor is what must be
    writable instead.
    """
    check: set[Path] = {git_dir}
    if (git_dir / "info").is_dir():
        check.add(git_dir / "info")
    for action in actions:
        if action.kind in ("team_takeover_delete", "seed_missing") and (
            action.path is not None
        ):
            check.add((target / PurePosixPath(action.path)).parent)
            continue
        if action.kind == "preserve":
            destination = preserved_destinations[action.unit]
            check.add(
                _nearest_existing_ancestor(
                    git_dir, str(destination.relative_to(git_dir))
                )
            )
        if action.kind not in ("install", "update", "remove", "preserve"):
            continue
        parent_relative = str(PurePosixPath(action.unit).parent)
        parent = (
            target
            if parent_relative == "."
            else _nearest_existing_ancestor(target, parent_relative)
        )
        check.add(parent)
        if action.kind in ("update", "remove", "preserve"):
            check.update(_iter_dirs_under(target / PurePosixPath(action.unit)))
    return tuple(sorted(path for path in check if not os.access(path, os.W_OK)))


def _sidecar_source_violations(
    source: Path, profile: str = SIDECAR_DEFAULT_PROFILE
) -> tuple[str, ...]:
    """Return every way ``source`` fails the exact sidecar source contract
    for ``profile`` (Decision 31; S13, S14, L2): a plain set comparison of
    every file found in ``source`` against ``sidecar_source_exact_allowlist()``,
    so a missing or extra path of any kind is reported. Shares its logic
    with the generated-target validator (``sidecar_source_violations`` in
    ``runtime_ownership.py``), so a crafted tree gets the same verdict from
    both."""
    present = frozenset(
        file_path.relative_to(source).as_posix()
        for file_path in sorted(source.rglob("*"))
        if file_path.is_file()
    )
    return _shared_source_violations(present, profile)


def _is_symlinked_ancestor(target: Path, relative: str) -> bool:
    """Return whether an ancestor directory of ``relative`` -- not the path
    itself -- is a symlink. That always aborts the run (non-goal). A symlink
    at the unit path itself does not: a tracked one is team-owned, and an
    untracked one is foreign (Decision 25)."""
    current = target
    parts = PurePosixPath(relative).parts
    for part in parts[:-1]:
        current = current / part
        if current.is_symlink():
            return True
    return False


# --------------------------------------------------------------------------
# Gathering planner inputs with Git
# --------------------------------------------------------------------------


def _read_index_entries(target: Path) -> tuple[tuple[str, str], ...]:
    """Return ``(mode, path)`` for every Git index entry, decoded with
    ``os.fsdecode`` (Decision 25 and 29). Includes ``skip-worktree``,
    intent-to-add, gitlink (``160000``), and symlink (``120000``) entries --
    everything ``git ls-files -s -z`` prints, whether or not the path exists
    on disk. This is the single index reader Phase H reuses for its own
    gitlink and ``.claude`` checks.
    """
    result = subprocess.run(
        ["git", "-C", str(target), "ls-files", "-s", "-z"],
        capture_output=True,
        check=True,
        env=_c_locale_env(),
    )
    entries: list[tuple[str, str]] = []
    for part in result.stdout.split(b"\0"):
        if not part:
            continue
        meta, _, raw_path = part.partition(b"\t")
        mode = meta.split(b" ", 1)[0].decode("ascii")
        entries.append((mode, os.fsdecode(raw_path)))
    return tuple(entries)


def _tracked_files(target: Path) -> frozenset[str]:
    """Return every path the Git index has an entry for (Decision 25)."""
    return frozenset(path for _mode, path in _read_index_entries(target))


def _ignorecase(target: Path) -> bool:
    """Return ``git config --bool core.ignorecase`` (Decision 22 and 25).
    An unset value (exit 1, no output) means false; it is not a Git error.
    """
    result = subprocess.run(
        ["git", "-C", str(target), "config", "--bool", "core.ignorecase"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0 and result.stdout.strip() == "true"


def _check_ignore(target: Path, paths: Sequence[str]) -> frozenset[str]:
    """Return the subset of ``paths`` that ``git check-ignore`` reports as
    currently ignored. Uses ``--stdin -z`` so an unusual name (embedded
    newline, non-ASCII byte) round-trips exactly. Bytes-safe (Decision 29):
    encodes and decodes with ``os.fsencode``/``os.fsdecode``, never strict
    UTF-8, so a legal but non-UTF-8 Git path never crashes the run.

    Raises ``GitCheckIgnoreError`` when Git exits with anything other than 0
    (something matched) or 1 (nothing matched) -- for example 128 for a path
    inside a submodule (Decision 37, 40) -- instead of silently treating the
    unreported paths as not ignored."""
    if not paths:
        return frozenset()
    payload = os.fsencode("\0".join(paths) + "\0")
    result = subprocess.run(
        ["git", "-C", str(target), "check-ignore", "--stdin", "-z"],
        input=payload,
        capture_output=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        stderr = os.fsdecode(result.stderr).strip()
        raise GitCheckIgnoreError(
            stderr or f"git check-ignore exited {result.returncode}"
        )
    return frozenset(os.fsdecode(part) for part in result.stdout.split(b"\0") if part)


def _full_relpath(unit_path: str, relpath: str) -> str:
    """Return a unit-relative file path as a path relative to the worktree."""
    return unit_path if unit_path in _ALL_BRIDGES else f"{unit_path}/{relpath}"


def _unit_index_relpaths(
    unit_path: str,
    tracked_paths: AbstractSet[str],
    ignorecase: bool,
    disk_relpaths: AbstractSet[str] = frozenset(),
) -> frozenset[str]:
    """Return every index path at or under ``unit_path``, as unit-relative
    paths (Decision 25): the file's own name for a bridge, or the sentinel
    ``""`` when the unit path itself is a non-directory index entry (a
    gitlink, or a tracked symlink). When ``ignorecase`` is true, matches a
    case-variant tracked path too, so a case-variant tracked folder makes
    the unit tracked. A case-variant tracked file is reconciled to
    ``disk_relpaths``'s own casing (the caller's ``file_hashes`` keys) so it
    is never counted as untracked: comparing the raw index casing against
    the disk casing by plain string equality would silently miss it.
    """
    if unit_path in _ALL_BRIDGES:
        target_unit = unit_path.casefold() if ignorecase else unit_path
        target_prefix = f"{target_unit}/"
        for path in tracked_paths:
            compare = path.casefold() if ignorecase else path
            # An entry under the bridge path (a tracked folder with the
            # bridge's name) makes the bridge tracked too, like a skill.
            if compare == target_unit or compare.startswith(target_prefix):
                return frozenset({PurePosixPath(unit_path).name})
        return frozenset()

    prefix = f"{unit_path}/"
    target_unit = unit_path.casefold() if ignorecase else unit_path
    target_prefix = prefix.casefold() if ignorecase else prefix
    disk_by_fold = (
        {relpath.casefold(): relpath for relpath in disk_relpaths} if ignorecase else {}
    )
    relpaths: set[str] = set()
    for path in tracked_paths:
        compare = path.casefold() if ignorecase else path
        if compare == target_unit:
            relpaths.add("")
        elif compare.startswith(target_prefix):
            relpath = path[len(prefix) :]
            if ignorecase:
                relpath = disk_by_fold.get(relpath.casefold(), relpath)
            relpaths.add(relpath)
    return frozenset(relpaths)


@dataclass(frozen=True)
class _GatherResult:
    """Everything ``_gather_unit`` learns from the worktree alone for one
    unit; ``_build_snapshots`` adds index-derived ``tracked_files`` and
    ``ignored_files`` (Decision 25) to turn this into a ``UnitSnapshot``."""

    exists: bool
    ancestor_symlinked: bool
    file_hashes: dict[str, str]
    symlink_relpaths: frozenset[str]
    incomplete: bool
    kind: Literal["folder", "symlink", "other"]
    nested_repo_relpath: str | None
    is_gitlink: bool = False
    gitlink_child_relpaths: frozenset[str] = frozenset()


def _gather_unit(
    target: Path, unit_path: str, gitlinks: AbstractSet[str] = frozenset()
) -> _GatherResult:
    """Walk one unit on disk (Decisions 25, 37, 38).

    ``relpath`` matches ``load_desired_units``'s convention: the file's own
    name for a bridge, or its path relative to the skill directory. A skill
    folder that holds no non-folder entry at any depth and no unreadable
    subfolder counts as absent: an empty leftover folder is not a reason to
    skip reinstalling a skill. Otherwise a symlink, named pipe, socket,
    device, empty subfolder, or unreadable subfolder anywhere inside makes
    the unit ``incomplete`` (Decision 38). Nothing at or under a gitlink
    index entry, and nothing under a nested ``.git`` entry, is ever hashed
    (Decision 37); neither is followed. The walk never follows a symlinked
    directory either, so a symlink cycle can never make it loop.
    """
    ancestor_symlinked = _is_symlinked_ancestor(target, unit_path)
    full_path = target / PurePosixPath(unit_path)

    if unit_path in _ALL_BRIDGES:
        if full_path.is_symlink():
            return _GatherResult(
                True, ancestor_symlinked, {}, frozenset(), False, "symlink", None
            )
        if full_path.is_file():
            name = PurePosixPath(unit_path).name
            try:
                bridge_files = {name: compute_file_hash(full_path.read_bytes())}
            except OSError:
                # N11 / Decision 38: an unreadable file makes the unit
                # incomplete, the same as an unreadable subfolder.
                return _GatherResult(
                    True, ancestor_symlinked, {}, frozenset(), True, "other", None
                )
            return _GatherResult(
                True,
                ancestor_symlinked,
                bridge_files,
                frozenset(),
                False,
                "other",
                None,
            )
        return _GatherResult(
            full_path.exists(),
            ancestor_symlinked,
            {},
            frozenset(),
            False,
            "folder",
            None,
        )

    if unit_path in gitlinks:
        # Decision 37: the unit itself is a gitlink. Every checked-out file
        # belongs to the submodule, not the sidecar; never recurse into it.
        exists = full_path.exists() or full_path.is_symlink()
        return _GatherResult(
            exists, ancestor_symlinked, {}, frozenset(), False, "other", None, True
        )

    if full_path.is_symlink():
        return _GatherResult(
            True, ancestor_symlinked, {}, frozenset(), False, "symlink", None
        )
    if not full_path.is_dir():
        exists = full_path.exists()
        # Decision 40: "<unit>/" is only for a real folder or an absent
        # unit; an existing non-folder (a plain file, FIFO, socket, or
        # device) is gated as "<unit>", not "<unit>/".
        return _GatherResult(
            exists,
            ancestor_symlinked,
            {},
            frozenset(),
            False,
            "other" if exists else "folder",
            None,
        )

    files: dict[str, str] = {}
    symlinks: set[str] = set()
    gitlink_children: set[str] = set()
    has_non_folder = False
    has_unreadable = False
    has_empty_subfolder = False
    has_special = False
    nested_repo_relpath: str | None = None

    def walk(dir_path: Path, dir_relpath: str, dir_full_relpath: str) -> None:
        nonlocal has_non_folder, has_unreadable, has_empty_subfolder
        nonlocal has_special, nested_repo_relpath
        try:
            entries = sorted(os.scandir(dir_path), key=lambda entry: entry.name)
        except OSError:
            has_unreadable = True
            return
        if not entries:
            if dir_relpath:  # never the unit root itself
                has_empty_subfolder = True
            return
        for entry in entries:
            relpath = f"{dir_relpath}/{entry.name}" if dir_relpath else entry.name
            full_relpath = f"{dir_full_relpath}/{entry.name}"
            if full_relpath in gitlinks:
                # Decision 37: never recurse below a gitlink, so its own
                # checked-out content is never hashed, gated, or actioned.
                # Recorded so a stale retained/listed line that now falls
                # under it can be dropped and reported, not silently kept.
                has_non_folder = True
                gitlink_children.add(relpath)
                continue
            if entry.is_symlink():
                has_non_folder = True
                has_special = True
                symlinks.add(relpath)
                continue
            if entry.name == ".git":
                # Every ".git" this walk can still reach has a parent that is
                # not itself a gitlink (one was skipped above already), so it
                # is always a disk-only nested repository (Decision 37).
                has_non_folder = True
                if nested_repo_relpath is None:
                    nested_repo_relpath = relpath
                continue
            if entry.is_file():
                has_non_folder = True
                try:
                    files[relpath] = compute_file_hash(Path(entry.path).read_bytes())
                except OSError:
                    # N11 / Decision 38: an unreadable file makes the unit
                    # incomplete, the same as an unreadable subfolder.
                    has_unreadable = True
            elif entry.is_dir():
                walk(Path(entry.path), relpath, full_relpath)
            else:
                has_non_folder = True
                has_special = True  # a named pipe, socket, or device

    walk(full_path, "", unit_path)

    has_content = has_non_folder or has_unreadable
    incomplete = has_special or has_empty_subfolder or has_unreadable
    return _GatherResult(
        has_content,
        ancestor_symlinked,
        files,
        frozenset(symlinks),
        incomplete,
        "folder",
        nested_repo_relpath,
        False,
        frozenset(gitlink_children),
    )


def _build_snapshots(
    target: Path,
    required_units: AbstractSet[str],
    tracked: AbstractSet[str],
    ignorecase: bool = False,
    gitlinks: AbstractSet[str] = frozenset(),
) -> dict[str, UnitSnapshot]:
    """Snapshot every required unit with one batched ``check-ignore`` call.

    ``tracked_files`` comes from the Git index (``tracked``), independent of
    disk presence (Decision 25); ``file_hashes`` and ``symlink_relpaths``
    still come from the worktree alone. Raises ``GitCheckIgnoreError`` when
    ``check-ignore`` fails fatally (Decision 37, 40); the caller must abort
    rather than plan from a partial ignore set.
    """
    raw = {
        unit_path: _gather_unit(target, unit_path, gitlinks)
        for unit_path in required_units
    }
    tracked_by_unit: dict[str, frozenset[str]] = {
        unit_path: _unit_index_relpaths(
            unit_path, tracked, ignorecase, frozenset(raw[unit_path].file_hashes)
        )
        for unit_path in required_units
    }
    candidates: list[str] = []
    for unit_path, result in raw.items():
        unit_tracked = tracked_by_unit[unit_path]
        candidates.extend(
            _full_relpath(unit_path, relpath)
            for relpath in (*result.file_hashes, *result.symlink_relpaths)
            if relpath not in unit_tracked
        )
    ignored_now = _check_ignore(target, candidates)
    snapshots: dict[str, UnitSnapshot] = {}
    for unit_path, result in raw.items():
        unit_tracked = tracked_by_unit[unit_path]
        unit_ignored = frozenset(
            relpath
            for relpath in (*result.file_hashes, *result.symlink_relpaths)
            if relpath not in unit_tracked
            and _full_relpath(unit_path, relpath) in ignored_now
        )
        snapshots[unit_path] = UnitSnapshot(
            exists=result.exists,
            symlinked=result.ancestor_symlinked,
            tracked_files=unit_tracked,
            file_hashes=result.file_hashes,
            ignored_files=unit_ignored,
            symlink_relpaths=result.symlink_relpaths,
            is_gitlink=result.is_gitlink,
            nested_repo_relpath=result.nested_repo_relpath,
            incomplete=result.incomplete,
            kind=result.kind,
            gitlink_child_relpaths=result.gitlink_child_relpaths,
        )
    return snapshots


def _resolve_or_none(path: Path) -> Path | None:
    try:
        return path.resolve()
    except OSError:
        return None


def _reflects_a_write_root(
    target: Path,
    path: Path,
    write_roots: Sequence[str] = SIDECAR_SKILL_WRITE_ROOTS,
) -> bool:
    """Return whether ``path`` is an alias into one of the sidecar's own
    write roots: it resolves somewhere other than its own name says
    (``target`` is already resolved, so any difference means a symlink on
    the way, the entry's own or a parent's such as ``.agent -> .claude``)
    and that place lies inside a write root. Such a folder mirrors a
    sidecar projection (the common ``.github/skills -> ../.claude/skills``
    layout) and is never treated as holding non-sidecar content (Decision
    22): the alternative would alternate install, remove, install every
    run. A write root's own real entries resolve to themselves and are
    never aliases. ``write_roots`` defaults to the skill write roots; the
    agent folders pass their own."""
    resolved = _resolve_or_none(path)
    if resolved is None or resolved == path:
        return False
    for write_root in write_roots:
        write_real = _resolve_or_none(target / PurePosixPath(write_root))
        if write_real is None:
            continue
        if resolved == write_real or write_real in resolved.parents:
            return True
    return False


def _enumerate_read_entries(
    target: Path,
    roots: Sequence[str] = SIDECAR_SKILL_READ_ROOTS,
    *,
    write_roots: Sequence[str] = SIDECAR_SKILL_WRITE_ROOTS,
    files_too: bool = False,
) -> dict[str, dict[str, Path]]:
    """One path-identity rule for every folder-name and frontmatter-name
    collision source (Decision 52), shared by ``_read_list_skill_names``,
    ``_declared_skill_names``, and ``_read_list_agent_names``. The defaults
    walk the skill roots for folders; the agent reader passes the agent
    roots and ``files_too=True``, since a client keeps an agent as a file
    or as a folder (Decision 9).

    An entry or root of the read list is an alias -- and contributes
    nothing -- when its resolved path differs from its lexical path (a
    symlink sits somewhere on the way, whether or not the entry's own last
    component is a symlink) and that resolved path lies inside a write
    root: it only ever mirrors a sidecar projection, the common
    ``.github/skills -> ../.claude/skills`` layout, and is never treated as
    holding non-sidecar content. Every other root or entry (a real folder,
    or a symlink that resolves outside every write root, including a
    broken one) is listed by its own name, whether or not it sits inside a
    write root itself.

    Returns ``{root: {entry_name: entry_path}}`` for every real, non-alias
    entry found on disk.
    """
    entries: dict[str, dict[str, Path]] = {}
    for root in roots:
        root_path = target / PurePosixPath(root)
        root_entries: dict[str, Path] = {}
        if root_path.is_dir() and not _reflects_a_write_root(
            target, root_path, write_roots
        ):
            try:
                children = list(root_path.iterdir())
            except OSError:
                children = []
            for entry in children:
                if not (files_too or entry.is_dir() or entry.is_symlink()):
                    continue
                if _reflects_a_write_root(target, entry, write_roots):
                    continue
                root_entries[entry.name] = entry
        entries[root] = root_entries
    return entries


def _read_list_skill_names(
    target: Path, index_paths: AbstractSet[str]
) -> dict[str, frozenset[str]]:
    """Return the skill directory names present in each read-list folder,
    from the index and the disk together (Decision 25), using the shared
    read-entry enumerator (Decision 41) for the disk side.
    """
    read_entries = _enumerate_read_entries(target)
    names: dict[str, frozenset[str]] = {}
    for root in SIDECAR_SKILL_READ_ROOTS:
        disk_names = set(read_entries.get(root, {}))
        prefix = f"{root}/"
        index_names = {
            path[len(prefix) :].split("/", 1)[0]
            for path in index_paths
            if path.startswith(prefix) and len(path) > len(prefix)
        }
        names[root] = frozenset(disk_names | index_names)
    return names


def _read_list_agent_names(
    target: Path, index_paths: AbstractSet[str]
) -> dict[str, frozenset[str]]:
    """Return the entry names present in every agent folder (Decision 9),
    both the one write root (``.claude/agents``) and its read-only siblings,
    from the index and the disk together, through the shared read-entry
    enumerator. An entry is a file or a folder, in the client's own shape
    (``reviewer.md``, ``reviewer.agent.md``, ``reviewer.toml``, or the folder
    ``reviewer/`` holding ``agent.md``); the precedence check reduces each
    to its identity with ``_entry_id``. Mirrors ``_read_list_skill_names``
    for the one other file-unit kind with more than one folder of its own;
    every other new-profile kind has exactly one folder, so its own
    team-owned or foreign classification already covers it fully."""
    roots = (_AGENT_WRITE_ROOT, *_AGENT_READ_ONLY_ROOTS)
    read_entries = _enumerate_read_entries(
        target, roots, write_roots=(_AGENT_WRITE_ROOT,), files_too=True
    )
    names: dict[str, frozenset[str]] = {}
    for root in roots:
        disk_names = set(read_entries.get(root, {}))
        prefix = f"{root}/"
        index_names = {
            path[len(prefix) :].split("/", 1)[0]
            for path in index_paths
            if path.startswith(prefix) and len(path) > len(prefix)
        }
        names[root] = frozenset(disk_names | index_names)
    return names


_FRONTMATTER_NAME_RE = re.compile(r"^name\s*:\s*(.+?)\s*$")
_FRONTMATTER_MAX_BYTES = 4096


def _parse_frontmatter_name(data: bytes) -> str | None:
    """Return the frontmatter ``name:`` value from a ``SKILL.md``'s leading
    ``---`` block, or ``None`` when missing or malformed (Decision 22).
    Strips surrounding quotes and, for an unquoted value, a trailing ``#``
    comment."""
    # The read window may end inside a multibyte character: replace, never
    # fail, since the name line always comes before the cut.
    text = data.decode("utf-8", errors="replace").removeprefix("\ufeff")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    closing = next(
        (index for index in range(1, len(lines)) if lines[index].strip() == "---"),
        None,
    )
    if closing is None:
        return None
    for line in lines[1:closing]:
        match = _FRONTMATTER_NAME_RE.match(line)
        if not match:
            continue
        value = match.group(1)
        if value[:1] in ("'", '"'):
            quote = value[0]
            closing = value.find(quote, 1)
            if closing == -1:
                return None
            value = value[1:closing]
        else:
            value = value.split("#", 1)[0].strip()
        return value or None
    return None


def _declared_skill_names(target: Path) -> dict[str, frozenset[str]]:
    """Return skill name -> every read-list path whose ``SKILL.md``
    frontmatter ``name:`` declares it (Decision 22, L3), using the shared
    read-entry enumerator (Decision 41): a symlinked read-only root is
    scanned through its link exactly like the folder-name scan, and a
    per-entry alias into a write root is skipped the same way. Opens only a
    regular file (``lstat``-checked) and reads at most 4 KB.

    Every declaring path is kept, including the sidecar's own write-root
    unit (which declares its own name): a first-wins map would let the
    sidecar's own entry, scanned first, silently hide a team or foreign
    folder under a different name that declares the same skill.
    ``_extra_taking_paths`` is what removes the sidecar's own write-root
    paths from the result, the same way it already does for the read-list
    name and case-variant checks.
    """
    read_entries = _enumerate_read_entries(target)
    declared: dict[str, set[str]] = {}
    for root in sorted(SIDECAR_SKILL_READ_ROOTS):
        for name, entry in sorted(read_entries.get(root, {}).items()):
            skill_md = entry / "SKILL.md"
            try:
                info = skill_md.lstat()
            except OSError:
                continue
            if not stat.S_ISREG(info.st_mode):
                continue
            try:
                with skill_md.open("rb") as handle:
                    data = handle.read(_FRONTMATTER_MAX_BYTES)
            except OSError:
                continue
            declared_name = _parse_frontmatter_name(data)
            if declared_name:
                declared.setdefault(declared_name, set()).add(f"{root}/{name}")
    return {name: frozenset(paths) for name, paths in declared.items()}


def _find_exclude_markers(lines: Sequence[str]) -> tuple[int, int] | None:
    """Return the 0-based ``(begin_index, end_index)`` of the sidecar's own
    BEGIN/END markers in ``lines``, or ``None`` when neither marker line is
    present at all (the ordinary "no sidecar block yet" case).

    Raises ``ExcludeMarkerError``, naming every marker line found (1-based),
    for anything else: an orphan BEGIN, an END with no earlier BEGIN, two
    blocks, or a repeated BEGIN or END (Decision 26; S7). Shared by mode
    detection (``sidecar_evidence``) and the sidecar's own preflight
    (``_read_exclude_block``), so both refuse the same malformed block
    before any write instead of one of them silently erasing the person's
    own ignore lines.
    """
    begins = [
        index for index, line in enumerate(lines) if line == SIDECAR_EXCLUDE_BEGIN
    ]
    ends = [index for index, line in enumerate(lines) if line == SIDECAR_EXCLUDE_END]
    if not begins and not ends:
        return None
    if len(begins) == 1 and len(ends) == 1 and begins[0] < ends[0]:
        return begins[0], ends[0]
    found = sorted(
        [(index + 1, "BEGIN") for index in begins]
        + [(index + 1, "END") for index in ends]
    )
    detail = ", ".join(f"{kind} at line {line}" for line, kind in found)
    raise ExcludeMarkerError(
        f"the sidecar's exclude-block markers in info/exclude are unbalanced "
        f"or repeated: {detail}"
    )


def _read_exclude_block(exclude_path: Path) -> ExcludeBlockContents:
    """Read and parse the sidecar's own exclude block (Decision 23).

    Reads bytes and decodes with ``os.fsdecode`` (Decision 29), so a
    non-UTF-8 byte in an existing personal ignore line never crashes the
    run. Raises ``ExcludeMarkerError`` when the markers are unbalanced or
    repeated (Decision 26); the caller must check for that before any write.
    """
    try:
        data = exclude_path.read_bytes()
    except (FileNotFoundError, NotADirectoryError):
        return ExcludeBlockContents()
    # N11: any other OSError (an unreadable file) propagates, so preflight
    # aborts instead of treating a file it could not read as "no block" and
    # then overwriting a person's own lines.
    return parse_exclude_block(os.fsdecode(data))


# --------------------------------------------------------------------------
# Exclude-file rendering and atomic writes
# --------------------------------------------------------------------------


def _replace_exclude_block(original_text: str, lines: Sequence[str]) -> str:
    """Return ``original_text`` with exactly one sidecar block set to
    ``lines``. Preserves every byte (including line endings) outside the
    ``BEGIN``/``END`` markers."""
    block_text = "\n".join([SIDECAR_EXCLUDE_BEGIN, *lines, SIDECAR_EXCLUDE_END]) + "\n"
    file_lines = _split_exclude_text(original_text, keepends=True)
    begin_index: int | None = None
    end_index: int | None = None
    for index, line in enumerate(file_lines):
        stripped = line.rstrip("\r\n")
        if begin_index is None and stripped == SIDECAR_EXCLUDE_BEGIN:
            begin_index = index
        elif begin_index is not None and stripped == SIDECAR_EXCLUDE_END:
            end_index = index
            break
    if begin_index is not None and end_index is not None:
        before = "".join(file_lines[:begin_index])
        after = "".join(file_lines[end_index + 1 :])
        return before + block_text + after
    separator = "" if not original_text or original_text.endswith("\n") else "\n"
    return f"{original_text}{separator}{block_text}"


def _remove_exclude_block(original_text: str, replacement_lines: Sequence[str]) -> str:
    """Return ``original_text`` with the sidecar's own BEGIN/END markers and
    everything between them removed entirely, and ``replacement_lines``
    written back as plain lines at that same position (Decision 34; the
    small plan's uninstall step): a line the sidecar never understood must
    survive the block's own markers, not vanish with them. Preserves every
    byte outside the block, the same way ``_replace_exclude_block`` does.
    Returns ``original_text`` unchanged when there is no block to remove.
    """
    file_lines = _split_exclude_text(original_text, keepends=True)
    begin_index: int | None = None
    end_index: int | None = None
    for index, line in enumerate(file_lines):
        stripped = line.rstrip("\r\n")
        if begin_index is None and stripped == SIDECAR_EXCLUDE_BEGIN:
            begin_index = index
        elif begin_index is not None and stripped == SIDECAR_EXCLUDE_END:
            end_index = index
            break
    if begin_index is None or end_index is None:
        return original_text
    before = "".join(file_lines[:begin_index])
    after = "".join(file_lines[end_index + 1 :])
    replacement_text = "\n".join(replacement_lines) + "\n" if replacement_lines else ""
    return before + replacement_text + after


def _atomic_write(path: Path, data: bytes) -> None:
    """Write ``data`` to ``path`` via a same-directory temp file + ``os.replace``.

    N9: ``mkstemp`` creates the temp file as 0600, and ``os.replace`` keeps
    that mode, so an existing file keeps its own mode and a new file gets
    the ordinary ``0666 & ~umask`` instead of ending up private.

    N19: the temp file's descriptor is ``fsync``ed before close, and the
    parent directory is ``fsync``ed after ``os.replace``, so a power cut
    cannot leave a zero-length or half-renamed file behind. The directory
    fsync is best-effort only (some filesystems refuse it); every other
    ``OSError`` here still propagates.
    """
    try:
        mode = stat.S_IMODE(os.stat(path).st_mode)
    except OSError:
        umask = os.umask(0)
        os.umask(umask)
        mode = 0o666 & ~umask
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            os.fchmod(handle.fileno(), mode)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise
    dir_fd = os.open(str(path.parent), os.O_RDONLY)
    try:
        os.fsync(dir_fd)
    except OSError:
        pass
    finally:
        os.close(dir_fd)


def _gate_spelling(
    path: str, snapshots: Mapping[str, UnitSnapshot] | None = None
) -> str:
    """Return the ignore-gate spelling for one path (Decision 30, 40): a
    skill unit that is a real folder, or absent, is gated as a folder,
    ``<unit>/``, so a team rule ending in ``/`` still applies before the
    folder exists; a unit that exists as a symlink or any other non-folder
    is gated as ``<unit>``, because Git refuses a trailing slash on a
    symlink. With no snapshot available, every unit is spelled as a folder
    (the pre-Decision-40 default). Bridges and individual files are gated as
    themselves. Uses ``_ALL_SKILL_WRITE_ROOTS`` so a retired root is still
    spelled correctly. The namespaced state root (Decision 2, 3) is folder-
    shaped like a skill unit, not a single file, so it gets the same
    folder-or-not spelling."""
    if path in _ALL_BRIDGES:
        return path
    if path in _ALL_STATE_ROOTS:
        snapshot = (snapshots or {}).get(path)
        if snapshot is not None and snapshot.kind != "folder":
            return path
        return f"{path}/"
    for write_root in _ALL_SKILL_WRITE_ROOTS:
        prefix = f"{write_root}/"
        if path.startswith(prefix) and "/" not in path[len(prefix) :]:
            snapshot = (snapshots or {}).get(path)
            if snapshot is not None and snapshot.kind != "folder":
                return path
            return f"{path}/"
    return path


# --------------------------------------------------------------------------
# The ignore gate (Decision 17)
# --------------------------------------------------------------------------


_NO_MATCHING_RULE = (
    "no matching rule (visible); a rule ending in `/` in a .gitignore file or "
    "in info/exclude may be un-ignoring the folder (Git cannot name a "
    "directory-only rule for a path that does not exist yet), or a plain "
    "negation naming this folder below the block or in a .gitignore may be "
    "un-ignoring it even though the folder already exists"
)


def _parse_check_ignore_verbose(
    output: bytes, expected: AbstractSet[str]
) -> tuple[tuple[str, str], ...]:
    """Parse ``git check-ignore -v -n -z --stdin``'s output: each requested
    path is one NUL-separated ``source, linenum, pattern, pathname`` record
    (verified in scratch against Git 2.43), so a legal but non-UTF-8 or
    embedded-newline path never breaks the split the way a line-oriented
    parse would (Decision 29). All three of ``source``/``linenum``/``pattern``
    come back empty for a directory-only rule matched against a path that
    does not exist on disk yet (Decision 36; S15, S16)."""
    fields = output.split(b"\0")
    if fields and fields[-1] == b"":
        fields = fields[:-1]
    failing: list[tuple[str, str]] = []
    for index in range(0, len(fields) - 3, 4):
        source, linenum, pattern, raw_pathname = fields[index : index + 4]
        pathname = os.fsdecode(raw_pathname)
        if pathname not in expected:
            continue
        if source or linenum or pattern:
            rule = (
                f"{os.fsdecode(source)}:{os.fsdecode(linenum)}:{os.fsdecode(pattern)}"
            )
        else:
            rule = _NO_MATCHING_RULE
        failing.append((pathname, rule))
    return tuple(failing)


def run_ignore_gate(
    target: Path,
    must_be_ignored: Sequence[str],
    candidate_exclude_text: bytes,
    *,
    dry_run: bool,
) -> tuple[bool, tuple[tuple[str, str], ...]]:
    """Run Decision 17's ignore gate; shared by a real run and dry-run.

    A real run has already written ``candidate_exclude_text`` to
    ``info/exclude`` and this checks it directly. A dry run writes the
    candidate text to a temporary file outside the worktree and the Git
    directory and points a one-shot ``core.excludesFile`` at it, never
    touching ``info/exclude``. Passes only when ``git check-ignore --stdin
    -z`` reports exactly the input set, byte for byte: plain ``--stdin``
    exits 0 as soon as one path is ignored, which is not enough.

    Raises ``GitCheckIgnoreError`` when either ``check-ignore`` call exits
    with anything other than 0 (something matched) or 1 (nothing matched),
    for example 128 for a path inside a submodule (Decision 40); the caller
    must restore the exclude file and abort with Git's own message rather
    than plan from a partial or misleading result.
    """
    if not must_be_ignored:
        return True, ()
    git_prefix = ["git", "-C", str(target)]
    temp_excludes_file: Path | None = None
    if dry_run:
        handle = tempfile.NamedTemporaryFile(
            prefix="ai-bootstrap-sidecar-dry-run-", suffix=".gitignore", delete=False
        )
        try:
            handle.write(candidate_exclude_text)
        finally:
            handle.close()
        temp_excludes_file = Path(handle.name)
        git_prefix = [*git_prefix, "-c", f"core.excludesFile={temp_excludes_file}"]
    try:
        payload = os.fsencode("\0".join(must_be_ignored) + "\0")
        result = subprocess.run(
            [*git_prefix, "check-ignore", "--stdin", "-z"],
            input=payload,
            capture_output=True,
            check=False,
        )
        if result.returncode not in (0, 1):
            raise GitCheckIgnoreError(
                os.fsdecode(result.stderr).strip()
                or f"git check-ignore exited {result.returncode}"
            )
        ignored = frozenset(
            os.fsdecode(part) for part in result.stdout.split(b"\0") if part
        )
        expected = frozenset(must_be_ignored)
        if ignored == expected:
            return True, ()
        # -z only makes sense with --stdin (git's own restriction), and the
        # explanatory fields must be bytes-safe too (Decision 29), so this
        # pipes the same NUL-separated payload instead of passing paths as
        # argv.
        verbose = subprocess.run(
            [*git_prefix, "check-ignore", "-v", "-n", "-z", "--stdin"],
            input=payload,
            capture_output=True,
            check=False,
        )
        if verbose.returncode not in (0, 1):
            raise GitCheckIgnoreError(
                os.fsdecode(verbose.stderr).strip()
                or f"git check-ignore exited {verbose.returncode}"
            )
        # O10: only the paths that are not already ignored are explained, so
        # a correctly ignored path never dilutes the failure list.
        return False, _parse_check_ignore_verbose(verbose.stdout, expected - ignored)
    finally:
        if temp_excludes_file is not None:
            temp_excludes_file.unlink(missing_ok=True)


def _still_ignored_by_another_rule(
    target: Path, paths: Sequence[str], *, dry_run: bool, candidate_text: bytes = b""
) -> frozenset[str]:
    """N16: return the subset of ``paths`` that ``git check-ignore`` still
    reports as ignored, checked against the exclude state uninstall leaves
    behind (the sidecar's own lines for these paths are already gone by
    construction -- only some other rule can still match them). A real run
    has already written the final text to ``info/exclude`` and this checks
    it directly; a dry run points a one-shot ``core.excludesFile`` at
    ``candidate_text`` instead, the same temp-file shape ``run_ignore_gate``
    uses, so it never touches the real file. Never raises: a Git failure
    here must not turn an already-finished uninstall into an error, only
    fall back to the ordinary "now visible" wording."""
    if not paths:
        return frozenset()
    git_prefix = ["git", "-C", str(target)]
    temp_excludes_file: Path | None = None
    if dry_run:
        handle = tempfile.NamedTemporaryFile(
            prefix="ai-bootstrap-sidecar-dry-run-", suffix=".gitignore", delete=False
        )
        try:
            handle.write(candidate_text)
        finally:
            handle.close()
        temp_excludes_file = Path(handle.name)
        git_prefix = [*git_prefix, "-c", f"core.excludesFile={temp_excludes_file}"]
    try:
        payload = os.fsencode("\0".join(paths) + "\0")
        result = subprocess.run(
            [*git_prefix, "check-ignore", "--stdin", "-z"],
            input=payload,
            capture_output=True,
            check=False,
        )
        if result.returncode not in (0, 1):
            return frozenset()
        return frozenset(
            os.fsdecode(part) for part in result.stdout.split(b"\0") if part
        )
    finally:
        if temp_excludes_file is not None:
            temp_excludes_file.unlink(missing_ok=True)


def _recheck_now_visible_reports(
    plan_result: PlanResult, target: Path, *, dry_run: bool, candidate_text: bytes = b""
) -> PlanResult:
    """N16: reword every "now visible" report whose path a team rule still
    ignores after uninstall. Minimal: one extra ``check-ignore`` call, only
    when there is at least one such report."""
    now_visible = tuple(
        report.path
        for report in plan_result.reports
        if report.category == "RETAINED"
        and report.remedy == _now_visible_remedy(report.path)
    )
    still_ignored = _still_ignored_by_another_rule(
        target, now_visible, dry_run=dry_run, candidate_text=candidate_text
    )
    if not still_ignored:
        return plan_result
    updated_reports = tuple(
        Report(
            "RETAINED", report.path, _still_ignored_after_uninstall_remedy(report.path)
        )
        if report.path in still_ignored
        and report.remedy == _now_visible_remedy(report.path)
        else report
        for report in plan_result.reports
    )
    return replace(plan_result, reports=updated_reports)


def _restore_exclude(exclude_path: Path, original_bytes: bytes | None) -> None:
    if original_bytes is None:
        exclude_path.unlink(missing_ok=True)
    else:
        _atomic_write(exclude_path, original_bytes)


def _ignore_gate_remedy() -> str:
    return (
        "a .gitignore rule is un-ignoring a sidecar path (for example a "
        "negation like `!.claude/skills/**`); ask the team to change the "
        "rule, or remove your own negation from info/exclude, then rerun"
    )


def _describe_gate_failure(failing: tuple[tuple[str, str], ...]) -> str:
    detail = "; ".join(f"{path} (winning rule: {rule})" for path, rule in failing)
    return (
        f"the ignore gate failed for: {detail}" if detail else "the ignore gate failed"
    )


# --------------------------------------------------------------------------
# Applying the plan (Decision 10: atomic moves, no intent records)
# --------------------------------------------------------------------------


def _staging_slug(unit_path: str) -> str:
    return hashlib.sha256(unit_path.encode("utf-8")).hexdigest()


def _place_unit(target: Path, source: Path, staging: Path, unit_path: str) -> None:
    """Atomically install or update one unit.

    Builds the new content in ``staging``, moves any existing copy out of
    the way into ``staging`` too, then swaps the new copy into place with
    one ``os.replace``. After an interruption the unit is the old copy, the
    new copy, or absent, and a rerun's classification handles all three.
    """
    destination = target / PurePosixPath(unit_path)
    source_path = source / PurePosixPath(unit_path)
    new_staging_path = staging / f"new-{_staging_slug(unit_path)}"
    old_staging_path = staging / f"old-{_staging_slug(unit_path)}"

    if unit_path in _ALL_BRIDGES:
        shutil.copy2(source_path, new_staging_path)
    else:
        shutil.copytree(source_path, new_staging_path)

    if destination.exists() or destination.is_symlink():
        os.replace(destination, old_staging_path)

    _fault_point("mid_unit_swap")

    destination.parent.mkdir(parents=True, exist_ok=True)
    os.replace(new_staging_path, destination)


def _remove_unit(target: Path, staging: Path, unit_path: str) -> None:
    destination = target / PurePosixPath(unit_path)
    if destination.exists() or destination.is_symlink():
        os.replace(destination, staging / f"removed-{_staging_slug(unit_path)}")


def _delete_file(target: Path, relative_path: str | None) -> None:
    if relative_path is None:
        return
    file_path = target / PurePosixPath(relative_path)
    if file_path.is_file() or file_path.is_symlink():
        file_path.unlink()


def _preserve_unit(target: Path, destination: Path, unit_path: str) -> None:
    """Move a taken skill's edited or unfinished unit out of the client
    folders and into the preserved folder (Decision 24), with ``os.replace``
    after creating the destination's parent."""
    source_path = target / PurePosixPath(unit_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    os.replace(source_path, destination)


def _seed_state_file(target: Path, source: Path, relative_path: str) -> None:
    """Add one missing state seed file (Decision 3): never overwrites a file
    that is already there, at any depth under the state root, whatever its
    own content -- ``relative_path`` is worktree-relative, matching
    ``team_takeover_delete``'s own convention."""
    destination = target / PurePosixPath(relative_path)
    if destination.exists() or destination.is_symlink():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source / PurePosixPath(relative_path), destination)


def _empty_staging(staging: Path) -> None:
    if staging.exists() and not staging.is_symlink():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)


_NO_UNINSTALL_SOURCE = Path("/nonexistent-uninstall-source")
"""Decision 39: uninstall reuses ``_apply_actions`` but has no source tree of
its own. An empty desired set can never produce "install", "update", or
"adopt" (those rows all require desired content), so this path is never
actually read; ``uninstall_sidecar`` asserts that before calling
``_apply_actions``, and a missing source here is deliberate, not a bug."""


def _apply_actions(
    target: Path,
    source: Path,
    staging: Path,
    plan_result: PlanResult,
    preserved_destinations: Mapping[str, Path],
) -> None:
    for action in plan_result.actions:
        if action.kind in ("install", "update"):
            _place_unit(target, source, staging, action.unit)
        elif action.kind == "remove":
            _remove_unit(target, staging, action.unit)
        elif action.kind == "team_takeover_delete":
            _delete_file(target, action.path)
        elif action.kind == "preserve":
            _preserve_unit(target, preserved_destinations[action.unit], action.unit)
        elif action.kind == "seed_missing" and action.path is not None:
            _seed_state_file(target, source, action.path)
        # "adopt", "unchanged", "retain", and "drop_record" touch no file:
        # the content already matches, the file already sits where it
        # belongs, or only the manifest record changes.


def _count_actions(plan_result: PlanResult) -> dict[str, int]:
    counts = {
        "install": 0,
        "update": 0,
        "remove": 0,
        "adopt": 0,
        "unchanged": 0,
        "preserve": 0,
        "seed_missing": 0,
    }
    for action in plan_result.actions:
        if action.kind in counts:
            counts[action.kind] += 1
    return counts


def _print_report(
    plan_result: PlanResult, preserved_destinations: Mapping[str, str] | None = None
) -> None:
    """Print the run's summary and one line per removed, deleted, seeded, or
    preserved path, plus every SKIPPED/RETAINED/PRESERVED report (S15: a
    real run must name what a takeover deleted, not only count it)."""
    preserved_destinations = preserved_destinations or {}
    counts = _count_actions(plan_result)
    _info(
        f"installed {counts['install']}, updated {counts['update']}, "
        f"removed {counts['remove']}, adopted {counts['adopt']}, "
        f"unchanged {counts['unchanged']}, preserved {counts['preserve']}, "
        f"seeded {counts['seed_missing']}"
    )
    for action in plan_result.actions:
        if action.kind == "remove":
            _info(f"removed {action.unit}")
        elif action.kind == "team_takeover_delete" and action.path is not None:
            _info(f"deleted {action.path}")
        elif action.kind == "preserve":
            destination = preserved_destinations.get(action.unit, "")
            _info(f"PRESERVED {action.unit} -> {destination}")
        elif action.kind == "seed_missing" and action.path is not None:
            _info(f"seeded {action.path}")
    for report in plan_result.reports:
        _info(f"{report.category} {report.path}: {report.remedy}")


def _describe_dry_run_actions(
    plan_result: PlanResult, preserved_destinations: Mapping[str, str] | None = None
) -> None:
    preserved_destinations = preserved_destinations or {}
    verbs = {
        "install": "install",
        "update": "update",
        "remove": "remove",
        "adopt": "adopt",
        "team_takeover_delete": "delete",
        "retain": "retain",
        "drop_record": "drop the record for",
        "unchanged": "keep",
        "seed_missing": "seed",
    }
    for action in plan_result.actions:
        if action.kind == "preserve":
            destination = preserved_destinations.get(action.unit, "")
            _info(f"would preserve {action.unit} -> {destination}")
            continue
        verb = verbs.get(action.kind, action.kind)
        _info(f"would {verb} {action.path or action.unit}")


def _install_sidecar_dry_run(
    target: Path,
    plan_result: PlanResult,
    exclude_path: Path,
    preserved_destinations: Mapping[str, str],
) -> int:
    original_text = (
        os.fsdecode(exclude_path.read_bytes()) if exclude_path.is_file() else ""
    )
    candidate_text = _replace_exclude_block(
        original_text, plan_result.exclude_lines_write
    )
    try:
        passed, failing = run_ignore_gate(
            target,
            plan_result.gate_paths_write,
            os.fsencode(candidate_text),
            dry_run=True,
        )
    except GitCheckIgnoreError as exc:
        return _abort(str(exc), _ignore_gate_remedy())
    if not passed:
        return _abort(_describe_gate_failure(failing), _ignore_gate_remedy())
    _describe_dry_run_actions(plan_result, preserved_destinations)
    _print_report(plan_result, preserved_destinations)
    _info(
        "dry-run gate is an approximation: Git ranks info/exclude above "
        "core.excludesFile, so the real run's gate decides"
    )
    return 0


def _install_sidecar_apply(
    target: Path,
    source: Path,
    plan_result: PlanResult,
    exclude_path: Path,
    manifest_path: Path,
    staging: Path,
    preserved_destinations: Mapping[str, Path],
) -> int:
    next_manifest = plan_result.next_manifest
    if next_manifest is None:
        return _abort(
            "internal error: the plan has no next manifest to write",
            "rerun the sidecar install",
        )

    original_exclude_bytes = (
        exclude_path.read_bytes() if exclude_path.is_file() else None
    )
    write_text = _replace_exclude_block(
        os.fsdecode(original_exclude_bytes) if original_exclude_bytes else "",
        plan_result.exclude_lines_write,
    )
    write_bytes = os.fsencode(write_text)
    if write_bytes != (original_exclude_bytes or b""):
        _atomic_write(exclude_path, write_bytes)

    try:
        passed, failing = run_ignore_gate(
            target, plan_result.gate_paths_write, write_bytes, dry_run=False
        )
    except GitCheckIgnoreError as exc:
        _restore_exclude(exclude_path, original_exclude_bytes)
        return _abort(str(exc), _ignore_gate_remedy())
    if not passed:
        _restore_exclude(exclude_path, original_exclude_bytes)
        return _abort(_describe_gate_failure(failing), _ignore_gate_remedy())

    # N8: the pending manifest is on disk before any unit moves (so before
    # the "after_exclude_write" checkpoint). It is ownership evidence for
    # the bytes this run is about to place, never an intent record; the
    # next run reads it only to recognize those bytes as the sidecar's own
    # when this run is interrupted before the real manifest lands.
    manifest_bytes = serialize_manifest(next_manifest)
    pending_path = _pending_manifest_path(manifest_path)
    _atomic_write(pending_path, manifest_bytes)

    _fault_point("after_exclude_write")

    _empty_staging(staging)
    _apply_actions(target, source, staging, plan_result, preserved_destinations)

    final_text = _replace_exclude_block(write_text, plan_result.exclude_lines_final)
    final_bytes = os.fsencode(final_text)
    if final_bytes != write_bytes:
        _atomic_write(exclude_path, final_bytes)

    # Same checkpoint as every other unit action (Decision 24): every
    # preserve move has already happened, and the final exclude block is
    # already on disk, but the manifest has not landed yet.
    _fault_point("before_manifest_write")

    current_manifest_bytes = (
        manifest_path.read_bytes() if manifest_path.is_file() else None
    )
    if manifest_bytes != current_manifest_bytes:
        _atomic_write(manifest_path, manifest_bytes)
    pending_path.unlink(missing_ok=True)

    _empty_staging(staging)
    # A profile switch or a dropped unit kind can empty a folder the sidecar
    # created (for example .claude/templates on the way down to the skills
    # profile); the same empty-only cleanup as uninstall applies.
    _remove_empty_sidecar_parents(target)
    _print_report(
        plan_result, {unit: str(path) for unit, path in preserved_destinations.items()}
    )
    return 0


def _pending_manifest_path(manifest_path: Path) -> Path:
    """N8: where an in-progress run keeps the manifest it is about to
    write, next to the real one (``<gitdir>/ai-bootstrap-sidecar.json.next``)."""
    return manifest_path.with_name(f"{manifest_path.name}.next")


_LOCK_NAME = "ai-bootstrap-sidecar.lock"


def _acquire_run_lock(git_dir: Path, target: Path) -> IO[bytes] | int:
    """N12: take a non-blocking ``flock`` on ``<gitdir>/ai-bootstrap-sidecar.lock``
    for the rest of the run. Returns the open handle (closing it releases
    the lock) or an already-printed abort code. The lock file itself is
    left in place after the run: unlinking it would race with another
    starter that already opened it."""
    lock_path = git_dir / _LOCK_NAME
    try:
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o666)
    except OSError as exc:
        return _abort(f"cannot open {lock_path}: {exc.strerror}", _WRITE_FAILURE_REMEDY)
    handle = os.fdopen(fd, "rb")
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return _abort(
            f"another sidecar run is active in {target}",
            "wait for it to finish, then rerun",
        )
    except OSError as exc:
        handle.close()
        return _abort(f"cannot lock {lock_path}: {exc.strerror}", _WRITE_FAILURE_REMEDY)
    return handle


@dataclass(frozen=True)
class _TargetPreflight:
    """Everything ``install_sidecar`` and ``uninstall_sidecar`` both gather
    about ``target`` alone, before either one even looks at a source tree or
    an empty desired set."""

    git_dir_path: Path
    manifest_path: Path
    staging: Path
    exclude_path: Path
    preserved_root: Path
    manifest: Manifest | None
    index_entries: tuple[tuple[str, str], ...]
    tracked: frozenset[str]
    ignorecase: bool
    exclude_block: ExcludeBlockContents
    pending_manifest: Manifest | None = None
    """N8: the manifest an interrupted run left at ``<manifest>.next``, when
    one is there and parses; extra ownership evidence for the planner."""


def _run_target_preflight(target: Path) -> _TargetPreflight | int:
    """Run every preflight check that depends only on ``target`` (Decision
    26, 27, 28; Phase H steps 3, 4, 6), shared by ``install_sidecar`` and
    ``uninstall_sidecar``. Returns the gathered state, or an already-printed
    non-zero exit code (from ``_abort``) when a check fails -- the caller
    must return that code immediately and write nothing.
    """
    version = _git_version()
    if version is None or version < _MIN_GIT_VERSION:
        return _abort(
            f"git is older than 2.31 (found {version or 'unknown'})",
            "upgrade Git to 2.31 or newer; the sidecar needs "
            "'git rev-parse --path-format'",
        )

    toplevel = rev_parse(target, "--show-toplevel")
    git_dir = rev_parse(target, "--git-dir")
    git_common_dir = rev_parse(target, "--git-common-dir")
    if toplevel is None or git_dir is None or git_common_dir is None:
        return _abort(
            f"{target} is not a Git repository",
            "run the sidecar install from the top level of a Git worktree",
        )
    if Path(toplevel) != target:
        return _abort(
            f"{target} is not the top level of its Git worktree (toplevel is {toplevel})",
            f"rerun the sidecar install from {toplevel}",
        )
    if Path(git_dir) != Path(git_common_dir):
        return _abort(
            f"{target} is a linked worktree (--git-dir {git_dir} != "
            f"--git-common-dir {git_common_dir})",
            "run the sidecar install from the main worktree; sidecar mode "
            "does not support linked worktrees",
        )

    git_dir_path = Path(git_dir)
    if _device_id(target) != _device_id(git_dir_path):
        return _abort(
            f"the Git directory ({git_dir_path}) and the worktree ({target}) "
            "are on different filesystems",
            "the sidecar needs one filesystem for atomic moves; relocate the "
            "Git directory or the worktree onto the same filesystem",
        )

    # Every Git-directory path below is built directly from the
    # already-verified --absolute-git-dir, never through git_path()'s
    # --git-path: that resolves symlinks in the path, which would hide
    # exactly the symlink these checks exist to catch (Decision 26; S6).
    # Checked with lstat and never opened, so a named pipe is refused, not
    # read, and a dangling symlink is still caught as a symlink.
    manifest_path = git_dir_path / SIDECAR_MANIFEST_NAME
    manifest_info = _lstat_or_none(manifest_path)
    if manifest_info is not None and (
        stat.S_ISLNK(manifest_info.st_mode) or not stat.S_ISREG(manifest_info.st_mode)
    ):
        return _abort(
            f"{manifest_path} is a symlink or not a regular file",
            f"replace {manifest_path} with a regular file, or remove it, then rerun",
        )

    staging = git_dir_path / SIDECAR_STAGING_NAME
    staging_info = _lstat_or_none(staging)
    if staging_info is not None and (
        stat.S_ISLNK(staging_info.st_mode) or not stat.S_ISDIR(staging_info.st_mode)
    ):
        return _abort(
            f"{staging} is a symlink or not a folder",
            f"replace {staging} with a regular folder, or remove it, then rerun",
        )

    info_dir = git_dir_path / "info"
    info_info = _lstat_or_none(info_dir)
    if info_info is not None and (
        stat.S_ISLNK(info_info.st_mode) or not stat.S_ISDIR(info_info.st_mode)
    ):
        # N11: `info` as a symlink, or anything that is not a folder (a
        # regular file), is refused here instead of failing inside
        # _atomic_write's mkdir later.
        return _abort(
            f"{info_dir} is a symlink or not a folder",
            f"replace {info_dir} with a regular folder, then rerun",
        )

    exclude_path = info_dir / "exclude"
    exclude_info = _lstat_or_none(exclude_path)
    if exclude_info is not None and (
        stat.S_ISLNK(exclude_info.st_mode) or not stat.S_ISREG(exclude_info.st_mode)
    ):
        return _abort(
            f"{exclude_path} is a symlink or not a regular file",
            f"replace {exclude_path} with a regular file, or remove it, then rerun",
        )

    preserved_root = git_dir_path / SIDECAR_PRESERVED_NAME
    preserved_info = _lstat_or_none(preserved_root)
    if preserved_info is not None and (
        stat.S_ISLNK(preserved_info.st_mode) or not stat.S_ISDIR(preserved_info.st_mode)
    ):
        return _abort(
            f"{preserved_root} is a symlink or not a folder",
            f"replace {preserved_root} with a regular folder, or remove it, then rerun",
        )

    manifest: Manifest | None = None
    if manifest_path.is_file():
        try:
            manifest = parse_manifest(manifest_path.read_text(encoding="utf-8"))
        except (ManifestError, OSError, UnicodeDecodeError) as exc:
            return _abort(
                f"invalid sidecar manifest at {manifest_path}: {exc}",
                _invalid_manifest_remedy(manifest_path),
            )

    # N8: a pending manifest from an interrupted run is extra ownership
    # evidence only. One that does not parse is ignored here (a dry run
    # writes nothing, not even a cleanup) and removed by the next real
    # run's own end-of-apply unlink.
    pending_manifest: Manifest | None = None
    pending_path = _pending_manifest_path(manifest_path)
    pending_info = _lstat_or_none(pending_path)
    if pending_info is not None and stat.S_ISREG(pending_info.st_mode):
        with contextlib.suppress(ManifestError, OSError, UnicodeDecodeError):
            pending_manifest = parse_manifest(pending_path.read_text(encoding="utf-8"))

    index_entries = _read_index_entries(target)
    tracked = frozenset(path for _mode, path in index_entries)

    # Decision 3: a tracked path under the namespaced state root aborts
    # before any write, naming it -- unlike an ordinary team-owned unit
    # (Decision 25), which is merely skipped and reported. The state root is
    # the person's own local work; the sidecar must never plan around a
    # team member having started to track part of it.
    state_tracked = sorted(
        path
        for path in tracked
        if any(path == root or path.startswith(f"{root}/") for root in _ALL_STATE_ROOTS)
    )
    if state_tracked:
        shown = ", ".join(state_tracked[:5])
        more = "" if len(state_tracked) <= 5 else f" (+{len(state_tracked) - 5} more)"
        return _abort(
            f"the repository tracks {shown}{more} under the sidecar's "
            "namespaced state folder",
            "untrack it (`git rm -r --cached <path>`) and commit that "
            "removal, then rerun",
        )

    # Decision 28: repository boundary and filesystem shape, before any
    # other Git-state gathering or write.
    boundary_violations = _repository_boundary_violations(
        target, _SIDECAR_STRUCTURAL_PATHS, index_entries
    )
    if boundary_violations:
        return _abort(boundary_violations[0], _NESTED_REPO_REMEDY)
    shape_violations = _filesystem_shape_violations(target, _SIDECAR_STRUCTURAL_PATHS)
    if shape_violations:
        return _abort(shape_violations[0], "fix the filesystem shape, then rerun")

    ignorecase = _ignorecase(target)
    try:
        exclude_block = _read_exclude_block(exclude_path)
    except ExcludeMarkerError as exc:
        return _abort(str(exc), _EXCLUDE_MARKER_REMEDY)
    except OSError as exc:
        # N11: an exclude file the sidecar cannot read is never treated as
        # empty -- a later write would replace lines it never saw.
        return _abort(
            f"cannot read {exclude_path}: {exc.strerror}",
            f"fix the permissions of {exclude_path}, then rerun",
        )

    return _TargetPreflight(
        git_dir_path=git_dir_path,
        manifest_path=manifest_path,
        staging=staging,
        exclude_path=exclude_path,
        preserved_root=preserved_root,
        manifest=manifest,
        index_entries=index_entries,
        tracked=tracked,
        ignorecase=ignorecase,
        exclude_block=exclude_block,
        pending_manifest=pending_manifest,
    )


def install_sidecar(
    target: Path,
    source: Path,
    *,
    dry_run: bool = False,
    profile: str = SIDECAR_DEFAULT_PROFILE,
) -> int:
    """Reconcile the sidecar overlay in ``target`` from ``source`` for
    ``profile`` (Decision 1).

    Returns the process exit code: 0 on success, including per-path skips;
    non-zero when preflight aborts before any write. Implements the big
    plan's "Reconciliation rules" exactly
    (``.claude/plans/consumer-sidecar-bootstrap-overlay.md``): every
    preflight check runs, in order, before any write; the planner
    (``plan_sidecar_reconciliation``) decides every action; this function
    only gathers Git state, writes in the required order, and reports.
    """
    if profile not in SIDECAR_PROFILES:
        raise ValueError(f"unknown sidecar profile: {profile!r}")
    target = target.resolve()
    source = source.resolve()

    if not source.is_dir():
        return _abort(
            f"{source} does not exist",
            "if this is the default sidecar source, run `uv run python "
            "scripts/generate_targets.py --all` to build it; if you passed "
            f"--source, check that {source} is the path you meant",
        )
    violations = _sidecar_source_violations(source, profile)
    if violations:
        shown = ", ".join(violations[:5])
        more = "" if len(violations) <= 5 else f" (+{len(violations) - 5} more)"
        return _abort(
            f"{source} is not a sidecar tree for the {profile!r} profile: "
            f"{shown}{more}",
            "pass a source built by generate_targets.py --all "
            f"(dist/sidecar/{profile}), not a full-install tree such as "
            "dist/multi-agent or another profile's tree",
        )

    preflight = _run_target_preflight(target)
    if isinstance(preflight, int):
        return preflight
    # N12: a real run holds the cross-process lock from here to the end of
    # apply; a dry run writes nothing and takes no lock.
    lock = (
        contextlib.nullcontext()
        if dry_run
        else _acquire_run_lock(preflight.git_dir_path, target)
    )
    if isinstance(lock, int):
        return lock
    with lock:
        try:
            return _install_sidecar_planned(
                target, source, preflight, dry_run=dry_run, profile=profile
            )
        except OSError as exc:
            return _abort_write_failure(exc)


def _install_sidecar_planned(
    target: Path,
    source: Path,
    preflight: _TargetPreflight,
    *,
    dry_run: bool,
    profile: str = SIDECAR_DEFAULT_PROFILE,
) -> int:
    """``install_sidecar`` after preflight and the run lock: gather Git
    state, plan, check writability, then dry-run or apply."""
    manifest_path = preflight.manifest_path
    staging = preflight.staging
    exclude_path = preflight.exclude_path
    preserved_root = preflight.preserved_root
    manifest = preflight.manifest
    tracked = preflight.tracked
    ignorecase = preflight.ignorecase
    exclude_block = preflight.exclude_block
    gitlinks = frozenset(
        path for mode, path in preflight.index_entries if mode == "160000"
    )

    desired_units = load_desired_units(source, profile)
    required_units = required_snapshot_units(
        desired_units, manifest, exclude_block.listed_units, exclude_block.listed_files
    )
    read_list_skill_names = _read_list_skill_names(target, tracked)
    declared_skill_names = _declared_skill_names(target)
    read_list_file_names = _read_list_agent_names(target, tracked)
    # Every listed unit is already part of required_units (it was folded in
    # above), so this is exactly the set the exclude block currently lists.
    excluded_units = exclude_block.listed_units
    try:
        snapshots = _build_snapshots(
            target, required_units, tracked, ignorecase, gitlinks
        )
    except GitCheckIgnoreError as exc:
        return _abort(str(exc), "resolve the git check-ignore failure, then rerun")
    unit_shape_violations = _unit_device_violations(target, required_units, snapshots)
    if unit_shape_violations:
        return _abort(unit_shape_violations[0], "fix the filesystem shape, then rerun")

    preserved_destinations = {
        unit_path: (
            preserved_root / state_backup_slug(preserved_root)
            if unit_path in _ALL_STATE_ROOTS
            else preserved_root
            / preserved_unit_slug(
                unit_path, compute_unit_hash(snapshots[unit_path].file_hashes)
            )
        )
        for unit_path in required_units
    }
    preserved_conflicts = frozenset(
        unit_path
        for unit_path, destination in preserved_destinations.items()
        if destination.exists() or destination.is_symlink()
    )

    plan_result = plan_sidecar_reconciliation(
        desired_units=desired_units,
        manifest=manifest,
        excluded_units=excluded_units,
        read_list_skill_names=read_list_skill_names,
        snapshots=snapshots,
        listed_files=exclude_block.listed_files,
        unrecognized_lines=exclude_block.unrecognized_lines,
        declared_skill_names=declared_skill_names,
        read_list_file_names=read_list_file_names,
        ignorecase=ignorecase,
        preserved_conflicts=preserved_conflicts,
        preserved_destinations={
            unit: str(path) for unit, path in preserved_destinations.items()
        },
        pending_manifest=preflight.pending_manifest,
        profile=profile,
    )
    if plan_result.aborts:
        message = "; ".join(
            f"{abort.reason}: {abort.message}" for abort in plan_result.aborts
        )
        return _abort(message, _plan_abort_remedy(plan_result.aborts))

    unwritable = _unwritable_paths_for_actions(
        target, plan_result.actions, preflight.git_dir_path, preserved_destinations
    )
    if unwritable:
        shown = ", ".join(str(path) for path in unwritable[:5])
        return _abort(
            f"not writable: {shown}",
            "fix folder permissions (the sidecar needs write access to move "
            "or remove these folders), then rerun",
        )

    if dry_run:
        return _install_sidecar_dry_run(
            target,
            plan_result,
            exclude_path,
            {unit: str(path) for unit, path in preserved_destinations.items()},
        )
    return _install_sidecar_apply(
        target,
        source,
        plan_result,
        exclude_path,
        manifest_path,
        staging,
        preserved_destinations,
    )


# --------------------------------------------------------------------------
# Uninstall (Decision 34; the small plan's step 9)
# --------------------------------------------------------------------------


def _uninstall_write_phase_text(
    original_text: str, plan_result: PlanResult, has_block: bool
) -> str:
    """Decision 39 item 1: skip the write-phase rewrite entirely when there
    is no existing block and no line to write -- otherwise
    ``_replace_exclude_block`` would create a needless empty block where
    none existed."""
    if has_block or plan_result.exclude_lines_write:
        return _replace_exclude_block(original_text, plan_result.exclude_lines_write)
    return original_text


def _uninstall_final_exclude_text(
    write_text: str, plan_result: PlanResult, unrecognized_lines: Sequence[str]
) -> str:
    """The exclude text uninstall leaves behind once every action lands:
    the whole block removed, or just its final lines when something stays
    hidden on purpose: a preserve conflict kept a unit (Decision 34), or the
    state folder is kept and its line must survive (workflow profile,
    Decision 3)."""
    own_final_lines = [
        line
        for line in plan_result.exclude_lines_final
        if line not in set(unrecognized_lines)
    ]
    if plan_result.kept_conflicts or own_final_lines:
        return _replace_exclude_block(write_text, plan_result.exclude_lines_final)
    return _remove_exclude_block(write_text, unrecognized_lines)


def _uninstall_sidecar_dry_run(
    target: Path,
    plan_result: PlanResult,
    exclude_path: Path,
    preserved_destinations: Mapping[str, str],
    has_block: bool,
    preserved_root: Path,
    unrecognized_lines: Sequence[str] = (),
) -> int:
    """Decision 39: the same write order as install -- write the write-phase
    block, then gate exactly the paths whose lines the final block keeps
    (``gate_paths_final``, Decision 40). That set is empty whenever
    ``kept_conflicts`` is empty, so the gate trivially passes and nothing
    below depends on branching over the raw ``preserved_conflicts`` input.
    """
    original_text = (
        os.fsdecode(exclude_path.read_bytes()) if exclude_path.is_file() else ""
    )
    candidate_text = _uninstall_write_phase_text(original_text, plan_result, has_block)
    try:
        passed, failing = run_ignore_gate(
            target,
            plan_result.gate_paths_final,
            os.fsencode(candidate_text),
            dry_run=True,
        )
    except GitCheckIgnoreError as exc:
        return _abort(str(exc), _ignore_gate_remedy())
    if not passed:
        return _abort(_describe_gate_failure(failing), _ignore_gate_remedy())

    final_text = _uninstall_final_exclude_text(
        candidate_text, plan_result, unrecognized_lines
    )
    plan_result = _recheck_now_visible_reports(
        plan_result, target, dry_run=True, candidate_text=os.fsencode(final_text)
    )
    _describe_dry_run_actions(plan_result, preserved_destinations)
    _print_report(plan_result, preserved_destinations)
    _report_preserved_folder_if_nonempty(preserved_root)
    if plan_result.kept_conflicts:
        _info(
            "a preserve conflict would keep at least one unit in place; a "
            "real run would exit 1 and rewrite the manifest to hold only "
            "the kept units"
        )
        return 1
    return 0


def _uninstall_sidecar_apply(
    target: Path,
    plan_result: PlanResult,
    exclude_path: Path,
    manifest_path: Path,
    staging: Path,
    preserved_destinations: Mapping[str, Path],
    unrecognized_lines: Sequence[str],
    has_block: bool,
    preserved_root: Path,
) -> int:
    """Decision 39: uninstall on the install's write order, sharing the same
    apply step and gate rule (Decision 40). Steps below match the small
    plan's numbered rebuild exactly."""
    assert not any(
        action.kind in ("install", "update", "adopt", "seed_missing")
        for action in plan_result.actions
    ), "uninstall must never plan install, update, adopt, or seed_missing"

    original_bytes = exclude_path.read_bytes() if exclude_path.is_file() else None
    original_text = os.fsdecode(original_bytes) if original_bytes else ""

    # 1. Write the write-phase block (skipped when there is nothing to write).
    write_text = _uninstall_write_phase_text(original_text, plan_result, has_block)
    write_bytes = os.fsencode(write_text)
    if write_bytes != (original_bytes or b""):
        _atomic_write(exclude_path, write_bytes)

    # 2. Gate the uninstall gate paths (Decision 40); empty when
    # kept_conflicts is empty. Restore the exclude file on failure.
    try:
        passed, failing = run_ignore_gate(
            target, plan_result.gate_paths_final, write_bytes, dry_run=False
        )
    except GitCheckIgnoreError as exc:
        _restore_exclude(exclude_path, original_bytes)
        return _abort(str(exc), _ignore_gate_remedy())
    if not passed:
        _restore_exclude(exclude_path, original_bytes)
        return _abort(_describe_gate_failure(failing), _ignore_gate_remedy())

    # 3. Empty staging and apply actions through the same step install uses.
    # Uninstall never plans install/update/adopt (asserted above), so the
    # source tree is never actually read.
    _empty_staging(staging)
    _apply_actions(
        target, _NO_UNINSTALL_SOURCE, staging, plan_result, preserved_destinations
    )

    _fault_point("after_units_removed")

    kept_conflicts = plan_result.kept_conflicts
    # The one exception to Decision 9: a preserve conflict means the
    # uninstall did not finish, so the block survives with its final (still
    # fully computed) lines, instead of being removed.
    final_text = _uninstall_final_exclude_text(
        write_text, plan_result, unrecognized_lines
    )
    final_bytes = os.fsencode(final_text)
    if final_bytes != write_bytes:
        _atomic_write(exclude_path, final_bytes)

    _fault_point("before_manifest_write")

    # 4. When kept_conflicts is empty, remove the block, delete the
    # manifest, and remove the staging folder entirely. Otherwise the final
    # block and a manifest holding only the kept units' records survive,
    # staging is only emptied, and the run exits 1.
    next_manifest = plan_result.next_manifest
    if kept_conflicts:
        if next_manifest is None:
            return _abort(
                "internal error: the plan has no next manifest to write",
                "rerun the sidecar uninstall",
            )
        manifest_bytes = serialize_manifest(next_manifest)
        current_manifest_bytes = (
            manifest_path.read_bytes() if manifest_path.is_file() else None
        )
        if manifest_bytes != current_manifest_bytes:
            _atomic_write(manifest_path, manifest_bytes)
        _empty_staging(staging)
        exit_code = 1
    else:
        if manifest_path.is_file() or manifest_path.is_symlink():
            manifest_path.unlink()
        if staging.exists() and not staging.is_symlink():
            shutil.rmtree(staging)
        _remove_empty_sidecar_parents(target)
        exit_code = 0
    # N8: a pending manifest from an interrupted install or update is
    # ownership evidence only; nothing is pending any more.
    _pending_manifest_path(manifest_path).unlink(missing_ok=True)

    # N16: info/exclude on disk already holds final_bytes (written above, or
    # unchanged because it already matched), so this checks the real file.
    plan_result = _recheck_now_visible_reports(plan_result, target, dry_run=False)
    _print_report(
        plan_result, {unit: str(path) for unit, path in preserved_destinations.items()}
    )
    _report_preserved_folder_if_nonempty(preserved_root)
    if exit_code == 1:
        _info(
            "a preserve conflict kept at least one unit in place; resolve "
            "it by hand, then rerun --uninstall"
        )
    return exit_code


def uninstall_sidecar(
    target: Path, *, dry_run: bool = False, purge_state: bool = False
) -> int:
    """Remove the sidecar overlay from ``target`` entirely (Decision 34; the
    small plan's step 9).

    Reconciles Phase G's planner (``plan_sidecar_reconciliation``) against
    an empty desired set, with ``uninstall=True`` so every sidecar skill and
    bridge is treated as taken: a unit whose content matches its record is
    removed; a locally modified or unfinished unit -- including a bridge --
    is preserved (Decision 24); team and foreign content is never touched;
    every retained file loses its line and becomes visible, reported as now
    visible to ``git add -A``; a block line the sidecar never understood
    survives as a plain line where the block was. Runs through the same
    target-only preflight as ``install_sidecar`` (steps 3, 4, 6).

    The namespaced state root (Decision 3) is the one unit this does not
    apply to: kept in place and hidden by default (reported, never removed),
    or moved into the preserved-copy folder and un-hidden when
    ``purge_state`` is set.

    Returns 0 on a clean uninstall, including when there was nothing to do;
    1 when a preserve conflict kept a unit in place -- the one exception to
    Decision 9, because the uninstall did not finish.
    """
    target = target.resolve()

    preflight = _run_target_preflight(target)
    if isinstance(preflight, int):
        return preflight
    preserved_root = preflight.preserved_root
    manifest = preflight.manifest
    exclude_block = preflight.exclude_block

    if manifest is None and not exclude_block.has_block:
        # The same "is a sidecar present" definition sidecar_evidence uses
        # for detection (Decision 27; S18): a manifest, or any balanced
        # block at all -- even an empty one, or one that holds only
        # unrecognized lines. Anything narrower here leaves a dead end
        # where detection sends --uninstall a target it then refuses to
        # touch.
        _report_preserved_folder_if_nonempty(preserved_root)
        _info("no sidecar found; nothing to do")
        return 0

    # N12: a real run holds the cross-process lock from here to the end of
    # apply; a dry run writes nothing and takes no lock.
    lock = (
        contextlib.nullcontext()
        if dry_run
        else _acquire_run_lock(preflight.git_dir_path, target)
    )
    if isinstance(lock, int):
        return lock
    with lock:
        try:
            return _uninstall_sidecar_planned(
                target, preflight, dry_run=dry_run, purge_state=purge_state
            )
        except OSError as exc:
            return _abort_write_failure(exc)


def _uninstall_sidecar_planned(
    target: Path,
    preflight: _TargetPreflight,
    *,
    dry_run: bool,
    purge_state: bool = False,
) -> int:
    """``uninstall_sidecar`` after preflight and the run lock: gather Git
    state, plan, check writability, then dry-run or apply."""
    manifest_path = preflight.manifest_path
    staging = preflight.staging
    exclude_path = preflight.exclude_path
    preserved_root = preflight.preserved_root
    manifest = preflight.manifest
    tracked = preflight.tracked
    ignorecase = preflight.ignorecase
    exclude_block = preflight.exclude_block

    required_units = (
        required_snapshot_units(
            {}, manifest, exclude_block.listed_units, exclude_block.listed_files
        )
        | frozenset(
            f"{write_root}/{skill}"
            for write_root in _ALL_SKILL_WRITE_ROOTS
            for skill in SIDECAR_SKILLS
        )
        | frozenset(_ALL_BRIDGES)
    )
    gitlinks = frozenset(
        path for mode, path in preflight.index_entries if mode == "160000"
    )
    try:
        snapshots = _build_snapshots(
            target, required_units, tracked, ignorecase, gitlinks
        )
    except GitCheckIgnoreError as exc:
        return _abort(str(exc), "resolve the git check-ignore failure, then rerun")
    unit_shape_violations = _unit_device_violations(target, required_units, snapshots)
    if unit_shape_violations:
        return _abort(unit_shape_violations[0], "fix the filesystem shape, then rerun")

    preserved_destinations = {
        unit_path: (
            preserved_root / state_backup_slug(preserved_root)
            if unit_path in _ALL_STATE_ROOTS
            else preserved_root
            / preserved_unit_slug(
                unit_path, compute_unit_hash(snapshots[unit_path].file_hashes)
            )
        )
        for unit_path in required_units
    }
    preserved_conflicts = frozenset(
        unit_path
        for unit_path, destination in preserved_destinations.items()
        if destination.exists() or destination.is_symlink()
    )

    plan_result = plan_sidecar_reconciliation(
        desired_units={},
        manifest=manifest,
        excluded_units=exclude_block.listed_units,
        read_list_skill_names={},
        snapshots=snapshots,
        listed_files=exclude_block.listed_files,
        unrecognized_lines=exclude_block.unrecognized_lines,
        ignorecase=ignorecase,
        preserved_conflicts=preserved_conflicts,
        preserved_destinations={
            unit: str(path) for unit, path in preserved_destinations.items()
        },
        uninstall=True,
        purge_state=purge_state,
        pending_manifest=preflight.pending_manifest,
    )
    if plan_result.aborts:
        message = "; ".join(
            f"{abort.reason}: {abort.message}" for abort in plan_result.aborts
        )
        return _abort(message, _plan_abort_remedy(plan_result.aborts))

    unwritable = _unwritable_paths_for_actions(
        target, plan_result.actions, preflight.git_dir_path, preserved_destinations
    )
    if unwritable:
        shown = ", ".join(str(path) for path in unwritable[:5])
        return _abort(
            f"not writable: {shown}",
            "fix folder permissions (the sidecar needs write access to move "
            "or remove these folders), then rerun",
        )

    display_destinations = {
        unit: str(path) for unit, path in preserved_destinations.items()
    }
    if dry_run:
        return _uninstall_sidecar_dry_run(
            target,
            plan_result,
            exclude_path,
            display_destinations,
            exclude_block.has_block,
            preserved_root,
            exclude_block.unrecognized_lines,
        )
    return _uninstall_sidecar_apply(
        target,
        plan_result,
        exclude_path,
        manifest_path,
        staging,
        preserved_destinations,
        exclude_block.unrecognized_lines,
        exclude_block.has_block,
        preserved_root,
    )


def backup_sidecar_state(target: Path, *, dry_run: bool = False) -> int:
    """``--backup-state``: copy the namespaced state folder into the
    preserved-copy folder, changing nothing else (Decision 3; the small
    plan's step 6). A standalone action, unlike install or uninstall: no
    manifest read or write, no reconciliation, no exclude-block change.
    With ``dry_run`` it only reports the copy it would make.

    Returns 0 whether or not the folder exists; a missing folder is
    reported, not an error. Raises ``subprocess.CalledProcessError`` when
    ``target`` is not a Git repository, for the caller to turn into a clean
    message the same way every other Git-repository check here does.
    """
    target = target.resolve()
    git_dir = Path(_git_rev_parse_or_raise(target, "--git-dir"))
    preserved_root = git_dir / SIDECAR_PRESERVED_NAME
    backed_up_any = False
    for state_root in sorted(_ALL_STATE_ROOTS):
        state_path = target / PurePosixPath(state_root)
        if not state_path.is_dir() or state_path.is_symlink():
            continue
        destination = preserved_root / state_backup_slug(preserved_root)
        if dry_run:
            _info(f"would back up {state_path} -> {destination}")
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(state_path, destination)
            _info(f"backed up {state_path} -> {destination}")
        backed_up_any = True
    if not backed_up_any:
        _info("no state folder found; nothing to back up")
    return 0
