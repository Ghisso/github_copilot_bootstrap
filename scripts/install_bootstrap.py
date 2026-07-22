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
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = REPO_ROOT / "dist" / "multi-agent"
IGNORE_BLOCK_START = "# BEGIN multi-agent bootstrap generated/private AI content"
IGNORE_BLOCK_END = "# END multi-agent bootstrap generated/private AI content"
IGNORE_PATTERNS = (
    ".claude/",
    ".codex/",
    ".github/agents/",
    ".github/hooks/",
    ".github/instructions/",
    ".github/copilot-instructions.md",
    ".vscode/mcp.json",
    ".mcp.json",
    ".claude/quality_reports/",
    "AGENTS.md",
    "CLAUDE.md",
    ".uv-cache/",
)
# GitHub Copilot cloud agents read the agent/hook/instruction surface only from
# the default branch, so it must be committed to work in the cloud. By default
# these paths are gitignored (local-IDE Copilot only); --commit-copilot-surface
# omits them from the ignore block so they are trackable like `.devcontainer/`.
COPILOT_SURFACE_PATTERNS = (
    ".github/agents/",
    ".github/hooks/",
    ".github/instructions/",
    ".github/copilot-instructions.md",
)
# D5: root-level adapter files that live outside .claude/ in a consumer, so
# state-sync.sh's checkout of .claude/ alone does not carry them. Mirrored
# into .claude/bootstrap-root/ (tracked, git-backed) and restored back out to
# these same relative paths by restore-root-adapters.sh on a fresh machine.
ROOT_ADAPTER_PATHS = (
    "CLAUDE.md",
    "AGENTS.md",
    ".mcp.json",
    ".codex",
    ".vscode/mcp.json",
    ".vscode/tasks.json",
)


def active_ignore_patterns(commit_copilot_surface: bool) -> tuple[str, ...]:
    if not commit_copilot_surface:
        return IGNORE_PATTERNS
    return tuple(p for p in IGNORE_PATTERNS if p not in COPILOT_SURFACE_PATTERNS)


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
        action="store_true",
        help="Keep the GitHub Copilot cloud surface (.github/agents, .github/hooks, "
        ".github/instructions, .github/copilot-instructions.md) out of the ignore block "
        "so it can be committed. Cloud Copilot agents only read these from the default "
        "branch; the default (omitting the flag) is local-IDE Copilot only.",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Refresh and commit AI state locally without contacting its configured remote.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without writing files.")
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
        raise SystemExit(f"{action} did not create a nested AI-state commit: {head.stderr.strip()}")


def require_clean_nested_state(target: Path, action: str) -> None:
    """Abort when an installer operation leaves nested state uncommitted."""
    require_nested_head(target, action)
    status = nested_git(target, "status", "--porcelain")
    if status.returncode != 0 or status.stdout.strip():
        raise SystemExit(f"{action} left nested AI state uncommitted: {status.stderr.strip()}")


def strip_quarantine(path: Path) -> None:
    """Copied files can carry macOS's com.apple.quarantine xattr (shutil.copy2/
    copytree preserve xattrs from the source tree). Left in place, that flag
    makes git refuse to exec the installed hook scripts (EPERM)."""
    if sys.platform != "darwin":
        return
    subprocess.run(["xattr", "-rc", str(path)], check=False, capture_output=True)


def copy_generated_tree(source: Path, target: Path, dry_run: bool) -> None:
    if not source.is_dir():
        raise SystemExit(f"Generated source does not exist: {source}")
    info(f"copy {source} -> {target}")
    if dry_run:
        return
    target.mkdir(parents=True, exist_ok=True)
    for child in sorted(source.iterdir()):
        destination = target / child.name
        if child.is_dir():
            memory = destination / "MEMORY.md"
            preserve_memory = child.name == ".claude" and (memory.exists() or memory.is_symlink())
            if preserve_memory:
                info("preserve consumer state .claude/MEMORY.md")
            shutil.copytree(
                child,
                destination,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("MEMORY.md") if preserve_memory else None,
            )
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(child, destination)
        strip_quarantine(destination)


def ignore_block(commit_copilot_surface: bool = False) -> str:
    lines = [IGNORE_BLOCK_START, *active_ignore_patterns(commit_copilot_surface), IGNORE_BLOCK_END]
    return "\n".join(lines) + "\n"


def substitute_project_name(target: Path, dry_run: bool) -> None:
    """Fill the workspace instructions' [TODO: project name...] placeholder with
    the target repo's directory name at install time, so every consumer ships a
    named workspace instead of the unfilled template."""
    workspace = target / ".claude" / "instructions" / "workspace.instructions.md"
    if not workspace.is_file():
        return
    text = workspace.read_text(encoding="utf-8")
    placeholder = "**Project:** [TODO: project name and one-liner description]"
    if placeholder not in text:
        return
    info(f"substitute workspace project name -> {target.name}")
    if dry_run:
        return
    workspace.write_text(text.replace(placeholder, f"**Project:** {target.name}"), encoding="utf-8")


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


def merge_gitignore(target: Path, dry_run: bool, commit_copilot_surface: bool = False) -> None:
    gitignore = target / ".gitignore"
    block = ignore_block(commit_copilot_surface)
    current = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
    if IGNORE_BLOCK_START in current and IGNORE_BLOCK_END in current:
        info(".gitignore already contains multi-agent ignore block")
        return

    info(f"append multi-agent ignore block to {gitignore}")
    if dry_run:
        return

    separator = "" if not current or current.endswith("\n") else "\n"
    gitignore.write_text(f"{current}{separator}\n{block}" if current else block, encoding="utf-8")


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
        ["git", "-C", str(target), "config", "core.hooksPath", ".claude/hooks/git-hooks"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        warn(f"could not set core.hooksPath: {result.stderr.strip()}")


def update_devcontainer_state_remote(target: Path, state_remote: str | None, dry_run: bool) -> None:
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


def populate_bootstrap_root(target: Path, dry_run: bool, commit_copilot_surface: bool) -> None:
    """D5: mirrors the root-level adapter files into .claude/bootstrap-root/
    so they are carried by the git-backed .claude/ checkout even though they
    live outside .claude/ themselves. Skips the Copilot surface when it is
    already committed to the outer repo (--commit-copilot-surface)."""
    paths: tuple[str, ...] = ROOT_ADAPTER_PATHS
    if not commit_copilot_surface:
        paths = paths + tuple(pattern.rstrip("/") for pattern in COPILOT_SURFACE_PATTERNS)

    destination_root = target / ".claude" / "bootstrap-root"
    info(f"populate {destination_root} from root adapters")
    if dry_run:
        return

    for relative in paths:
        source = target / relative
        if not source.exists():
            continue
        destination = destination_root / relative
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        strip_quarantine(destination)


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
    state_sync = target / ".claude" / "hooks" / "scripts" / "state-sync.sh"
    if not state_sync.is_file():
        raise SystemExit(f"missing state-sync helper: {state_sync}")

    info("sync AI state via state-sync.sh")
    if dry_run:
        return

    env = os.environ.copy()
    if state_remote:
        env["AI_STATE_REMOTE"] = state_remote
    if local_only:
        env["AI_STATE_LOCAL_ONLY"] = "1"

    # stdin=DEVNULL (F2 in plans/plan-git-state-sync.md §9): state-sync.sh
    # drains stdin for up to 2s (a hook/task contract). When invoked from this
    # installer with inherited stdin, an interactive run would block on — and
    # swallow — terminal input; the installer never reads stdin, so close it.
    subprocess.run(["bash", str(state_sync), "setup"], check=False, cwd=target, env=env, stdin=subprocess.DEVNULL)
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
            subprocess.run(["git", "-C", str(target / ".claude"), "add", "-A"], check=False)
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            subprocess.run(
                ["git", "-C", str(target / ".claude"), "commit", "-q", "-m", f"bootstrap: update {timestamp}"],
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
        check=False, cwd=target, env=env, stdin=subprocess.DEVNULL,
    )
    if push_result.returncode != 0:
        warn("state-sync push reported a non-zero exit; state committed locally, will retry on next sync.")


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
        check=False, cwd=target, env=env, stdin=subprocess.DEVNULL,
    )
    require_clean_nested_state(target, "legacy state migration")
    history = nested_git(target, "log", "--format=%s")
    if history.returncode != 0 or "migrate: import pre-git state" not in history.stdout.splitlines():
        raise SystemExit("legacy state migration did not create a migrate: import pre-git state commit")


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
            if any(path == pattern.rstrip("/") or path.startswith(pattern.rstrip("/") + "/") for path in tracked)
        }
    )
    warn("some generated AI paths are already tracked by git.")
    print("Run this in the consumer repo if you want to untrack them while keeping local files:")
    print(f"git rm --cached -r -- {' '.join(unique_roots)}")


def main() -> int:
    args = parse_args()
    state_remote = args.state_remote or os.environ.get("AI_STATE_REMOTE")
    target = args.target_repo.expanduser().resolve()
    source = args.source.expanduser().resolve()

    claude_dir = target / ".claude"
    had_claude_git = (claude_dir / ".git").exists()
    had_pre_existing_content = claude_dir.is_dir() and not had_claude_git and any(claude_dir.iterdir())

    migrate_pre_existing_state(
        target,
        source,
        args.dry_run,
        state_remote,
        had_pre_existing_content,
        args.local_only,
    )
    copy_generated_tree(source, target, args.dry_run)
    substitute_project_name(target, args.dry_run)
    substitute_python_version(target, args.dry_run)
    populate_bootstrap_root(target, args.dry_run, args.commit_copilot_surface)
    update_devcontainer_state_remote(target, state_remote, args.dry_run)
    merge_gitignore(target, args.dry_run, args.commit_copilot_surface)
    chmod_runtime_scripts(target, args.dry_run)
    configure_git_hooks_path(target, args.dry_run)
    warn_tracked_paths(target, active_ignore_patterns(args.commit_copilot_surface))

    sync_state_after_install(
        target,
        args.dry_run,
        state_remote,
        had_claude_git,
        had_pre_existing_content,
        args.local_only,
    )

    info("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
