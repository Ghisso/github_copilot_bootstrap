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
- Step 1 (profile constants) done by the orchestrator to unblock parallel
  work: `scripts/runtime_ownership.py` gained `SIDECAR_PROFILES`,
  `SIDECAR_WORKFLOW_SKILLS` (24), `SIDECAR_PROFILE_SKILLS`,
  `SIDECAR_WORKFLOW_AGENTS`, `SIDECAR_WORKFLOW_RULES`,
  `SIDECAR_WORKFLOW_REVIEW_PROFILES`, `SIDECAR_WORKFLOW_TEMPLATES`,
  `SIDECAR_PROFILE_FILE_UNITS` (23 workflow units), `SIDECAR_STATE_ROOT`,
  `SIDECAR_STATE_SEED_FILES`, `SIDECAR_PROFILE_STATE_ROOT`,
  `SIDECAR_FILE_UNIT_READ_ROOTS`, and a `profile` parameter on
  `sidecar_source_exact_allowlist` and `sidecar_source_violations`
  (skills allowlist 14 paths, workflow 80). ruff, format, mypy clean; the
  only failing test is the determinism check, because `dist/multi-agent/`
  embeds a copy of the module and is stale until regenerated.
- `documenter` authored the two relaxed templates,
  `shared/sidecar/workflow/templates/session-log.md` (36 lines) and
  `quality-report.md` (29 lines), grep clean.
- IMPLEMENT fan-out on disjoint files: `coder` A owns the generator, the
  validator, and their tests (steps 2 and 3); `coder` B owns
  `sidecar_overlay.py`, `install_bootstrap.py`, `update_consumers.py`,
  and the sidecar and installer tests (steps 4 to 7). Coder B builds
  fixture sources until coder A's `dist/sidecar/<profile>/` layout lands.

## [LEARN] Entries

(pending)

## Verification

(pending)

## Documentation

(pending)

## Open Questions / Next Steps

(pending)
