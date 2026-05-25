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
if ! is_gh_pr_create_command "$COMMAND" && ! is_git_push_command "$COMMAND"; then
  exit 0
fi

CURRENT_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
if [[ ! "$CURRENT_BRANCH" =~ ^[a-zA-Z0-9._-]+_implementation$ ]]; then
  deny_pretool "PR/push gate only allows implementation branches; current branch is ${CURRENT_BRANCH:-unknown}"
  exit 0
fi

if is_gh_pr_create_command "$COMMAND"; then
  if [[ ! "$COMMAND" =~ (^|[[:space:]])--base[=\ ]dev($|[[:space:]]) ]]; then
    deny_pretool "PRs from implementation branches must be created with --base dev"
    exit 0
  fi
fi

SLUG="${CURRENT_BRANCH%_implementation}"
BIG_PLAN="$REPO_ROOT/.claude/plans/$SLUG.md"
if [[ ! -f "$BIG_PLAN" ]]; then
  deny_pretool "missing big-plan file: .claude/plans/$SLUG.md"
  exit 0
fi

mapfile -t phases < <(fm_read_list "$BIG_PLAN" "phases")
if [[ "${#phases[@]}" -eq 0 ]]; then
  deny_pretool "$BIG_PLAN has no phases list"
  exit 0
fi

for phase in "${phases[@]}"; do
  small_plan="$REPO_ROOT/.claude/plans/$phase.md"
  if [[ ! -f "$small_plan" ]]; then
    deny_pretool "missing small-plan file: .claude/plans/$phase.md"
    exit 0
  fi
  status="$(fm_read "$small_plan" "status" || true)"
  if [[ "$status" != "complete" ]]; then
    deny_pretool "all small plans must be complete before PR/push; $phase is ${status:-missing-status}"
    exit 0
  fi
done

commit_count="$(git -C "$REPO_ROOT" rev-list --count dev..HEAD 2>/dev/null || echo 0)"
if [[ ! "$commit_count" =~ ^[0-9]+$ || "$commit_count" -lt "${#phases[@]}" ]]; then
  deny_pretool "implementation branch must have at least one commit per small plan before PR/push"
  exit 0
fi

started_at="$(fm_read "$BIG_PLAN" "started_at" || true)"
bypass_ack="$(fm_read "$BIG_PLAN" "bypass_acknowledged" || true)"
if [[ -f "$REPO_ROOT/.claude/session_logs/hooks-bypass.log" && "$bypass_ack" != "true" ]]; then
  while IFS= read -r line; do
    timestamp="${line%%,*}"
    [[ "$line" == *"branch=$CURRENT_BRANCH"* ]] || continue
    if [[ -z "$started_at" || "$timestamp" > "$started_at" ]]; then
      deny_pretool "this branch has logged commit-gate bypasses; add bypass_acknowledged: true to the big plan before opening a PR"
      exit 0
    fi
  done < "$REPO_ROOT/.claude/session_logs/hooks-bypass.log"
fi

exit 0
