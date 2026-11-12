#!/usr/bin/env bash
# Run a command in a clean environment whose home, config, data, cache, temp,
# and Context Mode variables all point at a scratch run folder.
#
# Usage: cmrun.sh <label> <node-bin-dir> [--nonet] [KEY=VALUE ...] -- cmd args...
#   --nonet   run inside bwrap with no network (loopback only), same uid.
#   --ro      run inside bwrap with the whole filesystem read-only except the run folder
#             (any write outside it fails with EROFS). Combine with --nonet.
#   -KEY      drop variable KEY from the default environment.
#   KEY=VALUE extra variables (override the defaults below).
set -euo pipefail
SCR="$(cd "$(dirname "$0")/.." && pwd)"
label="$1"; shift
nodebin="$1"; shift
nonet=0
ro=0
extra=()
drop=()
while [[ $# -gt 0 && "$1" != "--" ]]; do
  case "$1" in
    --nonet) nonet=1 ;;
    --ro) ro=1 ;;
    -?*) drop+=("${1#-}") ;;
    *=*) extra+=("$1") ;;
    *) echo "cmrun: bad arg $1" >&2; exit 64 ;;
  esac
  shift
done
[[ "${1:-}" == "--" ]] && shift
RUN="$SCR/run/$label"
mkdir -p "$RUN/home/.claude" "$RUN/home/.codex" "$RUN/xdg-config" "$RUN/xdg-data" \
  "$RUN/xdg-cache" "$RUN/xdg-state" "$RUN/tmp" "$RUN/repo"
if [[ ! -d "$RUN/repo/.git" ]]; then
  git init -q "$RUN/repo"
  printf 'capture fixture\n' > "$RUN/repo/README.md"
fi
envs=(
  "HOME=$RUN/home"
  "USER=research"
  "LOGNAME=research"
  "LANG=C.UTF-8"
  "PATH=$nodebin:/usr/bin:/bin"
  "TMPDIR=$RUN/tmp"
  "XDG_CONFIG_HOME=$RUN/xdg-config"
  "XDG_DATA_HOME=$RUN/xdg-data"
  "XDG_CACHE_HOME=$RUN/xdg-cache"
  "XDG_STATE_HOME=$RUN/xdg-state"
  "CONTEXT_MODE_DIR=$RUN/repo/.claude/.cache/context-mode"
  "CONTEXT_MODE_DATA_DIR=$RUN/repo/.claude/.cache/context-mode"
  "CONTEXT_MODE_PROJECT_ROOT=$RUN/repo"
  "CLAUDE_CONFIG_DIR=$RUN/home/.claude"
  "CODEX_HOME=$RUN/home/.codex"
  "CLAUDE_PROJECT_DIR=$RUN/repo"
  "COPILOT_HOME=$RUN/home/.copilot"
  "KIRO_HOME=$RUN/home/.kiro"
  "GEMINI_CLI_HOME=$RUN/home"
  "OPENCODE_CONFIG_DIR=$RUN/xdg-config/opencode"
  "PI_CODING_AGENT_DIR=$RUN/home/.pi/agent"
  "npm_config_cache=$RUN/npm-cache"
)
envs+=("${extra[@]}")
for key in "${drop[@]}"; do
  kept=(); for e in "${envs[@]}"; do [[ "${e%%=*}" == "$key" ]] || kept+=("$e"); done; envs=("${kept[@]}")
done
cd "$RUN/repo"
bw=()
(( nonet )) && bw+=(--unshare-net)
if (( ro )); then
  exec env -i "${envs[@]}" bwrap --ro-bind / / --bind "$RUN" "$RUN" --dev /dev --proc /proc "${bw[@]}" -- "$@"
elif (( nonet )); then
  exec env -i "${envs[@]}" bwrap --dev-bind / / "${bw[@]}" -- "$@"
fi
exec env -i "${envs[@]}" "$@"
