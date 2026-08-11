#!/usr/bin/env bash
set -euo pipefail

warn() {
  printf 'WARN context-mode-dispatch: %s\n' "$*" >&2
}

fail() {
  printf 'ERROR context-mode-dispatch: %s\n' "$*" >&2
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
DEFAULT_CONTEXT_MODE_DIR="$REPO_ROOT/.claude/.cache/context-mode"

resolve_context_mode() {
  if command -v context-mode >/dev/null 2>&1; then
    printf 'context-mode'
    return 0
  fi
  if command -v npx >/dev/null 2>&1; then
    printf 'npx'
    return 0
  fi
  return 1
}

configure_storage() {
  local requested="${CONTEXT_MODE_DIR:-}"
  if [[ -n "$requested" && "$requested" != /* ]]; then
    warn "ignoring non-absolute CONTEXT_MODE_DIR; using project-local cache"
    requested=""
  fi
  CONTEXT_MODE_DIR="${requested:-$DEFAULT_CONTEXT_MODE_DIR}"
  if ! mkdir -p "$CONTEXT_MODE_DIR" 2>/dev/null; then
    return 1
  fi
  CONTEXT_MODE_DIR="$(cd "$CONTEXT_MODE_DIR" && pwd)"
  export CONTEXT_MODE_DIR
}

select_storage_root() {
  local requested="${CONTEXT_MODE_DIR:-}"
  if [[ -n "$requested" && "$requested" != /* ]]; then
    warn "ignoring non-absolute CONTEXT_MODE_DIR; using project-local cache"
    requested=""
  fi
  printf '%s' "${requested:-$DEFAULT_CONTEXT_MODE_DIR}"
}

probe_storage() {
  local storage_root parent next_parent
  storage_root="$(select_storage_root)"
  printf 'PASS context-mode-dispatch: storage-root=%s\n' "$storage_root"
  if [[ -d "$storage_root" ]]; then
    if [[ -w "$storage_root" ]]; then
      printf 'PASS context-mode-dispatch: storage=writable\n'
      return 0
    fi
    return 1
  fi

  parent="$storage_root"
  while [[ ! -e "$parent" ]]; do
    next_parent="$(dirname "$parent")"
    if [[ "$next_parent" == "$parent" ]]; then
      return 1
    fi
    parent="$next_parent"
  done
  if [[ -d "$parent" && -w "$parent" ]]; then
    printf 'PASS context-mode-dispatch: storage=creatable\n'
    return 0
  fi
  return 1
}

self_check() {
  local command_path=""
  if command_path="$(resolve_context_mode)"; then
    if [[ "$command_path" == "npx" ]]; then
      warn "context-mode not found on PATH; npx fallback is available"
    else
      printf 'PASS context-mode-dispatch: launcher=%s\n' "$command_path"
    fi
  else
    warn "context-mode and npx are unavailable; hook events will be skipped"
  fi

  probe_storage \
    || warn "storage root is not writable or creatable: $(select_storage_root)"

  if [[ -d "$REPO_ROOT/.claude/.git" ]]; then
    if git -C "$REPO_ROOT/.claude" check-ignore -q .cache/context-mode 2>/dev/null; then
      printf 'PASS context-mode-dispatch: nested-ignore=.cache/\n'
    else
      warn "nested .claude repository does not ignore .cache/; run state-sync setup/checkpoint"
    fi
  else
    printf 'PASS context-mode-dispatch: nested-ignore=not-initialized\n'
  fi
}

if [[ "${1:-}" == "--self-check" ]]; then
  self_check
  exit 0
fi

MODE="${1:-}"
shift || true

if ! configure_storage; then
  if [[ "$MODE" == "server" ]]; then
    fail "storage root is not writable or creatable: ${CONTEXT_MODE_DIR:-$DEFAULT_CONTEXT_MODE_DIR}"
    exit 1
  fi
  warn "storage unavailable; skipping optional hook event"
  exit 0
fi

if ! command_path="$(resolve_context_mode)"; then
  if [[ "$MODE" == "server" ]]; then
    fail "context-mode and npx are unavailable; MCP server cannot start"
    exit 127
  fi
  warn "context-mode and npx are unavailable; skipping optional hook event: $MODE $*"
  exit 0
fi

if [[ "$MODE" == "server" ]]; then
  if [[ "$command_path" == "npx" ]]; then
    exec npx -y context-mode
  fi
  exec "$command_path"
fi

case "$MODE" in
  github-copilot) CONTEXT_MODE_TARGET="vscode-copilot" ;;
  claude-code) CONTEXT_MODE_TARGET="claude-code" ;;
  openai-codex) CONTEXT_MODE_TARGET="openai-codex" ;;
  *) CONTEXT_MODE_TARGET="$MODE" ;;
esac

if [[ "$command_path" == "npx" ]]; then
  exec npx -y context-mode hook "$CONTEXT_MODE_TARGET" "$@"
fi
exec "$command_path" hook "$CONTEXT_MODE_TARGET" "$@"
