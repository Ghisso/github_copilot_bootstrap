#!/usr/bin/env python3
"""Quality scorer for Python source files and directories.

Runs ruff, mypy, and pytest as subprocesses and aggregates results
into a single score against the rubric in .claude/instructions/quality-and-testing.instructions.md.

Usage:
    uv run python .claude/scripts/quality_score.py src/
    uv run python .claude/scripts/quality_score.py src/retrieval/query_runner.py
    uv run python .claude/scripts/quality_score.py src/ --json
    uv run python .claude/scripts/quality_score.py src/ --skip-tests
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# Scoring weights (from quality-and-testing.instructions.md rubric)
# ---------------------------------------------------------------------------

MYPY_PENALTY = 20  # binary: any errors = -20
TEST_PENALTY = 15  # binary: any failures = -15
SEVERITY_PENALTY: dict[str, int] = {
    "E": 1,  # ruff errors (style/minor)
    "W": 1,  # ruff warnings
    "I": 1,  # import ordering
    "D": 2,  # docstring violations
    "UP": 2,  # pyupgrade
    "G": 3,  # logging format (f-strings)
    "B": 5,  # bugbear (bugs)
    "S": 5,  # security (bandit)
}
DEFAULT_PENALTY = 2  # for rule codes not in map above


@dataclass(frozen=True)
class Measurement:
    """One tool measurement and whether its output was trustworthy."""

    status: str
    detail: str
    count: int = 0
    violations: list[dict] | None = None


MEASUREMENT_PASS = "PASS"
MEASUREMENT_FAIL = "FAIL"
MEASUREMENT_UNVERIFIED = "UNVERIFIED"


def _run(args: list[str], cwd: str = ".") -> tuple[int, str, str]:
    result = subprocess.run(args, capture_output=True, text=True, cwd=cwd, timeout=180)
    return result.returncode, result.stdout, result.stderr


def _git(args: list[str], cwd: Path) -> str:
    rc, stdout, _ = _run(["git", *args], cwd=str(cwd))
    if rc != 0:
        return ""
    return stdout.strip()


def _content_hash(base: str, cwd: Path) -> str:
    """A content signature of the branch's changes relative to `base`, computed
    as `git hash-object` of the raw `git diff <base>` output. It is stable across
    amend/rebase/editor-touch that preserve content (unlike an mtime check) and
    changes only when the diff content changes. The commit gate recomputes the
    identical value to detect edits made after scoring."""
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
    # "dirty" means the working tree has unstaged changes to tracked files, i.e.
    # the tree does not match the index. Staged changes destined for the commit
    # are expected and do NOT count as dirty, so the commit gate can require a
    # fully-staged tree (dirty == false) without blocking every commit. This
    # also catches edits made after the score was generated.
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


def _targets(target: str | list[str]) -> list[str]:
    """Normalize one or more measurement targets."""
    return [target] if isinstance(target, str) else target


def measure_ruff(target: str | list[str], cwd: str = ".") -> Measurement:
    """Measure Ruff without treating failed measurement as a clean result."""
    try:
        rc, stdout, stderr = _run(
            ["uv", "run", "ruff", "check", *_targets(target), "--output-format=json"],
            cwd=cwd,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return Measurement(MEASUREMENT_UNVERIFIED, f"Ruff did not run: {error}")
    if rc not in {0, 1}:
        return Measurement(
            MEASUREMENT_UNVERIFIED,
            f"Ruff exited abnormally ({rc}): {(stderr or stdout).strip()}",
        )
    if not stdout.strip():
        return Measurement(MEASUREMENT_UNVERIFIED, "Ruff produced no JSON output")
    try:
        violations = json.loads(stdout)
    except json.JSONDecodeError as error:
        return Measurement(
            MEASUREMENT_UNVERIFIED, f"Ruff produced invalid JSON: {error}"
        )
    if not isinstance(violations, list) or not all(
        isinstance(item, dict) for item in violations
    ):
        return Measurement(MEASUREMENT_UNVERIFIED, "Ruff JSON was not a violation list")
    if rc == 0 and violations:
        return Measurement(
            MEASUREMENT_UNVERIFIED,
            "Ruff reported violations with a successful exit status",
        )
    if rc == 1 and not violations:
        return Measurement(
            MEASUREMENT_UNVERIFIED,
            "Ruff failed without reporting any violations",
        )
    return Measurement(
        MEASUREMENT_PASS if rc == 0 else MEASUREMENT_FAIL,
        "Ruff completed",
        len(violations),
        violations,
    )


def run_ruff(target: str) -> tuple[list[dict], int]:
    """Return legacy Ruff fields while fencing failed measurement upstream."""
    measurement = measure_ruff(target)
    return measurement.violations or [], measurement.count


def measure_mypy(target: str | list[str], cwd: str = ".") -> Measurement:
    """Measure mypy while distinguishing type failures from tool failures."""
    try:
        rc, stdout, stderr = _run(
            [
                "uv",
                "run",
                "mypy",
                *_targets(target),
                "--ignore-missing-imports",
                "--explicit-package-bases",
            ],
            cwd=cwd,
        )
    except (OSError, subprocess.SubprocessError) as error:
        return Measurement(MEASUREMENT_UNVERIFIED, f"mypy did not run: {error}")
    output = stdout + stderr
    errors = sum(1 for line in output.splitlines() if ": error:" in line)
    if rc == 0:
        if errors:
            return Measurement(
                MEASUREMENT_UNVERIFIED,
                "mypy reported errors with a successful exit status",
            )
        return Measurement(MEASUREMENT_PASS, "mypy completed", errors)
    if rc == 1 and errors:
        return Measurement(MEASUREMENT_FAIL, "mypy reported type errors", errors)
    return Measurement(
        MEASUREMENT_UNVERIFIED,
        f"mypy exited abnormally ({rc}): {output.strip() or 'no output'}",
    )


def run_mypy(target: str) -> tuple[int, str]:
    """Return legacy mypy fields while fencing failed measurement upstream."""
    measurement = measure_mypy(target)
    return measurement.count, measurement.detail


def measure_pytest(cwd: str = ".") -> Measurement:
    """Measure pytest, separating test failures from infrastructure failures."""
    try:
        rc, stdout, stderr = _run(
            ["uv", "run", "pytest", "tests/", "-q", "--tb=no"], cwd=cwd
        )
    except (OSError, subprocess.SubprocessError) as error:
        return Measurement(MEASUREMENT_UNVERIFIED, f"pytest did not run: {error}")
    if rc == 0:
        return Measurement(MEASUREMENT_PASS, "pytest completed")
    if rc == 1:
        return Measurement(MEASUREMENT_FAIL, "pytest reported test failures")
    return Measurement(
        MEASUREMENT_UNVERIFIED,
        f"pytest infrastructure exit ({rc}): {(stderr or stdout).strip() or 'no output'}",
    )


def run_pytest() -> tuple[bool, str]:
    """Return legacy pytest fields while fencing failed measurement upstream."""
    measurement = measure_pytest()
    return measurement.status == MEASUREMENT_PASS, measurement.detail


def classify_ruff_violation(code: str) -> int:
    for prefix, penalty in SEVERITY_PENALTY.items():
        if code.startswith(prefix):
            return penalty
    return DEFAULT_PENALTY


def compute_score(
    ruff_violations: list[dict],
    mypy_errors: int,
    tests_passed: bool,
) -> tuple[int, list[str]]:
    score = 100
    deductions: list[str] = []

    if mypy_errors > 0:
        score -= MYPY_PENALTY
        deductions.append(f"mypy: {mypy_errors} error(s)  [-{MYPY_PENALTY}]")

    if not tests_passed:
        score -= TEST_PENALTY
        deductions.append(f"pytest: test failures  [-{TEST_PENALTY}]")

    by_code: dict[str, int] = {}
    for v in ruff_violations:
        code = v.get("code", "?")
        by_code[code] = by_code.get(code, 0) + 1

    ruff_total_deduction = 0
    for code, count in sorted(by_code.items()):
        penalty = classify_ruff_violation(code)
        total = penalty * count
        ruff_total_deduction += total
        deductions.append(f"ruff {code}: {count} violation(s)  [-{total}]")

    score -= ruff_total_deduction
    return max(0, score), deductions


def gate_label(score: int) -> str:
    if score >= 95:
        return "EXCELLENCE"
    if score >= 90:
        return "PR-READY"
    return "BLOCKED"


def main() -> None:
    parser = argparse.ArgumentParser(description="Quality scorer for Python code.")
    parser.add_argument("target", help="File or directory to score.")
    parser.add_argument("--json", action="store_true", help="Output as JSON.")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest.")
    parser.add_argument("--out", type=Path, help="Write the JSON result to this path.")
    parser.add_argument("--phase", default="", help="Current small-plan phase slug.")
    parser.add_argument(
        "--base-ref", default="dev", help="Base ref used for branch metadata."
    )
    args = parser.parse_args()

    target_path = Path(args.target).resolve()
    target = str(target_path)
    ruff = measure_ruff(target)
    mypy = measure_mypy(target)
    ruff_violations = ruff.violations or []
    ruff_count = ruff.count
    mypy_errors = mypy.count
    mypy_summary = mypy.detail

    if args.skip_tests:
        # Skipping tests is not the same as passing them. Record it explicitly
        # and treat tests as not-passed so the score and the commit gate both
        # reflect that the test surface was not verified.
        tests_passed, pytest_summary, tests_skipped = False, "skipped", True
    else:
        pytest = measure_pytest()
        tests_passed, pytest_summary = (
            pytest.status == MEASUREMENT_PASS,
            pytest.detail,
        )
        tests_skipped = False

    score, deductions = compute_score(ruff_violations, mypy_errors, tests_passed)
    measurement_status = {
        "ruff": ruff.status,
        "mypy": mypy.status,
        "pytest": "UNVERIFIED" if args.skip_tests else pytest.status,
    }
    measurement_failures = [
        f"{name}: {status}"
        for name, status in measurement_status.items()
        if status == MEASUREMENT_UNVERIFIED
    ]
    if measurement_failures:
        # A score is meaningful only when all required tools were measured. Keep
        # legacy count fields, but never publish a clean-looking gate result
        # after a missing executable, parser error, or abnormal tool exit.
        score = 0
        deductions.extend(
            f"measurement: {failure}  [-100]" for failure in measurement_failures
        )
    gate = gate_label(score)

    result = {
        "score": score,
        "gate": gate,
        "target": target,
        "ruff_violations": ruff_count,
        "mypy_errors": mypy_errors,
        "tests_passed": tests_passed,
        "tests_skipped": tests_skipped,
        "pytest_summary": pytest_summary,
        "mypy_summary": mypy_summary,
        "measurement_status": measurement_status,
        "measurement_failures": measurement_failures,
        "deductions": deductions,
        **git_metadata(target_path, args.phase, args.base_ref),
    }

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(result, indent=2))
        sys.exit(0)

    print(f"\n{'=' * 60}")
    print(f"  Quality Score: {score}/100  [{gate}]")
    print(f"  Target: {target}")
    print(f"{'=' * 60}")
    print(f"\n  ruff:   {ruff_count} violations")
    print(f"  mypy:   {mypy_errors} errors  ({mypy_summary})")
    print(f"  pytest: {'PASS' if tests_passed else 'FAIL'}  ({pytest_summary})")

    if deductions:
        print("\n  Deductions:")
        for d in deductions:
            print(f"    - {d}")
    else:
        print("\n  No deductions — perfect score!")

    if args.out:
        print(f"\n  Report: {args.out}")

    print(f"\n  Gate: {gate} {'OK' if score >= 90 else 'BLOCKED'}")
    if score < 90:
        print("  BLOCKED: resolve deductions above before committing.")
    print()

    sys.exit(0)


if __name__ == "__main__":
    main()
