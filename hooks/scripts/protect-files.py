#!/usr/bin/env python3
"""Classify protected-file mutations from one PreToolUse payload."""

from __future__ import annotations

import fnmatch
import glob
import json
import os
import posixpath
import re
import signal
import sys


# Repository files that run, disable, or redirect hooks or server commands.
# `PROTECTED_PATH_LITERAL` below is built from this set, so a name added here
# is also found in Bash text.
HOOK_CONFIGS = {
    ".github/hooks/hooks.json",
    ".claude/settings.json",
    # Claude local settings can add hooks or turn them off.
    ".claude/settings.local.json",
    ".codex/config.toml",
    ".codex/hooks.json",
    # Antigravity's only hook config.
    ".agents/hooks.json",
    # MCP configs launch server commands.
    ".mcp.json",
    ".vscode/mcp.json",
    ".agents/mcp_config.json",
    # VS Code workspace settings (`chat.useHooks`, `chat.hookFilesLocations`,
    # `chat.useClaudeHooks`) and Copilot settings (`disableAllHooks`, inline
    # `hooks`) can turn hooks off or move them.
    ".vscode/settings.json",
    ".github/copilot/settings.json",
    ".github/copilot/settings.local.json",
}
# Folders whose files, and the folders themselves, are protected: hook scripts
# and agent definitions (an agent file sets instructions and, in some clients,
# tools, hooks, MCP servers, and permission mode). Not the parent folders
# `.claude`, `.github`, `.codex`, `.agents` (that would block the nested
# checkpoint `git -C .claude add -A`), skill folders, or `shared/agents/`.
# `protected()` and `PROTECTED_PATH_LITERAL` both read this tuple, so they
# cannot drift. A `*.code-workspace` file is protected by name in both too.
CONTROL_PLANE_DIRS: tuple[str, ...] = (
    ".github/hooks",
    ".claude/hooks",
    ".codex/hooks",
    ".claude/agents",
    ".codex/agents",
    ".github/agents",
    ".agents/agents",
)
# Tools whose input is a shell command line (`tool_input.command`). A name that
# ends in `bash` or an empty name is also treated as a shell command in `main`.
TERMINAL_TOOLS = {"bash", "shell", "run_in_terminal", "send_to_terminal"}
# Native tools that only read. A hook-config path argument is never a write for
# them, so it gets no decision; a secret-shaped file (`.env*`, `uv.lock`,
# credentials, keys) is still denied, and their text is not scanned for patches.
# Exact lowercase names only; anything else is checked in full.
READ_ONLY_TOOLS = {
    "read_file",
    "view_image",
    "list_dir",
    "file_search",
    "grep_search",
    "semantic_search",
    "view",
    "grep",
    "rg",
    "glob",
}
PATH_KEYS = {
    "path",
    "file",
    "filepath",
    "file_path",
    "old_path",
    "new_path",
    "uri",
    "files",
    "dirpath",
}
PATCH_PREFIXES = (
    "*** Add File: ",
    "*** Update File: ",
    "*** Delete File: ",
    "*** Move to: ",
)
OPERATORS = {";", "&&", "||", "|", "|&", "&", "(", ")"}
# Characters that end a shell word: blanks (space, tab, newline; a carriage
# return is an ordinary character) and the operator characters.
PUNCTUATION = ";&|<>()"
WORD_BREAKS = " \t\n" + PUNCTUATION
# Bash's operator tokens, longest first, so a run of operator characters is read
# by longest match (`&&(` is `&&` then `(`). Only `OPERATORS` split a command
# into segments (`|&` is a pipe). The others are words here, and the redirects
# among them (`>`, `>>`, `&>`, `&>>`, `<>`, `>&`) take the next word as a target.
# `>&-` and `<&-` close a descriptor and take none: Bash ends the word after the `-`
# (`>&-{a,b}` closes stdout and passes two words).
SHELL_OPERATORS = sorted(
    ";;& &>> <<< <<- ;; ;& && || |& << <&- >&- <& <> >> >& >| &> ; & | ( ) < >".split(),
    key=len,
    reverse=True,
)
# Operators that need a command after them, even past a newline.
BINARY_OPERATORS = {"&&", "||", "|", "|&"}
REDIRECTS = {">", ">>", ">|", "&>", "&>>", "<>", "1>", "1>>", "2>", "2>>"}
# What `>&` duplicates when it is not followed by a file: a file descriptor number
# (`2>&1`), optionally moved (`1>&2-`), or `-` to close (`>&-`).
FD_TARGET = re.compile(r"[0-9]+-?|-")
SIMPLE_MUTATORS = {"rm", "rmdir", "touch", "mkdir", "truncate", "tee", "ln"}
READ_ONLY = {"cat", "wc", "rg", "grep", "head", "tail", "sed", "stat"}
# git subcommands that cannot write to a path they merely reference. Anything
# else routes through the generic unknown-command handling below: git has too
# many mutating subcommands to enumerate, so we do not assume the rest are safe.
GIT_READ_ONLY_SUBCOMMANDS = {
    "diff",
    "show",
    "log",
    "status",
    "blame",
    "grep",
    "cat-file",
    "ls-files",
    "ls-tree",
    "rev-parse",
    "describe",
}
# git global options that take a value, so the subcommand scan can skip past
# them (e.g. `git -C .claude status`) instead of misreading their value as
# the subcommand. Not the full git CLI grammar - just common dev usage.
GIT_GLOBAL_VALUE_OPTIONS = {"-C", "-c", "--git-dir", "--work-tree"}
ASSIGNMENT = re.compile(
    r"^([A-Za-z_][A-Za-z0-9_]*)(?:\[(-?[0-9]+)\])?(\+?)=(.*)$", re.S
)
VARIABLE_REFERENCE = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?")
# The start of an array assignment: `NAME=` or `NAME+=` right before a `(`.
ASSIGNMENT_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\[[^\]]*\])?\+?=")
ARRAY_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\+?=")
# A glob character: in a quoted word, the word may be a pattern (see
# `QUOTED_PATTERN_PREFIX`). A brace list is not one: `find -name '{a,b}'` never
# expands it.
QUOTED_GLOB = re.compile(r"[?*[]")
# Quoted text that must not be expanded again: a glob, a brace list, or a
# variable reference (`$NAME`, `${NAME}`). A word holding such a quoted part is
# returned by the scanner with `QUOTED_VALUE_PREFIX`.
QUOTED_MAGIC = re.compile(QUOTED_GLOB.pattern + r"|(?<!\$)\{[^{}]+\}|\$\{?[A-Za-z_]")
# `NAME:-word` and its relatives, and `NAME/pattern/replacement` and its relatives,
# inside `${ }`: the word is what the expansion may become.
DEFAULT_EXPANSION = re.compile(
    r"(?:[A-Za-z_][A-Za-z0-9_]*|[0-9]+|[@*#?!$-])(?::?[-=+])(?P<word>.*)", re.S
)
REPLACE_EXPANSION = re.compile(
    r"(?:[A-Za-z_][A-Za-z0-9_]*|[0-9]+|[@*])/[/#%]?(?:[^/\\]|\\.)*(?:/(?P<word>.*))?",
    re.S,
)
ANSI_C_ESCAPE = re.compile(
    r"\\(x[0-9A-Fa-f]{1,2}|[0-7]{1,3}|u[0-9A-Fa-f]{1,4}|U[0-9A-Fa-f]{1,8}|c.|.)", re.S
)
ANSI_C_SIMPLE_ESCAPES = {
    "a": "\a",
    "b": "\b",
    "e": "\x1b",
    "E": "\x1b",
    "f": "\f",
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "v": "\v",
    "\\": "\\",
    "'": "'",
    '"': '"',
    "?": "?",
}
# An unquoted `$IFS` or `${IFS}` expands to blanks, which split the word around it.
IFS_REFERENCE = re.compile(r"\$(?:IFS(?![A-Za-z0-9_])|\{IFS[^{}]*\})")
# `variables` also records, under these key prefixes, a name defined as a function
# or an alias (it then shadows a command of that name) and an array's elements
# (joined by NUL). A key cannot clash with a variable name.
FUNCTION_KEY = "()"
ARRAY_KEY = "[]"
SHADOWED = "(function)"
FUNCTION_NAME = re.compile(
    r"(?:^|[\s;&|(){}])([A-Za-z_][\w.:+-]*)\s*\(\s*\)|\bfunction\s+([A-Za-z_][\w.:+-]*)"
)
ALIAS_COMMAND = re.compile(r"\balias\b([^;&|\n]*)")
ALIAS_NAME = re.compile(r"(?:^|\s)([A-Za-z_][\w.:+-]*)=")
ARRAY_REFERENCE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\[([@*]|-?[0-9]+)\]\}")
ARRAY_SLICE = re.compile(
    r"\$\{([A-Za-z_][A-Za-z0-9_]*)\[[@*]\]:\s*(-?[0-9]+)(?::\s*(-?[0-9]+))?\}"
)
INDIRECT_REFERENCE = re.compile(r"\$\{!([A-Za-z_][A-Za-z0-9_]*)\}")
# A word that starts a compound command and is followed by the command it runs.
SHELL_KEYWORDS = {
    "if",
    "then",
    "elif",
    "else",
    "while",
    "until",
    "do",
    "{",
    "!",
    "time",
}
PLAIN_REFERENCE = re.compile(
    r"\$(?:([A-Za-z_][A-Za-z0-9_]*)|\{([A-Za-z_][A-Za-z0-9_]*)\})"
)
# `${NAME#pat}`, `${NAME%pat}`, `${NAME/pat/word}`, `${NAME:offset:length}`, and
# `${NAME^}` on a tracked variable, with a pattern free of quotes and expansions.
PARAM_OPERATION = re.compile(
    r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?:"
    r"(?P<cut>##?|%%?)(?P<cut_pattern>[^${}'\"\\]*)"
    r"|(?P<replace>//|/[#%]?)(?P<find>[^${}/'\"\\&]*)(?:/(?P<word>[^${}'\"\\&]*))?"
    r"|:(?!-|=|\+|\?)\s*(?P<offset>-?\d+)(?::\s*(?P<length>-?\d+))?"
    r"|(?P<case>\^\^?|,,?)"
    r")\}"
)
# `shopt -s dotglob`, `GLOBIGNORE=`, and zsh's `setopt glob_dots` make a glob match
# hidden files, which the guard cannot list.
DOTGLOB = re.compile(
    r"\bshopt\b[^;&|\n]*\s-\w*s\w*\b[^;&|\n]*\bdotglob\b"
    r"|\bGLOBIGNORE\s*="
    r"|\bsetopt\b[^;&|\n]*\b(?:glob_?dots|dotglob)\b",
    re.IGNORECASE,
)
# What a zsh glob qualifier needs to run code: `e` followed by a delimiter, or `+`
# and a function name. Read in the group after a glob character.
ZSH_QUALIFIER_CODE = re.compile(r"(?:^|[^A-Za-z0-9_])e[^A-Za-z0-9_]|\+[A-Za-z_]")
# `find` actions that act on every file the tests let through; an `-exec` whose
# command is one of these only reads.
FIND_EXEC_ACTIONS = {"-exec", "-execdir", "-ok", "-okdir"}
FIND_READ_ONLY_COMMANDS = (READ_ONLY - {"sed"}) | set(
    "ls echo printf file du basename dirname realpath readlink md5sum sha1sum "
    "sha256sum test true false".split()
)
FIND_PATTERN_TESTS = {
    "-name": "name",
    "-iname": "name",
    "-path": "path",
    "-ipath": "path",
    "-wholename": "path",
    "-iwholename": "path",
    "-regex": "regex",
    "-iregex": "regex",
}
# Operators that make `find`'s expression more than a conjunction of tests.
FIND_COMBINERS = {"-o", "-or", "!", "-not", "(", ")", "-prune"}
# Names and paths a protected file can have, to ask whether a `find` test can match one.
FIND_SAMPLE_NAMES = (
    ".env",
    ".env.local",
    "uv.lock",
    "credentials",
    "credentials.json",
    "key.pem",
    "id.key",
    "a.code-workspace",
) + tuple(config.rsplit("/", 1)[-1] for config in sorted(HOOK_CONFIGS))
FIND_CONFIG_PATHS = {
    config.rsplit("/", 1)[-1]: config for config in sorted(HOOK_CONFIGS)
}
FIND_SAMPLE_PATHS = (
    tuple("./" + name for name in FIND_SAMPLE_NAMES)
    + tuple("./" + config for config in sorted(HOOK_CONFIGS))
    + tuple("./" + folder + "/x.sh" for folder in CONTROL_PLANE_DIRS)
)
# A substitution glued to text may complete a protected name (`$(echo .e)nv`).
BUILT_NAMES = (".env", ".env.local", "uv.lock")
BUILT_PREFIXES = (".env.", "credentials")
BUILT_SUFFIXES = (".pem", ".key")
ZSH_EXPANSION_FLAGS = (
    "a zsh parameter expansion flag list ${(...)x} can run code and is not read"
)
QUOTE_IN_QUOTED_EXPANSION = (
    "a single quote inside a double-quoted parameter expansion is read "
    "differently by Bash and by POSIX shells"
)
# An extended glob operator: `@( )`, `*( )`, `+( )`, `?( )`, `!( )`.
EXTENDED_GLOB = re.compile(r"[@*+?!]\(")
# The word `case` followed by a blank, as a word of its own. Any such word is
# taken for the start of a case statement, wherever it stands: Bash reads `case`
# as one after `!`, `time`, `coproc`, `function NAME`, a reserved word, and an
# operator, and a list of those places is a list that can miss one. Searched in
# text with its quotes removed.
CASE_WORD = re.compile(r"(?:^|[\s;&|(){}!])case(?=[ \t\n])")
# Every alternative below is a *candidate* generator for `protected()`, not
# the decider (see `protected_path_literals`'s docstring). Each one carries
# word/token boundaries so it cannot extract a false-positive fragment out of
# a longer identifier or path: `(?<![\w.-])`/`(?![\w.-])` refuse a preceding
# or following identifier character (letter, digit, `_`, `.`, `-`), so
# `os.environ` no longer yields `.env` and `myuv.lock` no longer yields
# `uv.lock`, while `.env.local` and `foo/.env.production` still match in
# full. The three control-plane alternatives (`CONTROL_PLANE_DIRS` folders
# with or without a path after them, `*.code-workspace` files, and the
# `HOOK_CONFIGS` filenames) additionally capture the **whole** path token
# via an explicit, optional `(?:[^\s'\"]*/)?` directory-prefix group, rather
# than only the fixed repository-relative-looking tail: `/tmp/scratch/
# .claude/settings.json` now extracts as that whole absolute string, so
# `protected()` can tell it apart from an in-repository reference instead of
# reading every occurrence as repository-relative (Phase F3.4).
PROTECTED_PATH_LITERAL = re.compile(
    r"(?:(?<![\w.-])\.env(?:\.[\w.-]+)?(?![\w.-])|"
    r"(?<![\w.-])uv\.lock(?![\w.-])|"
    r"(?<![\w.-])credentials[-_.][\w.-]+|"
    r"[^\s/'\"]+\.(?:pem|key)(?![\w.-])|"
    r"(?<![\w./-])(?:[^\s'\"]*/)?(?:"
    + "|".join(map(re.escape, CONTROL_PLANE_DIRS))
    + r")(?:/[^\s'\"]*)?(?![\w.-])|"
    r"(?<![\w./-])(?:[^\s'\"]*/)?[^\s/'\"]*\.code-workspace(?![\w.-])|"
    r"(?<![\w./-])(?:[^\s'\"]*/)?(?:"
    + "|".join(map(re.escape, sorted(HOOK_CONFIGS)))
    + r"))",
    re.IGNORECASE,
)
# Matching `PROTECTED_PATH_LITERAL` takes time quadratic in the length of a word
# (80 KB took 8 s and 200 KB minutes; the hook times out at 10 s, and a timeout
# lets the command through). Every alternative holds one of these names, so a
# word without one has no literal. `protected_path_literals` skips such a word
# when it is longer than `LONG_WORD` (no real file name is) and fails closed on
# a long word that does hold a name.
PROTECTED_NAME = re.compile(
    "|".join(
        map(
            re.escape,
            (
                ".env",
                "uv.lock",
                "credentials",
                ".pem",
                ".key",
                ".code-workspace",
                *CONTROL_PLANE_DIRS,
                *sorted(HOOK_CONFIGS),
            ),
        )
    ),
    re.IGNORECASE,
)
LONG_WORD = 512
# Seconds the whole classifier may run (see the end of the file).
CLASSIFIER_SECONDS = 4
OPAQUE_WRITE_PATH = re.compile(
    r"(?:write_text|write_bytes)\(\s*['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)
BUILTIN_OPEN_PATH = re.compile(
    r"(?<!\.)open\(\s*['\"]([^'\"]+)['\"](?:\s*,\s*(?:mode\s*=\s*)?['\"]([^'\"]+)['\"])?",
    re.IGNORECASE,
)
PATHLIB_WRITE_PATH = re.compile(
    r"Path\(\s*['\"]([^'\"]+)['\"]\s*\)\.write_(?:text|bytes)\(",
    re.IGNORECASE,
)
PATHLIB_OPEN_WRITE_PATH = re.compile(
    r"Path\(\s*['\"]([^'\"]+)['\"]\s*\)\.open\(\s*(?:mode\s*=\s*)?['\"]([^'\"]*)['\"]",
    re.IGNORECASE,
)
BUILTIN_OPEN_KEYWORDS = re.compile(
    r"(?<!\.)open\([^)]*file\s*=\s*['\"]([^'\"]+)['\"][^)]*mode\s*=\s*['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)
PATHLIB_OPEN_KEYWORDS = re.compile(
    r"Path\(\s*['\"]([^'\"]+)['\"]\s*\)\.open\([^)]*mode\s*=\s*['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)
OPTION_VALUES = {
    "chmod": {"--reference"},
    "chown": {"--reference", "--from"},
    "cp": {"--suffix"},
    "install": {
        "-b",
        "-g",
        "-m",
        "-o",
        "-S",
        "--backup",
        "--group",
        "--mode",
        "--owner",
        "--suffix",
    },
    "mv": {"--suffix"},
    "perl": {"-e", "-E", "-f", "-M", "-m"},
    "sed": {"-e", "-f", "--expression", "--file"},
}
# command_name()'s sudo/env/command wrapper-flag skip: flags that consume a
# separate value token (or an attached `--long=value`/`-short=value`) versus
# flags that take no value at all. Not the full flag set of any of these
# tools - only what is needed to keep the wrapper-skip loop from ever
# mistaking a value token, or an unrecognized flag, for the command name.
WRAPPER_VALUE_FLAGS: dict[str, set[str]] = {
    "env": {"-u", "--unset", "-C", "--chdir", "-S", "--split-string", "-P"},
    "sudo": {"-u", "--user", "-g", "--group"},
    "command": set(),
}
WRAPPER_NO_VALUE_FLAGS: dict[str, set[str]] = {
    "env": {"-i", "--ignore-environment", "-0", "--null"},
    "sudo": set(),
    "command": {"-p", "-v", "-V"},
}
QUOTED_VALUE_PREFIX = "__PROTECT_FILES_QUOTED_VALUE__"
# A word that is one quoted glob (`'*.pem'`) is a pattern, not a file name:
# `find` and `ls` match it, they do not write to it. It starts with
# `QUOTED_VALUE_PREFIX`, so every check for that prefix also finds it.
QUOTED_PATTERN_PREFIX = QUOTED_VALUE_PREFIX + "PATTERN__"
# Commands that run their arguments, or hand them to another command, so a
# quoted word after them is text they interpret, never a pattern for them to
# match: `bash -c '{rm,.env}'` expands the list and runs `rm`.
RUNNERS = frozenset(
    (
        "bash sh zsh dash ksh ash fish csh tcsh busybox eval exec source . builtin "
        "command xargs env sudo doas nohup timeout time nice ionice setsid stdbuf "
        "watch perl ruby node nodejs php awk gawk mawk lua tclsh deno bun"
    ).split()
)
RUNNER_PATTERN = re.compile(r"python[0-9.]*")
# Text a pattern word cannot hold: a quoted word with a space, an operator
# character, or a quote is a script or a sentence (`bash -c 'cmd > f; echo *'`),
# which must still be read for what it names.
PATTERN_UNSAFE = re.compile(r"[\s;|&<>'\"\\]")
PROCESS_SUB_PREFIX = "__PROTECT_FILES_PROCSUB_"
# A placeholder for `$( )`, `$(( ))`, `<( )`, or `>( )` left inside a word.
SUBSTITUTION_PLACEHOLDER = re.compile(re.escape(PROCESS_SUB_PREFIX) + r"\d+__")
HEREDOC_PREFIX = "__PROTECT_FILES_HEREDOC_"
# Shell interpreters whose *bare* heredoc body (no inline -c script and no
# script-file argument) is the script they actually execute, so it is
# recursively classified rather than merely scanned as literal text.
SHELL_INTERPRETERS = {"bash", "sh", "zsh"}
# Work allowed for reading one command: this many units per character of the
# command, plus a floor. Every re-scan of the same text is charged to one
# budget (see `_charge`), so a crafted command that makes the guard scan the
# same text over and over fails closed instead of running past the hook
# timeout and being let through.
WORK_PER_CHARACTER = 50
MINIMUM_WORK = 10_000
# Work left for the `shell_targets` call that is running, or None outside one.
_work_left: list[int] | None = None


class AmbiguousCommand(ValueError):
    """Valid shell syntax the classifier cannot fully model.

    Not a crash: callers resolve this against protected-resource evidence
    (allow if none is present, conservative deny if some is) rather than
    failing the whole hook closed.
    """


class UnparseableCommand(ValueError):
    """The shell text itself could not be tokenized (e.g. an unterminated
    quote, an unbalanced substitution, or a heredoc with no
    delimiter word or no terminator line).

    Deliberately a sibling of AmbiguousCommand, not a subclass: recursive
    classification of a substitution or a bare shell heredoc runs
    inside an `except AmbiguousCommand` fallback (see `classify_command`), so
    genuinely malformed nested syntax must keep propagating to the top-level
    fail-closed exit instead of being caught there and downgraded to a soft,
    resource-scoped denial.
    """


def strip_quoted_prefix(value: str) -> str:
    """`value` without the scanner's quoted-word prefix, of either kind."""
    if value.startswith(QUOTED_PATTERN_PREFIX):
        return value[len(QUOTED_PATTERN_PREFIX) :]
    return value.removeprefix(QUOTED_VALUE_PREFIX)


def normalize(path: str, repo_root: str) -> str:
    value = path.strip().strip("\"'").replace("\\", "/")
    value = strip_quoted_prefix(value)
    if value.startswith("file://"):
        value = value[7:]
    if repo_root and value.startswith(repo_root.rstrip("/") + "/"):
        value = value[len(repo_root.rstrip("/")) + 1 :]
    return posixpath.normpath(value).removeprefix("./")


def _control_plane_in_repo_root(source: str, repo_root: str) -> bool:
    """Fail-closed containment test gating the control-plane clause below.

    `source` is the single path `normalized` (in the loop in `protected()`)
    was actually derived from - `candidate` for the lexical, symlink-
    unresolved form, `resolved` for the `os.path.realpath()` form - never
    the other one. Pairing each name-pattern match with its own source is
    what keeps a same-repository symlink pointing at a foreign control-plane
    file from reading as protected merely because the *link itself* lives in
    this repository (its `resolved` form, which is what matched the name
    pattern, does not).

    `source` is tested against **both** `repo_root`'s own literal form and
    its `os.path.realpath()` form, contained if either succeeds.
    `repo_root_from_script` (`_lib-frontmatter.sh`) resolves `REPO_ROOT` with
    a plain `cd && pwd`, which preserves a symlinked path component instead
    of resolving it (macOS `/tmp` -> `/private/tmp` is the standard case; a
    symlinked home directory or mount is another). Without this, a `source`
    reached through the *other* form of the same directory - `resolved`
    following symlinks down to `repo_root`'s physical path while `repo_root`
    itself is still the symlinked one, or vice versa - would read as outside
    a repository it is actually inside.

    Containment is decided on resolved path components via
    `os.path.commonpath`, never a string prefix, so a sibling directory
    whose name merely starts with `repo_root` (`/repo-evil` vs `/repo`) is
    never mistaken for containment.

    Returns True - in-repository, keep protecting - for every case this
    classifier cannot safely rule out: an empty or non-existent `repo_root`,
    a `source` that still carries an unresolved shell construct (`$`, a
    backtick, a glob metacharacter this classifier could not expand, or the
    internal `QUOTED_VALUE_PREFIX` marker for an unresolved quoted
    variable), or any `OSError`/`ValueError` from the path comparison
    itself.
    """
    if not repo_root or not os.path.isdir(repo_root):
        return True
    if (
        "$" in source
        or "`" in source
        or QUOTED_VALUE_PREFIX in source
        or glob.has_magic(source)
    ):
        return True
    try:
        source_norm = os.path.normpath(source)
        repo_lexical = os.path.normpath(repo_root)
        repo_real = os.path.realpath(repo_root)
        lexically_inside = (
            os.path.commonpath([repo_lexical, source_norm]) == repo_lexical
        )
        really_inside = os.path.commonpath([repo_real, source_norm]) == repo_real
    except (OSError, ValueError):
        return True
    return lexically_inside or really_inside


def _default_word(body: str) -> str:
    """What a `${ }` may expand to: the word of `${NAME:-word}` (also `-`, `:=`, `=`,
    `:+`, `+`) or the replacement of `${NAME/pattern/word}` (also `//`, `/#`, `/%`),
    with quotes removed; nothing for any other form."""
    match = DEFAULT_EXPANSION.fullmatch(body) or REPLACE_EXPANSION.fullmatch(body)
    if match is None:
        return ""
    return re.sub(r"[\"']", "", _replace_expansions(match.group("word") or "", True))


def _expansion_spans(text: str) -> list[tuple[int, int]]:
    """(start, end) of each `${ }` in `text`, found as Bash finds it (see
    `_matching_brace`). A `${` after an odd number of `$` is the process id and
    `{`, not an expansion; an unterminated one ends the search."""
    spans: list[tuple[int, int]] = []
    index = 0
    while True:
        start = text.find("${", index)
        if start == -1:
            return spans
        run = 0
        while start - run > 0 and text[start - run - 1] == "$":
            run += 1
        if run % 2:
            index = start + 2
            continue
        end = _matching_brace(text, start)
        if end == -1:
            return spans
        spans.append((start, end))
        index = end


def _replace_expansions(text: str, defaults: bool) -> str:
    """`text` with each `${ }` removed, or replaced by its default word when
    `defaults` is set."""
    pieces: list[str] = []
    index = 0
    for start, end in _expansion_spans(text):
        pieces.append(text[index:start])
        if defaults:
            pieces.append(_default_word(text[start + 2 : end - 1]))
        index = end
    pieces.append(text[index:])
    return "".join(pieces)


def _brace_list(path: str) -> tuple[int, int, list[str]] | None:
    """The first brace list `{a,b}` in `path` that is not part of a `${ }`, as
    (start, end, options), or None. Commas and braces inside a `${ }` do not
    count."""
    masked = path
    for start, end in reversed(_expansion_spans(path)):
        masked = masked[:start] + "\0" * (end - start) + masked[end:]
    match = re.search(r"\{([^{}]+)\}", masked)
    if match is None:
        return None
    options = []
    offset = match.start(1)
    for piece in masked[match.start(1) : match.end(1)].split(","):
        options.append(path[offset : offset + len(piece)])
        offset += len(piece) + 1
    return match.start(), match.end(), options


def _strip_variables(text: str) -> str:
    """`text` without its `${ }` expansions and unresolved `$NAME` references."""
    return VARIABLE_REFERENCE.sub("", _replace_expansions(text, False))


def without_expansions(text: str) -> str:
    """`text` without its substitution placeholders, its `${ }` expansions, and
    its unresolved `$NAME` references: each may expand to nothing, so a protected
    name may be only what is left."""
    return _strip_variables(SUBSTITUTION_PLACEHOLDER.sub("", text))


def expansion_defaults(text: str) -> str:
    """Like `without_expansions`, but each `${NAME:-word}` becomes its `word`: the
    name it may expand to (`${X:-.env}`, `.e${x:-n}v`)."""
    text = _replace_expansions(SUBSTITUTION_PLACEHOLDER.sub("", text), True)
    return VARIABLE_REFERENCE.sub("", text)


def _placeholder_may_complete_a_name(text: str) -> bool:
    """True when a substitution glued to text may complete a secret-shaped name:
    `$(echo .e)nv` can be the name of a protected file. The literal text on each
    side is tested against the protected names (exact, prefix, and suffix
    families); a whole-word substitution (`$(mktemp)`), a directory prefix
    (`$(pwd)/x`), and text that fits no protected name are not flagged."""
    pieces = SUBSTITUTION_PLACEHOLDER.split(text)
    if len(pieces) < 2 or "/" in pieces[-1]:
        return False
    head, tail = pieces[0].rsplit("/", 1)[-1], pieces[-1]
    if (head or tail) and any(
        name.startswith(head)
        and name.endswith(tail)
        and len(name) >= len(head) + len(tail)
        for name in BUILT_NAMES
    ):
        return True
    return (
        len(head) >= 2 and any(p.startswith(head) and p != head for p in BUILT_PREFIXES)
    ) or (
        len(tail) >= 2 and any(x.endswith(tail) and x != tail for x in BUILT_SUFFIXES)
    )


def _expansion_variants(text: str) -> list[str]:
    """The other texts `text` may stand for once its expansions are resolved to
    nothing or to their default words; empty for text with no expansion."""
    if "$" not in text and PROCESS_SUB_PREFIX not in text:
        return []
    variants = dict.fromkeys((without_expansions(text), expansion_defaults(text)))
    # A default word with blanks (`${X:-a b}`) splits into words, each maybe a name.
    words = [word for variant in variants for word in variant.split()]
    return [v for v in dict.fromkeys((*variants, *words)) if v != text]


def protected(path: str, repo_root: str) -> tuple[str, bool] | None:
    """Classify one path as an in-repository control-plane file, an
    anywhere-protected secret-shaped file, or unprotected.

    The two clauses use different scopes on purpose (Phase F3.4): the
    control-plane clause only refuses a name this repository's own hooks,
    settings or devcontainer identify, and only inside this repository - the
    same name elsewhere is that checkout's own control plane, not this
    repository's to govern. The secret-shaped clause is unconditionally
    global, because a credential-shaped file is harmful to mutate or
    exfiltrate in any tree.

    A substitution or an unresolved variable glued to a name (`.env$(true)`,
    `$X.env`) may expand to nothing, so the name without it is checked too.
    """
    for variant in _expansion_variants(path):
        hit = protected(variant, repo_root)
        if hit:
            return hit
    if _placeholder_may_complete_a_name(strip_quoted_prefix(path)):
        return normalize(path, repo_root), False
    raw = normalize(path, repo_root)
    candidate = path.strip().strip("\"'").replace("\\", "/")
    if candidate.startswith("file://"):
        candidate = candidate[7:]
    if not os.path.isabs(candidate):
        candidate = os.path.join(repo_root, candidate)
    resolved = os.path.realpath(candidate)
    # Each normalized form is paired with the single path it was actually
    # derived from, so `_control_plane_in_repo_root` is never asked about
    # one form's name while deciding the other form's location.
    normalized_paths = [(raw, candidate)]
    if repo_root:
        normalized_paths.append(
            (os.path.relpath(resolved, repo_root).replace("\\", "/"), resolved)
        )
    else:
        normalized_paths.append((resolved.replace("\\", "/"), resolved))
    forms = []
    for normalized, source in normalized_paths:
        normalized = posixpath.normpath(normalized).removeprefix("./")
        forms.append((normalized, source, posixpath.basename(normalized).lower()))
    # A secret-shaped name is tested first, in both forms, so a control-plane
    # name (a protected folder, a workspace file, or a path whose symlink
    # target is a secret) never softens the secret-file deny to ask or allow.
    for normalized, _source, base in forms:
        if (
            base in {".env", ".env.local", "uv.lock"}
            or base.startswith((".env.", "credentials"))
            or base.endswith((".pem", ".key"))
        ):
            return normalized, False
    for normalized, source, base in forms:
        is_control_plane_name = (
            normalized in HOOK_CONFIGS
            or any(normalized.endswith("/" + name) for name in HOOK_CONFIGS)
            or any(
                normalized == folder
                or normalized.startswith(folder + "/")
                or normalized.endswith("/" + folder)
                or "/" + folder + "/" in normalized
                for folder in CONTROL_PLANE_DIRS
            )
            or base.endswith(".code-workspace")
        )
        if is_control_plane_name and _control_plane_in_repo_root(source, repo_root):
            return normalized, True
    return None


def resolve_operands(
    paths: list[str], base_dir: str, repository_root: str = ""
) -> list[str]:
    """Expand filesystem operands without evaluating shell syntax."""
    display_root = repository_root or base_dir
    resolved: list[str] = []
    for path in paths:
        quoted_value = path.startswith(QUOTED_VALUE_PREFIX)
        path = strip_quoted_prefix(path)
        brace = None if quoted_value else _brace_list(path)
        if brace:
            brace_start, brace_end, options = brace
            for option in options:
                resolved.extend(
                    resolve_operands(
                        [path[:brace_start] + option + path[brace_end:]],
                        base_dir,
                        display_root,
                    )
                )
            continue
        if EXTENDED_GLOB.search(path):
            if not quoted_value:
                # With `shopt -s extglob` Bash expands it to files the guard
                # cannot list, a secret file among them: refuse, do not guess.
                raise UnparseableCommand("an extended glob in a write operand")
            resolved.append(path)
            resolved.extend(protected_path_literals(path))
            continue
        bare = _strip_variables(path)
        if bare != path and glob.has_magic(bare):
            # `"$X".e*` and `$X.e*`: the glob still expands, with the variable empty.
            resolved.extend(resolve_operands([bare], base_dir, display_root))
        absolute = path if os.path.isabs(path) else os.path.join(base_dir, path)
        matches = (
            sorted(glob.glob(absolute))
            if glob.has_magic(path) and not quoted_value
            else [absolute]
        )
        if not matches:
            # A glob that matches nothing is passed on as it is: a file with that name,
            # in this folder.
            resolved.append(path)
            matches = [absolute]
        for match in matches:
            display = os.path.relpath(match, display_root) if display_root else match
            resolved.append(display)
            real = os.path.realpath(match)
            if real != os.path.abspath(match):
                resolved.append(
                    os.path.relpath(real, display_root) if display_root else real
                )
    return resolved


def resolve_from_directories(
    paths: list[str], working_directories: list[str], repo_root: str
) -> list[str]:
    """Resolve operands against every cwd the parser considers possible."""
    resolved: list[str] = []
    for directory in working_directories:
        resolved.extend(resolve_operands(paths, directory, repo_root))
    return resolved


def protected_path_literals(value: str) -> list[str]:
    """Extract explicit high-confidence paths from opaque interpreter text."""
    literals: list[str] = []
    # No alternative reaches across whitespace, so the words can be read one by
    # one with the same result as the whole text. A word is read as it is, without
    # its substitutions, and without those and its variables too: each may
    # expand to nothing, and what is left may need the other's neighbours.
    for word in value.split():
        no_substitution = SUBSTITUTION_PLACEHOLDER.sub("", word)
        for text in dict.fromkeys((word, no_substitution, *_expansion_variants(word))):
            if len(text) <= LONG_WORD:
                literals.extend(PROTECTED_PATH_LITERAL.findall(text))
            elif PROTECTED_NAME.search(text):
                raise UnparseableCommand(
                    "a word of %d characters is too long to check for a "
                    "protected name" % len(text)
                )
    return [match.rstrip(",;:)") for match in literals]


def opaque_write_paths(value: str) -> list[str]:
    """Extract literal paths from common interpreter file-write calls."""
    return (
        [match.group(1) for match in OPAQUE_WRITE_PATH.finditer(value)]
        + [match.group(1) for match in PATHLIB_WRITE_PATH.finditer(value)]
        + [
            match.group(1)
            for pattern in (
                BUILTIN_OPEN_PATH,
                PATHLIB_OPEN_WRITE_PATH,
                BUILTIN_OPEN_KEYWORDS,
                PATHLIB_OPEN_KEYWORDS,
            )
            for match in pattern.finditer(value)
            if any(character in (match.group(2) or "r") for character in "wax+")
        ]
    )


def add_patch_paths(value: str, paths: list[str]) -> None:
    if "*** Begin Patch" not in value:
        return
    if "*** End Patch" not in value:
        raise AmbiguousCommand("unterminated apply_patch request")
    for line in value.splitlines():
        for prefix in PATCH_PREFIXES:
            if line.startswith(prefix):
                target = line[len(prefix) :].strip()
                if not target:
                    raise AmbiguousCommand("apply_patch has an empty target")
                paths.append(target)
                break


def _charge(work: int) -> None:
    """Charge `work` units to the budget of the command being read; fail closed
    once it is spent. Does nothing outside `shell_targets`."""
    if _work_left is not None:
        _work_left[0] -= work
        if _work_left[0] < 0:
            raise UnparseableCommand("shell command is too complex to read")


def _starts_word(text: str, index: int) -> bool:
    """True when `text[index]` begins a shell word, where a `#` is a comment.

    A word begins after whitespace, a newline, or an operator character, unless
    a backslash escapes that character: an odd run of backslashes before it
    makes a space or operator part of the word and a newline a line
    continuation, which Bash removes before it reads words.
    """
    if index == 0:
        return True
    slashes = 0
    while index - 2 - slashes >= 0 and text[index - 2 - slashes] == "\\":
        slashes += 1
    return slashes % 2 == 0 and text[index - 1] in WORD_BREAKS


_DOUBLE_QUOTE_SPECIAL = re.compile(r'[\\"$`]')
_BACKTICK_SPECIAL = re.compile(r"[\\`]")
_ANSI_C_SPECIAL = re.compile(r"[\\']")


def _skip_double_quoted(text: str, cursor: int) -> int:
    """Return the index just past the `"` that closes the double-quoted string
    whose body starts at `text[cursor]`, or -1 if the text ends first.

    A backslash escapes the next character. `$( )` and backtick command
    substitutions are code, so their own quotes nest and the closing quote is
    the first one outside them. The scan is charged to the command's budget.
    """
    start = cursor
    while True:
        match = _DOUBLE_QUOTE_SPECIAL.search(text, cursor)
        if match is None:
            _charge(len(text) - start)
            return -1
        cursor = match.start()
        char = text[cursor]
        if char == '"':
            _charge(cursor - start)
            return cursor + 1
        if char == "\\":
            cursor += 2
        elif char == "$" and text[cursor + 1 : cursor + 2] == "$":
            cursor += 2  # the process id: a `(` or `{` after it opens nothing
        elif char == "$" and text[cursor + 1 : cursor + 2] == "(":
            # ponytail: a here-document body inside this substitution is not
            # parsed, so an apostrophe or `)` in it makes the nesting fail and
            # the scan falls back to the next `"` (what the old lexer did).
            # Phase I classifies substitutions and can parse the body.
            end = _matching_paren(text, cursor + 1)
            cursor = end if end != -1 else cursor + 1
        elif char == "$" and text[cursor + 1 : cursor + 2] == "{":
            end = _matching_brace(text, cursor, True)
            cursor = end if end != -1 else cursor + 1
        elif char == "`":
            end = _skip_backticks(text, cursor)
            cursor = end if end != -1 else cursor + 1
        else:
            cursor += 1


def _skip_backticks(text: str, index: int) -> int:
    """Return the index just past the backtick that closes the one at
    `text[index]`, or -1. A backslash escapes the next character; quotes do not
    protect a backtick, as in Bash."""
    end = index + 1
    while True:
        found = _BACKTICK_SPECIAL.search(text, end)
        if found is None:
            _charge(len(text) - index)
            return -1
        if found.group() == "`":
            _charge(found.end() - index)
            return found.end()
        end = found.start() + 2


def _matching_brace(
    text: str, dollar_index: int, in_double_quotes: bool = False
) -> int:
    """Return the index just past the `}` that closes the `${` at
    `text[dollar_index]`, or -1 when it never closes.

    Bash's rules (checked on 5.2): a backslash escapes the next character;
    `'...'`, `"..."`, `$'...'`, `$"..."`, `$( )`, `$(( ))`, backticks, and a nested
    `${ }` each hide a `}` or a `)` inside them; a plain `{` does not nest; the
    first other `}` closes. A `#` inside is text, not a comment.

    Inside double quotes, shells disagree about a single quote in the `${ }`:
    Bash 5.2 starts a quote at it, but `bash --posix` and dash take it for a
    plain character, so a `}` or a `;` after it ends the expansion or the
    command. The client may run either, so `in_double_quotes` fails closed on a
    `'` or `$'` there.
    """
    index = dollar_index + 2
    length = len(text)
    while index < length:
        _charge(1)
        char = text[index]
        if char == "}":
            return index + 1
        if char == "\\":
            index += 2
        elif char == "'":
            if in_double_quotes:
                raise UnparseableCommand(QUOTE_IN_QUOTED_EXPANSION)
            end = text.find("'", index + 1)
            _charge((length if end == -1 else end) - index)
            if end == -1:
                return -1
            index = end + 1
        elif char == '"':
            end = _skip_double_quoted(text, index + 1)
            if end == -1:
                return -1
            index = end
        elif char == "`":
            end = _skip_backticks(text, index)
            if end == -1:
                return -1
            index = end
        elif char == "$":
            following = text[index + 1 : index + 2]
            if following == "(":
                end = _matching_paren(text, index + 1)
            elif following == "{":
                end = _matching_brace(text, index, in_double_quotes)
            elif following == "$":
                end = index + 2
            elif following == "'":
                if in_double_quotes:
                    raise UnparseableCommand(QUOTE_IN_QUOTED_EXPANSION)
                end = _skip_literal(text, index)
            elif following == '"':
                end = _skip_double_quoted(text, index + 2)
            else:
                end = index + 1
            if end == -1:
                return -1
            index = end
        else:
            index += 1
    return -1


def _skip_literal(text: str, index: int, comments: bool = True) -> int:
    """Return the index just past the quoted, escaped, or comment text that
    starts at `text[index]`, or `index` itself when none starts there. -1 means
    the text ends first: an unterminated quote, expansion, or a trailing
    backslash.

    Bash's rules, outside a here-document body: a backslash makes the next
    character literal; `'...'` is literal; in `$'...'` a backslash escapes the
    next character, `'` included; `"..."` and `$"..."` are double-quoted
    strings (see `_skip_double_quoted`); `$$` is the process id, so what follows
    it is not an expansion; `${ ... }` is one unit up to its own `}` (see
    `_matching_brace`); a `#` that starts a word begins a comment that runs up
    to the next newline (`comments=False` inside `${ }`, where it is text).
    """
    char = text[index]
    if char == "\\":
        return index + 2 if index + 1 < len(text) else -1
    if char == "'":
        end = text.find("'", index + 1)
        _charge((len(text) if end == -1 else end) - index)
        return -1 if end == -1 else end + 1
    if char == "#":
        if not comments or not _starts_word(text, index):
            return index
        end = text.find("\n", index)
        return len(text) if end == -1 else end
    following = text[index + 1 : index + 2]
    if char == "$" and following == "$":
        return index + 2
    if char == "$" and following == "{":
        return _matching_brace(text, index)
    if char == "$" and following == "'":
        cursor = index + 2
        while True:
            match = _ANSI_C_SPECIAL.search(text, cursor)
            if match is None:
                _charge(len(text) - index)
                return -1
            if match.group() == "'":
                _charge(match.end() - index)
                return match.end()
            cursor = match.start() + 2
    if char == '"':
        return _skip_double_quoted(text, index + 1)
    if char == "$" and following == '"':
        return _skip_double_quoted(text, index + 2)
    return index


def _decode_ansi_c(body: str) -> str:
    """The text of the `$'...'` string whose body is `body`: `\\xHH`, `\\NNN`,
    `\\uHHHH`, `\\UHHHHHHHH`, `\\cX`, and the one-letter escapes are decoded
    as Bash does, so an escape can spell a protected name; an unknown escape
    keeps its backslash."""

    def decode(match: re.Match[str]) -> str:
        code = match.group(1)
        kind = code[0]
        if kind == "x":
            return chr(int(code[1:], 16))
        if kind in "01234567":
            return chr(int(code, 8) & 0xFF)
        if kind in "uU":
            number = int(code[1:], 16)
            return chr(number) if number <= 0x10FFFF else ""
        if kind == "c" and len(code) == 2:
            return chr(ord(code[1]) & 0x1F)
        return ANSI_C_SIMPLE_ESCAPES.get(code, "\\" + code)

    return ANSI_C_ESCAPE.sub(decode, body)


def _unquote(span: str) -> str:
    """The text a quoted or escaped span (see `_skip_literal`) stands for."""
    if span[0] == "\\":
        return span[1:]
    if span[0] == "'":
        return span[1:-1]
    if span.startswith("$'"):
        return _decode_ansi_c(span[2:-1])
    body = span[2:-1] if span[0] == "$" else span[1:-1]
    return re.sub(
        r"\\([$`\"\\]|\n)",
        lambda match: "" if match.group(1) == "\n" else match.group(1),
        body,
    )


def _heredoc_operator(text: str, index: int) -> tuple[str, bool, bool, int] | None:
    """Read the here-document operator at `text[index]` (`<<` or `<<-`): its
    delimiter word with the quotes removed, whether any part of the word was
    quoted (the body is then not expanded), whether tabs are stripped from the
    body, and the index after the word. None when no word follows. The delimiter
    is a whole shell word, so `END-OF-DATA` and `EOF#x` are read in full."""
    start = index + 2
    strip_tabs = text[start : start + 1] == "-"
    start += int(strip_tabs)
    while start < len(text) and text[start] in " \t":
        start += 1
    if start >= len(text) or text[start] in WORD_BREAKS:
        return None
    word, quoted, end = _read_word(text, start)
    return strip_quoted_prefix(word), quoted, strip_tabs, end


def _skip_heredoc_bodies(text: str, start: int, pending: list[tuple[str, bool]]) -> int:
    """The index after the bodies of the here-documents in `pending` (each a
    delimiter and a tab-stripping flag), which begin at the line starting at
    `start`; -1 when a body never reaches its terminator line."""
    index = start
    for delimiter, strip_tabs in pending:
        while True:
            if index >= len(text):
                return -1
            end = text.find("\n", index)
            line = text[index:] if end == -1 else text[index:end]
            index = len(text) if end == -1 else end + 1
            if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                break
    _charge(index - start)
    return index


def _heredoc_step(text: str, index: int, pending: list[tuple[str, bool]]) -> int | None:
    """Follow here-document syntax at `text[index]` while scanning text that may
    hold one. An operator adds its delimiter to `pending` and returns the index
    after it; the newline that ends its line skips every pending body and returns
    the index after them (-1 when one never ends); `<<<` is a here-string and is
    skipped. None when nothing here-document related starts at `index`."""
    char = text[index]
    if char == "\n" and pending:
        end = _skip_heredoc_bodies(text, index + 1, pending)
        del pending[:]
        return end
    if char == "<" and text.startswith("<<", index):
        if text.startswith("<<<", index):
            return index + 3
        operator = _heredoc_operator(text, index)
        if operator is not None:
            pending.append((operator[0], operator[2]))
            return operator[3]
    return None


def _matching_paren(text: str, open_index: int, in_arithmetic: bool = False) -> int:
    """Return the index just past the ')' matching text[open_index] == '(',
    honoring nested parens, quotes, and here-documents (a body may hold a `)` or a
    quote). Returns -1 when never closed. `in_arithmetic` says the `(` is the
    inner one of `$((`, so a `<<` there is a shift."""
    depth = 0
    arithmetic = int(in_arithmetic)  # open `((`: a `<<` is a shift, not a heredoc
    pending: list[tuple[str, bool]] = []
    index = open_index
    length = len(text)
    while index < length:
        _charge(1)
        end = _skip_literal(text, index)
        if end == -1:
            return -1
        if end > index:
            index = end
            continue
        char = text[index]
        if char == "\n" or (char == "<" and not arithmetic):
            step = _heredoc_step(text, index, pending)
            if step is not None:
                if step == -1:
                    return -1
                index = step
                continue
        if char == "(":
            depth += 1
            arithmetic += text[index + 1 : index + 2] == "("
        elif char == ")":
            arithmetic -= bool(arithmetic) and text[index + 1 : index + 2] == ")"
            depth -= 1
            if depth == 0:
                return index + 1
        elif char == "`":
            end = _skip_backticks(text, index)
            if end == -1:
                return -1
            index = end
            continue
        index += 1
    return -1


def _refuse_case_statement(inner: str) -> None:
    """Fail closed when the text of a substitution holds the word `case`.

    A case pattern ends with an unmatched `)` (`case a in a) tee f;; esac`), so
    `_matching_paren` closes the substitution there, and the rest of the
    statement would be read as arguments of the outer command. Following
    `case ... esac` the way Bash does would take a second parser that must agree
    with Bash; refusing is smaller and cannot be wrong in the open direction.
    The price is an over-block for a harmless `case` word (`$(grep case f)`).
    Quoted text, escapes, comments, and here-document bodies are not searched (a
    body is data, or its own substitutions are checked on their own). The text may
    be the part up to that first `)`, which still holds the `case` word.
    """
    text = inner.replace("\\\n", "")
    _charge(len(text))
    parts: list[str] = []
    pending: list[tuple[str, bool]] = []
    index = 0
    length = len(text)
    while index < length:
        end = _skip_literal(text, index)
        if end == index:
            step = _heredoc_step(text, index, pending) if text[index] in "<\n" else None
            if step is not None and step != -1:
                index = step
                continue
            parts.append(text[index])
            index += 1
            continue
        if end == -1:
            break
        if text[index] != "#":  # a comment is dropped; a quoted word is one word
            parts.append("x")
        index = end
    if CASE_WORD.search("".join(parts)):
        raise UnparseableCommand("a case statement inside a substitution")


def extract_substitutions(command: str) -> tuple[str, dict[str, str]]:
    """Replace every `$( )`, `$(( ))`, `<( )`, `>( )`, and backtick command
    substitution that Bash runs, quoted or not, with an inert placeholder,
    returning the new text and a placeholder -> inner-command mapping for
    recursive classification.

    A `$( )` or `$(( ))` stays inside its word, as in Bash: `$(pwd)/x` becomes
    `<placeholder>/x`, and a word after the closing `)` is an operand, not a
    new command. A `<( )` or `>( )` is a word of its own (`cat<(...)` is valid:
    `<` ends the word before it), so it gets a space before it; text glued after
    its `)` stays in the word, as in Bash. The scanner reads the placeholder as
    ordinary word text, and `segment_targets` finds each placeholder inside a
    word to classify its inner command.

    A `$( )` or a backtick inside double quotes runs too, so its inner command
    is found there and the quotes are kept around the placeholder; single
    quotes, a backslash before the `$` or the backtick, and a comment keep the
    text literal. `$(( ))` is arithmetic: there is no command to classify, only
    the `$( )` that its expression may hold. An unbalanced construct is genuinely
    malformed shell syntax, not merely unmodeled, so it fails closed rather than
    being silently dropped.
    """
    inner_by_placeholder: dict[str, str] = {}
    return _extract(command, inner_by_placeholder), inner_by_placeholder


def _placeholder(inner: str, inner_by_placeholder: dict[str, str]) -> str:
    """A new placeholder standing for the inner command `inner`."""
    placeholder = "%s%d__" % (PROCESS_SUB_PREFIX, len(inner_by_placeholder))
    inner_by_placeholder[placeholder] = inner
    return placeholder


def _extract_substitution(
    text: str, index: int, inner_by_placeholder: dict[str, str]
) -> tuple[str, int]:
    """The `$( )`, `<( )`, or `>( )` at `text[index]` as (piece, end): a
    placeholder, with a space before it for the process substitutions."""
    opener = text[index : index + 2]
    end = _matching_paren(text, index + 1)
    if end == -1:
        raise UnparseableCommand("unbalanced substitution")
    inner = text[index + 2 : end - 1]
    _refuse_case_statement(inner)
    if (
        opener == "$("
        and inner.startswith("(")
        and _matching_paren(text, index + 2, True) == end - 1
    ):
        inner = "\n".join(extract_substitutions(inner[1:-1])[1].values())
    placeholder = _placeholder(inner, inner_by_placeholder)
    return (placeholder if opener == "$(" else " " + placeholder), end


def _extract_backticks(
    text: str, index: int, inner_by_placeholder: dict[str, str], in_quotes: bool
) -> tuple[str, int]:
    """The backtick substitution at `text[index]` as (placeholder, end). Inside
    backticks a backslash only escapes `$`, a backtick, and a backslash (and a
    double quote when the backticks are themselves inside double quotes)."""
    end = _skip_backticks(text, index)
    if end == -1:
        raise UnparseableCommand("unbalanced backticks")
    escapes = r"\\([`\\$\"])" if in_quotes else r"\\([`\\$])"
    inner = re.sub(escapes, r"\1", text[index + 1 : end - 1])
    return _placeholder(inner, inner_by_placeholder), end


def _extract_expansion(
    text: str, index: int, inner_by_placeholder: dict[str, str], in_quotes: bool
) -> tuple[str, int]:
    """The `${ }` at `text[index]` as (piece, end), with the substitutions in its
    default word replaced. A zsh flag list `${(...)x}` can run code, so it fails
    closed."""
    end = _matching_brace(text, index, in_quotes)
    if end == -1:
        raise UnparseableCommand("unbalanced parameter expansion")
    if text.startswith("(", index + 2):
        raise UnparseableCommand(ZSH_EXPANSION_FLAGS)
    interior = _extract(text[index + 2 : end - 1], inner_by_placeholder, True)
    return "${" + interior + "}", end


def _extract_quoted(span: str, inner_by_placeholder: dict[str, str]) -> str:
    """The double-quoted `span` (`"..."` or `$"..."`) with each substitution in it
    replaced by a placeholder."""
    _charge(len(span))
    start = 2 if span.startswith('$"') else 1
    body = span[start:-1]
    pieces: list[str] = []
    index = 0
    while index < len(body):
        special = _DOUBLE_QUOTE_SPECIAL.search(body, index)
        if special is None:
            pieces.append(body[index:])
            break
        found = special.start()
        pieces.append(body[index:found])
        two = body[found : found + 2]
        if body[found] == "`":
            piece, index = _extract_backticks(body, found, inner_by_placeholder, True)
        elif two == "$(":
            piece, index = _extract_substitution(body, found, inner_by_placeholder)
        elif two == "${":
            piece, index = _extract_expansion(body, found, inner_by_placeholder, True)
        else:  # an escape or `$$`, kept as it is, with its second character
            piece, index = body[found : found + 2], found + 2
        pieces.append(piece)
    return span[:start] + "".join(pieces) + span[-1]


def _extract(
    command: str, inner_by_placeholder: dict[str, str], in_expansion: bool = False
) -> str:
    """The text of `extract_substitutions` for `command`, adding each inner
    command to `inner_by_placeholder`. A `${ }` is walked into, not skipped: its
    default word is expanded and may hold a substitution, and a `#` in it is
    text (`in_expansion`)."""
    pieces: list[str] = []
    index = 0
    length = len(command)
    while index < length:
        if command.startswith("${", index):
            piece, index = _extract_expansion(
                command, index, inner_by_placeholder, False
            )
            pieces.append(piece)
            continue
        end = _skip_literal(command, index, comments=not in_expansion)
        if end != index:
            # Quoted or escaped text or a comment; text that never ends is left
            # for `split_segments`, which fails closed on it.
            span = command[index : length if end == -1 else end]
            if end != -1 and (span[0] == '"' or span.startswith('$"')):
                span = _extract_quoted(span, inner_by_placeholder)
            pieces.append(span)
            index = length if end == -1 else end
            continue
        if command[index] == "`":
            piece, index = _extract_backticks(
                command, index, inner_by_placeholder, False
            )
            pieces.append(piece)
        elif command[index : index + 2] in ("<(", ">(", "$("):
            piece, index = _extract_substitution(command, index, inner_by_placeholder)
            pieces.append(piece)
        else:
            pieces.append(command[index])
            index += 1
    return "".join(pieces)


def _find_unquoted_heredoc(text: str) -> int | None:
    """Return the index of the first <<[-] operator outside any quoting or
    arithmetic span, or None if there is none. A <<< here-string is a
    different construct and is left untouched for the outer tokenizer.

    `<<` is also bash's arithmetic left-shift operator inside `$(( ))`/
    `(( ))`. Two adjacent, unquoted parens open such a span (bash parses
    `((` this way regardless of a leading `$`); while depth is open, `<<`
    is arithmetic, not a heredoc redirect, even though a *single*-paren
    construct like `$( )` or `( )` can legitimately contain a real heredoc.
    """
    _charge(len(text))
    index = 0
    length = len(text)
    arithmetic_depth = 0
    while index < length:
        end = _skip_literal(text, index)
        if end != index:
            index = length if end == -1 else end
            continue
        char = text[index]
        if char == "(" and text[index + 1 : index + 2] == "(":
            arithmetic_depth += 1
            index += 2
            continue
        if char == ")" and arithmetic_depth > 0:
            if text[index + 1 : index + 2] == ")":
                arithmetic_depth -= 1
                index += 2
            else:
                index += 1
            continue
        if arithmetic_depth > 0:
            index += 1
            continue
        if char == "<" and text[index + 1 : index + 2] == "<":
            if text[index + 2 : index + 3] == "<":
                index += 3
                continue
            return index
        index += 1
    return None


def extract_heredocs(
    command: str, start_count: int = 0
) -> tuple[str, dict[str, tuple[str, bool]]]:
    """Remove every here-document body from the text the outer tokenizer will
    see, replacing the whole `<<WORD ... body ... WORD` construct (including
    the optional `<<-` and a bare/'quoted'/"quoted" delimiter word) with an
    inert placeholder. Prose punctuation and apostrophes inside a heredoc
    body can then never corrupt outer shell tokenization.

    Each placeholder maps to `(body_text, quoted)`. `quoted` is True only
    when the delimiter word itself was quoted (`<<'WORD'`/`<<"WORD"`): real
    bash then skips parameter/command-substitution expansion of the body.
    An unquoted delimiter's body is expanded by the shell itself before the
    consuming command ever runs, so it is never inert data regardless of
    what reads it.

    `start_count` numbers placeholders starting above any the caller has
    already allocated (e.g. a shared mapping accumulated across recursive
    calls), so nested extractions can never collide on the same name.

    The placeholder is padded with a space on both sides regardless of what
    was originally adjacent. `<<` is a shell metacharacter that terminates
    the preceding word even with no space (`bash<<'EOF'` is valid bash,
    equivalent to `bash <<'EOF'`), but the word scanner splits only on
    whitespace and operator characters: with no separator it would merge the
    placeholder into an adjacent word, and neither `command_name` nor the
    redirect-target/operand lookups that key off an exact placeholder token
    would ever see it as its own token again. The single extra space is
    always safe: the scanner collapses any run of whitespace, so it can never
    change how an already-separated case tokenizes.

    A missing delimiter word or a body that never reaches its terminator
    line is genuinely malformed shell syntax and fails closed rather than
    being silently ignored.
    """
    bodies: dict[str, tuple[str, bool]] = {}
    result = command
    count = start_count
    while True:
        operator_index = _find_unquoted_heredoc(result)
        if operator_index is None:
            return result, bodies
        operator = _heredoc_operator(result, operator_index)
        if operator is None:
            raise UnparseableCommand("heredoc redirect has no delimiter word")
        delimiter, quoted, strip_tabs, rest_of_line_start = operator
        newline_index = result.find("\n", rest_of_line_start)
        if newline_index == -1:
            raise UnparseableCommand("heredoc %r has no body" % delimiter)
        rest_of_line = result[rest_of_line_start:newline_index]
        body_start = newline_index + 1
        terminator = re.compile(
            r"^%s%s$" % (r"\t*" if strip_tabs else "", re.escape(delimiter)),
            re.MULTILINE,
        )
        terminator_match = terminator.search(result, body_start)
        if not terminator_match:
            raise UnparseableCommand(
                "heredoc delimiter %r is never terminated" % delimiter
            )
        body_text = result[body_start : terminator_match.start()]
        if strip_tabs:
            body_text = "\n".join(line.lstrip("\t") for line in body_text.split("\n"))
        after_terminator = result[terminator_match.end() :]
        if after_terminator.startswith("\n"):
            after_terminator = after_terminator[1:]
        placeholder = "%s%d__" % (HEREDOC_PREFIX, count)
        count += 1
        bodies[placeholder] = (body_text, quoted)
        result = (
            result[:operator_index]
            + " "
            + placeholder
            + " "
            + rest_of_line
            + "\n"
            + after_terminator
        )


def heredoc_command_substitutions(body: str) -> list[str]:
    """Return each $( ) / `...` inner command found in an *unquoted*
    heredoc's body.

    Real bash performs parameter, command-substitution, and arithmetic
    expansion on an unquoted heredoc's body before the consuming command
    ever sees it, so `$(touch .env)` inside `cat <<EOF` executes regardless
    of `cat` being read-only. Unlike an ordinary shell word, the body is not
    re-tokenized with normal quoting rules first: a heredoc body only
    recognizes a backslash escaping a dollar sign, a backtick, or itself - a
    single or double quote is plain literal text here (verified empirically
    in a real bash), so wrapping the construct in quotes does not suppress
    it. Once a genuine `$(` is found, `_matching_paren` still tracks quoting
    *inside* it, because that inner text is itself a normal command line. An
    unbalanced construct here is genuinely malformed and fails closed,
    matching process substitution.
    """
    inner_commands: list[str] = []
    index = 0
    length = len(body)
    while index < length:
        char = body[index]
        if char == "\\":
            index += 2
            continue
        if char == "$" and body[index + 1 : index + 2] == "(":
            end = _matching_paren(body, index + 1)
            if end == -1:
                raise UnparseableCommand("unbalanced command substitution")
            _refuse_case_statement(body[index + 2 : end - 1])
            inner_commands.append(body[index + 2 : end - 1])
            index = end
            continue
        if char == "`":
            end = body.find("`", index + 1)
            if end == -1:
                raise UnparseableCommand("unterminated command substitution")
            inner_commands.append(body[index + 1 : end])
            index = end + 1
            continue
        index += 1
    return inner_commands


def _read_group_word(
    command: str, index: int, parts: list[str], before: str
) -> int | None:
    """If the `(` at `command[index]` continues the word as an array assignment
    (`a=(x y)`) or an extended glob (`@(a|b)`), add its text to `parts` and
    return the index after its `)`; None when it does not, so the word ends.

    Bash keeps a `#` glued after an array's `)` in the word (`a=(x)#c`), but the
    other scans in this file take a `#` after any `)` for a comment, so that form
    fails closed instead of being read two ways.
    """
    if before == "=" and ARRAY_ASSIGNMENT.fullmatch("".join(parts)):
        kind = "array assignment"
    elif before and (before in "@*+?" or (before == "!" and parts != ["!"])):
        kind = "extended glob"
    else:
        return None
    end = _matching_paren(command, index)
    if end == -1:
        raise UnparseableCommand("unbalanced " + kind)
    if kind == "array assignment" and command[end : end + 1] == "#":
        raise UnparseableCommand("a # right after an array assignment")
    if kind == "extended glob" and ZSH_QUALIFIER_CODE.search(
        command[index + 1 : end - 1]
    ):
        # zsh reads `*(e:'cmd':)` and `*(+func)` as glob qualifiers that run code.
        raise UnparseableCommand("a zsh glob qualifier that can run code (e or +)")
    parts.append(command[index:end])
    return end


def _quoted_part(span: str, before: str) -> tuple[str, bool, bool]:
    """(value, magic, glob) of a quoted or escaped span of a word: its text with
    the quotes removed, whether it holds quoted magic that must not be expanded
    again (`QUOTED_MAGIC`), and whether that magic includes a glob character.
    A part glued to a name or to `=` (`NAME='*'`, `--opt="$X"`) is not magic."""
    value = _unquote(span)
    # An escaped character (`"\\$a"`) is literal, so it is not magic.
    literal = (
        value
        if span[0] == "'" or span.startswith("$'")
        else re.sub(r"\\.", "", span, flags=re.S)
    )
    if (
        span[0] != "\\"
        and QUOTED_MAGIC.search(literal)
        and not (before.isalnum() or before in ("_", "="))
    ):
        return value, True, bool(QUOTED_GLOB.search(literal))
    return value, False, False


def _mark_quoted_word(text: str, parts: list[str], glob: bool) -> str:
    """`text` of a word with quoted magic, marked with `QUOTED_PATTERN_PREFIX`
    when the word is only one quoted glob (a brace list does not count) and with
    `QUOTED_VALUE_PREFIX` otherwise."""
    pattern = glob and len(parts) == 1 and not PATTERN_UNSAFE.search(text)
    return (QUOTED_PATTERN_PREFIX if pattern else QUOTED_VALUE_PREFIX) + text


def _read_word(command: str, index: int) -> tuple[str, bool, int]:
    """Read the word that starts at `command[index]`, which is not whitespace,
    a newline, or an operator character. Returns (text, quoted, end): the word
    with its quotes and escapes removed, whether it used any, and the index
    after it. A backslash-newline joins the lines and is not part of a word.

    A quoted part that holds magic (see `_quoted_part`) gives the word a prefix
    (see `_mark_quoted_word`). A `(` right after `NAME=` or `NAME+=` opens an
    array assignment: the list and what is glued after its `)` stay in the word
    (`a=(x)b`). A `(` glued right after `@`, `*`, `+`, `?`, or a `!` that follows
    other text opens an extended glob (`@(a|b)`), which is one word too; without
    `shopt -s extglob` it is a syntax error in Bash, so it is never a group. A
    `!(` at the start of a word may be a negated group and stays one. A `${ }`
    and the process id `$$` are kept in the word as they are, except that an
    unquoted `$IFS` ends the word (it expands to blanks): `tee$IFS` plus a name is
    two words.
    """
    parts: list[str] = []
    quoted = False
    magic = False
    glob = False  # a magic part holds a glob character
    before = ""  # the last character of the word so far
    length = len(command)
    while index < length:
        if command[index] in WORD_BREAKS:
            end = None
            if command[index] == "(":
                end = _read_group_word(command, index, parts, before)
            if end is None:
                break
            before = ")"
            index = end
            continue
        ifs = IFS_REFERENCE.match(command, index) if command[index] == "$" else None
        if ifs:  # blanks end the word
            index = ifs.end()
            break
        end = _skip_literal(command, index)
        if end == -1:
            raise UnparseableCommand("shell command could not be parsed")
        if end == index:
            before = command[index]
            parts.append(before)
            index += 1
            continue
        span = command[index:end]
        if IFS_REFERENCE.fullmatch(span):
            index = end
            break
        if span.startswith("${") or span == "$$":
            parts.append(span)
            before = "}" if span[1] == "{" else "$"
        elif span != "\\\n":
            value, part_magic, part_glob = _quoted_part(span, before)
            magic = magic or part_magic
            glob = glob or part_glob
            parts.append(value)
            before = value[-1:] or before
            quoted = True
        index = end
    text = "".join(parts)
    return (_mark_quoted_word(text, parts, glob) if magic else text), quoted, index


def _shell_tokens(command: str) -> list[tuple[str, bool]]:
    """Read one shell command line the way Bash does, outside here-document
    bodies, as (text, is_operator) pairs: words with their quotes and escapes
    removed, comments dropped, and an unquoted newline as the operator "\\n".

    A run of unquoted `;&|<>()` characters is split into Bash's operators by
    longest match (`SHELL_OPERATORS`). Only the segment operators are returned
    as operators; the others, such as `>>` and `|&`, come back as words. A word
    that was quoted or escaped and reads as an operator or a redirect is
    returned with `QUOTED_VALUE_PREFIX`, so later stages never take it for one.
    """
    tokens: list[tuple[str, bool]] = []
    index = 0
    length = len(command)
    while index < length:
        char = command[index]
        if char in " \t":
            index += 1
        elif char == "\n":
            tokens.append(("\n", True))
            index += 1
        elif char in PUNCTUATION:
            operator = next(
                op for op in SHELL_OPERATORS if command.startswith(op, index)
            )
            tokens.append((operator, operator in OPERATORS))
            index += len(operator)
        elif char == "#" and _starts_word(command, index):
            index = _skip_literal(command, index)  # a comment: up to the newline
        else:
            text, quoted, index = _read_word(command, index)
            if text or quoted:
                if quoted and (text in OPERATORS or is_redirect(text)):
                    text = QUOTED_VALUE_PREFIX + text
                tokens.append((text, False))
    return tokens


def split_segments(command: str) -> list[list[str]]:
    """Split one command line into segments of words at its operators and
    newlines. A blank line and a newline after an operator add no segment. A
    group may open at any command and close after a newline, `;`, `&`, or `(`;
    an operator may follow a `)`. Any other empty segment fails closed."""
    segments: list[list[str]] = [[]]
    last = ""  # the operator the next command follows; "\n" after a newline
    for text, is_operator in _shell_tokens(command):
        if not is_operator:
            segments[-1].append(text)
            last = ""
        elif text == "\n":
            if segments[-1]:
                segments.append([])
            if last not in BINARY_OPERATORS and last != "(":
                last = "\n"
        elif segments[-1]:
            segments.append([])
            last = text
        elif (
            text == "("
            or last == ")"
            or (text == ")" and last in (";", "&", "(", "\n"))
        ):
            last = text
        else:
            raise AmbiguousCommand("empty shell command segment")
    if not segments[-1]:
        # A trailing separator ("rg foo .;") is valid Bash, not an error.
        segments.pop()
    return segments


def _known_value(value: str, variables: dict[str, str]) -> str | None:
    """`value` with the tracked variables in it replaced; None when an expansion
    is left in it (`y=.$x` with `x` tracked is known, `y=$(pwd)/a` is not)."""
    if "$" not in value and "`" not in value:
        return value
    words = substitute([QUOTED_VALUE_PREFIX + value], variables)
    text = strip_quoted_prefix(" ".join(words))
    return None if "$" in text or "`" in text else text


def _array_list(name: str, variables: dict[str, str]) -> list[str]:
    """The tracked elements of `name`: an array's, or a scalar's one element."""
    elements = variables.get(ARRAY_KEY + name)
    if elements is not None:
        return elements.split("\0") if elements else []
    return [variables[name]] if name in variables else []


def _store_array(name: str, items: list[str], variables: dict[str, str]) -> None:
    """Track an array: `$name` is its first element."""
    variables[ARRAY_KEY + name] = "\0".join(items)
    first = items[0] if items else ""
    if "$" in first or "`" in first:
        variables.pop(name, None)
    else:
        variables[name] = first


def _forget(name: str, variables: dict[str, str]) -> None:
    variables.pop(ARRAY_KEY + name, None)
    variables.pop(name, None)


def record_assignment(token: str, variables: dict[str, str]) -> None:
    """Track a bare `NAME=value` token's literal value, if it has one.

    A value that still holds an expansion once the tracked variables are put in
    (`$`, backticks) is not known, so the variable is left unresolved rather than
    guessed. `NAME+=value`, `NAME[N]=value`, and `NAME=(a b)` / `NAME+=(c)` are
    tracked too: an array is kept as its elements, `$NAME` being the first.
    """
    match = ASSIGNMENT.match(token)
    if not match:
        return
    name, index, plus, value = match.groups()
    if index is not None:
        known = _known_value(value, variables)
        position = int(index)
        items = _array_list(name, variables)
        if position < 0:
            position += len(items)
        if known is None or not 0 <= position <= MAX_ARRAY_INDEX:
            _forget(name, variables)
            return
        items = items + [""] * (position + 1 - len(items))
        items[position] = items[position] + known if plus else known
        _store_array(name, items, variables)
        return
    if value.startswith("(") and value.endswith(")"):
        # An array: `$a` is its first element, `${a[N]}` and `${a[@]}` the others.
        elements: list[str] = []
        for word in _array_elements(value[1:-1]):
            if "$" in word or "`" in word:
                resolved = substitute([QUOTED_VALUE_PREFIX + word], variables)
                elements.extend(strip_quoted_prefix(part) for part in resolved)
            else:
                elements.append(word)
        _store_array(
            name, (_array_list(name, variables) if plus else []) + elements, variables
        )
        return
    known = _known_value(value, variables)
    if plus:
        known = (
            variables[name] + known if known is not None and name in variables else None
        )
    if ARRAY_KEY + name in variables:
        # `a=x` on an array sets its first element and keeps the others.
        items = _array_list(name, variables)
        _store_array(name, [value if known is None else known] + items[1:], variables)
        return
    if known is None:
        variables.pop(name, None)
        return
    variables[name] = known


MAX_ARRAY_INDEX = 64


def _array_elements(inner: str) -> list[str]:
    """The elements of the array assignment whose list is `inner`."""
    try:
        words = [
            strip_quoted_prefix(text)
            for text, is_operator in _shell_tokens(inner)
            if not is_operator
        ]
    except UnparseableCommand:
        return []
    return [re.sub(r"^\[[^\]]*\]=", "", word) for word in words]


def _array_value(match: re.Match[str], variables: dict[str, str]) -> str:
    """The text of the array reference `${a[N]}`, `${a[@]}`, or `${a[*]}`."""
    elements = variables.get(ARRAY_KEY + match.group(1))
    if elements is None:
        return match.group(0)
    items = elements.split("\0") if elements else []
    index = match.group(2)
    if index in ("@", "*"):
        return " ".join(items)
    position = int(index)
    if position < 0:
        position += len(items)
    return items[position] if 0 <= position < len(items) else ""


def _array_slice(match: re.Match[str], variables: dict[str, str]) -> str:
    """The text of the slice `${a[@]:offset:length}` of a tracked array."""
    elements = variables.get(ARRAY_KEY + match.group(1))
    if elements is None:
        return match.group(0)
    items = elements.split("\0") if elements else []
    start = int(match.group(2))
    if start < 0:
        start = max(len(items) + start, 0)
    if match.group(3) is None:
        return " ".join(items[start:])
    length = int(match.group(3))
    return " ".join(
        items[start : start + length] if length >= 0 else items[start:length]
    )


def _indirect_value(match: re.Match[str], variables: dict[str, str]) -> str:
    """The value of the variable that `${!ref}` names, when both are tracked; the
    target may be an array element (`ref='a[0]'`)."""
    target = variables.get(match.group(1))
    if target is None:
        return match.group(0)
    element = ARRAY_REFERENCE.fullmatch("${" + target + "}")
    if element is not None:
        return _array_value(element, variables)
    return variables[target] if target in variables else match.group(0)


def _replace(value: str, kind: str, find: str, word: str) -> str:
    """`${NAME/find/word}` (also `//`, `/#`, `/%`) of `value`; the longest match wins."""
    if not any(char in find for char in "*?["):  # a literal: no need to try every part
        if kind == "/#":
            return word + value[len(find) :] if value.startswith(find) else value
        if kind == "/%":
            return (
                value[: len(value) - len(find)] + word
                if value.endswith(find)
                else value
            )
        return value.replace(find, word, 1 if kind == "/" else -1) if find else value
    if kind == "/#":
        for stop in range(len(value), -1, -1):
            if fnmatch.fnmatchcase(value[:stop], find):
                return word + value[stop:]
        return value
    if kind == "/%":
        for begin in range(len(value) + 1):
            if fnmatch.fnmatchcase(value[begin:], find):
                return value[:begin] + word
        return value
    if not find:
        return value
    pieces: list[str] = []
    begin = 0
    while begin < len(value):
        for stop in range(len(value), begin, -1):
            if fnmatch.fnmatchcase(value[begin:stop], find):
                pieces.append(word)
                begin = stop
                break
        else:
            pieces.append(value[begin])
            begin += 1
            continue
        if kind == "/":
            pieces.append(value[begin:])
            return "".join(pieces)
    return "".join(pieces)


MAX_OPERATION_VALUE = 256


def _operation_value(match: re.Match[str], variables: dict[str, str]) -> str:
    """The value of a `${NAME op}` on a tracked variable (see `PARAM_OPERATION`);
    the text itself when the variable is not tracked."""
    value = variables.get(match.group(1))
    if value is None:
        return match.group(0)
    pattern = match.group("cut_pattern") or match.group("find") or ""
    if (match.group("cut") or match.group("replace")) and any(
        char in pattern for char in "*?["
    ):
        # A glob is matched against every part of the value: bound the work.
        if len(value) > MAX_OPERATION_VALUE:
            raise UnparseableCommand("a pattern operation on a value too long to read")
        _charge(len(value) * len(value) // 16)
    if match.group("cut"):
        prefix = match.group("cut")[0] == "#"
        longest = len(match.group("cut")) == 2
        if not any(char in pattern for char in "*?["):  # a literal
            if prefix:
                return value[len(pattern) :] if value.startswith(pattern) else value
            return (
                value[: len(value) - len(pattern)] if value.endswith(pattern) else value
            )
        sizes = list(range(len(value) + 1))
        # The shortest cut first for `#`/`%`, the longest first for `##`/`%%`.
        for size in reversed(sizes) if longest else sizes:
            part = value[:size] if prefix else value[len(value) - size :]
            if fnmatch.fnmatchcase(part, pattern):
                return value[size:] if prefix else value[: len(value) - size]
        return value
    if match.group("replace"):
        return _replace(
            value,
            match.group("replace"),
            match.group("find"),
            match.group("word") or "",
        )
    if match.group("offset") is not None:
        start = int(match.group("offset"))
        start = max(len(value) + start, 0) if start < 0 else start
        if match.group("length") is None:
            return value[start:]
        length = int(match.group("length"))
        return value[start : start + length] if length >= 0 else value[start:length]
    kind = match.group("case")
    if kind.startswith("^"):
        return value.upper() if kind == "^^" else value[:1].upper() + value[1:]
    return value.lower() if kind == ",," else value[:1].lower() + value[1:]


def _blank_splitter(variables: dict[str, str]) -> re.Pattern[str]:
    """The characters that split an unquoted expansion into words: blanks and
    newlines, and what a tracked `IFS` adds."""
    extra = "".join(
        re.escape(char) for char in variables.get("IFS", "") if char not in " \t\n"
    )
    return re.compile("[ \t\n" + extra + "]+")


def substitute(tokens: list[str], variables: dict[str, str]) -> list[str]:
    """Replace `$NAME`/`${NAME}` references, array references, `${!NAME}`, and the
    operations of `PARAM_OPERATION` with tracked values; `"${a[@]}"` as a whole word
    becomes one word per element. The value of an unquoted reference splits into
    words at blanks (and at a tracked `IFS`), as Bash does."""
    resolved: list[str] = []
    splitter = _blank_splitter(variables)
    for token in tokens:
        whole = ARRAY_REFERENCE.fullmatch(strip_quoted_prefix(token))
        if (
            whole
            and whole.group(2) in ("@", "*")
            and variables.get(ARRAY_KEY + whole.group(1))
        ):
            resolved.extend(variables[ARRAY_KEY + whole.group(1)].split("\0"))
            continue
        # The value of an assignment (`b=(${a[@]})`) is never split into words.
        quoted = token.startswith((QUOTED_VALUE_PREFIX, QUOTED_PATTERN_PREFIX)) or bool(
            ASSIGNMENT_WORD.match(token)
        )

        def mark(text: str, quoted: bool = quoted) -> str:
            return text if quoted else splitter.sub("\0", text)

        token = ARRAY_SLICE.sub(
            lambda match: mark(_array_slice(match, variables)), token
        )
        token = ARRAY_REFERENCE.sub(
            lambda match: mark(_array_value(match, variables)), token
        )
        token = INDIRECT_REFERENCE.sub(
            lambda match: mark(_indirect_value(match, variables)), token
        )
        token = PARAM_OPERATION.sub(
            lambda match: mark(_operation_value(match, variables)), token
        )
        token = PLAIN_REFERENCE.sub(
            lambda match: mark(
                variables.get(match.group(1) or match.group(2), match.group(0))
            ),
            token,
        )
        if "\0" in token:
            resolved.extend(word for word in token.split("\0") if word)
        else:
            resolved.append(token)
    return resolved


def command_name(
    tokens: list[str], variables: dict[str, str]
) -> tuple[str, int, dict[str, str]] | None:
    """Return (command, args-start-index, prefix_assignments).

    Records any leading `NAME=value` tokens (including ones after a
    sudo/env/command wrapper) into the persistent `variables` dict as a side
    effect, exactly as before. `prefix_assignments` is a *separate*, fresh
    dict holding only the NAME=value tokens recorded by this one call - a
    prefix on this command's own invocation (`VAR=v cmd`) or an `env
    VAR=value cmd` wrapper - not any assignment tracked earlier on a
    different, already-processed segment.

    Real bash exports a prefix assignment into only the one command it
    precedes; a persistent bare assignment on its own segment (`VAR=v`, then
    `cmd` later) is not exported to a child process at all. Callers that
    need "what this invocation's own environment would contain" (a heredoc
    consumed by a bare child shell/interpreter) must use
    `prefix_assignments`, not `variables`, or they conflate the two.

    Returns None for a segment consisting entirely of assignments
    (`FOO=bar`): that is valid Bash with no command to classify, not an
    ambiguity.
    """
    prefix_assignments: dict[str, str] = {}
    index = 0
    while index < len(tokens) and tokens[index] in SHELL_KEYWORDS:
        index += 1  # `then cd x`, `{ rm y`: the command follows the keyword
    if index == len(tokens):
        return None
    while (
        index < len(tokens)
        and "=" in tokens[index]
        and not tokens[index].startswith("-")
    ):
        record_assignment(tokens[index], variables)
        record_assignment(tokens[index], prefix_assignments)
        index += 1
    if index == len(tokens):
        return None
    while index < len(tokens) and tokens[index] in {"sudo", "env", "command"}:
        wrapper = tokens[index]
        value_flags = WRAPPER_VALUE_FLAGS[wrapper]
        no_value_flags = WRAPPER_NO_VALUE_FLAGS[wrapper]
        index += 1
        while index < len(tokens) and tokens[index].startswith("-"):
            flag, _, attached_value = tokens[index].partition("=")
            if flag in value_flags:
                if attached_value:
                    index += 1
                    continue
                if index + 1 == len(tokens):
                    raise AmbiguousCommand(f"{wrapper} {flag} has no value")
                index += 2
                continue
            if tokens[index] in no_value_flags:
                index += 1
                continue
            # An unrecognized flag might take a value we do not know about
            # (this is exactly how -u's value was mistaken for the command
            # name before this fix): assuming "no value" is not safe, so
            # this segment is ambiguous rather than silently guessed.
            raise AmbiguousCommand(
                f"{wrapper} has an unrecognized option {tokens[index]!r}"
            )
        if (
            index < len(tokens)
            and "=" in tokens[index]
            and not tokens[index].startswith("-")
        ):
            record_assignment(tokens[index], variables)
            record_assignment(tokens[index], prefix_assignments)
            index += 1
    if index == len(tokens):
        raise AmbiguousCommand("shell wrapper has no command")
    return tokens[index], index + 1, prefix_assignments


def is_redirect(token: str) -> bool:
    """True for a redirection operator; the next token is its target."""
    return (
        token in REDIRECTS
        or token == ">&"
        or (token.endswith(">") and token[:-1].isdigit())
    )


def operands(tokens: list[str], value_options: set[str]) -> list[str]:
    """Return command operands, omitting redirections and option values."""
    result: list[str] = []
    index = 0
    options_done = False
    while index < len(tokens):
        token = tokens[index]
        if is_redirect(token):
            index += 2
            continue
        if token == "--":
            options_done = True
        elif not options_done and token in value_options:
            index += 2
            continue
        elif not options_done and token.startswith("-"):
            pass
        else:
            result.append(token)
        index += 1
    return result


def without_redirects(tokens: list[str]) -> list[str]:
    """Return tokens without redirection operators and their targets.

    `segment_targets` already reports each redirect target as confirmed, so an
    unmodelled command's argument scan must not list it a second time as
    uncertain.
    """
    result: list[str] = []
    index = 0
    while index < len(tokens):
        if is_redirect(tokens[index]):
            index += 2
            continue
        result.append(tokens[index])
        index += 1
    return result


def _skip_sed_pattern(script: str, index: int, delimiter: str) -> int:
    """The index after the part of a sed script that starts at `script[index]`
    and ends at the next unescaped `delimiter` (a regex or a replacement). A
    `[...]` in a regex may hold the delimiter. -1 when the script ends first."""
    length = len(script)
    while index < length:
        char = script[index]
        if char == "\\":
            index += 2
        elif char == delimiter:
            return index + 1
        elif char == "[" and delimiter != "[":
            close = script.find("]", index + 2 + (script[index + 1 : index + 2] == "^"))
            index = length if close == -1 else close + 1
        else:
            index += 1
    return -1


def _skip_sed_address(script: str, index: int) -> int:
    """The index after the address, address range, and `!` that precede a sed
    command: numbers, `first~step`, `$`, `+N`, `~N`, `/re/` and `\\cREc` (with
    the `I` and `M` flags), `addr1,addr2`."""
    length = len(script)
    for second in (False, True):
        while index < length and script[index] in " \t":
            index += 1
        if index >= length:
            return index
        char = script[index]
        if char.isdigit() or (second and char in "+~"):
            index += 1
            while index < length and (script[index].isdigit() or script[index] == "~"):
                index += 1
        elif char == "$":
            index += 1
        elif char == "/" or (char == "\\" and index + 1 < length):
            delimiter = "/" if char == "/" else script[index + 1]
            index = _skip_sed_pattern(
                script, index + (1 if char == "/" else 2), delimiter
            )
            if index == -1:
                raise AmbiguousCommand("sed address is not closed")
            while index < length and script[index] in "IM":
                index += 1
        elif second:
            raise AmbiguousCommand("sed address range has no second address")
        else:
            break
        while index < length and script[index] in " \t":
            index += 1
        if second or script[index : index + 1] != ",":
            break
        index += 1
    while index < length and script[index] in " \t!":
        index += 1
    return index


def _sed_script_effects(script: str) -> tuple[list[str], bool]:
    """The files a sed script writes (`w` and `W` commands, the `w` flag of
    `s///`) and whether it runs a shell command (`e` command, `e` flag). A script
    the reader cannot follow fails closed (AmbiguousCommand)."""
    files: list[str] = []
    executes = False
    index = 0
    length = len(script)

    def rest_of_line(start: int) -> tuple[str, int]:
        end = script.find("\n", start)
        end = length if end == -1 else end
        return script[start:end].strip(), end

    while index < length:
        if script[index] in " \t\n;{}":
            index += 1
            continue
        if script[index] == "#":
            index = rest_of_line(index)[1]
            continue
        index = _skip_sed_address(script, index)
        if index >= length:
            break
        command = script[index]
        index += 1
        if command in "wW":
            name, index = rest_of_line(index)
            files.append(name)
        elif command in "sy":
            delimiter = script[index : index + 1]
            if not delimiter:
                raise AmbiguousCommand("sed %s command has no delimiter" % command)
            index = _skip_sed_pattern(script, index + 1, delimiter)
            if index != -1:
                index = _skip_sed_pattern(script, index, delimiter)
            if index == -1:
                raise AmbiguousCommand("sed %s command is not closed" % command)
            while command == "s" and index < length and script[index] not in " \t\n;}":
                if script[index] == "w":
                    name, index = rest_of_line(index + 1)
                    files.append(name)
                    break
                executes = executes or script[index] == "e"
                index += 1
        elif command == "e":
            executes = True
            index = rest_of_line(index)[1]
        elif command in "rRaic":
            index = rest_of_line(index)[1]
            while script[index - 1 : index] == "\\" and index < length:
                index = rest_of_line(index + 1)[1]
        elif command in ":bBtT":
            while index < length and script[index] not in "\n;":
                index += 1
        elif command in "lLqQ":
            while index < length and script[index].isdigit():
                index += 1
    return files, executes


def sed_effects(args: list[str]) -> tuple[list[str], bool]:
    """The files the inline scripts of a `sed` command line write, and whether
    one runs a shell command. The scripts are the `-e` and `--expression` values,
    or the first operand when there is none (GNU option rules: bundled short
    options, an attached or separate value, `--`). A `-f` script file is not read."""
    scripts: list[str] = []
    operand_words: list[str] = []
    script_file = False
    index = 0
    while index < len(args):
        token = strip_quoted_prefix(args[index])
        index += 1
        if token in ("<", "<<<", "<&"):
            index += 1
        elif token == "--":
            operand_words.extend(strip_quoted_prefix(word) for word in args[index:])
            break
        elif token.startswith("--"):
            name, equals, attached = token.partition("=")
            if len(name) >= 5 and "--expression".startswith(name):
                if not equals and index < len(args):
                    attached = strip_quoted_prefix(args[index])
                    index += 1
                scripts.append(attached)
            elif len(name) >= 3 and "--file".startswith(name):
                script_file = True
                index += int(not equals)
            elif len(name) >= 3 and "--line-length".startswith(name):
                index += int(not equals)
        elif token.startswith("-") and len(token) > 1:
            for position, letter in enumerate(token[1:], start=1):
                if letter in "efl":
                    value = token[position + 1 :]
                    if not value and index < len(args):
                        value = strip_quoted_prefix(args[index])
                        index += 1
                    if letter == "e":
                        scripts.append(value)
                    script_file = script_file or letter == "f"
                    break
                if letter == "i":
                    break
        elif not token.startswith(HEREDOC_PREFIX):
            operand_words.append(token)
    if not scripts and not script_file and operand_words:
        scripts.append(operand_words[0])
    files: list[str] = []
    executes = False
    for script in scripts:
        script_files, script_executes = _sed_script_effects(script)
        files.extend(script_files)
        executes = executes or script_executes
    return files, executes


def find_targets(args: list[str]) -> list[str]:
    """A protected name that a `find` that deletes (`-delete`) or runs a command
    that is not read-only (`-exec rm {} +`) may reach, or nothing. Tests before
    the action narrow it (`-name '*.pyc'` cannot match a protected file, `-type d`
    only reaches folders); a name, path, or regex test is tried against the names
    and paths a protected file can have. Anything the reader cannot narrow, with
    `-o`, `!`, parentheses, or `-prune`, no test at all, or a test that can match,
    reaches a protected file."""
    words = [strip_quoted_prefix(arg) for arg in args]
    action = next(
        (
            index
            for index, word in enumerate(words)
            if word == "-delete"
            or (
                word in FIND_EXEC_ACTIONS
                and index + 1 < len(words)
                and posixpath.basename(words[index + 1]) not in FIND_READ_ONLY_COMMANDS
            )
        ),
        None,
    )
    if action is None:
        return []
    tests = words[:action]
    if any(word in FIND_COMBINERS for word in tests):
        return [FIND_SAMPLE_NAMES[0]]
    narrowed = False
    for index, word in enumerate(tests):
        kind = FIND_PATTERN_TESTS.get(word)
        if kind and index + 1 < len(tests):
            pattern = tests[index + 1]
            fold = word.startswith("-i")
            samples = FIND_SAMPLE_NAMES if kind == "name" else FIND_SAMPLE_PATHS
            for sample in samples:
                if _find_pattern_matches(kind, pattern, sample, fold):
                    # A config name alone is not protected; its path in the repository is.
                    return [FIND_CONFIG_PATHS.get(sample, sample)]
            narrowed = True
        elif word == "-type" and tests[index + 1 : index + 2] == ["d"]:
            narrowed = True
    return [] if narrowed else [FIND_SAMPLE_NAMES[0]]


def _find_pattern_matches(kind: str, pattern: str, sample: str, fold: bool) -> bool:
    """True when `find`'s `kind` test with `pattern` can match `sample`."""
    if fold:
        pattern, sample = pattern.lower(), sample.lower()
    if kind == "regex":
        try:
            return re.fullmatch(pattern, sample) is not None
        except re.error:
            return True
    return fnmatch.fnmatchcase(sample, pattern)


def target_directory(tokens: list[str]) -> str | None:
    for index, token in enumerate(tokens):
        if token in {"-t", "--target-directory"}:
            if index + 1 == len(tokens):
                raise AmbiguousCommand("target-directory option has no target")
            return tokens[index + 1]
        if token.startswith("--target-directory="):
            target = token.partition("=")[2]
            if not target:
                raise AmbiguousCommand("target-directory option has no target")
            return target
    return None


def git_subcommand(args: list[str]) -> str | None:
    """Return git's subcommand, skipping global options that precede it.

    Handles -C/-c/--git-dir/--work-tree in both "--opt value" and
    "--opt=value" forms (e.g. `git -C .claude status`), and safely skips any
    other flag-only global option. Not the full git CLI grammar - only
    enough to find the subcommand for common development usage.
    """
    index = 0
    while index < len(args):
        token = args[index]
        if not token.startswith("-"):
            return token
        if token in GIT_GLOBAL_VALUE_OPTIONS:
            index += 2
            continue
        name, _, value = token.partition("=")
        if value and name in GIT_GLOBAL_VALUE_OPTIONS:
            index += 1
            continue
        index += 1
    return None


def git_working_directory(args: list[str], shell_directory: str) -> str:
    """Resolve leading Git `-C` options using Git's sequential semantics."""
    directory = shell_directory
    work_tree: str | None = None
    index = 0
    while index < len(args):
        token = args[index]
        if token == "-C":
            if index + 1 == len(args):
                raise AmbiguousCommand("git -C has no directory")
            value = args[index + 1]
            directory = (
                value if os.path.isabs(value) else os.path.join(directory, value)
            )
            index += 2
            continue
        if token.startswith("-C") and token != "-C":
            value = token[2:]
            directory = (
                value if os.path.isabs(value) else os.path.join(directory, value)
            )
            index += 1
            continue
        if token == "--work-tree":
            if index + 1 == len(args):
                raise AmbiguousCommand("git --work-tree has no directory")
            value = args[index + 1]
            work_tree = (
                value if os.path.isabs(value) else os.path.join(directory, value)
            )
            index += 2
            continue
        if token.startswith("--work-tree="):
            value = token.partition("=")[2]
            if not value:
                raise AmbiguousCommand("git --work-tree has no directory")
            work_tree = (
                value if os.path.isabs(value) else os.path.join(directory, value)
            )
            index += 1
            continue
        if not token.startswith("-"):
            break
        if token in GIT_GLOBAL_VALUE_OPTIONS:
            index += 2
        else:
            index += 1
    return os.path.normpath(work_tree or directory)


def git_output_target(args: list[str]) -> str | None:
    """Return the value of git's `--output`/`--output=<path>` option, if any.

    A handful of otherwise read-only subcommands (diff, show, log, ...) can
    still write directly to a file via --output; that destination must not
    bypass protected-file protection.
    """
    for index, token in enumerate(args):
        if token == "--output":
            if index + 1 == len(args):
                raise AmbiguousCommand("git --output has no target")
            return args[index + 1]
        if token.startswith("--output="):
            target = token.partition("=")[2]
            if not target:
                raise AmbiguousCommand("git --output has no target")
            return target
    return None


def git_reads_message_from_stdin(args: list[str]) -> bool:
    """True when git's own -F/--file option reads message text from standard
    input (git's documented "-" convention, e.g. `commit -F -`, `tag -F -`,
    `notes add -F -`). Content read this way is stored as a message in the
    git object database, never written to the working tree, so heredoc data
    feeding it is not a filesystem write operand regardless of its literal
    contents. Not "-F -" specific to any one subcommand: the convention is
    git's own, so it applies uniformly wherever git accepts it."""
    for index, token in enumerate(args):
        if token in ("-F", "--file"):
            return index + 1 < len(args) and args[index + 1] == "-"
        if token.startswith("--file="):
            return token.partition("=")[2] == "-"
    return False


def _heredoc_is_bare_shell(
    args: list[str], heredocs: dict[str, tuple[str, bool]]
) -> bool:
    """True when a shell interpreter has no inline -c script and no
    script-file argument, so its heredoc body is the script it actually
    executes rather than stdin data for a script this classifier cannot
    see."""
    for token in args:
        if token in heredocs:
            continue
        if token == "-c":
            return False
        if not token.startswith("-"):
            return False
    return True


def heredoc_targets(
    command: str,
    args: list[str],
    body: str,
    quoted: bool,
    heredocs: dict[str, tuple[str, bool]],
    repo_root: str,
    outer_variables: dict[str, str],
    prefix_assignments: dict[str, str],
    working_directories: list[str],
    confirmed: list[str],
    uncertain: list[str],
    message: bool = False,
) -> None:
    """Classify one heredoc body by what its consuming command does with its
    own standard input.

    An *unquoted* delimiter's body is expanded by the *parent* shell itself,
    using the parent's own variable scope, before any consuming command
    runs - so an embedded $( )/`...` always executes, and a bare shell
    interpreter's whole body is real code the parent already resolved
    variables in. `outer_variables` models that parent scope: it is a
    snapshot of the persistently tracked variables taken *before* this
    command's own leading assignments were recorded, because a prefix
    assignment (`VAR=v cmd`) is exported only into the child process about
    to run `cmd` - it is never visible to the parent's own word expansion
    (verified empirically: `TARGET=x bash <<EOF\\ntouch $TARGET\\nEOF`
    writes nothing; `$TARGET` expands empty and `touch` errors). A
    persistent bare assignment from an earlier, separate segment *is*
    already in `outer_variables`, because it was recorded into the shared
    dict before this segment ever ran.

    A *quoted* delimiter's body passes through to the child process
    literally, unexpanded by the parent, so only a bare shell interpreter's
    own recursive classification needs variables at all, and only the ones
    that command's own environment would actually contain:
    `prefix_assignments` (this invocation's own `VAR=v cmd` or `env
    VAR=value cmd`), never `outer_variables` - a child process does not
    inherit the parent's non-exported shell variables (verified
    empirically: `TARGET=x` on its own segment, then `bash <<'EOF'\\ntouch
    $TARGET\\nEOF`, writes nothing; `touch` receives an empty operand and
    errors, matching a real, unexported bash variable).

    git's own -F - stdin convention is a genuine exception to all of this:
    its content is stored as an object-database message, never a
    working-tree file, so nothing further is scanned. Everything else - a
    READ_ONLY command (sed's own script language supports `w file` and `e`
    without needing -i), an interpreter heredoc, a shell fed an explicit
    script file, or a wholly unmodeled command - gets the same conservative
    literal/opaque-write fallback an unmodeled command's own arguments
    already get, rather than being skipped outright.
    """
    if not quoted:
        for inner in heredoc_command_substitutions(body):
            classify_command(
                inner,
                repo_root,
                dict(outer_variables),
                list(working_directories),
                confirmed,
                uncertain,
                heredocs,
            )
    if command == "git" and git_reads_message_from_stdin(args):
        return
    if message and command == "cat":
        # `git commit -m "$(cat <<'EOF' ... EOF)"`: the text becomes a commit
        # message, stored as an object, never written to a working-tree file.
        return
    if command in SHELL_INTERPRETERS and _heredoc_is_bare_shell(args, heredocs):
        # A bare `bash <<EOF ... EOF` starts a new interpreter process: it
        # only inherits the working directory (a process attribute), plus -
        # for a quoted delimiter only - this command's own prefix-exported
        # environment.
        heredoc_variables = (
            dict(prefix_assignments) if quoted else dict(outer_variables)
        )
        classify_command(
            body,
            repo_root,
            heredoc_variables,
            list(working_directories),
            confirmed,
            uncertain,
            heredocs,
        )
        return
    uncertain.extend(protected_path_literals(body))
    uncertain.extend(opaque_write_paths(body))


def classify_substitutions(
    token: str,
    process_subs: dict[str, str],
    repo_root: str,
    variables: dict[str, str],
    working_directories: list[str],
    confirmed: list[str],
    uncertain: list[str],
    heredocs: dict[str, tuple[str, bool]],
    message: bool = False,
) -> None:
    """Classify the inner command of every substitution placeholder in `token`.
    A placeholder may sit anywhere in a word (`$(pwd)/x`). `message` marks the
    value of a `git commit -m` option (see `_message_indices`)."""
    for placeholder in SUBSTITUTION_PLACEHOLDER.findall(token):
        inner = process_subs.get(placeholder)
        if inner is not None:
            classify_command(
                inner,
                repo_root,
                dict(variables),
                list(working_directories),
                confirmed,
                uncertain,
                heredocs,
                message,
            )


def _message_indices(
    tokens: list[str], command_info: tuple[str, int, dict[str, str]] | None
) -> set[int]:
    """The indices of the tokens that hold the message of `git commit`, `git tag`,
    or `git merge` (`-m TEXT`, `-mTEXT`, `-am TEXT`, `--message TEXT`,
    `--message=TEXT`). A heredoc fed to `cat` inside such a value is the message
    text, not a file the command writes."""
    if command_info is None or command_info[0] != "git":
        return set()
    start = command_info[1]
    if git_subcommand(tokens[start:]) not in {"commit", "tag", "merge"}:
        return set()
    indices: set[int] = set()
    for index in range(start, len(tokens)):
        token = tokens[index]
        if token in ("--message", "-m") or re.fullmatch(r"-[A-Za-z]*m", token):
            indices.add(index + 1)
        elif token.startswith("--message=") or (
            token.startswith("-m") and not token.startswith("--")
        ):
            indices.add(index)
    return indices


MAX_BRACE_ROUNDS = 8
# The folders a `cd` may leave the shell in are all tried for each path; a command
# that changes folder this many times is refused rather than guessed.
MAX_WORKING_DIRECTORIES = 64


def _brace_words(word: str) -> list[str]:
    """The words Bash makes of `word` by brace expansion (`a{b,c}d` is `abd acd`),
    or `[word]` when it has no comma list or is quoted."""
    if word.startswith((QUOTED_VALUE_PREFIX, QUOTED_PATTERN_PREFIX)):
        return [word]
    brace = _brace_list(word)
    if brace is None or len(brace[2]) < 2:
        return [word]
    start, end, options = brace
    words: list[str] = []
    for option in options:
        words.extend(_brace_words(word[:start] + option + word[end:]))
        _charge(len(word))
        if len(words) > MAX_BRACE_WORDS:
            raise UnparseableCommand("a brace list in a command word is too long")
    return words


MAX_BRACE_WORDS = 256


def segment_targets(
    tokens: list[str],
    variables: dict[str, str],
    confirmed: list[str],
    uncertain: list[str],
    repo_root: str,
    working_directories: list[str],
    heredocs: dict[str, tuple[str, bool]],
    process_subs: dict[str, str],
    message: bool = False,
) -> None:
    """Classify one segment's mutation targets into `confirmed` or `uncertain`.

    `confirmed` holds targets a known mutation mechanism (redirection, rm,
    cp/mv, etc.) definitely operates on. `uncertain` holds protected-looking
    literals seen only because the command itself is not provably safe; it is
    a softer, still-denied signal, not a confirmed mutation.
    """
    # A snapshot of the persistent scope taken *before* this segment's own
    # leading assignments are recorded below - the "parent shell" scope a
    # heredoc's own unquoted-delimiter expansion or bare-shell-consumer
    # recursion needs, which must not include this command's own prefix
    # assignment (see heredoc_targets).
    outer_variables = dict(variables)

    # command_name() records this segment's leading NAME=value assignments as
    # a side effect, so it must run on the raw tokens before substitute():
    # otherwise a same-segment `TARGET=.env rm "$TARGET"` would substitute
    # "$TARGET" using not-yet-recorded variables and leave it unresolved.
    command_info = command_name(tokens, variables)
    expanded = substitute(tokens, variables)
    if len(expanded) != len(tokens):
        # A value split into several words (`x="tee a"; $x`): read the command again.
        command_info = command_name(expanded, variables)
    for _ in range(MAX_BRACE_ROUNDS):
        if command_info is None:
            break
        words = _brace_words(expanded[command_info[1] - 1])
        if len(words) < 2:
            break
        # A command word that is a brace list (`{tee,x}`) is several words.
        expanded = expanded[: command_info[1] - 1] + words + expanded[command_info[1] :]
        command_info = command_name(expanded, variables)
    tokens = expanded
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if is_redirect(token):
            index += 1
            if index == len(tokens) or tokens[index] in REDIRECTS:
                raise AmbiguousCommand("redirection has no target")
            # `>&2` and `>&-` duplicate or close a descriptor; `>& file` writes it.
            if not (token == ">&" and FD_TARGET.fullmatch(tokens[index])):
                target = tokens[index]
                if token == ">&":
                    # Bash expands a glob in the word of `>& word` even when it is quoted.
                    target = strip_quoted_prefix(target)
                confirmed.extend(
                    resolve_from_directories([target], working_directories, repo_root)
                )
        index += 1

    # A command or process substitution always runs, regardless of which
    # command (or none) receives its output or /dev/fd path, so it is
    # recursively classified unconditionally - never merely because the outer
    # command looks unsafe.
    message_values = _message_indices(tokens, command_info)
    for token_index, token in enumerate(tokens):
        classify_substitutions(
            token,
            process_subs,
            repo_root,
            variables,
            working_directories,
            confirmed,
            uncertain,
            heredocs,
            token_index in message_values,
        )

    if command_info is None:
        return
    command, start, prefix_assignments = command_info
    args = tokens[start:]
    # Redirect targets are confirmed above, so the argument scans below skip
    # them. A leading redirect (`> file echo x`) makes the operator the command
    # name, so its target is still the first of `args`.
    plain_args = without_redirects(
        tokens[start - 1 :] if is_redirect(command) else args
    )

    for token in args:
        entry = heredocs.get(token)
        if entry is not None:
            body, quoted = entry
            heredoc_targets(
                command,
                args,
                body,
                quoted,
                heredocs,
                repo_root,
                outer_variables,
                prefix_assignments,
                working_directories,
                confirmed,
                uncertain,
                message,
            )

    if FUNCTION_KEY + command in variables:
        command = SHADOWED  # a function or alias of this name: not the command it names
    if command == "cd":
        candidates = operands(args, set())
        if len(candidates) != 1:
            raise AmbiguousCommand("cd must have exactly one directory")
        directory = candidates[0]
        candidate = os.path.normpath(
            directory
            if os.path.isabs(directory)
            else os.path.join(working_directories[-1], directory)
        )
        if candidate not in working_directories:
            if len(working_directories) >= MAX_WORKING_DIRECTORIES:
                raise UnparseableCommand("too many different folders to follow")
            working_directories.append(candidate)
    elif command in SIMPLE_MUTATORS:
        confirmed.extend(
            resolve_from_directories(
                operands(args, OPTION_VALUES.get(command, set())),
                working_directories,
                repo_root,
            )
        )
    elif command in {"cp", "install"}:
        target_dir = target_directory(args)
        candidates = operands(
            args, OPTION_VALUES[command] | {"-t", "--target-directory"}
        )
        if target_dir:
            confirmed.extend(
                resolve_from_directories(candidates, working_directories, repo_root)
            )
            confirmed.extend(
                resolve_from_directories([target_dir], working_directories, repo_root)
            )
        elif candidates:
            confirmed.extend(
                resolve_from_directories(candidates, working_directories, repo_root)
            )
        else:
            raise AmbiguousCommand(f"{command} has no destination")
    elif command == "mv":
        target_dir = target_directory(args)
        candidates = operands(
            args, OPTION_VALUES[command] | {"-t", "--target-directory"}
        )
        if target_dir:
            confirmed.extend(
                resolve_from_directories(candidates, working_directories, repo_root)
            )
            confirmed.extend(
                resolve_from_directories([target_dir], working_directories, repo_root)
            )
        elif len(candidates) >= 2:
            confirmed.extend(
                resolve_from_directories(
                    candidates[:-1], working_directories, repo_root
                )
            )
            confirmed.extend(
                resolve_from_directories(
                    [candidates[-1]], working_directories, repo_root
                )
            )
        else:
            raise AmbiguousCommand("mv has no source and destination")
    elif command in {"chmod", "chown"}:
        candidates = operands(args, OPTION_VALUES[command])
        if len(candidates) < 2:
            raise AmbiguousCommand(f"{command} has no path operand")
        confirmed.extend(
            resolve_from_directories(candidates[1:], working_directories, repo_root)
        )
    elif command in {"sed", "perl"}:
        if command == "sed":
            # An inline script can write a file (`w`, `W`, the `w` flag of `s///`)
            # or run a command (`e`) without `-i`.
            sed_files, sed_executes = sed_effects(plain_args)
            confirmed.extend(
                resolve_from_directories(sed_files, working_directories, repo_root)
            )
            if sed_executes:
                raise AmbiguousCommand("a sed script runs a shell command")
        candidates = operands(args, OPTION_VALUES[command])
        inplace = any(
            arg == "-i"
            or (arg.startswith("-") and "i" in arg[1:])
            or arg == "--in-place"
            or arg.startswith("--in-place=")
            for arg in args
        )
        if inplace:
            required = 1 if command == "perl" else 2
            if len(candidates) < required:
                raise AmbiguousCommand(f"{command} -i has no file target")
            confirmed.extend(
                resolve_from_directories(
                    candidates if command == "perl" else candidates[1:],
                    working_directories,
                    repo_root,
                )
            )
    elif command == "dd":
        confirmed.extend(
            resolve_from_directories(
                [
                    arg.partition("=")[2]
                    for arg in args
                    if arg.startswith("of=") and arg.partition("=")[2]
                ],
                working_directories,
                repo_root,
            )
        )
    elif command == "git":
        subcommand = git_subcommand(args)
        git_roots = [
            git_working_directory(args, directory) for directory in working_directories
        ]
        output_target = git_output_target(args)
        if output_target is not None:
            confirmed.extend(
                resolve_from_directories([output_target], git_roots, repo_root)
            )
        if subcommand == "mv":
            subcommand_index = args.index(subcommand)
            candidates = operands(args[subcommand_index + 1 :], OPTION_VALUES["mv"])
            if len(candidates) < 2:
                raise AmbiguousCommand("git mv has no source and destination")
            confirmed.extend(resolve_from_directories(candidates, git_roots, repo_root))
        elif subcommand not in GIT_READ_ONLY_SUBCOMMANDS and subcommand not in {
            "commit",
            "branch",
            "fetch",
            "merge",
            "pull",
            "push",
            "rebase",
            "tag",
        }:
            # For unmodelled mutating Git commands, inspect path-shaped
            # arguments only. Do not scan commit messages or other prose.
            uncertain.extend(
                token for token in plain_args if protected(token, repo_root)
            )
            # Git reads its paths from the `-C` directory (or the `cd`
            # directory), not the repository root, so resolve them there too,
            # as `git mv` does. A path found only that way is new coverage and
            # a confirmed target (ask on Claude Code and Copilot); a path
            # visible from the repository root is uncertain above, and any
            # uncertain hit denies in `emit()`.
            offset_roots = [
                root for root in git_roots if root != os.path.normpath(repo_root)
            ]
            confirmed.extend(
                resolve_from_directories(plain_args, offset_roots, repo_root)
            )
    elif command not in READ_ONLY:
        # Unknown commands are not interpreted as filesystem mutations merely
        # because their source or prose contains a sensitive-looking word.
        # Explicit paths remain covered by native edits and known mutators. A
        # word that is one quoted glob is a pattern for the command to match
        # (`find . -name '*.pem'`), not a file it writes, so it is not scanned,
        # unless the command runs its arguments (see `RUNNERS`).
        runs_arguments = (
            posixpath.basename(command) in RUNNERS
            or RUNNER_PATTERN.fullmatch(posixpath.basename(command)) is not None
        )
        scanned = [
            token
            for token in plain_args
            if runs_arguments or not token.startswith(QUOTED_PATTERN_PREFIX)
        ]
        if command == "find":
            uncertain.extend(find_targets(plain_args))
        uncertain.extend(token for token in scanned if protected(token, repo_root))
        uncertain.extend(protected_path_literals(" ".join(scanned)))
        uncertain.extend(opaque_write_paths(" ".join(scanned)))
        # A command spelled as a path runs that file.
        if "/" in command:
            uncertain.append(command)
        # The command reads its paths from the `cd` folder, not the repository
        # root, so resolve them there too, as for an unmodelled Git command. A
        # path found only that way is new coverage: a protected config gets the
        # protected-config decision (confirmed), but a file an interpreter or a
        # runner executes cannot be judged and denies (uncertain), like the same
        # path spelled from the root.
        offset_roots = [
            root for root in working_directories if root != os.path.normpath(repo_root)
        ]
        if offset_roots:
            # `--out=NAME` names a file too: its value is read from the folder.
            names = [
                token.partition("=")[2] if token.startswith("--") else token
                for token in scanned + ([command] if "/" in command else [])
                if (
                    not token.startswith("-")
                    or ("=" in token and token.startswith("--"))
                )
                and not EXTENDED_GLOB.search(token)
            ]
            offset_hits = resolve_from_directories(
                [name for name in names if name], offset_roots, repo_root
            )
            runs_a_file = runs_arguments or "/" in command
            (uncertain if runs_a_file else confirmed).extend(offset_hits)


def _defined_names(text: str) -> set[str]:
    """The names this command line defines as a function (`f() { ...; }`,
    `function f`) or as an alias (`alias f=...`). A command of that name runs the
    definition, whatever its own name suggests (`cat() { tee "$@"; }; cat x`)."""
    names = {a or b for a, b in FUNCTION_NAME.findall(text)}
    for definition in ALIAS_COMMAND.findall(text):
        names.update(ALIAS_NAME.findall(definition))
    return names


def classify_command(
    command: str,
    repo_root: str,
    variables: dict[str, str],
    working_directories: list[str],
    confirmed: list[str],
    uncertain: list[str],
    heredocs: dict[str, tuple[str, bool]],
    message: bool = False,
) -> None:
    """Classify one shell command line, appending its mutation targets into
    `confirmed`/`uncertain`. The sole recursion point for process
    substitutions and bare shell heredocs, so nesting composes: each level
    extracts its own heredocs and substitutions before tokenizing.

    `heredocs` is one mapping shared (by reference, never copied) across the
    whole recursive call tree for a single top-level command, with new
    placeholders numbered above whatever it already holds. A heredoc found
    while scanning an outer level can end up embedded, as an inert
    placeholder, inside a substitution or a bare shell heredoc body
    that only a *recursive* call ever tokenizes; without a shared mapping
    that recursive call could never resolve it back to its real body, and
    the mutation inside would go unclassified.

    A segment the classifier cannot fully model (AmbiguousCommand) does not
    abort the scan: it falls back to a conservative literal scan of that
    segment, so an ambiguity elsewhere in the command cannot hide a real
    mutation, while an ambiguity with no protected-resource evidence at all
    resolves to "nothing found" instead of an internal-error status. A
    genuinely malformed construct (UnparseableCommand) is deliberately not
    caught here: it propagates to the top-level fail-closed exit even when
    raised deep inside a recursive call.
    """
    _charge(len(command))
    command, found_heredocs = extract_heredocs(command, start_count=len(heredocs))
    heredocs.update(found_heredocs)
    command, process_subs = extract_substitutions(command)
    for name in _defined_names(command):
        variables[FUNCTION_KEY + name] = ""
    for segment in split_segments(command):
        try:
            segment_targets(
                segment,
                variables,
                confirmed,
                uncertain,
                repo_root,
                working_directories,
                heredocs,
                process_subs,
                message,
            )
        except AmbiguousCommand:
            resolved = substitute(segment, variables)
            uncertain.extend(token for token in resolved if protected(token, repo_root))
            uncertain.extend(protected_path_literals(" ".join(resolved)))
            uncertain.extend(opaque_write_paths(" ".join(resolved)))
            # An ambiguous segment (e.g. an unrecognized wrapper flag) is
            # raised before segment_targets ever reaches its own heredoc/
            # process-substitution dispatch, so a placeholder here would
            # otherwise be invisible to this fallback scan - the literal
            # text above is only the *outer* tokens, never a heredoc body
            # or a process substitution's inner command. A process
            # substitution still executes regardless of the ambiguity, so
            # it is classified the same as the unconditional case; a
            # heredoc's real consumer is unknown here, so its body gets the
            # same conservative floor an unmodeled command's own arguments
            # already get.
            for token in resolved:
                classify_substitutions(
                    token,
                    process_subs,
                    repo_root,
                    variables,
                    working_directories,
                    confirmed,
                    uncertain,
                    heredocs,
                )
                entry = heredocs.get(token)
                if entry is not None:
                    body, _quoted = entry
                    uncertain.extend(protected_path_literals(body))
                    uncertain.extend(opaque_write_paths(body))


def shell_targets(command: str, repo_root: str) -> tuple[list[str], list[str]]:
    """Return (confirmed_targets, uncertain_targets) for a whole command line."""
    global _work_left
    confirmed: list[str] = []
    uncertain: list[str] = []
    if DOTGLOB.search(command):
        raise UnparseableCommand(
            "a glob can match hidden files after shopt -s dotglob, GLOBIGNORE, "
            "or setopt dotglob, which the guard cannot list"
        )
    _work_left = [WORK_PER_CHARACTER * len(command) + MINIMUM_WORK]
    try:
        classify_command(command, repo_root, {}, [repo_root], confirmed, uncertain, {})
    except RecursionError as error:
        raise UnparseableCommand("shell command is nested too deeply") from error
    finally:
        _work_left = None
    return confirmed, uncertain


def native_targets(
    value: object,
    paths: list[str],
    key: str | None = None,
    read_only: bool = False,
) -> None:
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            native_targets(child_value, paths, str(child_key).lower(), read_only)
        return
    if isinstance(value, list):
        for child in value:
            native_targets(child, paths, key, read_only)
        return
    if not isinstance(value, str):
        return
    if not read_only:
        add_patch_paths(value, paths)
    if key in PATH_KEYS:
        paths.append(value)


def emit(
    target_id: str,
    repo_root: str,
    paths: list[str],
    uncertain: list[str],
    read_only: bool = False,
) -> None:
    hits = [result for path in paths if (result := protected(path, repo_root))]
    hooks = [] if read_only else sorted({path for path, is_hook in hits if is_hook})
    sensitive = sorted({path for path, is_hook in hits if not is_hook})
    uncertain_hits = sorted(
        {result[0] for path in uncertain if (result := protected(path, repo_root))}
    )
    # A secret-file hit or any uncertain hit denies on every client, so a
    # confirmed hook hit elsewhere in the command must not turn that deny into
    # ask.
    if hooks and not sensitive and not uncertain_hits:
        decision = (
            "deny" if target_id in {"openai-codex", "google-antigravity"} else "ask"
        )
        reason = (
            "Editing agent, hook, or server configuration is blocked because "
            "PreToolUse cannot request approval: "
            if decision == "deny"
            else "Editing agent, hook, or server configuration requires approval: "
        ) + ", ".join(hooks)
    elif sensitive:
        decision, reason = (
            "deny",
            "Protected file blocked by policy: " + ", ".join(sensitive),
        )
    elif uncertain_hits:
        decision, reason = (
            "deny",
            "Command references protected file(s) "
            + ", ".join(uncertain_hits)
            + ", but the hook could not determine whether the command may"
            " modify them.",
        )
    else:
        return
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": decision,
                    "permissionDecisionReason": reason,
                }
            },
            separators=(",", ":"),
        )
    )


def main() -> int:
    target_id, repo_root = sys.argv[1:3]
    payload = json.load(sys.stdin)
    tool_name = str(payload.get("tool_name") or payload.get("toolName") or "").lower()
    tool_input = payload.get("tool_input", payload.get("toolArgs", {}))
    if isinstance(tool_input, str):
        tool_input = json.loads(tool_input)
    if not isinstance(tool_input, dict):
        raise AmbiguousCommand("tool input is not an object")
    read_only = tool_name in READ_ONLY_TOOLS
    paths: list[str] = []
    uncertain: list[str] = []
    if tool_name in TERMINAL_TOOLS or tool_name.endswith("bash") or not tool_name:
        command = tool_input.get("command")
        if not isinstance(command, str):
            raise AmbiguousCommand("Bash payload has no command")
        confirmed, uncertain = shell_targets(command, repo_root)
        paths.extend(confirmed)
    else:
        native_targets(tool_input, paths, read_only=read_only)
    emit(target_id, repo_root, paths, uncertain, read_only)
    return 0


if __name__ == "__main__":
    # A backstop for any input that is slow to classify: the default action of
    # SIGALRM ends the process, and the hook script treats a failed exit as a
    # denial, so a timeout of the hook (which lets a command through) never
    # decides. A signal handler cannot do this: on Python 3.9 a regex match
    # cannot be interrupted. Real commands classify in well under a second. A
    # parent may have started this process with SIGALRM ignored, and an ignored
    # signal stays ignored across `exec`, so the default action is put back.
    if hasattr(signal, "SIGALRM"):
        signal.signal(signal.SIGALRM, signal.SIG_DFL)
        signal.alarm(CLASSIFIER_SECONDS)
    try:
        raise SystemExit(main())
    except (AmbiguousCommand, ValueError, json.JSONDecodeError) as error:
        print("protect-files classifier error: %s" % error, file=sys.stderr)
        raise SystemExit(2)
