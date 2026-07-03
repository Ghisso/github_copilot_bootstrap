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

# Return the effective subcommand of the FIRST git invocation in a segment,
# skipping global git flags (-C <path>, -c <k=v>, --git-dir, --work-tree, ...).
# Shell operators are normalized to spaces so a value glued to an operator does
# not leak into the next command's word.
_git_first_subcommand() {
  local segment="${1//[;|&]/ }"
  local -a tokens
  read -ra tokens <<< "$segment"
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
    local seg="${after//[;|&]/ }"
    local -a tokens
    read -ra tokens <<< "$seg"
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
