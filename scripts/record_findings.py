#!/usr/bin/env python3
"""Findings recorder for the REVIEW stage's severity-gated findings report.

Persists the reviewer's surviving findings (after the primary + verification
passes converge) as a git-metadata-stamped JSON artifact, matching the
schema the commit/push gates verify against
(.claude/instructions/quality-and-testing.instructions.md).

Usage:
    uv run python .claude/scripts/record_findings.py src/ --profile code \
        --profile ponytail --phase phase-one \
        --findings-json findings.json --out .claude/quality_reports/findings-phase-one.json
    echo '[]' | uv run python .claude/scripts/record_findings.py src/ --profile ponytail --phase phase-one \
        --out .claude/quality_reports/findings-phase-one.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


VALID_SEVERITIES = {"CRITICAL", "MAJOR", "MINOR"}


def _run(args: list[str], cwd: str = ".") -> tuple[int, str, str]:
    result = subprocess.run(args, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout, result.stderr


def _git(args: list[str], cwd: Path) -> str:
    rc, stdout, _ = _run(["git", *args], cwd=str(cwd))
    if rc != 0:
        return ""
    return stdout.strip()


def _content_hash(base: str, cwd: Path) -> str:
    """A content signature of the branch's changes relative to `base`,
    computed as `git hash-object` of the raw `git diff <base>` output. The
    commit/push gates recompute the identical value against the findings
    report they are checking. This is a deliberately single-file,
    no-dependency script, so the logic is not imported from elsewhere."""
    if not base:
        return ""
    diff = subprocess.run(
        ["git", "diff", "--no-color", "--no-ext-diff", base],
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )
    if diff.returncode != 0:
        return ""
    obj = subprocess.run(
        ["git", "hash-object", "--stdin"],
        input=diff.stdout,
        capture_output=True,
        text=True,
        cwd=str(cwd),
    )
    return obj.stdout.strip() if obj.returncode == 0 else ""


def untracked_target_files(target: Path, cwd: Path) -> list[str]:
    """Return untracked regular paths contained by the requested review target."""
    repo_root = _git(["rev-parse", "--show-toplevel"], cwd)
    if not repo_root:
        return []
    root_path = Path(repo_root).absolute()
    target_path = (
        (cwd / target).absolute() if not target.is_absolute() else target.absolute()
    )
    if target_path != root_path and root_path not in target_path.parents:
        return []
    rc, output, _ = _run(
        ["git", "status", "--porcelain=v1", "-z", "--untracked-files=all"],
        cwd=str(cwd),
    )
    if rc != 0:
        return []
    paths: list[str] = []
    for record in output.split("\0"):
        if not record.startswith("?? "):
            continue
        relative = record[3:]
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            continue
        if target_path == root_path or (root_path / candidate).is_relative_to(
            target_path
        ):
            paths.append(relative)
    return sorted(paths)


def display_path(path: str) -> str:
    """Render an untracked path on one safe terminal line."""
    return path.encode("unicode_escape").decode("ascii")


def git_metadata(target: Path, phase: str, base_ref: str) -> dict[str, object]:
    """Capture the git-metadata freshness binding for a findings report; see
    the module docstring and `_content_hash` above for the rationale."""
    cwd = Path.cwd()
    inside = _git(["rev-parse", "--is-inside-work-tree"], cwd)
    if inside != "true":
        return {
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "branch": "",
            "head_sha": "",
            "base_ref": base_ref,
            "merge_base_sha": "",
            "phase": phase,
            "dirty": False,
            "changed_files": [],
        }

    repo_root = _git(["rev-parse", "--show-toplevel"], cwd)
    branch = _git(["rev-parse", "--abbrev-ref", "HEAD"], cwd)
    head_sha = _git(["rev-parse", "HEAD"], cwd)
    merge_base = _git(["merge-base", base_ref, "HEAD"], cwd) if base_ref else ""
    changed: set[str] = set()
    for command in (
        ["diff", "--name-only", f"{base_ref}...HEAD"] if base_ref else [],
        ["diff", "--name-only"],
        ["diff", "--cached", "--name-only"],
    ):
        if not command:
            continue
        output = _git(command, cwd)
        changed.update(line for line in output.splitlines() if line.strip())
    # Staged changes destined for the commit are expected and do NOT count
    # as dirty, so the commit gate can require a fully-staged tree without
    # blocking every commit; this also catches edits made after findings
    # were recorded.
    unstaged = _git(["diff", "--name-only"], cwd)
    try:
        target_str = str(target.resolve().relative_to(Path(repo_root)))
    except ValueError:
        target_str = str(target)
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "branch": branch,
        "head_sha": head_sha,
        "base_ref": base_ref,
        "merge_base_sha": merge_base,
        "phase": phase,
        "target": target_str,
        "dirty": bool(unstaged.strip()),
        "content_hash": _content_hash(merge_base, cwd),
        "changed_files": sorted(changed),
    }


def load_findings(source: str) -> list[dict[str, object]]:
    text = (
        sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
    )
    text = text.strip()
    if not text:
        return []
    findings = json.loads(text)
    if not isinstance(findings, list):
        raise ValueError("findings-json must be a JSON list")
    for finding in findings:
        if not isinstance(finding, dict):
            raise ValueError("each finding must be a JSON object")
        severity = finding.get("severity")
        if severity not in VALID_SEVERITIES:
            raise ValueError(
                f"finding severity must be one of {sorted(VALID_SEVERITIES)}; got {severity!r}"
            )
        if not finding.get("title"):
            raise ValueError("each finding must have a non-empty title")
    return findings


def count_severities(findings: list[dict[str, object]]) -> dict[str, int]:
    counts = {"critical": 0, "major": 0, "minor": 0}
    for finding in findings:
        counts[str(finding["severity"]).lower()] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Findings recorder for the REVIEW stage's severity gate."
    )
    parser.add_argument("target", help="File or directory the findings apply to.")
    parser.add_argument(
        "--findings-json",
        default="-",
        help="Path to a JSON list of findings, or '-' for stdin.",
    )
    parser.add_argument(
        "--out", type=Path, required=True, help="Write the JSON result to this path."
    )
    parser.add_argument("--phase", default="", help="Current small-plan phase slug.")
    parser.add_argument(
        "--base-ref", default="dev", help="Base ref used for branch metadata."
    )
    parser.add_argument(
        "--profile",
        action="append",
        default=[],
        help="Review profile that was executed; repeat for every reviewed profile.",
    )
    args = parser.parse_args()

    try:
        findings = load_findings(args.findings_json)
        profiles_reviewed = sorted(
            {profile.strip() for profile in args.profile if profile.strip()}
        )
        if not profiles_reviewed:
            raise ValueError("at least one --profile is required")
        for finding in findings:
            profile = finding.get("profile")
            if not isinstance(profile, str) or not profile:
                raise ValueError("each finding must have a non-empty profile")
            if profile not in profiles_reviewed:
                raise ValueError(
                    "each finding profile must be present in the repeated --profile arguments; "
                    f"got {profile!r}"
                )
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"error: invalid findings-json: {exc}", file=sys.stderr)
        sys.exit(1)

    counts = count_severities(findings)
    ponytail_reviewed = "ponytail" in profiles_reviewed
    # Keep canonical report fields first for stable, readable JSON artifacts.
    result = {
        "counts": counts,
        "profiles_reviewed": profiles_reviewed,
        "findings": findings,
        **git_metadata(Path(args.target).resolve(), args.phase, args.base_ref),
    }
    if ponytail_reviewed:
        result["ponytail_reviewed"] = True
        result["ponytail_findings"] = sum(
            1 for finding in findings if finding.get("profile") == "ponytail"
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    untracked = untracked_target_files(Path(args.target), Path.cwd())
    if untracked:
        print(
            "warning: untracked target files are not included in git diff: "
            f"{', '.join(display_path(path) for path in untracked)}; stage intended files before recording again",
            file=sys.stderr,
        )

    print(
        f"recorded {len(findings)} finding(s): "
        f"{counts['critical']} critical, {counts['major']} major, {counts['minor']} minor; "
        f"ponytail_reviewed={str(ponytail_reviewed).lower()}"
    )
    print(f"report: {args.out}")
    sys.exit(0)


if __name__ == "__main__":
    main()
