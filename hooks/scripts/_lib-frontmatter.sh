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

# Small-plan names are file stems, not paths. Keep lifecycle reads rooted under
# .claude/plans instead of allowing current_phase to select an arbitrary file.
is_plan_slug() {
  [[ "$1" =~ ^[a-zA-Z0-9][a-zA-Z0-9._-]*$ ]]
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

# Return success only when every path changed since the branch's merge-base
# with `dev` is eligible for a typo-subject bypass: Markdown documentation
# outside runtime/execution directories. A single ineligible path - or an
# empty/unresolvable diff - fails closed, so the caller
# (commit_bypass_eligible) treats the typo subject as ineligible and falls
# through to the normal ceremony gate instead of granting a free pass.
# Mirrors diff_requires_ponytail's diff-ref convention: empty `diff_ref`
# checks the live working tree/index (commit gate), a ref checks that landed
# commit (push gate). The excluded directories hold no legitimate typo-only
# Markdown today (hook logic and scripts are `.sh`/`.py`, generated runtime
# lives under `.claude/`/`dist/`), so this stays narrow without excluding any
# real current documentation surface.
typo_bypass_diff_allowed() {
  local repo_root="$1"
  local diff_ref="${2:-}"
  local head_ref="${diff_ref:-HEAD}"
  local merge_base path
  merge_base="$(git -C "$repo_root" merge-base dev "$head_ref" 2>/dev/null || true)"
  [[ -n "$merge_base" ]] || return 1

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
  [[ "${#paths[@]}" -gt 0 ]] || return 1

  for path in "${paths[@]}"; do
    case "$path" in
      *.md)
        case "$path" in
          scripts/*|shared/scripts/*|shared/hooks/*|tests/*|.github/*|.claude/*|dist/*) return 1 ;;
        esac
        ;;
      *) return 1 ;;
    esac
  done
  return 0
}

# Full bypass eligibility for one commit subject. `fixup!`/`squash!` bypass
# unconditionally (recovery/history subjects; deliberately no diff-path
# restriction, per the recovery use-case they exist for).
# `chore(typo):`/`docs(typo):` bypass only when typo_bypass_diff_allowed
# confirms every changed path is eligible documentation content outside
# runtime/execution directories, so a substantive runtime/code change cannot
# hide under a typo subject. A subject `is_bypass_subject` never matches, or
# a typo subject with an ineligible diff, is simply not a bypass: it falls
# through to the normal ceremony gate below like any other commit.
commit_bypass_eligible() {
  local repo_root="$1"
  local subject="$2"
  local diff_ref="${3:-}"
  is_bypass_subject "$subject" || return 1
  case "$subject" in
    fixup!*|squash!*) return 0 ;;
  esac
  typo_bypass_diff_allowed "$repo_root" "$diff_ref"
}

repo_root_from_script() {
  local script_dir
  script_dir="$(cd "$(dirname "${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}")" && pwd)"
  cd "$script_dir/../../.." && pwd
}

# One fail-closed standard-library probe repeats Phase C's complete cancellation
# contract at push time. It emits only fixed result codes, one per line.
#
# This deliberately duplicates `validate_cancellation` in
# scripts/validate_plan_frontmatter.py rather than importing it: this copy ships
# into consumer `.claude/hooks/scripts/` and must run with nothing but a stock
# python3, while that one is authoring-repo-only tooling that never ships. The
# two are one contract in two places, so a change to the timestamp,
# block-scalar, or evidence-status rules here must be mirrored there.
# tests/test_validate_plan_frontmatter.py asserts the shared rules stay equal.
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

# Validate the artifact-backed audit contract for a paused small plan. This is
# deliberately separate from cancellation: a pause is non-terminal and may
# authorize a checkpoint commit, while cancellation never can.
pause_validation_probe() {
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
STATUS = re.compile(r"^\*\*Status:\*\*[ \t]+PAUSED\b", re.MULTILINE)


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
        if line.startswith((" ", "\t")) and current_key == "paused_reason":
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

    paused_at = data.get("paused_at", "")
    if paused_at in ("", []):
        errors.append("MISSING_PAUSED_AT")
    elif not isinstance(paused_at, str) or not TIMESTAMP.fullmatch(paused_at):
        errors.append("INVALID_PAUSED_AT")
    else:
        try:
            datetime.strptime(paused_at, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            errors.append("INVALID_PAUSED_AT")

    reason = data.get("paused_reason", "")
    if reason in ("", []):
        errors.append("MISSING_PAUSED_REASON")
    elif (
        not isinstance(reason, str)
        or not reason.strip()
        or BLOCK_REASON.fullmatch(reason.strip())
        or reason.lstrip().startswith(("[", "{", "- ", "#"))
    ):
        errors.append("INVALID_PAUSED_REASON")

    log = data.get("pause_session_log", "")
    if log in ("", []):
        errors.append("MISSING_PAUSE_SESSION_LOG")
        return errors
    if not isinstance(log, str):
        errors.append("INVALID_LOG_SCALAR")
        return errors

    log_path = Path(log)
    if log_path.is_absolute():
        errors.append("ABSOLUTE_LOG")
        return errors
    if ".." in log_path.parts:
        errors.append("TRAVERSAL_LOG")
        return errors

    try:
        canonical_root = repo_root.resolve(strict=True)
        canonical_log = (canonical_root / log_path).resolve(strict=False)
    except (OSError, RuntimeError, ValueError):
        errors.append("LOG_RESOLUTION_FAILED")
        return errors
    if not canonical_log.is_relative_to(canonical_root):
        errors.append("OUTSIDE_LOG")
        return errors
    try:
        canonical_log = canonical_log.resolve(strict=True)
    except FileNotFoundError:
        errors.append("MISSING_LOG_FILE")
        return errors
    except (OSError, RuntimeError, ValueError):
        errors.append("LOG_RESOLUTION_FAILED")
        return errors
    if not canonical_log.is_relative_to(canonical_root):
        errors.append("OUTSIDE_LOG")
        return errors
    try:
        mode = canonical_log.stat().st_mode
    except OSError:
        errors.append("UNREADABLE_LOG")
        return errors
    if not stat.S_ISREG(mode):
        errors.append("NON_REGULAR_LOG")
        return errors
    if not mode & (stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH):
        errors.append("UNREADABLE_LOG")
        return errors
    try:
        content = canonical_log.read_text(encoding="utf-8")
    except UnicodeError:
        errors.append("INVALID_UTF8_LOG")
        return errors
    except OSError:
        errors.append("UNREADABLE_LOG")
        return errors
    if not STATUS.search(content):
        errors.append("INVALID_LOG_MARKER")
    return errors


try:
    result = validate(Path(sys.argv[1]), Path(sys.argv[2]))
except Exception:
    print("PROBE_EXCEPTION")
else:
    print("\n".join(result) if result else "OK")
PY
}

assert_pause_evidence() {
  local plan_file="$1"
  local phase_label="$2"
  local probe_output="" probe_status=0 probe_code="" malformed=0
  probe_output="$(pause_validation_probe "$repo_root" "$plan_file" 2>/dev/null)" || probe_status=$?
  if [[ "$probe_status" -eq 127 ]]; then
    failures+=("$phase_label pause validation requires python3")
    return
  elif [[ "$probe_status" -ne 0 ]]; then
    failures+=("$phase_label pause validation probe failed")
    return
  elif [[ "$probe_output" == "OK" ]]; then
    return
  elif [[ -z "$probe_output" ]]; then
    failures+=("$phase_label pause validation probe returned malformed output")
    return
  fi

  while IFS= read -r probe_code; do
    case "$probe_code" in
      MISSING_PAUSED_AT) failures+=("$phase_label paused plan must set paused_at") ;;
      INVALID_PAUSED_AT) failures+=("$phase_label paused_at must be a real UTC timestamp in YYYY-MM-DDTHH:MM:SSZ format") ;;
      MISSING_PAUSED_REASON) failures+=("$phase_label paused plan must set paused_reason") ;;
      INVALID_PAUSED_REASON) failures+=("$phase_label paused_reason must be meaningful plain single-line scalar prose") ;;
      MISSING_PAUSE_SESSION_LOG) failures+=("$phase_label paused plan must set pause_session_log") ;;
      INVALID_LOG_SCALAR) failures+=("$phase_label pause_session_log must be a plain path scalar") ;;
      ABSOLUTE_LOG) failures+=("$phase_label pause_session_log must be repository-relative") ;;
      TRAVERSAL_LOG) failures+=("$phase_label pause_session_log must not contain .. traversal") ;;
      LOG_RESOLUTION_FAILED) failures+=("$phase_label pause session log path could not be resolved safely") ;;
      OUTSIDE_LOG) failures+=("$phase_label pause session log must stay inside the repository") ;;
      MISSING_LOG_FILE) failures+=("$phase_label pause session log file is missing") ;;
      NON_REGULAR_LOG) failures+=("$phase_label pause session log must be a regular file") ;;
      UNREADABLE_LOG) failures+=("$phase_label pause session log must be readable") ;;
      INVALID_UTF8_LOG) failures+=("$phase_label pause session log must be valid UTF-8 text") ;;
      INVALID_LOG_MARKER) failures+=("$phase_label pause session log must contain exact same-line prefix: **Status:** PAUSED") ;;
      PROBE_EXCEPTION) failures+=("$phase_label pause validation probe raised an exception") ;;
      *) malformed=1 ;;
    esac
  done <<< "$probe_output"
  if [[ "$malformed" -eq 1 ]]; then
    failures+=("$phase_label pause validation probe returned malformed output")
  fi
}

# Provider adapters stay thin: every completed-phase gate calls the same
# standard-library receipt reader.  It performs strict JSON/path/hash/freshness
# checks without running verification tools, so hook execution stays cheap.
assert_completed_receipt() {
  local repo_root="$1"
  local branch="$2"
  local phase="$3"
  local head="$4"
  local head_relation="$5"
  local require_major="$6"
  local require_ponytail="$7"
  local enforce_final_state="$8"
  local reader="$repo_root/.claude/scripts/verify.py"
  if [[ ! -f "$reader" ]]; then
    failures+=("missing provider-neutral closeout receipt reader: .claude/scripts/verify.py")
    return
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    failures+=("closeout receipt validation requires python3")
    return
  fi
  local -a args=(gate --branch "$branch" --phase "$phase" --head "$head" --head-relation "$head_relation")
  [[ "$require_major" == "true" ]] && args+=(--require-major)
  [[ "$require_ponytail" == "true" ]] && args+=(--require-ponytail)
  [[ "$enforce_final_state" == "true" ]] && args+=(--enforce-final-state)
  local output status
  output="$(cd "$repo_root" && python3 "$reader" "${args[@]}" 2>&1)" || status=$?
  if [[ "${status:-0}" -ne 0 ]]; then
    failures+=("${output:-closeout receipt validation failed}")
  fi
}

# Hard-validate every plan file's frontmatter schema (required fields, status
# enums, body phase inventory, paused/cancelled contracts) with the shipped
# stdlib-only validator - the same authoritative source the authoring repo
# uses, so consumers no longer get a weaker partial bash-only schema check.
# Runs unconditionally (before the paused/complete/cancelled dispatch below)
# so a paused checkpoint commit is still covered.
assert_plan_frontmatter() {
  local repo_root="$1"
  local validator="$repo_root/.claude/scripts/validate_plan_frontmatter.py"
  if [[ ! -f "$validator" ]]; then
    failures+=("missing plan-frontmatter validator: .claude/scripts/validate_plan_frontmatter.py")
    return
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    failures+=("plan frontmatter validation requires python3")
    return
  fi
  local output status=0
  output="$(cd "$repo_root" && python3 "$validator" 2>&1)" || status=$?
  if [[ "$status" -ne 0 ]]; then
    local line
    while IFS= read -r line; do
      [[ -n "$line" ]] && failures+=("$line")
    done <<< "$output"
  fi
}

# Single home for the plan/findings/closeout/LEARN ceremony shared by
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

  assert_plan_frontmatter "$repo_root"

  local big_status="" current_phase="" small_plan="" phase_listed=0
  local -a all_phases=()
  if [[ -f "$big_plan" ]]; then
    big_status="$(fm_read_unique_status "$big_plan" || true)"
    if [[ "$big_status" == "$DUPLICATE_STATUS_VALUE" ]]; then
      failures+=("$big_plan must contain exactly one status field before commit")
    fi
    current_phase="$(fm_read "$big_plan" "current_phase" || true)"
    if [[ -z "$current_phase" ]]; then
      failures+=("big plan has no current_phase")
    elif ! is_plan_slug "$current_phase"; then
      failures+=("big plan current_phase must be a safe small-plan slug")
    else
      small_plan="$repo_root/.claude/plans/$current_phase.md"
      local listed_phase
      while IFS= read -r listed_phase; do
        [[ -n "$listed_phase" ]] || continue
        all_phases+=("$listed_phase")
        [[ "$listed_phase" == "$current_phase" ]] && phase_listed=1
      done < <(fm_read_list "$big_plan" "phases")
      if [[ "$phase_listed" -ne 1 ]]; then
        failures+=("big plan current_phase must be listed in phases")
      fi
    fi
  fi

  # R-LIFECYCLE-02: cancellation evidence is a commit-time gate, not only a
  # push/PR-time one - a cancelled sibling phase must already carry the full
  # audit contract before any further commit lands on this branch.
  local other_phase other_plan="" other_status=""
  for other_phase in "${all_phases[@]}"; do
    [[ "$other_phase" == "$current_phase" ]] && continue
    other_plan="$repo_root/.claude/plans/$other_phase.md"
    [[ -f "$other_plan" ]] || continue
    other_status="$(fm_read_unique_status "$other_plan" || true)"
    if [[ "$other_status" == "cancelled" ]]; then
      assert_cancellation_evidence "$other_plan" "$other_phase"
    fi
  done

  local small_status="" closeout_log="" small_type="" small_parent=""
  if [[ -n "$small_plan" && -f "$small_plan" ]]; then
    small_type="$(fm_read "$small_plan" "type" || true)"
    small_parent="$(fm_read "$small_plan" "parent_plan" || true)"
    if [[ "$small_type" != "small-plan" ]]; then
      failures+=("$small_plan must have type: small-plan before commit")
    fi
    if [[ "$small_parent" != "$slug" ]]; then
      failures+=("$small_plan parent_plan must match $slug before commit")
    fi
    small_status="$(fm_read_unique_status "$small_plan" || true)"
    if [[ "$small_status" == "$DUPLICATE_STATUS_VALUE" ]]; then
      failures+=("$small_plan must contain exactly one status field before commit")
    elif [[ "$small_status" == "cancelled" ]]; then
      failures+=("$small_plan is cancelled; a cancelled phase never certifies a commit, so advance current_phase past it")
    elif [[ "$small_status" == "paused" ]]; then
      if [[ "$big_status" != "in-progress" ]]; then
        failures+=("$big_plan must have status: in-progress for a paused checkpoint commit")
      fi
      assert_pause_evidence "$small_plan" "$current_phase"
      return
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

  # The pending commit does not exist yet at gate time, so receipt freshness
  # is checked against HEAD plus the staged tracked state. Paused checkpoints
  # returned above and intentionally never enter this completed authority path.
  local commit_gate_head
  commit_gate_head="$(git -C "$repo_root" rev-parse HEAD 2>/dev/null || true)"
  local require_ponytail="false"
  if diff_requires_ponytail "$repo_root" ""; then
    require_ponytail="true"
  fi
  # R-LIFECYCLE-01: an open MAJOR finding blocks only the phase-completion
  # commit (small_status == complete), not every commit attempt while the
  # phase remains in progress - see docs/plan-deterministic-commit-gate.md.
  local require_major="false"
  [[ "$small_status" == "complete" ]] && require_major="true"
  assert_completed_receipt "$repo_root" "$current_branch" "$current_phase" "$commit_gate_head" "exact" "$require_major" "$require_ponytail" "true"
}

# Strict final closeout ceremony shared by PR creation and terminal pushes.
# Branch-shape is deliberately NOT checked here, mirroring
# assert_commit_invariants above:
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
assert_closeout_invariants() {
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
  # mirrors the read loops used by the paused-publication and bypass-ledger paths.
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

  # The terminal completed phase gets strict current-state freshness; every
  # earlier completed phase in the big plan's declared order is additionally
  # walked by historical_chain_errors (verify.py), which requires its own
  # valid receipt with ancestor/tree/artifact-hash integrity - a completed
  # phase can no longer silently skip the receipt chain.
  if [[ "$completed_count" -gt 0 ]]; then
    local require_ponytail="false"
    if diff_requires_ponytail "$repo_root" "$local_sha"; then
      require_ponytail="true"
    fi
    assert_completed_receipt "$repo_root" "$branch" "$last_completed_phase" "$local_sha" "ancestor" "true" "$require_ponytail" "true"
  fi
}

# Validate the narrow remote-backup path for a current paused phase. This does
# not inspect final closeout reports: the checkpoint remains unfinished and PR
# creation always calls assert_closeout_invariants directly.
assert_paused_publication_invariants() {
  local repo_root="$1"
  local branch="$2"
  local local_sha="$3"
  local slug="${branch%_implementation}"
  local big_plan="$repo_root/.claude/plans/$slug.md"
  if [[ ! -f "$big_plan" ]]; then
    failures+=("missing big-plan file: .claude/plans/$slug.md")
    return
  fi

  local big_status current_phase
  big_status="$(fm_read_unique_status "$big_plan" || true)"
  if [[ "$big_status" == "$DUPLICATE_STATUS_VALUE" ]]; then
    failures+=("$big_plan must contain exactly one status field before paused checkpoint push")
  elif [[ "$big_status" != "in-progress" ]]; then
    failures+=("$big_plan must have status: in-progress for a paused checkpoint push")
  fi

  current_phase="$(fm_read "$big_plan" "current_phase" || true)"
  if [[ -z "$current_phase" ]]; then
    failures+=("big plan has no current_phase")
    return
  elif ! is_plan_slug "$current_phase"; then
    failures+=("big plan current_phase must be a safe small-plan slug")
    return
  fi

  # Keep this Bash 3.2-compatible: collect the existing frontmatter list with
  # `while read` rather than mapfile/readarray.
  local -a phases=()
  local phase
  while IFS= read -r phase; do
    [[ -n "$phase" ]] && phases+=("$phase")
  done < <(fm_read_list "$big_plan" "phases")
  if [[ "${#phases[@]}" -eq 0 ]]; then
    failures+=("$big_plan has no phases list")
    return
  fi

  local current_listed=0 prior_completed_count=0 before_current=1
  local small_plan status
  for phase in "${phases[@]}"; do
    if [[ "$phase" == "$current_phase" ]]; then
      current_listed=1
      before_current=0
      continue
    fi
    [[ "$before_current" -eq 1 ]] || continue

    small_plan="$repo_root/.claude/plans/$phase.md"
    if [[ ! -f "$small_plan" ]]; then
      failures+=("missing small-plan file: .claude/plans/$phase.md")
      continue
    fi
    status="$(fm_read_unique_status "$small_plan" || true)"
    if [[ "$status" == "complete" ]]; then
      prior_completed_count=$((prior_completed_count + 1))
    elif [[ "$status" == "cancelled" ]]; then
      assert_cancellation_evidence "$small_plan" "$phase"
    elif [[ "$status" == "$DUPLICATE_STATUS_VALUE" ]]; then
      failures+=("$small_plan must contain exactly one status field before paused checkpoint push")
    else
      failures+=("all phases before current_phase must be complete or evidenced cancelled; $phase is ${status:-missing-status}")
    fi
  done

  if [[ "$current_listed" -ne 1 ]]; then
    failures+=("big plan current_phase must be listed in phases")
    return
  fi

  small_plan="$repo_root/.claude/plans/$current_phase.md"
  if [[ ! -f "$small_plan" ]]; then
    failures+=("missing small-plan file: .claude/plans/$current_phase.md")
    return
  fi
  if [[ "$(fm_read "$small_plan" "type" || true)" != "small-plan" ]]; then
    failures+=("$small_plan must have type: small-plan before paused checkpoint push")
  fi
  if [[ "$(fm_read "$small_plan" "parent_plan" || true)" != "$slug" ]]; then
    failures+=("$small_plan parent_plan must match $slug before paused checkpoint push")
  fi
  status="$(fm_read_unique_status "$small_plan" || true)"
  if [[ "$status" == "$DUPLICATE_STATUS_VALUE" ]]; then
    failures+=("$small_plan must contain exactly one status field before paused checkpoint push")
  elif [[ "$status" != "paused" ]]; then
    failures+=("$small_plan must have status: paused before paused checkpoint push")
  else
    assert_pause_evidence "$small_plan" "$current_phase"
  fi

  local commit_count minimum_commits=$((prior_completed_count + 1))
  commit_count="$(git -C "$repo_root" rev-list --count "dev..$local_sha" 2>/dev/null || echo 0)"
  if [[ ! "$commit_count" =~ ^[0-9]+$ || "$commit_count" -lt "$minimum_commits" ]]; then
    failures+=("paused checkpoint push must have at least $minimum_commits commit(s) beyond dev")
  fi
}

# Public push entry point. A paused current phase may publish a durable remote
# checkpoint; all other states retain the strict final closeout ceremony.
assert_push_invariants() {
  local repo_root="$1"
  local branch="$2"
  local local_sha="$3"
  local slug="${branch%_implementation}"
  local big_plan="$repo_root/.claude/plans/$slug.md"
  local current_phase="" small_plan="" current_status=""

  if [[ -f "$big_plan" ]]; then
    current_phase="$(fm_read "$big_plan" "current_phase" || true)"
    if [[ -n "$current_phase" ]] && is_plan_slug "$current_phase"; then
      small_plan="$repo_root/.claude/plans/$current_phase.md"
      if [[ -f "$small_plan" ]]; then
        current_status="$(fm_read_unique_status "$small_plan" || true)"
      fi
    fi
  fi

  if [[ "$current_status" == "paused" ]]; then
    assert_paused_publication_invariants "$repo_root" "$branch" "$local_sha"
  else
    assert_closeout_invariants "$repo_root" "$branch" "$local_sha"
  fi
}
