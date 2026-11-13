# Session: Knowledge refresh and final audit (skills-and-instructions-trim, Phase D)

**Date:** 2026-11-14
**Plan:** `.claude/plans/2026-11-12_phase-D-knowledge-refresh.md`
**Status:** IN-PROGRESS

## Goal

Refresh the OpenWiki pages that describe skills, installer ownership, and the lifecycle through OpenWiki's own tools; run the standing final-phase documentation, memory, and LEARN audit over every live-advice surface; regenerate and self-refresh; record the audit under `## Stale-claims surfaces checked` (REQ-010).

## Work Log

- Phase C committed as `1afc619` and pushed; the post-commit hook set Phase D `in-progress`. Material-impact check: Phases A-C's outcomes are what this phase documents; no planner run. The OpenWiki base is `950dde7` (2026-11-12).
- Read `.claude/skills/knowledge-refresh/SKILL.md` (installed copy) before the refresh. Per MEMORY, no other agent edits tracked files while the OpenWiki run is open; the audit runs after `openwiki_finish`.
- Step 1, OpenWiki refresh (run `d33af114`): `openwiki_begin` with `mode: "update"` opened planning; right after it, `git status --porcelain -- AGENTS.md CLAUDE.md` was empty and neither file held `<!-- OPENWIKI:START -->`. A sweep of every wiki page for stale text found hits only in the seven pages with flagged claims, so the plan was those seven: `architecture/agents-and-skills.md` (37 skills, merges, the 300-character cap, loading rules, project skills, Codex listing from `.agents/skills/`), `architecture/source-generated-consumer-layout.md` (the two new instruction files, the Codex config comment, the validator's new first checks), `operations/deterministic-verification.md` (the closeout file as the written gate, a new "Static checks on the guidance itself" section), `operations/install-ownership-and-runtime-checks.md` (marker, refusals, shipped-before record, mirror, renumbered full-install sequence), `operations/sidecar-overlay.md` (22 workflow skills; marker inert), `workflows/lifecycle-and-task-lanes.md` (three-file split, closeout summary with link, stale-receipt recovery, targeted MEMORY search), and `quickstart.md` (routing rows for closeout, plan lifecycle, and project skills). 31 flagged claims reconciled (revised with current evidence, or confirmed after a recheck), plus new claims for each new fact. `openwiki_finish` returned `complete`; `openwiki/.run.json` absent.
- Step 2, audit: a scripted sweep (`audit_scan.py` in the session scratchpad) over 127 live-advice files for the plan's claim list, then targeted greps for references that send readers to the workflow policy for moved sections. Fixes: `docs/runtime-checks.md:767` (reopening now points at `plan-lifecycle.instructions.md`); `shared/policies/closeout.instructions.md` step 4 now names the full recorder command `uv run python .claude/scripts/record_findings.py` (Phase B optional-1 gap); authoring `AGENTS.md` now says to follow the closeout file at CLOSEOUT (Phase B optional-3 gap); two `.claude/MEMORY.md` entries corrected in place (the closeout-status lesson now names `closeout.instructions.md`; the progressive-disclosure lesson no longer names the retired `caveman-compress` as if current); user-level memory: `feedback_personal_bootstrap_not_generic.md` updated (niche content kept, merged into two skills on 2026-11-13), `project_closeout_order_hooks.md` repointed to the closeout file, new `project_skills_trim.md`, index updated.
- Second OpenWiki run (`632266c5`): the closeout-file fix changed the evidence of two lifecycle-page claims; a one-page update rechecked and confirmed both (no prose change); `openwiki_finish` returned `complete`.
- Step 3: `generate_targets.py --all` exit 0; `install_bootstrap.py . --allow-self --local-only` exit 0, no refusal.

## [LEARN] Entries

## Verification

## Stale-claims surfaces checked

- `CLAUDE.md` (authoring): no stale claim (Phase B already points at the closeout file and uses the targeted MEMORY search).
- `AGENTS.md` (authoring): stale by omission; it named no closeout file. Added "At CLOSEOUT, follow `.claude/instructions/closeout.instructions.md` step by step."
- `README.md`: no stale claim. Line 937 "A full refresh deletes every file under `.claude/` it does not generate" opens the Project-owned skills section and the next sentence gives the marker exception; kept. Retired names, "hidden helpers", 55/25 counts: none.
- Undated `docs/` pages (`architecture.md`, `runtime-checks.md`, `smoke-tests.md`, `target-mapping.md`, and the rest): one stale pointer fixed (`runtime-checks.md:767`, reopening procedure location). `runtime-checks.md:836` correctly keeps the Verification Evidence Contract in the workflow core. `docs/sidecar-provider-contract.md:40` ("Undocumented" duplicate-name behavior for Copilot) is the documentation-tier column of a dated evidence record whose later native-run rows supersede it; left unchanged as a dated record.
- `shared/policies/`: one gap fixed (the closeout file's recorder command lacked its `uv run python .claude/scripts/` prefix). No "loaded into every session", no full MEMORY read, no CLOSEOUT restatement outside the closeout file.
- `shared/skills/`, `shared/agents/`, `shared/templates/`, `shared/review-profiles/`, `shared/sidecar/`: no retired skill name, Completion Protocol, "Never checkpoint after the receipts", or stale closeout location.
- State READMEs (`.claude/plans`, `explorations`, `session_logs`, `quality_reports` and their `shared/` seeds): no stale claim.
- This repository's `.claude/` overlay and `.claude/instructions/project-context.instructions.md`: refreshed by Step 3; no stale claim.
- `.claude/MEMORY.md`: two entries corrected in place (closeout authority; retired skill named as current). The July 2026 "keep niche skills" decision is not in this file; it lives in user-level memory, which was updated.
- The generated Codex config comment and docs repeating the old Codex skills claim: fixed in Phase C; recheck found none.
- Dated records left unchanged: archived plans, explorations, `docs/evidence/`, `docs/2026-*`, closed session logs.

## Open Questions / Next Steps
