---
name: 2026-11-11_phase-A-readme-wording-fixes
type: small-plan
parent_plan: readme-and-wiki-drift-fixes
phase_index: 1
status: in-progress
closeout_session_log:
---

# Small Plan: README Wording Fixes

## Scope

Two `README.md` sentences disagree with the code (found by the 2026-11-11 onboarding refresh). Fix both without changing the file's line count, so wiki claims that cite later README lines keep pointing at the same text.

1. Line 1426 says "All three generated targets (GitHub Copilot, Claude Code, OpenAI Codex)" route Context Mode through the dispatcher. All four generated MCP configs route it there (`dist/multi-agent/.mcp.json`, `.vscode/mcp.json`, `.codex/config.toml`, and `.agents/mcp_config.json`). Antigravity's PreToolUse bridge (`canonical_payload` in `shared/hooks/scripts/antigravity-pretool.py`) denies every tool it does not recognize, which includes every MCP call (`docs/runtime-checks.md` line 113).
2. Line 1391 introduces the "Verification Defaults" commands without saying they assume a consumer project with a `src/` layout. This repository has no `src/`; `verify.py` selects the authoring scope here (`is_bootstrap_authoring_repository` in `shared/scripts/verify.py`).

## Steps

- [ ] **1. Replace the two sentences.**
  - Owner: orchestrator (two exact one-line replacements; no other README text changes).
  - Required Skills: `.claude/skills/documentation/SKILL.md`.
  - Line 1426: replace "All three generated targets (GitHub Copilot, Claude Code, OpenAI Codex) route through the same dispatcher." with "GitHub Copilot, Claude Code, and OpenAI Codex route through the same dispatcher. The fourth generated target, Google Antigravity, gets the same server entry in `.agents/mcp_config.json`, but its PreToolUse bridge denies any tool it does not recognize, including every MCP call, so Antigravity cannot use it (see [runtime-checks.md](docs/runtime-checks.md))."
  - Line 1391: replace "Expected verification commands after implementation:" with "Expected verification commands after implementation, shown for a consumer project with a `src/` layout (this bootstrap repository has no `src/`; the `verify.py` modes below pick the right scope in either repository):"
  - Keep each replacement on its original line: the diff against `dev` is one file with 2 insertions and 2 deletions.

- [ ] **2. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`. The plan changes several files, so it is high-risk; in this phase only `documentation` has content to judge.
  - Focus: each new sentence matches the code it describes, and nothing else changed.

## Verification

```bash
! rg -n -F 'All three generated targets' README.md
rg -n -F 'The fourth generated target, Google Antigravity' README.md
rg -n -F 'shown for a consumer project with a `src/` layout' README.md
test "$(git diff --numstat dev -- README.md | cut -f1,2 | tr '\t' ' ')" = "2 2"
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
```

## Optional Verification

- Read the two new sentences in a rendered Markdown preview and confirm the link to `docs/runtime-checks.md` resolves.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT); the order below mirrors it
rather than restating it.

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)

## Pause Checkpoint

Use only after the user explicitly asks to stop or checkpoint and resume later.
Set `status: paused`, record the three pause fields, and create a session log
with `**Status:** PAUSED`. A checkpoint commit preserves incomplete work; it
does not require final findings, LEARN, DOCUMENT, or a completed closeout.
After the checkpoint commit, it may be pushed as a durable remote backup when
paused-publication invariants pass. It remains unfinished and blocks PR creation
and final closeout.
Keep the big plan `in-progress` with the same `current_phase`. On resume, read
the pause log and Git state, restore this plan to `in-progress`, and continue
this same phase without creating another small plan.
