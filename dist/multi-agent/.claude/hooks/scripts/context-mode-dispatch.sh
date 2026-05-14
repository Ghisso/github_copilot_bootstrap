#!/usr/bin/env bash
set -euo pipefail

warn() {
  printf 'WARN context-mode-dispatch: %s\n' "$*" >&2
}

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

if [[ "${1:-}" == "--self-check" ]]; then
  if command_path="$(resolve_context_mode)"; then
    if [[ "$command_path" == "npx" ]]; then
      warn "context-mode not found on PATH; npx fallback is available"
    else
      printf 'PASS context-mode-dispatch: found %s\n' "$command_path"
    fi
  else
    warn "context-mode and npx are unavailable; hook events will be skipped"
  fi
  exit 0
fi

TARGET_ID="${1:-unknown-target}"
shift || true

case "$TARGET_ID" in
  github-copilot) CONTEXT_MODE_TARGET="vscode-copilot" ;;
  claude-code) CONTEXT_MODE_TARGET="claude-code" ;;
  openai-codex) CONTEXT_MODE_TARGET="openai-codex" ;;
  *) CONTEXT_MODE_TARGET="$TARGET_ID" ;;
esac

if command_path="$(resolve_context_mode)"; then
  if [[ "$command_path" == "npx" ]]; then
    exec npx -y context-mode hook "$CONTEXT_MODE_TARGET" "$@"
  fi
  exec "$command_path" hook "$CONTEXT_MODE_TARGET" "$@"
fi

warn "context-mode and npx are unavailable; skipping optional hook event: $CONTEXT_MODE_TARGET $*"
exit 0
