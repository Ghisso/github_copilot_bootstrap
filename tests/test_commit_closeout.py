"""Regression coverage for commit-native phase closeout behavior."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOKS_SOURCE = REPO_ROOT / "shared" / "hooks"
RECORD_FINDINGS = REPO_ROOT / "shared" / "scripts" / "record_findings.py"


def run_git(root: Path, *args: str, input_text: str | None = None) -> None:
    """Run Git with a deterministic identity in a disposable repository."""
    subprocess.run(
        [
            "git",
            "-c",
            "user.name=Closeout Test",
            "-c",
            "user.email=closeout@example.com",
            *args,
        ],
        cwd=root,
        input=input_text,
        text=True,
        check=True,
    )


def write_plan(root: Path, phase_status: str) -> Path:
    """Write the smallest completed-plan state consumed by the Git hook."""
    plans = root / ".claude" / "plans"
    plans.mkdir(parents=True, exist_ok=True)
    (plans / "foo.md").write_text(
        "---\n"
        "name: foo\n"
        "status: in-progress\n"
        "phases:\n"
        "  - phase-one\n"
        "current_phase: phase-one\n"
        "---\n",
        encoding="utf-8",
    )
    (plans / "phase-one.md").write_text(
        f"---\nstatus: {phase_status}\n---\n", encoding="utf-8"
    )
    return plans / "foo.md"


def hook_repo(tmp_path: Path, phase_status: str = "complete") -> tuple[Path, Path]:
    """Create an outer repository with the shipped native post-commit hook."""
    root = tmp_path / "consumer"
    root.mkdir()
    run_git(root, "init", "-q")
    (root / ".gitignore").write_text(".claude/\n", encoding="utf-8")
    (root / "tracked.txt").write_text("base\n", encoding="utf-8")
    run_git(root, "add", ".gitignore", "tracked.txt")
    run_git(root, "commit", "-qm", "base")
    run_git(root, "checkout", "-qb", "foo_implementation")

    hooks = root / ".claude" / "hooks"
    scripts = hooks / "scripts"
    git_hooks = hooks / "git-hooks"
    scripts.mkdir(parents=True)
    git_hooks.mkdir()
    for name in ("_lib-frontmatter.sh", "record-commit-closeout.sh"):
        shutil.copy2(HOOKS_SOURCE / "scripts" / name, scripts / name)
    shutil.copy2(HOOKS_SOURCE / "git-hooks" / "post-commit", git_hooks / "post-commit")
    for path in (*scripts.iterdir(), *git_hooks.iterdir()):
        path.chmod(0o755)
    (scripts / "state-sync.sh").write_text(
        "#!/usr/bin/env bash\n"
        "awk '/^(status|current_phase):/' .claude/plans/foo.md >> state-sync.log\n",
        encoding="utf-8",
    )
    (scripts / "state-sync.sh").chmod(0o755)
    run_git(root, "config", "core.hooksPath", ".claude/hooks/git-hooks")
    return root, write_plan(root, phase_status)


def add_declared_next_phase(root: Path, plan: Path, status: str | None) -> None:
    """Declare ``phase-two`` and optionally write its plan metadata."""
    plan.write_text(
        plan.read_text(encoding="utf-8").replace(
            "  - phase-one\n", "  - phase-one\n  - phase-two\n"
        ),
        encoding="utf-8",
    )
    if status is not None:
        (root / ".claude" / "plans" / "phase-two.md").write_text(
            f"---\nstatus: {status}\n---\n", encoding="utf-8"
        )


@pytest.mark.parametrize(
    ("args", "input_text"),
    (
        (("commit", "-m", "phase closeout"), None),
        (("commit", "-F", "message.txt"), None),
        (("commit", "-F", "-"), "phase closeout from stdin\n"),
    ),
    ids=("message", "message-file", "stdin"),
)
def test_post_commit_advances_completed_phase_for_every_git_message_source(
    tmp_path: Path, args: tuple[str, ...], input_text: str | None
) -> None:
    """Git's created HEAD, rather than shell text, drives phase advancement."""
    root, plan = hook_repo(tmp_path)
    if args == ("commit", "-F", "message.txt"):
        (root / "message.txt").write_text(
            "phase closeout from file\n", encoding="utf-8"
        )
        run_git(root, "add", "message.txt")
    else:
        (root / "work.txt").write_text("complete\n", encoding="utf-8")
        run_git(root, "add", "work.txt")

    run_git(root, *args, input_text=input_text)

    plan_text = plan.read_text(encoding="utf-8")
    assert "status: complete" in plan_text
    assert "current_phase: \n" in plan_text
    assert (root / "state-sync.log").read_text(encoding="utf-8") == (
        "status: complete\ncurrent_phase: \n"
    )


def test_post_commit_keeps_an_incomplete_phase_active(tmp_path: Path) -> None:
    """A successful ordinary commit cannot advance an unfinished phase."""
    root, plan = hook_repo(tmp_path, phase_status="in-progress")
    (root / "work.txt").write_text("in progress\n", encoding="utf-8")
    run_git(root, "add", "work.txt")

    run_git(root, "commit", "-m", "checkpoint")

    plan_text = plan.read_text(encoding="utf-8")
    assert "status: in-progress" in plan_text
    assert "current_phase: phase-one" in plan_text


def test_failed_commit_does_not_run_phase_advance(tmp_path: Path) -> None:
    """A failed Git commit leaves the completed plan untouched."""
    root, plan = hook_repo(tmp_path)

    result = subprocess.run(
        ["git", "commit", "-m", "nothing to commit"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "current_phase: phase-one" in plan.read_text(encoding="utf-8")


def test_post_commit_ignores_nonimplementation_branch(tmp_path: Path) -> None:
    """A completed plan cannot advance when Git commits on another branch."""
    root, plan = hook_repo(tmp_path)
    run_git(root, "checkout", "-qb", "dev")
    (root / "work.txt").write_text("other branch\n", encoding="utf-8")
    run_git(root, "add", "work.txt")

    run_git(root, "commit", "-m", "ordinary dev work")

    assert "current_phase: phase-one" in plan.read_text(encoding="utf-8")


def test_editor_produced_commit_advances_completed_phase(tmp_path: Path) -> None:
    """An editor/template commit uses the same native post-commit transition."""
    root, plan = hook_repo(tmp_path)
    (root / "message-template.txt").write_text("editor closeout\n", encoding="utf-8")
    editor = root / "editor.sh"
    editor.write_text(
        "#!/usr/bin/env bash\nprintf 'editor confirmed\\n' >> \"$1\"\n",
        encoding="utf-8",
    )
    editor.chmod(0o755)
    run_git(root, "config", "commit.template", "message-template.txt")

    result = subprocess.run(
        ["git", "commit", "--allow-empty"],
        cwd=root,
        env={**os.environ, "GIT_EDITOR": str(editor)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "status: complete" in plan.read_text(encoding="utf-8")


@pytest.mark.parametrize("phase_status", ("paused", "cancelled"))
def test_post_commit_keeps_noncompleted_terminal_paths_active(
    tmp_path: Path, phase_status: str
) -> None:
    """Paused and cancelled plans cannot be advanced by an ordinary commit."""
    root, plan = hook_repo(tmp_path, phase_status=phase_status)
    (root / "work.txt").write_text("checkpoint\n", encoding="utf-8")
    run_git(root, "add", "work.txt")

    run_git(root, "commit", "-m", "checkpoint")

    plan_text = plan.read_text(encoding="utf-8")
    assert "status: in-progress" in plan_text
    assert "current_phase: phase-one" in plan_text


def test_post_commit_bypass_does_not_advance_a_completed_phase(tmp_path: Path) -> None:
    """Recovery commits keep phase state unchanged and retain bypass evidence."""
    root, plan = hook_repo(tmp_path)
    (root / "work.txt").write_text("recovery\n", encoding="utf-8")
    run_git(root, "add", "work.txt")

    run_git(root, "commit", "-m", "fixup! phase closeout")

    plan_text = plan.read_text(encoding="utf-8")
    assert "status: in-progress" in plan_text
    assert "current_phase: phase-one" in plan_text
    assert "subject=fixup! phase closeout" in (
        root / ".claude" / "session_logs" / "hooks-bypass.log"
    ).read_text(encoding="utf-8")


def test_post_commit_requires_an_in_progress_next_phase(tmp_path: Path) -> None:
    """A completed next plan cannot be silently skipped by one commit."""
    root, plan = hook_repo(tmp_path)
    plan.write_text(
        plan.read_text(encoding="utf-8").replace(
            "  - phase-one\n", "  - phase-one\n  - phase-two\n"
        ),
        encoding="utf-8",
    )
    (root / ".claude" / "plans" / "phase-two.md").write_text(
        "---\nstatus: complete\n---\n", encoding="utf-8"
    )
    (root / "work.txt").write_text("complete\n", encoding="utf-8")
    run_git(root, "add", "work.txt")

    run_git(root, "commit", "-m", "phase closeout")

    assert "current_phase: phase-one" in plan.read_text(encoding="utf-8")


def test_recorded_head_cannot_advance_a_second_phase(tmp_path: Path) -> None:
    """Repeating the recorder for one HEAD cannot consume another phase."""
    root, plan = hook_repo(tmp_path)
    plan.write_text(
        plan.read_text(encoding="utf-8").replace(
            "  - phase-one\n", "  - phase-one\n  - phase-two\n"
        ),
        encoding="utf-8",
    )
    phase_two = root / ".claude" / "plans" / "phase-two.md"
    phase_two.write_text("---\nstatus: in-progress\n---\n", encoding="utf-8")
    (root / "work.txt").write_text("complete\n", encoding="utf-8")
    run_git(root, "add", "work.txt")
    run_git(root, "commit", "-m", "phase one")
    phase_two.write_text("---\nstatus: complete\n---\n", encoding="utf-8")

    result = subprocess.run(
        [
            "bash",
            str(root / ".claude" / "hooks" / "scripts" / "record-commit-closeout.sh"),
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == "skipped\n"
    assert "current_phase: phase-two" in plan.read_text(encoding="utf-8")


def test_merge_head_does_not_advance_a_completed_phase(tmp_path: Path) -> None:
    """The recorder rejects a merge commit even when the current phase is complete."""
    root, plan = hook_repo(tmp_path, phase_status="in-progress")
    run_git(root, "checkout", "-qb", "feature")
    (root / "feature.txt").write_text("feature\n", encoding="utf-8")
    run_git(root, "add", "feature.txt")
    run_git(root, "commit", "-m", "feature work")
    run_git(root, "checkout", "foo_implementation")
    (root / "main.txt").write_text("main\n", encoding="utf-8")
    run_git(root, "add", "main.txt")
    run_git(root, "commit", "-m", "main work")
    (root / ".claude" / "plans" / "phase-one.md").write_text(
        "---\nstatus: complete\n---\n", encoding="utf-8"
    )
    run_git(root, "merge", "--no-ff", "feature", "-m", "merge feature")

    result = subprocess.run(
        [
            "bash",
            str(root / ".claude" / "hooks" / "scripts" / "record-commit-closeout.sh"),
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == "skipped\n"
    assert "current_phase: phase-one" in plan.read_text(encoding="utf-8")


def test_post_commit_warns_before_sync_when_recorder_fails(tmp_path: Path) -> None:
    """Recorder failure is durable and cannot silently publish partial state."""
    root, plan = hook_repo(tmp_path)
    recorder = root / ".claude" / "hooks" / "scripts" / "record-commit-closeout.sh"
    recorder.write_text("#!/usr/bin/env bash\nexit 1\n", encoding="utf-8")
    recorder.chmod(0o755)
    (root / "work.txt").write_text("complete\n", encoding="utf-8")
    run_git(root, "add", "work.txt")

    result = subprocess.run(
        ["git", "commit", "-m", "phase closeout"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "current_phase: phase-one" in plan.read_text(encoding="utf-8")
    assert "commit closeout was not recorded" in (
        root / ".claude" / "session_logs" / "hooks-errors.log"
    ).read_text(encoding="utf-8")
    assert (root / "state-sync.log").read_text(encoding="utf-8") == (
        "status: in-progress\ncurrent_phase: phase-one\n"
    )


@pytest.mark.parametrize(
    ("mutate_plan", "expected"),
    (
        (
            lambda plan: plan.write_text(
                plan.read_text(encoding="utf-8").replace(
                    "current_phase: phase-one\n",
                    "current_phase: phase-one\ncurrent_phase: phase-one\n",
                ),
                encoding="utf-8",
            ),
            "duplicate or missing current_phase",
        ),
        (
            lambda plan: plan.write_text(
                plan.read_text(encoding="utf-8").replace(
                    "status: in-progress\n", "status: unknown\n", 1
                ),
                encoding="utf-8",
            ),
            "invalid status",
        ),
    ),
    ids=("duplicate-current-phase", "invalid-big-status"),
)
def test_post_commit_logs_malformed_active_plan_before_sync(
    tmp_path: Path,
    mutate_plan: Callable[[Path], None],
    expected: str,
) -> None:
    """Malformed active state warns durably but never makes Git fail."""
    root, plan = hook_repo(tmp_path)
    mutate_plan(plan)
    (root / "work.txt").write_text("closeout\n", encoding="utf-8")
    run_git(root, "add", "work.txt")

    result = subprocess.run(
        ["git", "commit", "-m", "phase closeout"],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert expected in result.stderr
    assert "commit closeout was not recorded" in (
        root / ".claude" / "session_logs" / "hooks-errors.log"
    ).read_text(encoding="utf-8")
    assert (root / "state-sync.log").exists()


@pytest.mark.parametrize(
    ("mutate", "expected"),
    (
        (
            lambda root, plan: (root / ".claude" / "plans" / "phase-one.md").unlink(),
            "missing current phase plan",
        ),
        (
            lambda root, plan: plan.write_text(
                plan.read_text(encoding="utf-8").replace(
                    "current_phase: phase-one", "current_phase: ../unsafe"
                ),
                encoding="utf-8",
            ),
            "invalid current_phase",
        ),
        (
            lambda root, plan: plan.write_text(
                plan.read_text(encoding="utf-8").replace("phases:\n", "", 1),
                encoding="utf-8",
            ),
            "duplicate or missing phases",
        ),
        (
            lambda root, plan: add_declared_next_phase(root, plan, None),
            "missing declared phase plan",
        ),
        (
            lambda root, plan: add_declared_next_phase(root, plan, "unknown"),
            "declared phase has invalid status",
        ),
    ),
    ids=(
        "missing-current-plan",
        "unsafe-current-phase",
        "missing-phases",
        "missing-declared-phase",
        "invalid-declared-phase",
    ),
)
def test_recorder_returns_error_for_malformed_active_metadata(
    tmp_path: Path, mutate: Callable[[Path, Path], None], expected: str
) -> None:
    """Only expected lifecycle no-ops may return ``skipped``."""
    root, plan = hook_repo(tmp_path)
    mutate(root, plan)

    result = subprocess.run(
        [
            "bash",
            str(root / ".claude" / "hooks" / "scripts" / "record-commit-closeout.sh"),
        ],
        cwd=root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert expected in result.stderr


@pytest.mark.parametrize(
    "untracked", (True, False), ids=("inside-target", "outside-target")
)
def test_record_findings_warns_only_for_untracked_target_files(
    tmp_path: Path, untracked: bool
) -> None:
    """Untracked target content receives an actionable warning without schema drift."""
    root = tmp_path / "repository"
    root.mkdir()
    run_git(root, "init", "-q")
    (root / "src").mkdir()
    (root / "src" / "tracked.py").write_text("VALUE = 1\n", encoding="utf-8")
    run_git(root, "add", "src/tracked.py")
    run_git(root, "commit", "-qm", "base")
    untracked_path = root / ("src/new.py" if untracked else "elsewhere.py")
    untracked_path.write_text("VALUE = 2\n", encoding="utf-8")
    report = root / "findings.json"

    result = subprocess.run(
        [
            sys.executable,
            str(RECORD_FINDINGS),
            "src",
            "--profile",
            "code",
            "--out",
            str(report),
        ],
        cwd=root,
        input="[]",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    data = json.loads(report.read_text(encoding="utf-8"))
    assert "untracked_files" not in data
    if untracked:
        assert "src/new.py" in result.stderr
        assert "stage intended files before recording again" in result.stderr
    else:
        assert result.stderr == ""


def test_record_findings_uses_lexical_paths_and_escapes_controls(
    tmp_path: Path,
) -> None:
    """Warnings neither follow target symlinks nor render terminal control bytes."""
    root = tmp_path / "repository"
    root.mkdir()
    run_git(root, "init", "-q")
    (root / "src").mkdir()
    (root / "src" / "tracked.py").write_text("VALUE = 1\n", encoding="utf-8")
    run_git(root, "add", "src/tracked.py")
    run_git(root, "commit", "-qm", "base")
    outside = tmp_path / "outside"
    outside.mkdir()
    (root / "src" / "link").symlink_to(outside, target_is_directory=True)
    (root / "src" / "new\nfile.py").write_text("VALUE = 2\n", encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(RECORD_FINDINGS),
            "src",
            "--profile",
            "code",
            "--out",
            "report.json",
        ],
        cwd=root,
        input="[]",
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "src/new\\nfile.py" in result.stderr
    assert "src/link" in result.stderr
    assert str(outside) not in result.stderr
