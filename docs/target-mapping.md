# Target Mapping

## GitHub Copilot

Generated under `dist/github-copilot/`:

- `.github/copilot-instructions.md`
- `.github/instructions/*.instructions.md`
- `.github/agents/*.agent.md`
- `.github/prompts/*.prompt.md`
- `.github/skills/**/SKILL.md`
- `.github/scripts/quality_score.py`
- `.github/templates/*.md`
- `.github/MEMORY.md`, `.github/plans/`, `.github/session_logs/`, `.github/quality_reports/`, `.github/explorations/`
- `.github/hooks/hooks.json`
- `.github/hooks/scripts/*.sh`
- `.vscode/mcp.json`

GitHub Copilot preserves current custom agent files exactly. Any `model` frontmatter is a single current Copilot model string, matching GitHub's custom-agent configuration shape.

## Claude Code

Generated under `dist/claude-code/`:

- `CLAUDE.md`
- `.mcp.json`
- `.claude/settings.json`
- `.claude/skills/**/SKILL.md`
- `.claude/scripts/quality_score.py`
- `.claude/templates/*.md`
- `.claude/MEMORY.md`, `.claude/plans/`, `.claude/session_logs/`, `.claude/quality_reports/`, `.claude/explorations/`
- `.claude/agents/*.md`
- `.claude/hooks/scripts/*.sh`

Claude Code agents use project subagent files in `.claude/agents/`. Copilot model fields are omitted. Review helpers are mapped to:

- `review-pass-claude-primary`
- `review-pass-claude-adversarial`

Claude MCP config uses the Claude Code project format with a top-level `mcpServers` object.

## OpenAI Codex

Generated under `dist/openai-codex/`:

- `AGENTS.md`
- `.codex/config.toml`
- `.codex/hooks.json`
- `.codex/agents/*.toml`
- `.agents/skills/**/SKILL.md`
- `.codex/scripts/quality_score.py`
- `.codex/templates/*.md`
- `.codex/MEMORY.md`, `.codex/plans/`, `.codex/session_logs/`, `.codex/quality_reports/`, `.codex/explorations/`
- `.codex/hooks/scripts/*.sh`

Codex skills are generated under `.agents/skills/`, while Codex project custom agents remain under `.codex/agents/`.

Codex agent behavior is rendered as native project custom agents. Each generated `.codex/agents/*.toml` file includes `name`, `description`, and `developer_instructions`. Review helpers are mapped to:

- `review-pass-codex-primary`
- `review-pass-codex-adversarial`

Codex MCP config uses `[mcp_servers.<name>]` tables. Project hooks are enabled with `[features].codex_hooks = true` and use Codex's nested hook group shape in `.codex/hooks.json`.
