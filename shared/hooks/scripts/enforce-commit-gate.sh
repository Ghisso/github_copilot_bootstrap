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
# state-sync.sh commits to the nested ai-state repo (git -C .claude commit ...)
# constantly and has no plan/score/closeout ceremony of its own to satisfy —
# without this, the outer gate misjudges those commits against this repo's
# ceremony and blocks routine state syncing. git_targets_nested_claude checks
# the specific commit invocation, not "does the command string mention
# .claude/ anywhere", so a compound command that mixes a nested call with an
# unrelated outer-repo commit still gates the outer one.
if git_targets_nested_claude "$COMMAND" commit; then
  exit 0
fi
if ! is_git_commit_command "$COMMAND"; then
  exit 0
fi

SUBJECT="$(commit_subject_from_command "$COMMAND")"
BYPASS=0
if is_bypass_subject "$SUBJECT"; then
  BYPASS=1
fi

failures=()

CURRENT_BRANCH="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
if ! is_implementation_branch "$CURRENT_BRANCH"; then
  failures+=("commits must happen on a <plan_name>_implementation branch, not ${CURRENT_BRANCH:-unknown}")
fi

# Bypass subjects (fixup!/squash!/chore(typo):/docs(typo):) skip only the
# plan-ceremony checks below (small-plan/closeout/score/LEARN); branch-shape
# validation above still applies, and the bypass is still ledgered by
# record-commit-closeout.sh. This keeps the recovery use-case without turning
# the strictest gate into a blank check.
if [[ "$BYPASS" -eq 1 ]]; then
  if [[ "${#failures[@]}" -gt 0 ]]; then
    reason="$(printf '%s; ' "${failures[@]}")"
    deny_pretool "commit gate failed for $TARGET_ID: ${reason%; }"
  fi
  exit 0
fi

assert_commit_invariants "$REPO_ROOT" "$CURRENT_BRANCH"

if [[ "${#failures[@]}" -gt 0 ]]; then
  reason="$(printf '%s; ' "${failures[@]}")"
  deny_pretool "commit gate failed for $TARGET_ID: ${reason%; }"
fi

exit 0
