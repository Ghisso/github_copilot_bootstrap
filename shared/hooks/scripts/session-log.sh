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
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
TARGET_ID="${1:-unknown-target}"
LOG_DIR="$REPO_ROOT/.claude/session_logs"
LOG_FILE="$LOG_DIR/hooks-sessions.log"
mkdir -p "$LOG_DIR"

# Generate timestamp in bash — Claude Code hook payloads do not include a timestamp field.
NOW="$(date -u +%Y-%m-%dT%H:%M:%S.000Z 2>/dev/null || echo "unknown-timestamp")"

LINE=$(printf '%s' "$INPUT" | TARGET_ID="$TARGET_ID" NOW="$NOW" run_python -c 'import json, os, sys
try:
  data = json.load(sys.stdin)
except Exception:
  sys.exit(0)

def sanitize(value: object) -> str:
  text = str(value or "")
  return text.replace("\n", " ").replace(",", " ").strip()

timestamp = sanitize(os.environ.get("NOW"))
# Claude Code uses snake_case (hook_event_name, session_id); Codex uses camelCase (hookEventName, sessionId) or (event, session_id)
event = sanitize(data.get("hook_event_name") or data.get("hookEventName") or data.get("event"))
session_id = sanitize(data.get("sessionId") or data.get("session_id"))
source = sanitize(data.get("source"))
target = sanitize(os.environ.get("TARGET_ID"))
prompt = sanitize(data.get("prompt") or data.get("initialPrompt"))
stop_hook_active = sanitize(data.get("stop_hook_active"))
event_value = event or "unknown"

parts = [timestamp or "unknown-timestamp", f"event={event_value}"]
if target:
  parts.append(f"target={target}")
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
