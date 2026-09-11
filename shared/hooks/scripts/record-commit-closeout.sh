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
HEAD_SHA="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || true)"
RECORDED_COMMITS="$REPO_ROOT/.claude/session_logs/hooks-commit-closeout.log"

skip() {
  printf 'skipped\n'
  exit 0
}

fail() {
  printf 'error: %s\n' "$1" >&2
  exit 1
}

frontmatter_key_count() {
  local file="$1"
  local key="$2"
  awk -v key="$key" '
    NR == 1 && $0 == "---" { in_frontmatter = 1; next }
    in_frontmatter && $0 == "---" { print count; closed = 1; exit }
    in_frontmatter && $0 ~ "^" key "[[:space:]]*:" { count++ }
    END { if (!closed) print count }
  ' "$file"
}

# A merge can close several histories at once. Do not infer a normal phase
# transition from it; the commit gate only authorizes ordinary phase commits.
if [[ "$(printf '%s\n' "$PARENTS" | awk '{print NF}')" -gt 2 ]]; then
  skip
fi

if commit_bypass_eligible "$REPO_ROOT" "$SUBJECT" ""; then
  mkdir -p "$REPO_ROOT/.claude/session_logs"
  printf '%s,branch=%s,subject=%s,target=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$CURRENT_BRANCH" "$SUBJECT" "$TARGET_ID" >> "$REPO_ROOT/.claude/session_logs/hooks-bypass.log"
  skip
fi

if ! is_implementation_branch "$CURRENT_BRANCH"; then
  skip
fi

if [[ -n "$HEAD_SHA" && -f "$RECORDED_COMMITS" ]] && grep -Fqx "$HEAD_SHA" "$RECORDED_COMMITS"; then
  skip
fi

SLUG="${CURRENT_BRANCH%_implementation}"
BIG_PLAN="$REPO_ROOT/.claude/plans/$SLUG.md"
[[ -f "$BIG_PLAN" ]] || fail "missing big plan: .claude/plans/$SLUG.md"

BIG_STATUS="$(fm_read_unique_status "$BIG_PLAN" || true)"
[[ "$BIG_STATUS" != "$DUPLICATE_STATUS_VALUE" ]] || fail "big plan has duplicate status metadata"
case "$BIG_STATUS" in
  in-progress) ;;
  planning|complete|cancelled) skip ;;
  '') fail "big plan has missing status metadata" ;;
  *) fail "big plan has invalid status metadata: $BIG_STATUS" ;;
esac

CURRENT_PHASE_COUNT="$(frontmatter_key_count "$BIG_PLAN" "current_phase")"
[[ "$CURRENT_PHASE_COUNT" == "1" ]] || fail "big plan has duplicate or missing current_phase metadata"
CURRENT_PHASE="$(fm_read "$BIG_PLAN" "current_phase" || true)"
[[ -n "$CURRENT_PHASE" ]] || fail "big plan has missing current_phase metadata"
is_plan_slug "$CURRENT_PHASE" || fail "big plan has invalid current_phase metadata: $CURRENT_PHASE"

PHASES_COUNT="$(frontmatter_key_count "$BIG_PLAN" "phases")"
[[ "$PHASES_COUNT" == "1" ]] || fail "big plan has duplicate or missing phases metadata"

CURRENT_PLAN="$REPO_ROOT/.claude/plans/$CURRENT_PHASE.md"
[[ -f "$CURRENT_PLAN" ]] || fail "missing current phase plan: .claude/plans/$CURRENT_PHASE.md"
CURRENT_STATUS="$(fm_read_unique_status "$CURRENT_PLAN" || true)"
[[ "$CURRENT_STATUS" != "$DUPLICATE_STATUS_VALUE" ]] || fail "current phase has duplicate status metadata"
case "$CURRENT_STATUS" in
  complete) ;;
  in-progress|paused|cancelled) skip ;;
  '') fail "current phase has missing status metadata" ;;
  *) fail "current phase has invalid status metadata: $CURRENT_STATUS" ;;
esac

# macOS's default /bin/bash is 3.2 and has no `mapfile`/`readarray`; accumulate
# with a `while read` loop instead (mirrors _lib-frontmatter.sh).
phases=()
_phase_line=""
while IFS= read -r _phase_line; do
  [[ -n "$_phase_line" ]] && phases+=("$_phase_line")
done < <(fm_read_list "$BIG_PLAN" "phases")
[[ "${#phases[@]}" -gt 0 ]] || fail "big plan has malformed phases metadata"
next_phase=""
found=0
after_current=0
for index in ${phases[@]+"${!phases[@]}"}; do
  candidate_phase="${phases[$index]}"
  is_plan_slug "$candidate_phase" || fail "big plan has invalid phase metadata: $candidate_phase"
  for prior_index in ${phases[@]+"${!phases[@]}"}; do
    [[ "$prior_index" -lt "$index" ]] || continue
    [[ "${phases[$prior_index]}" != "$candidate_phase" ]] || fail "big plan has duplicate phase metadata: $candidate_phase"
  done
  if [[ "$after_current" -eq 0 && "${phases[$index]}" == "$CURRENT_PHASE" ]]; then
    found=1
    after_current=1
    continue
  fi
  if [[ "$after_current" -eq 1 ]]; then
    candidate_phase="${phases[$index]}"
    candidate_plan="$REPO_ROOT/.claude/plans/$candidate_phase.md"
    if [[ ! -f "$candidate_plan" ]]; then
      fail "missing declared phase plan: .claude/plans/$candidate_phase.md"
    fi
    candidate_status="$(fm_read_unique_status "$candidate_plan" || true)"
    [[ "$candidate_status" != "$DUPLICATE_STATUS_VALUE" ]] || fail "declared phase has duplicate status metadata: $candidate_phase"
    case "$candidate_status" in
      in-progress|planned|paused|complete|cancelled) ;;
      '') fail "declared phase has missing status metadata: $candidate_phase" ;;
      *) fail "declared phase has invalid status metadata: $candidate_phase" ;;
    esac
    if [[ "$candidate_status" == "planned" ]]; then
      # Activate the candidate before pointing current_phase at it: if the
      # current_phase rewrite below fails partway, a retry finds the phase
      # already in-progress and only needs to retry the pointer update.
      fm_write "$candidate_plan" "status" "in-progress" || fail "could not activate declared phase: $candidate_phase"
      next_phase="$candidate_phase"
      break
    elif [[ "$candidate_status" == "in-progress" ]]; then
      next_phase="$candidate_phase"
      break
    elif [[ "$candidate_status" != "cancelled" ]]; then
      printf 'warning: declared phase %s has status %s and was not activated; leaving current_phase unadvanced\n' "$candidate_phase" "$candidate_status" >&2
      skip
    fi
  fi
done

[[ "$found" -eq 1 ]] || fail "current_phase is not listed in phases metadata"

tmp="$(mktemp "${BIG_PLAN}.XXXXXX")" || exit 1
awk -v next_phase="$next_phase" '
  NR == 1 && $0 == "---" { in_frontmatter = 1 }
  in_frontmatter && $0 ~ "^current_phase[[:space:]]*:" {
    print "current_phase: " next_phase
    wrote_phase = 1
    next
  }
  in_frontmatter && next_phase == "" && $0 ~ "^status[[:space:]]*:" {
    print "status: complete"
    wrote_status = 1
    next
  }
  { print }
  in_frontmatter && $0 == "---" && NR != 1 { in_frontmatter = 0 }
  END {
    if (!wrote_phase || (next_phase == "" && !wrote_status)) exit 1
  }
' "$BIG_PLAN" > "$tmp" || { rm -f "$tmp"; exit 1; }
mv "$tmp" "$BIG_PLAN" || { rm -f "$tmp"; exit 1; }

mkdir -p "$REPO_ROOT/.claude/session_logs" || exit 1
printf '%s\n' "$HEAD_SHA" >> "$RECORDED_COMMITS" || exit 1

printf 'recorded\n'
