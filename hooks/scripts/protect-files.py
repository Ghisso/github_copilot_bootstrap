#!/usr/bin/env python3
"""Classify protected-file mutations from one PreToolUse payload."""

from __future__ import annotations

import glob
import json
import os
import posixpath
import re
import shlex
import sys


HOOK_CONFIGS = {
    ".github/hooks/hooks.json",
    ".claude/settings.json",
    ".codex/config.toml",
    ".codex/hooks.json",
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
QUOTED_GLOB = re.compile(r"(?<![=\w])(['\"])([^'\"]*[?*[][^'\"]*)\1")
QUOTED_BRACE = re.compile(r"(['\"])([^'\"]*(?<!\$)\{[^'\"]+\}[^'\"]*)\1")
QUOTED_VARIABLE = re.compile(r"(['\"])\$(?:\{)?([A-Za-z_][A-Za-z0-9_]*)(?:\})?\1")
QUOTED_VARIABLE_AFFIX = re.compile(
    r"(['\"])([^'\"]*)\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))([^'\"]*)\1"
)
QUOTED_VARIABLE_MARKER = re.compile(
    r"^__PROTECT_FILES_QUOTED_VARIABLE_([A-Za-z_][A-Za-z0-9_]*)__$"
)
PROTECTED_PATH_LITERAL = re.compile(
    r"(?:\.env(?:\.[\w.-]+)?|uv\.lock|credentials[-_.][\w.-]+|"
    r"[^\s/'\"]+\.(?:pem|key)|(?:\.github|\.claude|\.codex)/hooks/[^\s'\"]+|"
    r"\.claude/settings\.json|\.codex/(?:config\.toml|hooks\.json))",
    re.IGNORECASE,
)
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
QUOTED_VALUE_PREFIX = "__PROTECT_FILES_QUOTED_VALUE__"
PROCESS_SUB_PREFIX = "__PROTECT_FILES_PROCSUB_"
HEREDOC_PREFIX = "__PROTECT_FILES_HEREDOC_"
HEREDOC_WORD = re.compile(
    r"[ \t]*(?:'([A-Za-z0-9_]+)'|\"([A-Za-z0-9_]+)\"|([A-Za-z0-9_]+))"
)
# Shell interpreters whose *bare* heredoc body (no inline -c script and no
# script-file argument) is the script they actually execute, so it is
# recursively classified rather than merely scanned as literal text.
SHELL_INTERPRETERS = {"bash", "sh", "zsh"}


class AmbiguousCommand(ValueError):
    """Valid shell syntax the classifier cannot fully model.

    Not a crash: callers resolve this against protected-resource evidence
    (allow if none is present, conservative deny if some is) rather than
    failing the whole hook closed.
    """


class UnparseableCommand(ValueError):
    """The shell text itself could not be tokenized (e.g. an unterminated
    quote, an unbalanced process substitution, or a heredoc with no
    delimiter word or no terminator line).

    Deliberately a sibling of AmbiguousCommand, not a subclass: recursive
    classification of a process substitution or a bare shell heredoc runs
    inside an `except AmbiguousCommand` fallback (see `classify_command`), so
    genuinely malformed nested syntax must keep propagating to the top-level
    fail-closed exit instead of being caught there and downgraded to a soft,
    resource-scoped denial.
    """


def normalize(path: str, repo_root: str) -> str:
    value = path.strip().strip("\"'").replace("\\", "/")
    value = value.removeprefix(QUOTED_VALUE_PREFIX)
    if value.startswith("file://"):
        value = value[7:]
    if repo_root and value.startswith(repo_root.rstrip("/") + "/"):
        value = value[len(repo_root.rstrip("/")) + 1 :]
    return posixpath.normpath(value).removeprefix("./")


def protected(path: str, repo_root: str) -> tuple[str, bool] | None:
    raw = normalize(path, repo_root)
    candidate = path.strip().strip("\"'").replace("\\", "/")
    if candidate.startswith("file://"):
        candidate = candidate[7:]
    if not os.path.isabs(candidate):
        candidate = os.path.join(repo_root, candidate)
    resolved = os.path.realpath(candidate)
    normalized_paths = [raw]
    if repo_root:
        normalized_paths.append(os.path.relpath(resolved, repo_root).replace("\\", "/"))
    else:
        normalized_paths.append(resolved.replace("\\", "/"))
    for normalized in normalized_paths:
        normalized = posixpath.normpath(normalized).removeprefix("./")
        if (
            normalized in HOOK_CONFIGS
            or normalized.startswith(
                (".github/hooks/", ".claude/hooks/", ".codex/hooks/")
            )
            or "/.claude/hooks/" in normalized
            or "/.github/hooks/" in normalized
            or "/.codex/hooks/" in normalized
        ):
            return normalized, True
        base = posixpath.basename(normalized).lower()
        if (
            base in {".env", ".env.local", "uv.lock"}
            or base.startswith((".env.", "credentials"))
            or base.endswith((".pem", ".key"))
        ):
            return normalized, False
    return None


def resolve_operands(
    paths: list[str], base_dir: str, repository_root: str = ""
) -> list[str]:
    """Expand filesystem operands without evaluating shell syntax."""
    display_root = repository_root or base_dir
    resolved: list[str] = []
    for path in paths:
        quoted_value = path.startswith(QUOTED_VALUE_PREFIX)
        path = path.removeprefix(QUOTED_VALUE_PREFIX)
        brace = re.search(r"\{([^{}]+)\}", path)
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
    return [match.rstrip(",;:)") for match in PROTECTED_PATH_LITERAL.findall(value)]


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


def protect_quoted_globs(command: str) -> str:
    """Hide quoted glob characters so only shell-expanded patterns are resolved."""
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        value = match.group(2)
        if any(character.isspace() or character in ";|&<>" for character in value):
            return match.group(0)
        marker = f"__PROTECT_FILES_QUOTED_GLOB_{count}__"
        count += 1
        return marker

    command = QUOTED_GLOB.sub(replace, command)
    command = QUOTED_BRACE.sub(replace, command)
    command = QUOTED_VARIABLE.sub(
        lambda match: f"__PROTECT_FILES_QUOTED_VARIABLE_{match.group(2)}__",
        command,
    )
    return QUOTED_VARIABLE_AFFIX.sub(
        lambda match: (
            QUOTED_VALUE_PREFIX
            + match.group(2)
            + "${"
            + (match.group(3) or match.group(4))
            + "}"
            + match.group(5)
        ),
        command,
    )


def _matching_paren(text: str, open_index: int) -> int:
    """Return the index just past the ')' matching text[open_index] == '(',
    honoring nested parens and quotes. Returns -1 when never closed."""
    depth = 0
    index = open_index
    quote: str | None = None
    length = len(text)
    while index < length:
        char = text[index]
        if quote:
            if char == quote and text[index - 1] != "\\":
                quote = None
            index += 1
            continue
        if char in ("'", '"'):
            quote = char
            index += 1
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return index + 1
        index += 1
    return -1


def extract_process_substitutions(command: str) -> tuple[str, dict[str, str]]:
    """Replace every <( ) / >( ) construct with an inert placeholder so outer
    tokenization sees a plain word, returning the substituted text and a
    placeholder -> inner-command mapping for recursive classification.

    The placeholder is padded with a space on both sides regardless of what
    was originally adjacent. `<` and `>` are shell metacharacters that do
    not require surrounding whitespace (`cat<(...)` is valid bash - it word-
    glues, exactly like `$( )`, so the process substitution still forks and
    executes even though the resulting word is unlikely to be a real
    command), but `shlex` has no such rule: with no separator it would merge
    the placeholder into an adjacent word, and the substitution's own
    placeholder token - the only thing `segment_targets` can look up in
    `process_subs` - would vanish. The single extra space is always safe:
    `whitespace_split=True` collapses any run of whitespace, so it can never
    change how an already-separated case tokenizes.

    A construct inside a quoted string is left untouched (quoting suppresses
    process substitution in real shells too). An unbalanced construct is
    genuinely malformed shell syntax, not merely unmodeled, so it fails
    closed rather than being silently dropped.
    """
    pieces: list[str] = []
    inner_by_placeholder: dict[str, str] = {}
    index = 0
    length = len(command)
    quote: str | None = None
    count = 0
    while index < length:
        char = command[index]
        if quote:
            pieces.append(char)
            if char == quote and command[index - 1] != "\\":
                quote = None
            index += 1
            continue
        if char in ("'", '"'):
            quote = char
            pieces.append(char)
            index += 1
            continue
        if char in ("<", ">") and command[index + 1 : index + 2] == "(":
            end = _matching_paren(command, index + 1)
            if end == -1:
                raise UnparseableCommand("unbalanced process substitution")
            placeholder = "%s%d__" % (PROCESS_SUB_PREFIX, count)
            count += 1
            inner_by_placeholder[placeholder] = command[index + 2 : end - 1]
            pieces.append(" " + placeholder + " ")
            index = end
            continue
        pieces.append(char)
        index += 1
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
    quote: str | None = None
    index = 0
    length = len(text)
    arithmetic_depth = 0
    while index < length:
        char = text[index]
        if quote:
            if char == quote and text[index - 1] != "\\":
                quote = None
            index += 1
            continue
        if char in ("'", '"'):
            quote = char
            index += 1
            continue
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
    equivalent to `bash <<'EOF'`), but `shlex` has no such rule: with no
    separator it would merge the placeholder into an adjacent word, and
    neither `command_name` nor the redirect-target/operand lookups that key
    off an exact placeholder token would ever see it as its own token again.
    The single extra space is always safe: `whitespace_split=True` collapses
    any run of whitespace, so it can never change how an already-separated
    case tokenizes.

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


def split_segments(command: str) -> list[list[str]]:
    command = command.replace("\\\n", "")
    command = protect_quoted_globs(command)
    try:
        lexer = shlex.shlex(
            command.replace("\n", ";"), posix=True, punctuation_chars=";&|<>()"
        )
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError as error:
        raise UnparseableCommand("shell command could not be parsed") from error
    if not tokens:
        return []
    segments: list[list[str]] = [[]]
    for token in tokens:
        if token in OPERATORS:
            if not segments[-1]:
                raise AmbiguousCommand("empty shell command segment")
            segments.append([])
        else:
            segments[-1].append(token)
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
        quoted = QUOTED_VARIABLE_MARKER.fullmatch(token)
        if quoted and quoted.group(1) in variables:
            resolved.append(QUOTED_VALUE_PREFIX + variables[quoted.group(1)])
            continue
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
) -> tuple[str, int] | None:
    """Return (command, args-start-index) and record leading assignments.

    Records any leading `NAME=value` tokens (including ones after a
    sudo/env/command wrapper) into `variables` as a side effect. Returns None
    for a segment consisting entirely of assignments (`FOO=bar`): that is
    valid Bash with no command to classify, not an ambiguity.
    """
    index = 0
    while (
        index < len(tokens)
        and "=" in tokens[index]
        and not tokens[index].startswith("-")
    ):
        record_assignment(tokens[index], variables)
        index += 1
    if index == len(tokens):
        return None
    while index < len(tokens) and tokens[index] in {"sudo", "env", "command"}:
        index += 1
        while index < len(tokens) and tokens[index].startswith("-"):
            index += 1
        if (
            index < len(tokens)
            and "=" in tokens[index]
            and not tokens[index].startswith("-")
        ):
            record_assignment(tokens[index], variables)
            index += 1
    if index == len(tokens):
        raise AmbiguousCommand("shell wrapper has no command")
    return tokens[index], index + 1


def operands(tokens: list[str], value_options: set[str]) -> list[str]:
    """Return command operands, omitting redirections and option values."""
    result: list[str] = []
    index = 0
    options_done = False
    while index < len(tokens):
        token = tokens[index]
        if token in REDIRECTS or (token.endswith(">") and token[:-1].isdigit()):
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
    variables: dict[str, str],
    working_directories: list[str],
    confirmed: list[str],
    uncertain: list[str],
) -> None:
    """Classify one heredoc body by what its consuming command does with its
    own standard input.

    An *unquoted* delimiter's body is expanded by the shell itself before
    any consuming command runs, regardless of that command's own semantics,
    so an embedded $( )/`...` always executes and is recursively
    classified first, unconditionally. Like a process substitution, this
    expansion runs in a subshell of the *current* shell, so it inherits a
    copy of the tracked `variables` (e.g. `$TARGET` resolves inside
    `$(touch $TARGET)` when an earlier `TARGET=.env` was seen), unlike the
    bare-shell-heredoc case below.

    A bare shell interpreter then executes the whole body itself and is
    classified recursively. git's own -F - stdin convention is a genuine
    exception: its content is stored as an object-database message, never
    a working-tree file, so nothing further is scanned. Everything else -
    a READ_ONLY command (sed's own script language supports `w file` and
    `e` without needing -i), an interpreter heredoc, a shell fed an
    explicit script file, or a wholly unmodeled command - gets the same
    conservative literal/opaque-write fallback an unmodeled command's own
    arguments already get, rather than being skipped outright.
    """
    if not quoted:
        for inner in heredoc_command_substitutions(body):
            classify_command(
                inner,
                repo_root,
                dict(variables),
                list(working_directories),
                confirmed,
                uncertain,
                heredocs,
            )
    if command == "git" and git_reads_message_from_stdin(args):
        return
    if command in SHELL_INTERPRETERS and _heredoc_is_bare_shell(args, heredocs):
        # A bare `bash <<EOF ... EOF` starts a new interpreter process: it
        # only inherits the working directory (a process attribute), not
        # this classifier's tracked, non-exported shell variables.
        classify_command(
            body,
            repo_root,
            {},
            list(working_directories),
            confirmed,
            uncertain,
            heredocs,
        )
        return
    uncertain.extend(protected_path_literals(body))
    uncertain.extend(opaque_write_paths(body))


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
    # command_name() records this segment's leading NAME=value assignments as
    # a side effect, so it must run on the raw tokens before substitute():
    # otherwise a same-segment `TARGET=.env rm "$TARGET"` would substitute
    # "$TARGET" using not-yet-recorded variables and leave it unresolved.
    command_info = command_name(tokens, variables)
    tokens = substitute(tokens, variables)
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in REDIRECTS or (token.endswith(">") and token[:-1].isdigit()):
            index += 1
            if index == len(tokens) or tokens[index] in REDIRECTS:
                raise AmbiguousCommand("redirection has no target")
            confirmed.extend(
                resolve_from_directories(
                    [tokens[index]], working_directories, repo_root
                )
            )
        index += 1

    # A process substitution always runs, regardless of which command (or
    # none) receives its /dev/fd path, so it is recursively classified
    # unconditionally - never merely because the outer command looks unsafe.
    for token in tokens:
        inner = process_subs.get(token)
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

    if command_info is None:
        return
    command, start = command_info
    args = tokens[start:]

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
                variables,
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
            uncertain.extend(token for token in args if protected(token, repo_root))
    elif command not in READ_ONLY:
        # Unknown commands are not interpreted as filesystem mutations merely
        # because their source or prose contains a sensitive-looking word.
        # Explicit paths remain covered by native edits and known mutators.
        uncertain.extend(token for token in args if protected(token, repo_root))
        uncertain.extend(protected_path_literals(" ".join(args)))
        uncertain.extend(opaque_write_paths(" ".join(args)))


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
    extracts its own heredocs and process substitutions before tokenizing.

    `heredocs` is one mapping shared (by reference, never copied) across the
    whole recursive call tree for a single top-level command, with new
    placeholders numbered above whatever it already holds. A heredoc found
    while scanning an outer level can end up embedded, as an inert
    placeholder, inside a process substitution or a bare shell heredoc body
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
    command, found_heredocs = extract_heredocs(command, start_count=len(heredocs))
    heredocs.update(found_heredocs)
    command, process_subs = extract_process_substitutions(command)
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


def shell_targets(command: str, repo_root: str) -> tuple[list[str], list[str]]:
    """Return (confirmed_targets, uncertain_targets) for a whole command line."""
    confirmed: list[str] = []
    uncertain: list[str] = []
    classify_command(command, repo_root, {}, [repo_root], confirmed, uncertain, {})
    return confirmed, uncertain


def native_targets(value: object, paths: list[str], key: str | None = None) -> None:
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            native_targets(child_value, paths, str(child_key).lower())
        return
    if isinstance(value, list):
        for child in value:
            native_targets(child, paths, key)
        return
    if not isinstance(value, str):
        return
    add_patch_paths(value, paths)
    if key in PATH_KEYS:
        paths.append(value)


def emit(
    target_id: str, repo_root: str, paths: list[str], uncertain: list[str]
) -> None:
    hits = [result for path in paths if (result := protected(path, repo_root))]
    hooks = sorted({path for path, is_hook in hits if is_hook})
    sensitive = sorted({path for path, is_hook in hits if not is_hook})
    uncertain_hits = sorted(
        {result[0] for path in uncertain if (result := protected(path, repo_root))}
    )
    if hooks:
        decision = (
            "deny" if target_id in {"openai-codex", "google-antigravity"} else "ask"
        )
        reason = (
            "Editing hook files is blocked because PreToolUse cannot request approval: "
            if decision == "deny"
            else "Editing hook files requires approval: "
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
    paths: list[str] = []
    uncertain: list[str] = []
    if tool_name in {"bash", "shell"} or tool_name.endswith("bash") or not tool_name:
        command = tool_input.get("command")
        if not isinstance(command, str):
            raise AmbiguousCommand("Bash payload has no command")
        confirmed, uncertain = shell_targets(command, repo_root)
        paths.extend(confirmed)
    else:
        native_targets(tool_input, paths)
    emit(target_id, repo_root, paths, uncertain)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AmbiguousCommand, ValueError, json.JSONDecodeError) as error:
        print("protect-files classifier error: %s" % error, file=sys.stderr)
        raise SystemExit(2)
