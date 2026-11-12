#!/bin/bash
# Optional live check for Phase D: both Claude Code builds, MCP_PROTOCOL_NEGOTIATION=auto, --debug.
# Usage: live_probe_check.sh <label> <claude-binary>
set -u
S=/tmp/claude-1000/-home-ghisso-work-github-copilot-bootstrap/7bec07eb-a588-4e43-bc49-7ba8e1c8dc3b/scratchpad/live
label="$1"; bin="$2"
cp ~/.claude/state/mcp-discover-verdicts.json "$S/verdicts-before-$label.json" 2>/dev/null || echo '{}' > "$S/verdicts-before-$label.json"
rm -f "$S/m-c2s.log" "$S/m-s2c.log"
before=$(ls -t ~/.claude/debug/*.txt 2>/dev/null | head -1)
cd /home/ghisso/work/github_copilot_bootstrap || exit 1
MCP_PROTOCOL_NEGOTIATION=auto PATH="$S/bin:$PATH" timeout 300 "$bin" -p "Call the Context Mode tool ctx_stats once and report its result in one line. If no Context Mode tool is available, say exactly: NO CONTEXT MODE TOOLS." \
  --model haiku --allowedTools "mcp__context-mode__ctx_stats" --output-format text --debug < /dev/null > "$S/live-$label-out.txt" 2>&1
echo "exit=$?"
after=$(ls -t ~/.claude/debug/*.txt 2>/dev/null | head -1)
[[ "$after" != "$before" ]] || echo "WARN: no new debug log"
echo "debug=$after"
grep -a -E 'MCP server "context-mode": (Connection established|Failed to fetch tools)|context-mode" Failed' "$after" | cut -c1-420
echo "--- client to filter (first methods)"
grep -o '"method":"[^"]*"' "$S/m-c2s.log" 2>/dev/null | head -6
echo "--- answer"
head -3 "$S/live-$label-out.txt" | cut -c1-200
cp ~/.claude/state/mcp-discover-verdicts.json "$S/verdicts-after-$label.json" 2>/dev/null || echo '{}' > "$S/verdicts-after-$label.json"
python3 -I -c "
import json,sys
b=json.load(open('$S/verdicts-before-$label.json')); a=json.load(open('$S/verdicts-after-$label.json'))
def keys(d): return set((d.get('verdicts') if isinstance(d.get('verdicts'),dict) else d).keys()) if isinstance(d,dict) else set()
print('verdict entries before', len(keys(b)), 'after', len(keys(a)), 'new', sorted(keys(a)-keys(b)))
"
