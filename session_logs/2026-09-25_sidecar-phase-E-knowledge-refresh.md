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

Audit by `documenter` (steps 3-5), plus the orchestrator's own items from
steps 1-2:

- openwiki/INSTRUCTIONS.md (human-authored brief): corrected by the orchestrator before the refresh; it named `dist/multi-agent/` as the only generated output and described every consumer as receiving the full harness.
- openwiki/ generated pages: refreshed through OpenWiki's MCP tools (5 pages: new sidecar-overlay page; install-ownership, source-generated-consumer-layout, git-backed-ai-state-sync, and quickstart updated); no page hand-edited outside its page job.
- README.md: no stale claim found (Phase D already documents `--mode {full,sidecar}`, mode detection, batch-finishes-every-target, and client support).
- docs/architecture.md: no stale claim found (already describes `dist/sidecar/`, sidecar skill projection, ownership boundaries).
- docs/target-mapping.md: no stale claim found (already has the Sidecar Overlay projection table).
- docs/runtime-checks.md: no stale claim found; it describes only the full-install and dogfood runtime, which sidecar mode never touches, and claims no universality.
- docs/smoke-tests.md: no stale claim found; full-target generation and portability checks only.
- shared/policies/: no stale claim found (no install, update, or consumer-mode references).
- shared/skills/safe-consumer-bootstrap-refresh/SKILL.md: no stale claim found; generic warn-never-fail sync safety.
- shared/skills/setup-project/SKILL.md: no stale claim found; its `install_bootstrap.py` reference documents the default full path for a new project.
- scripts/install_bootstrap.py docstring and `--help`: no stale claim found; both modes and auto-detection documented.
- scripts/update_consumers.py docstring and `--help`: no stale claim found; mixed batches and finish-every-target documented.
- .claude/instructions/project-context.instructions.md: corrected; the Layout section called `dist/multi-agent/` the single generated target and described the installer and updater without modes.
- .claude/MEMORY.md: no stale claim found; the sidecar-phase lessons are present and nothing is superseded.
- CLAUDE.md: no stale claim found.
- AGENTS.md: corrected line 7, which named only `dist/multi-agent/` as generated output; it now also names `dist/sidecar/`. The standard self-refresh (`generate_targets.py --all`, then `install_bootstrap.py . --allow-self --local-only`) resynced `.claude/bootstrap-root/` afterwards.
- docs/plan-deterministic-commit-gate.md: no stale claim found; its installer references are scoped to the commit-gate design.
- docs/native-client-acceptance.md: no stale claim found.
- shared/agents/documenter/prompt.md: no stale claim found (its "sidecar" is OpenWiki's `.claims` sidecar file).
- State READMEs (`shared/*README*`, `.claude/*/README.md`): no stale claim found.
- Dated records (`docs/2026-*`, `plans/architecture-review-2026-07.md`, closed session logs, completed plans): left unchanged by rule.

## [LEARN] Entries

- [LEARN:workflow] Only the main session has the `openwiki` MCP tools; the
  `documenter` agent's tool list has none. A knowledge-refresh phase's
  refresh step is therefore run by the orchestrator itself; delegate only
  the stale-claims audit.
- [LEARN:documentation] `.openwikiignore` excludes `CLAUDE.md`, so
  `openwiki_submit_page` rejects a claim that cites it. Cite `README.md`
  or the code for command and guidance facts instead.

## Verification

Pending.

## Open Questions / Next Steps

- Run the refresh, review the generated diff, run the audit, review, and
  close out the big plan.
