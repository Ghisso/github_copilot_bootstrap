# Architecture

The bootstrap now uses a source-of-truth plus generated-target layout.

## Source Directories

- `shared/policies/`: reusable workflow, quality, code, testing, routing, and deployment guidance.
- `shared/skills/`: reusable skills with `visibility: public|background` metadata.
- `shared/hooks/`: hook config and guardrail scripts.
- `shared/mcp/servers.yaml`: single MCP server definition for Semble and context-mode.
- `shared/agents/`: canonical custom-agent metadata and neutral prompts.
- `shared/review-profiles/`: checklists consumed by the unified `reviewer` agent.
- `shared/prompts/`: reusable prompt templates.
- `shared/templates/`, `shared/scripts/`, `shared/MEMORY.md`, and state README directories: source inputs rendered into the shared `.claude/` basis.
- `shared/schemas/`: schema documentation for shared metadata.

## Generated Target

The single installable output is `dist/multi-agent/`.

It includes the `.claude/` shared basis for skills, instructions, review profiles, canonical agent bodies, prompts, memory, plans, explorations, session logs, quality reports, templates, quality scoring, and hook scripts. Native files outside `.claude/` are thin adapters or runtime config for GitHub Copilot, Claude Code, and OpenAI Codex.

Do not edit `dist/` manually. Regenerate it with:

```bash
python3 scripts/generate_targets.py --all
```

## Custom Agents

Custom agents are source-controlled under `shared/agents/<agent-id>/`.

Each agent contains:

- `agent.yaml`: stable metadata, capabilities, visibility, delegates, and model intent.
- `prompt.md`: target-neutral behavior.

The generator derives Copilot, Claude Code, and Codex adapters from those two files. Copilot model fields are target bindings, not portable semantics. GitHub Copilot agent `model` fields must be a single supported Copilot model string. Claude and Codex adapters must not include Copilot model pins. Codex agents are generated as project-scoped `.codex/agents/*.toml` adapters that point to `.claude/agents/`. Codex skills are generated under `.claude/skills/` and wired through `[[skills.config]]` entries in `.codex/config.toml`.
