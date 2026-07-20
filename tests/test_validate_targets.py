"""Integration coverage for the generated-target control-plane validator."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_validate_targets() -> None:
    """The real generated-target validator accepts the current repository."""
    result = subprocess.run(
        [sys.executable, "scripts/validate_targets.py"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS generated target is structurally valid" in result.stdout
