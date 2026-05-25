#!/usr/bin/env python3
"""Validate bootstrap plan frontmatter."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]


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
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            current_key = key.strip()
            value = value.strip().strip('"').strip("'")
            data[current_key] = value
    return data


def require_fields(path: Path, data: dict[str, Any], fields: list[str], errors: list[str]) -> None:
    for field in fields:
        if field not in data or data[field] in ("", []):
            errors.append(f"{path}: missing required field: {field}")


def validate_big_plan(path: Path, data: dict[str, Any], errors: list[str]) -> None:
    require_fields(
        path,
        data,
        ["name", "type", "status", "originating_branch", "implementation_branch", "phases"],
        errors,
    )
    status = str(data.get("status", ""))
    if status not in {"planning", "in-progress", "complete"}:
        errors.append(f"{path}: invalid status for big-plan: {status}")
    if status in {"in-progress", "complete"}:
        require_fields(path, data, ["started_at"], errors)
    if status == "in-progress":
        require_fields(path, data, ["current_phase"], errors)
    if not isinstance(data.get("phases"), list) or not data.get("phases"):
        errors.append(f"{path}: phases must be a non-empty list")


def validate_small_plan(path: Path, data: dict[str, Any], errors: list[str]) -> None:
    require_fields(path, data, ["name", "type", "parent_plan", "phase_index", "status"], errors)
    status = str(data.get("status", ""))
    if status not in {"in-progress", "complete"}:
        errors.append(f"{path}: invalid status for small-plan: {status}")
    if status == "complete":
        require_fields(path, data, ["closeout_session_log"], errors)


def validate_plan(path: Path, errors: list[str]) -> None:
    data = parse_frontmatter(path)
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
