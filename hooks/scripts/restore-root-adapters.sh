#!/usr/bin/env bash
set -euo pipefail

# Restores the root-level adapter files (CLAUDE.md, AGENTS.md, .mcp.json,
# .codex/**, `.agents/**`, .vscode/*.json, and the Copilot surface when not
# committed) that
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

fail() {
  printf '[restore-root-adapters] %s\n' "$1" >&2
  exit 1
}

canonical_path() {
  local path="$1"
  if [[ -d "$path" ]]; then
    (cd -P -- "$path" && pwd)
    return
  fi
  [[ -f "$path" ]] || return 1
  local parent base
  parent="$(cd -P -- "$(dirname -- "$path")" && pwd)" || return 1
  base="$(basename -- "$path")"
  printf '%s/%s\n' "$parent" "$base"
}

is_within() {
  local path="$1" root="$2"
  [[ "$path" == "$root" || "$path" == "$root"/* ]]
}

is_allowed_adapter_path() {
  case "$1" in
    CLAUDE.md|AGENTS.md|.mcp.json|.codex|.agents|.vscode/mcp.json|.vscode/tasks.json|.github/agents|.github/hooks|.github/instructions|.github/copilot-instructions.md)
      return 0
      ;;
    *) return 1 ;;
  esac
}

ensure_destination_parent() {
  local relative="$1" component cursor index
  local -a parts
  IFS='/' read -r -a parts <<< "$relative"
  cursor="$REPO_ROOT"
  for ((index = 0; index < ${#parts[@]} - 1; index++)); do
    component="${parts[$index]}"
    cursor="$cursor/$component"
    if [[ -L "$cursor" ]]; then
      cursor="$(canonical_path "$cursor")" || fail "cannot resolve destination parent"
      is_within "$cursor" "$REPO_ROOT" || fail "destination escapes repository root"
    elif [[ ! -e "$cursor" ]]; then
      mkdir -- "$cursor" || fail "cannot create destination parent"
    elif [[ ! -d "$cursor" ]]; then
      fail "destination parent is not a directory"
    fi
  done
}

REPO_ROOT="$(canonical_path "$REPO_ROOT")" || fail "cannot resolve repository root"
SOURCE_ROOT="$(canonical_path "$SOURCE_ROOT")" || fail "cannot resolve bootstrap root"
paths=()
while IFS= read -r line || [[ -n "$line" ]]; do
  case "$line" in
    ''|'#'*) continue ;;
    BOOTSTRAP_COMMIT_COPILOT_SURFACE=0|BOOTSTRAP_COMMIT_COPILOT_SURFACE=1)
      continue
      ;;
    BOOTSTRAP_ROOT_PATH=*)
      relative="${line#BOOTSTRAP_ROOT_PATH=}"
      [[ "$relative" =~ ^[A-Za-z0-9._/-]+$ ]] || fail "invalid manifest path"
      [[ "$relative" != /* && "$relative" != *'//' ]] || fail "invalid manifest path"
      case "/$relative/" in */./*|*/../*) fail "invalid manifest path" ;; esac
      is_allowed_adapter_path "$relative" || fail "manifest path is not an adapter"
      paths+=("$relative")
      ;;
    *) fail "invalid manifest record" ;;
  esac
done < "$OWNERSHIP_MANIFEST"

((${#paths[@]})) || fail "manifest contains no adapter paths"

for relative in "${paths[@]}"; do
  source="$SOURCE_ROOT/$relative"
  [[ -e "$source" && ! -L "$source" ]] || fail "missing or unsafe source path: $relative"
  source="$(canonical_path "$source")" || fail "cannot resolve source path: $relative"
  is_within "$source" "$SOURCE_ROOT" || fail "source path escapes bootstrap root"
  while IFS= read -r -d '' file; do
    file="$(canonical_path "$file")" || fail "cannot resolve source file"
    is_within "$file" "$SOURCE_ROOT" || fail "source file escapes bootstrap root"
    file_relative="${file#"$SOURCE_ROOT"/}"
    destination="$REPO_ROOT/$file_relative"
    ensure_destination_parent "$file_relative"
    [[ ! -L "$destination" ]] || fail "destination is a symlink"
    destination_parent="$(canonical_path "$(dirname -- "$destination")")" || fail "cannot resolve destination parent"
    is_within "$destination_parent" "$REPO_ROOT" || fail "destination escapes repository root"
    if git -C "$REPO_ROOT" ls-files --error-unmatch -- "$file_relative" >/dev/null 2>&1; then
      continue
    fi
    cp -- "$file" "$destination" || fail "cannot restore $file_relative"
  done < <(find "$source" -type f -print0)
done

exit 0
