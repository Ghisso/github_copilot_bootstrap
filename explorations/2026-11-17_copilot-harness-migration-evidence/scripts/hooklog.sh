#!/usr/bin/env bash
# Probe hook: record the label, working directory, selected environment, and stdin.
# By default it prints nothing and exits 0.
#
# Scripted replies: when stdin contains "PROBE-REPLY:<tag>", or a file
# replies/<run>/_always.<label>.reply exists, the hook answers with the files
#   replies/<run>/<tag>.<label>.reply   (stdout)
#   replies/<run>/<tag>.<label>.stderr  (stderr)
#   replies/<run>/<tag>.<label>.exit    (exit code)
#   replies/<run>/<tag>.<label>.sleep   (seconds to wait first)
set -u
label="${1:-unlabelled}"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
run="$(cat "$here/current-run" 2>/dev/null || echo default)"
dir="$here/hooklogs/$run"
mkdir -p "$dir"
stamp="$(date +%s%N)"
out="$dir/${stamp}-${label}.log"
input="$(cat)"
{
  printf 'label=%s\n' "$label"
  printf 'pwd=%s\n' "$PWD"
  printf 'argv=%s\n' "$*"
  env | grep -E '^(COPILOT|CLAUDE|GITHUB_COPILOT|VSCODE|HOOK)[A-Z0-9_]*=' | sed -E 's/(TOKEN|SECRET|KEY)=.*/\1=<redacted>/' | sort
  printf 'stdin=%s\n' "$input"
} > "$out" 2>&1

reply_dir="$here/replies/$run"
tag="$(printf '%s' "$input" | grep -oE 'PROBE-REPLY:[a-z0-9-]+' | head -n 1 | cut -d: -f2)"
base=""
if [[ -n "$tag" && ( -f "$reply_dir/$tag.$label.reply" || -f "$reply_dir/$tag.$label.exit" || -f "$reply_dir/$tag.$label.sleep" || -f "$reply_dir/$tag.$label.stderr" ) ]]; then
  base="$reply_dir/$tag.$label"
elif [[ -f "$reply_dir/_always.$label.reply" ]]; then
  base="$reply_dir/_always.$label"
fi
if [[ -n "$base" && -f "$base.unless" ]] && printf '%s' "$input" | grep -qF "$(cat "$base.unless")"; then
  printf 'reply-skipped=%s\n' "$(basename "$base")" >> "$out"
  base=""
fi
if [[ -n "$base" ]]; then
  printf 'replied-with=%s\n' "$(basename "$base")" >> "$out"
  [[ -f "$base.sleep" ]] && sleep "$(cat "$base.sleep")"
  [[ -f "$base.reply" ]] && cat "$base.reply"
  [[ -f "$base.stderr" ]] && cat "$base.stderr" >&2
  [[ -f "$base.exit" ]] && exit "$(cat "$base.exit")"
fi
exit 0
