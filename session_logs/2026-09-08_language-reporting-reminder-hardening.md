# Language Reporting Reminder Hardening

**Status:** PAUSED
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

## Pause reason

The user requested a stop because session usage was nearly exhausted.

## Completed work

- Created `language-reporting-reminder-hardening_implementation` from clean `dev`.
- Added the canonical reporting-policy examples, reminder script, Claude/Codex
  generator wiring, validator checks, focused tests, and current documentation.
- Preserved GitHub Copilot and Google Antigravity hook events and added no Gemini,
  periodic, PreCompact, or Stop-rewriting behavior.
- Regenerated the target and passed structural validation.
- Passed the complete suite: 1,259 tests, Ruff lint, Ruff format, and Mypy.
- Completed self-install and runtime validation. `AGENTS.md` and `CLAUDE.md`
  retained their pre-install SHA-256 hashes.
- Ran the six-profile reviewer twice. The first four MAJOR findings were fixed.
- Ran the native-client probe. Codex and Claude both reported
  `unavailable_untrusted`, so native aggregation is UNVERIFIED.

## Remaining work

- Finish the coder fix for the two surviving review findings:
  - remove the race between phase-completion detection and the parallel
    `record-commit-closeout.sh` handler;
  - reject `git -C`, `--git-dir`, or `--work-tree` commands that target another
    repository.
- Add and pass the corresponding interaction and external-repository tests.
- Regenerate and rerun every verification command from the small plan.
- Repeat the six-profile review until no CRITICAL or MAJOR finding survives.
- Persist final findings, record LEARN evidence, complete the stale-claims audit
  section, run `verify closeout`, and create the single phase-completion commit.

## Verification state

- `scripts/generate_targets.py --all`: PASS before the final interrupted fix.
- `scripts/validate_targets.py`: PASS before the final interrupted fix.
- Full pytest: PASS, 1,259 tests, before the final interrupted fix.
- Ruff lint and format: PASS before the final interrupted fix.
- Mypy: PASS before the final interrupted fix.
- `scripts/check_runtime.py`: PASS before the final interrupted fix.
- Final `verify phase` and `verify closeout`: not run after the latest edits.
- Final reviewer gate: FAIL with two MAJOR findings listed above.

## Incomplete checks

The working tree contains uncommitted implementation and documentation changes.
The interrupted coder may have partially changed validator and tests. Treat all
previous passing checks as stale and rerun them. No outer-repository checkpoint
commit was created. No pull request or merge was created.

## Resume point

Resume this same small plan. Read this log, inspect `git log --oneline -10`,
`git status`, and the current diff, then set the small plan back to
`in-progress` while preserving the pause metadata. Inspect the interrupted
changes in `scripts/validate_targets.py` and `tests/test_lifecycle_hooks.py`
before continuing the two-finding coder fix. Do not create another plan.
