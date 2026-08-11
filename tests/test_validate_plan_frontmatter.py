"""Tests for plan frontmatter validation."""

from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import validate_plan_frontmatter as validator  # noqa: E402

BLOCK_SCALAR_HEADERS = [
    f"{style}{suffix}"
    for style in ("|", ">")
    for suffix in (
        "",
        "+",
        "-",
        *(str(indent) for indent in range(1, 10)),
        *(f"{chomp}{indent}" for chomp in ("+", "-") for indent in range(1, 10)),
        *(f"{indent}{chomp}" for indent in range(1, 10) for chomp in ("+", "-")),
    )
]


def write_plan(path: Path, frontmatter: str) -> Path:
    """Write a plan with the supplied frontmatter."""
    path.write_text(f"---\n{frontmatter.strip()}\n---\n\n# Plan\n", encoding="utf-8")
    return path


def cancellation_fields(
    evidence: str = "evidence.md",
    *,
    cancelled_at: str = "2026-08-11T06:30:00Z",
    reason: str = "Measured value did not justify implementation",
) -> str:
    """Return valid cancellation fields for a test plan."""
    return (
        f"cancelled_at: {cancelled_at}\n"
        f"cancelled_reason: {reason}\n"
        f"cancelled_evidence: {evidence}"
    )


def small_plan(status: str, extra: str = "") -> str:
    """Return small-plan frontmatter for a test case."""
    return f"""
name: 2026-08-11_phase-C-example
type: small-plan
parent_plan: example
phase_index: 3
status: {status}
{extra}
"""


def big_plan(status: str, extra: str = "") -> str:
    """Return big-plan frontmatter for a test case."""
    return f"""
name: example
type: big-plan
status: {status}
originating_branch: dev
implementation_branch: example_implementation
phases:
  - 2026-08-11_phase-C-example
{extra}
"""


def validation_errors(path: Path) -> list[str]:
    """Validate one plan and return its accumulated errors."""
    errors: list[str] = []
    validator.validate_plan(path, errors)
    return errors


def test_accepts_cancelled_small_plan_with_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    (tmp_path / "evidence.md").write_text(
        "# Decision\n\n**Status:** CANCELLED\n", encoding="utf-8"
    )
    plan = write_plan(
        tmp_path / "small.md", small_plan("cancelled", cancellation_fields())
    )

    assert validation_errors(plan) == []


@pytest.mark.parametrize("missing_field", validator.CANCELLED_FIELDS)
def test_rejects_each_missing_cancellation_field(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, missing_field: str
) -> None:
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    (tmp_path / "evidence.md").write_text("**Status:** CANCELLED\n", encoding="utf-8")
    fields = {
        "cancelled_at": "2026-08-11T06:30:00Z",
        "cancelled_reason": "The phase is no longer authorized",
        "cancelled_evidence": "evidence.md",
    }
    del fields[missing_field]
    extra = "\n".join(f"{key}: {value}" for key, value in fields.items())
    plan = write_plan(tmp_path / "small.md", small_plan("cancelled", extra))

    errors = validation_errors(plan)

    assert any(f"missing required field: {missing_field}" in error for error in errors)


@pytest.mark.parametrize(
    "cancelled_at", ["2026-08-11T06:30:00", "2026-08-11", "yesterday"]
)
def test_rejects_malformed_cancelled_at(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cancelled_at: str,
) -> None:
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    (tmp_path / "evidence.md").write_text("**Status:** CANCELLED\n", encoding="utf-8")
    fields = cancellation_fields().replace("2026-08-11T06:30:00Z", cancelled_at)
    plan = write_plan(tmp_path / "small.md", small_plan("cancelled", fields))

    assert any(
        "cancelled_at must use UTC format" in error for error in validation_errors(plan)
    )


@pytest.mark.parametrize(
    "cancelled_at", ["2026-02-30T06:30:00Z", "2026-08-11T25:00:00Z"]
)
def test_rejects_impossible_cancelled_at(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    cancelled_at: str,
) -> None:
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    (tmp_path / "evidence.md").write_text("**Status:** CANCELLED\n", encoding="utf-8")
    plan = write_plan(
        tmp_path / "small.md",
        small_plan("cancelled", cancellation_fields(cancelled_at=cancelled_at)),
    )

    assert any(
        "cancelled_at must be a valid UTC timestamp" in error
        for error in validation_errors(plan)
    )


@pytest.mark.parametrize(
    "reason",
    [
        '"   "',
        "''",
        "[]",
        "[not, prose]",
        "{}",
        "{decision: cancelled}",
        "- list item",
        "# comment only",
        "First line\n  continued line",
        "|\n  block line",
        "\n  - list item",
    ],
)
def test_rejects_non_scalar_or_non_meaningful_cancelled_reason(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reason: str,
) -> None:
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    (tmp_path / "evidence.md").write_text("**Status:** CANCELLED\n", encoding="utf-8")
    plan = write_plan(
        tmp_path / "small.md",
        small_plan("cancelled", cancellation_fields(reason=reason)),
    )

    assert any("cancelled_reason" in error for error in validation_errors(plan))


@pytest.mark.parametrize("reason", BLOCK_SCALAR_HEADERS)
def test_rejects_every_yaml_block_scalar_header_for_cancelled_reason(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reason: str,
) -> None:
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    (tmp_path / "evidence.md").write_text("**Status:** CANCELLED\n", encoding="utf-8")
    plan = write_plan(
        tmp_path / "small.md",
        small_plan("cancelled", cancellation_fields(reason=reason)),
    )

    assert any("plain single-line scalar" in error for error in validation_errors(plan))


@pytest.mark.parametrize("header", BLOCK_SCALAR_HEADERS)
@pytest.mark.parametrize(
    "comment_suffix", ["#", " #", "\t# explanation", " \t # audit"]
)
def test_rejects_block_scalar_header_with_comment_suffix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    header: str,
    comment_suffix: str,
) -> None:
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    (tmp_path / "evidence.md").write_text("**Status:** CANCELLED\n", encoding="utf-8")
    plan = write_plan(
        tmp_path / "small.md",
        small_plan(
            "cancelled",
            cancellation_fields(reason=f"{header}{comment_suffix}"),
        ),
    )

    assert any("plain single-line scalar" in error for error in validation_errors(plan))


@pytest.mark.parametrize(
    "reason",
    [
        "| ordinary prose",
        "> threshold was not met",
        "|2 is a literal measurement",
        "|- remains ordinary with words",
        ">+9 remains ordinary with words",
    ],
)
def test_accepts_prose_starting_like_a_block_scalar_header(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    reason: str,
) -> None:
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    (tmp_path / "evidence.md").write_text("**Status:** CANCELLED\n", encoding="utf-8")
    plan = write_plan(
        tmp_path / "small.md",
        small_plan("cancelled", cancellation_fields(reason=reason)),
    )

    assert validation_errors(plan) == []


def test_rejects_missing_cancellation_evidence_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    plan = write_plan(
        tmp_path / "small.md", small_plan("cancelled", cancellation_fields())
    )

    assert any(
        "cannot read cancelled_evidence" in error for error in validation_errors(plan)
    )


def test_rejects_evidence_without_cancelled_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    (tmp_path / "evidence.md").write_text(
        "# Decision\n\n**Status:** IN-PROGRESS\n", encoding="utf-8"
    )
    plan = write_plan(
        tmp_path / "small.md", small_plan("cancelled", cancellation_fields())
    )

    assert any(
        "must contain **Status:** CANCELLED" in error
        for error in validation_errors(plan)
    )


@pytest.mark.parametrize(
    "content",
    [
        "**Status:**\nCANCELLED\n",
        " **Status:** CANCELLED\n",
        "**Status:** CANCELED\n",
        "**Status:** cancelled\n",
        "**Status:** CANCELLED_extra\n",
        "**Status:**\vCANCELLED\n",
    ],
)
def test_rejects_split_line_and_near_miss_cancelled_markers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    content: str,
) -> None:
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    (tmp_path / "evidence.md").write_text(content, encoding="utf-8")
    plan = write_plan(
        tmp_path / "small.md", small_plan("cancelled", cancellation_fields())
    )

    assert any(
        "must contain **Status:** CANCELLED" in error
        for error in validation_errors(plan)
    )


def test_accepts_tab_before_cancelled_marker_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    (tmp_path / "evidence.md").write_text("**Status:**\tCANCELLED\n", encoding="utf-8")
    plan = write_plan(
        tmp_path / "small.md", small_plan("cancelled", cancellation_fields())
    )

    assert validation_errors(plan) == []


def test_rejects_directory_as_cancellation_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    (tmp_path / "evidence").mkdir()
    plan = write_plan(
        tmp_path / "small.md",
        small_plan("cancelled", cancellation_fields("evidence")),
    )

    assert any(
        "regular readable text file" in error for error in validation_errors(plan)
    )


def test_rejects_invalid_utf8_cancellation_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    (tmp_path / "evidence.md").write_bytes(b"\xff\xfe")
    plan = write_plan(
        tmp_path / "small.md", small_plan("cancelled", cancellation_fields())
    )

    assert any(
        "cannot read cancelled_evidence" in error for error in validation_errors(plan)
    )


@pytest.mark.parametrize(
    "evidence_field",
    ["cancelled_evidence: bad\x00path", "cancelled_evidence:\n  - evidence.md"],
)
def test_rejects_invalid_cancellation_evidence_path_shapes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    evidence_field: str,
) -> None:
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    fields = cancellation_fields().rsplit("\n", 1)[0]
    plan = write_plan(
        tmp_path / "small.md",
        small_plan("cancelled", f"{fields}\n{evidence_field}"),
    )

    assert any("cancelled_evidence" in error for error in validation_errors(plan))


def test_rejects_symlink_loop_as_cancellation_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    (tmp_path / "loop.md").symlink_to("loop.md")
    plan = write_plan(
        tmp_path / "small.md",
        small_plan("cancelled", cancellation_fields("loop.md")),
    )

    assert any(
        "cannot read cancelled_evidence" in error for error in validation_errors(plan)
    )


def test_rejects_symlink_to_evidence_outside_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    outside_evidence = tmp_path / "outside.md"
    outside_evidence.write_text("**Status:** CANCELLED\n", encoding="utf-8")
    (repository_root / "evidence.md").symlink_to(outside_evidence)
    monkeypatch.setattr(validator, "REPO_ROOT", repository_root)
    plan = write_plan(
        repository_root / "small.md",
        small_plan("cancelled", cancellation_fields()),
    )

    assert any(
        "stay inside the repository" in error for error in validation_errors(plan)
    )


def test_rejects_unreadable_cancellation_evidence_portably(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    evidence_path = tmp_path / "evidence.md"
    evidence_path.write_text("**Status:** CANCELLED\n", encoding="utf-8")
    plan = write_plan(
        tmp_path / "small.md", small_plan("cancelled", cancellation_fields())
    )
    data = validator.parse_frontmatter(plan)

    def deny_read(self: Path, *args: object, **kwargs: object) -> str:
        raise PermissionError("permission denied")

    monkeypatch.setattr(Path, "read_text", deny_read)
    errors: list[str] = []
    validator.validate_cancellation(plan, data, errors)

    assert any("cannot read cancelled_evidence" in error for error in errors)


def test_accepts_cancelled_big_plan_without_started_at_or_current_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    (tmp_path / "evidence.md").write_text(
        "**Status:** CANCELLED because the plan was called off\n", encoding="utf-8"
    )
    plan = write_plan(tmp_path / "big.md", big_plan("cancelled", cancellation_fields()))

    assert validation_errors(plan) == []


@pytest.mark.parametrize("status", ["canceled", "abandoned"])
def test_rejects_near_miss_statuses(tmp_path: Path, status: str) -> None:
    plan = write_plan(tmp_path / "small.md", small_plan(status))

    assert any(
        "invalid status for small-plan" in error for error in validation_errors(plan)
    )


@pytest.mark.parametrize(
    ("status", "extra"),
    [
        ("in-progress", ""),
        ("complete", "closeout_session_log: .claude/session_logs/closeout.md"),
    ],
)
def test_preserves_existing_small_plan_statuses(
    tmp_path: Path, status: str, extra: str
) -> None:
    plan = write_plan(tmp_path / "small.md", small_plan(status, extra))

    assert validation_errors(plan) == []


def test_complete_small_plan_still_requires_closeout_log(tmp_path: Path) -> None:
    plan = write_plan(tmp_path / "small.md", small_plan("complete"))

    assert any(
        "missing required field: closeout_session_log" in error
        for error in validation_errors(plan)
    )


@pytest.mark.parametrize(
    ("status", "extra"),
    [
        ("planning", ""),
        ("in-progress", "started_at: 2026-08-11T06:00:00Z\ncurrent_phase: phase-a"),
        ("complete", "started_at: 2026-08-11T06:00:00Z"),
    ],
)
def test_preserves_existing_big_plan_statuses(
    tmp_path: Path, status: str, extra: str
) -> None:
    plan = write_plan(tmp_path / "big.md", big_plan(status, extra))

    assert validation_errors(plan) == []


@pytest.mark.parametrize("evidence", ["/tmp/evidence.md", "../evidence.md"])
def test_rejects_evidence_outside_repository(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    evidence: str,
) -> None:
    monkeypatch.setattr(validator, "REPO_ROOT", tmp_path)
    plan = write_plan(
        tmp_path / "small.md",
        small_plan("cancelled", cancellation_fields(evidence)),
    )

    errors = validation_errors(plan)

    assert any("repository" in error for error in errors)
