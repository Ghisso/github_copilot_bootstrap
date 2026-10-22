#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=_lib-frontmatter.sh
. "$SCRIPT_DIR/_lib-frontmatter.sh"

TARGET_ID="${1:-unknown-target}"
REPO_ROOT="$(repo_root_from_script)"
INPUT="$(cat)"

# Claude and Codex start sibling matching hooks concurrently.  This one wrapper
# is the ordered safety lane; observability remains a separate best-effort hook.
if ! is_bash_tool_payload "$INPUT"; then
  exit 0
fi

for guard in protect-files.sh git-protection.sh enforce-branch-state.sh enforce-commit-gate.sh enforce-pr-gate.sh; do
  set +e
  output="$(printf '%s' "$INPUT" | bash "$SCRIPT_DIR/$guard" "$TARGET_ID")"
  status=$?
  set -e
  if [[ "$status" -ne 0 ]]; then
    fail_closed "$guard exited with status $status"
  fi
  [[ -z "$output" ]] && continue
  if ! printf '%s' "$output" | python3 -c 'import json,sys; value=json.load(sys.stdin); decision=value.get("hookSpecificOutput", {}).get("permissionDecision"); sys.exit(0 if decision in {"deny", "ask"} else 1)' >/dev/null 2>&1; then
    fail_closed "$guard returned malformed safety output"
  fi
  printf '%s\n' "$output"
  exit 0
done
