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

# The Copilot runtime loads both hook files, also from a subfolder, so the
# lifecycle hooks run twice there (evidence F2, A3, P4). One reached through the
# Claude settings stands down: it drains its input, prints nothing, and exits 0.
# Only these five scripts; a guard never stands down. Only when every condition
# holds: the marker that only the generated Claude settings set; COPILOT_CLI=1;
# COPILOT_HOOK_DEPTH, which the runtime sets only for hook processes (a command
# from its shell tool lacks it, P1); no COPILOT_HOOK_DIR, which only .github/hooks
# hooks get, so an inherited marker cannot stand both copies down; no CLAUDECODE;
# and a Copilot hook file that runs the same lifecycle hooks. Claude Code and the
# Local harness with chat.useClaudeHooks (A2) never match. Never key on a
# CLAUDE_CODE_* variable (A3). Never read the payload.
stands_down() {
  case "$HOOK_SCRIPT" in
    state-sync.sh | session-log.sh | session-start-state.sh | claude-stop.sh | reporting-reminder.sh) ;;
    *) return 1 ;;
  esac
  local copilot_hooks="$REPO_ROOT/.github/hooks/hooks.json"
  [[ "${BOOTSTRAP_HOOK_SOURCE:-}" == "claude-settings" ]] || return 1
  [[ "${COPILOT_CLI:-}" == "1" ]] || return 1
  [[ -n "${COPILOT_HOOK_DEPTH:-}" ]] || return 1
  [[ -z "${COPILOT_HOOK_DIR:-}" ]] || return 1
  [[ -z "${CLAUDECODE:-}" ]] || return 1
  [[ -f "$copilot_hooks" && ! -L "$copilot_hooks" ]] || return 1
  ! grep -q -F disableAllHooks "$copilot_hooks" 2>/dev/null || return 1
  grep -q -F "session-log.sh github-copilot" "$copilot_hooks" 2>/dev/null || return 1
  grep -q -F "state-sync.sh push" "$copilot_hooks" 2>/dev/null || return 1
}

if stands_down; then
  cat >/dev/null 2>&1 || true
  exit 0
fi

exec /bin/bash "$TARGET" "$@"
