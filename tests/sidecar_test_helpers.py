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


def _absolute_git_dir(root: Path) -> Path:
    """Return ``root``'s absolute Git directory, built the same way
    ``install_sidecar`` itself does (Decision 26; Phase H step 3): never
    through ``git_path()``/``--git-path``, which resolves a symlinked
    component before printing it. Reused by every test that needs the real,
    unresolved location of the manifest, staging, preserved, or exclude
    path."""
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "--absolute-git-dir"],
        text=True,
        capture_output=True,
        check=True,
    )
    return Path(result.stdout.strip())


def _exclude_path(root: Path) -> Path:
    return _absolute_git_dir(root) / "info" / "exclude"


def _manifest_path(root: Path) -> Path:
    return _absolute_git_dir(root) / SIDECAR_MANIFEST_NAME


def _read_manifest(root: Path) -> dict:
    return json.loads(_manifest_path(root).read_text(encoding="utf-8"))


def _raise_at(name: str):
    """Return a ``_fault_point`` replacement that raises only at ``name``,
    for monkeypatching ``sidecar_overlay._fault_point`` in a crash-recovery
    test."""

    def _fault_point(point: str) -> None:
        if point == name:
            raise RuntimeError(f"injected fault at {point}")

    return _fault_point


def patch_sidecar_skills(monkeypatch, skills: tuple[str, ...]) -> None:
    """Monkeypatch ``SIDECAR_SKILLS`` everywhere it was bound as a
    module-level name at import time (``runtime_ownership`` itself, and
    ``sidecar_overlay``'s own separately-imported copy), so a test can
    install a reduced or different skill profile across synthetic
    "bootstrap versions" without weakening the real exact-source
    completeness check (Decision 31). That check always reads whatever
    ``SIDECAR_SKILLS`` currently is in each module, not a value captured
    once, so patching only one module's copy would leave the other
    checking against the real, unpatched profile.
    """
    import runtime_ownership
    import sidecar_overlay

    patched = tuple(skills)
    monkeypatch.setattr(runtime_ownership, "SIDECAR_SKILLS", patched)
    monkeypatch.setattr(sidecar_overlay, "SIDECAR_SKILLS", patched)


def install_sidecar_with_profile(
    target: Path, source: Path, monkeypatch, *, dry_run: bool = False
) -> int:
    """Call ``install_sidecar`` after patching ``SIDECAR_SKILLS`` (via
    ``patch_sidecar_skills``) to exactly the skill folder names ``source``
    ships at its ``.claude/skills`` write root.

    A synthetic fixture source built for a cross-version reconciliation test
    only ever needs to be complete relative to its own declared profile, not
    the real one; reading that profile straight from the tree means every
    caller keeps its own "which skills does this version ship" knowledge in
    exactly one place -- the fixture it already built -- instead of a second,
    separately maintained list.
    """
    from sidecar_overlay import install_sidecar

    skills_root = source / ".claude" / "skills"
    skills = (
        tuple(sorted(entry.name for entry in skills_root.iterdir() if entry.is_dir()))
        if skills_root.is_dir()
        else ()
    )
    patch_sidecar_skills(monkeypatch, skills)
    return install_sidecar(target, source, dry_run=dry_run)
