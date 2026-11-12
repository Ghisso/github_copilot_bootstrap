#!/usr/bin/env bash
# One MCP probe case through cmrun.sh and mcp_probe.py.
# Usage: case.sh <label> <client-name> <calls.json> <cmrun-flags...> -- <upstream args...>
# Env: PKG (package prefix, default pkg), CWD_SUB (subfolder of the run repo to start in).
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
label="$1"; client="$2"; calls="$3"; shift 3
flags=(); while [[ "$1" != "--" ]]; do flags+=("$1"); shift; done; shift
PKG="${PKG:-$HERE/pkg}"
NODEBIN="$(dirname "$(command -v node)")"
mkdir -p "$HERE/raw/mcp"
cd "$HERE"
python3 -I scripts/mcp_probe.py "raw/mcp/$label.json" "$client" "$calls" -- \
  bash scripts/cmrun.sh "$label" "$NODEBIN" "${flags[@]}" -- \
  sh -c 'cd "${CWD_SUB:-.}" && exec "$@"' sh node "$PKG/node_modules/context-mode/cli.mjs" server "$@"
