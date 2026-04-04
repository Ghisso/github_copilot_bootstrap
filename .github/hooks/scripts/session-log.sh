#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

INPUT=$(cat)
LOG_DIR=".github/session_logs"
LOG_FILE="$LOG_DIR/hooks-sessions.log"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
SOURCE=$(printf '%s' "$INPUT" | python3 -c 'import json, sys
try:
  data = json.load(sys.stdin)
  print(data.get("source") or "")
except Exception:
  print("")' 2>/dev/null || true)
REASON=$(printf '%s' "$INPUT" | python3 -c 'import json, sys
try:
  data = json.load(sys.stdin)
  print(data.get("reason") or "")
except Exception:
  print("")' 2>/dev/null || true)
INITIAL_PROMPT=$(printf '%s' "$INPUT" | python3 -c 'import json, sys
try:
  data = json.load(sys.stdin)
  print((data.get("initialPrompt") or "").replace("\n", " "))
except Exception:
  print("")' 2>/dev/null || true)

if [[ -n "$SOURCE" ]]; then
  printf '%s,event=sessionStart,source=%s' "$TIMESTAMP" "$SOURCE" >> "$LOG_FILE"
  if [[ -n "$INITIAL_PROMPT" ]]; then
    printf ',initialPrompt=%s' "$(printf '%s' "$INITIAL_PROMPT" | tr '\n' ' ' | sed 's/,/ /g')" >> "$LOG_FILE"
  fi
  printf '\n' >> "$LOG_FILE"
  exit 0
fi

if [[ -n "$REASON" ]]; then
  printf '%s,event=sessionEnd,reason=%s\n' "$TIMESTAMP" "$REASON" >> "$LOG_FILE"
fi

exit 0
