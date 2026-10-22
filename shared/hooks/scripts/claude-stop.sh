#!/usr/bin/env bash
set -euo pipefail

# Claude can run matching Stop handlers concurrently. Keep this wrapper as the
# one handler so session logging, checkpointing, and publication happen in order.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ERROR_LOG="$(cd "$SCRIPT_DIR/../../.." && pwd)/.claude/session_logs/hooks-errors.log"
# Command substitution strips trailing newlines, so it cannot replay an exact
# JSON payload. Keep a private temporary copy until every child has read it.
umask 077
PAYLOAD_FILE="$(mktemp "${TMPDIR:-/tmp}/claude-stop.XXXXXX")"
chmod 600 "$PAYLOAD_FILE"
trap 'rm -f "$PAYLOAD_FILE"' EXIT
cat > "$PAYLOAD_FILE"

warn() {
  local message="WARN claude-stop: $*"
  printf '%s\n' "$message" >&2
  mkdir -p "$(dirname "$ERROR_LOG")" 2>/dev/null || true
  printf '%s\n' "$message" >> "$ERROR_LOG" 2>/dev/null || true
}

if ! bash "$SCRIPT_DIR/session-log.sh" claude-code < "$PAYLOAD_FILE" >&2; then
  warn "session-log.sh failed; continuing."
fi

if ! bash "$SCRIPT_DIR/stop-session-log-check.sh" claude-code < "$PAYLOAD_FILE" >&2; then
  warn "stop-session-log-check.sh failed; continuing."
fi

if ! bash "$SCRIPT_DIR/state-sync.sh" checkpoint < "$PAYLOAD_FILE" >&2; then
  warn "state-sync.sh checkpoint failed; continuing."
fi

if ! bash "$SCRIPT_DIR/state-sync.sh" publish < "$PAYLOAD_FILE" >&2; then
  warn "state-sync.sh publish failed; continuing."
fi
