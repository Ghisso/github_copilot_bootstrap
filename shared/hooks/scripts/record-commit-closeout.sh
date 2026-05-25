#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_lib-frontmatter.sh
. "$SCRIPT_DIR/_lib-frontmatter.sh"

TARGET_ID="${1:-unknown-target}"
REPO_ROOT="$(repo_root_from_script)"
INPUT="$(cat)"

if ! is_bash_tool_payload "$INPUT"; then
  exit 0
fi

COMMAND="$(hook_command "$INPUT")"
if ! is_git_commit_command "$COMMAND"; then
  exit 0
fi

SUBJECT="$(commit_subject_from_command "$COMMAND")"
CURRENT_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
if [[ -z "$SUBJECT" ]]; then
  additional_context "PostToolUse" "commit closeout not recorded because the intercepted commit subject could not be parsed"
  exit 0
fi

LATEST_SUBJECT="$(git -C "$REPO_ROOT" log -1 --format=%s 2>/dev/null || true)"
if [[ "$LATEST_SUBJECT" != "$SUBJECT" ]]; then
  additional_context "PostToolUse" "commit closeout not recorded because HEAD subject did not match intercepted command"
  exit 0
fi

if is_bypass_subject "$SUBJECT"; then
  mkdir -p "$REPO_ROOT/.claude/session_logs"
  printf '%s,branch=%s,subject=%s,target=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$CURRENT_BRANCH" "$SUBJECT" "$TARGET_ID" >> "$REPO_ROOT/.claude/session_logs/hooks-bypass.log"
  exit 0
fi

if [[ ! "$CURRENT_BRANCH" =~ ^[a-zA-Z0-9._-]+_implementation$ ]]; then
  exit 0
fi

SLUG="${CURRENT_BRANCH%_implementation}"
BIG_PLAN="$REPO_ROOT/.claude/plans/$SLUG.md"
[[ -f "$BIG_PLAN" ]] || exit 0

CURRENT_PHASE="$(fm_read "$BIG_PLAN" "current_phase" || true)"
[[ -n "$CURRENT_PHASE" ]] || exit 0

mapfile -t phases < <(fm_read_list "$BIG_PLAN" "phases")
next_phase=""
found=0
for index in "${!phases[@]}"; do
  if [[ "${phases[$index]}" == "$CURRENT_PHASE" ]]; then
    found=1
    next_index=$((index + 1))
    if [[ "$next_index" -lt "${#phases[@]}" ]]; then
      next_phase="${phases[$next_index]}"
    fi
    break
  fi
done

if [[ "$found" -ne 1 ]]; then
  additional_context "PostToolUse" "commit closeout not recorded because current_phase is not listed in phases"
  exit 0
fi

if [[ -n "$next_phase" ]]; then
  fm_write "$BIG_PLAN" "current_phase" "$next_phase"
else
  fm_write "$BIG_PLAN" "current_phase" ""
  fm_write "$BIG_PLAN" "status" "complete"
fi

exit 0
