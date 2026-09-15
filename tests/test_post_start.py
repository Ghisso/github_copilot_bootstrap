"""Regression coverage for the devcontainer ``post-start.sh`` entrypoint.

The script runs under ``set -euo pipefail``, which makes a bare assignment
inherit the exit status of its command substitution. A ``git rev-parse`` that
fails outside a repository therefore aborts the whole script unless the
substitution is explicitly neutralised, silently skipping the directory-based
fallback that is supposed to keep container startup working.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_SRC = REPO_ROOT / "shared" / "devcontainer" / "post-start.sh"


def test_falls_back_to_script_parent_outside_a_git_repository(tmp_path: Path) -> None:
    """Outside a repository the script warns and exits 0 instead of dying."""
    workspace = tmp_path / "workspace"
    script_dir = workspace / ".devcontainer"
    script_dir.mkdir(parents=True)
    script = script_dir / "post-start.sh"
    shutil.copy(SCRIPT_SRC, script)

    # Precondition: the copy really is outside any repository, so the assertions
    # below exercise the fallback rather than an accidental real toplevel.
    toplevel = subprocess.run(
        ["git", "-C", str(script_dir), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert toplevel.returncode != 0, "tmp_path unexpectedly sits inside a git repo"

    result = subprocess.run(
        ["bash", str(script)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, (
        f"post-start.sh aborted with {result.returncode}; stderr={result.stderr!r}"
    )
    # Reaching the state-sync check proves execution continued past REPO_ROOT.
    assert "skipping AI state sync" in result.stderr
