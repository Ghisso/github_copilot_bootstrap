---
name: readme-and-wiki-drift-fixes
type: big-plan
status: in-progress
originating_branch: dev
implementation_branch: readme-and-wiki-drift-fixes_implementation
started_at: 2026-11-11T14:29:35Z
phases:
  - 2026-11-11_phase-A-readme-wording-fixes
  - 2026-11-11_phase-B-knowledge-refresh
current_phase: 2026-11-11_phase-B-knowledge-refresh
---

# Big Plan: README and Wiki Drift Fixes

## Context

The 2026-11-11 onboarding refresh (`.claude/instructions/project-context.instructions.md`, "Known documentation/status caveats") found two `README.md` sentences that disagree with the code. The PR #52 and PR #53 closeout audits recorded three OpenWiki statements that they left stale, because a one-phase plan gets no knowledge-refresh phase. On 2026-11-11 the user approved fixing both in one plan with two phases, README first, so the refresh reads the corrected README.

## Goals

- `README.md` line 1426 describes Context Mode routing for all four generated targets correctly.
- `README.md` line 1391 says the "Verification Defaults" commands assume a consumer project with a `src/` layout.
- The three stale OpenWiki statements describe the current code: the Claude Code Context Mode PreToolUse matcher (PR #53) and the receipt-chain exception for a plan's leading phases dated before 2026-08-29 (PR #52).

## Non-Goals and Constraints

- No code, hook, generator, policy, or test changes. No edits to consumer repositories.
- `README.md` keeps its line count, so wiki claims that cite later README lines keep pointing at the same text.
- OpenWiki pages change only through OpenWiki's own MCP lifecycle with `mode: "update"`. Never hand-edit a generated page, a `.claims` file, or the root snippet.
- The Context Mode 2.x upgrade is a separate plan.
- Lane: the plan changes several files, so it is control-plane/high-risk under the Task Lanes table. Review uses `code`, `architecture`, `security`, `tests`, `ponytail`, and `documentation`.

## Design Overview

Phase A replaces two `README.md` lines in place. Phase B runs one OpenWiki `update` run whose plan names the three known stale pages plus every page OpenWiki flags, then the standing final-phase audit.

## Phases

- [x] `2026-11-11_phase-A-readme-wording-fixes` — two README sentences.
- [x] `2026-11-11_phase-B-knowledge-refresh` — OpenWiki refresh and the final-phase audit.

## Verification

```bash
uv run python scripts/validate_plan_frontmatter.py .claude/plans/readme-and-wiki-drift-fixes.md .claude/plans/2026-11-11_phase-A-readme-wording-fixes.md .claude/plans/2026-11-11_phase-B-knowledge-refresh.md
```

## Completion Evidence

The last phase, `2026-11-11_phase-B-knowledge-refresh`, runs the documentation, memory, and LEARN audit across all live-advice surfaces and records each surface and its outcome under `## Stale-claims surfaces checked` in its closeout session log. Each phase has its own verification, review, findings, session log, commit, and normal push.
