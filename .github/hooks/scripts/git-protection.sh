#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

INPUT=$(cat)
TOOL_NAME=$(printf '%s' "$INPUT" | python3 -c 'import json, sys
try:
    data = json.load(sys.stdin)
    print((data.get("toolName") or "").lower())
except Exception:
    print("")' 2>/dev/null || true)

if [[ "$TOOL_NAME" != "bash" ]]; then
  exit 0
fi

COMMAND=$(printf '%s' "$INPUT" | python3 -c 'import json, sys
try:
  data = json.load(sys.stdin)
  args = data.get("toolArgs")
  if isinstance(args, str):
    try:
      args = json.loads(args)
    except Exception:
      args = {}
  if not isinstance(args, dict):
    args = {}
  print(args.get("command") or "")
except Exception:
  print("")' 2>/dev/null || true)

if [[ -z "$COMMAND" ]]; then
  exit 0
fi

if printf '%s' "$COMMAND" | grep -Eq 'git[[:space:]]+push[[:space:]].*(-f|--force)([[:space:]]|$)'; then
  printf '%s\n' '{"permissionDecision":"deny","permissionDecisionReason":"Blocked dangerous git operation: git push --force"}'
  exit 0
fi

if printf '%s' "$COMMAND" | grep -Eq 'git[[:space:]]+reset[[:space:]]+--hard([[:space:]]|$)'; then
  printf '%s\n' '{"permissionDecision":"deny","permissionDecisionReason":"Blocked dangerous git operation: git reset --hard"}'
  exit 0
fi

if printf '%s' "$COMMAND" | grep -Eq 'git[[:space:]]+branch[[:space:]]+-D[[:space:]]+(main|master)([[:space:]]|$)'; then
  printf '%s\n' '{"permissionDecision":"deny","permissionDecisionReason":"Blocked dangerous git operation: deleting main/master branch"}'
  exit 0
fi

if printf '%s' "$COMMAND" | grep -Eq 'git[[:space:]]+clean[[:space:]]+-[[:alnum:]]*f[[:alnum:]]*d[[:alnum:]]*([[:space:]]|$)'; then
  printf '%s\n' '{"permissionDecision":"deny","permissionDecisionReason":"Blocked dangerous git operation: git clean -fd"}'
  exit 0
fi

exit 0
