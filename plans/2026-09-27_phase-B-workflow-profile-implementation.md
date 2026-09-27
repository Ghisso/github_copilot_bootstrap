---
name: 2026-09-27_phase-B-workflow-profile-implementation
type: small-plan
parent_plan: sidecar-workflow-profile
phase_index: 2
status: planned
closeout_session_log:
---

# Small Plan: Phase B — Workflow Profile Implementation

## Scope

All the code and its documentation in one phase: profile constants,
rendering of `dist/sidecar/workflow/` with `dist/sidecar/skills/` kept
byte-identical to today's output, the validator's per-profile allowlist
and forbidden tokens, `--profile` and the manifest profile field, the new
single-file unit kinds with today's precedence rules, the state folder with
its create-once and keep-on-uninstall rules, `--purge-state`,
`--backup-state`, profile switching, the updater's profile reuse, the
README and docs, an end-to-end scenario test, and a manual run against a
clone of a real consumer (big plan Decisions 1, 2, 3, 6, 8, 9, 10, and 11).
Every invariant Phase L of the first sidecar plan proved must hold for the
new units, and that phase's test rules apply.

### Required Skills

- `shared/skills/ponytail/SKILL.md` — `full`
- `shared/skills/code-style/SKILL.md`
- `shared/skills/testing-patterns/SKILL.md`
- `shared/skills/safe-consumer-bootstrap-refresh/SKILL.md`
- `shared/skills/debug-investigator/SKILL.md` — for any regression that does not fail as described
- `shared/skills/documentation/SKILL.md` — step 9

## Primary Files

- `scripts/runtime_ownership.py` — `SIDECAR_PROFILES` and per-profile
  skills, unit roots, single-file units with frontmatter, state root and
  seeds, write roots, read roots, and the shared source contract.
- `scripts/generate_targets.py` — `render_sidecar(target_root, profile)`,
  agent rendering with the workflow supplement, rules and instructions
  rendering, state seeds.
- `scripts/validate_targets.py` — per-profile allowlist, forbidden tokens,
  completeness, adversarial self-tests.
- `scripts/sidecar_overlay.py` — `load_desired_units(source, profile)`,
  manifest schema 2 with `profile`, state units, `_unit_name`, precedence
  over the new roots, `required_snapshot_units` over every profile's
  roots, uninstall keep and purge rules, `--backup-state`.
- `scripts/install_bootstrap.py` — `--profile {skills,workflow}`,
  `--purge-state`, `--backup-state`, the `--source` default per profile,
  messages.
- `scripts/update_consumers.py` — passes no `--profile`.
- `tests/test_validate_targets.py`, `tests/test_sidecar_overlay.py`,
  `tests/test_sidecar_install.py`, `tests/test_sidecar_update.py`,
  `tests/test_sidecar_uninstall.py`, `tests/test_install_bootstrap.py`,
  `tests/sidecar_test_helpers.py`, `tests/test_sidecar_workflow_scenario.py`
  (new).
- `README.md`, `docs/target-mapping.md`, `docs/architecture.md`,
  `docs/sidecar-provider-contract.md` — step 9.

## Steps

Test rules: every behavior gets a real-Git test through the CLI or
`install_sidecar` and `uninstall_sidecar`; assert on files, the manifest,
the exclude bytes, the report, and `git status --porcelain --untracked-files=all`;
every scenario runs a second time and asserts nothing changes, and a dry
run predicts the same result. Coders working in parallel run `ruff format`
only on their own files.

- [ ] **1. Profile constants.**
  - **Owner:** `coder`
  - `SIDECAR_PROFILES = ("skills", "workflow")`; per profile: skills (the
    four, or every public skill minus `shared/sidecar/workflow/skills.txt`,
    frozen into a checked-in list that a test compares with the skills
    folder), single-file units per verified client with their frontmatter
    (bridges, rules, agents, review profiles, templates), the state root
    `.claude/ai-bootstrap` and its seed file names, write roots, and read
    roots from Phase A's frozen table. `sidecar_source_violations(present, profile)`
    takes the profile. Today's constants keep their names as the `skills`
    profile.

- [ ] **2. Rendering.**
  - **Owner:** `coder`
  - `generate` renders `dist/sidecar/skills/` and `dist/sidecar/workflow/`;
    the `skills` output is byte-identical to today's `dist/sidecar/`
    (snapshot-hash test). The `workflow` output: eligible skills at both
    write roots with replacements and licenses; agents per verified client
    from the canonical prompt plus `workflow-supplement.md` through the
    existing provider adapters; `.claude/rules/ai-bootstrap-*.md`; the
    Copilot instructions file with `applyTo: "**"`; review profiles and
    templates with the path rewrite to `.claude/ai-bootstrap/`; the state
    seeds.

- [ ] **3. Validator per profile.**
  - **Owner:** `coder`
  - `sidecar_allowed_relative_path(path, profile)`,
    `sidecar_text_errors(path, text, profile)`,
    `sidecar_target_errors(root, profile)`. The workflow forbidden list
    keeps every current token except `MEMORY.md` and adds `settings.json`,
    `core.hooksPath`, `ai-state`, `state-sync`, and `.claude/plans/`.
    Adversarial self-tests per profile: a disallowed path, a leaked token,
    a missing unit, an extra unit, a rule without the `ai-bootstrap-`
    prefix, an agent text naming a receipt. Determinism for both profiles.

- [ ] **4. Profile in the manifest and the CLI.**
  - **Owner:** `coder`
  - Manifest `schema_version` 2 adds `profile`; a version-1 manifest
    parses as `skills`. `--profile` defaults to the manifest's profile,
    else `skills`. `--source` defaults to `dist/sidecar/<profile>/`. A
    manifest with a different profile than the flag is an ordinary
    update. Tests: fresh install per profile; rerun without the flag keeps
    the profile; switch both ways; a version-1 manifest upgrades in place
    with no unit change.

- [ ] **5. Single-file units at the new roots.**
  - **Owner:** `coder`
  - Agents, rules, review profiles, and templates are single-file units
    like bridges. `_skill_name` becomes `_unit_name(unit_path)` (file stem
    for single-file units); precedence runs per unit kind: a team file
    with the same name in any read folder of that kind takes the unit.
    `_ALL_BRIDGES` and `_READ_ONLY_ROOTS` generalize to the profile's
    frozen lists. Tests: a team `.claude/agents/planner.md` takes the
    planner at every client root; a team `.claude/rules/ai-bootstrap-workflow.md`
    takes the rule; a team `.claude/settings.json` next to everything is
    never touched; every skills-profile test passes unchanged.

- [ ] **6. State units.**
  - **Owner:** `coder`
  - The state unit is `.claude/ai-bootstrap/`. Install seeds it when
    absent and adds a missing seed file when the folder exists, never
    overwriting a present file. Update never compares, hashes, or records
    its contents beyond seed file names. The exclude line is
    `/.claude/ai-bootstrap`. Uninstall keeps the folder and its line and
    prints `kept .claude/ai-bootstrap and its exclude line; pass --purge-state to remove it`;
    `--purge-state` moves it into the preserved-copy folder as
    `state--<timestamp>` and removes the line; `--backup-state` copies it
    there and removes nothing. A tracked path under `.claude/ai-bootstrap/`
    aborts before any write. Tests: seed once; a later update leaves an
    edited `MEMORY.md` and a new plan alone; uninstall keeps and hides;
    purge moves; backup copies; `git clean -fdx` then install reseeds and
    the backup survives; a tracked file under the namespace aborts.

- [ ] **7. Uninstall, dry run, reports, and the updater.**
  - **Owner:** `coder`
  - Uninstall takes every well-known unit of every profile. Dry run
    predicts each action. Reports name the unit kind ("agent", "rule",
    "review profile", "template", "state"). Empty-folder cleanup covers the
    new roots the sidecar created. `update_consumers.py` forwards no
    `--profile`. Tests per kind, a combined uninstall of a workflow install
    with a preserved edited agent, and a batch with a `skills` consumer, a
    `workflow` consumer, and a full consumer.

- [ ] **8. End-to-end scenario test.**
  - **Owner:** `coder`
  - `tests/test_sidecar_workflow_scenario.py`: a team repository from a
    fixture with a tracked `.claude/settings.json`, a tracked team skill,
    agent, and rule, and code; install `--profile workflow`; status
    unchanged, every unit present, team units reported as taken, state
    seeded; write a plan and a session log; update with a second bootstrap
    version that drops one skill and changes one agent; state untouched;
    switch to `skills` and back; `--backup-state`; `--uninstall` keeps the
    state; `--uninstall --purge-state` moves it; reinstall reseeds. Every
    step runs `--dry-run` first and asserts parity. Under 60 seconds.

- [ ] **9. Documentation and the manual run.**
  - **Owner:** `documenter` for the docs; `orchestrator` for the run
  - README sidecar section: profiles, what the workflow profile ships per
    client, the state folder rules, `--purge-state`, `--backup-state`, the
    `git clean -x` risk, profile switching, and the relaxed loop, quoting
    every message the installer prints and stating that the profile
    enforces nothing. `docs/target-mapping.md` and `docs/architecture.md`:
    the profile trees and unit kinds. `docs/sidecar-provider-contract.md`:
    link the frozen matrix to the shipped coverage. Then clone one of the
    maintainer's consumers into the scratchpad, commit a
    `.claude/settings.json` there as a team would, run the scenario's CLI
    steps by hand, and record the transcript in the closeout session log.
    Never touch the source project.

## Acceptance Criteria

- `dist/sidecar/skills/` equals today's `dist/sidecar/` byte for byte,
  and every Phase L guard test passes unchanged.
- The validator passes with both profiles and fails each adversarial
  case; no workflow text names a forbidden token.
- A workflow install into a repository with a team-tracked
  `.claude/settings.json`, team skills, agents, and rules leaves every
  team byte and `git status` unchanged and reports every skipped unit.
- The state folder rules hold in every scenario of step 6; profile
  switching converges both ways and never touches the state folder.
- Crash convergence, second-run idempotence, and dry-run parity hold for
  the new unit kinds.
- The scenario test passes; README and docs quote the messages the code
  prints; the manual run's transcript shows unchanged `git status` at
  every step.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run pytest tests/test_validate_targets.py tests/test_sidecar_overlay.py tests/test_sidecar_install.py tests/test_sidecar_update.py tests/test_sidecar_uninstall.py tests/test_install_bootstrap.py tests/test_sidecar_workflow_scenario.py -q --tb=short
uv run python scripts/validate_plan_frontmatter.py
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py fast --format json
```

This phase changes `scripts/` files copied into `dist/multi-agent/` and
installed under `.claude/`. Run the self-install
(`uv run python scripts/install_bootstrap.py . --allow-self --local-only`)
after regenerating and before `verify closeout`. Time the full suite before
closeout and compare it with `COMMAND_TIMEOUT_SECONDS` in
`shared/scripts/verify.py`.

## Optional Verification

- The manual run against a clone of a real consumer in step 9, recorded
  in the closeout session log.

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
