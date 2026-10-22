#!/usr/bin/env bash
set -euo pipefail

# Codex runs matching Stop handlers concurrently. Keep this wrapper as the one
# handler so session logging, checkpointing, and publication happen in order.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# Command substitution strips trailing newlines, so it cannot replay an exact
# JSON payload. Keep a private temporary copy until every child has read it.
umask 077
PAYLOAD_FILE="$(mktemp "${TMPDIR:-/tmp}/codex-stop.XXXXXX")"
chmod 600 "$PAYLOAD_FILE"
trap 'rm -f "$PAYLOAD_FILE"' EXIT
cat > "$PAYLOAD_FILE"

warn() {
  printf 'WARN codex-stop: %s\n' "$*" >&2
}

if ! bash "$SCRIPT_DIR/session-log.sh" openai-codex < "$PAYLOAD_FILE" >/dev/null; then
  warn "session-log.sh failed; continuing."
fi

if ! bash "$SCRIPT_DIR/stop-session-log-check.sh" openai-codex < "$PAYLOAD_FILE" >/dev/null; then
  warn "stop-session-log-check.sh failed; continuing."
fi

if ! bash "$SCRIPT_DIR/state-sync.sh" checkpoint < "$PAYLOAD_FILE" >/dev/null; then
  warn "state-sync.sh checkpoint failed; continuing."
fi

if ! bash "$SCRIPT_DIR/state-sync.sh" publish < "$PAYLOAD_FILE" >/dev/null; then
  warn "state-sync.sh publish failed; continuing."
fi

printf '{"continue":true}\n'
