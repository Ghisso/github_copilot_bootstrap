---
name: 2026-11-12_phase-E-knowledge-refresh
type: small-plan
parent_plan: context-mode-2x-migration
phase_index: 5
status: complete
closeout_session_log: .claude/session_logs/2026-11-12_context-mode-2x-migration-phase-E.md
---

# Small Plan: Knowledge Refresh and Stale-Claims Audit After the Reopen

## Scope

Phase D made the MCP filter answer the 2026-07-28 `server/discover` probe itself and, unless its separable Finding 3 unit was dropped, corrected three overstated comments and one README sentence. This phase refreshes the enabled OpenWiki layer through OpenWiki's own MCP tools so that it matches, then runs the standing final-phase audit again. OpenWiki pages are derived context, not authority; only OpenWiki's lifecycle changes them.

This phase is now the big plan's last entry. The plan was reopened on 2026-11-12 (`.claude/quality_reports/2026-11-12_context-mode-2x-live-check-findings.md`). Phase C, the earlier knowledge-refresh phase, stays complete where it is; the plan validator no longer counts it, because its small plan is complete.

Items marked "Finding 3 unit" go with Phase D's Step 5. When the user drops that step, the orchestrator drops these items too.

Known stale statements to include in the refresh plan:

- `openwiki/operations/context-mode-dispatcher.md`, the "Identity gate" and "Reduced `initialize`" bullets (near lines 78-79): add that the filter answers `server/discover` itself with `-32601` and never forwards it, so a client that speaks both MCP revisions falls back to `initialize`. The `-32001` rule there stays true.
- The same page, the test bullets (near lines 130-131): add the probe cases; the real-binary test now sends the probe before `initialize`.
- Finding 3 unit: the same page, near line 114: "so a hostile remote can neither read nor plant the secret" overstates it. `state-sync.sh` and the restore script are themselves synced through ai-state. State only what the scripts do, as Phase D's dispatcher comments do.
- Every other page OpenWiki flags for the Phase D diff. The five pages with drifted line ranges (Finding 4 of the quality report) are refreshed only when OpenWiki flags them; this phase does not add them by hand.

## Steps

- [x] **1. Refresh OpenWiki through its own tools.**
  - Owner: orchestrator (only the main session has the OpenWiki MCP tools).
  - Required Skills: `.claude/skills/knowledge-refresh/SKILL.md`, `.claude/skills/openwiki/SKILL.md`.
  - Call `openwiki_begin` with `mode: "update"`. In the planning step, include the page above plus every page OpenWiki flags. Write each page, reconcile every flagged claim, and require `openwiki_finish` to return `complete`.
  - Right after `openwiki_begin`, run `git status --porcelain -- AGENTS.md CLAUDE.md` (the skill's restore check).
  - On every page the run rewrites, map each cited range from the recorded base (`gitHead` in `openwiki/.last-update.json`) to the current file, and check the text there. Quote any page `description:` that holds a colon.
  - No other agent edits tracked files while the run is open. Never hand-edit a generated page, a `.claims` file, or the root snippet; a wrong page is fixed by another `update` run.

- [x] **2. Audit live advice for stale claims.**
  - Owner: orchestrator, after `openwiki_finish` returns `complete`; `documenter` for fixes in `README.md`, `docs/`, and `shared/` text. Required Skills: `.claude/skills/documentation/SKILL.md`.
  - This phase is the big plan's last entry, so it runs the standing final-phase documentation, memory, and LEARN audit. The sweep is not limited to Phase D's changes.
  - Surfaces: `CLAUDE.md`, `AGENTS.md`, `README.md`, undated `docs/` pages, `shared/policies/`, `shared/skills/`, `shared/agents/`, `shared/templates/`, `shared/review-profiles/`, state READMEs, the self-install `.claude/` overlay, `.claude/instructions/project-context.instructions.md`, and `.claude/MEMORY.md`.
  - Claims to look for:
    - every MCP method other than `initialize`, `tools/list`, and `tools/call` passes through unchanged (`server/discover` is now answered by the filter);
    - Context Mode 2.1.8 does not implement `server/discover` (it does, for a request that carries the 2026-07-28 `_meta`);
    - Finding 3 unit: the provenance secret is safe from a hostile ai-state remote, or `state-sync.sh` never adds, commits, or restores anything outside `.claude/`;
    - Finding 3 unit: the kit tool descriptions name no other tool (the `ctx_search` text names `ctx_index`);
    - Phase C's list, which must still be absent: `1.0.169` as the current pin; four Context Mode tools, or `ctx_doctor` as an allowed tool; any Context Mode hook, matcher, fixture, or session-continuity claim; the filter's version gate; Node.js 22 in the devcontainer; an Antigravity Context Mode server entry.
  - Correct each live claim found.
    - When the audit changes a statement that a generated OpenWiki page repeats, run another OpenWiki `update` for the affected pages, never a hand edit, and review its diff.
    - A fix that no generated page repeats, made after `openwiki_finish`, keeps the line count of the text it replaces. This rule protects the pages' cited line positions, not their meaning, so it applies only to such fixes.
  - Leave dated records unchanged, apart from the correction sections Phase D appended: the 2026-11-12 live-check exploration and quality report, the 2026-11-11 and pre-branch spike explorations, dated `docs/` notes, archived plans, and the small plans, closeout logs, findings, and receipts of Phases A to D.
  - The orchestrator also checks its user-level memory notes about the Context Mode 2.x plan, which live outside the repository, and records there that the plan was reopened and what Phase D fixed.
  - Record each surface and its outcome under the exact heading `## Stale-claims surfaces checked` in this phase's closeout session log.

- [x] **3. Review.**
  - Owner: `reviewer`. Review Profiles: `code`, `architecture`, `security`, `tests`, `ponytail`, `documentation`.
  - Focus: the refreshed pages match the code they cite, above all the `server/discover` handling against `handleClient`; the known statements are fixed; Phase C's fixes have not come back; any audit fix that a page repeats went through another OpenWiki `update`; no root adapter carries an OpenWiki block; no `openwiki/.run.json` remains.

## Risks and Fallbacks

- OpenWiki returns `CONNECT_TIMEOUT` right after the host boots. This is a timing issue. Fallback: reconnect with `/mcp` and retry.
- A provider or authentication failure blocks the refresh. Fallback: report OpenWiki's own error, fix it, and retry. The refresh is never skipped.
- OpenWiki flags more pages than the dispatcher page, for example the Finding 4 pages. Handle each flagged claim in the same run; do not add pages by hand.
- The `server/discover` check in Verification looks for that method name on the dispatcher page. A correct page that describes the probe without naming the method fails it. Fallback: run another `update` that names the method, as the filter code does; never edit the page by hand. The other wording checks look only for exact known stale phrases.

## Verification

```bash
test "$(grep -r -l -I -F '1.0.169' openwiki --include=*.md | wc -l)" = "0"
PIN="$(sed -n 's/^PINNED_CONTEXT_MODE_VERSION="\(.*\)"$/\1/p' shared/hooks/scripts/context-mode-dispatch.sh)" && test -n "$PIN" && grep -r -l -F "$PIN" openwiki --include=*.md
test "$(grep -r -l -F 'WebFetch|mcp__.*)$' openwiki --include=*.md | wc -l)" = "0"
test "$(grep -r -l -E 'ctx_index.{0,40}ctx_search.{0,40}ctx_stats.{0,40}ctx_doctor' openwiki --include=*.md | wc -l)" = "0"
test "$(grep -r -l -E 'context-mode-dispatch\.sh (claude-code|openai-codex|github-copilot)' openwiki --include=*.md | wc -l)" = "0"
test "$(grep -r -l -F 'fixtures/context_mode' openwiki --include=*.md | wc -l)" = "0"
grep -q -F 'server/discover' openwiki/operations/context-mode-dispatcher.md
# Finding 3 unit: drop the next two lines when Phase D's Step 5 is dropped.
test "$(grep -r -l -F 'neither read nor plant' openwiki --include=*.md | wc -l)" = "0"
# Regression-only: no wiki page carries this phrase today; it keeps the README's old wording from coming back.
test "$(grep -r -l -F 'never adds, commits, or restores' openwiki --include=*.md | wc -l)" = "0"
# End of the Finding 3 unit.
test ! -e openwiki/.run.json
test "$(cat AGENTS.md CLAUDE.md | grep -c -F '<!-- OPENWIKI:START -->')" = "0"
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py phase --format text
```

## Optional Verification

- Read each refreshed page's prose against the code it cites (filter, dispatcher, filter tests), not only its flagged claims, and record any mismatch.

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
