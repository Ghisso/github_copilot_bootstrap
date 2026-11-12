# Session: Knowledge refresh and stale-claims audit after the reopen (migration Phase E)

**Date:** 2026-11-12
**Plan:** `.claude/plans/2026-11-12_phase-E-knowledge-refresh.md`
**Status:** IN-PROGRESS

## Goal

Refresh OpenWiki through its own MCP tools so it matches Phase D (the filter answers `server/discover` itself with `-32601`; the provenance-secret wording states only what the scripts do), then run the standing final-phase documentation, memory, and LEARN audit for the whole big plan.

## Work Log

- Phase D committed as `950dde7` and pushed; the post-commit hook set this phase `in-progress` and `current_phase` to it.
- Material-impact check: no Phase D finding affects this phase; no planner run. The Finding 3 unit stays (the user kept it).
- Step 1: `openwiki_begin` (`mode: "update"`) started run `81571c3d-77ff-4a00-bf9a-75f7987d2960` at base `3f2f48d` for the five pages Phase C refreshed; the restore check (`git status --porcelain -- AGENTS.md CLAUDE.md`) printed nothing. OpenWiki flagged 4 Claim issues, all on `operations/context-mode-dispatcher.md`.
- Before writing, mapped every Claim that cites a file Phase D changed from `3f2f48d` to the current files (scratch `map_claims.py`): 21 ranges on the dispatcher page moved (dispatcher comment edits shifted lines by 1-2; the filter's new branch shifted lines after 145 by 14), and one on `architecture/hooks-and-guardrails.md` (the legacy no-op, now `context-mode-dispatch.sh#L331-L336`).
- Plan submitted with 2 pages:
  - `operations/context-mode-dispatcher.md`: new "Discovery probe answered locally" bullet (the probe, why 2.1.8's answer would leave the client without tools, `-32601`, the id-less drop, never forwarded before or after `initialize`, the fallback, and the 2026-07-28-only limit); the secret sentence now says `state-sync.sh` adds and commits only under `.claude/`, the root restore copies only allowlisted adapter files, and this gives no protection against a remote that replaces the synced scripts (the "neither read nor plant" wording is gone); the test bullets add the three probe tests and the real-binary probe. Claims: 14 revised (13 re-pointed to moved lines, the secret Claim restated), 1 confirmed (`kitTool` descriptions), 1 new (the probe rule).
  - `architecture/hooks-and-guardrails.md`: prose unchanged; the legacy no-op Claim re-pointed.
- `openwiki_finish` returned `complete`; no `openwiki/.run.json`; `.last-update.json` records the run.
- Step 2 audit: see `## Stale-claims surfaces checked`. No tracked live surface needed a fix after the refresh, so no second OpenWiki run was needed for audit fixes. The orchestrator's user-level memory note about the 2.x plan now records the reopen, Phase D's fix, the live check, and the follow-ups.

## Stale-claims surfaces checked

- `CLAUDE.md`, `AGENTS.md`: clean (no handshake, secret, tool-count, or hook claims).
- `README.md`: clean after Phase D (the `server/discover` sentence; the secret paragraph states the add-and-commit rule, the allowlist, and the limit, and its last clause is scoped to the same limit; no "ever", "neither read nor plant", or "never adds, commits, or restores").
- Undated `docs/` pages (`architecture.md`, `runtime-checks.md`, `smoke-tests.md`, `target-mapping.md`, `native-client-acceptance.md`, `plan-deterministic-commit-gate.md`, `sidecar-provider-contract.md`): clean; `runtime-checks.md` has the probe sentence and the 2026-07-28-only known limit; no page says every other MCP method passes through unchanged.
- Dated records (`docs/2026-*.md`, `docs/evidence/`, root `plans/`, the 2026-11-11, pre-branch, and live-check explorations, archived plans, and the logs, findings, and receipts of Phases A to D): left unchanged, apart from the dated Correction sections Phase D appended to the live-check report and the quality report.
- `shared/policies/`, `shared/skills/`, `shared/agents/`, `shared/templates/`, `shared/review-profiles/`, state READMEs, `shared/MEMORY.md`: clean (the only "other method" hit is an unrelated testing skill sentence).
- Self-install `.claude/` overlay: regenerated from `shared/` in Phase D Step 7; same sweep clean.
- `.claude/instructions/project-context.instructions.md`: clean; Phase D added the `server/discover` clause; no "neither read nor plant" or tool-count claim.
- `.claude/MEMORY.md`: the wrong pipelined-`tools/list` lesson was corrected in place in Phase D; the 1.x hook-output entry (historical upstream behavior, with the Phase A note) is still accurate; no other stale claim.
- User-level memory outside the repository: `project_docs_drift_and_cm2_plan.md` and its index line updated with the reopen and Phase D.
- OpenWiki: refreshed in Step 1; afterwards `1.0.169` in 0 pages, `fixtures/context_mode` in 0 pages, `neither read nor plant` in 0 pages, `server/discover` named on the dispatcher page. Not refreshed (recorded follow-up, Finding 4): five pages outside these runs with drifted Claim ranges and correct prose.

## [LEARN] Entries

- (filled at closeout)

## Verification

(filled at closeout)

## Open Questions / Next Steps

- Step 3 review, then closeout; this is the big plan's last phase.
