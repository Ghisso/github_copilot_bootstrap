#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_lib-frontmatter.sh
. "$SCRIPT_DIR/_lib-frontmatter.sh"

TARGET_ID="${1:-unknown-target}"
REPO_ROOT="$(repo_root_from_script)"
INPUT="$(cat)"

# Empty events carry no tool call.  A present but malformed payload is a
# safety decision, not an optional-observability failure.
if [[ -z "${INPUT//[[:space:]]/}" ]]; then
  exit 0
fi
if ! payload_parseable "$INPUT"; then
  fail_closed "unparseable tool payload"
fi

# The classifier deliberately uses Python directly instead of `uv run`: hooks
# must still protect files before a project environment exists.  Python is the
# same dependency already used by payload_parseable in the shared hook library.
if ! command -v python3 >/dev/null 2>&1; then
  fail_closed "python3 is unavailable for protected-file classification"
fi

# Diagnostic: capture Python version for troubleshooting
PY_VERSION="$(python3 --version 2>&1 | head -1)" || PY_VERSION="unknown"
PY_PATH="$(command -v python3)" || PY_PATH="not found"

set +e
STDERR_TMP="$(mktemp 2>/dev/null)" || STDERR_TMP=""
if [[ -n "$STDERR_TMP" ]]; then
  OUTPUT="$(printf '%s' "$INPUT" | python3 "$SCRIPT_DIR/protect-files.py" "$TARGET_ID" "$REPO_ROOT" 2>"$STDERR_TMP")"
  STATUS=$?
else
  OUTPUT="$(printf '%s' "$INPUT" | python3 "$SCRIPT_DIR/protect-files.py" "$TARGET_ID" "$REPO_ROOT" 2>&1)"
  STATUS=$?
fi
set -e

if [[ "$STATUS" -ne 0 ]]; then
  if [[ -n "$STDERR_TMP" && -f "$STDERR_TMP" ]]; then
    CLASSIFIER_ERR="$(head -1 "$STDERR_TMP" 2>/dev/null | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')" || CLASSIFIER_ERR=""
    rm -f "$STDERR_TMP"
    DIAGNOSTIC_MSG="protected-file classifier exited with status $STATUS (python: $PY_VERSION, path: $PY_PATH, error: ${CLASSIFIER_ERR:-unknown})"
  else
    [[ -n "$STDERR_TMP" ]] && rm -f "$STDERR_TMP"
    DIAGNOSTIC_MSG="protected-file classifier exited with status $STATUS (python: $PY_VERSION, path: $PY_PATH)"
  fi
  fail_closed "$DIAGNOSTIC_MSG"
fi
if [[ -n "$OUTPUT" ]]; then
  printf '%s\n' "$OUTPUT"
fi
