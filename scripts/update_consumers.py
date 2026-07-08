#!/usr/bin/env python3
"""
Regenerate dist/ and update one or more consumer repos with the latest bootstrap.

Runs install_bootstrap.py for each repo, which replaces every
bootstrap-controlled file (agents, hooks, instructions, settings, skills,
templates) with the new version and commits+pushes the change on the
consumer's git-backed ai-state branch (D1/D4 in
plans/plan-git-state-sync.md). Files that exist only in the consumer repo
(MEMORY.md, plans, session_logs, quality_reports, etc.) are state, not
bootstrap content, so the installer never touches them beyond what a normal
`bootstrap:` commit implies — there is no more backup/restore step, since
state now lives in git history rather than being overwritten in place by a
bucket pull.

For a consumer whose .claude/ predates this plan (no .claude/.git yet), runs
state-sync.sh migrate-from-hf first so its pre-existing state becomes one
`migrate: import pre-git state` commit before the bootstrap update lands on
top of it.

Usage:
    uv run python scripts/update_consumers.py /path/to/repo1 /path/to/repo2 ...

Options:
    --skip-regen     Skip regenerating dist/ before installing
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


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, cwd=BOOTSTRAP_ROOT)


def migrate_pre_git_state(project: Path, dry_run: bool) -> None:
    claude_dir = project / ".claude"
    state_sync = claude_dir / "hooks" / "scripts" / "state-sync.sh"
    if (claude_dir / ".git").exists() or not state_sync.is_file():
        return
    if not any(claude_dir.iterdir()):
        return
    print(f"  migrate-from-hf: {claude_dir} predates git-backed state", flush=True)
    if dry_run:
        return
    # stdin=DEVNULL (F2 §9): state-sync.sh drains stdin for up to 2s; this
    # updater never reads it, so an interactive run must not block/swallow it.
    subprocess.run(
        ["bash", str(state_sync), "migrate-from-hf"],
        check=False, cwd=project, stdin=subprocess.DEVNULL,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate dist/ and update consumer repos with the latest bootstrap."
    )
    parser.add_argument("projects", nargs="+", help="Paths to consumer repos to update.")
    parser.add_argument("--skip-regen", action="store_true", help="Skip regenerating dist/ first.")
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

        migrate_pre_git_state(project, dry)

        install_cmd = [sys.executable, str(INSTALLER), str(project)]
        if dry:
            install_cmd.append("--dry-run")
        run(install_cmd)

        print(f"=== Done: {project.name} ===")

    print("\nAll projects updated.")


if __name__ == "__main__":
    main()
