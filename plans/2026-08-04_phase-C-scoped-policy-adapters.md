---
name: 2026-08-04_phase-C-scoped-policy-adapters
type: small-plan
parent_plan: bootstrap-guidance-runtime-modernization
phase_index: 3
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-08-04_phase-C-scoped-policy-adapters

## Scope

Add target-neutral applicability metadata to conditional shared policies and
generate native scoped adapters. Keep always-on lifecycle rules concise and do
not create a second editable policy home.

## Ownership

- `coder`: policy metadata schema and target renderers.
- `verifier`: path-scope parity and discovery fixtures.
- `reviewer`: `architecture`, `config`, `tests`, `documentation`, `ponytail`.
- `documenter`: authoring and customization documentation.

## Required Skills

- `ponytail` (`full`), `context-manager-testing`, `testing-patterns`,
  `documentation`, `ponytail-review`.

## Steps

- [ ] Define minimal frontmatter for target-neutral applicability (always-on or
  path patterns) and validate it in `shared/policies/`.
- [ ] Generate Claude `.claude/rules/*.md` with `paths` only for genuinely
  conditional guidance; use always-on rules sparingly.
- [ ] Generate Copilot `applyTo` metadata from the same source patterns.
- [ ] For Codex, use nested `AGENTS.md` only when directory ownership is stable;
  otherwise expose conditional workflows as skills to avoid consuming the
  combined project-doc budget.
- [ ] Preserve `.claude/instructions/` as the canonical installed policy library
  used by agents/skills; native adapters must point to or derive from it and
  must never become authoring sources.
- [ ] Add cross-target tests proving one source policy produces equivalent
  scope semantics and unrelated paths do not load conditional guidance.

## Verification

```bash
uv run pytest tests/test_validate_targets.py -q --tb=short
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
```

## Acceptance Criteria

- Conditional policies load only for relevant paths on supported native clients.
- Scope metadata is single-homed and validated.
- Root guidance budgets from Phase B remain satisfied.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
