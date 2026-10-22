"""Regression coverage for Phase F3.3/F3.4: the protected-file literal
extractor's token boundaries, and repository-scoping the control-plane
alternatives while keeping the secret-shaped ones global. Phase H adds the
Bash-scanner cases at the end of the file.

Steps F3.3 and F3.4 land their tests here instead of extending
``tests/test_hook_gates.py``, because another coder edits that file in
parallel for the rest of Phase F3 (see the small plan's "Test-file
deviation" note).
"""

from __future__ import annotations

import importlib.util
import json
import signal
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_hook_gates import (  # noqa: E402
    CLIENT_CONFIG_DECISIONS,
    REPO_ROOT,
    SCRIPT_SRC,
    _client_bash_payload,
    _protect_decision,
    _run_protect_files,
)


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
    pytest.param("x.pem", "x.pem", id="pem-short-name"),
    pytest.param("a/b.key", "b.key", id="key-after-a-directory"),
    pytest.param('"x.pem"', "x.pem", id="pem-quoted"),
    pytest.param("x.pem,y.key", "x.pem,y.key", id="pem-then-key-in-one-word"),
    pytest.param(".mcp.json", ".mcp.json", id="mcp-bare"),
    pytest.param("/repo/.mcp.json", "/repo/.mcp.json", id="mcp-directory-prefix"),
    pytest.param(".vscode/mcp.json", ".vscode/mcp.json", id="vscode-mcp"),
    pytest.param(
        ".vscode/settings.json", ".vscode/settings.json", id="vscode-settings"
    ),
    pytest.param(".agents/hooks.json", ".agents/hooks.json", id="antigravity-hooks"),
    pytest.param(
        ".agents/mcp_config.json", ".agents/mcp_config.json", id="antigravity-mcp"
    ),
    pytest.param(
        ".claude/settings.local.json",
        ".claude/settings.local.json",
        id="claude-local-settings",
    ),
    pytest.param(
        ".github/copilot/settings.local.json",
        ".github/copilot/settings.local.json",
        id="copilot-local-settings",
    ),
    pytest.param(".claude/agents/coder.md", ".claude/agents/coder.md", id="agent-file"),
    pytest.param(".claude/agents", ".claude/agents", id="agent-folder-bare"),
    pytest.param(
        "/repo/.agents/agents/coder/agent.md",
        "/repo/.agents/agents/coder/agent.md",
        id="antigravity-agent-directory-prefix",
    ),
    pytest.param(".claude/hooks", ".claude/hooks", id="hook-folder-bare"),
    pytest.param("team.code-workspace", "team.code-workspace", id="workspace-file"),
    pytest.param(
        "Team.CODE-WORKSPACE", "Team.CODE-WORKSPACE", id="workspace-file-mixed-case"
    ),
    pytest.param(
        "/repo/team.code-workspace",
        "/repo/team.code-workspace",
        id="workspace-file-directory-prefix",
    ),
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
    pytest.param("x.pem.bak", id="pem-then-more-name"),
    pytest.param("foo.mcp.json", id="mcp-left-boundary"),
    pytest.param("my-.mcp.json", id="mcp-left-boundary-hyphen"),
    pytest.param("vscode/mcp.json", id="vscode-mcp-needs-leading-dot"),
    pytest.param("other.vscode/settings.json", id="vscode-settings-left-boundary"),
    pytest.param("shared/agents/coder/prompt.md", id="bootstrap-source-agents"),
    pytest.param(".claude/agents-old/x.md", id="agents-right-boundary-hyphen"),
    pytest.param(".claude/agentsx", id="agents-right-boundary-word"),
    pytest.param("x.claude/agents/y.md", id="agents-left-boundary"),
    pytest.param(".agents/skills/ponytail/SKILL.md", id="skill-folder"),
    pytest.param("team.code-workspaces", id="workspace-right-boundary"),
)


@pytest.mark.parametrize("text", _LITERAL_MUST_NOT_MATCH)
def test_protected_path_literal_rejects_embedded_near_misses(text: str) -> None:
    assert PROTECT_FILES.protected_path_literals(text) == []


@pytest.mark.parametrize(
    "relative_path",
    (
        ".claude/settings.local.json",
        ".agents/hooks.json",
        ".mcp.json",
        ".vscode/mcp.json",
        ".agents/mcp_config.json",
        ".vscode/settings.json",
        ".github/copilot/settings.json",
        ".github/copilot/settings.local.json",
        ".claude/agents/coder.md",
        ".agents/agents/coder/agent.md",
        "team.code-workspace",
        "Team.CODE-WORKSPACE",
    ),
)
def test_protect_files_finds_hook_and_server_configs_in_opaque_shell_text(
    relative_path: str,
) -> None:
    """An interpreter string that names one of these configs is caught by the
    literal extractor, the same way it catches the earlier hook configs."""
    command = f"bash -c 'cat {relative_path} > /tmp/out'"
    process = _run_protect_files(
        {"tool_name": "Bash", "tool_input": {"command": command}}
    )
    assert _denied(process), process.stdout


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
    pytest.param(".claude/settings.local.json", id="claude-local-settings"),
    pytest.param(".agents/hooks.json", id="antigravity-hooks"),
    pytest.param(".mcp.json", id="claude-mcp"),
    pytest.param(".vscode/mcp.json", id="copilot-mcp"),
    pytest.param(".agents/mcp_config.json", id="antigravity-mcp"),
    pytest.param(".vscode/settings.json", id="vscode-settings"),
    pytest.param(".github/copilot/settings.json", id="copilot-settings"),
    pytest.param(".github/copilot/settings.local.json", id="copilot-local-settings"),
    pytest.param(".claude/agents/coder.md", id="claude-agent"),
    pytest.param(".codex/agents/reviewer.toml", id="codex-agent"),
    pytest.param(".github/agents/planner.agent.md", id="copilot-agent"),
    pytest.param(".agents/agents/coder/agent.md", id="antigravity-agent"),
    pytest.param(".claude/agents", id="claude-agents-folder"),
    pytest.param(".claude/hooks", id="claude-hooks-folder"),
    pytest.param("team.code-workspace", id="workspace-file"),
    pytest.param("Team.CODE-WORKSPACE", id="workspace-file-mixed-case"),
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


# --------------------------------------------------------------------------
# Phase H - the Bash scanner. `split_segments` reads shell text with Bash's
# own quoting, escape, comment, and newline rules instead of Python's `shlex`
# after turning every newline into `;`. Every expected value below was
# checked against Bash itself, once, in a scratch harness outside the
# repository: `bash --norc -c` with PATH stand-ins (a `tee`, `touch`, or `rm`
# that only prints its arguments) in a temporary directory, never against this
# classifier. These tests never run Bash. A `.env` that Bash passes to a
# mutator, or redirects into, is a write target.
# --------------------------------------------------------------------------


def _scan(command: str) -> tuple[list[str], list[str]]:
    """``shell_targets`` for ``command`` against the real checkout."""
    return PROTECT_FILES.shell_targets(command, str(REPO_ROOT))


_QUOTED_OPERATOR_WORDS = (
    pytest.param("'|'", id="single-quoted-pipe"),
    pytest.param("';'", id="single-quoted-semicolon"),
    pytest.param("'&&'", id="single-quoted-and"),
    pytest.param("'||'", id="single-quoted-or"),
    pytest.param("'&'", id="single-quoted-ampersand"),
    pytest.param("'('", id="single-quoted-paren"),
    pytest.param('"|"', id="double-quoted-pipe"),
    pytest.param("'|''|'", id="two-quoted-pipes"),
    pytest.param("''\\|", id="empty-quotes-then-escaped-pipe"),
    pytest.param("\\|", id="escaped-pipe"),
    pytest.param("\\;", id="escaped-semicolon"),
    pytest.param("'\n'", id="quoted-newline"),
)


@pytest.mark.parametrize("word", _QUOTED_OPERATOR_WORDS)
def test_scanner_reads_a_quoted_or_escaped_operator_as_a_plain_word(word: str) -> None:
    """Bash passes the operator character to `tee` as a file name, so `cat`
    and `.env` are operands of the same command. Fails on the `shlex` guard,
    which splits the command at the quoted operator and loses `.env`."""
    confirmed, uncertain = _scan(f"tee {word} cat .env")
    assert len(confirmed) == 3, (confirmed, uncertain)
    assert confirmed[1:] == ["cat", ".env"]


_SCANNER_DENY_CASES = (
    pytest.param("# step 1\ntee .env", id="comment-line-then-tee"),
    pytest.param("ls # note\ntee .env", id="trailing-comment-then-tee"),
    pytest.param("echo hi # note\nrm .env", id="echo-comment-then-rm"),
    pytest.param("cat README.md\n\ntouch .env", id="blank-line-then-touch"),
    pytest.param("grep -n x README.md\n\nrm .env", id="blank-line-then-rm"),
    pytest.param("git status\n\ngit restore .env", id="blank-line-then-git-restore"),
    pytest.param("cat x;\ntee .env", id="semicolon-line-end"),
    pytest.param("cat x &\ntee .env", id="ampersand-line-end"),
    pytest.param("cat x |\ntee .env", id="pipe-line-end"),
    pytest.param("cat x &&\ntee .env", id="and-line-end"),
    pytest.param("cat <<EOF &&\nbody\nEOF\ntouch .env", id="heredoc-then-and-line-end"),
    pytest.param("cat x#y; tee .env", id="hash-inside-a-word-then-semicolon"),
    pytest.param("cat x#y\ntee .env", id="hash-inside-a-word-then-newline"),
    pytest.param("cat 'a'#b; tee .env", id="hash-after-a-quoted-part"),
    pytest.param("cat ${X}#y; tee .env", id="hash-after-an-expansion"),
    pytest.param("echo ${#X}; tee .env", id="length-expansion"),
    pytest.param("cat $# ; tee .env", id="argument-count"),
    pytest.param("cat x\\\\\ntee .env", id="escaped-backslash-before-newline"),
    pytest.param("cat a\\\n#b; tee .env", id="continuation-then-hash-word"),
    pytest.param("cat $'\\'' ; tee .env ; cat \\'", id="ansi-c-escaped-quote"),
    pytest.param("cat \\' <(tee .env)", id="escaped-quote-before-process-sub"),
    pytest.param("cat \\' <(tee .env) \\'", id="escaped-quotes-around-process-sub"),
    pytest.param(
        "cat \\' '<<EOF' \\'\ntee .env\nEOF", id="escaped-quote-before-quoted-heredoc"
    ),
    pytest.param('tee "|cat $Y" .env', id="quoted-operator-with-a-variable"),
    pytest.param('tee "a\nb" cat .env', id="newline-inside-double-quotes"),
    pytest.param('tee "a\\"|" cat .env', id="escaped-quote-inside-double-quotes"),
    pytest.param("tee a$'|'b cat .env", id="ansi-c-pipe-inside-a-word"),
    pytest.param("tee '&&' x && tee .env", id="quoted-and-then-real-and"),
    pytest.param('echo "$(echo ")")" ; tee .env', id="nested-quotes-in-substitution"),
    pytest.param("tee a\\ #b cat .env", id="escaped-space-then-hash"),
    pytest.param("echo \\;#x; tee .env", id="escaped-semicolon-then-hash"),
    pytest.param("cat <<< '|' ; tee .env", id="here-string-with-quoted-pipe"),
    pytest.param("echo hi # <<EOF\ntee .env\nEOF", id="heredoc-operator-in-comment"),
    pytest.param(
        "echo \\\\\n# <<EOF\ntee .env\nEOF", id="comment-after-escaped-backslash"
    ),
    pytest.param("ls # don't\ncat <(tee .env)", id="apostrophe-in-comment"),
    pytest.param("cat x # <(ls)\ncat <(tee .env)", id="process-sub-in-comment"),
    # A run of operator characters is split into Bash's operators, so a group
    # that follows one is still read as a command of its own.
    pytest.param("cat x;(tee .env)", id="semicolon-then-group"),
    pytest.param("cat x&&(tee .env)", id="and-then-group"),
    pytest.param("cat x||(tee .env)", id="or-then-group"),
    pytest.param("cat x|(tee .env)", id="pipe-then-group"),
    pytest.param("cat x&(tee .env)", id="ampersand-then-group"),
    pytest.param("cat x ;(cd docs;tee .env);cat y", id="group-inside-a-list"),
    # An operator after `)` and a `)` on its own line must not hide the command
    # inside the substitution or group.
    pytest.param("cat $(tee .env) && ls", id="substitution-write-then-and"),
    pytest.param("(tee .env) && ls", id="group-write-then-and"),
    pytest.param("ls && (tee .env)", id="and-then-group-write"),
    pytest.param("echo $(date) && tee .env", id="substitution-then-and-write"),
    pytest.param("(ls) && tee .env", id="group-then-and-write"),
    pytest.param("echo $(tee .env) | cat", id="substitution-write-then-pipe"),
    pytest.param("(ls) | tee .env", id="group-then-pipe-write"),
    pytest.param("(\n  cd docs\n  tee .env\n)", id="multi-line-group-write"),
    pytest.param("x=$(\n  tee .env\n)", id="multi-line-substitution-write"),
    pytest.param("f() { tee .env; }; f", id="function-definition-write"),
    # An unquoted `$( )` or `$(( ))` is part of its word: the words after it are
    # operands, not a new command name that nothing checks.
    pytest.param("tee $((1)) .env", id="arithmetic-then-operand"),
    pytest.param("tee $(echo $(date)) .env", id="nested-substitution-then-operand"),
    pytest.param("tee $(true) .env", id="substitution-then-operand"),
    pytest.param(
        "rm $(git rev-parse --show-toplevel)/.env", id="substitution-then-path-suffix"
    ),
    pytest.param("echo x > $(pwd)/.env", id="redirect-to-substitution-path"),
    pytest.param("tee x$(true)y .env", id="substitution-inside-a-word"),
    # A substitution glued to a protected name may expand to nothing.
    pytest.param("tee .env$(true)", id="name-then-substitution"),
    pytest.param("tee $(true).env", id="substitution-then-name"),
    pytest.param("rm .env$( $(true) )", id="name-then-nested-substitution"),
    pytest.param("echo x > .env$(true)", id="redirect-to-name-then-substitution"),
    pytest.param("cp x .env$(true)$(true)", id="name-then-two-substitutions"),
    pytest.param("tee $(echo a) $(echo b) .env", id="two-substitutions"),
    pytest.param("tee $(( $(echo 1) + 2 )) .env", id="substitution-inside-arithmetic"),
    pytest.param("echo $((1<<2)); tee .env", id="arithmetic-shift-then-write"),
    pytest.param("tee $(cat <<EOF\nx\nEOF\n) .env", id="heredoc-in-substitution"),
    pytest.param("echo $(date)#; tee .env", id="hash-after-substitution"),
    pytest.param("cat <(echo hi)#c; tee .env", id="hash-after-process-sub"),
    pytest.param("echo $((1+2))#c; tee .env", id="hash-after-arithmetic"),
    # `\r` is an ordinary word character; only space, tab, and newline are blanks.
    pytest.param("echo a\r#b; tee .env", id="carriage-return-then-hash"),
    pytest.param("echo a\r; tee .env", id="carriage-return-then-semicolon"),
    # Parentheses inside quotes do not end a word, with or without a variable.
    pytest.param('tee "$X(" cat .env', id="quoted-open-paren-and-variable"),
    pytest.param('tee "$X)" cat .env', id="quoted-close-paren-and-variable"),
    pytest.param("tee '$X(' cat .env", id="single-quoted-paren-and-variable"),
    pytest.param('tee "(a $X)" cat .env', id="quoted-parens-around-a-variable"),
    pytest.param("tee ')' .env", id="quoted-close-paren-before-the-operand"),
    pytest.param("tee \\) .env", id="escaped-close-paren-before-the-operand"),
    # `$"..."` is a double-quoted string with the `$` dropped.
    pytest.param('tee $".env"', id="locale-quoted-name"),
    pytest.param('tee $"a|b" cat .env', id="locale-quoted-pipe"),
    pytest.param('tee $"a $X" cat .env', id="locale-quoted-variable"),
    # An array assignment is one word, so what follows it is read as usual.
    pytest.param("a=(x y); tee .env", id="array-assignment-then-write"),
    pytest.param("a=(x)b#c; tee .env", id="array-then-glued-word-with-hash"),
    pytest.param("a=(x y)\ntee .env", id="array-then-newline-write"),
    pytest.param("a=($(tee .env))", id="array-element-substitution"),
    # An unresolved variable glued to a protected name may be empty.
    pytest.param("tee .env$X", id="name-then-variable"),
    pytest.param("tee $X.env", id="variable-then-name"),
    pytest.param("tee ${X}.env", id="braced-variable-then-name"),
    pytest.param("tee .env${X}", id="name-then-braced-variable"),
    pytest.param('tee "$X".env', id="quoted-variable-then-name"),
    pytest.param('tee .env"$X"', id="name-then-quoted-variable"),
    pytest.param("echo x > .env$X", id="redirect-to-name-then-variable"),
    pytest.param("rm $A$B.env", id="two-variables-then-name"),
    # The name is only a name next to the `}` of a variable that stays in the
    # text, and a substitution is glued after it: strip each one separately.
    pytest.param("foo x\r#y${X}.env$(true)", id="variable-name-then-substitution"),
    # A `${ }` is one unit up to its own `}`: a `)` or a quote or a `#` inside it
    # ends nothing outside it. Bash runs the `tee` in every one of these.
    pytest.param("cat $(tee ${x//)/} .env)", id="paren-in-expansion-in-cat-subst"),
    pytest.param("git status $(tee ${x//)/} .env)", id="paren-in-expansion-git-status"),
    pytest.param("x=$(tee ${x:-)} .env)", id="paren-in-default-in-assignment"),
    pytest.param("cat <(tee ${x//)/} .env)", id="paren-in-expansion-in-process-sub"),
    pytest.param("tee >(tee ${x//)/} .env)", id="paren-in-expansion-in-output-sub"),
    pytest.param("a=($(tee ${x//)/} .env))", id="paren-in-expansion-in-array-subst"),
    pytest.param(
        "cat <<EOF\n$(tee ${x//)/} .env)\nEOF", id="paren-in-expansion-in-heredoc-subst"
    ),
    pytest.param("cat $(echo $(tee ${x:-)} .env))", id="paren-in-default-nested-subst"),
    pytest.param("cat ${y:-$(tee ${x:-)} .env)}", id="paren-in-default-in-default"),
    pytest.param("tee ${y//) cat /} .env", id="paren-and-words-in-pattern-top-level"),
    pytest.param("rm ${x:-)} .env", id="paren-in-default-top-level"),
    pytest.param("cat $(echo ${x:-)}; tee .env)", id="paren-in-default-then-write"),
    pytest.param("tee ${x%)} .env", id="paren-in-suffix-pattern"),
    pytest.param("tee ${x#)} .env", id="paren-in-prefix-pattern"),
    pytest.param("tee ${x:-(} .env", id="open-paren-in-default"),
    pytest.param("cat $(tee ${x:-(} .env)", id="open-paren-in-default-in-subst"),
    pytest.param("echo ${x:- #}; tee .env", id="hash-in-expansion-is-not-a-comment"),
    pytest.param("echo ${x:-a #b}; tee .env", id="hash-word-in-expansion"),
    pytest.param("echo ${x:- #}\ntee .env", id="hash-in-expansion-then-newline"),
    pytest.param("tee ${x:-${y:-)}} .env", id="nested-expansion-with-paren"),
    pytest.param("tee ${x:-${y//)/}} .env", id="nested-expansion-pattern-paren"),
    pytest.param('tee "${x:-)}" .env', id="quoted-expansion-with-paren"),
    pytest.param('tee "${x:-"a)"}" .env', id="quotes-inside-quoted-expansion"),
    pytest.param("tee ${x//\\}/} .env", id="escaped-brace-in-pattern"),
    pytest.param('tee ${x//"}"/} .env', id="quoted-brace-in-pattern"),
    pytest.param("tee ${x//'}'/} .env", id="single-quoted-brace-in-pattern"),
    pytest.param("tee ${x:-$'}'} .env", id="ansi-c-brace-in-default"),
    pytest.param("tee ${x:-$(echo ))} .env", id="substitution-with-paren-in-default"),
    pytest.param("tee ${x:-`echo )`} .env", id="backticks-with-paren-in-default"),
    pytest.param("tee ${x:-}} .env", id="empty-default-then-brace"),
    pytest.param("tee ${x:-$(tee .env)}", id="write-in-the-default-word"),
    pytest.param("a=(${x//)/}); tee .env", id="array-element-with-expansion-paren"),
    pytest.param(
        "a=($(a=(${x:-)}); tee .env))", id="array-in-subst-with-expansion-paren"
    ),
    # A `${ }` of any kind may expand to nothing, or to its default word, so a
    # protected name next to one, or inside its default, is still a name.
    pytest.param("tee .env${x//)/}", id="name-then-pattern-expansion"),
    pytest.param("rm > .env${x//)/}", id="redirect-to-name-then-pattern-expansion"),
    pytest.param("tee .env${x:-}", id="name-then-empty-default"),
    pytest.param("tee ${x//)/}.env", id="pattern-expansion-then-name"),
    pytest.param('tee "${X:-.env}"', id="name-in-a-quoted-default"),
    pytest.param("tee .e${x:-n}v", id="default-completes-the-name"),
    pytest.param("tee ${x:-.env}", id="name-in-a-default"),
    pytest.param("touch ${x:+.env}", id="name-in-an-alternative"),
    pytest.param("tee ${x:-${y:-.env}}", id="name-in-a-nested-default"),
    pytest.param("echo x > ${x:-.env}", id="redirect-to-a-default-name"),
    pytest.param("cp a ${X:=.env}", id="assign-default-name-as-destination"),
    pytest.param("tee ${x:- .env}", id="blank-then-name-in-a-default"),
    pytest.param("tee '${x:-a}'.env", id="single-quoted-expansion-then-name"),
    # `$$` is the process id, so `{` after it opens nothing.
    pytest.param("echo $${x:- ; tee .env ; : }", id="pid-then-brace-then-semicolon"),
    pytest.param("echo $$$${x:- ; tee .env ; : }", id="two-pids-then-brace"),
    # A `)` in backticks in a substitution does not close the substitution.
    pytest.param("cat $(tee `echo )` .env)", id="paren-in-backticks-in-subst"),
    pytest.param("cat $(echo `echo )`; tee .env)", id="paren-in-backticks-then-write"),
    pytest.param("cat <(tee `echo )` .env)", id="paren-in-backticks-in-process-sub"),
    pytest.param("a=($(tee `echo )` .env))", id="paren-in-backticks-in-array-subst"),
    # A substitution in the folder of a `cd` or `git -C` still reaches the file.
    pytest.param(
        "cd $(git rev-parse --show-toplevel)/.claude/hooks && tee x.sh",
        id="cd-to-a-substitution-path-then-write",
    ),
    pytest.param(
        "cd $(git rev-parse --show-toplevel) && tee .env",
        id="cd-to-a-substitution-then-write",
    ),
    pytest.param(
        "git -C $(git rev-parse --show-toplevel)/.claude restore hooks/x.sh",
        id="git-c-substitution-path-then-restore",
    ),
    # A modelled mutator with a quoted glob names that literal file.
    pytest.param("rm 'credentials*'", id="remove-a-quoted-glob-name"),
    pytest.param("rm '*.pem'", id="remove-a-quoted-pem-glob"),
    pytest.param("touch 'credentials*'", id="touch-a-quoted-glob-name"),
)


@pytest.mark.parametrize("command", _SCANNER_DENY_CASES)
def test_scanner_finds_the_write_target_in_every_hidden_form(command: str) -> None:
    """A protected `.env` is a confirmed target, or an uncertain one (`git restore`
    is an unmodelled subcommand): either way the hook denies. The path may carry
    a substitution placeholder in front (`$(pwd)/.env`)."""
    confirmed, uncertain = _scan(command)
    assert any(
        PROTECT_FILES.protected(path, str(REPO_ROOT)) for path in confirmed + uncertain
    )


def test_scanner_gives_the_protected_config_decision_for_a_quoted_operator() -> None:
    confirmed, _uncertain = _scan("tee '&&' cat .claude/settings.json")
    assert ".claude/settings.json" in confirmed


_SCANNER_ALLOW_CASES = (
    pytest.param(
        "printf 'x|y\\n' | grep '|' | head -1", id="quoted-pipes-in-a-pipeline"
    ),
    pytest.param("find . -exec grep x {} \\; | head -1", id="find-exec-then-pipe"),
    pytest.param("grep ';' README.md | head -1", id="quoted-semicolon"),
    pytest.param("grep '>' README.md", id="quoted-redirect-sign"),
    pytest.param("grep '>' .env", id="quoted-redirect-sign-reading-env"),
    pytest.param("cat '2>' .env", id="quoted-fd-redirect-reading-env"),
    pytest.param(
        "git commit -m \"$(cat <<'EOF'\nFix: it works (really)\nEOF\n)\"",
        id="commit-message-heredoc-in-double-quotes",
    ),
    pytest.param(
        "git commit -m \"$(cat <<'EOF'\nFix: don't break it\nEOF\n)\"",
        id="commit-message-heredoc-with-an-apostrophe",
    ),
    pytest.param("ls # don't", id="apostrophe-in-comment"),
    pytest.param("cat a &&\n\ncat b", id="blank-lines-after-and"),
    pytest.param("(cd docs && ls)", id="leading-group"),
    pytest.param("(cd docs && ls) # note", id="comment-after-a-group"),
    pytest.param(
        "# Show the state\n"
        "git status\n"
        "\n"
        "# Then look around   (it's fine)\n"
        "ls -la docs # trailing note\n"
        "\n"
        "cat README.md | head -5 &&\n"
        "grep -n 'a|b' README.md\n",
        id="multi-line-read-only-with-comments-and-blank-lines",
    ),
    pytest.param("cat .env", id="plain-read-of-a-secret-file"),
    pytest.param("ls | head", id="plain-pipeline"),
    # An operator right after `)`.
    pytest.param("echo $(date) && ls", id="substitution-then-and"),
    pytest.param("(cd docs && ls) && ls", id="group-then-and"),
    pytest.param(
        "cd $(git rev-parse --show-toplevel) && ls", id="toplevel-substitution-then-and"
    ),
    pytest.param("echo $(date) &&\nls", id="substitution-then-and-line-end"),
    pytest.param("echo $(date) | cat", id="substitution-then-pipe"),
    pytest.param("echo $(date); ls", id="substitution-then-semicolon"),
    pytest.param("echo $(date) |\nls", id="substitution-then-pipe-line-end"),
    pytest.param("echo $(date) &\nls", id="substitution-then-ampersand-line-end"),
    pytest.param("echo $(echo $(date)) && ls", id="nested-substitution-then-and"),
    pytest.param("echo $((1+2)) && ls", id="arithmetic-then-and"),
    pytest.param("(ls) | cat", id="group-then-pipe"),
    # A `)` on its own line, or after a `;`.
    pytest.param("(\n  cd docs\n  ls\n)", id="multi-line-group"),
    pytest.param("( ls; )", id="group-closed-after-semicolon"),
    pytest.param("echo $(\n  date\n)", id="multi-line-substitution"),
    pytest.param("(\n  cd docs\n  ls\n) && ls", id="multi-line-group-then-and"),
    # Forms that already read right keep reading right.
    pytest.param("f() { echo hi; }; f", id="function-definition"),
    pytest.param("((i++))", id="arithmetic-command"),
    pytest.param("case x in (a) ls ;; esac", id="case-with-a-leading-paren"),
    # An unquoted `$( )` stays inside its word.
    pytest.param("ls $(pwd)/docs", id="substitution-then-path-suffix"),
    pytest.param("echo $((1+2))", id="arithmetic"),
    pytest.param("echo $((1<<2))", id="arithmetic-shift"),
    pytest.param("echo a$(date)b", id="substitution-inside-a-word"),
    pytest.param("echo $(date)#note", id="hash-after-substitution"),
    # After a group's `)` a `#` starts a comment (the `; tee .env` is text).
    pytest.param("(echo hi)#c; tee .env", id="comment-after-a-subshell"),
    pytest.param("((1))#c; tee .env", id="comment-after-an-arithmetic-command"),
    pytest.param("x=$(date); ls", id="assignment-from-substitution"),
    pytest.param('echo "$(date)"', id="double-quoted-substitution"),
    pytest.param('cat "$(echo "$(echo hi)")"', id="nested-double-quoted-substitution"),
    pytest.param("echo $(echo $(echo $(date)))", id="three-nested-substitutions"),
    # Ordinary characters that look like syntax.
    pytest.param("echo a\rb", id="carriage-return-inside-a-word"),
    pytest.param("grep -E '(a|b)' README.md", id="quoted-parens"),
    pytest.param('echo "$HOME(" ")"', id="quoted-parens-and-a-variable"),
    pytest.param('echo $"hello"', id="locale-quoted-word"),
    # An array assignment: the `)` ends the list, then the word goes on.
    pytest.param("a=(x y); echo ok", id="array-assignment"),
    pytest.param("a=(\n  x\n  y\n)\necho ok", id="multi-line-array-assignment"),
    pytest.param("a+=(x y); echo ok", id="array-append"),
    pytest.param("declare -a a=(x y); echo ok", id="declared-array"),
    # A variable that may be empty is not a protected name unless it is glued
    # to one; a read of a secret file is allowed in any form.
    pytest.param("echo $HOME", id="plain-variable"),
    pytest.param("ls $X/docs", id="variable-then-folder"),
    pytest.param("cat .env$X", id="read-name-then-variable"),
    pytest.param("cat $X.env", id="read-variable-then-name"),
    # A quoted glob is a pattern for an unknown command (`find`, `ls`), not the
    # name of a file it writes.
    pytest.param("find . -name '*.pem'", id="find-a-quoted-pem-glob"),
    pytest.param('find . -name "credentials*"', id="find-a-quoted-credentials-glob"),
    pytest.param("ls '*.key'", id="list-a-quoted-key-glob"),
    # Text that is not the word `case` read by Bash is not refused: quoted or
    # escaped text, a comment, a longer word, and a `case` that is a value.
    pytest.param('echo $(echo "case a in a) b;; esac")', id="case-text-in-quotes"),
    pytest.param("echo $(echo \\case x)", id="escaped-case-word"),
    pytest.param("echo $(echo showcase x)", id="word-ending-in-case"),
    pytest.param("echo $(echo case_study x)", id="word-starting-with-case"),
    pytest.param("echo $(echo case-insensitive x)", id="hyphenated-case-word"),
    pytest.param("echo $(echo x=case y)", id="case-as-an-assignment-value"),
    pytest.param("echo $(echo case)", id="case-last-in-the-substitution"),
    pytest.param("echo $(echo x # case a in a) b;; esac\n)", id="case-in-a-comment"),
    pytest.param('echo "case a in a) b;; esac"', id="case-text-in-a-top-level-string"),
    pytest.param("echo $(date) case a in", id="case-after-a-closed-substitution"),
    # Ordinary parameter expansions, and `)` or `}` or a quote inside one.
    pytest.param("echo ${X:-default}", id="default-expansion"),
    pytest.param("echo ${x//a/b}", id="replace-expansion"),
    pytest.param("echo ${#X}", id="length-expansion-read"),
    pytest.param('echo "${X}"', id="quoted-expansion"),
    pytest.param("ls ${X:-docs}/x", id="expansion-then-path"),
    pytest.param("echo ${x:-a b}", id="default-with-a-space"),
    pytest.param("echo ${x:-)}", id="paren-default-top-level"),
    pytest.param("cat $(echo ${x//)/})", id="paren-pattern-in-substitution"),
    pytest.param("echo $(echo ${x:-)} RAN)", id="paren-default-in-substitution"),
    pytest.param("a=(${x:-)}); echo ok", id="paren-default-in-array"),
    pytest.param("echo $$ $$$$", id="process-ids"),
    pytest.param('echo ${x:-"}"}', id="quoted-brace-in-default"),
    pytest.param("cat ${y:-$(echo a)}", id="substitution-in-default"),
    pytest.param("echo ${x//\\}/}", id="escaped-brace-pattern"),
    pytest.param("echo ${x:-}}", id="empty-default-then-literal-brace"),
    pytest.param("echo ${x:- ) ; ( }", id="operators-inside-a-default"),
    pytest.param(
        "echo ${x:-$(echo )) ( )}", id="parens-in-a-substitution-in-a-default"
    ),
    pytest.param("echo $${x}", id="pid-then-braces"),
    # A quoted `${ }` without a single quote in it, and a quote outside it or in a
    # nested command, are read as before.
    pytest.param('echo "${X:-default}"', id="quoted-default"),
    pytest.param('echo "${x//a/b}"', id="quoted-replace"),
    pytest.param('echo "${#X}"', id="quoted-length"),
    pytest.param('echo "it\'s ${x}"', id="apostrophe-outside-the-expansion"),
    pytest.param("echo \"${x:-$(echo 'a')}\"", id="quote-in-a-nested-command"),
    pytest.param('echo "${x:-"a b"}"', id="double-quotes-nested-in-a-default"),
    pytest.param("echo ${x:-'a}'}", id="unquoted-expansion-with-quotes-read-as-bash"),
    pytest.param("cat ${X:-.env}", id="read-a-default-name"),
    pytest.param("echo ${HOME:-/tmp}/a", id="default-path"),
    pytest.param("echo $(echo `echo )`)", id="paren-in-backticks-harmless"),
    # An extended glob that does not name a file the guard guards is read-only here.
    pytest.param("ls @(a|b)", id="extglob-in-a-read"),
    pytest.param("echo '@(a|b)' '*(x)'", id="quoted-extglob"),
)


@pytest.mark.parametrize("command", _SCANNER_ALLOW_CASES)
def test_scanner_reports_no_target_for_read_only_commands(command: str) -> None:
    assert _scan(command) == ([], [])


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("tee ${x:-out.txt}", id="write-to-a-default-name"),
        pytest.param("tee ${x:-a}/${y:-b}", id="write-to-two-defaults"),
        pytest.param("rm ${x:-a b}", id="remove-a-default-with-a-blank"),
        pytest.param("tee ${x//)/} out.txt", id="write-after-a-pattern-expansion"),
    ),
)
def test_scanner_finds_no_protected_name_in_a_write_with_an_expansion(
    command: str,
) -> None:
    """A write is a target, but none of the names it may expand to is protected."""
    confirmed, uncertain = _scan(command)
    assert confirmed
    assert not any(
        PROTECT_FILES.protected(path, str(REPO_ROOT)) for path in confirmed + uncertain
    )


_SCANNER_UNCHANGED_DENY_CASES = (
    pytest.param("echo hi | tee .env", id="pipe-to-tee"),
    pytest.param("tee .env", id="plain-tee"),
    pytest.param("cmd > .env", id="redirect"),
    pytest.param("cat x 3>> .env", id="fd-append"),
    pytest.param("cat x 2>&1 > .env", id="fd-duplicate-then-redirect"),
    pytest.param("cat x &> .env", id="redirect-both"),
    pytest.param("{ cat x; tee .env; }", id="brace-group"),
    pytest.param("case a in a) tee .env;; esac", id="case-statement"),
    pytest.param("tee $'|' cat .env", id="ansi-c-pipe"),
    pytest.param('tee "\\|" cat .env', id="double-quoted-escaped-pipe"),
    pytest.param("tee a'|'b cat .env", id="quoted-pipe-inside-a-word"),
    pytest.param("cat $(tee .env)", id="command-substitution"),
    pytest.param("eval 'tee .env'", id="eval"),
    pytest.param("bash -c 'tee .env'", id="bash-c"),
    pytest.param("bash -c 'printf x > .env; echo *'", id="bash-c-script-with-a-glob"),
    pytest.param("sh -c 'tee .env; ls ?'", id="sh-c-script-with-a-glob"),
    pytest.param("echo .env | xargs tee", id="xargs"),
    pytest.param("find . -name .env -exec rm {} \\;", id="find-exec-rm"),
    pytest.param("find . -name .env -exec tee {} +", id="find-exec-tee"),
    # A case statement in a group or at the top level is read as before.
    pytest.param("( case a in a) tee .env;; esac )", id="case-in-a-subshell-group"),
    pytest.param("{ case a in a) tee .env;; esac; }", id="case-in-a-brace-group-cmd"),
    pytest.param("true && case a in a) tee .env;; esac", id="case-after-and"),
    # An interpreter or a wrapper runs or passes on the quoted text, so it is
    # never a pattern. `bash -c` and `eval` read the brace list again and run
    # `rm` on the protected name; `xargs` and `python3` do not, but they are in
    # the same list on purpose (an over-block there costs less than a hole).
    pytest.param("bash -c '{rm,.env}'", id="bash-c-brace-list"),
    pytest.param("eval '{rm,.env}'", id="eval-brace-list"),
    pytest.param("sudo bash -c '{rm,.env}'", id="sudo-bash-c-brace-list"),
    pytest.param("timeout 5 sh -c '{rm,.env}'", id="timeout-sh-c-brace-list"),
    pytest.param("xargs '{rm,.env}'", id="xargs-brace-list"),
    pytest.param("python3 -c '{rm,.env}'", id="python-brace-list"),
    pytest.param("nohup eval '{rm,.env}'", id="nohup-eval-brace-list"),
)


@pytest.mark.parametrize("command", _SCANNER_UNCHANGED_DENY_CASES)
def test_scanner_keeps_todays_target_for_commands_that_already_denied(
    command: str,
) -> None:
    """Confirmed (a mutation mechanism) or uncertain (`eval`, `bash -c`, `xargs`,
    `find -exec`): either way `.env` is reported and the hook denies."""
    confirmed, uncertain = _scan(command)
    assert ".env" in confirmed + uncertain


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("find . -name '*.pem' -delete", id="find-delete-by-glob"),
        pytest.param("find . -name '*.key' -exec rm {} +", id="find-exec-by-glob"),
    ),
)
def test_scanner_denies_find_that_deletes_what_a_quoted_glob_matches(
    command: str,
) -> None:
    """The guard before Phase H read a quoted glob as an opaque word, so a
    `find` with one reported no target. `find` acts on every match of the
    pattern, and these patterns match protected names (Phase I)."""
    confirmed, uncertain = _scan(command)
    assert any(
        PROTECT_FILES.protected(path, str(REPO_ROOT)) for path in confirmed + uncertain
    )


def test_scanner_marks_a_word_that_is_one_quoted_glob_as_a_pattern() -> None:
    """Only a word that is a single quoted glob is a pattern; a quoted glob glued
    to other text, or a quoted variable, keeps the plain quoted-value marker."""
    pattern = PROTECT_FILES.QUOTED_PATTERN_PREFIX
    value = PROTECT_FILES.QUOTED_VALUE_PREFIX
    assert PROTECT_FILES.split_segments("ls '*.key'") == [["ls", pattern + "*.key"]]
    assert PROTECT_FILES.split_segments('ls "a?"') == [["ls", pattern + "a?"]]
    # A brace list is not a pattern: `find -name '{a,b}'` never expands it.
    assert PROTECT_FILES.split_segments("ls '{a,b}'") == [["ls", value + "{a,b}"]]
    assert PROTECT_FILES.split_segments("ls x'*'") == [["ls", "x*"]]
    assert PROTECT_FILES.split_segments("ls '*'.env") == [["ls", value + "*.env"]]
    assert PROTECT_FILES.split_segments('ls "$X"*.env') == [["ls", value + "$X*.env"]]
    assert PROTECT_FILES.split_segments('ls "$X"') == [["ls", value + "$X"]]
    # A quoted script or sentence that holds a glob is not a pattern.
    for text in ("a b*", "echo x; echo *", "x>*", "a'b*", "a\\b*"):
        quote = '"' if "'" in text else "'"
        words = PROTECT_FILES.split_segments("bash -c " + quote + text + quote)
        assert words == [["bash", "-c", value + text]], text


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("find . '*'.env", id="find-a-quoted-glob-glued-to-a-name"),
        pytest.param('ls "$X"*.env', id="list-a-quoted-variable-then-a-glob"),
        pytest.param("find . -name .env -delete", id="find-delete-by-name"),
        pytest.param("find . -name '{a,b}.pem'", id="find-a-quoted-brace-list"),
        # An interpreter or wrapper does not get the exemption, even for a star.
        pytest.param("bash -c '*.pem'", id="bash-c-a-quoted-glob"),
        pytest.param("eval '*.key'", id="eval-a-quoted-glob"),
        pytest.param("xargs 'credentials*'", id="xargs-a-quoted-glob"),
        pytest.param("python3 -c '*.pem'", id="python-a-quoted-glob"),
        pytest.param("/usr/bin/env bash -c '*.pem'", id="env-bash-a-quoted-glob"),
        pytest.param("nohup find . -name '*.pem'", id="nohup-find-a-quoted-glob"),
        pytest.param("timeout 5 find . -name '*.pem'", id="timeout-find-a-quoted-glob"),
    ),
)
def test_scanner_still_checks_a_word_that_is_not_only_a_quoted_glob(
    command: str,
) -> None:
    confirmed, uncertain = _scan(command)
    assert any(
        PROTECT_FILES.protected(path, str(REPO_ROOT)) for path in confirmed + uncertain
    )


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("cat x |& tee .env", id="pipe-and"),
        pytest.param("cat x &>> .env", id="both-append"),
        pytest.param("cat x >& .env", id="duplicate-redirect"),
        pytest.param("cat x <> .env", id="read-write"),
    ),
)
def test_scanner_finds_the_write_behind_a_grouped_operator(command: str) -> None:
    """Bash writes `.env` here: `|&` pipes into `tee`; `&>>`, `>&`, and `<>` open
    it."""
    confirmed, uncertain = _scan(command)
    assert ".env" in confirmed + uncertain


@pytest.mark.parametrize(
    "command, error, message",
    (
        pytest.param(
            "| head",
            "AmbiguousCommand",
            "empty shell command segment",
            id="leading-pipe",
        ),
        pytest.param(
            "a && && b",
            "AmbiguousCommand",
            "empty shell command segment",
            id="double-and",
        ),
        pytest.param(
            "echo $(date) && && ls",
            "AmbiguousCommand",
            "empty shell command segment",
            id="double-and-after-subst",
        ),
        pytest.param(
            "ls &&\n)",
            "AmbiguousCommand",
            "empty shell command segment",
            id="close-after-and",
        ),
        pytest.param(
            "ls ||\n;",
            "AmbiguousCommand",
            "empty shell command segment",
            id="semicolon-after-or",
        ),
        pytest.param(
            "cat 'abc",
            "UnparseableCommand",
            "could not be parsed",
            id="unterminated-quote",
        ),
        pytest.param(
            'cat "abc',
            "UnparseableCommand",
            "could not be parsed",
            id="unterminated-double-quote",
        ),
        pytest.param(
            "cat $'abc\\'",
            "UnparseableCommand",
            "could not be parsed",
            id="unterminated-ansi-c",
        ),
        pytest.param(
            'cat $"abc',
            "UnparseableCommand",
            "could not be parsed",
            id="unterminated-locale-quote",
        ),
        pytest.param(
            'cat "a $(ls',
            "UnparseableCommand",
            "could not be parsed",
            id="unterminated-double-quote-with-subst",
        ),
        pytest.param(
            'cat "a `ls',
            "UnparseableCommand",
            "could not be parsed",
            id="unterminated-double-quote-with-backtick",
        ),
        pytest.param(
            "cat x\\",
            "UnparseableCommand",
            "could not be parsed",
            id="trailing-backslash",
        ),
        pytest.param(
            "echo $(ls",
            "UnparseableCommand",
            "unbalanced substitution",
            id="unterminated-substitution",
        ),
        pytest.param(
            "echo $((1+2)",
            "UnparseableCommand",
            "unbalanced substitution",
            id="unterminated-arithmetic",
        ),
        pytest.param(
            "cat <(ls",
            "UnparseableCommand",
            "unbalanced substitution",
            id="unterminated-process-sub",
        ),
        # Bash keeps a `#` glued after the `)` of an array assignment in the
        # word, so `a=(x)#c; tee .env` runs `tee`. The comment scans of this file
        # would read `#c; tee .env` as a comment, so the form is refused.
        pytest.param(
            "a=(x)#c; tee .env",
            "UnparseableCommand",
            "array assignment",
            id="array-assignment-then-hash",
        ),
        pytest.param(
            "a+=(x)#c; tee .env",
            "UnparseableCommand",
            "array assignment",
            id="array-append-then-hash",
        ),
        pytest.param(
            "declare -a a=(x)#c; tee .env",
            "UnparseableCommand",
            "array assignment",
            id="declared-array-then-hash",
        ),
        pytest.param(
            "a=(x y z)#c\ntee .env",
            "UnparseableCommand",
            "array assignment",
            id="array-with-elements-then-hash",
        ),
        pytest.param(
            "a=(x",
            "UnparseableCommand",
            "unbalanced array assignment",
            id="unterminated-array-assignment",
        ),
        pytest.param(
            "echo ${x:-a",
            "UnparseableCommand",
            "unbalanced parameter expansion",
            id="unterminated-expansion",
        ),
        pytest.param(
            'echo ${x:-"a}"',
            "UnparseableCommand",
            "unbalanced parameter expansion",
            id="expansion-whose-brace-is-quoted",
        ),
        # Shells disagree on a single quote inside a `${ }` inside double quotes:
        # Bash 5.2 takes it as the start of a quote (so the `;` below is inside it),
        # `bash --posix` and dash take it as a plain character (so `tee` runs). The
        # guard cannot know which shell runs the command, so it refuses.
        pytest.param(
            'cat "${x:-\'}" ; tee .env ; echo "\'}"',
            "UnparseableCommand",
            "single quote inside a double-quoted parameter expansion",
            id="single-quote-in-a-quoted-default",
        ),
        pytest.param(
            'git status "${x:-\'}" ; tee .env ; echo "\'}"',
            "UnparseableCommand",
            "single quote inside a double-quoted parameter expansion",
            id="single-quote-in-a-quoted-default-git-status",
        ),
        pytest.param(
            'cat "${x:-$\'}" ; tee .env ; echo "\'}"',
            "UnparseableCommand",
            "single quote inside a double-quoted parameter expansion",
            id="ansi-c-quote-in-a-quoted-default",
        ),
        pytest.param(
            "echo \"${x%'}'}\"",
            "UnparseableCommand",
            "single quote inside a double-quoted parameter expansion",
            id="harmless-single-quotes-in-a-quoted-suffix-pattern",
        ),
        pytest.param(
            "x=\"${y:-'a'}\"",
            "UnparseableCommand",
            "single quote inside a double-quoted parameter expansion",
            id="harmless-quoted-word-in-a-quoted-default",
        ),
        pytest.param(
            'echo "${x//\'/_}"',
            "UnparseableCommand",
            "single quote inside a double-quoted parameter expansion",
            id="single-quote-in-a-quoted-pattern",
        ),
        pytest.param(
            'echo "${x:-${y:-\'}}"',
            "UnparseableCommand",
            "single quote inside a double-quoted parameter expansion",
            id="single-quote-in-a-nested-quoted-default",
        ),
        pytest.param(
            'cat $(echo "${x:-\'}" ; tee .env ; echo "\'}")',
            "UnparseableCommand",
            "single quote inside a double-quoted parameter expansion",
            id="single-quote-in-a-quoted-default-in-a-substitution",
        ),
        pytest.param(
            'a=("${x:-\'}" $(tee .env) "\'}")',
            "UnparseableCommand",
            "single quote inside a double-quoted parameter expansion",
            id="single-quote-in-a-quoted-default-in-an-array",
        ),
        pytest.param(
            "cat $(echo ${x:-a)",
            "UnparseableCommand",
            "unbalanced substitution",
            id="substitution-with-an-open-expansion",
        ),
        pytest.param(
            "cat $(echo `echo x)",
            "UnparseableCommand",
            "unbalanced substitution",
            id="substitution-with-an-open-backtick",
        ),
        # An extended glob (`@( )`, `*( )`, `+( )`, `?( )`, `X!( )`) names files the
        # guard cannot list: with `shopt -s extglob` Bash expands it to `.env`.
        pytest.param(
            "shopt -s extglob\ntee @(.env|x)",
            "UnparseableCommand",
            "extended glob",
            id="extglob-alternatives-as-a-write-operand",
        ),
        pytest.param(
            "shopt -s extglob\ntee +(.env)",
            "UnparseableCommand",
            "extended glob",
            id="extglob-plus-as-a-write-operand",
        ),
        pytest.param(
            "shopt -s extglob\ntee ?(.env)",
            "UnparseableCommand",
            "extended glob",
            id="extglob-question-as-a-write-operand",
        ),
        pytest.param(
            "shopt -s extglob\ntee *(.env)",
            "UnparseableCommand",
            "extended glob",
            id="extglob-star-as-a-write-operand",
        ),
        pytest.param(
            "shopt -s extglob\nrm .!(x)",
            "UnparseableCommand",
            "extended glob",
            id="extglob-negation-after-a-dot",
        ),
        pytest.param(
            "cat $(shopt -s extglob\ntee @(.env|x))",
            "UnparseableCommand",
            "extended glob",
            id="extglob-in-a-substitution",
        ),
        # A case pattern ends with an unmatched `)`, which the paren matcher
        # takes for the end of the substitution: the rest of the statement
        # would be read as arguments of the outer command, and Bash runs it.
        # A `case` inside an unquoted substitution is refused instead.
        pytest.param(
            "cat $(case a in a) tee .env;; esac)",
            "UnparseableCommand",
            "case statement inside a substitution",
            id="case-in-a-substitution",
        ),
        pytest.param(
            "git status $(case a in a) tee .env;; esac)",
            "UnparseableCommand",
            "case statement inside a substitution",
            id="case-in-a-substitution-after-read-only-git",
        ),
        pytest.param(
            "a=($(case a in a) tee .env;; esac))",
            "UnparseableCommand",
            "case statement inside a substitution",
            id="case-in-an-array-element-substitution",
        ),
        pytest.param(
            "cat <(case a in a) tee .env;; esac)",
            "UnparseableCommand",
            "case statement inside a substitution",
            id="case-in-a-process-substitution",
        ),
        pytest.param(
            "tee >(case a in a) tee .env;; esac)",
            "UnparseableCommand",
            "case statement inside a substitution",
            id="case-in-an-output-process-substitution",
        ),
        pytest.param(
            "cat $(echo $(case a in a) tee .env;; esac))",
            "UnparseableCommand",
            "case statement inside a substitution",
            id="case-in-a-nested-substitution",
        ),
        pytest.param(
            "cat $(echo hi; case a in (a) tee .env;; esac)",
            "UnparseableCommand",
            "case statement inside a substitution",
            id="case-with-a-leading-paren-after-a-command",
        ),
        pytest.param(
            "cat $(\n  case a in a) tee .env;; esac\n)",
            "UnparseableCommand",
            "case statement inside a substitution",
            id="case-on-its-own-line",
        ),
        pytest.param(
            "cat $(if case a in a) true;; esac; then tee .env; fi)",
            "UnparseableCommand",
            "case statement inside a substitution",
            id="case-as-an-if-condition",
        ),
        pytest.param(
            "cat $(f() case a in a) tee .env;; esac; f)",
            "UnparseableCommand",
            "case statement inside a substitution",
            id="case-as-a-function-body",
        ),
        pytest.param(
            "cat $({ case a in a) tee .env;; esac; })",
            "UnparseableCommand",
            "case statement inside a substitution",
            id="case-in-a-brace-group",
        ),
        pytest.param(
            "cat $(ca\\\nse a in a) tee .env;; esac)",
            "UnparseableCommand",
            "case statement inside a substitution",
            id="case-split-by-a-line-continuation",
        ),
        pytest.param(
            "cat <<EOF\n$(case a in a) tee .env;; esac)\nEOF",
            "UnparseableCommand",
            "case statement inside a substitution",
            id="case-in-a-heredoc-substitution",
        ),
        # Bash reads `case` as a statement after `!`, `time`, `coproc`, and
        # `function NAME` too, so the refusal does not depend on what comes before.
        pytest.param(
            "cat $(coproc case a in a) tee .env;; esac)",
            "UnparseableCommand",
            "case statement inside a substitution",
            id="case-after-coproc",
        ),
        pytest.param(
            "cat $(coproc X case a in a) tee .env;; esac)",
            "UnparseableCommand",
            "case statement inside a substitution",
            id="case-after-coproc-name",
        ),
        pytest.param(
            "cat $(function f case a in a) tee .env;; esac; f)",
            "UnparseableCommand",
            "case statement inside a substitution",
            id="case-after-function-name",
        ),
        pytest.param(
            "cat $(time -p case a in a) tee .env;; esac)",
            "UnparseableCommand",
            "case statement inside a substitution",
            id="case-after-time-option",
        ),
        pytest.param(
            "cat $(! case a in a) tee .env;; esac)",
            "UnparseableCommand",
            "case statement inside a substitution",
            id="case-after-bang",
        ),
        # Over-blocks: Bash runs these harmlessly, but they are refused too.
        pytest.param(
            "echo $(case a in a) echo hi;; esac)",
            "UnparseableCommand",
            "case statement inside a substitution",
            id="harmless-case-in-a-substitution",
        ),
        pytest.param(
            "echo $(grep -c case README.md)",
            "UnparseableCommand",
            "case statement inside a substitution",
            id="case-as-a-search-word",
        ),
        pytest.param(
            "echo $(echo case x)",
            "UnparseableCommand",
            "case statement inside a substitution",
            id="case-as-an-argument",
        ),
    ),
)
def test_scanner_still_fails_closed_on_what_it_cannot_read(
    command: str, error: str, message: str
) -> None:
    with pytest.raises(getattr(PROTECT_FILES, error), match=message):
        _scan(command)


@pytest.mark.parametrize(
    "command",
    (
        pytest.param(
            "cat " + '"$(' * 40, id="forty-nested-double-quoted-substitutions"
        ),
        pytest.param(
            '"' + "$(a" * 600 + '"' + "y" * 100000 + '"',
            id="unclosed-substitutions-before-a-long-string",
        ),
        pytest.param(
            'cat "' + "$(a " * 4000 + '"', id="thousands-of-unclosed-substitutions"
        ),
        pytest.param(
            "echo " + "$(" * 200 + "x" + ")" * 200, id="two-hundred-nested-levels"
        ),
        pytest.param(
            "cat " + '"$(' * 1500,
            id="fifteen-hundred-nested-double-quoted-substitutions",
        ),
    ),
)
def test_scanner_fails_closed_when_a_command_is_too_complex_to_read(
    command: str,
) -> None:
    """One work budget covers every scan of one command. A command that makes the
    guard re-scan the same text over and over must stop with an error (exit 2)
    instead of running past the hook timeout, which lets the command through."""
    with pytest.raises(
        PROTECT_FILES.UnparseableCommand, match="too complex|too deeply"
    ):
        _scan(command)


def test_scanner_budget_is_reset_for_every_command() -> None:
    """No work carries over from one call to the next."""
    for _ in range(3):
        with pytest.raises(PROTECT_FILES.UnparseableCommand, match="too complex"):
            _scan('cat "' + "$(a " * 4000 + '"')
        assert _scan("echo $(date) && ls") == ([], [])


# The literal regex takes time quadratic in the length of a word: a 200 KB word
# took minutes (80 KB took 8 s, the hook timeout is 10 s), and a timeout lets
# the command through. A word longer than `LONG_WORD` is therefore never given
# to it: with no protected name in it, no literal can match; with one, the word
# cannot be checked in time, so the guard fails closed. These tests use inputs
# large enough that the old regex needs tens of seconds to minutes, and assert
# the result, not the time.
_VERY_LONG = 200_000


@pytest.mark.parametrize("unit", ("x", ",", "=", "(", "a.b", "-", "/"))
def test_protected_path_literals_find_nothing_in_a_very_long_word_with_no_name(
    unit: str,
) -> None:
    word = (unit * _VERY_LONG)[:_VERY_LONG]
    assert PROTECT_FILES.protected_path_literals(word) == []


@pytest.mark.parametrize(
    "suffix",
    (".pem", ".key", ".env", "uv.lock", "/.claude/settings.json", ".code-workspace"),
)
def test_protected_path_literals_fail_closed_on_a_very_long_word_naming_a_file(
    suffix: str,
) -> None:
    with pytest.raises(PROTECT_FILES.UnparseableCommand, match="too long"):
        PROTECT_FILES.protected_path_literals("x" * _VERY_LONG + suffix)


def test_protected_path_literals_read_a_word_up_to_the_limit() -> None:
    limit = PROTECT_FILES.LONG_WORD
    word = "x" * (limit - len(".pem")) + ".pem"
    assert len(word) == limit
    assert PROTECT_FILES.protected_path_literals(word) == [word]
    with pytest.raises(PROTECT_FILES.UnparseableCommand, match="too long"):
        PROTECT_FILES.protected_path_literals("x" + word)


def test_protected_path_literals_read_every_word_of_a_long_text() -> None:
    """Only a word over the limit is skipped: the others in the same text are read."""
    text = "x" * _VERY_LONG + " a.pem " + "y" * _VERY_LONG + " b.key"
    assert PROTECT_FILES.protected_path_literals(text) == ["a.pem", "b.key"]


@pytest.mark.parametrize(
    "name",
    sorted(PROTECT_FILES.HOOK_CONFIGS)
    + list(PROTECT_FILES.CONTROL_PLANE_DIRS)
    + [
        ".env",
        ".env.local",
        "uv.lock",
        "credentials-x",
        "a.pem",
        "a.key",
        "t.code-workspace",
    ],
)
def test_every_protected_literal_holds_a_name_the_long_word_check_looks_for(
    name: str,
) -> None:
    """The long-word skip is sound only if no literal can match without one of
    these names, so every alternative must be covered."""
    assert PROTECT_FILES.PROTECTED_PATH_LITERAL.search(name)
    assert PROTECT_FILES.PROTECTED_NAME.search(name)


def test_a_literal_never_matches_in_text_without_a_protected_name() -> None:
    import random

    rng = random.Random(7)
    fragments = [
        "a",
        ".",
        "-",
        "/",
        ",",
        "=",
        "(",
        "'",
        '"',
        "pem",
        "key",
        "env",
        " ",
        "lock",
        "credential",
    ]
    for _ in range(3000):
        text = "".join(rng.choice(fragments) for _ in range(rng.randint(1, 14)))
        if PROTECT_FILES.PROTECTED_PATH_LITERAL.search(text):
            assert PROTECT_FILES.PROTECTED_NAME.search(text), text


def test_scanner_reads_a_very_long_quoted_string_of_open_braces() -> None:
    """Each `{` used to be tried against the whole rest of the string."""
    assert _scan('cat "' + "{" * _VERY_LONG + '"') == ([], [])
    assert _scan('cat "' + "{a," * 1000 + '}"') == ([], [])


def test_scanner_finds_a_write_after_a_very_long_argument() -> None:
    """`echo <200 KB>; tee .env` used to run past the hook timeout."""
    confirmed, _uncertain = _scan("echo " + "x" * _VERY_LONG + "; tee .env")
    assert ".env" in confirmed


def test_protect_files_denies_a_write_after_a_very_long_argument(
    tmp_path: Path,
) -> None:
    command = "echo " + "," * _VERY_LONG + "; tee .env"
    process = _run_protect_files(
        _client_bash_payload("openai-codex", command), tmp_path, "openai-codex"
    )
    assert _protect_decision(process) == "deny", process.stdout


# Slow by design: the time `opaque_write_paths` needs grows with the square of
# the repeats. With the alarm off, on the machine that wrote this test (seconds
# for 60,000 repeats, a 300 KB command): Python 3.9.0 29.3, 3.12.3 24.9, 3.13.6
# 24.7. The alarm is 4 s, so that is at least 6x over it; 40,000 repeats gave
# 10.5 to 12.9 s, under 3x, which a faster runner could undercut. The tests stay
# bounded: with the alarm working, each ends after about 4 s.
_SLOW_INPUT = "echo '" + "open(" * 60_000 + "'"


def test_protect_files_fails_closed_when_the_classifier_runs_too_long(
    tmp_path: Path,
) -> None:
    """A backstop for any slow input (3.9's regex cannot be interrupted): the
    process is killed by an alarm and the hook script treats the failed exit
    as a denial. This input is slow in `opaque_write_paths`, not in the word
    check."""
    command = _SLOW_INPUT
    process = _run_protect_files(
        _client_bash_payload("openai-codex", command), tmp_path, "openai-codex"
    )
    assert process.returncode == 2, process.stderr
    assert '"permissionDecision":"deny"' in process.stdout


@pytest.mark.parametrize(
    "command, expected",
    (
        pytest.param(
            "tee '|' cat x",
            [["tee", PROTECT_FILES.QUOTED_VALUE_PREFIX + "|", "cat", "x"]],
            id="quoted-operator-gets-the-quoted-prefix",
        ),
        pytest.param(
            "cat '2>' x",
            [["cat", PROTECT_FILES.QUOTED_VALUE_PREFIX + "2>", "x"]],
            id="quoted-redirect-gets-the-quoted-prefix",
        ),
        pytest.param(
            "tee a'|'b x", [["tee", "a|b", "x"]], id="operator-inside-a-longer-word"
        ),
        pytest.param("a\n\n# c\nb", [["a"], ["b"]], id="blank-line-and-comment"),
        pytest.param("a |\n b ;\n c", [["a"], ["b"], ["c"]], id="operator-line-ends"),
        pytest.param("(a && b)", [["a"], ["b"]], id="leading-group"),
        pytest.param("a\\\nb c", [["ab", "c"]], id="line-continuation"),
        pytest.param("'a\\\nb'", [["a\\\nb"]], id="single-quotes-keep-the-backslash"),
        pytest.param('"a\\\nb"', [["ab"]], id="double-quotes-join-the-lines"),
        pytest.param('"\\$a \\x"', [["$a \\x"]], id="double-quote-escapes"),
        pytest.param("cat x#y z", [["cat", "x#y", "z"]], id="hash-inside-a-word"),
        pytest.param("a ;", [["a"]], id="trailing-separator"),
        # A `${ }` is one part of its word, up to its own `}`.
        pytest.param(
            "tee ${x:- a b ) #} .env",
            [["tee", "${x:- a b ) #}", ".env"]],
            id="expansion-with-blanks-paren-and-hash",
        ),
        pytest.param(
            'echo "${x:-"a)"}" y',
            [["echo", PROTECT_FILES.QUOTED_VALUE_PREFIX + '${x:-"a)"}', "y"]],
            id="quotes-inside-a-quoted-expansion",
        ),
        pytest.param(
            "echo $${x:- ; tee .env}",
            [["echo", "$${x:-"], ["tee", ".env}"]],
            id="pid-then-brace-opens-no-expansion",
        ),
        pytest.param(
            "echo ${x:- #}; tee .env",
            [["echo", "${x:- #}"], ["tee", ".env"]],
            id="hash-in-an-expansion-is-not-a-comment",
        ),
        pytest.param(
            "echo a${x:-b c}d", [["echo", "a${x:-b c}d"]], id="expansion-inside-a-word"
        ),
        pytest.param("echo ${x:-}}", [["echo", "${x:-}}"]], id="expansion-then-brace"),
        pytest.param(
            "echo ${x:-${y:-)}} z",
            [["echo", "${x:-${y:-)}}", "z"]],
            id="nested-expansion",
        ),
        pytest.param(
            "echo ${x//'}'/} z",
            [["echo", "${x//'}'/}", "z"]],
            id="single-quoted-brace-stays-in-the-word",
        ),
        # A run of operator characters splits by longest match.
        pytest.param("a;(b)", [["a"], ["b"]], id="semicolon-then-group"),
        pytest.param("a&&(b)", [["a"], ["b"]], id="and-then-group"),
        pytest.param("a|(b)", [["a"], ["b"]], id="pipe-then-group"),
        pytest.param("a>>b", [["a", ">>", "b"]], id="append-stays-one-word"),
        pytest.param("a 2>&1 b", [["a", "2", ">&", "1", "b"]], id="fd-duplicate"),
        # A redirect operator is a word followed by its target, as in Bash.
        pytest.param("a &>> b", [["a", "&>>", "b"]], id="both-append-and-target"),
        pytest.param("a >& b", [["a", ">&", "b"]], id="duplicate-and-target"),
        pytest.param("a <> b", [["a", "<>", "b"]], id="read-write-and-target"),
        # Carriage return is an ordinary character, not a blank.
        pytest.param("a\rb", [["a\rb"]], id="carriage-return-inside-a-word"),
        pytest.param("a\r#b", [["a\r#b"]], id="carriage-return-then-hash"),
        # An operator after `)`, and a `)` after a newline or `;`.
        pytest.param("(a) && b", [["a"], ["b"]], id="after-group"),
        pytest.param("((a))", [["a"]], id="double-parens"),
        pytest.param("(\n a\n b\n)", [["a"], ["b"]], id="close-on-its-own-line"),
        pytest.param("( a; )", [["a"]], id="close-after-semicolon"),
        pytest.param(
            "f() { a; }", [["f"], ["{", "a"], ["}"]], id="function-definition"
        ),
    ),
)
def test_split_segments_follows_bash_word_and_segment_rules(
    command: str, expected: list[list[str]]
) -> None:
    assert PROTECT_FILES.split_segments(command) == expected


def test_split_segments_splits_a_pipe_and_at_its_operator() -> None:
    """Bash reads `|&` as a pipe, so `a |& b` is two commands."""
    assert PROTECT_FILES.split_segments("a |& b") == [["a"], ["b"]]


@pytest.mark.parametrize(
    "command, expected_text, expected_inner",
    (
        pytest.param(
            "tee $(pwd)/x y",
            "tee __PROTECT_FILES_PROCSUB_0__/x y",
            {"__PROTECT_FILES_PROCSUB_0__": "pwd"},
            id="substitution-then-suffix",
        ),
        pytest.param(
            "cat<(ls)x",
            "cat __PROTECT_FILES_PROCSUB_0__x",
            {"__PROTECT_FILES_PROCSUB_0__": "ls"},
            id="process-sub-keeps-the-word-after-it",
        ),
        pytest.param(
            "a$(b)$(c)d",
            "a__PROTECT_FILES_PROCSUB_0____PROTECT_FILES_PROCSUB_1__d",
            {"__PROTECT_FILES_PROCSUB_0__": "b", "__PROTECT_FILES_PROCSUB_1__": "c"},
            id="two-substitutions-in-one-word",
        ),
        pytest.param(
            "echo $((1+2))",
            "echo __PROTECT_FILES_PROCSUB_0__",
            {"__PROTECT_FILES_PROCSUB_0__": ""},
            id="arithmetic-has-no-command",
        ),
        pytest.param(
            "echo $(( $(a) + 1 ))",
            "echo __PROTECT_FILES_PROCSUB_0__",
            {"__PROTECT_FILES_PROCSUB_0__": "a"},
            id="arithmetic-keeps-its-nested-substitution",
        ),
        pytest.param(
            "echo $(echo $(a))",
            "echo __PROTECT_FILES_PROCSUB_0__",
            {"__PROTECT_FILES_PROCSUB_0__": "echo $(a)"},
            id="nested-substitution-is-classified-by-recursion",
        ),
        pytest.param(
            "echo '$(a)' \"$(b)\" \\$(c) # $(d)",
            "echo '$(a)' \"__PROTECT_FILES_PROCSUB_0__\" \\$(c) # $(d)",
            {"__PROTECT_FILES_PROCSUB_0__": "b"},
            id="single-quoted-escaped-and-commented-text-is-left-alone",
        ),
        # A `)` inside `${ }` does not close a substitution around it.
        pytest.param(
            "cat $(tee ${x//)/} .env)",
            "cat __PROTECT_FILES_PROCSUB_0__",
            {"__PROTECT_FILES_PROCSUB_0__": "tee ${x//)/} .env"},
            id="paren-in-an-expansion-in-a-substitution",
        ),
        # A substitution inside `${ }` is found, and `#` there is no comment.
        pytest.param(
            "echo ${x:-$(date)} ${#X} ${y:- #} $(a)",
            "echo ${x:-__PROTECT_FILES_PROCSUB_0__} ${#X} ${y:- #} "
            "__PROTECT_FILES_PROCSUB_1__",
            {"__PROTECT_FILES_PROCSUB_0__": "date", "__PROTECT_FILES_PROCSUB_1__": "a"},
            id="substitution-in-an-expansion-and-hash-in-another",
        ),
        pytest.param(
            "echo ${x:-$(echo ${y:-)})}",
            "echo ${x:-__PROTECT_FILES_PROCSUB_0__}",
            {"__PROTECT_FILES_PROCSUB_0__": "echo ${y:-)}"},
            id="expansion-inside-a-substitution-inside-an-expansion",
        ),
        pytest.param(
            "echo $$ $${x:-$(a)}",
            "echo $$ $${x:-__PROTECT_FILES_PROCSUB_0__}",
            {"__PROTECT_FILES_PROCSUB_0__": "a"},
            id="process-id-then-brace",
        ),
    ),
)
def test_extract_substitutions_keeps_an_unquoted_substitution_in_its_word(
    command: str, expected_text: str, expected_inner: dict[str, str]
) -> None:
    text, inner = PROTECT_FILES.extract_substitutions(command)
    assert (text, inner) == (expected_text, expected_inner)


_HOOK_CLIENTS = tuple(param.values[0] for param in CLIENT_CONFIG_DECISIONS)


@pytest.mark.parametrize("target_id", _HOOK_CLIENTS)
@pytest.mark.parametrize(
    "command",
    (
        pytest.param("tee '|' cat .env", id="quoted-pipe"),
        pytest.param("# step 1\ntee .env", id="comment-line"),
        pytest.param("cat README.md\n\ntouch .env", id="blank-line"),
        pytest.param("cat x;(tee .env)", id="semicolon-then-group"),
        pytest.param("tee $(true) .env", id="substitution-then-operand"),
        pytest.param("echo a\r#b; tee .env", id="carriage-return-then-hash"),
        pytest.param("a=(x y); tee .env", id="array-assignment-then-write"),
        pytest.param("tee .env$X", id="name-then-variable"),
        pytest.param("tee $X.env", id="variable-then-name"),
        pytest.param("tee ${X}.env", id="braced-variable-then-name"),
        pytest.param('tee "$X".env', id="quoted-variable-then-name"),
        pytest.param("echo x > .env$X", id="redirect-to-name-then-variable"),
        pytest.param("bash -c '{rm,.env}'", id="bash-c-brace-list"),
        pytest.param("eval '{rm,.env}'", id="eval-brace-list"),
        pytest.param("cat $(tee ${x//)/} .env)", id="paren-in-expansion-cat"),
        pytest.param("git status $(tee ${x//)/} .env)", id="paren-in-expansion-git"),
        pytest.param("x=$(tee ${x:-)} .env)", id="paren-in-default-assignment"),
        pytest.param("tee ${y//) cat /} .env", id="paren-and-words-in-pattern"),
        pytest.param("cat <(tee ${x//)/} .env)", id="paren-in-expansion-process-sub"),
        pytest.param("echo ${x:- #}; tee .env", id="hash-in-expansion"),
        pytest.param("cat $(tee `echo )` .env)", id="paren-in-backticks"),
        pytest.param("( case a in a) tee .env;; esac )", id="case-in-a-subshell-group"),
        pytest.param("case a in a) tee .env;; esac", id="case-at-the-top-level"),
    ),
)
def test_protect_files_denies_scanner_bypass_forms_on_every_client(
    tmp_path: Path, target_id: str, command: str
) -> None:
    process = _run_protect_files(
        _client_bash_payload(target_id, command), tmp_path, target_id
    )
    assert _protect_decision(process) == "deny", process.stdout
    assert ".env" in process.stdout


@pytest.mark.parametrize("target_id", _HOOK_CLIENTS)
def test_protect_files_denies_removing_a_quoted_glob_name_on_every_client(
    tmp_path: Path, target_id: str
) -> None:
    """`rm` is a modelled mutator, so its quoted glob is the literal file name
    (`credentials*`), not a pattern to skip like it is for `find`."""
    process = _run_protect_files(
        _client_bash_payload(target_id, "rm 'credentials*'"), tmp_path, target_id
    )
    assert _protect_decision(process) == "deny", process.stdout
    assert "credentials" in process.stdout


@pytest.mark.parametrize("target_id, expected", CLIENT_CONFIG_DECISIONS)
def test_protect_files_gates_a_config_write_behind_a_quoted_operator(
    tmp_path: Path, target_id: str, expected: str
) -> None:
    process = _run_protect_files(
        _client_bash_payload(target_id, "tee '&&' cat .claude/settings.json"),
        tmp_path,
        target_id,
    )
    assert _protect_decision(process) == expected, process.stdout
    assert ".claude/settings.json" in process.stdout


@pytest.mark.parametrize("target_id, expected", CLIENT_CONFIG_DECISIONS)
@pytest.mark.parametrize(
    "command",
    (
        pytest.param(
            "cd $(git rev-parse --show-toplevel)/.claude/hooks && tee x.sh",
            id="cd-to-a-substitution-path",
        ),
        pytest.param(
            "git -C $(git rev-parse --show-toplevel)/.claude restore hooks/x.sh",
            id="git-c-a-substitution-path",
        ),
    ),
)
def test_protect_files_gates_a_write_in_a_folder_named_by_a_substitution(
    tmp_path: Path, target_id: str, expected: str, command: str
) -> None:
    """The substitution may expand to the repository root, so the folder is
    `.claude/hooks`: the protected-config decision for the client, not allow."""
    process = _run_protect_files(
        _client_bash_payload(target_id, command), tmp_path, target_id
    )
    assert _protect_decision(process) == expected, process.stdout


@pytest.mark.skipif(not hasattr(signal, "SIGALRM"), reason="needs SIGALRM")
def test_protect_files_alarm_still_fires_when_the_parent_ignores_sigalrm(
    tmp_path: Path,
) -> None:
    """An ignored signal stays ignored across `exec`, so a parent that starts the
    hook with SIGALRM ignored would switch the 4-second backstop off. The script
    must put the default action back first; the alarm then ends the process
    (`protect-files.sh` turns that exit into a denial)."""
    command = _SLOW_INPUT
    process = subprocess.run(
        [
            "python3",
            str(SCRIPT_SRC / "protect-files.py"),
            "openai-codex",
            str(tmp_path),
        ],
        input=json.dumps(_client_bash_payload("openai-codex", command)),
        text=True,
        capture_output=True,
        check=False,
        timeout=120,
        preexec_fn=lambda: signal.signal(signal.SIGALRM, signal.SIG_IGN),
    )
    assert process.returncode == -signal.SIGALRM, (process.returncode, process.stderr)


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("find . -name '*.pem'", id="find-a-quoted-pem-glob"),
        pytest.param(
            'find . -name "credentials*"', id="find-a-quoted-credentials-glob"
        ),
        pytest.param("ls '*.key'", id="list-a-quoted-key-glob"),
        pytest.param("a=(x y); echo ok", id="array-assignment"),
        pytest.param("echo $HOME", id="plain-variable"),
        pytest.param("ls $X/docs", id="variable-then-folder"),
        pytest.param("cat .env$X", id="read-name-then-variable"),
    ),
)
def test_protect_files_allows_a_pattern_and_a_variable_that_names_no_protected_file(
    tmp_path: Path, command: str
) -> None:
    process = _run_protect_files(
        _client_bash_payload("claude-code", command), tmp_path, "claude-code"
    )
    assert _protect_decision(process) == "allow", process.stdout


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("printf 'x|y\\n' | grep '|' | head -1", id="quoted-pipes"),
        pytest.param("find . -exec grep x {} \\; | head -1", id="find-exec-pipe"),
        pytest.param("(cd docs && ls)", id="leading-group"),
        pytest.param(
            "# note\ngit status\n\nls # don't\n", id="comments-and-blank-lines"
        ),
        pytest.param("echo $(date) && ls", id="substitution-then-and"),
        pytest.param("(cd docs && ls) && ls", id="group-then-and"),
        pytest.param("(\n  cd docs\n  ls\n)", id="multi-line-group"),
        pytest.param("ls $(pwd)/docs", id="substitution-then-path-suffix"),
        pytest.param(
            "cd $(git rev-parse --show-toplevel) && ls", id="toplevel-then-and"
        ),
    ),
)
def test_protect_files_allows_read_only_commands_the_old_lexer_misread(
    tmp_path: Path, command: str
) -> None:
    process = _run_protect_files(
        _client_bash_payload("claude-code", command), tmp_path, "claude-code"
    )
    assert _protect_decision(process) == "allow", process.stdout


def test_protect_files_still_fails_closed_on_an_empty_segment(tmp_path: Path) -> None:
    process = _run_protect_files(
        _client_bash_payload("claude-code", "| head"), tmp_path, "claude-code"
    )
    assert process.returncode == 2
    assert '"permissionDecision":"deny"' in process.stdout


@pytest.mark.parametrize("target_id", _HOOK_CLIENTS)
@pytest.mark.parametrize(
    "command",
    (
        pytest.param('cat "${x:-\'}" ; tee .env ; echo "\'}"', id="cat"),
        pytest.param('git status "${x:-\'}" ; tee .env ; echo "\'}"', id="git-status"),
        pytest.param('cat "${x:-$\'}" ; tee .env ; echo "\'}"', id="ansi-c"),
    ),
)
def test_protect_files_fails_closed_on_a_single_quote_in_a_quoted_expansion(
    tmp_path: Path, target_id: str, command: str
) -> None:
    """`bash --posix` and dash run the `tee` in the middle; Bash 5.2 does not.
    The client may use either, so the command is refused."""
    process = _run_protect_files(
        _client_bash_payload(target_id, command), tmp_path, target_id
    )
    assert process.returncode == 2
    assert '"permissionDecision":"deny"' in process.stdout


@pytest.mark.parametrize("target_id", _HOOK_CLIENTS)
@pytest.mark.parametrize(
    "command",
    (
        pytest.param("cat $(case a in a) tee .env;; esac)", id="cat-substitution"),
        pytest.param(
            "git status $(case a in a) tee .env;; esac)", id="git-status-substitution"
        ),
        pytest.param("a=($(case a in a) tee .env;; esac))", id="array-substitution"),
        pytest.param("cat <(case a in a) tee .env;; esac)", id="process-substitution"),
        pytest.param(
            "cat <<EOF\n$(case a in a) tee .env;; esac)\nEOF",
            id="heredoc-substitution",
        ),
    ),
)
def test_protect_files_fails_closed_on_a_case_statement_inside_a_substitution(
    tmp_path: Path, target_id: str, command: str
) -> None:
    """Bash runs the `tee` after the case pattern's `)`; the matcher would close
    the substitution there, so the whole command is refused."""
    process = _run_protect_files(
        _client_bash_payload(target_id, command), tmp_path, target_id
    )
    assert process.returncode == 2
    assert '"permissionDecision":"deny"' in process.stdout


@pytest.mark.parametrize("target_id", _HOOK_CLIENTS)
@pytest.mark.parametrize(
    "command",
    (
        pytest.param("a=(x)#c; tee out.txt", id="array-assignment-then-hash"),
        pytest.param("a+=(x)#c; echo ok", id="array-append-then-hash"),
    ),
)
def test_protect_files_fails_closed_on_a_hash_right_after_an_array_assignment(
    tmp_path: Path, target_id: str, command: str
) -> None:
    """Bash reads the `#` as part of the word, so the rest of the line still
    runs; the scanner refuses the form instead of guessing."""
    process = _run_protect_files(
        _client_bash_payload(target_id, command), tmp_path, target_id
    )
    assert process.returncode == 2
    assert '"permissionDecision":"deny"' in process.stdout
