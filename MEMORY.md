# MEMORY.md — Cross-Session Learning Notes

<!-- Project-specific state for this bootstrap repository. -->

## Domain-Specific

- [LEARN:domain] This repository is a source-of-truth multi-target agent
  bootstrap, not a Hydra/BentoML/Haystack/Gradio application. Generated output
  is `dist/multi-agent/`; durable project findings are in
  `.claude/instructions/project-context.instructions.md`.

## Workflow

- [LEARN:workflow] Configuration and validator allow-list migrations should be
  one atomic phase when the previous validator rejects the new contract, so
  every phase boundary remains green.
- [LEARN:quality] The authoring repository uses `scripts/validate_targets.py`
  as its adversarial suite and has no `tests/` directory. The shared
  consumer-oriented `quality_score.py` therefore cannot produce a meaningful
  passing authoring-repository score until its project profile is adapted.
- [LEARN:runtime] Codex 0.144.x MultiAgent V2 hides custom-agent spawn routing
  metadata by default. Set
  `[features.multi_agent_v2].hide_spawn_agent_metadata = false` and
  `tool_namespace = "agents"` so named `.codex/agents/*.toml` model and effort
  overrides reach child threads instead of inheriting the parent session.
- [LEARN:installer] Generated seeds for consumer-owned mutable state must be
  copy-if-absent. State migration and git history cannot protect content that
  the installer overwrites before synchronization begins.
