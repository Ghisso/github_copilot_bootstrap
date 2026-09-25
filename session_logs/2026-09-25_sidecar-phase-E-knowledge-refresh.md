# Session: Sidecar Phase E — knowledge refresh

**Date:** 2026-09-25
**Plan:** `.claude/plans/2026-09-24_phase-E-sidecar-knowledge-refresh.md`
**Status:** IN-PROGRESS

## Goal

Refresh the OpenWiki knowledge layer for the sidecar lifecycle, then run
the final stale-claims audit across live-advice surfaces for claims that
assume every consumer owns the full harness or that a batch update stops
at the first failure.

## Work Log

- Phase E activated by the Phase D completion commit `faf1b7b` (pushed).
- Material-impact check: no Phase A-D outcome changes this phase's scope.
- Owner change for steps 1-2: only the main session has the `openwiki` MCP
  tools (the `documenter` agent's tool list has none), so the orchestrator
  runs the refresh itself per `.claude/skills/knowledge-refresh/SKILL.md`
  and OpenWiki's own `openwiki` skill. The stale-claims audit (steps 3-5)
  goes to `documenter`.
- Before the refresh, the orchestrator corrected the human-authored brief
  `openwiki/INSTRUCTIONS.md` (a live-advice surface, not a generated page):
  it described `dist/multi-agent/` as the only generated output and every
  consumer as receiving the full harness. It now names both generated
  targets and both install modes, and adds the install modes to the
  minimum coverage list.
- Step 1, refresh: `openwiki_begin` (`mode: "update"`, root
  `/home/ghisso/work/github_copilot_bootstrap`) returned run
  `4abe465d-63c4-4f06-be04-ee62c64ab4bd` in planning, with 16 changed paths
  since base `294382d` and 9 stale claims on 4 pages. Right after it,
  `git status --porcelain -- AGENTS.md CLAUDE.md` was empty (guard
  restored them). Plan: 5 pages. New `/openwiki/operations/sidecar-overlay.md`;
  updated `/openwiki/operations/install-ownership-and-runtime-checks.md`
  (mode section, full-mode sequence, batch skip-and-report),
  `/openwiki/architecture/source-generated-consumer-layout.md` (two targets,
  two consumer layouts, sidecar validator gates),
  `/openwiki/operations/git-backed-ai-state-sync.md` (full installs only),
  `/openwiki/quickstart.md` (routing row and diagram). Every stale claim got
  an explicit decision: revised with the same id (new line ranges, or new
  statements where the fact changed). One submission was rejected because
  `CLAUDE.md` is excluded by `.openwikiignore`; resubmitted without it.
  `openwiki_finish` returned `complete`.
- Step 2, generated diff review: `AGENTS.md`/`CLAUDE.md` unchanged;
  `openwiki/.run.json` removed (and ignored by `.gitignore:38`); no
  `openwiki-update.yml` workflow; the diff is OpenWiki-managed
  (`.claims/`, indexes, `.page-manifest.json`, `.last-update.json`), the
  five pages, and the brief. No generated page was edited outside its page
  job.

## Stale-claims surfaces checked

Pending.

## [LEARN] Entries

Pending.

## Verification

Pending.

## Open Questions / Next Steps

- Run the refresh, review the generated diff, run the audit, review, and
  close out the big plan.
