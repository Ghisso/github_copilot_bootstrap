#!/usr/bin/env bash
set -euo pipefail

# Restores the root-level adapter files (CLAUDE.md, AGENTS.md, .mcp.json,
# .codex/**, .vscode/*.json, and the Copilot surface when not committed) that
# live outside .claude/ in the outer repo. state-sync.sh only checks out
# .claude/ itself, so these are carried inside .claude/bootstrap-root/ (D5 in
# plans/plan-git-state-sync.md) and copied back out to their real locations
# here, on every setup and every devcontainer post-start.
#
# Installed alongside state-sync.sh in both .claude/hooks/scripts/ and
# .devcontainer/, for the same fresh-clone bootstrap reason (see the comment
# at the top of state-sync.sh).

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
case "$SCRIPT_DIR" in
  */.claude/hooks/scripts)
    REPO_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
    ;;
  */.devcontainer)
    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
    ;;
  *)
    REPO_ROOT="$(cd "$SCRIPT_DIR" && git rev-parse --show-toplevel 2>/dev/null || true)"
    [[ -n "$REPO_ROOT" ]] || REPO_ROOT="$SCRIPT_DIR"
    ;;
esac

SOURCE_ROOT="$REPO_ROOT/.claude/bootstrap-root"
OWNERSHIP_MANIFEST="$REPO_ROOT/.claude/bootstrap-ownership.env"

if [[ ! -d "$SOURCE_ROOT" || ! -r "$OWNERSHIP_MANIFEST" ]]; then
  exit 0
fi

# shellcheck source=/dev/null
source "$OWNERSHIP_MANIFEST"

while IFS= read -r relative; do
  [[ -n "$relative" && -e "$SOURCE_ROOT/$relative" ]] || continue
  while IFS= read -r file; do
    destination="$REPO_ROOT/${file#"$SOURCE_ROOT"/}"
    mkdir -p "$(dirname "$destination")"
    cp "$file" "$destination"
  done < <(find "$SOURCE_ROOT/$relative" -type f)
done <<< "$BOOTSTRAP_ROOT_PATHS"

exit 0
