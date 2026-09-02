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
  additional_context "PostToolUse" "commit closeout not recorded because the intercepted commit subject could not be parsed from the git command. Use -m or -F <file> with a readable message file, or advance the phase manually if the commit was created another way."
  exit 0
fi

LATEST_SUBJECT="$(git -C "$REPO_ROOT" log -1 --format=%s 2>/dev/null || true)"
# Tolerant correlation: shell-expanded or reflowed messages rarely byte-equal
# the parsed -m subject, so normalize whitespace and accept a word-boundary
# prefix match in either direction. On a miss, warn with a recovery command
# instead of silently stalling the phase machine.
norm_latest="$(printf '%s' "$LATEST_SUBJECT" | tr -s '[:space:]' ' ')"
norm_latest="${norm_latest# }"; norm_latest="${norm_latest% }"
norm_subject="$(printf '%s' "$SUBJECT" | tr -s '[:space:]' ' ')"
norm_subject="${norm_subject# }"; norm_subject="${norm_subject% }"
correlated=0
if [[ -n "$norm_subject" ]] && \
   { [[ "$norm_latest" == "$norm_subject" ]] || \
     [[ "$norm_latest" == "$norm_subject "* ]] || \
     [[ "$norm_subject" == "$norm_latest "* ]]; }; then
  correlated=1
fi
if [[ "$correlated" -ne 1 ]]; then
  additional_context "PostToolUse" "commit closeout not recorded: HEAD subject ('${norm_latest}') did not correlate with the intercepted commit subject ('${norm_subject}'). If this phase is complete, advance it by hand: set current_phase to the next phase (or status: complete when it was the last) in the big plan under .claude/plans/."
  exit 0
fi

if commit_bypass_eligible "$REPO_ROOT" "$SUBJECT" ""; then
  mkdir -p "$REPO_ROOT/.claude/session_logs"
  printf '%s,branch=%s,subject=%s,target=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$CURRENT_BRANCH" "$SUBJECT" "$TARGET_ID" >> "$REPO_ROOT/.claude/session_logs/hooks-bypass.log"
  exit 0
fi

if ! is_implementation_branch "$CURRENT_BRANCH"; then
  exit 0
fi

SLUG="${CURRENT_BRANCH%_implementation}"
BIG_PLAN="$REPO_ROOT/.claude/plans/$SLUG.md"
[[ -f "$BIG_PLAN" ]] || exit 0

BIG_STATUS="$(fm_read_unique_status "$BIG_PLAN" || true)"
if [[ "$BIG_STATUS" == "$DUPLICATE_STATUS_VALUE" ]]; then
  additional_context "PostToolUse" "commit closeout not recorded because the big plan must contain exactly one status field"
  exit 0
fi

CURRENT_PHASE="$(fm_read "$BIG_PLAN" "current_phase" || true)"
[[ -n "$CURRENT_PHASE" ]] || exit 0

CURRENT_PLAN="$REPO_ROOT/.claude/plans/$CURRENT_PHASE.md"
if [[ -f "$CURRENT_PLAN" ]]; then
  CURRENT_STATUS="$(fm_read_unique_status "$CURRENT_PLAN" || true)"
  if [[ "$CURRENT_STATUS" == "$DUPLICATE_STATUS_VALUE" ]]; then
    additional_context "PostToolUse" "commit closeout not recorded because the current phase plan must contain exactly one status field"
    exit 0
  fi
  if [[ "$CURRENT_STATUS" == "paused" ]]; then
    exit 0
  fi
fi

# macOS's default /bin/bash is 3.2 and has no `mapfile`/`readarray`; accumulate
# with a `while read` loop instead (mirrors _lib-frontmatter.sh).
phases=()
_phase_line=""
while IFS= read -r _phase_line; do
  [[ -n "$_phase_line" ]] && phases+=("$_phase_line")
done < <(fm_read_list "$BIG_PLAN" "phases")
next_phase=""
found=0
after_current=0
for index in ${phases[@]+"${!phases[@]}"}; do
  if [[ "$after_current" -eq 0 && "${phases[$index]}" == "$CURRENT_PHASE" ]]; then
    found=1
    after_current=1
    continue
  fi
  if [[ "$after_current" -eq 1 ]]; then
    candidate_phase="${phases[$index]}"
    candidate_plan="$REPO_ROOT/.claude/plans/$candidate_phase.md"
    if [[ ! -f "$candidate_plan" ]]; then
      additional_context "PostToolUse" "commit closeout not recorded because next phase plan is missing: .claude/plans/$candidate_phase.md"
      exit 0
    fi
    candidate_status="$(fm_read_unique_status "$candidate_plan" || true)"
    if [[ "$candidate_status" == "$DUPLICATE_STATUS_VALUE" ]]; then
      additional_context "PostToolUse" "commit closeout not recorded because the next phase plan must contain exactly one status field: .claude/plans/$candidate_phase.md"
      exit 0
    elif [[ "$candidate_status" != "cancelled" ]]; then
      next_phase="$candidate_phase"
      break
    fi
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
  if [[ "$BIG_STATUS" != "cancelled" ]]; then
    fm_write "$BIG_PLAN" "status" "complete"
  fi
fi

exit 0
