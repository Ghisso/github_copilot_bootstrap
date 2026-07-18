#!/usr/bin/env python3
"""Install the generated multi-agent bootstrap into a consumer repository."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import stat
import subprocess
import sys
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
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without writing files.")
    return parser.parse_args()


def info(message: str) -> None:
    print(f"install-bootstrap: {message}")


def warn(message: str) -> None:
    print(f"WARNING install-bootstrap: {message}", file=sys.stderr)


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
) -> None:
    """Commits and pushes the nested .claude/ AI-state repo (D1/D4). A
    pre-git .claude/ with real content migrates as one `migrate:` commit
    (state-sync.sh owns that commit message); otherwise this makes its own
    `bootstrap: install/update <timestamp>` commit, distinct from the
    `session:` commits the Stop hook makes."""
    state_sync = target / ".claude" / "hooks" / "scripts" / "state-sync.sh"
    if not state_sync.is_file():
        warn(f"missing state-sync helper: {state_sync}")
        return

    info("sync AI state via state-sync.sh")
    if dry_run:
        return

    env = os.environ.copy()
    if state_remote:
        env["AI_STATE_REMOTE"] = state_remote

    # stdin=DEVNULL (F2 in plans/plan-git-state-sync.md §9): state-sync.sh
    # drains stdin for up to 2s (a hook/task contract). When invoked from this
    # installer with inherited stdin, an interactive run would block on — and
    # swallow — terminal input; the installer never reads stdin, so close it.
    if not had_claude_git and had_pre_existing_content:
        # migrate-from-hf owns setup + its own "migrate:" commit + push.
        subprocess.run(
            ["bash", str(state_sync), "migrate-from-hf"],
            check=False, cwd=target, env=env, stdin=subprocess.DEVNULL,
        )
        return

    subprocess.run(["bash", str(state_sync), "setup"], check=False, cwd=target, env=env, stdin=subprocess.DEVNULL)
    # On a truly fresh install, `setup` above already committed everything
    # currently on disk as "bootstrap: init ai-state" (it always commits
    # whatever it finds when .claude/.git doesn't yet exist) — that commit
    # already satisfies D1's bootstrap:-prefixed-commit requirement, so there
    # is nothing left to stage here. On a repeat run .claude/.git already
    # existed, so `setup` was a no-op, and this run's freshly copied files
    # are real, uncommitted changes that need their own commit.
    if had_claude_git:
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

    push_result = subprocess.run(
        ["bash", str(state_sync), "push"],
        check=False, cwd=target, env=env, stdin=subprocess.DEVNULL,
    )
    if push_result.returncode != 0:
        warn("state-sync push reported a non-zero exit; state committed locally, will retry on next sync.")


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

    copy_generated_tree(source, target, args.dry_run)
    substitute_project_name(target, args.dry_run)
    populate_bootstrap_root(target, args.dry_run, args.commit_copilot_surface)
    update_devcontainer_state_remote(target, state_remote, args.dry_run)
    merge_gitignore(target, args.dry_run, args.commit_copilot_surface)
    chmod_runtime_scripts(target, args.dry_run)
    configure_git_hooks_path(target, args.dry_run)
    warn_tracked_paths(target, active_ignore_patterns(args.commit_copilot_surface))

    sync_state_after_install(target, args.dry_run, state_remote, had_claude_git, had_pre_existing_content)

    info("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
