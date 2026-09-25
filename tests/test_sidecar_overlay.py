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
    Manifest,
    ManifestError,
    ManifestUnit,
    Report,
    UnitSnapshot,
    compute_file_hash,
    compute_unit_hash,
    escape_exact_path,
    escape_ignore_segment,
    parse_manifest,
    plan_sidecar_reconciliation,
    required_snapshot_units,
    serialize_manifest,
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
    read_list=None,
    snapshots=None,
):
    return plan_sidecar_reconciliation(
        desired_units=desired_units or {},
        manifest=manifest,
        excluded_units=excluded,
        read_list_skill_names=read_list or {},
        snapshots=snapshots or {},
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
    assert "delete or restore" in result.reports[0].remedy


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


def test_skill_taken_keeps_and_reports_a_modified_copy_at_the_other_root():
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
    assert kinds(result, OTHER_UNIT) == []
    assert result.next_manifest.units[OTHER_UNIT] == recorded(record_content)
    assert any(r.path == OTHER_UNIT for r in result.reports)


def test_skill_taken_at_write_root_and_read_only_folder_gets_one_report():
    # A skill can be simultaneously taken at a write root (which already
    # reports itself) and present in a read-only folder. It must not also
    # get the separate read-only-folder report.
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
    assert len(result.reports) == 1
    assert result.reports[0].path == UNIT


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
        f"the repository tracks `{BRIDGE}`; the sidecar skips it at every root"
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
