#!/usr/bin/env python3
"""Classify protected-file mutations from one PreToolUse payload."""

from __future__ import annotations

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
OPERATORS = {";", "&&", "||", "|", "&", "(", ")"}
# Characters that end a shell word: blanks (space, tab, newline; a carriage
# return is an ordinary character) and the operator characters.
PUNCTUATION = ";&|<>()"
WORD_BREAKS = " \t\n" + PUNCTUATION
# Bash's operator tokens, longest first, so a run of operator characters is read
# by longest match (`&&(` is `&&` then `(`). Only `OPERATORS` split a command
# into segments. The others are words here: the redirects as before, and the
# grouped forms `|&`, `&>>`, `>&`, `<>`, `<&`, `;&`, `;;&`, `;;` keep their old
# reading until Phase I gives them their meaning.
SHELL_OPERATORS = sorted(
    ";;& &>> <<< <<- ;; ;& && || |& << <& <> >> >& >| &> ; & | ( ) < >".split(),
    key=len,
    reverse=True,
)
# Operators that need a command after them, even past a newline.
BINARY_OPERATORS = {"&&", "||", "|"}
REDIRECTS = {">", ">>", ">|", "&>", "1>", "1>>", "2>", "2>>"}
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
ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
VARIABLE_REFERENCE = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?")
# The start of an array assignment: `NAME=` or `NAME+=` right before a `(`.
ARRAY_ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\+?=")
# A glob character: in a quoted word, the word may be a pattern (see
# `QUOTED_PATTERN_PREFIX`). A brace list is not one: `find -name '{a,b}'` never
# expands it.
QUOTED_GLOB = re.compile(r"[?*[]")
# Quoted text that must not be expanded again: a glob, a brace list, or a
# variable reference (`$NAME`, `${NAME}`). A word holding such a quoted part is
# returned by the scanner with `QUOTED_VALUE_PREFIX`.
QUOTED_MAGIC = re.compile(QUOTED_GLOB.pattern + r"|(?<!\$)\{[^{}]+\}|\$\{?[A-Za-z_]")
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
HEREDOC_WORD = re.compile(
    r"[ \t]*(?:'([A-Za-z0-9_]+)'|\"([A-Za-z0-9_]+)\"|([A-Za-z0-9_]+))"
)
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


def without_expansions(text: str) -> str:
    """`text` without its substitution placeholders and unresolved `$NAME` and
    `${NAME}` references: each may expand to nothing, so a protected name may
    be only what is left."""
    return VARIABLE_REFERENCE.sub("", SUBSTITUTION_PLACEHOLDER.sub("", text))


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
    bare = without_expansions(path)
    if bare != path:
        hit = protected(bare, repo_root)
        if hit:
            return hit
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
        brace = None if quoted_value else re.search(r"\{([^{}]+)\}", path)
        if brace:
            for option in brace.group(1).split(","):
                resolved.extend(
                    resolve_operands(
                        [path[: brace.start()] + option + path[brace.end() :]],
                        base_dir,
                        display_root,
                    )
                )
            continue
        if "@(" in path or "!(" in path or "+(" in path:
            resolved.append(path)
            resolved.extend(protected_path_literals(path))
            continue
        absolute = path if os.path.isabs(path) else os.path.join(base_dir, path)
        matches = (
            sorted(glob.glob(absolute))
            if glob.has_magic(path) and not quoted_value
            else [absolute]
        )
        if not matches:
            resolved.append(path)
            continue
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
        for text in dict.fromkeys((word, no_substitution, without_expansions(word))):
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
        elif char == "$" and text[cursor + 1 : cursor + 2] == "(":
            # ponytail: a here-document body inside this substitution is not
            # parsed, so an apostrophe or `)` in it makes the nesting fail and
            # the scan falls back to the next `"` (what the old lexer did).
            # Phase I classifies substitutions and can parse the body.
            end = _matching_paren(text, cursor + 1)
            cursor = end if end != -1 else cursor + 1
        elif char == "`":
            end = cursor + 1
            while True:
                found = _BACKTICK_SPECIAL.search(text, end)
                if found is None or found.group() == "`":
                    break
                end = found.start() + 2
            if found is None:
                _charge(len(text) - cursor)
                cursor += 1
            else:
                cursor = found.end()
        else:
            cursor += 1


def _skip_literal(text: str, index: int) -> int:
    """Return the index just past the quoted, escaped, or comment text that
    starts at `text[index]`, or `index` itself when none starts there. -1 means
    the text ends first: an unterminated quote or a trailing backslash.

    Bash's rules, outside a here-document body: a backslash makes the next
    character literal; `'...'` is literal; in `$'...'` a backslash escapes the
    next character, `'` included; `"..."` and `$"..."` are double-quoted
    strings (see `_skip_double_quoted`); a `#` that starts a word begins a
    comment that runs up to the next newline.
    """
    char = text[index]
    if char == "\\":
        return index + 2 if index + 1 < len(text) else -1
    if char == "'":
        end = text.find("'", index + 1)
        _charge((len(text) if end == -1 else end) - index)
        return -1 if end == -1 else end + 1
    if char == "#":
        if not _starts_word(text, index):
            return index
        end = text.find("\n", index)
        return len(text) if end == -1 else end
    following = text[index + 1 : index + 2]
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


def _unquote(span: str) -> str:
    """The text a quoted or escaped span (see `_skip_literal`) stands for."""
    if span[0] == "\\":
        return span[1:]
    if span[0] == "'":
        return span[1:-1]
    if span.startswith("$'"):
        return re.sub(r"\\(['\"\\])", r"\1", span[2:-1])
    body = span[2:-1] if span[0] == "$" else span[1:-1]
    return re.sub(
        r"\\([$`\"\\]|\n)",
        lambda match: "" if match.group(1) == "\n" else match.group(1),
        body,
    )


def _matching_paren(text: str, open_index: int) -> int:
    """Return the index just past the ')' matching text[open_index] == '(',
    honoring nested parens and quotes. Returns -1 when never closed."""
    depth = 0
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
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index + 1
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
    Quoted text, escapes, and comments are not searched. The text may be the part
    up to that first `)`, which still holds the `case` word.
    """
    text = inner.replace("\\\n", "")
    _charge(len(text))
    parts: list[str] = []
    index = 0
    length = len(text)
    while index < length:
        end = _skip_literal(text, index)
        if end == index:
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
    """Replace every unquoted `$( )`, `$(( ))`, `<( )`, and `>( )` with an inert
    placeholder, returning the new text and a placeholder -> inner-command
    mapping for recursive classification.

    A `$( )` or `$(( ))` stays inside its word, as in Bash: `$(pwd)/x` becomes
    `<placeholder>/x`, and a word after the closing `)` is an operand, not a
    new command. A `<( )` or `>( )` is a word of its own (`cat<(...)` is valid:
    `<` ends the word before it), so it gets a space before it; text glued after
    its `)` stays in the word, as in Bash. The scanner reads the placeholder as
    ordinary word text, and `segment_targets` finds each placeholder inside a
    word to classify its inner command.

    `$(( ))` is arithmetic: there is no command to classify, only the `$( )`
    that its expression may hold. Text inside quotes, behind a backslash, or in
    a comment is left untouched (quoting suppresses substitution in real shells
    too). An unbalanced construct is genuinely malformed shell syntax, not
    merely unmodeled, so it fails closed rather than being silently dropped.
    """
    pieces: list[str] = []
    inner_by_placeholder: dict[str, str] = {}
    index = 0
    length = len(command)
    count = 0
    while index < length:
        end = _skip_literal(command, index)
        if end != index:
            # Quoted or escaped text or a comment; text that never ends is left
            # for `split_segments`, which fails closed on it.
            end = length if end == -1 else end
            pieces.append(command[index:end])
            index = end
            continue
        opener = command[index : index + 2]
        if opener not in ("<(", ">(", "$("):
            pieces.append(command[index])
            index += 1
            continue
        end = _matching_paren(command, index + 1)
        if end == -1:
            raise UnparseableCommand("unbalanced substitution")
        inner = command[index + 2 : end - 1]
        _refuse_case_statement(inner)
        if (
            opener == "$("
            and inner.startswith("(")
            and _matching_paren(command, index + 2) == end - 1
        ):
            inner = "\n".join(extract_substitutions(inner[1:-1])[1].values())
        placeholder = "%s%d__" % (PROCESS_SUB_PREFIX, count)
        count += 1
        inner_by_placeholder[placeholder] = inner
        pieces.append(placeholder if opener == "$(" else " " + placeholder)
        index = end
    return "".join(pieces), inner_by_placeholder


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
        strip_tabs = result[operator_index + 2 : operator_index + 3] == "-"
        word_start = operator_index + (3 if strip_tabs else 2)
        word_match = HEREDOC_WORD.match(result, word_start)
        if not word_match:
            raise UnparseableCommand("heredoc redirect has no delimiter word")
        delimiter = next(group for group in word_match.groups() if group)
        quoted = word_match.group(1) is not None or word_match.group(2) is not None
        rest_of_line_start = word_match.end()
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


def _read_word(command: str, index: int) -> tuple[str, bool, int]:
    """Read the word that starts at `command[index]`, which is not whitespace,
    a newline, or an operator character. Returns (text, quoted, end): the word
    with its quotes and escapes removed, whether it used any, and the index
    after it. A backslash-newline joins the lines and is not part of a word.

    A quoted part holding a glob, a brace list, or a variable reference
    (`QUOTED_MAGIC`) must not be expanded again, so the word gets
    `QUOTED_VALUE_PREFIX`, or `QUOTED_PATTERN_PREFIX` when the word is only one
    quoted glob (a brace list does not count); a part glued to a name or to `=`
    (`NAME='*'`, `--opt="$X"`) leaves the word as it is.

    A `(` right after `NAME=` or `NAME+=` opens an array assignment: the list
    and what is glued after its `)` stay in the word (`a=(x)b`). Bash keeps a
    `#` glued there in the word too (`a=(x)#c` holds no comment), but the other
    scans in this file take a `#` after any `)` for a comment, so that form
    fails closed instead of being read two ways.
    """
    parts: list[str] = []
    quoted = False
    magic = False
    glob = False  # a magic part holds a glob character
    before = ""  # the last character of the word so far
    length = len(command)
    while index < length:
        if command[index] in WORD_BREAKS:
            if (
                command[index] != "("
                or before != "="
                or not ARRAY_ASSIGNMENT.fullmatch("".join(parts))
            ):
                break
            end = _matching_paren(command, index)
            if end == -1:
                raise UnparseableCommand("unbalanced array assignment")
            if command[end : end + 1] == "#":
                raise UnparseableCommand("a # right after an array assignment")
            parts.append(command[index:end])
            before = ")"
            index = end
            continue
        end = _skip_literal(command, index)
        if end == -1:
            raise UnparseableCommand("shell command could not be parsed")
        if end == index:
            before = command[index]
            parts.append(before)
            index += 1
            continue
        span = command[index:end]
        if span != "\\\n":
            value = _unquote(span)
            # An escaped character (`"\\$a"`) is literal, so it is not magic.
            literal = value if span[0] == "'" else re.sub(r"\\.", "", span, flags=re.S)
            if (
                span[0] != "\\"
                and QUOTED_MAGIC.search(literal)
                and not (before.isalnum() or before in ("_", "="))
            ):
                magic = True
                glob = glob or bool(QUOTED_GLOB.search(literal))
            parts.append(value)
            before = value[-1:] or before
            quoted = True
        index = end
    text = "".join(parts)
    if not magic:
        return text, quoted, index
    pattern = glob and len(parts) == 1 and not PATTERN_UNSAFE.search(text)
    prefix = QUOTED_PATTERN_PREFIX if pattern else QUOTED_VALUE_PREFIX
    return prefix + text, quoted, index


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


def record_assignment(token: str, variables: dict[str, str]) -> None:
    """Track a bare `NAME=value` token's literal value, if it has one.

    Values that embed further expansion (`$`, backticks) are not "obvious"
    per the scoped fix, so the variable is left/marked unresolved rather than
    guessed.
    """
    match = ASSIGNMENT.match(token)
    if not match:
        return
    name, value = match.groups()
    if "$" in value or "`" in value:
        variables.pop(name, None)
        return
    variables[name] = value


def substitute(tokens: list[str], variables: dict[str, str]) -> list[str]:
    """Replace whole-token `$NAME`/`${NAME}` references with tracked values."""
    resolved = []
    for token in tokens:
        replaced = VARIABLE_REFERENCE.sub(
            lambda match: variables.get(match.group(1), match.group(0)), token
        )
        if replaced != token:
            resolved.append(replaced)
            continue
        match = VARIABLE_REFERENCE.fullmatch(token)
        if match and match.group(1) in variables:
            resolved.append(variables[match.group(1)])
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
    return token in REDIRECTS or (token.endswith(">") and token[:-1].isdigit())


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
) -> None:
    """Classify the inner command of every substitution placeholder in `token`.
    A placeholder may sit anywhere in a word (`$(pwd)/x`)."""
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
            )


def segment_targets(
    tokens: list[str],
    variables: dict[str, str],
    confirmed: list[str],
    uncertain: list[str],
    repo_root: str,
    working_directories: list[str],
    heredocs: dict[str, tuple[str, bool]],
    process_subs: dict[str, str],
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
    tokens = substitute(tokens, variables)
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if is_redirect(token):
            index += 1
            if index == len(tokens) or tokens[index] in REDIRECTS:
                raise AmbiguousCommand("redirection has no target")
            confirmed.extend(
                resolve_from_directories(
                    [tokens[index]], working_directories, repo_root
                )
            )
        index += 1

    # A command or process substitution always runs, regardless of which
    # command (or none) receives its output or /dev/fd path, so it is
    # recursively classified unconditionally - never merely because the outer
    # command looks unsafe.
    for token in tokens:
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
            )

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
        uncertain.extend(token for token in scanned if protected(token, repo_root))
        uncertain.extend(protected_path_literals(" ".join(scanned)))
        uncertain.extend(opaque_write_paths(" ".join(scanned)))


def classify_command(
    command: str,
    repo_root: str,
    variables: dict[str, str],
    working_directories: list[str],
    confirmed: list[str],
    uncertain: list[str],
    heredocs: dict[str, tuple[str, bool]],
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
