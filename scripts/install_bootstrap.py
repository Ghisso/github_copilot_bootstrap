#!/usr/bin/env python3
"""Install the generated multi-agent bootstrap into a consumer repository."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import stat
import subprocess
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from runtime_ownership import (
    COPILOT_SURFACE_PATHS,
    RESTORABLE_ROOT_PATHS,
    active_ignore_patterns,
    bootstrap_root_paths,
    install_mode_from_manifest,
    is_consumer_state_path,
    is_root_adapter_path,
    restore_manifest,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT / "dist" / "multi-agent"
IGNORE_BLOCK_START = "# BEGIN multi-agent bootstrap generated/private AI content"
IGNORE_BLOCK_END = "# END multi-agent bootstrap generated/private AI content"
LEGACY_ANTIGRAVITY_KEY = "BOOTSTRAP_ANTIGRAVITY_PATH"
LEGACY_ANTIGRAVITY_ALLOWLIST = Path(".claude/antigravity-ownership.env")


# GitHub Copilot cloud agents read the agent/hook/instruction surface only from
# the default branch, so it must be committed to work in the cloud. By default
# these paths are gitignored (local-IDE Copilot only); --commit-copilot-surface
# omits them from the ignore block so they are trackable like `.devcontainer/`.
# D5: root-level adapter files that live outside .claude/ in a consumer, so
# state-sync.sh's checkout of .claude/ alone does not carry them. Mirrored
# into .claude/bootstrap-root/ (tracked, git-backed) and restored back out to
# these same relative paths by restore-root-adapters.sh on a fresh machine.
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target_repo", type=Path, help="Consumer repository root.")
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help="Generated bootstrap source directory.",
    )
    parser.add_argument(
        "--state-remote",
        default=None,
        help="Git remote URL for the nested .claude/ AI-state repo (env: AI_STATE_REMOTE). "
        "Defaults to this repo's own 'origin' URL when unset.",
    )
    parser.add_argument(
        "--commit-copilot-surface",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Keep the GitHub Copilot cloud surface (.github/agents, .github/hooks, "
        ".github/instructions, .github/copilot-instructions.md) out of the ignore block "
        "so it can be committed. Omitting the option retains an existing consumer's "
        "mode and defaults to local-IDE-only on a fresh install.",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Refresh and commit AI state locally without contacting its configured remote.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned actions without writing files.",
    )
    parser.add_argument(
        "--allow-self",
        action="store_true",
        help="Permit the bootstrap repository to refresh its own dogfood overlay, "
        "where the generated source lives inside the target. Every other "
        "overlapping-root case stays rejected.",
    )
    return parser.parse_args()


def info(message: str) -> None:
    print(f"install-bootstrap: {message}")


def warn(message: str) -> None:
    print(f"WARNING install-bootstrap: {message}", file=sys.stderr)


def nested_git(target: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(target / ".claude"), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def require_nested_head(target: Path, action: str) -> None:
    """Abort when a fail-open state-sync call did not create durable state."""
    head = nested_git(target, "rev-parse", "--verify", "HEAD")
    if head.returncode != 0:
        raise SystemExit(
            f"{action} did not create a nested AI-state commit: {head.stderr.strip()}"
        )


def require_clean_nested_state(target: Path, action: str) -> None:
    """Abort when an installer operation leaves nested state uncommitted."""
    require_nested_head(target, action)
    status = nested_git(target, "status", "--porcelain")
    if status.returncode != 0 or status.stdout.strip():
        raise SystemExit(
            f"{action} left nested AI state uncommitted: {status.stderr.strip()}"
        )


def strip_quarantine(path: Path) -> None:
    """Copied files can carry macOS's com.apple.quarantine xattr (shutil.copy2/
    copytree preserve xattrs from the source tree). Left in place, that flag
    makes git refuse to exec the installed hook scripts (EPERM)."""
    if sys.platform != "darwin":
        return
    subprocess.run(["xattr", "-rc", str(path)], check=False, capture_output=True)


def _agents_tree(
    root: Path, relative_root: str
) -> tuple[dict[str, bytes | None], tuple[str, ...]]:
    """Return a safe relative `.agents` tree or paths that cannot be owned."""
    if not (root.exists() or root.is_symlink()):
        return {}, ()
    if root.is_symlink() or not root.is_dir():
        return {}, (relative_root,)

    entries: dict[str, bytes | None] = {}
    invalid: list[str] = []
    for directory, names, files in os.walk(root, topdown=True, followlinks=False):
        directory_path = Path(directory)
        for name in sorted(names):
            path = directory_path / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink() or not path.is_dir():
                invalid.append(f"{relative_root}/{relative}")
                names.remove(name)
                continue
            entries[relative] = None
        for name in sorted(files):
            path = directory_path / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink() or not path.is_file():
                invalid.append(f"{relative_root}/{relative}")
                continue
            entries[relative] = path.read_bytes()
    return entries, tuple(sorted(invalid))


def _agents_conflicts(
    actual: dict[str, bytes | None],
    expected: dict[str, bytes | None],
    relative_root: str,
) -> tuple[str, ...]:
    missing = object()
    return tuple(
        f"{relative_root}/{path}"
        for path in sorted(set(actual) | set(expected))
        if actual.get(path, missing) != expected.get(path, missing)
    )


def _is_legacy_agents_path(path: str) -> bool:
    pure_path = PurePosixPath(path)
    if (
        pure_path.parts[:1] != (".agents",)
        or pure_path.is_absolute()
        or "." in pure_path.parts
        or ".." in pure_path.parts
        or path.endswith("/")
        or "//" in path
    ):
        return False
    return (
        path in {".agents/mcp_config.json", ".agents/hooks.json"}
        or (
            len(pure_path.parts) == 4
            and pure_path.parts[1] == "agents"
            and pure_path.parts[3] == "agent.md"
        )
        or (len(pure_path.parts) >= 3 and pure_path.parts[1] == "skills")
    )


def _legacy_allowlist_records(text: str) -> tuple[str, ...] | None:
    """Read old file-level ownership records without widening their shape."""
    paths: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(f"{LEGACY_ANTIGRAVITY_KEY}="):
            path = line.removeprefix(f"{LEGACY_ANTIGRAVITY_KEY}=")
            if not _is_legacy_agents_path(path) or path in paths:
                return None
            paths.append(path)
        else:
            return None
    return tuple(sorted(paths)) if paths else None


def _legacy_manifest_records(text: str) -> tuple[bool, tuple[str, ...]] | None:
    """Validate the complete retired root manifest before migration reads it."""
    mode: bool | None = None
    root_paths: list[str] = []
    agents_paths: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("BOOTSTRAP_COMMIT_COPILOT_SURFACE="):
            value = line.removeprefix("BOOTSTRAP_COMMIT_COPILOT_SURFACE=")
            if mode is not None or value not in {"0", "1"}:
                return None
            mode = value == "1"
        elif line.startswith("BOOTSTRAP_ROOT_PATH="):
            path = line.removeprefix("BOOTSTRAP_ROOT_PATH=")
            if path in root_paths:
                return None
            root_paths.append(path)
        elif line.startswith(f"{LEGACY_ANTIGRAVITY_KEY}="):
            path = line.removeprefix(f"{LEGACY_ANTIGRAVITY_KEY}=")
            if not _is_legacy_agents_path(path) or path in agents_paths:
                return None
            agents_paths.append(path)
        else:
            return None
    if mode is None:
        return None
    expected_roots = set(bootstrap_root_paths(mode)) - {".agents"}
    if set(root_paths) != expected_roots:
        return None
    return mode, tuple(sorted(agents_paths))


def _regular_text(path: Path) -> str | None:
    """Read one evidence file only when it is a regular, non-symlink file."""
    if path.is_symlink() or not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _current_install_mode(target: Path) -> bool | None:
    """Return a validated current root-manifest mode, never trusting legacy data."""
    text = _regular_text(target / ".claude" / "bootstrap-ownership.env")
    return install_mode_from_manifest(text) if text is not None else None


def _legacy_agents_evidence(target: Path) -> tuple[str, ...] | None:
    """Return matching old allowlist records, never widening their ownership."""
    allowlist = target / ".claude" / "antigravity-ownership.env"
    manifest = target / ".claude" / "bootstrap-ownership.env"
    allowlist_text = _regular_text(allowlist)
    manifest_text = _regular_text(manifest)
    if allowlist_text is None or manifest_text is None:
        return None
    allowed = _legacy_allowlist_records(allowlist_text)
    manifest_records = _legacy_manifest_records(manifest_text)
    if allowed is None or manifest_records is None:
        return None
    _mode, recorded = manifest_records
    if allowed != recorded:
        return None
    return allowed


def _has_legacy_agents_evidence(target: Path) -> bool:
    """Return whether old per-file ownership records remain to be migrated."""
    allowlist = target / ".claude" / "antigravity-ownership.env"
    manifest = target / ".claude" / "bootstrap-ownership.env"
    if allowlist.exists() or allowlist.is_symlink():
        return True
    if not manifest.is_file():
        return False
    try:
        return LEGACY_ANTIGRAVITY_KEY in manifest.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return True


def _legacy_agents_tree_matches(
    tree: dict[str, bytes | None],
    legacy_paths: tuple[str, ...],
    source_tree: dict[str, bytes | None],
) -> bool:
    """Return whether a tree exactly matches the retired generated-file record."""
    entries = {path.removeprefix(".agents/") for path in legacy_paths}
    directories = {
        "/".join(path.split("/")[:index])
        for path in entries
        for index in range(1, len(path.split("/")))
    }
    return set(tree) == entries | directories and all(
        tree.get(path) == source_tree[path] for path in entries & set(source_tree)
    )


def validate_agents_takeover(source: Path, target: Path) -> None:
    """Fail before writes unless an existing `.agents` tree is proven generated."""
    source_tree, source_invalid = _agents_tree(source / ".agents", ".agents")
    if source_invalid:
        raise SystemExit(
            "Generated .agents source contains unsafe entries: "
            + ", ".join(source_invalid)
        )
    agents_root = target / ".agents"
    mirror_root = target / ".claude" / "bootstrap-root" / ".agents"
    has_agents = agents_root.exists() or agents_root.is_symlink()
    has_mirror = mirror_root.exists() or mirror_root.is_symlink()
    actual_tree, actual_invalid = _agents_tree(agents_root, ".agents")
    mirror_tree, mirror_invalid = _agents_tree(
        mirror_root, ".claude/bootstrap-root/.agents"
    )
    legacy_paths = _legacy_agents_evidence(target)
    current_mode = _current_install_mode(target)
    conflicts: list[str] = []
    evidence_paths = (
        target / ".claude" / "antigravity-ownership.env",
        target / ".claude" / "bootstrap-ownership.env",
    )
    for path in evidence_paths:
        if (path.exists() or path.is_symlink()) and _regular_text(path) is None:
            conflicts.append(str(path.relative_to(target)))
    if _has_legacy_agents_evidence(target) and legacy_paths is None:
        conflicts.extend(
            str(path.relative_to(target))
            for path in evidence_paths
            if path.exists() or path.is_symlink()
        )
    conflicts.extend(actual_invalid)
    conflicts.extend(mirror_invalid)
    if has_mirror and not mirror_invalid:
        if has_agents:
            if mirror_tree != actual_tree:
                conflicts.extend(
                    _agents_conflicts(
                        mirror_tree, actual_tree, ".claude/bootstrap-root/.agents"
                    )
                )
        elif current_mode is None and not (
            legacy_paths is not None
            and _legacy_agents_tree_matches(mirror_tree, legacy_paths, source_tree)
        ):
            conflicts.extend(
                _agents_conflicts(
                    mirror_tree, source_tree, ".claude/bootstrap-root/.agents"
                )
            )
            if mirror_tree == source_tree:
                conflicts.append(".claude/bootstrap-root/.agents")
    if conflicts:
        raise SystemExit(
            "Refusing .agents takeover; move or back up the listed content, remove it "
            "only if intended, then rerun: " + ", ".join(sorted(set(conflicts)))
        )
    if has_agents and actual_tree == source_tree:
        return
    if has_mirror and not has_agents:
        if current_mode is not None or (
            legacy_paths is not None
            and _legacy_agents_tree_matches(mirror_tree, legacy_paths, source_tree)
        ):
            return
    if has_mirror and has_agents and current_mode is not None:
        return

    if not has_agents:
        return

    if legacy_paths is not None and _legacy_agents_tree_matches(
        actual_tree, legacy_paths, source_tree
    ):
        return
    final_conflicts = _agents_conflicts(actual_tree, source_tree, ".agents")
    raise SystemExit(
        "Refusing .agents takeover; move or back up the listed content, remove it "
        "only if intended, then rerun: " + ", ".join(final_conflicts)
    )


def copy_generated_tree(
    source: Path,
    target: Path,
    dry_run: bool,
    commit_copilot_surface: bool = False,
    previously_committed_copilot_surface: bool = False,
) -> None:
    if not source.is_dir():
        raise SystemExit(f"Generated source does not exist: {source}")
    info(f"copy {source} -> {target}")
    if dry_run:
        return
    target.mkdir(parents=True, exist_ok=True)

    def is_tracked(relative_path: Path) -> bool:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(target),
                "ls-files",
                "--error-unmatch",
                "--",
                relative_path.as_posix(),
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        return relative_path.as_posix() in result.stdout.splitlines()

    def should_preserve(relative_path: Path) -> bool:
        if not is_root_adapter_path(relative_path):
            return False
        is_copilot_surface = any(
            relative_path == Path(path) or Path(path) in relative_path.parents
            for path in COPILOT_SURFACE_PATHS
        )
        if is_copilot_surface and (
            commit_copilot_surface or previously_committed_copilot_surface
        ):
            return False
        return is_tracked(relative_path)

    def owned_files() -> set[Path]:
        owned: set[Path] = set()
        claude_root = target / ".claude"
        if claude_root.is_dir():
            for directory, names, files in os.walk(claude_root, topdown=True):
                relative_directory = Path(directory).relative_to(claude_root)
                names[:] = [
                    name
                    for name in names
                    if not (relative_directory == Path(".") and name == ".git")
                    and not is_consumer_state_path(relative_directory / name)
                    and not (
                        relative_directory == Path(".") and name == "bootstrap-root"
                    )
                ]
                for name in files:
                    relative = relative_directory / name
                    if not (
                        relative_directory == Path(".") and name == ".git"
                    ) and not is_consumer_state_path(relative):
                        owned.add(Path(".claude") / relative)
        for adapter in RESTORABLE_ROOT_PATHS:
            adapter_path = target / adapter
            if adapter_path.is_file() or adapter_path.is_symlink():
                owned.add(Path(adapter))
            elif adapter_path.is_dir():
                owned.update(
                    path.relative_to(target)
                    for path in adapter_path.rglob("*")
                    if path.is_file() or path.is_symlink()
                )
        return owned

    for relative_path in sorted(owned_files()):
        if (
            relative_path != LEGACY_ANTIGRAVITY_ALLOWLIST
            and (source / relative_path).is_file()
        ) or should_preserve(relative_path):
            continue
        destination = target / relative_path
        if destination.is_dir() and not destination.is_symlink():
            warn(
                "preserve directory that replaced obsolete generated adapter: "
                f"{relative_path.as_posix()}"
            )
            continue
        info(f"remove obsolete generated file {relative_path.as_posix()}")
        destination.unlink()
        parent = destination.parent
        while parent != target:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent

    def copy_ignore(directory: str, names: list[str]) -> set[str]:
        relative_directory = Path(directory).relative_to(source)
        ignored: set[str] = set()
        for name in names:
            relative_path = relative_directory / name
            destination_path = target / relative_path
            if relative_path == LEGACY_ANTIGRAVITY_ALLOWLIST:
                ignored.add(name)
                continue
            claude_relative = (
                relative_path.relative_to(".claude")
                if relative_path.parts and relative_path.parts[0] == ".claude"
                else None
            )
            if claude_relative is not None and is_consumer_state_path(claude_relative):
                if destination_path.exists() or destination_path.is_symlink():
                    ignored.add(name)
                    info(f"preserve consumer state {relative_path.as_posix()}")
            elif should_preserve(relative_path):
                ignored.add(name)
                info(f"preserve tracked authoring adapter {relative_path.as_posix()}")
        return ignored

    for child in sorted(source.iterdir()):
        destination = target / child.name
        if should_preserve(Path(child.name)):
            info(f"preserve tracked authoring adapter {child.name}")
            continue
        if child.is_dir():
            shutil.copytree(
                child,
                destination,
                dirs_exist_ok=True,
                ignore=copy_ignore,
            )
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(child, destination)
        strip_quarantine(destination)


def _legacy_install_mode(text: str) -> bool | None:
    """Read the old root manifest only while retaining the Copilot mode."""
    records = _legacy_manifest_records(text)
    return records[0] if records is not None else None


def persisted_install_mode(target: Path) -> bool | None:
    """Return the consumer's validated persisted Copilot-surface mode."""
    manifest = target / ".claude" / "bootstrap-ownership.env"
    if not manifest.is_file():
        return None
    try:
        text = manifest.read_text(encoding="utf-8")
        mode = install_mode_from_manifest(text)
        return mode if mode is not None else _legacy_install_mode(text)
    except OSError:
        return None


def validate_install_roots(
    source: Path, target: Path, allow_self: bool = False
) -> None:
    """Reject overlapping source and target trees before installer side effects.

    ``--allow-self`` permits exactly one overlap: the bootstrap repository
    refreshing its own dogfood overlay, where the generated source lives inside
    the target. That case is safe because removal only walks ``target/.claude``
    and ``RESTORABLE_ROOT_PATHS``, so the source under ``dist/`` is never a
    removal candidate. Installing a tree over itself, or into a directory under
    the source, stays rejected either way.
    """
    if allow_self and source != target and source.is_relative_to(target):
        if target != REPO_ROOT:
            raise SystemExit(
                "--allow-self only refreshes the bootstrap repository's own overlay: "
                f"target={target}; bootstrap={REPO_ROOT}"
            )
        return
    if (
        source == target
        or source.is_relative_to(target)
        or target.is_relative_to(source)
    ):
        hint = (
            ""
            if allow_self
            else " Pass --allow-self to refresh the bootstrap repository's own overlay."
        )
        raise SystemExit(
            "Generated source and target repository must be separate, non-overlapping directories: "
            f"source={source}; target={target}.{hint}"
        )


def ignore_block(
    commit_copilot_surface: bool = False,
) -> str:
    lines = [
        IGNORE_BLOCK_START,
        *active_ignore_patterns(commit_copilot_surface),
        IGNORE_BLOCK_END,
    ]
    return "\n".join(lines) + "\n"


PROJECT_NAME_PLACEHOLDER = "**Project:** [TODO: project name and one-liner description]"
# Every generated surface that states the project's identity. Root guidance is
# installed alongside workspace instructions and must carry the same facts.
PROJECT_NAME_FILES = (
    Path("CLAUDE.md"),
    Path("AGENTS.md"),
    Path(".claude") / "instructions" / "workspace.instructions.md",
    Path(".claude") / "instructions" / "workspace.md",
)


def substitute_project_name(target: Path, dry_run: bool) -> None:
    """Fill generated project-name placeholders with the target directory name."""
    paths = [target / relative for relative in PROJECT_NAME_FILES]
    if not any(
        path.is_file() and PROJECT_NAME_PLACEHOLDER in path.read_text(encoding="utf-8")
        for path in paths
    ):
        return
    info(f"substitute generated project name -> {target.name}")
    if dry_run:
        return
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if PROJECT_NAME_PLACEHOLDER in text:
            path.write_text(
                text.replace(PROJECT_NAME_PLACEHOLDER, f"**Project:** {target.name}"),
                encoding="utf-8",
            )


# The bootstrap's declared Python baseline. Kept in generated guidance verbatim
# when the target declares nothing more specific. Must stay in sync with the
# `**Python:**`/`**Stack:**` lines in shared/policies/workspace.instructions.md.
PYTHON_BASELINE = "3.12+"
# Every generated surface that carries the two project-fact lines. workspace.md
# and workspace.instructions.md are near-duplicates and the root adapters embed
# the same section, so all four must be reconciled together.
PYTHON_FACT_FILES = (
    Path("CLAUDE.md"),
    Path("AGENTS.md"),
    Path(".claude") / "instructions" / "workspace.instructions.md",
    Path(".claude") / "instructions" / "workspace.md",
)


def _python_display(requires_python: str | None) -> str | None:
    """Turn a `requires-python` spec into a docs display string like `3.13+`.

    Only the common `>=X.Y` form is normalized; a compound or unusual spec
    (`>=3.11,<3.14`, `~=3.12`, `==3.12.*`) returns None so the baseline is kept
    rather than guessed."""
    if not requires_python:
        return None
    spec = requires_python.strip()
    if not spec.startswith(">="):
        return None
    version = spec[2:].strip()
    if not version or any(ch in version for ch in ",<>=!~* "):
        return None
    return f"{version}+"


def _target_requires_python(target: Path) -> str | None:
    """Read `[project].requires-python` from the target's pyproject.toml, or
    None when it is absent/unreadable (a fresh, pre-`uv init` target)."""
    pyproject = target / "pyproject.toml"
    if not pyproject.is_file():
        return None
    try:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    project = data.get("project")
    if not isinstance(project, dict):
        return None
    value = project.get("requires-python")
    return value if isinstance(value, str) else None


def substitute_python_version(target: Path, dry_run: bool) -> None:
    """Reconcile the documented Python prerequisite with the target's declared
    `requires-python` across every generated surface that states it. A fresh
    target with no parseable `requires-python` keeps the bootstrap baseline."""
    display = _python_display(_target_requires_python(target))
    if display is None or display == PYTHON_BASELINE:
        return
    replacements = (
        (f"**Python:** {PYTHON_BASELINE} |", f"**Python:** {display} |"),
        (
            f"**Stack:** Python {PYTHON_BASELINE} with uv",
            f"**Stack:** Python {display} with uv",
        ),
    )
    info(f"substitute documented python version -> {display}")
    if dry_run:
        return
    for relative in PYTHON_FACT_FILES:
        path = target / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        updated = text
        for old, new in replacements:
            updated = updated.replace(old, new)
        if updated != text:
            path.write_text(updated, encoding="utf-8")


def merge_gitignore(
    target: Path,
    dry_run: bool,
    commit_copilot_surface: bool = False,
) -> None:
    gitignore = target / ".gitignore"
    block = ignore_block(commit_copilot_surface)
    current = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if IGNORE_BLOCK_START in current and IGNORE_BLOCK_END in current:
        # Refresh an existing block in place so pattern changes (e.g. a new
        # ignore entry) reach consumers that already have the block. Text
        # outside the START..END markers is left untouched.
        start = current.index(IGNORE_BLOCK_START)
        end = current.index(IGNORE_BLOCK_END) + len(IGNORE_BLOCK_END)
        refreshed = current[:start] + block.rstrip("\n") + current[end:]
        if refreshed == current:
            info(".gitignore multi-agent ignore block is up to date")
            return
        info(f"refresh multi-agent ignore block in {gitignore}")
        if dry_run:
            return
        gitignore.write_text(refreshed, encoding="utf-8")
        return

    info(f"append multi-agent ignore block to {gitignore}")
    if dry_run:
        return

    separator = "" if not current or current.endswith("\n") else "\n"
    gitignore.write_text(
        f"{current}{separator}\n{block}" if current else block, encoding="utf-8"
    )


def chmod_runtime_scripts(target: Path, dry_run: bool) -> None:
    patterns = (
        ".claude/hooks/scripts/*.sh",
        ".claude/hooks/git-hooks/*",
        ".devcontainer/*.sh",
        ".devcontainer/*.py",
    )
    for pattern in patterns:
        for path in target.glob(pattern):
            if not path.is_file():
                continue
            info(f"chmod +x {path.relative_to(target)}")
            if dry_run:
                continue
            path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def configure_git_hooks_path(target: Path, dry_run: bool) -> None:
    if not (target / ".git").exists():
        warn(f"{target} is not a git repository; skipping core.hooksPath configuration")
        return
    info("set git config core.hooksPath .claude/hooks/git-hooks")
    if dry_run:
        return
    result = subprocess.run(
        [
            "git",
            "-C",
            str(target),
            "config",
            "core.hooksPath",
            ".claude/hooks/git-hooks",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        warn(f"could not set core.hooksPath: {result.stderr.strip()}")


def update_devcontainer_state_remote(
    target: Path, state_remote: str | None, dry_run: bool
) -> None:
    """Persists a non-default --state-remote into the committed devcontainer
    config, so a fresh container clone (which has no other way to learn a
    private state-remote URL, since .claude/ itself is gitignored) picks it
    up automatically. The default (origin) needs no config at all."""
    if not state_remote:
        return
    devcontainer_path = target / ".devcontainer" / "devcontainer.json"
    if not devcontainer_path.is_file():
        warn(f"missing devcontainer config: {devcontainer_path}")
        return

    info(f"set devcontainer AI_STATE_REMOTE={state_remote}")
    if dry_run:
        return

    data = json.loads(devcontainer_path.read_text(encoding="utf-8"))
    container_env = data.setdefault("containerEnv", {})
    container_env["AI_STATE_REMOTE"] = state_remote
    devcontainer_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def populate_bootstrap_root(
    target: Path,
    dry_run: bool,
    commit_copilot_surface: bool,
) -> None:
    """D5: mirrors the root-level adapter files into .claude/bootstrap-root/
    so they are carried by the git-backed .claude/ checkout even though they
    live outside .claude/ themselves. Skips the Copilot surface when it is
    already committed to the outer repo (--commit-copilot-surface)."""
    paths = bootstrap_root_paths(commit_copilot_surface)

    destination_root = target / ".claude" / "bootstrap-root"
    info(f"populate {destination_root} from root adapters")
    if dry_run:
        return
    destination_root.mkdir(parents=True, exist_ok=True)

    active_paths = set(paths)
    for relative in RESTORABLE_ROOT_PATHS:
        if relative in active_paths:
            continue
        destination = destination_root / relative
        if not (destination.exists() or destination.is_symlink()):
            continue
        info(f"remove inactive bootstrap-root adapter {relative}")
        if destination.is_dir() and not destination.is_symlink():
            shutil.rmtree(destination)
        else:
            destination.unlink()
        parent = destination.parent
        while parent != destination_root:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent

    for relative in paths:
        source = target / relative
        if not source.exists():
            continue
        destination = destination_root / relative
        if source.is_dir():
            if destination.is_dir() and not destination.is_symlink():
                shutil.rmtree(destination)
            elif destination.exists() or destination.is_symlink():
                raise SystemExit(
                    "Unsafe bootstrap-root adapter destination: "
                    f"{destination.relative_to(target)}"
                )
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        strip_quarantine(destination)

    ownership_manifest = target / ".claude" / "bootstrap-ownership.env"
    ownership_manifest.write_text(
        restore_manifest(commit_copilot_surface),
        encoding="utf-8",
    )


def sync_state_after_install(
    target: Path,
    dry_run: bool,
    state_remote: str | None,
    had_claude_git: bool,
    had_pre_existing_content: bool,
    local_only: bool,
) -> None:
    """Commits and pushes the nested .claude/ AI-state repo (D1/D4). A
    pre-git .claude/ with real content must already have been migrated before
    generated files replace it. This function then makes the distinct
    `bootstrap: install/update <timestamp>` commit, separate from `session:`
    commits made by the Stop hook."""
    info("sync AI state via state-sync.sh")
    if dry_run:
        return

    state_sync = target / ".claude" / "hooks" / "scripts" / "state-sync.sh"
    if not state_sync.is_file():
        raise SystemExit(f"missing state-sync helper: {state_sync}")

    env = os.environ.copy()
    if state_remote:
        env["AI_STATE_REMOTE"] = state_remote
    if local_only:
        env["AI_STATE_LOCAL_ONLY"] = "1"

    # stdin=DEVNULL (F2 in plans/plan-git-state-sync.md §9): state-sync.sh
    # drains stdin for up to 2s (a hook/task contract). When invoked from this
    # installer with inherited stdin, an interactive run would block on — and
    # swallow — terminal input; the installer never reads stdin, so close it.
    subprocess.run(
        ["bash", str(state_sync), "setup"],
        check=False,
        cwd=target,
        env=env,
        stdin=subprocess.DEVNULL,
    )
    require_nested_head(target, "state-sync setup")
    if not had_claude_git and not had_pre_existing_content:
        require_clean_nested_state(target, "state-sync setup")
    # On a truly fresh install, `setup` above already committed everything
    # currently on disk as "bootstrap: init ai-state" (it always commits
    # whatever it finds when .claude/.git doesn't yet exist) — that commit
    # already satisfies D1's bootstrap:-prefixed-commit requirement, so there
    # is nothing left to stage here. On a repeat run .claude/.git already
    # existed, so `setup` was a no-op, and this run's freshly copied files
    # are real, uncommitted changes that need their own commit.
    if had_claude_git or had_pre_existing_content:
        status = subprocess.run(
            ["git", "-C", str(target / ".claude"), "status", "--porcelain"],
            text=True,
            capture_output=True,
            check=False,
        )
        if status.stdout.strip():
            subprocess.run(
                ["git", "-C", str(target / ".claude"), "add", "-A"], check=False
            )
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(target / ".claude"),
                    "commit",
                    "-q",
                    "-m",
                    f"bootstrap: update {timestamp}",
                ],
                check=False,
            )

    require_clean_nested_state(target, "bootstrap update")

    if local_only:
        status = nested_git(target, "status", "--short", "--branch")
        print("Nested AI-state status:")
        print(status.stdout.rstrip() or "(unable to read nested repository status)")
        print(f"Publish later: bash {shlex.quote(str(state_sync))} push")
        return

    push_result = subprocess.run(
        ["bash", str(state_sync), "push"],
        check=False,
        cwd=target,
        env=env,
        stdin=subprocess.DEVNULL,
    )
    if push_result.returncode != 0:
        warn(
            "state-sync push reported a non-zero exit; state committed locally, will retry on next sync."
        )


def report_codex_hook_trust(dry_run: bool) -> None:
    """Explain the explicit Codex for VS Code project-hook trust boundary."""
    action = "would install or update" if dry_run else "installed or updated"
    info(
        f"{action} .codex/hooks.json; Codex for VS Code project-hook trust "
        "is bound to its content/hash."
    )
    print("An actual install or update can require review/retrust.")
    print(
        "After an actual install or update, reopen/reload this repository in Codex for VS Code, "
        "then review and approve the project hooks when prompted before relying on the new lifecycle hooks."
    )
    print(
        "This installer does not approve project hooks or change user trust settings."
    )


def migrate_pre_existing_state(
    target: Path,
    source: Path,
    dry_run: bool,
    state_remote: str | None,
    had_pre_existing_content: bool,
    local_only: bool,
) -> None:
    """Commit legacy state before generated files replace it."""
    if not had_pre_existing_content:
        return

    state_sync = source / ".claude" / "hooks" / "scripts" / "state-sync.sh"
    if not state_sync.is_file():
        raise SystemExit(f"missing source state-sync helper: {state_sync}")

    info("migrate pre-existing AI state via state-sync.sh")
    if dry_run:
        return

    env = os.environ.copy()
    env["AI_STATE_REPO_ROOT"] = str(target)
    if state_remote:
        env["AI_STATE_REMOTE"] = state_remote
    if local_only:
        env["AI_STATE_LOCAL_ONLY"] = "1"
    subprocess.run(
        ["bash", str(state_sync), "migrate-from-hf"],
        check=False,
        cwd=target,
        env=env,
        stdin=subprocess.DEVNULL,
    )
    require_clean_nested_state(target, "legacy state migration")
    history = nested_git(target, "log", "--format=%s")
    if (
        history.returncode != 0
        or "migrate: import pre-git state" not in history.stdout.splitlines()
    ):
        raise SystemExit(
            "legacy state migration did not create a migrate: import pre-git state commit"
        )


def tracked_generated_paths(target: Path, patterns: tuple[str, ...]) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(target), "ls-files", "--", *patterns],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def warn_tracked_paths(target: Path, patterns: tuple[str, ...]) -> None:
    tracked = tracked_generated_paths(target, patterns)
    if not tracked:
        return
    unique_roots = sorted(
        {
            pattern.rstrip("/")
            for pattern in patterns
            if any(
                path == pattern.rstrip("/")
                or path.startswith(pattern.rstrip("/") + "/")
                for path in tracked
            )
        }
    )
    warn("some generated AI paths are already tracked by git.")
    print(
        "Run this in the consumer repo if you want to untrack them while keeping local files:"
    )
    print(f"git rm --cached -r -- {' '.join(unique_roots)}")


def main() -> int:
    args = parse_args()
    state_remote = args.state_remote or os.environ.get("AI_STATE_REMOTE")
    target = args.target_repo.expanduser().resolve()
    source = args.source.expanduser().resolve()
    validate_install_roots(source, target, args.allow_self)
    validate_agents_takeover(source, target)
    persisted_mode = persisted_install_mode(target)
    commit_copilot_surface = (
        args.commit_copilot_surface
        if args.commit_copilot_surface is not None
        else persisted_mode or False
    )
    mode_source = "explicit" if args.commit_copilot_surface is not None else "retained"
    if persisted_mode is None and args.commit_copilot_surface is None:
        mode_source = "fresh default"
    info(
        "Copilot surface mode: "
        f"{'committed' if commit_copilot_surface else 'local-only'} ({mode_source})"
    )

    claude_dir = target / ".claude"
    had_claude_git = (claude_dir / ".git").exists()
    had_pre_existing_content = (
        claude_dir.is_dir() and not had_claude_git and any(claude_dir.iterdir())
    )

    migrate_pre_existing_state(
        target,
        source,
        args.dry_run,
        state_remote,
        had_pre_existing_content,
        args.local_only,
    )
    copy_generated_tree(
        source,
        target,
        args.dry_run,
        commit_copilot_surface,
        previously_committed_copilot_surface=persisted_mode is True,
    )
    substitute_project_name(target, args.dry_run)
    substitute_python_version(target, args.dry_run)
    populate_bootstrap_root(
        target,
        args.dry_run,
        commit_copilot_surface,
    )
    update_devcontainer_state_remote(target, state_remote, args.dry_run)
    merge_gitignore(target, args.dry_run, commit_copilot_surface)
    chmod_runtime_scripts(target, args.dry_run)
    configure_git_hooks_path(target, args.dry_run)
    warn_tracked_paths(
        target,
        active_ignore_patterns(commit_copilot_surface),
    )

    sync_state_after_install(
        target,
        args.dry_run,
        state_remote,
        had_claude_git,
        had_pre_existing_content,
        args.local_only,
    )

    report_codex_hook_trust(args.dry_run)
    info("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
