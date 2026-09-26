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
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence, Set as AbstractSet
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Literal

from runtime_ownership import (
    SIDECAR_BRIDGES,
    SIDECAR_EXCLUDE_BEGIN,
    SIDECAR_EXCLUDE_END,
    SIDECAR_MANIFEST_NAME,
    SIDECAR_PRESERVED_NAME,
    SIDECAR_RETIRED_BRIDGES,
    SIDECAR_RETIRED_SKILL_WRITE_ROOTS,
    SIDECAR_SKILL_READ_ROOTS,
    SIDECAR_SKILL_WRITE_ROOTS,
    SIDECAR_SKILLS,
    SIDECAR_STAGING_NAME,
)
from runtime_ownership import sidecar_source_violations as _shared_source_violations

KNOWN_SCHEMA_VERSION = 1
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_READ_ONLY_ROOTS = tuple(
    root for root in SIDECAR_SKILL_READ_ROOTS if root not in SIDECAR_SKILL_WRITE_ROOTS
)
_ESCAPE_CHARS = frozenset("\\*?[")

# Every write root and bridge-parent folder (Decision 28): the structural
# boundary and filesystem-shape preflight checks these, rather than every
# individual skill unit. A unit path that does not exist yet always resolves
# to one of these through the nearest-existing-ancestor walk, so this is
# equivalent for every currently required test scenario at a fraction of the
# Git calls.
# ponytail: a unit that already exists on disk as its own nested clone,
# without its write root also being one, is not covered; extend this set to
# every required unit path if that scenario needs the same abort.
_SIDECAR_STRUCTURAL_PATHS: frozenset[str] = frozenset(
    SIDECAR_SKILL_WRITE_ROOTS
) | frozenset(str(PurePosixPath(bridge).parent) for bridge in SIDECAR_BRIDGES)

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
    """The parsed sidecar manifest (schema_version 1).

    ``retained`` holds only the paths of files kept alongside a team-taken
    unit (Decision 16); no hash is stored for them because no decision reads
    one back, and the ledger is recomputed from the live snapshot each run.
    """

    schema_version: int
    units: Mapping[str, ManifestUnit]
    retained: frozenset[str]


# Manifest validation accepts the current write roots and bridges plus any
# retired ones (Decision 32): a recorded unit outside the current desired set
# still goes through the normal remove row instead of failing schema
# validation the moment a bridge or write root is retired.
_ALL_SKILL_WRITE_ROOTS = SIDECAR_SKILL_WRITE_ROOTS + SIDECAR_RETIRED_SKILL_WRITE_ROOTS
_ALL_BRIDGES = frozenset(SIDECAR_BRIDGES) | frozenset(SIDECAR_RETIRED_BRIDGES)


def _validate_unit_path(unit_path: str) -> None:
    pure = PurePosixPath(unit_path)
    if not unit_path or "\\" in unit_path or pure.is_absolute() or ".." in pure.parts:
        raise ManifestError(f"unsafe unit path: {unit_path!r}")
    if unit_path in _ALL_BRIDGES:
        return
    for write_root in _ALL_SKILL_WRITE_ROOTS:
        prefix = f"{write_root}/"
        if unit_path.startswith(prefix):
            remainder = unit_path[len(prefix) :]
            if remainder and "/" not in remainder and remainder not in (".", ".."):
                return
    raise ManifestError(f"unit path outside the sidecar namespace: {unit_path!r}")


def _validate_retained_path(path: str) -> None:
    pure = PurePosixPath(path)
    if not path or "\\" in path or pure.is_absolute() or ".." in pure.parts:
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
    if schema_version != KNOWN_SCHEMA_VERSION:
        raise ManifestError(f"unknown schema_version: {schema_version!r}")

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
    )


def serialize_manifest(manifest: Manifest) -> bytes:
    """Render the manifest deterministically: sorted keys, trailing newline.

    An unchanged ``Manifest`` always re-serializes to identical bytes, so the
    caller can skip the write when nothing changed.
    """
    payload = {
        "schema_version": manifest.schema_version,
        "units": {
            unit_path: {"files": dict(record.files), "hash": record.hash}
            for unit_path, record in manifest.units.items()
        },
        "retained": sorted(manifest.retained),
    }
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


def load_desired_units(source_root: Path) -> dict[str, DesiredUnit]:
    """Read the desired sidecar units from a generated tree (``dist/sidecar/``).

    This is the one allowed reader: it only reads files under ``source_root``
    and turns them into data. It never writes anything.
    """
    units: dict[str, DesiredUnit] = {}
    for write_root in SIDECAR_SKILL_WRITE_ROOTS:
        for skill in SIDECAR_SKILLS:
            skill_dir = source_root / write_root / skill
            if not skill_dir.is_dir():
                continue
            files = _hash_tree(skill_dir)
            if files:
                units[f"{write_root}/{skill}"] = DesiredUnit(
                    files=files, hash=compute_unit_hash(files)
                )
    for bridge_path in SIDECAR_BRIDGES:
        file_path = source_root / bridge_path
        if file_path.is_file():
            files = {
                PurePosixPath(bridge_path).name: compute_file_hash(
                    file_path.read_bytes()
                )
            }
            units[bridge_path] = DesiredUnit(files=files, hash=compute_unit_hash(files))
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
    index entry such as a gitlink), whether or not it currently exists on
    disk. It therefore is not a subset of ``file_hashes``: a deleted tracked
    file stays in ``tracked_files`` but never appears in ``file_hashes``.
    ``file_hashes`` covers every file present at the unit path on disk,
    relative to the unit itself (tracked and untracked alike). ``symlinked``
    means an ancestor directory of the unit is a symlink (always an abort);
    a symlink at the unit path itself is not ancestor-symlinked and is
    instead classified as team-owned (tracked) or foreign (untracked).
    ``ignored_files`` is a relative-path subset of ``file_hashes``.
    """

    exists: bool = False
    symlinked: bool = False
    tracked_files: frozenset[str] = frozenset()
    file_hashes: Mapping[str, str] = field(default_factory=dict)
    ignored_files: frozenset[str] = frozenset()

    @property
    def untracked_files(self) -> frozenset[str]:
        return frozenset(self.file_hashes) - self.tracked_files


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


def required_snapshot_units(
    desired_units: Mapping[str, DesiredUnit],
    manifest: Manifest | None,
    excluded_units: AbstractSet[str] = frozenset(),
) -> frozenset[str]:
    """Return every unit path the caller must snapshot for this run.

    This is the union of the desired units, the manifest's recorded units,
    the owning unit of every ``retained`` file, and every unit the sidecar's
    own exclude block lists (``excluded_units``, Decision 23), so a skill
    dropped from the profile or a unit whose record was already dropped by
    a team takeover -- or a unit whose record was lost with the manifest --
    is still classified and cleaned up correctly instead of silently
    un-hidden.
    """
    units: set[str] = set(desired_units) | set(excluded_units)
    if manifest is not None:
        units.update(manifest.units)
        for path in manifest.retained:
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
    markers = _find_exclude_markers(text.splitlines())
    if markers is None:
        return ExcludeBlockContents()
    begin, end = markers
    listed_units: set[str] = set()
    listed_files: set[str] = set()
    unrecognized: list[str] = []
    for line in text.splitlines()[begin + 1 : end]:
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


def _skill_name(unit_path: str) -> str | None:
    for write_root in SIDECAR_SKILL_WRITE_ROOTS:
        prefix = f"{write_root}/"
        if unit_path.startswith(prefix):
            return unit_path[len(prefix) :]
    return None


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
    unit_path: str, tracked_relpaths: AbstractSet[str] = frozenset()
) -> str:
    skill = _skill_name(unit_path)
    tracked_path = _representative_tracked_path(unit_path, tracked_relpaths)
    if skill is None:
        return f"the repository tracks `{tracked_path}`; the sidecar does not install this bridge"
    return f"the repository tracks `{tracked_path}`; the sidecar skips `{skill}` at every root"


def _read_only_taken_remedy(path: str, skill: str) -> str:
    return f"the repository has `{path}`; the sidecar skips `{skill}` at every root"


def _locally_modified_remedy(path: str, *, skill_still_shipped: bool) -> str:
    if skill_still_shipped:
        return (
            f"`{path}` has local edits, so the sidecar keeps it. A pull can "
            "overwrite hidden files without warning. To take the current "
            f"version, copy your edits elsewhere, delete `{path}`, and rerun"
        )
    skill = _skill_name(path) or path
    return (
        f"`{path}` has local edits and the sidecar no longer ships `{skill}`; "
        f"copy your edits elsewhere, then delete `{path}`"
    )


def _unfinished_remedy(path: str) -> str:
    return (
        f"`{path}` is an unfinished sidecar copy that the sidecar cannot "
        "verify. It stays hidden. Copy anything you need from it, delete "
        "it, and rerun"
    )


def _foreign_remedy(unit_path: str) -> str:
    skill = _skill_name(unit_path)
    if skill is None:
        return (
            f"the sidecar will not replace `{unit_path}`; rename or remove "
            "it only if you do not need it"
        )
    return (
        f"the sidecar will not replace `{unit_path}` and skips `{skill}` at "
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


def _unrecognized_line_remedy(line: str) -> str:
    return (
        f"the sidecar does not recognize `{line}` in its own exclude block "
        "and keeps it; move it outside the block to keep it, or delete it "
        "if you do not need it"
    )


def _preserved_remedy(unit_path: str) -> str:
    skill = _skill_name(unit_path) or unit_path
    return (
        f"the repository now uses `{skill}`, so your edited copy was moved "
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
) -> _UnitOutcome:
    """Classify a tracked unit as a team takeover (Decision 16, 23, 25).

    An untracked file is recognized as the sidecar's own -- and deleted --
    when its bytes match the manifest record *or* the desired content
    (Decision 23): a crash during an update can leave a stale record while
    the swap already landed the new bytes, and a unit that is merely listed
    (no record yet) has only the desired content as its ownership reference.

    ``uninstall`` (Decision 34): a file that would otherwise be retained
    (kept hidden) instead gets no line at all and the "now visible" report,
    the same as every other already-retained file during an uninstall --
    even when this run is the very first one to see this team takeover.
    """
    record_files = record.files if record is not None else {}
    desired_files = desired.files if desired is not None else {}
    actions: list[Action] = []
    if record is not None:
        actions.append(Action("drop_record", unit_path))
    reports: list[Report] = [
        Report(
            "SKIPPED",
            unit_path,
            _team_owned_remedy(unit_path, snapshot.tracked_files),
        )
    ]
    retained_here: set[str] = set()
    for relpath in sorted(snapshot.untracked_files):
        full_path = f"{unit_path}/{relpath}"
        current_hash = snapshot.file_hashes[relpath]
        if record_files.get(relpath) == current_hash or (
            desired_files.get(relpath) == current_hash
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


def _classify_unit(
    unit_path: str,
    snapshot: UnitSnapshot,
    record: ManifestUnit | None,
    desired: DesiredUnit | None,
    excluded_units: AbstractSet[str],
    uninstall: bool = False,
) -> _UnitOutcome:
    if snapshot.tracked_files:
        if record is not None or unit_path in excluded_units:
            # Tracked, and either recorded or merely listed (Decision 23):
            # team takeover either way. A listed-only unit uses the desired
            # content as its ownership reference.
            return _team_takeover(unit_path, snapshot, record, desired, uninstall)
        report = Report(
            "SKIPPED", unit_path, _team_owned_remedy(unit_path, snapshot.tracked_files)
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

    current_hash = compute_unit_hash(snapshot.file_hashes)
    if record is not None and current_hash == record.hash:
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
        desired is not None
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

    report = Report("SKIPPED", unit_path, _foreign_remedy(unit_path))
    return _UnitOutcome("foreign", None, [], [report], frozenset(), False, False)


# --------------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------------


def _case_variant_taking_paths(
    skill: str,
    read_list_skill_names: Mapping[str, AbstractSet[str]],
    ignorecase: bool,
) -> tuple[str, ...]:
    """Return every read-list path whose entry is a case variant of
    ``skill`` (Decision 22), when ``core.ignorecase`` is true. Covers every
    read root, including the write roots: a case-variant folder there is a
    different filesystem entry the sidecar must never touch."""
    if not ignorecase:
        return ()
    paths: list[str] = []
    for root in SIDECAR_SKILL_READ_ROOTS:
        for name in sorted(read_list_skill_names.get(root, frozenset())):
            if name != skill and name.casefold() == skill.casefold():
                paths.append(f"{root}/{name}")
    return tuple(paths)


def _extra_taking_paths(
    skill: str,
    read_list_skill_names: Mapping[str, AbstractSet[str]],
    declared_skill_names: Mapping[str, AbstractSet[str]],
    ignorecase: bool,
) -> frozenset[str]:
    """Return every path -- besides the skill's own write-root units, which
    self-report through their own classification -- that takes ``skill``
    (Decision 22): an exact name in a read-only folder, a case variant in
    any read folder, or a non-sidecar ``SKILL.md`` frontmatter declaration.

    ``declared_skill_names`` includes the sidecar's own write-root entries
    (it declares its own name too); they are removed by the same trailing
    subtraction that already removes the skill's own write-root units from
    every other source here, so a team or foreign declaration under a
    different folder name is never hidden behind the sidecar's own entry.
    """
    paths: set[str] = set()
    for root in _READ_ONLY_ROOTS:
        if skill in read_list_skill_names.get(root, frozenset()):
            paths.add(f"{root}/{skill}")
    paths.update(_case_variant_taking_paths(skill, read_list_skill_names, ignorecase))
    paths.update(declared_skill_names.get(skill, frozenset()))
    paths -= {f"{write_root}/{skill}" for write_root in SIDECAR_SKILL_WRITE_ROOTS}
    return frozenset(paths)


def _preserved_uninstall_remedy(unit_path: str) -> str:
    skill = _skill_name(unit_path) or unit_path
    return f"the sidecar was uninstalled, so your edited copy of `{skill}` was moved out of the client folders"


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
            _preserved_uninstall_remedy(unit_path)
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
    unrecognized_lines: AbstractSet[str] = frozenset(),
    declared_skill_names: Mapping[str, AbstractSet[str]] | None = None,
    ignorecase: bool = False,
    preserved_conflicts: AbstractSet[str] = frozenset(),
    preserved_destinations: Mapping[str, str] | None = None,
    uninstall: bool = False,
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
            or a file line. Kept in the block and reported every run (as
            ``RETAINED``), so a hand-inserted line, or a line the sidecar no
            longer understands, is never silently dropped -- that could
            un-hide the file it was hiding.
        declared_skill_names: Skill name -> every read-list path whose
            ``SKILL.md`` frontmatter ``name:`` declares it, including the
            sidecar's own write-root entries (Decision 22, L3). This
            function removes the sidecar's own write-root paths from the
            result, the same way it already does for the other taking-path
            sources, so a team or foreign declaration under a different
            folder name is never hidden behind the sidecar's own entry.
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
            with no record, no exclude line, and nothing on disk.

    Returns:
        A ``PlanResult``. When ``aborts`` is non-empty, every other field is
        empty: the caller must not write anything.
    """
    declared_skill_names = declared_skill_names or {}
    preserved_destinations = preserved_destinations or {}

    required = required_snapshot_units(desired_units, manifest, excluded_units)
    if uninstall:
        required = (
            required
            | frozenset(
                f"{write_root}/{skill}"
                for write_root in SIDECAR_SKILL_WRITE_ROOTS
                for skill in SIDECAR_SKILLS
            )
            | frozenset(SIDECAR_BRIDGES)
        )
    symlinked = sorted(
        unit for unit in required if snapshots.get(unit, UnitSnapshot()).symlinked
    )
    if symlinked:
        message = "symlinked unit or ancestor: " + ", ".join(symlinked)
        return PlanResult(aborts=(Abort("symlink", message),))

    outcomes: dict[str, _UnitOutcome] = {}
    for unit_path in required:
        snapshot = snapshots.get(unit_path, UnitSnapshot())
        record = manifest.units.get(unit_path) if manifest is not None else None
        desired = desired_units.get(unit_path)
        outcomes[unit_path] = _classify_unit(
            unit_path, snapshot, record, desired, excluded_units, uninstall
        )

    # One precedence decision per skill (Decision 22): a skill is taken by
    # non-sidecar content at a write root (already self-reporting through
    # its own outcome above), an exact or case-variant name on the read
    # list, or a frontmatter declaration. Every taking path is reported.
    taken_by_write_root: set[str] = set()
    for skill in SIDECAR_SKILLS:
        for write_root in SIDECAR_SKILL_WRITE_ROOTS:
            outcome = outcomes.get(f"{write_root}/{skill}")
            if outcome is not None and outcome.kind in (
                "team_owned",
                "team_takeover",
                "foreign",
            ):
                taken_by_write_root.add(skill)
                break

    taken_skills: set[str] = set(taken_by_write_root)
    extra_reports: list[Report] = []
    for skill in SIDECAR_SKILLS:
        extra_paths = _extra_taking_paths(
            skill, read_list_skill_names, declared_skill_names, ignorecase
        )
        if not extra_paths:
            continue
        taken_skills.add(skill)
        for path in sorted(extra_paths):
            extra_reports.append(
                Report("SKIPPED", path, _read_only_taken_remedy(path, skill))
            )

    if uninstall:
        # Decision 34: every skill and every bridge is taken, so the exact
        # same conversion a taken skill's units already get (remove/preserve/
        # noop) applies uniformly, including to bridges, which the ordinary
        # taken-skill precedence never touches.
        taken_skills = set(SIDECAR_SKILLS)
    taken_units = {
        f"{write_root}/{skill}"
        for skill in taken_skills
        for write_root in SIDECAR_SKILL_WRITE_ROOTS
    }
    if uninstall:
        taken_units |= set(_ALL_BRIDGES)
    for unit_path in taken_units:
        outcome = outcomes.get(unit_path)
        if outcome is None or outcome.kind in _ALLOWED_TAKEN_OUTCOMES:
            continue
        outcomes[unit_path] = _convert_for_taken_skill(
            unit_path,
            outcome,
            preserved_conflicts,
            preserved_destinations,
            uninstall=uninstall,
        )

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
        if owner_outcome is not None and owner_outcome.kind == "team_takeover":
            continue
        owner_snapshot = (
            snapshots.get(owner, UnitSnapshot()) if owner else UnitSnapshot()
        )
        relpath = path[len(owner) + 1 :] if owner else path
        if (
            relpath in owner_snapshot.tracked_files
            or relpath not in owner_snapshot.file_hashes
        ):
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
    for unit_path, outcome in sorted(outcomes.items()):
        actions.extend(outcome.actions)
        reports.extend(outcome.reports)
        if outcome.record is not None:
            next_units[unit_path] = outcome.record
        if outcome.line_write:
            exclude_write.add(unit_exclude_line(unit_path))
        if outcome.line_final:
            exclude_final.add(unit_exclude_line(unit_path))
        for action in outcome.actions:
            if (
                action.kind in ("team_takeover_delete", "retain")
                and action.path is not None
            ):
                exclude_write.add(escape_exact_path(action.path))
                if action.kind == "retain":
                    exclude_final.add(escape_exact_path(action.path))

    actions.extend(retained_actions)
    reports.extend(retained_reports)
    for path in retained_line_paths:
        exclude_write.add(escape_exact_path(path))
        exclude_final.add(escape_exact_path(path))

    # Decision 23 / the big plan's exclude-block rules: keep any line the
    # sidecar does not understand, and report it once, every run, so a run
    # never un-hides a file through a line it does not recognize.
    for line in sorted(unrecognized_lines):
        exclude_write.add(line)
        exclude_final.add(line)
        reports.append(Report("RETAINED", line, _unrecognized_line_remedy(line)))

    next_manifest = Manifest(
        schema_version=KNOWN_SCHEMA_VERSION,
        units=next_units,
        retained=frozenset(next_retained),
    )

    return PlanResult(
        aborts=(),
        actions=tuple(actions),
        reports=tuple(sorted(reports, key=lambda item: (item.category, item.path))),
        next_manifest=next_manifest,
        exclude_lines_write=tuple(sorted(exclude_write)),
        exclude_lines_final=tuple(sorted(exclude_final)),
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
        lines = os.fsdecode(exclude.read_bytes()).splitlines()
        if _find_exclude_markers(lines) is not None:
            evidence.append(f"sidecar block in {exclude}")
    return tuple(evidence)


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

    Uninstall (Decision 34) reuses ``"before_manifest_write"`` for its own,
    same-named last step (the manifest is deleted or rewritten there
    instead of written fresh), and adds ``"after_units_removed"``: every
    unit has been removed or preserved, but the exclude block still holds
    its pre-uninstall bytes.
    """


def _info(message: str) -> None:
    print(f"sidecar-install: {message}")


def _abort(evidence: str, remedy: str) -> int:
    print(f"sidecar-install: ABORT: {evidence}", file=sys.stderr)
    print(f"sidecar-install: {remedy}", file=sys.stderr)
    return 1


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
    target: Path, actions: Sequence[Action]
) -> tuple[Path, ...]:
    """Decision 28: every folder a planned action must move, replace, or
    empty needs write access -- the parent of every unit that moves, every
    unit folder that itself moves, and every folder inside a unit that is
    removed, replaced, or later emptied from staging. Checked with
    ``os.access`` before any write.

    A unit's parent that does not exist yet (a fresh install under a write
    root nobody has created on this run) is not itself checked: ``mkdir``
    creates it later, so its nearest *existing* ancestor is what must be
    writable instead.
    """
    check: set[Path] = set()
    for action in actions:
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


def _sidecar_source_violations(source: Path) -> tuple[str, ...]:
    """Return every way ``source`` fails the exact sidecar source contract
    (Decision 31; S13, S14, L2): a plain set comparison of every file found
    in ``source`` against ``sidecar_source_exact_allowlist()``, so a missing
    or extra path of any kind is reported. Shares its logic with the
    generated-target validator (``sidecar_source_violations`` in
    ``runtime_ownership.py``), so a crafted tree gets the same verdict from
    both."""
    present = frozenset(
        file_path.relative_to(source).as_posix()
        for file_path in sorted(source.rglob("*"))
        if file_path.is_file()
    )
    return _shared_source_violations(present)


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
    UTF-8, so a legal but non-UTF-8 Git path never crashes the run."""
    if not paths:
        return frozenset()
    payload = os.fsencode("\0".join(paths) + "\0")
    result = subprocess.run(
        ["git", "-C", str(target), "check-ignore", "--stdin", "-z"],
        input=payload,
        capture_output=True,
        check=False,
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
        for path in tracked_paths:
            compare = path.casefold() if ignorecase else path
            if compare == target_unit:
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


def _gather_unit(target: Path, unit_path: str) -> tuple[bool, bool, dict[str, str]]:
    """Return ``(exists, ancestor_symlinked, {relpath: sha256})`` for one
    unit from the worktree alone. The caller adds index-derived
    ``tracked_files`` separately (Decision 25).

    ``relpath`` matches ``load_desired_units``'s convention: the file's own
    name for a bridge, or its path relative to the skill directory. A skill
    folder that holds only subfolders -- no file, symlink, pipe, or socket
    at any depth -- counts as absent: an empty leftover folder is not a
    reason to skip reinstalling a skill.
    """
    ancestor_symlinked = _is_symlinked_ancestor(target, unit_path)
    full_path = target / PurePosixPath(unit_path)
    if unit_path in _ALL_BRIDGES:
        if full_path.is_symlink() or not full_path.is_file():
            exists = full_path.exists() or full_path.is_symlink()
            return exists, ancestor_symlinked, {}
        name = PurePosixPath(unit_path).name
        return (
            True,
            ancestor_symlinked,
            {name: compute_file_hash(full_path.read_bytes())},
        )
    if full_path.is_symlink() or not full_path.is_dir():
        exists = full_path.exists() or full_path.is_symlink()
        return exists, ancestor_symlinked, {}
    files: dict[str, str] = {}
    has_content = False
    inner_symlinked = False
    for entry in sorted(full_path.rglob("*")):
        if entry.is_symlink():
            has_content = True
            inner_symlinked = True
        elif entry.is_file():
            has_content = True
            files[entry.relative_to(full_path).as_posix()] = compute_file_hash(
                entry.read_bytes()
            )
        elif not entry.is_dir():
            has_content = True  # a pipe, socket, or other special file
    return has_content, ancestor_symlinked or inner_symlinked, files


def _build_snapshots(
    target: Path,
    required_units: AbstractSet[str],
    tracked: AbstractSet[str],
    ignorecase: bool = False,
) -> dict[str, UnitSnapshot]:
    """Snapshot every required unit with one batched ``check-ignore`` call.

    ``tracked_files`` comes from the Git index (``tracked``), independent of
    disk presence (Decision 25); ``file_hashes`` still comes from the
    worktree alone.
    """
    raw = {unit_path: _gather_unit(target, unit_path) for unit_path in required_units}
    tracked_by_unit: dict[str, frozenset[str]] = {
        unit_path: _unit_index_relpaths(
            unit_path, tracked, ignorecase, frozenset(raw[unit_path][2])
        )
        for unit_path in required_units
    }
    candidates: list[str] = []
    for unit_path, (_exists, _symlinked, file_hashes) in raw.items():
        unit_tracked = tracked_by_unit[unit_path]
        candidates.extend(
            _full_relpath(unit_path, relpath)
            for relpath in file_hashes
            if relpath not in unit_tracked
        )
    ignored_now = _check_ignore(target, candidates)
    snapshots: dict[str, UnitSnapshot] = {}
    for unit_path, (exists, symlinked, file_hashes) in raw.items():
        unit_tracked = tracked_by_unit[unit_path]
        unit_ignored = frozenset(
            relpath
            for relpath in file_hashes
            if relpath not in unit_tracked
            and _full_relpath(unit_path, relpath) in ignored_now
        )
        snapshots[unit_path] = UnitSnapshot(
            exists=exists,
            symlinked=symlinked,
            tracked_files=unit_tracked,
            file_hashes=file_hashes,
            ignored_files=unit_ignored,
        )
    return snapshots


def _resolve_or_none(path: Path) -> Path | None:
    try:
        return path.resolve()
    except OSError:
        return None


def _reflects_a_write_root(target: Path, path: Path) -> bool:
    """Return whether ``path`` resolves into one of the sidecar's own write
    roots, so a symlinked read-only folder that mirrors a write root (the
    common ``.github/skills -> ../.claude/skills`` layout) is never treated
    as holding non-sidecar content (Decision 22): the alternative would
    alternate install, remove, install every run."""
    resolved = _resolve_or_none(path)
    if resolved is None:
        return False
    for write_root in SIDECAR_SKILL_WRITE_ROOTS:
        write_real = _resolve_or_none(target / PurePosixPath(write_root))
        if write_real is None:
            continue
        if resolved == write_real or write_real in resolved.parents:
            return True
    return False


def _read_list_skill_names(
    target: Path, index_paths: AbstractSet[str]
) -> dict[str, frozenset[str]]:
    """Return the skill directory names present in each read-list folder,
    from the index and the disk together (Decision 25).

    Lists a symlinked read folder through its link, unless the link
    resolves into a write root, and skips any entry that itself resolves
    into a write root (Decision 22).
    """
    names: dict[str, frozenset[str]] = {}
    for root in SIDECAR_SKILL_READ_ROOTS:
        root_path = target / PurePosixPath(root)
        disk_names: set[str] = set()
        if root_path.is_dir() and not _reflects_a_write_root(target, root_path):
            for entry in root_path.iterdir():
                if not (entry.is_dir() or entry.is_symlink()):
                    continue
                if _reflects_a_write_root(target, entry):
                    continue
                disk_names.add(entry.name)
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
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return None
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
    frontmatter ``name:`` declares it (Decision 22, L3). Opens only a
    regular file (``lstat``-checked) and reads at most 4 KB.

    Every declaring path is kept, including the sidecar's own write-root
    unit (which declares its own name): a first-wins map would let the
    sidecar's own entry, scanned first, silently hide a team or foreign
    folder under a different name that declares the same skill.
    ``_extra_taking_paths`` is what removes the sidecar's own write-root
    paths from the result, the same way it already does for the read-list
    name and case-variant checks.
    """
    declared: dict[str, set[str]] = {}
    for root in sorted(SIDECAR_SKILL_READ_ROOTS):
        root_path = target / PurePosixPath(root)
        if not root_path.is_dir() or root_path.is_symlink():
            continue
        for entry in sorted(root_path.iterdir()):
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
            name = _parse_frontmatter_name(data)
            if name:
                declared.setdefault(name, set()).add(f"{root}/{entry.name}")
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
    except (FileNotFoundError, NotADirectoryError, OSError):
        return ExcludeBlockContents()
    return parse_exclude_block(os.fsdecode(data))


# --------------------------------------------------------------------------
# Exclude-file rendering and atomic writes
# --------------------------------------------------------------------------


def _replace_exclude_block(original_text: str, lines: Sequence[str]) -> str:
    """Return ``original_text`` with exactly one sidecar block set to
    ``lines``. Preserves every byte (including line endings) outside the
    ``BEGIN``/``END`` markers."""
    block_text = "\n".join([SIDECAR_EXCLUDE_BEGIN, *lines, SIDECAR_EXCLUDE_END]) + "\n"
    file_lines = original_text.splitlines(keepends=True)
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
    file_lines = original_text.splitlines(keepends=True)
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
    """Write ``data`` to ``path`` via a same-directory temp file + ``os.replace``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(tmp_name, path)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise


def _gate_spelling(path: str) -> str:
    """Return the ignore-gate spelling for one path (Decision 30): a skill
    unit is gated as a folder, ``<unit>/``, so a team rule ending in ``/``
    still applies before the folder exists. Bridges and individual files are
    gated as themselves."""
    if path in _ALL_BRIDGES:
        return path
    for write_root in SIDECAR_SKILL_WRITE_ROOTS:
        prefix = f"{write_root}/"
        if path.startswith(prefix) and "/" not in path[len(prefix) :]:
            return f"{path}/"
    return path


def _write_raw_paths(plan_result: PlanResult) -> frozenset[str]:
    """Return the gate spelling of every path the write-phase exclude block
    must hide, reconstructed from the plan's public actions and next
    manifest (Decision 30: skill units are gated as folders)."""
    paths: set[str] = set()
    if plan_result.next_manifest is not None:
        paths.update(plan_result.next_manifest.units)
        paths.update(plan_result.next_manifest.retained)
    paths.update(
        action.unit
        for action in plan_result.actions
        if action.kind in ("remove", "preserve")
    )
    paths.update(
        action.path
        for action in plan_result.actions
        if action.kind == "team_takeover_delete" and action.path is not None
    )
    return frozenset(_gate_spelling(path) for path in paths)


# --------------------------------------------------------------------------
# The ignore gate (Decision 17)
# --------------------------------------------------------------------------


_NO_MATCHING_RULE = (
    "no matching rule (visible); a rule ending in `/` in a .gitignore file or "
    "in info/exclude may be un-ignoring the folder (Git cannot name a "
    "directory-only rule for a path that does not exist yet)"
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
        return False, _parse_check_ignore_verbose(verbose.stdout, expected)
    finally:
        if temp_excludes_file is not None:
            temp_excludes_file.unlink(missing_ok=True)


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


def _empty_staging(staging: Path) -> None:
    if staging.exists() and not staging.is_symlink():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)


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
        # "adopt", "unchanged", "retain", and "drop_record" touch no file:
        # the content already matches, the file already sits where it
        # belongs, or only the manifest record changes.


def _apply_uninstall_actions(
    target: Path,
    staging: Path,
    plan_result: PlanResult,
    preserved_destinations: Mapping[str, Path],
) -> None:
    """Apply an uninstall plan's unit-level actions (Decision 34). An empty
    desired set can never produce "install", "update", or "adopt" -- those
    rows all require desired content -- so only remove, preserve, and
    team_takeover_delete can appear; this never needs a source tree to copy
    from, unlike ``_apply_actions``."""
    for action in plan_result.actions:
        if action.kind == "remove":
            _remove_unit(target, staging, action.unit)
        elif action.kind == "team_takeover_delete":
            _delete_file(target, action.path)
        elif action.kind == "preserve":
            _preserve_unit(target, preserved_destinations[action.unit], action.unit)
        # "retain" and "drop_record" touch no file.


def _count_actions(plan_result: PlanResult) -> dict[str, int]:
    counts = {
        "install": 0,
        "update": 0,
        "remove": 0,
        "adopt": 0,
        "unchanged": 0,
        "preserve": 0,
    }
    for action in plan_result.actions:
        if action.kind in counts:
            counts[action.kind] += 1
    return counts


def _print_report(
    plan_result: PlanResult, preserved_destinations: Mapping[str, str] | None = None
) -> None:
    """Print the run's summary and one line per removed, deleted, or
    preserved path, plus every SKIPPED/RETAINED/PRESERVED report (S15: a
    real run must name what a takeover deleted, not only count it)."""
    preserved_destinations = preserved_destinations or {}
    counts = _count_actions(plan_result)
    _info(
        f"installed {counts['install']}, updated {counts['update']}, "
        f"removed {counts['remove']}, adopted {counts['adopt']}, "
        f"unchanged {counts['unchanged']}, preserved {counts['preserve']}"
    )
    for action in plan_result.actions:
        if action.kind == "remove":
            _info(f"removed {action.unit}")
        elif action.kind == "team_takeover_delete" and action.path is not None:
            _info(f"deleted {action.path}")
        elif action.kind == "preserve":
            destination = preserved_destinations.get(action.unit, "")
            _info(f"PRESERVED {action.unit} -> {destination}")
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
    write_paths = sorted(_write_raw_paths(plan_result))
    passed, failing = run_ignore_gate(
        target, write_paths, os.fsencode(candidate_text), dry_run=True
    )
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

    write_paths = sorted(_write_raw_paths(plan_result))
    passed, failing = run_ignore_gate(target, write_paths, write_bytes, dry_run=False)
    if not passed:
        _restore_exclude(exclude_path, original_exclude_bytes)
        return _abort(_describe_gate_failure(failing), _ignore_gate_remedy())

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

    manifest_bytes = serialize_manifest(next_manifest)
    current_manifest_bytes = (
        manifest_path.read_bytes() if manifest_path.is_file() else None
    )
    if manifest_bytes != current_manifest_bytes:
        _atomic_write(manifest_path, manifest_bytes)

    _empty_staging(staging)
    _print_report(
        plan_result, {unit: str(path) for unit, path in preserved_destinations.items()}
    )
    return 0


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
    if info_dir.is_symlink():
        return _abort(
            f"{info_dir} is a symlink",
            f"replace the symlink at {info_dir} with a regular folder, then rerun",
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

    index_entries = _read_index_entries(target)
    tracked = frozenset(path for _mode, path in index_entries)

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
    )


def install_sidecar(target: Path, source: Path, *, dry_run: bool = False) -> int:
    """Reconcile the sidecar overlay in ``target`` from ``source``.

    Returns the process exit code: 0 on success, including per-path skips;
    non-zero when preflight aborts before any write. Implements the big
    plan's "Reconciliation rules" exactly
    (``.claude/plans/consumer-sidecar-bootstrap-overlay.md``): every
    preflight check runs, in order, before any write; the planner
    (``plan_sidecar_reconciliation``) decides every action; this function
    only gathers Git state, writes in the required order, and reports.
    """
    target = target.resolve()
    source = source.resolve()

    if not source.is_dir():
        return _abort(
            f"{source} does not exist",
            "if this is the default sidecar source, run `uv run python "
            "scripts/generate_targets.py --all` to build it; if you passed "
            f"--source, check that {source} is the path you meant",
        )
    violations = _sidecar_source_violations(source)
    if violations:
        shown = ", ".join(violations[:5])
        more = "" if len(violations) <= 5 else f" (+{len(violations) - 5} more)"
        return _abort(
            f"{source} is not a sidecar tree: {shown}{more}",
            "pass a source built by generate_targets.py --all (dist/sidecar), "
            "not a full-install tree such as dist/multi-agent",
        )

    preflight = _run_target_preflight(target)
    if isinstance(preflight, int):
        return preflight
    manifest_path = preflight.manifest_path
    staging = preflight.staging
    exclude_path = preflight.exclude_path
    preserved_root = preflight.preserved_root
    manifest = preflight.manifest
    tracked = preflight.tracked
    ignorecase = preflight.ignorecase
    exclude_block = preflight.exclude_block

    desired_units = load_desired_units(source)
    required_units = required_snapshot_units(
        desired_units, manifest, exclude_block.listed_units
    )
    read_list_skill_names = _read_list_skill_names(target, tracked)
    declared_skill_names = _declared_skill_names(target)
    # Every listed unit is already part of required_units (it was folded in
    # above), so this is exactly the set the exclude block currently lists.
    excluded_units = exclude_block.listed_units
    snapshots = _build_snapshots(target, required_units, tracked, ignorecase)

    preserved_destinations = {
        unit_path: preserved_root
        / preserved_unit_slug(
            unit_path, compute_unit_hash(snapshots[unit_path].file_hashes)
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
        unrecognized_lines=frozenset(exclude_block.unrecognized_lines),
        declared_skill_names=declared_skill_names,
        ignorecase=ignorecase,
        preserved_conflicts=preserved_conflicts,
        preserved_destinations={
            unit: str(path) for unit, path in preserved_destinations.items()
        },
    )
    if plan_result.aborts:
        message = "; ".join(
            f"{abort.reason}: {abort.message}" for abort in plan_result.aborts
        )
        return _abort(
            message,
            "sidecar mode does not support a symlinked skill folder or "
            "projection parent; nothing was written",
        )

    unwritable = _unwritable_paths_for_actions(target, plan_result.actions)
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


def _uninstall_conflict_pre_write_gate(
    target: Path,
    plan_result: PlanResult,
    preserved_conflicts: AbstractSet[str],
    original_bytes: bytes | None,
) -> tuple[bool, tuple[tuple[str, str], ...]]:
    """Decision 17: before touching anything, re-prove that every unit this
    run leaves untouched -- every conflicting kept unit, whatever its
    outcome shape (recorded, unfinished, or a bridge), and every unit still
    mid-removal, since nothing has moved yet -- is still actually hidden by
    the exclude file exactly as it already stands, not merely assumed
    correct from an earlier run.

    ``preserved_conflicts`` is checked directly, not read back from
    ``plan_result``: an unfinished conflicting unit converts to an outcome
    with no action and no manifest record (Decision 23: it has no record to
    begin with), so ``_write_raw_paths`` alone would silently miss it.
    ``dry_run=False``: checks the real, as-yet-unwritten file directly,
    which is correct in a real run (nothing has been written yet either)
    and in a dry run (nothing ever is).
    """
    must_be_ignored = _write_raw_paths(plan_result) | {
        _gate_spelling(unit) for unit in preserved_conflicts
    }
    return run_ignore_gate(
        target, sorted(must_be_ignored), original_bytes or b"", dry_run=False
    )


def _uninstall_conflict_post_rewrite_gate(
    target: Path,
    preserved_conflicts: AbstractSet[str],
    candidate_bytes: bytes,
    *,
    dry_run: bool,
) -> tuple[bool, tuple[tuple[str, str], ...]]:
    """Decision 17: after computing the rewritten block, re-prove it still
    hides every conflicting kept unit -- the rewrite only ever drops the
    removed units' lines, but this proves that rather than assumes it.

    Built from ``preserved_conflicts`` directly, for the same reason as
    ``_uninstall_conflict_pre_write_gate``: ``plan_result.next_manifest.units``
    only holds units with a manifest record, which an unfinished conflicting
    unit never has.
    """
    kept_paths = sorted(_gate_spelling(unit) for unit in preserved_conflicts)
    return run_ignore_gate(target, kept_paths, candidate_bytes, dry_run=dry_run)


def _uninstall_sidecar_dry_run(
    target: Path,
    plan_result: PlanResult,
    exclude_path: Path,
    preserved_destinations: Mapping[str, str],
    preserved_conflicts: AbstractSet[str],
) -> int:
    if preserved_conflicts:
        original_bytes = exclude_path.read_bytes() if exclude_path.is_file() else None
        passed, failing = _uninstall_conflict_pre_write_gate(
            target, plan_result, preserved_conflicts, original_bytes
        )
        if not passed:
            return _abort(_describe_gate_failure(failing), _ignore_gate_remedy())

        original_text = os.fsdecode(original_bytes) if original_bytes else ""
        final_text = _replace_exclude_block(
            original_text, plan_result.exclude_lines_final
        )
        final_bytes = os.fsencode(final_text)
        passed, failing = _uninstall_conflict_post_rewrite_gate(
            target, preserved_conflicts, final_bytes, dry_run=True
        )
        if not passed:
            return _abort(_describe_gate_failure(failing), _ignore_gate_remedy())

    _describe_dry_run_actions(plan_result, preserved_destinations)
    _print_report(plan_result, preserved_destinations)
    if preserved_conflicts:
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
    preserved_conflicts: AbstractSet[str],
) -> int:
    next_manifest = plan_result.next_manifest
    if next_manifest is None:
        return _abort(
            "internal error: the plan has no next manifest to write",
            "rerun the sidecar uninstall",
        )

    original_bytes = exclude_path.read_bytes() if exclude_path.is_file() else None
    if preserved_conflicts:
        passed, failing = _uninstall_conflict_pre_write_gate(
            target, plan_result, preserved_conflicts, original_bytes
        )
        if not passed:
            return _abort(_describe_gate_failure(failing), _ignore_gate_remedy())

    # Decision 34's order: move or remove every unit first (units that are
    # merely kept in place on a preserve conflict are untouched here), only
    # then touch the block, then the manifest, then empty staging.
    _empty_staging(staging)
    _apply_uninstall_actions(target, staging, plan_result, preserved_destinations)

    _fault_point("after_units_removed")

    original_text = os.fsdecode(original_bytes) if original_bytes else ""
    if preserved_conflicts:
        # The one exception to Decision 9: a preserve conflict means the
        # uninstall did not finish, so the block survives -- rewritten the
        # same way an ordinary run rewrites it -- instead of being removed.
        final_text = _replace_exclude_block(
            original_text, plan_result.exclude_lines_final
        )
    else:
        final_text = _remove_exclude_block(original_text, unrecognized_lines)
    final_bytes = os.fsencode(final_text)
    if final_bytes != (original_bytes or b""):
        _atomic_write(exclude_path, final_bytes)

    if preserved_conflicts:
        passed, failing = _uninstall_conflict_post_rewrite_gate(
            target, preserved_conflicts, final_bytes, dry_run=False
        )
        if not passed:
            _restore_exclude(exclude_path, original_bytes)
            return _abort(_describe_gate_failure(failing), _ignore_gate_remedy())

    _fault_point("before_manifest_write")

    if preserved_conflicts:
        manifest_bytes = serialize_manifest(next_manifest)
        current_manifest_bytes = (
            manifest_path.read_bytes() if manifest_path.is_file() else None
        )
        if manifest_bytes != current_manifest_bytes:
            _atomic_write(manifest_path, manifest_bytes)
        exit_code = 1
    else:
        if manifest_path.is_file() or manifest_path.is_symlink():
            manifest_path.unlink()
        exit_code = 0

    # Decision 34's own last step: remove the staging folder entirely
    # (unlike install/update, which only empty it -- an uninstall promises
    # no sidecar file, block, manifest, or staging folder remains).
    if staging.exists() and not staging.is_symlink():
        shutil.rmtree(staging)
    _print_report(
        plan_result, {unit: str(path) for unit, path in preserved_destinations.items()}
    )
    if exit_code == 1:
        _info(
            "a preserve conflict kept at least one unit in place; resolve "
            "it by hand, then rerun --uninstall"
        )
    return exit_code


def uninstall_sidecar(target: Path, *, dry_run: bool = False) -> int:
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

    Returns 0 on a clean uninstall, including when there was nothing to do;
    1 when a preserve conflict kept a unit in place -- the one exception to
    Decision 9, because the uninstall did not finish.
    """
    target = target.resolve()

    preflight = _run_target_preflight(target)
    if isinstance(preflight, int):
        return preflight
    manifest_path = preflight.manifest_path
    staging = preflight.staging
    exclude_path = preflight.exclude_path
    preserved_root = preflight.preserved_root
    manifest = preflight.manifest
    tracked = preflight.tracked
    ignorecase = preflight.ignorecase
    exclude_block = preflight.exclude_block

    if manifest is None and not exclude_block.has_block:
        # The same "is a sidecar present" definition sidecar_evidence uses
        # for detection (Decision 27; S18): a manifest, or any balanced
        # block at all -- even an empty one, or one that holds only
        # unrecognized lines. Anything narrower here leaves a dead end
        # where detection sends --uninstall a target it then refuses to
        # touch.
        _info("no sidecar found; nothing to do")
        return 0

    required_units = (
        required_snapshot_units({}, manifest, exclude_block.listed_units)
        | frozenset(
            f"{write_root}/{skill}"
            for write_root in SIDECAR_SKILL_WRITE_ROOTS
            for skill in SIDECAR_SKILLS
        )
        | frozenset(SIDECAR_BRIDGES)
    )
    snapshots = _build_snapshots(target, required_units, tracked, ignorecase)

    preserved_destinations = {
        unit_path: preserved_root
        / preserved_unit_slug(
            unit_path, compute_unit_hash(snapshots[unit_path].file_hashes)
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
        unrecognized_lines=frozenset(exclude_block.unrecognized_lines),
        ignorecase=ignorecase,
        preserved_conflicts=preserved_conflicts,
        preserved_destinations={
            unit: str(path) for unit, path in preserved_destinations.items()
        },
        uninstall=True,
    )
    if plan_result.aborts:
        message = "; ".join(
            f"{abort.reason}: {abort.message}" for abort in plan_result.aborts
        )
        return _abort(
            message,
            "sidecar mode does not support a symlinked skill folder or "
            "projection parent; nothing was written",
        )

    unwritable = _unwritable_paths_for_actions(target, plan_result.actions)
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
            preserved_conflicts,
        )
    return _uninstall_sidecar_apply(
        target,
        plan_result,
        exclude_path,
        manifest_path,
        staging,
        preserved_destinations,
        exclude_block.unrecognized_lines,
        preserved_conflicts,
    )
