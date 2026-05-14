#!/usr/bin/env bash
set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
  exit 0
fi

INPUT=$(cat)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET_CONFIG_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$TARGET_CONFIG_ROOT/session_logs"
LOG_FILE="$LOG_DIR/hooks-sessions.log"
mkdir -p "$LOG_DIR"

LINE=$(printf '%s' "$INPUT" | python3 -c 'import json, sys
try:
  data = json.load(sys.stdin)
except Exception:
  sys.exit(0)

def sanitize(value: object) -> str:
  text = str(value or "")
  return text.replace("\n", " ").replace(",", " ").strip()

timestamp = sanitize(data.get("timestamp"))
event = sanitize(data.get("hookEventName"))
session_id = sanitize(data.get("sessionId"))
source = sanitize(data.get("source"))
prompt = sanitize(data.get("prompt") or data.get("initialPrompt"))
stop_hook_active = sanitize(data.get("stop_hook_active"))
event_value = event or "unknown"

parts = [timestamp or "unknown-timestamp", f"event={event_value}"]
if session_id:
  parts.append(f"sessionId={session_id}")
if source:
  parts.append(f"source={source}")
if prompt:
  parts.append(f"prompt={prompt}")
if stop_hook_active:
  parts.append(f"stop_hook_active={stop_hook_active}")

print(",".join(parts))' 2>/dev/null || true)

if [[ -n "$LINE" ]]; then
  printf '%s\n' "$LINE" >> "$LOG_FILE"
fi

exit 0
