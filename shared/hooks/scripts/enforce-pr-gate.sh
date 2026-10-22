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

# This hook guards two unrelated command shapes: pushing (git push) and
# opening a pull request (gh pr create). Work out once whether each is
# present; `detector && FLAG=1` is never used here because this file runs
# under `set -euo pipefail`, and that form would exit the whole hook (as an
# allow) the moment a detector reports false.
IS_PR=0
if is_gh_pr_create_command "$COMMAND"; then
  IS_PR=1
fi
IS_PUSH=0
if is_git_push_command "$COMMAND"; then
  IS_PUSH=1
fi

if [[ "$IS_PR" -eq 0 && "$IS_PUSH" -eq 0 ]]; then
  exit 0
fi

# Only the push shape may stand down, and only when it is the sole shape
# present: a pull request never carries a directory redirect (gh's -R names
# an owner/repo pair, not a filesystem path), so it always reaches the
# checks below. Standing down here for a command that ALSO opens a pull
# request would let that pull request skip every check below unchecked,
# which is the hole this restructure closes.
if [[ "$IS_PR" -eq 0 ]]; then
  # Same nested-ai-state exemption as enforce-commit-gate.sh, for
  # state-sync.sh's `git -C .claude push`, plus a push explicitly redirected
  # at some other repository entirely (git -C <dir> push, --git-dir,
  # --work-tree). Both check each push invocation individually and fail
  # closed on anything undeterminable, so a compound command mixing a push
  # elsewhere with a push targeting this repository still gates in full.
  PUSH_ELSEWHERE=0
  if git_targets_nested_claude "$COMMAND" push; then
    PUSH_ELSEWHERE=1
  fi
  if [[ "$PUSH_ELSEWHERE" -eq 0 ]] && git_targets_other_repository "$COMMAND" push; then
    PUSH_ELSEWHERE=1
  fi
  if [[ "$PUSH_ELSEWHERE" -eq 1 ]]; then
    exit 0
  fi
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
if is_gh_pr_create_command "$COMMAND"; then
  assert_closeout_invariants "$REPO_ROOT" "$CURRENT_BRANCH" "HEAD"
else
  assert_push_invariants "$REPO_ROOT" "$CURRENT_BRANCH" "HEAD"
fi

if [[ "${#failures[@]}" -gt 0 ]]; then
  reason="$(printf '%s; ' "${failures[@]}")"
  reason="${reason%; }"
  # A chained `git commit ... && git push` is evaluated here against the
  # pre-commit HEAD, since this hook runs before the command executes: the
  # commit that would satisfy the invariants below does not exist yet. Name
  # that ordering constraint instead of leaving the operator to guess why an
  # apparently-valid commit-then-push was refused.
  if is_git_commit_command "$COMMAND"; then
    reason="commit and push must be separate Bash commands: the push gate evaluates the current HEAD before this command's commit exists; run the commit first, then push; $reason"
  fi
  deny_pretool "$reason"
  exit 0
fi

exit 0
