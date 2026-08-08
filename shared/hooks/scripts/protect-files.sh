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

set +e
OUTPUT="$(printf '%s' "$INPUT" | python3 "$SCRIPT_DIR/protect-files.py" "$TARGET_ID" "$REPO_ROOT")"
STATUS=$?
set -e
if [[ "$STATUS" -ne 0 ]]; then
  fail_closed "protected-file classifier exited with status $STATUS"
fi
if [[ -n "$OUTPUT" ]]; then
  printf '%s\n' "$OUTPUT"
fi
