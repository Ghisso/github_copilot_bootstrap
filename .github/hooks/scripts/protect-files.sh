#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

INPUT=$(cat)
OUTPUT=$(printf '%s' "$INPUT" | python3 -c 'import json, posixpath, sys

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
  sys.exit(0)

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

  normalized_key = (key or "").lower()
  if normalized_key in path_keys or value.startswith("/") or "/" in value or value.endswith((".py", ".json", ".md", ".sh", ".lock", ".env", ".pem", ".key")):
    paths.append(value)

collect(tool_input)
if not paths:
  sys.exit(0)

def normalize(path: str) -> str:
  candidate = path.replace("\\", "/")
  if candidate.startswith("file://"):
    candidate = candidate[7:]
  if "/workspaces/RAG/" in candidate:
    candidate = candidate.split("/workspaces/RAG/", 1)[1]
  elif candidate.startswith("/workspaces/RAG"):
    candidate = candidate[len("/workspaces/RAG/"):]
  candidate = posixpath.normpath(candidate)
  if candidate.startswith("./"):
    candidate = candidate[2:]
  return candidate

def is_hook_file(path: str) -> bool:
  return path == ".github/hooks/hooks.json" or path.startswith(".github/hooks/")

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
  reason = f"Editing hook files requires approval: {hook_list}"
  print(json.dumps({
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "ask",
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
