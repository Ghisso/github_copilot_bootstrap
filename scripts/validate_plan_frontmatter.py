#!/usr/bin/env python3
"""Validate bootstrap plan frontmatter."""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
BIG_PLAN_STATUSES = {"planning", "in-progress", "complete", "cancelled"}
SMALL_PLAN_STATUSES = {"in-progress", "complete", "cancelled"}
CANCELLED_FIELDS = ("cancelled_at", "cancelled_reason", "cancelled_evidence")
CANCELLED_AT_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
CANCELLED_REASON_BLOCK_PATTERN = re.compile(
    r"^[|>](?:[+-][1-9]?|[1-9][+-]?)?(?:[ \t]*#.*)?$"
)
CANCELLED_STATUS_PATTERN = re.compile(
    r"^\*\*Status:\*\*[ \t]+CANCELLED\b", re.MULTILINE
)


def parse_frontmatter(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    parts = text.split("---\n", 2)
    if len(parts) != 3:
        return {}
    data: dict[str, Any] = {}
    current_key = ""
    for raw_line in parts[1].splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current_key:
            value = data.get(current_key)
            if not isinstance(value, list):
                value = [] if value in (None, "") else [str(value)]
                data[current_key] = value
            value.append(line[4:].strip())
            continue
        if line.startswith((" ", "\t")) and current_key == "cancelled_reason":
            value = data.get(current_key)
            data[current_key] = [value, line.strip()]
            continue
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            current_key = key.strip()
            value = value.strip().strip('"').strip("'")
            data[current_key] = value
    return data


def frontmatter_key_count(path: Path, key: str) -> int:
    """Count top-level key occurrences in the hand-parsed frontmatter."""
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return 0
    parts = text.split("---\n", 2)
    if len(parts) != 3:
        return 0
    return sum(
        1
        for line in parts[1].splitlines()
        if not line.startswith((" ", "\t"))
        and ":" in line
        and line.split(":", 1)[0].strip() == key
    )


def require_fields(
    path: Path, data: dict[str, Any], fields: Sequence[str], errors: list[str]
) -> None:
    for field in fields:
        if field not in data or data[field] in ("", []):
            errors.append(f"{path}: missing required field: {field}")


def validate_cancellation(path: Path, data: dict[str, Any], errors: list[str]) -> None:
    """Validate the audit evidence required for a cancelled plan."""
    require_fields(path, data, CANCELLED_FIELDS, errors)

    cancelled_at = str(data.get("cancelled_at", ""))
    if cancelled_at:
        if not CANCELLED_AT_PATTERN.fullmatch(cancelled_at):
            errors.append(
                f"{path}: cancelled_at must use UTC format YYYY-MM-DDTHH:MM:SSZ"
            )
        else:
            try:
                datetime.strptime(cancelled_at, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                errors.append(f"{path}: cancelled_at must be a valid UTC timestamp")

    reason = data.get("cancelled_reason")
    if reason not in (None, "", []):
        if not isinstance(reason, str) or not reason.strip():
            errors.append(
                f"{path}: cancelled_reason must be meaningful plain single-line prose"
            )
        elif CANCELLED_REASON_BLOCK_PATTERN.fullmatch(
            reason.strip()
        ) or reason.lstrip().startswith(("[", "{", "- ", "#")):
            errors.append(
                f"{path}: cancelled_reason must be a plain single-line scalar"
            )

    evidence_value = data.get("cancelled_evidence", "")
    if evidence_value in ("", []):
        return
    if not isinstance(evidence_value, str):
        errors.append(f"{path}: cancelled_evidence must be a plain path scalar")
        return
    try:
        evidence_path = Path(evidence_value)
        if evidence_path.is_absolute():
            errors.append(f"{path}: cancelled_evidence must be repository-relative")
            return
        repository_root = REPO_ROOT.resolve(strict=True)
        evidence_path = (repository_root / evidence_path).resolve(strict=False)
        if not evidence_path.is_relative_to(repository_root):
            errors.append(f"{path}: cancelled_evidence must stay inside the repository")
            return
        evidence_path = evidence_path.resolve(strict=True)
        if not evidence_path.is_file():
            errors.append(
                f"{path}: cancelled_evidence must be a regular readable text file"
            )
            return
        evidence = evidence_path.read_text(encoding="utf-8")
    except (OSError, RuntimeError, TypeError, UnicodeError, ValueError) as error:
        errors.append(
            f"{path}: cannot read cancelled_evidence {evidence_path}: {error}"
        )
        return
    if not CANCELLED_STATUS_PATTERN.search(evidence):
        errors.append(f"{path}: cancelled_evidence must contain **Status:** CANCELLED")


def validate_big_plan(path: Path, data: dict[str, Any], errors: list[str]) -> None:
    require_fields(
        path,
        data,
        [
            "name",
            "type",
            "status",
            "originating_branch",
            "implementation_branch",
            "phases",
        ],
        errors,
    )
    status = str(data.get("status", ""))
    if status not in BIG_PLAN_STATUSES:
        errors.append(f"{path}: invalid status for big-plan: {status}")
    if status in {"in-progress", "complete"}:
        require_fields(path, data, ["started_at"], errors)
    if status == "in-progress":
        require_fields(path, data, ["current_phase"], errors)
    if status == "cancelled":
        validate_cancellation(path, data, errors)
    if not isinstance(data.get("phases"), list) or not data.get("phases"):
        errors.append(f"{path}: phases must be a non-empty list")


def validate_small_plan(path: Path, data: dict[str, Any], errors: list[str]) -> None:
    require_fields(
        path, data, ["name", "type", "parent_plan", "phase_index", "status"], errors
    )
    status = str(data.get("status", ""))
    if status not in SMALL_PLAN_STATUSES:
        errors.append(f"{path}: invalid status for small-plan: {status}")
    if status == "complete":
        require_fields(path, data, ["closeout_session_log"], errors)
    if status == "cancelled":
        validate_cancellation(path, data, errors)


def validate_plan(path: Path, errors: list[str]) -> None:
    data = parse_frontmatter(path)
    if frontmatter_key_count(path, "status") > 1:
        errors.append(f"{path}: duplicate status fields are not allowed")
        return
    plan_type = str(data.get("type", ""))
    if plan_type == "big-plan":
        validate_big_plan(path, data, errors)
    elif plan_type == "small-plan":
        validate_small_plan(path, data, errors)
    else:
        errors.append(f"{path}: type must be big-plan or small-plan")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path, help="Plan files to validate.")
    args = parser.parse_args()

    if args.paths:
        paths = args.paths
    else:
        plan_root = REPO_ROOT / ".claude" / "plans"
        if not plan_root.exists():
            return 0
        paths = sorted(plan_root.glob("*.md"))

    errors: list[str] = []
    for path in paths:
        if path.name == "README.md":
            continue
        validate_plan(path, errors)

    for error in errors:
        print(f"FAIL {error}", file=sys.stderr)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
