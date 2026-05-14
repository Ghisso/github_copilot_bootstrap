# Target Mapping

The repo generates one installable output: `dist/multi-agent/`.

## Shared Basis

The shared basis lives under `.claude/`:

- `.claude/skills/**/SKILL.md`
- `.claude/instructions/*.instructions.md`
- `.claude/agents/*.md`
- `.claude/prompts/*.prompt.md`
- `.claude/scripts/quality_score.py`
- `.claude/templates/*.md`
- `.claude/MEMORY.md`, `.claude/plans/`, `.claude/session_logs/`, `.claude/quality_reports/`, `.claude/explorations/`
- `.claude/hooks/scripts/*.sh`

Keep `.claude/` when pruning optional tool adapters, because it is the shared basis for all supported systems.

## Native Adapters

GitHub Copilot:

- `.github/copilot-instructions.md`
- `.github/instructions/*.instructions.md`
- `.github/agents/*.agent.md`
- `.github/hooks/hooks.json`
- `.vscode/mcp.json`

Copilot files are native adapters. Agent wrappers preserve Copilot frontmatter and point to `.claude/agents/`; instruction wrappers preserve Copilot discovery and point to `.claude/instructions/`; hook config invokes `.claude/hooks/scripts/`.

Claude Code:

- `CLAUDE.md`
- `.mcp.json`
- `.claude/settings.json`

Claude Code uses `.claude/agents/` and `.claude/skills/` natively. Review helpers are mapped to:

- `review-pass-claude-primary`
- `review-pass-claude-adversarial`

OpenAI Codex:

- `AGENTS.md`
- `.codex/config.toml`
- `.codex/hooks.json`
- `.codex/agents/*.toml`

Codex custom agents remain project-scoped `.codex/agents/*.toml` files with `name`, `description`, and `developer_instructions`. Each adapter points to the canonical body in `.claude/agents/`.

Codex skills are stored under `.claude/skills/` and enabled through `[[skills.config]]` entries in `.codex/config.toml` with paths such as `../.claude/skills/run-tests`. Codex project trust is required for that project config, hooks, and skill wiring to load.
