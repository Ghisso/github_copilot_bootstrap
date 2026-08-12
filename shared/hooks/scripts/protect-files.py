#!/usr/bin/env python3
"""Classify protected-file mutations from one PreToolUse payload."""

from __future__ import annotations

import json
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
ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
VARIABLE_REFERENCE = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)\}?")
PROTECTED_LITERAL = re.compile(
    r"(?:\.env(?:\.[\w.-]+)?|uv\.lock|credentials[^\s/'\"]*|[^\s/'\"]*secret[^\s/'\"]*|[^\s/'\"]+\.(?:pem|key)|(?:\.github|\.claude|\.codex)/hooks/[^\s'\"]+|\.claude/settings\.json|\.codex/(?:config\.toml|hooks\.json))",
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
    if value.startswith("file://"):
        value = value[7:]
    if repo_root and value.startswith(repo_root.rstrip("/") + "/"):
        value = value[len(repo_root.rstrip("/")) + 1 :]
    return posixpath.normpath(value).removeprefix("./")


def protected(path: str, repo_root: str) -> tuple[str, bool] | None:
    normalized = normalize(path, repo_root)
    if (
        normalized in HOOK_CONFIGS
        or normalized.startswith((".github/hooks/", ".claude/hooks/", ".codex/hooks/"))
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
        or "secret" in base
    ):
        return normalized, False
    return None


def protected_literals(value: str) -> list[str]:
    """Return every protected-looking literal embedded in an opaque command."""
    return [match.rstrip(",;:)") for match in PROTECTED_LITERAL.findall(value)]


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


def split_segments(command: str) -> list[list[str]]:
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
    for token in args:
        if not token.startswith("-"):
            return token
    return None


def segment_targets(
    tokens: list[str],
    variables: dict[str, str],
    confirmed: list[str],
    uncertain: list[str],
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
            confirmed.append(tokens[index])
        index += 1

    if command_info is None:
        return
    command, start = command_info
    args = tokens[start:]
    if command in SIMPLE_MUTATORS:
        confirmed.extend(operands(args, OPTION_VALUES.get(command, set())))
    elif command in {"cp", "install"}:
        directory = target_directory(args)
        candidates = operands(
            args, OPTION_VALUES[command] | {"-t", "--target-directory"}
        )
        if directory:
            confirmed.extend(candidates)
            confirmed.append(directory)
        elif candidates:
            confirmed.extend(candidates)
        else:
            raise AmbiguousCommand(f"{command} has no destination")
    elif command == "mv":
        directory = target_directory(args)
        candidates = operands(
            args, OPTION_VALUES[command] | {"-t", "--target-directory"}
        )
        if directory:
            confirmed.extend(candidates)
            confirmed.append(directory)
        elif len(candidates) >= 2:
            confirmed.extend(candidates)
        else:
            raise AmbiguousCommand("mv has no source and destination")
    elif command in {"chmod", "chown"}:
        candidates = operands(args, OPTION_VALUES[command])
        if len(candidates) < 2:
            raise AmbiguousCommand(f"{command} has no path operand")
        confirmed.extend(candidates[1:])
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
            confirmed.extend(candidates if command == "perl" else candidates[1:])
    elif command == "dd":
        confirmed.extend(
            arg.partition("=")[2]
            for arg in args
            if arg.startswith("of=") and arg.partition("=")[2]
        )
    elif command == "git":
        # git has too many mutating subcommands to enumerate safely, so only
        # the provably read-only ones are cleared; everything else is uncertain.
        if git_subcommand(args) not in GIT_READ_ONLY_SUBCOMMANDS:
            uncertain.extend(token for token in args if protected(token, ""))
            uncertain.extend(protected_literals(" ".join(args)))
    elif command not in READ_ONLY:
        # Unknown interpreters and archive tools are not proven read-only, but
        # nor is a mutation confirmed: flag any protected literal as uncertain
        # rather than guessing the command's syntax or failing the hook closed.
        uncertain.extend(token for token in args if protected(token, ""))
        uncertain.extend(protected_literals(" ".join(args)))


def shell_targets(command: str) -> tuple[list[str], list[str]]:
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
    for segment in split_segments(command):
        try:
            segment_targets(segment, variables, confirmed, uncertain)
        except AmbiguousCommand:
            resolved = substitute(segment, variables)
            uncertain.extend(token for token in resolved if protected(token, ""))
            uncertain.extend(protected_literals(" ".join(resolved)))
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
        decision = "deny" if target_id == "openai-codex" else "ask"
        reason = (
            "Editing hook files is blocked in Codex because PreToolUse cannot request approval: "
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
        confirmed, uncertain = shell_targets(command)
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
