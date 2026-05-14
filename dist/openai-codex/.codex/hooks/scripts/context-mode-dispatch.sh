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

if command_path="$(resolve_context_mode)"; then
  if [[ "$command_path" == "npx" ]]; then
    exec npx -y context-mode hook "$@"
  fi
  exec "$command_path" hook "$@"
fi

warn "context-mode and npx are unavailable; skipping optional hook event: $*"
exit 0
