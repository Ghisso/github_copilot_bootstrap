"""Regression coverage for Phase F3.3/F3.4: the protected-file literal
extractor's token boundaries, and repository-scoping the control-plane
alternatives while keeping the secret-shaped ones global.

Steps F3.3 and F3.4 land their tests here instead of extending
``tests/test_hook_gates.py``, because another coder edits that file in
parallel for the rest of Phase F3 (see the small plan's "Test-file
deviation" note).
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_hook_gates import SCRIPT_SRC, _run_protect_files  # noqa: E402


def _load_protect_files_module() -> ModuleType:
    """Load ``protect-files.py`` as an importable module.

    The script's hyphenated filename is not a valid module name, so it
    cannot be reached with a plain ``import``. This gives the table-driven
    extractor tests below direct access to ``protected_path_literals``
    without duplicating its regex.
    """
    spec = importlib.util.spec_from_file_location(
        "protect_files_under_test", SCRIPT_SRC / "protect-files.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROTECT_FILES = _load_protect_files_module()


def _run_protect_files_with_repo_root(
    payload: dict, repo_root: str
) -> subprocess.CompletedProcess[str]:
    """Invoke ``protect-files.py`` directly with an explicit REPO_ROOT
    string, bypassing ``protect-files.sh``'s ``repo_root_from_script()``
    computation (which can never itself produce an empty string) so the
    empty-``repo_root`` fail-closed case can be exercised.
    """
    return subprocess.run(
        ["python3", str(SCRIPT_SRC / "protect-files.py"), "openai-codex", repo_root],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )


def _denied(process: subprocess.CompletedProcess[str]) -> bool:
    assert process.returncode == 0, process.stderr
    return '"permissionDecision":"deny"' in process.stdout


def _allowed(process: subprocess.CompletedProcess[str]) -> bool:
    assert process.returncode == 0, process.stderr
    return process.stdout.strip() == ""


# --------------------------------------------------------------------------
# Step F3.3 - table-driven boundary coverage for every PROTECTED_PATH_LITERAL
# alternative: one string each alternative must still match, one near-miss
# it must no longer match.
# --------------------------------------------------------------------------

_LITERAL_MUST_MATCH = (
    # (input text, expected extracted literal). `.env` and friends are not
    # given a directory-prefix-capturing group (only the three control-plane
    # alternatives are, per F3.4), so a leading `foo/` is not part of the
    # extracted literal - the alternative still matches, it just does not
    # carry the prefix along.
    pytest.param(".env", ".env", id="env-bare"),
    pytest.param(".env.local", ".env.local", id="env-dotted-suffix"),
    pytest.param("foo/.env.production", ".env.production", id="env-directory-prefix"),
    pytest.param("uv.lock", "uv.lock", id="uv-lock-bare"),
    pytest.param("credentials.json", "credentials.json", id="credentials-dot-suffix"),
    pytest.param(
        "credentials-prod.json", "credentials-prod.json", id="credentials-hyphen-suffix"
    ),
    pytest.param("server.key", "server.key", id="key-bare"),
    pytest.param("cert.pem", "cert.pem", id="pem-bare"),
)


@pytest.mark.parametrize("text, expected", _LITERAL_MUST_MATCH)
def test_protected_path_literal_still_matches_real_references(
    text: str, expected: str
) -> None:
    assert PROTECT_FILES.protected_path_literals(text) == [expected]


_LITERAL_MUST_NOT_MATCH = (
    pytest.param("os.environ", id="env-left-boundary-word"),
    pytest.param(".environment", id="env-right-boundary-word"),
    pytest.param("myuv.lock", id="uv-lock-left-boundary"),
    pytest.param("uv.lockfile", id="uv-lock-right-boundary"),
    pytest.param("mycredentials.json", id="credentials-left-boundary"),
    pytest.param("bundle.keys", id="key-right-boundary"),
)


@pytest.mark.parametrize("text", _LITERAL_MUST_NOT_MATCH)
def test_protected_path_literal_rejects_embedded_near_misses(text: str) -> None:
    assert PROTECT_FILES.protected_path_literals(text) == []


def test_protect_files_allows_python_heredoc_referencing_os_environ() -> None:
    """Phase F reproduction: a bare Bash heredoc was denied merely because
    its text contained ``os.environ``, extracting a false ``.env`` candidate
    from the middle of that word. Fails on the pre-change tree."""
    command = "python3 - <<'PY'\nimport os\nfor key in os.environ:\n    print(key)\nPY"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert _allowed(process), process.stdout


def test_protect_files_allows_echo_mentioning_env_as_a_word_fragment() -> None:
    """An unbounded ``.env`` alternative also extracted a false candidate
    out of a longer filename mentioned in ordinary message text. Fails on
    the pre-change tree."""
    command = 'echo "Reading development.env values"'
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert _allowed(process), process.stdout


@pytest.mark.parametrize(
    "command",
    (
        "touch .env",
        "touch /tmp/other/.env",
        "rm config/service.pem",
    ),
)
def test_protect_files_still_blocks_real_mutation_targets(command: str) -> None:
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert _denied(process), process.stdout


# --------------------------------------------------------------------------
# Step F3.4 - repository-scope the control-plane alternatives, keep the
# secret-shaped ones global.
# --------------------------------------------------------------------------

_CONTROL_PLANE_RELATIVE_PATHS = (
    pytest.param(".claude/settings.json", id="claude-settings"),
    pytest.param(".codex/config.toml", id="codex-config"),
    pytest.param(".codex/hooks.json", id="codex-hooks"),
    pytest.param(".github/hooks/hooks.json", id="github-hooks-config"),
    pytest.param(".claude/hooks/run-hook.sh", id="claude-hooks-dir"),
)


@pytest.mark.parametrize("relative_path", _CONTROL_PLANE_RELATIVE_PATHS)
def test_protect_files_allows_outside_control_plane_names(
    relative_path: str, tmp_path: Path
) -> None:
    """`rm <outside>/<control-plane name>` is allowed: the same name in a
    foreign checkout is that checkout's own control plane, not this
    repository's. Fails on the pre-change tree."""
    repo_root = tmp_path / "repo"
    outside = tmp_path / "outside"
    outside.mkdir(parents=True)
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": f"rm {outside / relative_path}"},
        },
        repo_root,
    )
    assert _allowed(process), process.stdout


@pytest.mark.parametrize("relative_path", _CONTROL_PLANE_RELATIVE_PATHS)
def test_protect_files_denies_in_repository_control_plane_names(
    relative_path: str, tmp_path: Path
) -> None:
    """The same names, addressed absolutely inside this repository, are
    still denied: this is the in-repository half of the before/after pair
    for defect 2(b)."""
    repo_root = tmp_path / "repo"
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": f"rm {repo_root / relative_path}"},
        },
        repo_root,
    )
    assert _denied(process), process.stdout


def test_protect_files_denies_bare_relative_control_plane_name(tmp_path: Path) -> None:
    """A bare relative ``.claude/settings.json`` in a mutating command keeps
    its current meaning: repository-local, still denied."""
    repo_root = tmp_path / "repo"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": "rm .claude/settings.json"}},
        repo_root,
    )
    assert _denied(process), process.stdout


@pytest.mark.parametrize(
    "basename",
    (
        pytest.param(".env", id="env"),
        pytest.param("uv.lock", id="uv-lock"),
        pytest.param("id_rsa.key", id="key"),
        pytest.param("credentials.json", id="credentials"),
    ),
)
def test_protect_files_still_blocks_secret_shaped_names_outside_repo(
    basename: str, tmp_path: Path
) -> None:
    """Proof that a credential-shaped filename outside this repository stays
    protected: the secret-shaped clause is unconditionally global and must
    not be narrowed by the new containment predicate."""
    repo_root = tmp_path / "repo"
    outside = tmp_path / "outside"
    outside.mkdir(parents=True)
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": f"rm {outside / basename}"}},
        repo_root,
    )
    assert _denied(process), process.stdout


def test_protect_files_allows_symlink_inside_repo_pointing_outside(
    tmp_path: Path,
) -> None:
    """A symlink physically inside this repository, whose real target is a
    foreign control-plane file, is allowed: removing the link does not
    touch the foreign file, and the link's own resolved location is outside
    this repository."""
    repo_root = tmp_path / "repo"
    outside = tmp_path / "outside" / ".claude"
    outside.mkdir(parents=True)
    target = outside / "settings.json"
    target.write_text("{}", encoding="utf-8")
    repo_root.mkdir(parents=True, exist_ok=True)
    link = repo_root / "link.json"
    link.symlink_to(target)
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": f"rm {link}"}}, repo_root
    )
    assert _allowed(process), process.stdout


def test_protect_files_denies_symlink_outside_repo_pointing_inside(
    tmp_path: Path,
) -> None:
    """A symlink physically outside this repository, whose real target is
    this repository's own control-plane file, is denied: the resolved
    target lands inside this repository."""
    repo_root = tmp_path / "repo" / ".claude"
    repo_root.mkdir(parents=True)
    target = repo_root / "settings.json"
    target.write_text("{}", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir(parents=True)
    link = outside / "link.json"
    link.symlink_to(target)
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": f"rm {link}"}},
        tmp_path / "repo",
    )
    assert _denied(process), process.stdout


def test_protect_files_allows_dotdot_traversal_that_resolves_outside(
    tmp_path: Path,
) -> None:
    """``..`` traversal is collapsed by ``realpath`` before the containment
    test: a path that textually starts inside this repository but actually
    escapes it is allowed."""
    repo_root = tmp_path / "repo"
    (repo_root / "x").mkdir(parents=True)
    outside = tmp_path / "outside" / ".claude"
    outside.mkdir(parents=True)
    command = f"rm {repo_root}/x/../../{outside.parent.name}/.claude/settings.json"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}, repo_root
    )
    assert _allowed(process), process.stdout


def test_protect_files_denies_dotdot_traversal_that_resolves_inside(
    tmp_path: Path,
) -> None:
    """The reverse traversal, textually starting outside this repository
    but actually landing inside it, is still denied."""
    repo_root = tmp_path / "repo"
    outside = tmp_path / "outside"
    outside.mkdir(parents=True)
    command = f"rm {outside}/../{repo_root.name}/.claude/settings.json"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}, repo_root
    )
    assert _denied(process), process.stdout


def test_protect_files_denies_unresolvable_variable_reference(tmp_path: Path) -> None:
    """An unresolved shell variable inside an otherwise control-plane-shaped
    path cannot be proven to resolve outside this repository, so it stays
    denied (fail closed)."""
    repo_root = tmp_path / "repo"
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": 'rm "$UNKNOWN_DIR/.claude/settings.json"'},
        },
        repo_root,
    )
    assert _denied(process), process.stdout


def test_protect_files_denies_control_plane_name_with_empty_repo_root() -> None:
    """An empty ``repo_root`` argument cannot support a containment
    decision, so it makes every candidate in-repository."""
    process = _run_protect_files_with_repo_root(
        {"tool_name": "Bash", "tool_input": {"command": "rm .claude/settings.json"}},
        "",
    )
    assert _denied(process), process.stdout


def test_protect_files_allows_read_only_cat_of_control_plane_file(
    tmp_path: Path,
) -> None:
    """A read-only ``cat`` of a protected configuration remains allowed,
    matching the contract in ``docs/smoke-tests.md``."""
    repo_root = tmp_path / "repo"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": "cat .claude/settings.json"}},
        repo_root,
    )
    assert _allowed(process), process.stdout


def test_protect_files_denies_repo_root_physical_path_when_repo_root_is_symlinked(
    tmp_path: Path,
) -> None:
    """Reviewer-reported CRITICAL: `REPO_ROOT` is resolved with a plain
    ``cd && pwd`` (`repo_root_from_script`), which preserves a symlinked
    path component instead of resolving it (the macOS `/tmp` ->
    `/private/tmp` case, also a symlinked home directory or mount). A
    command that names an in-repository control-plane file by its physical
    path, while `REPO_ROOT` is the symlinked logical path, must still be
    denied - not read as outside the repository because only one of the two
    paths' forms was compared. Fails on the pre-fix tree."""
    real_root = tmp_path / "real"
    (real_root / ".claude").mkdir(parents=True)
    link_root = tmp_path / "link"
    link_root.symlink_to(real_root, target_is_directory=True)
    other = tmp_path / "other" / ".claude"
    other.mkdir(parents=True)

    # (a) the symlinked (logical) prefix, matching REPO_ROOT's own form.
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": f"rm {link_root}/.claude/settings.json"},
        },
        link_root,
    )
    assert _denied(process), process.stdout

    # (b) the physical (realpath) prefix - the reported bypass.
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": f"rm {real_root}/.claude/settings.json"},
        },
        link_root,
    )
    assert _denied(process), process.stdout

    # (c) a genuinely unrelated directory stays allowed.
    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": f"rm {other}/settings.json"},
        },
        link_root,
    )
    assert _allowed(process), process.stdout


def test_protect_files_denies_symlinked_path_when_repo_root_is_physical(
    tmp_path: Path,
) -> None:
    """Mirror of the reviewer-reported case: `REPO_ROOT` is the physical
    (realpath) form, and the command names the file through a symlinked
    (logical) prefix pointing at the same directory. Still denied."""
    real_root = tmp_path / "real"
    (real_root / ".claude").mkdir(parents=True)
    link_root = tmp_path / "link"
    link_root.symlink_to(real_root, target_is_directory=True)

    process = _run_protect_files(
        {
            "tool_name": "Bash",
            "tool_input": {"command": f"rm {link_root}/.claude/settings.json"},
        },
        real_root,
    )
    assert _denied(process), process.stdout


def test_protect_files_allows_bash_command_naming_absolute_foreign_settings(
    tmp_path: Path,
) -> None:
    """Phase F reproduction: a Bash heredoc naming an absolute foreign
    ``.claude/settings.json`` path in opaque prose text is allowed. A bare
    (no ``-c``) ``python3`` heredoc body is scanned by the literal extractor
    only, exercising the whole-token capture fix directly rather than the
    separate per-argument path check an unknown command's own operands also
    go through."""
    repo_root = tmp_path / "repo"
    outside = tmp_path / "scratch" / ".claude"
    outside.mkdir(parents=True)
    command = (
        f"python3 - <<'PY'\n# Config drift detected at {outside}/settings.json\nPY"
    )
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}, repo_root
    )
    assert _allowed(process), process.stdout
