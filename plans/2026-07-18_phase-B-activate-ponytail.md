---
name: 2026-07-18_phase-B-activate-ponytail
type: small-plan
parent_plan: ponytail-integration
phase_index: 2
status: complete
closeout_session_log: plans/2026-07-18_ponytail-integration-closeout.md
---

# Small Plan: 2026-07-18_phase-B-activate-ponytail

## Scope

Make Ponytail `full` mode part of every code-writing path: main-thread work,
delegated coder work, bug fixes, refactors, tests, scripts, and control-plane
changes. Use canonical instructions and skill discovery so behavior is uniform
across GitHub Copilot, Claude Code, and OpenAI Codex.

## Steps

- [ ] Add a concise mandatory Ponytail section to
  `shared/policies/workspace.instructions.md`.
  - Trigger for writing, adding, changing, fixing, refactoring, reviewing, or
    designing code and for dependency selection.
  - Require reading `.claude/skills/ponytail/SKILL.md` before the first code
    edit and keeping `full` mode active for the task.
  - State that existing correctness, security, accessibility, and test rules
    take precedence over code-size reduction.
- [ ] Modify `shared/policies/workflow.instructions.md`.
  - Insert `PONYTAIL` between PLAN and IMPLEMENT as a required implementation
    constraint, without renaming the public lifecycle states consumed by hooks.
  - Add a mandatory Ponytail diff review within REVIEW before findings are
    recorded.
  - Require coder re-entry when Ponytail findings survive.
- [ ] Modify the canonical coder body under `shared/agents/coder/`.
  - Load Ponytail before any edit.
  - Search for existing helpers and trace callers before writing.
  - Run a self-check against the minimal-solution ladder before returning.
  - Preserve config-first design where configuration is genuinely variable;
    do not create configuration solely for hypothetical flexibility.
- [ ] Modify the orchestrator and planner bodies only enough to ensure
  implementation tasks carry the Ponytail requirement into delegated prompts.
  Read-only exploration, verification, and documentation work must not be
  forced into a coding persona.
- [ ] Modify `scripts/generate_targets.py` root guidance/adapters so direct
  main-thread coding in Copilot, Claude, or Codex points to the canonical
  Ponytail skill before editing code.
- [ ] Extend `scripts/validate_targets.py` with structural assertions that:
  - every target's root guidance contains the canonical Ponytail pointer;
  - the coder adapter points to the canonical coder body;
  - planner/orchestrator delegation guidance preserves the requirement;
  - Ponytail does not replace security, tests, review, or score gates.
- [ ] Add adversarial generated-text cases that fail validation when a target
  omits Ponytail or embeds a divergent target-specific copy of its rules.

## Verification

```bash
uv run python scripts/generate_targets.py --all
uv run python scripts/validate_targets.py
uv run python scripts/check_runtime.py
```

## Closeout Checklist

- [ ] Verification passed
- [ ] Review findings resolved
- [ ] Score >= 90 persisted with branch/phase metadata
- [ ] Documentation updated or explicitly skipped as pure-internal
- [ ] LEARN entries saved or no-lessons marker recorded
- [ ] Closeout session log has `**Status:** COMPLETED`
