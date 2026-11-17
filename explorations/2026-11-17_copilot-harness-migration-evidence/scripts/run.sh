#!/usr/bin/env bash
# Run one spike scenario in a fresh copy of the probe project.
# Usage: run.sh <run-name> <scenario.json> <both|copilot-only|claude-only|probe-only> [camel|pascal|both|remove]
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
vscode="/home/ghisso/.vscode-server/bin/69047191fc427f2f92828279aae1d90d8eeda7ab"
node="$vscode/node"
sdk="$vscode/node_modules/@github/copilot-sdk"
name="$1"
scenario="$2"
sources="$3"
probes="${4:-both}"
project="$here/projects/$name"
rm -rf "$project" "$here/$name" "$here/hooklogs/$name"
mkdir -p "$here/projects"
cp -a "${PROBE_TEMPLATE:-$here/consumer}" "$project"
"$node" "$here/setup_probe_hooks.mjs" "$project" "$here/hooklog.sh" "$probes" > /dev/null
"$node" "$here/toggle_sources.mjs" "$project" "$sources"
printf '%s' "$name" > "$here/current-run"
cd "$here"
timeout 500 "$node" "$here/step3_session.mjs" "$sdk" "$here/home" "$project" "$scenario" "$here/$name"
