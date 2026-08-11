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
READ_ONLY = {"cat", "wc", "rg", "grep", "head", "tail", "sed"}
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
    """The safety classifier cannot identify all mutation targets."""


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
        raise AmbiguousCommand("shell command could not be parsed") from error
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
        raise AmbiguousCommand("trailing shell command separator")
    return segments


def command_name(tokens: list[str]) -> tuple[str, int]:
    index = 0
    while (
        index < len(tokens)
        and "=" in tokens[index]
        and not tokens[index].startswith("-")
    ):
        index += 1
    if index == len(tokens):
        raise AmbiguousCommand("shell segment has no command")
    while index < len(tokens) and tokens[index] in {"sudo", "env", "command"}:
        index += 1
        while index < len(tokens) and tokens[index].startswith("-"):
            index += 1
        if (
            index < len(tokens)
            and "=" in tokens[index]
            and not tokens[index].startswith("-")
        ):
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


def segment_targets(tokens: list[str]) -> list[str]:
    targets: list[str] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in REDIRECTS or (token.endswith(">") and token[:-1].isdigit()):
            index += 1
            if index == len(tokens) or tokens[index] in REDIRECTS:
                raise AmbiguousCommand("redirection has no target")
            targets.append(tokens[index])
        index += 1

    command, start = command_name(tokens)
    args = tokens[start:]
    if command in SIMPLE_MUTATORS:
        targets.extend(operands(args, OPTION_VALUES.get(command, set())))
    elif command in {"cp", "install"}:
        directory = target_directory(args)
        candidates = operands(
            args, OPTION_VALUES[command] | {"-t", "--target-directory"}
        )
        if directory:
            targets.extend(candidates)
            targets.append(directory)
        elif candidates:
            targets.extend(candidates)
        else:
            raise AmbiguousCommand(f"{command} has no destination")
    elif command == "mv":
        directory = target_directory(args)
        candidates = operands(
            args, OPTION_VALUES[command] | {"-t", "--target-directory"}
        )
        if directory:
            targets.extend(candidates)
            targets.append(directory)
        elif len(candidates) >= 2:
            targets.extend(candidates)
        else:
            raise AmbiguousCommand("mv has no source and destination")
    elif command in {"chmod", "chown"}:
        candidates = operands(args, OPTION_VALUES[command])
        if len(candidates) < 2:
            raise AmbiguousCommand(f"{command} has no path operand")
        targets.extend(candidates[1:])
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
            targets.extend(candidates if command == "perl" else candidates[1:])
    elif command == "dd":
        targets.extend(
            arg.partition("=")[2]
            for arg in args
            if arg.startswith("of=") and arg.partition("=")[2]
        )
    elif command not in READ_ONLY:
        # Unknown interpreters and archive tools are not proven read-only. Any
        # protected literal therefore fails safe without guessing their syntax.
        targets.extend(token for token in args if protected(token, ""))
        targets.extend(protected_literals(" ".join(args)))
    return targets


def shell_targets(command: str) -> list[str]:
    targets: list[str] = []
    for segment in split_segments(command):
        targets.extend(segment_targets(segment))
    return targets


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


def emit(target_id: str, repo_root: str, paths: list[str]) -> None:
    hits = [result for path in paths if (result := protected(path, repo_root))]
    hooks = sorted({path for path, is_hook in hits if is_hook})
    sensitive = sorted({path for path, is_hook in hits if not is_hook})
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
    if tool_name in {"bash", "shell"} or tool_name.endswith("bash") or not tool_name:
        command = tool_input.get("command")
        if not isinstance(command, str):
            raise AmbiguousCommand("Bash payload has no command")
        paths.extend(shell_targets(command))
    else:
        native_targets(tool_input, paths)
    emit(target_id, repo_root, paths)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AmbiguousCommand, ValueError, json.JSONDecodeError) as error:
        print("protect-files classifier error: %s" % error, file=sys.stderr)
        raise SystemExit(2)
