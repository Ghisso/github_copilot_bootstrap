#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_lib-frontmatter.sh
. "$SCRIPT_DIR/_lib-frontmatter.sh"
REPO_ROOT_FOR_LOG="$(cd "$SCRIPT_DIR/../../.." && pwd)"
ERROR_LOG="$REPO_ROOT_FOR_LOG/.claude/session_logs/hooks-errors.log"

warn() {
  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%S.000Z 2>/dev/null || echo unknown-timestamp)"
  local msg="$ts hf-ai-sync: $*"
  printf 'WARN %s\n' "$msg" >&2
  mkdir -p "$(dirname "$ERROR_LOG")"
  printf '%s\n' "$msg" >> "$ERROR_LOG" 2>/dev/null || true
}

if ! uv_available; then
  warn "uv is unavailable; skipping Hugging Face AI state sync."
  exit 0
fi

# Drain hook JSON from stdin. The sync helper derives everything from git/env.
timeout 2 cat >/dev/null 2>/dev/null || true

MODE="${1:-push-state}"
REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
HELPER="$REPO_ROOT/.devcontainer/hf-ai-sync.py"

if [[ ! -f "$HELPER" ]]; then
  warn "missing sync helper at $HELPER; skipping Hugging Face AI state sync."
  exit 0
fi

SYNC_OUT="$(run_python "$HELPER" "$MODE" --repo-root "$REPO_ROOT" 2>&1)" \
  && printf '%s\n' "$SYNC_OUT" >&2 \
  || { warn "Hugging Face AI state sync ($MODE) failed: $SYNC_OUT"; }
printf '{}\n'
exit 0
