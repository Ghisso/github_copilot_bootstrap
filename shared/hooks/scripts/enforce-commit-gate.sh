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
if [[ ! "$CURRENT_BRANCH" =~ ^[a-zA-Z0-9._-]+_implementation$ ]]; then
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

SLUG="${CURRENT_BRANCH%_implementation}"
BIG_PLAN="$REPO_ROOT/.claude/plans/$SLUG.md"
if [[ ! -f "$BIG_PLAN" ]]; then
  failures+=("missing big-plan file: .claude/plans/$SLUG.md")
fi

CURRENT_PHASE=""
SMALL_PLAN=""
if [[ -f "$BIG_PLAN" ]]; then
  CURRENT_PHASE="$(fm_read "$BIG_PLAN" "current_phase" || true)"
  if [[ -z "$CURRENT_PHASE" ]]; then
    failures+=("big plan has no current_phase")
  else
    SMALL_PLAN="$REPO_ROOT/.claude/plans/$CURRENT_PHASE.md"
  fi
fi

if [[ -n "$SMALL_PLAN" && -f "$SMALL_PLAN" ]]; then
  SMALL_STATUS="$(fm_read "$SMALL_PLAN" "status" || true)"
  if [[ "$SMALL_STATUS" != "complete" ]]; then
    failures+=("$SMALL_PLAN must have status: complete before commit")
  fi
  CLOSEOUT_LOG="$(fm_read "$SMALL_PLAN" "closeout_session_log" || true)"
  if [[ -z "$CLOSEOUT_LOG" ]]; then
    failures+=("$SMALL_PLAN must set closeout_session_log before commit")
  else
    [[ "$CLOSEOUT_LOG" = /* ]] || CLOSEOUT_LOG="$REPO_ROOT/$CLOSEOUT_LOG"
    if [[ ! -f "$CLOSEOUT_LOG" ]]; then
      failures+=("closeout session log missing: $CLOSEOUT_LOG")
    elif ! grep -Eq '^\*\*Status:\*\*[[:space:]]+COMPLETED\b' "$CLOSEOUT_LOG"; then
      failures+=("closeout session log must contain exact line prefix: **Status:** COMPLETED")
    fi
  fi
else
  failures+=("missing small-plan file: .claude/plans/${CURRENT_PHASE:-unknown}.md")
fi

score_file=""
if [[ -n "$CURRENT_PHASE" ]]; then
  while IFS= read -r candidate; do
    branch="$(json_file_string_value "$candidate" "branch" 2>/dev/null || true)"
    phase="$(json_file_string_value "$candidate" "phase" 2>/dev/null || true)"
    if [[ "$branch" == "$CURRENT_BRANCH" && "$phase" == "$CURRENT_PHASE" ]]; then
      score_file="$candidate"
      break
    fi
  done < <(find "$REPO_ROOT/.claude/quality_reports" -maxdepth 1 -name 'score-*.json' -type f 2>/dev/null | sort -r)
fi

if [[ -z "$score_file" ]]; then
  failures+=("no matching quality report found - run uv run python .claude/scripts/quality_score.py <target> --phase ${CURRENT_PHASE:-current_phase} --base-ref dev --json --out .claude/quality_reports/score-<ts>.json")
else
  score="$(json_file_number_value "$score_file" "score" 2>/dev/null || true)"
  if [[ ! "$score" =~ ^[0-9]+$ || "$score" -lt 90 ]]; then
    failures+=("quality score must be >= 90; found ${score:-unknown} in $score_file")
  fi

  base_ref="$(json_file_string_value "$score_file" "base_ref" 2>/dev/null || true)"
  merge_base_sha="$(json_file_string_value "$score_file" "merge_base_sha" 2>/dev/null || true)"
  head_sha="$(json_file_string_value "$score_file" "head_sha" 2>/dev/null || true)"
  generated_at="$(json_file_string_value "$score_file" "generated_at" 2>/dev/null || true)"
  target_path="$(json_file_string_value "$score_file" "target" 2>/dev/null || true)"
  dirty="$(json_file_bool_value "$score_file" "dirty" 2>/dev/null || true)"
  tests_passed="$(json_file_bool_value "$score_file" "tests_passed" 2>/dev/null || true)"
  tests_skipped="$(json_file_bool_value "$score_file" "tests_skipped" 2>/dev/null || true)"

  if [[ "$base_ref" != "dev" ]]; then
    failures+=("quality report base_ref must be dev; found ${base_ref:-missing} in $score_file")
  fi
  current_head="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || true)"
  if [[ -z "$head_sha" || "$head_sha" != "$current_head" ]]; then
    failures+=("quality report head_sha must match current HEAD")
  fi
  expected_merge_base="$(git -C "$REPO_ROOT" merge-base dev HEAD 2>/dev/null || true)"
  if [[ -z "$merge_base_sha" ]]; then
    failures+=("quality report must include merge_base_sha")
  elif [[ -n "$expected_merge_base" && "$merge_base_sha" != "$expected_merge_base" ]]; then
    failures+=("quality report merge_base_sha must match dev...HEAD merge base")
  fi
  if [[ ! "$generated_at" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]]; then
    failures+=("quality report generated_at must be an ISO-8601 UTC timestamp")
  fi
  if [[ -z "$target_path" ]]; then
    failures+=("quality report must include target")
  elif [[ "$target_path" = /* ]]; then
    if [[ "$target_path" != "$REPO_ROOT"* ]]; then
      failures+=("quality report target '$target_path' is outside this repo; re-run quality_score.py from within this repo")
    fi
  else
    if [[ ! -e "$REPO_ROOT/$target_path" ]]; then
      failures+=("quality report target '$target_path' does not exist under repo root")
    fi
  fi
  if [[ "$dirty" != "true" && "$dirty" != "false" ]]; then
    failures+=("quality report must include dirty boolean")
  elif [[ "$dirty" == "true" ]]; then
    failures+=("working tree has unstaged changes (dirty=true); stage everything and re-run quality_score.py")
  fi
  if [[ "$tests_passed" != "true" ]]; then
    failures+=("quality report must record tests_passed: true; found ${tests_passed:-missing}")
  fi
  if [[ "$tests_skipped" == "true" ]]; then
    failures+=("tests were skipped (tests_skipped=true); run the full test suite before committing")
  fi
  if ! json_file_array_present "$score_file" "changed_files" 2>/dev/null; then
    failures+=("quality report must include changed_files array")
  fi

  report_mtime="$(file_mtime "$score_file" || true)"
  if [[ -z "$report_mtime" ]]; then
    failures+=("could not read modification time of $score_file to verify report freshness")
  else
    changed_files="$(git -C "$REPO_ROOT" diff --name-only dev...HEAD 2>/dev/null; git -C "$REPO_ROOT" diff --name-only 2>/dev/null; git -C "$REPO_ROOT" diff --cached --name-only 2>/dev/null)"
    while IFS= read -r relative; do
      [[ -n "$relative" ]] || continue
      [[ -f "$REPO_ROOT/$relative" ]] || continue
      changed_mtime="$(file_mtime "$REPO_ROOT/$relative" || true)"
      if [[ -z "$changed_mtime" ]]; then
        failures+=("could not read modification time of changed file: $relative")
        break
      fi
      if [[ "$changed_mtime" -gt "$report_mtime" ]]; then
        failures+=("quality report is older than changed file: $relative")
        break
      fi
    done <<< "$changed_files"
  fi
fi

learn_ok=0
if [[ -n "${CLOSEOUT_LOG:-}" && -f "$CLOSEOUT_LOG" ]] && grep -Fq "[LEARN] none - no new lessons this session" "$CLOSEOUT_LOG"; then
  learn_ok=1
elif [[ -f "$REPO_ROOT/.claude/MEMORY.md" && -n "$SMALL_PLAN" && -f "$SMALL_PLAN" ]]; then
  memory_mtime="$(file_mtime "$REPO_ROOT/.claude/MEMORY.md" || true)"
  plan_mtime="$(file_mtime "$SMALL_PLAN" || true)"
  if [[ -n "$memory_mtime" && -n "$plan_mtime" && "$memory_mtime" -ge "$plan_mtime" ]]; then
    learn_ok=1
  fi
fi
if [[ "$learn_ok" -ne 1 ]]; then
  failures+=("LEARN evidence missing - update .claude/MEMORY.md or add [LEARN] none - no new lessons this session to closeout log")
fi

if [[ "${#failures[@]}" -gt 0 ]]; then
  reason="$(printf '%s; ' "${failures[@]}")"
  deny_pretool "commit gate failed for $TARGET_ID: ${reason%; }"
fi

exit 0
