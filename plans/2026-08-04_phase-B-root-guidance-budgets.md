---
name: 2026-08-04_phase-B-root-guidance-budgets
type: small-plan
parent_plan: bootstrap-guidance-runtime-modernization
phase_index: 2
status: in-progress
closeout_session_log:
---

# Small Plan: 2026-08-04_phase-B-root-guidance-budgets

## Scope

Replace full-policy concatenation in generated `CLAUDE.md` and `AGENTS.md`
with concise target-native entrypoints. Critical commands and invariants remain
visible at startup; conditional detail stays single-homed in policies/skills.

## Ownership

- `coder`: root-guidance renderer and validator budgets.
- `verifier`: generated-content, discovery, and truncation tests.
- `reviewer`: `code`, `architecture`, `tests`, `documentation`, `ponytail`.
- `documenter`: target mapping and customization guidance.

## Required Skills

- `ponytail` (`full`), `context-manager-testing`, `testing-patterns`,
  `documentation`, `ponytail-review`.

## Steps

- [ ] Replace `render_root_guidance()` policy-body concatenation with a concise
  template containing project purpose, source-of-truth rule, exact `uv`
  commands, task-lane routing, canonical lifecycle, safety constraints, and a
  short map to policies, skills, agents, and hooks.
- [ ] Keep mandatory constraints explicit; do not rely on links for branch,
  verification, documentation-before-score, memory location, or protected
  control-plane behavior.
- [ ] Add generated budgets: Claude target at most 200 lines; Codex root guidance
  at most 16 KiB, leaving headroom under the 32 KiB combined discovery cap.
- [ ] Add duplicate-section and stale-phase-order assertions rather than broad
  substring-only validation.
- [ ] Verify installation substitutions still fill project name, Python
  version, and target-specific paths without expanding beyond budgets.

## Verification

```bash
uv run pytest tests/test_validate_targets.py tests/test_install_bootstrap.py -q --tb=short
uv run python scripts/generate_targets.py --all
wc -l -c dist/multi-agent/CLAUDE.md dist/multi-agent/AGENTS.md
uv run python scripts/validate_targets.py
```

## Acceptance Criteria

- Both root files meet budgets and retain every mechanically required invariant.
- No canonical policy section is copied wholesale into either root file.
- Generated output remains deterministic.

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
