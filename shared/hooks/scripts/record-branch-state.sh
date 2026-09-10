#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_lib-frontmatter.sh
. "$SCRIPT_DIR/_lib-frontmatter.sh"

REPO_ROOT="$(repo_root_from_script)"
INPUT="$(cat)"

if ! is_bash_tool_payload "$INPUT"; then
  exit 0
fi

COMMAND="$(hook_command "$INPUT")"
BRANCH="$(parse_branch_create_command "$COMMAND")"
if [[ -z "$BRANCH" ]]; then
  exit 0
fi

CURRENT_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
if [[ "$CURRENT_BRANCH" != "$BRANCH" ]]; then
  additional_context "PostToolUse" "branch state not recorded because current branch is ${CURRENT_BRANCH:-unknown}, not $BRANCH"
  exit 0
fi

SLUG="${BRANCH%_implementation}"
BIG_PLAN="$REPO_ROOT/.claude/plans/$SLUG.md"
if [[ ! -f "$BIG_PLAN" ]]; then
  additional_context "PostToolUse" "branch state not recorded because .claude/plans/$SLUG.md is missing"
  exit 0
fi

FIRST_PHASE="$(fm_read_list "$BIG_PLAN" "phases" | sed -n '1p')"
if [[ -z "$FIRST_PHASE" ]]; then
  additional_context "PostToolUse" "branch state not recorded because $BIG_PLAN has no phases list"
  exit 0
fi
# FIRST_PHASE feeds a path below (FIRST_PLAN) as well as current_phase; an
# unsafe value (e.g. a traversal segment) must never reach either, so bail
# out before either use, matching the empty-phases-list bailout just above
# rather than writing partial/broken big-plan bookkeeping.
if ! is_plan_slug "$FIRST_PHASE"; then
  additional_context "PostToolUse" "branch state not recorded because $BIG_PLAN's first phase is not a safe slug: $FIRST_PHASE"
  exit 0
fi

# Activate exactly the first selected phase. A legacy `in-progress` first
# phase is left untouched for compatibility; any other unexpected status
# (paused, complete, duplicate, invalid, or missing) is reported instead of
# silently overwritten, and a failed activation write degrades to a report
# rather than aborting the big-plan bookkeeping below.
FIRST_PLAN="$REPO_ROOT/.claude/plans/$FIRST_PHASE.md"
if [[ -f "$FIRST_PLAN" ]]; then
  FIRST_STATUS="$(fm_read_unique_status "$FIRST_PLAN" || true)"
  if [[ "$FIRST_STATUS" == "planned" ]]; then
    if ! fm_write "$FIRST_PLAN" "status" "in-progress"; then
      additional_context "PostToolUse" "first phase $FIRST_PHASE could not be activated; its plan file was not writable"
    fi
  elif [[ "$FIRST_STATUS" == "$DUPLICATE_STATUS_VALUE" ]]; then
    additional_context "PostToolUse" "first phase $FIRST_PHASE was not activated because its plan file has duplicate status metadata"
  elif [[ "$FIRST_STATUS" != "in-progress" ]]; then
    additional_context "PostToolUse" "first phase $FIRST_PHASE was not activated because its status is ${FIRST_STATUS:-missing}, not planned or in-progress"
  fi
fi

fm_write "$BIG_PLAN" "implementation_branch" "$BRANCH"
fm_write "$BIG_PLAN" "originating_branch" "dev"
if [[ -z "$(fm_read "$BIG_PLAN" "started_at" || true)" ]]; then
  fm_write "$BIG_PLAN" "started_at" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
fi
fm_write "$BIG_PLAN" "status" "in-progress"
fm_write "$BIG_PLAN" "current_phase" "$FIRST_PHASE"

exit 0
