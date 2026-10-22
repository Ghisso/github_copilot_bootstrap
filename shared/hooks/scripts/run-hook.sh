#!/usr/bin/env bash
set -euo pipefail

warn() {
  printf 'WARN run-hook: %s\n' "$*" >&2
}

if [[ $# -lt 1 ]]; then
  warn "missing hook script name"
  # Fail closed: a missing script name is a wiring error, and a non-zero exit
  # denies the tool call on runtimes that key blocking on exit status.
  exit 2
fi

HOOK_SCRIPT="$1"
shift

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"

if [[ ! -d "$REPO_ROOT/.claude/hooks/scripts" ]]; then
  for candidate in "${GITHUB_WORKSPACE:-}" "${WORKSPACE_FOLDER:-}" "${VSCODE_CWD:-}" "${PWD:-}"; do
    if [[ -n "$candidate" && -d "$candidate/.claude/hooks/scripts" ]]; then
      REPO_ROOT="$candidate"
      break
    fi
  done
fi

if [[ ! -d "$REPO_ROOT/.claude/hooks/scripts" ]] && command -v git >/dev/null 2>&1; then
  GIT_ROOT="$(git -C "${PWD:-.}" rev-parse --show-toplevel 2>/dev/null || true)"
  if [[ -n "$GIT_ROOT" && -d "$GIT_ROOT/.claude/hooks/scripts" ]]; then
    REPO_ROOT="$GIT_ROOT"
  fi
fi

TARGET="$REPO_ROOT/.claude/hooks/scripts/$HOOK_SCRIPT"
if [[ ! -f "$TARGET" ]]; then
  warn "missing hook script: $TARGET"
  exit 0
fi

exec /bin/bash "$TARGET" "$@"
