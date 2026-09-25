"""Pure reconciliation planner for the consumer sidecar overlay.

This module never touches the filesystem for anything other than reading the
desired content tree (``load_desired_units``, a deliberately narrow reader).
Every other function is a pure transformation over data the caller (Phase C's
``install_bootstrap.py``) gathers with Git: tracked-file lists, per-file
hashes of what is on disk, and which untracked files are currently ignored.
The caller applies the returned actions; this module only decides them.

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

Preflight checks this module can decide from data alone are a symlinked unit
(or a symlinked ancestor) and manifest schema/namespace problems
(``parse_manifest`` raising ``ManifestError``). Git version, filesystem,
worktree, and ``info/exclude`` symlink checks need live Git state and belong
to the Phase C caller.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Set as AbstractSet
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Literal

from runtime_ownership import (
    SIDECAR_BRIDGES,
    SIDECAR_SKILL_READ_ROOTS,
    SIDECAR_SKILL_WRITE_ROOTS,
    SIDECAR_SKILLS,
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
