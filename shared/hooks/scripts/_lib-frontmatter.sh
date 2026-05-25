#!/usr/bin/env bash

if ! command -v awk >/dev/null 2>&1; then
  printf 'ERROR _lib-frontmatter: awk is required for workflow gates\n' >&2
  return 127 2>/dev/null || exit 127
fi

json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

deny_pretool() {
  local reason
  reason="$(json_escape "$1")"
  printf '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"%s"}}\n' "$reason"
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

hook_tool_name() {
  printf '%s' "$1" | json_string_value "tool_name"
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

fm_has() {
  local file="$1"
  local key="$2"
  [[ -n "$(fm_read "$file" "$key")" ]]
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

parse_branch_create_command() {
  local command="$1"
  local branch=""
  if [[ "$command" =~ (^|[[:space:];|&])git[[:space:]]+checkout[[:space:]]+(-b|-B)[[:space:]]+([^[:space:];|&]+) ]]; then
    branch="${BASH_REMATCH[3]}"
  elif [[ "$command" =~ (^|[[:space:];|&])git[[:space:]]+switch[[:space:]]+(-c|-C|--create)[[:space:]]+([^[:space:];|&]+) ]]; then
    branch="${BASH_REMATCH[3]}"
  elif [[ "$command" =~ (^|[[:space:];|&])git[[:space:]]+switch[[:space:]]+--create=([^[:space:];|&]+) ]]; then
    branch="${BASH_REMATCH[2]}"
  fi
  branch="${branch%\"}"
  branch="${branch#\"}"
  branch="${branch%\'}"
  branch="${branch#\'}"
  printf '%s' "$branch"
}

is_git_commit_command() {
  [[ "$1" =~ (^|[[:space:];|&])git[[:space:]]+commit($|[[:space:]]) ]]
}

is_git_push_command() {
  [[ "$1" =~ (^|[[:space:];|&])git[[:space:]]+push($|[[:space:]]) ]]
}

is_gh_pr_create_command() {
  [[ "$1" =~ (^|[[:space:];|&])gh[[:space:]]+pr[[:space:]]+create($|[[:space:]]) ]]
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
