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
from pathlib import Path


# ---------------------------------------------------------------------------
# Scoring weights (from quality-and-testing.instructions.md rubric)
# ---------------------------------------------------------------------------

MYPY_PENALTY = 20      # binary: any errors = -20
TEST_PENALTY = 15      # binary: any failures = -15
SEVERITY_PENALTY: dict[str, int] = {
    "E": 1,    # ruff errors (style/minor)
    "W": 1,    # ruff warnings
    "I": 1,    # import ordering
    "D": 2,    # docstring violations
    "UP": 2,   # pyupgrade
    "G": 3,    # logging format (f-strings)
    "B": 5,    # bugbear (bugs)
    "S": 5,    # security (bandit)
}
DEFAULT_PENALTY = 2    # for rule codes not in map above


def _run(args: list[str], cwd: str = ".") -> tuple[int, str, str]:
    result = subprocess.run(args, capture_output=True, text=True, cwd=cwd)
    return result.returncode, result.stdout, result.stderr


def run_ruff(target: str) -> tuple[list[dict], int]:
    rc, stdout, _ = _run(["uv", "run", "ruff", "check", target, "--output-format=json"])
    if not stdout.strip():
        return [], 0
    try:
        violations = json.loads(stdout)
    except json.JSONDecodeError:
        return [], 0
    return violations, len(violations)


def run_mypy(target: str) -> tuple[int, str]:
    rc, stdout, stderr = _run([
        "uv", "run", "mypy", target,
        "--ignore-missing-imports",
        "--explicit-package-bases",
    ])
    output = stdout + stderr
    errors = sum(1 for line in output.splitlines() if ": error:" in line)
    summary = next(
        (line for line in reversed(output.splitlines()) if line.strip()),
        "No output",
    )
    return errors, summary


def run_pytest() -> tuple[bool, str]:
    rc, stdout, _ = _run(["uv", "run", "pytest", "tests/", "-q", "--tb=no"])
    passed = rc == 0
    summary = next(
        (line for line in reversed(stdout.splitlines()) if line.strip()),
        "No tests run",
    )
    return passed, summary


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
    if score >= 80:
        return "COMMIT"
    return "BLOCKED"


def main() -> None:
    parser = argparse.ArgumentParser(description="Quality scorer for Python code.")
    parser.add_argument("target", help="File or directory to score.")
    parser.add_argument("--json", action="store_true", help="Output as JSON.")
    parser.add_argument("--skip-tests", action="store_true", help="Skip pytest.")
    args = parser.parse_args()

    target = str(Path(args.target).resolve())
    ruff_violations, ruff_count = run_ruff(target)
    mypy_errors, mypy_summary = run_mypy(target)

    if args.skip_tests:
        tests_passed, pytest_summary = True, "skipped"
    else:
        tests_passed, pytest_summary = run_pytest()

    score, deductions = compute_score(ruff_violations, mypy_errors, tests_passed)
    gate = gate_label(score)

    result = {
        "score": score,
        "gate": gate,
        "target": target,
        "ruff_violations": ruff_count,
        "mypy_errors": mypy_errors,
        "tests_passed": tests_passed,
        "pytest_summary": pytest_summary,
        "mypy_summary": mypy_summary,
        "deductions": deductions,
    }

    if args.json:
        print(json.dumps(result, indent=2))
        sys.exit(0)

    print(f"\n{'='*60}")
    print(f"  Quality Score: {score}/100  [{gate}]")
    print(f"  Target: {target}")
    print(f"{'='*60}")
    print(f"\n  ruff:   {ruff_count} violations")
    print(f"  mypy:   {mypy_errors} errors  ({mypy_summary})")
    print(f"  pytest: {'PASS' if tests_passed else 'FAIL'}  ({pytest_summary})")

    if deductions:
        print("\n  Deductions:")
        for d in deductions:
            print(f"    - {d}")
    else:
        print("\n  No deductions — perfect score!")

    print(f"\n  Gate: {gate} {'OK' if score >= 80 else 'BLOCKED'}")
    if score < 80:
        print("  BLOCKED: resolve deductions above before committing.")
    elif score < 90:
        print("  Commit allowed. Address deductions before PR.")
    print()

    sys.exit(0)


if __name__ == "__main__":
    main()
