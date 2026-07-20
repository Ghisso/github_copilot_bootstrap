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

fm_write "$BIG_PLAN" "implementation_branch" "$BRANCH"
fm_write "$BIG_PLAN" "originating_branch" "dev"
if [[ -z "$(fm_read "$BIG_PLAN" "started_at" || true)" ]]; then
  fm_write "$BIG_PLAN" "started_at" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
fi
fm_write "$BIG_PLAN" "status" "in-progress"
fm_write "$BIG_PLAN" "current_phase" "$FIRST_PHASE"

exit 0
