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

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from runtime_ownership import (  # noqa: E402
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
from sidecar_test_helpers import _absolute_git_dir, _commit, _init_repo, _status  # noqa: E402

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
    capsys.readouterr()
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
    assert "kept .claude/ai-bootstrap and its exclude line" in dry
    assert uninstall_sidecar(team_repo) == 0
    out = capsys.readouterr().out
    assert (
        "kept .claude/ai-bootstrap and its exclude line; pass --purge-state to remove it"
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
    capsys.readouterr()
    assert plan.is_file()
    assert uninstall_sidecar(team_repo, purge_state=True) == 0
    out = capsys.readouterr().out
    assert "PRESERVED .claude/ai-bootstrap" in out
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


def test_unit_name_keeps_only_the_part_before_the_first_dot() -> None:
    assert (
        _unit_name(".github/instructions/ai-bootstrap-workflow.instructions.md")
        == "ai-bootstrap-workflow"
    )
    assert _unit_name(".claude/agents/reviewer.md") == "reviewer"
    assert (
        _unit_name(".claude/rules/ai-bootstrap-workflow.md") == "ai-bootstrap-workflow"
    )
