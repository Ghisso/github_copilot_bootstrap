# Session: Sidecar Phase I — hardening knowledge refresh

**Date:** 2026-09-26
**Plan:** `.claude/plans/2026-09-25_phase-I-sidecar-hardening-knowledge-refresh.md`
**Status:** IN-PROGRESS

## Goal

The big plan's final knowledge-refresh phase after the reopen (Decision 21):
refresh OpenWiki against Phases F-H, then run the standing final-phase
documentation, memory, and LEARN audit.

## Work Log

- Phase I activated by the Phase H completion commit `f7d9af4` (pushed).
- Material-impact check: Phases F-H changed the plan validator and the
  workflow text (F), the sidecar planner and ownership rules (G), and
  preflight, bytes-safety, sources, `--uninstall`, and the docs (H). This
  phase's scope already names these topics. No change.
- Owner for steps 1-2: only the main session has the `openwiki` MCP tools,
  so the orchestrator runs the refresh itself (MEMORY LEARN from Phase E).
  The stale-claims audit (steps 3-4) goes to `documenter`.
- Before the refresh, the orchestrator added team precedence, the
  preserved-copy folder, and `--uninstall` to the sidecar coverage item in
  the human-authored brief `openwiki/INSTRUCTIONS.md`.
- Step 1, refresh: `openwiki_begin` (`mode: "update"`) returned run
  `648c59de-72d9-46f6-a234-48b7bcf44eaa` in planning, with 21 changed paths
  since `faf1b7b` and 23 stale or unresolved claims on 6 pages. Right after
  it, `git status --porcelain -- AGENTS.md CLAUDE.md` was empty (the guard
  restored them). The other four pages mention none of the changed topics.
  The plan covered 6 pages:
  - `source-generated-consumer-layout`: the exact sidecar source set shared
    by the validator and the installer;
  - `git-backed-ai-state-sync`: uninstall also skips state sync;
  - `install-ownership-and-runtime-checks`: the environment scrub,
    submodule and gitlink rules, Git-error abort, `LC_ALL=C`,
    `require_source_exists`, `require_full_source_complete`, and
    `--uninstall` dispatch;
  - `sidecar-overlay`: rewritten for preflight, index ownership, team
    precedence, preserved copies, block parsing, the folder gate,
    bytes-safety, uninstall, and the removal of manual removal steps;
  - `lifecycle-and-task-lanes`: the knowledge-refresh exemption and the
    reopening procedure;
  - `quickstart`: routing rows for uninstall, preserved copies, and
    reopening.
  Every stale or unresolved claim was revised with current evidence
  (including the two known stale claims, `229e75d4` and `e46454b4`). Two
  current claims whose line ranges had moved were revised too, and new
  claims were added for the new behavior. `openwiki_finish` returned
  `complete`, `openwiki/.run.json` is absent, and `.last-update.json`
  records `f7d9af4`.
- Step 2, diff review: 16 OpenWiki files changed (6 pages, their claim
  files, the manifest and index, and the brief). No page was hand-edited
  outside the page loop.
- Orchestrator notes for the audit, found while researching pages:
  - `README.md` around line 627 still says the installer proves paths
    ignored "before writing anything"; it should say before any sidecar
    file is written.
  - The docstring of `_sidecar_source_violations`
    (`scripts/sidecar_overlay.py:1676-1681`) still describes the old,
    weaker check.
  - The linked-worktree refusal message in `detect_install_mode` gives the
    old reason ("its own Git directory, separate from the main worktree's
    shared one").

## Stale-claims surfaces checked

## [LEARN] Entries

## Verification

## Documentation

## Open Questions / Next Steps
