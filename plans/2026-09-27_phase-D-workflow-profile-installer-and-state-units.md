---
name: 2026-09-27_phase-D-workflow-profile-installer-and-state-units
type: small-plan
parent_plan: sidecar-workflow-profile
phase_index: 4
status: planned
closeout_session_log:
---

# Small Plan: Phase D — Workflow Profile Installer and State Units

## Scope

Teach the installer and the planner about profiles, the new unit kinds, and
the state folder. Add `--profile`, the manifest `profile` field with schema
version 2, state units that are created once and kept on uninstall,
`--purge-state`, `--backup-state`, the new write roots with the same
precedence rules skills have, profile switching, and profile reuse in
`update_consumers.py` (big plan Decisions 1, 2, 3, 9, and 10). Every
invariant Phase L proved must hold for the new units; the test rules of
that phase apply.

### Required Skills

- `shared/skills/ponytail/SKILL.md` — `full`
- `shared/skills/code-style/SKILL.md`
- `shared/skills/testing-patterns/SKILL.md`
- `shared/skills/safe-consumer-bootstrap-refresh/SKILL.md`
- `shared/skills/debug-investigator/SKILL.md` — for any regression that does not fail as described

## Primary Files

- `scripts/sidecar_overlay.py` — `load_desired_units(source, profile)`,
  manifest schema 2 with `profile`, state units in the planner and the
  apply step, `_skill_name` and precedence over the new single-file roots,
  `required_snapshot_units` over every profile's roots, uninstall keep and
  purge rules, `--backup-state`.
- `scripts/install_bootstrap.py` — `--profile {skills,workflow}`,
  `--purge-state`, `--backup-state`, the `--source` default per profile,
  and the `--mode full` and `--uninstall` messages.
- `scripts/update_consumers.py` — pass no `--profile`; the installer reads
  it from the manifest.
- `tests/test_sidecar_overlay.py`, `tests/test_sidecar_install.py`,
  `tests/test_sidecar_update.py`, `tests/test_sidecar_uninstall.py`,
  `tests/test_install_bootstrap.py`, `tests/sidecar_test_helpers.py`.

## Steps

Test rules: every behavior gets a real-Git test through the CLI or
`install_sidecar` and `uninstall_sidecar`; assert on files, the manifest,
the exclude bytes, the report, and `git status --porcelain --untracked-files=all`;
every scenario runs a second time and asserts nothing changes, and a dry
run predicts the same result.

- [ ] **1. Profile in the manifest and the CLI.**
  - **Owner:** `coder`
  - Manifest `schema_version` 2 adds `profile`; a version-1 manifest parses
    as `skills`. `--profile` defaults to the manifest's profile when a
    manifest exists, else `skills`. `--source` defaults to
    `dist/sidecar/<profile>/`. The planner receives the desired set for the
    chosen profile; a manifest with a different profile is an ordinary
    update. Tests: fresh install per profile; rerun without the flag keeps
    the profile; `--profile` switch in both directions; a version-1
    manifest upgrades in place with no unit change.

- [ ] **2. Single-file units at the new roots.**
  - **Owner:** `coder`
  - Agents, rules, review profiles, and templates are single-file units
    like bridges. `_skill_name` becomes `_unit_name(unit_path)`, returning
    the file stem for single-file units, and precedence runs per unit
    kind: a team file with the same name in any read folder of that kind
    takes the unit. `_ALL_BRIDGES` and `_READ_ONLY_ROOTS` generalize to the
    profile's frozen lists. Tests: a team `.claude/agents/planner.md` takes
    the planner agent at every client root; a team `.claude/rules/ai-bootstrap-workflow.md`
    takes the rule; a team `.claude/settings.json` next to everything is
    never touched; the skills-profile tests pass unchanged.

- [ ] **3. State units.**
  - **Owner:** `coder`
  - A state unit is `.claude/ai-bootstrap/`. Install seeds it from the
    source when absent (all files) and adds any missing seed file when the
    folder exists, never overwriting a present file. Update never
    compares, hashes, or records its contents beyond the seed file names.
    The exclude line is `/.claude/ai-bootstrap`. Uninstall keeps the folder
    and its line by default and prints `kept .claude/ai-bootstrap and its
    exclude line; pass --purge-state to remove it`; `--purge-state` moves
    the folder into the preserved-copy folder as `state--<timestamp>` and
    removes the line. `--backup-state` copies it there without removing
    anything. A tracked path under `.claude/ai-bootstrap/` aborts before
    any write, since the namespace is personal by definition. Tests: seed
    once; a later update leaves an edited `MEMORY.md` and a new plan file
    alone; uninstall keeps and hides; `--purge-state` moves; `--backup-state`
    copies and leaves; `git clean -fdx` followed by an install reseeds and
    the backup survives; a tracked file under the namespace aborts.

- [ ] **4. Uninstall, dry run, and reports for the new kinds.**
  - **Owner:** `coder`
  - Uninstall takes every well-known unit of every profile, as it does
    for retired roots today. Dry run predicts each action. Reports name
    the unit kind ("agent", "rule", "review profile", "template", "state")
    in the SKIPPED, PRESERVED, and RETAINED lines. Empty-folder cleanup
    covers the new roots the sidecar created. Tests per kind and for the
    combined uninstall of a workflow install with a preserved edited agent.

- [ ] **5. Updater.**
  - **Owner:** `coder`
  - `update_consumers.py` forwards no `--profile`; the installer reuses
    the manifest's. Test: a batch with a `skills` consumer, a `workflow`
    consumer, and a full consumer updates each in its own profile.

## Acceptance Criteria

- All Phase L guard tests pass unchanged for the `skills` profile.
- A workflow install into a repository with a team-tracked
  `.claude/settings.json`, team skills, agents, and rules leaves every
  team byte and `git status` unchanged, and reports every skipped unit.
- The state folder rules hold in every scenario of step 3.
- Profile switching converges in both directions and never touches the
  state folder.
- Crash convergence, second-run idempotence, and dry-run parity hold for
  the new unit kinds.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run pytest tests/test_sidecar_overlay.py tests/test_sidecar_install.py tests/test_sidecar_update.py tests/test_sidecar_uninstall.py tests/test_install_bootstrap.py -q --tb=short
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py fast --format json
```

Time the full suite before closeout and compare it with
`COMMAND_TIMEOUT_SECONDS` in `shared/scripts/verify.py`.

## Review Profiles

- `code`
- `architecture`
- `security`
- `tests`
- `ponytail`
- `documentation`

## Closeout Checklist

Follow the fixed closeout order in `shared/policies/workflow.instructions.md`
(Canonical Orchestrator Loop, step 5: CLOSEOUT).

- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
- [ ] Nested plan state checkpointed (`.claude` ai-state) before staging outer-repository files
- [ ] Intended outer files explicitly staged and `git diff --cached` reviewed
- [ ] Every surviving MINOR has an explicit disposition and non-empty reason
- [ ] Review findings resolved and persisted with branch/phase metadata
- [ ] Verification passed (`verify phase` PASS; `verify closeout` runs the plan's required verification items itself and PASS)
