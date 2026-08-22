# Session: Antigravity installer ownership and native acceptance

**Date:** 2026-08-21
**Plan:** .claude/plans/2026-08-20_phase-C-antigravity-installer-and-native-acceptance.md
**Status:** COMPLETED

## Goal

Complete file-granular `.agents/` ownership, deterministic install/update/restore behavior, final validation and documentation, and native acceptance where the environment permits.

## Work Log

- **01:48 JST** - Phase B committed as `f5151a5`; commit hook advanced the big plan to Phase C. Planner delegation remains skipped under the approved plan and user authorization.
- **02:23 JST** - Completed installer ownership, pruning, mirror/restore, manifest, semantic validation, dogfood, review fix loops, and final documentation. Local Antigravity CLI 1.1.16 initialized in a disposable consumer. Model-backed native acceptance was rejected because it would transmit workspace guidance and metadata to an external service without explicit user authorization.
- **02:45 JST** - User authorized disposable-workspace transmission and completed OAuth. A persisted Antigravity project initially reused the development repository, so that run was rejected as evidence. Forced `--new-project --sandbox` isolation then proved the disposable root and root guidance; orchestrator, planner, canonical coder, and reviewer invocations succeeded. The account quota then blocked Flash coder, verifier, tier, escalation, skills, MCP-use, and native hard-deny checks for about 12 hours.
- **12:20 JST** - After quota reset, `agy` 1.1.17 loaded `antigravity_flash_coder` and `verifier` successfully with minimal exact-response prompts. Both runs used `--new-project --sandbox`; the Flash-coder run also reconfirmed the exact disposable root. Loading does not prove model tier.
- **13:05 JST** - Native compatibility testing showed that a custom main agent cannot invoke a workspace custom subagent in `agy` 1.1.17, while the default native agent can. The approved layout therefore makes the default native agent the main thread through root `AGENTS.md`, sets all custom adapters to `mainAgent: false`, keeps the six specialists as subagents, and leaves the custom `orchestrator` non-delegatable. `manage_task` is allowed only in the PreToolUse bridge for native scheduling; it is not added to custom-agent tools or treated as bootstrap todo capability.
- **13:18 JST** - A fresh `--new-project --sandbox` consumer at `/tmp/antigravity-final-native.y4Nx6j` gave the default agent one tiny prompt. It delegated to `antigravity_flash_coder` and then `coder`, returned exact `F/P`, and completed with `SUCCESS`. A previous `F/P` sequence had ended in `ERROR` only because scheduling was denied; this run confirms the bridge fix. It proves delegation and scheduling, not model tier or the formal automatic Flash-to-Pro escalation contract. `agy mcp list` still reported no configured servers.

## [LEARN] Entries

- [LEARN:security] Antigravity native acceptance must force `--new-project --sandbox` and verify the workspace root before transmitting prompts; this is recorded in `.claude/MEMORY.md`.

## Verification Results

```bash
UV_CACHE_DIR=/tmp/codex-uv-cache uv run python scripts/generate_targets.py --all  # PASS, deterministic twice
UV_CACHE_DIR=/tmp/codex-uv-cache uv run python scripts/validate_targets.py       # PASS
UV_CACHE_DIR=/tmp/codex-uv-cache uv run python scripts/check_runtime.py          # PASS, unrelated legacy-plan warning only
UV_CACHE_DIR=/tmp/codex-uv-cache uv run pytest tests/ -q --tb=short              # 969 passed in 71.16s
UV_CACHE_DIR=/tmp/codex-uv-cache uv run mypy . --ignore-missing-imports --explicit-package-bases  # PASS, 23 files
UV_CACHE_DIR=/tmp/codex-uv-cache uv run ruff check scripts/ tests/               # PASS
UV_CACHE_DIR=/tmp/codex-uv-cache uv run ruff format --check <changed Python files>  # PASS
# Native evidence: agy 1.1.16 authenticated; isolated disposable root and root guidance passed.
# Native agents passed: default native agent with root guidance, planner, coder, reviewer.
# Native agents passed: antigravity_flash_coder and verifier after quota reset.
# Native delegation/scheduling: default agent -> antigravity_flash_coder -> coder returned exact F/P with SUCCESS.
# Remaining native gap: tier evidence, formal escalation proof, bounded Flash-only task, skills, MCP use, and hard-deny checks.
```

## Score: 100 EXCELLENCE

Score report: `.claude/quality_reports/score-20260822T131721+0900.json`.
The matching findings report records zero findings.

## Closeout

Final verification passed: 969 tests in 71.16 seconds, mypy found no issues in
23 source files, and the final score report recorded a clean worktree with a
score of 100 EXCELLENCE. The documented native evidence boundary remains
intentional; this closeout does not turn unobserved tier, skill, MCP, or
hard-deny behavior into native proof.
