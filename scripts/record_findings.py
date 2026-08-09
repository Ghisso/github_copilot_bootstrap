#!/usr/bin/env python3
"""Findings recorder for the REVIEW stage's severity-gated findings report.

Persists the reviewer's surviving findings (after the primary + verification
passes converge) as a git-metadata-stamped JSON artifact, matching the
schema the commit/push gates verify against
(.claude/instructions/quality-and-testing.instructions.md).

Usage:
    uv run python .claude/scripts/record_findings.py src/ --profile code \
        --profile ponytail --phase phase-one \
        --findings-json findings.json --out .claude/quality_reports/findings-<ts>.json
    echo '[]' | uv run python .claude/scripts/record_findings.py src/ --profile ponytail --phase phase-one \
        --out .claude/quality_reports/findings-<ts>.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, datetime
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
    """Twin of quality_score.py's `_content_hash`: a content signature of the
    branch's changes relative to `base`, computed as `git hash-object` of the
    raw `git diff <base>` output. The commit/push gates recompute the
    identical value against whichever report (score or findings) they are
    checking, so both scripts must derive it the same way. Duplicated rather
    than imported - these are deliberately single-file, no-dependency
    scripts (see shared/scripts/quality_score.py, this script's twin)."""
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


def git_metadata(target: Path, phase: str, base_ref: str) -> dict[str, object]:
    """Twin of quality_score.py's `git_metadata`; see that file for the
    rationale behind each field. Duplicated deliberately - see module
    docstring and `_content_hash` above."""
    cwd = Path.cwd()
    inside = _git(["rev-parse", "--is-inside-work-tree"], cwd)
    if inside != "true":
        return {
            "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
    # See quality_score.py's git_metadata for why staged-only changes do not
    # count as "dirty".
    unstaged = _git(["diff", "--name-only"], cwd)
    try:
        target_str = str(target.resolve().relative_to(Path(repo_root)))
    except ValueError:
        target_str = str(target)
    return {
        "generated_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
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
    text = sys.stdin.read() if source == "-" else Path(source).read_text(encoding="utf-8")
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
            raise ValueError(f"finding severity must be one of {sorted(VALID_SEVERITIES)}; got {severity!r}")
        if not finding.get("title"):
            raise ValueError("each finding must have a non-empty title")
    return findings


def count_severities(findings: list[dict[str, object]]) -> dict[str, int]:
    counts = {"critical": 0, "major": 0, "minor": 0}
    for finding in findings:
        counts[str(finding["severity"]).lower()] += 1
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Findings recorder for the REVIEW stage's severity gate.")
    parser.add_argument("target", help="File or directory the findings apply to.")
    parser.add_argument("--findings-json", default="-", help="Path to a JSON list of findings, or '-' for stdin.")
    parser.add_argument("--out", type=Path, required=True, help="Write the JSON result to this path.")
    parser.add_argument("--phase", default="", help="Current small-plan phase slug.")
    parser.add_argument("--base-ref", default="dev", help="Base ref used for branch metadata.")
    parser.add_argument(
        "--profile",
        action="append",
        default=[],
        help="Review profile that was executed; repeat for every reviewed profile.",
    )
    args = parser.parse_args()

    try:
        findings = load_findings(args.findings_json)
        profiles_reviewed = sorted({profile.strip() for profile in args.profile if profile.strip()})
        for finding in findings:
            profile = finding.get("profile")
            if profiles_reviewed and profile not in profiles_reviewed:
                raise ValueError(
                    "each finding profile must be present in the repeated --profile arguments; "
                    f"got {profile!r}"
                )
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"error: invalid findings-json: {exc}", file=sys.stderr)
        sys.exit(1)

    counts = count_severities(findings)
    ponytail_reviewed = "ponytail" in profiles_reviewed
    # `counts` is serialized before `findings` so the gate's flat-text
    # `critical`-key scanner (json_file_number_value in _lib-frontmatter.sh,
    # which is not JSON-nesting-aware) matches counts.critical before it can
    # reach any free-text finding title/file value that happens to contain a
    # colliding `"critical": <digits>` substring.
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

    print(
        f"recorded {len(findings)} finding(s): "
        f"{counts['critical']} critical, {counts['major']} major, {counts['minor']} minor; "
        f"ponytail_reviewed={str(ponytail_reviewed).lower()}"
    )
    print(f"report: {args.out}")
    sys.exit(0)


if __name__ == "__main__":
    main()
