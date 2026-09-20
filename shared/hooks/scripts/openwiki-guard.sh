#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_lib-frontmatter.sh
. "$SCRIPT_DIR/_lib-frontmatter.sh"

MODE="${1:-}"
INPUT="$(cat)"

# `post` never denies a tool call - the call already ran - so its failure
# path is a plain stderr message and exit 2, not fail_closed's PreToolUse-
# shaped deny JSON. `pre` failures always go through fail_closed.
fail() {
  if [[ "$MODE" == "post" ]]; then
    printf '%s\n' "$1" >&2
    exit 2
  fi
  fail_closed "$1"
}

if [[ "$MODE" != "pre" && "$MODE" != "post" ]]; then
  fail_closed "openwiki-guard: unknown mode ${MODE:-missing}"
fi

if ! payload_parseable "$INPUT"; then
  fail "unparseable tool payload"
fi

# Same reasoning as protect-files.sh: hooks must work before a project
# environment exists, so this calls python3 directly rather than `uv run`.
if ! command -v python3 >/dev/null 2>&1; then
  fail "python3 is unavailable for the openwiki guard"
fi

set +e
STDERR_TMP="$(mktemp 2>/dev/null)" || STDERR_TMP=""
if [[ -n "$STDERR_TMP" ]]; then
  OUTPUT="$(printf '%s' "$INPUT" | python3 "$SCRIPT_DIR/openwiki-guard.py" "$MODE" 2>"$STDERR_TMP")"
  STATUS=$?
else
  OUTPUT="$(printf '%s' "$INPUT" | python3 "$SCRIPT_DIR/openwiki-guard.py" "$MODE" 2>&1)"
  STATUS=$?
fi
set -e

if [[ "$STATUS" -ne 0 ]]; then
  REASON=""
  if [[ -n "$STDERR_TMP" && -f "$STDERR_TMP" ]]; then
    REASON="$(head -1 "$STDERR_TMP" 2>/dev/null)" || REASON=""
  fi
  [[ -n "$STDERR_TMP" ]] && rm -f "$STDERR_TMP"
  fail "${REASON:-openwiki-guard exited with status $STATUS}"
fi

[[ -n "$STDERR_TMP" ]] && rm -f "$STDERR_TMP"
if [[ -n "$OUTPUT" ]]; then
  printf '%s\n' "$OUTPUT"
fi
