#!/usr/bin/env bash
# Write the small text outputs that the report cites into raw/.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$1"
raw="$here/raw"
rm -rf "$raw"
mkdir -p "$raw"
py() { (cd "$repo" && uv run python "$@"); }
home="$here/home"
py "$here/summarize_discover.py" "$here/discover-untrusted.json" "$here/consumer" "$home" > "$raw/discover-before-trust.txt"
py "$here/show_tools.py" "$here/discover-untrusted.json" > "$raw/built-in-tools.txt"
py "$here/show_hooks_mcp.py" "$here/run0/summary.json" "$here/consumer" "$home" > "$raw/discover-after-trust-hooks-and-mcp.txt"
for run in g-both g-copilot g-claude d1 c1 s1 a1; do
  py "$here/show_outcomes.py" "$here/$run" "$here/projects/$run" "$home" > "$raw/outcomes-$run.txt"
done
py "$here/show_timing.py" "$here/g-both" "$here/g-copilot" "$here/g-claude" > "$raw/hook-timing.txt"
py "$here/show_hooklogs.py" "$here/hooklogs/g-copilot" "$here/projects/g-copilot" "$home" > "$raw/hook-inputs-first-per-event.txt"
py "$here/show_hooklogs.py" "$here/hooklogs/c1" "$here/projects/c1" "$home" reToolUse --all > "$raw/hook-inputs-patch-tool.txt"
py "$here/show_hooklogs.py" "$here/hooklogs/s1" "$here/projects/s1" "$home" ubagent > "$raw/hook-inputs-subagent-events.txt"
py "$here/show_hooklogs.py" "$here/hooklogs/l1" "$here/projects/l1" "$home" claudelocal > "$raw/hook-inputs-from-claude-settings.txt"
py "$here/show_children.py" "$here/s1" "$here/projects/s1" > "$raw/subagent-context.txt"
py "$here/check_instructions.py" "$here/g-copilot" "$here/projects/g-copilot" > "$raw/instructions-in-system-prompt.txt"
py "$here/show_model.py" "$here/g-copilot" "$here/projects/g-copilot" "$home" > "$raw/model-requests-g-copilot.txt"
py "$here/show_model.py" "$here/d1" "$here/projects/d1" "$home" > "$raw/model-requests-d1-context.txt"
vscode="/home/ghisso/.vscode-server/bin/69047191fc427f2f92828279aae1d90d8eeda7ab"
(cd "$here" && timeout 170 "$vscode/node" step4_tools_by_model.mjs "$vscode/node_modules/@github/copilot-sdk" "$home") > "$raw/tools-by-model.txt" 2>&1
tail -n 12 "$here/projects/c1/.claude/session_logs/hooks-errors.log" > "$raw/guard-errors-patch-tool.txt"
tail -n 8 "$here/projects/g-both/.claude/session_logs/hooks-sessions.log" > "$raw/session-log-double-entries.txt"
# Keep machine paths out of the saved outputs.
sed -i -e "s|$here|<spike>|g" -e "s|/home/[a-z0-9_-]*|<user-home>|g" -e "s|/mnt/c/Users/[^/;\"]*|<windows-home>|g" "$raw"/*.txt
wc -c "$raw"/*.txt | tail -n 30
