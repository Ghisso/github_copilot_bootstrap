#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_lib-frontmatter.sh
. "$SCRIPT_DIR/_lib-frontmatter.sh"

TARGET_ID="${1:-unknown-target}"
REPO_ROOT="$(repo_root_from_script)"
INPUT="$(cat)"

if ! payload_parseable "$INPUT"; then
  fail_closed "unparseable tool payload"
fi

if ! is_bash_tool_payload "$INPUT"; then
  exit 0
fi

COMMAND="$(hook_command "$INPUT")"
BRANCH="$(parse_branch_create_command "$COMMAND")"
if [[ -z "$BRANCH" ]]; then
  exit 0
fi

if ! command -v git >/dev/null 2>&1; then
  deny_pretool "git is required to enforce branch lifecycle for $TARGET_ID"
  exit 0
fi

if [[ ! "$BRANCH" =~ ^[a-zA-Z0-9._-]+_implementation$ ]]; then
  deny_pretool "implementation branch must be named <plan_name>_implementation using only letters, numbers, dot, underscore, and dash"
  exit 0
fi

if ! git check-ref-format --branch "$BRANCH" >/dev/null 2>&1; then
  deny_pretool "invalid git branch name: $BRANCH"
  exit 0
fi

CURRENT_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
if [[ "$CURRENT_BRANCH" != "dev" ]]; then
  deny_pretool "implementation branches must be created from dev; current branch is ${CURRENT_BRANCH:-unknown}"
  exit 0
fi

if [[ -n "$(git -C "$REPO_ROOT" status --porcelain 2>/dev/null || true)" ]]; then
  deny_pretool "working tree must be clean before creating an implementation branch"
  exit 0
fi

SLUG="${BRANCH%_implementation}"
BIG_PLAN="$REPO_ROOT/.claude/plans/$SLUG.md"
if [[ ! -f "$BIG_PLAN" ]]; then
  deny_pretool "missing big-plan file for branch $BRANCH: .claude/plans/$SLUG.md"
  exit 0
fi

PLAN_TYPE="$(fm_read "$BIG_PLAN" "type" || true)"
STATUS="$(fm_read "$BIG_PLAN" "status" || true)"
if [[ "$PLAN_TYPE" != "big-plan" ]]; then
  deny_pretool "$BIG_PLAN must have type: big-plan frontmatter"
  exit 0
fi

if [[ "$STATUS" != "planning" && "$STATUS" != "in-progress" ]]; then
  deny_pretool "$BIG_PLAN status must be planning or in-progress before branch creation"
  exit 0
fi

exit 0
