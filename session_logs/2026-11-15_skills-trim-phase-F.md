# Session: Installer safety and project-skill guidance (skills-and-instructions-trim, Phase F)

**Date:** 2026-11-15
**Plan:** `.claude/plans/2026-11-14_phase-F-installer-safety.md`
**Status:** IN-PROGRESS

## Goal

Fix review findings R13 to R22 (`.claude/quality_reports/merges/2026-11-14_skills-and-instructions-trim-review-claude.md`): no write through a symlink anywhere in a full refresh, a refusal for an unmarked folder whose name is newly shipped, an honest no-record refusal, a robust mirror, a stray-marker check, an explanation for stale `.agents/` content on a second clone, learn and refresh-skill guidance, installer docs, and the mirror-update test (REQ-012).

## Work Log

- Phase E committed as `4aa49d4` and pushed; the post-commit hook set Phase F `in-progress` and moved `current_phase`. Material-impact check: Phase E changed only guidance, validators, and docs; nothing in it changes Phase F's installer design, so no planner run. Phase F starts from the plan as revised after the devil's-advocate review (big plan Decisions 8 to 11).

## [LEARN] Entries

## Verification

## Open Questions / Next Steps
