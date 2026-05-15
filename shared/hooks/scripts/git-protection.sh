#!/usr/bin/env bash
set -euo pipefail

run_python() {
  if command -v uv >/dev/null 2>&1; then
    UV_CACHE_DIR="${UV_CACHE_DIR:-${TMPDIR:-/tmp}/uv-cache}" uv run python "$@"
    return $?
  fi
  return 127
}

if ! command -v uv >/dev/null 2>&1; then
  exit 0
fi

INPUT=$(cat)
OUTPUT=$(printf '%s' "$INPUT" | run_python -c 'import json, re, sys

try:
  data = json.load(sys.stdin)
except Exception:
  sys.exit(0)

tool_input = data.get("tool_input")
if tool_input is None:
  tool_input = data.get("toolArgs")
if isinstance(tool_input, str):
  try:
    tool_input = json.loads(tool_input)
  except Exception:
    tool_input = {"command": tool_input}
if not isinstance(tool_input, dict):
  tool_input = {}

command = str(tool_input.get("command") or "")
if not command:
  sys.exit(0)

normalized = " ".join(command.lower().split())
rules = [
  (r"git\s+push\b.*(?:\s-f(?:\s|$)|\s--force(?:\s|$)|\s--force-with-lease(?:\s|$))", "Blocked dangerous git operation: force push"),
  (r"git\s+push\b.*\s--mirror(?:\s|$)", "Blocked dangerous git operation: git push --mirror"),
  (r"git\s+reset\s+--hard(?:\s|$)", "Blocked dangerous git operation: git reset --hard"),
  (r"git\s+checkout\s+--(?:\s|$)", "Blocked dangerous git operation: git checkout --"),
  (r"git\s+restore\b.*\s--source(?:\s|=)", "Blocked dangerous git operation: git restore --source"),
  (r"git\s+clean\s+-[^\n]*f[^\n]*d", "Blocked dangerous git operation: git clean -fd"),
  (r"git\s+branch\s+-d\s+(main|master)(?:\s|$)", "Blocked dangerous git operation: deleting main/master branch"),
]

for pattern, reason in rules:
  if re.search(pattern, normalized):
    print(json.dumps({
      "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason,
      }
    }))
    sys.exit(0)
' 2>/dev/null || true)

if [[ -n "$OUTPUT" ]]; then
  printf '%s\n' "$OUTPUT"
fi

exit 0
