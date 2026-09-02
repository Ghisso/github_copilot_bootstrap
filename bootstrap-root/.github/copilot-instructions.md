# GitHub Copilot Workspace Adapter

This target is generated from `shared/`. Do not edit generated files manually.

`.claude/` is the canonical shared project space for all AI systems in this repo. Use it for skills, plans, explorations, session logs, quality reports, memory, templates, prompts, shared agent bodies, and hook scripts.

Native Copilot files under `.github/` are adapters:

- `.github/instructions/*.instructions.md` preserves Copilot discovery and points to `.claude/instructions/`.
- `.github/agents/*.agent.md` preserves Copilot agent metadata and points to `.claude/agents/`.
- `.github/hooks/hooks.json` invokes shared hook scripts in `.claude/hooks/scripts/`.

Before planning or implementation, load the relevant canonical instruction files from `.claude/instructions/`, especially `workflow.instructions.md`, `quality-and-testing.instructions.md`, and `tool-routing.instructions.md`. Before every coding action, load `.claude/skills/ponytail/SKILL.md` in `full` mode.

Preserve the pre-flight -> branch -> plan -> implement -> verify -> review -> document -> learn -> session-log -> commit workflow. A passing `verify phase` plus required documentation updates are mandatory before commit or PR closeout. Write all plans, session logs, exploration notes, memory updates, and quality reports under `.claude/`, not target-local `.github/` or `.codex/` state directories.
