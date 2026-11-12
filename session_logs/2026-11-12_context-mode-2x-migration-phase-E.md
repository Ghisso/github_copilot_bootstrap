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
- Required Verification block, orchestrator scratch runner (after the first run): 14 items, 0 failed; `verify.py phase` PASS (318 s).
- Review round 1 (six profiles): gate WARN, no CRITICAL or MAJOR; every evidence range on both pages checked line by line and found correct. Two MINORs: (1) the dispatcher page's description ("stops an untrusted cache from ever being trusted") and its lifecycle-evidence sentence ("No cache is ever searched or cited unless ...") stayed absolute next to the new limit sentence, unlike the README sentence Phase D scoped; (2) the secret Claim states what `state-sync.sh` does but cited no `state-sync.sh` line. Open request: a scoped diff of the `openwiki/` changes.
- Fix loop through OpenWiki, never by hand: second `update` run `413780a0-879a-491c-ac93-0262c9ae0fb7` (restore check empty; 1 page; `openwiki_finish` complete; no `.run.json`). The description now ends "keeps an untrusted cache from being trusted unless a remote replaces the synced scripts themselves"; the sentence now starts "Short of a remote that replaces the synced scripts themselves, no cache is searched or cited ..."; OpenWiki regenerated `operations/index.md` from the new description; the secret Claim now also cites `state-sync.sh#L283-L291` and `#L468-L472`. Scoped diff of all `openwiki/` changes written to the scratchpad (`phaseE-openwiki.diff`, 458 lines) for review round 2. This also follows Phase E's rule that a statement a generated page repeats is fixed by another OpenWiki run.
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

- Review round 2 (same reviewer, six profiles): gate PASS, 0 findings, no open requests. It confirmed both fixes against the scoped diff, that the diff holds only the described changes (the hooks page prose is unchanged; `.page-manifest.json` only re-serialized two unchanged entries), and that no Phase C wording came back.
- Closeout AI state: small plan `status: complete`, boxes ticked, Phase E ticked in the big plan (the post-commit hook sets the big plan `complete`); one documentation lesson in MEMORY.md and below.

## [LEARN] Entries

- [LEARN:documentation] OpenWiki copies each page's `description:` into the generated folder `index.md`, so a wording fix in a description also changes that index; stage and review both. Give a reviewer of generated wiki pages a scoped `git diff -- openwiki/` file, which separates OpenWiki-only changes (timestamps, key reordering) from real edits.

## Verification

- Findings: `.claude/quality_reports/findings-2026-11-12_phase-E-knowledge-refresh.json` (0 findings after review round 2; gate PASS; six profiles; round 1 had two MINORs and one open request, all resolved by the second OpenWiki run and the scoped diff).
- optional 1: PASS — the reviewer read the refreshed prose and every cited range on both pages against the filter, the dispatcher, `state-sync.sh`, `restore-root-adapters.sh`, and the filter tests in two rounds; round 1's two mismatches were fixed by the second OpenWiki run and confirmed in round 2.

## Open Questions / Next Steps

- This is the big plan's last phase. After its commit, opening a PR from `context-mode-2x-migration_implementation` to `dev` is the user's call.
- Recorded follow-ups: refuse every method except `initialize` and `ping` before an accepted `initialize`; check whether VS Code Copilot or Codex send `server/discover`; refresh the five OpenWiki pages with drifted Claim ranges; Codex asks approval for `ctx_index`.
