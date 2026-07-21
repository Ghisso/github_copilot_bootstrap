# MEMORY.md — Cross-Session Learning Notes

<!-- Project-specific state for this bootstrap repository. -->

## Domain-Specific

- [LEARN:domain] This repository is a source-of-truth multi-target agent
  bootstrap, not a Hydra/BentoML/Haystack/Gradio application. Generated output
  is `dist/multi-agent/`; durable project findings are in
  `.claude/instructions/project-context.instructions.md`.

## Workflow

- [LEARN:workflow] An implementation branch named `<slug>_implementation`
  requires a matching `.claude/plans/<slug>.md` big plan; a governing design
  under top-level `plans/` does not satisfy the commit lifecycle gate.
- [LEARN:workflow] Configuration and validator allow-list migrations should be
  one atomic phase when the previous validator rejects the new contract, so
  every phase boundary remains green.
- [LEARN:quality] The authoring repository uses `scripts/validate_targets.py`
  as its adversarial suite. Keep `tests/test_validate_targets.py` as the
  pytest integration entrypoint so the canonical quality scorer exercises that
  real suite instead of reporting a false no-tests failure.
- [LEARN:runtime] Codex 0.144.x MultiAgent V2 hides custom-agent spawn routing
  metadata by default. Set
  `[features.multi_agent_v2].hide_spawn_agent_metadata = false` and
  `tool_namespace = "agents"` so named `.codex/agents/*.toml` model and effort
  overrides reach child threads instead of inheriting the parent session.
- [LEARN:installer] Generated seeds for consumer-owned mutable state must be
  copy-if-absent. State migration and git history cannot protect content that
  the installer overwrites before synchronization begins.
- [LEARN:installer] A warn-never-fail sync hook cannot prove an installer
  preserved state; the installer must verify nested Git postconditions before
  copying generated files. Local-only promises also need Git Trace2 coverage,
  because unchanged remote refs prove no push but not no remote read. See
  `.claude/skills/safe-consumer-bootstrap-refresh/SKILL.md`.
- [LEARN:testing] Cover state-sync entry points directly from the generated
  `.devcontainer` copy: installer coverage cannot prove that `pull
  --local-only` initializes a fresh nested repository or that an invalid
  `AI_STATE_REPO_ROOT` falls back to the consumer root.
