#!/usr/bin/env python3
"""
Regenerate dist/ and update one or more consumer repos with the latest bootstrap.

Preserves user state files (.claude/MEMORY.md) that the bootstrap template
would otherwise overwrite. Everything else (agents, hooks, instructions,
settings, skills, templates) is replaced with the new version. Files that
exist only in the consumer repo (plans, session_logs, quality_reports, etc.)
are never touched.

Usage:
    uv run python scripts/update_consumers.py /path/to/repo1 /path/to/repo2 ...

Options:
    --skip-regen     Skip regenerating dist/ before installing
    --skip-upload    Skip Hugging Face upload (local install only)
    --dry-run        Print planned actions without writing files
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

BOOTSTRAP_ROOT = Path(__file__).resolve().parent.parent
INSTALLER = BOOTSTRAP_ROOT / "scripts" / "install_bootstrap.py"
GENERATOR = BOOTSTRAP_ROOT / "scripts" / "generate_targets.py"

# Files present in dist/ that carry user-owned content in consumer repos.
# These are backed up before install and restored after.
PRESERVED_RELPATHS = [
    ".claude/MEMORY.md",
]


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, cwd=BOOTSTRAP_ROOT)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate dist/ and update consumer repos with the latest bootstrap."
    )
    parser.add_argument("projects", nargs="+", help="Paths to consumer repos to update.")
    parser.add_argument("--skip-regen", action="store_true", help="Skip regenerating dist/ first.")
    parser.add_argument("--skip-upload", action="store_true", help="Skip Hugging Face upload.")
    parser.add_argument("--dry-run", action="store_true", help="Print planned actions only.")
    args = parser.parse_args()

    dry = args.dry_run

    if not args.skip_regen:
        print("=== Regenerating dist/ ===")
        cmd = [sys.executable, str(GENERATOR), "--all"]
        if dry:
            print(f"  [dry-run] {' '.join(cmd)}")
        else:
            run(cmd)

    for project_str in args.projects:
        project = Path(project_str).resolve()
        if not project.is_dir():
            print(f"ERROR: {project} is not a directory", file=sys.stderr)
            sys.exit(1)

        print(f"\n=== Updating {project.name} ({project}) ===", flush=True)

        # Back up preserved files
        backups: dict[Path, bytes | None] = {}
        for rel in PRESERVED_RELPATHS:
            path = project / rel
            content = path.read_bytes() if path.exists() else None
            backups[path] = content
            if content is not None:
                print(f"  backup:  {rel} ({len(content)} bytes)", flush=True)
            else:
                print(f"  missing: {rel} (nothing to preserve)", flush=True)

        # Run installer
        install_cmd = [sys.executable, str(INSTALLER), str(project)]
        if args.skip_upload:
            install_cmd.append("--skip-upload")
        if dry:
            install_cmd.append("--dry-run")
        run(install_cmd)

        # Restore preserved files
        for path, content in backups.items():
            rel = path.relative_to(project)
            if content is None:
                continue
            if dry:
                print(f"  [dry-run] restore: {rel}")
            else:
                path.write_bytes(content)
                print(f"  restore: {rel}")

        print(f"=== Done: {project.name} ===")

    print("\nAll projects updated.")


if __name__ == "__main__":
    main()
