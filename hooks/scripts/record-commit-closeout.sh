#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_lib-frontmatter.sh
. "$SCRIPT_DIR/_lib-frontmatter.sh"

TARGET_ID="${1:-git-post-commit}"
REPO_ROOT="$(repo_root_from_script)"
CURRENT_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
SUBJECT="$(git -C "$REPO_ROOT" log -1 --format=%s 2>/dev/null || true)"
PARENTS="$(git -C "$REPO_ROOT" rev-list --parents -n 1 HEAD 2>/dev/null || true)"

# A merge can close several histories at once. Do not infer a normal phase
# transition from it; the commit gate only authorizes ordinary phase commits.
if [[ "$(printf '%s\n' "$PARENTS" | awk '{print NF}')" -gt 2 ]]; then
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
if [[ "$BIG_STATUS" != "in-progress" ]]; then
  exit 0
fi

CURRENT_PHASE="$(fm_read "$BIG_PLAN" "current_phase" || true)"
[[ -n "$CURRENT_PHASE" ]] || exit 0

CURRENT_PLAN="$REPO_ROOT/.claude/plans/$CURRENT_PHASE.md"
[[ -f "$CURRENT_PLAN" ]] || exit 0
CURRENT_STATUS="$(fm_read_unique_status "$CURRENT_PLAN" || true)"
[[ "$CURRENT_STATUS" == "complete" ]] || exit 0

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
      exit 0
    fi
    candidate_status="$(fm_read_unique_status "$candidate_plan" || true)"
    [[ "$candidate_status" != "$DUPLICATE_STATUS_VALUE" ]] || exit 0
    if [[ "$candidate_status" != "cancelled" ]]; then
      next_phase="$candidate_phase"
      break
    fi
  fi
done

[[ "$found" -eq 1 ]] || exit 0

if [[ -n "$next_phase" ]]; then
  fm_write "$BIG_PLAN" "current_phase" "$next_phase"
else
  fm_write "$BIG_PLAN" "current_phase" ""
  if [[ "$BIG_STATUS" != "cancelled" ]]; then
    fm_write "$BIG_PLAN" "status" "complete"
  fi
fi

exit 0
