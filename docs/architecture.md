# Architecture

The bootstrap now uses a source-of-truth plus generated-target layout.

## Source Directories

- `shared/policies/`: reusable workflow, quality, code, testing, routing, and deployment guidance.
- `shared/skills/`: reusable skills copied from the original Copilot bootstrap.
- `shared/hooks/`: hook config and guardrail scripts.
- `shared/mcp/servers.yaml`: single MCP server definition for Semble and context-mode.
- `shared/agents/`: canonical custom-agent metadata, neutral prompts, and target forks.
- `shared/prompts/`: reusable prompt templates.
- `shared/schemas/`: schema documentation for shared metadata.
- `.github/MEMORY.md`, `.github/templates/`, `.github/scripts/quality_score.py`, and the workflow directories are legacy source inputs rendered into the shared `.claude/` basis.

## Generated Target

The single installable output is `dist/multi-agent/`.

It includes the `.claude/` shared basis for skills, instructions, canonical agent bodies, prompts, memory, plans, explorations, session logs, quality reports, templates, quality scoring, and hook scripts. Native files outside `.claude/` are thin adapters or runtime config for GitHub Copilot, Claude Code, and OpenAI Codex.

Do not edit `dist/` manually. Regenerate it with:

```bash
python3 scripts/generate_targets.py --all
```

## Custom Agents

Custom agents are source-controlled under `shared/agents/<agent-id>/`.

Each agent contains:

- `agent.yaml`: stable metadata and target mapping.
- `prompt.md`: target-neutral behavior.
- `targets/github-copilot.md`: Copilot-native frontmatter source for adapter generation.
- `targets/claude-code.md`: canonical `.claude/agents/*.md` behavior.
- `targets/openai-codex.md`: retained target guidance source for compatibility checks.

Copilot model fields are target bindings, not portable semantics. GitHub Copilot agent `model` fields must be a single supported Copilot model string. Claude and Codex adapters must not include Copilot model pins. Codex agents are generated as project-scoped `.codex/agents/*.toml` adapters that point to `.claude/agents/`. Codex skills are generated under `.claude/skills/` and wired through `[[skills.config]]` entries in `.codex/config.toml`.
