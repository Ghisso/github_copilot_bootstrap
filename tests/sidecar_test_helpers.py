"""Small git/file helpers shared by the sidecar test suite.

Used by ``tests/test_sidecar_install.py`` (the apply-step regressions) and
``tests/test_sidecar_update.py`` (the upgrade/reconciliation regressions) so
both build and inspect real, temporary Git repositories the same way. Every
test that uses these still runs ``git commit`` in-process through
pytest/subprocess, which the repository's own commit-gate hook does not
intercept (see ``docs/sidecar-provider-contract.md``).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from runtime_ownership import SIDECAR_MANIFEST_NAME
from sidecar_overlay import git_path


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(root), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def _commit_staged(root: Path, message: str) -> None:
    commit = _git(
        root,
        "-c",
        "user.name=sidecar-test",
        "-c",
        "user.email=sidecar-test@example.invalid",
        "commit",
        "-q",
        "-m",
        message,
    )
    assert commit.returncode == 0, commit.stderr


def _commit(root: Path, message: str, *paths: str) -> None:
    """Stage ``paths`` (or everything, on a fresh fixture with nothing else
    untracked) and commit. Never use bare ``-A`` once a sidecar file might be
    visible: that would sweep it into tracking instead of leaving it as the
    "still untracked" state a given scenario needs."""
    add = _git(root, "add", "--", *paths) if paths else _git(root, "add", "-A")
    assert add.returncode == 0, add.stderr
    _commit_staged(root, message)


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    result = _git(root, "init", "-q")
    assert result.returncode == 0, result.stderr


def _status(root: Path) -> str:
    result = _git(root, "status", "--porcelain", "--untracked-files=all")
    assert result.returncode == 0, result.stderr
    return result.stdout


def _exclude_path(root: Path) -> Path:
    return git_path(root, "info/exclude")


def _manifest_path(root: Path) -> Path:
    return git_path(root, SIDECAR_MANIFEST_NAME)


def _read_manifest(root: Path) -> dict:
    return json.loads(_manifest_path(root).read_text(encoding="utf-8"))
