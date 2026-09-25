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
  file, sorted by its POSIX path relative to the unit, hash the UTF-8 relative
  path, a NUL byte, the file's own SHA-256 hex digest (ASCII), and a newline;
  concatenate those records in sorted order and hash the result. The NUL
  cannot appear in a POSIX relative path and the digest is a fixed-width hex
  string, so no relative path or digest can be crafted to collide across the
  framing boundary.
* A **manifest** records, per unit, its per-file hashes and its unit hash,
  plus the paths of any ``retained`` files (Decision 16, paths only: no
  decision reads a stored hash for them, since a retained file's ledger
  entry is recomputed from the live snapshot on every run) and a diagnostic
  ``bootstrap_commit`` that no decision in this module reads.

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
    SIDECAR_SKILL_READ_ROOTS,
    SIDECAR_SKILL_WRITE_ROOTS,
    SIDECAR_SKILLS,
    SIDECAR_STAGING_NAME,
)

KNOWN_SCHEMA_VERSION = 1
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_READ_ONLY_ROOTS = tuple(
    root for root in SIDECAR_SKILL_READ_ROOTS if root not in SIDECAR_SKILL_WRITE_ROOTS
)
_ESCAPE_CHARS = frozenset("\\*?[")

ActionKind = Literal[
    "install",
    "update",
    "remove",
    "adopt",
    "drop_record",
    "team_takeover_delete",
    "retain",
    "unchanged",
]
ReportCategory = Literal["SKIPPED", "RETAINED"]


class ManifestError(ValueError):
    """The sidecar manifest is unreadable, malformed, or names an unsafe path."""


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
        hasher.update(relpath.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(files[relpath].encode("ascii"))
        hasher.update(b"\n")
    return hasher.hexdigest()


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
    bootstrap_commit: str
    units: Mapping[str, ManifestUnit]
    retained: frozenset[str]


def _validate_unit_path(unit_path: str) -> None:
    pure = PurePosixPath(unit_path)
    if not unit_path or pure.is_absolute() or ".." in pure.parts:
        raise ManifestError(f"unsafe unit path: {unit_path!r}")
    if unit_path in SIDECAR_BRIDGES:
        return
    for write_root in SIDECAR_SKILL_WRITE_ROOTS:
        prefix = f"{write_root}/"
        if unit_path.startswith(prefix):
            remainder = unit_path[len(prefix) :]
            if remainder and "/" not in remainder and remainder not in (".", ".."):
                return
    raise ManifestError(f"unit path outside the sidecar namespace: {unit_path!r}")


def _validate_retained_path(path: str) -> None:
    pure = PurePosixPath(path)
    if not path or pure.is_absolute() or ".." in pure.parts:
        raise ManifestError(f"unsafe retained path: {path!r}")
    for write_root in SIDECAR_SKILL_WRITE_ROOTS:
        prefix = f"{write_root}/"
        if path.startswith(prefix):
            remainder = path[len(prefix) :].split("/", 1)
            if len(remainder) == 2 and remainder[0] and remainder[1]:
                return
    raise ManifestError(f"retained path outside a sidecar unit: {path!r}")


def _owning_unit(path: str) -> str | None:
    """Return the skill unit path that contains a retained file, if any."""
    for write_root in SIDECAR_SKILL_WRITE_ROOTS:
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

    bootstrap_commit = raw.get("bootstrap_commit", "")
    if not isinstance(bootstrap_commit, str):
        raise ManifestError("bootstrap_commit must be a string")

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
        bootstrap_commit=bootstrap_commit,
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
        "bootstrap_commit": manifest.bootstrap_commit,
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

    ``file_hashes`` covers every file present at the unit path, relative to
    the unit itself (tracked and untracked alike). ``tracked_files`` and
    ``ignored_files`` are relative-path subsets of ``file_hashes``.
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
    desired_units: Mapping[str, DesiredUnit], manifest: Manifest | None
) -> frozenset[str]:
    """Return every unit path the caller must snapshot for this run.

    This is the union of the desired units, the manifest's recorded units,
    and the owning unit of every ``retained`` file, so a skill dropped from
    the profile or a unit whose record was already dropped by a team
    takeover is still classified and cleaned up correctly.
    """
    units: set[str] = set(desired_units)
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


# --------------------------------------------------------------------------
# Remedies (exact wording from the big plan)
# --------------------------------------------------------------------------


def _skill_name(unit_path: str) -> str | None:
    for write_root in SIDECAR_SKILL_WRITE_ROOTS:
        prefix = f"{write_root}/"
        if unit_path.startswith(prefix):
            return unit_path[len(prefix) :]
    return None


def _team_owned_remedy(unit_path: str) -> str:
    skill = _skill_name(unit_path)
    if skill is None:
        return (
            f"the repository tracks `{unit_path}`; the sidecar skips it at every root"
        )
    return f"the repository tracks `{unit_path}`; the sidecar skips `{skill}` at every root"


def _read_only_taken_remedy(folder: str, skill: str) -> str:
    return f"the repository has `{folder}/{skill}`; the sidecar skips `{skill}` at every root"


def _locally_modified_remedy(path: str) -> str:
    return f"delete or restore `{path}`, then rerun to take the current version"


def _foreign_remedy(path: str) -> str:
    return f"the sidecar will not replace `{path}`; rename or remove it only if it is not needed"


def _retained_remedy(path: str) -> str:
    return f"`{path}` was left behind when the repository started tracking its folder; delete it or commit it"


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
    unit_path: str, snapshot: UnitSnapshot, record: ManifestUnit
) -> _UnitOutcome:
    actions: list[Action] = [Action("drop_record", unit_path)]
    reports: list[Report] = [
        Report("SKIPPED", unit_path, _team_owned_remedy(unit_path))
    ]
    retained_here: set[str] = set()
    for relpath in sorted(snapshot.untracked_files):
        full_path = f"{unit_path}/{relpath}"
        current_hash = snapshot.file_hashes[relpath]
        if record.files.get(relpath) == current_hash:
            actions.append(Action("team_takeover_delete", unit_path, full_path))
        elif relpath in snapshot.ignored_files:
            actions.append(Action("retain", unit_path, full_path))
            retained_here.add(full_path)
            reports.append(Report("RETAINED", full_path, _retained_remedy(full_path)))
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
) -> _UnitOutcome:
    if snapshot.tracked_files:
        if record is not None:
            return _team_takeover(unit_path, snapshot, record)
        report = Report("SKIPPED", unit_path, _team_owned_remedy(unit_path))
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
        and unit_path in excluded_units
    ):
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
        report = Report("SKIPPED", unit_path, _locally_modified_remedy(unit_path))
        return _UnitOutcome(
            "locally_modified", record, [], [report], frozenset(), True, True
        )

    report = Report("SKIPPED", unit_path, _foreign_remedy(unit_path))
    return _UnitOutcome("foreign", None, [], [report], frozenset(), False, False)


# --------------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------------


def plan_sidecar_reconciliation(
    *,
    desired_units: Mapping[str, DesiredUnit],
    manifest: Manifest | None,
    excluded_units: AbstractSet[str],
    read_list_skill_names: Mapping[str, AbstractSet[str]],
    snapshots: Mapping[str, UnitSnapshot],
    bootstrap_commit: str = "",
) -> PlanResult:
    """Plan one sidecar reconciliation run. Performs no I/O.

    Args:
        desired_units: The content the sidecar wants, keyed by unit path
            (see ``load_desired_units``).
        manifest: The previously parsed manifest, or ``None`` on a fresh
            install.
        excluded_units: The unit paths the sidecar's own exclude block
            currently lists (Decision 10: adoption needs this).
        read_list_skill_names: For every read-list folder (Decision 8, the
            keys of ``SIDECAR_SKILL_READ_ROOTS``), the skill names found
            there (directory names; presence only, no hashing needed).
        snapshots: A ``UnitSnapshot`` for every unit in
            ``required_snapshot_units(desired_units, manifest)``. A unit
            missing here is treated as absent (safe default: it plans as an
            install rather than as a destructive guess).
        bootstrap_commit: A diagnostic value carried into the next manifest.
            No decision here reads it back.

    Returns:
        A ``PlanResult``. When ``aborts`` is non-empty, every other field is
        empty: the caller must not write anything.
    """
    required = required_snapshot_units(desired_units, manifest)
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
            unit_path, snapshot, record, desired, excluded_units
        )

    # Skill-level anti-shadowing (Decision 8): a skill name taken by
    # non-sidecar content anywhere on the read list is skipped everywhere. A
    # write-root takeover already carries its own SKIPPED report from
    # ``_classify_unit``/``_team_takeover``; a read-only-folder-only takeover
    # has no unit of its own to report from, so it gets one report here.
    taken_skills: set[str] = set()
    taken_by_write_root: set[str] = set()
    for skill in SIDECAR_SKILLS:
        for write_root in SIDECAR_SKILL_WRITE_ROOTS:
            outcome = outcomes.get(f"{write_root}/{skill}")
            if outcome is not None and outcome.kind in (
                "team_owned",
                "team_takeover",
                "foreign",
            ):
                taken_skills.add(skill)
                taken_by_write_root.add(skill)
                break

    read_only_reports: list[Report] = []
    for skill in SIDECAR_SKILLS:
        folder = next(
            (
                root
                for root in _READ_ONLY_ROOTS
                if skill in read_list_skill_names.get(root, ())
            ),
            None,
        )
        if folder is None:
            continue
        taken_skills.add(skill)
        if skill not in taken_by_write_root:
            read_only_reports.append(
                Report(
                    "SKIPPED",
                    f"{folder}/{skill}",
                    _read_only_taken_remedy(folder, skill),
                )
            )

    for skill in taken_skills:
        for write_root in SIDECAR_SKILL_WRITE_ROOTS:
            unit_path = f"{write_root}/{skill}"
            outcome = outcomes.get(unit_path)
            if outcome is None:
                continue
            if outcome.kind in ("unchanged", "update"):
                outcomes[unit_path] = _UnitOutcome(
                    "remove",
                    None,
                    [Action("remove", unit_path)],
                    [],
                    frozenset(),
                    True,
                    False,
                )
            elif outcome.kind == "install":
                outcomes[unit_path] = _UnitOutcome(
                    "noop", None, [], [], frozenset(), False, False
                )

    # Carry forward previously retained files whose owning unit is not
    # undergoing a fresh team takeover this run (that unit's own outcome
    # already made the authoritative retain/delete decision above).
    next_retained: set[str] = set()
    retained_reports: list[Report] = []
    retained_actions: list[Action] = []
    retained_line_paths: set[str] = set()
    if manifest is not None:
        for path in sorted(manifest.retained):
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
            next_retained.add(path)
            retained_line_paths.add(path)
            retained_reports.append(Report("RETAINED", path, _retained_remedy(path)))

    for outcome in outcomes.values():
        next_retained.update(outcome.retained_here)

    actions: list[Action] = []
    reports: list[Report] = list(read_only_reports)
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

    next_manifest = Manifest(
        schema_version=KNOWN_SCHEMA_VERSION,
        bootstrap_commit=bootstrap_commit,
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


def git_path(target: Path, name: str) -> Path:
    """Return the absolute path of a Git-directory file of ``target``.

    ``--path-format=absolute`` matters: plain ``--git-path`` prints a relative
    path in the main worktree. ``info/exclude`` resolves to the common Git
    directory, shared by every worktree; the manifest is per worktree.
    """
    result = subprocess.run(
        [
            "git",
            "-C",
            str(target),
            "rev-parse",
            "--path-format=absolute",
            "--git-path",
            name,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return Path(result.stdout.removesuffix("\n"))


def sidecar_evidence(target: Path) -> tuple[str, ...]:
    """Describe the sidecar evidence in ``target``, or return ``()``.

    Evidence is a manifest file at the Git-directory path, valid or not, or
    the sidecar marker block in ``info/exclude``.
    """
    evidence = []
    manifest = git_path(target, SIDECAR_MANIFEST_NAME)
    if manifest.exists() or manifest.is_symlink():
        evidence.append(f"sidecar manifest {manifest}")
    exclude = git_path(target, "info/exclude")
    try:
        lines = exclude.read_text(encoding="utf-8").splitlines()
    except (FileNotFoundError, NotADirectoryError):
        lines = []
    if SIDECAR_EXCLUDE_BEGIN in lines:
        evidence.append(f"sidecar block in {exclude}")
    return tuple(evidence)


_GIT_VERSION_RE = re.compile(r"git version (\d+)\.(\d+)(?:\.(\d+))?")
_MIN_GIT_VERSION = (2, 31, 0)

_INVALID_MANIFEST_REMEDY = (
    "move the manifest aside and rerun with --mode sidecar. Units that the "
    "exclude block lists and that match current content are adopted. Any "
    "other sidecar file is reported as foreign and stops being ignored."
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


def _is_sidecar_unit_file(relative: str) -> bool:
    """Return whether a source-relative file path belongs to the sidecar."""
    if relative in SIDECAR_BRIDGES:
        return True
    for write_root in SIDECAR_SKILL_WRITE_ROOTS:
        prefix = f"{write_root}/"
        if relative.startswith(prefix):
            skill, _, rest = relative[len(prefix) :].partition("/")
            if skill in SIDECAR_SKILLS and rest:
                return True
    return False


def _sidecar_source_violations(source: Path) -> tuple[str, ...]:
    """Return every file under ``source`` outside the sidecar namespace."""
    return tuple(
        relative
        for relative in (
            file_path.relative_to(source).as_posix()
            for file_path in sorted(source.rglob("*"))
            if file_path.is_file()
        )
        if not _is_sidecar_unit_file(relative)
    )


def _is_symlinked_path_or_ancestor(target: Path, relative: str) -> bool:
    current = target
    for part in PurePosixPath(relative).parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


# --------------------------------------------------------------------------
# Gathering planner inputs with Git
# --------------------------------------------------------------------------


def _tracked_files(target: Path) -> frozenset[str]:
    result = subprocess.run(
        ["git", "-C", str(target), "ls-files", "-z"],
        capture_output=True,
        check=True,
    )
    return frozenset(
        part.decode("utf-8") for part in result.stdout.split(b"\0") if part
    )


def _check_ignore(target: Path, paths: Sequence[str]) -> frozenset[str]:
    """Return the subset of ``paths`` that ``git check-ignore`` reports as
    currently ignored. Uses ``--stdin -z`` so an unusual name (embedded
    newline, non-ASCII byte) round-trips exactly."""
    if not paths:
        return frozenset()
    payload = ("\0".join(paths) + "\0").encode("utf-8")
    result = subprocess.run(
        ["git", "-C", str(target), "check-ignore", "--stdin", "-z"],
        input=payload,
        capture_output=True,
        check=False,
    )
    return frozenset(
        part.decode("utf-8") for part in result.stdout.split(b"\0") if part
    )


def _full_relpath(unit_path: str, relpath: str) -> str:
    """Return a unit-relative file path as a path relative to the worktree."""
    return unit_path if unit_path in SIDECAR_BRIDGES else f"{unit_path}/{relpath}"


def _gather_unit(target: Path, unit_path: str) -> tuple[bool, bool, dict[str, str]]:
    """Return ``(exists, symlinked, {relpath: sha256})`` for one unit on disk.

    ``relpath`` matches ``load_desired_units``'s convention: the file's own
    name for a bridge, or its path relative to the skill directory.
    """
    symlinked = _is_symlinked_path_or_ancestor(target, unit_path)
    full_path = target / PurePosixPath(unit_path)
    if unit_path in SIDECAR_BRIDGES:
        if full_path.is_symlink() or not full_path.is_file():
            exists = full_path.exists() or full_path.is_symlink()
            return exists, symlinked or full_path.is_symlink(), {}
        name = PurePosixPath(unit_path).name
        return True, symlinked, {name: compute_file_hash(full_path.read_bytes())}
    if full_path.is_symlink() or not full_path.is_dir():
        exists = full_path.exists() or full_path.is_symlink()
        return exists, symlinked or full_path.is_symlink(), {}
    files: dict[str, str] = {}
    any_symlink = symlinked
    for entry in sorted(full_path.rglob("*")):
        if entry.is_symlink():
            any_symlink = True
        elif entry.is_file():
            files[entry.relative_to(full_path).as_posix()] = compute_file_hash(
                entry.read_bytes()
            )
    return True, any_symlink, files


def _build_snapshots(
    target: Path,
    required_units: AbstractSet[str],
    tracked: AbstractSet[str],
) -> dict[str, UnitSnapshot]:
    """Snapshot every required unit with one batched ``check-ignore`` call."""
    raw = {unit_path: _gather_unit(target, unit_path) for unit_path in required_units}
    tracked_by_unit: dict[str, frozenset[str]] = {}
    candidates: list[str] = []
    for unit_path, (_exists, _symlinked, file_hashes) in raw.items():
        unit_tracked = frozenset(
            relpath
            for relpath in file_hashes
            if _full_relpath(unit_path, relpath) in tracked
        )
        tracked_by_unit[unit_path] = unit_tracked
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


def _read_list_skill_names(target: Path) -> dict[str, frozenset[str]]:
    """Return the skill directory names present in each read-list folder."""
    names: dict[str, frozenset[str]] = {}
    for root in SIDECAR_SKILL_READ_ROOTS:
        root_path = target / PurePosixPath(root)
        if root_path.is_dir() and not root_path.is_symlink():
            names[root] = frozenset(
                entry.name
                for entry in root_path.iterdir()
                if entry.is_dir() and not entry.is_symlink()
            )
        else:
            names[root] = frozenset()
    return names


def _extract_sidecar_block_lines(text: str) -> list[str]:
    lines = text.splitlines()
    try:
        begin = lines.index(SIDECAR_EXCLUDE_BEGIN)
        end = lines.index(SIDECAR_EXCLUDE_END, begin + 1)
    except ValueError:
        return []
    return lines[begin + 1 : end]


def _excluded_units(
    exclude_path: Path, candidate_units: AbstractSet[str]
) -> frozenset[str]:
    """Return which of ``candidate_units`` the sidecar's own exclude block
    currently lists (Decision 10: adoption needs this)."""
    try:
        text = exclude_path.read_text(encoding="utf-8")
    except (FileNotFoundError, NotADirectoryError, OSError):
        return frozenset()
    lines = set(_extract_sidecar_block_lines(text))
    return frozenset(
        unit_path
        for unit_path in candidate_units
        if unit_exclude_line(unit_path) in lines
    )


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


def _write_raw_paths(plan_result: PlanResult) -> frozenset[str]:
    """Return the real (unescaped) paths the write-phase exclude block must
    hide, reconstructed from the plan's public actions and next manifest."""
    paths: set[str] = set()
    if plan_result.next_manifest is not None:
        paths.update(plan_result.next_manifest.units)
        paths.update(plan_result.next_manifest.retained)
    paths.update(
        action.unit for action in plan_result.actions if action.kind == "remove"
    )
    paths.update(
        action.path
        for action in plan_result.actions
        if action.kind == "team_takeover_delete" and action.path is not None
    )
    return frozenset(paths)


# --------------------------------------------------------------------------
# The ignore gate (Decision 17)
# --------------------------------------------------------------------------


def _parse_check_ignore_verbose(
    output: str, expected: AbstractSet[str]
) -> tuple[tuple[str, str], ...]:
    failing: list[tuple[str, str]] = []
    for line in output.splitlines():
        prefix, sep, pathname = line.rpartition("\t")
        if not sep or pathname not in expected:
            continue
        rule = prefix if prefix.strip(":") else "no matching rule (visible)"
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
        payload = ("\0".join(must_be_ignored) + "\0").encode("utf-8")
        result = subprocess.run(
            [*git_prefix, "check-ignore", "--stdin", "-z"],
            input=payload,
            capture_output=True,
            check=False,
        )
        ignored = frozenset(
            part.decode("utf-8") for part in result.stdout.split(b"\0") if part
        )
        expected = frozenset(must_be_ignored)
        if ignored == expected:
            return True, ()
        verbose = subprocess.run(
            [*git_prefix, "check-ignore", "-v", "-n", "--", *must_be_ignored],
            capture_output=True,
            text=True,
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
        "a team .gitignore rule is un-ignoring a sidecar path (for example a "
        "negation like `!.claude/skills/**`); fix the team .gitignore, or "
        "rerun once it changes"
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

    if unit_path in SIDECAR_BRIDGES:
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


def _empty_staging(staging: Path) -> None:
    if staging.exists() and not staging.is_symlink():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)


def _apply_actions(
    target: Path, source: Path, staging: Path, plan_result: PlanResult
) -> None:
    for action in plan_result.actions:
        if action.kind in ("install", "update"):
            _place_unit(target, source, staging, action.unit)
        elif action.kind == "remove":
            _remove_unit(target, staging, action.unit)
        elif action.kind == "team_takeover_delete":
            _delete_file(target, action.path)
        # "adopt", "unchanged", "retain", and "drop_record" touch no file:
        # the content already matches, the file already sits where it
        # belongs, or only the manifest record changes.


def _count_actions(plan_result: PlanResult) -> dict[str, int]:
    counts = {"install": 0, "update": 0, "remove": 0, "adopt": 0, "unchanged": 0}
    for action in plan_result.actions:
        if action.kind in counts:
            counts[action.kind] += 1
    return counts


def _print_report(plan_result: PlanResult) -> None:
    counts = _count_actions(plan_result)
    _info(
        f"installed {counts['install']}, updated {counts['update']}, "
        f"removed {counts['remove']}, adopted {counts['adopt']}, "
        f"unchanged {counts['unchanged']}"
    )
    for report in plan_result.reports:
        _info(f"{report.category} {report.path}: {report.remedy}")


def _describe_dry_run_actions(plan_result: PlanResult) -> None:
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
        verb = verbs.get(action.kind, action.kind)
        _info(f"would {verb} {action.path or action.unit}")


def _install_sidecar_dry_run(
    target: Path, plan_result: PlanResult, exclude_path: Path
) -> int:
    original_text = (
        exclude_path.read_text(encoding="utf-8") if exclude_path.is_file() else ""
    )
    candidate_text = _replace_exclude_block(
        original_text, plan_result.exclude_lines_write
    )
    write_paths = sorted(_write_raw_paths(plan_result))
    passed, failing = run_ignore_gate(
        target, write_paths, candidate_text.encode("utf-8"), dry_run=True
    )
    if not passed:
        return _abort(_describe_gate_failure(failing), _ignore_gate_remedy())
    _describe_dry_run_actions(plan_result)
    _print_report(plan_result)
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
        original_exclude_bytes.decode("utf-8") if original_exclude_bytes else "",
        plan_result.exclude_lines_write,
    )
    write_bytes = write_text.encode("utf-8")
    if write_bytes != (original_exclude_bytes or b""):
        _atomic_write(exclude_path, write_bytes)

    write_paths = sorted(_write_raw_paths(plan_result))
    passed, failing = run_ignore_gate(target, write_paths, write_bytes, dry_run=False)
    if not passed:
        _restore_exclude(exclude_path, original_exclude_bytes)
        return _abort(_describe_gate_failure(failing), _ignore_gate_remedy())

    _fault_point("after_exclude_write")

    staging = git_path(target, SIDECAR_STAGING_NAME)
    _empty_staging(staging)
    _apply_actions(target, source, staging, plan_result)

    final_text = _replace_exclude_block(write_text, plan_result.exclude_lines_final)
    final_bytes = final_text.encode("utf-8")
    if final_bytes != write_bytes:
        _atomic_write(exclude_path, final_bytes)

    _fault_point("before_manifest_write")

    manifest_bytes = serialize_manifest(next_manifest)
    current_manifest_bytes = (
        manifest_path.read_bytes() if manifest_path.is_file() else None
    )
    if manifest_bytes != current_manifest_bytes:
        _atomic_write(manifest_path, manifest_bytes)

    _empty_staging(staging)
    _print_report(plan_result)
    return 0


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
            "point --source at a generated sidecar tree, for example dist/sidecar",
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

    manifest_path = git_path(target, SIDECAR_MANIFEST_NAME)
    manifest: Manifest | None = None
    if manifest_path.is_file():
        try:
            manifest = parse_manifest(manifest_path.read_text(encoding="utf-8"))
        except (ManifestError, OSError, UnicodeDecodeError) as exc:
            return _abort(
                f"invalid sidecar manifest at {manifest_path}: {exc}",
                _INVALID_MANIFEST_REMEDY,
            )

    # Built directly from the already-verified --git-dir, not through
    # git_path()/--git-path: git resolves a symlinked info/exclude to its
    # target before printing it, which would hide exactly the symlink this
    # check exists to catch.
    exclude_path = git_dir_path / "info" / "exclude"
    if exclude_path.is_symlink():
        return _abort(
            f"{exclude_path} is a symlink",
            f"replace the symlink at {exclude_path} with a regular file, then rerun",
        )

    desired_units = load_desired_units(source)
    required_units = required_snapshot_units(desired_units, manifest)
    tracked = _tracked_files(target)
    read_list_skill_names = _read_list_skill_names(target)
    # required_units always includes every desired unit already
    # (required_snapshot_units starts from set(desired_units)).
    excluded_units = _excluded_units(exclude_path, required_units)
    snapshots = _build_snapshots(target, required_units, tracked)

    plan_result = plan_sidecar_reconciliation(
        desired_units=desired_units,
        manifest=manifest,
        excluded_units=excluded_units,
        read_list_skill_names=read_list_skill_names,
        snapshots=snapshots,
    )
    if plan_result.aborts:
        message = "; ".join(
            f"{abort.reason}: {abort.message}" for abort in plan_result.aborts
        )
        return _abort(
            message,
            "replace the symlinked path (or its symlinked ancestor directory) "
            "with a regular directory, then rerun",
        )

    if dry_run:
        return _install_sidecar_dry_run(target, plan_result, exclude_path)
    return _install_sidecar_apply(
        target, source, plan_result, exclude_path, manifest_path
    )
