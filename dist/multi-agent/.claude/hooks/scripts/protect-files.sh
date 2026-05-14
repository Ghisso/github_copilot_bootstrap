#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
TARGET_ID="${1:-unknown-target}"
export REPO_ROOT
export TARGET_ID

INPUT=$(cat)
OUTPUT=$(printf '%s' "$INPUT" | python3 -c 'import json, os, posixpath, re, shlex, sys

repo_root = os.environ.get("REPO_ROOT", "").rstrip("/")
target_id = os.environ.get("TARGET_ID", "")

try:
  data = json.load(sys.stdin)
except Exception:
  sys.exit(0)

tool_name = str(data.get("tool_name") or data.get("toolName") or "").lower()
tool_input = data.get("tool_input")
if tool_input is None:
  tool_input = data.get("toolArgs")
if isinstance(tool_input, str):
  try:
    tool_input = json.loads(tool_input)
  except Exception:
    tool_input = {}
if not isinstance(tool_input, dict):
  tool_input = {}

is_bash = tool_name in {"bash", "shell"} or tool_name.endswith("bash")
bash_command = str(tool_input.get("command") or "") if is_bash else ""
bash_write_markers = (
  ">",
  "touch",
  "rm",
  "mv",
  "cp",
  "install",
  "mkdir",
  "rmdir",
  "chmod",
  "chown",
  "truncate",
  "tee",
  "sed",
  "perl",
)

mutation_keywords = (
  "edit",
  "create",
  "write",
  "delete",
  "rename",
  "move",
  "replace",
  "patch",
  "apply",
)
if tool_name and not any(keyword in tool_name for keyword in mutation_keywords):
  if not is_bash or not any(marker in bash_command for marker in bash_write_markers):
    sys.exit(0)

shell_commands = {
  "cat",
  "cp",
  "chmod",
  "chown",
  "install",
  "mkdir",
  "mv",
  "perl",
  "printf",
  "rm",
  "rmdir",
  "sed",
  "tee",
  "touch",
  "truncate",
}
shell_operators = {"|", "||", "&&", ";", ">", ">>", ">|", "<", "<<", "<<<", "&>", "2>", "2>>", "1>", "1>>"}

def looks_like_path(value: str) -> bool:
  return (
    value.startswith(("/", "./", "../", ".github/", ".claude/", ".codex/", ".agents/"))
    or "/" in value
    or value.endswith((".py", ".json", ".toml", ".md", ".sh", ".lock", ".env", ".pem", ".key"))
    or value in {".env", ".env.local", "uv.lock"}
  )

def collect_shell_paths(command: str) -> None:
  if not command:
    return
  redirection_pattern = re.compile(r"(?:^|[\s;|&])(?:[0-9]?>{1,2}|&>)\s*([^\s;&|]+)")
  for match in redirection_pattern.finditer(command):
    paths.append(match.group(1).strip("\""))

  for protected_pattern in (
    r"(?<![\w./-])\.env(?:\.[\w.-]+)?(?![\w./-])",
    r"(?<![\w./-])uv\.lock(?![\w./-])",
    r"(?<![\w./-])(?:\.github/hooks/|\.claude/hooks/|\.codex/hooks/)[^\s;&|\x27\"]+",
    r"(?<![\w./-])\.github/hooks/hooks\.json(?![\w./-])",
    r"(?<![\w./-])\.claude/settings\.json(?![\w./-])",
    r"(?<![\w./-])\.codex/(?:config\.toml|hooks\.json)(?![\w./-])",
  ):
    for match in re.finditer(protected_pattern, command):
      paths.append(match.group(0))

  try:
    tokens = shlex.split(command)
  except ValueError:
    tokens = command.replace(";", " ").replace("|", " ").split()

  for index, token in enumerate(tokens):
    stripped = token.strip("\"")
    if not stripped or stripped.startswith("-") or stripped in shell_commands or stripped in shell_operators:
      continue
    previous = tokens[index - 1] if index else ""
    if previous in {">", ">>", ">|", "&>", "2>", "2>>", "1>", "1>>"} or looks_like_path(stripped):
      paths.append(stripped)

path_keys = {
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
paths: list[str] = []
patch_prefixes = (
  "*** Add File: ",
  "*** Update File: ",
  "*** Delete File: ",
  "*** Move to: ",
)

def collect_patch_paths(value: str) -> None:
  if "*** Begin Patch" not in value:
    return
  for line in value.splitlines():
    for prefix in patch_prefixes:
      if line.startswith(prefix):
        paths.append(line[len(prefix):].strip())
        break

def collect(value: object, key: str | None = None) -> None:
  if isinstance(value, dict):
    for child_key, child_value in value.items():
      collect(child_value, str(child_key).lower())
    return
  if isinstance(value, list):
    for item in value:
      collect(item, key)
    return
  if not isinstance(value, str):
    return

  collect_patch_paths(value)
  normalized_key = (key or "").lower()
  if normalized_key in path_keys or value.startswith("/") or "/" in value or value.endswith((".py", ".json", ".md", ".sh", ".lock", ".env", ".pem", ".key")):
    paths.append(value)

if is_bash:
  collect_shell_paths(bash_command)
else:
  collect(tool_input)
if not paths:
  sys.exit(0)

def normalize(path: str) -> str:
  candidate = path.replace("\\", "/")
  if candidate.startswith("file://"):
    candidate = candidate[7:]
  # Strip repo-root prefix so absolute paths compare correctly against relative hook paths
  if repo_root and candidate.startswith(repo_root + "/"):
    candidate = candidate[len(repo_root) + 1:]
  candidate = posixpath.normpath(candidate)
  if candidate.startswith("./"):
    candidate = candidate[2:]
  return candidate

def is_hook_file(path: str) -> bool:
  hook_config_files = {
    ".github/hooks/hooks.json",
    ".claude/settings.json",
    ".codex/config.toml",
    ".codex/hooks.json",
  }
  hook_dirs = (
    ".github/hooks/",
    ".claude/hooks/",
    ".codex/hooks/",
  )
  return path in hook_config_files or any(path.startswith(prefix) for prefix in hook_dirs)

def is_protected(path: str) -> bool:
  basename = posixpath.basename(path).lower()
  lowered = path.lower()
  return (
    basename == ".env"
    or basename == ".env.local"
    or basename.startswith(".env.")
    or basename.endswith(".pem")
    or basename.endswith(".key")
    or "secret" in basename
    or basename.startswith("credentials")
    or basename == "uv.lock"
  )

normalized_paths = [normalize(path) for path in paths]
hook_paths = sorted({path for path in normalized_paths if is_hook_file(path)})
protected_paths = sorted({path for path in normalized_paths if is_protected(path)})

if hook_paths:
  hook_list = ", ".join(hook_paths)
  decision = "deny" if target_id == "openai-codex" else "ask"
  reason = (
    f"Editing hook files is blocked in Codex because PreToolUse cannot request approval: {hook_list}"
    if decision == "deny"
    else f"Editing hook files requires approval: {hook_list}"
  )
  print(json.dumps({
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": decision,
      "permissionDecisionReason": reason,
    }
  }))
  sys.exit(0)

if protected_paths:
  protected_list = ", ".join(protected_paths)
  reason = f"Protected file blocked by policy: {protected_list}"
  print(json.dumps({
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "deny",
      "permissionDecisionReason": reason,
    }
  }))
' 2>/dev/null || true)

if [[ -n "$OUTPUT" ]]; then
  printf '%s\n' "$OUTPUT"
fi

exit 0
