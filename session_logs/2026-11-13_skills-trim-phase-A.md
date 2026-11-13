# Session: Project-owned skills (skills-and-instructions-trim, Phase A)

**Date:** 2026-11-13
**Plan:** `.claude/plans/2026-11-12_phase-A-project-owned-skills.md`
**Status:** IN-PROGRESS

## Goal

Let a consumer project keep its own skills across full-install refreshes: a `.claude/skills/<name>/` folder holding a regular `.project-skill` file is never deleted or overwritten, is mirrored without the marker to `.agents/skills/<name>/`, and unsafe or unmarked never-shipped skill folders are refused before any write (REQ-001).

## Work Log

- Approval: the user asked to implement the whole big plan on 2026-11-13. That approves the plan and its seven "Decisions for the user" as written.
- PRE-FLIGHT: `dev` clean in both repositories at `cfde280`; plan files read; MEMORY searched by area (installer, closeout, generation, OpenWiki, branch hook) through Context Mode.
- Pre-branch spike: `.claude/explorations/2026-11-12_skills-trim-client-spike/REPORT.md`. S1 success (55 shipped skills listed once from `.agents/skills/`; config-only run lists none), S3 recorded (891-character description shown cut to 404 characters), S4 success (`spike-project-skill` listed once), S5 working control with no baseline warning (`--bare` could not authenticate; `--setting-sources project` ran). No plan change before the branch.
- BRANCH: `git checkout -b skills-and-instructions-trim_implementation`; the hook set the big plan `in-progress` (`started_at: 2026-11-13T11:54:23Z`) and Phase A `in-progress`.

## [LEARN] Entries

## Verification

## Open Questions / Next Steps
