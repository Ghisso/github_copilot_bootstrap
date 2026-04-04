# Hooks

This directory contains GitHub Copilot hook configuration and scripts.

GitHub Copilot supports repository hooks via `hooks.json` in `.github/hooks/`.

## Implemented Hooks

Configuration file: `.github/hooks/hooks.json`

### preToolUse

- `scripts/protect-files.sh`
- Blocks edits/creates for protected files: `.env`, `.env.*`, `.env.local`, `*.pem`, `*.key`, `*secret*`, `credentials*`, `uv.lock`.
- `scripts/git-protection.sh`
- Blocks dangerous git commands in bash tool calls: `git push --force`, `git push -f`, `git reset --hard`, `git branch -D main`, `git branch -D master`, and `git clean -fd` (including equivalent flag combinations).

### sessionStart / sessionEnd

- `scripts/session-log.sh`
- Appends lifecycle entries to `.github/session_logs/hooks-sessions.log`

### errorOccurred

- `scripts/error-log.sh`
- Appends errors to `.github/session_logs/hooks-errors.log`

## Behavior Notes

- `preToolUse` can deny tool execution by returning JSON with `permissionDecision: "deny"`.
- `postToolUse`, `sessionStart`, `sessionEnd`, and `errorOccurred` are best used for logging and observability.

## Hook Gaps vs Claude Code

Copilot currently does not expose Claude-specific hook events like `PreCompact`, `Stop`, or `Notification`.
Because of that, reminders like verification nudges, context warnings, and session-log cadence are still handled in always-on instructions:

- `.github/instructions/workflow.instructions.md`
