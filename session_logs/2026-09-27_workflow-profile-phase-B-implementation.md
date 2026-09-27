# Session: Workflow profile Phase B — implementation

**Date:** 2026-09-27
**Plan:** `.claude/plans/2026-09-27_phase-B-workflow-profile-implementation.md`
**Status:** IN PROGRESS

## Goal

Make the workflow profile installable: profile constants, rendering of
`dist/sidecar/workflow/` with `dist/sidecar/skills/` byte-identical to
today's output, the validator per profile, `--profile` and the manifest
profile field, the new single-file unit kinds with today's precedence
rules, the state folder with its create-once and keep-on-uninstall rules,
`--purge-state`, `--backup-state`, profile switching, the updater's reuse,
README and docs, the end-to-end scenario test, and a manual run against a
clone of a real consumer.

## Work Log

- PRE-FLIGHT: Phase A committed as `3cf7871` and pushed; the post-commit
  hook set Phase B to `in-progress`. Outer tree clean. Inputs from Phase
  A: the frozen coverage (Claude Code: agents, rules, review profiles,
  templates, skills, state; Copilot: the instructions file and skills;
  Codex: skills and state), the 24 eligible skills, the complete
  `workflow-prompt.md` per agent (Decision 6 as amended), and the note
  that the canonical session-log and quality-report templates name the
  verifier.

## [LEARN] Entries

(pending)

## Verification

(pending)

## Documentation

(pending)

## Open Questions / Next Steps

(pending)
