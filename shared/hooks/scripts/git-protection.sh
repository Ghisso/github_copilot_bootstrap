#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_lib-frontmatter.sh
. "$SCRIPT_DIR/_lib-frontmatter.sh"

TARGET_ID="${1:-unknown-target}"
REPO_ROOT="$(repo_root_from_script)"
INPUT="$(cat)"

# An empty/whitespace payload carries no command to inspect; allow it directly.
if [[ -z "${INPUT//[[:space:]]/}" ]]; then
  exit 0
fi

if ! payload_parseable "$INPUT"; then
  fail_closed "unparseable tool payload"
fi

log_error() {
  local log_dir="$REPO_ROOT/.claude/session_logs"
  mkdir -p "$log_dir" 2>/dev/null || true
  printf '%s WARN git-protection: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" >> "$log_dir/hooks-errors.log" 2>/dev/null || true
}

# Inspect one git invocation's tokens (operator-normalized, lowercased),
# skipping global flags to find the subcommand, then flag its destructive forms.
_git_danger_from_tokens() {
  local -a tokens=("$@")
  local i=0 n="${#tokens[@]}" tok sub=""
  while (( i < n )); do
    tok="${tokens[$i]}"
    case "$tok" in
      -C|-c|--git-dir|--work-tree|--namespace|--super-prefix|--config-env|--exec-path)
        i=$((i + 2)); continue ;;
      --*=*) i=$((i + 1)); continue ;;
      -*)    i=$((i + 1)); continue ;;
      *) sub="$tok"; i=$((i + 1)); break ;;
    esac
  done
  [[ -n "$sub" ]] || return 1
  local -a args=("${tokens[@]:$i}")
  local a cluster="" del=0
  case "$sub" in
    reset)
      for a in "${args[@]:-}"; do
        if [[ "$a" == "--hard" ]]; then printf 'git reset --hard'; return 0; fi
      done ;;
    push)
      for a in "${args[@]:-}"; do
        case "$a" in
          -f|--force|--force-with-lease) printf 'force push'; return 0 ;;
          --mirror) printf 'git push --mirror'; return 0 ;;
        esac
      done ;;
    checkout)
      for a in "${args[@]:-}"; do
        if [[ "$a" == "--" ]]; then printf 'git checkout --'; return 0; fi
      done ;;
    restore)
      for a in "${args[@]:-}"; do
        if [[ "$a" == --source* ]]; then printf 'git restore --source'; return 0; fi
      done ;;
    clean)
      for a in "${args[@]:-}"; do
        if [[ "$a" == -* && "$a" != --* ]]; then cluster="$cluster${a#-}"; fi
      done
      if [[ "$cluster" == *f* && "$cluster" == *d* ]]; then printf 'git clean -fd'; return 0; fi ;;
    branch)
      for a in "${args[@]:-}"; do
        case "$a" in
          -d|-D|--delete) del=1 ;;
          --*) ;;
          -*[dD]*) del=1 ;;
        esac
        if [[ "$del" -eq 1 && ( "$a" == "main" || "$a" == "master" ) ]]; then
          printf 'deleting main/master branch'; return 0
        fi
      done ;;
  esac
  return 1
}

# True (prints reason) if any git invocation in the command is destructive.
git_danger_reason() {
  local rest="$1" after reason
  while [[ "$rest" =~ (^|[[:space:];|\&])git[[:space:]]+(.*) ]]; do
    after="${BASH_REMATCH[2]}"
    # Quote-aware tokenizer (shared with the commit classifier) so a quoted flag
    # value with whitespace, e.g. `-C "some dir"`, cannot slip a destructive
    # subcommand past detection. Lowercase per-token for case-insensitive match.
    local -a tokens
    _shell_tokenize "$after"
    tokens=()
    local _t
    for _t in ${_TOKENS[@]+"${_TOKENS[@]}"}; do tokens+=("${_t,,}"); done
    if reason="$(_git_danger_from_tokens "${tokens[@]}")"; then
      printf '%s' "$reason"
      return 0
    fi
    rest="$after"
  done
  return 1
}

COMMAND="$(hook_command "$INPUT" 2>/dev/null || true)"
if [[ -z "$COMMAND" ]]; then
  exit 0
fi

if reason="$(git_danger_reason "$COMMAND")"; then
  deny_pretool "Blocked dangerous git operation: $reason"
fi

exit 0
