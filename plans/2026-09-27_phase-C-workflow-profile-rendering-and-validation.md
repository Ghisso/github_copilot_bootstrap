---
name: 2026-09-27_phase-C-workflow-profile-rendering-and-validation
type: small-plan
parent_plan: sidecar-workflow-profile
phase_index: 3
status: planned
closeout_session_log:
---

# Small Plan: Phase C — Workflow Profile Rendering and Validation

## Scope

Render the workflow profile into `dist/sidecar/workflow/` and move today's
sidecar output to `dist/sidecar/skills/`, byte-identical. Split the
validator's sidecar allowlist and forbidden tokens per profile. Move the
profile constants into `scripts/runtime_ownership.py` so the generator, the
validator, and the installer share one definition (big plan Decisions 1, 6,
8, 9, and 11).

### Required Skills

- `shared/skills/ponytail/SKILL.md` — `full`
- `shared/skills/code-style/SKILL.md`
- `shared/skills/testing-patterns/SKILL.md`

## Primary Files

- `scripts/runtime_ownership.py` — `SIDECAR_PROFILES` and per-profile
  skills, unit roots, bridges, state paths, and the shared source contract.
- `scripts/generate_targets.py` — `render_sidecar(target_root, profile)`,
  agent rendering with the workflow supplement, rules and instructions
  rendering, state seeds.
- `scripts/validate_targets.py` — per-profile allowlist, forbidden tokens,
  completeness, and adversarial self-tests.
- `tests/test_validate_targets.py`, `tests/test_generate_targets.py` (or the
  existing generator tests).

## Steps

- [ ] **1. Profile constants.**
  - **Owner:** `coder`
  - `SIDECAR_PROFILES = ("skills", "workflow")`; per profile: skills (the
    four, or every public skill minus the denylist read from
    `shared/sidecar/workflow/skills.txt` at generation time and frozen into
    the constant by a generated module or a checked-in list, decide and
    state which), single-file units per client (bridges, rules, agents,
    review profiles, templates) with their frontmatter, the state root
    `.claude/ai-bootstrap` and its seeds, write roots, and read roots from
    Phase A's frozen table. `sidecar_source_violations(present, profile)`
    takes the profile. Today's constants keep their names as the `skills`
    profile so `sidecar_overlay.py` needs no change in this phase.

- [ ] **2. Rendering.**
  - **Owner:** `coder`
  - `generate` renders `dist/sidecar/skills/` and `dist/sidecar/workflow/`.
    The `skills` output must be byte-identical to today's `dist/sidecar/`
    (assert in a test against a snapshot hash). The `workflow` output
    renders: eligible skills at both write roots with the text
    replacements and licenses; agents per verified client from the
    canonical prompt plus `workflow-supplement.md` through the existing
    provider adapters (`render_claude_agents`,
    `render_github_agent_adapter`, and the Codex adapter only if Phase A
    allowed it); `.claude/rules/ai-bootstrap-*.md` from
    `shared/sidecar/workflow/rules/`; the Copilot instructions file with
    `applyTo: "**"`; review profiles and templates copied verbatim with the
    path rewrite to `.claude/ai-bootstrap/`; the state seeds.

- [ ] **3. Validator per profile.**
  - **Owner:** `coder`
  - `sidecar_allowed_relative_path(path, profile)`,
    `sidecar_text_errors(path, text, profile)`, and
    `sidecar_target_errors(root, profile)`. The workflow forbidden list
    keeps every current token except `MEMORY.md` and adds `settings.json`,
    `core.hooksPath`, `ai-state`, `state-sync`, and `.claude/plans/` (the
    profile uses `.claude/ai-bootstrap/plans/`). Adversarial self-tests per
    profile: a disallowed path, a leaked token, a missing unit, an extra
    unit, a rule file without the `ai-bootstrap-` prefix, an agent text
    naming a receipt.
  - `full_install_root_coverage_errors` is unchanged.

- [ ] **4. Tests.**
  - **Owner:** `coder`
  - Snapshot equality for the `skills` profile; every workflow unit present
    and self-contained; the denylist honored; agents render only for the
    clients Phase A allowed; determinism for both profiles.

## Acceptance Criteria

- `uv run python scripts/generate_targets.py --all` writes both profile
  trees; `dist/sidecar/skills/` equals today's `dist/sidecar/` byte for
  byte.
- `uv run python scripts/validate_targets.py` passes with both profiles and
  fails each adversarial case.
- No workflow text names a forbidden token.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run pytest tests/test_validate_targets.py tests/test_sidecar_overlay.py -q --tb=short
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
uv run python .claude/scripts/verify.py fast --format json
```

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
