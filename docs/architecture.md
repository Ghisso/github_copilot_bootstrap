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
- `.github/MEMORY.md`, `.github/templates/`, `.github/scripts/quality_score.py`, and the workflow directories are copied as target-native support files.

## Generated Targets

- `dist/github-copilot/`: GitHub Copilot in VS Code.
- `dist/claude-code/`: Claude Code official VS Code extension.
- `dist/openai-codex/`: OpenAI Codex VS Code extension.

Do not edit `dist/` manually. Regenerate it with:

```bash
python3 scripts/generate_targets.py --all
```

## Custom Agents

Custom agents are source-controlled under `shared/agents/<agent-id>/`.

Each agent contains:

- `agent.yaml`: stable metadata and target mapping.
- `prompt.md`: target-neutral behavior.
- `targets/github-copilot.md`: original Copilot-native agent file.
- `targets/claude-code.md`: Claude Code subagent behavior.
- `targets/openai-codex.md`: Codex custom-agent behavior rendered into TOML.

Copilot model fields are target bindings, not portable semantics. GitHub Copilot agent `model` fields must be a single supported Copilot model string. Claude and Codex outputs must not include Copilot model pins. Codex agents are generated as project-scoped `.codex/agents/*.toml` files with `name`, `description`, and `developer_instructions`. Codex skills are generated separately under `.agents/skills/`.
