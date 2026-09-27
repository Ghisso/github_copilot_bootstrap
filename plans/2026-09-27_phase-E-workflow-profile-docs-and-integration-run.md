---
name: 2026-09-27_phase-E-workflow-profile-docs-and-integration-run
type: small-plan
parent_plan: sidecar-workflow-profile
phase_index: 5
status: planned
closeout_session_log:
---

# Small Plan: Phase E — Workflow Profile Docs and Integration Run

## Scope

Document the workflow profile for the person who installs it, and prove
it end to end against a clone of a real full consumer whose `.claude/`
has been made team-tracked, through the CLI only. The run is a scripted
scenario kept in `tests/` so it stays reproducible (big plan Done
Criteria).

### Required Skills

- `shared/skills/documentation/SKILL.md`
- `shared/skills/humanize/SKILL.md`
- `shared/skills/testing-patterns/SKILL.md`
- `shared/skills/ponytail/SKILL.md` — `full`, for the scenario script

## Primary Files

- `README.md` — the sidecar section: profiles, what the workflow profile
  ships per client, the state folder and its rules, `--purge-state`,
  `--backup-state`, the `git clean -x` risk, profile switching, and the
  relaxed-loop description.
- `docs/target-mapping.md`, `docs/architecture.md` — profile trees and the
  unit kinds.
- `docs/sidecar-provider-contract.md` — link the frozen matrix to the
  shipped coverage.
- `tests/test_sidecar_workflow_scenario.py` — the end-to-end scenario.

## Steps

- [ ] **1. Documentation.**
  - **Owner:** `documenter`
  - Quote every message the installer prints for the profile. State
    plainly that the profile enforces nothing and that the repository's
    own guidance wins.

- [ ] **2. End-to-end scenario.**
  - **Owner:** `coder`
  - A test that builds a team repository from a fixture with a tracked
    `.claude/settings.json`, a tracked team skill, a tracked team agent,
    a tracked rule, and code; installs `--profile workflow`; asserts
    status unchanged, every unit present, the team units reported as
    taken, the state folder seeded; writes a plan and a session log into
    the state folder; updates with a second bootstrap version that drops
    one skill and changes one agent; asserts the state files untouched;
    switches to `--profile skills` and back; `--backup-state`;
    `--uninstall` keeps the state; `--uninstall --purge-state` moves it;
    reinstalls and reseeds. Every step also runs `--dry-run` first and
    asserts parity.

- [ ] **3. Manual run against a real clone.**
  - **Owner:** `orchestrator`
  - Clone one of the maintainer's consumers into the scratchpad, commit a
    `.claude/settings.json` there as the team would, run the scenario's
    CLI steps by hand, and record the transcript in the closeout session
    log. Never touch the source project.

## Acceptance Criteria

- The scenario test passes and takes under 60 seconds.
- README and docs describe both profiles with the messages the code
  prints.
- The manual run's transcript shows unchanged `git status` at every step.

## Verification

```bash
uv run pytest tests/test_sidecar_workflow_scenario.py tests/test_sidecar_install.py -q --tb=short
uv run python scripts/validate_targets.py
uv run python scripts/validate_plan_frontmatter.py
uv run python .claude/scripts/verify.py fast --format json
```

## Optional Verification

- The manual run against a clone of a real consumer, recorded in the
  closeout session log.

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
