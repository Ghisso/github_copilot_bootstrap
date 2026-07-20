#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
LOG_DIR="$REPO_ROOT/.claude/session_logs"
ERROR_LOG="$LOG_DIR/hooks-errors.log"
mkdir -p "$LOG_DIR"

changed_non_state="$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null | awk '
  $2 !~ /^\.claude\/(session_logs|quality_reports|plans|MEMORY\.md)/ { print; found = 1 }
  END { exit found ? 0 : 1 }
' || true)"

if [[ -z "$changed_non_state" ]]; then
  exit 0
fi

today="$(date -u +%Y-%m-%d)"
# Portable freshness check: `-mtime -1` (modified within the last day) works on
# both GNU and BSD find, unlike GNU-only `-newermt`. Combined with the
# date-stamped filename this is a good-enough signal for a warn-only path; if
# find errors, we fall through to the warning rather than silently passing.
if find "$LOG_DIR" -maxdepth 1 -name "${today}_*.md" -type f -mtime -1 2>/dev/null | grep -q .; then
  exit 0
fi

printf '%s WARN stop-session-log-check: worktree changed but no session log was updated today\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$ERROR_LOG"
exit 0
