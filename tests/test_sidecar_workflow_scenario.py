"""End-to-end scenario for the sidecar's workflow profile (big plan
sidecar-workflow-profile, Phase B step 8).

One real Git repository whose team tracks ``.claude/`` (a settings file, a
team skill, a team agent, and a team rule) goes through the whole life of a
workflow-profile install: dry run, install, personal state, rerun, profile
switch both ways, backup, uninstall that keeps the state, uninstall that
purges it, and a reinstall that reseeds. Every step asserts that
``git status --porcelain --untracked-files=all`` is unchanged, that the
team's files are byte-identical, and that a dry run predicts the real run.
"""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import sidecar_overlay as sidecar_overlay_module  # noqa: E402
from runtime_ownership import (  # noqa: E402
    SIDECAR_LEGACY_STATE_ROOT,
    SIDECAR_STATE_ROOT,
    SIDECAR_STATE_SEED_FILES,
    SIDECAR_WORKFLOW_AGENTS,
    SIDECAR_WORKFLOW_RULES,
    SIDECAR_WORKFLOW_SKILLS,
    SIDECAR_WORKFLOW_TEMPLATES,
)
from sidecar_overlay import (  # noqa: E402
    _unit_name,
    backup_sidecar_state,
    install_sidecar,
    read_sidecar_profile,
    uninstall_sidecar,
)
from sidecar_test_helpers import (  # noqa: E402
    _absolute_git_dir,
    _commit,
    _commit_staged,
    _exclude_path,
    _init_repo,
    _manifest_path,
    _raise_at,
    _read_manifest,
    _status,
)

INSTALLER = REPO_ROOT / "scripts" / "install_bootstrap.py"
WORKFLOW_SOURCE = REPO_ROOT / "dist" / "sidecar" / "workflow"
SKILLS_SOURCE = REPO_ROOT / "dist" / "sidecar" / "skills"
TEAM_FILES = {
    ".claude/settings.json": '{\n  "cleanupPeriodDays": 30\n}\n',
    ".claude/skills/ponytail/SKILL.md": "---\nname: ponytail\ndescription: the team's own ponytail\n---\nteam body\n",
    ".claude/agents/reviewer.md": "---\nname: reviewer\ndescription: the team's reviewer\n---\nteam reviewer\n",
    ".claude/rules/team.md": "Team rule.\n",
    "app.py": "def add(a: int, b: int) -> int:\n    return a + b\n",
}
STATE = Path(SIDECAR_STATE_ROOT)
LEGACY_STATE = Path(SIDECAR_LEGACY_STATE_ROOT)


@pytest.fixture
def team_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    _init_repo(root)
    for relative, text in TEAM_FILES.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    _commit(root, "team repository")
    return root


def _team_bytes(root: Path) -> dict[str, str]:
    return {
        relative: (root / relative).read_text(encoding="utf-8")
        for relative in TEAM_FILES
    }


def _exclude_block(root: Path) -> str:
    text = (_absolute_git_dir(root) / "info" / "exclude").read_text(encoding="utf-8")
    if "# BEGIN ai-bootstrap sidecar" not in text:
        return ""
    start = text.index("# BEGIN ai-bootstrap sidecar")
    end = text.index("# END ai-bootstrap sidecar")
    return text[start:end]


def _sidecar_files(root: Path, *relative_roots: str) -> set[str]:
    found: set[str] = set()
    for relative_root in relative_roots:
        base = root / relative_root
        if base.exists():
            found.update(
                str(p.relative_to(root)) for p in base.rglob("*") if p.is_file()
            )
    return found


def _tree_snapshot(root: Path) -> dict[Path, bytes | None]:
    """A byte-for-byte snapshot of every file under ``root``, including
    ``.git`` when ``root`` is a repository root: used to prove a dry run,
    or a refused real run, wrote nothing anywhere."""
    return {
        path.relative_to(root): path.read_bytes() if path.is_file() else None
        for path in root.rglob("*")
    }


def _move_state_to_legacy_root(root: Path) -> Path:
    """Simulate a pre-finding-1 workflow install: rename the just-seeded
    state folder back to the recognized legacy root
    (``SIDECAR_LEGACY_STATE_ROOT``), and repoint its own exclude line to
    match -- exactly what an older bootstrap version left behind. Returns
    the legacy directory's absolute path. Requires a prior
    ``install_sidecar(..., profile="workflow")`` so the state folder and
    its exclude line already exist."""
    new_dir = root / STATE
    legacy_dir = root / LEGACY_STATE
    legacy_dir.parent.mkdir(parents=True, exist_ok=True)
    new_dir.rename(legacy_dir)
    exclude_path = _exclude_path(root)
    text = exclude_path.read_text(encoding="utf-8")
    text = text.replace(f"/{SIDECAR_STATE_ROOT}\n", f"/{SIDECAR_LEGACY_STATE_ROOT}\n")
    exclude_path.write_text(text, encoding="utf-8")
    return legacy_dir


def _preserved_entries(root: Path) -> list[str]:
    folder = _absolute_git_dir(root) / "ai-bootstrap-sidecar-preserved"
    return sorted(p.name for p in folder.iterdir()) if folder.exists() else []


def test_workflow_profile_life_cycle(
    team_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    status_before = _status(team_repo)
    team_before = _team_bytes(team_repo)

    # 1. Dry run writes nothing, not even the state folder.
    assert (
        install_sidecar(team_repo, WORKFLOW_SOURCE, dry_run=True, profile="workflow")
        == 0
    )
    dry = capsys.readouterr().out
    assert "would install .claude/skills/humanize" in dry
    assert "SKIPPED .claude/agents/reviewer.md" in dry
    assert "SKIPPED .claude/skills/ponytail" in dry
    assert _status(team_repo) == status_before
    assert not (team_repo / STATE).exists()

    # 2. Install: every unit kind, the state seeded, team files untouched.
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    out = capsys.readouterr().out
    assert "SKIPPED .claude/agents/reviewer.md" in out
    assert "SKIPPED .claude/skills/ponytail" in out
    assert _status(team_repo) == status_before
    assert _team_bytes(team_repo) == team_before
    for seed in SIDECAR_STATE_SEED_FILES:
        assert (team_repo / STATE / seed).is_file()
    for agent in SIDECAR_WORKFLOW_AGENTS:
        expected = agent != "reviewer"
        path = team_repo / ".claude" / "agents" / f"{agent}.md"
        assert (expected and "mcp__" not in path.read_text(encoding="utf-8")) or (
            not expected
        )
        if not expected:
            assert (
                path.read_text(encoding="utf-8")
                == TEAM_FILES[".claude/agents/reviewer.md"]
            )
    for rule in SIDECAR_WORKFLOW_RULES:
        assert (team_repo / ".claude" / "rules" / f"ai-bootstrap-{rule}.md").is_file()
    for template in SIDECAR_WORKFLOW_TEMPLATES:
        assert (team_repo / ".claude" / "templates" / template).is_file()
    for skill in SIDECAR_WORKFLOW_SKILLS:
        expected = skill != "ponytail"
        assert (
            team_repo / ".agents" / "skills" / skill / "SKILL.md"
        ).is_file() is expected
    assert (
        team_repo / ".github" / "instructions" / "ai-bootstrap-workflow.instructions.md"
    ).is_file()
    block = _exclude_block(team_repo)
    assert block.count(f"/{SIDECAR_STATE_ROOT}\n") == 1
    assert read_sidecar_profile(team_repo) == "workflow"

    # 3. Personal state survives a rerun untouched; the state line is recognized.
    plan = team_repo / STATE / "plans" / "2026-09-27_try.md"
    plan.write_text("# try\n", encoding="utf-8")
    memory = team_repo / STATE / "MEMORY.md"
    memory.write_text(
        memory.read_text(encoding="utf-8") + "\n- personal note\n", encoding="utf-8"
    )
    (team_repo / STATE / "plans" / "README.md").unlink()
    status_with_state = _status(team_repo)

    assert (
        install_sidecar(team_repo, WORKFLOW_SOURCE, dry_run=True, profile="workflow")
        == 0
    )
    seed_dry = capsys.readouterr().out
    # Finding 3: a dry run predicts the missing seed file would be
    # restored, but never claims it already was, and never restores it.
    assert f"would seed {STATE}/plans/README.md" in seed_dry
    assert f"seeded {STATE}/plans/README.md" not in seed_dry
    assert not (team_repo / STATE / "plans" / "README.md").exists()
    assert _status(team_repo) == status_with_state

    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    out = capsys.readouterr().out
    assert "does not recognize" not in out
    assert _status(team_repo) == status_with_state
    assert plan.is_file() and "personal note" in memory.read_text(encoding="utf-8")
    assert (team_repo / STATE / "plans" / "README.md").is_file(), (
        "a deleted seed file is re-added"
    )
    assert _exclude_block(team_repo).count(f"/{SIDECAR_STATE_ROOT}\n") == 1

    # 4. Switch to the skills profile: workflow units go, the state stays hidden.
    assert (
        install_sidecar(team_repo, SKILLS_SOURCE, dry_run=True, profile="skills") == 0
    )
    downgrade_dry = capsys.readouterr().out
    # Finding 3: the downgrade dry run predicts every removal; it never
    # claims one already happened.
    assert "would remove .claude/templates/plan-big.md" in downgrade_dry
    assert "removed .claude/templates/plan-big.md" not in downgrade_dry
    assert _status(team_repo) == status_with_state
    assert (team_repo / ".claude" / "templates" / "plan-big.md").is_file()
    assert install_sidecar(team_repo, SKILLS_SOURCE, profile="skills") == 0
    capsys.readouterr()
    assert _status(team_repo) == status_with_state
    assert _sidecar_files(team_repo, ".claude/agents") == {".claude/agents/reviewer.md"}
    assert not (team_repo / ".claude" / "templates").exists()
    assert plan.is_file()
    assert _exclude_block(team_repo).count(f"/{SIDECAR_STATE_ROOT}\n") == 1
    assert read_sidecar_profile(team_repo) == "skills"

    # 5. Switch back: the workflow units return, the skills-profile bridges go.
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    assert _status(team_repo) == status_with_state
    assert (team_repo / ".claude" / "templates" / "plan-big.md").is_file()
    assert not (team_repo / ".claude" / "rules" / "ai-bootstrap-sidecar.md").exists()
    assert plan.is_file() and "personal note" in memory.read_text(encoding="utf-8")

    # 6. Backup copies the state into the Git directory and changes nothing else.
    assert backup_sidecar_state(team_repo) == 0
    capsys.readouterr()
    backups = _preserved_entries(team_repo)
    assert len(backups) == 1 and backups[0].startswith("state--")
    assert _status(team_repo) == status_with_state
    assert plan.is_file()

    # 7. Uninstall keeps the state folder and its exclude line.
    assert uninstall_sidecar(team_repo, dry_run=True) == 0
    dry = capsys.readouterr().out
    assert "kept .ai-bootstrap and its exclude line" in dry
    assert uninstall_sidecar(team_repo) == 0
    out = capsys.readouterr().out
    assert (
        "kept .ai-bootstrap and its exclude line; pass --purge-state to remove it"
        in out
    )
    assert _status(team_repo) == status_with_state
    assert _team_bytes(team_repo) == team_before
    assert plan.is_file()
    assert _exclude_block(team_repo).count(f"/{SIDECAR_STATE_ROOT}\n") == 1
    assert _sidecar_files(
        team_repo, ".claude/rules", ".claude/templates", ".agents"
    ) == {".claude/rules/team.md"}
    assert uninstall_sidecar(team_repo) == 0, "a second uninstall is a no-op"
    capsys.readouterr()
    assert plan.is_file()

    # 8. Purge moves the state into the preserved folder and removes the block.
    assert uninstall_sidecar(team_repo, dry_run=True, purge_state=True) == 0
    purge_dry = capsys.readouterr().out
    # Finding 3: a purge dry run predicts the move (the `would preserve`
    # action line, and the PRESERVED report's own remedy, both reworded to
    # "would move"/"would be moved"), never claims it happened, and writes
    # nothing. The per-action `PRESERVED <unit> -> <destination>` line
    # (distinct from the `PRESERVED <unit>: <remedy>` report line) is a
    # real-run-only line and must not appear.
    assert "would preserve .ai-bootstrap ->" in purge_dry
    assert "a real uninstall with --purge-state would move" in purge_dry
    assert "PRESERVED .ai-bootstrap ->" not in purge_dry
    assert "was moved out of the client folders" not in purge_dry
    assert (team_repo / STATE).is_dir()
    assert _exclude_block(team_repo) != ""
    assert plan.is_file()
    assert uninstall_sidecar(team_repo, purge_state=True) == 0
    out = capsys.readouterr().out
    assert "PRESERVED .ai-bootstrap" in out
    assert not (team_repo / STATE).exists()
    assert _exclude_block(team_repo) == ""
    assert len(_preserved_entries(team_repo)) == 2
    assert _status(team_repo) == status_before
    assert _team_bytes(team_repo) == team_before

    # 9. Reinstall reseeds a fresh state folder.
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    assert _status(team_repo) == status_before
    assert (team_repo / STATE / "MEMORY.md").is_file()
    assert "personal note" not in (team_repo / STATE / "MEMORY.md").read_text(
        encoding="utf-8"
    )


def test_version_1_manifest_reads_as_skills_and_upgrades_in_place(
    team_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A manifest written before profiles has no `profile` key and schema 1;
    a rerun without `--profile` reads it as `skills`, rewrites it as schema 2,
    and changes no unit."""
    assert install_sidecar(team_repo, SKILLS_SOURCE) == 0
    capsys.readouterr()
    manifest_path = _absolute_git_dir(team_repo) / "ai-bootstrap-sidecar.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = 1
    del manifest["profile"]
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    files_before = _sidecar_files(team_repo, ".claude", ".agents", ".github")
    status_before = _status(team_repo)

    assert read_sidecar_profile(team_repo) == "skills"
    assert install_sidecar(team_repo, SKILLS_SOURCE) == 0
    out = capsys.readouterr().out

    assert "installed 0, updated 0, removed 0" in out
    upgraded = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert upgraded["schema_version"] == 2 and upgraded["profile"] == "skills"
    assert _sidecar_files(team_repo, ".claude", ".agents", ".github") == files_before
    assert _status(team_repo) == status_before


def test_team_tracked_rule_with_the_sidecars_name_takes_the_rule_unit(
    team_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    team_rule = team_repo / ".claude" / "rules" / "ai-bootstrap-workflow.md"
    team_rule.write_text("The team's own workflow rule.\n", encoding="utf-8")
    _commit(
        team_repo,
        "team ships a rule with the sidecar's name",
        ".claude/rules/ai-bootstrap-workflow.md",
    )
    status_before = _status(team_repo)

    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    out = capsys.readouterr().out

    assert "SKIPPED .claude/rules/ai-bootstrap-workflow.md" in out
    assert team_rule.read_text(encoding="utf-8") == "The team's own workflow rule.\n"
    assert (team_repo / ".claude" / "rules" / "ai-bootstrap-reporting.md").is_file()
    assert "/.claude/rules/ai-bootstrap-workflow.md" not in _exclude_block(team_repo)
    assert _status(team_repo) == status_before
    assert uninstall_sidecar(team_repo) == 0
    capsys.readouterr()
    assert team_rule.read_text(encoding="utf-8") == "The team's own workflow rule.\n"
    assert _status(team_repo) == status_before


def test_team_precedence_on_review_profiles_and_templates(
    team_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Finding 7's own test gap: team precedence on
    `.claude/review-profiles/<name>.md` and `.claude/templates/<name>` had
    no coverage (only agents and rules did). Covers a tracked collision, a
    foreign (untracked, pre-existing) collision, and a deleted-but-tracked
    entry, through a dry run, a real run, a rerun, and uninstall -- byte
    content, `git status`, and the exclude block all stay exactly as the
    team left them."""
    tracked_profile = team_repo / ".claude" / "review-profiles" / "security.md"
    tracked_profile.parent.mkdir(parents=True, exist_ok=True)
    tracked_profile.write_text("team security profile\n", encoding="utf-8")
    _commit(
        team_repo,
        "team ships its own security review profile",
        ".claude/review-profiles/security.md",
    )

    foreign_template = team_repo / ".claude" / "templates" / "plan-big.md"
    foreign_template.parent.mkdir(parents=True, exist_ok=True)
    foreign_template.write_text("a stray template, not tracked\n", encoding="utf-8")

    deleted_template = team_repo / ".claude" / "templates" / "session-log.md"
    deleted_template.parent.mkdir(parents=True, exist_ok=True)
    deleted_template.write_text("team session-log template\n", encoding="utf-8")
    _commit(
        team_repo,
        "team tracks a session-log template it then deletes",
        ".claude/templates/session-log.md",
    )
    deleted_template.unlink()

    status_before = _status(team_repo)

    dry_exit = install_sidecar(
        team_repo, WORKFLOW_SOURCE, dry_run=True, profile="workflow"
    )
    dry_out = capsys.readouterr().out
    assert dry_exit == 0
    assert "SKIPPED .claude/review-profiles/security.md" in dry_out
    assert "SKIPPED .claude/templates/plan-big.md" in dry_out
    assert "SKIPPED .claude/templates/session-log.md" in dry_out
    assert _status(team_repo) == status_before
    assert tracked_profile.read_text(encoding="utf-8") == "team security profile\n"
    assert foreign_template.read_text(encoding="utf-8") == (
        "a stray template, not tracked\n"
    )
    assert not deleted_template.exists()

    exit_code = install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow")
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "SKIPPED .claude/review-profiles/security.md" in out
    assert "the repository tracks" in out
    assert "SKIPPED .claude/templates/plan-big.md" in out
    assert "the sidecar will not replace" in out
    assert "SKIPPED .claude/templates/session-log.md" in out
    assert tracked_profile.read_text(encoding="utf-8") == "team security profile\n"
    assert foreign_template.read_text(encoding="utf-8") == (
        "a stray template, not tracked\n"
    )
    assert not deleted_template.exists()
    assert (team_repo / ".claude" / "review-profiles" / "code.md").is_file()
    assert (team_repo / ".claude" / "templates" / "plan-small.md").is_file()
    assert _status(team_repo) == status_before
    block = _exclude_block(team_repo)
    assert "/.claude/review-profiles/security.md" not in block
    assert "/.claude/templates/plan-big.md" not in block
    assert "/.claude/templates/session-log.md" not in block

    # Rerun: nothing changes.
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    assert _status(team_repo) == status_before
    assert tracked_profile.read_text(encoding="utf-8") == "team security profile\n"
    assert foreign_template.read_text(encoding="utf-8") == (
        "a stray template, not tracked\n"
    )

    # Uninstall: team content, tracked or foreign, is never touched.
    assert uninstall_sidecar(team_repo) == 0
    capsys.readouterr()
    assert _status(team_repo) == status_before
    assert tracked_profile.read_text(encoding="utf-8") == "team security profile\n"
    assert foreign_template.read_text(encoding="utf-8") == (
        "a stray template, not tracked\n"
    )
    assert not deleted_template.exists()


def test_tracked_path_under_the_state_namespace_aborts_before_any_write(
    team_repo: Path,
) -> None:
    tracked = team_repo / STATE / "plans" / "team.md"
    tracked.parent.mkdir(parents=True)
    tracked.write_text("team plan\n", encoding="utf-8")
    _commit(
        team_repo, "team tracks the namespace", f"{SIDECAR_STATE_ROOT}/plans/team.md"
    )
    status_before = _status(team_repo)

    exit_code = install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow")

    assert exit_code != 0
    assert _status(team_repo) == status_before
    assert not (team_repo / ".claude" / "templates").exists()
    assert _exclude_block(team_repo) == ""


def test_git_clean_x_loses_the_state_but_the_backup_survives_and_install_reseeds(
    team_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    (team_repo / STATE / "plans" / "note.md").write_text("mine\n", encoding="utf-8")
    assert backup_sidecar_state(team_repo) == 0
    capsys.readouterr()
    backup = (
        _absolute_git_dir(team_repo)
        / "ai-bootstrap-sidecar-preserved"
        / _preserved_entries(team_repo)[0]
    )
    assert (backup / "plans" / "note.md").read_text(encoding="utf-8") == "mine\n"

    subprocess.run(["git", "-C", str(team_repo), "clean", "-fdxq"], check=True)

    assert not (team_repo / STATE).exists()
    assert (backup / "plans" / "note.md").is_file(), (
        "git clean never touches the Git directory"
    )
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    assert (team_repo / STATE / "MEMORY.md").is_file()
    assert not (team_repo / STATE / "plans" / "note.md").exists()


def test_updater_keeps_each_consumers_profile_in_a_mixed_batch(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`update_consumers.py` passes no `--profile`; each consumer is updated
    in the profile its manifest records."""
    repos: dict[str, Path] = {}
    for profile in ("skills", "workflow"):
        root = tmp_path / f"{profile}-consumer"
        _init_repo(root)
        (root / "app.py").write_text("x = 1\n", encoding="utf-8")
        _commit(root, "init")
        source = SKILLS_SOURCE if profile == "skills" else WORKFLOW_SOURCE
        assert install_sidecar(root, source, profile=profile) == 0
        repos[profile] = root
    capsys.readouterr()
    before = {
        profile: (_status(root), _sidecar_files(root, ".claude", ".agents", ".github"))
        for profile, root in repos.items()
    }

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts" / "update_consumers.py"),
            "--skip-regen",
            "--local-only",
            str(repos["skills"]),
            str(repos["workflow"]),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "--profile" not in result.stdout + result.stderr
    for profile, root in repos.items():
        assert read_sidecar_profile(root) == profile
        assert (
            _status(root),
            _sidecar_files(root, ".claude", ".agents", ".github"),
        ) == before[profile]
    assert (repos["workflow"] / STATE / "MEMORY.md").is_file()
    assert not (repos["skills"] / STATE).exists()


def test_team_agents_in_each_clients_own_file_shape_take_the_sidecars_agents(
    team_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A team keeps agents the way each client names them: Copilot as
    ``<id>.agent.md``, Codex as ``<id>.toml``, Antigravity as the folder
    ``<id>/agent.md``. Each takes the sidecar's ``.claude/agents/<id>.md``;
    a README in the same folder takes nothing."""
    team_agents = {
        ".github/agents/planner.agent.md": "team planner\n",
        ".github/agents/README.md": "about our agents\n",
        ".codex/agents/coder.toml": 'name = "coder"\n',
        ".agents/agents/documenter/agent.md": "team documenter\n",
    }
    for relative, text in team_agents.items():
        path = team_repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    _commit(team_repo, "team ships agents in client shapes", *team_agents)
    status_before = _status(team_repo)

    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    out = capsys.readouterr().out

    for taking, agent in (
        (".github/agents/planner.agent.md", "planner"),
        (".codex/agents/coder.toml", "coder"),
        (".agents/agents/documenter", "documenter"),
    ):
        assert f"SKIPPED {taking}" in out
        assert f"the sidecar skips the agent `{agent}` at every root" in out
        assert not (team_repo / ".claude" / "agents" / f"{agent}.md").exists()
    assert (team_repo / ".claude" / "agents" / "orchestrator.md").is_file()
    assert "README" not in out
    assert _status(team_repo) == status_before
    assert uninstall_sidecar(team_repo) == 0
    capsys.readouterr()
    assert _status(team_repo) == status_before


def test_team_github_coder_agent_suppresses_sidecar_coder_and_text_has_fallback(
    team_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Finding 7's own check: a team's Copilot-shaped coder agent
    (`.github/agents/coder.agent.md`) still suppresses the Claude sidecar's
    `coder` as before. Finding 6: the emitted guidance -- the orchestrator
    prompt and the shared rule -- already names what to do without one,
    regardless of whether this particular run actually loses its coder."""
    team_agent = team_repo / ".github" / "agents" / "coder.agent.md"
    team_agent.parent.mkdir(parents=True, exist_ok=True)
    team_agent.write_text("team coder\n", encoding="utf-8")
    _commit(
        team_repo, "team ships a Copilot coder agent", ".github/agents/coder.agent.md"
    )
    status_before = _status(team_repo)

    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    out = capsys.readouterr().out

    assert "SKIPPED .github/agents/coder.agent.md" in out
    assert "the sidecar skips the agent `coder` at every root" in out
    assert not (team_repo / ".claude" / "agents" / "coder.md").exists()
    assert team_agent.read_text(encoding="utf-8") == "team coder\n"
    assert _status(team_repo) == status_before

    orchestrator_text = (
        team_repo / ".claude" / "agents" / "orchestrator.md"
    ).read_text(encoding="utf-8")
    assert "implement the change yourself instead" in orchestrator_text
    rule_text = (
        team_repo / ".claude" / "rules" / "ai-bootstrap-workflow.md"
    ).read_text(encoding="utf-8")
    assert "write the plan yourself instead" in rule_text
    assert "review the diff yourself against the review profiles" in rule_text


def test_backup_state_dry_run_reports_the_copy_and_writes_nothing(
    team_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()

    assert backup_sidecar_state(team_repo, dry_run=True) == 0

    out = capsys.readouterr().out
    assert "would back up" in out
    assert _preserved_entries(team_repo) == []
    assert not (
        _absolute_git_dir(team_repo) / "ai-bootstrap-sidecar-preserved"
    ).exists()


# --------------------------------------------------------------------------
# Finding 4: safe state backup (run lock, filesystem-error handling)
# --------------------------------------------------------------------------


def test_backup_state_dry_run_is_a_byte_for_byte_no_op_through_the_cli(
    team_repo: Path,
) -> None:
    """The dry-run prediction through the public CLI, not just the
    in-process call: no lock file, no preserved folder, no state-folder
    change, nothing in the whole repository (worktree or `.git`) differs
    by a single byte."""
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    status_before = _status(team_repo)
    snapshot_before = _tree_snapshot(team_repo)

    result = subprocess.run(
        [sys.executable, str(INSTALLER), str(team_repo), "--backup-state", "--dry-run"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "would back up" in result.stdout
    assert _status(team_repo) == status_before
    assert _tree_snapshot(team_repo) == snapshot_before


def test_backup_state_with_no_state_folder_succeeds_without_a_lock(
    tmp_path: Path,
) -> None:
    """Finding 4: a target that never had the sidecar's state folder (no
    install at all, or a skills-profile install) backs up cleanly -- no
    manifest, no state, still 0 -- and never even takes the run lock."""
    root = tmp_path / "plain-repo"
    _init_repo(root)
    (root / "app.py").write_text("x = 1\n", encoding="utf-8")
    _commit(root, "init")
    status_before = _status(root)

    exit_code = backup_sidecar_state(root)

    assert exit_code == 0
    assert not (_absolute_git_dir(root) / "ai-bootstrap-sidecar.lock").exists()
    assert not (_absolute_git_dir(root) / "ai-bootstrap-sidecar-preserved").exists()
    assert _status(root) == status_before


def test_backup_state_refuses_while_another_run_holds_the_lock(
    team_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Finding 4: `backup_sidecar_state` now takes the same non-blocking
    run lock install and uninstall already do, so a concurrent run refuses
    instead of racing the copy; releasing the lock lets a normal backup
    through right after."""
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    status_before = _status(team_repo)
    lock_path = _absolute_git_dir(team_repo) / "ai-bootstrap-sidecar.lock"
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        exit_code = backup_sidecar_state(team_repo)
    finally:
        os.close(fd)

    err = capsys.readouterr().err
    assert exit_code == 1
    assert f"another sidecar run is active in {team_repo}" in err
    assert "Traceback" not in err
    assert _preserved_entries(team_repo) == []
    assert _status(team_repo) == status_before

    # The lock is released once the holder closes its handle: a normal
    # backup now succeeds.
    assert backup_sidecar_state(team_repo) == 0
    capsys.readouterr()
    assert len(_preserved_entries(team_repo)) == 1


def test_two_backups_in_one_second_do_not_collide(
    team_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()

    assert backup_sidecar_state(team_repo) == 0
    assert backup_sidecar_state(team_repo) == 0
    capsys.readouterr()

    backups = _preserved_entries(team_repo)
    assert len(backups) == 2
    assert len(set(backups)) == 2
    assert all(name.startswith("state--") for name in backups)


def test_backup_state_copy_failure_aborts_cleanly_and_leaves_no_partial_copy(
    team_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Finding 4: an `OSError` from the copy itself is a clean `ABORT:
    filesystem error at <path>: <reason>`, never a traceback, and the
    exclusively created temporary copy this run made is removed -- the
    source state folder and the preserved folder are left exactly as they
    were (no `state--<timestamp>` ever got a chance to exist)."""
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    status_before = _status(team_repo)
    state_before = _tree_snapshot(team_repo / STATE)
    preserved_root = _absolute_git_dir(team_repo) / "ai-bootstrap-sidecar-preserved"
    original_copytree = sidecar_overlay_module.shutil.copytree

    def boom_copytree(*args: object, **kwargs: object) -> None:
        raise OSError(28, "No space left on device", "/fake/full-disk")

    monkeypatch.setattr(sidecar_overlay_module.shutil, "copytree", boom_copytree)

    exit_code = backup_sidecar_state(team_repo)
    err = capsys.readouterr().err

    assert exit_code == 1
    assert "ABORT: filesystem error at /fake/full-disk: No space left on device" in err
    assert "Traceback" not in err
    assert _status(team_repo) == status_before
    assert _tree_snapshot(team_repo / STATE) == state_before
    assert not preserved_root.exists() or list(preserved_root.iterdir()) == []

    monkeypatch.setattr(sidecar_overlay_module.shutil, "copytree", original_copytree)
    assert backup_sidecar_state(team_repo) == 0
    assert len(_preserved_entries(team_repo)) == 1


def test_backup_state_rename_failure_aborts_cleanly_and_leaves_no_partial_copy(
    team_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Finding 4: the publish rename can fail too (for example a permission
    problem on the preserved folder), after a complete copy already sits in
    the temporary sibling -- that copy is removed the same way, and no
    `state--<timestamp>` folder is left half-published."""
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    status_before = _status(team_repo)
    preserved_root = _absolute_git_dir(team_repo) / "ai-bootstrap-sidecar-preserved"
    original_rename = sidecar_overlay_module.os.rename

    def boom_rename(*args: object, **kwargs: object) -> None:
        raise OSError(13, "Permission denied", "/fake/destination")

    monkeypatch.setattr(sidecar_overlay_module.os, "rename", boom_rename)

    exit_code = backup_sidecar_state(team_repo)
    err = capsys.readouterr().err

    assert exit_code == 1
    assert "ABORT: filesystem error at /fake/destination: Permission denied" in err
    assert "Traceback" not in err
    assert _status(team_repo) == status_before
    assert preserved_root.exists()
    assert list(preserved_root.iterdir()) == []

    monkeypatch.setattr(sidecar_overlay_module.os, "rename", original_rename)
    assert backup_sidecar_state(team_repo) == 0
    assert len(_preserved_entries(team_repo)) == 1


def test_backup_state_reports_the_incomplete_path_when_cleanup_itself_fails(
    team_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Finding 4: if the copy fails and removing its own partial copy also
    fails, the diagnostic still names the exact incomplete path instead of
    silently losing that information."""
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    status_before = _status(team_repo)

    def boom_copytree(*args: object, **kwargs: object) -> None:
        raise OSError(28, "No space left on device", "/fake/full-disk")

    def boom_rmtree(path: object, *args: object, **kwargs: object) -> None:
        raise OSError(13, "Permission denied", str(path))

    monkeypatch.setattr(sidecar_overlay_module.shutil, "copytree", boom_copytree)
    monkeypatch.setattr(sidecar_overlay_module.shutil, "rmtree", boom_rmtree)

    exit_code = backup_sidecar_state(team_repo)
    err = capsys.readouterr().err

    assert exit_code == 1
    assert "ABORT: filesystem error at" in err
    assert "left incomplete after" in err
    assert "No space left on device" in err
    assert "Permission denied" in err
    assert "Traceback" not in err
    assert _status(team_repo) == status_before


def test_backup_state_refuses_a_symlinked_state_folder(
    team_repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Unsafe path: the state root itself is a symlink. Reused from the
    shared preflight's own filesystem-shape check (the same one install and
    uninstall already refuse on), so this aborts before any write instead
    of silently following the link or reporting a false "nothing to back
    up"."""
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    state_dir = team_repo / STATE
    elsewhere = tmp_path / "elsewhere-state"
    state_dir.rename(elsewhere)
    state_dir.symlink_to(elsewhere, target_is_directory=True)
    status_before = _status(team_repo)

    exit_code = backup_sidecar_state(team_repo)
    err = capsys.readouterr().err

    assert exit_code == 1
    assert "symlinked skill folder or projection parent" in err
    assert "fix the filesystem shape, then rerun" in err
    assert "Traceback" not in err
    assert _preserved_entries(team_repo) == []
    assert _status(team_repo) == status_before
    assert elsewhere.is_dir()


def test_backup_state_refuses_a_symlinked_preserved_folder(
    team_repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Unsafe path: the preserved-copy folder itself is a symlink --
    reused from the same preflight install and uninstall already share, so
    this now aborts before any write instead of copying through the link."""
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    preserved_root = _absolute_git_dir(team_repo) / "ai-bootstrap-sidecar-preserved"
    elsewhere = tmp_path / "elsewhere-preserved"
    elsewhere.mkdir()
    preserved_root.symlink_to(elsewhere, target_is_directory=True)
    status_before = _status(team_repo)

    exit_code = backup_sidecar_state(team_repo)
    err = capsys.readouterr().err

    assert exit_code == 1
    assert f"{preserved_root} is a symlink or not a folder" in err
    assert "Traceback" not in err
    assert _status(team_repo) == status_before
    assert list(elsewhere.iterdir()) == []


# --------------------------------------------------------------------------
# Finding 1: relocate sidecar state and migrate owned legacy state
# --------------------------------------------------------------------------


def test_legacy_state_migrates_byte_for_byte_with_edits_and_extra_files(
    team_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Fresh-legacy-to-new migration: an edited ``MEMORY.md`` and an extra
    personal file both survive the move byte-for-byte, a complete backup
    of the legacy folder lands in the preserved-copy folder first, the
    legacy exclude line is replaced by the new root's, and team files and
    `git status` never change."""
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    memory_path = team_repo / STATE / "MEMORY.md"
    memory_path.write_text(
        memory_path.read_text(encoding="utf-8") + "\n- personal lesson\n",
        encoding="utf-8",
    )
    (team_repo / STATE / "plans" / "my-plan.md").write_text(
        "# my plan\n", encoding="utf-8"
    )
    legacy_dir = _move_state_to_legacy_root(team_repo)
    legacy_bytes = {
        str(p.relative_to(legacy_dir)): p.read_bytes()
        for p in legacy_dir.rglob("*")
        if p.is_file()
    }
    status_before = _status(team_repo)
    team_before = _team_bytes(team_repo)

    exit_code = install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow")
    out = capsys.readouterr().out

    assert exit_code == 0
    assert f"moved {legacy_dir} -> {team_repo / STATE}" in out
    assert not legacy_dir.exists()
    assert (team_repo / STATE).is_dir()
    migrated_bytes = {
        str(p.relative_to(team_repo / STATE)): p.read_bytes()
        for p in (team_repo / STATE).rglob("*")
        if p.is_file()
    }
    assert migrated_bytes == legacy_bytes
    assert "personal lesson" in (team_repo / STATE / "MEMORY.md").read_text(
        encoding="utf-8"
    )
    assert (team_repo / STATE / "plans" / "my-plan.md").read_text(
        encoding="utf-8"
    ) == "# my plan\n"
    backups = _preserved_entries(team_repo)
    assert len(backups) == 1
    backup_dir = (
        _absolute_git_dir(team_repo) / "ai-bootstrap-sidecar-preserved" / backups[0]
    )
    backup_bytes = {
        str(p.relative_to(backup_dir)): p.read_bytes()
        for p in backup_dir.rglob("*")
        if p.is_file()
    }
    assert backup_bytes == legacy_bytes
    assert _status(team_repo) == status_before
    assert _team_bytes(team_repo) == team_before
    block = _exclude_block(team_repo)
    assert f"/{SIDECAR_STATE_ROOT}\n" in block
    assert f"/{SIDECAR_LEGACY_STATE_ROOT}\n" not in block


def test_legacy_state_migration_dry_run_predicts_and_writes_nothing(
    team_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    legacy_dir = _move_state_to_legacy_root(team_repo)
    status_before = _status(team_repo)
    snapshot_before = _tree_snapshot(team_repo)

    exit_code = install_sidecar(
        team_repo, WORKFLOW_SOURCE, dry_run=True, profile="workflow"
    )
    out = capsys.readouterr().out

    assert exit_code == 0
    assert f"would back up {legacy_dir}" in out
    assert f"would move {legacy_dir} -> {team_repo / STATE}" in out
    # Finding 3: a migration dry run never claims the backup or the move
    # already happened.
    assert "moved " not in out
    assert "backed up " not in out
    assert _status(team_repo) == status_before
    assert _tree_snapshot(team_repo) == snapshot_before


def test_legacy_state_retained_with_no_manifest_still_migrates(
    team_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The retained-state-only exclude block a plain ``--uninstall`` leaves
    behind is ownership evidence on its own, with no manifest at all (a
    state unit is never recorded in one anyway)."""
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    (team_repo / STATE / "plans" / "keep-me.md").write_text(
        "kept across uninstall\n", encoding="utf-8"
    )
    legacy_dir = _move_state_to_legacy_root(team_repo)
    assert uninstall_sidecar(team_repo) == 0
    capsys.readouterr()
    assert not _manifest_path(team_repo).exists()
    assert legacy_dir.is_dir()

    exit_code = install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow")

    assert exit_code == 0
    assert not legacy_dir.exists()
    assert (team_repo / STATE / "plans" / "keep-me.md").read_text(
        encoding="utf-8"
    ) == "kept across uninstall\n"


@pytest.mark.parametrize("schema_version", (1, 2), ids=("schema-1", "schema-2"))
def test_legacy_state_migrates_regardless_of_manifest_schema_version(
    team_repo: Path, capsys: pytest.CaptureFixture[str], schema_version: int
) -> None:
    """A state unit is never recorded in the manifest, so migration does
    not care whether the *other* units' manifest is schema 1 or 2."""
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    legacy_dir = _move_state_to_legacy_root(team_repo)
    manifest_path = _manifest_path(team_repo)
    manifest = _read_manifest(team_repo)
    manifest["schema_version"] = schema_version
    if schema_version == 1:
        del manifest["profile"]
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    exit_code = install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow")

    assert exit_code == 0
    assert not legacy_dir.exists()
    assert (team_repo / STATE / "MEMORY.md").is_file()


def test_both_state_roots_present_refuses_before_any_write(
    team_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    legacy_dir = team_repo / LEGACY_STATE
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "old.txt").write_text("old copy\n", encoding="utf-8")
    status_before = _status(team_repo)
    snapshot_before = _tree_snapshot(team_repo)

    exit_code = install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow")
    err = capsys.readouterr().err

    assert exit_code == 1
    assert f"both {legacy_dir}" in err
    assert str(team_repo / STATE) in err
    assert "back up both folders" in err
    assert "--mode" not in err
    assert _status(team_repo) == status_before
    assert _tree_snapshot(team_repo) == snapshot_before


def test_unowned_legacy_folder_refuses_and_is_never_claimed(
    team_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A real ``.claude/ai-bootstrap`` folder with no recognized exclude
    entry is left alone, not silently adopted as migratable state, the
    same way an unrecognized legacy full install is left alone (finding 2's
    own "do not claim the folder" principle, applied here to state)."""
    legacy_dir = team_repo / LEGACY_STATE
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "unrelated.txt").write_text("not the sidecar's\n", encoding="utf-8")
    status_before = _status(team_repo)

    exit_code = install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow")
    err = capsys.readouterr().err

    assert exit_code == 1
    assert f"{legacy_dir} exists" in err
    assert "does not list it" in err
    assert "will not claim" in err
    assert _status(team_repo) == status_before
    assert (legacy_dir / "unrelated.txt").read_text(encoding="utf-8") == (
        "not the sidecar's\n"
    )


def test_tracked_legacy_state_aborts_before_any_write(
    team_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    legacy_dir = _move_state_to_legacy_root(team_repo)
    tracked_file = legacy_dir / "plans" / "team.md"
    tracked_file.write_text("team tracks this\n", encoding="utf-8")
    # -f: the legacy root is already hidden by its own exclude line, so an
    # ordinary `git add` would refuse it as ignored; forcing the add is
    # exactly how a team member tracking it by mistake would do it too.
    add = subprocess.run(
        [
            "git",
            "-C",
            str(team_repo),
            "add",
            "-f",
            "--",
            f"{SIDECAR_LEGACY_STATE_ROOT}/plans/team.md",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert add.returncode == 0, add.stderr
    _commit_staged(team_repo, "team tracks the legacy namespace")
    status_before = _status(team_repo)

    exit_code = install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow")
    err = capsys.readouterr().err

    assert exit_code != 0
    assert "tracks" in err
    assert _status(team_repo) == status_before
    assert not (team_repo / STATE).exists()


def test_symlinked_legacy_root_aborts_before_any_write(
    team_repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    legacy_dir = _move_state_to_legacy_root(team_repo)
    elsewhere = tmp_path / "elsewhere-legacy"
    legacy_dir.rename(elsewhere)
    legacy_dir.symlink_to(elsewhere, target_is_directory=True)
    status_before = _status(team_repo)

    exit_code = install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow")
    err = capsys.readouterr().err

    assert exit_code != 0
    assert "symlinked skill folder or projection parent" in err
    assert _status(team_repo) == status_before
    assert elsewhere.is_dir()


def test_symlinked_descendant_inside_legacy_state_migrates_as_a_symlink(
    team_repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A symlink a person left inside their own state folder (not
    something the sidecar ever creates) is carried through the migration
    as a symlink, never followed and copied as the target's content."""
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    link_target = tmp_path / "outside-note.md"
    link_target.write_text("outside content\n", encoding="utf-8")
    (team_repo / STATE / "plans" / "linked.md").symlink_to(link_target)
    legacy_dir = _move_state_to_legacy_root(team_repo)

    exit_code = install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow")

    assert exit_code == 0
    migrated_link = team_repo / STATE / "plans" / "linked.md"
    assert migrated_link.is_symlink()
    assert os.readlink(migrated_link) == str(link_target)
    backups = _preserved_entries(team_repo)
    backup_link = (
        _absolute_git_dir(team_repo)
        / "ai-bootstrap-sidecar-preserved"
        / backups[0]
        / "plans"
        / "linked.md"
    )
    assert backup_link.is_symlink()
    assert os.readlink(backup_link) == str(link_target)
    assert not legacy_dir.exists()


def test_negated_new_root_fails_the_ignore_gate_and_restores_exclude(
    team_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    legacy_dir = _move_state_to_legacy_root(team_repo)
    exclude_path = _exclude_path(team_repo)
    exclude_before = exclude_path.read_bytes()
    gitignore = team_repo / ".gitignore"
    gitignore.write_text(f"!/{SIDECAR_STATE_ROOT}\n", encoding="utf-8")
    _commit(team_repo, "team un-ignores the new state root", ".gitignore")
    status_before = _status(team_repo)

    exit_code = install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow")
    err = capsys.readouterr().err

    assert exit_code != 0
    assert "ignore gate failed" in err
    assert exclude_path.read_bytes() == exclude_before
    assert _status(team_repo) == status_before
    assert legacy_dir.is_dir()
    assert not (team_repo / STATE).exists()


def test_migration_fault_after_backup_rerun_converges(
    team_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    legacy_dir = _move_state_to_legacy_root(team_repo)

    monkeypatch.setattr(
        sidecar_overlay_module, "_fault_point", _raise_at("after_legacy_state_backup")
    )
    with pytest.raises(RuntimeError, match="after_legacy_state_backup"):
        install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow")
    capsys.readouterr()

    # Pre-rerun state: the legacy folder is untouched (the rename never
    # ran), and one backup already exists.
    assert legacy_dir.is_dir()
    assert len(_preserved_entries(team_repo)) == 1

    monkeypatch.setattr(sidecar_overlay_module, "_fault_point", lambda name: None)
    exit_code = install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow")

    assert exit_code == 0
    assert not legacy_dir.exists()
    assert (team_repo / STATE / "MEMORY.md").is_file()


def test_migration_fault_after_rename_rerun_converges_without_remigrating(
    team_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    legacy_dir = _move_state_to_legacy_root(team_repo)

    monkeypatch.setattr(
        sidecar_overlay_module, "_fault_point", _raise_at("after_legacy_state_rename")
    )
    with pytest.raises(RuntimeError, match="after_legacy_state_rename"):
        install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow")
    capsys.readouterr()

    # Pre-rerun state: the move already happened; the rest of this run's own
    # reconciliation never started, so the manifest is still the first
    # install's own, untouched by this attempt.
    assert not legacy_dir.exists()
    assert (team_repo / STATE / "MEMORY.md").is_file()
    assert _manifest_path(team_repo).is_file()

    manifest_before_rerun = _read_manifest(team_repo)
    monkeypatch.setattr(sidecar_overlay_module, "_fault_point", lambda name: None)
    exit_code = install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow")
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "sidecar-install: moved " not in out, (
        "a rerun must never re-migrate already-moved state"
    )
    assert len(_preserved_entries(team_repo)) == 1
    manifest = _read_manifest(team_repo)
    assert len(manifest["units"]) == len(manifest_before_rerun["units"])


def test_migration_fault_during_reconciliation_rerun_converges(
    team_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A failure in the ordinary reconciliation that runs right after a
    successful migration is the existing crash-recovery machinery's own
    job, not a new one: this reuses the existing ``before_manifest_write``
    fault point to prove it."""
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    legacy_dir = _move_state_to_legacy_root(team_repo)

    monkeypatch.setattr(
        sidecar_overlay_module, "_fault_point", _raise_at("before_manifest_write")
    )
    with pytest.raises(RuntimeError, match="before_manifest_write"):
        install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow")
    capsys.readouterr()

    # The migration itself (the move) already landed; only the ordinary
    # reconciliation that runs right after it -- not the migration -- hit
    # this fault, so the real manifest is still this run's *pending* one,
    # not yet promoted (N8), while the first install's real manifest file
    # on disk is the one `before_manifest_write` fires just before
    # replacing.
    assert not legacy_dir.exists()
    assert _manifest_path(team_repo).is_file()
    manifest_before_rerun = _read_manifest(team_repo)

    monkeypatch.setattr(sidecar_overlay_module, "_fault_point", lambda name: None)
    exit_code = install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow")

    assert exit_code == 0
    manifest = _read_manifest(team_repo)
    assert len(manifest["units"]) == len(manifest_before_rerun["units"])


def test_legacy_state_survives_a_skills_profile_switch_untouched(
    team_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Keep legacy state on skills-only updates: the skills profile has no
    state root at all, so migration never applies, and the legacy folder
    is kept hidden exactly like the current root already is."""
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    legacy_dir = _move_state_to_legacy_root(team_repo)
    legacy_bytes_before = {
        str(p.relative_to(legacy_dir)): p.read_bytes()
        for p in legacy_dir.rglob("*")
        if p.is_file()
    }

    assert install_sidecar(team_repo, SKILLS_SOURCE, profile="skills") == 0
    capsys.readouterr()

    assert legacy_dir.is_dir()
    legacy_bytes_after = {
        str(p.relative_to(legacy_dir)): p.read_bytes()
        for p in legacy_dir.rglob("*")
        if p.is_file()
    }
    assert legacy_bytes_after == legacy_bytes_before
    assert f"/{SIDECAR_LEGACY_STATE_ROOT}\n" in _exclude_block(team_repo)

    # Switching back to workflow migrates it, same as any other rerun.
    exit_code = install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow")
    assert exit_code == 0
    assert not legacy_dir.exists()
    assert (team_repo / STATE / "MEMORY.md").is_file()


def test_uninstall_and_purge_handle_both_recognized_roots_independently(
    team_repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Explicit purge preserves either recognized root to a backup, and
    backup recognizes both: proven here with both roots present at once
    (an edge case install always refuses, but uninstall/backup must still
    handle safely, each to its own distinct destination)."""
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    capsys.readouterr()
    legacy_dir = team_repo / LEGACY_STATE
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "old.txt").write_text("old copy\n", encoding="utf-8")
    (team_repo / STATE / "new.txt").write_text("new copy\n", encoding="utf-8")

    assert uninstall_sidecar(team_repo) == 0
    out = capsys.readouterr().out
    assert "RETAINED .ai-bootstrap" in out
    assert "RETAINED .claude/ai-bootstrap" in out
    assert legacy_dir.is_dir()
    assert (team_repo / STATE).is_dir()

    exit_code = uninstall_sidecar(team_repo, purge_state=True)
    out = capsys.readouterr().out

    assert exit_code == 0
    assert "PRESERVED .ai-bootstrap ->" in out
    assert "PRESERVED .claude/ai-bootstrap ->" in out
    backups = _preserved_entries(team_repo)
    assert len(backups) == 2
    preserved_root = _absolute_git_dir(team_repo) / "ai-bootstrap-sidecar-preserved"
    contents = {
        backup: sorted(p.name for p in (preserved_root / backup).iterdir())
        for backup in backups
    }
    assert {"old.txt"} in (set(names) for names in contents.values())
    assert any("new.txt" in names for names in contents.values())
    assert not legacy_dir.exists()
    assert not (team_repo / STATE).exists()

    # Reinstall reseeds a fresh current-root state only; the legacy root
    # stays gone (it was purged, not retained).
    assert install_sidecar(team_repo, WORKFLOW_SOURCE, profile="workflow") == 0
    assert (team_repo / STATE / "MEMORY.md").is_file()
    assert not (team_repo / LEGACY_STATE).exists()


def test_unit_name_keeps_only_the_part_before_the_first_dot() -> None:
    assert (
        _unit_name(".github/instructions/ai-bootstrap-workflow.instructions.md")
        == "ai-bootstrap-workflow"
    )
    assert _unit_name(".claude/agents/reviewer.md") == "reviewer"
    assert (
        _unit_name(".claude/rules/ai-bootstrap-workflow.md") == "ai-bootstrap-workflow"
    )
