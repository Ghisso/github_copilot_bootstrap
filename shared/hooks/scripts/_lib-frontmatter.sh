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

# Lowercase a string portably. macOS ships bash 3.2, which lacks the
# ${var,,} case-conversion expansion (bash 4+), so route through tr.
hook_to_lower() {
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]'
}

json_file_string_value() {
  local file="$1"
  local key="$2"
  json_file_top_level_value "$file" "$key" string
}

json_file_number_value() {
  json_file_top_level_value "$1" "$2" number
}

json_file_bool_value() {
  json_file_top_level_value "$1" "$2" bool
}

json_file_array_present() {
  json_file_top_level_value "$1" "$2" array >/dev/null
}

# Reports are untrusted files. Read only a named top-level key (or the explicit
# `counts.<severity>` contract path) so a nested finding title or
# attacker-controlled payload cannot forge a report field by appearing earlier
# in the JSON text. Python is already the runtime baseline for this bootstrap;
# this deliberately does not depend on uv.
json_file_top_level_value() {
  local file="$1"
  local key="$2"
  local kind="$3"
  [[ -f "$file" ]] || return 1
  python3 - "$file" "$key" "$kind" <<'PY'
import json
import sys

file_name, key, kind = sys.argv[1:]
try:
    with open(file_name, encoding="utf-8") as handle:
        report = json.load(handle)
except (OSError, json.JSONDecodeError):
    raise SystemExit(1)
if not isinstance(report, dict):
    raise SystemExit(1)
if key.startswith("counts."):
    counts_key = key[len("counts."):]
    counts = report.get("counts")
    if not isinstance(counts, dict) or counts_key not in counts:
        raise SystemExit(1)
    value = counts[counts_key]
elif key in report:
    value = report[key]
else:
    raise SystemExit(1)
valid = {
    "string": isinstance(value, str),
    "number": type(value) is int,
    "bool": type(value) is bool,
    "array": isinstance(value, list),
}.get(kind, False)
if not valid:
    raise SystemExit(1)
print(str(value).lower() if type(value) is bool else value)
PY
}

is_bash_tool_payload() {
  local payload="$1"
  local tool
  tool="$(hook_tool_name_any "$payload")"
  tool="$(hook_to_lower "$tool")"
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

readonly DUPLICATE_STATUS_VALUE="__DUPLICATE_FRONTMATTER_STATUS__"

# Read status only when it occurs exactly once in frontmatter. Callers compare
# the sentinel explicitly so duplicate same-value and conflicting-value keys
# fail closed without changing fm_read semantics for any other field.
fm_read_unique_status() {
  local file="$1"
  [[ -f "$file" ]] || return 1
  awk -v duplicate_value="$DUPLICATE_STATUS_VALUE" '
    NR == 1 && $0 == "---" { in_fm = 1; next }
    in_fm && $0 == "---" {
      if (count > 1) {
        print duplicate_value
      } else if (count == 1) {
        print value
      }
      exit
    }
    in_fm && $0 ~ "^status[[:space:]]*:" {
      line = $0
      sub("^[^:]*:[[:space:]]*", "", line)
      gsub(/^["'\'']|["'\'']$/, "", line)
      value = line
      count++
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

# Index of the first unquoted shell operator (; | &) in a command segment, or
# the segment's length if there is none. Global git flags (-C, --git-dir, ...)
# always precede the subcommand within one invocation with no operator in
# between, so scanning for THOSE never needs this. Scanning an invocation's
# ARGS (after its subcommand) is different: `git push origin main && curl
# --force ...` tokenizes (via _shell_tokenize, which drops operators as mere
# separators) to a flat ["push","origin","main","curl","--force",...] with no
# trace of the "&&" — a naive "does --force appear anywhere after push" scan
# would misattribute the unrelated curl command's flag to the git push. Callers
# that scan args must truncate the segment to this boundary first so a later
# chained command's tokens can never bleed into the current invocation's scan.
_unquoted_operator_boundary() {
  local s="$1" n=${#1} i=0 c q=''
  while (( i < n )); do
    c="${s:i:1}"
    if [[ -n "$q" ]]; then
      [[ "$c" == "$q" ]] && q=''
    else
      case "$c" in
        \"|\') q="$c" ;;
        ';'|'|'|'&') printf '%s' "$i"; return 0 ;;
      esac
    fi
    (( i++ ))
  done
  printf '%s' "$n"
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

# True if the global flags of ONE git invocation (tokens starting right after
# "git ") point -C/--git-dir/--work-tree at the nested .claude/ repo. Stops at
# the first positional token (the subcommand) so it never reads flags that
# actually belong to a later chained `git ...` call in the same tokens array
# (operators are not preserved as tokens by _shell_tokenize).
_git_invocation_targets_nested_claude() {
  local -a tokens=("$@")
  local i=0 n=${#tokens[@]} tok next git_dir="" work_tree="" cpath=""
  while (( i < n )); do
    tok="${tokens[$i]}"
    case "$tok" in
      -C)
        next="${tokens[$((i + 1))]:-}"; cpath="$next"; i=$((i + 2)); continue ;;
      --git-dir)
        next="${tokens[$((i + 1))]:-}"; git_dir="$next"; i=$((i + 2)); continue ;;
      --git-dir=*)
        git_dir="${tok#--git-dir=}"; i=$((i + 1)); continue ;;
      --work-tree)
        next="${tokens[$((i + 1))]:-}"; work_tree="$next"; i=$((i + 2)); continue ;;
      --work-tree=*)
        work_tree="${tok#--work-tree=}"; i=$((i + 1)); continue ;;
      -c|--namespace|--super-prefix|--config-env|--exec-path)
        i=$((i + 2)); continue ;;
      --*=*|-*)
        i=$((i + 1)); continue ;;
      *) break ;;
    esac
  done

  case "$cpath" in
    .claude|./.claude|../.claude|*/.claude|"$REPO_ROOT"/.claude) return 0 ;;
  esac
  case "$work_tree" in
    .claude|./.claude|../.claude|*/.claude|"$REPO_ROOT"/.claude) return 0 ;;
  esac
  case "$git_dir" in
    .claude/.git|./.claude/.git|../.claude/.git|*/.claude/.git|"$REPO_ROOT"/.claude/.git) return 0 ;;
  esac
  return 1
}

# True only when the command contains at least one `git $want` invocation AND
# every invocation of that subcommand targets the nested .claude/ repo. A
# compound command mixing a nested-.claude invocation with an unrelated
# outer-repo invocation of the same subcommand (e.g.
# `git -C .claude status && git commit -m "outer"`) must NOT be exempted, so
# this checks each matching invocation individually rather than asking "does
# ANY git call anywhere in the string target .claude".
git_targets_nested_claude() {
  local rest="$1" want="$2" after sub found=0
  while [[ "$rest" =~ (^|[[:space:];|\&])git[[:space:]]+(.*) ]]; do
    after="${BASH_REMATCH[2]}"
    local -a tokens
    _shell_tokenize "$after"
    tokens=("${_TOKENS[@]}")
    sub="$(_git_first_subcommand "$after")"
    if [[ "$sub" == "$want" ]]; then
      found=1
      _git_invocation_targets_nested_claude "${tokens[@]}" || return 1
    fi
    rest="$after"
  done
  [[ "$found" -eq 1 ]]
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

# Tokenizes (honoring quotes, via _shell_tokenize) rather than regexing the
# raw string, so a quoted -m/-F value containing another flag-like substring
# can't desync parsing. -F -/--file=- means the message is piped on stdin,
# which this function has no access to (it only sees the command string) —
# that intentionally yields an empty subject rather than misreading "-" as a
# filename; callers must treat empty as "could not determine subject", not
# "empty commit message".
commit_subject_from_command() {
  local command="$1"
  local subject=""
  _shell_tokenize "$command"
  local i=0 n=${#_TOKENS[@]} tok next
  while (( i < n )); do
    tok="${_TOKENS[i]}"
    case "$tok" in
      -m|--message)
        next="${_TOKENS[i+1]:-}"
        subject="$next"
        break
        ;;
      --message=*)
        subject="${tok#--message=}"
        break
        ;;
      -F|--file)
        next="${_TOKENS[i+1]:-}"
        if [[ "$next" == "-" ]]; then
          subject=""
        else
          subject="$(head -n 1 "$next" 2>/dev/null || true)"
        fi
        break
        ;;
      --file=*)
        next="${tok#--file=}"
        if [[ "$next" == "-" ]]; then
          subject=""
        else
          subject="$(head -n 1 "$next" 2>/dev/null || true)"
        fi
        break
        ;;
    esac
    i=$((i + 1))
  done
  printf '%s' "$subject"
}

is_bypass_subject() {
  case "$1" in
    fixup!*|squash!*|chore\(typo\):*|docs\(typo\):*) return 0 ;;
    *) return 1 ;;
  esac
}

# Return success when the implementation diff has a deterministic high-risk
# Ponytail trigger. This is the hook-safe subset of the authoritative Task
# Lanes table: control-plane, scripts/generators, dependencies/lockfiles, and
# multi-file diffs. Reviewers also select Ponytail for semantic complexity
# expansion, which cannot be inferred safely from paths. A documentation-only
# exemption applies only to one documentation/state file; high-risk paths and
# multi-file diffs take precedence. With no `diff_ref`, the live working
# tree/index is checked (commit gate); with a ref, that landed commit is checked
# (push gate).
diff_requires_ponytail() {
  local repo_root="$1"
  local diff_ref="${2:-}"
  local head_ref="${diff_ref:-HEAD}"
  local merge_base path
  merge_base="$(git -C "$repo_root" merge-base dev "$head_ref" 2>/dev/null || true)"
  [[ -n "$merge_base" ]] || return 0

  local -a paths=()
  if [[ -n "$diff_ref" ]]; then
    while IFS= read -r path; do
      [[ -n "$path" ]] && paths+=("$path")
    done < <(git -C "$repo_root" diff --no-renames --name-only "$merge_base" "$diff_ref" 2>/dev/null)
  else
    while IFS= read -r path; do
      [[ -n "$path" ]] && paths+=("$path")
    done < <(git -C "$repo_root" diff --no-renames --name-only "$merge_base" 2>/dev/null)
  fi

  [[ "${#paths[@]}" -gt 1 ]] && return 0
  for path in "${paths[@]}"; do
    case "$path" in
      .claude/hooks/*|.claude/settings.json|.github/hooks/*|.codex/*|.mcp.json|.devcontainer/*|AGENTS.md|CLAUDE.md|scripts/*|shared/scripts/*|pyproject.toml|*/pyproject.toml|uv.lock|*/uv.lock|requirements*.txt|*/requirements*.txt|Pipfile|*/Pipfile|Pipfile.lock|*/Pipfile.lock|poetry.lock|*/poetry.lock|package.json|*/package.json|package-lock.json|*/package-lock.json|pnpm-lock.yaml|*/pnpm-lock.yaml|yarn.lock|*/yarn.lock|Cargo.toml|*/Cargo.toml|Cargo.lock|*/Cargo.lock|go.mod|*/go.mod|go.sum|*/go.sum) return 0 ;;
    esac
  done
  return 1
}

assert_required_ponytail_review() {
  local findings_file="$1"
  local repo_root="$2"
  local diff_ref="$3"
  local gate="$4"
  local regen_hint="$5"
  diff_requires_ponytail "$repo_root" "$diff_ref" || return 0

  local ponytail_reviewed
  ponytail_reviewed="$(json_file_bool_value "$findings_file" "ponytail_reviewed" 2>/dev/null || true)"
  if [[ "$ponytail_reviewed" != "true" ]]; then
    failures+=("this high-risk diff requires a fresh Ponytail review before $gate; $regen_hint")
  fi
}

repo_root_from_script() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}")" && pwd)"
  cd "$script_dir/../../.." && pwd
}

# Select the newest-by-generated_at report file matching `glob` under
# `reports_dir` whose `branch`/`phase` fields equal the given values.
# ISO-8601 `generated_at` sorts lexically == chronologically, so a stale
# report cannot shadow a fresh one by filename. Echoes the selected path (or
# nothing on no match). Shared by score-*.json and findings-*.json selection
# so the two report types cannot drift apart on how "freshest" is decided.
select_fresh_report() {
  local reports_dir="$1"
  local glob="$2"
  local branch="$3"
  local phase="$4"
  local best_file="" best_generated_at=""
  local candidate cand_branch cand_phase cand_generated_at
  while IFS= read -r candidate; do
    cand_branch="$(json_file_string_value "$candidate" "branch" 2>/dev/null || true)"
    cand_phase="$(json_file_string_value "$candidate" "phase" 2>/dev/null || true)"
    if [[ "$cand_branch" == "$branch" && "$cand_phase" == "$phase" ]]; then
      cand_generated_at="$(json_file_string_value "$candidate" "generated_at" 2>/dev/null || true)"
      if [[ -z "$best_generated_at" || "$cand_generated_at" > "$best_generated_at" ]]; then
        best_generated_at="$cand_generated_at"
        best_file="$candidate"
      fi
    fi
  done < <(find "$reports_dir" -maxdepth 1 -name "$glob" -type f 2>/dev/null)
  printf '%s' "$best_file"
}

# Verify the freshness fields shared by every report type the commit/push
# gates verify (score-*.json and findings-*.json, both stamped by the same
# git_metadata() helper in quality_score.py / record_findings.py): base_ref,
# head_sha vs `expected_head_sha`, merge_base_sha vs the actual
# dev...expected_head_sha merge base, generated_at format, target existence,
# dirty:false, and content_hash vs a fresh recomputation. Appends to the
# caller's `failures` array (same dynamic-scoping convention as
# assert_commit_invariants).
#
# `expected_head_sha` is caller-supplied rather than read from `git rev-parse
# HEAD` internally, because the two callers disagree on what "the commit
# this report certifies" is: the commit gate fires BEFORE the pending commit
# object exists (current HEAD is its parent; the certified content is still
# only staged), while the push gate fires AFTER the commit has already
# landed, possibly on a branch that isn't even checked out (D4-B) - there
# `expected_head_sha` is the pushed sha itself, an immutable, already-landed
# commit.
#
# `head_relation` picks how `head_sha` is compared to `expected_head_sha`:
# "exact" requires equality (the commit gate's case); "ancestor" requires
# `head_sha` to be `expected_head_sha` or one of its ancestors (the push
# gate's case). This split exists because reports are generated pre-commit
# (during REVIEW, per workflow.instructions.md) - a report's stored head_sha
# is always the PARENT of the commit it certifies, never that commit itself.
# At commit time that parent IS current HEAD (exact match is correct and
# required). At push time the branch tip is one or more commits past that
# parent, so requiring exact equality there would reject every legitimately
# fresh report; "ancestor" combined with the content_hash check below (which
# independently proves the diff content is unchanged) is the correct
# invariant - it cannot be satisfied by content that was never reviewed.
#
# `content_diff_ref` mirrors the exact/ancestor split for the content_hash
# recomputation: empty means "diff merge_base against the live working tree"
# (the commit gate's case - the certified content is still uncommitted), a
# sha means "diff merge_base against that landed commit" (the push gate's
# case - the working tree may belong to a different branch entirely by push
# time).
#
# `label` names the report kind in messages (e.g. "quality report",
# "findings report"); `regen_hint` names the exact regenerate command.
assert_report_freshness() {
  local report_file="$1"
  local repo_root="$2"
  local expected_head_sha="$3"
  local head_relation="$4"
  local content_diff_ref="$5"
  local label="$6"
  local regen_hint="$7"

  local base_ref head_sha merge_base_sha generated_at target_path dirty
  base_ref="$(json_file_string_value "$report_file" "base_ref" 2>/dev/null || true)"
  head_sha="$(json_file_string_value "$report_file" "head_sha" 2>/dev/null || true)"
  merge_base_sha="$(json_file_string_value "$report_file" "merge_base_sha" 2>/dev/null || true)"
  generated_at="$(json_file_string_value "$report_file" "generated_at" 2>/dev/null || true)"
  target_path="$(json_file_string_value "$report_file" "target" 2>/dev/null || true)"
  dirty="$(json_file_bool_value "$report_file" "dirty" 2>/dev/null || true)"

  if [[ "$base_ref" != "dev" ]]; then
    failures+=("$label base_ref must be dev; found ${base_ref:-missing} in $report_file")
  fi
  local expected_merge_base
  if [[ "$head_relation" == "ancestor" ]]; then
    if [[ -z "$head_sha" ]] || ! git -C "$repo_root" merge-base --is-ancestor "$head_sha" "$expected_head_sha" 2>/dev/null; then
      failures+=("$label head_sha (${head_sha:-missing}) is not the pushed commit or one of its ancestors (${expected_head_sha:-unknown}); $regen_hint")
    fi
  elif [[ -z "$head_sha" || "$head_sha" != "$expected_head_sha" ]]; then
    failures+=("$label head_sha (${head_sha:-missing}) does not match the expected commit (${expected_head_sha:-unknown}); $regen_hint")
  fi
  expected_merge_base="$(git -C "$repo_root" merge-base dev "$expected_head_sha" 2>/dev/null || true)"
  if [[ -z "$merge_base_sha" ]]; then
    failures+=("$label must include merge_base_sha; $regen_hint")
  elif [[ -n "$expected_merge_base" && "$merge_base_sha" != "$expected_merge_base" ]]; then
    failures+=("$label merge_base_sha (${merge_base_sha}) must match the dev...${expected_head_sha} merge base (${expected_merge_base}); $regen_hint")
  fi
  if [[ ! "$generated_at" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$ ]]; then
    failures+=("$label generated_at must be an ISO-8601 UTC timestamp")
  fi
  if [[ -z "$target_path" ]]; then
    failures+=("$label must include target")
  elif [[ "$target_path" = /* ]]; then
    if [[ "$target_path" != "$repo_root"* ]]; then
      failures+=("$label target '$target_path' is outside this repo; $regen_hint")
    fi
  else
    if [[ ! -e "$repo_root/$target_path" ]]; then
      failures+=("$label target '$target_path' does not exist under repo root")
    fi
  fi
  if [[ "$dirty" != "true" && "$dirty" != "false" ]]; then
    failures+=("$label must include dirty boolean")
  elif [[ "$dirty" == "true" ]]; then
    failures+=("working tree has unstaged changes (dirty=true); stage everything and $regen_hint")
  fi

  local report_hash current_hash
  report_hash="$(json_file_string_value "$report_file" "content_hash" 2>/dev/null || true)"
  if [[ -z "$report_hash" ]]; then
    failures+=("$label must include content_hash; $regen_hint")
  elif [[ -n "$expected_merge_base" ]] && command -v git >/dev/null 2>&1; then
    if [[ -n "$content_diff_ref" ]]; then
      current_hash="$(git -C "$repo_root" diff --no-color --no-ext-diff "$expected_merge_base" "$content_diff_ref" 2>/dev/null | git -C "$repo_root" hash-object --stdin 2>/dev/null || true)"
    else
      current_hash="$(git -C "$repo_root" diff --no-color --no-ext-diff "$expected_merge_base" 2>/dev/null | git -C "$repo_root" hash-object --stdin 2>/dev/null || true)"
    fi
    if [[ -z "$current_hash" ]]; then
      failures+=("could not compute the content hash to verify $label freshness; $regen_hint")
    elif [[ "$current_hash" != "$report_hash" ]]; then
      failures+=("$label content_hash does not match the current changes (files edited since generating); $regen_hint")
    fi
  fi
}

# Best-effort extraction of a given severity's finding titles from a
# findings-*.json report, for an actionable failure message. The
# `counts.<severity>` field (read by the exact-path json_file_number_value)
# is what actually gates the commit/push; this only enriches the message, so
# it degrades to nothing when python3 is unavailable rather than failing
# the gate.
list_finding_titles_by_severity() {
  local file="$1"
  local severity="$2"
  command -v python3 >/dev/null 2>&1 || return 0
  python3 -c "
import json, sys
try:
    data = json.load(open(sys.argv[1], encoding='utf-8'))
except Exception:
    sys.exit(0)
titles = [f.get('title', 'untitled') for f in data.get('findings', []) if f.get('severity') == sys.argv[2]]
print('; '.join(titles))
" "$file" "$severity" 2>/dev/null || true
}

# One fail-closed standard-library probe repeats Phase C's complete cancellation
# contract at push time. It emits only fixed result codes, one per line.
cancellation_validation_probe() {
  local repo_root="$1"
  local plan_file="$2"
  command -v python3 >/dev/null 2>&1 || return 127
  python3 - "$repo_root" "$plan_file" <<'PY'
import re
import stat
import sys
from datetime import datetime
from pathlib import Path

TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
BLOCK_REASON = re.compile(r"^[|>](?:[+-][1-9]?|[1-9][+-]?)?(?:[ \t]*#.*)?$")
STATUS = re.compile(r"^\*\*Status:\*\*[ \t]+CANCELLED\b", re.MULTILINE)


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}
    parts = text.split("---\n", 2)
    if len(parts) != 3:
        return {}
    data = {}
    current_key = ""
    for raw_line in parts[1].splitlines():
        line = raw_line.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line.startswith("  - ") and current_key:
            value = data.get(current_key)
            if not isinstance(value, list):
                value = [] if value in (None, "") else [str(value)]
                data[current_key] = value
            value.append(line[4:].strip())
            continue
        if line.startswith((" ", "\t")) and current_key == "cancelled_reason":
            data[current_key] = [data.get(current_key), line.strip()]
            continue
        if ":" in line and not line.startswith(" "):
            key, value = line.split(":", 1)
            current_key = key.strip()
            data[current_key] = value.strip().strip('"').strip("'")
    return data


def validate(repo_root, plan_file):
    errors = []
    data = frontmatter(plan_file)

    cancelled_at = data.get("cancelled_at", "")
    if cancelled_at in ("", []):
        errors.append("MISSING_CANCELLED_AT")
    elif not isinstance(cancelled_at, str) or not TIMESTAMP.fullmatch(cancelled_at):
        errors.append("INVALID_CANCELLED_AT")
    else:
        try:
            datetime.strptime(cancelled_at, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            errors.append("INVALID_CANCELLED_AT")

    reason = data.get("cancelled_reason", "")
    if reason in ("", []):
        errors.append("MISSING_CANCELLED_REASON")
    elif (
        not isinstance(reason, str)
        or not reason.strip()
        or BLOCK_REASON.fullmatch(reason.strip())
        or reason.lstrip().startswith(("[", "{", "- ", "#"))
    ):
        errors.append("INVALID_CANCELLED_REASON")

    evidence = data.get("cancelled_evidence", "")
    if evidence in ("", []):
        errors.append("MISSING_CANCELLED_EVIDENCE")
        return errors
    if not isinstance(evidence, str):
        errors.append("INVALID_EVIDENCE_SCALAR")
        return errors

    evidence_path = Path(evidence)
    if evidence_path.is_absolute():
        errors.append("ABSOLUTE_EVIDENCE")
        return errors
    if ".." in evidence_path.parts:
        errors.append("TRAVERSAL_EVIDENCE")
        return errors

    try:
        canonical_root = repo_root.resolve(strict=True)
        canonical_evidence = (canonical_root / evidence_path).resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        errors.append("EVIDENCE_RESOLUTION_FAILED")
        return errors
    if not canonical_evidence.is_relative_to(canonical_root):
        errors.append("OUTSIDE_EVIDENCE")
        return errors
    try:
        canonical_evidence = canonical_evidence.resolve(strict=True)
    except FileNotFoundError:
        errors.append("MISSING_EVIDENCE_FILE")
        return errors
    except (OSError, RuntimeError, ValueError):
        errors.append("EVIDENCE_RESOLUTION_FAILED")
        return errors
    if not canonical_evidence.is_relative_to(canonical_root):
        errors.append("OUTSIDE_EVIDENCE")
        return errors
    try:
        mode = canonical_evidence.stat().st_mode
    except OSError:
        errors.append("UNREADABLE_EVIDENCE")
        return errors
    if not stat.S_ISREG(mode):
        errors.append("NON_REGULAR_EVIDENCE")
        return errors
    if not mode & (stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH):
        errors.append("UNREADABLE_EVIDENCE")
        return errors
    try:
        content = canonical_evidence.read_text(encoding="utf-8")
    except UnicodeError:
        errors.append("INVALID_UTF8_EVIDENCE")
        return errors
    except OSError:
        errors.append("UNREADABLE_EVIDENCE")
        return errors
    if not STATUS.search(content):
        errors.append("INVALID_EVIDENCE_MARKER")
    return errors


try:
    result = validate(Path(sys.argv[1]), Path(sys.argv[2]))
except Exception:
    print("PROBE_EXCEPTION")
else:
    print("\n".join(result) if result else "OK")
PY
}

# Validate the artifact-backed audit contract for a cancelled plan. Appends
# distinct failure messages to the caller's dynamically scoped `failures`
# array, matching assert_commit_invariants and assert_push_invariants.
assert_cancellation_evidence() {
  local plan_file="$1"
  local phase_label="$2"
  local probe_output="" probe_status=0 probe_code="" malformed=0
  probe_output="$(cancellation_validation_probe "$repo_root" "$plan_file" 2>/dev/null)" || probe_status=$?
  if [[ "$probe_status" -eq 127 ]]; then
    failures+=("$phase_label cancellation validation requires python3")
    return
  elif [[ "$probe_status" -ne 0 ]]; then
    failures+=("$phase_label cancellation validation probe failed")
    return
  elif [[ "$probe_output" == "OK" ]]; then
    return
  elif [[ -z "$probe_output" ]]; then
    failures+=("$phase_label cancellation validation probe returned malformed output")
    return
  fi

  while IFS= read -r probe_code; do
    case "$probe_code" in
      MISSING_CANCELLED_AT) failures+=("$phase_label cancelled plan must set cancelled_at") ;;
      INVALID_CANCELLED_AT) failures+=("$phase_label cancelled_at must be a real UTC timestamp in YYYY-MM-DDTHH:MM:SSZ format") ;;
      MISSING_CANCELLED_REASON) failures+=("$phase_label cancelled plan must set cancelled_reason") ;;
      INVALID_CANCELLED_REASON) failures+=("$phase_label cancelled_reason must be meaningful plain single-line scalar prose") ;;
      MISSING_CANCELLED_EVIDENCE) failures+=("$phase_label cancelled plan must set cancelled_evidence") ;;
      INVALID_EVIDENCE_SCALAR) failures+=("$phase_label cancelled_evidence must be a plain path scalar") ;;
      ABSOLUTE_EVIDENCE) failures+=("$phase_label cancelled_evidence must be repository-relative") ;;
      TRAVERSAL_EVIDENCE) failures+=("$phase_label cancelled_evidence must not contain .. traversal") ;;
      EVIDENCE_RESOLUTION_FAILED) failures+=("$phase_label cancelled evidence path could not be resolved safely") ;;
      OUTSIDE_EVIDENCE) failures+=("$phase_label cancelled evidence must stay inside the repository") ;;
      MISSING_EVIDENCE_FILE) failures+=("$phase_label cancelled evidence file is missing") ;;
      NON_REGULAR_EVIDENCE) failures+=("$phase_label cancelled evidence must be a regular file") ;;
      UNREADABLE_EVIDENCE) failures+=("$phase_label cancelled evidence must be readable") ;;
      INVALID_UTF8_EVIDENCE) failures+=("$phase_label cancelled evidence must be valid UTF-8 text") ;;
      INVALID_EVIDENCE_MARKER) failures+=("$phase_label cancelled evidence must contain exact same-line prefix: **Status:** CANCELLED") ;;
      PROBE_EXCEPTION) failures+=("$phase_label cancellation validation probe raised an exception") ;;
      *) malformed=1 ;;
    esac
  done <<< "$probe_output"
  if [[ "$malformed" -eq 1 ]]; then
    failures+=("$phase_label cancellation validation probe returned malformed output")
  fi
}

# Single home for the plan/score/findings/closeout/LEARN ceremony shared by
# every commit gate entry point (PreToolUse and the commit-msg git hook).
# Branch-shape is deliberately NOT checked here - callers diverge on it (see
# D4 in docs/plan-deterministic-commit-gate.md) - so `branch` is assumed
# already valid (an <plan>_implementation branch) by the time this is called.
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
    small_status="$(fm_read_unique_status "$small_plan" || true)"
    if [[ "$small_status" == "$DUPLICATE_STATUS_VALUE" ]]; then
      failures+=("$small_plan must contain exactly one status field before commit")
    elif [[ "$small_status" == "cancelled" ]]; then
      failures+=("$small_plan is cancelled; a cancelled phase never certifies a commit, so advance current_phase past it")
    elif [[ "$small_status" != "complete" ]]; then
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

  # The pending commit object does not exist yet at gate time (D5 in
  # docs/plan-deterministic-commit-gate.md): current HEAD is its parent, and
  # the certified content is still only staged in the working tree - so
  # report freshness is checked against HEAD + the working tree, not a
  # landed sha (contrast assert_push_invariants below, which fires after the
  # commit has already landed).
  local commit_gate_head
  commit_gate_head="$(git -C "$repo_root" rev-parse HEAD 2>/dev/null || true)"

  local score_file=""
  if [[ -n "$current_phase" ]]; then
    score_file="$(select_fresh_report "$repo_root/.claude/quality_reports" "score-*.json" "$current_branch" "$current_phase")"
  fi

  if [[ -z "$score_file" ]]; then
    failures+=("no matching quality report found - run uv run python .claude/scripts/quality_score.py <target> --phase ${current_phase:-current_phase} --base-ref dev --json --out .claude/quality_reports/score-<ts>.json")
  else
    local score_regen_hint="re-run quality_score.py: uv run python .claude/scripts/quality_score.py <target> --phase ${current_phase:-current_phase} --base-ref dev --json --out .claude/quality_reports/score-<ts>.json"
    local score
    score="$(json_file_number_value "$score_file" "score" 2>/dev/null || true)"
    if [[ ! "$score" =~ ^[0-9]+$ || "$score" -lt 90 ]]; then
      failures+=("quality score must be >= 90; found ${score:-unknown} in $score_file")
    fi

    assert_report_freshness "$score_file" "$repo_root" "$commit_gate_head" "exact" "" "quality report" "$score_regen_hint"

    local tests_passed tests_skipped
    tests_passed="$(json_file_bool_value "$score_file" "tests_passed" 2>/dev/null || true)"
    tests_skipped="$(json_file_bool_value "$score_file" "tests_skipped" 2>/dev/null || true)"
    if [[ "$tests_passed" != "true" ]]; then
      failures+=("quality report must record tests_passed: true; found ${tests_passed:-missing}")
    fi
    if [[ "$tests_skipped" == "true" ]]; then
      failures+=("tests were skipped (tests_skipped=true); run the full test suite before committing")
    fi
    if ! json_file_array_present "$score_file" "changed_files" 2>/dev/null; then
      failures+=("quality report must include changed_files array")
    fi
  fi

  # R-SCORE-03: the REVIEW stage's own severity-gated findings report. The
  # arithmetic score above is honest about what it measures (lint/types/tests)
  # but says nothing about what the review found; this is the second gated
  # artifact the review's own R-SCORE-01(d) deferred to a later iteration.
  local findings_file=""
  if [[ -n "$current_phase" ]]; then
    findings_file="$(select_fresh_report "$repo_root/.claude/quality_reports" "findings-*.json" "$current_branch" "$current_phase")"
  fi

  if [[ -z "$findings_file" ]]; then
    failures+=("no matching findings report found - run uv run python .claude/scripts/record_findings.py <target> --profile <reviewed-profile> --phase ${current_phase:-current_phase} --base-ref dev --findings-json <path> --out .claude/quality_reports/findings-<ts>.json")
  else
    local findings_regen_hint="re-run record_findings.py with the profiles that ran: uv run python .claude/scripts/record_findings.py <target> --profile <reviewed-profile> --phase ${current_phase:-current_phase} --base-ref dev --findings-json <path> --out .claude/quality_reports/findings-<ts>.json"
    assert_report_freshness "$findings_file" "$repo_root" "$commit_gate_head" "exact" "" "findings report" "$findings_regen_hint"

    local critical_count
    critical_count="$(json_file_number_value "$findings_file" "counts.critical" 2>/dev/null || true)"
    if [[ ! "$critical_count" =~ ^[0-9]+$ ]]; then
      failures+=("findings report must include counts.critical; $findings_regen_hint")
    elif [[ "$critical_count" -gt 0 ]]; then
      local critical_titles
      critical_titles="$(list_finding_titles_by_severity "$findings_file" "CRITICAL")"
      failures+=("findings report has $critical_count CRITICAL finding(s) blocking commit: ${critical_titles:-see $findings_file}")
    fi

    assert_required_ponytail_review "$findings_file" "$repo_root" "" "commit" "$findings_regen_hint"
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

  # R-HOOKS-10: accumulate with `while read`, not `mapfile` - macOS's default
  # /bin/bash is 3.2, which has no `mapfile`/`readarray` builtin (same 3.2
  # constraint the `${phases[${#phases[@]}-1]}` below is written for). This
  # mirrors the read loops in select_fresh_report and the bypass-ledger scan.
  local -a phases=()
  local _phase_line
  while IFS= read -r _phase_line; do
    [[ -n "$_phase_line" ]] && phases+=("$_phase_line")
  done < <(fm_read_list "$big_plan" "phases")
  if [[ "${#phases[@]}" -eq 0 ]]; then
    failures+=("$big_plan has no phases list")
    return
  fi

  local phase small_plan status completed_count=0 last_completed_phase=""
  for phase in "${phases[@]}"; do
    small_plan="$repo_root/.claude/plans/$phase.md"
    if [[ ! -f "$small_plan" ]]; then
      failures+=("missing small-plan file: .claude/plans/$phase.md")
      continue
    fi
    status="$(fm_read_unique_status "$small_plan" || true)"
    if [[ "$status" == "$DUPLICATE_STATUS_VALUE" ]]; then
      failures+=("$small_plan must contain exactly one status field before PR/push")
    elif [[ "$status" == "complete" ]]; then
      completed_count=$((completed_count + 1))
      last_completed_phase="$phase"
    elif [[ "$status" == "cancelled" ]]; then
      assert_cancellation_evidence "$small_plan" "$phase"
    else
      failures+=("all small plans must be complete before PR/push; $phase is ${status:-missing-status}")
    fi
  done

  if [[ "$completed_count" -eq 0 ]]; then
    failures+=("implementation branch certifies no completed work and should be deleted rather than pushed")
  fi

  local commit_count
  commit_count="$(git -C "$repo_root" rev-list --count "dev..$local_sha" 2>/dev/null || echo 0)"
  if [[ ! "$commit_count" =~ ^[0-9]+$ || "$commit_count" -lt "$completed_count" ]]; then
    failures+=("implementation branch must have at least one commit per completed small plan before PR/push")
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

  # R-SCORE-03: the push tier of the severity gate additionally requires
  # counts.major == 0 (the commit gate already required counts.critical == 0
  # before any commit could land). Bind to the last COMPLETED phase because a
  # cancelled trailing phase has no findings report and never will.
  local final_phase="$last_completed_phase"
  local findings_file=""
  if [[ -n "$final_phase" ]]; then
    findings_file="$(select_fresh_report "$repo_root/.claude/quality_reports" "findings-*.json" "$branch" "$final_phase")"
  fi

  if [[ -n "$final_phase" && -z "$findings_file" ]]; then
    failures+=("no matching findings report found for phase $final_phase - run uv run python .claude/scripts/record_findings.py <target> --profile <reviewed-profile> --phase $final_phase --base-ref dev --findings-json <path> --out .claude/quality_reports/findings-<ts>.json")
  elif [[ -n "$findings_file" ]]; then
    local findings_regen_hint="re-run record_findings.py with the profiles that ran: uv run python .claude/scripts/record_findings.py <target> --profile <reviewed-profile> --phase $final_phase --base-ref dev --findings-json <path> --out .claude/quality_reports/findings-<ts>.json"
    assert_report_freshness "$findings_file" "$repo_root" "$local_sha" "ancestor" "$local_sha" "findings report" "$findings_regen_hint"

    local major_count
    major_count="$(json_file_number_value "$findings_file" "counts.major" 2>/dev/null || true)"
    if [[ ! "$major_count" =~ ^[0-9]+$ ]]; then
      failures+=("findings report must include counts.major; $findings_regen_hint")
    elif [[ "$major_count" -gt 0 ]]; then
      local major_titles
      major_titles="$(list_finding_titles_by_severity "$findings_file" "MAJOR")"
      failures+=("findings report has $major_count MAJOR finding(s) blocking push: ${major_titles:-see $findings_file}")
    fi

    assert_required_ponytail_review "$findings_file" "$repo_root" "$local_sha" "push" "$findings_regen_hint"
  fi
}
