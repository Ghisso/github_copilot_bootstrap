#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_lib-frontmatter.sh
. "$SCRIPT_DIR/_lib-frontmatter.sh"

TARGET_ID="${1:-unknown-target}"
REPO_ROOT="$(repo_root_from_script)"
export REPO_ROOT
export TARGET_ID
INPUT="$(cat)"

# An empty/whitespace payload carries no tool call to inspect. Allow it without
# running any check: feeding it to the Python precision pass would exit non-zero
# and spuriously escalate to `ask` while writing an error log into the repo.
if [[ -z "${INPUT//[[:space:]]/}" ]]; then
  exit 0
fi

if ! payload_parseable "$INPUT"; then
  fail_closed "unparseable tool payload"
fi

log_error() {
  local log_dir="$REPO_ROOT/.claude/session_logs"
  mkdir -p "$log_dir" 2>/dev/null || true
  printf '%s WARN protect-files: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" >> "$log_dir/hooks-errors.log" 2>/dev/null || true
}

# Fail toward approval rather than silent allow when we cannot decide safely.
fail_safe() {
  log_error "$1"
  if [[ "$TARGET_ID" == "openai-codex" ]]; then
    deny_pretool "protect-files could not verify the request safely, denying: $1"
  else
    ask_pretool "protect-files could not verify the request safely, approval required: $1"
  fi
  exit 0
}

# --- Pure-bash primary check (no dependency on uv) ---------------------------

pf_normalize() {
  local p="${1//\\//}"
  p="${p#file://}"
  if [[ -n "$REPO_ROOT" && "$p" == "$REPO_ROOT/"* ]]; then p="${p#"$REPO_ROOT"/}"; fi
  while [[ "$p" == ./* ]]; do p="${p#./}"; done
  printf '%s' "$p"
}

pf_is_hook_file() {
  local p
  p="$(pf_normalize "$1")"
  case "$p" in
    .github/hooks/hooks.json|.claude/settings.json|.codex/config.toml|.codex/hooks.json) return 0 ;;
    .github/hooks/*|.claude/hooks/*|.codex/hooks/*) return 0 ;;
    *) return 1 ;;
  esac
}

pf_is_protected() {
  local p base lb
  p="$(pf_normalize "$1")"
  base="${p##*/}"
  lb="${base,,}"
  case "$lb" in
    .env|.env.local) return 0 ;;
    .env.*) return 0 ;;
    *.pem|*.key) return 0 ;;
    credentials*) return 0 ;;
    uv.lock) return 0 ;;
  esac
  [[ "$lb" == *secret* ]] && return 0
  return 1
}

pf_looks_like_path() {
  case "$1" in
    /*|./*|../*|.github/*|.claude/*|.codex/*|.agents/*) return 0 ;;
    */*) return 0 ;;
    *.py|*.json|*.toml|*.md|*.sh|*.lock|*.env|*.pem|*.key) return 0 ;;
    .env|.env.local|uv.lock) return 0 ;;
  esac
  return 1
}

CANDIDATES=()
pf_collect() {
  local input="$1"
  local tool cmd is_bash=0
  tool="$(hook_tool_name_any "$input")"
  tool="${tool,,}"
  cmd="$(hook_command "$input")"
  if [[ -z "$tool" || "$tool" == *bash* || "$tool" == *shell* || "$tool" == "execute" ]]; then
    is_bash=1
  fi

  # apply_patch prefixes live in the command field regardless of tool
  if [[ -n "$cmd" && "$cmd" == *"*** Begin Patch"* ]]; then
    while IFS= read -r line; do
      case "$line" in
        "*** Add File: "*)    CANDIDATES+=("${line#\*\*\* Add File: }") ;;
        "*** Update File: "*) CANDIDATES+=("${line#\*\*\* Update File: }") ;;
        "*** Delete File: "*) CANDIDATES+=("${line#\*\*\* Delete File: }") ;;
        "*** Move to: "*)     CANDIDATES+=("${line#\*\*\* Move to: }") ;;
      esac
    done <<< "$cmd"
  fi

  if [[ "$is_bash" -eq 1 && -n "$cmd" ]]; then
    # Only scan write-bearing commands (mirrors the python bash_write_markers)
    case " $cmd " in
      *" > "*|*">"*|*" touch "*|*" rm "*|*" mv "*|*" cp "*|*" install "*|*" mkdir "*|*" rmdir "*|*" chmod "*|*" chown "*|*" truncate "*|*" tee "*|*" sed "*|*" perl "*) : ;;
      *) return 0 ;;
    esac
    # Redirection targets
    local re='(^|[[:space:]])([0-9]?>{1,2}|&>)[[:space:]]*([^[:space:];&|]+)'
    local work="$cmd"
    while [[ "$work" =~ $re ]]; do
      CANDIDATES+=("${BASH_REMATCH[3]//\"/}")
      work="${work#*"${BASH_REMATCH[0]}"}"
    done
    # General path-like tokens
    local norm="${cmd//[;|&]/ }"
    local -a toks
    read -ra toks <<< "$norm"
    local t st
    for t in "${toks[@]:-}"; do
      st="${t%\"}"; st="${st#\"}"; st="${st%\'}"; st="${st#\'}"
      if pf_looks_like_path "$st"; then CANDIDATES+=("$st"); fi
    done
  elif [[ "$is_bash" -ne 1 ]]; then
    local key v
    for key in path file file_path filepath old_path new_path uri dirpath; do
      v="$(printf '%s' "$input" | json_string_value "$key")"
      if [[ -n "$v" ]]; then CANDIDATES+=("$v"); fi
    done
  fi
}

bash_decision=""
bash_reason=""
pf_scan() {
  pf_collect "$INPUT"
  local c hook_hit="" prot_hit=""
  for c in "${CANDIDATES[@]:-}"; do
    [[ -n "$c" ]] || continue
    if pf_is_hook_file "$c"; then hook_hit="$(pf_normalize "$c")"; fi
    if pf_is_protected "$c"; then prot_hit="$(pf_normalize "$c")"; fi
  done
  if [[ -n "$hook_hit" ]]; then
    if [[ "$TARGET_ID" == "openai-codex" ]]; then
      bash_decision="deny"
      bash_reason="Editing hook files is blocked in Codex because PreToolUse cannot request approval: $hook_hit"
    else
      bash_decision="ask"
      bash_reason="Editing hook files requires approval: $hook_hit"
    fi
  elif [[ -n "$prot_hit" ]]; then
    bash_decision="deny"
    bash_reason="Protected file blocked by policy: $prot_hit"
  fi
}

pf_scan

if [[ "$bash_decision" == "deny" ]]; then
  deny_pretool "$bash_reason"
  exit 0
elif [[ "$bash_decision" == "ask" ]]; then
  ask_pretool "$bash_reason"
  exit 0
fi

# --- Python precision pass (enhancement only, when uv is available) ----------

# uv_available / run_python are single-homed in _lib-frontmatter.sh.
if ! uv_available; then
  exit 0
fi

set +e
OUTPUT="$(printf '%s' "$INPUT" | run_python -c 'import json, os, posixpath, re, shlex, sys

repo_root = os.environ.get("REPO_ROOT", "").rstrip("/")
target_id = os.environ.get("TARGET_ID", "")

try:
  data = json.load(sys.stdin)
except Exception:
  sys.exit(3)

tool_name = str(data.get("tool_name") or data.get("toolName") or "").lower()
tool_input = data.get("tool_input")
if tool_input is None:
  tool_input = data.get("toolArgs")
if isinstance(tool_input, str):
  try:
    tool_input = json.loads(tool_input)
  except Exception:
    tool_input = {}
if not isinstance(tool_input, dict):
  tool_input = {}

is_bash = tool_name in {"bash", "shell"} or tool_name.endswith("bash")
bash_command = str(tool_input.get("command") or "") if is_bash else ""
bash_write_markers = (
  ">", "touch", "rm", "mv", "cp", "install", "mkdir", "rmdir",
  "chmod", "chown", "truncate", "tee", "sed", "perl",
)

mutation_keywords = (
  "edit", "create", "write", "delete", "rename", "move", "replace", "patch", "apply",
)
if tool_name and not any(keyword in tool_name for keyword in mutation_keywords):
  if not is_bash or not any(marker in bash_command for marker in bash_write_markers):
    sys.exit(0)

shell_commands = {
  "cat", "cp", "chmod", "chown", "install", "mkdir", "mv", "perl",
  "printf", "rm", "rmdir", "sed", "tee", "touch", "truncate",
}
shell_operators = {"|", "||", "&&", ";", ">", ">>", ">|", "<", "<<", "<<<", "&>", "2>", "2>>", "1>", "1>>"}

def looks_like_path(value: str) -> bool:
  return (
    value.startswith(("/", "./", "../", ".github/", ".claude/", ".codex/", ".agents/"))
    or "/" in value
    or value.endswith((".py", ".json", ".toml", ".md", ".sh", ".lock", ".env", ".pem", ".key"))
    or value in {".env", ".env.local", "uv.lock"}
  )

def collect_shell_paths(command: str) -> None:
  if not command:
    return
  redirection_pattern = re.compile(r"(?:^|[\s;|&])(?:[0-9]?>{1,2}|&>)\s*([^\s;&|]+)")
  for match in redirection_pattern.finditer(command):
    paths.append(match.group(1).strip("\""))

  for protected_pattern in (
    r"(?<![\w./-])\.env(?:\.[\w.-]+)?(?![\w./-])",
    r"(?<![\w./-])uv\.lock(?![\w./-])",
    r"(?<![\w./-])(?:\.github/hooks/|\.claude/hooks/|\.codex/hooks/)[^\s;&|\x27\"]+",
    r"(?<![\w./-])\.github/hooks/hooks\.json(?![\w./-])",
    r"(?<![\w./-])\.claude/settings\.json(?![\w./-])",
    r"(?<![\w./-])\.codex/(?:config\.toml|hooks\.json)(?![\w./-])",
  ):
    for match in re.finditer(protected_pattern, command):
      paths.append(match.group(0))

  try:
    tokens = shlex.split(command)
  except ValueError:
    tokens = command.replace(";", " ").replace("|", " ").split()

  for index, token in enumerate(tokens):
    stripped = token.strip("\"")
    if not stripped or stripped.startswith("-") or stripped in shell_commands or stripped in shell_operators:
      continue
    previous = tokens[index - 1] if index else ""
    if previous in {">", ">>", ">|", "&>", "2>", "2>>", "1>", "1>>"} or looks_like_path(stripped):
      paths.append(stripped)

path_keys = {
  "path", "file", "filepath", "file_path", "old_path", "new_path", "uri", "files", "dirpath",
}
paths: list[str] = []
patch_prefixes = (
  "*** Add File: ", "*** Update File: ", "*** Delete File: ", "*** Move to: ",
)

def collect_patch_paths(value: str) -> None:
  if "*** Begin Patch" not in value:
    return
  for line in value.splitlines():
    for prefix in patch_prefixes:
      if line.startswith(prefix):
        paths.append(line[len(prefix):].strip())
        break

def collect(value: object, key: str | None = None) -> None:
  if isinstance(value, dict):
    for child_key, child_value in value.items():
      collect(child_value, str(child_key).lower())
    return
  if isinstance(value, list):
    for item in value:
      collect(item, key)
    return
  if not isinstance(value, str):
    return

  collect_patch_paths(value)
  normalized_key = (key or "").lower()
  if normalized_key in path_keys or value.startswith("/") or "/" in value or value.endswith((".py", ".json", ".md", ".sh", ".lock", ".env", ".pem", ".key")):
    paths.append(value)

if is_bash:
  collect_shell_paths(bash_command)
else:
  collect(tool_input)
if not paths:
  sys.exit(0)

def normalize(path: str) -> str:
  candidate = path.replace("\\", "/")
  if candidate.startswith("file://"):
    candidate = candidate[7:]
  if repo_root and candidate.startswith(repo_root + "/"):
    candidate = candidate[len(repo_root) + 1:]
  candidate = posixpath.normpath(candidate)
  if candidate.startswith("./"):
    candidate = candidate[2:]
  return candidate

def is_hook_file(path: str) -> bool:
  hook_config_files = {
    ".github/hooks/hooks.json",
    ".claude/settings.json",
    ".codex/config.toml",
    ".codex/hooks.json",
  }
  hook_dirs = (
    ".github/hooks/",
    ".claude/hooks/",
    ".codex/hooks/",
  )
  return path in hook_config_files or any(path.startswith(prefix) for prefix in hook_dirs)

def is_protected(path: str) -> bool:
  basename = posixpath.basename(path).lower()
  return (
    basename == ".env"
    or basename == ".env.local"
    or basename.startswith(".env.")
    or basename.endswith(".pem")
    or basename.endswith(".key")
    or "secret" in basename
    or basename.startswith("credentials")
    or basename == "uv.lock"
  )

normalized_paths = [normalize(path) for path in paths]
hook_paths = sorted({path for path in normalized_paths if is_hook_file(path)})
protected_paths = sorted({path for path in normalized_paths if is_protected(path)})

if hook_paths:
  hook_list = ", ".join(hook_paths)
  decision = "deny" if target_id == "openai-codex" else "ask"
  reason = (
    f"Editing hook files is blocked in Codex because PreToolUse cannot request approval: {hook_list}"
    if decision == "deny"
    else f"Editing hook files requires approval: {hook_list}"
  )
  print(json.dumps({
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": decision,
      "permissionDecisionReason": reason,
    }
  }, separators=(",", ":")))
  sys.exit(0)

if protected_paths:
  protected_list = ", ".join(protected_paths)
  reason = f"Protected file blocked by policy: {protected_list}"
  print(json.dumps({
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "deny",
      "permissionDecisionReason": reason,
    }
  }, separators=(",", ":")))
')"
PY_RC=$?
set -e

if [[ "$PY_RC" -ne 0 ]]; then
  fail_safe "python precision pass exited with status $PY_RC"
fi

if [[ -n "$OUTPUT" ]]; then
  printf '%s\n' "$OUTPUT"
fi

exit 0
