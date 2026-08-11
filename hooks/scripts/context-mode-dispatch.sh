#!/usr/bin/env bash
set -euo pipefail

warn() {
  printf 'WARN context-mode-dispatch: %s\n' "$*" >&2
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd -P)"
DEFAULT_CONTEXT_MODE_DIR="$REPO_ROOT/.claude/.cache/context-mode"
PINNED_CONTEXT_MODE_VERSION="1.0.169"
FILTER_CONTRACT="ctx-index-file-content-v1"
FILTER_SCRIPT="$SCRIPT_DIR/context-mode-mcp-filter.mjs"

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

canonical_storage_path() {
  local candidate="$1" parent suffix="" next_parent
  case "/$candidate/" in
    */../*) return 1 ;;
  esac
  parent="$candidate"
  while [[ ! -e "$parent" ]]; do
    suffix="/$(basename "$parent")$suffix"
    next_parent="$(dirname "$parent")"
    if [[ "$next_parent" == "$parent" ]]; then
      return 1
    fi
    parent="$next_parent"
  done
  [[ -d "$parent" ]] || return 1
  printf '%s%s' "$(cd "$parent" && pwd -P)" "$suffix"
}

storage_override_is_allowed() {
  local requested="$1" canonical="$2"
  case "$requested" in
    "$REPO_ROOT"|"$REPO_ROOT/"*)
      case "$canonical" in
        "$DEFAULT_CONTEXT_MODE_DIR"|"$DEFAULT_CONTEXT_MODE_DIR/"*) ;;
        *) return 1 ;;
      esac
      ;;
  esac
  case "$canonical" in
    "$DEFAULT_CONTEXT_MODE_DIR"|"$DEFAULT_CONTEXT_MODE_DIR/"*) return 0 ;;
    "$REPO_ROOT"|"$REPO_ROOT/"*) return 1 ;;
    *) return 0 ;;
  esac
}

select_storage_root() {
  local requested="${CONTEXT_MODE_DIR:-}" canonical
  if [[ -z "$requested" ]]; then
    printf '%s' "$DEFAULT_CONTEXT_MODE_DIR"
    return 0
  fi
  if [[ "$requested" != /* ]]; then
    warn "ignoring non-absolute CONTEXT_MODE_DIR; using project-local cache"
    printf '%s' "$DEFAULT_CONTEXT_MODE_DIR"
    return 0
  fi
  if ! canonical="$(canonical_storage_path "$requested")"; then
    warn "ignoring unsafe CONTEXT_MODE_DIR; using project-local cache"
    printf '%s' "$DEFAULT_CONTEXT_MODE_DIR"
    return 0
  fi
  if ! storage_override_is_allowed "$requested" "$canonical"; then
    warn "ignoring tracked or protected in-project CONTEXT_MODE_DIR; using project-local cache"
    printf '%s' "$DEFAULT_CONTEXT_MODE_DIR"
    return 0
  fi
  printf '%s' "$canonical"
}

configure_storage() {
  CONTEXT_MODE_DIR="$(select_storage_root)"
  local provenance="$CONTEXT_MODE_DIR/.bootstrap-provenance" quarantine
  if [[ -d "$CONTEXT_MODE_DIR" ]] && ! {
    grep -Fqx "repository=$REPO_ROOT" "$provenance" 2>/dev/null \
      && grep -Fqx "context-mode=$PINNED_CONTEXT_MODE_VERSION" "$provenance" 2>/dev/null \
      && grep -Fqx "filter=$FILTER_CONTRACT" "$provenance" 2>/dev/null
  }; then
    quarantine="$CONTEXT_MODE_DIR.untrusted.$(date -u +%Y%m%dT%H%M%SZ).$$"
    if ! mv "$CONTEXT_MODE_DIR" "$quarantine"; then
      return 1
    fi
    warn "preserved unaudited Context Mode cache at $quarantine"
  fi
  if ! mkdir -p "$CONTEXT_MODE_DIR" 2>/dev/null; then
    return 1
  fi
  CONTEXT_MODE_DIR="$(cd "$CONTEXT_MODE_DIR" && pwd)"
  provenance="$CONTEXT_MODE_DIR/.bootstrap-provenance"
  if [[ ! -f "$provenance" ]]; then
    if ! printf 'repository=%s\ncontext-mode=%s\nfilter=%s\n' \
      "$REPO_ROOT" "$PINNED_CONTEXT_MODE_VERSION" "$FILTER_CONTRACT" > "$provenance"; then
      return 1
    fi
  fi
  export CONTEXT_MODE_DIR
  CONTEXT_MODE_PROJECT_ROOT="$REPO_ROOT"
  export CONTEXT_MODE_PROJECT_ROOT
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
  printf 'PASS context-mode-dispatch: required-version=%s\n' "$PINNED_CONTEXT_MODE_VERSION"
  printf 'PASS context-mode-dispatch: filter=%s\n' "$FILTER_SCRIPT"

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
    printf 'ERROR context-mode-dispatch: guarded storage/provenance unavailable\n' >&2
    exit 1
  fi
  warn "storage unavailable; skipping optional hook event"
  exit 0
fi

if ! command_path="$(resolve_context_mode)"; then
  if [[ "$MODE" == "server" ]]; then
    printf 'ERROR context-mode-dispatch: context-mode and npx are unavailable; MCP server cannot start\n' >&2
    exit 127
  fi
  warn "context-mode and npx are unavailable; skipping optional hook event: $MODE $*"
  exit 0
fi

if [[ "$MODE" == "server" ]]; then
  if [[ ! -f "$FILTER_SCRIPT" ]] || ! command -v node >/dev/null 2>&1; then
    printf 'ERROR context-mode-dispatch: MCP filter or Node runtime unavailable\n' >&2
    exit 127
  fi
  if [[ "$command_path" == "npx" ]]; then
    exec node "$FILTER_SCRIPT" -- npx -y "context-mode@$PINNED_CONTEXT_MODE_VERSION"
  fi
  exec node "$FILTER_SCRIPT" -- "$command_path"
fi

case "$MODE" in
  github-copilot) CONTEXT_MODE_TARGET="vscode-copilot" ;;
  claude-code) CONTEXT_MODE_TARGET="claude-code" ;;
  openai-codex) CONTEXT_MODE_TARGET="codex" ;;
  *) CONTEXT_MODE_TARGET="$MODE" ;;
esac

if [[ "$command_path" == "npx" ]]; then
  exec npx -y "context-mode@$PINNED_CONTEXT_MODE_VERSION" hook "$CONTEXT_MODE_TARGET" "$@"
fi
exec "$command_path" hook "$CONTEXT_MODE_TARGET" "$@"
