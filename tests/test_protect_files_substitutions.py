"""Coverage for the classifier of `protect-files.py` beyond plain commands: command
substitutions in double quotes and backticks, grouped operators, inline `sed` writes,
folder changes before an unmodelled command, names built by expansions, tracked
variables, shell options, `find` patterns, and the forms of review rounds 1 and 2.

Every expected value was checked against Bash's own reading (and GNU sed's) with a
harmless stand-in outside the repository; these tests never run a command. A name
`.env` that a command would write is a protected hit, found by `protected()` in
the scanner's targets, as `emit()` does.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_hook_gates import (  # noqa: E402
    CLIENT_CONFIG_DECISIONS,
    REPO_ROOT,
    _client_bash_payload,
    _protect_decision,
    _run_protect_files,
)
from test_protect_files_scoping import PROTECT_FILES  # noqa: E402

_CLIENTS = tuple(param.values[0] for param in CLIENT_CONFIG_DECISIONS)


def _hit(command: str, root: Path | None = None) -> bool:
    """True when the scanner reports a protected path for `command`."""
    base = str(root if root is not None else REPO_ROOT)
    confirmed, uncertain = PROTECT_FILES.shell_targets(command, base)
    return any(PROTECT_FILES.protected(path, base) for path in confirmed + uncertain)


# --------------------------------------------------------------------------
# BF-I1: command substitution inside double quotes, and in backticks.
# --------------------------------------------------------------------------

_SUBSTITUTION_DENY = (
    pytest.param('cat "$(tee .env)"', id="double-quoted-substitution"),
    pytest.param("cat `tee .env`", id="backticks"),
    pytest.param('cat "`tee .env`"', id="double-quoted-backticks"),
    pytest.param('cat <<< "$(tee .env)"', id="here-string-substitution"),
    pytest.param('echo "Today: $(tee .env)"', id="text-then-substitution"),
    pytest.param('x="$(tee .env)"', id="assignment-substitution"),
    pytest.param('cat "a $(tee .env) b"', id="substitution-between-words"),
    pytest.param('echo "$(echo "$(tee .env)")"', id="nested-double-quotes"),
    pytest.param('echo "$(echo `tee .env`)"', id="backticks-in-a-substitution"),
    pytest.param('cat "${x:-$(tee .env)}"', id="substitution-in-a-default"),
    pytest.param('a=("$(tee .env)")', id="array-element-substitution"),
    pytest.param("cat `echo $(tee .env)`", id="substitution-in-backticks"),
    pytest.param('echo "$((1+$(tee .env)))"', id="substitution-in-arithmetic"),
    pytest.param('git commit -m "$(tee .env)"', id="commit-message-substitution"),
    pytest.param('cat $"$(tee .env)"', id="locale-quoted-substitution"),
    pytest.param('echo "$(rm .env)"', id="remove-in-substitution"),
    pytest.param('echo "$(touch .env)"', id="touch-in-substitution"),
    pytest.param('echo "$(echo x > .env)"', id="redirect-in-substitution"),
    pytest.param(
        "echo \"$(sed -n 'w .env' README.md)\"", id="sed-write-in-substitution"
    ),
    pytest.param('echo "$(cat x |& tee .env)"', id="pipe-and-in-substitution"),
    pytest.param(
        "git commit -m \"$(cat <<'EOF'\nmsg\nEOF\n) $(tee .env)\"",
        id="commit-message-heredoc-then-write",
    ),
    pytest.param(
        'cat "$(bash <<EOF\ntee .env\nEOF\n)"',
        id="heredoc-body-in-a-quoted-substitution",
    ),
    pytest.param(
        "cat \"$(bash <<'EOF'\ntee .env\nEOF\n)\"",
        id="quoted-heredoc-body-in-a-quoted-substitution",
    ),
    pytest.param(
        'cat "$(cat <<EOF\n$(tee .env)\nEOF\n)"',
        id="substitution-in-an-unquoted-heredoc-in-a-quoted-substitution",
    ),
    pytest.param("echo \"$(bash -c 'tee .env')\"", id="shell-script-in-a-substitution"),
    pytest.param(
        'echo "$(cd .claude && ls)" $(tee .env)', id="write-after-a-quoted-one"
    ),
)


@pytest.mark.parametrize("command", _SUBSTITUTION_DENY)
def test_scanner_finds_the_write_in_a_quoted_substitution_or_backticks(
    command: str,
) -> None:
    assert _hit(command)


@pytest.mark.parametrize("target_id", _CLIENTS)
@pytest.mark.parametrize(
    "command",
    (
        pytest.param('cat "$(tee .env)"', id="double-quoted-substitution"),
        pytest.param("cat `tee .env`", id="backticks"),
        pytest.param('cat "`tee .env`"', id="double-quoted-backticks"),
        pytest.param('cat <<< "$(tee .env)"', id="here-string"),
    ),
)
def test_protect_files_denies_a_write_in_a_quoted_substitution_on_every_client(
    tmp_path: Path, target_id: str, command: str
) -> None:
    process = _run_protect_files(
        _client_bash_payload(target_id, command), tmp_path, target_id
    )
    assert _protect_decision(process) == "deny", process.stdout
    assert ".env" in process.stdout


_COMMIT_MESSAGE = "git commit -m \"$(cat <<'EOF'\n%s\nEOF\n)\""
_SUBSTITUTION_ALLOW = (
    pytest.param('echo "$(date)"', id="quoted-substitution"),
    pytest.param('echo "`date`"', id="quoted-backticks"),
    pytest.param("cat '$(tee .env)'", id="single-quotes-are-literal"),
    pytest.param("cat '`tee .env`'", id="single-quoted-backticks-are-literal"),
    pytest.param('echo "Today: $(date)"', id="text-then-substitution"),
    pytest.param('cd "$(git rev-parse --show-toplevel)"', id="cd-to-the-toplevel"),
    pytest.param('git log --format="%h $(echo x)"', id="log-format-substitution"),
    pytest.param('echo "$X"', id="quoted-variable"),
    pytest.param('echo "${X:-default}"', id="quoted-default"),
    pytest.param('echo "$(echo "a b")"', id="nested-double-quotes"),
    pytest.param('echo "$(echo `date`)"', id="backticks-in-a-substitution"),
    pytest.param('cat "\\$(tee .env)"', id="escaped-dollar-is-literal"),
    pytest.param('cat "\\`tee .env\\`"', id="escaped-backticks-are-literal"),
    pytest.param('cat <<< "$(date)"', id="here-string-substitution"),
    pytest.param('echo "$((1+2))"', id="arithmetic"),
    pytest.param("echo $((\n1 << 2\n))", id="arithmetic-shift-across-newlines"),
    pytest.param(
        'echo "$((\n1 << 2\n))"', id="quoted-arithmetic-shift-across-newlines"
    ),
    pytest.param("echo $((1 << 2)) $((\n3 << 4\n))", id="two-arithmetic-shifts"),
    pytest.param("cat x 2>&1 | head", id="duplicate-then-pipe"),
    pytest.param("cat x >&2", id="duplicate-to-stderr"),
    pytest.param("cat x |& head", id="pipe-and-read"),
    pytest.param("cat x >&-", id="close-stdout"),
    pytest.param("cat x 2>&-", id="close-stderr"),
    pytest.param("echo a >&2 | cat", id="duplicate-in-a-pipeline"),
    pytest.param("ls >& /dev/null", id="duplicate-to-null"),
    pytest.param(
        _COMMIT_MESSAGE % "Fix: it works (really) # note", id="commit-message"
    ),
    pytest.param(
        _COMMIT_MESSAGE % "Refuse a case word: case a in a) b;; esac",
        id="commit-message-with-the-word-case",
    ),
    pytest.param(
        _COMMIT_MESSAGE % "Don't \"quote\" ${x:-'} $(not run) `tick` ) ( ' \" #",
        id="commit-message-with-punctuation",
    ),
    pytest.param(
        _COMMIT_MESSAGE % "mention .env and .claude/hooks in the prose",
        id="commit-message-naming-protected-paths",
    ),
    pytest.param(
        'git commit -m "$(cat <<EOF\nplain body $(date)\nEOF\n)"',
        id="commit-message-unquoted-heredoc",
    ),
    pytest.param(
        'git commit -m "title" -m "$(cat <<\'EOF\'\nbody case ) \'\nEOF\n)"',
        id="commit-second-message",
    ),
    pytest.param(
        "git commit -am \"$(cat <<'EOF'\nbody\nEOF\n)\"",
        id="commit-combined-flag-message",
    ),
    pytest.param(
        "git tag -a v1 -m \"$(cat <<'EOF'\nnotes about .env\nEOF\n)\"",
        id="tag-message",
    ),
)


@pytest.mark.parametrize("command", _SUBSTITUTION_ALLOW)
def test_scanner_allows_the_common_quoted_substitution_forms(command: str) -> None:
    assert not _hit(command)


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("echo '$(tee .env)'", id="single-quoted-substitution"),
        pytest.param('echo "\\$(tee .env)"', id="escaped-substitution"),
        pytest.param("echo .env", id="plain-name"),
    ),
)
def test_scanner_still_denies_echo_of_a_protected_name_as_text(command: str) -> None:
    """Today's result, unchanged: an unknown command is scanned for protected
    names even in quotes (`echo .env` has always been denied). The quoted
    substitution is still not run, which `cat` (read-only, arguments ignored)
    shows above."""
    assert _hit(command)


def test_scanner_still_scans_a_quoted_heredoc_outside_a_commit_message() -> None:
    """The message exemption is for the value of `git commit -m`, not for any
    `cat <<'EOF'` in a substitution: `tee "$(cat <<'EOF' ...)"` names a file."""
    assert _hit("echo \"$(cat <<'EOF'\nmention .env\nEOF\n)\"")
    assert _hit("tee \"$(cat <<'EOF'\n.env\nEOF\n)\"")


# A `case` word and a quote rule must not reach a quoted heredoc body.
@pytest.mark.parametrize(
    "command",
    (
        pytest.param(
            _COMMIT_MESSAGE % "case a in a) tee x;; esac", id="case-statement"
        ),
        pytest.param(_COMMIT_MESSAGE % "case", id="case-word-alone"),
        pytest.param(
            _COMMIT_MESSAGE % "x ${y:-'} z", id="single-quote-in-an-expansion"
        ),
        pytest.param(_COMMIT_MESSAGE % "it's `a` (b) # c", id="mixed-punctuation"),
    ),
)
def test_scanner_reads_a_quoted_heredoc_body_in_a_commit_message_as_data(
    command: str,
) -> None:
    assert PROTECT_FILES.shell_targets(command, str(REPO_ROOT)) == ([], [])


@pytest.mark.parametrize(
    "command, message",
    (
        pytest.param(
            'cat "$(case a in a) tee .env;; esac)"',
            "case statement inside a substitution",
            id="case-in-a-quoted-substitution",
        ),
        pytest.param(
            'cat "$(echo "$(case a in a) echo hi;; esac)")"',
            "case statement inside a substitution",
            id="case-in-a-nested-quoted-substitution",
        ),
        pytest.param(
            'cat "$(echo `x)"',
            "unbalanced",
            id="open-backtick-in-a-quoted-substitution",
        ),
        pytest.param("cat `echo x", "unbalanced", id="open-backticks"),
        pytest.param(
            'cat "$(echo "${x:-\'}" ; tee .env ; echo "\'}")"',
            "single quote inside a double-quoted parameter expansion",
            id="single-quote-in-a-quoted-expansion-in-a-quoted-substitution",
        ),
    ),
)
def test_scanner_fails_closed_on_what_it_still_cannot_read_in_quotes(
    command: str, message: str
) -> None:
    with pytest.raises(PROTECT_FILES.UnparseableCommand, match=message):
        PROTECT_FILES.shell_targets(command, str(REPO_ROOT))


@pytest.mark.parametrize(
    "command, expected_text, expected_inner",
    (
        pytest.param(
            'echo "a $(date) b"',
            'echo "a __PROTECT_FILES_PROCSUB_0__ b"',
            {"__PROTECT_FILES_PROCSUB_0__": "date"},
            id="quoted-substitution",
        ),
        pytest.param(
            'echo "`date`"',
            'echo "__PROTECT_FILES_PROCSUB_0__"',
            {"__PROTECT_FILES_PROCSUB_0__": "date"},
            id="quoted-backticks",
        ),
        pytest.param(
            "echo `echo \\`date\\``",
            "echo __PROTECT_FILES_PROCSUB_0__",
            {"__PROTECT_FILES_PROCSUB_0__": "echo `date`"},
            id="escaped-backticks-inside-backticks",
        ),
        pytest.param(
            'echo "`echo \\"x\\"`"',
            'echo "__PROTECT_FILES_PROCSUB_0__"',
            {"__PROTECT_FILES_PROCSUB_0__": 'echo "x"'},
            id="escaped-quote-inside-quoted-backticks",
        ),
        pytest.param(
            "echo '$(a)' \"\\$(b)\"",
            "echo '$(a)' \"\\$(b)\"",
            {},
            id="single-quoted-and-escaped-are-left-alone",
        ),
        pytest.param(
            'echo "${x:-$(a)}"',
            'echo "${x:-__PROTECT_FILES_PROCSUB_0__}"',
            {"__PROTECT_FILES_PROCSUB_0__": "a"},
            id="substitution-in-a-quoted-default",
        ),
        pytest.param(
            "echo \"$(cat <<'EOF'\nit's ) done\nEOF\n)\" x",
            'echo "__PROTECT_FILES_PROCSUB_0__" x',
            {"__PROTECT_FILES_PROCSUB_0__": "cat <<'EOF'\nit's ) done\nEOF\n"},
            id="heredoc-body-with-a-paren-and-a-quote",
        ),
        pytest.param(
            'echo "$(echo "$(a)")"',
            'echo "__PROTECT_FILES_PROCSUB_0__"',
            {"__PROTECT_FILES_PROCSUB_0__": 'echo "$(a)"'},
            id="nested-quoted-substitution",
        ),
    ),
)
def test_extract_substitutions_finds_a_substitution_inside_double_quotes(
    command: str, expected_text: str, expected_inner: dict[str, str]
) -> None:
    assert PROTECT_FILES.extract_substitutions(command) == (
        expected_text,
        expected_inner,
    )


# --------------------------------------------------------------------------
# BF-I2: grouped operators.
# --------------------------------------------------------------------------

_GROUPED_DENY = (
    pytest.param("cat x |& tee .env", id="pipe-and"),
    pytest.param("cat x &>> .env", id="both-append"),
    pytest.param("cat x >& .env", id="duplicate-to-a-file"),
    pytest.param("cat x <> .env", id="read-write"),
    pytest.param("cat x &>>.env", id="both-append-glued"),
    pytest.param("cat x >&.env", id="duplicate-to-a-file-glued"),
    pytest.param("cat x <>.env", id="read-write-glued"),
    pytest.param("cat x 2>&.env", id="stderr-duplicate-to-a-file"),
    pytest.param("cat x |& cat |& tee .env", id="two-pipe-ands"),
    pytest.param("cat x 2>&1 |& tee .env", id="duplicate-then-pipe-and"),
    pytest.param("cat x |&\ntee .env", id="pipe-and-line-end"),
    pytest.param("cat x |& tee .env | cat", id="pipe-and-then-pipe"),
    pytest.param("echo a |& rm .env", id="pipe-and-into-rm"),
    pytest.param("cat x 2>&1 >& .env", id="duplicate-then-duplicate-to-a-file"),
)


@pytest.mark.parametrize("command", _GROUPED_DENY)
def test_scanner_finds_the_write_behind_a_grouped_operator(command: str) -> None:
    assert _hit(command)


@pytest.mark.parametrize("target_id", _CLIENTS)
@pytest.mark.parametrize(
    "command",
    (
        pytest.param("cat x |& tee .env", id="pipe-and"),
        pytest.param("cat x &>> .env", id="both-append"),
        pytest.param("cat x >& .env", id="duplicate-to-a-file"),
        pytest.param("cat x <> .env", id="read-write"),
    ),
)
def test_protect_files_denies_a_grouped_operator_write_on_every_client(
    tmp_path: Path, target_id: str, command: str
) -> None:
    process = _run_protect_files(
        _client_bash_payload(target_id, command), tmp_path, target_id
    )
    assert _protect_decision(process) == "deny", process.stdout


@pytest.mark.parametrize(
    "command, expected",
    (
        pytest.param(
            "cat x |& tee out.txt", [["cat", "x"], ["tee", "out.txt"]], id="pipe"
        ),
        pytest.param("a |& b |& c", [["a"], ["b"], ["c"]], id="two-pipes"),
        pytest.param("a |&\n b", [["a"], ["b"]], id="newline-after-the-pipe"),
        pytest.param("a &>> b", [["a", "&>>", "b"]], id="both-append-and-target"),
        pytest.param("a >& 2", [["a", ">&", "2"]], id="duplicate-and-fd"),
    ),
)
def test_split_segments_reads_the_grouped_operators(
    command: str, expected: list[list[str]]
) -> None:
    assert PROTECT_FILES.split_segments(command) == expected


# --------------------------------------------------------------------------
# BF-I3: an inline sed script that writes a file.
# --------------------------------------------------------------------------

_SED_DENY = (
    pytest.param("sed -n 'w .env' README.md", id="w-command"),
    pytest.param("sed 's/a/b/w .env' README.md", id="s-flag-w"),
    pytest.param("sed -e 'w .env' README.md", id="e-script"),
    pytest.param("sed --expression='w .env' README.md", id="long-option-attached"),
    pytest.param("sed --expression 'w .env' README.md", id="long-option-separate"),
    pytest.param("sed -ne 'w .env' README.md", id="combined-short-options"),
    pytest.param("sed -n -e p -e 'W .env' README.md", id="second-e-script-capital-w"),
    pytest.param("sed -n '/data/w .env' README.md", id="address-then-w"),
    pytest.param("sed '1p;w .env' README.md", id="w-after-a-semicolon"),
    pytest.param("sed -n '1,1{w .env\n}' README.md", id="w-in-a-block"),
    pytest.param("sed 's/a/b/gw .env' README.md", id="flags-then-w"),
    pytest.param("sed -E 's/(a)/\\1/w .env' README.md", id="extended-regex-s-w"),
    pytest.param("sed 's|a|b|w .env' README.md", id="other-delimiter-s-w"),
    pytest.param("sed -n 'w.env' README.md", id="w-without-a-space"),
    pytest.param("sed -n 'W .env' README.md", id="capital-w"),
    pytest.param("sed -n '1!W .env' README.md", id="negated-address-then-w"),
    pytest.param("sed -s -n 'w .env' README.md", id="separate-option-then-w"),
    pytest.param("sed -nE 's/(d)/\\1/w .env' README.md", id="combined-flags-s-w"),
    pytest.param("sed -n -- 'w .env' README.md", id="after-double-dash"),
    pytest.param("sed -n 'w .env' < README.md", id="stdin-input"),
    pytest.param("cat x | sed -n 'w .env'", id="sed-in-a-pipeline"),
    pytest.param("sed -n 'w .env' README.md | head", id="sed-then-pipe"),
    pytest.param("sed -n 'w .claude/settings.json' README.md", id="w-to-a-hook-config"),
)


@pytest.mark.parametrize("command", _SED_DENY)
def test_scanner_finds_the_file_an_inline_sed_script_writes(command: str) -> None:
    assert _hit(command)


@pytest.mark.parametrize("target_id", _CLIENTS)
def test_protect_files_denies_an_inline_sed_write_on_every_client(
    tmp_path: Path, target_id: str
) -> None:
    process = _run_protect_files(
        _client_bash_payload(target_id, "sed -n 'w .env' README.md"),
        tmp_path,
        target_id,
    )
    assert _protect_decision(process) == "deny", process.stdout


@pytest.mark.parametrize("target_id, expected", CLIENT_CONFIG_DECISIONS)
def test_protect_files_gates_an_inline_sed_write_to_a_hook_config(
    tmp_path: Path, target_id: str, expected: str
) -> None:
    process = _run_protect_files(
        _client_bash_payload(target_id, "sed -n 'w .claude/settings.json' README.md"),
        tmp_path,
        target_id,
    )
    assert _protect_decision(process) == expected, process.stdout


_SED_ALLOW = (
    pytest.param("sed -n '1p' README.md", id="print-a-line"),
    pytest.param("sed 's/a/b/' README.md", id="substitute"),
    pytest.param("sed -n '/w .env/p' README.md", id="w-inside-a-regex"),
    pytest.param("sed 's/w .env/b/' README.md", id="w-inside-the-s-regex"),
    pytest.param("sed 'y/w/x/' README.md", id="transliterate"),
    pytest.param("sed 's/a/w .env/' README.md", id="w-inside-the-replacement"),
    pytest.param("sed -n '$p' README.md", id="print-the-last-line"),
    pytest.param("sed 's/a/b/g;s/c/d/' README.md", id="two-substitutions"),
    pytest.param("sed -n 's/a/b/p' README.md", id="substitute-and-print"),
    pytest.param("sed -E 's/(a|b)/\\1/g' README.md", id="extended-regex"),
    pytest.param("sed -n 'w /dev/stdout' README.md", id="write-to-stdout"),
    pytest.param("sed -n 'r .env' README.md", id="read-a-file"),
    pytest.param("sed -n 'a w .env' README.md", id="append-text"),
    pytest.param("sed '1d' README.md", id="delete-a-line"),
    pytest.param("cat .env | sed -n '1p'", id="sed-reads-a-pipe"),
    pytest.param("sed -n -e '1p' -e '2p' README.md", id="two-e-scripts"),
    pytest.param("sed --quiet --expression='1p' README.md", id="long-options"),
)


@pytest.mark.parametrize("command", _SED_ALLOW)
def test_scanner_allows_sed_scripts_that_write_nothing(command: str) -> None:
    assert not _hit(command)


# --------------------------------------------------------------------------
# BF-I4: an unmodelled command after `cd` is resolved against the `cd` folder.
# --------------------------------------------------------------------------

_CD_DENY = (
    pytest.param(
        "cd .claude/hooks/scripts && bash openwiki-guard.sh post </dev/null",
        id="bash-runs-a-hook-script",
    ),
    pytest.param(
        "cd .claude/hooks/scripts && ./openwiki-guard.sh post", id="run-a-hook-script"
    ),
    pytest.param(
        "cd .claude/hooks/scripts; sh openwiki-guard.sh post", id="sh-semicolon"
    ),
    pytest.param(
        "cd .claude/hooks/scripts && python3 helper.py", id="python-runs-a-hook-file"
    ),
    pytest.param(
        "(cd .claude/hooks/scripts && bash openwiki-guard.sh post)", id="subshell"
    ),
    pytest.param("cd .claude && cd hooks && bash scripts/x.sh", id="two-cds"),
    pytest.param("cd .claude/hooks && cd scripts && bash x.sh", id="two-cds-nested"),
    pytest.param("cd docs && cd ../.claude/hooks && bash x.sh", id="cd-up-and-down"),
    # The same commands spelled from the repository root were already denied.
    pytest.param(
        "bash .claude/hooks/scripts/openwiki-guard.sh post </dev/null", id="bash-direct"
    ),
    pytest.param(
        ".claude/hooks/scripts/openwiki-guard.sh post </dev/null", id="direct"
    ),
    pytest.param(
        "./.claude/hooks/scripts/openwiki-guard.sh post", id="dot-slash-direct"
    ),
    pytest.param(
        "cd .claude/hooks/scripts && bash -c 'sh openwiki-guard.sh'", id="bash-c"
    ),
    # A compound command keyword before the cd does not hide it.
    pytest.param(
        "if true; then cd .claude/hooks/scripts && bash openwiki-guard.sh post; fi",
        id="cd-after-then",
    ),
    pytest.param("{ cd .claude && cmd settings.json; }", id="cd-after-a-brace"),
    pytest.param(
        "for i in 1; do cd .claude && cmd settings.json; done", id="cd-after-do"
    ),
    pytest.param(
        "while false; do cd .claude; done; cmd settings.json", id="cd-in-while"
    ),
)


@pytest.mark.parametrize("command", _CD_DENY)
def test_scanner_finds_a_hook_script_named_after_cd(command: str) -> None:
    assert _hit(command)


@pytest.mark.parametrize("target_id", _CLIENTS)
def test_protect_files_denies_running_a_hook_script_after_cd_on_every_client(
    tmp_path: Path, target_id: str
) -> None:
    command = "cd .claude/hooks/scripts && bash openwiki-guard.sh post </dev/null"
    process = _run_protect_files(
        _client_bash_payload(target_id, command), tmp_path, target_id
    )
    assert _protect_decision(process) == "deny", process.stdout


@pytest.mark.parametrize("target_id, expected", CLIENT_CONFIG_DECISIONS)
@pytest.mark.parametrize(
    "command",
    (
        pytest.param("cd .claude && patch settings.json fix.diff", id="patch"),
        pytest.param("cd .claude && jq . settings.json", id="jq-reads-it"),
        pytest.param("cd .claude && sponge settings.json", id="sponge"),
    ),
)
def test_protect_files_gates_an_unmodelled_command_that_names_a_config_after_cd(
    tmp_path: Path, target_id: str, expected: str, command: str
) -> None:
    """`patch` writes its operand in place and the guard has no model for it. A
    path found only through the `cd` folder is new coverage, so it gets the
    protected-config decision (as `git -C .claude restore settings.json` does), not
    the deny of an interpreter that runs a script."""
    process = _run_protect_files(
        _client_bash_payload(target_id, command), tmp_path, target_id
    )
    assert _protect_decision(process) == expected, process.stdout
    assert ".claude/settings.json" in process.stdout


_CD_ALLOW = (
    pytest.param("cd .claude/hooks/scripts && ls", id="list-the-folder"),
    pytest.param("cd docs && patch notes.md fix.diff", id="patch-an-ordinary-file"),
    pytest.param("cd .claude && cat settings.json", id="read-a-config"),
    pytest.param("cd docs && python3 -c 'print(1)'", id="python-in-docs"),
    pytest.param("cd docs && bash ../scripts/build.sh", id="bash-a-script-outside"),
    pytest.param("cd docs && foo --bar baz", id="unmodelled-with-plain-operands"),
    pytest.param("cd .claude/hooks/scripts && cd ../../.. && ls", id="cd-back-out"),
    pytest.param("cd /tmp && foo x.txt", id="cd-elsewhere"),
)


@pytest.mark.parametrize("command", _CD_ALLOW)
def test_scanner_allows_an_unmodelled_command_after_a_harmless_cd(command: str) -> None:
    assert not _hit(command)


# --------------------------------------------------------------------------
# BF-I7 and finding R10: the forms the Phase H sweep listed as unchecked.
# --------------------------------------------------------------------------

_R9_DENY = (
    # ANSI-C escapes that spell the name.
    pytest.param("touch $'\\x2eenv'", id="ansi-c-hex"),
    pytest.param("tee $'\\056env'", id="ansi-c-octal"),
    pytest.param("touch $'.\\u0065nv'", id="ansi-c-unicode"),
    pytest.param("touch $'\\x2e\\x65nv'", id="ansi-c-two-hex"),
    pytest.param("touch $'\\U0000002eenv'", id="ansi-c-long-unicode"),
    pytest.param("rm -f $'\\056\\145nv'", id="ansi-c-octal-name"),
    pytest.param("echo x > $'\\x2eenv'", id="ansi-c-redirect-target"),
    # Heredoc delimiters read in full.
    pytest.param("bash <<END-OF-DATA\ntee .env\nEND-OF-DATA", id="dashed-delimiter"),
    pytest.param("bash <<EOF#x\ntee .env\nEOF#x", id="hash-in-the-delimiter"),
    pytest.param("bash <<'A B'\ntee .env\nA B", id="delimiter-with-a-blank"),
    pytest.param('bash <<E"O"F\ntee .env\nEOF', id="partly-quoted-delimiter"),
    pytest.param("bash <<\\EOF\ntee .env\nEOF", id="backslash-quoted-delimiter"),
    pytest.param(
        "bash <<END-OF-DATA\necho hi\nEND\ntee .env\nEND-OF-DATA",
        id="short-prefix-line-inside-the-body",
    ),
    pytest.param("bash <<-EOF\n\ttee .env\n\tEOF", id="tab-stripping-delimiter"),
    # A function or an alias that hides a write.
    pytest.param('cat() { tee "$@"; }; cat .env', id="function-named-cat"),
    pytest.param("alias cat='tee'; cat .env", id="alias-named-cat"),
    pytest.param('function grep { tee "$@"; }; grep .env', id="function-keyword"),
    pytest.param('head() { tee "$@"; }\nhead .env', id="function-on-an-earlier-line"),
    pytest.param("rm() { echo no; }; unalias rm; rm .env", id="function-then-rm"),
    pytest.param('wc() { tee "$@"; }; (wc .env)', id="function-then-group"),
    pytest.param('sed() { tee "$@"; }; sed .env', id="function-named-sed"),
    # $IFS word splitting.
    pytest.param("tee$IFS.env", id="ifs-then-name"),
    pytest.param("tee${IFS}.env", id="braced-ifs-then-name"),
    pytest.param("rm$IFS-f$IFS.env", id="ifs-between-words"),
    pytest.param("touch$IFS''.env", id="ifs-then-empty-quotes"),
    pytest.param("cat x;tee$IFS.env", id="ifs-after-a-semicolon"),
    # A name built by a command.
    pytest.param("tee $(echo .e)nv", id="command-then-tail"),
    pytest.param("tee .e$(echo n)v", id="head-command-tail"),
    pytest.param("touch cred$(echo entials).json", id="credentials-prefix"),
    pytest.param("tee x$(echo .p)em", id="pem-suffix"),
    pytest.param("rm $(echo .e)nv", id="remove-a-built-name"),
    pytest.param("echo x > $(echo .e)nv", id="redirect-to-a-built-name"),
    pytest.param("tee `echo .e`nv", id="backticks-then-tail"),
    pytest.param('tee "$(echo .e)nv"', id="quoted-command-then-tail"),
    # Replacement and default words of an unassigned name.
    pytest.param("tee ${x/#/.env}", id="replace-the-start"),
    pytest.param("tee ${x//a/.env}", id="replace-all"),
    pytest.param('tee "${x/%/.env}"', id="replace-the-end-quoted"),
    pytest.param("tee ${x/a/.env}", id="replace-first"),
    pytest.param("tee .e${x/#/nv}", id="replace-completes-the-name"),
    # A value with blanks splits into words when it is not quoted.
    pytest.param('x="a .env"; tee $x', id="value-with-a-blank-splits"),
    pytest.param('x=".env a"; rm $x', id="name-first-in-the-value"),
    pytest.param('x="tee .env"; $x', id="variable-holds-the-whole-command"),
    pytest.param('a=".env x"; touch $a', id="array-name-splits"),
    pytest.param('IFS=,; x="a,.env"; tee $x', id="custom-ifs-splits"),
    pytest.param("tee ${x:-a .env}", id="default-word-with-a-blank"),
    # An operation on a tracked variable is applied, not skipped.
    # A brace list in the command word is several words: the command and its names.
    pytest.param("{tee,.env}", id="brace-command-tee"),
    pytest.param("{rm,-f,.env}", id="brace-command-rm"),
    pytest.param("echo x | {tee,.env}", id="brace-command-after-a-pipe"),
    pytest.param("tee |& {tee,.env}", id="brace-command-after-a-pipe-and"),
    pytest.param("te{e,e} .env", id="brace-inside-the-command-name"),
    pytest.param("{git,restore,.env}", id="brace-command-git"),
    pytest.param("{ {tee,.env}; }", id="brace-command-in-a-group"),
    pytest.param("{tee,.claude/settings.json}", id="brace-command-config"),
    # A name appended to before it was assigned.
    pytest.param("x+=.env; tee $x", id="append-to-an-unassigned-name"),
    # Operations on `$IFS` still give blanks.
    pytest.param("tee${IFS:0:1}.env", id="ifs-first-character"),
    pytest.param("tee${IFS%?}.env", id="ifs-cut-suffix"),
    pytest.param("tee$IFS$IFS.env", id="two-ifs"),
    # A keyword before the command does not hide it.
    pytest.param("{ tee .env; }", id="after-a-brace"),
    pytest.param("for i in 1; do tee .env; done", id="after-do"),
    pytest.param("if true; then rm x; else tee .env; fi", id="after-else"),
    # A variable built from a tracked one is tracked.
    pytest.param("x=env; y=.$x; tee $y", id="chained-assignment"),
    pytest.param("x=env y=.$x; tee $y", id="assignments-in-one-command"),
)


@pytest.mark.parametrize("command", _R9_DENY)
def test_scanner_finds_the_write_hidden_by_an_r9_form(command: str) -> None:
    assert _hit(command)


_R9_ALLOW = (
    pytest.param("touch $'out\\x2etxt'", id="ansi-c-harmless-name"),
    pytest.param("echo $'a\\nb'", id="ansi-c-newline"),
    pytest.param(
        "bash <<END-OF-DATA\necho hi\nEND-OF-DATA", id="dashed-delimiter-harmless"
    ),
    pytest.param(
        "bash <<END-OF-DATA\necho hi\nEND\nEND-OF-DATA", id="short-prefix-line-harmless"
    ),
    pytest.param("cat <<EOF#x\nbody\nEOF#x", id="hash-delimiter-harmless"),
    pytest.param("cat() { echo hi; }; cat README.md", id="function-named-cat-harmless"),
    pytest.param("alias ll='ls -l'; ll", id="alias-harmless"),
    pytest.param('echo "$IFS"', id="quoted-ifs"),
    pytest.param('echo "a${IFS}b"', id="quoted-braced-ifs"),
    pytest.param("echo a$IFS-b", id="ifs-between-plain-words"),
    pytest.param("touch file-$(date +%s).txt", id="date-in-a-name"),
    pytest.param("tee out-$(echo 1).log", id="number-in-a-name"),
    pytest.param("rm $(pwd)/x", id="directory-command"),
    pytest.param("tee $(mktemp)", id="whole-word-command"),
    pytest.param("cp x $(dirname y)/z", id="dirname-prefix"),
    pytest.param("touch v$(echo 1)", id="short-prefix-command"),
    pytest.param("tee ${x/a/b}", id="replace-harmless"),
    pytest.param('x="a .env"; tee "$x"', id="quoted-value-is-one-word"),
    pytest.param('x="a b"; echo $x', id="split-value-harmless"),
    pytest.param("IFS=; x='a b'; echo $x", id="empty-ifs-harmless"),
    pytest.param(
        'while IFS= read -r line; do echo "$line"; done < README.md',
        id="read-with-an-empty-ifs",
    ),
    pytest.param("IFS=, read a b < README.md; echo $a", id="read-with-a-comma-ifs"),
    pytest.param("x=env; y=.$x; echo done", id="chained-assignment-unused"),
    pytest.param("{echo,hi}", id="brace-command-harmless"),
    pytest.param("{ls,-la}", id="brace-command-ls"),
    pytest.param("cp x {a,b}", id="brace-in-an-argument-harmless"),
    pytest.param("for f in a b; do echo $f; done", id="for-loop-harmless"),
    pytest.param("if [ -f x ]; then cat x; fi", id="if-harmless"),
    pytest.param("echo${IFS:0:1}hi", id="ifs-operation-harmless"),
)


@pytest.mark.parametrize("command", _R9_ALLOW)
def test_scanner_allows_the_harmless_twin_of_an_r9_form(command: str) -> None:
    assert not _hit(command)


def test_scanner_reads_a_dashed_heredoc_delimiter_in_full() -> None:
    text, bodies = PROTECT_FILES.extract_heredocs(
        "cat <<END-OF-DATA\nEND\nx\nEND-OF-DATA\n"
    )
    assert [body for body, _quoted in bodies.values()] == ["END\nx\n"]
    text, bodies = PROTECT_FILES.extract_heredocs("cat <<EOF#x\na\nEOF\nb\nEOF#x\n")
    assert [body for body, _quoted in bodies.values()] == ["a\nEOF\nb\n"]
    text, bodies = PROTECT_FILES.extract_heredocs('cat <<E"O"F\nq\nEOF\n')
    assert [(body, quoted) for body, quoted in bodies.values()] == [("q\n", True)]
    text, bodies = PROTECT_FILES.extract_heredocs("cat <<\\EOF\nq\nEOF\n")
    assert [(body, quoted) for body, quoted in bodies.values()] == [("q\n", True)]
    text, bodies = PROTECT_FILES.extract_heredocs("cat <<EOF\nq\nEOF\n")
    assert [(body, quoted) for body, quoted in bodies.values()] == [("q\n", False)]


@pytest.mark.parametrize(
    "command, expected",
    (
        pytest.param("touch $'\\x2eenv'", [["touch", ".env"]], id="hex"),
        pytest.param("touch $'\\056env'", [["touch", ".env"]], id="octal"),
        pytest.param("touch $'.\\u0065nv'", [["touch", ".env"]], id="unicode"),
        pytest.param("echo $'a\\tb\\n'", [["echo", "a\tb\n"]], id="tab-and-newline"),
        pytest.param("echo $'it\\'s'", [["echo", "it's"]], id="escaped-quote"),
        pytest.param("echo $'\\\\x41'", [["echo", "\\x41"]], id="escaped-backslash"),
        pytest.param("echo $'\\x41\\101'", [["echo", "AA"]], id="hex-and-octal-letter"),
        pytest.param("echo $'\\q'", [["echo", "\\q"]], id="unknown-escape-stays"),
        pytest.param("tee$IFS.env", [["tee", ".env"]], id="ifs-splits-the-word"),
        pytest.param(
            "tee${IFS}.env", [["tee", ".env"]], id="braced-ifs-splits-the-word"
        ),
        pytest.param(
            'echo "a$IFS.b"',
            [["echo", PROTECT_FILES.QUOTED_VALUE_PREFIX + "a$IFS.b"]],
            id="quoted-ifs-does-not-split",
        ),
        pytest.param("echo $IFS", [["echo"]], id="ifs-alone-is-nothing"),
    ),
)
def test_split_segments_decodes_ansi_c_and_splits_on_ifs(
    command: str, expected: list[list[str]]
) -> None:
    assert PROTECT_FILES.split_segments(command) == expected


def test_scanner_expands_a_glob_glued_to_a_variable(tmp_path: Path) -> None:
    """The unquoted glob in `"$X".e*` still expands, to `.env` when it exists."""
    (tmp_path / ".env").write_text("", encoding="utf-8")
    for command in (
        'tee "$X".e*',
        "tee $X.e*",
        'tee "$X".en?',
        "tee ${X}.e[n]v",
        'tee "$X".env*',
        'touch "${X:-}".e*',
    ):
        assert _hit(command, tmp_path), command
    for command in ('tee "$X".x*', "tee $X.zz*", 'tee "$X"*.log'):
        assert not _hit(command, tmp_path), command


def test_scanner_expands_a_quoted_glob_in_the_word_of_a_duplicate_redirect(
    tmp_path: Path,
) -> None:
    """Bash globs the word of `>& word` even when it is quoted (`cat >& '.e*'`
    writes `.env`), unlike the word of `>` or `&>`."""
    (tmp_path / ".env").write_text("", encoding="utf-8")
    for command in (
        "cat x >& '.e*'",
        'cat x >& ".en?"',
        "cat x >& '.e[n]v'",
        "cat x >& \\.e*",
    ):
        assert _hit(command, tmp_path), command
    for command in (
        "cat x > '.e*'",
        "cat x &> '.e*'",
        "cat x >> '.e*'",
        "cat x >& '.x*'",
    ):
        assert not _hit(command, tmp_path), command


_FAIL_CLOSED = (
    pytest.param("shopt -s dotglob; tee *", "dotglob", id="dotglob-then-star"),
    pytest.param("shopt -s dotglob nullglob\nrm *", "dotglob", id="dotglob-nullglob"),
    pytest.param("shopt -s extglob dotglob; ls *", "dotglob", id="extglob-dotglob"),
    pytest.param("GLOBIGNORE=x; tee *", "dotglob", id="globignore"),
    pytest.param("setopt glob_dots; tee *", "dotglob", id="zsh-glob-dots"),
    pytest.param("setopt dotglob; tee *", "dotglob", id="zsh-dotglob"),
    pytest.param("echo ${(e)x}", "zsh", id="zsh-evaluate-flag"),
    pytest.param('echo "${(P)x}"', "zsh", id="zsh-indirect-flag-quoted"),
    pytest.param("cat *(e:'touch .env':)", "qualifier", id="zsh-code-qualifier"),
    pytest.param("ls *(e:'rm x':)", "qualifier", id="zsh-code-qualifier-on-ls"),
    pytest.param("cat **/*(.e:'tee .env':)", "qualifier", id="zsh-dot-then-e"),
    pytest.param("cat *(+tee)", "qualifier", id="zsh-function-qualifier"),
    pytest.param("cat *(N+fn)", "qualifier", id="zsh-null-then-function"),
    pytest.param("cat ?(om[1]e:'x':)", "qualifier", id="zsh-order-then-e"),
    pytest.param("cat @(a|e|b)", "qualifier", id="single-e-alternative-is-refused-too"),
    pytest.param("cd a; " * 80 + "cmd x", "too many", id="many-different-folders"),
    pytest.param(
        "".join("pushd d%d; " % i for i in range(80)) + "cmd x",
        "too many",
        id="many-pushd-folders",
    ),
    pytest.param(
        "env " + "".join("-C d%d " % i for i in range(80)) + "cmd x",
        "too many",
        id="many-env-folders",
    ),
    pytest.param(
        "{a,b}" * 12 + " x", "too complex|brace list", id="brace-command-too-long"
    ),
)


@pytest.mark.parametrize("command, message", _FAIL_CLOSED)
def test_scanner_fails_closed_on_forms_only_another_shell_reads(
    command: str, message: str
) -> None:
    with pytest.raises(PROTECT_FILES.UnparseableCommand, match=message):
        PROTECT_FILES.shell_targets(command, str(REPO_ROOT))


_FAIL_CLOSED_ALLOW = (
    pytest.param("shopt -s nullglob; ls *", id="nullglob-only"),
    pytest.param("shopt -u dotglob; ls *", id="dotglob-off"),
    pytest.param("shopt -q dotglob; ls *", id="dotglob-query"),
    pytest.param("echo dotglob", id="the-word-alone"),
    pytest.param("cat *(.)", id="plain-qualifier"),
    pytest.param("ls @(a|b)", id="extglob-alternatives"),
    pytest.param("ls *(a)", id="extglob-star-group"),
    pytest.param("echo ${x:-(a)}", id="paren-in-a-default"),
    pytest.param("echo ${#x}", id="length-expansion"),
    pytest.param("cat +(a|b)", id="extglob-plus"),
    pytest.param("cd a; " * 20 + "cmd x", id="twenty-folders"),
    pytest.param("{a,b}{c,d}{e,f} x", id="short-brace-command"),
)


@pytest.mark.parametrize("command", _FAIL_CLOSED_ALLOW)
def test_scanner_still_reads_the_harmless_twin_of_a_fail_closed_form(
    command: str,
) -> None:
    assert not _hit(command)


# find: -delete and a mutating -exec act on every match.
_FIND_DENY = (
    pytest.param("find . -delete", id="delete-everything"),
    pytest.param("find . -type f -delete", id="delete-every-file"),
    pytest.param("find . -name '*' -delete", id="star-pattern"),
    pytest.param("find . -name '*.pem' -delete", id="pem-pattern"),
    pytest.param("find . -exec rm {} +", id="exec-rm-plus"),
    pytest.param("find . -exec rm -f {} \\;", id="exec-rm-semicolon"),
    pytest.param("find . -name '.env*' -delete", id="env-pattern"),
    pytest.param("find . -mtime +3 -delete", id="age-only"),
    pytest.param("find . -exec mv {} /tmp/x \\;", id="exec-mv"),
    pytest.param("find . -execdir rm {} +", id="execdir-rm"),
    pytest.param("find . -ok rm {} \\;", id="ok-rm"),
    pytest.param("find . -name '*' -exec tee {} +", id="exec-tee"),
    pytest.param("find . -iname '*.KEY' -delete", id="case-insensitive-name"),
    pytest.param("find .claude -name settings.json -delete", id="config-name-delete"),
    pytest.param(
        "find . -name 'settings*' -exec rm {} +", id="config-name-pattern-exec"
    ),
    pytest.param("find . -path './.claude/*' -delete", id="path-pattern"),
    pytest.param("find . ! -name '*.keep' -delete", id="negated-name"),
    pytest.param(
        "find . -name '*.pyc' -o -type f -delete", id="or-with-an-open-branch"
    ),
    pytest.param("find . -path ./x -prune -o -type f -delete", id="prune-then-delete"),
    pytest.param("find . \\( -name '*.pyc' \\) -o -delete", id="grouped-or-delete"),
    pytest.param("find . -name credentials* -delete", id="unquoted-credentials-glob"),
    pytest.param("find /tmp/x -delete", id="other-folder-delete-everything"),
    pytest.param("find . -name x -exec sh -c 'rm .env' {} \\;", id="exec-shell-script"),
    pytest.param("cd docs && find . -delete", id="after-cd"),
    pytest.param("find . -type f -exec chmod 600 {} +", id="exec-chmod"),
    pytest.param("find . -exec tee x {} \\;", id="exec-tee-a-file"),
    pytest.param("find . -regex '.*' -delete", id="regex-everything"),
    pytest.param("find . -name '.e*' -delete", id="dot-e-glob"),
    pytest.param(
        "find . -name '*.json' -delete", id="json-names-include-the-hook-configs"
    ),
)


@pytest.mark.parametrize("command", _FIND_DENY)
def test_scanner_denies_find_that_deletes_or_mutates_what_it_matches(
    command: str,
) -> None:
    assert _hit(command)


_FIND_ALLOW = (
    pytest.param("find . -name '*.pyc' -delete", id="pyc-delete"),
    pytest.param("find . -name '*.log' -exec rm {} +", id="log-exec-rm"),
    pytest.param("find . -type f -name '*.tmp' -delete", id="type-and-tmp"),
    pytest.param("find . -type d -empty -delete", id="empty-directories"),
    pytest.param("find . -exec grep x {} \\; | head -1", id="exec-grep"),
    pytest.param("find . -name '*.md' -exec cat {} +", id="exec-cat"),
    pytest.param(
        "find . -name '*.py' -exec sed -i 's/a/b/' {} +", id="exec-sed-in-place-py"
    ),
    pytest.param("find . -name '*.py' -print", id="print"),
    pytest.param("find . -name '*.pyc' -name '*.x' -delete", id="two-names-and"),
    pytest.param("find . -iname '*.PYC' -delete", id="iname-pyc"),
    pytest.param("find . -name '*.tmp' -delete -print", id="delete-then-print"),
    pytest.param(
        "find . -name node_modules -type d -exec rm -rf {} +", id="node-modules"
    ),
    pytest.param("find . -name '*.pem'", id="plain-pem-search"),
    pytest.param("find . -type f", id="list-files"),
    pytest.param("find . -name '*.o' -exec ls -l {} \\;", id="exec-ls"),
)


@pytest.mark.parametrize("command", _FIND_ALLOW)
def test_scanner_allows_find_whose_names_cannot_match_a_protected_file(
    command: str,
) -> None:
    assert not _hit(command)


@pytest.mark.parametrize("target_id", _CLIENTS)
def test_protect_files_denies_find_delete_on_every_client(
    tmp_path: Path, target_id: str
) -> None:
    process = _run_protect_files(
        _client_bash_payload(target_id, "find . -type f -delete"), tmp_path, target_id
    )
    assert _protect_decision(process) == "deny", process.stdout


# --------------------------------------------------------------------------
# Review round 2.
# --------------------------------------------------------------------------

_MESSAGE_HEAD = "git commit -m \"$(cat <<'EOF'"
_PIPED_MESSAGE_DENY = (
    pytest.param(_MESSAGE_HEAD + ' | sh\ntee .env\nEOF\n)"', id="piped-to-sh"),
    pytest.param(_MESSAGE_HEAD + ' | bash\ntee .env\nEOF\n)"', id="piped-to-bash"),
    pytest.param(_MESSAGE_HEAD + ' | xargs tee\n.env\nEOF\n)"', id="piped-to-xargs"),
    pytest.param(
        _MESSAGE_HEAD + " | python3 -\nopen('.env','w')\nEOF\n)\"", id="piped-to-python"
    ),
    pytest.param(_MESSAGE_HEAD + ' |& sh\ntee .env\nEOF\n)"', id="piped-with-stderr"),
    pytest.param(_MESSAGE_HEAD + '; tee .env\nx\nEOF\n)"', id="semicolon-command"),
    pytest.param(_MESSAGE_HEAD + ' && tee .env\nx\nEOF\n)"', id="and-command"),
    pytest.param(_MESSAGE_HEAD + ' || tee .env\nx\nEOF\n)"', id="or-command"),
    pytest.param(
        _MESSAGE_HEAD + ' | sh\nx\nEOF\ntee .env)"', id="pipe-then-another-command"
    ),
)


@pytest.mark.parametrize("command", _PIPED_MESSAGE_DENY)
def test_scanner_reads_a_message_heredoc_that_goes_somewhere_else_as_a_script(
    command: str,
) -> None:
    assert _hit(command)


def test_scanner_still_reads_a_message_heredoc_alone_as_message_text() -> None:
    assert not _hit(_MESSAGE_HEAD + '\nmention .env here\nEOF\n)"')
    # Recorded over-block: any pipe after the heredoc makes it a script for the scanner.
    assert _hit(_MESSAGE_HEAD + ' | head -1\nmention .env here\nEOF\n)"')


@pytest.mark.parametrize(
    "head",
    (
        pytest.param("git commit -m", id="commit"),
        pytest.param("git tag -a v1 -m", id="tag"),
        pytest.param("git merge -m", id="merge"),
        pytest.param("git notes add -m", id="notes"),
        pytest.param("git stash push -m", id="stash"),
    ),
)
def test_scanner_reads_the_message_heredoc_of_a_message_taking_git_command_as_text(
    head: str,
) -> None:
    assert not _hit(head + " \"$(cat <<'EOF'\nmention .env here\nEOF\n)\"")
    assert _hit(head + " \"$(cat <<'EOF' | sh\ntee .env\nEOF\n)\"")


def test_scanner_reads_other_text_in_a_message_as_a_command_line() -> None:
    """Recorded: only a `cat` heredoc is message text; `$(echo '.env')` is a command."""
    assert _hit("git commit -m \"$(echo 'mention .env')\"")
    assert not _hit('git commit -m "mention .env here"')
    assert not _hit("git commit -F - <<'EOF'\nmention .env here\nEOF")


# A variable assigned earlier on the line is not evaluated for an operation, an array
# subscript, or an indirection: the guard refuses instead of guessing what it holds.
_TRACKED_REFUSED = (
    pytest.param("x='.e-n-v'; tee \"${x//[^a-z.]/}\"", id="bracket-negation"),
    pytest.param('x=Xenv; tee "${x/#[[:upper:]]/.}"', id="posix-class"),
    pytest.param("x='\\x2eenv'; tee \"${x@E}\"", id="transform-escapes"),
    pytest.param('x=.ENV; tee "${x@L}"', id="transform-lower"),
    pytest.param("x=abc.env; tee ${x#abc}", id="cut-prefix"),
    pytest.param("x=aa.env; tee ${x##*a}", id="cut-longest-prefix"),
    pytest.param("x=.env.bak; tee ${x%.bak}", id="cut-suffix"),
    pytest.param("x=zz.env; tee ${x:2}", id="substring"),
    pytest.param("x=a.env; tee ${x: -4}", id="negative-offset"),
    pytest.param("x=.ENV; tee ${x,,}", id="lower-case"),
    pytest.param("x=.env; tee ${x//e/e}", id="replace-all"),
    pytest.param("x=env; tee ${x/#/.}", id="replace-the-start"),
    pytest.param("x=a; tee ${x/a/.env}", id="replace-first"),
    pytest.param("x=env; y=${x/#/.}; tee $y", id="operation-in-an-assignment"),
    pytest.param("x=a; tee ${x:-.env}", id="default-on-an-assigned-variable"),
    pytest.param("a=(.env); tee ${a[0]}", id="array-first-element"),
    pytest.param("a=(x .env); tee ${a[1]}", id="array-second-element"),
    pytest.param("a=(.env); tee $a", id="array-name"),
    pytest.param('a=(x .env); tee "${a[@]}"', id="array-all-quoted"),
    pytest.param("a=(x .env); tee ${a[*]}", id="array-all"),
    pytest.param("a=(x\n.env)\ntee ${a[1]}", id="array-over-lines"),
    pytest.param("a=('.env' x); tee ${a[0]}", id="array-quoted-element"),
    pytest.param("a=(x); a+=(.env); tee ${a[1]}", id="array-append"),
    pytest.param("a[1]=.env; tee ${a[1]}", id="array-element-assignment"),
    pytest.param("a=(x .env); tee ${a[@]:1}", id="array-slice"),
    pytest.param("a=(.env); tee ${a[-1]}", id="array-negative-index"),
    pytest.param('a=(.env x); b=("${a[@]}"); tee ${b[0]}', id="array-copy"),
    pytest.param("ref=X; X=.env; tee ${!ref}", id="indirect"),
    pytest.param("declare -a a=(.env); tee ${a[0]}", id="declared-array"),
    pytest.param("x=.env; y=x; tee ${!y}", id="indirect-to-a-variable"),
    # The harmless twins are refused too (recorded over-blocks).
    pytest.param("x=readme.md; echo ${x%.md}", id="harmless-cut"),
    pytest.param("x=a/b/c; echo ${x##*/}", id="harmless-basename"),
    pytest.param("x=abc; echo ${x:1:1}", id="harmless-substring"),
    pytest.param("a=(x y); echo ${a[0]}", id="harmless-array-element"),
    pytest.param("a=(x y); tee $a", id="harmless-array-name"),
    pytest.param("x=a; echo ${x:-b}", id="harmless-default"),
)


@pytest.mark.parametrize("command", _TRACKED_REFUSED)
def test_scanner_refuses_an_operation_on_a_variable_assigned_earlier(
    command: str,
) -> None:
    with pytest.raises(PROTECT_FILES.UnparseableCommand, match="assigned earlier"):
        PROTECT_FILES.shell_targets(command, str(REPO_ROOT))


_TRACKED_READ = (
    pytest.param("x=abc; echo ${#x}", id="length"),
    pytest.param(
        "echo ${y#abc} ${y%x} ${y/a/b} ${y:1}", id="operations-on-an-unknown-name"
    ),
    pytest.param("echo ${y:-z}", id="default-on-an-unknown-name"),
    pytest.param("x=a; echo $x ${x}", id="plain-and-braced"),
    pytest.param("for f in a b; do echo ${f%.md}; done", id="loop-variable"),
    pytest.param("echo ${a[0]} ${!y}", id="subscript-of-an-unknown-name"),
)


@pytest.mark.parametrize("command", _TRACKED_READ)
def test_scanner_still_reads_plain_and_unknown_expansions(command: str) -> None:
    assert not _hit(command)


# A name assigned a different value again on the same line is refused, in any context:
# the guard cannot know which assignment runs (or which value a copy takes).
_ASSIGNED_TWICE_REFUSED = (
    pytest.param("x=.env; false && x=safe; tee $x", id="and-list"),
    pytest.param("x=.env; true || x=safe; tee $x", id="or-list"),
    pytest.param('x=.env; x=safe true; tee "$x"', id="prefix-assignment"),
    pytest.param("x=.env; (x=safe); tee $x", id="subshell"),
    pytest.param("x=.env; x=safe | cat; tee $x", id="pipe"),
    pytest.param("x=.env; x=safe & wait; tee $x", id="background"),
    pytest.param("x=.env; { x=safe; } & wait; tee $x", id="background-group"),
    pytest.param("x=.claude/settings.json; x=.env; tee $x", id="config-then-secret"),
    pytest.param("x=.env; x=out.txt; tee $x", id="overwritten-protected-value"),
    pytest.param("x=.env; x=$(pwd)/a; tee $x", id="overwritten-by-a-substitution"),
    pytest.param("x=.env; x=y; x=z; tee $x", id="overwritten-twice"),
    pytest.param(
        'x=.env; false && x=safe; y=$x; tee "$y"', id="copy-after-conditional"
    ),
    pytest.param('x=.env; x=safe true; y=$x; tee "$y"', id="copy-after-prefix"),
    pytest.param('x=.env; (x=safe); y=$x; tee "$y"', id="copy-after-subshell"),
    pytest.param('x=.env; x=safe | cat; y=$x; tee "$y"', id="copy-after-pipe"),
    pytest.param("a=.e; b=nv; false && a=x; false && b=y; tee $a$b", id="two-names"),
    pytest.param("x=.env; x=a; x=b; x=c; x=d; x=e; tee $x", id="five-reassignments"),
    pytest.param("x=.en; false && x+=q; x+=v; tee $x", id="append-after-conditional"),
    pytest.param("x=.en; x+=v; tee $x", id="string-append"),
    pytest.param('x=a; x+=" .env"; tee $x', id="string-append-with-a-blank"),
    pytest.param("x=a; x+=b; echo $x", id="harmless-string-append"),
    pytest.param("x=a; x=b; echo $x", id="harmless-two-values"),
    pytest.param("x=a.txt; false && x=b.txt; tee $x", id="harmless-conditional"),
    pytest.param("x=a; export x=b", id="export-again"),
    pytest.param("x=a; declare x=b", id="declare-again"),
    pytest.param("x=a; bash -c 'x=b; echo $x'", id="child-shell-reassigns-a-copy"),
    pytest.param("x=a; x=${x#a}", id="reassigned-from-an-operation"),
)


@pytest.mark.parametrize("command", _ASSIGNED_TWICE_REFUSED)
def test_scanner_refuses_a_name_assigned_a_different_value_again(command: str) -> None:
    with pytest.raises(
        PROTECT_FILES.UnparseableCommand, match="assigned twice|assigned earlier"
    ):
        PROTECT_FILES.shell_targets(command, str(REPO_ROOT))


def test_scanner_names_the_second_assignment() -> None:
    with pytest.raises(PROTECT_FILES.UnparseableCommand, match="assigned twice"):
        PROTECT_FILES.shell_targets("x=a; x=b", str(REPO_ROOT))


@pytest.mark.parametrize(
    "command",
    (
        pytest.param('x=.env; y=$x; tee "$y"', id="copy"),
        pytest.param("x=.env; y=$x; z=$y; tee $z", id="copy-of-a-copy"),
        pytest.param("x=env; y=.$x; tee $y", id="copy-with-text"),
        pytest.param("x=.claude/settings.json; y=$x; echo x > $y", id="copy-redirect"),
        pytest.param("x+=.env; tee $x", id="append-to-an-unassigned-name"),
    ),
)
def test_scanner_follows_a_copy_of_a_singly_assigned_value(command: str) -> None:
    assert _hit(command)


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("x=out.txt; tee $x", id="plain"),
        pytest.param("x=a; y=$x; z=$y; echo $z", id="copy-chain"),
        pytest.param("x=a; x=a; echo $x", id="same-value-twice"),
        pytest.param("x=a y=b; echo $x$y", id="two-names-in-one-statement"),
        pytest.param("x+=a; echo $x", id="append-to-an-unassigned-name-harmless"),
    ),
)
def test_scanner_allows_a_value_assigned_once(command: str) -> None:
    assert not _hit(command)


# An assignment reads its own value before the assignment, so it may name itself.
@pytest.mark.parametrize(
    "command",
    (
        pytest.param("PORT=${PORT:-8080} ./run.sh", id="prefix-default"),
        pytest.param('export PATH="${PATH:-/usr/bin}:/opt/bin"', id="export-default"),
        pytest.param(
            "export PYTHONPATH=src${PYTHONPATH:+:$PYTHONPATH}", id="export-alternative"
        ),
        pytest.param("x=$(cmd ${x:-d})", id="substitution-with-a-default"),
        pytest.param("x=${x:-a}; echo $x", id="default-then-plain-reference"),
        pytest.param("PATH=$PATH:/opt/bin cmd", id="prefix-extends-path"),
        pytest.param("export PATH=$PATH:a; echo ${PATH}", id="export-then-braced"),
    ),
)
def test_scanner_allows_an_assignment_that_names_itself(command: str) -> None:
    assert not _hit(command)


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("x=a; echo ${x:-b}", id="default-after-the-assignment"),
        pytest.param("x=a y=$(echo ${x:-q})", id="later-word-reads-the-earlier-one"),
        pytest.param(
            "export x=a; export y=${x:-b}", id="export-reads-an-assigned-name"
        ),
    ),
)
def test_scanner_refuses_a_default_on_a_name_assigned_before(command: str) -> None:
    with pytest.raises(PROTECT_FILES.UnparseableCommand, match="assigned earlier"):
        PROTECT_FILES.shell_targets(command, str(REPO_ROOT))


# shopt, setopt, alias, GLOBIGNORE: read from the scanned words, not from raw text.
_OPTION_REFUSED = (
    pytest.param('shopt "-s" dotglob; tee *env', "dotglob", id="quoted-flag"),
    pytest.param("shopt -s 'dot'glob; tee *env", "dotglob", id="quoted-name"),
    pytest.param("shopt -s -- dotglob; tee *env", "dotglob", id="end-of-options"),
    pytest.param("shopt -s nullglob dotglob; tee *env", "dotglob", id="two-names"),
    pytest.param("shopt -qs dotglob; tee *env", "dotglob", id="quiet-set"),
    pytest.param("eval 'shopt -s dotglob'; tee *env", "dotglob", id="inside-eval"),
    pytest.param("bash -c 'shopt -s dotglob; tee *env'", "dotglob", id="inside-bash-c"),
    pytest.param("GLOBIGNORE='x'; tee *env", "dotglob", id="globignore-quoted"),
    pytest.param("export GLOBIGNORE=x; tee *env", "dotglob", id="globignore-export"),
    pytest.param("GLOBIGNORE=x tee *env", "dotglob", id="globignore-prefix"),
    pytest.param("env GLOBIGNORE=x tee *env", "dotglob", id="globignore-env"),
    pytest.param('setopt "glob_dots"; tee *env', "dotglob", id="setopt-quoted"),
    pytest.param("set -o glob_dots; tee *env", "dotglob", id="zsh-set-option"),
    pytest.param(
        "unsetopt no_glob_dots; tee *env", "dotglob", id="unsetopt-the-negation"
    ),
    pytest.param("setopt GLOB_DOTS; tee *env", "dotglob", id="setopt-upper-case"),
    pytest.param("setopt globdots; tee *env", "dotglob", id="setopt-no-underscore"),
    pytest.param("CDPATH=.claude cd hooks && cmd scripts/x.sh", "CDPATH", id="cdpath"),
    pytest.param("export CDPATH=.claude; cd hooks", "CDPATH", id="cdpath-export"),
    pytest.param("bash -O dotglob -c 'tee *env'", "dotglob", id="bash-O-dotglob"),
    pytest.param("bash -O nullglob -O dotglob -c 'ls'", "dotglob", id="bash-O-second"),
    pytest.param("zsh -o glob_dots -c 'tee *env'", "dotglob", id="zsh-o-globdots"),
    pytest.param("zsh -o GLOB_DOTS -c 'ls'", "dotglob", id="zsh-o-upper-case"),
    pytest.param("/bin/bash -O dotglob -c 'ls'", "dotglob", id="bash-by-full-path"),
    pytest.param("eval 'CDPATH=.claude'; cd hooks", "CDPATH", id="cdpath-in-eval"),
    pytest.param("eval 'GLOBIGNORE=x'; tee *env", "dotglob", id="globignore-in-eval"),
    pytest.param(
        "sed 'e echo hi' README.md", "runs a shell command", id="sed-e-command"
    ),
    pytest.param("sed 's/a/b/e' README.md", "runs a shell command", id="sed-e-flag"),
    pytest.param(
        "sed '1e tee .env' README.md", "runs a shell command", id="sed-e-writes"
    ),
    pytest.param(
        "sed -n '$!{e echo hi\n}' README.md",
        "runs a shell command",
        id="sed-e-in-block",
    ),
)


@pytest.mark.parametrize("command, message", _OPTION_REFUSED)
def test_scanner_refuses_a_shell_option_that_changes_what_a_name_means(
    command: str, message: str
) -> None:
    with pytest.raises(PROTECT_FILES.UnparseableCommand, match=message):
        PROTECT_FILES.shell_targets(command, str(REPO_ROOT))


_OPTION_ALLOWED = (
    pytest.param("bash -O extglob -c 'echo hi'", id="bash-O-other-option"),
    pytest.param("bash +O dotglob -c 'echo hi'", id="bash-plus-O-unsets"),
    pytest.param(
        "bash -c 'tee *env' -O dotglob", id="O-after-the-script-is-an-argument"
    ),
    pytest.param("zsh -o extendedglob -c 'ls'", id="zsh-o-other-option"),
    pytest.param(
        'git commit -m "mention shopt -s dotglob here"', id="message-mentions-shopt"
    ),
    pytest.param('echo "shopt -s dotglob"', id="echo-mentions-shopt"),
    pytest.param("echo setopt dotglob", id="echo-mentions-setopt"),
    pytest.param("shopt -q dotglob; echo ok", id="query"),
    pytest.param("shopt -u dotglob; ls", id="unset"),
    pytest.param("shopt dotglob", id="list"),
    pytest.param("shopt -s nullglob; ls", id="other-option"),
    pytest.param("GLOBIGNORE= ls", id="empty-globignore"),
    pytest.param("echo GLOBIGNORE=x", id="echo-mentions-globignore"),
    pytest.param("alias ll='ls -l'; ll", id="alias-harmless"),
    pytest.param("sed -n 's/a/b/;p' README.md", id="sed-without-e"),
    pytest.param("sed -n '/e/p' README.md", id="e-in-a-pattern"),
    pytest.param("sed 's/a/e/' README.md", id="e-in-a-replacement"),
)


@pytest.mark.parametrize("command", _OPTION_ALLOWED)
def test_scanner_allows_text_that_only_mentions_a_shell_option(command: str) -> None:
    assert not _hit(command)


# `eval` runs in the current shell: its folder changes, variables, aliases and functions
# stay; `bash -c` runs a child shell, whose do not.
_EVAL_DENY = (
    pytest.param("eval 'cd .claude'; cmd settings.json", id="cd-stays"),
    pytest.param("eval 'cd .claude' && cmd settings.json", id="cd-stays-and-list"),
    pytest.param("eval 'x=.e'; eval 'y=nv'; tee $x$y", id="two-halves-of-a-name"),
    pytest.param("eval 'x=.env'; tee $x", id="variable-stays"),
    pytest.param(
        "shopt -s expand_aliases\neval 'alias cat=tee'\ncat .env", id="alias-stays"
    ),
    pytest.param("eval 'f() { tee \"$@\"; }'; f .env", id="function-stays"),
    pytest.param("eval 'pushd .claude'; cmd settings.json", id="pushd-stays"),
    pytest.param("eval cd .claude; cmd settings.json", id="unquoted-words-are-joined"),
)


@pytest.mark.parametrize("command", _EVAL_DENY)
def test_scanner_keeps_what_eval_changes_in_the_current_shell(command: str) -> None:
    assert _hit(command)


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("bash -c 'cd .claude'; cmd settings.json", id="child-cd-is-gone"),
        pytest.param("bash -c 'x=a'; echo $x", id="child-variable-is-gone"),
        pytest.param("eval 'cd docs'; cmd x", id="eval-cd-elsewhere"),
        pytest.param("eval 'x=a'; echo $x", id="eval-variable-harmless"),
    ),
)
def test_scanner_does_not_invent_state_for_a_child_shell(command: str) -> None:
    assert not _hit(command)


# Aliases are read from the words of the alias command.
_ALIAS_DENY = (
    pytest.param("alias 'cat=tee'; cat .env", id="single-quoted"),
    pytest.param('alias "cat=tee"\ncat .env', id="double-quoted"),
    pytest.param("alias -- 'cat=tee'; cat .env", id="end-of-options"),
    pytest.param("alias ll=ls 'cat=tee'; cat .env", id="second-name"),
    pytest.param("builtin alias 'cat=tee'; cat .env", id="builtin-alias"),
)


@pytest.mark.parametrize("command", _ALIAS_DENY)
def test_scanner_reads_a_quoted_alias_definition(command: str) -> None:
    assert _hit(command)


# find: a name pattern is instantiated, and path or regex tests do not narrow.
_FIND_ROUND2_DENY = (
    pytest.param("find . -name '.env.p*' -delete", id="env-family-prefix"),
    pytest.param("find . -name 'server*.pem' -delete", id="pem-between-stars"),
    pytest.param("find . -name 'credentials-*' -exec rm {} +", id="credentials-dash"),
    pytest.param("find . -name 'key?.pem' -delete", id="pem-question"),
    pytest.param("find . -name 'id_[rd]sa.key' -delete", id="key-class"),
    pytest.param("find . -name '[.]env' -delete", id="class-spells-the-dot"),
    pytest.param("find . -name '?env' -delete", id="question-spells-the-dot"),
    pytest.param("find . -iname 'CREDENTIALS*' -delete", id="upper-case-credentials"),
    pytest.param("find .claude -path '.claude/settings*' -delete", id="path-test"),
    pytest.param("find . -ipath '*settings.json' -delete", id="ipath-test"),
    pytest.param("find . -wholename './.env' -delete", id="wholename-test"),
    pytest.param("find . -regex '.*\\.\\(pem\\|key\\)' -delete", id="regex-test"),
    pytest.param("find . -iregex '.*CREDENTIALS.*' -delete", id="iregex-test"),
    pytest.param(
        "find . -name \"$(echo '.env*')\" -delete", id="pattern-from-a-command"
    ),
    pytest.param('find . -name "$X" -delete', id="pattern-from-a-variable"),
    pytest.param("find . -name '\\.env' -delete", id="pattern-with-a-backslash"),
    pytest.param("find . -name '*.code-workspace' -delete", id="workspace-files"),
    pytest.param("find . -name uv.lock -delete", id="exact-lock"),
    pytest.param("find . -name '.*' -delete", id="every-dot-file"),
)


@pytest.mark.parametrize("command", _FIND_ROUND2_DENY)
def test_scanner_denies_a_find_pattern_that_can_match_a_protected_name(
    command: str,
) -> None:
    assert _hit(command)


_FIND_ROUND2_ALLOW = (
    pytest.param("find . -name '*.pyc' -delete", id="pyc"),
    pytest.param("find . -name 'build*' -type f -delete", id="build-prefix"),
    pytest.param("find . -name '*.txt' -exec rm {} +", id="txt"),
    pytest.param("find . -name 'x?' -delete", id="short-question"),
    pytest.param("find . -name '.env.p*' -print", id="no-action"),
    pytest.param("find . -name '*.log' -exec ls {} +", id="read-only-exec"),
    pytest.param("find . -type d -empty -delete", id="empty-folders"),
)


@pytest.mark.parametrize("command", _FIND_ROUND2_ALLOW)
def test_scanner_allows_a_find_pattern_that_cannot_match_a_protected_name(
    command: str,
) -> None:
    assert not _hit(command)


# sed: any unique prefix of a long option, as GNU getopt reads it.
_SED_ABBREVIATED_DENY = (
    pytest.param("sed --ex='w .env' README.md", id="expression-prefix-equals"),
    pytest.param("sed --e 'w .env' README.md", id="expression-one-letter"),
    pytest.param("sed --expr 'w .env' README.md", id="expression-prefix-separate"),
    pytest.param("sed --sep 'w .env' README.md", id="separate-prefix"),
    pytest.param("sed --nu 'w .env' README.md", id="null-data-prefix"),
    pytest.param("sed --qui -n --exp='w .env' README.md", id="quiet-then-expression"),
    pytest.param("sed --in -e 's/a/b/' .env", id="in-place-prefix"),
    pytest.param("sed --regexp-e -n 'w .env' README.md", id="regexp-extended-prefix"),
)


@pytest.mark.parametrize("command", _SED_ABBREVIATED_DENY)
def test_scanner_reads_an_abbreviated_sed_long_option(command: str) -> None:
    assert _hit(command)


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("sed --quiet --expression=p README.md", id="full-names"),
        pytest.param("sed --qui -e p README.md", id="quiet-prefix"),
        pytest.param(
            "sed --s -n p README.md", id="ambiguous-prefix-is-an-error-in-sed"
        ),
        pytest.param("sed --line-length=5 -n p README.md", id="line-length"),
    ),
)
def test_scanner_allows_an_abbreviated_sed_option_that_writes_nothing(
    command: str,
) -> None:
    assert not _hit(command)


# cd: its operand is resolved like any path; pushd, builtin, env -C and shadowing count.
_CD_ROUND2_DENY = (
    pytest.param(
        "cd .claud?/hooks/scripts && bash openwiki-guard.sh post </dev/null",
        id="cd-glob",
    ),
    pytest.param(
        "cd .claude/hook[s]/scripts && ./openwiki-guard.sh post", id="cd-class"
    ),
    pytest.param(
        "pushd .claude/hooks/scripts >/dev/null && bash openwiki-guard.sh post",
        id="pushd",
    ),
    pytest.param("pushd .claude >/dev/null && cmd settings.json", id="pushd-config"),
    pytest.param("builtin cd .claude && cmd settings.json", id="builtin-cd"),
    pytest.param("bash -c 'cd .claude && cmd settings.json'", id="cd-inside-bash-c"),
    pytest.param("sh -c 'cd .claude; tee settings.json'", id="cd-inside-sh-c"),
    pytest.param("bash -lc 'cd .claude && cmd settings.json'", id="cd-inside-bash-lc"),
    pytest.param("eval 'cd .claude; tee settings.json'", id="cd-inside-eval"),
    pytest.param(
        "bash -c 'cd docs && tee ../.env'", id="bash-c-writes-up-from-a-folder"
    ),
    pytest.param("bash -c 'x=.en; tee ${x}v'", id="bash-c-reads-its-variables"),
    pytest.param("builtin pushd .claude && cmd settings.json", id="builtin-pushd"),
    pytest.param(
        "timeout 5 env -C .claude cmd settings.json", id="env-C-behind-timeout"
    ),
    pytest.param("timeout -k 2 5 env -C .claude cmd settings.json", id="timeout-flags"),
    pytest.param("nohup env -C .claude cmd settings.json", id="env-C-behind-nohup"),
    pytest.param("nice -n 5 env -C .claude cmd settings.json", id="env-C-behind-nice"),
    pytest.param("command env -C .claude cmd settings.json", id="env-C-behind-command"),
    pytest.param("/usr/bin/env -C .claude cmd settings.json", id="env-C-by-full-path"),
    pytest.param(
        "/usr/bin/env -C .claude/hooks/scripts bash openwiki-guard.sh post",
        id="env-C-full-path-runs-a-hook-script",
    ),
    pytest.param("sudo env -C .claude cmd settings.json", id="env-C-behind-sudo"),
    pytest.param("make -C .claude settings.json", id="make-C"),
    pytest.param("make --directory=.claude settings.json", id="make-directory-equals"),
    pytest.param(
        "make --directory .claude settings.json", id="make-directory-separate"
    ),
    pytest.param("tar -C .claude -xf a.tar settings.json", id="tar-C"),
    pytest.param("xargs -n1 env -C .claude cmd settings.json", id="env-C-behind-xargs"),
    pytest.param("timeout 5 tee .env", id="timeout-runs-tee"),
    pytest.param("nohup tee x > .env", id="nohup-redirect"),
    pytest.param("env -C .claude cmd settings.json", id="env-C"),
    pytest.param("env -C.claude cmd settings.json", id="env-C-attached"),
    pytest.param("env --chdir=.claude cmd settings.json", id="env-chdir-equals"),
    pytest.param(
        "env --chdir .claude/hooks/scripts bash openwiki-guard.sh post",
        id="env-chdir-separate",
    ),
    pytest.param(
        'cd() { builtin cd "$1"; }; cd .claude; cmd settings.json', id="shadowed-cd"
    ),
    pytest.param(
        'cd() { pushd "$@" >/dev/null; }; cd .claude; cmd settings.json',
        id="shadowed-cd-pushd",
    ),
)


@pytest.mark.parametrize("command", _CD_ROUND2_DENY)
def test_scanner_follows_every_way_to_change_folder(command: str) -> None:
    assert _hit(command)


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("pushd docs >/dev/null; popd >/dev/null; cmd x", id="pushd-popd"),
        pytest.param("popd", id="popd-alone"),
        pytest.param("env FOO=1 cmd x", id="env-assignment"),
        pytest.param("env -i cmd x", id="env-flag"),
        pytest.param("env -C docs cmd x", id="env-C-elsewhere"),
        pytest.param("builtin cd docs && cmd x", id="builtin-cd-elsewhere"),
        pytest.param("bash -c 'cd docs && cmd x'", id="bash-c-cd-elsewhere"),
        pytest.param("bash -c 'cd .claude && ls'", id="bash-c-list-the-folder"),
        pytest.param("bash -c 'echo hi'", id="bash-c-harmless"),
        pytest.param("timeout 5 cmd x", id="timeout-harmless"),
        pytest.param("timeout -k 2 5 cmd x", id="timeout-flags-harmless"),
        pytest.param("nohup cmd x", id="nohup-harmless"),
        pytest.param("make -C docs build", id="make-C-elsewhere"),
        pytest.param("tar -C docs -xf a.tar", id="tar-C-elsewhere"),
        pytest.param("nice -n 5 cmd x", id="nice-harmless"),
        pytest.param("/usr/bin/env -C docs cmd x", id="env-C-full-path-elsewhere"),
        pytest.param(
            "timeout 5 env -C docs cmd x", id="env-C-behind-timeout-elsewhere"
        ),
        pytest.param(
            "cd .claude; bash -c 'cd docs; ls'", id="child-shell-cd-does-not-leak"
        ),
        pytest.param(
            "bash -c 'cd .claude'; cmd settings.json", id="cd-in-a-child-does-not-leak"
        ),
        pytest.param("cd docs && cmd x", id="cd-elsewhere"),
        pytest.param("pushd +1 >/dev/null; cmd x", id="pushd-rotate"),
    ),
)
def test_scanner_allows_a_folder_change_to_a_harmless_folder(command: str) -> None:
    assert not _hit(command)


# A name built around a substitution: the text around it may complete a protected family.
_BUILT_NAME_DENY = (
    pytest.param("touch $(echo cred)entials", id="tail-only-credentials"),
    pytest.param("touch $(echo .)env.production", id="tail-only-env-family"),
    pytest.param("touch .$(echo env).production", id="middle-env-family"),
    pytest.param("touch .`echo env`.production", id="middle-with-backticks"),
    pytest.param("touch .e$(echo n)v.local", id="head-and-tail-env-family"),
    pytest.param("touch $(echo creden)tials.json", id="credentials-with-a-tail"),
    pytest.param('touch "$(echo cred)entials"', id="quoted-tail-only"),
)


@pytest.mark.parametrize("command", _BUILT_NAME_DENY)
def test_scanner_flags_a_name_that_a_substitution_can_complete(command: str) -> None:
    assert _hit(command)


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("tee $(mktemp)", id="whole-word-substitution"),
        pytest.param("touch $(date +%s).txt", id="date-then-extension"),
        pytest.param("cp x $(basename y).bak", id="basename-then-backup"),
        pytest.param("touch file-$(echo 1).txt", id="prefix-then-extension"),
        pytest.param("tee out-$(echo 1).log", id="prefix-then-log"),
        pytest.param("touch $(echo a)b.md", id="short-tail"),
    ),
)
def test_scanner_allows_a_substitution_that_cannot_complete_a_protected_name(
    command: str,
) -> None:
    assert not _hit(command)


# A bare assignment whose value holds a default or an unresolved expansion: the value may
# name a protected file (the name the default gives, or what is left without the
# expansion), so a later use is checked against it. Only a value that names one is
# tracked: `PORT=${PORT:-8080}` stays untracked.
_ASSIGNMENT_DEFAULT_DENY = (
    pytest.param('y=${z:-.env}; tee "$y"', id="default-word"),
    pytest.param('x=.en${z}v; tee "$x"', id="glued-braced-reference"),
    pytest.param('y=${z/#/.env}; tee "$y"', id="replacement-word"),
    pytest.param("y=${z:=.env}; tee $y", id="assign-default"),
    pytest.param("y=${z-.env}; tee $y", id="short-default"),
    pytest.param("y=${z:+.env}; tee $y", id="alternative-word"),
    pytest.param("y=${a:-${b:-.env}}; tee $y", id="nested-default"),
    pytest.param("y=${z}.env; tee $y", id="reference-then-name"),
    pytest.param("y=.e${z:-n}v; tee $y", id="default-inside-a-name"),
    pytest.param("y=.env$z; tee $y", id="plain-reference-after-the-name"),
    pytest.param("export y=${z:-.env}; tee $y", id="export"),
    pytest.param("declare y=${z:-.env}; tee $y", id="declare"),
    pytest.param("y=${z:-.claude/settings.json}; echo x > $y", id="config-default"),
    pytest.param("y=${z:-a .env}; tee $y", id="default-with-a-blank"),
    pytest.param("y=${z:-.env.local}; rm $y", id="env-family-default"),
    pytest.param("y=${z:-x.pem}; touch $y", id="pem-default"),
)


@pytest.mark.parametrize("command", _ASSIGNMENT_DEFAULT_DENY)
def test_scanner_checks_a_use_of_an_assignment_that_may_name_a_protected_file(
    command: str,
) -> None:
    assert _hit(command)


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("y=${z:-.env}; y=safe; tee $y", id="reassigned"),
        pytest.param("y=${z:-.env}; false && y=safe; tee $y", id="conditional"),
        pytest.param("y=${z:-.env}; (y=safe); tee $y", id="subshell"),
        pytest.param("y=${z:-.env}; y+=x; echo $y", id="appended"),
    ),
)
def test_scanner_refuses_a_second_value_for_a_name_that_may_hold_a_protected_name(
    command: str,
) -> None:
    with pytest.raises(PROTECT_FILES.UnparseableCommand, match="assigned twice"):
        PROTECT_FILES.shell_targets(command, str(REPO_ROOT))


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("PORT=${PORT:-8080} ./run.sh", id="prefix-default"),
        pytest.param("PORT=${PORT:-8080}; PORT=9090; echo $PORT", id="port-twice"),
        pytest.param('export PATH="${PATH:-/usr/bin}:/opt/bin"', id="export-path"),
        pytest.param(
            "export PYTHONPATH=src${PYTHONPATH:+:$PYTHONPATH}", id="export-alternative"
        ),
        pytest.param(
            "export PATH=${PATH:-/usr/bin}:/opt/bin; export PATH=x:$PATH",
            id="path-twice",
        ),
        pytest.param('y=${z:-out.txt}; tee "$y"', id="harmless-default"),
        pytest.param("x=${z:-a}b; echo $x", id="harmless-glued-default"),
        pytest.param("y=$HOME/bin:$PATH; y=other; echo $y", id="plain-references"),
        pytest.param("y=${z#.}; echo $y", id="operation-on-an-unassigned-name"),
        pytest.param("y=${z:-$HOME}; tee $y", id="default-that-is-a-reference"),
    ),
)
def test_scanner_still_allows_an_assignment_that_names_no_protected_file(
    command: str,
) -> None:
    assert not _hit(command)


# An in-place perl edit is a confirmed write target, like `sed -i`: a hook config asks on
# Claude Code and Copilot and is denied on Codex and Antigravity; only the `-e`/`-E`/`-M`
# script text is scanned for names, so a file that is only read is not a hit.
@pytest.mark.parametrize("target_id, expected", CLIENT_CONFIG_DECISIONS)
@pytest.mark.parametrize(
    "command",
    (
        pytest.param("perl -pi -e 's/x/y/' .claude/settings.json", id="cluster"),
        pytest.param("perl -pi.bak -e 's/x/y/' .claude/settings.json", id="suffix"),
        pytest.param("perl -i -pe 's/x/y/' .claude/settings.json", id="separate-i"),
        pytest.param(
            "perl -Mstrict -pi -e 's/x/y/' .claude/settings.json", id="module"
        ),
    ),
)
def test_protect_files_gates_an_in_place_perl_edit_of_a_hook_config(
    tmp_path: Path, target_id: str, expected: str, command: str
) -> None:
    process = _run_protect_files(
        _client_bash_payload(target_id, command), tmp_path, target_id
    )
    assert _protect_decision(process) == expected, process.stdout


@pytest.mark.parametrize("target_id", _CLIENTS)
@pytest.mark.parametrize(
    "command",
    (
        pytest.param("perl -pi -e 's/x/y/' .env", id="in-place-secret"),
        pytest.param(
            "perl -pi -e 'open(F,\">x\")' .env", id="in-place-secret-with-a-script"
        ),
        pytest.param("perl -e 'open(F,\">.env\")'", id="script-names-the-secret"),
        pytest.param(
            "perl -pi -e 'open(F,\">.claude/settings.json\")' README.md",
            id="script-names-a-config",
        ),
        pytest.param("perl script.pl .env", id="script-file-names-the-secret"),
        pytest.param(
            "perl -e 'open(F, \">\", $ARGV[0])' .claude/settings.json",
            id="program-writes-a-config-operand",
        ),
        pytest.param(
            "perl -ne 'print' .claude/settings.json", id="reads-a-config-operand"
        ),
    ),
)
def test_protect_files_denies_a_perl_run_that_names_a_protected_file_on_every_client(
    tmp_path: Path, target_id: str, command: str
) -> None:
    process = _run_protect_files(
        _client_bash_payload(target_id, command), tmp_path, target_id
    )
    assert _protect_decision(process) == "deny", process.stdout


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("perl -pi -e 's/x/y/' README.md", id="in-place-harmless"),
        pytest.param("perl -pi.bak -e 's/x/y/' docs/a.md docs/b.md", id="two-files"),
        pytest.param("perl -ne 'print' README.md", id="read-a-harmless-file"),
    ),
)
def test_scanner_allows_a_perl_run_that_only_reads_or_edits_a_harmless_file(
    command: str,
) -> None:
    assert not _hit(command)


# `source` and `.` of a here-document run it in the current shell, like `eval`.
@pytest.mark.parametrize(
    "command",
    (
        pytest.param(
            "source /dev/stdin <<'EOF'\ncd .claude\nEOF\ncmd settings.json",
            id="cd-stays",
        ),
        pytest.param(
            ". /dev/stdin <<'EOF'\ncd .claude\nEOF\ncmd settings.json",
            id="dot-cd-stays",
        ),
        pytest.param(
            "source /dev/stdin <<EOF\ncd .claude\nEOF\ncmd settings.json",
            id="unquoted-delimiter",
        ),
        pytest.param(
            "source /dev/stdin <<'EOF'\nx=.e\nEOF\ntee ${x}nv", id="variable-stays"
        ),
        pytest.param("source /dev/stdin <<'EOF'\ntee .env\nEOF", id="body-writes"),
        pytest.param(
            "source <(cat <<'EOF'\ncd .claude\nEOF\n); cmd settings.json",
            id="process-substitution-cd-stays",
        ),
        pytest.param(
            '. <(cat <<EOF\nx=.e\nEOF\n); tee "${x}nv"',
            id="process-substitution-variable-stays",
        ),
        pytest.param(
            "eval \"$(cat <<'EOF'\ncd .claude\nEOF\n)\"; cmd settings.json",
            id="eval-of-a-quoted-substitution-cd-stays",
        ),
        pytest.param(
            "eval $(cat <<'EOF'\ncd .claude\nEOF\n); cmd settings.json",
            id="eval-of-a-substitution-cd-stays",
        ),
        pytest.param(
            "eval \"$(cat <<'EOF'\ntee .env\nEOF\n)\"",
            id="eval-substitution-body-writes",
        ),
    ),
)
def test_scanner_keeps_what_a_sourced_heredoc_changes_in_the_current_shell(
    command: str,
) -> None:
    assert _hit(command)


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("source /dev/stdin <<'EOF'\ncd docs\nEOF\ncmd x", id="elsewhere"),
        pytest.param(
            "bash <<'EOF'\ncd .claude\nEOF\ncmd settings.json", id="child-shell"
        ),
        pytest.param("source ./env.sh; cmd x", id="a-file"),
        pytest.param("source /dev/stdin <<'EOF'\nx=a\nEOF\necho $x", id="harmless"),
        pytest.param(
            "eval \"$(cat <<'EOF'\ncd docs\nEOF\n)\"; cmd x", id="eval-elsewhere"
        ),
        pytest.param(
            "bash <(cat <<'EOF'\ncd .claude\nEOF\n); cmd settings.json",
            id="child-shell-reads-a-script",
        ),
        pytest.param(
            "eval \"$(cat <<'EOF'\nx=a\nEOF\n)\"; echo $x", id="eval-harmless"
        ),
    ),
)
def test_scanner_does_not_invent_state_from_a_harmless_sourced_heredoc(
    command: str,
) -> None:
    assert not _hit(command)


# Interpreter and tool options that run a command.
_RUNS_COMMAND_DENY = (
    pytest.param("perl -e 'open(F,\">.env\")'", id="perl-open"),
    pytest.param('perl -e \'open(F,">", ".env")\'', id="perl-open-three-arguments"),
    pytest.param("perl -ne 'print' .env", id="perl-names-the-file-as-an-operand"),
    pytest.param("perl script.pl .env", id="perl-script-file-names-the-file"),
    pytest.param("perl -i script.pl .env", id="perl-in-place-script-file"),
    # Without `-i` a perl program can open an operand for writing, so unlike `sed` the
    # operands are scanned.
    pytest.param(
        "perl -e 'open(F, \">\", $ARGV[0])' .env", id="perl-writes-its-operand"
    ),
    pytest.param("perl -nle 'print length' .env", id="perl-cluster-reads-the-file"),
    pytest.param("perl -Mstrict -ne 'print' .env", id="perl-module-and-operand"),
    # A flag cluster is read up to its first letter that takes a value: `-M` and `-I`
    # take the rest of the cluster, so an `i` in `-Mwarnings` is not `-i`.
    pytest.param(
        "perl -Mwarnings -e 'open(F,\">.env\")' README.md", id="perl-module-flag"
    ),
    pytest.param(
        "perl -MFile::Spec -e 'open(F,\">.env\")' README.md", id="perl-module-with-i"
    ),
    pytest.param("perl -wle 'open(F,\">.env\")'", id="perl-cluster-ending-in-e"),
    pytest.param("perl -le'open(F,\">.env\")'", id="perl-attached-script"),
    pytest.param("perl -I lib -e 'open(F,\">.env\")'", id="perl-include-then-e"),
    pytest.param("perl -E 'open(F,\">.env\")'", id="perl-E-script"),
    pytest.param(
        "perl -pi -e 'open(F,\">.env\")' README.md", id="perl-in-place-script"
    ),
    pytest.param("perl -pi.bak -e 's/a/b/' .env", id="perl-in-place-operand"),
    pytest.param("perl -i.bak -pe 's/a/b/' .env", id="perl-suffix-then-script"),
    pytest.param("git -c alias.x='!tee .env' x", id="git-alias-runs-a-command"),
    pytest.param("git -c core.pager='tee .env' log", id="git-pager-runs-a-command"),
    pytest.param("rg --pre tee x .env", id="rg-pre-separate"),
    pytest.param("rg --pre=tee x .env", id="rg-pre-equals"),
)


@pytest.mark.parametrize("command", _RUNS_COMMAND_DENY)
def test_scanner_reads_a_tool_option_that_runs_a_command(command: str) -> None:
    assert _hit(command)


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("perl -e 'print 1'", id="perl-print"),
        pytest.param("perl -Mstrict -e 'print 1'", id="perl-module-harmless"),
        pytest.param("perl -wnl -e 'print' README.md", id="perl-cluster-harmless"),
        pytest.param("perl -pi -e 's/a/b/' README.md", id="perl-in-place-harmless"),
        pytest.param("perl -I lib script.pl README.md", id="perl-script-file"),
        pytest.param("git -c alias.st='!git status' st", id="git-alias-harmless"),
        pytest.param("git -c user.name=x commit -m msg", id="git-config-harmless"),
        pytest.param("rg --pre cat x README.md", id="rg-pre-harmless"),
        pytest.param("rg x README.md", id="rg-plain"),
    ),
)
def test_scanner_allows_a_tool_option_that_runs_a_harmless_command(
    command: str,
) -> None:
    assert not _hit(command)


# A NUL ends a word in Bash: `$'.env\x00x'` is the name `.env`.
def test_scanner_cuts_an_ansi_c_word_at_a_nul() -> None:
    assert PROTECT_FILES._unquote("$'.env\\x00x'") == ".env"
    assert PROTECT_FILES._unquote("$'.env\\0x'") == ".env"
    assert PROTECT_FILES._unquote("$'.env\\u0000x'") == ".env"
    assert PROTECT_FILES._unquote("$'a\\x00.env'") == "a"


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("touch $'.env\\x00x'", id="hex"),
        pytest.param("touch $'.env\\0x'", id="octal"),
        pytest.param("touch $'.env\\u0000x'", id="unicode"),
        pytest.param("touch .e$'n\\x00'v", id="nul-in-the-middle-of-a-word"),
    ),
)
def test_scanner_finds_the_name_before_a_nul(command: str) -> None:
    assert _hit(command)


def test_scanner_does_not_invent_a_name_after_a_nul() -> None:
    assert not _hit("touch $'a\\x00.env'")


def test_scanner_refuses_a_raw_nul_byte_in_the_command() -> None:
    with pytest.raises(PROTECT_FILES.UnparseableCommand, match="NUL"):
        PROTECT_FILES.shell_targets("touch .env\0x", str(REPO_ROOT))


# --------------------------------------------------------------------------
# Known gap (listed in the docs): a value whose default word, or what is left without its
# expansions, is only a FRAGMENT of a protected name is not tracked, so the name that the
# fragment completes later is not seen. Only a guess that names a protected file by itself
# is tracked (`y=${z:-.env}`). Tracking fragments made `${z:+a}`, `${z+a}`, and `${z/a/b}`
# stand in for `z` and let `y=${z:+a}; tee .env$y` through (Phase H denies it, and Bash
# writes `.env` with `z` unset). These tests pin the current result; closing the gap
# means making them deny tests and keeping `test_scanner_keeps_an_unresolved_reference_
# glued_to_a_protected_name` green.
# --------------------------------------------------------------------------

_FRAGMENT_GAP = (
    pytest.param('y=${z:-.e}; tee "${y}nv"', id="fragment-default"),
    pytest.param("y=${z:-.e}; tee ${y}nv", id="fragment-default-unquoted"),
    pytest.param('x=.e; y=${z}${x}nv; tee "$y"', id="chained-unresolved"),
    pytest.param('y=${z:-.e}; w=${y}nv; tee "$w"', id="fragment-through-a-second-name"),
    pytest.param('y=.e${z}; tee "${y}nv"', id="expansion-removed-leaves-a-fragment"),
    pytest.param('y=${z}.en; tee "${y}v"', id="fragment-after-an-expansion"),
    pytest.param('x=${a:-.e}; y=${b:-nv}; tee "${x}${y}"', id="two-fragments"),
    pytest.param('d=${z:-.cla}; cd "${d}ude"; cmd settings.json', id="fragment-folder"),
    pytest.param('export y=${z:-.e}; tee "${y}nv"', id="fragment-default-in-an-export"),
    pytest.param(
        'y=${z:-.e}; y2=$y; y3=${y2}nv; tee "$y3"', id="fragment-copied-twice"
    ),
    pytest.param('a=${p:-.}; b=${q:-env}; tee "${a}${b}"', id="two-short-fragments"),
    pytest.param(
        'x=.en; y=${z}${x}${w}v; tee "$y"', id="expansions-around-a-known-part"
    ),
    pytest.param('x=${a:-.e}; y=${x}${b:-nv}; tee "$y"', id="fragment-then-default"),
    pytest.param('x=.e; y=${z:-}${x}nv; tee "$y"', id="empty-default-then-part"),
    pytest.param('a=${p:-.e}; b=${a}${q}; c=${b}nv; tee "$c"', id="chain-of-three"),
)


@pytest.mark.parametrize("command", _FRAGMENT_GAP)
def test_scanner_does_not_track_a_fragment_that_an_unresolved_expansion_leaves(
    command: str,
) -> None:
    assert not _hit(command)  # the gap: Bash writes `.env` for each of these


@pytest.mark.parametrize(
    "command",
    (
        pytest.param('y=${z:-.e}; y=x; tee "${y}nv"', id="fragment-then-assigned"),
        pytest.param("PORT=${PORT:-8080}; PORT=9090; echo $PORT", id="port-twice"),
        pytest.param(
            'export PATH="${PATH:-/usr/bin}:/opt/bin"; PATH=x:$PATH; PATH=y:$PATH',
            id="path-three-times",
        ),
        pytest.param('y=${z:-a}; tee "${y}b"', id="harmless-fragment"),
        pytest.param('y=${z:-.e}; tee "${y}"', id="fragment-alone"),
        pytest.param('y=${z:-out}; tee "${y}.txt"', id="harmless-default-and-tail"),
        pytest.param('x=${a:-.e}; y=${b:-xv}; tee "${x}${y}"', id="two-harmless-parts"),
        pytest.param(
            'a=${p:-x}; b=${a}${q}; c=${b}y; tee "$c"', id="harmless-chain-of-three"
        ),
    ),
)
def test_scanner_allows_a_fragment_that_names_no_protected_file(command: str) -> None:
    assert not _hit(command)


# The word of `${z:+word}`, `${z+word}`, or `${z/a/b}` is not the value of an unset `z`
# (it is empty), so it must not stand in for the variable: the unresolved reference next
# to `.env` still names a protected file.
@pytest.mark.parametrize(
    "command",
    (
        pytest.param("y=${z:+a}; tee .env$y", id="plus-word"),
        pytest.param("y=${z+a}; tee ${y}.env", id="plus-word-without-colon"),
        pytest.param("y=${z/a/b}; tee .env$y", id="replacement-word"),
        pytest.param('y=${z:+a}; tee ".env${y}"', id="plus-word-quoted"),
        pytest.param("y=${z:+a}; export y; tee .env$y", id="plus-word-exported"),
        pytest.param("export y=${z:+a}; tee .env$y", id="plus-word-in-an-export"),
        pytest.param("y=${z:?}; tee .env$y", id="error-word"),
        pytest.param("y=${z#a}; tee .env$y", id="removal-word"),
    ),
)
def test_scanner_keeps_an_unresolved_reference_glued_to_a_protected_name(
    command: str,
) -> None:
    assert _hit(command)


# --------------------------------------------------------------------------
# Review round 4: a shell fed by a heredoc, a here-string, or a pipe, in any spelling.
# --------------------------------------------------------------------------

_SHELL_BODIES = (
    pytest.param("cd .claude\ntee settings.json", id="folder"),
    pytest.param("x=.e; tee ${x}nv", id="built-name"),
)
_FED_SHELLS = (
    "bash",
    "/bin/bash",
    "/usr/bin/bash",
    "dash",
    "ksh",
    "ash",
    "sh",
    "zsh",
    "env bash",
    "command bash",
    "exec bash",
    "nohup bash",
    "timeout 5 bash",
    "nice -n 5 bash",
    "setsid bash",
    "time bash",
    "bash -s",
    "bash -",
    "bash -e",
    "bash -o posix",
    "bash /dev/stdin",
    "sh /dev/fd/0",
    "bash /proc/self/fd/0",
    "bash -s --",
)


@pytest.mark.parametrize("body", _SHELL_BODIES)
@pytest.mark.parametrize("shell", _FED_SHELLS)
def test_scanner_reads_a_heredoc_fed_to_a_shell_in_any_spelling(
    shell: str, body: str
) -> None:
    assert _hit("%s <<'EOF'\n%s\nEOF" % (shell, body))


@pytest.mark.parametrize("body", _SHELL_BODIES)
@pytest.mark.parametrize(
    "shell",
    ("bash", "/bin/bash", "dash", "sh", "env bash", "exec bash", "bash -s"),
)
def test_scanner_reads_a_here_string_fed_to_a_shell(shell: str, body: str) -> None:
    assert _hit("%s <<< '%s'" % (shell, body.replace("\n", "; ")))


def test_scanner_reads_a_here_string_with_double_quotes_and_a_variable() -> None:
    assert _hit('s=".e"; bash <<< "x=$s; tee \\${x}nv"')
    assert _hit('bash <<< "cd .claude; tee settings.json"')


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("cat <<'EOF' | sh\nx=.e; tee ${x}nv\nEOF", id="cat-heredoc"),
        pytest.param(
            "cat <<EOF | sh\nx=.e; tee \\${x}nv\nEOF", id="unquoted-delimiter"
        ),
        pytest.param(
            "cat <<'EOF' | sh\ncd .claude\ntee settings.json\nEOF", id="folder"
        ),
        pytest.param("cat <<< 'x=.e; tee ${x}nv' | bash", id="here-string"),
        pytest.param("cat <<'EOF' | /bin/bash\nx=.e; tee ${x}nv\nEOF", id="path"),
        pytest.param("cat <<'EOF' | dash\nx=.e; tee ${x}nv\nEOF", id="dash"),
        pytest.param("cat <<'EOF' | env bash\nx=.e; tee ${x}nv\nEOF", id="env"),
        pytest.param("cat <<'EOF' | sudo sh\nx=.e; tee ${x}nv\nEOF", id="sudo"),
        pytest.param("cat <<'EOF' | nohup sh\nx=.e; tee ${x}nv\nEOF", id="nohup"),
        pytest.param("cat <<'EOF' | sh -s\nx=.e; tee ${x}nv\nEOF", id="stdin-flag"),
        pytest.param(
            "cat <<'EOF' | sh -x\nx=.e; tee ${x}nv\nEOF", id="shell-with-a-flag"
        ),
        pytest.param("cat <<'EOF' |& sh\nx=.e; tee ${x}nv\nEOF", id="pipe-and-stderr"),
        pytest.param(
            "cat <<'EOF' |sh\nx=.e; tee ${x}nv\nEOF", id="no-space-after-the-pipe"
        ),
        pytest.param(
            "cat <<'EOF' | (sh)\nx=.e; tee ${x}nv\nEOF", id="shell-in-a-subshell"
        ),
        pytest.param(
            "cat <<'EOF' | { sh; }\nx=.e; tee ${x}nv\nEOF", id="shell-in-a-group"
        ),
        pytest.param(
            "c=bash; cat <<'EOF' | $c\nx=.e; tee ${x}nv\nEOF", id="variable-shell"
        ),
        pytest.param(
            "c=bash; cat <<'EOF' | \"${c}\"\nx=.e; tee ${x}nv\nEOF",
            id="quoted-variable-shell",
        ),
        pytest.param(
            "/bin/cat <<'EOF' | sh\nx=.e; tee ${x}nv\nEOF", id="producer-by-path"
        ),
        pytest.param(
            "command cat <<'EOF' | sh\nx=.e; tee ${x}nv\nEOF", id="producer-by-command"
        ),
        pytest.param(
            "c=cat; $c <<'EOF' | sh\nx=.e; tee ${x}nv\nEOF", id="producer-variable"
        ),
        pytest.param(
            "cd .claude; cat <<'EOF' | sh\ntee settings.json\nEOF",
            id="folder-then-pipe",
        ),
        pytest.param(
            "echo hi | cat <<'EOF' | sh\nx=.e; tee ${x}nv\nEOF",
            id="producer-after-a-pipe",
        ),
    ),
)
def test_scanner_reads_cat_text_piped_into_a_shell(command: str) -> None:
    assert _hit(command)


# Known gap (listed in the docs): the text of `echo` or `printf` piped into a shell is not
# read (Phase H did not read it either). Only `cat <<EOF` and `cat <<< text` are. These
# tests pin the current result; closing the gap means making them deny tests.
@pytest.mark.parametrize(
    "command",
    (
        pytest.param("echo 'x=.e; tee ${x}nv' | sh", id="echo"),
        pytest.param("echo 'x=.e; tee ${x}nv' | /bin/bash", id="path"),
        pytest.param("echo 'x=.e; tee ${x}nv' | dash", id="dash"),
        pytest.param("echo 'x=.e; tee ${x}nv' | env bash", id="env"),
        pytest.param("echo 'x=.e; tee ${x}nv' | sudo sh", id="sudo"),
        pytest.param("echo 'x=.e; tee ${x}nv' | nohup sh", id="nohup"),
        pytest.param("echo 'x=.e; tee ${x}nv' | sh -s", id="stdin-flag"),
        pytest.param("echo 'x=.e; tee ${x}nv' |& sh", id="pipe-and-stderr"),
        pytest.param("c=bash; echo 'x=.e; tee ${x}nv' | $c", id="variable"),
        pytest.param(
            "c=bash; echo 'x=.e; tee ${x}nv' | \"${c}\"", id="quoted-variable"
        ),
        pytest.param(
            "printf '%s\\n' 'cd .claude' 'tee settings.json' | bash", id="printf-lines"
        ),
        pytest.param(
            "printf 'cd .claude\\ntee settings.json\\n' | sh", id="printf-format"
        ),
        pytest.param("echo -e 'cd .claude\\ntee settings.json' | sh", id="echo-e"),
        pytest.param("echo -n 'cd .claude; tee settings.json' | sh", id="echo-n"),
        pytest.param("echo cd .claude\\; tee settings.json | sh", id="echo-words"),
        pytest.param(
            "s='cd .claude; tee settings.json'; echo \"$s\" | sh",
            id="tracked-variable-text",
        ),
        pytest.param(
            "cd .claude; echo 'tee settings.json' | sh", id="folder-then-pipe"
        ),
        pytest.param(
            "echo hi | echo 'x=.e; tee ${x}nv' | sh", id="producer-after-a-pipe"
        ),
        pytest.param("/bin/echo 'x=.e; tee ${x}nv' | sh", id="producer-by-path"),
        pytest.param("command echo 'x=.e; tee ${x}nv' | sh", id="producer-by-command"),
        pytest.param("echo 'x=.e; tee ${x}nv' |sh", id="no-space-after-the-pipe"),
        pytest.param("echo 'x=.e; tee ${x}nv'|sh", id="no-space-around-the-pipe"),
        pytest.param("echo 'x=.e; tee ${x}nv' | (sh)", id="shell-in-a-subshell"),
        pytest.param("echo 'x=.e; tee ${x}nv' | { sh; }", id="shell-in-a-group"),
        pytest.param("echo 'x=.e; tee ${x}nv' | sh -x", id="shell-with-a-flag"),
        pytest.param("printf %s 'x=.e; tee ${x}nv' | sh", id="printf-plain-format"),
        pytest.param(
            "printf '%b' 'cd .claude\\ntee settings.json' | sh", id="printf-b"
        ),
        pytest.param("echo 'tee settings.json' | source /dev/stdin", id="source-pipe"),
        pytest.param(
            "echo 'x=.e; tee ${x}nv' | . /dev/stdin", id="source-pipe-built-name"
        ),
    ),
)
def test_scanner_does_not_read_echo_or_printf_text_piped_into_a_shell(
    command: str,
) -> None:
    assert not _hit(command)  # the gap: Bash writes `.env` for each of these


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("echo hi | sh", id="harmless-text"),
        pytest.param("cat script.sh | bash", id="unknown-producer"),
        pytest.param("echo 'cd docs; tee x' | sh", id="elsewhere"),
        pytest.param(
            "echo 'cd .claude; tee settings.json' | sh -c 'echo hi'", id="dash-c"
        ),
        pytest.param(
            "echo 'cd .claude' | sh; cmd settings.json",
            id="child-folder-stays-in-the-child",
        ),
        pytest.param("echo 'cd .claude; tee settings.json' | cat", id="not-a-shell"),
        pytest.param(
            "bash -c 'echo hi' <<< 'cd .claude; tee settings.json'",
            id="dash-c-here-string",
        ),
        pytest.param(
            "bash -c 'echo hi' <<'EOF'\ncd .claude\ntee settings.json\nEOF",
            id="dash-c-heredoc",
        ),
        pytest.param("bash <<'EOF'\ncd docs\ntee x\nEOF", id="heredoc-elsewhere"),
        pytest.param("bash <<< 'cd docs; tee x'", id="here-string-elsewhere"),
        pytest.param(
            "cat <<< 'cd .claude; tee settings.json'", id="here-string-to-cat"
        ),
        pytest.param("exec bash <<'EOF'\necho hi\nEOF", id="exec-harmless"),
    ),
)
def test_scanner_does_not_invent_a_write_for_text_that_a_shell_cannot_run(
    command: str,
) -> None:
    assert not _hit(command)


# --------------------------------------------------------------------------
# Review round 4: the command-spelling sweep. A runner that starts a shell, and a
# variable that holds a command name, are read like the plain command.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("exec bash -c 'x=.e; tee ${x}nv'", id="exec"),
        pytest.param("nohup bash -c 'cd .claude; tee settings.json'", id="nohup"),
        pytest.param("nice -n 5 bash -c 'x=.e; tee ${x}nv'", id="nice"),
        pytest.param("timeout 5 bash -c 'cd .claude; tee settings.json'", id="timeout"),
        pytest.param("setsid sh -c 'x=.e; tee ${x}nv'", id="setsid"),
        pytest.param("ionice -c 3 bash -c 'x=.e; tee ${x}nv'", id="ionice"),
        pytest.param("stdbuf -oL bash -c 'x=.e; tee ${x}nv'", id="stdbuf"),
        pytest.param("/usr/bin/time bash -c 'x=.e; tee ${x}nv'", id="time-binary"),
        pytest.param("nohup timeout 5 bash -c 'x=.e; tee ${x}nv'", id="two-runners"),
        pytest.param("xargs -n1 bash -c 'x=.e; tee ${x}nv'", id="xargs"),
        pytest.param("watch -n 1 bash -c 'cd .claude; tee settings.json'", id="watch"),
        pytest.param("doas bash -c 'x=.e; tee ${x}nv'", id="doas"),
        pytest.param("exec env bash -c 'x=.e; tee ${x}nv'", id="exec-env"),
        pytest.param("c=cd; $c .claude; cmd settings.json", id="variable-cd"),
        pytest.param("c=pushd; $c .claude; cmd settings.json", id="variable-pushd"),
        pytest.param("c=eval; $c 'x=.e; tee ${x}nv'", id="variable-eval"),
        pytest.param(
            "c=source; $c /dev/stdin <<'EOF'\ncd .claude\nEOF\ncmd settings.json",
            id="variable-source",
        ),
        pytest.param("c=bash; $c -c 'x=.e; tee ${x}nv'", id="variable-shell"),
        pytest.param("c=env; $c bash -c 'x=.e; tee ${x}nv'", id="variable-env"),
        pytest.param("c=command; $c bash -c 'x=.e; tee ${x}nv'", id="variable-command"),
        pytest.param(
            "c=builtin; $c cd .claude; cmd settings.json", id="variable-builtin"
        ),
        pytest.param('c=cd; "${c}" .claude; cmd settings.json', id="quoted-variable"),
        pytest.param(
            "c=env; \"${c}\" bash -c 'x=.e; tee ${x}nv'", id="quoted-variable-env"
        ),
        pytest.param(
            'c=builtin; "${c}" cd .claude; cmd settings.json',
            id="quoted-variable-builtin",
        ),
        pytest.param(
            "c=command; \"${c}\" bash <<'EOF'\ncd .claude\ntee settings.json\nEOF",
            id="quoted-variable-command-heredoc",
        ),
        pytest.param("c=time; $c bash -c 'x=.e; tee ${x}nv'", id="variable-time"),
    ),
)
def test_scanner_reads_a_runner_or_a_variable_that_starts_the_command(
    command: str,
) -> None:
    assert _hit(command)


@pytest.mark.parametrize(
    "command",
    (
        pytest.param("exec bash -c 'echo hi'", id="exec-harmless"),
        pytest.param("c=cd; $c docs; cmd x", id="variable-cd-elsewhere"),
        pytest.param("c=echo; $c hi", id="variable-echo"),
        pytest.param("nohup bash -c 'cd docs; tee x'", id="nohup-elsewhere"),
    ),
)
def test_scanner_does_not_invent_a_write_for_a_runner_or_a_variable(
    command: str,
) -> None:
    assert not _hit(command)


@pytest.mark.parametrize(
    "command",
    (
        pytest.param(
            "bash 0<<'EOF'\ncd .claude\ntee settings.json\nEOF", id="fd-heredoc"
        ),
        pytest.param("bash 0<<< 'x=.e; tee ${x}nv'", id="fd-here-string"),
        pytest.param(
            "bash <<-'EOF'\n\tx=.e; tee ${x}nv\nEOF", id="tab-stripped-heredoc"
        ),
        pytest.param(
            "bash <<'EOF' > out.txt\nx=.e; tee ${x}nv\nEOF",
            id="heredoc-and-a-redirect",
        ),
        pytest.param(
            "bash <<<$'cd .claude\\ntee settings.json'", id="ansi-c-here-string"
        ),
        pytest.param(
            "bash <(cat <<'EOF'\ncd .claude\ntee settings.json\nEOF\n)",
            id="script-from-a-process-substitution",
        ),
        pytest.param(
            "bash -c \"$(cat <<'EOF'\ncd .claude\ntee settings.json\nEOF\n)\"",
            id="script-from-a-command-substitution",
        ),
        pytest.param(
            "env bash -c \"$(cat <<'EOF'\nx=.e; tee ${x}nv\nEOF\n)\"",
            id="script-from-a-substitution-through-env",
        ),
    ),
)
def test_scanner_reads_a_shell_script_given_in_another_spelling(command: str) -> None:
    assert _hit(command)


@pytest.mark.parametrize(
    "command",
    (
        pytest.param(
            "source /dev/stdin <<< 'cd .claude'; cmd settings.json",
            id="here-string-folder-stays",
        ),
        pytest.param(
            ". /dev/stdin <<< 'x=.e'; tee ${x}nv", id="here-string-variable-stays"
        ),
        pytest.param(
            "source /dev/stdin <<< 'tee .claude/settings.json'",
            id="here-string-body",
        ),
        pytest.param(
            "cd .claude; cat <<'EOF' | source /dev/stdin\ntee settings.json\nEOF",
            id="pipe-body",
        ),
        pytest.param("cat <<< 'x=.e; tee ${x}nv' | . /dev/stdin", id="pipe-built-name"),
        pytest.param("busybox sh -c 'x=.e; tee ${x}nv'", id="busybox-shell-script"),
        pytest.param(
            "busybox ash <<'EOF'\nx=.e; tee ${x}nv\nEOF", id="busybox-shell-heredoc"
        ),
    ),
)
def test_scanner_reads_stdin_text_that_source_and_busybox_run(command: str) -> None:
    assert _hit(command)


@pytest.mark.parametrize(
    "command",
    (
        pytest.param(
            "cat <<< 'cd .claude' | source /dev/stdin; cmd settings.json",
            id="pipe-folder-stays-in-the-subshell",
        ),
        pytest.param("source /dev/stdin <<< 'cd docs'; cmd x", id="elsewhere"),
        pytest.param("busybox ls -l", id="busybox-applet"),
    ),
)
def test_scanner_does_not_invent_state_from_stdin_text_that_source_runs(
    command: str,
) -> None:
    assert not _hit(command)
