#!/usr/bin/env bash
set -euo pipefail

warn() {
  printf 'WARNING post-start: %s\n' "$*" >&2
}

run_helper() {
  if command -v python3 >/dev/null 2>&1; then
    python3 "$@"
    return $?
  fi
  return 127
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || cd "$SCRIPT_DIR/.." && pwd)"

# Fix git object ownership — root can create files in .git during container init
# when the workspace is a bind mount, breaking subsequent git operations.
if [[ -d "$REPO_ROOT/.git" ]]; then
  sudo chown -R "$(id -u):$(id -g)" "$REPO_ROOT/.git" 2>/dev/null \
    || warn "could not fix .git ownership; git writes may fail."
fi
HELPER="$SCRIPT_DIR/hf-ai-sync.py"

if ! command -v python3 >/dev/null 2>&1; then
  warn "python3 is unavailable; skipping Hugging Face AI state sync."
  exit 0
fi

if [[ ! -f "$HELPER" ]]; then
  warn "missing sync helper at $HELPER; skipping Hugging Face AI state sync."
  exit 0
fi

run_helper "$HELPER" pull --repo-root "$REPO_ROOT" || warn "Hugging Face AI state sync failed; continuing."
