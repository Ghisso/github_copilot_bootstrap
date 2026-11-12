---
name: 2026-11-12_phase-C-knowledge-refresh
type: small-plan
parent_plan: context-mode-2x-migration
phase_index: 3
status: in-progress
closeout_session_log:
---

# Small Plan: Knowledge Refresh and Stale-Claims Audit

## Scope

Refresh the enabled OpenWiki layer through OpenWiki's own MCP tools so that it matches Phases A and B, then run the standing final-phase audit. OpenWiki pages are derived context, not authority; only OpenWiki's lifecycle changes them.

Known stale statements to include in the refresh plan:

- every page that names `1.0.169` as the pin, including `openwiki/operations/context-mode-dispatcher.md` and `openwiki/operations/index.md`;
- every page that describes Context Mode hooks on any client, the advice-only hook filter, the recorded fixtures, or the Claude Code matcher `^(Bash|Read|Grep|WebFetch|mcp__.*)$` (for example `openwiki/architecture/hooks-and-guardrails.md` near line 100);
- every page that lists four Context Mode tools, describes the filter's `serverInfo.version` gate, or calls `CONTEXT_MODE_DIR` Context Mode's own data variable;
- every page that names the devcontainer's Node.js 22 base or an Antigravity Context Mode server.

## Steps

- [ ] **1. Refresh OpenWiki through its own tools.**
  - Owner: orchestrator (only the main session has the OpenWiki MCP tools).
  - Required Skills: `.claude/skills/knowledge-refresh/SKILL.md`, `.claude/skills/openwiki/SKILL.md`.
  - Call `openwiki_begin` with `mode: "update"`. In the planning step, include the pages above plus every page OpenWiki flags. Write each page, reconcile every flagged claim, and require `openwiki_finish` to return `complete`.
  - Right after `openwiki_begin`, run `git status --porcelain -- AGENTS.md CLAUDE.md` (the skill's restore check).
  - On every page the run rewrites, map each cited range from the recorded base (`gitHead` in `openwiki/.last-update.json`) to the current file, and check the text there. Quote any page `description:` that holds a colon.
  - No other agent edits tracked files while the run is open. Never hand-edit a generated page, a `.claims` file, or the root snippet; a wrong page is fixed by another `update` run.

- [ ] **2. Audit live advice for stale claims.**
  - Owner: orchestrator, after `openwiki_finish` returns `complete`; `documenter` for fixes in `README.md`, `docs/`, and `shared/` text. Required Skills: `.claude/skills/documentation/SKILL.md`.
  - This phase is the big plan's last entry, so it runs the standing final-phase documentation, memory, and LEARN audit.
  - Surfaces: `CLAUDE.md`, `AGENTS.md`, `README.md`, undated `docs/` pages, `shared/policies/`, `shared/skills/`, `shared/agents/`, `shared/templates/`, `shared/review-profiles/`, state READMEs, the self-install `.claude/` overlay, `.claude/instructions/project-context.instructions.md`, and `.claude/MEMORY.md`.
  - Claims to look for:
    - `1.0.169` as the current pin;
    - four Context Mode tools, or `ctx_doctor` as an allowed tool;
    - any Context Mode hook, matcher, fixture, or session-continuity claim;
    - the filter's version gate;
    - Node.js 22 in the devcontainer;
    - an Antigravity Context Mode server entry.
  - Correct each live claim found. A fix made after `openwiki_finish` keeps the line count of the text it replaces.
  - Leave dated records unchanged: the 2026-11-11 and pre-branch spike explorations, dated `docs/` notes, archived plans, and closed session logs.
  - The orchestrator also marks its own user-level memory note about the Context Mode Agent matcher as historical. It lives outside the repository.
  - Record each surface and its outcome under the exact heading `## Stale-claims surfaces checked` in this phase's closeout session log.

- [ ] **3. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`.
  - Focus: the refreshed pages match the code they cite; the known statements are fixed; no root adapter carries an OpenWiki block; no `openwiki/.run.json` remains.

## Risks and Fallbacks

- OpenWiki returns `CONNECT_TIMEOUT` right after the host boots. This is a timing issue. Fallback: reconnect with `/mcp` and retry.
- A provider or authentication failure blocks the refresh. Fallback: report OpenWiki's own error, fix it, and retry. The refresh is never skipped.

## Verification

```bash
test "$(grep -r -l -I -F '1.0.169' openwiki --include=*.md | wc -l)" = "0"
grep -r -l -F "$(sed -n 's/^PINNED_CONTEXT_MODE_VERSION="\(.*\)"$/\1/p' shared/hooks/scripts/context-mode-dispatch.sh)" openwiki --include=*.md
test "$(grep -r -l -F 'WebFetch|mcp__.*)$' openwiki --include=*.md | wc -l)" = "0"
test "$(grep -r -l -E 'ctx_index.{0,40}ctx_search.{0,40}ctx_stats.{0,40}ctx_doctor' openwiki --include=*.md | wc -l)" = "0"
test "$(grep -r -l -E 'context-mode-dispatch\.sh (claude-code|openai-codex|github-copilot)' openwiki --include=*.md | wc -l)" = "0"
test ! -e openwiki/.run.json
test "$(cat AGENTS.md CLAUDE.md | grep -c -F '<!-- OPENWIKI:START -->')" = "0"
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

- Read each refreshed page's prose against the code it cites (dispatcher, filter, generator, validator), not only its flagged claims, and record any mismatch.

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
