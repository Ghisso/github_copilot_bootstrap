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
- Both coders were stopped by the organization's monthly spend limit
  (HTTP 429; the session limit resets at 22:00 Asia/Tokyo). Coder A had
  sent its final report: layout `dist/sidecar/skills/` and
  `dist/sidecar/workflow/`, `render_sidecar(target_root, profile)`,
  `render_sidecar_workflow_units`, `claude_agent_frontmatter` extracted
  and reused, the validator per profile with adversarial cases, 18 new
  tests, and a snapshot hash proving the skills profile is byte-identical
  to the pre-change output; it reported six open findings (extra files in
  larger skills rejected by the exact allowlist, `mcp__` tool grants in
  the agents' frontmatter, full-install references in the plan templates,
  `ponytail.md`, and one skill, and no `.claude/instructions/` token).
  Coder B was stopped before writing tests but had implemented steps 4 to
  7: `--profile`, `--purge-state`, `--backup-state`, manifest schema 2
  with `profile`, `read_sidecar_profile`, `_unit_name` and the file-unit
  kinds with precedence, `_classify_state_unit`, `backup_sidecar_state`,
  and the updater; the tree was lint and type clean and 512 tests passed.
- Orchestrator closed coder A's findings directly (usage constraint):
  `sidecar_source_violations` and `sidecar_allowed_relative_path` allow any
  file inside a shipped skill folder (a skill is copied whole) while
  keeping the exact set elsewhere; `sidecar_agent_frontmatter` strips
  `mcp__*` tool grants and the validator compares against it; the
  workflow path replacements gained the two `.claude/instructions/`
  policy paths and apply to skills text too; all four templates ship from
  `shared/sidecar/workflow/templates/`, the two plan templates derived
  from the canonical ones with the verifier, receipt, and checkpoint
  passages replaced; `.claude/instructions/` joined the workflow forbidden
  tokens; the validator's stray-file case moved outside a skill folder.
  `validate_targets.py` PASS.
- Orchestrator ran the manual scenario against a fresh clone of
  `schema-bootstrap-llm-wiki` with a team-tracked `.claude/settings.json`,
  team `ponytail` skill, team `reviewer` agent, and team rule. It found
  three defects in coder B's unfinished work and fixed them:
  `_validate_unit_path` did not accept the state root, so the parser kept
  `/.claude/ai-bootstrap` as a person's line and appended a copy every
  run; uninstall crashed with `KeyError: 'state_kept'` because the state
  unit entered the taken-outcome conversion (now excluded from
  `taken_units`); and `_uninstall_final_exclude_text` removed the block
  with the kept state line (now keeps the block whenever one of the
  sidecar's own lines survives, judged without the person's lines, so a
  block holding only user lines is still written back plain). Two stale
  tests updated (agent frontmatter now `sidecar_agent_frontmatter`; the
  crafted-source stray file sits outside a skill folder).
- Manual run, final transcript (every step `git status --porcelain
  --untracked-files=all` unchanged): dry run predicts 69 installs and
  writes nothing; install 69 with `SKIPPED .claude/agents/reviewer.md`
  and `SKIPPED .claude/skills/ponytail` (team-owned), state seeded; rerun
  `unchanged 68` with an edited `MEMORY.md` and a new plan left alone;
  `--profile skills` removes the workflow units and keeps the state
  hidden; `--profile workflow` restores them; `--backup-state` copies to
  `state--<timestamp>`; `--uninstall` keeps the state folder and its line
  (`RETAINED .claude/ai-bootstrap: kept ...`); `--uninstall --purge-state`
  moves it (`PRESERVED .claude/ai-bootstrap -> ...`) and removes the
  block; reinstall reseeds. Focused suites: 690 passed; ruff, format,
  mypy clean.
- Step 9 documentation delegated to `documenter`; the scenario test (step
  8) written by the orchestrator from the proven run script.
- Step 9 done by `documenter`: README (Profiles table and commands, what
  the workflow profile adds, the relaxed loop with a diagram, the state
  folder rules and the `git clean -x` risk, profile switching, the report
  table rows for state, the uninstall paragraphs), `docs/target-mapping.md`
  (the two profile trees, seven unit rows, manifest schema 2), and
  `docs/architecture.md` (one paragraph). Every quoted message verified
  against the code by the documenter.
- Step 8, `tests/test_sidecar_workflow_scenario.py` (orchestrator): the
  life-cycle test (dry run, install with team-taken agent and skill, state
  seeded, personal edits survive a rerun and a deleted seed is re-added,
  switch down and up, backup, uninstall keeps, second uninstall no-op,
  purge, reinstall reseeds), a tracked path under the namespace aborting
  before any write, and `git clean -fdx` losing the state while the backup
  survives and a reinstall reseeds. It exposed two more defects, fixed:
  the empty-folder cleanup list lacked `.claude/agents`,
  `.claude/review-profiles`, and `.claude/templates` and ran only on
  uninstall (now also at the end of an install, so a profile switch leaves
  no empty folder); and `state_backup_slug` named the destination by a
  per-second timestamp, so a backup and an uninstall in the same second
  collided and read as a preserve conflict (now the slug appends `-2`,
  `-3`, ... while the name exists). The three tests run in about two
  seconds. Focused suites: 693 passed; ruff, format, mypy clean;
  `validate_targets.py` PASS.

## [LEARN] Entries

(pending)

## Verification

(pending)

## Documentation

(pending)

## Open Questions / Next Steps

(pending)
