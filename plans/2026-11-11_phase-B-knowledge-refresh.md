---
name: 2026-11-11_phase-B-knowledge-refresh
type: small-plan
parent_plan: readme-and-wiki-drift-fixes
phase_index: 2
status: complete
closeout_session_log: .claude/session_logs/2026-11-11_readme-and-wiki-drift-fixes-phase-B.md
---

# Small Plan: Knowledge Refresh and Stale-Claims Audit

## Scope

Refresh the enabled OpenWiki layer through OpenWiki's own MCP tools so it matches PR #52, PR #53, and phase A, then run the standing final-phase audit. OpenWiki pages are derived context, not authority; only OpenWiki's lifecycle changes them.

Known stale statements (recorded by the PR #52 and PR #53 audits and the 2026-11-11 onboarding refresh):

- `openwiki/architecture/hooks-and-guardrails.md` line 88 says the Context Mode PreToolUse group matches `*` on both Claude Code and Codex. Since PR #53, Claude Code uses `^(Bash|Read|Grep|WebFetch|mcp__.*)$` (`CLAUDE_CONTEXT_MODE_MATCHER` in `scripts/generate_targets.py`); Codex keeps `*`.
- `openwiki/workflows/lifecycle-and-task-lanes.md` line 115 ("across every completed phase") and `openwiki/operations/deterministic-verification.md` near line 157 ("walks every earlier completed phase") omit PR #52's exception: the push and PR checks skip a plan's leading run of phases dated before 2026-08-29 that have no receipt file (`RECEIPT_CHAIN_SINCE` and `leading_pre_receipt_count` in `shared/scripts/verify.py`).
- Any page whose claims cite `README.md` line 1391 or line 1426, which phase A changed.

## Steps

- [x] **1. Refresh OpenWiki through its own tools.**
  - Owner: orchestrator (only the main session has the OpenWiki MCP tools).
  - Required Skills: `.claude/skills/knowledge-refresh/SKILL.md`, `.claude/skills/openwiki/SKILL.md`.
  - Call `openwiki_begin` with `mode: "update"`. In the planning step, include the three pages above plus every page OpenWiki flags. Write each page, reconcile every flagged claim, and require `openwiki_finish` to return `complete`. Right after `openwiki_begin`, run `git status --porcelain -- AGENTS.md CLAUDE.md` (the skill's restore check).
  - On every page the run rewrites, map each cited range from the recorded base (`gitHead` in `openwiki/.last-update.json`) to the current file and check the text there. Quote any page `description:` that holds a colon.
  - No other agent edits tracked files while the run is open. Never hand-edit a generated page, a `.claims` file, or the root snippet; a wrong page is fixed by another `update` run.

- [x] **2. Audit live advice for stale claims.**
  - Owner: orchestrator, after `openwiki_finish` returns `complete`.
  - This phase is the big plan's last entry, so it runs the standing final-phase documentation, memory, and LEARN audit. Surfaces: `CLAUDE.md`, `AGENTS.md`, `README.md`, undated `docs/`, `shared/policies/`, `shared/skills/`, `shared/agents/`, `shared/templates/`, `shared/review-profiles/`, state READMEs, `.claude/instructions/project-context.instructions.md`, and `.claude/MEMORY.md`.
  - Claims to look for: Context Mode routing described for "three" generated targets; a Claude Code Context Mode PreToolUse matcher of `*`; a receipt-chain check said to cover every completed phase with no exception.
  - Correct each live claim found. A fix made after `openwiki_finish` keeps the line count of the text it replaces. Leave dated records unchanged.
  - Record each surface and its outcome under the exact heading `## Stale-claims surfaces checked` in this phase's closeout session log.

- [x] **3. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`.
  - Focus: the refreshed pages match the code they cite; the three known statements are fixed; no root adapter carries an OpenWiki block; no `openwiki/.run.json` remains.

## Verification

```bash
test "$(grep -c -F '`*` runs only the optional' openwiki/architecture/hooks-and-guardrails.md)" = "0"
grep -n -F 'mcp__.*)$' openwiki/architecture/hooks-and-guardrails.md
grep -n -F '2026-08-29' openwiki/workflows/lifecycle-and-task-lanes.md
grep -n -F '2026-08-29' openwiki/operations/deterministic-verification.md
test ! -e openwiki/.run.json
git diff --quiet dev -- AGENTS.md CLAUDE.md
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
```

## Optional Verification

- Read each refreshed page's prose against the code it cites (generator, verifier, hooks), not only its flagged claims, and record any mismatch.

## Closeout Checklist

Follow the fixed closeout order in `.claude/instructions/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT); the order below mirrors it
rather than restating it.

- [x] Documentation updated or explicitly skipped as pure-internal
- [x] LEARN entries saved or no-lessons marker recorded
- [x] Closeout session log has `**Status:** COMPLETED`
- [x] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [x] Intended outer files explicitly staged and `git diff --cached` reviewed
- [x] Every surviving MINOR has an explicit disposition and non-empty reason
- [x] Review findings resolved and persisted with branch/phase metadata
- [x] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)

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
