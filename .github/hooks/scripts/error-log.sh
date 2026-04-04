#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

INPUT=$(cat)
LOG_DIR=".github/session_logs"
LOG_FILE="$LOG_DIR/hooks-errors.log"
mkdir -p "$LOG_DIR"

TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)
ERROR_NAME=$(printf '%s' "$INPUT" | python3 -c 'import json, sys
try:
	data = json.load(sys.stdin)
	err = data.get("error") if isinstance(data.get("error"), dict) else {}
	print(err.get("name") or "UnknownError")
except Exception:
	print("UnknownError")' 2>/dev/null || true)
ERROR_MESSAGE=$(printf '%s' "$INPUT" | python3 -c 'import json, sys
try:
	data = json.load(sys.stdin)
	err = data.get("error") if isinstance(data.get("error"), dict) else {}
	msg = (err.get("message") or "No message").replace("\n", " ").replace(",", " ")
	print(msg)
except Exception:
	print("No message")' 2>/dev/null || true)

printf '%s,error=%s,message=%s\n' "$TIMESTAMP" "$ERROR_NAME" "$ERROR_MESSAGE" >> "$LOG_FILE"

exit 0
