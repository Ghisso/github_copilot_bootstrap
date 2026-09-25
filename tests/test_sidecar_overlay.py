"""Failing-first coverage for the pure sidecar reconciliation planner.

Every test exercises the public API in ``scripts/sidecar_overlay.py`` with
in-memory data only; nothing here reads ``dist/`` or touches a real Git
repository, except the escaping tests, which use a real temporary Git
repository to prove the exact-path lines are honored by
``git check-ignore`` (Decision 17 is a security-relevant contract, so it is
checked against real Git, not just against the string it produces).
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections.abc import Set as AbstractSet
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from runtime_ownership import (  # noqa: E402
    SIDECAR_BRIDGES,
    SIDECAR_SKILL_WRITE_ROOTS,
)
from sidecar_overlay import (  # noqa: E402
    Action,
    DesiredUnit,
    ExcludeBlockContents,
    Manifest,
    ManifestError,
    ManifestUnit,
    Report,
    UnitSnapshot,
    _parse_frontmatter_name,
    _unit_index_relpaths,
    compute_file_hash,
    compute_unit_hash,
    escape_exact_path,
    escape_ignore_segment,
    parse_exclude_block,
    parse_manifest,
    plan_sidecar_reconciliation,
    preserved_unit_slug,
    required_snapshot_units,
    serialize_manifest,
    unescape_exact_path,
    unescape_ignore_segment,
    unit_exclude_line,
)

CLAUDE_ROOT, AGENTS_ROOT = SIDECAR_SKILL_WRITE_ROOTS
SKILL = "ponytail"
UNIT = f"{CLAUDE_ROOT}/{SKILL}"
OTHER_UNIT = f"{AGENTS_ROOT}/{SKILL}"
BRIDGE = next(iter(SIDECAR_BRIDGES))


def unit_files(contents: dict[str, bytes]) -> dict[str, str]:
    return {path: compute_file_hash(data) for path, data in contents.items()}


def desired(contents: dict[str, bytes]) -> DesiredUnit:
    files = unit_files(contents)
    return DesiredUnit(files=files, hash=compute_unit_hash(files))


def recorded(contents: dict[str, bytes]) -> ManifestUnit:
    files = unit_files(contents)
    return ManifestUnit(files=files, hash=compute_unit_hash(files))


def manifest_with(
    units: dict[str, ManifestUnit] | None = None,
    retained: AbstractSet[str] | None = None,
) -> Manifest:
    return Manifest(
        schema_version=1,
        bootstrap_commit="deadbeef",
        units=units or {},
        retained=frozenset(retained or ()),
    )


def snapshot(
    contents: dict[str, bytes] | None = None,
    *,
    exists: bool = True,
    symlinked: bool = False,
    tracked: frozenset[str] = frozenset(),
    ignored: frozenset[str] = frozenset(),
) -> UnitSnapshot:
    return UnitSnapshot(
        exists=exists,
        symlinked=symlinked,
        tracked_files=frozenset(tracked),
        file_hashes=unit_files(contents or {}),
        ignored_files=frozenset(ignored),
    )


def plan(
    *,
    desired_units=None,
    manifest=None,
    excluded=frozenset(),
    listed_files=frozenset(),
    unrecognized_lines=frozenset(),
    read_list=None,
    declared_skill_names=None,
    ignorecase=False,
    snapshots=None,
    preserved_conflicts=frozenset(),
    preserved_destinations=None,
):
    return plan_sidecar_reconciliation(
        desired_units=desired_units or {},
        manifest=manifest,
        excluded_units=excluded,
        listed_files=listed_files,
        unrecognized_lines=unrecognized_lines,
        read_list_skill_names=read_list or {},
        declared_skill_names=declared_skill_names,
        ignorecase=ignorecase,
        snapshots=snapshots or {},
        preserved_conflicts=preserved_conflicts,
        preserved_destinations=preserved_destinations,
    )


def kinds(result, unit=UNIT) -> list[str]:
    return [action.kind for action in result.actions if action.unit == unit]


# --------------------------------------------------------------------------
# Hashing framing
# --------------------------------------------------------------------------


def test_compute_unit_hash_matches_documented_framing():
    files = {"SKILL.md": "a" * 64, "sub/notes.txt": "b" * 64}
    expected = (
        "SKILL.md".encode()
        + b"\0"
        + b"a" * 64
        + b"\n"
        + "sub/notes.txt".encode()
        + b"\0"
        + b"b" * 64
        + b"\n"
    )
    import hashlib

    assert compute_unit_hash(files) == hashlib.sha256(expected).hexdigest()


def test_compute_unit_hash_framing_prevents_ambiguous_collision():
    # Without a separator, ("ab", "c") and ("a", "bc") would concatenate to
    # the same bytes. The NUL/newline framing must keep them distinct.
    left = compute_unit_hash({"ab": "c" * 64})
    right = compute_unit_hash({"a": ("bc" * 32)[:64]})
    assert left != right


# --------------------------------------------------------------------------
# Manifest parsing and schema validation
# --------------------------------------------------------------------------


def test_parse_manifest_roundtrip_is_deterministic():
    original = manifest_with(
        units={UNIT: recorded({"SKILL.md": b"hi"})},
        retained={f"{UNIT}/x.txt"},
    )
    text = serialize_manifest(original).decode()
    parsed = parse_manifest(text)
    assert parsed == original
    assert serialize_manifest(parsed) == serialize_manifest(original)
    assert serialize_manifest(original).endswith(b"\n")
    # sorted keys: "bootstrap_commit" before "retained" before "schema_version" before "units"
    payload = json.loads(text)
    assert list(json.dumps(payload, sort_keys=True)) == list(
        json.dumps(payload, sort_keys=True)
    )


def test_parse_manifest_rejects_invalid_json():
    with pytest.raises(ManifestError, match="invalid JSON"):
        parse_manifest("{not json")


def test_parse_manifest_rejects_missing_schema_version():
    with pytest.raises(ManifestError, match="schema_version"):
        parse_manifest(json.dumps({"units": {}, "retained": []}))


def test_parse_manifest_rejects_unknown_schema_version():
    with pytest.raises(ManifestError, match="unknown schema_version"):
        parse_manifest(json.dumps({"schema_version": 2, "units": {}, "retained": []}))


def test_parse_manifest_rejects_missing_file_hashes():
    body = {
        "schema_version": 1,
        "units": {UNIT: {"files": {}, "hash": "a" * 64}},
        "retained": [],
    }
    with pytest.raises(ManifestError, match="missing per-file hashes"):
        parse_manifest(json.dumps(body))


def test_parse_manifest_rejects_absolute_unit_path():
    body = {
        "schema_version": 1,
        "units": {"/etc/passwd": {"files": {"a": "a" * 64}, "hash": "a" * 64}},
        "retained": [],
    }
    with pytest.raises(ManifestError, match="unsafe unit path"):
        parse_manifest(json.dumps(body))


def test_parse_manifest_rejects_dotdot_unit_path():
    path = f"{CLAUDE_ROOT}/../../etc"
    body = {
        "schema_version": 1,
        "units": {path: {"files": {"a": "a" * 64}, "hash": "a" * 64}},
        "retained": [],
    }
    with pytest.raises(ManifestError, match="unsafe unit path"):
        parse_manifest(json.dumps(body))


def test_parse_manifest_rejects_unit_path_outside_namespace():
    # Two segments after the write root is not "one safe segment".
    path = f"{CLAUDE_ROOT}/{SKILL}/extra"
    body = {
        "schema_version": 1,
        "units": {path: {"files": {"a": "a" * 64}, "hash": "a" * 64}},
        "retained": [],
    }
    with pytest.raises(ManifestError, match="outside the sidecar namespace"):
        parse_manifest(json.dumps(body))


def test_parse_manifest_accepts_bridge_unit_path():
    body = {
        "schema_version": 1,
        "units": {BRIDGE: {"files": {"a": "a" * 64}, "hash": "a" * 64}},
        "retained": [],
    }
    parsed = parse_manifest(json.dumps(body))
    assert BRIDGE in parsed.units


def test_parse_manifest_rejects_retained_path_not_inside_a_unit():
    body = {"schema_version": 1, "units": {}, "retained": [CLAUDE_ROOT]}
    with pytest.raises(ManifestError, match="outside a sidecar unit"):
        parse_manifest(json.dumps(body))


def test_parse_manifest_rejects_retained_path_with_dotdot():
    body = {
        "schema_version": 1,
        "units": {},
        "retained": [f"{UNIT}/../escape.txt"],
    }
    with pytest.raises(ManifestError, match="unsafe retained path"):
        parse_manifest(json.dumps(body))


def test_parse_manifest_accepts_nested_retained_path():
    body = {
        "schema_version": 1,
        "units": {},
        "retained": [f"{UNIT}/sub/x.txt"],
    }
    parsed = parse_manifest(json.dumps(body))
    assert f"{UNIT}/sub/x.txt" in parsed.retained


# --------------------------------------------------------------------------
# Preflight aborts the planner can decide from data
# --------------------------------------------------------------------------


def test_plan_aborts_on_symlinked_unit():
    result = plan(
        desired_units={UNIT: desired({"SKILL.md": b"hi"})},
        snapshots={UNIT: snapshot(exists=False, symlinked=True)},
    )
    assert len(result.aborts) == 1
    assert result.aborts[0].reason == "symlink"
    assert result.actions == ()
    assert result.reports == ()
    assert result.next_manifest is None
    assert result.exclude_lines_write == ()
    assert result.exclude_lines_final == ()


def test_plan_aborts_on_symlinked_ancestor():
    # The caller sets ``symlinked`` the same way whether the unit itself or
    # an ancestor directory is the symlink; the planner treats both alike.
    result = plan(
        desired_units={UNIT: desired({"SKILL.md": b"hi"})},
        snapshots={UNIT: snapshot({"SKILL.md": b"hi"}, symlinked=True)},
    )
    assert result.aborts and result.aborts[0].reason == "symlink"


# --------------------------------------------------------------------------
# Classification table, one test per row
# --------------------------------------------------------------------------


def test_row_install_when_absent_and_desired():
    content = {"SKILL.md": b"hello"}
    result = plan(
        desired_units={UNIT: desired(content)},
        snapshots={UNIT: snapshot(exists=False)},
    )
    assert kinds(result) == ["install"]
    assert result.next_manifest.units[UNIT].hash == desired(content).hash
    assert unit_exclude_line(UNIT) in result.exclude_lines_write
    assert unit_exclude_line(UNIT) in result.exclude_lines_final


def test_row_drop_record_when_absent_and_no_longer_desired():
    result = plan(
        desired_units={},
        manifest=manifest_with(units={UNIT: recorded({"SKILL.md": b"hi"})}),
        snapshots={UNIT: snapshot(exists=False)},
    )
    assert kinds(result) == ["drop_record"]
    assert UNIT not in result.next_manifest.units
    assert unit_exclude_line(UNIT) not in result.exclude_lines_write


def test_row_unchanged_when_untracked_matches_record_and_desired():
    content = {"SKILL.md": b"same"}
    result = plan(
        desired_units={UNIT: desired(content)},
        manifest=manifest_with(units={UNIT: recorded(content)}),
        snapshots={UNIT: snapshot(content)},
    )
    assert kinds(result) == ["unchanged"]
    assert result.next_manifest.units[UNIT].hash == desired(content).hash
    assert unit_exclude_line(UNIT) in result.exclude_lines_final


def test_row_update_when_untracked_matches_record_but_desired_changed():
    old_content = {"SKILL.md": b"old"}
    new_content = {"SKILL.md": b"new"}
    result = plan(
        desired_units={UNIT: desired(new_content)},
        manifest=manifest_with(units={UNIT: recorded(old_content)}),
        snapshots={UNIT: snapshot(old_content)},
    )
    assert kinds(result) == ["update"]
    assert result.next_manifest.units[UNIT].hash == desired(new_content).hash


def test_row_remove_when_untracked_matches_record_and_no_longer_desired():
    content = {"SKILL.md": b"gone"}
    result = plan(
        desired_units={},
        manifest=manifest_with(units={UNIT: recorded(content)}),
        snapshots={UNIT: snapshot(content)},
    )
    assert kinds(result) == ["remove"]
    assert UNIT not in result.next_manifest.units
    assert unit_exclude_line(UNIT) in result.exclude_lines_write
    assert unit_exclude_line(UNIT) not in result.exclude_lines_final


def test_row_adopt_when_untracked_equals_desired_and_exclude_lists_unit():
    content = {"SKILL.md": b"reborn"}
    result = plan(
        desired_units={UNIT: desired(content)},
        manifest=None,
        excluded={UNIT},
        snapshots={UNIT: snapshot(content)},
    )
    assert kinds(result) == ["adopt"]
    assert result.next_manifest.units[UNIT].hash == desired(content).hash


def test_row_foreign_when_untracked_equals_desired_but_exclude_does_not_list_unit():
    content = {"SKILL.md": b"visible"}
    result = plan(
        desired_units={UNIT: desired(content)},
        manifest=None,
        excluded=frozenset(),
        snapshots={UNIT: snapshot(content)},
    )
    assert kinds(result) == []
    assert result.reports == (Report("SKIPPED", UNIT, result.reports[0].remedy),)
    assert "will not replace" in result.reports[0].remedy
    assert unit_exclude_line(UNIT) not in result.exclude_lines_write


def test_row_adopt_finishes_an_interrupted_update_with_the_new_record():
    old_content = {"SKILL.md": b"old"}
    new_content = {"SKILL.md": b"new"}
    result = plan(
        desired_units={UNIT: desired(new_content)},
        manifest=manifest_with(units={UNIT: recorded(old_content)}),
        excluded={UNIT},
        snapshots={UNIT: snapshot(new_content)},
    )
    assert kinds(result) == ["adopt"]
    assert result.next_manifest.units[UNIT].hash == desired(new_content).hash


def test_row_locally_modified_keeps_files_record_and_line():
    recorded_content = {"SKILL.md": b"recorded"}
    on_disk_content = {"SKILL.md": b"edited-by-a-person"}
    result = plan(
        desired_units={UNIT: desired(recorded_content)},
        manifest=manifest_with(units={UNIT: recorded(recorded_content)}),
        excluded=frozenset(),  # not excluded, so it cannot be misread as adopt
        snapshots={UNIT: snapshot(on_disk_content)},
    )
    assert kinds(result) == []
    assert result.next_manifest.units[UNIT] == recorded(recorded_content)
    assert unit_exclude_line(UNIT) in result.exclude_lines_final
    assert "has local edits" in result.reports[0].remedy
    assert "copy your edits elsewhere" in result.reports[0].remedy


def test_row_team_owned_when_tracked_and_unrecorded():
    result = plan(
        desired_units={UNIT: desired({"SKILL.md": b"team"})},
        manifest=None,
        snapshots={UNIT: snapshot({"SKILL.md": b"team"}, tracked={"SKILL.md"})},
    )
    assert result.actions == ()
    assert UNIT not in result.next_manifest.units
    assert unit_exclude_line(UNIT) not in result.exclude_lines_write
    assert result.reports == (Report("SKIPPED", UNIT, result.reports[0].remedy),)
    assert "the sidecar skips" in result.reports[0].remedy


def test_row_team_takeover_deletes_matches_retains_hidden_leaves_visible_alone():
    record = recorded(
        {"SKILL.md": b"team", "notes.txt": b"matches", "scratch.txt": b"stale"}
    )
    disk = {
        "SKILL.md": b"team-checked-out",  # tracked now; content is irrelevant
        "notes.txt": b"matches",  # untracked, matches the record -> deleted
        "scratch.txt": b"user-added-hidden",  # untracked, ignored, no match -> retained
        "visible.txt": b"user-added-visible",  # untracked, visible, no match -> left alone
    }
    snap = snapshot(disk, tracked={"SKILL.md"}, ignored={"scratch.txt"})
    result = plan(
        desired_units={UNIT: desired({"SKILL.md": b"team", "notes.txt": b"matches"})},
        manifest=manifest_with(units={UNIT: record}),
        snapshots={UNIT: snap},
    )
    action_kinds = sorted((a.kind, a.path) for a in result.actions if a.unit == UNIT)
    assert action_kinds == sorted(
        [
            ("drop_record", None),
            ("team_takeover_delete", f"{UNIT}/notes.txt"),
            ("retain", f"{UNIT}/scratch.txt"),
        ]
    )
    assert UNIT not in result.next_manifest.units
    assert f"{UNIT}/scratch.txt" in result.next_manifest.retained
    assert f"{UNIT}/scratch.txt" not in [
        a.path for a in result.actions if a.kind != "retain"
    ]
    assert unit_exclude_line(UNIT) not in result.exclude_lines_write
    assert escape_exact_path(f"{UNIT}/notes.txt") in result.exclude_lines_write
    assert escape_exact_path(f"{UNIT}/notes.txt") not in result.exclude_lines_final
    assert escape_exact_path(f"{UNIT}/scratch.txt") in result.exclude_lines_write
    assert escape_exact_path(f"{UNIT}/scratch.txt") in result.exclude_lines_final
    assert escape_exact_path(f"{UNIT}/visible.txt") not in result.exclude_lines_write
    categories = {(r.category, r.path) for r in result.reports}
    assert (
        "RETAINED",
        f"{UNIT}/scratch.txt",
    ) in categories
    assert ("SKIPPED", UNIT) in categories


# --------------------------------------------------------------------------
# Retained-file ledger across later runs
# --------------------------------------------------------------------------


def test_retained_file_dropped_once_tracked():
    retained_path = f"{UNIT}/scratch.txt"
    result = plan(
        desired_units={},
        manifest=manifest_with(retained={retained_path}),
        snapshots={
            UNIT: snapshot(
                {"SKILL.md": b"team", "scratch.txt": b"kept"},
                tracked={"SKILL.md", "scratch.txt"},
            )
        },
    )
    assert retained_path not in result.next_manifest.retained
    assert escape_exact_path(retained_path) not in result.exclude_lines_final
    assert not any(r.path == retained_path for r in result.reports)
    assert Action("drop_record", UNIT, retained_path) in result.actions


def test_retained_file_dropped_once_deleted():
    retained_path = f"{UNIT}/scratch.txt"
    result = plan(
        desired_units={},
        manifest=manifest_with(retained={retained_path}),
        snapshots={UNIT: snapshot({"SKILL.md": b"team"}, tracked={"SKILL.md"})},
    )
    assert retained_path not in result.next_manifest.retained
    assert escape_exact_path(retained_path) not in result.exclude_lines_final
    assert not any(r.path == retained_path for r in result.reports)


def test_retained_file_carried_forward_while_still_hidden():
    retained_path = f"{UNIT}/scratch.txt"
    result = plan(
        desired_units={},
        manifest=manifest_with(retained={retained_path}),
        snapshots={
            UNIT: snapshot(
                {"SKILL.md": b"team", "scratch.txt": b"kept"},
                tracked={"SKILL.md"},
                ignored={"scratch.txt"},
            )
        },
    )
    assert retained_path in result.next_manifest.retained
    assert escape_exact_path(retained_path) in result.exclude_lines_final
    assert any(
        r.category == "RETAINED" and r.path == retained_path for r in result.reports
    )


# --------------------------------------------------------------------------
# Skill-level anti-shadowing (Decision 8)
# --------------------------------------------------------------------------


def test_skill_taken_at_one_write_root_removes_unchanged_copy_at_the_other():
    content = {"SKILL.md": b"shared"}
    result = plan(
        desired_units={UNIT: desired(content), OTHER_UNIT: desired(content)},
        manifest=manifest_with(units={OTHER_UNIT: recorded(content)}),
        snapshots={
            UNIT: snapshot({"SKILL.md": b"team-owns-this-name"}, tracked={"SKILL.md"}),
            OTHER_UNIT: snapshot(content),
        },
    )
    assert kinds(result, UNIT) == []
    assert kinds(result, OTHER_UNIT) == ["remove"]
    assert OTHER_UNIT not in result.next_manifest.units
    assert unit_exclude_line(OTHER_UNIT) not in result.exclude_lines_final


def test_skill_taken_removes_an_update_candidate_copy_at_the_other_root():
    # The sibling write root's on-disk content still matches its OLD record
    # (so, on its own, it would classify as "update" toward the new desired
    # content) rather than "unchanged". The anti-shadow override must still
    # convert it to "remove", not leave it as "update".
    old_content = {"SKILL.md": b"old-shared"}
    new_content = {"SKILL.md": b"new-shared"}
    result = plan(
        desired_units={UNIT: desired(new_content), OTHER_UNIT: desired(new_content)},
        manifest=manifest_with(units={OTHER_UNIT: recorded(old_content)}),
        snapshots={
            UNIT: snapshot({"SKILL.md": b"team-owns-this-name"}, tracked={"SKILL.md"}),
            OTHER_UNIT: snapshot(old_content),
        },
    )
    assert kinds(result, UNIT) == []
    assert kinds(result, OTHER_UNIT) == ["remove"]
    assert OTHER_UNIT not in result.next_manifest.units
    assert unit_exclude_line(OTHER_UNIT) not in result.exclude_lines_final


def test_skill_name_found_only_in_read_only_folder_is_skipped_at_both_roots():
    content = {"SKILL.md": b"fresh"}
    result = plan(
        desired_units={UNIT: desired(content), OTHER_UNIT: desired(content)},
        manifest=None,
        read_list={".github/skills": frozenset({SKILL})},
        snapshots={UNIT: snapshot(exists=False), OTHER_UNIT: snapshot(exists=False)},
    )
    assert kinds(result, UNIT) == []
    assert kinds(result, OTHER_UNIT) == []
    assert UNIT not in result.next_manifest.units
    assert OTHER_UNIT not in result.next_manifest.units
    # Decision 8: skipped everywhere AND reported, even though no unit at
    # either write root exists to carry the report itself.
    assert len(result.reports) == 1
    report = result.reports[0]
    assert report.category == "SKIPPED"
    assert report.path == f".github/skills/{SKILL}"
    assert f"`{SKILL}`" in report.remedy
    assert ".github/skills" in report.remedy


def test_skill_taken_preserves_and_reports_a_modified_copy_at_the_other_root():
    # Decision 24 (round-2 review, design item 2): a taken skill's modified
    # copy is moved out of the client folders, not merely left in place.
    record_content = {"SKILL.md": b"recorded"}
    edited_content = {"SKILL.md": b"edited-locally"}
    result = plan(
        desired_units={
            UNIT: desired(record_content),
            OTHER_UNIT: desired(record_content),
        },
        manifest=manifest_with(units={OTHER_UNIT: recorded(record_content)}),
        snapshots={
            UNIT: snapshot({"SKILL.md": b"team"}, tracked={"SKILL.md"}),
            OTHER_UNIT: snapshot(edited_content),
        },
    )
    assert kinds(result, OTHER_UNIT) == ["preserve"]
    assert OTHER_UNIT not in result.next_manifest.units
    assert unit_exclude_line(OTHER_UNIT) not in result.exclude_lines_final
    preserved = [r for r in result.reports if r.category == "PRESERVED"]
    assert any(r.path == OTHER_UNIT for r in preserved)


def test_skill_taken_at_write_root_and_read_only_folder_gets_both_reports():
    # S15: the report names every path that took the skill, so a write-root
    # collision (which already self-reports) never suppresses the separate
    # read-only-folder report.
    content = {"SKILL.md": b"fresh"}
    result = plan(
        desired_units={UNIT: desired(content), OTHER_UNIT: desired(content)},
        manifest=None,
        read_list={".github/skills": frozenset({SKILL})},
        snapshots={
            UNIT: snapshot({"SKILL.md": b"team"}, tracked={"SKILL.md"}),
            OTHER_UNIT: snapshot(exists=False),
        },
    )
    assert kinds(result, OTHER_UNIT) == []
    assert len(result.reports) == 2
    paths = {r.path for r in result.reports}
    assert paths == {UNIT, f".github/skills/{SKILL}"}


# --------------------------------------------------------------------------
# Bridge-specific remedy wording
# --------------------------------------------------------------------------


def test_bridge_team_owned_remedy_has_no_skill_name():
    bridge_file_name = BRIDGE.rsplit("/", 1)[-1]
    result = plan(
        desired_units={BRIDGE: desired({bridge_file_name: b"team-owned-bridge"})},
        manifest=None,
        snapshots={
            BRIDGE: snapshot(
                {bridge_file_name: b"team-owned-bridge"}, tracked={bridge_file_name}
            )
        },
    )
    assert kinds(result, BRIDGE) == []
    assert BRIDGE not in result.next_manifest.units
    assert unit_exclude_line(BRIDGE) not in result.exclude_lines_write
    assert result.reports == (Report("SKIPPED", BRIDGE, result.reports[0].remedy),)
    assert result.reports[0].remedy == (
        f"the repository tracks `{BRIDGE}`; the sidecar does not install this bridge"
    )


# --------------------------------------------------------------------------
# Exact-path escaping (Decision 17), checked against real git
# --------------------------------------------------------------------------


NAMES_NEEDING_ESCAPE = [
    "back\\slash.txt",
    "glob[1].txt",
    "wild*card.txt",
    "ques?tion.txt",
    "!bang.txt",
    "#hash.txt",
    "trailing space.txt ",
    "héllo.txt",
]


@pytest.mark.parametrize("name", NAMES_NEEDING_ESCAPE)
def test_escape_ignore_segment_covers_every_special_character(name):
    escaped = escape_ignore_segment(name)
    if name[0] in ("!", "#"):
        assert escaped.startswith(f"\\{name[0]}")
    for char in "\\*?[":
        if char in name:
            assert f"\\{char}" in escaped
    if name.endswith(" "):
        assert escaped.endswith("\\ ")


def test_escaped_exact_paths_hide_exactly_those_files_and_nothing_else(tmp_path: Path):
    git = ["git", "-C", str(tmp_path)]
    subprocess.run([*git, "init", "-q"], check=True)
    sub = tmp_path / "sub"
    sub.mkdir()
    decoys = [
        "bang.txt",
        "hash.txt",
        "trailing space.txt",  # no trailing space, must stay visible
    ]
    for name in NAMES_NEEDING_ESCAPE + decoys:
        (sub / name).write_bytes(b"x")

    lines = [escape_exact_path(f"sub/{name}") for name in NAMES_NEEDING_ESCAPE]
    (tmp_path / ".git" / "info" / "exclude").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    all_paths = [f"sub/{name}" for name in NAMES_NEEDING_ESCAPE + decoys]
    stdin_payload = ("\0".join(all_paths) + "\0").encode()
    result = subprocess.run(
        [*git, "check-ignore", "--stdin", "-z"],
        input=stdin_payload,
        capture_output=True,
        check=False,
    )
    ignored = {path for path in result.stdout.decode().split("\0") if path}
    assert ignored == {f"sub/{name}" for name in NAMES_NEEDING_ESCAPE}


# --------------------------------------------------------------------------
# required_snapshot_units
# --------------------------------------------------------------------------


def test_required_snapshot_units_includes_retained_files_owning_unit():
    manifest = manifest_with(retained={f"{UNIT}/scratch.txt"})
    assert UNIT in required_snapshot_units({}, manifest)


def test_required_snapshot_units_includes_desired_and_recorded_units():
    manifest = manifest_with(units={OTHER_UNIT: recorded({"SKILL.md": b"x"})})
    required = required_snapshot_units({UNIT: desired({"SKILL.md": b"y"})}, manifest)
    assert required == {UNIT, OTHER_UNIT}


# --------------------------------------------------------------------------
# Idempotency: plan, apply to data, plan again
# --------------------------------------------------------------------------


def test_plan_apply_plan_again_yields_no_further_actions():
    content = {"SKILL.md": b"stable"}
    desired_units = {UNIT: desired(content)}

    first = plan(
        desired_units=desired_units,
        manifest=None,
        snapshots={UNIT: snapshot(exists=False)},
    )
    assert kinds(first) == ["install"]

    # Simulate applying the plan: the file now exists, untracked, and is
    # hidden by the exclude lines the first plan reported as final.
    applied_snapshot = snapshot(content, ignored={"SKILL.md"})
    excluded_after_apply = {UNIT}

    second = plan(
        desired_units=desired_units,
        manifest=first.next_manifest,
        excluded=excluded_after_apply,
        snapshots={UNIT: applied_snapshot},
    )
    non_trivial = [action for action in second.actions if action.kind != "unchanged"]
    assert non_trivial == []
    assert second.aborts == ()
    assert second.reports == ()
    assert serialize_manifest(second.next_manifest) == serialize_manifest(
        first.next_manifest
    )
    assert second.exclude_lines_final == first.exclude_lines_final


# --------------------------------------------------------------------------
# Phase G step 2: one precedence decision per skill (S12, S15, L3)
# --------------------------------------------------------------------------


def test_foreign_write_root_plus_read_only_collision_reports_both():
    # S15: a write-root copy being foreign must not suppress the separate
    # read-only-folder report.
    foreign_content = {"SKILL.md": b"foreign-here"}
    desired_content = {"SKILL.md": b"something-else"}
    result = plan(
        desired_units={
            UNIT: desired(desired_content),
            OTHER_UNIT: desired(desired_content),
        },
        manifest=None,
        read_list={".github/skills": frozenset({SKILL})},
        snapshots={UNIT: snapshot(foreign_content), OTHER_UNIT: snapshot(exists=False)},
    )
    assert kinds(result, UNIT) == []
    assert kinds(result, OTHER_UNIT) == []
    paths = {r.path for r in result.reports}
    assert paths == {UNIT, f".github/skills/{SKILL}"}


def test_ignorecase_case_variant_in_read_only_folder_skips_without_hiding_it():
    content = {"SKILL.md": b"fresh"}
    result = plan(
        desired_units={UNIT: desired(content), OTHER_UNIT: desired(content)},
        manifest=None,
        read_list={".github/skills": frozenset({"Ponytail"})},
        ignorecase=True,
        snapshots={UNIT: snapshot(exists=False), OTHER_UNIT: snapshot(exists=False)},
    )
    assert kinds(result, UNIT) == []
    assert kinds(result, OTHER_UNIT) == []
    report = next(r for r in result.reports if r.path == ".github/skills/Ponytail")
    # The real (case-variant) path, not the reconstructed ``folder/skill``.
    assert report.remedy == (
        "the repository has `.github/skills/Ponytail`; the sidecar skips "
        f"`{SKILL}` at every root"
    )
    assert (
        escape_exact_path(".github/skills/Ponytail") not in result.exclude_lines_final
    )


def test_ignorecase_false_does_not_treat_case_variant_as_taken():
    content = {"SKILL.md": b"fresh"}
    result = plan(
        desired_units={UNIT: desired(content), OTHER_UNIT: desired(content)},
        manifest=None,
        read_list={".github/skills": frozenset({"Ponytail"})},
        ignorecase=False,
        snapshots={UNIT: snapshot(exists=False), OTHER_UNIT: snapshot(exists=False)},
    )
    assert kinds(result, UNIT) == ["install"]
    assert kinds(result, OTHER_UNIT) == ["install"]


def test_ignorecase_case_variant_at_write_root_skips_without_hiding_it():
    content = {"SKILL.md": b"fresh"}
    result = plan(
        desired_units={UNIT: desired(content), OTHER_UNIT: desired(content)},
        manifest=None,
        read_list={CLAUDE_ROOT: frozenset({"Ponytail"})},
        ignorecase=True,
        snapshots={UNIT: snapshot(exists=False), OTHER_UNIT: snapshot(exists=False)},
    )
    assert kinds(result, UNIT) == []
    assert kinds(result, OTHER_UNIT) == []
    assert any(r.path == f"{CLAUDE_ROOT}/Ponytail" for r in result.reports)


def test_frontmatter_declared_name_takes_the_skill_everywhere():
    content = {"SKILL.md": b"fresh"}
    result = plan(
        desired_units={UNIT: desired(content), OTHER_UNIT: desired(content)},
        manifest=None,
        declared_skill_names={SKILL: frozenset({".github/skills/team-humanize"})},
        snapshots={UNIT: snapshot(exists=False), OTHER_UNIT: snapshot(exists=False)},
    )
    assert kinds(result, UNIT) == []
    assert kinds(result, OTHER_UNIT) == []
    report = next(r for r in result.reports if r.path == ".github/skills/team-humanize")
    # The real declaring path, not the reconstructed ``folder/skill`` (which
    # would have printed the wrong ".github/skills/ponytail").
    assert report.remedy == (
        "the repository has `.github/skills/team-humanize`; the sidecar "
        f"skips `{SKILL}` at every root"
    )


@pytest.mark.parametrize(
    "outcome_kind",
    ["install", "unchanged", "update", "adopt"],
)
def test_taken_skill_never_produces_a_disallowed_outcome(outcome_kind):
    # Decision 22: an allowlist of outcomes cannot miss a future kind, unlike
    # the old enumerated conversion that let "adopt" escape (R1).
    if outcome_kind == "install":
        other_snapshot = snapshot(exists=False)
        manifest = None
    elif outcome_kind == "unchanged":
        content = {"SKILL.md": b"same"}
        other_snapshot = snapshot(content)
        manifest = manifest_with(units={OTHER_UNIT: recorded(content)})
    elif outcome_kind == "update":
        old_content = {"SKILL.md": b"old"}
        other_snapshot = snapshot(old_content)
        manifest = manifest_with(units={OTHER_UNIT: recorded(old_content)})
    else:  # adopt
        content = {"SKILL.md": b"reborn"}
        other_snapshot = snapshot(content)
        manifest = None

    result = plan(
        desired_units={
            UNIT: desired({"SKILL.md": b"new"}),
            OTHER_UNIT: desired({"SKILL.md": b"new"}),
        },
        manifest=manifest,
        excluded={OTHER_UNIT} if outcome_kind == "adopt" else frozenset(),
        snapshots={
            UNIT: snapshot({"SKILL.md": b"team"}, tracked={"SKILL.md"}),
            OTHER_UNIT: other_snapshot,
        },
    )
    assert kinds(result, OTHER_UNIT) not in (
        ["install"],
        ["unchanged"],
        ["update"],
        ["adopt"],
    )


# --------------------------------------------------------------------------
# Phase G step 2: L3, frontmatter name parsing
# --------------------------------------------------------------------------


def test_parse_frontmatter_name_reads_a_plain_value():
    assert _parse_frontmatter_name(b"---\nname: humanize\n---\nbody\n") == "humanize"


def test_parse_frontmatter_name_strips_quotes_and_trailing_comment():
    assert (
        _parse_frontmatter_name(b"---\nname: 'humanize'  # a comment\n---\n")
        == "humanize"
    )
    assert (
        _parse_frontmatter_name(b'---\nname: "humanize" # trailing\n---\n')
        == "humanize"
    )
    assert (
        _parse_frontmatter_name(b"---\nname: humanize # trailing\n---\n") == "humanize"
    )


def test_parse_frontmatter_name_malformed_block_declares_nothing():
    assert _parse_frontmatter_name(b"no frontmatter here\nname: humanize\n") is None
    assert _parse_frontmatter_name(b"---\nname: humanize\nno closing marker\n") is None
    assert _parse_frontmatter_name(b"---\ntitle: something\n---\n") is None
    assert _parse_frontmatter_name(b"\xff\xfe not utf-8") is None


# --------------------------------------------------------------------------
# Phase G step 3: ownership proof by record or exclude line
# --------------------------------------------------------------------------


def test_unescape_exact_path_round_trips_every_special_character():
    for name in [
        "back\\slash.txt",
        "glob[1].txt",
        "wild*card.txt",
        "ques?tion.txt",
        "!bang.txt",
        "#hash.txt",
        "héllo.txt",
    ]:
        path = f"sub/{name}"
        line = escape_exact_path(path)
        assert unescape_exact_path(line) == path
        assert escape_exact_path(unescape_exact_path(line)) == line


def test_unescape_exact_path_rejects_a_line_with_no_leading_slash():
    assert unescape_exact_path("not/anchored") is None


def test_unescape_ignore_segment_is_the_plain_inverse_of_escape():
    for segment in ["plain", "back\\\\slash", "wild\\*card", "!bang", "trailing\\ "]:
        assert escape_ignore_segment(unescape_ignore_segment(segment)) in (
            segment,
            escape_ignore_segment(unescape_ignore_segment(segment)),
        )


def test_parse_exclude_block_classifies_unit_file_and_unrecognized_lines():
    text = "\n".join(
        [
            "# BEGIN ai-bootstrap sidecar",
            unit_exclude_line(UNIT),
            escape_exact_path(f"{UNIT}/scratch.txt"),
            "some line the sidecar does not understand",
            "# END ai-bootstrap sidecar",
        ]
    )
    parsed = parse_exclude_block(text)
    assert parsed.listed_units == frozenset({UNIT})
    assert parsed.listed_files == frozenset({f"{UNIT}/scratch.txt"})
    assert parsed.unrecognized_lines == ("some line the sidecar does not understand",)


def test_parse_exclude_block_finds_a_listed_unit_for_a_skill_that_no_longer_ships():
    # The manifest is empty and the profile no longer includes this skill,
    # but the line is still recognized as a unit line (Decision 23).
    text = "\n".join(
        [
            "# BEGIN ai-bootstrap sidecar",
            unit_exclude_line(UNIT),
            "# END ai-bootstrap sidecar",
        ]
    )
    parsed = parse_exclude_block(text)
    assert parsed.listed_units == frozenset({UNIT})


def test_parse_exclude_block_empty_without_markers():
    assert parse_exclude_block("no sidecar block here\n") == ExcludeBlockContents()


def test_recorded_content_matches_desired_but_line_missing_is_adopted_not_reported():
    # S3 sibling: a stale record whose bytes already equal the desired
    # content is proof enough on its own (Decision 23); no exclude line and
    # no "locally modified" false report.
    content = {"SKILL.md": b"already-current"}
    result = plan(
        desired_units={UNIT: desired(content)},
        manifest=manifest_with(units={UNIT: recorded(content)}),
        excluded=frozenset(),  # the line is missing entirely
        snapshots={UNIT: snapshot(content)},
    )
    assert kinds(result) == ["unchanged"]
    assert result.reports == ()
    assert unit_exclude_line(UNIT) in result.exclude_lines_final


def test_listed_no_record_content_differs_from_desired_is_unfinished():
    # S3: a crash during a fresh install, then new content before the rerun.
    # The unit is listed (the write-phase exclude block already covered it)
    # but has no record; it must stay hidden and reported, not become
    # "foreign" and lose its line.
    on_disk = {"SKILL.md": b"partial-old-content"}
    new_desired = {"SKILL.md": b"brand-new-content"}
    result = plan(
        desired_units={UNIT: desired(new_desired)},
        manifest=None,
        excluded={UNIT},
        snapshots={UNIT: snapshot(on_disk)},
    )
    assert kinds(result) == []
    assert result.reports[0].category == "SKIPPED"
    assert "unfinished" in result.reports[0].remedy
    assert unit_exclude_line(UNIT) in result.exclude_lines_write
    assert unit_exclude_line(UNIT) in result.exclude_lines_final
    assert UNIT not in result.next_manifest.units


def test_listed_unit_with_no_desired_content_is_unfinished_not_dropped():
    # S3: a crash, or the manifest moved aside, then a skill stops
    # shipping. Because the unit is still listed, it must be classified
    # (required_snapshot_units) and kept hidden, not silently un-hidden.
    on_disk = {"SKILL.md": b"leftover-content"}
    result = plan(
        desired_units={},
        manifest=None,
        excluded={UNIT},
        snapshots={UNIT: snapshot(on_disk)},
    )
    assert kinds(result) == []
    assert UNIT not in result.next_manifest.units
    assert unit_exclude_line(UNIT) in result.exclude_lines_final
    assert any(r.path == UNIT for r in result.reports)


def test_tracked_and_listed_with_no_record_is_team_takeover_using_desired_reference():
    # S3: a crash during a fresh install, then the team tracks a file in the
    # unit. Must become a team takeover (using the desired content as the
    # ownership reference), not a bare team_owned that leaves our own
    # untracked bytes exposed.
    desired_content = {"SKILL.md": b"team", "notes.txt": b"sidecar-owned"}
    disk = {
        "SKILL.md": b"team-checked-out",
        "notes.txt": b"sidecar-owned",  # untracked, matches desired -> deleted
    }
    snap = snapshot(disk, tracked={"SKILL.md"})
    result = plan(
        desired_units={UNIT: desired(desired_content)},
        manifest=None,
        excluded={UNIT},
        snapshots={UNIT: snap},
    )
    action_kinds = {(a.kind, a.path) for a in result.actions if a.unit == UNIT}
    assert ("team_takeover_delete", f"{UNIT}/notes.txt") in action_kinds
    assert UNIT not in result.next_manifest.units


def test_team_takeover_after_crashed_update_matches_desired_not_only_record():
    # S3: a crash during an update, then a team takeover. Sidecar bytes must
    # not be marked RETAINED just because they no longer match the stale
    # record (Decision 23: match the record OR the desired content).
    old_content = {"SKILL.md": b"team", "notes.txt": b"old-bytes"}
    new_content = {"SKILL.md": b"team", "notes.txt": b"new-bytes-after-swap"}
    disk = {
        "SKILL.md": b"team-checked-out",
        "notes.txt": b"new-bytes-after-swap",  # already swapped to the new bytes
    }
    snap = snapshot(disk, tracked={"SKILL.md"})
    result = plan(
        desired_units={UNIT: desired(new_content)},
        manifest=manifest_with(units={UNIT: recorded(old_content)}),
        snapshots={UNIT: snap},
    )
    action_kinds = {(a.kind, a.path) for a in result.actions if a.unit == UNIT}
    assert ("team_takeover_delete", f"{UNIT}/notes.txt") in action_kinds
    assert not any(r.category == "RETAINED" for r in result.reports)


# --------------------------------------------------------------------------
# Phase G step 4: preserving edited copies of a taken skill (Decision 24)
# --------------------------------------------------------------------------


def test_preserved_unit_slug_is_one_level_deep_and_content_addressed():
    slug = preserved_unit_slug(UNIT, "a" * 64)
    assert "/" not in slug
    assert slug == f"{UNIT.replace('/', '__')}--{'a' * 64}"


def test_taken_skill_locally_modified_unit_is_preserved():
    record_content = {"SKILL.md": b"recorded"}
    edited_content = {"SKILL.md": b"edited-by-a-person"}
    result = plan(
        desired_units={
            UNIT: desired(record_content),
            OTHER_UNIT: desired(record_content),
        },
        manifest=manifest_with(units={OTHER_UNIT: recorded(record_content)}),
        preserved_destinations={
            OTHER_UNIT: "/fake/git-dir/ai-bootstrap-sidecar-preserved/x"
        },
        snapshots={
            UNIT: snapshot({"SKILL.md": b"team"}, tracked={"SKILL.md"}),
            OTHER_UNIT: snapshot(edited_content),
        },
    )
    assert kinds(result, OTHER_UNIT) == ["preserve"]
    assert OTHER_UNIT not in result.next_manifest.units
    assert unit_exclude_line(OTHER_UNIT) not in result.exclude_lines_final
    preserved_reports = [r for r in result.reports if r.category == "PRESERVED"]
    assert len(preserved_reports) == 1
    assert preserved_reports[0].path == OTHER_UNIT


def test_taken_skill_unfinished_unit_is_preserved():
    on_disk = {"SKILL.md": b"unfinished-copy"}
    result = plan(
        desired_units={
            UNIT: desired({"SKILL.md": b"team"}),
            OTHER_UNIT: desired({"SKILL.md": b"team"}),
        },
        manifest=None,
        excluded={OTHER_UNIT},
        snapshots={
            UNIT: snapshot({"SKILL.md": b"team"}, tracked={"SKILL.md"}),
            OTHER_UNIT: snapshot(on_disk),
        },
    )
    assert kinds(result, OTHER_UNIT) == ["preserve"]
    assert OTHER_UNIT not in result.next_manifest.units


def test_taken_skill_preserve_conflict_keeps_unit_in_place_and_reports():
    record_content = {"SKILL.md": b"recorded"}
    edited_content = {"SKILL.md": b"edited-by-a-person"}
    result = plan(
        desired_units={
            UNIT: desired(record_content),
            OTHER_UNIT: desired(record_content),
        },
        manifest=manifest_with(units={OTHER_UNIT: recorded(record_content)}),
        preserved_conflicts={OTHER_UNIT},
        preserved_destinations={OTHER_UNIT: "/fake/preserved/already-exists"},
        snapshots={
            UNIT: snapshot({"SKILL.md": b"team"}, tracked={"SKILL.md"}),
            OTHER_UNIT: snapshot(edited_content),
        },
    )
    assert kinds(result, OTHER_UNIT) == []
    assert result.next_manifest.units[OTHER_UNIT] == recorded(record_content)
    assert unit_exclude_line(OTHER_UNIT) in result.exclude_lines_final
    report = next(r for r in result.reports if r.path == OTHER_UNIT)
    assert report.category == "SKIPPED"
    assert "already-exists" in report.remedy


# --------------------------------------------------------------------------
# Phase G step 7: stable manifest namespace (Decision 32, L1, L4)
# --------------------------------------------------------------------------


def test_manifest_rejects_a_unit_path_with_a_backslash():
    # The backslash sits inside an otherwise valid segment (a normal "/"
    # write-root prefix), so a check that only looks for the wrong path
    # shape would miss it (L4).
    path = f"{CLAUDE_ROOT}/pony\\tail"
    body = {
        "schema_version": 1,
        "units": {path: {"files": {"a": "a" * 64}, "hash": "a" * 64}},
        "retained": [],
    }
    with pytest.raises(ManifestError, match="unsafe unit path"):
        parse_manifest(json.dumps(body))


def test_manifest_rejects_a_retained_path_with_a_backslash():
    path = f"{UNIT}/notes\\file.txt"
    body = {
        "schema_version": 1,
        "units": {},
        "retained": [path],
    }
    with pytest.raises(ManifestError, match="unsafe retained path"):
        parse_manifest(json.dumps(body))


def test_retired_write_root_manifest_unit_is_still_valid_and_goes_through_remove():
    import sidecar_overlay as sidecar_overlay_module

    retired_root = ".claude/retired-skills"
    original = sidecar_overlay_module._ALL_SKILL_WRITE_ROOTS
    sidecar_overlay_module._ALL_SKILL_WRITE_ROOTS = original + (retired_root,)
    try:
        retired_unit = f"{retired_root}/{SKILL}"
        body = {
            "schema_version": 1,
            "units": {
                retired_unit: {"files": {"SKILL.md": "a" * 64}, "hash": "a" * 64}
            },
            "retained": [],
        }
        parsed = parse_manifest(json.dumps(body))
        assert retired_unit in parsed.units
    finally:
        sidecar_overlay_module._ALL_SKILL_WRITE_ROOTS = original


# --------------------------------------------------------------------------
# Phase G step 1 follow-up: case-insensitive team takeover (Decision 25,
# MAJOR in the round-2 review; plan step 1's last bullet)
# --------------------------------------------------------------------------


def test_case_insensitive_tracked_folder_triggers_team_takeover_not_preserve():
    # Index entry ".claude/skills/Ponytail/SKILL.md" (case variant); disk
    # unit ".claude/skills/ponytail/" holds the team's checked-out SKILL.md
    # bytes plus the sidecar's own untracked LICENSE. With core.ignorecase
    # true, this must be a team takeover: LICENSE (matches the record) is
    # deleted, SKILL.md is never deleted, removed, or preserved -- team
    # content must never be touched, and it must not fall through to
    # "locally modified"/"preserve" just because its hash doesn't match.
    license_bytes = b"MIT-LICENSE-TEXT\n"
    record = recorded({"SKILL.md": b"sidecar-original\n", "LICENSE": license_bytes})
    disk = {"SKILL.md": b"TEAM-CHECKED-OUT-CONTENT\n", "LICENSE": license_bytes}
    index_path = f"{CLAUDE_ROOT}/Ponytail/SKILL.md"

    tracked_files = _unit_index_relpaths(
        UNIT, frozenset({index_path}), ignorecase=True, disk_relpaths=frozenset(disk)
    )
    snap = UnitSnapshot(
        exists=True,
        tracked_files=tracked_files,
        file_hashes=unit_files(disk),
        ignored_files=frozenset(),
    )

    result = plan(
        desired_units={
            UNIT: desired({"SKILL.md": b"sidecar-original\n", "LICENSE": license_bytes})
        },
        manifest=manifest_with(units={UNIT: record}),
        ignorecase=True,
        snapshots={UNIT: snap},
    )

    action_kinds = {(a.kind, a.path) for a in result.actions if a.unit == UNIT}
    assert ("team_takeover_delete", f"{UNIT}/LICENSE") in action_kinds
    assert not any(a.path == f"{UNIT}/SKILL.md" for a in result.actions)
    assert not any(a.kind == "preserve" for a in result.actions if a.unit == UNIT)
    assert UNIT not in result.next_manifest.units


def test_case_variant_tracked_file_is_never_counted_as_untracked():
    # A tracked "skill.md" (lowercase, as it appears in the index) must
    # reconcile against the disk's actual "SKILL.md" casing, or the exact
    # string-based ``untracked_files`` computation would still expose it.
    tracked_index_path = f"{UNIT}/skill.md"
    disk_relpaths = frozenset({"SKILL.md"})

    tracked_files = _unit_index_relpaths(
        UNIT,
        frozenset({tracked_index_path}),
        ignorecase=True,
        disk_relpaths=disk_relpaths,
    )
    assert tracked_files == frozenset({"SKILL.md"})

    snap = UnitSnapshot(
        exists=True,
        tracked_files=tracked_files,
        file_hashes=unit_files({"SKILL.md": b"team-content\n"}),
        ignored_files=frozenset(),
    )
    assert snap.untracked_files == frozenset()


def test_case_variant_without_ignorecase_is_not_reconciled():
    # Sanity guard: without core.ignorecase, casing is never reconciled --
    # a case-variant tracked path is a genuinely different file.
    tracked_files = _unit_index_relpaths(
        UNIT,
        frozenset({f"{UNIT}/skill.md"}),
        ignorecase=False,
        disk_relpaths=frozenset({"SKILL.md"}),
    )
    assert tracked_files == frozenset({"skill.md"})


# --------------------------------------------------------------------------
# Phase G review round 3: CRITICAL, unrecognized exclude-block lines
# --------------------------------------------------------------------------


def test_unrecognized_line_is_kept_and_reported_every_run():
    garbage_line = "not-a-recognized-sidecar-line"
    result = plan(
        desired_units={},
        manifest=None,
        unrecognized_lines={garbage_line},
        snapshots={},
    )
    assert garbage_line in result.exclude_lines_write
    assert garbage_line in result.exclude_lines_final
    matching = [r for r in result.reports if r.path == garbage_line]
    assert len(matching) == 1
    assert matching[0].category == "RETAINED"
    assert garbage_line in matching[0].remedy
    assert "does not recognize" in matching[0].remedy


def test_unrecognized_line_survives_plan_apply_plan_again():
    garbage_line = "notes.txt"
    first = plan(desired_units={}, manifest=None, unrecognized_lines={garbage_line})
    second = plan(
        desired_units={},
        manifest=first.next_manifest,
        unrecognized_lines={garbage_line},
    )
    assert first.exclude_lines_final == second.exclude_lines_final
    assert garbage_line in second.exclude_lines_final
    assert any(r.path == garbage_line for r in second.reports)


def test_parse_exclude_block_unrecognized_line_reaches_the_planner_via_real_text():
    text = "\n".join(
        [
            "# BEGIN ai-bootstrap sidecar",
            "notes.txt",
            "# END ai-bootstrap sidecar",
        ]
    )
    parsed = parse_exclude_block(text)
    assert parsed.unrecognized_lines == ("notes.txt",)
    result = plan(
        desired_units={},
        manifest=None,
        unrecognized_lines=parsed.unrecognized_lines,
    )
    assert "notes.txt" in result.exclude_lines_write
    assert "notes.txt" in result.exclude_lines_final
