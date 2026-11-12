#!/usr/bin/env bash
# S4: run the server under strace (inside the read-only, no-network sandbox) for one probe.
# Usage: s4_run.sh <label> <calls.json|->   Output: run/<label>/strace.txt
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
label="$1"; calls="$2"
NODEBIN="$(dirname "$(command -v node)")"
mkdir -p "$HERE/run/$label"
cd "$HERE"
python3 -I scripts/mcp_probe.py "raw/mcp/$label.json" codex-mcp-client "$calls" -- \
  bash scripts/cmrun.sh "$label" "$NODEBIN" --nonet --ro -CLAUDE_PROJECT_DIR -- \
  strace -f -qq -s 200 -o "$HERE/run/$label/strace.txt" -e trace=%file,%network,%process,%desc \
  node "$HERE/pkg/node_modules/context-mode/cli.mjs" server --agent codex
