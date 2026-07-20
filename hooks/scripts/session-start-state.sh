#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_lib-frontmatter.sh
. "$SCRIPT_DIR/_lib-frontmatter.sh"

REPO_ROOT="$(repo_root_from_script)"
INPUT="$(cat >/dev/null || true)"

CURRENT_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
if ! is_implementation_branch "$CURRENT_BRANCH"; then
  exit 0
fi

SLUG="${CURRENT_BRANCH%_implementation}"
BIG_PLAN="$REPO_ROOT/.claude/plans/$SLUG.md"
[[ -f "$BIG_PLAN" ]] || exit 0

done_count=0
pending_count=0
# macOS's default /bin/bash is 3.2 and has no `mapfile`/`readarray`; accumulate
# with a `while read` loop instead (mirrors _lib-frontmatter.sh).
phases=()
_phase_line=""
while IFS= read -r _phase_line; do
  [[ -n "$_phase_line" ]] && phases+=("$_phase_line")
done < <(fm_read_list "$BIG_PLAN" "phases")
for phase in ${phases[@]+"${phases[@]}"}; do
  small_plan="$REPO_ROOT/.claude/plans/$phase.md"
  status="$(fm_read "$small_plan" "status" 2>/dev/null || true)"
  if [[ "$status" == "complete" ]]; then
    done_count=$((done_count + 1))
  else
    pending_count=$((pending_count + 1))
  fi
done

current_phase="$(fm_read "$BIG_PLAN" "current_phase" || true)"
last_score=""
score_file="$(find "$REPO_ROOT/.claude/quality_reports" -maxdepth 1 -name 'score-*.json' -type f 2>/dev/null | sort -r | sed -n '1p')"
if [[ -n "$score_file" ]]; then
  last_score="$(json_file_number_value "$score_file" "score" 2>/dev/null || true)"
fi

message="Implementation branch $CURRENT_BRANCH: big plan $SLUG, phases done=$done_count pending=$pending_count, current_phase=${current_phase:-none}"
if [[ -n "$last_score" ]]; then
  message="$message, last_score=$last_score"
fi

if git -C "$REPO_ROOT" rev-parse --verify origin/dev >/dev/null 2>&1; then
  if git -C "$REPO_ROOT" branch -r --merged origin/dev | grep -Eq "origin/${CURRENT_BRANCH}$"; then
    message="$message. Branch appears merged upstream; consider git checkout dev && git pull."
  fi
fi

additional_context "SessionStart" "$message"
exit 0
