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


class AmbiguousCommand(ValueError):
    """Valid shell syntax the classifier cannot fully model.

    Not a crash: callers resolve this against protected-resource evidence
    (allow if none is present, conservative deny if some is) rather than
    failing the whole hook closed.
    """


class UnparseableCommand(AmbiguousCommand):
    """The shell text itself could not be tokenized (e.g. an unterminated quote).

    Unlike AmbiguousCommand, this is genuinely malformed input, not valid
    syntax our lightweight parser fails to model, so it stays fail-closed.
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


def segment_targets(
    tokens: list[str],
    variables: dict[str, str],
    confirmed: list[str],
    uncertain: list[str],
    repo_root: str,
    working_directories: list[str],
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

    if command_info is None:
        return
    command, start = command_info
    args = tokens[start:]
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


def shell_targets(command: str, repo_root: str) -> tuple[list[str], list[str]]:
    """Return (confirmed_targets, uncertain_targets) for a whole command line.

    A segment the classifier cannot fully model (AmbiguousCommand) does not
    abort the scan: it falls back to a conservative literal scan of that
    segment, so an ambiguity elsewhere in the command cannot hide a real
    mutation, while an ambiguity with no protected-resource evidence at all
    resolves to "nothing found" instead of an internal-error status.
    """
    confirmed: list[str] = []
    uncertain: list[str] = []
    variables: dict[str, str] = {}
    working_directories = [repo_root]
    for segment in split_segments(command):
        try:
            segment_targets(
                segment,
                variables,
                confirmed,
                uncertain,
                repo_root,
                working_directories,
            )
        except AmbiguousCommand:
            resolved = substitute(segment, variables)
            uncertain.extend(token for token in resolved if protected(token, repo_root))
            uncertain.extend(protected_path_literals(" ".join(resolved)))
            uncertain.extend(opaque_write_paths(" ".join(resolved)))
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
            "deny"
            if target_id in {"openai-codex", "google-antigravity"}
            else "ask"
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
