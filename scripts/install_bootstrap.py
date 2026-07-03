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
        "--bucket",
        default=None,
        help="HF bucket id or bucket prefix path used for bootstrap/state sync. "
        "Required unless HF_AI_SYNC_BUCKET is set in the environment. No default "
        "is baked in, so no personal namespace ships in the bootstrap.",
    )
    parser.add_argument(
        "--prefix",
        help="Optional project prefix inside the bucket. Overrides remote-derived prefixes.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions without writing files.")
    parser.add_argument("--skip-upload", action="store_true", help="Do not upload bootstrap files to HF.")
    parser.add_argument("--verbose", action="store_true", help="Pass verbose mode to the HF sync helper.")
    return parser.parse_args()


def info(message: str) -> None:
    print(f"install-bootstrap: {message}")


def warn(message: str) -> None:
    print(f"WARNING install-bootstrap: {message}", file=sys.stderr)


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
            shutil.copytree(child, destination, dirs_exist_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(child, destination)


def ignore_block() -> str:
    lines = [IGNORE_BLOCK_START, *IGNORE_PATTERNS, IGNORE_BLOCK_END]
    return "\n".join(lines) + "\n"


def merge_gitignore(target: Path, dry_run: bool) -> None:
    gitignore = target / ".gitignore"
    block = ignore_block()
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
    patterns = (".claude/hooks/scripts/*.sh", ".devcontainer/*.sh", ".devcontainer/*.py")
    for pattern in patterns:
        for path in target.glob(pattern):
            if not path.is_file():
                continue
            info(f"chmod +x {path.relative_to(target)}")
            if dry_run:
                continue
            path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def update_devcontainer_sync_env(target: Path, bucket: str, prefix: str | None, dry_run: bool) -> None:
    devcontainer_path = target / ".devcontainer" / "devcontainer.json"
    if not devcontainer_path.is_file():
        warn(f"missing devcontainer config: {devcontainer_path}")
        return

    info(f"set devcontainer HF_AI_SYNC_BUCKET={bucket}")
    if prefix:
        info(f"set devcontainer HF_AI_SYNC_PREFIX={prefix}")
    if dry_run:
        return

    data = json.loads(devcontainer_path.read_text(encoding="utf-8"))
    container_env = data.setdefault("containerEnv", {})
    container_env["HF_AI_SYNC_BUCKET"] = bucket
    if prefix:
        container_env["HF_AI_SYNC_PREFIX"] = prefix
    else:
        container_env.pop("HF_AI_SYNC_PREFIX", None)
    devcontainer_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def tracked_generated_paths(target: Path) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(target), "ls-files", "--", *IGNORE_PATTERNS],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def warn_tracked_paths(target: Path) -> None:
    tracked = tracked_generated_paths(target)
    if not tracked:
        return
    unique_roots = sorted(
        {
            pattern.rstrip("/")
            for pattern in IGNORE_PATTERNS
            if any(path == pattern.rstrip("/") or path.startswith(pattern.rstrip("/") + "/") for path in tracked)
        }
    )
    warn("some generated AI paths are already tracked by git.")
    print("Run this in the consumer repo if you want to untrack them while keeping local files:")
    print(f"git rm --cached -r -- {' '.join(unique_roots)}")


def upload_bootstrap(target: Path, bucket: str, prefix: str | None, dry_run: bool, verbose: bool) -> None:
    helper = target / ".devcontainer" / "hf-ai-sync.py"
    if not helper.is_file():
        warn(f"missing HF sync helper: {helper}")
        return

    command = [
        sys.executable,
        str(helper),
        "upload-bootstrap",
        "--repo-root",
        str(target),
        "--bucket",
        bucket,
    ]
    if prefix:
        command.extend(["--prefix", prefix])
    if dry_run:
        command.append("--dry-run")
    if verbose:
        command.append("--verbose")

    env = os.environ.copy()
    repo_venv_bin = REPO_ROOT / ".venv" / "bin"
    if repo_venv_bin.is_dir():
        env["PATH"] = f"{repo_venv_bin}{os.pathsep}{env.get('PATH', '')}"

    info("upload generated AI bootstrap bundle to Hugging Face")
    result = subprocess.run(command, text=True, check=False, env=env)
    if result.returncode != 0:
        warn("HF bootstrap upload command failed; continuing.")


def main() -> int:
    args = parse_args()
    bucket = args.bucket or os.environ.get("HF_AI_SYNC_BUCKET")
    if not bucket:
        print(
            "error: no HF sync bucket configured. Pass --bucket <org/bucket[/prefix]> "
            "or set HF_AI_SYNC_BUCKET in the environment before installing.",
            file=sys.stderr,
        )
        return 2
    args.bucket = bucket
    target = args.target_repo.expanduser().resolve()
    source = args.source.expanduser().resolve()

    copy_generated_tree(source, target, args.dry_run)
    update_devcontainer_sync_env(target, args.bucket, args.prefix, args.dry_run)
    merge_gitignore(target, args.dry_run)
    chmod_runtime_scripts(target, args.dry_run)
    warn_tracked_paths(target)

    if args.skip_upload:
        info("skipping HF bootstrap upload")
    else:
        upload_bootstrap(target, args.bucket, args.prefix, args.dry_run, args.verbose)

    info("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
