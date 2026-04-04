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

if [[ "$TOOL_NAME" != "edit" && "$TOOL_NAME" != "create" ]]; then
  exit 0
fi

FILE_PATH=$(printf '%s' "$INPUT" | python3 -c 'import json, sys
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
  print(args.get("path") or args.get("file_path") or args.get("filePath") or args.get("file") or "")
except Exception:
  print("")' 2>/dev/null || true)

if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

BASENAME=$(basename "$FILE_PATH")

is_protected=0
if [[ "$BASENAME" == ".env" || "$BASENAME" == ".env.local" || "$FILE_PATH" == *.env.* ]]; then
  is_protected=1
elif [[ "$BASENAME" == *.pem || "$BASENAME" == *.key ]]; then
  is_protected=1
elif [[ "$BASENAME" == *secret* || "$BASENAME" == credentials* ]]; then
  is_protected=1
elif [[ "$BASENAME" == "uv.lock" ]]; then
  is_protected=1
fi

if [[ "$is_protected" -eq 1 ]]; then
  printf '%s\n' '{"permissionDecision":"deny","permissionDecisionReason":"Protected file blocked by policy"}'
fi

exit 0
