#!/usr/bin/env bash

if ! command -v awk >/dev/null 2>&1; then
  printf 'ERROR _lib-frontmatter: awk is required for workflow gates\n' >&2
  return 127 2>/dev/null || exit 127
fi

json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

# Single home for the implementation-branch shape used by every lifecycle gate.
is_implementation_branch() {
  [[ "$1" =~ ^[a-zA-Z0-9._-]+_implementation$ ]]
}

# Single home for the uv guard / python runner shared by the optional-python paths.
uv_available() {
  command -v uv >/dev/null 2>&1
}

run_python() {
  if uv_available; then
    UV_CACHE_DIR="${UV_CACHE_DIR:-${TMPDIR:-/tmp}/uv-cache}" uv run python "$@"
    return $?
  fi
  return 127
}

deny_pretool() {
  local reason
  reason="$(json_escape "$1")"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$reason"
}

ask_pretool() {
  local reason
  reason="$(json_escape "$1")"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"ask","permissionDecisionReason":"%s"}}\n' "$reason"
}

# True if the payload is empty (some events send nothing) or valid JSON. A
# present-but-unparseable payload means the gate cannot reason about the tool
# call and must fail closed rather than silently allow.
payload_parseable() {
  local input="$1"
  if [[ -z "${input//[[:space:]]/}" ]]; then
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    if printf '%s' "$input" | python3 -c 'import json,sys; json.load(sys.stdin)' >/dev/null 2>&1; then
      return 0
    fi
    return 1
  fi
  # Fallback heuristic when python3 is unavailable: a JSON object/array only.
  local trimmed="${input#"${input%%[![:space:]]*}"}"
  case "$trimmed" in
    \{*|\[*) return 0 ;;
    *) return 1 ;;
  esac
}

# Fail closed: emit a deny decision and exit non-zero (2) so runtimes that key
# blocking on exit status (Copilot: any non-zero = deny; Codex/Claude: exit 2 =
# block) refuse the tool call instead of allowing it on a silent internal error.
fail_closed() {
  local message="$1"
  if [[ -n "${REPO_ROOT:-}" && -d "${REPO_ROOT:-/nonexistent}" ]]; then
    mkdir -p "$REPO_ROOT/.claude/session_logs" 2>/dev/null || true
    printf '%s WARN hook fail-closed: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$message" \
      >> "$REPO_ROOT/.claude/session_logs/hooks-errors.log" 2>/dev/null || true
  fi
  deny_pretool "hook could not evaluate the request safely, denying: $message"
  exit 2
}

# Print a file's modification time as a Unix epoch, portably across GNU coreutils
# (stat -c), BSD/macOS (stat -f), and any POSIX system with python3. Returns
# non-zero (and prints nothing) when the mtime cannot be read, so callers can
# warn instead of silently treating an unreadable mtime as 0.
file_mtime() {
  local f="$1" m
  [[ -e "$f" ]] || return 1
  if m="$(stat -c %Y "$f" 2>/dev/null)" && [[ "$m" =~ ^[0-9]+$ ]]; then printf '%s' "$m"; return 0; fi
  if m="$(stat -f %m "$f" 2>/dev/null)" && [[ "$m" =~ ^[0-9]+$ ]]; then printf '%s' "$m"; return 0; fi
  if command -v python3 >/dev/null 2>&1; then
    if m="$(python3 -c 'import os,sys; print(int(os.path.getmtime(sys.argv[1])))' "$f" 2>/dev/null)" && [[ "$m" =~ ^[0-9]+$ ]]; then
      printf '%s' "$m"; return 0
    fi
  fi
  return 1
}

additional_context() {
  local event message
  event="$(json_escape "$1")"
  message="$(json_escape "$2")"
  printf '{"hookSpecificOutput":{"hookEventName":"%s","additionalContext":"%s"}}\n' "$event" "$message"
}

json_string_value() {
  local key="$1"
  awk -v key="$key" '
    {
      text = text $0 "\n"
    }
    END {
      pattern = "\"" key "\"[[:space:]]*:[[:space:]]*\""
      if (!match(text, pattern)) {
        exit
      }
      i = RSTART + RLENGTH
      out = ""
      escaped = 0
      for (; i <= length(text); i++) {
        c = substr(text, i, 1)
        if (escaped) {
          if (c == "n") {
            out = out "\n"
          } else if (c == "t") {
            out = out "\t"
          } else {
            out = out c
          }
          escaped = 0
          continue
        }
        if (c == "\\") {
          escaped = 1
          continue
        }
        if (c == "\"") {
          print out
          exit
        }
        out = out c
      }
    }
  '
}

hook_tool_name_any() {
  local payload="$1"
  local value
  value="$(printf '%s' "$payload" | json_string_value "tool_name")"
  if [[ -z "$value" ]]; then
    value="$(printf '%s' "$payload" | json_string_value "toolName")"
  fi
  printf '%s' "$value"
}

hook_command() {
  local payload="$1"
  printf '%s' "$payload" | json_string_value "command"
}

json_file_string_value() {
  local file="$1"
  local key="$2"
  [[ -f "$file" ]] || return 1
  json_string_value "$key" < "$file"
}

json_file_number_value() {
  local file="$1"
  local key="$2"
  [[ -f "$file" ]] || return 1
  awk -v key="$key" '
    {
      text = text $0 "\n"
    }
    END {
      pattern = "\"" key "\"[[:space:]]*:[[:space:]]*-?[0-9]+"
      if (!match(text, pattern)) {
        exit
      }
      value = substr(text, RSTART, RLENGTH)
      sub("^.*:[[:space:]]*", "", value)
      sub("[^0-9-].*$", "", value)
      print value
    }
  ' "$file"
}

json_file_bool_value() {
  local file="$1"
  local key="$2"
  [[ -f "$file" ]] || return 1
  awk -v key="$key" '
    {
      text = text $0 "\n"
    }
    END {
      pattern = "\"" key "\"[[:space:]]*:[[:space:]]*(true|false)"
      if (!match(text, pattern)) {
        exit
      }
      value = substr(text, RSTART, RLENGTH)
      sub("^.*:[[:space:]]*", "", value)
      sub("[^A-Za-z].*$", "", value)
      print value
    }
  ' "$file"
}

json_file_array_present() {
  local file="$1"
  local key="$2"
  [[ -f "$file" ]] || return 1
  awk -v key="$key" '
    {
      text = text $0 "\n"
    }
    END {
      pattern = "\"" key "\"[[:space:]]*:[[:space:]]*\\["
      if (match(text, pattern)) {
        found = 1
      }
      exit found ? 0 : 1
    }
  ' "$file"
}

is_bash_tool_payload() {
  local payload="$1"
  local tool
  tool="$(hook_tool_name_any "$payload")"
  tool="${tool,,}"
  [[ -z "$tool" || "$tool" == *bash* || "$tool" == *shell* || "$tool" == "execute" ]]
}

fm_read() {
  local file="$1"
  local key="$2"
  [[ -f "$file" ]] || return 1
  awk -v key="$key" '
    NR == 1 && $0 == "---" { in_fm = 1; next }
    in_fm && $0 == "---" { exit }
    in_fm && $0 ~ "^" key "[[:space:]]*:" {
      sub("^[^:]*:[[:space:]]*", "")
      gsub(/^["'\'']|["'\'']$/, "")
      print
      exit
    }
  ' "$file"
}

fm_write() {
  local file="$1"
  local key="$2"
  local value="$3"
  local tmp
  [[ -f "$file" ]] || return 1
  tmp="$(mktemp "${file}.XXXXXX")"
  awk -v key="$key" -v value="$value" '
    NR == 1 && $0 == "---" {
      in_fm = 1
      print
      next
    }
    in_fm && $0 == "---" {
      if (!written) {
        print key ": " value
      }
      in_fm = 0
      print
      next
    }
    in_fm && $0 ~ "^" key "[[:space:]]*:" {
      print key ": " value
      written = 1
      next
    }
    { print }
  ' "$file" > "$tmp"
  mv "$tmp" "$file"
}

fm_read_list() {
  local file="$1"
  local key="$2"
  [[ -f "$file" ]] || return 1
  awk -v key="$key" '
    NR == 1 && $0 == "---" { in_fm = 1; next }
    in_fm && $0 == "---" { exit }
    in_fm && $0 ~ "^" key "[[:space:]]*:[[:space:]]*$" { capture = 1; next }
    capture && $0 ~ "^[[:space:]]*-[[:space:]]*" {
      sub("^[[:space:]]*-[[:space:]]*", "")
      print
      next
    }
    capture && $0 ~ "^[A-Za-z0-9_.-]+[[:space:]]*:" { exit }
  ' "$file"
}

# Split a command segment into tokens, honoring single/double quotes so a
# quoted value containing whitespace (e.g. `-C "some dir"`) stays ONE token and
# cannot desync flag/subcommand detection. Unquoted shell operators (; | &) are
# treated as separators. Results are returned in the global array _TOKENS; quote
# characters are stripped from the emitted tokens. Using a plain `read -ra` here
# would word-split inside quotes and re-open the flag-evasion bypass.
_shell_tokenize() {
  local s="$1" n=${#1} i=0 c q='' cur='' have=0
  _TOKENS=()
  while (( i < n )); do
    c="${s:i:1}"
    if [[ -n "$q" ]]; then
      if [[ "$c" == "$q" ]]; then q=''; else cur+="$c"; fi
      have=1
    else
      case "$c" in
        \"|\') q="$c"; have=1 ;;
        ' '|$'\t'|$'\n'|';'|'|'|'&')
          if (( have )); then _TOKENS+=("$cur"); cur=''; have=0; fi ;;
        *) cur+="$c"; have=1 ;;
      esac
    fi
    (( i++ ))
  done
  if (( have )); then _TOKENS+=("$cur"); fi
}

# Return the effective subcommand of the FIRST git invocation in a segment,
# skipping global git flags (-C <path>, -c <k=v>, --git-dir, --work-tree, ...).
_git_first_subcommand() {
  local -a tokens
  _shell_tokenize "$1"
  tokens=("${_TOKENS[@]}")
  local i=0 n="${#tokens[@]}" tok
  while (( i < n )); do
    tok="${tokens[$i]}"
    case "$tok" in
      -C|-c|--git-dir|--work-tree|--namespace|--super-prefix|--config-env|--exec-path)
        i=$((i + 2)); continue ;;
      --*=*) i=$((i + 1)); continue ;;
      -*)    i=$((i + 1)); continue ;;
      *) printf '%s' "$tok"; return 0 ;;
    esac
  done
  return 0
}

# True if any git invocation in the command uses subcommand $want. Tokenizes
# past global flags so `git -C . commit`, `git -c k=v commit`, and chained forms
# like `git status && git commit` are all detected.
git_command_has_subcommand() {
  local rest="$1" want="$2" after sub
  while [[ "$rest" =~ (^|[[:space:];|\&])git[[:space:]]+(.*) ]]; do
    after="${BASH_REMATCH[2]}"
    sub="$(_git_first_subcommand "$after")"
    if [[ "$sub" == "$want" ]]; then
      return 0
    fi
    rest="$after"
  done
  return 1
}

parse_branch_create_command() {
  local rest="$1" after
  while [[ "$rest" =~ (^|[[:space:];|\&])git[[:space:]]+(.*) ]]; do
    after="${BASH_REMATCH[2]}"
    local -a tokens
    _shell_tokenize "$after"
    tokens=("${_TOKENS[@]}")
    local i=0 n="${#tokens[@]}" tok sub="" branch=""
    while (( i < n )); do
      tok="${tokens[$i]}"
      case "$tok" in
        -C|-c|--git-dir|--work-tree|--namespace|--super-prefix|--config-env|--exec-path)
          i=$((i + 2)); continue ;;
        --*=*|-*) break ;;
        *) sub="$tok"; i=$((i + 1)); break ;;
      esac
    done
    if [[ "$sub" == "checkout" ]]; then
      while (( i < n )); do
        case "${tokens[$i]}" in
          -b|-B) branch="${tokens[$((i + 1))]:-}"; break ;;
          *) i=$((i + 1)) ;;
        esac
      done
    elif [[ "$sub" == "switch" ]]; then
      while (( i < n )); do
        case "${tokens[$i]}" in
          -c|-C|--create) branch="${tokens[$((i + 1))]:-}"; break ;;
          --create=*) branch="${tokens[$i]#--create=}"; break ;;
          *) i=$((i + 1)) ;;
        esac
      done
    fi
    if [[ -n "$branch" ]]; then
      branch="${branch%\"}"
      branch="${branch#\"}"
      branch="${branch%\'}"
      branch="${branch#\'}"
      printf '%s' "$branch"
      return 0
    fi
    rest="$after"
  done
  return 0
}

is_git_commit_command() {
  git_command_has_subcommand "$1" commit
}

is_git_push_command() {
  git_command_has_subcommand "$1" push
}

is_gh_pr_create_command() {
  local rest="$1" after seg
  while [[ "$rest" =~ (^|[[:space:];|\&])gh[[:space:]]+(.*) ]]; do
    after="${BASH_REMATCH[2]}"
    seg="${after//[;|&]/ }"
    local -a tokens
    read -ra tokens <<< "$seg"
    local i=0 n="${#tokens[@]}" tok
    local -a pos=()
    while (( i < n )); do
      tok="${tokens[$i]}"
      case "$tok" in
        -R|--repo|--hostname) i=$((i + 2)); continue ;;
        --*=*|-*) i=$((i + 1)); continue ;;
        *) pos+=("$tok"); i=$((i + 1)) ;;
      esac
      if (( ${#pos[@]} >= 2 )); then break; fi
    done
    if [[ "${pos[0]:-}" == "pr" && "${pos[1]:-}" == "create" ]]; then
      return 0
    fi
    rest="$after"
  done
  return 1
}

commit_subject_from_command() {
  local command="$1"
  local subject=""
  if [[ "$command" =~ (^|[[:space:]])-m[[:space:]]+\"([^\"]*)\" ]]; then
    subject="${BASH_REMATCH[2]}"
  elif [[ "$command" =~ (^|[[:space:]])-m[[:space:]]+\'([^\']*)\' ]]; then
    subject="${BASH_REMATCH[2]}"
  elif [[ "$command" =~ (^|[[:space:]])-m[[:space:]]+([^[:space:];|&]+) ]]; then
    subject="${BASH_REMATCH[2]}"
  elif [[ "$command" =~ (^|[[:space:]])--file[=\ ]([^[:space:];|&]+) ]]; then
    subject="$(head -n 1 "${BASH_REMATCH[2]}" 2>/dev/null || true)"
  elif [[ "$command" =~ (^|[[:space:]])-F[[:space:]]+([^[:space:];|&]+) ]]; then
    subject="$(head -n 1 "${BASH_REMATCH[2]}" 2>/dev/null || true)"
  fi
  printf '%s' "$subject"
}

is_bypass_subject() {
  case "$1" in
    fixup!*|squash!*|chore\(typo\):*|docs\(typo\):*) return 0 ;;
    *) return 1 ;;
  esac
}

repo_root_from_script() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}")" && pwd)"
  cd "$script_dir/../../.." && pwd
}

# Single home for the plan/score/closeout/LEARN ceremony shared by every commit
# gate entry point (PreToolUse and the commit-msg git hook). Branch-shape is
# deliberately NOT checked here - callers diverge on it (see D4 in
# docs/plan-deterministic-commit-gate.md) - so `branch` is assumed already
# valid (an <plan>_implementation branch) by the time this is called.
#
# Appends failure messages to a `failures` array that the CALLER must declare
# (`failures=()`) before calling; this function intentionally never `local`s
# `failures` so its `+=` mutates the caller's array via bash dynamic scoping.
assert_commit_invariants() {
  local repo_root="$1"
  local current_branch="$2"
  local slug="${current_branch%_implementation}"
  local big_plan="$repo_root/.claude/plans/$slug.md"
  if [[ ! -f "$big_plan" ]]; then
    failures+=("missing big-plan file: .claude/plans/$slug.md")
  fi

  local current_phase="" small_plan=""
  if [[ -f "$big_plan" ]]; then
    current_phase="$(fm_read "$big_plan" "current_phase" || true)"
    if [[ -z "$current_phase" ]]; then
      failures+=("big plan has no current_phase")
    else
      small_plan="$repo_root/.claude/plans/$current_phase.md"
    fi
  fi

  local small_status closeout_log=""
  if [[ -n "$small_plan" && -f "$small_plan" ]]; then
    small_status="$(fm_read "$small_plan" "status" || true)"
    if [[ "$small_status" != "complete" ]]; then
      failures+=("$small_plan must have status: complete before commit")
    fi
    closeout_log="$(fm_read "$small_plan" "closeout_session_log" || true)"
    if [[ -z "$closeout_log" ]]; then
      failures+=("$small_plan must set closeout_session_log before commit")
    else
      [[ "$closeout_log" = /* ]] || closeout_log="$repo_root/$closeout_log"
      if [[ ! -f "$closeout_log" ]]; then
        failures+=("closeout session log missing: $closeout_log")
      elif ! grep -Eq '^\*\*Status:\*\*[[:space:]]+COMPLETED\b' "$closeout_log"; then
        failures+=("closeout session log must contain exact line prefix: **Status:** COMPLETED")
      fi
    fi
  else
    failures+=("missing small-plan file: .claude/plans/${current_phase:-unknown}.md")
  fi

  local score_file="" best_generated_at=""
  if [[ -n "$current_phase" ]]; then
    # Select the newest matching report by generated_at (ISO-8601 sorts lexically
    # == chronologically), not by filename order, so a stale report cannot shadow
    # a fresh one.
    local candidate cand_branch cand_phase cand_generated_at
    while IFS= read -r candidate; do
      cand_branch="$(json_file_string_value "$candidate" "branch" 2>/dev/null || true)"
      cand_phase="$(json_file_string_value "$candidate" "phase" 2>/dev/null || true)"
      if [[ "$cand_branch" == "$current_branch" && "$cand_phase" == "$current_phase" ]]; then
        cand_generated_at="$(json_file_string_value "$candidate" "generated_at" 2>/dev/null || true)"
        if [[ -z "$best_generated_at" || "$cand_generated_at" > "$best_generated_at" ]]; then
          best_generated_at="$cand_generated_at"
          score_file="$candidate"
        fi
      fi
    done < <(find "$repo_root/.claude/quality_reports" -maxdepth 1 -name 'score-*.json' -type f 2>/dev/null)
  fi

  if [[ -z "$score_file" ]]; then
    failures+=("no matching quality report found - run uv run python .claude/scripts/quality_score.py <target> --phase ${current_phase:-current_phase} --base-ref dev --json --out .claude/quality_reports/score-<ts>.json")
  else
    local regen_hint="re-run quality_score.py: uv run python .claude/scripts/quality_score.py <target> --phase ${current_phase:-current_phase} --base-ref dev --json --out .claude/quality_reports/score-<ts>.json"
    local score
    score="$(json_file_number_value "$score_file" "score" 2>/dev/null || true)"
    if [[ ! "$score" =~ ^[0-9]+$ || "$score" -lt 90 ]]; then
      failures+=("quality score must be >= 90; found ${score:-unknown} in $score_file")
    fi

    local base_ref merge_base_sha head_sha generated_at target_path dirty tests_passed tests_skipped
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
    local current_head expected_merge_base
    current_head="$(git -C "$repo_root" rev-parse HEAD 2>/dev/null || true)"
    if [[ -z "$head_sha" || "$head_sha" != "$current_head" ]]; then
      failures+=("quality report head_sha (${head_sha:-missing}) does not match current HEAD (${current_head:-unknown}); HEAD moved since scoring - $regen_hint")
    fi
    expected_merge_base="$(git -C "$repo_root" merge-base dev HEAD 2>/dev/null || true)"
    if [[ -z "$merge_base_sha" ]]; then
      failures+=("quality report must include merge_base_sha; $regen_hint")
    elif [[ -n "$expected_merge_base" && "$merge_base_sha" != "$expected_merge_base" ]]; then
      failures+=("quality report merge_base_sha (${merge_base_sha}) must match dev...HEAD merge base (${expected_merge_base}); $regen_hint")
    fi
    if [[ ! "$generated_at" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]]; then
      failures+=("quality report generated_at must be an ISO-8601 UTC timestamp")
    fi
    if [[ -z "$target_path" ]]; then
      failures+=("quality report must include target")
    elif [[ "$target_path" = /* ]]; then
      if [[ "$target_path" != "$repo_root"* ]]; then
        failures+=("quality report target '$target_path' is outside this repo; re-run quality_score.py from within this repo")
      fi
    else
      if [[ ! -e "$repo_root/$target_path" ]]; then
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

    # Freshness by content, not mtime: recompute the same content signature the
    # scorer stamped (git hash-object of `git diff <merge-base>`). This is immune
    # to amend/rebase/editor-touch that preserve content, and detects any edit to
    # the changes after scoring - with a message that names the fix.
    local report_hash current_hash
    report_hash="$(json_file_string_value "$score_file" "content_hash" 2>/dev/null || true)"
    if [[ -z "$report_hash" ]]; then
      failures+=("quality report must include content_hash; $regen_hint")
    elif [[ -n "$expected_merge_base" ]] && command -v git >/dev/null 2>&1; then
      current_hash="$(git -C "$repo_root" diff --no-color --no-ext-diff "$expected_merge_base" 2>/dev/null | git -C "$repo_root" hash-object --stdin 2>/dev/null || true)"
      if [[ -z "$current_hash" ]]; then
        failures+=("could not compute the working-tree content hash to verify report freshness; $regen_hint")
      elif [[ "$current_hash" != "$report_hash" ]]; then
        failures+=("quality report content_hash does not match the current changes (files edited since scoring); $regen_hint")
      fi
    fi
  fi

  local learn_ok=0
  if [[ -n "${closeout_log:-}" && -f "$closeout_log" ]] && grep -Fq "[LEARN] none - no new lessons this session" "$closeout_log"; then
    learn_ok=1
  elif [[ -f "$repo_root/.claude/MEMORY.md" && -n "$small_plan" && -f "$small_plan" ]]; then
    local memory_mtime plan_mtime
    memory_mtime="$(file_mtime "$repo_root/.claude/MEMORY.md" || true)"
    plan_mtime="$(file_mtime "$small_plan" || true)"
    if [[ -n "$memory_mtime" && -n "$plan_mtime" && "$memory_mtime" -ge "$plan_mtime" ]]; then
      learn_ok=1
    fi
  fi
  if [[ "$learn_ok" -ne 1 ]]; then
    failures+=("LEARN evidence missing - update .claude/MEMORY.md or add [LEARN] none - no new lessons this session to closeout log")
  fi
}

# Single home for the push/PR ceremony shared by every push gate entry point
# (PreToolUse `enforce-pr-gate.sh` and the `pre-push` git hook). Branch-shape
# is deliberately NOT checked here, mirroring assert_commit_invariants above:
# callers diverge on it (docs/plan-post-review-hardening.md Phase 3), so
# `branch` is assumed already valid (an <plan>_implementation branch).
#
# `local_sha` is the sha being pushed for this ref, NOT necessarily HEAD -
# a caller pushing a branch it doesn't have checked out (or the pre-push
# hook, which reads ref lines from stdin) must gate the pushed commit, not
# whatever happens to be checked out. Callers pass "HEAD" when the two
# coincide (the PreToolUse gate always evaluates the agent's own HEAD).
#
# Appends failure messages to a `failures` array that the CALLER must declare
# (`failures=()`) before calling; see assert_commit_invariants for the same
# dynamic-scoping convention. The gh/PR-shape check (`--base dev`) has no
# pre-push analog and stays in the PreToolUse caller.
assert_push_invariants() {
  local repo_root="$1"
  local branch="$2"
  local local_sha="$3"
  local slug="${branch%_implementation}"
  local big_plan="$repo_root/.claude/plans/$slug.md"
  if [[ ! -f "$big_plan" ]]; then
    failures+=("missing big-plan file: .claude/plans/$slug.md")
    return
  fi

  local -a phases
  mapfile -t phases < <(fm_read_list "$big_plan" "phases")
  if [[ "${#phases[@]}" -eq 0 ]]; then
    failures+=("$big_plan has no phases list")
    return
  fi

  local phase small_plan status
  for phase in "${phases[@]}"; do
    small_plan="$repo_root/.claude/plans/$phase.md"
    if [[ ! -f "$small_plan" ]]; then
      failures+=("missing small-plan file: .claude/plans/$phase.md")
      continue
    fi
    status="$(fm_read "$small_plan" "status" || true)"
    if [[ "$status" != "complete" ]]; then
      failures+=("all small plans must be complete before PR/push; $phase is ${status:-missing-status}")
    fi
  done

  local commit_count
  commit_count="$(git -C "$repo_root" rev-list --count "dev..$local_sha" 2>/dev/null || echo 0)"
  if [[ ! "$commit_count" =~ ^[0-9]+$ || "$commit_count" -lt "${#phases[@]}" ]]; then
    failures+=("implementation branch must have at least one commit per small plan before PR/push")
  fi

  local started_at bypass_ack
  started_at="$(fm_read "$big_plan" "started_at" || true)"
  bypass_ack="$(fm_read "$big_plan" "bypass_acknowledged" || true)"
  if [[ -f "$repo_root/.claude/session_logs/hooks-bypass.log" && "$bypass_ack" != "true" ]]; then
    local line timestamp
    while IFS= read -r line; do
      timestamp="${line%%,*}"
      [[ "$line" == *"branch=$branch"* ]] || continue
      if [[ -z "$started_at" || "$timestamp" > "$started_at" ]]; then
        failures+=("this branch has logged commit-gate bypasses; add bypass_acknowledged: true to the big plan before opening a PR")
        break
      fi
    done < "$repo_root/.claude/session_logs/hooks-bypass.log"
  fi
}
