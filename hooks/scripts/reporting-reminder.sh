#!/usr/bin/env bash
set -Eeu -o pipefail

warn() {
  printf 'WARN reporting-reminder: %s\n' "$*" >&2
}

fail_open() {
  warn "internal error; skipping reminder"
  exit 0
}

trap fail_open ERR

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_lib-frontmatter.sh
. "$SCRIPT_DIR/_lib-frontmatter.sh"

REMINDER="For user-facing updates, use direct language; explain internal labels and uncommon abbreviations, and avoid idioms. State what options mean in practice. Preserve exact technical text."
REPO_ROOT="$(repo_root_from_script)"
MODE="${1:-}"
PROVIDER="${2:-}"
INPUT="$(cat)"

if [[ "$PROVIDER" != "claude-code" && "$PROVIDER" != "openai-codex" ]]; then
  warn "unsupported provider: ${PROVIDER:-missing}"
  exit 0
fi
if [[ "$MODE" != "prompt" && "$MODE" != "late-report" ]]; then
  warn "unsupported mode: ${MODE:-missing}"
  exit 0
fi
if ! payload_parseable "$INPUT"; then
  warn "malformed hook input"
  exit 0
fi

if [[ "$MODE" == "prompt" ]]; then
  additional_context "UserPromptSubmit" "$REMINDER"
  exit 0
fi

if ! is_bash_tool_payload "$INPUT"; then
  exit 0
fi

COMMAND="$(hook_command "$INPUT")"
[[ -n "$COMMAND" ]] || exit 0

is_direct_shell_segment() {
  local boundary
  boundary="$(_unquoted_operator_boundary "$COMMAND")"
  [[ "$boundary" -eq "${#COMMAND}" && "$COMMAND" != *$'\n'* ]]
}

command_starts_with() {
  local command="$1"
  shift
  local -a expected=("$@")
  local index
  _shell_tokenize "$command"
  (( ${#_TOKENS[@]} >= ${#expected[@]} )) || return 1
  for index in "${!expected[@]}"; do
    [[ "${_TOKENS[$index]}" == "${expected[$index]}" ]] || return 1
  done
}

is_verify_closeout() {
  command_starts_with "$COMMAND" uv run python .claude/scripts/verify.py closeout
}

is_findings_persistence() {
  command_starts_with "$COMMAND" uv run python .claude/scripts/record_findings.py \
    && [[ " ${_TOKENS[*]} " == *" --out "* ]]
}

is_phase_completion_commit() {
  local subject branch slug big_plan current_phase current_plan status
  command_starts_with "$COMMAND" git || return 1
  is_git_commit_command "$COMMAND" || return 1
  git_targets_nested_claude "$COMMAND" commit && return 1
  subject="$(commit_subject_from_command "$COMMAND")"
  [[ -n "$subject" ]] || return 1
  is_bypass_subject "$subject" && return 1
  branch="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
  is_implementation_branch "$branch" || return 1
  slug="${branch%_implementation}"
  big_plan="$REPO_ROOT/.claude/plans/$slug.md"
  [[ -f "$big_plan" ]] || return 1
  current_phase="$(fm_read "$big_plan" "current_phase" || true)"
  [[ -n "$current_phase" ]] || return 1
  current_plan="$REPO_ROOT/.claude/plans/$current_phase.md"
  [[ -f "$current_plan" ]] || return 1
  status="$(fm_read_unique_status "$current_plan" || true)"
  [[ "$status" == "complete" ]]
}

if is_direct_shell_segment \
  && { is_verify_closeout || is_findings_persistence || is_phase_completion_commit; }; then
  additional_context "PostToolUse" "$REMINDER"
fi
