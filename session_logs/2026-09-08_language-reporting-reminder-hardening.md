# Language Reporting Reminder Hardening

**Status:** IN PROGRESS
**Plan:** .claude/plans/2026-09-08_phase-A-language-reporting-reminder-hardening.md

## Goal

Implement the approved one-phase control-plane plan. Keep the shared reporting
policy authoritative and add short, non-blocking reminders only for Claude Code
and OpenAI Codex at prompt start and selected late reporting boundaries.

## Approach

- Preserve existing state synchronization, PostToolUse, and Context Mode handlers.
- Add one canonical reminder script and minimum generator and validation changes.
- Keep GitHub Copilot, Google Antigravity, Gemini CLI, periodic reminders,
  PreCompact behavior, and Stop-based rewriting out of scope.
- Preserve the tracked `AGENTS.md` and `CLAUDE.md` authoring files byte-for-byte
  during self-install verification.

## Rationale

The approved plan addresses reporting drift with bounded context injection at
known lifecycle points. It avoids a second writing authority and avoids recurring
reminders after every tool call.
