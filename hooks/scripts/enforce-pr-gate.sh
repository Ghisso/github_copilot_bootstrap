#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_lib-frontmatter.sh
. "$SCRIPT_DIR/_lib-frontmatter.sh"

REPO_ROOT="$(repo_root_from_script)"
INPUT="$(cat)"

if ! payload_parseable "$INPUT"; then
  fail_closed "unparseable tool payload"
fi

if ! is_bash_tool_payload "$INPUT"; then
  exit 0
fi

COMMAND="$(hook_command "$INPUT")"
# Same nested-ai-state exemption as enforce-commit-gate.sh, for state-sync.sh's
# `git -C .claude push`. See the comment there for why this checks the
# specific push invocation rather than the whole command string.
if git_targets_nested_claude "$COMMAND" push; then
  exit 0
fi
if ! is_gh_pr_create_command "$COMMAND" && ! is_git_push_command "$COMMAND"; then
  exit 0
fi

CURRENT_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
if ! is_implementation_branch "$CURRENT_BRANCH"; then
  deny_pretool "PR/push gate only allows implementation branches; current branch is ${CURRENT_BRANCH:-unknown}"
  exit 0
fi

if is_gh_pr_create_command "$COMMAND"; then
  if [[ ! "$COMMAND" =~ (^|[[:space:]])--base[=\ ]dev($|[[:space:]]) ]]; then
    deny_pretool "PRs from implementation branches must be created with --base dev"
    exit 0
  fi
fi

failures=()
assert_push_invariants "$REPO_ROOT" "$CURRENT_BRANCH" "HEAD"

if [[ "${#failures[@]}" -gt 0 ]]; then
  reason="$(printf '%s; ' "${failures[@]}")"
  deny_pretool "${reason%; }"
  exit 0
fi

exit 0
