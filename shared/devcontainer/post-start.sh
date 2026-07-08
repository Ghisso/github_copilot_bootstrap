#!/usr/bin/env bash
set -euo pipefail

warn() {
  printf 'WARNING post-start: %s\n' "$*" >&2
}

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# NOT `A || cd B && pwd` on one line: || and && share precedence and
# left-associate, so that reads as (A || cd B) && pwd — pwd always runs,
# printing the invocation-time cwd on its own line below A's own output
# whenever A (git rev-parse) already succeeded, corrupting REPO_ROOT with an
# embedded newline and a bogus trailing path.
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)"
if [[ -z "$REPO_ROOT" ]]; then
  REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

# Fix git object ownership — root can create files in .git during container init
# when the workspace is a bind mount, breaking subsequent git operations.
if [[ -d "$REPO_ROOT/.git" ]]; then
  sudo chown -R "$(id -u):$(id -g)" "$REPO_ROOT/.git" 2>/dev/null \
    || warn "could not fix .git ownership; git writes may fail."
fi

STATE_SYNC="$SCRIPT_DIR/state-sync.sh"
RESTORE_ROOT_ADAPTERS="$SCRIPT_DIR/restore-root-adapters.sh"

if [[ ! -f "$STATE_SYNC" ]]; then
  warn "missing state-sync helper at $STATE_SYNC; skipping AI state sync."
  exit 0
fi

# `setup` checks out .claude/ (including .claude/hooks/git-hooks/) from the
# ai-state branch, so core.hooksPath is configured immediately after it —
# there is no window where a fresh container is ungated because nobody
# re-ran this after the checkout populated the hook directory.
bash "$STATE_SYNC" setup || warn "AI state setup failed; continuing."

if [[ -d "$REPO_ROOT/.git" ]]; then
  git -C "$REPO_ROOT" config core.hooksPath .claude/hooks/git-hooks \
    || warn "could not set core.hooksPath; the commit-msg gate will not run."
fi

bash "$STATE_SYNC" pull || warn "AI state pull failed; continuing."

if [[ -f "$RESTORE_ROOT_ADAPTERS" ]]; then
  bash "$RESTORE_ROOT_ADAPTERS" || warn "restoring root adapter files failed; continuing."
fi
