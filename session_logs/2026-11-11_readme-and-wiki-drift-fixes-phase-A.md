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
