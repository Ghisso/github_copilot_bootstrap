# Session: README wording fixes

**Date:** 2026-11-11
**Plan:** `.claude/plans/2026-11-11_phase-A-readme-wording-fixes.md`
**Status:** IN-PROGRESS

## Goal

Fix two `README.md` sentences that disagree with the code, without changing the file's line count: Context Mode routing for all four generated targets (line 1426), and the consumer `src/` layout behind the "Verification Defaults" commands (line 1391).

## Work Log

- The user approved the big plan `readme-and-wiki-drift-fixes` on 2026-11-11 ("go" to: one plan, README phase first, then a knowledge-refresh phase).
- Pre-flight: `dev` clean and equal to `origin/dev` after `git fetch`; nested `.claude` clean. Plan lint passed for the three new plan files and the whole plan set.
- Evidence for the new wording, checked before writing: all four generated MCP configs route `context-mode` through `context-mode-dispatch.sh server` (`dist/multi-agent/.mcp.json`, `.vscode/mcp.json`, `.codex/config.toml`, `.agents/mcp_config.json`); `canonical_payload` in `shared/hooks/scripts/antigravity-pretool.py` raises for any tool outside its known sets, and `main` turns that into `deny`, so every MCP call is denied on Antigravity; `is_bootstrap_authoring_repository` in `shared/scripts/verify.py` selects this repository's scope. No validator or test quotes either README passage. `record_findings.py src/` in the same section is valid for a consumer (its first argument is the path the findings apply to), so it stays.
- Branch `readme-and-wiki-drift-fixes_implementation` created from `dev`; the branch hook set the big plan to `in-progress` and activated this phase.
- The plans first named README line 1390 for the "Verification Defaults" sentence; reading the file showed it at line 1391 (heading at 1389, blank line at 1390). Corrected the number in the big plan, both small plans, and this log before editing.
- Implemented (orchestrator, two exact in-place replacements): line 1391 now says the commands are shown for a consumer project with a `src/` layout and that the `verify.py` modes pick the right scope in either repository; line 1426 now says Copilot, Claude Code, and Codex route through the dispatcher, and that Antigravity gets the same server entry but its PreToolUse bridge denies every MCP call. `git diff --numstat dev -- README.md` is `2 2`.
- Focused checks: the stale phrase is gone, both new phrases are present, `validate_targets.py` exit 0, plan lint exit 0, `verify.py fast` NOT_APPLICABLE (no Python changed). Rendered both lines with `markdown-it-py` (temporary `uv run --with`): two links, both targets exist; 27 code spans; no stray backticks.
- Review round 1 (`code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`): gate PASS, no findings, no open requests. The reviewer checked each sentence against the generated configs, the Antigravity bridge, `phase_checks` in `verify.py`, and `docs/runtime-checks.md` line 113.
- CLOSEOUT step 4, first attempt: findings recorded (0 findings, `ponytail_reviewed=true`, gate PASS) and `verify.py phase --persist` PASS (Ruff, mypy, pytest), but the `verify.py closeout` dry run failed: `rg: command not found` (exit 127) on the second required item. The first item, `! rg ...`, had reported PASS only because the negated missing command exits 0. Cause: in the interactive tool shell `rg` is a shell function supplied by Claude Code (`type -t rg` prints `function`), while `verify.py` runs each item with `bash -c`, where only `/usr/bin/grep` exists.
- Fix (back to IMPLEMENT, plan text only; `README.md` unchanged, so the review stands): both small plans now use `grep`, and each absence check is `test "$(grep -c -F '<text>' <file>)" = "0"`. Under `env -i PATH="$PATH" bash -c` all four phase A text checks exit 0; negative controls: the absence check exits 1 against a file that contains the phrase and exits 1 with `grep` unavailable, while the old `! grep ...` form exits 0 with `grep` unavailable.

## [LEARN] Entries

- [LEARN:verification] Never use `rg` in a plan's `## Verification` block. `verify.py closeout` runs each required item with `bash -c`, where Claude Code's `rg` (a shell function from the session snapshot, not a program on `PATH`) does not exist, and a negated item such as `! rg ...` then exits 0 and passes without checking anything. Use `grep`, and write an absence check as `test "$(grep -c -F '<text>' <file>)" = "0"`, which also fails when `grep` itself fails.

## Verification

```text
# filled in from verify closeout --format text at CLOSEOUT step 4
```

- optional 1: PASS — rendered lines 1391 and 1426 with `markdown-it-py`: both links (`shared/hooks/scripts/context-mode-dispatch.sh`, `docs/runtime-checks.md`) resolve to existing files from the README location, 27 code spans render, and no stray backtick remains.

## Open Questions / Next Steps

- Phase B: refresh OpenWiki (three known stale statements, plus every page OpenWiki flags) and run the final-phase audit.
