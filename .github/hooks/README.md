# Hooks

This directory contains GitHub Copilot hook configuration and scripts.

GitHub Copilot supports repository hooks via `hooks.json` in `.github/hooks/`.

## Implemented Hooks

Configuration file: `.github/hooks/hooks.json`

### `PreToolUse`

- `scripts/protect-files.sh`
- Denies writes to protected files: `.env`, `.env.*`, `.env.local`, `*.pem`, `*.key`, `*secret*`, `credentials*`, `uv.lock`.
- Detects protected paths in structured write tools, patches, and Bash write commands such as redirection or `touch`.
- Requires approval (`ask`) before editing `.github/hooks/**` so agents cannot silently rewrite their own enforcement.
- `scripts/git-protection.sh`
- Denies destructive git commands in terminal-style tool calls, including force-push, `git reset --hard`, `git checkout --`, `git restore --source`, deleting `main`/`master`, and `git clean -fd` variants.

### `SessionStart` / `Stop`

- `scripts/session-log.sh`
- Appends lifecycle entries to `.github/session_logs/hooks-sessions.log`

## Native VS Code Hook Contract

These hooks use VS Code's native workspace hook contract:

- PascalCase event names (`SessionStart`, `PreToolUse`, `Stop`)
- `command` and `timeout` fields in `hooks.json`
- `hookSpecificOutput.permissionDecision` for `PreToolUse` allow/ask/deny decisions

The previous Claude/Copilot-CLI-compatible shape mostly loaded, but it was too brittle
for reliable enforcement in VS Code.

## Behavior Notes

- `PreToolUse` can deny or require approval for a single tool call.
- `SessionStart` and `Stop` are used only for lightweight logging.
- There is intentionally no `PostToolUse` hook here.

## Hook Gaps vs Claude Code

Not every Claude/Copilot CLI pattern maps cleanly to VS Code hooks, and some
older examples use different payload field names. For repo policy and workflow nudges,
always-on instructions still carry most of the guidance:

- `.github/instructions/workflow.instructions.md`
