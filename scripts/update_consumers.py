#!/usr/bin/env python3
"""
Regenerate dist/ and update one or more consumer repos with the latest bootstrap.

Runs install_bootstrap.py for each repo without `--mode`, so each target's
install mode (full or sidecar) is auto-detected from the target alone
(`detect_install_mode`). A full consumer gets today's takeover refresh: every
bootstrap-controlled file (agents, hooks, instructions, settings, skills,
templates) is replaced, and the change is committed and pushed on the
consumer's git-backed ai-state branch (D1/D4 in
plans/plan-git-state-sync.md). A sidecar consumer instead gets its private,
per-clone overlay reconciled (`sidecar_overlay.install_sidecar`): only its own
skill and bridge files change, and no tracked file, hook, or AI-state branch
is touched (big plan
`.claude/plans/consumer-sidecar-bootstrap-overlay.md`, Decision 20). Files
that exist only in a full consumer repo (MEMORY.md, plans, session_logs,
quality_reports, etc.) are state, not bootstrap content, so the installer
never touches them beyond what a normal `bootstrap:` commit implies — there
is no more backup/restore step, since state now lives in git history rather
than being overwritten in place by a bucket pull.

For a full consumer whose .claude/ predates this plan (no .claude/.git yet),
the installer commits its pre-existing state as `migrate: import pre-git
state` before the bootstrap update lands on top of it.

A batch may mix full and sidecar consumers. When one target's installer
exits non-zero, or a target path is not a directory, this script records it
and moves on to the next target instead of stopping the batch. After the
last target it prints one `FAILED: <path> (exit <code>)` line per failed
target and exits 1; it prints "All projects updated." (or, in `--dry-run`,
"Preview complete; no projects were updated.") only when every target
succeeded. A `dist/` regeneration failure still stops the batch before any
target runs.

Usage:
    uv run python scripts/update_consumers.py /path/to/repo1 /path/to/repo2 ...

Options:
    --skip-regen     Skip regenerating dist/ before installing
    --dry-run        Print planned actions without writing files
    --allow-self     Permit refreshing this bootstrap repo's own overlay
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


def run_target(cmd: list[str]) -> int:
    """Run one target's installer and return its exit code without raising.

    Unlike ``run``, a non-zero exit is a per-target failure (Decision 20 in
    ``.claude/plans/consumer-sidecar-bootstrap-overlay.md``): the caller
    records it and continues with the next target instead of stopping the
    batch.
    """
    return subprocess.run(cmd, cwd=BOOTSTRAP_ROOT).returncode


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Regenerate dist/ and update consumer repos with the latest bootstrap."
    )
    parser.add_argument(
        "projects", nargs="+", help="Paths to consumer repos to update."
    )
    parser.add_argument(
        "--skip-regen", action="store_true", help="Skip regenerating dist/ first."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print planned actions only."
    )
    parser.add_argument(
        "--allow-self",
        action="store_true",
        help="Permit refreshing the bootstrap repository's own dogfood overlay.",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Commit refreshes locally without remote AI-state sync.",
    )
    parser.add_argument(
        "--commit-copilot-surface",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Select committed or local-only Copilot surfaces for every project. "
        "Omit to retain each consumer's persisted mode.",
    )
    args = parser.parse_args()

    dry = args.dry_run

    if not args.skip_regen:
        print("=== Regenerating dist/ ===")
        cmd = [sys.executable, str(GENERATOR), "--all"]
        if dry:
            print(f"  [dry-run] {' '.join(cmd)}")
        else:
            run(cmd)

    failures: list[tuple[Path, int]] = []

    for project_str in args.projects:
        project = Path(project_str).resolve()
        if not project.is_dir():
            print(f"ERROR: {project} is not a directory", file=sys.stderr)
            failures.append((project, 1))
            continue

        action = "Previewing" if dry else "Updating"
        print(f"\n=== {action} {project.name} ({project}) ===", flush=True)

        install_cmd = [sys.executable, str(INSTALLER), str(project)]
        if dry:
            install_cmd.append("--dry-run")
        if args.local_only:
            install_cmd.append("--local-only")
        if args.allow_self:
            install_cmd.append("--allow-self")
        if args.commit_copilot_surface is not None:
            install_cmd.append(
                "--commit-copilot-surface"
                if args.commit_copilot_surface
                else "--no-commit-copilot-surface"
            )
        exit_code = run_target(install_cmd)
        if exit_code != 0:
            failures.append((project, exit_code))
            continue

        if dry:
            print(f"=== Preview complete: {project.name}; no files updated ===")
        else:
            print(f"=== Done: {project.name} ===")

    if failures:
        for project, exit_code in failures:
            print(f"FAILED: {project} (exit {exit_code})")
        sys.exit(1)

    print(
        "\nPreview complete; no projects were updated."
        if dry
        else "\nAll projects updated."
    )


if __name__ == "__main__":
    main()
